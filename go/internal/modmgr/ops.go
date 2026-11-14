package modmgr

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/modmgr/archive"
	"github.com/snakex21/game-launcher/go/internal/modmgr/conflict"
	"github.com/snakex21/game-launcher/go/internal/modmgr/deploy"
	"github.com/snakex21/game-launcher/go/internal/modmgr/detect"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/ids"
	"github.com/snakex21/game-launcher/go/internal/modmgr/install"
	"github.com/snakex21/game-launcher/go/internal/modmgr/loadorder"
	"github.com/snakex21/game-launcher/go/internal/modmgr/modstore"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
	"github.com/snakex21/game-launcher/go/internal/paths"
)

// ---------------------------------------------------------------- views

// DefInfo describes a definition for the UI.
type DefInfo struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Engine   string   `json:"engine"`
	Generic  bool     `json:"generic"`
	Builtin  bool     `json:"builtin"`
	ModTypes []TypeKV `json:"modTypes"`
}

// TypeKV is a mod type id + name.
type TypeKV struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

// Definitions lists the selectable definitions.
func (s *Service) Definitions() []DefInfo {
	var out []DefInfo
	for _, d := range s.defs.List() {
		di := DefInfo{ID: d.ID, Name: d.Name, Engine: d.Engine, Generic: d.IsGeneric(), Builtin: d.Builtin}
		for _, t := range d.ModTypes {
			di.ModTypes = append(di.ModTypes, TypeKV{t.ID, t.Name})
		}
		out = append(out, di)
	}
	return out
}

// InstallSummary is one row of the game list.
type InstallSummary struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Game     string `json:"game,omitempty"`
	DefName  string `json:"defName"`
	Path     string `json:"path"`
	Missing  bool   `json:"missing"`
	Deployed int    `json:"deployed"`
}

// Installs lists the managed games.
func (s *Service) Installs() []InstallSummary {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []InstallSummary
	for _, in := range s.installs {
		row := InstallSummary{ID: in.ID, Name: in.Name, Game: in.Game, Path: s.gamePath(in)}
		if d := s.defs.Get(in.DefID); d != nil {
			row.DefName = d.Name
		}
		if st, err := os.Stat(row.Path); err != nil || !st.IsDir() {
			row.Missing = true
		}
		if e, err := s.engine(in); err == nil {
			if m, err := e.Manifest(); err == nil {
				row.Deployed = len(m.Entries)
			}
		}
		out = append(out, row)
	}
	sort.SliceStable(out, func(i, j int) bool { return strings.ToLower(out[i].Name) < strings.ToLower(out[j].Name) })
	return out
}

// InstallForGame returns the install linked to a library game ("" if none).
func (s *Service) InstallForGame(game string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, in := range s.installs {
		if in.Game != "" && in.Game == game {
			return in.ID
		}
	}
	return ""
}

// ModRow is one mod in the list.
type ModRow struct {
	ID         string           `json:"id"`
	Name       string           `json:"name"`
	Version    string           `json:"version,omitempty"`
	InProfile  bool             `json:"inProfile"`
	Enabled    bool             `json:"enabled"`
	Order      int              `json:"order"`
	Files      int              `json:"files"`
	Size       int64            `json:"size"`
	Source     string           `json:"source"`
	Conflicts  conflict.Summary `json:"conflicts"`
	Executable bool             `json:"executable"`
	Badges     []string         `json:"badges,omitempty"`
	ModType    string           `json:"modType"`
	Installed  string           `json:"installed"`
	Warnings   []string         `json:"warnings,omitempty"`
}

// ProfileInfo is a profile name.
type ProfileInfo struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Active bool   `json:"active"`
}

// Executable is a way to start the game.
type Executable struct {
	ID      string   `json:"id"`
	Name    string   `json:"name"`
	Path    string   `json:"path"`
	Args    []string `json:"args,omitempty"`
	Exists  bool     `json:"exists"`
	Default bool     `json:"default"`
}

// View is the full state of one install for the UI.
type View struct {
	Install      *Install               `json:"install"`
	Path         string                 `json:"path"`
	Def          DefInfo                `json:"def"`
	Profiles     []ProfileInfo          `json:"profiles"`
	Mods         []ModRow               `json:"mods"`
	Plugins      []loadorder.PluginInfo `json:"plugins,omitempty"`
	LoadOrder    string                 `json:"loadOrder"`
	Strategy     string                 `json:"strategy"`
	Deployed     int                    `json:"deployed"`
	DeployedProf string                 `json:"deployedProfile,omitempty"`
	InSync       bool                   `json:"inSync"`
	GameUpdated  bool                   `json:"gameUpdated"`
	Pending      bool                   `json:"pending"`
	Warnings     []string               `json:"warnings,omitempty"`
	Notes        []string               `json:"notes,omitempty"`
	Executables  []Executable           `json:"executables,omitempty"`
	LaunchArgs   []string               `json:"launchArgs,omitempty"`
	Recovered    []string               `json:"recovered,omitempty"`
}

// GetView builds the view of an install.
func (s *Service) GetView(id string) (*View, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	v := &View{Install: in, Path: s.gamePath(in), LoadOrder: d.LoadOrder.Kind, Recovered: s.Recovered}
	v.Def = DefInfo{ID: d.ID, Name: d.Name, Engine: d.Engine, Generic: d.IsGeneric(), Builtin: d.Builtin}
	for _, t := range d.ModTypes {
		v.Def.ModTypes = append(v.Def.ModTypes, TypeKV{t.ID, t.Name})
	}
	launch, hard := strategyKinds(d)
	switch {
	case launch:
		v.Strategy = "argumenty uruchomienia (pliki zostają w magazynie)"
	case hard && sameVolume(v.Path, s.root):
		v.Strategy = "dowiązania twarde (bez kopiowania)"
	default:
		v.Strategy = "kopie plików"
	}
	if st, err := os.Stat(v.Path); err != nil || !st.IsDir() {
		v.Warnings = append(v.Warnings, "Folder gry nie istnieje: "+v.Path+" (dysk odłączony albo gra przeniesiona).")
	}
	profs, err := s.profiles(in)
	if err != nil {
		return nil, err
	}
	for _, p := range profs {
		v.Profiles = append(v.Profiles, ProfileInfo{ID: p.ID, Name: p.Name, Active: p.ID == in.ActiveProfile})
	}
	p, err := s.active(in)
	if err != nil {
		return nil, err
	}
	key := gameKey(in, d)
	all, err := s.store.List(key)
	if err != nil {
		return nil, err
	}
	ds, derr := s.computeDesired(in, d, p)
	summaries := map[string]conflict.Summary{}
	if derr == nil {
		summaries = ds.index.Summaries()
		v.Warnings = append(v.Warnings, ds.warnings...)
		if ds.lo != nil {
			v.Plugins = ds.lo.Plugins
		}
	} else {
		v.Warnings = append(v.Warnings, derr.Error())
	}
	inProfile := map[string]ProfileMod{}
	pos := map[string]int{}
	for i, pm := range p.Mods {
		inProfile[pm.ModID] = pm
		pos[pm.ModID] = i
	}
	fwMissing := s.missingFrameworks(in, d)
	for _, m := range all {
		pm, ok := inProfile[m.ID]
		row := ModRow{ID: m.ID, Name: m.Name, Version: m.Version, InProfile: ok, Enabled: ok && pm.Enabled, Order: -1,
			Files: len(m.Files), Size: m.TotalSize(), Source: m.Source.Name, Conflicts: summaries[m.ID], Executable: m.ExecutableContent,
			ModType: m.ModType, Installed: m.Installed.Local().Format("2006-01-02 15:04"), Warnings: m.Warnings}
		if ok {
			row.Order = pos[m.ID]
		}
		if m.ExecutableContent {
			row.Badges = append(row.Badges, "executable")
		}
		for _, fw := range fwMissing {
			if modNeeds(fw, m) {
				row.Badges = append(row.Badges, "needs:"+fw.Name)
			}
		}
		v.Mods = append(v.Mods, row)
	}
	sort.SliceStable(v.Mods, func(i, j int) bool {
		a, b := v.Mods[i], v.Mods[j]
		if (a.Order >= 0) != (b.Order >= 0) {
			return a.Order >= 0
		}
		if a.Order != b.Order {
			return a.Order < b.Order
		}
		return a.ID < b.ID
	})
	// deployed state
	e, _ := s.engine(in)
	v.Pending = e.Pending()
	if man, err := e.Manifest(); err == nil {
		v.Deployed = len(man.Entries)
		v.DeployedProf = man.ProfileID
		if derr == nil {
			v.InSync = s.inSync(man, ds, in)
		}
		if len(man.Entries) > 0 && len(man.Fingerprint) > 0 {
			now := s.fingerprint(in, d)
			for k, val := range man.Fingerprint {
				if now[k] != val {
					v.GameUpdated = true
				}
			}
		}
	} else {
		v.Warnings = append(v.Warnings, err.Error())
	}
	if v.GameUpdated {
		for _, w := range d.WarningsWhen("on-game-update") {
			v.Warnings = append(v.Warnings, w.Text)
		}
		v.Warnings = append(v.Warnings, "Gra zmieniła się od ostatniego wdrożenia (aktualizacja?). Kliknij „Sprawdź pliki”, a potem „Wdróż” – nowe pliki gry zostaną zachowane jako oryginały.")
	}
	for _, w := range d.WarningsWhen("always") {
		v.Notes = append(v.Notes, w.Text)
	}
	if len(all) > 0 {
		for _, w := range d.WarningsWhen("on-first-mod") {
			v.Notes = append(v.Notes, w.Text)
		}
	}
	if !loadorder.Supported(d.LoadOrder.Kind) {
		v.Notes = append(v.Notes, fmt.Sprintf("Plik kolejności ładowania (%s) nie jest jeszcze zapisywany – pliki modów są wdrażane, kolejność ustaw w narzędziu gry.", d.LoadOrder.Kind))
	}
	if d.Launch != nil && d.Launch.SteamLaunchOptionsHint != "" {
		v.Notes = append(v.Notes, "Opcje uruchamiania w Steam: "+d.Launch.SteamLaunchOptionsHint)
	}
	v.Executables = s.executables(in, d)
	if launch && derr == nil {
		v.LaunchArgs = loadorder.LaunchArgs(d, ds.placed, paths.Resolve(in.Iwad, s.appDir))
	}
	return v, nil
}

func (s *Service) inSync(man *deploy.Manifest, ds *desiredState, in *Install) bool {
	if ds.launch {
		return true
	}
	if len(ds.desired) == 0 {
		return len(man.Entries) == 0
	}
	if man.ProfileID != in.ActiveProfile || len(man.Entries) != len(ds.desired) {
		return false
	}
	have := map[string]string{}
	for _, en := range man.Entries {
		have[en.Target.Key()] = en.SHA256
	}
	for _, w := range ds.desired {
		if have[w.Target.Key()] != w.SHA256 {
			return false
		}
	}
	return true
}

func (s *Service) missingFrameworks(in *Install, d *gamedef.Definition) []gamedef.Framework {
	var out []gamedef.Framework
	root := s.gamePath(in)
	for _, fw := range d.Frameworks {
		if fw.Detect == nil {
			continue
		}
		ok := len(fw.Detect.AllFiles) > 0 || len(fw.Detect.AnyFiles) > 0
		for _, f := range fw.Detect.AllFiles {
			if !globExists(root, f) {
				ok = false
			}
		}
		if len(fw.Detect.AnyFiles) > 0 {
			any := false
			for _, f := range fw.Detect.AnyFiles {
				if globExists(root, f) {
					any = true
				}
			}
			ok = ok && any
		}
		if !ok {
			out = append(out, fw)
		}
	}
	return out
}

func globExists(root, pattern string) bool {
	m, _ := filepath.Glob(filepath.Join(root, filepath.FromSlash(pattern)))
	return len(m) > 0
}

func modNeeds(fw gamedef.Framework, m *modstore.Mod) bool {
	if fw.ModRequiresIf == nil {
		return false
	}
	for _, f := range m.Files {
		for _, p := range fw.ModRequiresIf.AnyFiles {
			if relpath.Match(p, f.Rel) || relpath.Match(p, relpath.Join("Data", f.Rel)) {
				return true
			}
		}
	}
	return false
}

func (s *Service) executables(in *Install, d *gamedef.Definition) []Executable {
	r := s.resolver(in, d)
	var out []Executable
	for _, x := range d.Executables {
		abs, err := r.AbsTemplate(x.Path)
		if err != nil {
			continue
		}
		var args []string
		for _, a := range x.Args {
			if strings.HasPrefix(a, "{") {
				if v, err := r.AbsTemplate(a); err == nil {
					a = v
				}
			}
			args = append(args, a)
		}
		_, err = os.Stat(abs)
		out = append(out, Executable{ID: x.ID, Name: x.Name, Path: abs, Args: args, Exists: err == nil, Default: x.Default})
	}
	return out
}

// LaunchCommand returns the command to start the game with its mods.
func (s *Service) LaunchCommand(id, exeID string) ([]string, string, error) {
	v, err := s.GetView(id)
	if err != nil {
		return nil, "", err
	}
	s.mu.Lock()
	in, d, err := s.install(id)
	s.mu.Unlock()
	if err != nil {
		return nil, "", err
	}
	var exe *Executable
	for i := range v.Executables {
		x := &v.Executables[i]
		if x.ID == exeID || (exeID == "" && x.Default) {
			exe = x
			break
		}
	}
	if exe == nil {
		for i := range v.Executables {
			if v.Executables[i].Exists {
				exe = &v.Executables[i]
				break
			}
		}
	}
	if exe == nil || !exe.Exists {
		return nil, "", uerr("Nie znaleziono pliku uruchomieniowego gry.")
	}
	cmd := append([]string{exe.Path}, exe.Args...)
	cmd = append(cmd, v.LaunchArgs...)
	enabled := 0
	for _, m := range v.Mods {
		if m.Enabled {
			enabled++
		}
	}
	if d.Launch != nil && enabled > 0 {
		cmd = append(cmd, d.Launch.ModdedArgs...)
	}
	if !v.InSync && in.AutoDeploy {
		if _, err := s.Deploy(id, false); err != nil {
			return nil, "", err
		}
	}
	return cmd, filepath.Dir(exe.Path), nil
}

// ---------------------------------------------------------------- import

// ImportIn describes an import.
type ImportIn struct {
	Install        string `json:"install"`
	Path           string `json:"path"`
	Name           string `json:"name"`
	Root           string `json:"root"`
	ModType        string `json:"modType"`
	Enable         bool   `json:"enable"`
	AllowDuplicate bool   `json:"allowDuplicate"`
	AckExecutable  bool   `json:"ackExecutable"`
}

// PreviewFile is one planned file with its destination.
type PreviewFile struct {
	Source string `json:"source"`
	Target string `json:"target"`
	Type   string `json:"type"`
}

// Preview is the plan shown before importing.
type Preview struct {
	Plan     *install.Plan `json:"plan"`
	Files    []PreviewFile `json:"files"`
	More     int           `json:"more"`
	Kind     string        `json:"kind"`
	Warnings []string      `json:"warnings,omitempty"`
}

func (s *Service) openSource(path string) (archive.Source, error) {
	path = strings.TrimSpace(path)
	if path == "" || !filepath.IsAbs(path) {
		return nil, uerr("Wybierz plik albo folder moda.")
	}
	src, err := archive.Open(path)
	if err != nil {
		return nil, uerr("%v", err)
	}
	return src, nil
}

func (s *Service) plan(inst *Install, src archive.Source, d *gamedef.Definition, in ImportIn) (*install.Plan, error) {
	r := s.resolver(inst, d)
	byPath := map[string]archive.Entry{}
	for _, e := range src.Entries() {
		byPath[relpath.Key(e.Path)] = e
	}
	p, err := install.Make(src.Entries(), d, install.Options{
		ModName: strings.TrimSpace(in.Name), SourceName: filepath.Base(in.Path), Root: in.Root, ModType: in.ModType,
		Read: func(p string) ([]byte, error) {
			e, ok := byPath[relpath.Key(p)]
			if !ok {
				return nil, os.ErrNotExist
			}
			return archive.ReadSmall(src, e, 1<<20)
		},
		TargetHasDir: func(typ, dir string) bool {
			mt := d.ModType(typ)
			if mt == nil {
				return false
			}
			abs, err := r.AbsTemplate(mt.Target)
			if err != nil {
				return false
			}
			st, err := os.Stat(filepath.Join(abs, filepath.FromSlash(dir)))
			return err == nil && st.IsDir()
		},
	})
	if err != nil {
		return nil, uerr("%v", err)
	}
	p.Warnings = append(p.Warnings, src.Warnings()...)
	return p, nil
}

// PreviewImport shows where the files of a source would go.
func (s *Service) PreviewImport(in ImportIn) (*Preview, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	inst, d, err := s.install(in.Install)
	if err != nil {
		return nil, err
	}
	src, err := s.openSource(in.Path)
	if err != nil {
		return nil, err
	}
	defer src.Close()
	p, err := s.plan(inst, src, d, in)
	if err != nil {
		return nil, err
	}
	pv := &Preview{Plan: p, Kind: src.Kind()}
	r := s.resolver(inst, d)
	for i, f := range p.Files {
		if i >= 200 {
			pv.More = len(p.Files) - i
			break
		}
		mt := d.ModType(f.ModType)
		target := f.Rel
		if base, err := r.Location(mt.Target); err == nil {
			target = base.Child(f.Rel).String()
		}
		pv.Files = append(pv.Files, PreviewFile{Source: f.Source, Target: target, Type: mt.Name})
	}
	if p.ExecutableContent {
		for _, w := range d.WarningsWhen("on-executable-content") {
			pv.Warnings = append(pv.Warnings, w.Text)
		}
	}
	return pv, nil
}

// Import adds a mod to the store and to the active profile.
func (s *Service) Import(in ImportIn) (*ModRow, *DeployResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	inst, d, err := s.install(in.Install)
	if err != nil {
		return nil, nil, err
	}
	src, err := s.openSource(in.Path)
	if err != nil {
		return nil, nil, err
	}
	defer src.Close()
	p, err := s.plan(inst, src, d, in)
	if err != nil {
		return nil, nil, err
	}
	if in.Enable && p.ExecutableContent && !in.AckExecutable {
		return nil, nil, &UserError{Message: execWarning(d, p.ExecutableFiles), Confirm: "executable"}
	}
	m, err := s.store.Import(gameKey(inst, d), src, in.Path, p, modstore.ImportOptions{AllowDuplicate: in.AllowDuplicate})
	var dup *modstore.ErrDuplicate
	if errors.As(err, &dup) {
		return nil, nil, &UserError{Message: dup.Error() + ". Zainstalować jeszcze raz jako osobną kopię?", Confirm: "duplicate"}
	}
	if err != nil {
		return nil, nil, uerr("Instalacja moda nie powiodła się: %v", err)
	}
	if in.Enable && m.ExecutableContent {
		m.ExecAcknowledged = true
		_ = s.store.Save(m)
	}
	prof, err := s.active(inst)
	if err != nil {
		return nil, nil, err
	}
	prof.Mods = append(prof.Mods, ProfileMod{ModID: m.ID, Enabled: in.Enable})
	if err := s.saveProfile(inst, prof); err != nil {
		return nil, nil, err
	}
	row := &ModRow{ID: m.ID, Name: m.Name, Files: len(m.Files), Enabled: in.Enable}
	var dr *DeployResult
	if in.Enable {
		dr, err = s.autoDeploy(inst, d)
		if err != nil {
			return row, nil, uerr("Mod zainstalowany w magazynie, ale wdrożenie do gry nie powiodło się: %v", err)
		}
	}
	return row, dr, nil
}

func execWarning(d *gamedef.Definition, files []string) string {
	var b strings.Builder
	b.WriteString("Ten mod zawiera kod wykonywalny (uruchamiany z uprawnieniami gry, ma dostęp do Twoich plików):\n")
	for i, f := range files {
		if i == 8 {
			b.WriteString("…\n")
			break
		}
		b.WriteString("  " + f + "\n")
	}
	for _, w := range d.WarningsWhen("on-executable-content") {
		b.WriteString("\n" + w.Text + "\n")
	}
	b.WriteString("\nWłączaj tylko mody z zaufanych źródeł. Kontynuować?")
	return b.String()
}

// ---------------------------------------------------------------- profile edits

func (s *Service) editProfile(id string, fn func(in *Install, d *gamedef.Definition, p *Profile) error) (*DeployResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	p, err := s.active(in)
	if err != nil {
		return nil, err
	}
	if err := fn(in, d, p); err != nil {
		return nil, err
	}
	if err := s.saveProfile(in, p); err != nil {
		return nil, err
	}
	dr, err := s.autoDeploy(in, d)
	if err != nil {
		return nil, uerr("Zmiana zapisana w profilu, ale wdrożenie nie powiodło się: %v", err)
	}
	return dr, nil
}

// SetEnabled turns a mod on or off in the active profile.
func (s *Service) SetEnabled(id, modID string, enabled, ack bool) (*DeployResult, error) {
	return s.editProfile(id, func(in *Install, d *gamedef.Definition, p *Profile) error {
		m, err := s.store.Get(gameKey(in, d), modID)
		if err != nil {
			return uerr("Nie ma takiego moda.")
		}
		if enabled && m.ExecutableContent && !m.ExecAcknowledged {
			if !ack {
				return &UserError{Message: execWarning(d, m.ExecutableFiles), Confirm: "executable"}
			}
			m.ExecAcknowledged = true
			if err := s.store.Save(m); err != nil {
				return err
			}
		}
		for i := range p.Mods {
			if p.Mods[i].ModID == modID {
				p.Mods[i].Enabled = enabled
				return nil
			}
		}
		p.Mods = append(p.Mods, ProfileMod{ModID: modID, Enabled: enabled})
		return nil
	})
}

// Move puts a mod at a new position (0 = lowest priority).
func (s *Service) Move(id, modID string, to int) (*DeployResult, error) {
	return s.editProfile(id, func(in *Install, d *gamedef.Definition, p *Profile) error {
		from := -1
		for i, pm := range p.Mods {
			if pm.ModID == modID {
				from = i
			}
		}
		if from < 0 {
			if _, err := s.store.Get(gameKey(in, d), modID); err != nil {
				return uerr("Nie ma takiego moda.")
			}
			p.Mods = append(p.Mods, ProfileMod{ModID: modID})
			from = len(p.Mods) - 1
		}
		if to < 0 {
			to = 0
		}
		if to >= len(p.Mods) {
			to = len(p.Mods) - 1
		}
		pm := p.Mods[from]
		p.Mods = append(p.Mods[:from], p.Mods[from+1:]...)
		p.Mods = append(p.Mods[:to], append([]ProfileMod{pm}, p.Mods[to:]...)...)
		return nil
	})
}

// SetOverride makes modID win the target key ("" removes the rule).
func (s *Service) SetOverride(id, key, modID string) (*DeployResult, error) {
	return s.editProfile(id, func(in *Install, d *gamedef.Definition, p *Profile) error {
		if p.FileOverrides == nil {
			p.FileOverrides = map[string]string{}
		}
		if modID == "" {
			delete(p.FileOverrides, key)
		} else {
			p.FileOverrides[key] = modID
		}
		_, cms, err := s.profileMods(in, d, p)
		if err != nil {
			return err
		}
		p.FileOverrides = conflict.CleanOverrides(cms, p.FileOverrides)
		if modID != "" && p.FileOverrides[key] != modID {
			return uerr("Ten mod nie dostarcza tego pliku.")
		}
		return nil
	})
}

// ClearOverrides removes all rules of a mod ("" = all rules).
func (s *Service) ClearOverrides(id, modID string) (*DeployResult, error) {
	return s.editProfile(id, func(in *Install, d *gamedef.Definition, p *Profile) error {
		for k, v := range p.FileOverrides {
			if modID == "" || v == modID {
				delete(p.FileOverrides, k)
			}
		}
		return nil
	})
}

// SetPluginOrder stores the plugin order of the active profile.
func (s *Service) SetPluginOrder(id string, order []loadorder.Plugin) (*DeployResult, error) {
	return s.editProfile(id, func(in *Install, d *gamedef.Definition, p *Profile) error {
		var clean []loadorder.Plugin
		seen := map[string]bool{}
		for _, pl := range order {
			n := strings.TrimSpace(pl.Name)
			if n == "" || strings.ContainsAny(n, `/\`) || seen[strings.ToLower(n)] {
				continue
			}
			seen[strings.ToLower(n)] = true
			clean = append(clean, loadorder.Plugin{Name: n, Enabled: pl.Enabled})
		}
		p.PluginOrder = clean
		return nil
	})
}

// RenameMod changes the display name.
func (s *Service) RenameMod(id, modID, name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return err
	}
	m, err := s.store.Get(gameKey(in, d), modID)
	if err != nil {
		return uerr("Nie ma takiego moda.")
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return uerr("Podaj nazwę.")
	}
	m.Name = name
	return s.store.Save(m)
}

// CreateProfile adds a profile (a copy of another one when copyFrom is set).
func (s *Service) CreateProfile(id, name, copyFrom string) (*ProfileInfo, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, _, err := s.install(id)
	if err != nil {
		return nil, err
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return nil, uerr("Podaj nazwę profilu.")
	}
	p := &Profile{ID: ids.New(), Name: name}
	if copyFrom != "" {
		src, err := s.profile(in, copyFrom)
		if err != nil {
			return nil, err
		}
		p.Mods = append(p.Mods, src.Mods...)
		p.PluginOrder = append(p.PluginOrder, src.PluginOrder...)
		if src.FileOverrides != nil {
			p.FileOverrides = map[string]string{}
			for k, v := range src.FileOverrides {
				p.FileOverrides[k] = v
			}
		}
	}
	if err := s.saveProfile(in, p); err != nil {
		return nil, err
	}
	return &ProfileInfo{ID: p.ID, Name: p.Name}, nil
}

// RenameProfile renames a profile.
func (s *Service) RenameProfile(id, profileID, name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, _, err := s.install(id)
	if err != nil {
		return err
	}
	p, err := s.profile(in, profileID)
	if err != nil {
		return err
	}
	if name = strings.TrimSpace(name); name == "" {
		return uerr("Podaj nazwę profilu.")
	}
	p.Name = name
	return s.saveProfile(in, p)
}

// DeleteProfile removes a profile that is not active.
func (s *Service) DeleteProfile(id, profileID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, _, err := s.install(id)
	if err != nil {
		return err
	}
	if profileID == in.ActiveProfile {
		return uerr("Nie można usunąć aktywnego profilu – najpierw przełącz się na inny.")
	}
	if _, err := s.profile(in, profileID); err != nil {
		return err
	}
	return os.Remove(filepath.Join(s.profileDir(in), profileID+".json"))
}

// ActivateProfile switches profiles (and redeploys when automatic).
func (s *Service) ActivateProfile(id, profileID string) (*DeployResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	if _, err := s.profile(in, profileID); err != nil {
		return nil, err
	}
	prev := in.ActiveProfile
	in.ActiveProfile = profileID
	if err := s.saveInstalls(); err != nil {
		in.ActiveProfile = prev
		return nil, err
	}
	dr, err := s.autoDeploy(in, d)
	if err != nil {
		return nil, uerr("Profil przełączony, ale wdrożenie nie powiodło się: %v", err)
	}
	return dr, nil
}

// UninstallMod removes a mod from the game (purging its files from every
// install that has them deployed), from all profiles and from the store.
func (s *Service) UninstallMod(id, modID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return err
	}
	key := gameKey(in, d)
	if _, err := s.store.Get(key, modID); err != nil {
		return uerr("Nie ma takiego moda.")
	}
	// every install sharing the store
	var sharing []*Install
	for _, other := range s.installs {
		od := s.defs.Get(other.DefID)
		if od != nil && gameKey(other, od) == key {
			sharing = append(sharing, other)
		}
	}
	for _, other := range sharing {
		profs, err := s.profiles(other)
		if err != nil {
			return err
		}
		for _, p := range profs {
			changed := false
			for i := 0; i < len(p.Mods); i++ {
				if p.Mods[i].ModID == modID {
					p.Mods = append(p.Mods[:i], p.Mods[i+1:]...)
					i--
					changed = true
				}
			}
			for k, v := range p.FileOverrides {
				if v == modID {
					delete(p.FileOverrides, k)
					changed = true
				}
			}
			if changed {
				if err := s.saveProfile(other, p); err != nil {
					return err
				}
			}
		}
		// files still deployed from this mod must go before the store copy does
		e, _ := s.engine(other)
		man, err := e.Manifest()
		if err != nil {
			return err
		}
		uses := false
		for _, en := range man.Entries {
			if en.Source.ModID == modID {
				uses = true
			}
		}
		if uses {
			od := s.defs.Get(other.DefID)
			if _, err := s.apply(other, od, false, true); err != nil {
				return uerr("Nie można usunąć plików moda z gry „%s”: %v", other.Name, err)
			}
		}
	}
	return s.store.Remove(key, modID)
}

// ---------------------------------------------------------------- files & conflicts

// FileRow is one file of a mod with its conflict state.
type FileRow struct {
	Key       string   `json:"key"`
	Target    string   `json:"target"`
	Size      int64    `json:"size"`
	State     string   `json:"state"` // only|wins|loses|identical
	Rule      string   `json:"rule,omitempty"`
	Winner    string   `json:"winner,omitempty"`
	Providers []string `json:"providers,omitempty"`
}

// ModFiles lists a mod's files and how they fare in the active profile.
func (s *Service) ModFiles(id, modID string) ([]FileRow, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	p, err := s.active(in)
	if err != nil {
		return nil, err
	}
	m, err := s.store.Get(gameKey(in, d), modID)
	if err != nil {
		return nil, uerr("Nie ma takiego moda.")
	}
	_, cms, err := s.profileMods(in, d, p)
	if err != nil {
		return nil, err
	}
	idx := conflict.Build(cms, p.FileOverrides)
	names := map[string]string{}
	for _, c := range cms {
		names[c.ID] = c.Name
	}
	r := s.resolver(in, d)
	var out []FileRow
	for _, f := range m.Files {
		mt := d.ModType(f.Type)
		if mt == nil {
			continue
		}
		base, err := r.Location(mt.Target)
		if err != nil {
			continue
		}
		loc := base.Child(f.Rel)
		row := FileRow{Key: loc.Key(), Target: loc.String(), Size: f.Size, State: "only"}
		if e := idx.Entries[loc.Key()]; e != nil && e.Conflicted() {
			row.Rule, row.Winner = e.Rule, names[e.Winner]
			for _, pr := range e.Providers {
				row.Providers = append(row.Providers, pr.Name)
			}
			switch {
			case e.Identical:
				row.State = "identical"
			case e.Winner == modID:
				row.State = "wins"
			default:
				row.State = "loses"
			}
		}
		out = append(out, row)
	}
	return out, nil
}

// ConflictRow is one conflicted path of the profile.
type ConflictRow struct {
	Key       string   `json:"key"`
	Target    string   `json:"target"`
	Winner    string   `json:"winner"`
	WinnerID  string   `json:"winnerId"`
	Rule      string   `json:"rule"`
	Identical bool     `json:"identical"`
	Providers []TypeKV `json:"providers"`
}

// Conflicts lists all conflicts of the active profile.
func (s *Service) Conflicts(id string) ([]ConflictRow, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	p, err := s.active(in)
	if err != nil {
		return nil, err
	}
	_, cms, err := s.profileMods(in, d, p)
	if err != nil {
		return nil, err
	}
	idx := conflict.Build(cms, p.FileOverrides)
	var out []ConflictRow
	for _, e := range idx.Conflicts() {
		row := ConflictRow{Key: e.Key, Target: e.Target.String(), WinnerID: e.Winner, Rule: e.Rule, Identical: e.Identical}
		for _, pr := range e.Providers {
			row.Providers = append(row.Providers, TypeKV{pr.ModID, pr.Name})
			if pr.ModID == e.Winner {
				row.Winner = pr.Name
			}
		}
		out = append(out, row)
	}
	return out, nil
}

// ---------------------------------------------------------------- verification & detection

// VerifyResult reports the check of an install.
type VerifyResult struct {
	Drift       []deploy.DriftItem `json:"drift"`
	StoreIssues []string           `json:"storeIssues,omitempty"`
	GameUpdated bool               `json:"gameUpdated"`
}

// Verify compares the game with the manifest and checks the store.
func (s *Service) Verify(id string) (*VerifyResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return nil, err
	}
	e, err := s.engine(in)
	if err != nil {
		return nil, err
	}
	drift, man, err := e.Verify()
	if err != nil {
		return nil, uerr("%v", err)
	}
	res := &VerifyResult{Drift: drift}
	if len(man.Entries) > 0 {
		now := s.fingerprint(in, d)
		for k, v := range man.Fingerprint {
			if now[k] != v {
				res.GameUpdated = true
			}
		}
	}
	p, _ := s.active(in)
	if p != nil {
		for _, pm := range p.Mods {
			if !pm.Enabled {
				continue
			}
			probs, err := s.store.Verify(gameKey(in, d), pm.ModID)
			if err != nil {
				continue
			}
			for _, pr := range probs {
				res.StoreIssues = append(res.StoreIssues, fmt.Sprintf("%s: %s (%s)", pm.ModID, pr.Rel, pr.Reason))
			}
		}
	}
	return res, nil
}

// SuggestDefs proposes definitions for a folder or exe path.
func (s *Service) SuggestDefs(path string) []detect.Suggestion {
	path = strings.TrimSpace(path)
	if path == "" {
		return nil
	}
	if st, err := os.Stat(path); err == nil && !st.IsDir() {
		path = filepath.Dir(path)
	}
	return detect.Suggest(s.defs, path)
}

// DetectSteam lists supported games installed through Steam.
func (s *Service) DetectSteam() ([]detect.Found, error) {
	if s.opt.SteamRoot == "" {
		return nil, uerr("Nie znaleziono instalacji Steam.")
	}
	found, err := detect.FromSteam(s.opt.SteamRoot, s.defs)
	if err != nil {
		return nil, uerr("Odczyt bibliotek Steam: %v", err)
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []detect.Found
	for _, f := range found {
		dup := false
		for _, in := range s.installs {
			if strings.EqualFold(filepath.Clean(s.gamePath(in)), filepath.Clean(f.Path)) {
				dup = true
			}
		}
		if !dup {
			out = append(out, f)
		}
	}
	return out, nil
}

// FolderPath returns a folder to open in Explorer: the game folder, the
// mod store of the game or the backups of originals.
func (s *Service) FolderPath(id, which string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	in, d, err := s.install(id)
	if err != nil {
		return "", err
	}
	var p string
	switch which {
	case "store":
		p = filepath.Join(s.root, "store", gameKey(in, d))
	case "backups":
		p = filepath.Join(s.stateDir(in), "backups")
	default:
		p = s.gamePath(in)
	}
	if which == "store" || which == "backups" {
		if err := os.MkdirAll(p, 0o755); err != nil {
			return "", err
		}
	}
	if _, err := os.Stat(p); err != nil {
		return "", uerr("Folder nie istnieje: %s", p)
	}
	return p, nil
}
