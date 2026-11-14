package relpath

import "testing"

func TestClean(t *testing.T) {
	ok := map[string]string{
		"a/b.txt":              "a/b.txt",
		`Data\Textures\x.dds`:  "Data/Textures/x.dds",
		"./a/./b":              "a/b",
		"dir/":                 "dir",
		"Zażółć gęślą/ą ę.esp": "Zażółć gęślą/ą ę.esp",
		"con.d/x":              "con.d/x", // "con.d" base is "con" -> rejected? see below
	}
	delete(ok, "con.d/x")
	for in, want := range ok {
		got, err := Clean(in)
		if err != nil || got != want {
			t.Errorf("%q -> %q, %v", in, got, err)
		}
	}
	for _, bad := range []string{"", "/abs", `\\server\share\x`, `\\?\C:\x`, "C:x", "C:/x", "../x", "a/../../x", "a//b",
		"a:b", "NUL", "aux.txt", "com1.ini", "LPT9", "x.", "x ", "a/b./c", "a\x00b", "a|b", "a*b", "a?b", `a"b`, "<x>"} {
		if _, err := Clean(bad); err == nil {
			t.Errorf("%q accepted", bad)
		}
	}
}

func TestMatch(t *testing.T) {
	cases := []struct {
		pat, rel string
		want     bool
	}{
		{"*.esp", "Data/x.ESP", true},
		{"*.esp", "x.esm", false},
		{"fomod/**", "FOMOD/ModuleConfig.xml", true},
		{"fomod/**", "fomod", true},
		{"red4ext/plugins/**/*.dll", "red4ext/plugins/a/b/x.dll", true},
		{"red4ext/plugins/**/*.dll", "red4ext/plugins/x.dll", true},
		{"red4ext/plugins/**/*.dll", "red4ext/x.dll", false},
		{"SKSE/Plugins/*.dll", "skse/plugins/a.dll", true},
		{"SKSE/Plugins/*.dll", "skse/plugins/sub/a.dll", false},
		{"readme*", "README.md", true},
		{"1.*", "1.5", true},
		{"[x]*", "[x]file", true},
		{"a?c", "abc", true},
		{"**/init.lua", "init.lua", true},
	}
	for _, c := range cases {
		if got := Match(c.pat, c.rel); got != c.want {
			t.Errorf("Match(%q,%q)=%v", c.pat, c.rel, got)
		}
	}
}

func FuzzClean(f *testing.F) {
	for _, s := range []string{"a/b", "../x", "C:/x", "a:b", "con"} {
		f.Add(s)
	}
	f.Fuzz(func(t *testing.T, s string) {
		c, err := Clean(s)
		if err != nil {
			return
		}
		again, err := Clean(c)
		if err != nil || again != c {
			t.Fatalf("not idempotent: %q -> %q -> %q (%v)", s, c, again, err)
		}
		for _, seg := range splitSegs(c) {
			if seg == ".." || seg == "." || seg == "" {
				t.Fatalf("unsafe segment in %q", c)
			}
		}
	})
}

func splitSegs(s string) []string {
	var out []string
	cur := ""
	for _, r := range s {
		if r == '/' {
			out = append(out, cur)
			cur = ""
			continue
		}
		cur += string(r)
	}
	return append(out, cur)
}
