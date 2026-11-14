package modmgr

import (
	"errors"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/testkit"
)

// Malicious archives imported through the service: refused, nothing
// written anywhere outside the launcher's own data folder, no store
// leftovers, game untouched.
func TestQAMaliciousArchivesThroughService(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra atak")
	vanilla := w.snap(game)
	outside := qaSnapshot(t, w.base)
	cases := map[string][]qaZipEntry{
		"traversal":         {{name: "ok.txt", data: "ok"}, {name: "../../../zło.txt", data: "evil"}},
		"traversal-mid":     {{name: "a/b/../../../zło.txt", data: "evil"}},
		"traversal-bslash":  {{name: `a\..\..\zło.txt`, data: "evil"}},
		"absolute-slash":    {{name: "/zło.txt", data: "evil"}},
		"absolute-drive":    {{name: "C:/zło.txt", data: "evil"}},
		"drive-relative":    {{name: "C:zło.txt", data: "evil"}},
		"unc":               {{name: `\\serwer\udział\zło.txt`, data: "evil"}},
		"unc-slash":         {{name: "//serwer/udział/zło.txt", data: "evil"}},
		"long-prefix":       {{name: `\\?\C:\zło.txt`, data: "evil"}},
		"ads":               {{name: "plik.txt:ukryty", data: "evil"}},
		"ads-data":          {{name: "plik.txt::$DATA", data: "evil"}},
		"ads-dir":           {{name: "dir:x/plik.txt", data: "evil"}},
		"reserved":          {{name: "CON", data: "evil"}},
		"reserved-ext":      {{name: "dane/nul.txt", data: "evil"}},
		"reserved-multiext": {{name: "dane/Aux.tar.gz", data: "evil"}},
		"reserved-com":      {{name: "com1.dat", data: "evil"}},
		"reserved-space":    {{name: "dane/lpt9 .txt", data: "evil"}},
		"trailing-dot":      {{name: "dane/plik.", data: "evil"}},
		"trailing-dot-dir":  {{name: "dane./plik.txt", data: "evil"}},
		"trailing-space":    {{name: "dane /plik.txt", data: "evil"}},
		"control-char":      {{name: "pl\x01ik.txt", data: "evil"}},
		"symlink-file":      {{name: "link.txt", data: "../../../../Windows/win.ini", mode: fs.ModeSymlink | 0o777}},
		"symlink-then-file": {{name: "x", data: "..", mode: fs.ModeSymlink | 0o777}, {name: "x/zło.txt", data: "evil"}},
		"win-reparse":       {{name: "reparse.txt", data: "C:/", extAttr: 0x400, creator: 0}},
		"file-and-dir":      {{name: "a", data: "x"}, {name: "A/b.txt", data: "y"}},
	}
	for name, entries := range cases {
		z := qaRawZip(t, filepath.Join(w.base, "Pobrane mody ąę", "złośliwy "+name+".zip"), entries)
		row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z, Enable: true, AckExecutable: true})
		if err == nil {
			t.Errorf("%s: accepted (%d files)", name, row.Files)
			_ = w.svc.UninstallMod(in.ID, row.ID)
		}
	}
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("game changed:\n%s", diff)
	}
	// nothing new outside the launcher data and the downloads
	after := qaSnapshot(t, w.base)
	for k := range after {
		if _, ok := outside[k]; ok {
			continue
		}
		if strings.HasPrefix(k, "Pobrane mody ąę/") || strings.Contains(k, "/data/modmgr/") || strings.HasSuffix(k, "/data/") || strings.HasSuffix(k, "/data/modmgr/") {
			continue
		}
		t.Errorf("new file outside: %s", k)
	}
	if left := qaDirNames(t, w.storeDir(in.ID)); len(left) != 0 {
		t.Errorf("store leftovers: %v", left)
	}
	for _, p := range []string{filepath.Join(filepath.VolumeName(w.base)+`\`, "zło.txt"), filepath.Join(filepath.Dir(w.base), "zło.txt")} {
		if _, err := os.Stat(p); err == nil {
			t.Errorf("escaped to %s", p)
		}
	}
}

// A mod folder that contains a junction to a folder outside it must not
// pull in files from outside (they could be private files).
func TestQAFolderSourceJunctionNotFollowed(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("junctions are Windows-only")
	}
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra junction")
	secret := filepath.Join(w.base, "Prywatne ź")
	testkit.Write(t, secret, "hasła.txt", "tajne")
	src := filepath.Join(w.base, "Mod folder")
	testkit.Write(t, src, "ok.txt", "ok")
	if out, err := exec.Command("cmd", "/c", "mklink", "/J", filepath.Join(src, "skrót"), secret).CombinedOutput(); err != nil {
		t.Skipf("mklink /J: %v %s", err, out)
	}
	row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: src, Enable: true})
	w.must(err)
	if row.Files != 1 {
		t.Errorf("junction followed: %d files", row.Files)
	}
	filepath.WalkDir(game, func(p string, d fs.DirEntry, err error) error {
		if err == nil && d.Name() == "hasła.txt" {
			t.Errorf("private file deployed: %s", p)
		}
		return nil
	})
	if qaRead(filepath.Join(secret, "hasła.txt")) != "tajne" {
		t.Error("secret modified")
	}
}

// A junction inside the game folder (e.g. a "Data" folder moved to another
// drive) that a mod writes into: deployment must not write through it
// outside the game, or must at least restore everything on purge.
func TestQAGameFolderWithJunctionPurges(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("junctions are Windows-only")
	}
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra junction 2")
	elsewhere := filepath.Join(w.base, "Inny dysk", "Dane")
	testkit.Write(t, elsewhere, "orig.txt", "oryginał")
	if out, err := exec.Command("cmd", "/c", "mklink", "/J", filepath.Join(game, "Dane"), elsewhere).CombinedOutput(); err != nil {
		t.Skipf("mklink /J: %v %s", err, out)
	}
	vanG, vanE := qaSnapshot(t, game), qaSnapshot(t, elsewhere)
	_, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: w.zip("j.zip", map[string]string{"Dane/orig.txt": "mod", "Dane/nowy.txt": "n"}), Enable: true})
	t.Logf("import through junction: %v; elsewhere now %v", err, qaSnapshot(t, elsewhere))
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if d := qaDiffNoMtime(vanG, qaSnapshot(t, game)) + testkit.Diff(vanE, qaSnapshot(t, elsewhere)); d != "" {
		t.Errorf("not vanilla after purge:\n%s", d)
	}
}

// A mod file where the game has a folder (and vice versa) fails cleanly:
// nothing half-deployed, the manager keeps working.
func TestQAFileVersusFolderCollision(t *testing.T) {
	for name, files := range map[string]map[string]string{
		"file-over-dir": {"a.txt": "a", "vanilla": "file where a folder is"},
		"dir-over-file": {"a.txt": "a", "vanilla/readme.txt/x.txt": "folder where a file is"},
	} {
		t.Run(name, func(t *testing.T) {
			w := qaNew(t)
			game, in := w.game(gamedef.GenericID, "Gra kolizja "+name)
			vanilla := w.snap(game)
			_, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: w.zip(name+".zip", files), Enable: true})
			if err == nil {
				t.Fatal("deployed over a folder/file")
			}
			t.Logf("error: %v", err)
			if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
				t.Errorf("half deployed:\n%s", diff)
			}
			v, err := w.svc.GetView(in.ID)
			w.must(err)
			if v.Pending {
				t.Error("left a pending transaction")
			}
			_, err = w.svc.Purge(in.ID)
			w.must(err)
		})
	}
}

// A game file held open by another process (no FILE_SHARE_DELETE, like a
// running tool) during deployment: clean failure, rollback, retry works.
func TestQALockedGameFileRollsBack(t *testing.T) {
	w := qaNew(t)
	game, in := w.game(gamedef.GenericID, "Gra zablokowana")
	testkit.Write(t, game, "a/1.txt", "o1")
	testkit.Write(t, game, "z/2.txt", "o2")
	vanilla := w.snap(game)
	f, err := os.Open(filepath.Join(game, "z", "2.txt"))
	w.must(err)
	_, _, err = w.svc.Import(ImportIn{Install: in.ID, Path: w.zip("m.zip", map[string]string{"a/1.txt": "m1", "z/2.txt": "m2", "b/3.txt": "m3"}), Enable: true})
	if err == nil {
		t.Log("deploy succeeded although a file was open (Windows allowed it)")
	} else if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("failed deployment not rolled back:\n%s", diff)
	}
	f.Close()
	_, err = w.svc.Deploy(in.ID, false)
	w.must(err)
	if qaRead(filepath.Join(game, "z", "2.txt")) != "m2" {
		t.Error("retry did not deploy")
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if diff := testkit.Diff(vanilla, w.snap(game)); diff != "" {
		t.Errorf("not vanilla:\n%s", diff)
	}
}

// A mod that overwrites the game's exe needs consent; the consent request
// must reach the UI (Confirm == "protected") also when it comes from an
// automatic deployment after Import / SetEnabled.
func TestQAProtectedFileConsentReachesUI(t *testing.T) {
	// QA-BUG fixed (regression test): Confirm=protected lost when deployment is triggered by Import/SetEnabled (wrapped in uerr)
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim exe")
	exe := filepath.Join(game, "SkyrimSE.exe")
	orig := qaRead(exe)
	row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: w.zip("exe.zip", map[string]string{"SkyrimSE.exe": "podmieniony exe", "skse64_loader.exe": "loader"}), Enable: true, AckExecutable: true})
	var ue *UserError
	if !errors.As(err, &ue) || ue.Confirm != "protected" {
		t.Errorf("import of an exe-overwriting mod: want Confirm=protected, got %#v", err)
	}
	if qaRead(exe) != orig {
		t.Fatal("exe overwritten without consent")
	}
	if row == nil {
		return
	}
	if _, err := w.svc.Deploy(in.ID, true); err != nil {
		t.Fatal(err)
	}
	if qaRead(exe) != "podmieniony exe" {
		t.Error("consented deployment did not place the exe")
	}
	_, err = w.svc.Purge(in.ID)
	w.must(err)
	if qaRead(exe) != orig {
		t.Error("exe not restored")
	}
}

// Protected-path matching must ignore case (Windows): "SKYRIMSE.EXE" in a
// mod overwrites SkyrimSE.exe as well.
func TestQAProtectedFileCaseInsensitive(t *testing.T) {
	w := qaNew(t)
	game, in := w.game("skyrimse", "Skyrim EXE")
	exe := filepath.Join(game, "SkyrimSE.exe")
	orig := qaRead(exe)
	off := false
	w.must(w.svc.SetOptions(in.ID, SetInstallOptions{AutoDeploy: &off}))
	w.imp(in.ID, w.zip("exe2.zip", map[string]string{"SKYRIMSE.EXE": "podmieniony", "skse64_loader.exe": "loader"}), true)
	_, err := w.svc.Deploy(in.ID, false)
	var ue *UserError
	if !errors.As(err, &ue) || ue.Confirm != "protected" {
		t.Errorf("upper-case exe name bypassed the protection: err=%v exe=%q", err, qaRead(exe))
	}
	if qaRead(exe) != orig {
		t.Error("exe overwritten without consent")
		w.svc.Purge(in.ID)
	}
}
