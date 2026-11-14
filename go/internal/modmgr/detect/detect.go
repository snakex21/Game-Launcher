// Package detect finds game installs: Steam libraries (libraryfolders.vdf
// and appmanifest_*.acf, KeyValues text format) and folders chosen by the
// user (matched against the definitions' required files).
package detect

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// KV is a parsed KeyValues node.
type KV struct {
	Value    string
	Children map[string]*KV // keys lower-case
	Order    []string
}

// Get follows lower-case keys.
func (k *KV) Get(keys ...string) *KV {
	cur := k
	for _, key := range keys {
		if cur == nil || cur.Children == nil {
			return nil
		}
		cur = cur.Children[strings.ToLower(key)]
	}
	return cur
}

// Str is the value at keys ("" if missing).
func (k *KV) Str(keys ...string) string {
	if n := k.Get(keys...); n != nil {
		return n.Value
	}
	return ""
}

// ParseVDF parses Valve's text KeyValues format.
func ParseVDF(data []byte) (*KV, error) {
	p := &vdfParser{s: string(data)}
	root := &KV{Children: map[string]*KV{}}
	if err := p.object(root, 0); err != nil {
		return nil, err
	}
	return root, nil
}

type vdfParser struct {
	s   string
	pos int
}

func (p *vdfParser) skip() {
	for p.pos < len(p.s) {
		c := p.s[p.pos]
		switch {
		case c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == 0xEF || c == 0xBB || c == 0xBF:
			p.pos++
		case c == '/' && p.pos+1 < len(p.s) && p.s[p.pos+1] == '/':
			for p.pos < len(p.s) && p.s[p.pos] != '\n' {
				p.pos++
			}
		default:
			return
		}
	}
}

func (p *vdfParser) token() (string, bool, error) {
	p.skip()
	if p.pos >= len(p.s) {
		return "", false, nil
	}
	c := p.s[p.pos]
	if c == '{' || c == '}' {
		p.pos++
		return string(c), false, nil
	}
	if c == '"' {
		p.pos++
		var b strings.Builder
		for p.pos < len(p.s) {
			c := p.s[p.pos]
			if c == '\\' && p.pos+1 < len(p.s) {
				switch p.s[p.pos+1] {
				case '\\', '"':
					b.WriteByte(p.s[p.pos+1])
					p.pos += 2
					continue
				case 'n':
					b.WriteByte('\n')
					p.pos += 2
					continue
				case 't':
					b.WriteByte('\t')
					p.pos += 2
					continue
				}
			}
			if c == '"' {
				p.pos++
				return b.String(), true, nil
			}
			b.WriteByte(c)
			p.pos++
		}
		return "", false, errors.New("VDF: niezamknięty cudzysłów")
	}
	start := p.pos
	for p.pos < len(p.s) && !strings.ContainsRune(" \t\r\n{}\"", rune(p.s[p.pos])) {
		p.pos++
	}
	return p.s[start:p.pos], true, nil
}

func (p *vdfParser) object(into *KV, depth int) error {
	if depth > 32 {
		return errors.New("VDF: zbyt głębokie zagnieżdżenie")
	}
	for {
		key, isStr, err := p.token()
		if err != nil {
			return err
		}
		if !isStr {
			if key == "}" {
				if depth == 0 {
					return errors.New("VDF: nadmiarowe }")
				}
				return nil
			}
			if key == "" {
				if depth > 0 {
					return errors.New("VDF: niezamknięty obiekt")
				}
				return nil
			}
			return fmt.Errorf("VDF: nieoczekiwany znak %q", key)
		}
		val, vStr, err := p.token()
		if err != nil {
			return err
		}
		node := &KV{}
		switch {
		case vStr:
			node.Value = val
		case val == "{":
			node.Children = map[string]*KV{}
			if err := p.object(node, depth+1); err != nil {
				return err
			}
		default:
			return fmt.Errorf("VDF: brak wartości dla %q", key)
		}
		lk := strings.ToLower(key)
		if _, dup := into.Children[lk]; !dup {
			into.Order = append(into.Order, lk)
		}
		into.Children[lk] = node
	}
}

// SteamApp is one installed Steam app.
type SteamApp struct {
	AppID      int
	Name       string
	Path       string
	BuildID    string
	StateFlags int
	Library    string
}

// Updating reports whether Steam is still updating/installing the app.
func (a SteamApp) Updating() bool { return a.StateFlags != 0 && a.StateFlags != 4 }

// SteamLibraries lists library folders of a Steam installation.
func SteamLibraries(steamRoot string) ([]string, error) {
	libs := []string{steamRoot}
	b, err := os.ReadFile(filepath.Join(steamRoot, "steamapps", "libraryfolders.vdf"))
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return libs, nil
		}
		return nil, err
	}
	kv, err := ParseVDF(b)
	if err != nil {
		return nil, err
	}
	lf := kv.Get("libraryfolders")
	if lf == nil {
		return libs, nil
	}
	for _, k := range lf.Order {
		n := lf.Children[k]
		p := n.Value
		if n.Children != nil {
			p = n.Str("path")
		}
		if p == "" {
			continue
		}
		p = filepath.Clean(p)
		dup := false
		for _, l := range libs {
			if strings.EqualFold(filepath.Clean(l), p) {
				dup = true
			}
		}
		if !dup {
			libs = append(libs, p)
		}
	}
	return libs, nil
}

// SteamApps reads all appmanifest files of the libraries.
func SteamApps(steamRoot string) ([]SteamApp, error) {
	libs, err := SteamLibraries(steamRoot)
	if err != nil {
		return nil, err
	}
	var out []SteamApp
	for _, lib := range libs {
		files, _ := filepath.Glob(filepath.Join(lib, "steamapps", "appmanifest_*.acf"))
		for _, f := range files {
			b, err := os.ReadFile(f)
			if err != nil {
				continue
			}
			kv, err := ParseVDF(b)
			if err != nil {
				continue
			}
			st := kv.Get("AppState")
			if st == nil {
				continue
			}
			id, _ := strconv.Atoi(st.Str("appid"))
			dir := st.Str("installdir")
			if id == 0 || dir == "" || strings.ContainsAny(dir, `/\:`) || dir == ".." {
				continue
			}
			flags, _ := strconv.Atoi(st.Str("StateFlags"))
			out = append(out, SteamApp{AppID: id, Name: st.Str("name"), Path: filepath.Join(lib, "steamapps", "common", dir),
				BuildID: st.Str("buildid"), StateFlags: flags, Library: lib})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].AppID < out[j].AppID })
	return out, nil
}

// Found is a detected install.
type Found struct {
	DefID   string `json:"defId"`
	Name    string `json:"name"`
	Path    string `json:"path"`
	Store   string `json:"store"`
	BuildID string `json:"buildId,omitempty"`
	Valid   bool   `json:"valid"`
}

// FromSteam matches Steam apps against the definitions.
func FromSteam(steamRoot string, set *gamedef.Set) ([]Found, error) {
	apps, err := SteamApps(steamRoot)
	if err != nil {
		return nil, err
	}
	var out []Found
	for _, d := range set.List() {
		if d.Detection.Steam == nil {
			continue
		}
		for _, a := range apps {
			for _, id := range d.Detection.Steam.AppIDs {
				if id == a.AppID {
					out = append(out, Found{DefID: d.ID, Name: d.Name, Path: a.Path, Store: "steam", BuildID: a.BuildID, Valid: Validate(d, a.Path) == nil})
				}
			}
		}
	}
	return out, nil
}

// Validate checks requiredFiles / anyOfFiles in a game folder.
func Validate(d *gamedef.Definition, root string) error {
	st, err := os.Stat(root)
	if err != nil || !st.IsDir() {
		return fmt.Errorf("folder gry nie istnieje: %s", root)
	}
	var missing []string
	for _, f := range d.Detection.RequiredFiles {
		if !exists(root, f) {
			missing = append(missing, f)
		}
	}
	if len(d.Detection.AnyOfFiles) > 0 {
		ok := false
		for _, f := range d.Detection.AnyOfFiles {
			if exists(root, f) {
				ok = true
			}
		}
		if !ok {
			missing = append(missing, "jeden z: "+strings.Join(d.Detection.AnyOfFiles, ", "))
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("w folderze brakuje plików gry: %s", strings.Join(missing, "; "))
	}
	return nil
}

func exists(root, rel string) bool {
	_, err := os.Stat(filepath.Join(root, filepath.FromSlash(rel)))
	return err == nil
}

// Suggestion is a definition matching a folder.
type Suggestion struct {
	DefID string `json:"defId"`
	Name  string `json:"name"`
	Root  string `json:"root"`
	Score int    `json:"score"`
}

// Suggest finds definitions whose required files are in dir or in one of
// its parents (an exe deep inside the game, like bin/x64/Cyberpunk2077.exe).
func Suggest(set *gamedef.Set, dir string) []Suggestion {
	var out []Suggestion
	for _, d := range set.List() {
		if d.IsGeneric() || (len(d.Detection.RequiredFiles) == 0 && len(d.Detection.AnyOfFiles) == 0) {
			continue
		}
		cur := filepath.Clean(dir)
		for i := 0; i < 4; i++ {
			if Validate(d, cur) == nil {
				score := 10*len(d.Detection.RequiredFiles) + len(d.Detection.AnyOfFiles) - i
				out = append(out, Suggestion{DefID: d.ID, Name: d.Name, Root: cur, Score: score})
				break
			}
			parent := filepath.Dir(cur)
			if parent == cur {
				break
			}
			cur = parent
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Score > out[j].Score })
	return out
}
