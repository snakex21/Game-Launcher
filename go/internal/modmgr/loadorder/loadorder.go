// Package loadorder writes the files that tell a game which mods/plugins
// to load and in which order (plugins.txt, Morrowind.ini, modlist.txt,
// mods.settings, ModsConfig.xml) and builds command-line arguments for
// games that take mods as arguments (Doom source ports).
//
// Writers only produce content; the deploy engine puts it in place as part
// of the same transaction (with a backup of the original file), so purge
// restores the original load order file too.
package loadorder

import (
	"bytes"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// Placed is one deployed file (the winner), in mod order.
type Placed struct {
	Target    gamedef.Location
	SourceAbs string
	ModIndex  int
	ModID     string
}

// Plugin is a plugin entry of the profile's own order.
type Plugin struct {
	Name    string `json:"name"`
	Enabled bool   `json:"enabled"`
}

// Input is what a writer gets.
type Input struct {
	Def   *gamedef.Definition
	Res   *gamedef.Resolver
	Files []Placed
	// Order is the profile's plugin order (may be empty = automatic).
	Order []Plugin
	// ReadFile returns the current content of a location (nil if missing).
	ReadFile func(gamedef.Location) ([]byte, error)
	// ListDir lists file names in a location (for plugins installed by hand).
	ListDir func(gamedef.Location) ([]string, error)
}

// Generated is a file to deploy.
type Generated struct {
	Target  gamedef.Location
	Content []byte
}

// PluginInfo describes a plugin for the UI.
type PluginInfo struct {
	Name     string `json:"name"`
	Enabled  bool   `json:"enabled"`
	Implicit bool   `json:"implicit"` // always loaded by the game (not written)
	External bool   `json:"external"` // in the game folder, not from a mod
	Master   bool   `json:"master"`
	ModID    string `json:"modId,omitempty"`
}

// Output is what a writer produces.
type Output struct {
	Files    []Generated
	MTimes   map[string]time.Time // target key -> modification time to set
	Plugins  []PluginInfo
	Warnings []string
	Kind     string
}

// Supported reports whether the load order kind is handled.
func Supported(kind string) bool {
	switch kind {
	case "", "none", "deploy-priority", "dependency-sorted", "launch-args",
		"bethesda-plugins", "cyberpunk-modlist", "witcher3-mods-settings", "rimworld-modsconfig":
		return true
	}
	return false
}

// Build runs the writer for the definition's load order kind.
func Build(in Input) (*Output, error) {
	lo := in.Def.LoadOrder
	out := &Output{MTimes: map[string]time.Time{}, Kind: lo.Kind}
	switch lo.Kind {
	case "", "none", "deploy-priority", "dependency-sorted", "launch-args":
		return out, nil
	case "bethesda-plugins":
		return out, bethesda(in, out)
	case "cyberpunk-modlist":
		return out, cyberpunk(in, out)
	case "witcher3-mods-settings":
		return out, witcher3(in, out)
	case "rimworld-modsconfig":
		return out, rimworld(in, out)
	}
	out.Warnings = append(out.Warnings, fmt.Sprintf("Zapis kolejności ładowania typu %q nie jest jeszcze obsługiwany – pliki modów są wdrażane, a kolejność ustaw w narzędziu gry.", lo.Kind))
	return out, nil
}

// ------------------------------------------------------------- Bethesda

func isMaster(name string) bool {
	l := strings.ToLower(name)
	return strings.HasSuffix(l, ".esm") || strings.HasSuffix(l, ".esl")
}

func bethesda(in Input, out *Output) error {
	lo := in.Def.LoadOrder
	dir, err := in.Res.Location(lo.PluginsDir)
	if err != nil {
		return err
	}
	implicit := map[string]bool{}
	var implicitOrder []string
	for _, p := range lo.ImplicitPlugins {
		implicit[strings.ToLower(p)] = true
		implicitOrder = append(implicitOrder, p)
	}
	if lo.ImplicitListFile != "" { // Creation Club list (Skyrim.ccc)
		if l, err := in.Res.Location(lo.ImplicitListFile); err == nil && in.ReadFile != nil {
			if b, err := in.ReadFile(l); err == nil {
				for _, line := range strings.Split(string(b), "\n") {
					if n := strings.TrimSpace(line); n != "" && !implicit[strings.ToLower(n)] {
						implicit[strings.ToLower(n)] = true
						implicitOrder = append(implicitOrder, n)
					}
				}
			}
		}
	}
	// plugins from mods, in mod order
	type pl struct {
		name    string
		modIdx  int
		modID   string
		target  gamedef.Location
		fromMod bool
	}
	var plugins []pl
	seen := map[string]bool{}
	for _, f := range in.Files {
		if f.Target.Root != dir.Root || !strings.EqualFold(relpath.Dir(f.Target.Rel), dir.Rel) {
			continue
		}
		name := relpath.Base(f.Target.Rel)
		if !relpath.MatchAny(lo.PluginGlobs, name) || implicit[strings.ToLower(name)] {
			continue
		}
		seen[strings.ToLower(name)] = true
		plugins = append(plugins, pl{name: name, modIdx: f.ModIndex, modID: f.ModID, target: f.Target, fromMod: true})
	}
	// plugins already in the game folder (installed by hand, DLC)
	var external []pl
	if in.ListDir != nil {
		names, _ := in.ListDir(dir)
		sort.Strings(names)
		for _, n := range names {
			if relpath.MatchAny(lo.PluginGlobs, n) && !seen[strings.ToLower(n)] && !implicit[strings.ToLower(n)] {
				external = append(external, pl{name: n, modIdx: -1})
				seen[strings.ToLower(n)] = true
			}
		}
	}
	all := append(external, plugins...)
	// automatic order: masters first, otherwise stable (external, then mod order)
	sort.SliceStable(all, func(i, j int) bool {
		if lo.SortHints == "masters-first" && isMaster(all[i].name) != isMaster(all[j].name) {
			return isMaster(all[i].name)
		}
		return all[i].modIdx < all[j].modIdx
	})
	enabled := map[string]bool{}
	for _, p := range all {
		enabled[strings.ToLower(p.name)] = true
	}
	// the profile's own order wins for the plugins it lists
	if len(in.Order) > 0 {
		pos := map[string]int{}
		for i, p := range in.Order {
			pos[strings.ToLower(p.Name)] = i
			if _, ok := enabled[strings.ToLower(p.Name)]; ok {
				enabled[strings.ToLower(p.Name)] = p.Enabled
			}
		}
		sort.SliceStable(all, func(i, j int) bool {
			pi, iok := pos[strings.ToLower(all[i].name)]
			pj, jok := pos[strings.ToLower(all[j].name)]
			switch {
			case iok && jok:
				return pi < pj
			case iok != jok:
				return iok // listed ones first, new ones after
			}
			return false
		})
		if lo.SortHints == "masters-first" {
			sort.SliceStable(all, func(i, j int) bool { return isMaster(all[i].name) && !isMaster(all[j].name) })
		}
	}
	for _, n := range implicitOrder {
		out.Plugins = append(out.Plugins, PluginInfo{Name: n, Enabled: true, Implicit: true, Master: isMaster(n)})
	}
	for _, p := range all {
		out.Plugins = append(out.Plugins, PluginInfo{Name: p.name, Enabled: enabled[strings.ToLower(p.name)], External: !p.fromMod, Master: isMaster(p.name), ModID: p.modID})
	}
	full := 0
	for _, p := range out.Plugins {
		if p.Enabled && !strings.HasSuffix(strings.ToLower(p.Name), ".esl") {
			full++
		}
	}
	if lo.MaxFullPlugins > 0 && full > lo.MaxFullPlugins {
		out.Warnings = append(out.Warnings, fmt.Sprintf("Włączonych pełnych pluginów: %d – gra obsługuje najwyżej %d.", full, lo.MaxFullPlugins))
	}

	enc := func(s string) ([]byte, error) { return encode(s, lo.Encoding) }
	var lines, order []string
	for _, p := range all {
		on := enabled[strings.ToLower(p.name)]
		switch lo.Format {
		case "asterisk":
			if on {
				lines = append(lines, "*"+p.name)
			} else {
				lines = append(lines, p.name)
			}
		default:
			if on {
				lines = append(lines, p.name)
			}
		}
		order = append(order, p.name)
	}
	switch lo.Format {
	case "asterisk", "active-only", "textfile", "timestamp":
		file, err := in.Res.Location(lo.File)
		if err != nil {
			return err
		}
		b, err := enc(crlf(lines))
		if err != nil {
			return err
		}
		out.Files = append(out.Files, Generated{Target: file, Content: b})
		if lo.Format == "textfile" && lo.SecondaryFile != "" {
			sec, err := in.Res.Location(lo.SecondaryFile)
			if err != nil {
				return err
			}
			full := append(append([]string{}, implicitOrder...), order...)
			b, err := enc(crlf(full))
			if err != nil {
				return err
			}
			out.Files = append(out.Files, Generated{Target: sec, Content: b})
		}
	case "ini-gamefile":
		file, err := in.Res.Location(lo.File)
		if err != nil {
			return err
		}
		var cur []byte
		if in.ReadFile != nil {
			cur, _ = in.ReadFile(file)
		}
		var active []string
		for _, p := range out.Plugins {
			if p.Enabled {
				active = append(active, p.Name)
			}
		}
		ini, err := setGameFiles(cur, active)
		if err != nil {
			return err
		}
		b, err := enc(ini)
		if err != nil {
			return err
		}
		out.Files = append(out.Files, Generated{Target: file, Content: b})
	default:
		return fmt.Errorf("nieznany format pliku pluginów %q", lo.Format)
	}
	// games that order by modification time: one minute apart, in order
	if lo.Format == "timestamp" || lo.Format == "ini-gamefile" || lo.Format == "active-only" || lo.Format == "textfile" {
		base := time.Date(2002, 1, 1, 12, 0, 0, 0, time.UTC)
		for i, p := range all {
			if p.fromMod {
				out.MTimes[p.target.Key()] = base.Add(time.Duration(i+1) * time.Minute)
			}
		}
	}
	return nil
}

func crlf(lines []string) string {
	if len(lines) == 0 {
		return ""
	}
	return strings.Join(lines, "\r\n") + "\r\n"
}

var gameFileLine = regexp.MustCompile(`(?i)^\s*GameFile\d+\s*=`)

// setGameFiles rewrites the [Game Files] section of Morrowind.ini and keeps
// everything else (line endings included).
func setGameFiles(cur []byte, active []string) (string, error) {
	text := string(cur)
	nl := "\r\n"
	if len(cur) > 0 && !bytes.Contains(cur, []byte("\r\n")) {
		nl = "\n"
	}
	lines := strings.Split(strings.ReplaceAll(text, "\r\n", "\n"), "\n")
	var out []string
	inSection, done := false, false
	emit := func() {
		for i, n := range active {
			out = append(out, fmt.Sprintf("GameFile%d=%s", i, n))
		}
		done = true
	}
	for _, l := range lines {
		t := strings.TrimSpace(l)
		if strings.HasPrefix(t, "[") {
			if inSection && !done {
				emit()
			}
			inSection = strings.EqualFold(t, "[Game Files]")
			out = append(out, l)
			continue
		}
		if inSection && gameFileLine.MatchString(l) {
			continue
		}
		out = append(out, l)
	}
	if inSection && !done {
		// section at the end: put the entries before trailing empty lines
		trail := 0
		for trail < len(out) && strings.TrimSpace(out[len(out)-1-trail]) == "" {
			trail++
		}
		tail := append([]string{}, out[len(out)-trail:]...)
		out = out[:len(out)-trail]
		emit()
		out = append(out, tail...)
	}
	if !done {
		if len(out) > 0 && out[len(out)-1] == "" {
			out = out[:len(out)-1]
		}
		out = append(out, "[Game Files]")
		emit()
		out = append(out, "")
	}
	return strings.Join(out, nl), nil
}

// cp1252 high half (0x80-0x9F); 0xA0-0xFF equal Latin-1.
var cp1252 = map[rune]byte{
	'€': 0x80, '‚': 0x82, 'ƒ': 0x83, '„': 0x84, '…': 0x85, '†': 0x86, '‡': 0x87, 'ˆ': 0x88, '‰': 0x89, 'Š': 0x8A, '‹': 0x8B, 'Œ': 0x8C, 'Ž': 0x8E,
	'‘': 0x91, '’': 0x92, '“': 0x93, '”': 0x94, '•': 0x95, '–': 0x96, '—': 0x97, '˜': 0x98, '™': 0x99, 'š': 0x9A, '›': 0x9B, 'œ': 0x9C, 'ž': 0x9E, 'Ÿ': 0x9F,
}

func encode(s, enc string) ([]byte, error) {
	switch enc {
	case "", "utf-8":
		return []byte(s), nil
	case "utf-8-bom":
		return append([]byte{0xef, 0xbb, 0xbf}, s...), nil
	case "windows-1252":
		var b bytes.Buffer
		for _, r := range s {
			switch {
			case r < 0x80 || (r >= 0xA0 && r <= 0xFF):
				b.WriteByte(byte(r))
			default:
				c, ok := cp1252[r]
				if !ok {
					return nil, fmt.Errorf("nazwy %q nie da się zapisać w kodowaniu Windows-1252 (gra jej nie odczyta) – zmień nazwę pliku pluginu", s)
				}
				b.WriteByte(c)
			}
		}
		return b.Bytes(), nil
	}
	return nil, fmt.Errorf("nieznane kodowanie %q", enc)
}

// ------------------------------------------------------------- Cyberpunk

// cyberpunk: modlist.txt lists .archive files, the first one has the
// highest priority; in the profile the later mod wins, so it goes first.
func cyberpunk(in Input, out *Output) error {
	lo := in.Def.LoadOrder
	file, err := in.Res.Location(lo.File)
	if err != nil {
		return err
	}
	dir := gamedef.Location{Root: file.Root, Rel: relpath.Dir(file.Rel)}
	type a struct {
		name string
		idx  int
	}
	var list []a
	for _, f := range in.Files {
		if f.Target.Root == dir.Root && strings.EqualFold(relpath.Dir(f.Target.Rel), dir.Rel) && relpath.MatchAny(lo.PluginGlobs, relpath.Base(f.Target.Rel)) {
			list = append(list, a{relpath.Base(f.Target.Rel), f.ModIndex})
		}
	}
	if len(list) == 0 {
		return nil
	}
	sort.SliceStable(list, func(i, j int) bool {
		if list[i].idx != list[j].idx {
			return list[i].idx > list[j].idx
		}
		return strings.ToLower(list[i].name) < strings.ToLower(list[j].name)
	})
	var names []string
	for _, x := range list {
		names = append(names, x.name)
		out.Plugins = append(out.Plugins, PluginInfo{Name: x.name, Enabled: true})
	}
	out.Files = append(out.Files, Generated{Target: file, Content: []byte(strings.Join(names, "\n") + "\n")})
	return nil
}

// ------------------------------------------------------------- Witcher 3

var w3Section = regexp.MustCompile(`^\s*\[(.+)\]\s*$`)

// witcher3: mods.settings, lower Priority wins; the last mod in the profile
// gets 0. Sections of mods we did not deploy are kept.
func witcher3(in Input, out *Output) error {
	lo := in.Def.LoadOrder
	file, err := in.Res.Location(lo.File)
	if err != nil {
		return err
	}
	modsDir, err := in.Res.Location("{game}/Mods")
	if err != nil {
		return err
	}
	type m struct {
		name string
		idx  int
	}
	var ours []m
	seen := map[string]bool{}
	for _, f := range in.Files {
		if f.Target.Root != modsDir.Root || !relpath.HasPrefixDir(f.Target.Rel, modsDir.Rel) {
			continue
		}
		rest := relpath.TrimDir(f.Target.Rel, modsDir.Rel)
		name := strings.SplitN(rest, "/", 2)[0]
		if name == "" || seen[strings.ToLower(name)] {
			continue
		}
		seen[strings.ToLower(name)] = true
		ours = append(ours, m{name, f.ModIndex})
	}
	if len(ours) == 0 {
		return nil
	}
	sort.SliceStable(ours, func(i, j int) bool { return ours[i].idx > ours[j].idx })
	// keep sections of other mods
	var kept []string
	if in.ReadFile != nil {
		if cur, err := in.ReadFile(file); err == nil {
			skip := false
			for _, l := range strings.Split(strings.ReplaceAll(string(cur), "\r\n", "\n"), "\n") {
				if mm := w3Section.FindStringSubmatch(l); mm != nil {
					skip = seen[strings.ToLower(strings.TrimSpace(mm[1]))]
				}
				if !skip && strings.TrimSpace(l) != "" {
					kept = append(kept, l)
				}
			}
		}
	}
	var b strings.Builder
	for i, o := range ours {
		fmt.Fprintf(&b, "[%s]\r\nEnabled=1\r\nPriority=%d\r\n\r\n", o.name, i)
		out.Plugins = append(out.Plugins, PluginInfo{Name: o.name, Enabled: true})
	}
	if len(kept) > 0 {
		b.WriteString(strings.Join(kept, "\r\n"))
		b.WriteString("\r\n")
	}
	out.Files = append(out.Files, Generated{Target: file, Content: []byte(b.String())})
	return nil
}

// ------------------------------------------------------------- RimWorld

var (
	activeModsRe = regexp.MustCompile(`(?s)<activeMods>(.*?)</activeMods>`)
	liRe         = regexp.MustCompile(`(?s)<li>\s*(.*?)\s*</li>`)
	packageIDRe  = regexp.MustCompile(`(?s)<packageId>\s*(.*?)\s*</packageId>`)
)

// rimworld: activeMods in ModsConfig.xml; entries we did not deploy (core,
// DLC, Workshop) keep their place at the top, our mods follow in order.
func rimworld(in Input, out *Output) error {
	lo := in.Def.LoadOrder
	file, err := in.Res.Location(lo.File)
	if err != nil {
		return err
	}
	var cur []byte
	if in.ReadFile != nil {
		cur, _ = in.ReadFile(file)
	}
	if len(cur) == 0 {
		out.Warnings = append(out.Warnings, "Brak ModsConfig.xml – uruchom grę raz bez modów, żeby go utworzyła; mody są wdrożone, ale nie zostały włączone.")
		return nil
	}
	// our mods: About/About.xml of each deployed mod folder
	type m struct {
		id  string
		idx int
	}
	var ours []m
	seen := map[string]bool{}
	for _, f := range in.Files {
		if !strings.EqualFold(relpath.Base(f.Target.Rel), "About.xml") || !strings.EqualFold(relpath.Base(relpath.Dir(f.Target.Rel)), "About") {
			continue
		}
		b, err := os.ReadFile(f.SourceAbs)
		if err != nil || len(b) > 1<<20 {
			continue
		}
		mm := packageIDRe.FindSubmatch(b)
		if mm == nil {
			out.Warnings = append(out.Warnings, "About.xml bez <packageId>: "+f.Target.Rel)
			continue
		}
		id := strings.ToLower(strings.TrimSpace(string(mm[1])))
		if !seen[id] {
			seen[id] = true
			ours = append(ours, m{id, f.ModIndex})
		}
	}
	sort.SliceStable(ours, func(i, j int) bool { return ours[i].idx < ours[j].idx })
	loc := activeModsRe.FindSubmatchIndex(cur)
	if loc == nil {
		return fmt.Errorf("ModsConfig.xml nie ma sekcji <activeMods>")
	}
	inner := cur[loc[2]:loc[3]]
	indent := "    "
	if i := bytes.Index(inner, []byte("<li>")); i > 0 {
		j := bytes.LastIndexByte(inner[:i], '\n')
		indent = string(inner[j+1 : i])
	}
	nl := "\n"
	if bytes.Contains(cur, []byte("\r\n")) {
		nl = "\r\n"
	}
	var ids []string
	for _, mm := range liRe.FindAllSubmatch(inner, -1) {
		id := strings.ToLower(strings.TrimSpace(string(mm[1])))
		if !seen[id] {
			ids = append(ids, id)
		}
	}
	for _, o := range ours {
		ids = append(ids, o.id)
	}
	var b strings.Builder
	b.WriteString(nl)
	for _, id := range ids {
		b.WriteString(indent + "<li>" + xmlEscape(id) + "</li>" + nl)
		out.Plugins = append(out.Plugins, PluginInfo{Name: id, Enabled: true, External: !seen[id]})
	}
	closeIndent := ""
	if j := bytes.LastIndexByte(inner, '\n'); j >= 0 {
		closeIndent = string(inner[j+1:])
	}
	b.WriteString(closeIndent)
	res := append(append(append([]byte{}, cur[:loc[2]]...), b.String()...), cur[loc[3]:]...)
	out.Files = append(out.Files, Generated{Target: file, Content: res})
	return nil
}

func xmlEscape(s string) string {
	r := strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", `"`, "&quot;")
	return r.Replace(s)
}

// ------------------------------------------------------------- launch args

// LaunchArgs builds arguments from the definition's argTemplate:
// "{iwad}" is replaced by iwad (the pair is dropped when empty) and
// "{files:*.wad,*.pk3...}" by the matching store files in mod order (the
// preceding flag is dropped when nothing matches).
func LaunchArgs(def *gamedef.Definition, files []Placed, iwad string) []string {
	tpl := def.LoadOrder.ArgTemplate
	var out []string
	for i := 0; i < len(tpl); i++ {
		a := tpl[i]
		next := ""
		if i+1 < len(tpl) {
			next = tpl[i+1]
		}
		if strings.HasPrefix(a, "-") && (next == "{iwad}" || strings.HasPrefix(next, "{files:")) {
			vals := expandArg(next, files, iwad)
			if len(vals) > 0 {
				out = append(out, a)
				out = append(out, vals...)
			}
			i++
			continue
		}
		out = append(out, expandArg(a, files, iwad)...)
	}
	return out
}

func expandArg(a string, files []Placed, iwad string) []string {
	switch {
	case a == "{iwad}":
		if iwad == "" {
			return nil
		}
		return []string{iwad}
	case strings.HasPrefix(a, "{files:"):
		spec := strings.TrimSuffix(strings.TrimPrefix(a, "{files:"), "}")
		spec = strings.TrimSuffix(spec, "...")
		globs := strings.Split(spec, ",")
		var out []string
		for _, f := range files {
			if relpath.MatchAny(globs, relpath.Base(f.Target.Rel)) {
				out = append(out, f.SourceAbs)
			}
		}
		return out
	}
	return []string{a}
}
