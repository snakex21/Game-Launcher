package modmgr

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// TestDemoData fills a launcher folder with fake games and generated mods
// for screenshots: GL_MODMGR_DEMO=<launcher folder> go test -run TestDemoData
// The fake games and user folders are created inside that folder.
func TestDemoData(t *testing.T) {
	app := os.Getenv("GL_MODMGR_DEMO")
	if app == "" {
		t.Skip("GL_MODMGR_DEMO not set")
	}
	base := filepath.Join(app, "demo")
	folders := testkit.Folders(t, filepath.Join(base, "Użytkownik"))
	svc, err := New(app, Options{Folders: folders})
	if err != nil {
		t.Fatal(err)
	}
	// only games whose files all live in the game folder: the launcher run
	// for screenshots uses the real user folders, which must stay untouched
	cp := filepath.Join(base, "Gry", "Cyberpunk 2077")
	testkit.Game(t, svc.Defs().Get("cyberpunk2077"), cp)
	in, err := svc.AddInstall(AddInstallIn{DefID: "cyberpunk2077", Path: cp, Store: "gog"})
	if err != nil {
		t.Fatal(err)
	}
	zip := func(name string, files map[string]string) string {
		return testkit.Zip(t, filepath.Join(base, "Pobrane", name), files)
	}
	imp := func(id, path string, enable bool) {
		if _, _, err := svc.Import(ImportIn{Install: id, Path: path, Enable: enable, AckExecutable: true}); err != nil {
			t.Fatal(err)
		}
	}
	imp(in.ID, zip("Better Vehicle Handling-1.4.zip", map[string]string{"archive/pc/mod/BetterHandling.archive": "bvh", "r6/tweaks/handling.yaml": "a: 1"}), true)
	imp(in.ID, zip("Nova LUT-2.1.zip", map[string]string{"archive/pc/mod/NovaLUT.archive": "lut", "engine/config/platform/pc/lut.ini": "lut"}), true)
	imp(in.ID, zip("Cyber Engine Tweaks-1.32.zip", map[string]string{"bin/x64/version.dll": "dll", "bin/x64/plugins/cyber_engine_tweaks.asi": "asi"}), true)
	imp(in.ID, zip("Immersive Handling-2.0.zip", map[string]string{"archive/pc/mod/ImmersiveHandling.archive": "ih", "r6/tweaks/handling.yaml": "a: 2"}), true)
	imp(in.ID, zip("Appearance Menu Mod-2.6.zip", map[string]string{"bin/x64/plugins/cyber_engine_tweaks/mods/AppearanceMenuMod/init.lua": "print()"}), false)
	if _, err := svc.CreateProfile(in.ID, "Nowa gra – minimum", ""); err != nil {
		t.Fatal(err)
	}
	gen := filepath.Join(base, "Gry", "Gothic II")
	testkit.Write(t, gen, "System/Gothic2.exe", "exe")
	testkit.Write(t, gen, "Data/Textures.vdf", "vanilla")
	g, err := svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: gen, Name: "Gothic II: Noc Kruka"})
	if err != nil {
		t.Fatal(err)
	}
	imp(g.ID, zip("Gothic II Ostatnia Lekcja.zip", map[string]string{"Data/Textures_Ostatnia.vdf": "x", "Data/Speech.vdf": "y"}), true)
	t.Logf("demo data in %s", app)
}
