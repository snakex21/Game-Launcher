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

// world is a temp launcher folder, fake user folders and fake games.
type world struct {
	t       *testing.T
	base    string
	app     string
	folders map[gamedef.RootKind]string
	svc     *Service
	running []string
}

func newWorld(t *testing.T) *world {
	t.Helper()
	base := filepath.Join(t.TempDir(), "Gry i mody Zażółć")
	w := &world{t: t, base: base, app: filepath.Join(base, "Launcher ąę")}
	w.folders = testkit.Folders(t, filepath.Join(base, "Użytkownik"))
	w.open()
	return w
}

func (w *world) open() {
	w.t.Helper()
	svc, err := New(w.app, Options{Folders: w.folders, Running: func() ([]string, error) { return w.running, nil }})
	if err != nil {
		w.t.Fatal(err)
	}
	w.svc = svc
}

func (w *world) game(defID string) (string, *Install) {
	w.t.Helper()
	d := w.svc.Defs().Get(defID)
	dir := filepath.Join(w.base, "Steam Library", "common", "Gra ąę "+defID)
	testkit.Game(w.t, d, dir)
	in, err := w.svc.AddInstall(AddInstallIn{DefID: defID, Path: dir})
	if err != nil {
		w.t.Fatal(err)
	}
	return dir, in
}

func (w *world) zip(name string, files map[string]string) string {
	return testkit.Zip(w.t, filepath.Join(w.base, "Pobrane mody", name), files)
}

func (w *world) importMod(inst, path string, enable bool) string {
	w.t.Helper()
	row, _, err := w.svc.Import(ImportIn{Install: inst, Path: path, Enable: enable, AckExecutable: true})
	if err != nil {
		w.t.Fatal(err)
	}
	return row.ID
}

func (w *world) snapshotAll(game string) map[string]string {
	out := map[string]string{}
	for k, v := range testkit.Snapshot(w.t, game) {
		out["game:"+k] = v
	}
	for kind, dir := range w.folders {
		for k, v := range testkit.Snapshot(w.t, dir) {
			out[string(kind)+":"+k] = v
		}
	}
	return out
}

func readOr(p string) string {
	b, err := os.ReadFile(p)
	if err != nil {
		return "<brak>"
	}
	return string(b)
}

// Every built-in game definition: install a generated mod, deploy, check
// the files land where the game expects them, purge back to vanilla.
func TestEveryDefinitionDeploysAndPurges(t *testing.T) {
	type expect struct {
		root gamedef.RootKind
		rel  string
	}
	cases := []struct {
		def     string
		source  string
		files   map[string]string
		setup   func(w *world, game string)
		want    []expect
		wantArg string
	}{
		{def: "skyrimse", source: "Cool-1.0.zip", files: map[string]string{"Data/Cool.esp": "esp", "Data/textures/a.dds": "tex"},
			want: []expect{{gamedef.RootGame, "Data/Cool.esp"}, {gamedef.RootGame, "Data/textures/a.dds"}, {gamedef.RootLocalAppData, "Skyrim Special Edition/plugins.txt"}}},
		{def: "fallout4", source: "f4.zip", files: map[string]string{"Data/Cool.esp": "esp", "Data/meshes/m.nif": "m"},
			want: []expect{{gamedef.RootGame, "Data/Cool.esp"}, {gamedef.RootLocalAppData, "Fallout4/plugins.txt"}}},
		{def: "falloutnv", source: "nv.zip", files: map[string]string{"Cool.esp": "esp", "textures/t.dds": "t"},
			want: []expect{{gamedef.RootGame, "Data/Cool.esp"}, {gamedef.RootLocalAppData, "FalloutNV/plugins.txt"}}},
		{def: "starfield", source: "sf.zip", files: map[string]string{"Data/Cool.esm": "esm", "Data/textures/a.dds": "tex"},
			want: []expect{{gamedef.RootGame, "Data/Cool.esm"}, {gamedef.RootDocuments, "My Games/Starfield/Data/textures/a.dds"}}},
		{def: "morrowind", source: "mw.zip", files: map[string]string{"Data Files/Cool.esp": "esp"},
			setup: func(w *world, g string) {
				testkit.Write(t, g, "Morrowind.ini", "[Game Files]\r\nGameFile0=Morrowind.esm\r\n")
			},
			want: []expect{{gamedef.RootGame, "Data Files/Cool.esp"}, {gamedef.RootGame, "Morrowind.ini"}}},
		{def: "valheim", source: "Author-Foo-1.0.0.zip", files: map[string]string{"manifest.json": `{"name":"Foo","version_number":"1.0.0"}`, "plugins/Foo.dll": "dll"},
			want: []expect{{gamedef.RootGame, "BepInEx/plugins/Author-Foo/Foo.dll"}}},
		{def: "minecraft-java", source: "sodium.zip", files: map[string]string{"sodium.jar": "jar"},
			want: []expect{{gamedef.RootInstance, "mods/sodium.jar"}}},
		{def: "stardewvalley", source: "sdv.zip", files: map[string]string{"ModA/manifest.json": "{}", "ModA/ModA.dll": "dll"},
			want: []expect{{gamedef.RootGame, "Mods/ModA/ModA.dll"}}},
		{def: "rimworld", source: "rw.zip", files: map[string]string{"MyMod/About/About.xml": "<ModMetaData><packageId>Me.MyMod</packageId></ModMetaData>", "MyMod/Defs/x.xml": "<Defs/>"},
			setup: func(w *world, g string) {
				testkit.Write(t, w.folders[gamedef.RootLocalLow], "Ludeon Studios/RimWorld by Ludeon Studios/Config/ModsConfig.xml",
					"<ModsConfigData>\n  <activeMods>\n    <li>ludeon.rimworld</li>\n  </activeMods>\n</ModsConfigData>\n")
			},
			want: []expect{{gamedef.RootGame, "Mods/MyMod/About/About.xml"}, {gamedef.RootLocalLow, "Ludeon Studios/RimWorld by Ludeon Studios/Config/ModsConfig.xml"}}},
		{def: "baldursgate3", source: "bg3.zip", files: map[string]string{"Mod.pak": "pak", "info.json": "{}"},
			want: []expect{{gamedef.RootLocalAppData, "Larian Studios/Baldur's Gate 3/Mods/Mod.pak"}}},
		{def: "cyberpunk2077", source: "cp.zip", files: map[string]string{"archive/pc/mod/a.archive": "a", "r6/scripts/x.reds": "r"},
			want: []expect{{gamedef.RootGame, "archive/pc/mod/a.archive"}, {gamedef.RootGame, "r6/scripts/x.reds"}, {gamedef.RootGame, "archive/pc/mod/modlist.txt"}}},
		{def: "witcher3", source: "w3.zip", files: map[string]string{"modFoo/content/blob0.bundle": "b"},
			want: []expect{{gamedef.RootGame, "Mods/modFoo/content/blob0.bundle"}, {gamedef.RootDocuments, "The Witcher 3/mods.settings"}}},
		{def: "doom-sourceport", source: "map.zip", files: map[string]string{"mymap.wad": "wad"}, wantArg: "mymap.wad"},
		{def: "halflife", source: "hl.zip", files: map[string]string{"mymod/liblist.gam": "game", "mymod/maps/a.bsp": "bsp"},
			want: []expect{{gamedef.RootGame, "mymod/liblist.gam"}}},
		{def: "gtasa", source: "car.zip", files: map[string]string{"MyCar/vehicle.dff": "dff", "MyCar/vehicle.txd": "txd"},
			want: []expect{{gamedef.RootGame, "modloader/MyCar/vehicle.dff"}}},
		{def: gamedef.GenericID, source: "Wrap.zip", files: map[string]string{"Wrap/a/b.txt": "b"},
			want: []expect{{gamedef.RootGame, "a/b.txt"}}},
	}
	w := newWorld(t)
	seen := map[string]bool{}
	for _, c := range cases {
		seen[c.def] = true
		game, in := w.game(c.def)
		if c.setup != nil {
			c.setup(w, game)
		}
		vanilla := w.snapshotAll(game)
		modID := w.importMod(in.ID, w.zip(c.def+"/"+c.source, c.files), true)
		v, err := w.svc.GetView(in.ID)
		if err != nil {
			t.Fatal(c.def, err)
		}
		if c.wantArg != "" {
			if !strings.Contains(strings.Join(v.LaunchArgs, " "), c.wantArg) || v.Deployed != 0 {
				t.Errorf("%s: launch args %v, deployed %d", c.def, v.LaunchArgs, v.Deployed)
			}
		}
		if !v.InSync {
			t.Errorf("%s: not in sync after import", c.def)
		}
		roots := map[gamedef.RootKind]string{gamedef.RootGame: game, gamedef.RootInstance: filepath.Join(w.app, "data", "modmgr", "instances", in.ID)}
		for k, p := range w.folders {
			roots[k] = p
		}
		for _, e := range c.want {
			p := filepath.Join(roots[e.root], filepath.FromSlash(e.rel))
			if _, err := os.Stat(p); err != nil {
				t.Errorf("%s: missing %s:%s (plan %+v)", c.def, e.root, e.rel, v.Mods)
			}
		}
		if vr, err := w.svc.Verify(in.ID); err != nil || len(vr.Drift) != 0 || len(vr.StoreIssues) != 0 {
			t.Errorf("%s: verify %+v %v", c.def, vr, err)
		}
		if _, err := w.svc.Purge(in.ID); err != nil {
			t.Fatal(c.def, err)
		}
		if diff := testkit.Diff(vanilla, w.snapshotAll(game)); diff != "" {
			t.Errorf("%s: not vanilla after purge:\n%s", c.def, diff)
		}
		// uninstall leaves the store clean too
		if err := w.svc.UninstallMod(in.ID, modID); err != nil {
			t.Fatal(c.def, err)
		}
		if err := w.svc.RemoveInstall(in.ID); err != nil {
			t.Fatal(c.def, err)
		}
	}
	for _, d := range w.svc.Defs().List() {
		if !seen[d.ID] {
			t.Errorf("definition %s has no deployment test", d.ID)
		}
	}
}

func TestConflictsOrderOverridesAndProfiles(t *testing.T) {
	w := newWorld(t)
	game, in := w.game("skyrimse")
	a := w.importMod(in.ID, w.zip("A.zip", map[string]string{"Data/textures/sky.dds": "A", "Data/A.esp": "a", "Data/same.txt": "same"}), true)
	b := w.importMod(in.ID, w.zip("B.zip", map[string]string{"Data/textures/sky.dds": "B", "Data/B.esp": "b", "Data/same.txt": "same"}), true)
	sky := filepath.Join(game, "Data", "textures", "sky.dds")
	if readOr(sky) != "B" {
		t.Fatal("later mod must win")
	}
	v, _ := w.svc.GetView(in.ID)
	if v.Mods[1].Conflicts.Wins != 1 || v.Mods[0].Conflicts.Loses != 1 || v.Mods[0].Conflicts.Identical != 1 {
		t.Fatalf("%+v", v.Mods)
	}
	plugins := readOr(filepath.Join(w.folders[gamedef.RootLocalAppData], "Skyrim Special Edition", "plugins.txt"))
	if plugins != "*A.esp\r\n*B.esp\r\n" {
		t.Fatalf("%q", plugins)
	}
	// move A to the top
	if _, err := w.svc.Move(in.ID, a, 1); err != nil {
		t.Fatal(err)
	}
	if readOr(sky) != "A" {
		t.Fatal("order change not deployed")
	}
	// rule: B wins this one file
	cs, _ := w.svc.Conflicts(in.ID)
	var key string
	for _, c := range cs {
		if strings.HasSuffix(c.Target, "sky.dds") {
			key = c.Key
		}
	}
	if _, err := w.svc.SetOverride(in.ID, key, b); err != nil {
		t.Fatal(err)
	}
	if readOr(sky) != "B" {
		t.Fatal("override not deployed")
	}
	files, _ := w.svc.ModFiles(in.ID, b)
	for _, f := range files {
		if strings.HasSuffix(f.Target, "sky.dds") && (f.State != "wins" || f.Rule != "override") {
			t.Fatalf("%+v", f)
		}
	}
	// a second profile with only A
	p2, err := w.svc.CreateProfile(in.ID, "Tylko A", "")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.svc.ActivateProfile(in.ID, p2.ID); err != nil {
		t.Fatal(err)
	}
	if readOr(sky) != "oryginał" && readOr(sky) != "<brak>" {
		t.Fatal("empty profile must purge", readOr(sky))
	}
	if _, err := w.svc.SetEnabled(in.ID, a, true, false); err != nil {
		t.Fatal(err)
	}
	if readOr(sky) != "A" || readOr(filepath.Join(game, "Data", "B.esp")) != "<brak>" {
		t.Fatal("profile 2 wrong")
	}
	// disable -> files go away
	if _, err := w.svc.SetEnabled(in.ID, a, false, false); err != nil {
		t.Fatal(err)
	}
	if readOr(sky) != "<brak>" {
		t.Fatal("disable did not remove")
	}
	if err := w.svc.DeleteProfile(in.ID, p2.ID); err == nil {
		t.Fatal("active profile deleted")
	}
}

func TestExecutableNeedsConsentAndDuplicates(t *testing.T) {
	w := newWorld(t)
	_, in := w.game("cyberpunk2077")
	z := w.zip("cet.zip", map[string]string{"bin/x64/plugins/cyber_engine_tweaks/mods/My/init.lua": "print(1)"})
	_, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z, Enable: true})
	var ue *UserError
	if !errors.As(err, &ue) || ue.Confirm != "executable" {
		t.Fatal("no consent asked", err)
	}
	// installed but disabled: no consent needed
	row, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.svc.SetEnabled(in.ID, row.ID, true, false); !errors.As(err, &ue) || ue.Confirm != "executable" {
		t.Fatal("enable without consent", err)
	}
	if _, err := w.svc.SetEnabled(in.ID, row.ID, true, true); err != nil {
		t.Fatal(err)
	}
	if _, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z}); !errors.As(err, &ue) || ue.Confirm != "duplicate" {
		t.Fatal("duplicate not detected", err)
	}
	if _, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z, AllowDuplicate: true}); err != nil {
		t.Fatal(err)
	}
}

func TestRunningGameBlocksDeployment(t *testing.T) {
	w := newWorld(t)
	game, in := w.game("skyrimse")
	w.running = []string{filepath.Join(game, "SkyrimSE.exe")}
	_, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: w.zip("a.zip", map[string]string{"Data/a.esp": "a"}), Enable: true})
	if err == nil || !strings.Contains(err.Error(), "uruchomiona") {
		t.Fatal(err)
	}
	if readOr(filepath.Join(game, "Data", "a.esp")) != "<brak>" {
		t.Fatal("deployed while running")
	}
	w.running = nil
	if _, err := w.svc.Deploy(in.ID, false); err != nil {
		t.Fatal(err)
	}
	if readOr(filepath.Join(game, "Data", "a.esp")) != "a" {
		t.Fatal("not deployed after the game closed")
	}
}

func TestReadOnlyOriginalAndSameFileFromTwoMods(t *testing.T) {
	w := newWorld(t)
	game, in := w.game(gamedef.GenericID)
	ro := testkit.Write(t, game, "config/game.ini", "oryginalny ini")
	os.Chmod(ro, 0o444)
	vanilla := w.snapshotAll(game)
	w.importMod(in.ID, w.zip("one.zip", map[string]string{"config/game.ini": "mod 1"}), true)
	w.importMod(in.ID, w.zip("two.zip", map[string]string{"config/game.ini": "mod 2"}), true)
	if readOr(ro) != "mod 2" {
		t.Fatal(readOr(ro))
	}
	if _, err := w.svc.Purge(in.ID); err != nil {
		t.Fatal(err)
	}
	if diff := testkit.Diff(vanilla, w.snapshotAll(game)); diff != "" {
		t.Fatal(diff)
	}
	st, _ := os.Stat(ro)
	if st.Mode().Perm()&0o200 != 0 {
		t.Fatal("read-only attribute not restored")
	}
}

func TestUninstallAfterGameUpdate(t *testing.T) {
	w := newWorld(t)
	game, in := w.game(gamedef.GenericID)
	testkit.Write(t, game, "data/level.pak", "v1 gry")
	id := w.importMod(in.ID, w.zip("m.zip", map[string]string{"data/level.pak": "mod", "data/extra.txt": "x"}), true)
	// the store "updates" the game: new file replaces the deployed one
	p := filepath.Join(game, "data", "level.pak")
	os.Chmod(p, 0o644)
	os.Remove(p)
	testkit.Write(t, game, "data/level.pak", "v2 gry")
	v, _ := w.svc.GetView(in.ID)
	if v.InSync && v.Deployed == 0 {
		t.Fatal("view")
	}
	if err := w.svc.UninstallMod(in.ID, id); err != nil {
		t.Fatal(err)
	}
	if readOr(p) != "v2 gry" || readOr(filepath.Join(game, "data", "extra.txt")) != "<brak>" {
		t.Fatal("uninstall after update broke the game", readOr(p))
	}
	if mods, _ := w.svc.store.List("generic-" + in.ID); len(mods) != 0 {
		t.Fatal("store not cleaned")
	}
}

func TestInterruptedImportIsCleanedUp(t *testing.T) {
	w := newWorld(t)
	_, in := w.game(gamedef.GenericID)
	tmp := filepath.Join(w.app, "data", "modmgr", "store", "generic-"+in.ID, ".tmp-01ARZ3NDEKTSV4RRFFQ69G5FAV")
	testkit.Write(t, tmp, "files/files/half.txt", "half")
	w.open()
	if _, err := os.Stat(tmp); err == nil {
		t.Fatal("leftover not removed")
	}
	if len(w.svc.Recovered) == 0 {
		t.Fatal("not reported")
	}
	v, _ := w.svc.GetView(in.ID)
	if len(v.Mods) != 0 {
		t.Fatal("half mod visible")
	}
}

func TestDriveLetterIndependentInstallPath(t *testing.T) {
	w := newWorld(t)
	game, in := w.game(gamedef.GenericID)
	if filepath.VolumeName(game) != "" && strings.Contains(in.Path, ":") {
		t.Fatalf("path on the launcher drive stored with a letter: %s", in.Path)
	}
}

func TestDoomLaunchCommand(t *testing.T) {
	w := newWorld(t)
	game, in := w.game("doom-sourceport")
	testkit.Write(t, game, "DOOM2.WAD", "iwad")
	iw := filepath.Join(game, "DOOM2.WAD")
	if err := w.svc.SetOptions(in.ID, SetInstallOptions{Iwad: &iw}); err != nil {
		t.Fatal(err)
	}
	w.importMod(in.ID, w.zip("Mapa z spacją.zip", map[string]string{"Mapa z spacją.wad": "wad"}), true)
	cmd, cwd, err := w.svc.LaunchCommand(in.ID, "")
	if err != nil {
		t.Fatal(err)
	}
	if cwd != game || !strings.HasSuffix(cmd[0], "gzdoom.exe") || cmd[1] != "-iwad" || cmd[2] != iw || cmd[3] != "-file" || !strings.HasSuffix(cmd[4], "Mapa z spacją.wad") {
		t.Fatal(cmd)
	}
}

func TestSuggestAndValidation(t *testing.T) {
	w := newWorld(t)
	d := w.svc.Defs().Get("cyberpunk2077")
	dir := filepath.Join(w.base, "CP")
	testkit.Game(t, d, dir)
	sug := w.svc.SuggestDefs(filepath.Join(dir, "bin", "x64", "Cyberpunk2077.exe"))
	if len(sug) == 0 || sug[0].DefID != "cyberpunk2077" || sug[0].Root != dir {
		t.Fatal(sug)
	}
	empty := filepath.Join(w.base, "pusty")
	os.MkdirAll(empty, 0o755)
	_, err := w.svc.AddInstall(AddInstallIn{DefID: "skyrimse", Path: empty})
	var ue *UserError
	if !errors.As(err, &ue) || ue.Confirm != "force" {
		t.Fatal(err)
	}
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: "skyrimse", Path: empty, Force: true}); err != nil {
		t.Fatal(err)
	}
	if _, err := w.svc.AddInstall(AddInstallIn{DefID: "skyrimse", Path: empty, Force: true}); err == nil {
		t.Fatal("same folder twice")
	}
}

func TestMaliciousArchiveLeavesNothing(t *testing.T) {
	w := newWorld(t)
	game, in := w.game(gamedef.GenericID)
	vanilla := w.snapshotAll(game)
	z := w.zip("evil.zip", map[string]string{"ok.txt": "ok", "../../../evil.txt": "evil"})
	if _, _, err := w.svc.Import(ImportIn{Install: in.ID, Path: z, Enable: true}); err == nil {
		t.Fatal("accepted")
	}
	if diff := testkit.Diff(vanilla, w.snapshotAll(game)); diff != "" {
		t.Fatal(diff)
	}
	if _, err := os.Stat(filepath.Join(w.base, "evil.txt")); err == nil {
		t.Fatal("escaped")
	}
}

// Configs (*.cfg, *.ini, *.json...) are deployed as writable copies: the
// game may rewrite them; the edit is kept while the same mod stays deployed,
// it is not reported as drift, and purge still returns to vanilla.
func TestEditedConfigIsKeptAndPurged(t *testing.T) {
	w := newWorld(t)
	game, in := w.game(gamedef.GenericID)
	vanilla := w.snapshotAll(game)
	w.importMod(in.ID, w.zip("cfg.zip", map[string]string{"BepInEx/config/mod.cfg": "volume=1", "BepInEx/plugins/mod.dll": "dll"}), true)
	cfg := filepath.Join(game, "BepInEx", "config", "mod.cfg")
	if st, err := os.Stat(cfg); err != nil || st.Mode().Perm()&0o200 == 0 {
		t.Fatal("config not deployed as a writable file", err)
	}
	if err := os.WriteFile(cfg, []byte("volume=7 (zapisane przez grę)"), 0o644); err != nil {
		t.Fatal(err)
	}
	vr, err := w.svc.Verify(in.ID)
	if err != nil || len(vr.Drift) != 0 || len(vr.StoreIssues) != 0 {
		t.Fatalf("edited config reported: %+v %v", vr, err)
	}
	if _, err := w.svc.Deploy(in.ID, false); err != nil {
		t.Fatal(err)
	}
	if readOr(cfg) != "volume=7 (zapisane przez grę)" {
		t.Fatal("redeploy overwrote the game's edit:", readOr(cfg))
	}
	if v, _ := w.svc.GetView(in.ID); !v.InSync {
		t.Fatal("edited config makes the profile look out of date")
	}
	if _, err := w.svc.Purge(in.ID); err != nil {
		t.Fatal(err)
	}
	if diff := testkit.Diff(vanilla, w.snapshotAll(game)); diff != "" {
		t.Fatal(diff)
	}
}
