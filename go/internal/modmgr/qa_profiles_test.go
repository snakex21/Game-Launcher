package modmgr

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// P1 -> P2 -> P1 equals P1; P1 -> P2 equals P2 deployed on vanilla; purge
// is vanilla (game + user folders, incl. plugins.txt the user had).
func TestQAProfileSwitchRoundTrip(t *testing.T) {
	type world struct {
		w        *qaWorld
		game     string
		in       *Install
		p1, p2   string
		vanilla  map[string]string
		a, b, c  string
		pluginsF string
	}
	mk := func() *world {
		w := qaNew(t)
		game, in := w.game("skyrimse", "Skyrim Special Edition ąę")
		pf := testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Gracza.esp\r\n")
		testkit.Write(t, game, "Data/Gracza.esp", "gracz")
		testkit.Write(t, game, "Data/textures/sky.dds", "vanilla sky")
		qaWriteRO(t, game, "Data/ro.ini", "ro")
		x := &world{w: w, game: game, in: in, pluginsF: pf}
		x.vanilla = w.snap(game)
		x.a = w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/A.esp": "a", "Data/textures/sky.dds": "A sky", "Data/ro.ini": "A ro"}), true)
		x.b = w.imp(in.ID, w.zip("B.zip", map[string]string{"Data/B.esp": "b", "Data/textures/sky.dds": "B sky"}), true)
		x.c = w.imp(in.ID, w.zip("C ż.zip", map[string]string{"Data/C.esm": "c", "Data/meshes/m.nif": "m"}), false)
		x.p1 = in.ActiveProfile
		p2, err := w.svc.CreateProfile(in.ID, "Profil drugi ść", x.p1)
		w.must(err)
		x.p2 = p2.ID
		return x
	}
	toP2 := func(x *world) {
		_, err := x.w.svc.ActivateProfile(x.in.ID, x.p2)
		x.w.must(err)
		_, err = x.w.svc.SetEnabled(x.in.ID, x.a, false, false)
		x.w.must(err)
		_, err = x.w.svc.SetEnabled(x.in.ID, x.c, true, false)
		x.w.must(err)
		_, err = x.w.svc.Move(x.in.ID, x.b, 0)
		x.w.must(err)
	}
	x := mk()
	p1State := x.w.snap(x.game)
	if qaRead(filepath.Join(x.game, "Data", "textures", "sky.dds")) != "B sky" {
		t.Fatal("P1 wrong")
	}
	toP2(x)
	p2State := x.w.snap(x.game)
	_, err := x.w.svc.ActivateProfile(x.in.ID, x.p1)
	x.w.must(err)
	if diff := qaDiffNoMtimeOfMod(p1State, x.w.snap(x.game)); diff != "" {
		t.Errorf("P1 -> P2 -> P1 != P1:\n%s", diff)
	}
	// P2 deployed directly on vanilla in a twin world
	y := mk()
	toP2(y)
	if diff := qaDiffNoMtime(p2State, y.w.snap(y.game)); diff != "" {
		t.Errorf("P1 -> P2 != P2 on vanilla:\n%s", diff)
	}
	_, err = x.w.svc.Purge(x.in.ID)
	x.w.must(err)
	if diff := testkit.Diff(x.vanilla, x.w.snap(x.game)); diff != "" {
		t.Errorf("purge not vanilla:\n%s", diff)
	}
	if got := qaRead(x.pluginsF); got != "*Gracza.esp\r\n" {
		t.Errorf("user's plugins.txt not restored: %q", got)
	}
}

// Two installs of the same game (Steam + GOG: different user folders) share
// the store; uninstalling a mod from one removes its files from both games
// and from the store. (Same-store installs: TestQABugTwoInstallsSameUserFolderFile.)
func TestQATwoInstallsShareStore(t *testing.T) {
	w := qaNew(t)
	g1, i1 := w.game("skyrimse", "Steam Skyrim ą")
	g2 := filepath.Join(w.base, "Biblioteka gier", "GOG Skyrim ę")
	testkit.Game(t, w.svc.Defs().Get("skyrimse"), g2)
	i2, err := w.svc.AddInstall(AddInstallIn{DefID: "skyrimse", Path: g2, Store: "gog"})
	w.must(err)
	v1, v2 := w.snap(g1), w.snap(g2)
	id := w.imp(i1.ID, w.zip("Wspólny.zip", map[string]string{"Data/W.esp": "w", "Data/textures/t.dds": "t"}), true)
	v, err := w.svc.GetView(i2.ID)
	w.must(err)
	if len(v.Mods) != 1 || v.Mods[0].InProfile {
		t.Fatalf("second install should see the mod (not in its profile): %+v", v.Mods)
	}
	_, err = w.svc.SetEnabled(i2.ID, id, true, false)
	w.must(err)
	if qaRead(filepath.Join(g2, "Data", "W.esp")) != "w" || qaRead(filepath.Join(g1, "Data", "W.esp")) != "w" {
		t.Fatal("not deployed in both")
	}
	if w.storeDir(i1.ID) != w.storeDir(i2.ID) {
		t.Fatal("store not shared")
	}
	w.must(w.svc.UninstallMod(i1.ID, id))
	if diff := testkit.Diff(v2, w.snap(g2)); diff != "" {
		t.Errorf("second game not vanilla after uninstall from the first:\n%s", diff)
	}
	if diff := testkit.Diff(v1, w.snap(g1)); diff != "" {
		t.Errorf("first game not vanilla:\n%s", diff)
	}
	if left := qaDirNames(t, w.storeDir(i1.ID)); len(left) != 0 {
		t.Errorf("store not empty: %v", left)
	}
	// both installs can be removed now
	w.must(w.svc.RemoveInstall(i1.ID))
	w.must(w.svc.RemoveInstall(i2.ID))
}

// Removing one of two installs sharing a store must not delete mods the
// other install still uses.
func TestQARemoveInstallKeepsSharedMods(t *testing.T) {
	w := qaNew(t)
	_, i1 := w.game("skyrimse", "Skyrim 1")
	g2, i2 := w.game("skyrimse", "Skyrim 2")
	id := w.imp(i1.ID, w.zip("m.zip", map[string]string{"Data/M.esp": "m"}), false)
	_, err := w.svc.SetEnabled(i2.ID, id, true, false)
	w.must(err)
	w.must(w.svc.RemoveInstall(i1.ID))
	v, err := w.svc.GetView(i2.ID)
	w.must(err)
	if len(v.Mods) != 1 || !v.InSync || qaRead(filepath.Join(g2, "Data", "M.esp")) != "m" {
		t.Errorf("the other install lost its mod: %+v", v.Mods)
	}
}

// RemoveInstall while files are deployed is refused.
func TestQARemoveInstallWhileDeployedRefused(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra usuń")
	w.imp(in.ID, w.zip("m.zip", map[string]string{"x.txt": "x"}), true)
	var ue *UserError
	if err := w.svc.RemoveInstall(in.ID); !errors.As(err, &ue) {
		t.Fatalf("remove while deployed: %v", err)
	}
	if qaRead(filepath.Join(game, "x.txt")) != "x" {
		t.Error("files touched")
	}
}

// Store files are read-only; a write through the hardlink in the game
// folder (an in-place save by a tool) is detected by Verify.
func TestQAStoreReadOnlyAndHardlinkWriteDetected(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra hardlink")
	w.imp(in.ID, w.zip("m.zip", map[string]string{"tex/mod.dds": "a=1"}), true)
	store := w.storeDir(in.ID)
	filepath.WalkDir(store, func(p string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() && d.Name() != "mod.json" && !qaIsRO(t, p) {
			t.Errorf("store file not read-only: %s", p)
		}
		return nil
	})
	gp := filepath.Join(game, "tex", "mod.dds")
	// a tool clears the attribute and writes in place
	w.must(os.Chmod(gp, 0o644))
	w.must(os.WriteFile(gp, []byte("a=2 zapis w miejscu"), 0o644))
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	if len(vr.Drift) == 0 && len(vr.StoreIssues) == 0 {
		t.Errorf("write through a hardlink not detected: %+v", vr)
	}
	t.Logf("verify: %+v", vr)
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	t.Logf("after purge: %q", qaRead(gp))
}

// Empty archives and archives with only ignored files are refused cleanly.
func TestQAEmptyArchives(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra pusta")
	vanilla := w.snap(game)
	cases := map[string]string{
		"pusty.zip":         qaRawZip(t, filepath.Join(w.base, "pusty.zip"), nil),
		"tylko readme.zip":  testkit.Zip(t, filepath.Join(w.base, "tylko readme.zip"), map[string]string{"readme.txt": "r", "screenshots/a.png": "p"}),
		"tylko foldery.zip": qaRawZip(t, filepath.Join(w.base, "tylko foldery.zip"), []qaZipEntry{{name: "a/"}, {name: "a/b/"}}),
	}
	empty := filepath.Join(w.base, "pusty folder")
	w.must(os.MkdirAll(empty, 0o755))
	cases["folder"] = empty
	for name, p := range cases {
		row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: p, Enable: true})
		if err == nil {
			t.Errorf("%s: accepted (%+v)", name, row)
		} else {
			var ue *UserError
			if !errors.As(err, &ue) {
				t.Errorf("%s: not a user error: %v", name, err)
			}
		}
	}
	if left := qaDirNames(t, w.storeDir(in.ID)); len(left) != 0 {
		t.Errorf("store not empty: %v", left)
	}
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Error(diff)
	}
}

// Very long paths (beyond MAX_PATH) inside the archive: either installed and
// purged cleanly, or refused without leftovers.
func TestQAVeryLongPaths(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra długie ścieżki")
	vanilla := w.snap(game)
	seg := strings.Repeat("ż", 40)
	deep := strings.Join([]string{seg, seg, seg, seg, seg, seg, seg}, "/") + "/plik.txt"
	z := w.zip("długi.zip", map[string]string{deep: "głęboko", "krótki.txt": "k"})
	row, dr, err := w.svc.Import(ImportIn{Install: in.ID, Path: z, Enable: true})
	t.Logf("long path import: row=%+v dr=%+v err=%v (abs len %d)", row, dr, err, len(filepath.Join(game, deep)))
	if err == nil {
		if qaRead(filepath.Join(game, filepath.FromSlash(deep))) != "głęboko" {
			t.Error("long file not deployed")
		}
		_, err = w.svc.Purge(in.ID)
		w.must(err)
		w.must(w.svc.UninstallMod(in.ID, row.ID))
	}
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla:\n%s", diff)
	}
	if left := qaDirNames(t, w.storeDir(in.ID)); len(left) != 0 {
		t.Errorf("store leftovers: %v", left)
	}
}

// A running game blocks purge and uninstall without half-done changes.
func TestQARunningGameBlocksPurgeAndUninstall(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra działa")
	testkit.Write(t, game, "Gra.exe", "exe")
	id := w.imp(in.ID, w.zip("m.zip", map[string]string{"m.txt": "m"}), true)
	deployed := w.snap(game)
	w.running = []string{strings.ToUpper(filepath.Join(game, "Gra.exe"))}
	if _, err := w.svc.Purge(in.ID); err == nil {
		t.Error("purge while running")
	}
	if err := w.svc.UninstallMod(in.ID, id); err == nil {
		t.Error("uninstall while running")
	}
	if diff := testkit.Diff(deployed, w.snap(game)); diff != "" {
		t.Errorf("game changed while running:\n%s", diff)
	}
	w.running = nil
	w.must(w.svc.UninstallMod(in.ID, id))
	if qaRead(filepath.Join(game, "m.txt")) != "<brak>" {
		t.Error("not removed after the game closed")
	}
}

// Overrides pointing to an uninstalled mod are cleaned from every profile,
// including inactive ones.
func TestQAUninstallCleansInactiveProfiles(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra profile")
	a := w.imp(in.ID, w.zip("A.zip", map[string]string{"f.txt": "A"}), true)
	w.imp(in.ID, w.zip("B.zip", map[string]string{"f.txt": "B"}), true)
	cs, _ := w.svc.Conflicts(in.ID)
	_, err := w.svc.SetOverride(in.ID, cs[0].Key, a)
	w.must(err)
	p1 := in.ActiveProfile
	p2, err := w.svc.CreateProfile(in.ID, "kopia", p1)
	w.must(err)
	_, err = w.svc.ActivateProfile(in.ID, p2.ID)
	w.must(err)
	w.must(w.svc.UninstallMod(in.ID, a))
	_, err = w.svc.ActivateProfile(in.ID, p1)
	w.must(err)
	if qaRead(filepath.Join(game, "f.txt")) != "B" {
		t.Errorf("P1 after uninstall: %q", qaRead(filepath.Join(game, "f.txt")))
	}
	pr, err := w.svc.profile(in, p1)
	w.must(err)
	if len(pr.FileOverrides) != 0 || len(pr.Mods) != 1 {
		t.Errorf("inactive profile still references the mod: %+v", pr)
	}
}
