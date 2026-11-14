package store

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

func writeFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func openWithEnv(t *testing.T, dir string, env map[string]string) *Store {
	t.Helper()
	s := &Store{L: NewLayout(dir), backedUp: map[string]bool{}, getenv: func(k string) string { return env[k] }}
	if err := s.Load(); err != nil {
		t.Fatal(err)
	}
	return s
}

func TestDefaultsOnEmptyFolder(t *testing.T) {
	dir := t.TempDir()
	s := openWithEnv(t, dir, nil)
	s.ReadConfig(func(c *ojson.Object) {
		if c.Obj("games") == nil || c.Str("version") != ProgramVersion {
			t.Fatal("defaults missing")
		}
		if c.Obj("settings").Arr("rss_feeds") == nil {
			t.Fatal("rss default missing")
		}
	})
	s.ReadLocal(func(l *ojson.Object) {
		if l.Int("remote_control_port", 0) != DefaultRemoteControlPort || len(l.Arr("chat_servers")) != 1 {
			t.Fatal("local defaults missing")
		}
	})
}

func TestProfilesRepairedAndUnknownKeysKept(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "data", "config", "config.json"), `{
    "version": "1.4.0",
    "games": {
        "A": {"exe_path": "D:\\A\\a.exe", "launch_profiles": [{"name": "Mod", "exe_path": null, "arguments": "-x"}, {"name": "default", "exe_path": null, "arguments": ""}], "future_field": {"x": [1, 2.50]}},
        "B": {"exe_path": "D:\\B\\b.exe"}
    },
    "mods_data": {"A": {"profiles": {}}}
}`)
	s := openWithEnv(t, dir, nil)
	s.ReadConfig(func(c *ojson.Object) {
		a := c.Obj("games").Obj("A")
		profs := a.Arr("launch_profiles")
		if profs[0].(*ojson.Object).Str("name") != "default" || len(profs) != 2 {
			t.Fatalf("default profile not first: %v", ojson.ToPlain(profs))
		}
		b := c.Obj("games").Obj("B")
		if len(b.Arr("launch_profiles")) != 1 {
			t.Fatal("missing default profile")
		}
		if c.Str("version") != ProgramVersion {
			t.Fatal("version not bumped")
		}
	})
	if err := s.UpdateConfig(func(*ojson.Object) error { return nil }); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(s.L.ConfigFile)
	if !bytes.Contains(raw, []byte(`"future_field": {`)) || !bytes.Contains(raw, []byte("2.50")) || !bytes.Contains(raw, []byte(`"mods_data"`)) {
		t.Fatalf("unknown data lost:\n%s", raw)
	}
	if _, err := os.Stat(s.L.ConfigFile + ".bak"); err != nil {
		t.Fatal("no .bak of the previous file")
	}
}

func TestSecretsFromEnvAreNotWritten(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "data", "config", "local_settings.json"), "{\r\n    \"rawg_api_key\": \"FROM_FILE\"\r\n}")
	s := openWithEnv(t, dir, map[string]string{"GL_RAWG_API_KEY": "FROM_ENV", "GL_LASTFM_API_KEY": "LFM_ENV"})
	if s.Secret("rawg_api_key") != "FROM_ENV" || !s.SecretFromEnv("rawg_api_key") {
		t.Fatal("env override not applied")
	}
	if err := s.UpdateLocal(func(l *ojson.Object) error { l.Set("tiles_per_row", 6); return nil }); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(s.L.LocalFile)
	if bytes.Contains(raw, []byte("FROM_ENV")) || bytes.Contains(raw, []byte("LFM_ENV")) || bytes.Contains(raw, []byte("FROM_FILE")) {
		t.Fatalf("secret in plaintext in the file")
	}
	o, _ := ojson.DecodeObject(raw)
	if v, err := RevealValue(o.Str("rawg_api_key")); err != nil || v != "FROM_FILE" {
		t.Fatal("file value lost or not decryptable")
	}
	if !bytes.Contains(raw, []byte("\r\n")) {
		t.Fatal("CRLF style not preserved")
	}
}

func TestBrokenConfigIsKeptAside(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "data", "config", "config.json")
	writeFile(t, cfgPath, `{"games": {`)
	s := openWithEnv(t, dir, nil)
	if len(s.Warnings) == 0 {
		t.Fatal("no warning for a broken file")
	}
	matches, _ := filepath.Glob(cfgPath + ".broken-*")
	if len(matches) != 1 {
		t.Fatal("broken file not preserved")
	}
}

func TestLegacyChatSettingsMigrated(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "data", "config", "local_settings.json"), `{"chat_server_url": "http://example.invalid:5000", "chat_email": "a@b.c", "chat_password": "x", "chat_remember_me": true, "remote_control_port": 5000}`)
	s := openWithEnv(t, dir, nil)
	s.ReadLocal(func(l *ojson.Object) {
		servers := l.Arr("chat_servers")
		if len(servers) != 1 || servers[0].(*ojson.Object).Str("url") != "http://example.invalid:5000" {
			t.Fatal("not migrated")
		}
		if l.Has("chat_server_url") || l.Has("chat_password") {
			t.Fatal("old keys kept")
		}
		if l.Int("remote_control_port", 0) != DefaultRemoteControlPort {
			t.Fatal("remote port collides with chat")
		}
	})
}

func TestLegacyRootFilesMoved(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, filepath.Join(dir, "config.json"), `{"games": {"X": {"exe_path": "D:\\x.exe"}}}`)
	writeFile(t, filepath.Join(dir, "games_saves", "X", "saves", "s1", "f.sav"), "1")
	s := openWithEnv(t, dir, nil)
	s.ReadConfig(func(c *ojson.Object) {
		if c.Obj("games").Obj("X") == nil {
			t.Fatal("legacy config not loaded")
		}
	})
	if _, err := os.Stat(filepath.Join(dir, "data", "games_saves", "X", "saves", "s1", "f.sav")); err != nil {
		t.Fatal("legacy saves not moved")
	}
}

func TestRedact(t *testing.T) {
	o, _ := ojson.DecodeObject([]byte(`{"rawg_api_key":"k","chat_servers":[{"url":"u","credentials":{"password":"p"}}],"tiles_per_row":3,"remote_control_token":""}`))
	out := string(ojson.MarshalCompact(Redact(o)))
	if strings.Contains(out, `"k"`) || strings.Contains(out, `"p"`) || !strings.Contains(out, `"tiles_per_row":3`) {
		t.Fatal(out)
	}
}

// Migration test on a COPY of the user's real data (GL_TEST_USERDATA points
// at a copied launcher folder; the original is never touched). The copy is
// copied once more into a temp folder because the store writes.
func TestUserDataCopyMigration(t *testing.T) {
	src := os.Getenv("GL_TEST_USERDATA")
	if src == "" {
		t.Skip("GL_TEST_USERDATA not set")
	}
	dir := t.TempDir()
	for _, name := range []string{"config.json", "local_settings.json", "achievements_def.json"} {
		copyFile(t, filepath.Join(src, "data", "config", name), filepath.Join(dir, "data", "config", name))
	}
	origRaw, _ := os.ReadFile(filepath.Join(src, "data", "config", "config.json"))
	orig, err := ojson.DecodeObject(origRaw)
	if err != nil {
		t.Fatal(err)
	}

	s := openWithEnv(t, dir, nil)
	var before any
	var games int
	s.ReadConfig(func(c *ojson.Object) {
		before = ojson.ToPlain(c.Clone())
		games = c.Obj("games").Len()
		if games != orig.Obj("games").Len() {
			t.Fatalf("games: %d vs %d", games, orig.Obj("games").Len())
		}
		// stats survive unchanged
		for _, name := range orig.Obj("games").Keys() {
			og, ng := orig.Obj("games").Obj(name), c.Obj("games").Obj(name)
			if og.Get("play_time") != ng.Get("play_time") || og.Get("last_played") != ng.Get("last_played") || len(og.Arr("play_sessions")) != len(ng.Arr("play_sessions")) {
				t.Errorf("%s: stats changed", name)
			}
		}
		for _, k := range orig.Keys() {
			if !c.Has(k) {
				t.Errorf("top-level key %q lost", k)
			}
		}
	})
	if err := s.UpdateConfig(func(*ojson.Object) error { return nil }); err != nil {
		t.Fatal(err)
	}
	if err := s.UpdateLocal(func(*ojson.Object) error { return nil }); err != nil {
		t.Fatal(err)
	}
	// Reload what Go wrote: same data after path resolution.
	s2 := openWithEnv(t, dir, nil)
	s2.ReadConfig(func(c *ojson.Object) {
		after := ojson.ToPlain(c.Clone())
		if !reflect.DeepEqual(before, after) {
			t.Fatal("config differs after a Go save + reload")
		}
	})
	// Secrets in local_settings survived, now DPAPI-protected (compared
	// without printing them).
	for _, k := range []string{"rawg_api_key", "lastfm_api_key", "github_token"} {
		ov := origLocal(t, src).Str(k)
		nv := origLocal(t, dir).Str(k)
		plain, err := RevealValue(nv)
		if err != nil || plain != ov || (ov != "" && nv == ov) {
			t.Errorf("secret %s not preserved/protected", k)
		}
	}
	t.Logf("migrated %d games, remapped %d paths", games, s.Remapped)
}

func origLocal(t *testing.T, dir string) *ojson.Object {
	raw, err := os.ReadFile(filepath.Join(dir, "data", "config", "local_settings.json"))
	if err != nil {
		t.Fatal(err)
	}
	o, err := ojson.DecodeObject(raw)
	if err != nil {
		t.Fatal(err)
	}
	return o
}

func copyFile(t *testing.T, from, to string) {
	t.Helper()
	in, err := os.Open(from)
	if err != nil {
		t.Skip("missing in the copy: " + from)
	}
	defer in.Close()
	_ = os.MkdirAll(filepath.Dir(to), 0o755)
	out, err := os.Create(to)
	if err != nil {
		t.Fatal(err)
	}
	defer out.Close()
	if _, err := io.Copy(out, in); err != nil {
		t.Fatal(err)
	}
}

// The launcher folder moved to another drive letter (config written on Q:,
// loaded from a temp folder on this machine's drive): paths that were on the
// old launcher drive follow it, others stay, and a save writes them back
// without the drive letter.
func TestDriveLetterChangeThroughStore(t *testing.T) {
	dir := t.TempDir()
	drive := filepath.VolumeName(dir) // e.g. "C:"
	writeFile(t, filepath.Join(dir, "data", "config", "config.json"), `{
    "games": {
        "A": {"exe_path": "Q:\\Gry\\A\\a.exe", "save_path": "D:\\Saves\\A"},
        "B": {"exe_path": "\\Gry\\B\\b.exe"}
    },
    "emulators": {"PCSX2": {"path": "Q:\\Emu\\pcsx2.exe"}},
    "settings": {"launcher_drive": "Q:"}
}`)
	s := openWithEnv(t, dir, nil)
	if s.Remapped != 2 {
		t.Fatalf("remapped %d", s.Remapped)
	}
	s.ReadConfig(func(c *ojson.Object) {
		g := c.Obj("games")
		if g.Obj("A").Str("exe_path") != drive+`\Gry\A\a.exe` || g.Obj("A").Str("save_path") != `D:\Saves\A` || g.Obj("B").Str("exe_path") != drive+`\Gry\B\b.exe` {
			t.Fatalf("%s", ojson.MarshalCompact(g))
		}
		if c.Obj("settings").Str("launcher_drive") != strings.ToUpper(drive) {
			t.Fatal("launcher_drive not updated")
		}
	})
	if err := s.UpdateConfig(func(*ojson.Object) error { return nil }); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(s.L.ConfigFile)
	if !bytes.Contains(raw, []byte(`"exe_path": "\\Gry\\A\\a.exe"`)) || !bytes.Contains(raw, []byte(`"path": "\\Emu\\pcsx2.exe"`)) {
		t.Fatalf("not stored portably:\n%s", raw)
	}
}
