package app

import (
	"context"
	"errors"
	"log"
	"path/filepath"
	"sort"
	"sync"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/modmgr"
	"github.com/snakex21/game-launcher/go/internal/modmgr/loadorder"
	"github.com/snakex21/game-launcher/go/internal/ojson"
)

// modsState holds the mod manager (opened on first use: startup recovery
// of an interrupted deployment runs then).
type modsState struct {
	once sync.Mutex
	svc  *modmgr.Service
	err  error
	// Options replaces the system parts in tests.
	Options *modmgr.Options
}

func (a *App) modsService() (*modmgr.Service, error) {
	a.mods.once.Lock()
	defer a.mods.once.Unlock()
	if a.mods.svc != nil {
		return a.mods.svc, nil
	}
	opt := modmgr.Options{Folders: modmgr.SystemFolders(), SteamRoot: modmgr.SteamRoot()}
	if a.mods.Options != nil {
		opt = *a.mods.Options
	}
	if opt.Running == nil {
		opt.Running = func() ([]string, error) {
			list, err := a.procs.List()
			if err != nil {
				return nil, err
			}
			var out []string
			for _, p := range list {
				if p.Exe != "" {
					out = append(out, p.Exe)
				}
			}
			return out, nil
		}
	}
	svc, err := modmgr.New(a.appDir(), opt)
	if err != nil {
		log.Printf("[mods] %v", err)
		return nil, &bridge.UserError{Title: "Menedżer modów", Message: "Nie można otworzyć menedżera modów: " + err.Error()}
	}
	for _, r := range svc.Recovered {
		log.Printf("[mods] %s", r)
	}
	a.mods.svc = svc
	return svc, nil
}

// SetModOptions replaces the mod manager's system parts (tests).
func (a *App) SetModOptions(o modmgr.Options) { a.mods.Options = &o }

// modsErr converts mod manager errors for the UI.
func modsErr(err error) error {
	var ue *modmgr.UserError
	if errors.As(err, &ue) {
		return &bridge.UserError{Message: ue.Message, Confirm: ue.Confirm}
	}
	return err
}

// modsHandler wraps a typed handler that needs the service.
func modsHandler[T any](a *App, fn func(s *modmgr.Service, in T) (any, error)) bridge.Handler {
	return handler(func(_ context.Context, in T) (any, error) {
		s, err := a.modsService()
		if err != nil {
			return nil, err
		}
		res, err := fn(s, in)
		return res, modsErr(err)
	})
}

type modsID struct {
	ID string `json:"id"`
}

type modsModIn struct {
	ID      string `json:"id"`
	Mod     string `json:"mod"`
	Enabled bool   `json:"enabled"`
	Ack     bool   `json:"ack"`
	To      int    `json:"to"`
	Name    string `json:"name"`
	Key     string `json:"key"`
	Profile string `json:"profile"`
	Copy    string `json:"copy"`
	Allow   bool   `json:"allow"`
	Exe     string `json:"exe"`
	Path    string `json:"path"`
	Which   string `json:"which"`
}

func (a *App) registerMods(reg func(string, bridge.Handler)) {
	reg("mods.defs", modsHandler(a, func(s *modmgr.Service, _ empty) (any, error) { return s.Definitions(), nil }))
	reg("mods.installs", modsHandler(a, func(s *modmgr.Service, _ empty) (any, error) {
		return map[string]any{"installs": s.Installs(), "recovered": s.Recovered, "problems": s.Defs().Problems, "games": a.libraryGameFolders()}, nil
	}))
	reg("mods.view", modsHandler(a, func(s *modmgr.Service, in modsID) (any, error) { return s.GetView(in.ID) }))
	reg("mods.suggest", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.SuggestDefs(in.Path), nil }))
	reg("mods.detectSteam", modsHandler(a, func(s *modmgr.Service, _ empty) (any, error) { return s.DetectSteam() }))
	reg("mods.addInstall", modsHandler(a, func(s *modmgr.Service, in modmgr.AddInstallIn) (any, error) { return s.AddInstall(in) }))
	reg("mods.removeInstall", modsHandler(a, func(s *modmgr.Service, in modsID) (any, error) { return true, s.RemoveInstall(in.ID) }))
	reg("mods.setOptions", modsHandler(a, func(s *modmgr.Service, in struct {
		ID string `json:"id"`
		modmgr.SetInstallOptions
	}) (any, error) {
		return true, s.SetOptions(in.ID, in.SetInstallOptions)
	}))
	reg("mods.preview", modsHandler(a, func(s *modmgr.Service, in modmgr.ImportIn) (any, error) { return s.PreviewImport(in) }))
	reg("mods.import", modsHandler(a, func(s *modmgr.Service, in modmgr.ImportIn) (any, error) {
		row, dr, err := s.Import(in)
		if err != nil {
			return nil, err
		}
		return map[string]any{"mod": row, "deploy": dr}, nil
	}))
	reg("mods.setEnabled", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) {
		return s.SetEnabled(in.ID, in.Mod, in.Enabled, in.Ack)
	}))
	reg("mods.move", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.Move(in.ID, in.Mod, in.To) }))
	reg("mods.setOverride", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) {
		return s.SetOverride(in.ID, in.Key, in.Mod)
	}))
	reg("mods.clearOverrides", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) {
		return s.ClearOverrides(in.ID, in.Mod)
	}))
	reg("mods.setPlugins", modsHandler(a, func(s *modmgr.Service, in struct {
		ID      string             `json:"id"`
		Plugins []loadorder.Plugin `json:"plugins"`
	}) (any, error) {
		return s.SetPluginOrder(in.ID, in.Plugins)
	}))
	reg("mods.rename", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return true, s.RenameMod(in.ID, in.Mod, in.Name) }))
	reg("mods.uninstall", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return true, s.UninstallMod(in.ID, in.Mod) }))
	reg("mods.files", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.ModFiles(in.ID, in.Mod) }))
	reg("mods.conflicts", modsHandler(a, func(s *modmgr.Service, in modsID) (any, error) { return s.Conflicts(in.ID) }))
	reg("mods.profileCreate", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.CreateProfile(in.ID, in.Name, in.Copy) }))
	reg("mods.profileRename", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) {
		return true, s.RenameProfile(in.ID, in.Profile, in.Name)
	}))
	reg("mods.profileDelete", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return true, s.DeleteProfile(in.ID, in.Profile) }))
	reg("mods.profileActivate", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.ActivateProfile(in.ID, in.Profile) }))
	reg("mods.deploy", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return s.Deploy(in.ID, in.Allow) }))
	reg("mods.purge", modsHandler(a, func(s *modmgr.Service, in modsID) (any, error) { return s.Purge(in.ID) }))
	reg("mods.verify", modsHandler(a, func(s *modmgr.Service, in modsID) (any, error) { return s.Verify(in.ID) }))
	reg("mods.launch", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) { return a.modsLaunch(s, in.ID, in.Exe) }))
	reg("mods.openFolder", modsHandler(a, func(s *modmgr.Service, in modsModIn) (any, error) {
		p, err := s.FolderPath(in.ID, in.Which)
		if err != nil {
			return nil, err
		}
		return true, a.dlg.ShellOpen(p)
	}))
	reg("mods.legacy", handler(func(_ context.Context, in nameIn) (any, error) { return a.legacyMods(in.Name), nil }))
}

// libraryGameFolders lists library games (PC) with their exe for linking.
func (a *App) libraryGameFolders() []map[string]string {
	var out []map[string]string
	a.S.ReadConfig(func(cfg *ojson.Object) {
		games := cfg.Obj("games")
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil || g.Str("game_type") == "emulator" {
				continue
			}
			out = append(out, map[string]string{"name": name, "exe": a.resolveAsset(g.Str("exe_path"))})
		}
	})
	sort.Slice(out, func(i, j int) bool { return lower(out[i]["name"]) < lower(out[j]["name"]) })
	return out
}

// modsLaunch starts a game through the mod manager (arguments for
// launch-args games, deployment first when out of date).
func (a *App) modsLaunch(s *modmgr.Service, id, exe string) (any, error) {
	cmd, cwd, err := s.LaunchCommand(id, exe)
	if err != nil {
		return nil, err
	}
	name := ""
	for _, in := range s.Installs() {
		if in.ID == id {
			name = in.Game
			if name == "" {
				name = in.Name
			}
		}
	}
	pid, err := a.StartProcess(name, cmd, cwd)
	if err != nil {
		return nil, err
	}
	a.trackStarted(name, "Mody", pid)
	return map[string]any{"pid": pid, "command": cmd}, nil
}

// modsBeforeLaunch deploys the mods of a library game that is linked to
// the mod manager when its profile is not deployed yet.
func (a *App) modsBeforeLaunch(game string) error {
	if a.mods.svc == nil && !fileExists(filepath.Join(a.appDir(), "data", "modmgr", "installs.json")) {
		return nil // mod manager never used: do not open it
	}
	s, err := a.modsService()
	if err != nil {
		return nil
	}
	id := s.InstallForGame(game)
	if id == "" {
		return nil
	}
	v, err := s.GetView(id)
	if err != nil || v.InSync || !v.Install.AutoDeploy || v.LaunchArgs != nil {
		return nil
	}
	if _, err := s.Deploy(id, false); err != nil {
		return &bridge.UserError{Title: "Mody nie zostały wdrożone", Message: modsErr(err).Error() + "\n\nUruchom grę ponownie po rozwiązaniu problemu albo wyłącz automatyczne wdrażanie w menedżerze modów."}
	}
	return nil
}

// legacyMods shows the Python version's mods_data for a game (read-only).
func (a *App) legacyMods(game string) any {
	type mod struct {
		Name     string   `json:"name"`
		Active   bool     `json:"active"`
		Location string   `json:"location,omitempty"`
		Files    []string `json:"files,omitempty"`
		Backup   string   `json:"backup,omitempty"`
	}
	type prof struct {
		Name string `json:"name"`
		Mods []mod  `json:"mods"`
	}
	var out []prof
	a.S.ReadConfig(func(cfg *ojson.Object) {
		g := cfg.Obj("mods_data").Obj(game)
		if g == nil {
			return
		}
		profs := g.Obj("profiles")
		for _, pn := range profs.Keys() {
			p := profs.Obj(pn)
			if p == nil {
				continue
			}
			pr := prof{Name: pn}
			mods := p.Obj("mods")
			for _, mn := range mods.Keys() {
				m := mods.Obj(mn)
				if m == nil {
					continue
				}
				x := mod{Name: mn, Active: m.Bool("active", false), Location: m.Str("location"), Backup: m.Str("backup_folder")}
				for _, f := range m.Arr("files_changed") {
					if s, ok := f.(string); ok {
						x.Files = append(x.Files, s)
					}
				}
				pr.Mods = append(pr.Mods, x)
			}
			if len(pr.Mods) > 0 {
				out = append(out, pr)
			}
		}
	})
	return out
}
