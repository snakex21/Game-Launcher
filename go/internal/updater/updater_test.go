package updater

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCompare(t *testing.T) {
	order := []string{"0.9.0", "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0", "v1.0.1", "1.2", "1.10.0"}
	for i := 0; i+1 < len(order); i++ {
		a, _ := Parse(order[i])
		b, _ := Parse(order[i+1])
		if Compare(a, b) >= 0 || Compare(b, a) <= 0 {
			t.Errorf("%s should be < %s", order[i], order[i+1])
		}
	}
	if _, err := Parse("latest"); err == nil {
		t.Fatal("non-version parsed")
	}
}

type fake struct {
	srv      *httptest.Server
	releases []map[string]any
	files    map[string][]byte
}

func newFake(t *testing.T) *fake {
	f := &fake{files: map[string][]byte{}}
	f.srv = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/releases") {
			json.NewEncoder(w).Encode(f.releases)
			return
		}
		if b, ok := f.files[r.URL.Path]; ok {
			w.Write(b)
			return
		}
		w.WriteHeader(404)
	}))
	t.Cleanup(f.srv.Close)
	return f
}

func (f *fake) release(tag string, pre bool, assets ...string) {
	var list []map[string]any
	for _, a := range assets {
		list = append(list, map[string]any{"name": a, "browser_download_url": f.srv.URL + "/dl/" + tag + "/" + a})
	}
	f.releases = append(f.releases, map[string]any{"tag_name": tag, "prerelease": pre, "assets": list, "body": "zmiany " + tag})
}

func TestCheckPicksNewestAndRightAsset(t *testing.T) {
	f := newFake(t)
	f.release("v1.5.1", false, "GameLauncher.exe", "GameLauncher.exe.sha256")
	f.release("v1.10.0", false, "source.zip", "GameLauncher-1.10.0-windows-amd64.exe", "SHA256SUMS")
	f.release("v1.6.0", false, "GameLauncher.exe", "GameLauncher.exe.sha256")
	f.release("v2.0.0-beta.1", true, "GameLauncher.exe", "GameLauncher.exe.sha256")
	c := &Checker{Repo: "o/r", Base: f.srv.URL}
	u, err := c.Check(context.Background(), "1.5.0")
	if err != nil {
		t.Fatal(err)
	}
	if u.Version != "v1.10.0" || u.Asset.Name != "GameLauncher-1.10.0-windows-amd64.exe" || u.SumAsset.Name != "SHA256SUMS" {
		t.Fatalf("%+v", u)
	}
	c.Prerelease = true
	if u, _ := c.Check(context.Background(), "1.5.0"); u.Version != "v2.0.0-beta.1" {
		t.Fatal(u.Version)
	}
	if u, _ := (&Checker{Repo: "o/r", Base: f.srv.URL}).Check(context.Background(), "1.10.0"); u != nil {
		t.Fatal("update offered for the current version")
	}
}

func TestChecksumIsMandatory(t *testing.T) {
	f := newFake(t)
	f.release("v9.0.0", false, "GameLauncher.exe")
	if _, err := (&Checker{Repo: "o/r", Base: f.srv.URL}).Check(context.Background(), "1.0.0"); err == nil || !strings.Contains(err.Error(), "SHA-256") {
		t.Fatal("release without checksum accepted:", err)
	}
}

func TestDownloadVerifiesAndSwapRollback(t *testing.T) {
	f := newFake(t)
	f.release("v2.0.0", false, "GameLauncher.exe", "GameLauncher.exe.sha256")
	good := []byte("NEW-EXE-CONTENT")
	sum := sha256.Sum256(good)
	f.files["/dl/v2.0.0/GameLauncher.exe"] = good
	f.files["/dl/v2.0.0/GameLauncher.exe.sha256"] = []byte(hex.EncodeToString(sum[:]) + "  GameLauncher.exe\n")
	c := &Checker{Repo: "o/r", Base: f.srv.URL}
	u, err := c.Check(context.Background(), "1.0.0")
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	exe := filepath.Join(dir, "GameLauncher.exe")
	os.WriteFile(exe, []byte("OLD"), 0o755)

	// tampered download is rejected and removed
	f.files["/dl/v2.0.0/GameLauncher.exe"] = []byte("EVIL")
	if _, err := c.Download(context.Background(), u, exe); err == nil {
		t.Fatal("bad checksum accepted")
	}
	if _, err := os.Stat(exe + ".new"); err == nil {
		t.Fatal("bad file left behind")
	}
	f.files["/dl/v2.0.0/GameLauncher.exe"] = good
	nf, err := c.Download(context.Background(), u, exe)
	if err != nil {
		t.Fatal(err)
	}
	if err := Swap(exe, nf, "1.0.0", "2.0.0"); err != nil {
		t.Fatal(err)
	}
	if b, _ := os.ReadFile(exe); string(b) != "NEW-EXE-CONTENT" {
		t.Fatal("not swapped")
	}
	// two failed starts of the new version -> rollback on the third
	for i := 0; i < MaxAttempts; i++ {
		if st, _ := OnStartup(exe); st != Trial {
			t.Fatalf("attempt %d: %v", i, st)
		}
	}
	if st, _ := OnStartup(exe); st != RolledBack {
		t.Fatal("no rollback")
	}
	if b, _ := os.ReadFile(exe); string(b) != "OLD" {
		t.Fatal("old exe not restored")
	}
	if st, _ := OnStartup(exe); st != Normal {
		t.Fatal("marker left")
	}
}

func TestConfirm(t *testing.T) {
	dir := t.TempDir()
	exe := filepath.Join(dir, "GameLauncher.exe")
	os.WriteFile(exe, []byte("OLD"), 0o755)
	os.WriteFile(exe+".new", []byte("NEW"), 0o755)
	if err := Swap(exe, exe+".new", "1", "2"); err != nil {
		t.Fatal(err)
	}
	if st, _ := OnStartup(exe); st != Trial {
		t.Fatal(st)
	}
	Confirm(exe)
	if _, err := os.Stat(exe + ".old"); err == nil {
		t.Fatal(".old not removed")
	}
	if st, _ := OnStartup(exe); st != Normal {
		t.Fatal("still trial")
	}
}

func TestExpectedSum(t *testing.T) {
	d := strings.Repeat("a", 64)
	if s, _ := expectedSum(d+"  other.exe\n"+strings.Repeat("b", 64)+" *GameLauncher.exe\n", "GameLauncher.exe"); s != strings.Repeat("b", 64) {
		t.Fatal(s)
	}
	if _, err := expectedSum(d+"  other.exe\n", "GameLauncher.exe"); err == nil {
		t.Fatal("missing sum accepted")
	}
}
