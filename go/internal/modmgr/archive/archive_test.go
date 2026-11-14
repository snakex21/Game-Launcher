package archive

import (
	"archive/zip"
	"bytes"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeZip(t *testing.T, path string, entries []zipEntry) string {
	t.Helper()
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	w := zip.NewWriter(f)
	for _, e := range entries {
		h := &zip.FileHeader{Name: e.name, Method: zip.Deflate}
		if e.mode != 0 {
			h.SetMode(e.mode)
		}
		zw, err := w.CreateHeader(h)
		if err != nil {
			t.Fatal(err)
		}
		zw.Write([]byte(e.data))
	}
	w.Close()
	f.Close()
	return path
}

type zipEntry struct {
	name string
	data string
	mode fs.FileMode
}

func TestMaliciousZipsRejected(t *testing.T) {
	dir := t.TempDir()
	cases := map[string][]zipEntry{
		"traversal":           {{name: "../../evil.txt", data: "x"}},
		"traversal-backslash": {{name: `ok\..\..\evil.txt`, data: "x"}},
		"absolute":            {{name: "/etc/evil", data: "x"}},
		"drive":               {{name: "C:/Windows/evil.dll", data: "x"}},
		"ads":                 {{name: "file.txt:stream", data: "x"}},
		"reserved":            {{name: "data/CON.txt", data: "x"}},
		"trailing":            {{name: "data/name. ", data: "x"}},
		"symlink":             {{name: "link", data: "/etc/passwd", mode: fs.ModeSymlink | 0o777}},
		"file-dir":            {{name: "a", data: "x"}, {name: "a/b", data: "y"}},
	}
	for name, entries := range cases {
		p := writeZip(t, filepath.Join(dir, name+".zip"), entries)
		src, err := Open(p)
		if err == nil {
			src.Close()
			t.Errorf("%s: accepted", name)
		}
	}
	// nothing was written next to the temp dir
	if _, err := os.Stat(filepath.Join(filepath.Dir(dir), "evil.txt")); err == nil {
		t.Fatal("file written outside")
	}
}

func TestExtractLimits(t *testing.T) {
	dir := t.TempDir()
	big := strings.Repeat("A", 1<<20) // compresses ~1000:1
	p := writeZip(t, filepath.Join(dir, "bomb.zip"), []zipEntry{{name: "big.bin", data: big}})
	src, err := Open(p)
	if err != nil {
		t.Fatal(err)
	}
	defer src.Close()
	out := filepath.Join(dir, "out")
	os.MkdirAll(out, 0o755)
	lim := DefaultLimits
	lim.RatioMinSize = 1 << 10
	_, err = Extract(src, []Job{{Entry: src.Entries()[0], Dest: "big.bin"}}, out, lim, nil)
	if !errors.Is(err, ErrLimit) {
		t.Fatal("ratio limit not enforced:", err)
	}
	if _, err := os.Stat(filepath.Join(out, "big.bin")); err == nil {
		t.Fatal("partial file left")
	}
	lim = DefaultLimits
	lim.MaxTotal = 1000
	if _, err := Extract(src, []Job{{Entry: src.Entries()[0], Dest: "big.bin"}}, out, lim, nil); !errors.Is(err, ErrLimit) {
		t.Fatal("size limit not enforced:", err)
	}
	lim = DefaultLimits
	lim.MaxFiles = 0
	if _, err := Extract(src, []Job{{Entry: src.Entries()[0], Dest: "big.bin"}}, out, lim, func(string) (int64, error) { return 100, nil }); err == nil {
		t.Fatal("free space not checked")
	}
	// destination path escaping dst
	if _, err := Extract(src, []Job{{Entry: src.Entries()[0], Dest: "../x"}}, out, DefaultLimits, nil); err == nil {
		t.Fatal("escaping destination accepted")
	}
}

func TestSevenZipAndPolishNames(t *testing.T) {
	src, err := Open(filepath.Join("testdata", "mod.7z"))
	if err != nil {
		t.Fatal(err)
	}
	defer src.Close()
	var names []string
	for _, e := range src.Entries() {
		names = append(names, e.Path)
	}
	if strings.Join(names, "|") != "Data/Mój plugin.esp|Data/textures/a.dds" {
		t.Fatal(names)
	}
	out := filepath.Join(t.TempDir(), "wynik ąę")
	os.MkdirAll(out, 0o755)
	var jobs []Job
	for _, e := range src.Entries() {
		jobs = append(jobs, Job{Entry: e, Dest: e.Path})
	}
	got, err := Extract(src, jobs, out, DefaultLimits, nil)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(filepath.Join(out, "Data", "Mój plugin.esp"))
	if string(b) != "plugin z 7z" || got[0].SHA256 == "" {
		t.Fatal(string(b))
	}
}

func TestSniffAndLooseFiles(t *testing.T) {
	dir := t.TempDir()
	// a .pk3 is a zip but must stay a file
	pk3 := writeZip(t, filepath.Join(dir, "mod.pk3"), []zipEntry{{name: "x", data: "y"}})
	if k, _ := Sniff(pk3); k != "file" {
		t.Fatal(k)
	}
	// a zip with a wrong extension is still a zip
	z := writeZip(t, filepath.Join(dir, "mod.dat"), []zipEntry{{name: "x", data: "y"}})
	if k, _ := Sniff(z); k != "zip" {
		t.Fatal(k)
	}
	rar := filepath.Join(dir, "mod.rar")
	os.WriteFile(rar, []byte("Rar!\x1a\x07\x01\x00junk"), 0o644)
	if _, err := Open(rar); !errors.Is(err, ErrUnsupported) {
		t.Fatal(err)
	}
	src, err := Open(pk3)
	if err != nil || len(src.Entries()) != 1 || src.Entries()[0].Path != "mod.pk3" {
		t.Fatal(err)
	}
	// corrupted 7z must not panic
	bad := filepath.Join(dir, "bad.7z")
	os.WriteFile(bad, append([]byte{'7', 'z', 0xBC, 0xAF, 0x27, 0x1C}, bytes.Repeat([]byte{0xff}, 64)...), 0o644)
	if s, err := Open(bad); err == nil {
		s.Close()
		t.Fatal("corrupted 7z accepted")
	}
}

func TestFolderSourceSkipsNothingAndCaseCollisions(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, "Folder z spacją", "sub"), 0o755)
	os.WriteFile(filepath.Join(dir, "Folder z spacją", "sub", "plik.txt"), []byte("a"), 0o644)
	src, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	if src.Kind() != "folder" || len(src.Entries()) != 1 || src.Entries()[0].Path != "Folder z spacją/sub/plik.txt" {
		t.Fatal(src.Entries())
	}
	p := writeZip(t, filepath.Join(t.TempDir(), "case.zip"), []zipEntry{{name: "Tex/A.dds", data: "1"}, {name: "tex/a.dds", data: "2"}})
	z, err := Open(p)
	if err != nil {
		t.Fatal(err)
	}
	defer z.Close()
	if len(z.Entries()) != 1 || len(z.Warnings()) != 1 {
		t.Fatal(z.Entries(), z.Warnings())
	}
}
