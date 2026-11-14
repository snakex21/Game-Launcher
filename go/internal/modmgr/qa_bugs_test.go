package modmgr

// Focused reproductions of problems found by the QA pass; all are fixed and
// kept as regression tests (marked "QA-BUG fixed").

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// Deploying a mod must not enable plugins the user had disabled in
// plugins.txt (the definition says readExternalChanges: true).
func TestQABugDeployEnablesUserDisabledPlugins(t *testing.T) {
	// QA-BUG fixed (regression test): deploy enables plugins the user disabled in plugins.txt (readExternalChanges ignored)
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim wyłączone")
	pf := testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Gracza.esp\r\nWylaczony.esp\r\n")
	testkit.Write(t, game, "Data/Gracza.esp", "g")
	testkit.Write(t, game, "Data/Wylaczony.esp", "w")
	w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/A.esp": "a"}), true)
	got := qaRead(pf)
	if strings.Contains(got, "*Wylaczony.esp") {
		t.Errorf("a plugin the user disabled was enabled by the deployment: %q", got)
	}
}

// The user changes plugins.txt while mods are deployed (disables a plugin
// in another tool); a redeploy must not undo it.
func TestQABugRedeployUndoesExternalPluginsTxtEdit(t *testing.T) {
	// QA-BUG fixed (regression test): redeploy re-enables a plugin the user disabled in plugins.txt outside the manager
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim edycja 2")
	pf := testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Gracza.esp\r\n")
	testkit.Write(t, game, "Data/Gracza.esp", "g")
	w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/A.esp": "a"}), true)
	qaReplace(t, pf, "Gracza.esp\r\n*A.esp\r\n")
	_, err := w.svc.Deploy(in.ID, false)
	w.must(err)
	if got := qaRead(pf); strings.Contains(got, "*Gracza.esp") {
		t.Errorf("redeploy re-enabled a plugin the user disabled: %q", got)
	}
}

// After an external edit of plugins.txt the edited file (with our lines)
// becomes the "original"; purge then leaves our plugin active although
// its file is gone.
func TestQABugPurgeLeavesModPluginInEditedPluginsTxt(t *testing.T) {
	// QA-BUG fixed (regression test): after an external plugins.txt edit, purge restores it with the removed mod plugin still active
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim edycja 3")
	pf := testkit.Write(t, w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition/plugins.txt", "*Gracza.esp\r\n")
	testkit.Write(t, game, "Data/Gracza.esp", "g")
	w.imp(in.ID, w.zip("A.zip", map[string]string{"Data/A.esp": "a"}), true)
	qaReplace(t, pf, "*A.esp\r\n*Gracza.esp\r\n") // user reordered in an external tool
	_, err := w.svc.Deploy(in.ID, false)
	w.must(err)
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if qaRead(filepath.Join(game, "Data", "A.esp")) != "<brak>" {
		t.Fatal("mod file left")
	}
	if got := qaRead(pf); strings.Contains(got, "A.esp") {
		t.Errorf("purge left the removed mod's plugin in plugins.txt: %q", got)
	}
}

// Two installs of the same game resolve user-folder targets (plugins.txt
// in %LOCALAPPDATA%) to the same file. Each one backs up the other's
// generated file as an "original", so after removing everything a stale
// plugins.txt (that did not exist before) stays behind.
func TestQABugTwoInstallsSameUserFolderFile(t *testing.T) {
	// QA-BUG fixed (regression test): two installs writing the same user-folder file (plugins.txt) leave a stale file after purge of both
	w := qaNew(t)
	g1, i1 := w.game("skyrimse", "Skyrim kopia 1")
	g2, i2 := w.game("skyrimse", "Skyrim kopia 2")
	v1, v2 := w.snap(g1), w.snap(g2)
	id := w.imp(i1.ID, w.zip("W.zip", map[string]string{"Data/W.esp": "w"}), true)
	// fix: the second install may not deploy into a file the first one
	// has deployed (the change is kept in its profile, the deploy refused)
	_, err := w.svc.SetEnabled(i2.ID, id, true, false)
	if err == nil || !strings.Contains(err.Error(), "Skyrim") {
		t.Fatalf("second install deployed into the first one's plugins.txt: %v", err)
	}
	pfFirst := filepath.Join(w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition", "plugins.txt")
	if got := qaRead(pfFirst); got != "*W.esp\r\n" {
		t.Fatalf("first install's plugins.txt touched: %q", got)
	}
	w.must(w.svc.UninstallMod(i1.ID, id))
	_, err = w.svc.Purge(i1.ID)
	w.must(err)
	_, err = w.svc.Purge(i2.ID)
	w.must(err)
	pf := filepath.Join(w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition", "plugins.txt")
	if diff := testkit.Diff(v1, w.snap(g1)) + testkit.Diff(v2, w.snap(g2)); diff != "" {
		t.Errorf("not vanilla after uninstall + purge of both (plugins.txt=%q):\n%s", qaRead(pf), diff)
	}
}

// A file that is not an archive but has a .zip name (truncated download, an
// HTML error page, zero bytes) is installed into the game as a loose file.
func TestQABugCorruptZipInstalledAsLooseFile(t *testing.T) {
	// QA-BUG fixed (regression test): non-archive with .zip/.7z extension is installed into the game as a loose file
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra zły zip")
	vanilla := w.snap(game)
	html := filepath.Join(w.base, "mod z błędem.zip")
	w.must(os.WriteFile(html, []byte("<!DOCTYPE html><html><body>429 Too Many Requests</body></html>"), 0o644))
	zero := filepath.Join(w.base, "zero.7z")
	w.must(os.WriteFile(zero, nil, 0o644))
	for _, p := range []string{html, zero} {
		row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: p, Enable: true})
		if err == nil {
			t.Errorf("%s: a non-archive with an archive extension was accepted as a loose file (%d files)", filepath.Base(p), row.Files)
		}
	}
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("game changed:\n%s", diff)
	}
}

// UninstallMod while the game runs fails, but has already removed the mod
// from every profile: the user loses the mod's place/state although the
// operation "failed".
func TestQABugFailedUninstallStillEditsProfiles(t *testing.T) {
	// QA-BUG fixed (regression test): UninstallMod that fails (game running) already removed the mod from all profiles
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra działa 2")
	testkit.Write(t, game, "Gra.exe", "exe")
	w.imp(in.ID, w.zip("A.zip", map[string]string{"a.txt": "a"}), true)
	id := w.imp(in.ID, w.zip("B.zip", map[string]string{"b.txt": "b"}), true)
	w.running = []string{filepath.Join(game, "Gra.exe")}
	if err := w.svc.UninstallMod(in.ID, id); err == nil {
		t.Fatal("uninstall while running succeeded")
	}
	v, err := w.svc.GetView(in.ID)
	w.must(err)
	for _, m := range v.Mods {
		if m.ID == id && (!m.InProfile || !m.Enabled) {
			t.Errorf("failed uninstall changed the profile: %+v", m)
		}
	}
}

// A tool writes in place to a deployed (hardlinked) mod file. The store copy
// changes with it. Purge leaves the file in the game (it is the same NTFS
// file as the store copy, i.e. still ours by fileId) and uninstall does
// not remove it either: the game never gets back to vanilla.
func TestQABugHardlinkWriteThroughLeftAfterPurge(t *testing.T) {
	// QA-BUG fixed (regression test): in-place write through a hardlink: purge+uninstall leave the mod file in the game
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra hardlink 2")
	vanilla := w.snap(game)
	id := w.imp(in.ID, w.zip("m.zip", map[string]string{"tex/mod.dds": "a=1"}), true)
	gp := filepath.Join(game, "tex", "mod.dds")
	w.must(os.Chmod(gp, 0o644))
	w.must(os.WriteFile(gp, []byte("a=2 zapis w miejscu"), 0o644))
	_, err := w.svc.Purge(in.ID)
	w.must(err)
	w.must(w.svc.UninstallMod(in.ID, id))
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("mod file stays in the game after purge + uninstall:\n%s", diff)
	}
}

// Same write-through, but followed by a (re)deploy: the modified mod file
// is taken as a new "original" and comes back on purge.
func TestQABugHardlinkWriteThroughBecomesOriginal(t *testing.T) {
	// QA-BUG fixed (regression test): in-place write through a hardlink, then deploy: modified mod file becomes the original and survives purge
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra hardlink 3")
	vanilla := w.snap(game)
	id := w.imp(in.ID, w.zip("m.zip", map[string]string{"tex/mod.dds": "a=1"}), true)
	gp := filepath.Join(game, "tex", "mod.dds")
	w.must(os.Chmod(gp, 0o644))
	w.must(os.WriteFile(gp, []byte("a=2 zapis w miejscu"), 0o644))
	_, err := w.svc.Deploy(in.ID, false)
	w.must(err)
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	w.must(w.svc.UninstallMod(in.ID, id))
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla (got %q):\n%s", qaRead(gp), diff)
	}
}

// Same-size in-place write: the store is silently corrupted and the next
// deploy of another install/profile uses the corrupted content without a
// repair (design §1.7: repair from downloads/).
func TestQAHardlinkSameSizeWriteReported(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra hardlink 4")
	w.imp(in.ID, w.zip("m.zip", map[string]string{"tex/mod.dds": "a=1"}), true)
	gp := filepath.Join(game, "tex", "mod.dds")
	w.must(os.Chmod(gp, 0o644))
	w.must(os.WriteFile(gp, []byte("a=9"), 0o644))
	vr, err := w.svc.Verify(in.ID)
	w.must(err)
	if len(vr.StoreIssues) == 0 {
		t.Errorf("same-size write through hardlink not reported: %+v", vr)
	}
}

var _ = errors.New
