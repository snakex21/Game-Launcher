package cloud

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

// fakeGitHub implements the endpoints the client uses, in memory.
type fakeGitHub struct {
	mu      sync.Mutex
	token   string
	repos   map[string]*fakeRepo
	created []map[string]any
	blobs   int // blobs uploaded
}

type fakeRepo struct {
	private bool
	head    string
	commits map[string]string            // commit -> tree
	trees   map[string]map[string]string // tree -> path->blob
	objects map[string][]byte            // blob sha -> data
	n       int
}

func newRepo(private bool) *fakeRepo {
	r := &fakeRepo{private: private, commits: map[string]string{}, trees: map[string]map[string]string{}, objects: map[string][]byte{}}
	r.trees["t0"] = map[string]string{}
	r.commits["c0"] = "t0"
	r.head = "c0"
	return r
}

func (f *fakeGitHub) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if r.Header.Get("Authorization") != "Bearer "+f.token {
		w.WriteHeader(401)
		w.Write([]byte(`{"message":"Bad credentials"}`))
		return
	}
	out := func(v any) { json.NewEncoder(w).Encode(v) }
	var body map[string]any
	json.NewDecoder(r.Body).Decode(&body)
	p := r.URL.Path
	if p == "/user" {
		out(map[string]string{"login": "gracz"})
		return
	}
	if p == "/user/repos" && r.Method == "POST" {
		f.created = append(f.created, body)
		name := body["name"].(string)
		f.repos[name] = newRepo(body["private"] == true)
		out(map[string]any{"name": name, "private": body["private"], "default_branch": "main"})
		return
	}
	parts := strings.Split(strings.TrimPrefix(p, "/repos/gracz/"), "/")
	repo := f.repos[parts[0]]
	if repo == nil {
		w.WriteHeader(404)
		w.Write([]byte(`{"message":"Not Found"}`))
		return
	}
	rest := strings.Join(parts[1:], "/")
	switch {
	case rest == "":
		out(map[string]any{"name": parts[0], "private": repo.private, "default_branch": "main"})
	case rest == "git/ref/heads/main":
		out(map[string]any{"object": map[string]string{"sha": repo.head}})
	case strings.HasPrefix(rest, "git/commits/") && r.Method == "GET":
		out(map[string]any{"tree": map[string]string{"sha": repo.commits[strings.TrimPrefix(rest, "git/commits/")]}})
	case strings.HasPrefix(rest, "git/trees/") && r.Method == "GET":
		var list []map[string]string
		for path, sha := range repo.trees[strings.TrimPrefix(rest, "git/trees/")] {
			list = append(list, map[string]string{"path": path, "type": "blob", "sha": sha})
		}
		out(map[string]any{"tree": list})
	case rest == "git/blobs" && r.Method == "POST":
		data, _ := base64.StdEncoding.DecodeString(body["content"].(string))
		sha := BlobSHA(data)
		repo.objects[sha] = data
		f.blobs++
		out(map[string]string{"sha": sha})
	case strings.HasPrefix(rest, "git/blobs/"):
		data := repo.objects[strings.TrimPrefix(rest, "git/blobs/")]
		out(map[string]string{"content": base64.StdEncoding.EncodeToString(data), "encoding": "base64"})
	case rest == "git/trees" && r.Method == "POST":
		base := repo.trees[body["base_tree"].(string)]
		nt := map[string]string{}
		for k, v := range base {
			nt[k] = v
		}
		for _, e := range body["tree"].([]any) {
			m := e.(map[string]any)
			if m["sha"] == nil {
				delete(nt, m["path"].(string))
			} else {
				nt[m["path"].(string)] = m["sha"].(string)
			}
		}
		repo.n++
		id := fmt.Sprintf("t%d", repo.n)
		repo.trees[id] = nt
		out(map[string]string{"sha": id})
	case rest == "git/commits" && r.Method == "POST":
		repo.n++
		id := fmt.Sprintf("c%d", repo.n)
		repo.commits[id] = body["tree"].(string)
		out(map[string]string{"sha": id})
	case rest == "git/refs/heads/main" && r.Method == "PATCH":
		repo.head = body["sha"].(string)
		out(map[string]string{})
	default:
		w.WriteHeader(404)
	}
}

func setup(t *testing.T) (*Client, *fakeGitHub) {
	f := &fakeGitHub{token: "TOKEN-xyz", repos: map[string]*fakeRepo{}}
	srv := httptest.NewServer(f)
	t.Cleanup(srv.Close)
	c := New("TOKEN-xyz")
	c.Base = srv.URL
	return c, f
}

func write(t *testing.T, p, s string) {
	os.MkdirAll(filepath.Dir(p), 0o755)
	if err := os.WriteFile(p, []byte(s), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestRepoIsCreatedPrivate(t *testing.T) {
	c, f := setup(t)
	r, err := c.EnsureRepo(context.Background(), "gl-backup")
	if err != nil || !r.Private {
		t.Fatal(r, err)
	}
	if len(f.created) != 1 || f.created[0]["private"] != true {
		t.Fatalf("created %v", f.created)
	}
	// an existing PUBLIC repo is refused
	f.repos["publiczne"] = newRepo(false)
	if _, err := c.EnsureRepo(context.Background(), "publiczne"); err == nil || !strings.Contains(err.Error(), "PUBLICZNE") {
		t.Fatal("public repo accepted:", err)
	}
	if _, err := c.EnsureRepo(context.Background(), "../x"); err == nil {
		t.Fatal("bad name accepted")
	}
	bad := New("zly")
	bad.Base = c.Base
	if _, err := bad.EnsureRepo(context.Background(), "x"); err == nil || strings.Contains(err.Error(), "zly") {
		t.Fatal("bad token:", err)
	}
}

func TestDiffBackupAndRestore(t *testing.T) {
	c, f := setup(t)
	ctx := context.Background()
	root := t.TempDir()
	write(t, filepath.Join(root, "data", "config", "config.json"), `{"games":{}}`)
	write(t, filepath.Join(root, "data", "games_saves", "Gothic", "saves", "s1", "a.sav"), "save-1")
	write(t, filepath.Join(root, "data", "games_saves", "Gothic", "saves", "s2", "b.sav"), "save-2")
	prefixes := []string{"data/config/config.json", "data/games_saves"}
	r, _ := c.EnsureRepo(ctx, "gl-backup")

	files, _, err := Collect(root, prefixes)
	if err != nil || len(files) != 3 {
		t.Fatal(files, err)
	}
	res, err := c.Backup(ctx, r, files, prefixes, nil)
	if err != nil || res.Uploaded != 3 {
		t.Fatal(res, err)
	}
	// nothing changed -> nothing uploaded, no commit
	res, _ = c.Backup(ctx, r, files, prefixes, nil)
	if res.Uploaded != 0 || res.Unchanged != 3 || res.Commit != "" {
		t.Fatalf("not diff-based: %+v", res)
	}
	// one change + one deletion
	write(t, filepath.Join(root, "data", "config", "config.json"), `{"games":{"X":{}}}`)
	os.RemoveAll(filepath.Join(root, "data", "games_saves", "Gothic", "saves", "s2"))
	files, _, _ = Collect(root, prefixes)
	before := f.blobs
	res, err = c.Backup(ctx, r, files, prefixes, nil)
	if err != nil || res.Uploaded != 1 || res.Deleted != 1 || f.blobs-before != 1 {
		t.Fatalf("%+v %v", res, err)
	}

	// restore into an empty folder
	dst := t.TempDir()
	res, err = c.Restore(ctx, r, dst, prefixes)
	if err != nil || res.Uploaded != 2 {
		t.Fatal(res, err)
	}
	b, _ := os.ReadFile(filepath.Join(dst, "data", "config", "config.json"))
	if string(b) != `{"games":{"X":{}}}` {
		t.Fatal(string(b))
	}
	if _, err := os.Stat(filepath.Join(dst, "data", "games_saves", "Gothic", "saves", "s2")); err == nil {
		t.Fatal("deleted file restored")
	}
	res, _ = c.Restore(ctx, r, dst, prefixes)
	if res.Uploaded != 0 {
		t.Fatal("restore not diff-based")
	}
}

func TestBlobSHA(t *testing.T) {
	// `printf 'hello\n' | git hash-object --stdin`
	if BlobSHA([]byte("hello\n")) != "ce013625030ba8dba906f756967f9e9ca394464a" {
		t.Fatal(BlobSHA([]byte("hello\n")))
	}
}
