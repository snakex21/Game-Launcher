// Package install decides where the files of a mod source go: it finds the
// mod's root inside an archive (wrapper folders, "Data/" on top, several
// mod types), understands package formats (Thunderstore manifest.json,
// SMAPI manifest folders) and produces a deterministic plan:
// archive path -> (mod type, path inside the type's target).
package install

import (
	"encoding/json"
	"fmt"
	"path"
	"regexp"
	"sort"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/modmgr/archive"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// Options steer planning (all optional).
type Options struct {
	ModName    string // display name; default from the source name
	SourceName string // file/folder name of the source (for names, namespaces)
	Root       string // forced root folder inside the archive ("" = auto, "/" = archive root)
	ModType    string // forced mod type id
	// Read returns a small file from the source (manifests); may be nil.
	Read func(path string) ([]byte, error)
	// TargetHasDir reports whether a folder exists in the target folder of
	// a mod type (a top folder that the game already has is not a wrapper).
	TargetHasDir func(modType, dir string) bool
}

// File is one planned file.
type File struct {
	Source  string `json:"source"`  // path in the archive
	ModType string `json:"modType"` // mod type id
	Rel     string `json:"rel"`     // path inside the type's target (subfolder included)
}

// Candidate is a possible (root, type) choice shown to the user.
type Candidate struct {
	Root    string `json:"root"` // "" = archive root
	ModType string `json:"modType"`
	Score   int    `json:"score"`
}

// Plan is the result.
type Plan struct {
	ModName           string      `json:"modName"`
	Version           string      `json:"version,omitempty"`
	Files             []File      `json:"files"`
	Skipped           []string    `json:"skipped,omitempty"` // ignored or outside the root
	Root              string      `json:"root"`
	ModType           string      `json:"modType"` // main type ("" for package formats with several)
	Format            string      `json:"format"`  // heuristic|manual|thunderstore|smapi-manifest
	Ambiguous         bool        `json:"ambiguous"`
	Candidates        []Candidate `json:"candidates,omitempty"`
	ExecutableContent bool        `json:"executableContent"`
	ExecutableFiles   []string    `json:"executableFiles,omitempty"`
	HasFomod          bool        `json:"hasFomod"`
	HasInstaller      bool        `json:"hasInstaller"` // .exe/.msi/.bat in the archive (never run)
	Warnings          []string    `json:"warnings,omitempty"`
	Dirs              []string    `json:"dirs,omitempty"` // archive folders (for manual root choice)
}

var defaultIgnore = []string{"__MACOSX/**", ".DS_Store", "Thumbs.db", "desktop.ini", "*.gl-new"}

// executable extensions (§5.3)
var execExt = map[string]bool{
	".dll": true, ".asi": true, ".exe": true, ".so": true, ".jar": true, ".lua": true, ".cs": true, ".reds": true,
	".ws": true, ".py": true, ".ps1": true, ".bat": true, ".cmd": true, ".js": true, ".vbs": true, ".msi": true, ".com": true, ".scr": true,
}

var installerExt = map[string]bool{".exe": true, ".msi": true, ".bat": true, ".cmd": true, ".ps1": true, ".vbs": true}

// tree is the folder structure of the source.
type tree struct {
	files    []string            // all kept files
	children map[string][]string // dir -> child names (dirs and files), "" = root
	isDir    map[string]bool     // lower path -> true for dirs
	dirs     []string
}

func buildTree(files []string) *tree {
	t := &tree{files: files, children: map[string][]string{}, isDir: map[string]bool{"": true}}
	seenChild := map[string]bool{}
	for _, f := range files {
		parts := strings.Split(f, "/")
		cur := ""
		for i, p := range parts {
			next := relpath.Join(cur, p)
			key := relpath.Key(cur) + "|" + strings.ToLower(p)
			if !seenChild[key] {
				seenChild[key] = true
				t.children[relpath.Key(cur)] = append(t.children[relpath.Key(cur)], p)
			}
			if i < len(parts)-1 {
				if !t.isDir[relpath.Key(next)] {
					t.isDir[relpath.Key(next)] = true
					t.dirs = append(t.dirs, next)
				}
			}
			cur = next
		}
	}
	sort.Strings(t.dirs)
	return t
}

func depth(dir string) int {
	if dir == "" {
		return 0
	}
	return strings.Count(dir, "/") + 1
}

// filesUnder lists files inside dir (relative to dir).
func (t *tree) filesUnder(dir string) []string {
	var out []string
	for _, f := range t.files {
		if dir == "" {
			out = append(out, f)
		} else if relpath.HasPrefixDir(f, dir) && len(f) > len(dir) {
			out = append(out, relpath.TrimDir(f, dir))
		}
	}
	return out
}

// Make plans the installation of the given entries for a game definition.
func Make(entries []archive.Entry, def *gamedef.Definition, opt Options) (*Plan, error) {
	plan := &Plan{Format: "heuristic"}
	ignore := append(append([]string{}, defaultIgnore...), def.Installer.IgnoreGlobs...)
	var kept []string
	for _, e := range entries {
		low := strings.ToLower(e.Path)
		if low == "fomod/moduleconfig.xml" || strings.HasSuffix(low, "/fomod/moduleconfig.xml") && strings.Count(low, "/") <= 2 {
			plan.HasFomod = true
		}
		if installerExt[strings.ToLower(path.Ext(e.Path))] && !strings.Contains(low, "/") {
			plan.HasInstaller = true
		}
		if relpath.MatchAny(ignore, e.Path) || matchAnyDeep(ignore, e.Path) {
			plan.Skipped = append(plan.Skipped, e.Path)
			continue
		}
		kept = append(kept, e.Path)
	}
	if len(kept) == 0 {
		return nil, fmt.Errorf("źródło nie zawiera plików do zainstalowania")
	}
	t := buildTree(kept)
	plan.Dirs = t.dirs
	plan.ModName = opt.ModName
	if plan.ModName == "" {
		plan.ModName = nameFromSource(opt.SourceName)
	}
	if plan.HasFomod {
		plan.Warnings = append(plan.Warnings, "Archiwum ma instalator FOMOD – kreator FOMOD nie jest jeszcze obsługiwany. Sprawdź podgląd i w razie potrzeby wskaż folder z właściwym wariantem ręcznie.")
	}

	manual := opt.Root != "" || opt.ModType != ""
	if !manual {
		switch def.Installer.PackageFormat {
		case "thunderstore":
			if ok := planThunderstore(t, def, opt, plan); ok {
				return finish(plan, def), nil
			}
		case "smapi-manifest":
			if ok := planManifestFolders(t, def, plan, "manifest.json"); ok {
				return finish(plan, def), nil
			}
		}
	}

	cands := scoreAll(t, def)
	plan.Candidates = topCandidates(cands, 6)
	var root, typ string
	switch {
	case manual:
		plan.Format = "manual"
		root = strings.Trim(opt.Root, "/")
		if opt.Root == "/" {
			root = ""
		}
		if root != "" && !t.isDir[relpath.Key(root)] {
			return nil, fmt.Errorf("w źródle nie ma folderu %q", root)
		}
		typ = opt.ModType
		if typ == "" {
			typ = bestTypeFor(cands, root, def)
		}
	case len(cands) > 0 && cands[0].Score > 0:
		root, typ = cands[0].Root, cands[0].ModType
		if len(cands) > 1 && cands[0].Score-cands[1].Score < 3 {
			plan.Ambiguous = true
		}
	default:
		// nothing recognisable: archive root (minus a single wrapper folder), default type
		typ = def.DefaultModType().ID
		root = stripWrapper(t, "")
		if root != "" && opt.TargetHasDir != nil && opt.TargetHasDir(typ, root) {
			root = ""
		}
		plan.Ambiguous = !def.IsGeneric() || root != ""
	}
	mt := def.ModType(typ)
	if mt == nil {
		return nil, fmt.Errorf("nieznany typ moda %q", typ)
	}
	plan.Root, plan.ModType = root, typ
	folder := folderName(root, plan.ModName, def, mt)
	sub, err := subfolder(def, mt, folder, plan.ModName, "")
	if err != nil {
		return nil, err
	}
	for _, f := range t.files {
		if !relpath.HasPrefixDir(f, root) || (root != "" && len(f) == len(root)) {
			plan.Skipped = append(plan.Skipped, f)
			continue
		}
		rel := relpath.TrimDir(f, root)
		if mt.Flatten {
			if !includedFlat(mt, rel) {
				plan.Skipped = append(plan.Skipped, f)
				continue
			}
			rel = relpath.Base(rel)
		} else if (len(mt.IncludeGlobs) > 0 && !relpath.MatchAny(mt.IncludeGlobs, rel)) || relpath.MatchAny(mt.ExcludeGlobs, rel) {
			// a mod of several kinds (Starfield: plugins to Data, loose files
			// to Documents): the rest goes to the default type
			if dt := def.DefaultModType(); dt != nil && dt.ID != mt.ID && !dt.Flatten && dt.PerModSubfolder == "" &&
				(len(dt.IncludeGlobs) == 0 || relpath.MatchAny(dt.IncludeGlobs, rel)) && !relpath.MatchAny(dt.ExcludeGlobs, rel) {
				plan.Files = append(plan.Files, File{Source: f, ModType: dt.ID, Rel: rel})
				continue
			}
			plan.Skipped = append(plan.Skipped, f)
			continue
		}
		plan.Files = append(plan.Files, File{Source: f, ModType: typ, Rel: relpath.Join(sub, rel)})
	}
	if len(plan.Files) == 0 {
		return nil, fmt.Errorf("w wybranym folderze nie ma plików pasujących do typu %q", mt.Name)
	}
	return finish(plan, def), nil
}

func includedFlat(mt *gamedef.ModType, rel string) bool {
	globs := mt.IncludeGlobs
	if len(globs) == 0 && mt.Match != nil {
		globs = mt.Match.AnyFiles
	}
	if len(globs) == 0 {
		return true
	}
	return relpath.MatchAny(globs, relpath.Base(rel)) && !relpath.MatchAny(mt.ExcludeGlobs, rel)
}

func matchAnyDeep(globs []string, p string) bool {
	// patterns like "readme*" should also hit "Wrapper/readme.txt" at shallow depth
	for _, g := range globs {
		if !strings.Contains(g, "/") {
			continue
		}
		parts := strings.Split(p, "/")
		for i := 1; i < len(parts) && i <= 2; i++ {
			if relpath.Match(g, strings.Join(parts[i:], "/")) {
				return true
			}
		}
	}
	return false
}

// finish computes executable flags and sorts files.
func finish(p *Plan, def *gamedef.Definition) *Plan {
	sort.Slice(p.Files, func(i, j int) bool {
		if p.Files[i].ModType != p.Files[j].ModType {
			return p.Files[i].ModType < p.Files[j].ModType
		}
		return p.Files[i].Rel < p.Files[j].Rel
	})
	seen := map[string]bool{}
	for _, f := range p.Files {
		mt := def.ModType(f.ModType)
		if execExt[strings.ToLower(path.Ext(f.Rel))] || (mt != nil && mt.ExecutableContent && execExt[strings.ToLower(path.Ext(f.Rel))]) {
			p.ExecutableContent = true
			if len(p.ExecutableFiles) < 20 && !seen[f.Rel] {
				seen[f.Rel] = true
				p.ExecutableFiles = append(p.ExecutableFiles, f.Rel)
			}
		}
	}
	if p.HasInstaller {
		p.Warnings = append(p.Warnings, "Archiwum zawiera program instalacyjny (.exe/.msi/.bat). Menedżer nigdy go nie uruchamia – jeśli mod wymaga instalatora, sprawdź instrukcję autora.")
	}
	sort.Strings(p.Skipped)
	return p
}

var versionSuffix = regexp.MustCompile(`(?i)[-_ ]v?\d+(\.\d+)+.*$`)

func nameFromSource(src string) string {
	n := path.Base(strings.ReplaceAll(src, `\`, "/"))
	low := strings.ToLower(n)
	for _, ext := range []string{".zip", ".7z", ".rar"} {
		if strings.HasSuffix(low, ext) {
			n = n[:len(n)-len(ext)]
			break
		}
	}
	if s := versionSuffix.ReplaceAllString(n, ""); s != "" {
		n = s
	}
	n = strings.TrimSpace(n)
	if n == "" || n == "." || n == "/" {
		n = "Mod"
	}
	return n
}

// safeFolder makes a name usable as a single folder name.
func safeFolder(name string) string {
	var b strings.Builder
	for _, r := range name {
		switch {
		case r < 0x20, strings.ContainsRune(`<>:"/\|?*`, r):
			b.WriteRune('_')
		default:
			b.WriteRune(r)
		}
	}
	s := strings.TrimRight(strings.TrimSpace(b.String()), ". ")
	if _, err := relpath.Clean(s); err != nil || s == "" {
		return "Mod"
	}
	return s
}

func folderName(root, modName string, def *gamedef.Definition, mt *gamedef.ModType) string {
	name := ""
	if root != "" {
		name = relpath.Base(root)
	} else {
		name = safeFolder(modName)
	}
	if def.Adapter == "witcher3" && mt.ID == "mod" && !strings.HasPrefix(strings.ToLower(name), "mod") {
		name = "mod" + name
	}
	return name
}

// subfolder expands the perModSubfolder template ("" when the type has none).
func subfolder(def *gamedef.Definition, mt *gamedef.ModType, folder, name, namespace string) (string, error) {
	if mt.PerModSubfolder == "" {
		return "", nil
	}
	if namespace == "" {
		namespace = "mod"
	}
	r := &gamedef.Resolver{Def: def, Vars: map[string]string{
		"mod.folderName": folder, "mod.name": safeFolder(name), "mod.namespace": safeFolder(namespace), "mod.id": safeFolder(name),
	}}
	s, err := r.Expand(mt.PerModSubfolder)
	if err != nil {
		return "", err
	}
	return relpath.Clean(safeFolder(s))
}

// stripWrapper descends into a folder that is the only child (one level).
func stripWrapper(t *tree, dir string) string {
	for i := 0; i < 1; i++ {
		ch := t.children[relpath.Key(dir)]
		if len(ch) != 1 {
			break
		}
		next := relpath.Join(dir, ch[0])
		if !t.isDir[relpath.Key(next)] {
			break
		}
		dir = next
	}
	return dir
}

// ------------------------------------------------------------- scoring

func lastSegment(target string) string {
	t := strings.TrimRight(strings.ReplaceAll(target, `\`, "/"), "/")
	if i := strings.LastIndexByte(t, '/'); i >= 0 {
		t = t[i+1:]
	}
	if strings.HasPrefix(t, "{") {
		return ""
	}
	return t
}

func dataDirName(def *gamedef.Definition, mt *gamedef.ModType) string {
	t := mt.Target
	if strings.HasPrefix(t, "{paths.") {
		if end := strings.IndexByte(t, '}'); end > 0 {
			if v, ok := def.Paths[t[7:end]]; ok {
				t = v + t[end+1:]
			}
		}
	}
	return lastSegment(t)
}

func scoreAll(t *tree, def *gamedef.Definition) []Candidate {
	maxDepth := def.Installer.MaxRootSearchDepth
	if maxDepth <= 0 {
		maxDepth = 2
	}
	dirs := append([]string{""}, t.dirs...)
	var out []Candidate
	for i := range def.ModTypes {
		mt := &def.ModTypes[i]
		for _, d := range dirs {
			if depth(d) > maxDepth {
				continue
			}
			if s, ok := score(t, def, mt, d); ok && !pureWrapper(t, mt, d) {
				out = append(out, Candidate{Root: d, ModType: mt.ID, Score: s})
			}
			// "Data/" on top of a Bethesda mod etc.: offer the folder itself
			if mt.PerModSubfolder == "" {
				if want := dataDirName(def, mt); want != "" {
					for _, ch := range t.children[relpath.Key(d)] {
						sub := relpath.Join(d, ch)
						if strings.EqualFold(ch, want) && t.isDir[relpath.Key(sub)] {
							if s2, ok := score(t, def, mt, sub); ok {
								out = append(out, Candidate{Root: sub, ModType: mt.ID, Score: s2 + 4})
							}
						}
					}
				}
			}
		}
	}
	// keep the best score per (root,type)
	best := map[string]Candidate{}
	for _, c := range out {
		k := relpath.Key(c.Root) + "|" + c.ModType
		if b, ok := best[k]; !ok || c.Score > b.Score {
			best[k] = c
		}
	}
	out = out[:0]
	for _, c := range best {
		out = append(out, c)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Score != out[j].Score {
			return out[i].Score > out[j].Score
		}
		pi, pj := def.ModType(out[i].ModType).Priority, def.ModType(out[j].ModType).Priority
		if pi != pj {
			return pi < pj
		}
		if depth(out[i].Root) != depth(out[j].Root) {
			return depth(out[i].Root) < depth(out[j].Root)
		}
		return out[i].Root < out[j].Root
	})
	return out
}

// pureWrapper: d only holds one folder that means nothing to the type.
func pureWrapper(t *tree, mt *gamedef.ModType, d string) bool {
	ch := t.children[relpath.Key(d)]
	if len(ch) != 1 || !t.isDir[relpath.Key(relpath.Join(d, ch[0]))] {
		return false
	}
	return !relpath.MatchAny(mt.RootMarkers, ch[0])
}

func topCandidates(c []Candidate, n int) []Candidate {
	if len(c) > n {
		c = c[:n]
	}
	return append([]Candidate(nil), c...)
}

func bestTypeFor(cands []Candidate, root string, def *gamedef.Definition) string {
	for _, c := range cands {
		if strings.EqualFold(c.Root, root) {
			return c.ModType
		}
	}
	return def.DefaultModType().ID
}

func score(t *tree, def *gamedef.Definition, mt *gamedef.ModType, d string) (int, bool) {
	under := t.filesUnder(d)
	if len(under) == 0 {
		return 0, false
	}
	s := -depth(d)
	hasCriteria := len(mt.RootMarkers) > 0 || mt.Match != nil
	if !hasCriteria {
		return -100, true // only reachable through the fallback/manual choice
	}
	for _, ch := range t.children[relpath.Key(d)] {
		if relpath.MatchAny(mt.RootMarkers, ch) {
			s += 3
		} else {
			s -= 2
		}
	}
	if mt.Match != nil && matches(t, mt.Match, d, under) {
		s += 5
	}
	// files of the source that this choice would leave out
	outside := len(t.files) - len(under)
	if mt.Flatten {
		for _, f := range under {
			if !includedFlat(mt, f) {
				outside++
			}
		}
	}
	s -= min(outside*2, 12)
	return s, true
}

func matches(t *tree, m *gamedef.Match, d string, under []string) bool {
	near := func(f string) bool { return strings.Count(f, "/") <= 1 }
	fileMatch := func(p string) bool {
		for _, f := range under {
			if strings.Contains(p, "/") {
				if relpath.Match(p, f) {
					return true
				}
			} else if near(f) && relpath.Match(p, f) {
				return true
			}
		}
		return false
	}
	any := false
	if len(m.AnyFiles) > 0 {
		ok := false
		for _, p := range m.AnyFiles {
			if fileMatch(p) {
				ok = true
				break
			}
		}
		if !ok {
			return false
		}
		any = true
	}
	for _, p := range m.AllFiles {
		if !fileMatch(p) {
			return false
		}
		any = true
	}
	if len(m.AnyDirs) > 0 {
		ok := false
		for _, dir := range t.dirs {
			if !relpath.HasPrefixDir(dir, d) || strings.EqualFold(dir, d) {
				continue
			}
			rel := relpath.TrimDir(dir, d)
			if strings.Count(rel, "/") > 1 {
				continue
			}
			if relpath.MatchAny(m.AnyDirs, rel) {
				ok = true
				break
			}
		}
		if !ok {
			return false
		}
		any = true
	}
	if m.ManifestFile != "" {
		ok := false
		for _, f := range under {
			if strings.EqualFold(f, m.ManifestFile) {
				ok = true
			}
		}
		if !ok {
			return false
		}
		any = true
	}
	return any
}

// ------------------------------------------------------------- package formats

type tsManifest struct {
	Name          string   `json:"name"`
	VersionNumber string   `json:"version_number"`
	Author        string   `json:"author"`
	Dependencies  []string `json:"dependencies"`
}

func planThunderstore(t *tree, def *gamedef.Definition, opt Options, plan *Plan) bool {
	pkg := ""
	found := false
	for _, cand := range []string{"", stripWrapper(t, "")} {
		for _, f := range t.files {
			if strings.EqualFold(f, relpath.Join(cand, "manifest.json")) {
				pkg, found = cand, true
				break
			}
		}
		if found {
			break
		}
	}
	if !found {
		return false
	}
	var man tsManifest
	if opt.Read != nil {
		if b, err := opt.Read(relpath.Join(pkg, "manifest.json")); err == nil {
			_ = json.Unmarshal(trimBOM(b), &man)
		}
	}
	name := safeFolder(man.Name)
	if man.Name == "" {
		name = safeFolder(plan.ModName)
	}
	ns := namespaceFrom(opt.SourceName, man.Name)
	if ns == "" {
		ns = man.Author
	}
	if opt.ModName == "" && man.Name != "" {
		plan.ModName = strings.ReplaceAll(man.Name, "_", " ")
	}
	plan.Version = man.VersionNumber
	plan.Format, plan.Root = "thunderstore", pkg

	// BepInExPack: the loader sits in a sub folder with winhttp.dll
	packRoot := ""
	for _, ch := range t.children[relpath.Key(pkg)] {
		sub := relpath.Join(pkg, ch)
		if !t.isDir[relpath.Key(sub)] {
			continue
		}
		for _, f := range t.filesUnder(sub) {
			lf := strings.ToLower(f)
			if lf == "winhttp.dll" || lf == "doorstop_config.ini" {
				packRoot = sub
			}
		}
	}
	typ := func(id string) *gamedef.ModType { return def.ModType(id) }
	plugin, patcher, config, pack := typ("bepinex-plugin"), typ("bepinex-patcher"), typ("bepinex-config"), typ("bepinex-pack")
	if plugin == nil || pack == nil {
		return false
	}
	sub := func(mt *gamedef.ModType) string {
		s, err := subfolder(def, mt, name, name, ns)
		if err != nil {
			return safeFolder(name)
		}
		return s
	}
	meta := map[string]bool{"manifest.json": true, "icon.png": true, "readme.md": true, "changelog.md": true, "license": true, "license.md": true, "license.txt": true}
	for _, f := range t.files {
		if !relpath.HasPrefixDir(f, pkg) {
			plan.Skipped = append(plan.Skipped, f)
			continue
		}
		rel := relpath.TrimDir(f, pkg)
		low := strings.ToLower(rel)
		switch {
		case packRoot != "" && relpath.HasPrefixDir(f, packRoot):
			plan.Files = append(plan.Files, File{Source: f, ModType: pack.ID, Rel: relpath.TrimDir(f, packRoot)})
		case meta[low]:
			plan.Skipped = append(plan.Skipped, f)
		case strings.HasPrefix(low, "bepinex/"):
			plan.Files = append(plan.Files, File{Source: f, ModType: pack.ID, Rel: rel})
		case strings.HasPrefix(low, "plugins/"):
			plan.Files = append(plan.Files, File{Source: f, ModType: plugin.ID, Rel: relpath.Join(sub(plugin), rel[len("plugins/"):])})
		case strings.HasPrefix(low, "patchers/") && patcher != nil:
			plan.Files = append(plan.Files, File{Source: f, ModType: patcher.ID, Rel: relpath.Join(sub(patcher), rel[len("patchers/"):])})
		case strings.HasPrefix(low, "config/") && config != nil:
			plan.Files = append(plan.Files, File{Source: f, ModType: config.ID, Rel: rel[len("config/"):]})
		default:
			plan.Files = append(plan.Files, File{Source: f, ModType: plugin.ID, Rel: relpath.Join(sub(plugin), rel)})
		}
	}
	if packRoot != "" {
		plan.ModType = pack.ID
	} else {
		plan.ModType = plugin.ID
	}
	return len(plan.Files) > 0
}

// namespaceFrom takes "Namespace" out of "Namespace-Name-1.2.3.zip".
func namespaceFrom(source, name string) string {
	b := path.Base(strings.ReplaceAll(source, `\`, "/"))
	if i := strings.Index(b, "-"); i > 0 {
		rest := b[i+1:]
		if name == "" || strings.HasPrefix(strings.ToLower(rest), strings.ToLower(name)) {
			return b[:i]
		}
	}
	return ""
}

func trimBOM(b []byte) []byte {
	if len(b) >= 3 && b[0] == 0xef && b[1] == 0xbb && b[2] == 0xbf {
		return b[3:]
	}
	return b
}

// planManifestFolders: every folder with the manifest file is one mod folder
// (SMAPI: several mods in one archive).
func planManifestFolders(t *tree, def *gamedef.Definition, plan *Plan, manifest string) bool {
	mt := def.DefaultModType()
	var roots []string
	for _, f := range t.files {
		if !strings.EqualFold(relpath.Base(f), manifest) {
			continue
		}
		d := relpath.Dir(f)
		roots = append(roots, d)
	}
	if len(roots) == 0 {
		return false
	}
	sort.Slice(roots, func(i, j int) bool {
		return depth(roots[i]) < depth(roots[j]) || (depth(roots[i]) == depth(roots[j]) && roots[i] < roots[j])
	})
	var top []string
	for _, r := range roots {
		nested := false
		for _, o := range top {
			if relpath.HasPrefixDir(r, o) {
				nested = true
			}
		}
		if !nested {
			top = append(top, r)
		}
	}
	plan.Format = def.Installer.PackageFormat
	plan.ModType = mt.ID
	for _, f := range t.files {
		owner := ""
		for _, r := range top {
			if relpath.HasPrefixDir(f, r) {
				owner = r
				break
			}
		}
		if owner == "" && !(len(top) == 1 && top[0] == "") {
			plan.Skipped = append(plan.Skipped, f)
			continue
		}
		folder := relpath.Base(owner)
		if owner == "" {
			folder = safeFolder(plan.ModName)
		}
		plan.Files = append(plan.Files, File{Source: f, ModType: mt.ID, Rel: relpath.Join(folder, relpath.TrimDir(f, owner))})
	}
	if len(top) == 1 {
		plan.Root = top[0]
	} else {
		plan.Root = relpath.Dir(top[0])
		plan.Warnings = append(plan.Warnings, fmt.Sprintf("Archiwum zawiera %d modów (osobne foldery z %s) – instalowane razem jako jedna pozycja.", len(top), manifest))
	}
	return len(plan.Files) > 0
}
