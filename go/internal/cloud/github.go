// Package cloud backs the launcher data up to a GitHub repository.
//
// Rules:
//   - the repository is ALWAYS private: it is created with private=true and
//     an existing public repository is refused (nothing is uploaded);
//   - uploads are diff-based: files are compared by their git blob SHA-1 and
//     only new/changed blobs are sent; deleted files are removed in the same
//     commit (one commit per backup, via the Git Data API);
//   - the token never appears in errors or logs.
package cloud

import (
	"bytes"
	"context"
	"crypto/sha1"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// API is the GitHub REST base URL (tests point it at a fake).
var API = "https://api.github.com"

// MaxFile is the largest file uploaded (GitHub rejects > 100 MB).
const MaxFile = 50 << 20

// Client talks to GitHub.
type Client struct {
	Token string
	HTTP  *http.Client
	Base  string
}

// New creates a client.
func New(token string) *Client {
	return &Client{Token: strings.TrimSpace(token), HTTP: &http.Client{Timeout: 60 * time.Second}, Base: API}
}

// Error is an API error without secrets.
type Error struct {
	Status  int
	Message string
}

func (e *Error) Error() string { return fmt.Sprintf("GitHub: %s (HTTP %d)", e.Message, e.Status) }

func (c *Client) req(ctx context.Context, method, path string, in, out any) error {
	if c.Token == "" {
		return errors.New("brak tokenu GitHub – dodaj go w Ustawieniach → Klucze API")
	}
	var body io.Reader
	if in != nil {
		b, err := json.Marshal(in)
		if err != nil {
			return err
		}
		body = bytes.NewReader(b)
	}
	r, err := http.NewRequestWithContext(ctx, method, c.Base+path, body)
	if err != nil {
		return err
	}
	r.Header.Set("Authorization", "Bearer "+c.Token)
	r.Header.Set("Accept", "application/vnd.github+json")
	r.Header.Set("X-GitHub-Api-Version", "2022-11-28")
	r.Header.Set("User-Agent", "GameLauncher-Go")
	if in != nil {
		r.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.HTTP.Do(r)
	if err != nil {
		var ue *url.Error
		if errors.As(err, &ue) {
			err = ue.Err
		}
		return fmt.Errorf("GitHub: brak połączenia (%v)", err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 200<<20))
	if resp.StatusCode >= 300 {
		var e struct{ Message string }
		_ = json.Unmarshal(data, &e)
		if e.Message == "" {
			e.Message = http.StatusText(resp.StatusCode)
		}
		return &Error{Status: resp.StatusCode, Message: e.Message}
	}
	if out != nil && len(data) > 0 {
		return json.Unmarshal(data, out)
	}
	return nil
}

func isStatus(err error, code int) bool {
	var e *Error
	return errors.As(err, &e) && e.Status == code
}

// Repo identifies the backup repository.
type Repo struct {
	Owner, Name, Branch string
	Private             bool
}

var validRepo = func(n string) bool {
	if n == "" || len(n) > 100 {
		return false
	}
	for _, r := range n {
		if !(r == '-' || r == '_' || r == '.' || r >= '0' && r <= '9' || r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z') {
			return false
		}
	}
	return true
}

// EnsureRepo finds or creates the PRIVATE repository name of the token's user.
func (c *Client) EnsureRepo(ctx context.Context, name string) (*Repo, error) {
	if !validRepo(name) {
		return nil, errors.New("nieprawidłowa nazwa repozytorium (litery, cyfry, - _ .)")
	}
	var me struct{ Login string }
	if err := c.req(ctx, "GET", "/user", nil, &me); err != nil {
		return nil, err
	}
	var repo struct {
		Name          string `json:"name"`
		Private       bool   `json:"private"`
		DefaultBranch string `json:"default_branch"`
		Owner         struct{ Login string }
	}
	err := c.req(ctx, "GET", "/repos/"+url.PathEscape(me.Login)+"/"+url.PathEscape(name), nil, &repo)
	if isStatus(err, 404) {
		err = c.req(ctx, "POST", "/user/repos", map[string]any{
			"name": name, "private": true, "auto_init": true,
			"description": "Kopia zapasowa Game Launchera (prywatna)",
		}, &repo)
	}
	if err != nil {
		return nil, err
	}
	if !repo.Private {
		return nil, fmt.Errorf("repozytorium %s/%s jest PUBLICZNE – kopia nie zostanie wysłana. Zmień je na prywatne albo podaj inną nazwę", me.Login, name)
	}
	if repo.DefaultBranch == "" {
		repo.DefaultBranch = "main"
	}
	return &Repo{Owner: me.Login, Name: repo.Name, Branch: repo.DefaultBranch, Private: true}, nil
}

func (r *Repo) path(p string) string {
	return "/repos/" + url.PathEscape(r.Owner) + "/" + url.PathEscape(r.Name) + p
}

// BlobSHA is git's object id of a file content.
func BlobSHA(data []byte) string {
	h := sha1.New()
	fmt.Fprintf(h, "blob %d\x00", len(data))
	h.Write(data)
	return hex.EncodeToString(h.Sum(nil))
}

type treeEntry struct {
	Path string  `json:"path"`
	Mode string  `json:"mode"`
	Type string  `json:"type"`
	SHA  *string `json:"sha"`
}

// remoteTree returns path -> blob sha of the branch head (and the head commit).
func (c *Client) remoteTree(ctx context.Context, r *Repo) (map[string]string, string, string, error) {
	var ref struct {
		Object struct{ SHA string } `json:"object"`
	}
	if err := c.req(ctx, "GET", r.path("/git/ref/heads/"+url.PathEscape(r.Branch)), nil, &ref); err != nil {
		return nil, "", "", err
	}
	var commit struct {
		Tree struct{ SHA string } `json:"tree"`
	}
	if err := c.req(ctx, "GET", r.path("/git/commits/"+ref.Object.SHA), nil, &commit); err != nil {
		return nil, "", "", err
	}
	var tree struct {
		Tree []struct {
			Path, Type, SHA string
		} `json:"tree"`
		Truncated bool `json:"truncated"`
	}
	if err := c.req(ctx, "GET", r.path("/git/trees/"+commit.Tree.SHA+"?recursive=1"), nil, &tree); err != nil {
		return nil, "", "", err
	}
	if tree.Truncated {
		return nil, "", "", errors.New("drzewo repozytorium jest za duże dla API GitHub")
	}
	out := map[string]string{}
	for _, e := range tree.Tree {
		if e.Type == "blob" {
			out[e.Path] = e.SHA
		}
	}
	return out, ref.Object.SHA, commit.Tree.SHA, nil
}

// Local lists the files to back up: path in repo -> absolute path.
type Local map[string]string

// Collect walks dirs (relative to root) and adds files (forward slashes).
// Files over MaxFile are skipped and returned.
func Collect(root string, entries []string) (Local, []string, error) {
	out := Local{}
	var skipped []string
	for _, e := range entries {
		abs := filepath.Join(root, filepath.FromSlash(e))
		st, err := os.Stat(abs)
		if err != nil {
			continue
		}
		if !st.IsDir() {
			if st.Size() > MaxFile {
				skipped = append(skipped, e)
				continue
			}
			out[filepath.ToSlash(e)] = abs
			continue
		}
		err = filepath.WalkDir(abs, func(p string, d fs.DirEntry, err error) error {
			if err != nil || d.IsDir() || !d.Type().IsRegular() {
				return nil
			}
			rel, _ := filepath.Rel(root, p)
			if info, err := d.Info(); err == nil && info.Size() > MaxFile {
				skipped = append(skipped, filepath.ToSlash(rel))
				return nil
			}
			out[filepath.ToSlash(rel)] = p
			return nil
		})
		if err != nil {
			return nil, nil, err
		}
	}
	return out, skipped, nil
}

// Result of a backup or restore.
type Result struct {
	Repo      string   `json:"repo"`
	Uploaded  int      `json:"uploaded"`
	Deleted   int      `json:"deleted"`
	Unchanged int      `json:"unchanged"`
	Skipped   []string `json:"skipped,omitempty"`
	Commit    string   `json:"commit,omitempty"`
}

// Backup uploads only what changed under the given prefixes and removes
// remote files under those prefixes that no longer exist locally.
func (c *Client) Backup(ctx context.Context, r *Repo, files Local, prefixes []string, progress func(done, total int)) (*Result, error) {
	remote, head, baseTree, err := c.remoteTree(ctx, r)
	if err != nil {
		return nil, err
	}
	res := &Result{Repo: r.Owner + "/" + r.Name}
	var entries []treeEntry
	paths := make([]string, 0, len(files))
	for p := range files {
		paths = append(paths, p)
	}
	sort.Strings(paths)
	for i, p := range paths {
		data, err := os.ReadFile(files[p])
		if err != nil {
			return nil, err
		}
		sha := BlobSHA(data)
		if remote[p] == sha {
			res.Unchanged++
			continue
		}
		var blob struct{ SHA string }
		if err := c.req(ctx, "POST", r.path("/git/blobs"), map[string]string{"content": base64.StdEncoding.EncodeToString(data), "encoding": "base64"}, &blob); err != nil {
			return nil, err
		}
		s := blob.SHA
		entries = append(entries, treeEntry{Path: p, Mode: "100644", Type: "blob", SHA: &s})
		res.Uploaded++
		if progress != nil {
			progress(i+1, len(paths))
		}
	}
	for p := range remote {
		if _, ok := files[p]; ok {
			continue
		}
		for _, pre := range prefixes {
			if p == pre || strings.HasPrefix(p, strings.TrimSuffix(pre, "/")+"/") {
				entries = append(entries, treeEntry{Path: p, Mode: "100644", Type: "blob", SHA: nil})
				res.Deleted++
				break
			}
		}
	}
	if len(entries) == 0 {
		return res, nil
	}
	var tree struct{ SHA string }
	if err := c.req(ctx, "POST", r.path("/git/trees"), map[string]any{"base_tree": baseTree, "tree": entries}, &tree); err != nil {
		return nil, err
	}
	var commit struct{ SHA string }
	msg := fmt.Sprintf("Kopia Game Launchera %s (+%d, -%d)", time.Now().Format("2006-01-02 15:04"), res.Uploaded, res.Deleted)
	if err := c.req(ctx, "POST", r.path("/git/commits"), map[string]any{"message": msg, "tree": tree.SHA, "parents": []string{head}}, &commit); err != nil {
		return nil, err
	}
	if err := c.req(ctx, "PATCH", r.path("/git/refs/heads/"+url.PathEscape(r.Branch)), map[string]any{"sha": commit.SHA}, nil); err != nil {
		return nil, err
	}
	res.Commit = commit.SHA
	return res, nil
}

// Restore downloads files under prefixes that differ from the local copy
// into root (written via a temp file + rename). Only paths under the
// prefixes are written; ".." paths are refused.
func (c *Client) Restore(ctx context.Context, r *Repo, root string, prefixes []string) (*Result, error) {
	remote, _, _, err := c.remoteTree(ctx, r)
	if err != nil {
		return nil, err
	}
	res := &Result{Repo: r.Owner + "/" + r.Name}
	for p, sha := range remote {
		ok := false
		for _, pre := range prefixes {
			if p == pre || strings.HasPrefix(p, strings.TrimSuffix(pre, "/")+"/") {
				ok = true
			}
		}
		clean := filepath.Clean(filepath.FromSlash(p))
		if !ok || strings.HasPrefix(clean, "..") || filepath.IsAbs(clean) {
			continue
		}
		dst := filepath.Join(root, clean)
		if cur, err := os.ReadFile(dst); err == nil && BlobSHA(cur) == sha {
			res.Unchanged++
			continue
		}
		var blob struct {
			Content  string `json:"content"`
			Encoding string `json:"encoding"`
		}
		if err := c.req(ctx, "GET", r.path("/git/blobs/"+sha), nil, &blob); err != nil {
			return nil, err
		}
		data, err := base64.StdEncoding.DecodeString(strings.ReplaceAll(blob.Content, "\n", ""))
		if err != nil || BlobSHA(data) != sha {
			return nil, fmt.Errorf("uszkodzony plik z GitHub: %s", p)
		}
		if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
			return nil, err
		}
		tmp := dst + ".restore-tmp"
		if err := os.WriteFile(tmp, data, 0o644); err != nil {
			return nil, err
		}
		if err := os.Rename(tmp, dst); err != nil {
			os.Remove(tmp)
			return nil, err
		}
		res.Uploaded++ // = downloaded
	}
	return res, nil
}
