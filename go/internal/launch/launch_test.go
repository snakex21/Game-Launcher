package launch

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"syscall"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

const app = `F:\Launcher`

func existsIn(present ...string) func(string) bool {
	set := map[string]bool{}
	for _, p := range present {
		set[strings.ToLower(p)] = true
	}
	return func(p string) bool { return set[strings.ToLower(p)] }
}

func obj(t *testing.T, s string) *ojson.Object {
	t.Helper()
	if s == "" {
		return nil
	}
	o, err := ojson.DecodeObject([]byte(s))
	if err != nil {
		t.Fatal(err)
	}
	return o
}

func TestPCGameUsesExeFolderAsCwd(t *testing.T) {
	spec, err := Build("DSJ4", obj(t, `{"exe_path":"D:\\Gry\\DSJ4\\DSJ4.exe"}`), nil, nil, app, existsIn(`D:\Gry\DSJ4\DSJ4.exe`))
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(spec.Command, []string{`D:\Gry\DSJ4\DSJ4.exe`}) || spec.Cwd != `D:\Gry\DSJ4` {
		t.Fatalf("%+v", spec)
	}
}

func TestProfileExeAndArguments(t *testing.T) {
	game := obj(t, `{"exe_path":"D:\\Gry\\GTA\\gta_sa.exe"}`)
	prof := obj(t, `{"name":"Mody","exe_path":"D:\\Gry\\GTA\\gta_sa_mod.exe","arguments":"-windowed -cfg \"D:\\Gry\\GTA\\my cfg.ini\""}`)
	spec, err := Build("GTA SA", game, nil, prof, app, existsIn(`D:\Gry\GTA\gta_sa_mod.exe`))
	if err != nil {
		t.Fatal(err)
	}
	want := []string{`D:\Gry\GTA\gta_sa_mod.exe`, "-windowed", "-cfg", `D:\Gry\GTA\my cfg.ini`}
	if !reflect.DeepEqual(spec.Command, want) || spec.Cwd != `D:\Gry\GTA` || !strings.Contains(spec.ProfileName, "Mody") {
		t.Fatalf("%+v", spec)
	}
}

func TestProfileWithoutExeFallsBack(t *testing.T) {
	spec, err := Build("X", obj(t, `{"exe_path":"D:\\Gry\\x\\x.exe"}`), nil, obj(t, `{"name":"Default","exe_path":null,"arguments":""}`), app, existsIn(`D:\Gry\x\x.exe`))
	if err != nil || spec.Command[0] != `D:\Gry\x\x.exe` {
		t.Fatal(spec, err)
	}
}

func TestEmulatorCommandAndCwd(t *testing.T) {
	game := obj(t, `{"game_type":"emulator","emulator_name":"PCSX2","rom_path":"H:\\ROM\\okami.iso","emulator_args":"-fullscreen -nogui"}`)
	emus := obj(t, `{"PCSX2":{"path":"H:\\Emu\\PCSX2\\pcsx2-qt.exe"}}`)
	spec, err := Build("Okami", game, emus, nil, app, existsIn(`H:\ROM\okami.iso`, `H:\Emu\PCSX2\pcsx2-qt.exe`))
	if err != nil {
		t.Fatal(err)
	}
	want := []string{`H:\Emu\PCSX2\pcsx2-qt.exe`, "-fullscreen", "-nogui", `H:\ROM\okami.iso`}
	if !reflect.DeepEqual(spec.Command, want) || spec.Cwd != `H:\Emu\PCSX2` {
		t.Fatalf("%+v", spec)
	}
}

func TestMissingExeOnOldDriveFoundOnLauncherDrive(t *testing.T) {
	spec, err := Build("Gothic", obj(t, `{"exe_path":"E:\\Gry\\Gothic\\Gothic.exe"}`), nil, nil, app, existsIn(`F:\Gry\Gothic\Gothic.exe`))
	if err != nil || spec.Command[0] != `F:\Gry\Gothic\Gothic.exe` || spec.Cwd != `F:\Gry\Gothic` {
		t.Fatal(spec, err)
	}
}

func TestErrorsHaveRealPolishMessages(t *testing.T) {
	cases := []struct{ game, emus, profile, fragment string }{
		{`{}`, `{}`, ``, "nie ma ustawionej ścieżki"},
		{`{"exe_path":"D:\\brak.exe"}`, `{}`, ``, `D:\brak.exe`},
		{`{}`, `{}`, `{"name":"P1","exe_path":null}`, "Profil „P1”"},
		{`{"exe_path":"D:\\x.exe"}`, `{}`, `{"name":"P","arguments":"-a \"niedomkniety"}`, "cudzysłowy"},
		{`{"game_type":"emulator","emulator_name":"PCSX2"}`, `{}`, ``, "ROM/ISO"},
		{`{"game_type":"emulator","emulator_name":"PCSX2","rom_path":"r.iso"}`, `{}`, ``, "nie jest skonfigurowany"},
		{`{"game_type":"emulator","emulator_name":"E","rom_path":"r.iso"}`, `{"E":{"path":"D:\\e.exe"}}`, ``, "emulatora „E”"},
		{`{"game_type":"dos"}`, `{}`, ``, "Nieznany typ gry"},
	}
	for _, c := range cases {
		_, err := Build("Gra", obj(t, c.game), obj(t, c.emus), obj(t, c.profile), app, existsIn(`D:\x.exe`))
		var le *Error
		if !errors.As(err, &le) || !strings.Contains(le.Message, c.fragment) || le.Title == "" {
			t.Errorf("%s: got %v, want fragment %q", c.game, err, c.fragment)
		}
	}
}

func TestSplitArgs(t *testing.T) {
	cases := map[string][]string{
		``:                          nil,
		`-a -b`:                     {"-a", "-b"},
		`  -x   "C:\a b\c.ini"  `:   {"-x", `C:\a b\c.ini`},
		`"a b"c`:                    {`"a b"c`},
		`'single quoted' x`:         {"'single quoted'", "x"},
		"tab\tsep":                  {"tab", "sep"},
		`-cfg="C:\Program Files\x"`: {`-cfg="C:\Program Files\x"`},
	}
	for in, want := range cases {
		got, err := SplitArgs(in)
		if err != nil || !reflect.DeepEqual(got, want) {
			t.Errorf("SplitArgs(%q) = %#v, %v; want %#v", in, got, err, want)
		}
	}
}

// Start passes the working directory to the process (fake starter) and
// maps WinError 740 to a readable message.
func TestStartUsesCwdAndElevationMessage(t *testing.T) {
	spec := &Spec{Command: []string{`D:\Gry\a.exe`, "-x"}, Cwd: `D:\Gry`}
	var seen *exec.Cmd
	if _, err := Start("A", spec, func(c *exec.Cmd) error { seen = c; return nil }); err != nil {
		t.Fatal(err)
	}
	if seen.Dir != `D:\Gry` || !reflect.DeepEqual(seen.Args, []string{`D:\Gry\a.exe`, "-x"}) {
		t.Fatalf("%+v", seen)
	}
	_, err := Start("A", spec, func(*exec.Cmd) error { return &os.PathError{Op: "fork/exec", Path: "a", Err: syscall.Errno(740)} })
	var le *Error
	if !errors.As(err, &le) || le.Title != "Błąd uprawnień" {
		t.Fatal(err)
	}
}

// A real process: the child sees the game folder as its working directory.
func TestStartRealProcessCwd(t *testing.T) {
	if os.Getenv("GL_HELPER_PRINT_CWD") == "1" {
		wd, _ := os.Getwd()
		os.WriteFile(os.Getenv("GL_HELPER_OUT"), []byte(wd), 0o644)
		os.Exit(0)
	}
	exe, err := os.Executable()
	if err != nil {
		t.Skip(err)
	}
	gameDir := t.TempDir()
	out := filepath.Join(t.TempDir(), "cwd.txt")
	t.Setenv("GL_HELPER_PRINT_CWD", "1")
	t.Setenv("GL_HELPER_OUT", out)
	cmd, err := Start("helper", &Spec{Command: []string{exe, "-test.run=^TestStartRealProcessCwd$"}, Cwd: gameDir}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Wait(); err != nil {
		t.Fatal(err)
	}
	got, _ := os.ReadFile(out)
	if !strings.EqualFold(filepath.Clean(string(got)), filepath.Clean(gameDir)) {
		t.Fatalf("cwd %q, want %q", got, gameDir)
	}
}
