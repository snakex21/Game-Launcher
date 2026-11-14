package modmgr

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// Polish characters and spaces in: launcher folder, game folder, archive
// name, folders and files inside the archive, mods target.
func TestQAPolishAndSpacesEverywhere(t *testing.T) {
	w := qaNew(t)
	d := w.svc.Defs().Get(gamedef.GenericID)
	game := filepath.Join(w.base, "Biblioteka gier", "Gra Źdźbło ąęśżźćńół")
	testkit.Game(t, d, game)
	in, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: game, ModsTarget: "Dane gry ŻÓŁW"})
	w.must(err)
	testkit.Write(t, game, "Dane gry ŻÓŁW/Tekstury ćma/niebo ń.dds", "oryginalne niebo")
	vanilla := w.snap(game)

	z := w.zip("Mod ąęśżźćńół wersja 1.0 (final).zip", map[string]string{
		"Tekstury ćma/niebo ń.dds":           "niebo z moda",
		"Nowy folder ŁĄKA/plik z spacją.txt": "łąka",
		"źdźbło.ini":                         "[Sekcja]\nklucz=wartość\n",
	})
	id := w.imp(in.ID, z, true)
	v, err := w.svc.GetView(in.ID)
	w.must(err)
	if len(v.Mods) != 1 || !strings.Contains(v.Mods[0].Name, "ąęśżźćńół") {
		t.Errorf("mod name lost Polish characters: %+v", v.Mods)
	}
	if !v.InSync || v.Deployed != 3 {
		t.Errorf("view after import: inSync=%v deployed=%d", v.InSync, v.Deployed)
	}
	target := filepath.Join(game, "Dane gry ŻÓŁW")
	for rel, want := range map[string]string{
		"Tekstury ćma/niebo ń.dds":           "niebo z moda",
		"Nowy folder ŁĄKA/plik z spacją.txt": "łąka",
		"źdźbło.ini":                         "[Sekcja]\nklucz=wartość\n",
	} {
		if got := qaRead(filepath.Join(target, filepath.FromSlash(rel))); got != want {
			t.Errorf("%s = %q, want %q", rel, got, want)
		}
	}
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	if len(vr.Drift) != 0 || len(vr.StoreIssues) != 0 {
		t.Errorf("verify: %+v", vr)
	}
	// a fresh service (restart of the launcher) sees the same state
	w.reopen()
	if len(w.svc.Recovered) != 0 {
		t.Errorf("clean restart reported recovery: %v", w.svc.Recovered)
	}
	v, err = w.svc.GetView(in.ID)
	w.must(err)
	if !v.InSync {
		t.Error("not in sync after restart")
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla after purge:\n%s", diff)
	}
	w.must(w.svc.UninstallMod(in.ID, id))
	if left := qaDirNames(t, w.storeDir(in.ID)); len(left) != 0 {
		t.Errorf("store not empty after uninstall: %v", left)
	}
}

// A folder (not an archive) with Polish names is a valid source too.
func TestQAImportFromFolderWithPolishNames(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra folder ąę")
	vanilla := w.snap(game)
	src := filepath.Join(w.base, "Rozpakowany mod ŹĆ")
	testkit.Write(t, src, "Mój mod/żaba.txt", "rechot")
	testkit.Write(t, src, "Mój mod/sub dir/ł.cfg", "x=1")
	id := w.imp(in.ID, src, true)
	found := false
	filepath.WalkDir(game, func(p string, de os.DirEntry, err error) error {
		if err == nil && de.Name() == "żaba.txt" {
			found = qaRead(p) == "rechot"
		}
		return nil
	})
	if !found {
		t.Errorf("żaba.txt not deployed:\n%v", qaSnapshot(t, game))
	}
	// the source folder must stay untouched (it is not moved into the store)
	if qaRead(filepath.Join(src, "Mój mod", "żaba.txt")) != "rechot" {
		t.Error("source folder modified")
	}
	w.must(w.svc.UninstallMod(in.ID, id))
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla after uninstall:\n%s", diff)
	}
}

// A read-only original overwritten by a mod comes back read-only, with the
// same content and modification time, whichever way the mod goes away.
func TestQAReadOnlyOriginalRestoredEveryWay(t *testing.T) {
	for _, how := range []string{"purge", "disable", "uninstall", "empty-profile"} {
		t.Run(how, func(t *testing.T) {
			w := qaNew(t)
			game, in := w.game(gamedef.GenericID, "Gra RO ść")
			ro := qaWriteRO(t, game, "Konfiguracja/gra ą.ini", "oryginał tylko do odczytu")
			qaWriteRO(t, game, "Konfiguracja/inny.ini", "drugi RO, nietykany")
			vanilla := w.snap(game)
			id := w.imp(in.ID, w.zip("ro ę.zip", map[string]string{"Konfiguracja/gra ą.ini": "z moda", "Konfiguracja/nowy.ini": "nowy"}), true)
			if qaRead(ro) != "z moda" {
				t.Fatalf("not deployed: %q", qaRead(ro))
			}
			switch how {
			case "purge":
				_, err := w.svc.Purge(in.ID)
				w.must(err)
			case "disable":
				_, err := w.svc.SetEnabled(in.ID, id, false, false)
				w.must(err)
			case "uninstall":
				w.must(w.svc.UninstallMod(in.ID, id))
			case "empty-profile":
				p, err := w.svc.CreateProfile(in.ID, "Pusty", "")
				w.must(err)
				_, err = w.svc.ActivateProfile(in.ID, p.ID)
				w.must(err)
			}
			if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
				t.Errorf("not bit-identical vanilla (incl. ro flag and mtime):\n%s", diff)
			}
			if !qaIsRO(t, ro) {
				t.Error("read-only flag not restored")
			}
		})
	}
}

// Two mods, one file: later wins; a per-file rule overrides the order;
// disabling/uninstalling the winner brings back the other mod's file and
// removing everything brings back the original.
func TestQASameFileTwoModsWinnerChain(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra konflikt ż")
	f := testkit.Write(t, game, "dane/wspólny plik.txt", "oryginał")
	vanilla := w.snap(game)
	a := w.imp(in.ID, w.zip("A ą.zip", map[string]string{"dane/wspólny plik.txt": "A", "dane/tylko A.txt": "a"}), true)
	b := w.imp(in.ID, w.zip("B ę.zip", map[string]string{"dane/wspólny plik.txt": "B", "dane/tylko B.txt": "b"}), true)
	if qaRead(f) != "B" {
		t.Fatalf("later mod must win, got %q", qaRead(f))
	}
	cs, err := w.svc.Conflicts(in.ID)
	w.must(err)
	if len(cs) != 1 || cs[0].WinnerID != b {
		t.Fatalf("conflicts: %+v", cs)
	}
	// rule: A wins this file
	_, err = w.svc.SetOverride(in.ID, cs[0].Key, a)
	w.must(err)
	if qaRead(f) != "A" {
		t.Fatalf("override not deployed: %q", qaRead(f))
	}
	// reorder must not beat the rule
	_, err = w.svc.Move(in.ID, b, 5)
	w.must(err)
	if qaRead(f) != "A" {
		t.Fatalf("order beat the rule: %q", qaRead(f))
	}
	// disable the rule's winner: the rule is ignored, B wins
	_, err = w.svc.SetEnabled(in.ID, a, false, false)
	w.must(err)
	if qaRead(f) != "B" || qaRead(filepath.Join(game, "dane", "tylko A.txt")) != "<brak>" {
		t.Fatalf("disable winner: %q", qaRead(f))
	}
	// enable A again: the rule still exists → A
	_, err = w.svc.SetEnabled(in.ID, a, true, false)
	w.must(err)
	if qaRead(f) != "A" {
		t.Fatalf("rule lost after re-enable: %q", qaRead(f))
	}
	// uninstall A (the rule's winner): B's file comes back, rule removed
	w.must(w.svc.UninstallMod(in.ID, a))
	if qaRead(f) != "B" {
		t.Fatalf("after uninstalling A: %q", qaRead(f))
	}
	if cs, _ := w.svc.Conflicts(in.ID); len(cs) != 0 {
		t.Errorf("conflicts left: %+v", cs)
	}
	w.must(w.svc.UninstallMod(in.ID, b))
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla after uninstalling all:\n%s", diff)
	}
	if left := qaDirNames(t, w.storeDir(in.ID)); len(left) != 0 {
		t.Errorf("store not empty: %v", left)
	}
}

// Disabling the losing mod changes nothing on disk; disabling the winner of
// a file the game did not have originally brings the loser's version.
func TestQASameNewFileLoserComesBack(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra nowy plik")
	vanilla := w.snap(game)
	a := w.imp(in.ID, w.zip("A.zip", map[string]string{"nowe/x.txt": "A"}), true)
	b := w.imp(in.ID, w.zip("B.zip", map[string]string{"nowe/x.txt": "B"}), true)
	x := filepath.Join(game, "nowe", "x.txt")
	_, err := w.svc.SetEnabled(in.ID, a, false, false)
	w.must(err)
	if qaRead(x) != "B" {
		t.Fatalf("disabling loser changed winner: %q", qaRead(x))
	}
	_, err = w.svc.SetEnabled(in.ID, a, true, false)
	w.must(err)
	_, err = w.svc.SetEnabled(in.ID, b, false, false)
	w.must(err)
	if qaRead(x) != "A" {
		t.Fatalf("loser did not come back: %q", qaRead(x))
	}
	_, err = w.svc.SetEnabled(in.ID, a, false, false)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla with all disabled:\n%s", diff)
	}
}

// Case-only differences between two mods and the game: one target, the
// original file keeps its exact name case after purge.
func TestQACaseOnlyDifferences(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra Wielkość Liter")
	testkit.Write(t, game, "Data/Textures/Sky.DDS", "oryginał")
	vanilla := w.snap(game)
	w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/Textures/Sky.DDS": "A"}), true)
	b := w.imp(in.ID, w.zip("B.zip", map[string]string{"data/textures/sky.dds": "B"}), true)
	cs, err := w.svc.Conflicts(in.ID)
	w.must(err)
	if len(cs) != 1 || cs[0].WinnerID != b {
		t.Errorf("case-insensitive conflict not detected: %+v", cs)
	}
	ents, _ := os.ReadDir(filepath.Join(game, "Data", "Textures"))
	if len(ents) != 1 || qaRead(filepath.Join(game, "Data", "Textures", ents[0].Name())) != "B" {
		t.Errorf("expected exactly one file with B, got %v", ents)
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("purge changed the original (name case?):\n%s", diff)
	}
}

// An archive with two entries differing only in case: a warning, one file.
func TestQACaseCollisionInsideArchive(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra kolizja")
	z := qaRawZip(t, filepath.Join(w.base, "kolizja.zip"), []qaZipEntry{
		{name: "Tex/A.dds", data: "first"}, {name: "tex/a.dds", data: "last"},
	})
	pv, err := w.svc.PreviewImport(ImportIn{Install: in.ID, Path: z})
	w.must(err)
	if !qaContains(pv.Warnings, "wielko") && !qaContains(pv.Plan.Warnings, "wielko") {
		t.Errorf("no case-collision warning: %v / %v", pv.Warnings, pv.Plan.Warnings)
	}
	w.imp(in.ID, z, true)
	var got []string
	filepath.WalkDir(game, func(p string, de os.DirEntry, err error) error {
		if err == nil && !de.IsDir() && strings.EqualFold(de.Name(), "a.dds") {
			got = append(got, qaRead(p))
		}
		return nil
	})
	if len(got) != 1 || got[0] != "last" {
		t.Errorf("want one file with the last entry, got %v", got)
	}
}
