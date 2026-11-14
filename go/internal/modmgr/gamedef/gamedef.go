// Package gamedef loads game definitions (JSON data describing where a
// game's mods go, how its load order is written, what it needs to run),
// merges "extends" templates and resolves path templates into locations
// relative to named roots (never absolute paths with a drive letter).
//
// The built-in definitions are embedded (defs/*.json, schema in
// defs/game-definition.schema.json). A user folder can add or replace
// definitions by id.
package gamedef

import (
	"bytes"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

//go:embed defs/*.json
var builtin embed.FS

// Match is a set of file/dir criteria.
type Match struct {
	AnyFiles     []string `json:"anyFiles,omitempty"`
	AllFiles     []string `json:"allFiles,omitempty"`
	AnyDirs      []string `json:"anyDirs,omitempty"`
	ManifestFile string   `json:"manifestFile,omitempty"`
}

// ModType says where one kind of mod file goes.
type ModType struct {
	ID                string   `json:"id"`
	Name              string   `json:"name"`
	Target            string   `json:"target"`
	Priority          int      `json:"priority,omitempty"`
	Default           bool     `json:"default,omitempty"`
	Match             *Match   `json:"match,omitempty"`
	RootMarkers       []string `json:"rootMarkers,omitempty"`
	PerModSubfolder   string   `json:"perModSubfolder,omitempty"`
	Flatten           bool     `json:"flatten,omitempty"`
	IncludeGlobs      []string `json:"includeGlobs,omitempty"`
	ExcludeGlobs      []string `json:"excludeGlobs,omitempty"`
	ExecutableContent bool     `json:"executableContent,omitempty"`
	DeployStrategy    string   `json:"deployStrategy,omitempty"`
	Notes             string   `json:"notes,omitempty"`
}

// Executable is one way to start the game.
type Executable struct {
	ID                string   `json:"id"`
	Name              string   `json:"name"`
	Path              string   `json:"path"`
	Args              []string `json:"args,omitempty"`
	WorkingDir        string   `json:"workingDir,omitempty"`
	Default           bool     `json:"default,omitempty"`
	RequiresFramework string   `json:"requiresFramework,omitempty"`
	Kind              string   `json:"kind,omitempty"`
}

// Detection describes how to find the game.
type Detection struct {
	Steam *struct {
		AppIDs         []int    `json:"appIds,omitempty"`
		InstallDirName []string `json:"installDirNames,omitempty"`
	} `json:"steam,omitempty"`
	GOG *struct {
		GameIDs []string `json:"gameIds,omitempty"`
	} `json:"gog,omitempty"`
	Epic *struct {
		AppNames          []string `json:"appNames,omitempty"`
		CatalogNamespaces []string `json:"catalogNamespaces,omitempty"`
	} `json:"epic,omitempty"`
	Xbox *struct {
		PackageFamilyNames []string `json:"packageFamilyNames,omitempty"`
		Moddable           string   `json:"moddable,omitempty"`
	} `json:"xbox,omitempty"`
	Registry []struct {
		Hive    string `json:"hive"`
		Key     string `json:"key"`
		Value   string `json:"value"`
		View    string `json:"view,omitempty"`
		SubPath string `json:"subPath,omitempty"`
	} `json:"registry,omitempty"`
	RequiredFiles []string `json:"requiredFiles,omitempty"`
	AnyOfFiles    []string `json:"anyOfFiles,omitempty"`
	RootFromExe   string   `json:"rootFromExe,omitempty"`
	AllowManual   *bool    `json:"allowManual,omitempty"`
}

// Installer holds the install heuristics.
type Installer struct {
	Fomod              bool     `json:"fomod,omitempty"`
	MaxRootSearchDepth int      `json:"maxRootSearchDepth,omitempty"`
	IgnoreGlobs        []string `json:"ignoreGlobs,omitempty"`
	PackageFormat      string   `json:"packageFormat,omitempty"`
}

// PostDeploy is a step after deployment.
type PostDeploy struct {
	Kind            string   `json:"kind"`
	Tool            string   `json:"tool,omitempty"`
	Args            []string `json:"args,omitempty"`
	RequiresConsent bool     `json:"requiresConsent,omitempty"`
}

// Deployment holds the deployment settings.
type Deployment struct {
	Strategies                []string     `json:"strategies,omitempty"`
	CaseInsensitivePaths      *bool        `json:"caseInsensitivePaths,omitempty"`
	ProtectedPaths            []string     `json:"protectedPaths,omitempty"`
	PreferStagingOnGameVolume bool         `json:"preferStagingOnGameVolume,omitempty"`
	PostDeploy                []PostDeploy `json:"postDeploy,omitempty"`
}

// LightPlugins describes ESL support.
type LightPlugins struct {
	Supported  bool     `json:"supported"`
	Extensions []string `json:"extensions,omitempty"`
	Flagged    bool     `json:"flagged,omitempty"`
	MaxCount   int      `json:"maxCount,omitempty"`
}

// LoadOrder describes the load order file.
type LoadOrder struct {
	Kind                string            `json:"kind"`
	File                string            `json:"file,omitempty"`
	SecondaryFile       string            `json:"secondaryFile,omitempty"`
	PluginGlobs         []string          `json:"pluginGlobs,omitempty"`
	PluginsDir          string            `json:"pluginsDir,omitempty"`
	Format              string            `json:"format,omitempty"`
	Encoding            string            `json:"encoding,omitempty"`
	ImplicitPlugins     []string          `json:"implicitPlugins,omitempty"`
	ImplicitListFile    string            `json:"implicitListFile,omitempty"`
	LightPlugins        *LightPlugins     `json:"lightPlugins,omitempty"`
	MediumPlugins       *json.RawMessage  `json:"mediumPlugins,omitempty"`
	MaxFullPlugins      int               `json:"maxFullPlugins,omitempty"`
	ArgTemplate         []string          `json:"argTemplate,omitempty"`
	BaseEntries         []json.RawMessage `json:"baseEntries,omitempty"`
	SortHints           string            `json:"sortHints,omitempty"`
	ReadExternalChanges bool              `json:"readExternalChanges,omitempty"`
}

// Framework is a loader the mods may need.
type Framework struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Required string `json:"required,omitempty"`
	Detect   *struct {
		AnyFiles    []string        `json:"anyFiles,omitempty"`
		AllFiles    []string        `json:"allFiles,omitempty"`
		VersionFrom json.RawMessage `json:"versionFrom,omitempty"`
	} `json:"detect,omitempty"`
	ModRequiresIf *struct {
		AnyFiles           []string `json:"anyFiles,omitempty"`
		ManifestDependency string   `json:"manifestDependency,omitempty"`
	} `json:"modRequiresIf,omitempty"`
	Install           string          `json:"install,omitempty"`
	Source            json.RawMessage `json:"source,omitempty"`
	GameVersionLocked bool            `json:"gameVersionLocked,omitempty"`
	LaunchVia         string          `json:"launchVia,omitempty"`
	Notes             string          `json:"notes,omitempty"`
}

// Launch holds launch settings.
type Launch struct {
	PreferStoreLaunch      bool              `json:"preferStoreLaunch,omitempty"`
	SteamLaunchOptionsHint string            `json:"steamLaunchOptionsHint,omitempty"`
	Args                   []string          `json:"args,omitempty"`
	ModdedArgs             []string          `json:"moddedArgs,omitempty"`
	Env                    map[string]string `json:"env,omitempty"`
}

// Updates says how game updates are noticed.
type Updates struct {
	SteamBuildID bool     `json:"steamBuildId,omitempty"`
	EpicVersion  bool     `json:"epicVersion,omitempty"`
	WatchFiles   []string `json:"watchFiles,omitempty"`
	OnUpdate     string   `json:"onUpdate,omitempty"`
}

// Warning is a message shown in a given situation.
type Warning struct {
	ID    string `json:"id"`
	Level string `json:"level"`
	Text  string `json:"text"`
	When  string `json:"when,omitempty"`
}

// Definition is one game definition (after merging "extends").
type Definition struct {
	Schema         string                     `json:"$schema,omitempty"`
	SchemaVersion  int                        `json:"schemaVersion"`
	ID             string                     `json:"id"`
	Name           string                     `json:"name"`
	Extends        string                     `json:"extends,omitempty"`
	Abstract       bool                       `json:"abstract,omitempty"`
	Aliases        []string                   `json:"aliases,omitempty"`
	Engine         string                     `json:"engine,omitempty"`
	Tags           []string                   `json:"tags,omitempty"`
	Adapter        string                     `json:"adapter,omitempty"`
	Detection      Detection                  `json:"detection"`
	Paths          map[string]string          `json:"paths,omitempty"`
	StoreOverrides map[string]json.RawMessage `json:"storeOverrides,omitempty"`
	Executables    []Executable               `json:"executables,omitempty"`
	ModTypes       []ModType                  `json:"modTypes"`
	Installer      Installer                  `json:"installer,omitempty"`
	Deployment     Deployment                 `json:"deployment"`
	LoadOrder      LoadOrder                  `json:"loadOrder"`
	Frameworks     []Framework                `json:"frameworks,omitempty"`
	Launch         *Launch                    `json:"launch,omitempty"`
	Updates        *Updates                   `json:"updates,omitempty"`
	Sources        json.RawMessage            `json:"sources,omitempty"`
	Warnings       []Warning                  `json:"warnings,omitempty"`
	Notes          string                     `json:"notes,omitempty"`

	// Builtin is false for definitions loaded from the user folder.
	Builtin bool `json:"-"`
}

// GenericID is the template used for games without their own definition.
const GenericID = "template.generic"

// ModType returns the mod type with the id.
func (d *Definition) ModType(id string) *ModType {
	for i := range d.ModTypes {
		if d.ModTypes[i].ID == id {
			return &d.ModTypes[i]
		}
	}
	return nil
}

// DefaultModType is the type marked default (or the last one).
func (d *Definition) DefaultModType() *ModType {
	for i := range d.ModTypes {
		if d.ModTypes[i].Default {
			return &d.ModTypes[i]
		}
	}
	if len(d.ModTypes) == 0 {
		return nil
	}
	return &d.ModTypes[len(d.ModTypes)-1]
}

// CaseInsensitive reports whether target paths compare case-insensitively.
func (d *Definition) CaseInsensitive() bool {
	return d.Deployment.CaseInsensitivePaths == nil || *d.Deployment.CaseInsensitivePaths
}

// IsGeneric reports whether this is the generic template.
func (d *Definition) IsGeneric() bool { return d.ID == GenericID }

// WarningsWhen lists the warnings for a situation.
func (d *Definition) WarningsWhen(when string) []Warning {
	var out []Warning
	for _, w := range d.Warnings {
		if w.When == when || (when == "always" && w.When == "") {
			out = append(out, w)
		}
	}
	return out
}

// Set is the loaded definitions.
type Set struct {
	defs map[string]*Definition
	// Problems are user definitions that failed to load (shown, not fatal).
	Problems []string
}

// Get returns a definition by id (including abstract templates).
func (s *Set) Get(id string) *Definition { return s.defs[id] }

// List returns the concrete definitions plus the generic template, sorted
// by name (generic last).
func (s *Set) List() []*Definition {
	var out []*Definition
	for _, d := range s.defs {
		if !d.Abstract || d.IsGeneric() {
			out = append(out, d)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].IsGeneric() != out[j].IsGeneric() {
			return !out[i].IsGeneric()
		}
		return strings.ToLower(out[i].Name) < strings.ToLower(out[j].Name)
	})
	return out
}

// Load reads the built-in definitions and then userDir (may be "" or
// missing); a user file with the same id replaces the built-in one.
func Load(userDir string) (*Set, error) {
	raw := map[string]map[string]any{}
	builtinIDs := map[string]bool{}
	err := fs.WalkDir(builtin, "defs", func(p string, de fs.DirEntry, err error) error {
		if err != nil || de.IsDir() || !strings.HasSuffix(p, ".json") || strings.HasSuffix(p, ".schema.json") {
			return err
		}
		b, err := builtin.ReadFile(p)
		if err != nil {
			return err
		}
		m, err := decodeRaw(b)
		if err != nil {
			return fmt.Errorf("%s: %w", p, err)
		}
		id, _ := m["id"].(string)
		if id == "" {
			return fmt.Errorf("%s: brak id", p)
		}
		if _, dup := raw[id]; dup {
			return fmt.Errorf("%s: powtórzone id %q", p, id)
		}
		raw[id] = m
		builtinIDs[id] = true
		return nil
	})
	if err != nil {
		return nil, err
	}
	set := &Set{defs: map[string]*Definition{}}
	if userDir != "" {
		ents, _ := os.ReadDir(userDir)
		for _, e := range ents {
			if e.IsDir() || !strings.HasSuffix(strings.ToLower(e.Name()), ".json") {
				continue
			}
			b, err := os.ReadFile(filepath.Join(userDir, e.Name()))
			if err == nil {
				var m map[string]any
				if m, err = decodeRaw(b); err == nil {
					if id, _ := m["id"].(string); id != "" {
						raw[id] = m
						builtinIDs[id] = false
						continue
					}
					err = errors.New("brak id")
				}
			}
			set.Problems = append(set.Problems, fmt.Sprintf("%s: %v", e.Name(), err))
		}
	}
	for id := range raw {
		merged, err := resolveExtends(raw, id, map[string]bool{})
		if err != nil {
			if builtinIDs[id] {
				return nil, err
			}
			set.Problems = append(set.Problems, err.Error())
			continue
		}
		d, err := decodeDef(merged)
		if err == nil {
			err = d.validate()
		}
		if err != nil {
			if builtinIDs[id] {
				return nil, fmt.Errorf("definicja %s: %w", id, err)
			}
			set.Problems = append(set.Problems, fmt.Sprintf("definicja %s: %v", id, err))
			continue
		}
		d.Builtin = builtinIDs[id]
		set.defs[id] = d
	}
	sort.Strings(set.Problems)
	return set, nil
}

func decodeRaw(b []byte) (map[string]any, error) {
	b = bytes.TrimPrefix(b, []byte("\xef\xbb\xbf"))
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.UseNumber()
	var m map[string]any
	if err := dec.Decode(&m); err != nil {
		return nil, err
	}
	return m, nil
}

func decodeDef(m map[string]any) (*Definition, error) {
	b, err := json.Marshal(m)
	if err != nil {
		return nil, err
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	var d Definition
	if err := dec.Decode(&d); err != nil {
		return nil, err
	}
	return &d, nil
}

// resolveExtends merges the chain of templates: objects deep, arrays and
// scalars replaced; "abstract" is never inherited.
func resolveExtends(raw map[string]map[string]any, id string, seen map[string]bool) (map[string]any, error) {
	if seen[id] {
		return nil, fmt.Errorf("definicja %s: cykl w extends", id)
	}
	seen[id] = true
	m, ok := raw[id]
	if !ok {
		return nil, fmt.Errorf("definicja %s nie istnieje", id)
	}
	parent, _ := m["extends"].(string)
	if parent == "" {
		return m, nil
	}
	base, err := resolveExtends(raw, parent, seen)
	if err != nil {
		return nil, fmt.Errorf("definicja %s: %w", id, err)
	}
	out := deepMerge(base, m)
	if _, ok := m["abstract"]; !ok {
		delete(out, "abstract")
	}
	return out, nil
}

func deepMerge(base, over map[string]any) map[string]any {
	out := make(map[string]any, len(base)+len(over))
	for k, v := range base {
		out[k] = v
	}
	for k, v := range over {
		if bo, ok := out[k].(map[string]any); ok {
			if oo, ok := v.(map[string]any); ok {
				out[k] = deepMerge(bo, oo)
				continue
			}
		}
		out[k] = v
	}
	return out
}

var knownStrategies = map[string]bool{"hardlink": true, "symlink": true, "copy": true, "launch-args": true, "external-folder": true}

func (d *Definition) validate() error {
	if d.ID == "" || d.Name == "" {
		return errors.New("brak id lub nazwy")
	}
	if len(d.ModTypes) == 0 {
		return errors.New("brak modTypes")
	}
	seen := map[string]bool{}
	for _, mt := range d.ModTypes {
		if mt.ID == "" || mt.Target == "" {
			return errors.New("typ moda bez id lub target")
		}
		if seen[mt.ID] {
			return fmt.Errorf("powtórzony typ moda %q", mt.ID)
		}
		seen[mt.ID] = true
		if err := checkTemplate(d, mt.Target); err != nil {
			return fmt.Errorf("typ %s: %w", mt.ID, err)
		}
	}
	if len(d.Deployment.Strategies) == 0 {
		return errors.New("brak deployment.strategies")
	}
	for _, s := range d.Deployment.Strategies {
		if !knownStrategies[s] {
			return fmt.Errorf("nieznana strategia %q", s)
		}
	}
	for _, f := range []string{d.LoadOrder.File, d.LoadOrder.SecondaryFile, d.LoadOrder.PluginsDir} {
		if f != "" {
			if err := checkTemplate(d, f); err != nil {
				return fmt.Errorf("loadOrder: %w", err)
			}
		}
	}
	for k, v := range d.Paths {
		if err := checkTemplate(d, v); err != nil {
			return fmt.Errorf("paths.%s: %w", k, err)
		}
	}
	return nil
}

// checkTemplate verifies that a template starts at a known root.
func checkTemplate(d *Definition, t string) error {
	r := &Resolver{Def: d, Roots: map[RootKind]string{}, Vars: map[string]string{"selectedGameDir": "valve", "redmodOrderArgs": ""}}
	for k := range rootVars {
		r.Roots[rootVars[k]] = "C:/x"
	}
	_, err := r.Location(t)
	return err
}
