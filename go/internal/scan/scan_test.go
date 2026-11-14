package scan

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func touch(t *testing.T, path string, size int) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, make([]byte, size), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestGuessName(t *testing.T) {
	cases := map[string]string{
		"Gothic.II-PLAZA":               "Gothic II",
		"Stray [FitGirl Repack]":        "Stray",
		"Teardown v1.5.4 (2024)":        "Teardown",
		"Deluxe_Ski_Jumping_4":          "Deluxe Ski Jumping 4",
		"The Witcher 3 GOTY":            "The Witcher 3",
		"Kingdom Come - Deliverance II": "Kingdom Come - Deliverance II",
		"[]":                            "[]",
	}
	for in, want := range cases {
		if got := GuessName(in); got != want {
			t.Errorf("GuessName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestFindExesPrefersFolderNameAndSkipsInstallers(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "Stray")
	touch(t, filepath.Join(dir, "unins000.exe"), 5000)
	touch(t, filepath.Join(dir, "Tool.exe"), 9000)
	touch(t, filepath.Join(dir, "Binaries", "Win64", "Stray-Win64-Shipping.exe"), 100)
	touch(t, filepath.Join(dir, "Stray.exe"), 10)
	exes := FindExes(dir, "Stray")
	if len(exes) != 3 || filepath.Base(exes[0]) != "Stray.exe" {
		t.Fatalf("%v", exes)
	}
	for _, e := range exes {
		if strings.EqualFold(filepath.Base(e), "unins000.exe") {
			t.Fatal("installer offered")
		}
	}
}

func TestRunFindsGamesSkipsKnownAndIgnored(t *testing.T) {
	root := t.TempDir()
	touch(t, filepath.Join(root, "Gry", "Teardown", "teardown.exe"), 10)
	touch(t, filepath.Join(root, "Gry", "Teardown", "data", "inner", "tool.exe"), 10) // inside a game: not a new game
	touch(t, filepath.Join(root, "Gry", "Akcja", "Stray [Repack]", "Stray.exe"), 10)
	touch(t, filepath.Join(root, "Gry", "Znana", "Znana.exe"), 10)
	touch(t, filepath.Join(root, "Gry", "Redist", "vc.exe"), 10)
	touch(t, filepath.Join(root, "Gry", "Pusta", "readme.txt"), 10)

	opt := Options{Folders: []string{filepath.Join(root, "Gry")}, Recursive: true, Ignored: []string{"redist"}, KnownNames: map[string]bool{"znana": true}}
	got, err := Run(context.Background(), opt)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, c := range got {
		names = append(names, c.Name)
	}
	if strings.Join(names, ",") != "Stray,Teardown" {
		t.Fatalf("got %v", names)
	}

	opt.Recursive = false // one level only: "Akcja/Stray" is too deep
	got, _ = Run(context.Background(), opt)
	if len(got) != 1 || got[0].Name != "Teardown" {
		t.Fatalf("non-recursive: %+v", got)
	}
}

func TestRunCancel(t *testing.T) {
	root := t.TempDir()
	touch(t, filepath.Join(root, "A", "a.exe"), 1)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := Run(ctx, Options{Folders: []string{root}, Recursive: true}); err == nil {
		t.Fatal("cancel ignored")
	}
}
