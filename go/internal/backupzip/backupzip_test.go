package backupzip

import (
	"archive/zip"
	"os"
	"path/filepath"
	"testing"
)

func write(t *testing.T, p, s string) {
	os.MkdirAll(filepath.Dir(p), 0o755)
	if err := os.WriteFile(p, []byte(s), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestCreateRestore(t *testing.T) {
	app := t.TempDir()
	write(t, filepath.Join(app, "data", "config", "config.json"), "v1")
	write(t, filepath.Join(app, "data", "games_saves", "G", "saves", "s", "a.sav"), "save")
	write(t, filepath.Join(app, "images", "c.png"), "img")
	write(t, filepath.Join(app, "GameLauncher.exe"), "exe") // not backed up
	z := filepath.Join(t.TempDir(), "b.zip")
	n, err := Create(app, z, "test")
	if err != nil || n != 3 {
		t.Fatal(n, err)
	}
	write(t, filepath.Join(app, "data", "config", "config.json"), "v2")
	if n, err := Restore(app, z); err != nil || n != 3 {
		t.Fatal(n, err)
	}
	if b, _ := os.ReadFile(filepath.Join(app, "data", "config", "config.json")); string(b) != "v1" {
		t.Fatal(string(b))
	}
	m, _ := filepath.Glob(filepath.Join(app, "data", "config.before-restore-*"))
	if len(m) != 1 {
		t.Fatal("previous data not kept aside")
	}
}

func evil(t *testing.T, names ...string) string {
	z := filepath.Join(t.TempDir(), "e.zip")
	f, _ := os.Create(z)
	zw := zip.NewWriter(f)
	for _, n := range names {
		w, _ := zw.Create(n)
		w.Write([]byte("x"))
	}
	zw.Close()
	f.Close()
	return z
}

func TestRestoreRejectsBadArchives(t *testing.T) {
	app := t.TempDir()
	for _, names := range [][]string{
		{Manifest, "../evil.txt"},
		{Manifest, "data/config/../../evil.txt"},
		{Manifest, "C:/Windows/evil.dll"},
		{Manifest, "GameLauncher.exe"},
		{"data/config/config.json"}, // no manifest
	} {
		if _, err := Restore(app, evil(t, names...)); err == nil {
			t.Errorf("accepted %v", names)
		}
	}
	if _, err := os.Stat(filepath.Join(filepath.Dir(app), "evil.txt")); err == nil {
		t.Fatal("zip slip")
	}
}
