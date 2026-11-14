// Package scan finds games in folders (the feature intent of
// launcher/scan_pipeline.py): every sub-folder that holds a plausible game
// .exe becomes a candidate that the user confirms before import.
package scan

import (
	"context"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// IgnoredExes are never the main game executable.
var IgnoredExes = map[string]bool{
	"setup.exe": true, "uninstall.exe": true, "unins000.exe": true, "unins001.exe": true,
	"launcher.exe": true, "crashreporter.exe": true, "configtool.exe": true, "activation.exe": true,
	"vc_redist.x64.exe": true, "vc_redist.x86.exe": true, "dxsetup.exe": true, "dxwebsetup.exe": true,
	"unitycrashhandler64.exe": true, "unitycrashhandler32.exe": true, "crashpad_handler.exe": true,
}

var preferredKeywords = []string{"game", "shipping", "retail"}

// binFolders are searched one level below the game folder.
var binFolders = []string{"bin", "Binaries", "Win32", "Win64", "x64", "x86", `Binaries\Win64`, `bin\x64`, `bin\win64`}

// Options for a scan.
type Options struct {
	Folders    []string
	Recursive  bool
	MaxDepth   int             // recursion limit (0 = 4)
	Ignored    []string        // folder names to skip (case-insensitive)
	KnownNames map[string]bool // lower-case names already in the library
	Progress   func(done, total int, current string)
}

// Candidate is a folder that looks like a game.
type Candidate struct {
	Name   string   `json:"name"`
	Folder string   `json:"folder"`
	Exe    string   `json:"exe"`
	Exes   []string `json:"exes"` // all candidate exes, best first
	Import bool     `json:"import"`
}

var cleanupPatterns = []*regexp.Regexp{
	regexp.MustCompile(`\[.*?\]`),
	regexp.MustCompile(`\(.*?\)`),
	regexp.MustCompile(`(?i)\bv\d+(\.\d+)*\b`),
	regexp.MustCompile(`(?i)\b(Repack|Update|Fix|GOTY|CODEX|PLAZA|SKIDROW|RELOADED|FLT|CPY|GOG|MULTi\d*)\b`),
	regexp.MustCompile(`[_.]`),
	regexp.MustCompile(`\s-\s*$`),
}

// GuessName cleans a folder name into a game title.
func GuessName(folder string) string {
	s := folder
	for _, re := range cleanupPatterns {
		s = re.ReplaceAllString(s, " ")
	}
	s = strings.Join(strings.Fields(s), " ")
	s = strings.Trim(s, " -")
	if s == "" {
		return folder
	}
	return s
}

type exeInfo struct {
	path  string
	name  string // lower-case without .exe
	size  int64
	depth int
}

// FindExes lists plausible executables of a game folder, best first.
func FindExes(folder, guessed string) []string {
	var found []exeInfo
	seen := map[string]bool{}
	look := func(dir string, depth int) {
		entries, err := os.ReadDir(dir)
		if err != nil {
			return
		}
		for _, e := range entries {
			n := strings.ToLower(e.Name())
			if e.IsDir() || !strings.HasSuffix(n, ".exe") || IgnoredExes[n] {
				continue
			}
			p := filepath.Join(dir, e.Name())
			key := strings.ToLower(p)
			if seen[key] {
				continue
			}
			seen[key] = true
			info, err := e.Info()
			if err != nil {
				continue
			}
			found = append(found, exeInfo{path: p, name: strings.TrimSuffix(n, ".exe"), size: info.Size(), depth: depth})
		}
	}
	look(folder, 0)
	for _, b := range binFolders {
		look(filepath.Join(folder, b), 1)
	}
	folderName := strings.ToLower(filepath.Base(folder))
	g := strings.ToLower(guessed)
	gCompact := compact(g)
	score := func(x exeInfo) int {
		switch {
		case x.name == folderName:
			return 10
		case g != "" && (x.name == g || compact(x.name) == gCompact):
			return 9
		case g != "" && strings.Contains(x.name, g):
			return 7
		case len(x.name) > 2 && strings.Contains(folderName, x.name):
			return 6
		}
		for _, k := range preferredKeywords {
			if strings.Contains(x.name, k) {
				return 5
			}
		}
		return 0
	}
	sort.SliceStable(found, func(i, j int) bool {
		si, sj := score(found[i]), score(found[j])
		if si != sj {
			return si > sj
		}
		if found[i].size != found[j].size {
			return found[i].size > found[j].size
		}
		return found[i].depth < found[j].depth
	})
	out := make([]string, len(found))
	for i, f := range found {
		out[i] = f.path
	}
	return out
}

func compact(s string) string {
	return strings.Map(func(r rune) rune {
		if r == ' ' || r == '-' || r == '_' || r == '\'' || r == ':' {
			return -1
		}
		return r
	}, s)
}

// Run scans the folders. A folder that itself contains a game exe is a
// candidate (and is not descended further); otherwise its sub-folders are
// visited (up to MaxDepth when Recursive, one level otherwise).
func Run(ctx context.Context, opt Options) ([]Candidate, error) {
	ignored := map[string]bool{}
	for _, n := range opt.Ignored {
		ignored[strings.ToLower(n)] = true
	}
	maxDepth := opt.MaxDepth
	if maxDepth <= 0 {
		maxDepth = 4
	}
	if !opt.Recursive {
		maxDepth = 1
	}
	var out []Candidate
	names := map[string]bool{}
	visited := 0
	var walk func(dir string, depth int) error
	walk = func(dir string, depth int) error {
		if err := ctx.Err(); err != nil {
			return err
		}
		visited++
		if opt.Progress != nil && visited%10 == 1 {
			opt.Progress(visited, 0, dir)
		}
		if depth > 0 {
			guessed := GuessName(filepath.Base(dir))
			if exes := FindExes(dir, guessed); len(exes) > 0 {
				key := strings.ToLower(guessed)
				if !opt.KnownNames[key] && !names[key] {
					names[key] = true
					out = append(out, Candidate{Name: guessed, Folder: dir, Exe: exes[0], Exes: exes, Import: true})
				}
				return nil // a game folder: its sub-folders belong to the game
			}
		}
		if depth >= maxDepth {
			return nil
		}
		entries, err := os.ReadDir(dir)
		if err != nil {
			return nil
		}
		for _, e := range entries {
			if !e.IsDir() || ignored[strings.ToLower(e.Name())] || strings.HasPrefix(e.Name(), "$") {
				continue
			}
			if err := walk(filepath.Join(dir, e.Name()), depth+1); err != nil {
				return err
			}
		}
		return nil
	}
	for _, f := range opt.Folders {
		st, err := os.Stat(f)
		if err != nil || !st.IsDir() {
			continue
		}
		// The scan folder itself may be a single game.
		if exes := FindExes(f, GuessName(filepath.Base(f))); len(exes) > 0 && !ignored[strings.ToLower(filepath.Base(f))] {
			guessed := GuessName(filepath.Base(f))
			key := strings.ToLower(guessed)
			if !opt.KnownNames[key] && !names[key] {
				names[key] = true
				out = append(out, Candidate{Name: guessed, Folder: f, Exe: exes[0], Exes: exes, Import: true})
			}
		}
		if err := walk(f, 0); err != nil {
			return out, err
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return strings.ToLower(out[i].Name) < strings.ToLower(out[j].Name) })
	return out, nil
}
