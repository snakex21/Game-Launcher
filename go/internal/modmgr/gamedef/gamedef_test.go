package gamedef

import (
	"os"
	"path/filepath"
	"testing"
)

func TestBuiltinDefinitionsLoad(t *testing.T) {
	set, err := Load("")
	if err != nil {
		t.Fatal(err)
	}
	if len(set.Problems) > 0 {
		t.Fatal(set.Problems)
	}
	want := []string{"skyrimse", "fallout4", "falloutnv", "starfield", "morrowind", "valheim", "minecraft-java",
		"stardewvalley", "rimworld", "baldursgate3", "cyberpunk2077", "witcher3", "doom-sourceport", "halflife", "gtasa",
		GenericID, "template.bethesda", "template.bepinex"}
	for _, id := range want {
		if set.Get(id) == nil {
			t.Errorf("missing %s", id)
		}
	}
	if n := len(set.List()); n != 16 {
		t.Errorf("List() = %d definitions, want 15 games + generic", n)
	}
	for _, d := range set.List() {
		if d.DefaultModType() == nil {
			t.Errorf("%s: no default mod type", d.ID)
		}
	}
}

func TestExtendsMerge(t *testing.T) {
	set, err := Load("")
	if err != nil {
		t.Fatal(err)
	}
	sk := set.Get("skyrimse")
	if sk.Abstract {
		t.Fatal("abstract inherited")
	}
	if sk.ModType("data") == nil || sk.ModType("script-extender") == nil {
		t.Fatal("mod types not inherited")
	}
	if sk.LoadOrder.Format != "asterisk" || len(sk.LoadOrder.ImplicitPlugins) != 5 {
		t.Fatalf("loadOrder merge: %+v", sk.LoadOrder)
	}
	if sk.Installer.MaxRootSearchDepth != 3 {
		t.Fatal("installer not inherited")
	}
	mw := set.Get("morrowind")
	if mw.Paths["data"] != "{game}/Data Files" {
		t.Fatal("paths override", mw.Paths)
	}
	if len(mw.ModTypes) != 2 {
		t.Fatal("arrays must be replaced, not merged")
	}
}

func TestResolveTemplates(t *testing.T) {
	set, _ := Load("")
	r := &Resolver{Def: set.Get("skyrimse"), Store: "gog", Roots: map[RootKind]string{RootGame: `C:\G`, RootLocalAppData: `C:\L`}}
	l, err := r.Location(r.Def.LoadOrder.File)
	if err != nil {
		t.Fatal(err)
	}
	if l.Root != RootLocalAppData || l.Rel != "Skyrim Special Edition GOG/plugins.txt" {
		t.Fatalf("%+v", l)
	}
	if _, err := r.Location("C:/Windows/x"); err == nil {
		t.Fatal("absolute template accepted")
	}
	if _, err := r.Location("{game}/../x"); err == nil {
		t.Fatal(".. accepted")
	}
	if _, err := r.Location("{windows}/x"); err == nil {
		t.Fatal("unknown root accepted")
	}
	abs, err := r.AbsTemplate("{paths.data}/textures")
	if err != nil || abs != `C:\G\Data\textures` {
		t.Fatal(abs, err)
	}
	if _, err := r.AbsTemplate("{myGames}/x"); err == nil {
		t.Fatal("unknown root on this machine must fail")
	}
}

func TestUserDefinitionOverridesAndProblems(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "mine.json"), []byte(`{"schemaVersion":1,"id":"mygame","name":"Moja gra","extends":"template.generic","detection":{"requiredFiles":["a.exe"]}}`), 0o644)
	os.WriteFile(filepath.Join(dir, "bad.json"), []byte(`{"schemaVersion":1,"id":"bad","name":"x","modTypes":[{"id":"a","target":"C:/Windows"}],"deployment":{"strategies":["copy"]},"loadOrder":{"kind":"none"},"detection":{}}`), 0o644)
	os.WriteFile(filepath.Join(dir, "broken.json"), []byte(`{`), 0o644)
	set, err := Load(dir)
	if err != nil {
		t.Fatal(err)
	}
	if d := set.Get("mygame"); d == nil || d.Builtin || d.ModType("files") == nil {
		t.Fatal("user definition not loaded")
	}
	if len(set.Problems) != 2 {
		t.Fatal(set.Problems)
	}
}
