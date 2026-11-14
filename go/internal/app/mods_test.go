package app

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/modmgr"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
	"github.com/snakex21/game-launcher/go/internal/ojson"
)

func modsEnv(t *testing.T) (*env, *modmgr.Service) {
	e := newEnv(t)
	e.a.SetModOptions(modmgr.Options{Folders: testkit.Folders(t, filepath.Join(e.dir, "Użytkownik"))})
	s, err := e.a.modsService()
	if err != nil {
		t.Fatal(err)
	}
	return e, s
}

func TestLaunchDeploysLinkedModsFirst(t *testing.T) {
	e, s := modsEnv(t)
	in, err := s.AddInstall(modmgr.AddInstallIn{DefID: gamedef.GenericID, Path: filepath.Dir(e.gameExe), Game: "Gothic"})
	if err != nil {
		t.Fatal(err)
	}
	off := false
	s.SetOptions(in.ID, modmgr.SetInstallOptions{AutoDeploy: &off})
	z := testkit.Zip(t, filepath.Join(e.dir, "mody", "Lepsze tekstury.zip"), map[string]string{"Data/Textures/a.tex": "tekstura"})
	row, _, err := s.Import(modmgr.ImportIn{Install: in.ID, Path: z, Enable: true})
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(filepath.Dir(e.gameExe), "Data", "Textures", "a.tex")
	if _, err := os.Stat(target); err == nil {
		t.Fatal("deployed although automatic deployment is off")
	}
	on := true
	s.SetOptions(in.ID, modmgr.SetInstallOptions{AutoDeploy: &on})
	if _, err := e.a.Launch("Gothic", ""); err != nil {
		t.Fatal(err)
	}
	if b, _ := os.ReadFile(target); string(b) != "tekstura" {
		t.Fatal("mods not deployed before launch")
	}
	// the game is running now: changes are refused, files stay
	if _, err := s.SetEnabled(in.ID, row.ID, false, false); err == nil || !strings.Contains(err.Error(), "uruchomiona") {
		t.Fatal("change while the game runs:", err)
	}
	if _, err := os.Stat(target); err != nil {
		t.Fatal("file removed while running")
	}
}

func TestModsChannelsRegistered(t *testing.T) {
	e, _ := modsEnv(t)
	d := bridge.New(context.Background(), "tok")
	e.a.Register(d)
	for _, ch := range []string{"mods.defs", "mods.installs", "mods.view", "mods.import", "mods.preview", "mods.deploy", "mods.purge", "mods.uninstall",
		"mods.setEnabled", "mods.move", "mods.conflicts", "mods.files", "mods.setOverride", "mods.profileCreate", "mods.profileActivate", "mods.verify", "mods.launch", "mods.legacy"} {
		if !d.Has(ch) {
			t.Errorf("missing channel %s", ch)
		}
	}
	var mu sync.Mutex
	var got []string
	done := make(chan struct{}, 1)
	d.Invoke("tok", 1, "mods.view", `{"id":"nope"}`, func(id int64, ok bool, p any) {
		mu.Lock()
		b, _ := json.Marshal(p)
		got = append(got, string(b))
		mu.Unlock()
		done <- struct{}{}
	})
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("no answer")
	}
	if !strings.Contains(got[0], "Nie ma takiej gry") {
		t.Fatal(got)
	}
}

func TestLegacyModsDataIsReadOnly(t *testing.T) {
	e, _ := modsEnv(t)
	e.a.S.UpdateConfig(func(cfg *ojson.Object) error {
		md := cfg.EnsureObj("mods_data").EnsureObj("Gothic").EnsureObj("profiles").EnsureObj("default")
		md.EnsureObj("mods").EnsureObj("whirlwind").Set("active", false)
		md.Set("load_order", []any{"whirlwind"})
		return nil
	})
	before, _ := os.ReadFile(filepath.Join(e.dir, "data", "config", "config.json"))
	got := e.a.legacyMods("Gothic")
	b, _ := json.Marshal(got)
	if !strings.Contains(string(b), "whirlwind") {
		t.Fatal(string(b))
	}
	after, _ := os.ReadFile(filepath.Join(e.dir, "data", "config", "config.json"))
	if string(before) != string(after) {
		t.Fatal("legacy view changed config")
	}
}
