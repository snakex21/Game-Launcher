package deploy

import (
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

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// env is a fake game + store in a temp dir.
type env struct {
	t      *testing.T
	game   string
	docs   string
	store  string
	state  string
	engine *Engine
}

func newEnv(t *testing.T) *env {
	t.Helper()
	base := filepath.Join(t.TempDir(), "Gry Zażółć")
	e := &env{t: t, game: filepath.Join(base, "Moja Gra"), docs: filepath.Join(base, "Dokumenty"), store: filepath.Join(base, "magazyn"), state: filepath.Join(base, "state", "inst")}
	for _, d := range []string{e.game, e.docs, e.store} {
		must(t, os.MkdirAll(d, 0o755))
	}
	e.engine = &Engine{
		InstallID: "inst", StateDir: e.state,
		Roots: map[gamedef.RootKind]string{gamedef.RootGame: e.game, gamedef.RootDocuments: e.docs},
		SourcePath: func(s Source) (string, error) {
			if s.Type == "@blob" {
				return filepath.Join(e.state, "blobs", filepath.FromSlash(s.Rel)), nil
			}
			return filepath.Join(e.store, s.ModID, s.Type, filepath.FromSlash(s.Rel)), nil
		},
		Protected: []string{"*.exe"},
	}
	// vanilla game
	e.write(e.game, "Game.exe", "exe")
	e.write(e.game, "Data/Original.esm", "original esm")
	e.write(e.game, "Data/textures/sky.dds", "vanilla sky")
	e.write(e.game, "Data/ro.ini", "read only original")
	must(t, os.Chmod(filepath.Join(e.game, "Data", "ro.ini"), 0o444))
	old := time.Date(2010, 1, 2, 3, 4, 5, 0, time.UTC)
	must(t, os.Chtimes(filepath.Join(e.game, "Data", "Original.esm"), old, old))
	return e
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func (e *env) write(root, rel, content string) {
	p := filepath.Join(root, filepath.FromSlash(rel))
	must(e.t, os.MkdirAll(filepath.Dir(p), 0o755))
	_ = os.Chmod(p, 0o644)
	must(e.t, os.WriteFile(p, []byte(content), 0o644))
}

// replace swaps a game file for a new one (how stores update files), never
// writing through an existing hardlink.
func (e *env) replace(rel, content string) {
	p := filepath.Join(e.game, filepath.FromSlash(rel))
	tmp := p + ".upd"
	must(e.t, os.WriteFile(tmp, []byte(content), 0o644))
	_ = os.Chmod(p, 0o644)
	must(e.t, os.Remove(p))
	must(e.t, os.Rename(tmp, p))
}

func sum(s string) string { h := sha256.Sum256([]byte(s)); return hex.EncodeToString(h[:]) }

// mod creates a stored mod and returns its desired files (target = game/Data).
func (e *env) mod(id string, files map[string]string) []Desired {
	var out []Desired
	keys := make([]string, 0, len(files))
	for k := range files {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, rel := range keys {
		content := files[rel]
		p := filepath.Join(e.store, id, "data", filepath.FromSlash(rel))
		if _, err := os.Stat(p); err != nil {
			must(e.t, os.MkdirAll(filepath.Dir(p), 0o755))
			must(e.t, os.WriteFile(p, []byte(content), 0o444))
		}
		out = append(out, Desired{
			Target: gamedef.Location{Root: gamedef.RootGame, Rel: "Data/" + rel},
			Source: Source{ModID: id, Type: "data", Rel: rel}, SHA256: sum(content), Size: int64(len(content)), Kind: "hardlink",
		})
	}
	return out
}

// merge applies "later wins" like the conflict index.
func merge(lists ...[]Desired) []Desired {
	m := map[string]Desired{}
	var order []string
	for _, l := range lists {
		for _, d := range l {
			k := d.Target.Key()
			if _, ok := m[k]; !ok {
				order = append(order, k)
			}
			m[k] = d
		}
	}
	var out []Desired
	for _, k := range order {
		out = append(out, m[k])
	}
	return out
}

// snapshot of a folder: rel -> sha|ro|mtime
func snapshot(t *testing.T, root string) map[string]string {
	t.Helper()
	out := map[string]string{}
	filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if d.IsDir() {
			if rel != "." {
				out[rel+"/"] = "dir"
			}
			return nil
		}
		b, _ := os.ReadFile(p)
		st, _ := os.Stat(p)
		out[rel] = fmt.Sprintf("%s|ro=%v", sum(string(b)), st.Mode().Perm()&0o200 == 0)
		if strings.HasSuffix(rel, ".esm") {
			out[rel] += "|" + st.ModTime().UTC().Format(time.RFC3339)
		}
		return nil
	})
	return out
}

func same(a, b map[string]string) string {
	var diffs []string
	for k, v := range a {
		if b[k] != v {
			diffs = append(diffs, fmt.Sprintf("%s: %q vs %q", k, v, b[k]))
		}
	}
	for k, v := range b {
		if _, ok := a[k]; !ok {
			diffs = append(diffs, fmt.Sprintf("%s: missing vs %q", k, v))
		}
	}
	sort.Strings(diffs)
	return strings.Join(diffs, "\n")
}

func (e *env) apply(d []Desired) *Result {
	e.t.Helper()
	p, err := e.engine.PlanTo(d, "p1", nil)
	must(e.t, err)
	r, err := e.engine.Apply(p, ApplyOptions{})
	must(e.t, err)
	return r
}

func (e *env) read(rel string) string {
	b, err := os.ReadFile(filepath.Join(e.game, filepath.FromSlash(rel)))
	if err != nil {
		return "<missing>"
	}
	return string(b)
}

func (e *env) noLeftovers() {
	e.t.Helper()
	var left []string
	filepath.WalkDir(e.state, func(p string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() && (strings.Contains(p, string(filepath.Separator)+"backups"+string(filepath.Separator)) || strings.HasSuffix(p, ".wal")) {
			left = append(left, p)
		}
		return nil
	})
	filepath.WalkDir(e.game, func(p string, d fs.DirEntry, err error) error {
		if err == nil && (strings.HasSuffix(p, ".gl-new") || strings.HasSuffix(p, ".gl-tmp")) {
			left = append(left, p)
		}
		return nil
	})
	if len(left) > 0 {
		e.t.Fatalf("leftovers: %v", left)
	}
}

func TestDeployPurgeRestoresVanillaBitForBit(t *testing.T) {
	e := newEnv(t)
	vanilla := snapshot(t, e.game)
	a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A plugin", "meshes/x/y.nif": "A mesh"})
	b := e.mod("B", map[string]string{"textures/sky.dds": "B sky", "ro.ini": "B ini", "Original.esm": "B replaces esm"})
	r := e.apply(merge(a, b))
	if r.Changed != 5 {
		t.Fatalf("changed %d", r.Changed)
	}
	if e.read("Data/textures/sky.dds") != "B sky" || e.read("Data/a.esp") != "A plugin" || e.read("Data/ro.ini") != "B ini" {
		t.Fatal("wrong winners")
	}
	if d, _, _ := e.engine.Verify(); len(d) != 0 {
		t.Fatal(d)
	}
	e.apply(nil) // purge
	if diff := same(vanilla, snapshot(t, e.game)); diff != "" {
		t.Fatalf("not vanilla after purge:\n%s", diff)
	}
	e.noLeftovers()
	// store untouched and still read-only
	b2, _ := os.ReadFile(filepath.Join(e.store, "B", "data", "textures", "sky.dds"))
	if string(b2) != "B sky" {
		t.Fatal("store changed")
	}
}

func TestProfileSwitchEqualsDirectDeploy(t *testing.T) {
	e := newEnv(t)
	a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A plugin"})
	b := e.mod("B", map[string]string{"textures/sky.dds": "B sky", "b.esp": "B"})
	e.apply(merge(a))
	e.apply(merge(b, a)) // A wins now, B added
	switched := snapshot(t, e.game)
	e.apply(nil)
	e.apply(merge(b, a))
	if diff := same(switched, snapshot(t, e.game)); diff != "" {
		t.Fatal(diff)
	}
	e.apply(merge(a))
	e.apply(merge(a, b))
	if e.read("Data/textures/sky.dds") != "B sky" {
		t.Fatal("order change not applied")
	}
}

func TestUnchangedFilesAreNotTouched(t *testing.T) {
	e := newEnv(t)
	a := e.mod("A", map[string]string{"a.esp": "A plugin"})
	e.apply(a)
	r := e.apply(a)
	if r.Changed != 0 {
		t.Fatal("redeploy changed files", r.Changed)
	}
}

// crash at every step of deploy, purge and switch: after Recover the game is
// exactly before or after, and a second Recover changes nothing.
func TestCrashAtEveryStep(t *testing.T) {
	type scenario struct {
		name        string
		setup, step func(e *env) []Desired
	}
	mods := func(e *env) ([]Desired, []Desired) {
		a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A plugin", "new/dir/f.txt": "deep"})
		b := e.mod("B", map[string]string{"textures/sky.dds": "B sky", "ro.ini": "B ini", "b.esp": "B"})
		return a, b
	}
	scenarios := []scenario{
		{"deploy", func(e *env) []Desired { return nil }, func(e *env) []Desired { a, b := mods(e); return merge(a, b) }},
		{"purge", func(e *env) []Desired { a, b := mods(e); return merge(a, b) }, func(e *env) []Desired { return nil }},
		{"switch", func(e *env) []Desired { a, _ := mods(e); return a }, func(e *env) []Desired { _, b := mods(e); return b }},
	}
	for _, sc := range scenarios {
		for _, crash := range []bool{true, false} {
			for n := 0; ; n++ {
				e := newEnv(t)
				if s := sc.setup(e); s != nil {
					e.apply(s)
				}
				before := snapshot(t, e.game)
				want := sc.step(e)
				// reference "after" state in a twin environment
				twin := newEnv(t)
				if s := sc.setup(twin); s != nil {
					twin.apply(s)
				}
				twin.apply(sc.step(twin))
				after := snapshot(t, twin.game)

				p, err := e.engine.PlanTo(want, "p", nil)
				must(t, err)
				if !crash && n > len(p.Ops)+1 {
					break // after the manifest is written only a crash can stop it
				}
				hit := false
				e.engine.FailAt = func(i int) error {
					if i == n {
						hit = true
						if crash {
							return ErrCrash
						}
						return errors.New("injected")
					}
					return nil
				}
				_, err = e.engine.Apply(p, ApplyOptions{})
				e.engine.FailAt = nil
				if !hit {
					if err != nil {
						t.Fatalf("%s: %v", sc.name, err)
					}
					break // ran past the last step
				}
				if err == nil {
					t.Fatalf("%s n=%d: no error", sc.name, n)
				}
				if _, err := e.engine.Recover(); err != nil {
					t.Fatalf("%s n=%d: recover: %v", sc.name, n, err)
				}
				got := snapshot(t, e.game)
				if same(got, before) != "" && same(got, after) != "" {
					t.Fatalf("%s crash=%v n=%d: intermediate state\nvs before:\n%s\nvs after:\n%s", sc.name, crash, n, same(before, got), same(after, got))
				}
				if !crash && same(got, before) != "" {
					t.Fatalf("%s n=%d: error must roll back", sc.name, n)
				}
				if r, err := e.engine.Recover(); err != nil || len(r) != 0 {
					t.Fatalf("second recover: %v %v", r, err)
				}
				// and the manager can still purge to vanilla
				e.apply(nil)
				e.noLeftovers()
				if n > 40 {
					t.Fatal("runaway")
				}
			}
		}
	}
}

func TestRecoverRollsBackWhenSourceMissing(t *testing.T) {
	e := newEnv(t)
	vanilla := snapshot(t, e.game)
	a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A plugin"})
	p, _ := e.engine.PlanTo(a, "p", nil)
	e.engine.FailAt = func(i int) error {
		if i == 1 {
			return ErrCrash
		}
		return nil
	}
	e.engine.Apply(p, ApplyOptions{})
	e.engine.FailAt = nil
	// the store drive is gone
	must(t, os.Rename(e.store, e.store+"-odlaczony"))
	rep, err := e.engine.Recover()
	if err != nil || len(rep) != 1 || rep[0].Action != "rollback" {
		t.Fatal(rep, err)
	}
	if diff := same(vanilla, snapshot(t, e.game)); diff != "" {
		t.Fatal(diff)
	}
}

func TestGameUpdateDuringDeployment(t *testing.T) {
	e := newEnv(t)
	a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A"})
	e.apply(a)
	// the store updates the file the mod hides, and adds a file where the mod has one
	e.replace("Data/textures/sky.dds", "patched sky v2")
	drift, _, _ := e.engine.Verify()
	if len(drift) != 1 || drift[0].State != "changed" {
		t.Fatal(drift)
	}
	// uninstall after the update: the new game file stays, nothing old comes back
	r := e.apply(nil)
	if e.read("Data/textures/sky.dds") != "patched sky v2" || e.read("Data/a.esp") != "<missing>" {
		t.Fatal("purge after update broke the game file")
	}
	if len(r.Drift) != 1 {
		t.Fatal(r.Drift)
	}
	e.noLeftovers()

	// redeploy after an update: the new version becomes the original
	e.apply(a)
	e.replace("Data/textures/sky.dds", "patched sky v3")
	r = e.apply(a)
	if e.read("Data/textures/sky.dds") != "A sky" || len(r.Drift) != 1 {
		t.Fatal("redeploy did not heal", r.Drift)
	}
	e.apply(nil)
	if e.read("Data/textures/sky.dds") != "patched sky v3" {
		t.Fatal("new original not restored:", e.read("Data/textures/sky.dds"))
	}
	e.noLeftovers()
}

func TestDeletedAndVerifiedFilesHeal(t *testing.T) {
	e := newEnv(t)
	vanilla := snapshot(t, e.game)
	a := e.mod("A", map[string]string{"textures/sky.dds": "A sky", "a.esp": "A"})
	e.apply(a)
	os.Remove(filepath.Join(e.game, "Data", "a.esp"))
	e.replace("Data/textures/sky.dds", "vanilla sky") // "verify files" restored the original
	drift, _, _ := e.engine.Verify()
	if len(drift) != 2 {
		t.Fatal(drift)
	}
	e.apply(a)
	if drift, _, _ := e.engine.Verify(); len(drift) != 0 {
		t.Fatal(drift)
	}
	e.apply(nil)
	if diff := same(vanilla, snapshot(t, e.game)); diff != "" {
		t.Fatal(diff)
	}
}

func TestProtectedNeedsConsent(t *testing.T) {
	e := newEnv(t)
	d := []Desired{{Target: gamedef.Location{Root: gamedef.RootGame, Rel: "Game.exe"}, Source: Source{ModID: "X", Type: "data", Rel: "Game.exe"}, SHA256: sum("patched"), Size: 7}}
	e.write(e.store, "X/data/Game.exe", "patched")
	p, err := e.engine.PlanTo(d, "p", nil)
	must(t, err)
	var pe *ProtectedError
	if _, err := e.engine.Apply(p, ApplyOptions{}); !errors.As(err, &pe) {
		t.Fatal("protected file overwritten without consent", err)
	}
	if e.read("Game.exe") != "exe" {
		t.Fatal("changed")
	}
	if _, err := e.engine.Apply(p, ApplyOptions{AllowProtected: true}); err != nil {
		t.Fatal(err)
	}
	e.apply(nil)
	if e.read("Game.exe") != "exe" {
		t.Fatal("not restored")
	}
}

func TestTornJournalLine(t *testing.T) {
	e := newEnv(t)
	vanilla := snapshot(t, e.game)
	a := e.mod("A", map[string]string{"a.esp": "A"})
	p, _ := e.engine.PlanTo(a, "p", nil)
	e.engine.FailAt = func(i int) error {
		if i == 0 {
			return ErrCrash
		}
		return nil
	}
	e.engine.Apply(p, ApplyOptions{})
	e.engine.FailAt = nil
	// damage: append half a line, then a line with a bad checksum
	f, _ := os.OpenFile(e.engine.walPath(p.TxID), os.O_APPEND|os.O_WRONLY, 0)
	f.WriteString("deadbeef {\"t\":\"COMMIT\"}\n0000")
	f.Close()
	if _, err := e.engine.Recover(); err != nil {
		t.Fatal(err)
	}
	if e.read("Data/a.esp") != "A" {
		t.Fatal("bad CRC line must be ignored (roll forward)")
	}
	e.apply(nil)
	if diff := same(vanilla, snapshot(t, e.game)); diff != "" {
		t.Fatal(diff)
	}
	// a journal without a plan is just discarded
	os.MkdirAll(filepath.Join(e.state, "journal"), 0o755)
	os.WriteFile(filepath.Join(e.state, "journal", "X.wal"), []byte("garbage"), 0o644)
	rep, err := e.engine.Recover()
	if err != nil || rep[0].Action != "discarded" {
		t.Fatal(rep, err)
	}
}

func TestHardlinkSharesStoreAndStaysProtected(t *testing.T) {
	e := newEnv(t)
	a := e.mod("A", map[string]string{"a.esp": "A"})
	e.apply(a)
	m, _ := e.engine.Manifest()
	if m.Entries[0].Kind != "hardlink" {
		t.Skip("hardlinks not supported on this volume")
	}
	// writing through the link must fail (store is read-only)
	if err := os.WriteFile(filepath.Join(e.game, "Data", "a.esp"), []byte("x"), 0o644); err == nil {
		t.Fatal("write through hardlink succeeded")
	}
}

func TestDocumentsRootAndBlob(t *testing.T) {
	e := newEnv(t)
	must(t, os.MkdirAll(filepath.Join(e.state, "blobs", "B1"), 0o755))
	must(t, os.WriteFile(filepath.Join(e.state, "blobs", "B1", "lo"), []byte("*a.esp\r\n"), 0o644))
	e.write(e.docs, "My Games/plugins.txt", "old order")
	d := []Desired{{Target: gamedef.Location{Root: gamedef.RootDocuments, Rel: "My Games/plugins.txt"}, Source: Source{Type: "@blob", Rel: "B1/lo"}, SHA256: sum("*a.esp\r\n"), Size: 8, Kind: "copy"}}
	e.apply(d)
	b, _ := os.ReadFile(filepath.Join(e.docs, "My Games", "plugins.txt"))
	if string(b) != "*a.esp\r\n" {
		t.Fatal(string(b))
	}
	e.apply(nil)
	b, _ = os.ReadFile(filepath.Join(e.docs, "My Games", "plugins.txt"))
	if string(b) != "old order" {
		t.Fatal(string(b))
	}
}
