package saves

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func write(t *testing.T, p, s string) {
	t.Helper()
	os.MkdirAll(filepath.Dir(p), 0o755)
	if err := os.WriteFile(p, []byte(s), 0o644); err != nil {
		t.Fatal(err)
	}
}

func read(t *testing.T, p string) string {
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

func TestCreateListRestoreDelete(t *testing.T) {
	root := t.TempDir()
	game := "Grand Theft Auto - San Andreas"
	savePath := filepath.Join(t.TempDir(), "GTA User Files")
	write(t, filepath.Join(savePath, "GTASAsf1.b"), "v1")
	write(t, filepath.Join(savePath, "sub", "x.cfg"), "cfg")

	t0 := time.Date(2026, 11, 14, 10, 0, 0, 0, time.Local)
	e, err := Create(root, game, savePath, 40, t0)
	if err != nil {
		t.Fatal(err)
	}
	if e.ID != "Save_40%_20261114_100000" || e.Files != 2 {
		t.Fatalf("%+v", e)
	}
	if _, err := Autosave(root, game, savePath); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(savePath, "GTASAsf1.b"), "v2")     // the player continues
	if _, err := Autosave(root, game, savePath); err != nil { // replace autosave
		t.Fatal(err)
	}
	list, err := List(root, game)
	if err != nil || len(list) != 2 || !list[0].Auto || list[1].Percent != 40 {
		t.Fatalf("%+v %v", list, err)
	}
	if read(t, filepath.Join(root, game, "_autosave", "GTASAsf1.b")) != "v2" {
		t.Fatal("autosave not replaced")
	}

	safety, err := Restore(root, game, e.ID, savePath, t0.Add(time.Hour))
	if err != nil {
		t.Fatal(err)
	}
	if read(t, filepath.Join(savePath, "GTASAsf1.b")) != "v1" {
		t.Fatal("not restored")
	}
	if read(t, filepath.Join(root, game, "saves", safety, "GTASAsf1.b")) != "v2" {
		t.Fatal("pre-restore safety copy missing")
	}
	newID, err := SetPercent(root, game, e.ID, 75)
	if err != nil || newID != "Save_75%_20261114_100000" {
		t.Fatal(newID, err)
	}
	if err := Delete(root, game, newID); err != nil {
		t.Fatal(err)
	}
	if err := Delete(root, game, `..\..\x`); err == nil {
		t.Fatal("path traversal accepted")
	}
	if _, err := Create(root, game, filepath.Join(root, "brak"), 1, t0); err == nil {
		t.Fatal("missing save folder accepted")
	}
}

// Layout written by the Python launcher (user data copy) is listed.
func TestListPythonLayout(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "High on Life", "saves", "Save_1%_20241026_223410", "a.sav"), "x")
	write(t, filepath.Join(root, "High on Life", "saves", "Save_0%_20241026_223438", "a.sav"), "x")
	list, err := List(root, "High on Life")
	if err != nil || len(list) != 2 {
		t.Fatal(list, err)
	}
	if src := os.Getenv("GL_TEST_USERDATA"); src != "" {
		l, err := List(filepath.Join(src, "data", "games_saves"), "Grand Theft Auto - San Andreas")
		if err != nil || len(l) == 0 || !l[0].Auto {
			t.Fatalf("user copy: %+v %v", l, err)
		}
	}
}
