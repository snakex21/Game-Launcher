package install

import (
	"errors"
	"sort"
	"strings"
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/archive"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

func defs(t *testing.T) *gamedef.Set {
	t.Helper()
	s, err := gamedef.Load("")
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func entries(paths ...string) []archive.Entry {
	var out []archive.Entry
	for _, p := range paths {
		out = append(out, archive.Entry{Path: p, Size: 1})
	}
	return out
}

func got(p *Plan) []string {
	var out []string
	for _, f := range p.Files {
		out = append(out, f.ModType+":"+f.Rel)
	}
	sort.Strings(out)
	return out
}

func TestLayouts(t *testing.T) {
	set := defs(t)
	cases := []struct {
		game, source string
		files        []string
		manifest     string
		want         []string
	}{
		{"skyrimse", "Cool Mod-123-1-0.7z", []string{"Data/textures/a.dds", "Data/Cool.esp", "readme.txt"},
			"", []string{"data:Cool.esp", "data:textures/a.dds"}},
		{"skyrimse", "x.zip", []string{"Cool-1.0/meshes/x.nif", "Cool-1.0/Cool.esp"},
			"", []string{"data:Cool.esp", "data:meshes/x.nif"}},
		{"skyrimse", "skse.7z", []string{"skse64_1_6/skse64_loader.exe", "skse64_1_6/skse64_1_6_1170.dll", "skse64_1_6/Data/Scripts/a.pex"},
			"", []string{"script-extender:Data/Scripts/a.pex", "script-extender:skse64_1_6_1170.dll", "script-extender:skse64_loader.exe"}},
		{"morrowind", "m.zip", []string{"Data Files/x.esp", "Data Files/textures/t.dds"},
			"", []string{"data:textures/t.dds", "data:x.esp"}},
		{"cyberpunk2077", "c.zip", []string{"archive/pc/mod/a.archive", "r6/scripts/x/a.reds"},
			"", []string{"root:archive/pc/mod/a.archive", "root:r6/scripts/x/a.reds"}},
		{"cyberpunk2077", "c.zip", []string{"a.archive", "b.xl"},
			"", []string{"archive:a.archive", "archive:b.xl"}},
		{"cyberpunk2077", "cet.zip", []string{"bin/x64/plugins/cyber_engine_tweaks/mods/My/init.lua"},
			"", []string{"root:bin/x64/plugins/cyber_engine_tweaks/mods/My/init.lua"}},
		{"valheim", "Author-Foo-1.2.3.zip", []string{"manifest.json", "icon.png", "README.md", "plugins/Foo.dll", "config/foo.cfg"},
			`{"name":"Foo","version_number":"1.2.3"}`, []string{"bepinex-config:foo.cfg", "bepinex-plugin:Author-Foo/Foo.dll"}},
		{"valheim", "denikson-BepInExPack_Valheim-5.4.zip", []string{"manifest.json", "BepInExPack_Valheim/winhttp.dll", "BepInExPack_Valheim/BepInEx/core/BepInEx.dll"},
			`{"name":"BepInExPack_Valheim"}`, []string{"bepinex-pack:BepInEx/core/BepInEx.dll", "bepinex-pack:winhttp.dll"}},
		{"stardewvalley", "pack.zip", []string{"ModA/manifest.json", "ModA/a.dll", "ModB/manifest.json", "ModB/assets/x.png"},
			"", []string{"smapi-mod:ModA/a.dll", "smapi-mod:ModA/manifest.json", "smapi-mod:ModB/assets/x.png", "smapi-mod:ModB/manifest.json"}},
		{"witcher3", "w.zip", []string{"modFoo/content/blob0.bundle"},
			"", []string{"mod:modFoo/content/blob0.bundle"}},
		{"witcher3", "w.zip", []string{"Mods/modFoo/content/blob0.bundle"},
			"", []string{"mod:modFoo/content/blob0.bundle"}},
		{"witcher3", "w.zip", []string{"Foo/content/blob0.bundle"},
			"", []string{"mod:modFoo/content/blob0.bundle"}},
		{"doom-sourceport", "map.zip", []string{"mymap.wad", "mymap.txt"},
			"", []string{"wad:mymap.txt", "wad:mymap.wad"}},
		{"doom-sourceport", "x.pk3", []string{"x.pk3"},
			"", []string{"wad:x.pk3"}},
		{"gtasa", "car.zip", []string{"MyCar/vehicle.dff", "MyCar/vehicle.txd"},
			"", []string{"modloader:MyCar/vehicle.dff", "modloader:MyCar/vehicle.txd"}},
		{"gtasa", "asi.zip", []string{"plugin.asi", "plugin.ini"},
			"", []string{"asi:plugin.asi", "asi:plugin.ini"}},
		{"rimworld", "r.zip", []string{"MyMod/About/About.xml", "MyMod/Defs/x.xml"},
			"", []string{"rimworld-mod:MyMod/About/About.xml", "rimworld-mod:MyMod/Defs/x.xml"}},
		{"baldursgate3", "b.zip", []string{"Mod.pak", "info.json"},
			"", []string{"pak:Mod.pak"}},
		{"halflife", "h.zip", []string{"mymod/liblist.gam", "mymod/dlls/x.dll"},
			"", []string{"gamedir:mymod/dlls/x.dll", "gamedir:mymod/liblist.gam"}},
		{"minecraft-java", "sodium.jar", []string{"sodium.jar"},
			"", []string{"mod:sodium.jar"}},
		{gamedef.GenericID, "Wrap.zip", []string{"Wrap/a/b.txt", "Wrap/c.dat"},
			"", []string{"files:a/b.txt", "files:c.dat"}},
	}
	for _, c := range cases {
		def := set.Get(c.game)
		opt := Options{SourceName: c.source}
		if c.manifest != "" {
			m := c.manifest
			opt.Read = func(string) ([]byte, error) { return []byte(m), nil }
		}
		p, err := Make(entries(c.files...), def, opt)
		if err != nil {
			t.Errorf("%s %v: %v", c.game, c.files, err)
			continue
		}
		g := got(p)
		if strings.Join(g, "|") != strings.Join(c.want, "|") {
			t.Errorf("%s %v:\n got  %v\n want %v\n candidates %+v", c.game, c.files, g, c.want, p.Candidates)
		}
	}
}

func TestManualOverride(t *testing.T) {
	def := defs(t).Get("skyrimse")
	p, err := Make(entries("Variant A/x.esp", "Variant B/y.esp"), def, Options{Root: "Variant B", ModType: "data"})
	if err != nil {
		t.Fatal(err)
	}
	if g := got(p); len(g) != 1 || g[0] != "data:y.esp" || p.Format != "manual" {
		t.Fatal(g)
	}
	if _, err := Make(entries("a.esp"), def, Options{Root: "nope"}); err == nil {
		t.Fatal("missing root accepted")
	}
}

func TestFlagsAndWarnings(t *testing.T) {
	def := defs(t).Get("skyrimse")
	p, err := Make(entries("fomod/ModuleConfig.xml", "Data/x.esp", "Data/SKSE/Plugins/a.dll", "setup.exe"), def, Options{})
	if err != nil {
		t.Fatal(err)
	}
	if !p.HasFomod || !p.ExecutableContent || !p.HasInstaller || len(p.Warnings) < 2 {
		t.Fatalf("%+v", p)
	}
	if _, err := Make(entries("readme.txt"), def, Options{}); err == nil {
		t.Fatal("empty mod accepted")
	}
}

func TestPolishAndSpacesInNames(t *testing.T) {
	def := defs(t).Get(gamedef.GenericID)
	p, err := Make(entries("Zażółć gęślą/Pliki z spacją/ąę.txt"), def, Options{SourceName: `C:\Mody\Zażółć gęślą 1.2.zip`})
	if err != nil {
		t.Fatal(err)
	}
	if p.ModName != "Zażółć gęślą" {
		t.Fatal(p.ModName)
	}
	if g := got(p); len(g) != 1 || g[0] != "files:Pliki z spacją/ąę.txt" {
		t.Fatal(g)
	}
}

func TestNameFromSource(t *testing.T) {
	for in, want := range map[string]string{
		"SkyUI_5_2_SE-12604-5-2SE.7z": "SkyUI_5_2_SE-12604-5-2SE",
		"Cool Mod v1.2.3.zip":         "Cool Mod",
		`C:\a\b\mod-1.0.zip`:          "mod",
		".zip":                        "Mod",
	} {
		if g := nameFromSource(in); g != want {
			t.Errorf("%q -> %q, want %q", in, g, want)
		}
	}
	_ = errors.New
}
