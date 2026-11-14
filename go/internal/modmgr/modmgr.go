// Package modmgr is the mod manager of the launcher (design:
// docs/MOD_MANAGER.md). It ties together:
//
//   - gamedef: game definitions (JSON, embedded + user folder);
//   - modstore: installed mods kept outside the game folder;
//   - install: where the files of an archive go;
//   - conflict: file-level conflicts and winners per profile;
//   - deploy: journaled deployment with backups of originals, purge to
//     vanilla and recovery after a crash;
//   - loadorder: plugins.txt & co. and launch arguments.
//
// Everything lives under <launcher>/data/modmgr; paths of game installs on
// the launcher's drive are stored without the drive letter.
package modmgr

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/conflict"
	"github.com/snakex21/game-launcher/go/internal/modmgr/deploy"
	"github.com/snakex21/game-launcher/go/internal/modmgr/detect"
	"github.com/snakex21/game-launcher/go/internal/modmgr/fsx"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/ids"
	"github.com/snakex21/game-launcher/go/internal/modmgr/loadorder"
	"github.com/snakex21/game-launcher/go/internal/modmgr/modstore"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
	"github.com/snakex21/game-launcher/go/internal/paths"
)

// UserError is shown to the user as-is.
type UserError struct {
	Message string
	// Confirm is set when the action can be repeated with consent
	// (executable content, protected files, duplicate archive).
	Confirm string
}

func (e *UserError) Error() string { return e.Message }

func uerr(format string, a ...any) error { return &UserError{Message: fmt.Sprintf(format, a...)} }

// Install is one game install managed by the mod manager.
type Install struct {
	ID            string            `json:"id"`
	DefID         string            `json:"defId"`
	Name          string            `json:"name"`
	Game          string            `json:"game,omitempty"` // launcher library game name
	Path          string            `json:"path"`           // portable (no drive letter on the launcher drive)
	Store         string            `json:"store,omitempty"`
	Vars          map[string]string `json:"vars,omitempty"`
	PathOverrides map[string]string `json:"pathOverrides,omitempty"`
	ActiveProfile string            `json:"activeProfile"`
	AutoDeploy    bool              `json:"autoDeploy"`
	Iwad          string            `json:"iwad,omitempty"`
	Created       time.Time         `json:"created"`
}

// ProfileMod is a mod in a profile (order = priority, later wins).
type ProfileMod struct {
	ModID   string `json:"modId"`
	Enabled bool   `json:"enabled"`
}

// Profile is a set of enabled mods with their order and rules.
type Profile struct {
	ID            string             `json:"id"`
	Name          string             `json:"name"`
	Mods          []ProfileMod       `json:"mods"`
	FileOverrides map[string]string  `json:"fileOverrides,omitempty"`
	PluginOrder   []loadorder.Plugin `json:"pluginOrder,omitempty"`
}

type installsFile struct {
	FormatVersion int        `json:"formatVersion"`
	Installs      []*Install `json:"installs"`
}

// Options configure the service (tests replace the system parts).
type Options struct {
	// Folders are the user's known folders (documents, AppData...).
	Folders map[gamedef.RootKind]string
	// Running lists the exe paths of running processes.
	Running func() ([]string, error)
	// SteamRoot is the Steam folder for detection ("" = none).
	SteamRoot string
}

// Service is the mod manager.
type Service struct {
	appDir string
	root   string
	opt    Options

	mu       sync.Mutex
	defs     *gamedef.Set
	store    *modstore.Store
	installs []*Install
	// Recovered reports what the startup recovery did.
	Recovered []string
}

// New opens the mod manager of a launcher folder.
func New(appDir string, opt Options) (*Service, error) {
	root := filepath.Join(appDir, "data", "modmgr")
	s := &Service{appDir: appDir, root: root, opt: opt}
	defs, err := gamedef.Load(filepath.Join(root, "gamedefs"))
	if err != nil {
		return nil, err
	}
	s.defs = defs
	s.store = modstore.New(root)
	if err := fsx.ReadJSON(s.installsPath(), &installsFile{}); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return nil, fmt.Errorf("installs.json: %w", err)
	}
	var f installsFile
	_ = fsx.ReadJSON(s.installsPath(), &f)
	s.installs = f.Installs
	for _, p := range s.store.CleanupTemp() {
		s.Recovered = append(s.Recovered, "Usunięto pozostałość przerwanej instalacji: "+filepath.Base(p))
	}
	for _, in := range s.installs {
		e, err := s.engine(in)
		if err != nil {
			continue
		}
		reps, err := e.Recover()
		for _, r := range reps {
			s.Recovered = append(s.Recovered, fmt.Sprintf("%s: przerwana operacja – %s", in.Name, recoveryText(r.Action)))
		}
		if err != nil {
			s.Recovered = append(s.Recovered, fmt.Sprintf("%s: %v", in.Name, err))
		}
		if len(reps) > 0 {
			s.reprotect(in)
		}
	}
	return s, nil
}

func recoveryText(a string) string {
	switch a {
	case "forward":
		return "dokończona"
	case "rollback":
		return "wycofana (gra w stanie sprzed operacji)"
	case "committed":
		return "była już zakończona"
	case "discarded":
		return "nic nie zostało zmienione"
	}
	return a
}

// Defs returns the definitions.
func (s *Service) Defs() *gamedef.Set { return s.defs }

func (s *Service) installsPath() string { return filepath.Join(s.root, "installs.json") }

func (s *Service) saveInstalls() error {
	return fsx.WriteJSONAtomic(s.installsPath(), installsFile{FormatVersion: 1, Installs: s.installs})
}

func (s *Service) install(id string) (*Install, *gamedef.Definition, error) {
	for _, in := range s.installs {
		if in.ID == id {
			d := s.defs.Get(in.DefID)
			if d == nil {
				return nil, nil, uerr("Definicja gry %q nie jest dostępna.", in.DefID)
			}
			return in, d, nil
		}
	}
	return nil, nil, uerr("Nie ma takiej gry w menedżerze modów.")
}

// gameKey is the store folder: shared by installs of the same game,
// separate for every generic install.
func gameKey(in *Install, d *gamedef.Definition) string {
	if d.IsGeneric() {
		return "generic-" + in.ID
	}
	return d.ID
}

func (s *Service) gamePath(in *Install) string { return paths.Resolve(in.Path, s.appDir) }

func (s *Service) stateDir(in *Install) string { return filepath.Join(s.root, "state", in.ID) }

func (s *Service) profileDir(in *Install) string { return filepath.Join(s.root, "profiles", in.ID) }

func (s *Service) resolver(in *Install, d *gamedef.Definition) *gamedef.Resolver {
	roots := map[gamedef.RootKind]string{}
	for k, v := range s.opt.Folders {
		roots[k] = v
	}
	roots[gamedef.RootGame] = s.gamePath(in)
	roots[gamedef.RootModsStaging] = filepath.Join(s.root, "store", gameKey(in, d))
	roots[gamedef.RootProfileDir] = filepath.Join(s.profileDir(in), in.ActiveProfile)
	roots[gamedef.RootInstance] = filepath.Join(s.root, "instances", in.ID)
	vars := map[string]string{"selectedGameDir": "valve", "redmodOrderArgs": ""}
	for k, v := range in.Vars {
		vars[k] = v
	}
	return &gamedef.Resolver{Def: d, Store: in.Store, Roots: roots, Vars: vars, PathOverrides: in.PathOverrides}
}

func (s *Service) engine(in *Install) (*deploy.Engine, error) {
	d := s.defs.Get(in.DefID)
	if d == nil {
		return nil, fmt.Errorf("brak definicji %s", in.DefID)
	}
	r := s.resolver(in, d)
	key := gameKey(in, d)
	e := &deploy.Engine{
		InstallID: in.ID,
		StateDir:  s.stateDir(in),
		Roots:     r.Roots,
		Protected: d.Deployment.ProtectedPaths,
		SourcePath: func(src deploy.Source) (string, error) {
			if src.Type == "@blob" {
				rel, err := relpath.Clean(src.Rel)
				if err != nil {
					return "", err
				}
				return filepath.Join(s.stateDir(in), "blobs", filepath.FromSlash(rel)), nil
			}
			if !ids.Valid(src.ModID) {
				return "", fmt.Errorf("nieprawidłowe id moda %q", src.ModID)
			}
			rel, err := relpath.Clean(src.Rel)
			if err != nil {
				return "", err
			}
			if strings.ContainsAny(src.Type, `/\.:`) {
				return "", fmt.Errorf("nieprawidłowy typ %q", src.Type)
			}
			return s.store.FilePath(key, src.ModID, src.Type, rel), nil
		},
	}
	return e, nil
}

// ---------------------------------------------------------------- profiles

func (s *Service) profiles(in *Install) ([]*Profile, error) {
	ents, err := os.ReadDir(s.profileDir(in))
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return nil, err
	}
	var out []*Profile
	for _, e := range ents {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") || !ids.Valid(strings.TrimSuffix(e.Name(), ".json")) {
			continue
		}
		var p Profile
		if err := fsx.ReadJSON(filepath.Join(s.profileDir(in), e.Name()), &p); err != nil {
			return nil, fmt.Errorf("profil %s jest uszkodzony: %w", e.Name(), err)
		}
		out = append(out, &p)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

func (s *Service) profile(in *Install, id string) (*Profile, error) {
	if !ids.Valid(id) {
		return nil, uerr("Nie ma takiego profilu.")
	}
	var p Profile
	err := fsx.ReadJSON(filepath.Join(s.profileDir(in), id+".json"), &p)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, uerr("Nie ma takiego profilu.")
	}
	return &p, err
}

func (s *Service) saveProfile(in *Install, p *Profile) error {
	return fsx.WriteJSONAtomic(filepath.Join(s.profileDir(in), p.ID+".json"), p)
}

func (s *Service) active(in *Install) (*Profile, error) { return s.profile(in, in.ActiveProfile) }

// ---------------------------------------------------------------- installs

// AddInstallIn describes a game to add.
type AddInstallIn struct {
	DefID      string `json:"defId"`
	Path       string `json:"path"`
	Name       string `json:"name"`
	Game       string `json:"game"`
	Store      string `json:"store"`
	Force      bool   `json:"force"`
	ModsTarget string `json:"modsTarget"` // generic: subfolder of the game for mods ("" = game root)
}

// AddInstall registers a game folder.
func (s *Service) AddInstall(in AddInstallIn) (*Install, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	d := s.defs.Get(in.DefID)
	if d == nil || (d.Abstract && !d.IsGeneric()) {
		return nil, uerr("Wybierz definicję gry.")
	}
	path := filepath.Clean(strings.TrimSpace(in.Path))
	if !filepath.IsAbs(path) {
		return nil, uerr("Podaj pełną ścieżkę folderu gry.")
	}
	if st, err := os.Stat(path); err != nil || !st.IsDir() {
		return nil, uerr("Folder gry nie istnieje: %s", path)
	}
	if err := detect.Validate(d, path); err != nil && !in.Force {
		return nil, &UserError{Message: err.Error() + ". Czy to na pewno folder tej gry?", Confirm: "force"}
	}
	if err := s.checkGameFolder(path); err != nil {
		return nil, err
	}
	name := strings.TrimSpace(in.Name)
	if name == "" {
		name = d.Name
		if d.IsGeneric() {
			name = filepath.Base(path)
		}
	}
	inst := &Install{ID: ids.New(), DefID: d.ID, Name: name, Game: in.Game, Path: paths.ToPortable(path, s.appDir),
		Store: in.Store, AutoDeploy: true, Created: time.Now().UTC().Truncate(time.Second)}
	if inst.Store == "" {
		inst.Store = "manual"
	}
	if d.IsGeneric() {
		target := "{game}"
		if t := strings.Trim(strings.ReplaceAll(strings.TrimSpace(in.ModsTarget), `\`, "/"), "/"); t != "" {
			rel, err := relpath.Clean(t)
			if err != nil {
				return nil, uerr("Folder docelowy modów: %v", err)
			}
			target = "{game}/" + rel
		}
		inst.PathOverrides = map[string]string{"modsTarget": target}
	}
	p := &Profile{ID: ids.New(), Name: "Domyślny"}
	inst.ActiveProfile = p.ID
	if err := s.saveProfile(inst, p); err != nil {
		return nil, err
	}
	s.installs = append(s.installs, inst)
	if err := s.saveInstalls(); err != nil {
		s.installs = s.installs[:len(s.installs)-1]
		return nil, err
	}
	return inst, nil
}

// inside reports whether p is dir or lies inside it (case-insensitive).
func inside(p, dir string) bool {
	p, dir = strings.ToLower(filepath.Clean(p)), strings.ToLower(filepath.Clean(dir))
	return p == dir || strings.HasPrefix(p, strings.TrimRight(dir, `\/`)+string(filepath.Separator))
}

// checkGameFolder refuses folders that would let deployments touch the
// launcher's own data or another managed game.
func (s *Service) checkGameFolder(path string) error {
	if inside(path, filepath.Join(s.appDir, "data")) || inside(s.root, path) {
		return uerr("To jest folder launchera albo jego danych (albo go zawiera) – wybierz folder gry.")
	}
	for _, other := range s.installs {
		op := filepath.Clean(s.gamePath(other))
		switch {
		case strings.EqualFold(op, path):
			return uerr("Ten folder jest już w menedżerze jako „%s”.", other.Name)
		case inside(path, op) || inside(op, path):
			return uerr("Ten folder leży w folderze gry „%s” (albo go zawiera) – dwie gry w menedżerze nie mogą zarządzać tymi samymi plikami.", other.Name)
		}
	}
	return nil
}

// RemoveInstall forgets a game; it must be back to vanilla first.
func (s *Service) RemoveInstall(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return err
	}
	e, _ := s.engine(in)
	m, err := e.Manifest()
	if err != nil {
		return err
	}
	if len(m.Entries) > 0 || e.Pending() {
		return uerr("Najpierw przywróć grę do stanu bez modów (przycisk „Przywróć vanilla”).")
	}
	for i, x := range s.installs {
		if x.ID == id {
			s.installs = append(s.installs[:i], s.installs[i+1:]...)
			break
		}
	}
	if err := s.saveInstalls(); err != nil {
		return err
	}
	fsx.RemoveAll(s.profileDir(in))
	fsx.RemoveAll(s.stateDir(in))
	if d.IsGeneric() {
		mods, _ := s.store.List(gameKey(in, d))
		for _, m := range mods {
			s.store.Remove(gameKey(in, d), m.ID)
		}
		fsx.RemoveAll(filepath.Join(s.root, "store", gameKey(in, d)))
		fsx.RemoveAll(filepath.Join(s.root, "downloads", gameKey(in, d)))
	}
	fsx.RemoveAll(filepath.Join(s.root, "instances", in.ID))
	return nil
}

// SetInstallOptions changes per-install settings.
type SetInstallOptions struct {
	Name       *string `json:"name"`
	AutoDeploy *bool   `json:"autoDeploy"`
	Iwad       *string `json:"iwad"`
	GameDir    *string `json:"selectedGameDir"`
}

// SetOptions updates install settings.
func (s *Service) SetOptions(id string, o SetInstallOptions) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, _, err := s.install(id)
	if err != nil {
		return err
	}
	if o.Name != nil && strings.TrimSpace(*o.Name) != "" {
		in.Name = strings.TrimSpace(*o.Name)
	}
	if o.AutoDeploy != nil {
		in.AutoDeploy = *o.AutoDeploy
	}
	if o.Iwad != nil {
		in.Iwad = paths.ToPortable(strings.TrimSpace(*o.Iwad), s.appDir)
	}
	if o.GameDir != nil {
		g := strings.TrimSpace(*o.GameDir)
		if g != "" {
			if c, err := relpath.Clean(g); err != nil || strings.Contains(c, "/") {
				return uerr("Nieprawidłowa nazwa katalogu gry.")
			}
		}
		if in.Vars == nil {
			in.Vars = map[string]string{}
		}
		in.Vars["selectedGameDir"] = g
	}
	return s.saveInstalls()
}

// ---------------------------------------------------------------- desired state

// mods of a profile in order, with the store data; unknown ids are dropped.
func (s *Service) profileMods(in *Install, d *gamedef.Definition, p *Profile) ([]*modstore.Mod, []conflict.Mod, error) {
	key := gameKey(in, d)
	all, err := s.store.List(key)
	if err != nil {
		return nil, nil, err
	}
	byID := map[string]*modstore.Mod{}
	for _, m := range all {
		byID[m.ID] = m
	}
	r := s.resolver(in, d)
	var mods []*modstore.Mod
	var cms []conflict.Mod
	for _, pm := range p.Mods {
		m := byID[pm.ModID]
		if m == nil {
			continue
		}
		cm := conflict.Mod{ID: m.ID, Name: m.Name, Enabled: pm.Enabled}
		for _, f := range m.Files {
			mt := d.ModType(f.Type)
			if mt == nil {
				return nil, nil, uerr("Mod „%s” używa typu %q, którego definicja gry już nie ma.", m.Name, f.Type)
			}
			base, err := r.Location(mt.Target)
			if err != nil {
				return nil, nil, uerr("Typ %s: %v", mt.ID, err)
			}
			cm.Files = append(cm.Files, conflict.File{Target: base.Child(f.Rel), Type: f.Type, Rel: f.Rel, SHA256: f.SHA256, Size: f.Size})
		}
		mods = append(mods, m)
		cms = append(cms, cm)
	}
	return mods, cms, nil
}

type desiredState struct {
	desired  []deploy.Desired
	blobs    map[string][]byte // blob rel -> content
	index    *conflict.Index
	lo       *loadorder.Output
	placed   []loadorder.Placed
	launch   bool // launch-args game: nothing is deployed
	warnings []string
}

// mutableGlobs are files games and mods rewrite while running (configs):
// they are deployed as writable copies, never as hardlinks into the store.
var mutableGlobs = []string{"*.cfg", "*.ini", "*.json", "*.toml", "*.yaml", "*.yml", "*.conf", "*.config", "*.properties", "*.settings", "*.xml"}

func strategyKinds(d *gamedef.Definition) (launch bool, hard bool) {
	for _, st := range d.Deployment.Strategies {
		switch st {
		case "launch-args":
			return true, false
		case "hardlink":
			return false, true
		case "copy":
			return false, false
		}
	}
	return false, false
}

func sameVolume(a, b string) bool {
	return a != "" && b != "" && strings.EqualFold(filepath.VolumeName(a), filepath.VolumeName(b))
}

func (s *Service) computeDesired(in *Install, d *gamedef.Definition, p *Profile) (*desiredState, error) {
	_, cms, err := s.profileMods(in, d, p)
	if err != nil {
		return nil, err
	}
	idx := conflict.Build(cms, p.FileOverrides)
	ds := &desiredState{index: idx, blobs: map[string][]byte{}}
	launch, hard := strategyKinds(d)
	ds.launch = launch
	r := s.resolver(in, d)
	key := gameKey(in, d)
	order := map[string]int{}
	for i, m := range cms {
		order[m.ID] = i
	}
	keys := idx.Keys()
	sort.SliceStable(keys, func(i, j int) bool {
		a, b := idx.Entries[keys[i]], idx.Entries[keys[j]]
		if order[a.Winner] != order[b.Winner] {
			return order[a.Winner] < order[b.Winner]
		}
		return keys[i] < keys[j]
	})
	for _, k := range keys {
		e := idx.Entries[k]
		f := e.WinnerFile()
		ds.placed = append(ds.placed, loadorder.Placed{Target: e.Target, SourceAbs: s.store.FilePath(key, e.Winner, f.Type, f.Rel), ModIndex: order[e.Winner], ModID: e.Winner})
		if launch {
			continue
		}
		kind := "copy"
		mutable := relpath.MatchAny(mutableGlobs, f.Rel)
		if hard && !mutable {
			if rootAbs := r.Roots[e.Target.Root]; sameVolume(rootAbs, s.root) {
				kind = "hardlink"
			}
		}
		ds.desired = append(ds.desired, deploy.Desired{Target: e.Target, Source: deploy.Source{ModID: e.Winner, Type: f.Type, Rel: f.Rel}, SHA256: f.SHA256, Size: f.Size, Kind: kind, Mutable: mutable})
	}
	if launch {
		return ds, nil
	}
	if len(ds.desired) == 0 {
		return ds, nil // nothing enabled: no load order file either (purge)
	}
	lo, err := loadorder.Build(loadorder.Input{
		Def: d, Res: r, Files: ds.placed, Order: p.PluginOrder,
		ReadFile: func(l gamedef.Location) ([]byte, error) { return s.readOriginal(in, r, l) },
		ReadCurrent: func(l gamedef.Location) ([]byte, error) {
			abs, err := r.Abs(l)
			if err != nil {
				return nil, err
			}
			if st, err := os.Stat(abs); err != nil || st.Size() > 8<<20 {
				return nil, fs.ErrNotExist
			}
			return os.ReadFile(abs)
		},
		ListDir: func(l gamedef.Location) ([]string, error) {
			abs, err := r.Abs(l)
			if err != nil {
				return nil, err
			}
			ents, err := os.ReadDir(abs)
			var out []string
			for _, e := range ents {
				if !e.IsDir() && !s.isDeployedByUs(in, l.Child(e.Name())) {
					out = append(out, e.Name())
				}
			}
			return out, err
		},
	})
	if err != nil {
		return nil, uerr("Kolejność ładowania: %v", err)
	}
	ds.lo = lo
	ds.warnings = append(ds.warnings, lo.Warnings...)
	for i := range ds.desired {
		if t, ok := lo.MTimes[ds.desired[i].Target.Key()]; ok {
			ds.desired[i].MTime = t
			ds.desired[i].Kind = "copy"
		}
	}
	for i, g := range lo.Files {
		rel := fmt.Sprintf("lo-%d", i)
		sum := sha256.Sum256(g.Content)
		ds.blobs[rel] = g.Content
		ds.desired = append(ds.desired, deploy.Desired{Target: g.Target, Source: deploy.Source{Type: "@blob", Rel: rel}, SHA256: hex.EncodeToString(sum[:]), Size: int64(len(g.Content)), Kind: "copy", Mutable: true})
	}
	return ds, nil
}

// readOriginal returns the content a load order writer should start from:
// the original backup when the file is currently ours, else the disk.
func (s *Service) readOriginal(in *Install, r *gamedef.Resolver, l gamedef.Location) ([]byte, error) {
	e, err := s.engine(in)
	if err != nil {
		return nil, err
	}
	if m, err := e.Manifest(); err == nil {
		for _, en := range m.Entries {
			if en.Target.Key() == l.Key() {
				if en.Orig == nil {
					return nil, fs.ErrNotExist
				}
				return os.ReadFile(filepath.Join(s.stateDir(in), filepath.FromSlash(en.Orig.Backup)))
			}
		}
	}
	abs, err := r.Abs(l)
	if err != nil {
		return nil, err
	}
	st, err := os.Stat(abs)
	if err != nil {
		return nil, err
	}
	if st.Size() > 8<<20 {
		return nil, fmt.Errorf("plik %s jest za duży", abs)
	}
	return os.ReadFile(abs)
}

func (s *Service) isDeployedByUs(in *Install, l gamedef.Location) bool {
	e, err := s.engine(in)
	if err != nil {
		return false
	}
	m, err := e.Manifest()
	if err != nil {
		return false
	}
	for _, en := range m.Entries {
		if en.Target.Key() == l.Key() {
			return true
		}
	}
	return false
}

// ---------------------------------------------------------------- deploy / purge

// DeployResult is shown after a deployment.
type DeployResult struct {
	Changed  int      `json:"changed"`
	Drift    []string `json:"drift,omitempty"`
	Warnings []string `json:"warnings,omitempty"`
	Purged   bool     `json:"purged"`
}

func (s *Service) checkNotRunning(in *Install) error {
	if s.opt.Running == nil {
		return nil
	}
	exes, err := s.opt.Running()
	if err != nil {
		return nil
	}
	root := strings.ToLower(filepath.Clean(s.gamePath(in))) + string(filepath.Separator)
	for _, x := range exes {
		if strings.HasPrefix(strings.ToLower(filepath.Clean(x)), root) {
			return uerr("Gra jest uruchomiona (%s). Zamknij ją przed zmianą modów.", filepath.Base(x))
		}
	}
	return nil
}

func (s *Service) fingerprint(in *Install, d *gamedef.Definition) map[string]string {
	if d.Updates == nil || len(d.Updates.WatchFiles) == 0 {
		return nil
	}
	out := map[string]string{}
	for _, f := range d.Updates.WatchFiles {
		rel, err := relpath.Clean(f)
		if err != nil {
			continue
		}
		if st, err := os.Stat(filepath.Join(s.gamePath(in), filepath.FromSlash(rel))); err == nil {
			out[rel] = fmt.Sprintf("%d:%d", st.Size(), st.ModTime().Unix())
		}
	}
	return out
}

func (s *Service) apply(in *Install, d *gamedef.Definition, purge, allowProtected bool) (*DeployResult, error) {
	if err := s.checkNotRunning(in); err != nil {
		return nil, err
	}
	e, err := s.engine(in)
	if err != nil {
		return nil, err
	}
	if e.Pending() {
		if _, err := e.Recover(); err != nil {
			return nil, err
		}
	}
	var ds *desiredState
	res := &DeployResult{Purged: purge}
	var desired []deploy.Desired
	if !purge {
		p, err := s.active(in)
		if err != nil {
			return nil, err
		}
		ds, err = s.computeDesired(in, d, p)
		if err != nil {
			return nil, err
		}
		res.Warnings = ds.warnings
		if ds.launch {
			return res, nil
		}
		desired = ds.desired
		if len(ds.blobs) > 0 {
			dir := ids.New()
			for rel, b := range ds.blobs {
				if err := fsx.WriteFileAtomic(filepath.Join(s.stateDir(in), "blobs", dir, rel), b, 0o644); err != nil {
					return nil, err
				}
			}
			for i := range desired {
				if desired[i].Source.Type == "@blob" {
					desired[i].Source.Rel = dir + "/" + desired[i].Source.Rel
				}
			}
		}
	}
	if err := s.checkOverlap(in, d, desired); err != nil {
		return nil, err
	}
	plan, err := e.PlanTo(desired, in.ActiveProfile, s.fingerprint(in, d))
	if err != nil {
		return nil, uerr("Nie można przygotować wdrożenia: %v", err)
	}
	r, err := e.Apply(plan, deploy.ApplyOptions{AllowProtected: allowProtected})
	s.reprotect(in)
	var pe *deploy.ProtectedError
	if errors.As(err, &pe) {
		return nil, &UserError{Message: "Mod nadpisze chronione pliki gry:\n" + strings.Join(pe.Paths, "\n") + "\n\nKontynuować? Oryginały zostaną zachowane w kopii.", Confirm: "protected"}
	}
	if err != nil {
		return nil, uerr("%v", err)
	}
	res.Changed, res.Drift = r.Changed, r.Drift
	return res, nil
}

// checkOverlap refuses to deploy into a file that another install has
// deployed (two copies of a game share Documents/AppData files such as
// plugins.txt: each would take the other's file for the original).
func (s *Service) checkOverlap(in *Install, d *gamedef.Definition, desired []deploy.Desired) error {
	if len(desired) == 0 {
		return nil
	}
	mine := map[string]bool{}
	r := s.resolver(in, d)
	for _, w := range desired {
		if abs, err := r.Abs(w.Target); err == nil {
			mine[strings.ToLower(filepath.Clean(abs))] = true
		}
	}
	for _, other := range s.installs {
		if other.ID == in.ID {
			continue
		}
		od := s.defs.Get(other.DefID)
		if od == nil {
			continue
		}
		e, err := s.engine(other)
		if err != nil {
			continue
		}
		man, err := e.Manifest()
		if err != nil {
			continue
		}
		or := s.resolver(other, od)
		for _, en := range man.Entries {
			if abs, err := or.Abs(en.Target); err == nil && mine[strings.ToLower(filepath.Clean(abs))] {
				return uerr("Gra „%s” ma już wdrożony plik %s. Dwie instalacje nie mogą jednocześnie zarządzać tym samym plikiem – przywróć „%s” do stanu bez modów (Przywróć vanilla) albo wyłącz w niej mody.", other.Name, abs, other.Name)
			}
		}
	}
	return nil
}

// reprotect makes the store files of the game read-only again.
func (s *Service) reprotect(in *Install) {
	d := s.defs.Get(in.DefID)
	if d == nil {
		return
	}
	mods, _ := s.store.List(gameKey(in, d))
	for _, m := range mods {
		s.store.Protect(m.GameKey, m.ID)
	}
}

// Deploy puts the active profile into the game.
func (s *Service) Deploy(id string, allowProtected bool) (*DeployResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	return s.apply(in, d, false, allowProtected)
}

// Purge returns the game to the state before the first deployment.
func (s *Service) Purge(id string) (*DeployResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	return s.apply(in, d, true, true)
}

// autoDeploy redeploys after a change when the install wants it and the
// profile is (or was) deployed; errors are reported, the change is kept.
func (s *Service) autoDeploy(in *Install, d *gamedef.Definition) (*DeployResult, error) {
	if !in.AutoDeploy {
		return nil, nil
	}
	return s.apply(in, d, false, false)
}
