package modmgr

// QA (black-box) helpers. Everything lives in t.TempDir(); the fake user
// folders come from testkit.Folders, never the real ones.

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/deploy"
	"github.com/snakex21/game-launcher/go/internal/modmgr/fsx"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/ids"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

type qaWorld struct {
	t       *testing.T
	base    string
	app     string
	folders map[gamedef.RootKind]string
	svc     *Service
	running []string
}

func qaNew(t *testing.T) *qaWorld {
	t.Helper()
	base := filepath.Join(t.TempDir(), "QA ąęśżźćńół Gry")
	w := &qaWorld{t: t, base: base, app: filepath.Join(base, "Launcher ŻÓŁĆ ąę")}
	w.folders = testkit.Folders(t, filepath.Join(base, "Użytkownik Łódź"))
	w.reopen()
	return w
}

func (w *qaWorld) reopen() {
	w.t.Helper()
	svc, err := New(w.app, Options{Folders: w.folders, Running: func() ([]string, error) { return w.running, nil }})
	if err != nil {
		w.t.Fatal(err)
	}
	w.svc = svc
}

// game creates a fake install of defID in a folder with spaces and Polish
// characters and registers it.
func (w *qaWorld) game(defID, folder string) (string, *Install) {
	w.t.Helper()
	d := w.svc.Defs().Get(defID)
	if d == nil {
		w.t.Fatalf("no def %s", defID)
	}
	dir := filepath.Join(w.base, "Biblioteka gier", folder)
	testkit.Game(w.t, d, dir)
	in, err := w.svc.AddInstall(AddInstallIn{DefID: defID, Path: dir})
	if err != nil {
		w.t.Fatal(err)
	}
	return dir, in
}

func (w *qaWorld) zip(name string, files map[string]string) string {
	return testkit.Zip(w.t, filepath.Join(w.base, "Pobrane mody ąę", name), files)
}

func (w *qaWorld) imp(inst, path string, enable bool) string {
	w.t.Helper()
	row, _, err := w.svc.Import(ImportIn{Install: inst, Path: path, Enable: enable, AckExecutable: true})
	if err != nil {
		w.t.Fatal(err)
	}
	return row.ID
}

func (w *qaWorld) must(err error) {
	w.t.Helper()
	if err != nil {
		w.t.Fatal(err)
	}
}

// snap is a full snapshot of the game plus every fake user folder.
func (w *qaWorld) snap(game string) map[string]string {
	out := map[string]string{}
	for k, v := range qaSnapshot(w.t, game) {
		out["game:"+k] = v
	}
	for kind, dir := range w.folders {
		for k, v := range qaSnapshot(w.t, dir) {
			out[string(kind)+":"+k] = v
		}
	}
	return out
}

// qaSnapshot is testkit.Snapshot plus the modification time and the exact
// on-disk name case (the walk reports real names).
func qaSnapshot(t testing.TB, root string) map[string]string {
	t.Helper()
	out := map[string]string{}
	filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		if d.IsDir() {
			out[rel+"/"] = "dir"
			return nil
		}
		b, _ := os.ReadFile(p)
		st, _ := os.Stat(p)
		h := sha256.Sum256(b)
		out[rel] = fmt.Sprintf("%s|ro=%v|mt=%d", hex.EncodeToString(h[:8]), st.Mode().Perm()&0o200 == 0, st.ModTime().Unix())
		return nil
	})
	return out
}

func qaRead(p string) string {
	b, err := os.ReadFile(p)
	if err != nil {
		return "<brak>"
	}
	return string(b)
}

func qaIsRO(t *testing.T, p string) bool {
	t.Helper()
	st, err := os.Stat(p)
	if err != nil {
		t.Fatalf("stat %s: %v", p, err)
	}
	return st.Mode().Perm()&0o200 == 0
}

// writeRO writes a read-only file with a fixed old modification time.
func qaWriteRO(t *testing.T, root, rel, content string) string {
	t.Helper()
	p := testkit.Write(t, root, rel, content)
	old := time.Date(2011, 11, 11, 11, 11, 11, 0, time.UTC)
	if err := os.Chtimes(p, old, old); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(p, 0o444); err != nil {
		t.Fatal(err)
	}
	return p
}

// replaceFile swaps a file for a new one (how stores update games): never
// writes through an existing hardlink.
func qaReplace(t *testing.T, p, content string) {
	t.Helper()
	_ = os.Chmod(p, 0o644)
	_ = os.Remove(p)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

// storeDir is the store folder of one install's game.
func (w *qaWorld) storeDir(inID string) string {
	p, err := w.svc.FolderPath(inID, "store")
	if err != nil {
		w.t.Fatal(err)
	}
	return p
}

// storeMods lists the mod folders in the store of a game.
func qaDirNames(t *testing.T, dir string) []string {
	ents, err := os.ReadDir(dir)
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		t.Fatal(err)
	}
	var out []string
	for _, e := range ents {
		out = append(out, e.Name())
	}
	sort.Strings(out)
	return out
}

// qaZipEntry is a raw zip entry (for malicious archives).
type qaZipEntry struct {
	name string
	data string
	mode fs.FileMode
	// extAttr overrides the external attributes (Windows attributes in the low byte)
	extAttr uint32
	creator uint16
}

func qaRawZip(t *testing.T, path string, entries []qaZipEntry) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	zw := zip.NewWriter(f)
	for _, e := range entries {
		h := &zip.FileHeader{Name: e.name, Method: zip.Deflate}
		if e.mode != 0 {
			h.SetMode(e.mode)
		}
		if e.extAttr != 0 {
			h.ExternalAttrs = e.extAttr
			h.CreatorVersion = e.creator
		}
		ww, err := zw.CreateHeader(h)
		if err != nil {
			t.Fatal(err)
		}
		ww.Write([]byte(e.data))
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	f.Close()
	return path
}

// qaCrashApply runs the same transaction as Service.Deploy (purge when
// purge is set) but injects a power loss before step n. It reports whether
// the crash was hit.
func (w *qaWorld) qaCrashApply(inID string, purge bool, n int) bool {
	w.t.Helper()
	s := w.svc
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(inID)
	w.must(err)
	e, err := s.engine(in)
	w.must(err)
	var desired []deploy.Desired
	if !purge {
		p, err := s.active(in)
		w.must(err)
		ds, err := s.computeDesired(in, d, p)
		w.must(err)
		desired = ds.desired
		if len(ds.blobs) > 0 {
			dir := ids.New()
			for rel, b := range ds.blobs {
				w.must(fsx.WriteFileAtomic(filepath.Join(s.stateDir(in), "blobs", dir, rel), b, 0o644))
			}
			for i := range desired {
				if desired[i].Source.Type == "@blob" {
					desired[i].Source.Rel = dir + "/" + desired[i].Source.Rel
				}
			}
		}
	}
	plan, err := e.PlanTo(desired, in.ActiveProfile, s.fingerprint(in, d))
	w.must(err)
	hit := false
	e.FailAt = func(i int) error {
		if i == n {
			hit = true
			return deploy.ErrCrash
		}
		return nil
	}
	_, err = e.Apply(plan, deploy.ApplyOptions{AllowProtected: true})
	if hit && !errors.Is(err, deploy.ErrCrash) {
		w.t.Fatalf("crash at %d: unexpected error %v", n, err)
	}
	if !hit && err != nil {
		w.t.Fatalf("apply without crash: %v", err)
	}
	return hit
}

func qaContains(list []string, sub string) bool {
	for _, s := range list {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}
