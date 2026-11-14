package ojson

import (
	"os"
	"path/filepath"
	"testing"
)

// Written by Python: json.dumps(data, indent=4, ensure_ascii=False)
const pythonDump = `{
    "version": "1.5.0",
    "games": {
        "Wiedźmin 3": {
            "exe_path": "\\Gry\\Wiedźmin 3\\bin\\x64\\witcher3.exe",
            "play_time": 1157.0904660224915,
            "completion": 50,
            "last_played": 1745925721.6030233,
            "rating": null,
            "genres": [],
            "tags": [
                "RPG",
                "\"cytat\" i \\ backslash",
                "tab\tnowa\nlinia\u0001"
            ],
            "play_sessions": [
                {
                    "start": 1745920000.0,
                    "end": 1745921157.0904
                }
            ],
            "requirements_pc": {},
            "html": "<b>&amp;</b>   emoji 🎮"
        }
    },
    "settings": {
        "theme": "dark",
        "big": 1e+16,
        "small": 1e-05,
        "neg": -0.5
    },
    "empty_list": [],
    "flag": true
}`

func TestPythonRoundTripIsByteIdentical(t *testing.T) {
	v, err := Decode([]byte(pythonDump))
	if err != nil {
		t.Fatal(err)
	}
	if got := string(MarshalPython(v)); got != pythonDump {
		t.Fatalf("round trip differs:\n%s", got)
	}
}

func TestKeyOrderAndAppend(t *testing.T) {
	o, err := DecodeObject([]byte(`{"b":1,"a":2}`))
	if err != nil {
		t.Fatal(err)
	}
	o.Set("c", 3)
	o.Set("b", 9) // existing key keeps its position
	if got := string(MarshalCompact(o)); got != `{"b":9,"a":2,"c":3}` {
		t.Fatal(got)
	}
	o.Delete("a")
	if err := o.Rename("b", "z"); err != nil {
		t.Fatal(err)
	}
	if got := string(MarshalCompact(o)); got != `{"z":9,"c":3}` {
		t.Fatal(got)
	}
	if o.SetDefault("c", 5) != Int(3) {
		t.Fatal("SetDefault overwrote")
	}
}

func TestPyFloat(t *testing.T) {
	cases := map[float64]string{
		0:                  "0.0",
		1:                  "1.0",
		1157.0904660224915: "1157.0904660224915",
		1234567:            "1234567.0",
		1e16:               "1e+16",
		1.5e-5:             "1.5e-05",
		0.0001:             "0.0001",
		-2.5:               "-2.5",
		1e22:               "1e+22",
		123456789012345678: "1.2345678901234568e+17",
	}
	for f, want := range cases {
		if got := PyFloat(f); got != want {
			t.Errorf("PyFloat(%v) = %q, want %q", f, got, want)
		}
	}
}

func TestDecodeErrors(t *testing.T) {
	for _, bad := range []string{``, `{`, `{"a":1} x`, `[1,]`} {
		if _, err := Decode([]byte(bad)); err == nil {
			t.Errorf("Decode(%q) succeeded", bad)
		}
	}
	if _, err := DecodeObject([]byte(`[1]`)); err == nil {
		t.Error("array accepted as object")
	}
	// BOM is tolerated
	if _, err := DecodeObject([]byte("\xEF\xBB\xBF{}")); err != nil {
		t.Error(err)
	}
}

// Optional: the user's real config.json (a COPY - set GL_TEST_USERDATA to
// the copied launcher folder). Python wrote it, so the round trip must be
// byte-identical.
func TestUserConfigCopyRoundTrip(t *testing.T) {
	dir := os.Getenv("GL_TEST_USERDATA")
	if dir == "" {
		t.Skip("GL_TEST_USERDATA not set")
	}
	for _, name := range []string{"config.json", "local_settings.json"} {
		raw, err := os.ReadFile(filepath.Join(dir, "data", "config", name))
		if err != nil {
			t.Fatal(err)
		}
		v, err := Decode(raw)
		if err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		if string(DetectStyle(raw).Apply(MarshalPython(v))) != string(raw) {
			t.Errorf("%s: round trip is not byte-identical", name)
		}
	}
}
