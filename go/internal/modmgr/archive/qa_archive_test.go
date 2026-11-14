package archive

import (
	"archive/zip"
	"bytes"
	"compress/flate"
	"errors"
	"hash/crc32"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

// Windows also treats COM¹-³ / LPT¹-³ (superscript digits) as devices.
func TestQASuperscriptDeviceNamesRejected(t *testing.T) {
	// QA-BUG fixed (regression test): COM¹-³/LPT¹-³ (superscript digits) not treated as reserved device names
	dir := t.TempDir()
	for _, n := range []string{"COM¹.txt", "dane/LPT³", "com²"} {
		p := writeZip(t, filepath.Join(dir, "dev.zip"), []zipEntry{{name: n, data: "x"}})
		if src, err := Open(p); err == nil {
			src.Close()
			t.Errorf("%q accepted (Windows opens a device for this name)", n)
		}
	}
}

// More unsafe names (UNC, \\?\, drive-relative, ADS variants, NUL byte).
func TestQAMoreMaliciousNames(t *testing.T) {
	dir := t.TempDir()
	for i, n := range []string{
		`\\server\share\x.txt`, "//server/share/x.txt", `\\?\C:\x.txt`, `\\.\PhysicalDrive0`, "C:x.txt", "c:", "a/b:c/d.txt",
		"x.txt::$DATA", "a\x00b.txt", "a//b.txt", "../", "..\\", "a/./../../b", "AUX.tar.gz", "CONIN$", "a/ nul .txt",
	} {
		p := writeZip(t, filepath.Join(dir, "m"+string(rune('a'+i))+".zip"), []zipEntry{{name: "ok.txt", data: "ok"}, {name: n, data: "x"}})
		src, err := Open(p)
		if err == nil {
			var names []string
			for _, e := range src.Entries() {
				names = append(names, e.Path)
			}
			src.Close()
			// accepted only if the bad name was dropped/normalised to something local
			for _, nm := range names {
				if !filepath.IsLocal(filepath.FromSlash(nm)) || strings.ContainsAny(nm, ":\x00") {
					t.Errorf("%q: unsafe entry %q accepted", n, nm)
				}
			}
		}
	}
}

// Zip archives from Windows Explorer / old tools store Polish names in the
// OEM code page (CP852) without the UTF-8 flag. They must not be refused.
func TestQAZipWithOEMCodePageNames(t *testing.T) {
	// QA-BUG fixed (regression test): zip with CP852/OEM file names (no UTF-8 flag, Windows Explorer) refused as invalid encoding
	if oemPage != 852 {
		t.Skipf("names are decoded with the system OEM code page (%d here, the test data is CP852)", oemPage)
	}
	dir := t.TempDir()
	p := filepath.Join(dir, "explorer.zip")
	f, err := os.Create(p)
	if err != nil {
		t.Fatal(err)
	}
	w := zip.NewWriter(f)
	// "żaba ćma.txt" in CP852: ż=0xBE, ć=0x86
	h := &zip.FileHeader{Name: "\xbeaba \x86ma.txt", Method: zip.Deflate, NonUTF8: true}
	zw, _ := w.CreateHeader(h)
	zw.Write([]byte("rechot"))
	w.Close()
	f.Close()
	src, err := Open(p)
	if err != nil {
		t.Fatalf("archive with CP852 names refused: %v", err)
	}
	defer src.Close()
	if es := src.Entries(); len(es) != 1 || es[0].Path != "żaba ćma.txt" {
		t.Errorf("CP852 name not decoded: %+v", es)
	}
}

// A zip bomb is stopped while streaming (design §1.5: counters checked
// during the stream), not after the whole entry was written to disk.
func TestQAZipBombStoppedWhileStreaming(t *testing.T) {
	// QA-BUG fixed (regression test): compression ratio checked only after the whole entry is written to disk
	dir := t.TempDir()
	p := filepath.Join(dir, "bomb.zip")
	f, err := os.Create(p)
	if err != nil {
		t.Fatal(err)
	}
	w := zip.NewWriter(f)
	w.RegisterCompressor(zip.Deflate, func(out io.Writer) (io.WriteCloser, error) { return flate.NewWriter(out, flate.BestCompression) })
	zw, _ := w.CreateHeader(&zip.FileHeader{Name: "big.bin", Method: zip.Deflate})
	chunk := make([]byte, 1<<20)
	const total = 256
	for i := 0; i < total; i++ {
		zw.Write(chunk)
	}
	w.Close()
	f.Close()
	src, err := Open(p)
	if err != nil {
		t.Fatal(err)
	}
	defer src.Close()
	out := filepath.Join(dir, "out")
	os.MkdirAll(out, 0o755)
	lim := DefaultLimits
	lim.RatioMinSize = 1 << 20
	var peak atomic.Int64
	stop := make(chan struct{})
	done := make(chan struct{})
	go func() {
		defer close(done)
		for {
			select {
			case <-stop:
				return
			default:
			}
			if st, err := os.Stat(filepath.Join(out, "big.bin")); err == nil && st.Size() > peak.Load() {
				peak.Store(st.Size())
			}
			time.Sleep(200 * time.Microsecond)
		}
	}()
	_, err = Extract(src, []Job{{Entry: src.Entries()[0], Dest: "big.bin"}}, out, lim, nil)
	close(stop)
	<-done
	if !errors.Is(err, ErrLimit) {
		t.Fatalf("bomb not refused: %v", err)
	}
	if peak.Load() > 64<<20 {
		t.Errorf("bomb was written to disk up to %d MiB before the ratio check (declared ratio is visible in the header)", peak.Load()>>20)
	}
}

// Headers that lie about the size (both ways) are refused, no partial file.
func TestQALyingSizeHeaders(t *testing.T) {
	dir := t.TempDir()
	data := bytes.Repeat([]byte("ab"), 5000)
	for _, declared := range []uint64{10, uint64(len(data)) * 2} {
		p := filepath.Join(dir, "lie.zip")
		f, _ := os.Create(p)
		w := zip.NewWriter(f)
		h := &zip.FileHeader{Name: "x.bin", Method: zip.Store, CRC32: crc32.ChecksumIEEE(data), CompressedSize64: uint64(len(data)), UncompressedSize64: declared}
		zw, err := w.CreateRaw(h)
		if err != nil {
			t.Fatal(err)
		}
		zw.Write(data)
		w.Close()
		f.Close()
		src, err := Open(p)
		if err != nil {
			continue // refused at listing: fine
		}
		out := filepath.Join(dir, "out", "d")
		os.MkdirAll(out, 0o755)
		_, err = Extract(src, []Job{{Entry: src.Entries()[0], Dest: "x.bin"}}, out, DefaultLimits, nil)
		src.Close()
		if err == nil {
			t.Errorf("declared %d, real %d: accepted", declared, len(data))
		}
		if _, err := os.Stat(filepath.Join(out, "x.bin")); err == nil {
			t.Errorf("declared %d: partial file left", declared)
		}
		os.RemoveAll(filepath.Join(dir, "out"))
	}
}

// Extract never follows a link that already exists at the destination.
func TestQAExtractDoesNotFollowExistingLink(t *testing.T) {
	dir := t.TempDir()
	victim := filepath.Join(dir, "ofiara.txt")
	os.WriteFile(victim, []byte("nietykalny"), 0o644)
	p := writeZip(t, filepath.Join(dir, "m.zip"), []zipEntry{{name: "a.txt", data: "zły"}})
	src, err := Open(p)
	if err != nil {
		t.Fatal(err)
	}
	defer src.Close()
	out := filepath.Join(dir, "out")
	os.MkdirAll(out, 0o755)
	if err := os.Symlink(victim, filepath.Join(out, "a.txt")); err != nil {
		if err := os.Link(victim, filepath.Join(out, "a.txt")); err != nil {
			t.Skip("no links:", err)
		}
	}
	_, _ = Extract(src, []Job{{Entry: src.Entries()[0], Dest: "a.txt"}}, out, DefaultLimits, nil)
	if b, _ := os.ReadFile(victim); string(b) != "nietykalny" {
		t.Errorf("extraction wrote through an existing link: %q", b)
	}
}

// Folder sources: symlinked files inside a mod folder are skipped.
func TestQAFolderSourceSkipsSymlinkFile(t *testing.T) {
	dir := t.TempDir()
	secret := filepath.Join(dir, "sekret.txt")
	os.WriteFile(secret, []byte("tajne"), 0o644)
	mod := filepath.Join(dir, "mod")
	os.MkdirAll(mod, 0o755)
	os.WriteFile(filepath.Join(mod, "ok.txt"), []byte("ok"), 0o644)
	if err := os.Symlink(secret, filepath.Join(mod, "link.txt")); err != nil {
		t.Skip("symlinks need privileges:", err)
	}
	src, err := Open(mod)
	if err != nil {
		t.Fatal(err)
	}
	defer src.Close()
	for _, e := range src.Entries() {
		if e.Path == "link.txt" {
			t.Error("symlink followed")
		}
	}
	_ = fs.ModeSymlink
}
