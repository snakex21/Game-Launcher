package modmgr

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// Ids coming from the UI are validated: path-like ids never reach the
// file system (installs.json, other profiles, store).
func TestQAHostileIDsFromUI(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra id")
	id := w.imp(in.ID, w.zip("m.zip", map[string]string{"m.txt": "m"}), true)
	root := filepath.Join(w.app, "data", "modmgr")
	before := qaSnapshot(t, root)
	gameBefore := w.snap(game)
	bad := []string{"", ".", "..", `..\..\installs`, "../../installs", `..\..\..\..\Windows`, "C:/x", in.ID + "/../x", "CON", strings.Repeat("A", 300)}
	for _, b := range bad {
		if err := w.svc.DeleteProfile(in.ID, b); err == nil {
			t.Errorf("DeleteProfile(%q) accepted", b)
		}
		if err := w.svc.RenameProfile(in.ID, b, "x"); err == nil {
			t.Errorf("RenameProfile(%q) accepted", b)
		}
		if _, err := w.svc.ActivateProfile(in.ID, b); err == nil {
			t.Errorf("ActivateProfile(%q) accepted", b)
		}
		if _, err := w.svc.CreateProfile(in.ID, "kopia", b); err == nil && b != "" {
			t.Errorf("CreateProfile(copyFrom=%q) accepted", b)
		}
		if _, err := w.svc.SetEnabled(in.ID, b, true, true); err == nil {
			t.Errorf("SetEnabled(%q) accepted", b)
		}
		if _, err := w.svc.Move(in.ID, b, 0); err == nil {
			t.Errorf("Move(%q) accepted", b)
		}
		if err := w.svc.UninstallMod(in.ID, b); err == nil {
			t.Errorf("UninstallMod(%q) accepted", b)
		}
		if err := w.svc.RenameMod(in.ID, b, "x"); err == nil {
			t.Errorf("RenameMod(%q) accepted", b)
		}
		if _, err := w.svc.ModFiles(in.ID, b); err == nil {
			t.Errorf("ModFiles(%q) accepted", b)
		}
		if _, err := w.svc.GetView(b); err == nil {
			t.Errorf("GetView(%q) accepted", b)
		}
		if err := w.svc.RemoveInstall(b); err == nil {
			t.Errorf("RemoveInstall(%q) accepted", b)
		}
		if _, err := w.svc.SetOverride(in.ID, "files:m.txt", b); err == nil && b != "" {
			t.Errorf("SetOverride(mod=%q) accepted", b)
		}
		if p, err := w.svc.FolderPath(in.ID, b); err == nil && !strings.HasPrefix(p, game) && !strings.HasPrefix(p, root) {
			t.Errorf("FolderPath(%q) = %s", b, p)
		}
	}
	// the CreateProfile calls with copyFrom="" legitimately added profiles;
	// ignore new profile files, nothing else may change
	after := qaSnapshot(t, root)
	for k, v := range before {
		// new profiles (copyFrom="") and no-op redeploys (new manifest tx) are legitimate
		if (strings.HasPrefix(k, "profiles/") && strings.HasSuffix(k, ".json")) || strings.HasPrefix(k, "state/") {
			continue
		}
		if after[k] != v {
			t.Errorf("changed: %s %q -> %q", k, v, after[k])
		}
	}
	if diff := testkit.Diff(gameBefore, w.snap(game)); diff != "" {
		t.Errorf("game changed:\n%s", diff)
	}
	if _, err := w.svc.ModFiles(in.ID, id); err != nil {
		t.Error(err)
	}
}

// AddInstall rejects relative paths, files, the launcher's own folder and
// duplicates that differ only by case or a trailing separator.
func TestQAAddInstallValidation(t *testing.T) {
	w := qaNew(t)
	game, _ := w.game(gamedef.GenericID, "Gra dodaj")
	f := testkit.Write(t, w.base, "plik.txt", "x")
	for _, p := range []string{"", "względna\\ścieżka", f, strings.ToUpper(game), game + `\`, filepath.Join(game, ".", "")} {
		if _, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: p, Force: true}); err == nil {
			t.Errorf("AddInstall(%q) accepted", p)
		}
	}
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: game + "x", ModsTarget: `..\..\Windows`, Force: true}); err == nil {
		t.Error("mods target outside the game accepted")
	}
}

// The launcher folder itself (or its data folder) is never a game: a mod
// could overwrite the manager's own state (installs.json, manifests).
func TestQAAddInstallLauncherFolderRefused(t *testing.T) {
	// QA-BUG fixed (regression test): launcher folder / its data folder accepted as a game folder
	w := qaNew(t)
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: w.app, Force: true}); err == nil {
		t.Error("launcher folder accepted as a game folder")
	}
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: filepath.Join(w.app, "data"), Force: true}); err == nil {
		t.Error("launcher data folder accepted as a game folder")
	}
}

// A game folder inside another managed game folder (nested installs) would
// let two engines fight over the same files.
func TestQANestedInstallsRefused(t *testing.T) {
	// QA-BUG fixed (regression test): a game folder inside another managed game folder is accepted
	w := qaNew(t)
	game, _ := w.game(gamedef.GenericID, "Gra zewnętrzna")
	inner := filepath.Join(game, "vanilla")
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: gamedef.GenericID, Path: inner, Force: true}); err == nil {
		t.Error("an install inside another install was accepted")
	}
}

// Two launcher instances (two Services on the same folder) deploying at
// the same time: no corruption, the game ends in a consistent state.
func TestQATwoServicesConcurrently(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra równolegle")
	vanilla := w.snap(game)
	for i := 0; i < 5; i++ {
		files := map[string]string{}
		for j := 0; j < 20; j++ {
			files[filepath.ToSlash(filepath.Join("d", string(rune('a'+j))+".txt"))] = strings.Repeat(string(rune('A'+i)), j+1)
		}
		w.imp(in.ID, w.zip(string(rune('A'+i))+".zip", files), true)
	}
	other, err := New(w.app, Options{Folders: w.folders})
	w.must(err)
	var wg sync.WaitGroup
	errs := make(chan error, 40)
	for i := 0; i < 10; i++ {
		wg.Add(2)
		go func() {
			defer wg.Done()
			if _, err := w.svc.Purge(in.ID); err != nil {
				errs <- err
			}
		}()
		go func() {
			defer wg.Done()
			if _, err := other.Deploy(in.ID, false); err != nil {
				errs <- err
			}
		}()
	}
	wg.Wait()
	close(errs)
	n := 0
	for err := range errs {
		n++
		if n < 3 {
			t.Logf("concurrent error (expected sometimes): %v", err)
		}
	}
	w.reopen()
	_, err = w.svc.Deploy(in.ID, false)
	w.must(err)
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	if len(vr.Drift) != 0 || len(vr.StoreIssues) != 0 {
		t.Errorf("inconsistent after concurrent use: %+v", vr)
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla:\n%s", diff)
	}
}

// Removing a generic install leaves no folder of it behind.
func TestQARemoveGenericInstallLeavesNothing(t *testing.T) {
	// QA-BUG fixed (regression test): RemoveInstall leaves empty store/generic-<id> and downloads/generic-<id> folders
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra do usunięcia")
	id := w.imp(in.ID, w.zip("m.zip", map[string]string{"m.txt": "m"}), true)
	_, err := w.svc.Purge(in.ID)
	w.must(err)
	_ = id
	w.must(w.svc.RemoveInstall(in.ID))
	var left []string
	filepath.WalkDir(filepath.Join(w.app, "data", "modmgr"), func(p string, d os.DirEntry, err error) error {
		if err == nil && strings.Contains(p, in.ID) {
			left = append(left, p)
		}
		return nil
	})
	if len(left) != 0 {
		t.Errorf("leftovers of the removed install: %v", left)
	}
	if qaRead(filepath.Join(game, "m.txt")) != "<brak>" {
		t.Error("game file left")
	}
}

// One plugin with a name that cannot be written in Windows-1252, put into
// Data by hand (not by the manager), blocks every deployment of the game.
func TestQAExternalNonCp1252PluginBlocksDeploy(t *testing.T) {
	// QA-BUG fixed (regression test): a hand-installed plugin with a non-cp1252 name blocks every deployment; error shows the whole plugins.txt
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim cp1252")
	testkit.Write(t, game, "Data/Łódź.esp", "ręcznie")
	_, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: w.zip("A.zip", map[string]string{"Data/A.esp": "a"}), Enable: true})
	if err != nil {
		t.Errorf("a hand-installed plugin with a non-cp1252 name blocks deployment: %v", err)
		if strings.Contains(err.Error(), "\r\n") {
			t.Errorf("error message contains the whole generated plugins.txt instead of the plugin name")
		}
	}
}

// Import with Enable=false and a later SetEnabled must give the same
// result as Import with Enable=true; an executable mod imported disabled
// needs consent on enable.
func TestQAEnableLaterSameAsImmediate(t *testing.T) {
	w := qaNew(t)
	g1, i1 := w.game(gamedef.GenericID, "Gra od razu")
	g2, i2 := w.game(gamedef.GenericID, "Gra później")
	files := map[string]string{"bin/x.dll": "dll", "dane/a.txt": "a"}
	w.imp(i1.ID, w.zip("x.zip", files), true)
	row, _, err := w.svc.Import(ImportIn{Install: i2.ID, Path: w.zip("x2.zip", files)})
	w.must(err)
	if qaRead(filepath.Join(g2, "dane", "a.txt")) != "<brak>" {
		t.Error("disabled import deployed")
	}
	var ue *UserError
	if _, err := w.svc.SetEnabled(i2.ID, row.ID, true, false); !errors.As(err, &ue) || ue.Confirm != "executable" {
		t.Errorf("enable of a DLL mod without consent: %v", err)
	}
	_, err = w.svc.SetEnabled(i2.ID, row.ID, true, true)
	w.must(err)
	if diff := qaDiffNoMtime(qaSnapshot(t, g1), qaSnapshot(t, g2)); diff != "" {
		t.Errorf("enable later != enable on import:\n%s", diff)
	}
}
