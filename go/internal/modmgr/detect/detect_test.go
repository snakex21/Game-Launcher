package detect

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

func TestVDF(t *testing.T) {
	src := "\xef\xbb\xbf// comment\n\"libraryfolders\"\n{\n \"0\" { \"path\" \"C:\\\\Program Files (x86)\\\\Steam\" \"apps\" { \"489830\" \"123\" } }\n \"1\" { \"path\" \"E:\\\\Gry \\\"Steam\\\"\" }\n}\n"
	kv, err := ParseVDF([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	if got := kv.Str("libraryfolders", "1", "path"); got != `E:\Gry "Steam"` {
		t.Fatal(got)
	}
	if got := kv.Str("libraryfolders", "0", "apps", "489830"); got != "123" {
		t.Fatal(got)
	}
	for _, bad := range []string{"\"a\" {", "\"a\"", "}", "\"a\" \"b"} {
		if _, err := ParseVDF([]byte(bad)); err == nil {
			t.Errorf("%q accepted", bad)
		}
	}
}

func TestSteamDetection(t *testing.T) {
	base := t.TempDir()
	steam := filepath.Join(base, "Steam")
	lib2 := filepath.Join(base, "Biblioteka ąę")
	esc := func(p string) string { return strings.ReplaceAll(p, `\`, `\\`) }
	os.MkdirAll(filepath.Join(steam, "steamapps"), 0o755)
	os.WriteFile(filepath.Join(steam, "steamapps", "libraryfolders.vdf"), []byte(`"libraryfolders" { "0" { "path" "`+esc(steam)+`" } "1" { "path" "`+esc(lib2)+`" } }`), 0o644)
	game := filepath.Join(lib2, "steamapps", "common", "Skyrim Special Edition")
	os.MkdirAll(filepath.Join(game, "Data"), 0o755)
	os.WriteFile(filepath.Join(game, "SkyrimSE.exe"), []byte("x"), 0o644)
	os.WriteFile(filepath.Join(game, "Data", "Skyrim.esm"), []byte("x"), 0o644)
	os.WriteFile(filepath.Join(lib2, "steamapps", "appmanifest_489830.acf"), []byte(`"AppState" { "appid" "489830" "name" "Skyrim" "installdir" "Skyrim Special Edition" "StateFlags" "4" "buildid" "15012345" }`), 0o644)
	os.WriteFile(filepath.Join(lib2, "steamapps", "appmanifest_1.acf"), []byte(`"AppState" { "appid" "1" "installdir" "..\\..\\Windows" }`), 0o644)
	set, _ := gamedef.Load("")
	found, err := FromSteam(steam, set)
	if err != nil {
		t.Fatal(err)
	}
	if len(found) != 1 || found[0].DefID != "skyrimse" || !found[0].Valid || found[0].BuildID != "15012345" {
		t.Fatal(found)
	}
	apps, _ := SteamApps(steam)
	if len(apps) != 1 || apps[0].Updating() {
		t.Fatal(apps)
	}
}
