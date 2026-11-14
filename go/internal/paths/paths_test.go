package paths

import (
	"reflect"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

const (
	appE = `E:\Launchery\Game_Launcher`
	appF = `F:\Launchery\Game_Launcher`
)

func TestDriveOf(t *testing.T) {
	cases := map[string]string{
		`E:\Gry\Gothic\Gothic.exe`: "E:",
		"e:/gry/x.exe":             "E:",
		`\Gry\x.exe`:               "",
		`\\nas\gry\x.exe`:          "",
		"images/x.png":             "",
		"":                         "",
	}
	for in, want := range cases {
		if got := DriveOf(in); got != want {
			t.Errorf("DriveOf(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestToPortable(t *testing.T) {
	cases := []struct{ in, want string }{
		{`E:\Gry\Gothic\Gothic.exe`, `\Gry\Gothic\Gothic.exe`},
		{"e:/Gry/Gothic/Gothic.exe", `\Gry\Gothic\Gothic.exe`},
		{appE + `\Gry\DSJ4\DSJ4.exe`, `Gry\DSJ4\DSJ4.exe`},
		{`e:\launchery\game_launcher\Gry\x.exe`, `Gry\x.exe`},
		{"D:/Gry/x.exe", `D:\Gry\x.exe`},
		{`\\nas\gry\x.exe`, `\\nas\gry\x.exe`},
		{"", ""},
		{`%APPDATA%\Gra\save`, `%APPDATA%\Gra\save`},
	}
	for _, c := range cases {
		if got := ToPortable(c.in, appE); got != c.want {
			t.Errorf("ToPortable(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestResolve(t *testing.T) {
	stored := ToPortable(`E:\Gry\Gothic\Gothic.exe`, appE)
	if got := Resolve(stored, appE); got != `E:\Gry\Gothic\Gothic.exe` {
		t.Fatal(got)
	}
	// the USB drive got the letter F: -> the same game on F:
	if got := Resolve(stored, appF); got != `F:\Gry\Gothic\Gothic.exe` {
		t.Fatal(got)
	}
	if got := Resolve(`Gry\DSJ4\DSJ4.exe`, appF); got != appF+`\Gry\DSJ4\DSJ4.exe` {
		t.Fatal(got)
	}
	if got := Resolve(`images\High on Life_rawg_cover.jpg`, appF); got != appF+`\images\High on Life_rawg_cover.jpg` {
		t.Fatal(got)
	}
	for _, p := range []string{`%APPDATA%\Gra\save`, `~\Saved Games`} {
		if got := Resolve(p, appF); got != p {
			t.Errorf("Resolve(%q) = %q", p, got)
		}
	}
	if got := Resolve("C:/Users/x/../y/Saves", appF); got != `C:\Users\y\Saves` {
		t.Fatal(got)
	}
}

func TestRemapDrive(t *testing.T) {
	if got := RemapDrive(`E:\Gry\x.exe`, "E:", "F:"); got != `F:\Gry\x.exe` {
		t.Fatal(got)
	}
	if got := RemapDrive(`D:\Gry\x.exe`, "E:", "F:"); got != `D:\Gry\x.exe` {
		t.Fatal(got)
	}
}

func sampleConfig(t *testing.T) *ojson.Object {
	t.Helper()
	src := `{
	  "games": {
	    "Gothic": {
	      "exe_path": "E:\\Gry\\Gothic\\System\\Gothic.exe",
	      "save_path": "C:\\Users\\gracz\\Saved Games\\Gothic",
	      "launch_profiles": [
	        {"name": "Default", "exe_path": null, "arguments": ""},
	        {"name": "Mod", "exe_path": "E:/Gry/Gothic/System/GothicMod.exe"}
	      ]
	    },
	    "Okami": {"game_type": "emulator", "emulator_name": "PCSX2", "rom_path": "E:\\ROM\\okami.iso"},
	    "DSJ4": {"exe_path": "E:\\Launchery\\Game_Launcher\\Gry\\DSJ4\\DSJ4.exe"}
	  },
	  "emulators": {"PCSX2": {"path": "E:\\Emu\\PCSX2\\pcsx2.exe"}},
	  "settings": {}
	}`
	o, err := ojson.DecodeObject([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	return o
}

func get(o *ojson.Object, keys ...string) string {
	for _, k := range keys[:len(keys)-1] {
		o = o.Obj(k)
	}
	return o.Str(keys[len(keys)-1])
}

// The USB drive is E: when saving and F: when loading: paths on the
// launcher drive follow it, other drives stay.
func TestRoundTripAfterDriveLetterChange(t *testing.T) {
	saved := MakePortable(sampleConfig(t), appE)
	checks := map[string]string{
		get(saved, "games", "Gothic", "exe_path"):  `\Gry\Gothic\System\Gothic.exe`,
		get(saved, "games", "Okami", "rom_path"):   `\ROM\okami.iso`,
		get(saved, "emulators", "PCSX2", "path"):   `\Emu\PCSX2\pcsx2.exe`,
		get(saved, "games", "DSJ4", "exe_path"):    `Gry\DSJ4\DSJ4.exe`,
		get(saved, "games", "Gothic", "save_path"): `C:\Users\gracz\Saved Games\Gothic`,
		get(saved, "settings", "launcher_drive"):   "E:",
	}
	for got, want := range checks {
		if got != want {
			t.Errorf("saved: got %q, want %q", got, want)
		}
	}
	prof := saved.Obj("games").Obj("Gothic").Arr("launch_profiles")[1].(*ojson.Object)
	if prof.Str("exe_path") != `\Gry\Gothic\System\GothicMod.exe` {
		t.Error(prof.Str("exe_path"))
	}

	// Write -> read the file bytes -> resolve on F:
	loaded, err := ojson.DecodeObject(ojson.MarshalPython(saved))
	if err != nil {
		t.Fatal(err)
	}
	ResolveConfig(loaded, appF)
	checks = map[string]string{
		get(loaded, "games", "Gothic", "exe_path"):  `F:\Gry\Gothic\System\Gothic.exe`,
		get(loaded, "games", "Okami", "rom_path"):   `F:\ROM\okami.iso`,
		get(loaded, "emulators", "PCSX2", "path"):   `F:\Emu\PCSX2\pcsx2.exe`,
		get(loaded, "games", "DSJ4", "exe_path"):    appF + `\Gry\DSJ4\DSJ4.exe`,
		get(loaded, "games", "Gothic", "save_path"): `C:\Users\gracz\Saved Games\Gothic`,
		get(loaded, "settings", "launcher_drive"):   "F:",
	}
	for got, want := range checks {
		if got != want {
			t.Errorf("loaded: got %q, want %q", got, want)
		}
	}
}

// Old config (absolute E:\... paths) + remembered drive E:, launcher now on F:.
func TestLegacyAbsolutePathsRemapped(t *testing.T) {
	cfg := sampleConfig(t)
	cfg.EnsureObj("settings").Set("launcher_drive", "E:")
	if n := ResolveConfig(cfg, appF); n != 5 {
		t.Fatalf("remapped %d, want 5", n)
	}
	if got := get(cfg, "games", "Gothic", "exe_path"); got != `F:\Gry\Gothic\System\Gothic.exe` {
		t.Fatal(got)
	}
	if got := get(cfg, "games", "Gothic", "save_path"); got != `C:\Users\gracz\Saved Games\Gothic` {
		t.Fatal(got)
	}
}

func TestNoRemapWithoutKnownPreviousDrive(t *testing.T) {
	cfg := sampleConfig(t)
	if n := ResolveConfig(cfg, appF); n != 0 {
		t.Fatal(n)
	}
	if got := get(cfg, "games", "Gothic", "exe_path"); got != `E:\Gry\Gothic\System\Gothic.exe` {
		t.Fatal(got)
	}
}

func TestMakePortableDoesNotMutate(t *testing.T) {
	cfg := sampleConfig(t)
	before := ojson.ToPlain(cfg.Clone())
	MakePortable(cfg, appE)
	if !reflect.DeepEqual(before, ojson.ToPlain(cfg)) {
		t.Fatal("MakePortable mutated its input")
	}
}

func TestFindExisting(t *testing.T) {
	present := map[string]bool{`F:\Gry\x.exe`: true}
	exists := func(p string) bool { return present[p] }
	if got := FindExisting(`E:\Gry\x.exe`, `F:\Launcher`, exists); got != `F:\Gry\x.exe` {
		t.Fatal(got)
	}
	if got := FindExisting(`E:\Gry\y.exe`, `F:\Launcher`, exists); got != "" {
		t.Fatal(got)
	}
}

func TestNormPathAndDir(t *testing.T) {
	cases := map[string]string{
		`C:/a/b/../c/./d.exe`: `C:\a\c\d.exe`,
		`\\nas\share\x\..\y`:  `\\nas\share\y`,
		`a\..\..\b`:           `..\b`,
		`C:\`:                 `C:\`,
	}
	for in, want := range cases {
		if got := NormPath(in); got != want {
			t.Errorf("NormPath(%q) = %q, want %q", in, got, want)
		}
	}
	if Dir(`D:\Gry\DSJ4\DSJ4.exe`) != `D:\Gry\DSJ4` || Dir(`D:\x.exe`) != `D:\` || Base(`D:\Gry\a.exe`) != "a.exe" {
		t.Fatal(Dir(`D:\Gry\DSJ4\DSJ4.exe`), Dir(`D:\x.exe`))
	}
}
