package modmgr

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// qaCrashScenario prepares a world; step changes the profile (with
// AutoDeploy off) so that the next deployment does the interesting work.
type qaCrashScenario struct {
	name  string
	def   string
	purge bool
	setup func(w *qaWorld, game string, in *Install)
}

// Power loss before every step of a deployment / purge / profile switch,
// then a launcher restart: the game is exactly "before" or "after" (never
// in between), a second restart changes nothing and purge gets vanilla.
func TestQACrashAtEveryStepThroughService(t *testing.T) {
	off := false
	mods := func(w *qaWorld, in *Install) (string, string) {
		a := w.imp(in.ID, w.zip("A ą.zip", map[string]string{"dane/wspólny.txt": "A", "dane/nowy folder/głęboki/a.txt": "a"}), false)
		b := w.imp(in.ID, w.zip("B ę.zip", map[string]string{"dane/wspólny.txt": "B", "konfig/ro.ini": "B ini", "b.esp": "b"}), false)
		return a, b
	}
	scenarios := []qaCrashScenario{
		{name: "deploy", def: gamedef.GenericID, setup: func(w *qaWorld, game string, in *Install) {
			a, b := mods(w, in)
			w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
			_, err := w.svc.SetEnabled(in.ID, a, true, true)
			w.must(err)
			_, err = w.svc.SetEnabled(in.ID, b, true, true)
			w.must(err)
		}},
		{name: "purge", def: gamedef.GenericID, purge: true, setup: func(w *qaWorld, game string, in *Install) {
			a, b := mods(w, in)
			_, err := w.svc.SetEnabled(in.ID, a, true, true)
			w.must(err)
			_, err = w.svc.SetEnabled(in.ID, b, true, true)
			w.must(err)
		}},
		{name: "switch", def: gamedef.GenericID, setup: func(w *qaWorld, game string, in *Install) {
			a, b := mods(w, in)
			_, err := w.svc.SetEnabled(in.ID, a, true, true)
			w.must(err)
			p2, err := w.svc.CreateProfile(in.ID, "Drugi ż", "")
			w.must(err)
			w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
			_, err = w.svc.ActivateProfile(in.ID, p2.ID)
			w.must(err)
			_, err = w.svc.SetEnabled(in.ID, b, true, true)
			w.must(err)
		}},
		{name: "skyrim-plugins", def: "skyrimse", setup: func(w *qaWorld, game string, in *Install) {
			testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Über Mod.esp\r\n")
			testkit.Write(t, game, "Data/Über Mod.esp", "user")
			a := w.imp(in.ID, w.zip("Sky ą.zip", map[string]string{"Data/Moj.esp": "esp", "Data/textures/n.dds": "t"}), false)
			w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
			_, err := w.svc.SetEnabled(in.ID, a, true, true)
			w.must(err)
		}},
	}
	for _, sc := range scenarios {
		t.Run(sc.name, func(t *testing.T) {
			for n := 0; n < 60; n++ {
				mk := func() (*qaWorld, string, *Install) {
					w := qaNew(t)
					game, in := w.game(sc.def, "Gra awaria ść")
					qaWriteRO(t, game, "konfig/ro.ini", "oryginał RO")
					testkit.Write(t, game, "dane/wspólny.txt", "oryginał")
					sc.setup(w, game, in)
					return w, game, in
				}
				w, game, in := mk()
				before := w.snap(game)
				// reference "after": the same change without a crash
				twin, tgame, tin := mk()
				if sc.purge {
					_, err := twin.svc.Purge(tin.ID)
					twin.must(err)
				} else {
					_, err := twin.svc.Deploy(tin.ID, true)
					twin.must(err)
				}
				after := map[string]string{}
				for k, v := range twin.snap(tgame) {
					after[k] = v
				}
				_ = tin
				hit := w.qaCrashApply(in.ID, sc.purge, n)
				if !hit {
					if n == 0 {
						t.Fatal("no steps")
					}
					return
				}
				v, err := w.svc.GetView(in.ID)
				w.must(err)
				if !v.Pending {
					t.Errorf("n=%d: view does not show the pending transaction", n)
				}
				w.reopen() // launcher restart → recovery
				if len(w.svc.Recovered) == 0 {
					t.Errorf("n=%d: recovery not reported", n)
				}
				got := w.snap(game)
				dB, dA := qaDiffNoMtime(before, got), qaDiffNoMtime(after, got)
				if dB != "" && dA != "" {
					t.Fatalf("n=%d: intermediate state\nvs before:\n%s\nvs after:\n%s", n, dB, dA)
				}
				w.reopen()
				if len(w.svc.Recovered) != 0 {
					t.Fatalf("n=%d: second recovery did something: %v", n, w.svc.Recovered)
				}
				if v, _ := w.svc.GetView(in.ID); v.Pending {
					t.Fatalf("n=%d: still pending", n)
				}
				_, err = w.svc.Purge(in.ID)
				w.must(err)
				vanilla := qaVanilla(t, sc, w)
				if diff := qaDiffNoMtimeOfMod(vanilla, w.snap(game)); diff != "" {
					t.Fatalf("n=%d: purge after recovery not vanilla:\n%s", n, diff)
				}
			}
			t.Fatal("runaway")
		})
	}
}

// qaVanilla builds a fresh vanilla world for comparison.
func qaVanilla(t *testing.T, sc qaCrashScenario, _ *qaWorld) map[string]string {
	w := qaNew(t)
	game, _ := w.game(sc.def, "Gra awaria ść")
	qaWriteRO(t, game, "konfig/ro.ini", "oryginał RO")
	testkit.Write(t, game, "dane/wspólny.txt", "oryginał")
	if sc.name == "skyrim-plugins" {
		testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Über Mod.esp\r\n")
		testkit.Write(t, game, "Data/Über Mod.esp", "user")
	}
	return w.snap(game)
}

// qaDiffNoMtimeOfMod compares snapshots ignoring the modification time
// of files that are not read-only originals (worlds are built at different
// moments, so only content/ro/mtime of RO originals is comparable).
func qaDiffNoMtimeOfMod(a, b map[string]string) string {
	strip := func(m map[string]string) map[string]string {
		out := map[string]string{}
		for k, v := range m {
			if j := strings.LastIndex(v, "|mt="); j > 0 && !strings.HasSuffix(k, "ro.ini") {
				v = v[:j]
			}
			out[k] = v
		}
		return out
	}
	return testkit.Diff(strip(a), strip(b))
}

// After a crash, the next user action (Deploy) recovers by itself without
// a restart.
func TestQACrashThenDeployWithoutRestart(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra bez restartu")
	vanilla := w.snap(game)
	off := false
	w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
	w.imp(in.ID, w.zip("m.zip", map[string]string{"a/1.txt": "1", "a/2.txt": "2", "a/3.txt": "3"}), true)
	if !w.qaCrashApply(in.ID, false, 2) {
		t.Fatal("crash not hit")
	}
	_, err := w.svc.Deploy(in.ID, false)
	w.must(err)
	for _, f := range []string{"1", "2", "3"} {
		if qaRead(filepath.Join(game, "a", f+".txt")) != f {
			t.Errorf("file %s not deployed after recovery", f)
		}
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla:\n%s", diff)
	}
}

// The store source disappears (USB unplugged) between the crash and the
// recovery: recovery must roll back, never leave half a deployment.
func TestQACrashThenStoreGoneRollsBack(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra USB")
	testkit.Write(t, game, "x/orig.txt", "oryginał")
	vanilla := w.snap(game)
	off := false
	w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
	w.imp(in.ID, w.zip("m.zip", map[string]string{"x/orig.txt": "mod", "x/b.txt": "b", "x/c.txt": "c"}), true)
	if !w.qaCrashApply(in.ID, false, 2) {
		t.Fatal("crash not hit")
	}
	// the store vanishes
	store := w.storeDir(in.ID)
	filepath.WalkDir(store, func(p string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() {
			os.Chmod(p, 0o644)
		}
		return nil
	})
	moved := store + " (odłączony)"
	w.must(os.Rename(store, moved))
	w.reopen()
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("recovery without the store is not a rollback:\n%s\nrecovered: %v", diff, w.svc.Recovered)
	}
}

// Leftovers of an interrupted import (.tmp-* with read-only files) in a
// shared (non-generic) store are removed on start.
func TestQAInterruptedImportReadOnlyLeftovers(t *testing.T) {
	w := qaNew(t)
	_, in := w.game("skyrimse", "Skyrim ąę")
	store := w.storeDir(in.ID)
	tmp := filepath.Join(store, ".tmp-01ARZ3NDEKTSV4RRFFQ69G5FAV")
	p := testkit.Write(t, tmp, "files/data/ż.esp", "pół")
	os.Chmod(p, 0o444)
	testkit.Write(t, tmp, "mod.json", "{\"id\":")
	// a half-written mod folder without a valid mod.json is not a mod either
	half := filepath.Join(store, "01ARZ3NDEKTSV4RRFFQ69G5FAW")
	testkit.Write(t, half, "files/data/x.esp", "x")
	w.reopen()
	if _, err := os.Stat(tmp); err == nil {
		t.Errorf("read-only leftover not removed: %v", qaDirNames(t, store))
	}
	v, err := w.svc.GetView(in.ID)
	w.must(err)
	if len(v.Mods) != 0 {
		t.Errorf("half mods visible: %+v", v.Mods)
	}
}

// A game update replaces a file the mod overwrote: redeploy keeps the mod
// but the update becomes the new original, which purge must bring back.
func TestQAGameUpdateThenRedeployThenPurgeKeepsNewOriginal(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra aktualizacja")
	lvl := testkit.Write(t, game, "data/level.pak", "v1 gry")
	w.imp(in.ID, w.zip("m.zip", map[string]string{"data/level.pak": "mod"}), true)
	qaReplace(t, lvl, "v2 gry")
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	if len(vr.Drift) == 0 {
		t.Error("update not detected as drift")
	}
	dr, err := w.svc.Deploy(in.ID, false)
	w.must(err)
	t.Logf("deploy after update: %+v -> %q", dr, qaRead(lvl))
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if got := qaRead(lvl); got != "v2 gry" {
		t.Errorf("purge after a game update brought back %q, want the updated game file", got)
	}
}

// A game update adds a file at a path where a mod had already placed a
// (new) file: uninstall/purge must keep the game's new file.
func TestQAGameUpdateAddsFileWhereModPlacedOne(t *testing.T) {
	for _, how := range []string{"uninstall", "purge", "disable"} {
		t.Run(how, func(t *testing.T) {
			w := qaNew(t)
			game, in := w.game(gamedef.GenericID, "Gra łatka")
			id := w.imp(in.ID, w.zip("m.zip", map[string]string{"patch/nowy.dll.txt": "mod", "patch/inny.txt": "i"}), true)
			p := filepath.Join(game, "patch", "nowy.dll.txt")
			qaReplace(t, p, "plik z łatki gry")
			switch how {
			case "uninstall":
				w.must(w.svc.UninstallMod(in.ID, id))
			case "purge":
				_, err := w.svc.Purge(in.ID)
				w.must(err)
			case "disable":
				_, err := w.svc.SetEnabled(in.ID, id, false, false)
				w.must(err)
			}
			if got := qaRead(p); got != "plik z łatki gry" {
				t.Errorf("game's new file lost: %q", got)
			}
			if qaRead(filepath.Join(game, "patch", "inny.txt")) != "<brak>" {
				t.Error("mod file left")
			}
		})
	}
}

// Steam "verify files" deleted a file the mod had overwritten: purge must
// not fail and the original comes back.
func TestQADeletedDeployedFileThenPurge(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra weryfikacja")
	f := testkit.Write(t, game, "d/x.txt", "oryginał")
	vanilla := w.snap(game)
	w.imp(in.ID, w.zip("m.zip", map[string]string{"d/x.txt": "mod", "d/y.txt": "y"}), true)
	os.Chmod(f, 0o644)
	w.must(os.Remove(f))
	os.Chmod(filepath.Join(game, "d", "y.txt"), 0o644)
	w.must(os.Remove(filepath.Join(game, "d", "y.txt")))
	_, err := w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla:\n%s", diff)
	}
}

// qaDiffNoMtime compares snapshots ignoring every modification time.
func qaDiffNoMtime(a, b map[string]string) string {
	strip := func(m map[string]string) map[string]string {
		out := map[string]string{}
		for k, v := range m {
			if j := strings.LastIndex(v, "|mt="); j > 0 {
				v = v[:j]
			}
			out[k] = v
		}
		return out
	}
	return testkit.Diff(strip(a), strip(b))
}

// "Last resort" (design §1.8): purge must work from the manifest and the
// backups even when the store is gone (unplugged USB).
func TestQAPurgeWithoutStore(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra bez magazynu")
	qaWriteRO(t, game, "c/ro.ini", "oryginał")
	vanilla := w.snap(game)
	w.imp(in.ID, w.zip("m.zip", map[string]string{"c/ro.ini": "mod", "c/nowy.txt": "n"}), true)
	store := w.storeDir(in.ID)
	filepath.WalkDir(store, func(p string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() {
			os.Chmod(p, 0o644)
		}
		return nil
	})
	w.must(os.Rename(store, store+".odłączony"))
	w.reopen()
	_, err := w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("purge without the store is not vanilla:\n%s", diff)
	}
}

// A damaged manifest is reported, never silently replaced, and nothing in
// the game is touched.
func TestQADamagedManifestReported(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra zły manifest")
	w.imp(in.ID, w.zip("m.zip", map[string]string{"x.txt": "x"}), true)
	deployed := w.snap(game)
	mp := filepath.Join(w.app, "data", "modmgr", "state", in.ID, "manifest.json")
	b, err := os.ReadFile(mp)
	w.must(err)
	w.must(os.WriteFile(mp, b[:len(b)/2], 0o644))
	w.reopen()
	if _, err := w.svc.Purge(in.ID); err == nil {
		t.Error("purge with a damaged manifest succeeded silently")
	} else if !strings.Contains(err.Error(), "manifest") {
		t.Errorf("unclear error: %v", err)
	}
	if _, err := w.svc.Deploy(in.ID, false); err == nil {
		t.Error("deploy with a damaged manifest succeeded silently")
	}
	if diff := testkit.Diff(deployed, w.snap(game)); diff != "" {
		t.Errorf("game touched:\n%s", diff)
	}
	if qaRead(mp) != string(b[:len(b)/2]) {
		t.Error("damaged manifest replaced")
	}
}

// A game update (watched exe changed) is shown in the view and by Verify.
func TestQAGameUpdateFlag(t *testing.T) {
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim update")
	w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/A.esp": "a"}), true)
	if v, _ := w.svc.GetView(in.ID); v.GameUpdated {
		t.Fatal("updated right after deploy")
	}
	qaReplace(t, filepath.Join(game, "SkyrimSE.exe"), "nowa wersja exe – inny rozmiar")
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	v, err := w.svc.GetView(in.ID)
	w.must(err)
	if !vr.GameUpdated || !v.GameUpdated {
		t.Errorf("game update not detected: verify=%v view=%v", vr.GameUpdated, v.GameUpdated)
	}
	_, err = w.svc.Deploy(in.ID, false)
	w.must(err)
	if v, _ := w.svc.GetView(in.ID); v.GameUpdated {
		t.Error("flag not cleared after redeploy")
	}
}
