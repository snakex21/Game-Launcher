package loadorder

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

func setup(t *testing.T, id string) (*gamedef.Definition, *gamedef.Resolver) {
	t.Helper()
	set, err := gamedef.Load("")
	if err != nil {
		t.Fatal(err)
	}
	d := set.Get(id)
	r := &gamedef.Resolver{Def: d, Roots: map[gamedef.RootKind]string{gamedef.RootGame: "G", gamedef.RootLocalAppData: "L", gamedef.RootDocuments: "D", gamedef.RootLocalLow: "LL"}}
	return d, r
}

func placed(root gamedef.RootKind, rels ...string) []Placed {
	var out []Placed
	for i, r := range rels {
		out = append(out, Placed{Target: gamedef.Location{Root: root, Rel: r}, ModIndex: i, ModID: "m"})
	}
	return out
}

func TestSkyrimAsterisk(t *testing.T) {
	d, r := setup(t, "skyrimse")
	in := Input{Def: d, Res: r, Files: placed(gamedef.RootGame, "Data/B.esp", "Data/A.esm", "Data/textures/x.dds", "Data/Skyrim.esm"),
		ListDir:  func(gamedef.Location) ([]string, error) { return []string{"Skyrim.esm", "Hand.esp", "B.esp"}, nil },
		ReadFile: func(gamedef.Location) ([]byte, error) { return []byte("ccBGSSSE001-Fish.esm\r\n"), nil }}
	out, err := Build(in)
	if err != nil {
		t.Fatal(err)
	}
	if len(out.Files) != 1 || out.Files[0].Target.Rel != "Skyrim Special Edition/plugins.txt" {
		t.Fatal(out.Files)
	}
	if got := string(out.Files[0].Content); got != "*A.esm\r\n*Hand.esp\r\n*B.esp\r\n" {
		t.Fatalf("%q", got)
	}
	if !out.Plugins[5].Implicit || out.Plugins[5].Name != "ccBGSSSE001-Fish.esm" {
		t.Fatal(out.Plugins)
	}
	// own order + disabled plugin
	in.Order = []Plugin{{Name: "B.esp", Enabled: false}, {Name: "Hand.esp", Enabled: true}}
	out, _ = Build(in)
	if got := string(out.Files[0].Content); got != "*A.esm\r\nB.esp\r\n*Hand.esp\r\n" {
		t.Fatalf("%q", got)
	}
}

func TestCP1252(t *testing.T) {
	b, err := encode("Café.esp", "windows-1252")
	if err != nil || len(b) != 8 || b[3] != 0xE9 {
		t.Fatal(b, err)
	}
	if _, err := encode("Zażółć.esp", "windows-1252"); err == nil {
		t.Fatal("unencodable name accepted")
	}
}

func TestMorrowindIni(t *testing.T) {
	d, r := setup(t, "morrowind")
	ini := "[General]\r\nx=1\r\n[Game Files]\r\nGameFile0=Morrowind.esm\r\nGameFile1=Old.esp\r\n[Archives]\r\nArchive 0=Tribunal.bsa\r\n"
	in := Input{Def: d, Res: r, Files: placed(gamedef.RootGame, "Data Files/New.esp"),
		ListDir:  func(gamedef.Location) ([]string, error) { return []string{"Morrowind.esm", "New.esp"}, nil },
		ReadFile: func(gamedef.Location) ([]byte, error) { return []byte(ini), nil }}
	out, err := Build(in)
	if err != nil {
		t.Fatal(err)
	}
	want := "[General]\r\nx=1\r\n[Game Files]\r\nGameFile0=Morrowind.esm\r\nGameFile1=New.esp\r\n[Archives]\r\nArchive 0=Tribunal.bsa\r\n"
	if got := string(out.Files[0].Content); got != want {
		t.Fatalf("%q", got)
	}
	if len(out.MTimes) != 1 {
		t.Fatal("timestamps not set", out.MTimes)
	}
}

func TestCyberpunkModlist(t *testing.T) {
	d, r := setup(t, "cyberpunk2077")
	out, err := Build(Input{Def: d, Res: r, Files: placed(gamedef.RootGame, "archive/pc/mod/a.archive", "archive/pc/mod/b.archive", "r6/x.reds")})
	if err != nil {
		t.Fatal(err)
	}
	if got := string(out.Files[0].Content); got != "b.archive\na.archive\n" {
		t.Fatalf("%q", got)
	}
}

func TestWitcherSettings(t *testing.T) {
	d, r := setup(t, "witcher3")
	cur := "[modOther]\r\nEnabled=0\r\nPriority=5\r\n[modA]\r\nEnabled=0\r\nPriority=9\r\n"
	out, err := Build(Input{Def: d, Res: r, Files: placed(gamedef.RootGame, "Mods/modA/content/x", "Mods/modB/content/y"),
		ReadFile: func(gamedef.Location) ([]byte, error) { return []byte(cur), nil }})
	if err != nil {
		t.Fatal(err)
	}
	got := string(out.Files[0].Content)
	if !strings.HasPrefix(got, "[modB]\r\nEnabled=1\r\nPriority=0\r\n\r\n[modA]\r\nEnabled=1\r\nPriority=1\r\n") || !strings.Contains(got, "[modOther]\r\nEnabled=0\r\nPriority=5") || strings.Contains(got, "Priority=9") {
		t.Fatalf("%q", got)
	}
}

func TestRimWorldKeepsUnknownXML(t *testing.T) {
	d, r := setup(t, "rimworld")
	dir := t.TempDir()
	about := filepath.Join(dir, "About.xml")
	os.WriteFile(about, []byte("<ModMetaData><packageId>Author.Cool</packageId></ModMetaData>"), 0o644)
	cur := "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<ModsConfigData>\n  <version>1.5</version>\n  <activeMods>\n    <li>ludeon.rimworld</li>\n    <li>author.cool</li>\n  </activeMods>\n  <knownExpansions><li>x</li></knownExpansions>\n  <future>keep</future>\n</ModsConfigData>\n"
	f := []Placed{{Target: gamedef.Location{Root: gamedef.RootGame, Rel: "Mods/Cool/About/About.xml"}, SourceAbs: about}}
	out, err := Build(Input{Def: d, Res: r, Files: f, ReadFile: func(gamedef.Location) ([]byte, error) { return []byte(cur), nil }})
	if err != nil {
		t.Fatal(err)
	}
	want := "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<ModsConfigData>\n  <version>1.5</version>\n  <activeMods>\n    <li>ludeon.rimworld</li>\n    <li>author.cool</li>\n  </activeMods>\n  <knownExpansions><li>x</li></knownExpansions>\n  <future>keep</future>\n</ModsConfigData>\n"
	if got := string(out.Files[0].Content); got != want {
		t.Fatalf("%q", got)
	}
}

func TestDoomArgs(t *testing.T) {
	d, _ := setup(t, "doom-sourceport")
	files := []Placed{
		{Target: gamedef.Location{Root: gamedef.RootModsStaging, Rel: "a.wad"}, SourceAbs: `E:\Mody\Mój mod\a.wad`},
		{Target: gamedef.Location{Root: gamedef.RootModsStaging, Rel: "b.pk3"}, SourceAbs: `E:\b.pk3`},
		{Target: gamedef.Location{Root: gamedef.RootModsStaging, Rel: "readme.txt"}, SourceAbs: `E:\readme.txt`},
	}
	got := strings.Join(LaunchArgs(d, files, `C:\DOOM2.WAD`), "|")
	if got != `-iwad|C:\DOOM2.WAD|-file|E:\Mody\Mój mod\a.wad|E:\b.pk3` {
		t.Fatal(got)
	}
	if got := strings.Join(LaunchArgs(d, nil, ""), "|"); got != "" {
		t.Fatal(got)
	}
}
