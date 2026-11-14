// Package archive reads mod sources safely: .zip and .7z archives, plain
// folders and single loose files (.esp, .pak, .wad, .pk3, .jar...). Entry
// paths are validated before anything is written (no traversal, absolute
// paths, NTFS streams, reserved names or links), and extraction enforces
// size, count and compression-ratio limits while streaming.
package archive

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/bodgit/sevenzip"

	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// Entry is one file in a source (directories are implied by paths).
type Entry struct {
	Path string // clean relative path ('/')
	Size int64  // declared size
	idx  int
}

// Limits bound an extraction.
type Limits struct {
	MaxFiles      int
	MaxTotal      int64
	MaxRatio      int64 // per entry, only checked for entries >= RatioMinSize
	RatioMinSize  int64
	MaxPathLength int
}

// DefaultLimits follow the design (§1.5).
var DefaultLimits = Limits{
	MaxFiles:      200000,
	MaxTotal:      64 << 30,
	MaxRatio:      200,
	RatioMinSize:  50 << 20,
	MaxPathLength: 240,
}

// Source is an opened mod source.
type Source interface {
	Entries() []Entry
	Open(e Entry) (io.ReadCloser, error)
	Close() error
	// Kind is zip|7z|folder|file.
	Kind() string
	// Warnings collected while listing (duplicate names...).
	Warnings() []string
}

// ErrUnsupported is returned for formats that cannot be read.
var ErrUnsupported = errors.New("nieobsługiwany format")

// keepAsFile are extensions that are archives inside but must be installed
// as files (game data containers), never unpacked.
var keepAsFile = map[string]bool{
	".pk3": true, ".pk7": true, ".pke": true, ".ipk3": true, ".pk4": true, ".jar": true, ".pak": true,
	".wad": true, ".esp": true, ".esm": true, ".esl": true, ".bsa": true, ".ba2": true, ".archive": true,
	".vpk": true, ".asi": true, ".dll": true, ".xl": true, ".mrpack": false,
}

var (
	magicZip = []byte("PK\x03\x04")
	magicEmp = []byte("PK\x05\x06") // empty zip
	magic7z  = []byte{'7', 'z', 0xBC, 0xAF, 0x27, 0x1C}
	magicRar = []byte("Rar!\x1a\x07")
)

// Sniff tells what kind of source path is: zip, 7z, rar, folder or file.
func Sniff(path string) (string, error) {
	st, err := os.Stat(path)
	if err != nil {
		return "", err
	}
	if st.IsDir() {
		return "folder", nil
	}
	if keepAsFile[strings.ToLower(filepath.Ext(path))] {
		return "file", nil
	}
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	head := make([]byte, 8)
	n, _ := io.ReadFull(f, head)
	head = head[:n]
	switch {
	case bytes.HasPrefix(head, magicZip), bytes.HasPrefix(head, magicEmp):
		return "zip", nil
	case bytes.HasPrefix(head, magic7z):
		return "7z", nil
	case bytes.HasPrefix(head, magicRar):
		return "rar", nil
	}
	switch strings.ToLower(filepath.Ext(path)) {
	case ".zip", ".7z", ".rar":
		// a truncated download or an HTML error page saved as .zip
		return "", fmt.Errorf("plik %s nie jest prawidłowym archiwum (uszkodzony albo niedokończony plik?)", filepath.Base(path))
	}
	return "file", nil
}

// Open opens a source by its content (not its extension).
func Open(path string) (Source, error) {
	kind, err := Sniff(path)
	if err != nil {
		return nil, err
	}
	switch kind {
	case "folder":
		return openFolder(path)
	case "zip":
		return openZip(path)
	case "7z":
		return open7z(path)
	case "rar":
		return nil, fmt.Errorf("%w: RAR – rozpakuj archiwum (np. 7-Zip) i dodaj mod jako folder", ErrUnsupported)
	}
	return openLoose(path)
}

// ------------------------------------------------------------------ listing

type lister struct {
	entries  []Entry
	warnings []string
	seen     map[string]int // lower path -> index in entries
	bad      []string
}

func newLister() *lister { return &lister{seen: map[string]int{}} }

func (l *lister) add(raw string, size int64, idx int) {
	p, err := relpath.Clean(raw)
	if err != nil {
		l.bad = append(l.bad, err.Error())
		return
	}
	k := relpath.Key(p)
	if prev, ok := l.seen[k]; ok {
		l.warnings = append(l.warnings, fmt.Sprintf("Powtórzona nazwa (różnica wielkości liter): %s – użyto ostatniej", p))
		l.entries[prev] = Entry{Path: p, Size: size, idx: idx}
		return
	}
	l.seen[k] = len(l.entries)
	l.entries = append(l.entries, Entry{Path: p, Size: size, idx: idx})
}

func (l *lister) finish() error {
	if len(l.bad) > 0 {
		sort.Strings(l.bad)
		more := ""
		if len(l.bad) > 5 {
			more = fmt.Sprintf(" (i %d więcej)", len(l.bad)-5)
			l.bad = l.bad[:5]
		}
		return fmt.Errorf("archiwum zawiera niebezpieczne ścieżki – odrzucono: %s%s", strings.Join(l.bad, "; "), more)
	}
	// a file and a directory with the same name cannot both exist
	dirs := map[string]bool{}
	for _, e := range l.entries {
		d := relpath.Dir(e.Path)
		for d != "" {
			dirs[relpath.Key(d)] = true
			d = relpath.Dir(d)
		}
	}
	for _, e := range l.entries {
		if dirs[relpath.Key(e.Path)] {
			return fmt.Errorf("archiwum zawiera plik i folder o tej samej nazwie: %s", e.Path)
		}
	}
	sort.Slice(l.entries, func(i, j int) bool { return l.entries[i].Path < l.entries[j].Path })
	return nil
}

// ------------------------------------------------------------------ zip

type zipSource struct {
	rc *zip.ReadCloser
	*lister
}

const (
	unixTypeMask = 0o170000
	unixSymlink  = 0o120000
	winReparse   = 0x400
)

func openZip(path string) (Source, error) {
	rc, err := zip.OpenReader(path)
	if err != nil {
		return nil, fmt.Errorf("nie można odczytać ZIP: %w", err)
	}
	s := &zipSource{rc: rc, lister: newLister()}
	for i, f := range rc.File {
		name := f.Name
		if strings.HasSuffix(name, "/") || strings.HasSuffix(name, `\`) || f.FileInfo().IsDir() {
			continue
		}
		hostUnix := f.CreatorVersion>>8 == 3
		if f.Mode()&fs.ModeSymlink != 0 || (hostUnix && (f.ExternalAttrs>>16)&unixTypeMask == unixSymlink) || f.ExternalAttrs&winReparse != 0 {
			s.bad = append(s.bad, fmt.Sprintf("%q: dowiązanie (link) w archiwum", name))
			continue
		}
		if f.Flags&0x1 != 0 {
			rc.Close()
			return nil, errors.New("archiwum jest zaszyfrowane (hasło) – nieobsługiwane")
		}
		if f.NonUTF8 && !utf8.ValidString(name) {
			// Explorer and old packers store names in the OEM code page
			// (CP852 on Polish Windows) without the UTF-8 flag
			name = decodeOEM(name)
		}
		s.add(name, int64(f.UncompressedSize64), i)
	}
	if err := s.finish(); err != nil {
		rc.Close()
		return nil, err
	}
	return s, nil
}

func (s *zipSource) Entries() []Entry   { return s.entries }
func (s *zipSource) Kind() string       { return "zip" }
func (s *zipSource) Warnings() []string { return s.warnings }
func (s *zipSource) Close() error       { return s.rc.Close() }
func (s *zipSource) Open(e Entry) (io.ReadCloser, error) {
	f := s.rc.File[e.idx]
	compressed := int64(f.CompressedSize64)
	rc, err := f.Open()
	if err != nil {
		return nil, err
	}
	return &ratioReader{rc: rc, compressed: compressed}, nil
}

// ratioReader enforces the compression ratio limit as bytes arrive (a
// bomb is stopped after RatioMinSize bytes, not after the whole entry).
type ratioReader struct {
	rc         io.ReadCloser
	compressed int64
	n          int64
	maxRatio   int64
	minSize    int64
}

func (r *ratioReader) Read(p []byte) (int, error) {
	n, err := r.rc.Read(p)
	r.n += int64(n)
	if r.maxRatio > 0 && r.n >= r.minSize && r.n/max(r.compressed, 1) > r.maxRatio {
		return n, fmt.Errorf("%w: podejrzany współczynnik kompresji (bomba ZIP?)", ErrLimit)
	}
	return n, err
}
func (r *ratioReader) Close() error { return r.rc.Close() }

// ------------------------------------------------------------------ 7z

type sevenSource struct {
	rc *sevenzip.ReadCloser
	*lister
}

func open7z(path string) (src Source, err error) {
	defer func() {
		if r := recover(); r != nil { // malformed headers must not crash the app
			src, err = nil, fmt.Errorf("uszkodzone archiwum 7z: %v", r)
		}
	}()
	rc, err := sevenzip.OpenReader(path)
	if err != nil {
		if strings.Contains(strings.ToLower(err.Error()), "password") {
			return nil, errors.New("archiwum 7z jest zaszyfrowane (hasło) – nieobsługiwane")
		}
		return nil, fmt.Errorf("nie można odczytać 7z: %w", err)
	}
	s := &sevenSource{rc: rc, lister: newLister()}
	for i, f := range rc.File {
		if f.FileInfo().IsDir() {
			continue
		}
		a := f.Attributes
		if a&winReparse != 0 || (a&0x8000 != 0 && (a>>16)&unixTypeMask == unixSymlink) {
			s.bad = append(s.bad, fmt.Sprintf("%q: dowiązanie (link) w archiwum", f.Name))
			continue
		}
		s.add(f.Name, int64(f.UncompressedSize), i)
	}
	if err := s.finish(); err != nil {
		rc.Close()
		return nil, err
	}
	return s, nil
}

func (s *sevenSource) Entries() []Entry   { return s.entries }
func (s *sevenSource) Kind() string       { return "7z" }
func (s *sevenSource) Warnings() []string { return s.warnings }
func (s *sevenSource) Close() error       { return s.rc.Close() }
func (s *sevenSource) Open(e Entry) (io.ReadCloser, error) {
	return s.rc.File[e.idx].Open()
}

// ------------------------------------------------------------------ folder

type folderSource struct {
	root string
	*lister
	abs []string
}

func openFolder(root string) (Source, error) {
	s := &folderSource{root: root, lister: newLister()}
	err := filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if p == root {
			return nil
		}
		if d.Type()&fs.ModeSymlink != 0 || d.Type()&fs.ModeIrregular != 0 {
			// links and junctions are not followed (they could point anywhere)
			s.warnings = append(s.warnings, "Pominięto dowiązanie: "+p)
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		if d.IsDir() {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, p)
		if err != nil {
			return err
		}
		s.abs = append(s.abs, p)
		s.add(filepath.ToSlash(rel), info.Size(), len(s.abs)-1)
		return nil
	})
	if err != nil {
		return nil, err
	}
	if err := s.finish(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *folderSource) Entries() []Entry                    { return s.entries }
func (s *folderSource) Kind() string                        { return "folder" }
func (s *folderSource) Warnings() []string                  { return s.warnings }
func (s *folderSource) Close() error                        { return nil }
func (s *folderSource) Open(e Entry) (io.ReadCloser, error) { return os.Open(s.abs[e.idx]) }

// ------------------------------------------------------------------ loose file

type looseSource struct {
	path string
	*lister
}

func openLoose(path string) (Source, error) {
	st, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	s := &looseSource{path: path, lister: newLister()}
	s.add(filepath.Base(path), st.Size(), 0)
	if err := s.finish(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *looseSource) Entries() []Entry                  { return s.entries }
func (s *looseSource) Kind() string                      { return "file" }
func (s *looseSource) Warnings() []string                { return s.warnings }
func (s *looseSource) Close() error                      { return nil }
func (s *looseSource) Open(Entry) (io.ReadCloser, error) { return os.Open(s.path) }

// ------------------------------------------------------------------ extraction

// ErrLimit is wrapped by limit violations.
var ErrLimit = errors.New("przekroczony limit bezpieczeństwa")

// Extracted is one written file.
type Extracted struct {
	Path   string // destination relative path
	Size   int64
	SHA256 string
}

// Job maps entries to destination relative paths inside dst.
type Job struct {
	Entry Entry
	Dest  string // clean relative path
}

// Extract writes the jobs into dst (which must exist and be empty of these
// paths). Files are created exclusively, never through existing links, and
// sizes are counted while streaming (headers can lie).
func Extract(src Source, jobs []Job, dst string, lim Limits, freeSpace func(string) (int64, error)) ([]Extracted, error) {
	if lim.MaxFiles > 0 && len(jobs) > lim.MaxFiles {
		return nil, fmt.Errorf("%w: %d plików (maks. %d)", ErrLimit, len(jobs), lim.MaxFiles)
	}
	var declared int64
	for _, j := range jobs {
		declared += j.Entry.Size
	}
	if lim.MaxTotal > 0 && declared > lim.MaxTotal {
		return nil, fmt.Errorf("%w: %d bajtów po rozpakowaniu", ErrLimit, declared)
	}
	budget := lim.MaxTotal
	if freeSpace != nil {
		if free, err := freeSpace(dst); err == nil {
			avail := free - 2<<30
			if declared > avail {
				return nil, fmt.Errorf("za mało miejsca na dysku: potrzeba %d MB, wolne %d MB (z zapasem 2 GB)", declared>>20, avail>>20)
			}
			if budget <= 0 || avail < budget {
				budget = avail
			}
		}
	}
	dstAbs, err := filepath.Abs(dst)
	if err != nil {
		return nil, err
	}
	var total int64
	out := make([]Extracted, 0, len(jobs))
	for _, j := range jobs {
		rel, err := relpath.Clean(j.Dest)
		if err != nil {
			return nil, err
		}
		target := filepath.Join(dstAbs, filepath.FromSlash(rel))
		if !strings.HasPrefix(target, dstAbs+string(filepath.Separator)) {
			return nil, fmt.Errorf("ścieżka poza katalogiem docelowym: %s", rel)
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return nil, err
		}
		n, sum, err := writeEntry(src, j.Entry, target, lim, budget-total)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", j.Entry.Path, err)
		}
		total += n
		out = append(out, Extracted{Path: rel, Size: n, SHA256: sum})
	}
	return out, nil
}

func writeEntry(src Source, e Entry, target string, lim Limits, budget int64) (n int64, sum string, err error) {
	defer func() {
		if r := recover(); r != nil { // a malformed stream must not crash the app
			os.Remove(target)
			n, sum, err = 0, "", fmt.Errorf("uszkodzone dane w archiwum: %v", r)
		}
	}()
	rc, err := src.Open(e)
	if err != nil {
		return 0, "", err
	}
	defer rc.Close()
	if rr, ok := rc.(*ratioReader); ok && lim.MaxRatio > 0 {
		// the header already shows a bomb: refuse before writing anything
		if e.Size >= lim.RatioMinSize && e.Size/max(rr.compressed, 1) > lim.MaxRatio {
			return 0, "", fmt.Errorf("%w: podejrzany współczynnik kompresji (bomba ZIP?)", ErrLimit)
		}
		rr.maxRatio, rr.minSize = lim.MaxRatio, lim.RatioMinSize
	}
	f, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return 0, "", err
	}
	h := sha256.New()
	// never more than declared (+1 to detect lies), never more than the budget
	limit := e.Size + 1
	if src.Kind() == "folder" || src.Kind() == "file" {
		limit = 1<<62 - 1
	}
	if budget > 0 && budget < limit {
		limit = budget + 1
	}
	n, err = io.Copy(io.MultiWriter(f, h), io.LimitReader(rc, limit))
	if err == nil && n == limit {
		err = fmt.Errorf("%w: wpis jest większy niż deklarowano lub przekracza limit", ErrLimit)
	}
	if err == nil && (src.Kind() == "zip" || src.Kind() == "7z") && n != e.Size {
		err = fmt.Errorf("rozmiar wpisu (%d) nie zgadza się z nagłówkiem (%d)", n, e.Size)
	}
	if err == nil {
		if rr, ok := rc.(*ratioReader); ok && lim.MaxRatio > 0 && n >= lim.RatioMinSize {
			if rr.compressed <= 0 || n/max(rr.compressed, 1) > lim.MaxRatio {
				err = fmt.Errorf("%w: podejrzany współczynnik kompresji (bomba ZIP?)", ErrLimit)
			}
		}
	}
	if err == nil {
		err = f.Sync()
	}
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		os.Remove(target)
		return 0, "", err
	}
	return n, hex.EncodeToString(h.Sum(nil)), nil
}

// HashFile returns the sha256 and size of a file.
func HashFile(path string) (string, int64, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()
	h := sha256.New()
	n, err := io.Copy(h, f)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(h.Sum(nil)), n, nil
}

// ReadSmall reads an entry fully if it is not larger than max bytes.
func ReadSmall(src Source, e Entry, max int64) ([]byte, error) {
	if e.Size > max {
		return nil, fmt.Errorf("plik %s jest za duży (%d B)", e.Path, e.Size)
	}
	rc, err := src.Open(e)
	if err != nil {
		return nil, err
	}
	defer rc.Close()
	b, err := io.ReadAll(io.LimitReader(rc, max+1))
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > max {
		return nil, fmt.Errorf("plik %s jest za duży", e.Path)
	}
	return b, nil
}
