package app

import (
	"context"
	"errors"
	"log"
	"os/exec"
	"strconv"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/launch"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/procwatch"
	"github.com/snakex21/game-launcher/go/internal/rawg"
	"github.com/snakex21/game-launcher/go/internal/remote"
	"github.com/snakex21/game-launcher/go/internal/saves"
	"github.com/snakex21/game-launcher/go/internal/store"
)

// launchGrace: right after a launch, a launcher stub may exit before the
// real game process appears; the session is kept alive meanwhile.
const launchGrace = 45 * time.Second

func (a *App) startProcess(game string, command []string, cwd string) (uint32, error) {
	cmd, err := launch.Start(game, &launch.Spec{Command: command, Cwd: cwd}, nil)
	if err != nil {
		return 0, err
	}
	pid := uint32(cmd.Process.Pid)
	go func(c *exec.Cmd) { _ = c.Wait() }(cmd) // reap; timing uses the process monitor
	return pid, nil
}

// LaunchResult is returned to the UI.
type LaunchResult struct {
	Game    string `json:"game"`
	Profile string `json:"profile"`
	PID     uint32 `json:"pid"`
}

func (a *App) gameLaunch(_ context.Context, in struct {
	Name    string `json:"name"`
	Profile string `json:"profile"`
}) (any, error) {
	return a.Launch(in.Name, in.Profile)
}

// Launch starts a game (optionally with a named profile).
func (a *App) Launch(name, profileName string) (*LaunchResult, error) {
	a.mu.Lock()
	_, running := a.sessions[name]
	a.mu.Unlock()
	if running {
		return nil, &bridge.UserError{Title: "Gra już działa", Message: "„" + name + "” jest już uruchomiona."}
	}
	var spec *launch.Spec
	var buildErr error
	a.S.ReadConfig(func(cfg *ojson.Object) {
		g := cfg.Obj("games").Obj(name)
		if g == nil {
			buildErr = bridge.Errf("Nie znaleziono gry „%s” w bibliotece.", name)
			return
		}
		var prof *ojson.Object
		if profileName != "" {
			for _, p := range g.Arr("launch_profiles") {
				if po, ok := p.(*ojson.Object); ok && po.Str("name") == profileName {
					prof = po
				}
			}
			if prof == nil {
				buildErr = bridge.Errf("Gra „%s” nie ma profilu „%s”.", name, profileName)
				return
			}
		}
		spec, buildErr = launch.Build(name, g, cfg.Obj("emulators"), prof, a.appDir(), paths.Exists)
	})
	if buildErr != nil {
		var le *launch.Error
		if errors.As(buildErr, &le) {
			return nil, &bridge.UserError{Title: le.Title, Message: le.Message}
		}
		return nil, buildErr
	}
	log.Printf("[launch] %s, cwd=%s", spec.Description, spec.Cwd)
	pid, err := a.StartProcess(name, spec.Command, spec.Cwd)
	if err != nil {
		var le *launch.Error
		if errors.As(err, &le) {
			return nil, &bridge.UserError{Title: le.Title, Message: le.Message}
		}
		return nil, err
	}
	now := a.now()
	a.mu.Lock()
	a.sessions[name] = &session{start: now, launched: true, grace: now.Add(launchGrace), pids: map[uint32]bool{pid: true}}
	a.owned[pid] = name
	a.mu.Unlock()
	_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(name)
		if g == nil {
			return nil
		}
		g.Set("last_played", ojson.Float(float64(now.UnixNano())/1e9))
		g.Set("play_count", g.Int("play_count", 0)+1)
		if h := now.Hour(); h >= 2 && h < 4 {
			ach := cfg.EnsureObj("user").EnsureObj("achievements")
			e := ach.EnsureObj("night_owl")
			e.SetDefault("unlocked", false)
			e.Set("_triggered_at_night", true)
		}
		return nil
	})
	a.emit("game:started", map[string]any{"name": name, "profile": spec.ProfileName})
	return &LaunchResult{Game: name, Profile: spec.ProfileName, PID: pid}, nil
}

// targets builds the process-matching targets for all games.
func (a *App) targets() []procwatch.Target {
	var out []procwatch.Target
	a.S.ReadConfig(func(cfg *ojson.Object) {
		games := cfg.Obj("games")
		emus := cfg.Obj("emulators")
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			t := procwatch.Target{Game: name}
			if g.Str("game_type") == "emulator" {
				t.Emulator = true
				t.ROM = paths.FindExisting(g.Str("rom_path"), a.appDir(), paths.Exists)
				if e := emus.Obj(g.Str("emulator_name")); e != nil {
					t.Exes = []string{paths.FindExisting(e.Str("path"), a.appDir(), paths.Exists)}
				}
			} else {
				for _, p := range append([]string{g.Str("exe_path")}, profileExes(g)...) {
					if p == "" {
						continue
					}
					if r := paths.FindExisting(p, a.appDir(), paths.Exists); r != "" {
						p = r
					}
					t.Exes = append(t.Exes, p)
				}
			}
			out = append(out, t)
		}
	})
	return out
}

func profileExes(g *ojson.Object) []string {
	var out []string
	for _, p := range g.Arr("launch_profiles") {
		if po, ok := p.(*ojson.Object); ok && po.Str("exe_path") != "" {
			out = append(out, po.Str("exe_path"))
		}
	}
	return out
}

// Poll checks running processes once and records finished sessions.
func (a *App) Poll() {
	procs, err := a.procs.List()
	if err != nil {
		log.Printf("[monitor] process list: %v", err)
		return
	}
	alive := map[uint32]bool{}
	for _, p := range procs {
		alive[p.PID] = true
	}
	targets := a.targets()
	now := a.now()

	a.mu.Lock()
	for pid := range a.owned {
		if !alive[pid] {
			delete(a.owned, pid)
		}
	}
	ownedBy := map[string]map[uint32]bool{}
	for pid, g := range a.owned {
		if ownedBy[g] == nil {
			ownedBy[g] = map[uint32]bool{}
		}
		ownedBy[g][pid] = true
	}
	a.mu.Unlock()

	var started, ended []string
	type finished struct {
		name       string
		start, end time.Time
	}
	var done []finished
	a.mu.Lock()
	for _, t := range targets {
		pids := procwatch.Match(t, procs, ownedBy[t.Game])
		s, tracking := a.sessions[t.Game]
		switch {
		case len(pids) > 0 && !tracking:
			s = &session{start: now, pids: map[uint32]bool{}}
			a.sessions[t.Game] = s
			started = append(started, t.Game)
			fallthrough
		case len(pids) > 0:
			for _, p := range pids {
				s.pids[p] = true
			}
		case tracking && now.After(s.grace):
			delete(a.sessions, t.Game)
			done = append(done, finished{t.Game, s.start, now})
			ended = append(ended, t.Game)
		}
	}
	a.mu.Unlock()

	for _, name := range started {
		_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
			if g := cfg.Obj("games").Obj(name); g != nil {
				g.Set("last_played", ojson.Float(float64(now.UnixNano())/1e9))
			}
			return nil
		})
		a.emit("game:started", map[string]any{"name": name, "detected": true})
	}
	for _, f := range done {
		a.recordSession(f.name, f.start, f.end)
	}
}

// recordSession adds the play time like the Python monitor did (play_time,
// play_sessions, roadmap time for "Planowana") and runs the autosave.
func (a *App) recordSession(name string, start, end time.Time) {
	elapsed := end.Sub(start).Seconds()
	var savePath string
	autoBackup := true
	var openTasks int
	_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(name)
		if g == nil {
			return nil
		}
		g.Set("play_time", ojson.Float(g.Float("play_time", 0)+elapsed))
		sess := ojson.NewObject()
		sess.Set("start", ojson.Float(float64(start.UnixNano())/1e9))
		sess.Set("end", ojson.Float(float64(end.UnixNano())/1e9))
		g.Set("play_sessions", append(g.Arr("play_sessions"), sess))
		for _, it := range cfg.Arr("roadmap") {
			if o, ok := it.(*ojson.Object); ok && o.Str("game_name") == name && o.Str("status") == "Planowana" {
				o.Set("time_spent", ojson.Float(o.Float("time_spent", 0)+elapsed))
				break
			}
		}
		savePath = g.Str("save_path")
		autoBackup = cfg.Obj("settings").Bool("auto_backup_on_exit", true)
		for _, it := range g.Arr("checklist") {
			if o, ok := it.(*ojson.Object); ok && !o.Bool("done", false) {
				openTasks++
			}
		}
		return nil
	})
	log.Printf("[monitor] %s finished after %.0f s", name, elapsed)
	ev := map[string]any{"name": name, "seconds": elapsed, "openTasks": openTasks}
	if autoBackup && savePath != "" && paths.Exists(savePath) {
		if n, err := saves.Autosave(a.S.L.GamesSaves, name, savePath); err != nil {
			ev["autosaveError"] = err.Error()
		} else {
			ev["autosaved"] = n
		}
	}
	a.emit("game:stopped", ev)
}

// monitor runs the 5 s process poll and the 1 min roadmap/reminder checks.
func (a *App) monitor(ctx context.Context) {
	tick := time.NewTicker(5 * time.Second)
	defer tick.Stop()
	minute := 0
	for {
		func() {
			defer func() {
				if r := recover(); r != nil { // a bug must not stop time tracking
					log.Printf("[monitor] recovered: %v", r)
				}
			}()
			a.Poll()
			if minute%12 == 0 {
				a.checkRoadmap()
				a.checkReminders()
			}
			minute++
		}()
		select {
		case <-ctx.Done():
			return
		case <-tick.C:
		}
	}
}

func (a *App) gameClose(_ context.Context, in nameIn) (any, error) {
	return a.Close(in.Name)
}

// Close ends a running game (its matching processes and their children).
func (a *App) Close(name string) (int, error) {
	procs, err := a.procs.List()
	if err != nil {
		return 0, err
	}
	var target *procwatch.Target
	for _, t := range a.targets() {
		if t.Game == name {
			t := t
			target = &t
		}
	}
	if target == nil {
		return 0, bridge.Errf("Nie znaleziono gry „%s”.", name)
	}
	a.mu.Lock()
	owned := map[uint32]bool{}
	for pid, g := range a.owned {
		if g == name {
			owned[pid] = true
		}
	}
	a.mu.Unlock()
	pids := procwatch.Match(*target, procs, owned)
	if len(pids) == 0 {
		return 0, &bridge.UserError{Title: "Gra nie działa", Message: "Nie znaleziono uruchomionego procesu gry „" + name + "”."}
	}
	n := 0
	var lastErr error
	for _, pid := range procwatch.Descendants(pids, procs) {
		if err := a.procs.Terminate(pid); err != nil {
			lastErr = err
			continue
		}
		n++
	}
	if n == 0 && lastErr != nil {
		return 0, bridge.Errf("Nie udało się zamknąć gry: %v", lastErr)
	}
	a.mu.Lock()
	if s := a.sessions[name]; s != nil {
		s.grace = time.Time{}
	}
	a.mu.Unlock()
	// the monitor (5 s) records the end of the session
	return n, nil
}

// Running lists games with an active session.
func (a *App) Running() []string {
	a.mu.Lock()
	defer a.mu.Unlock()
	out := make([]string, 0, len(a.sessions))
	for k := range a.sessions {
		out = append(out, k)
	}
	return out
}

// ------------------------------------------------------------------- RAWG

func (a *App) gameRAWG(ctx context.Context, in struct {
	Name       string `json:"name"`
	ForceCover bool   `json:"forceCover"`
}) (any, error) {
	key := a.S.Secret("rawg_api_key")
	c := &rawg.Client{Key: key, UserAgent: "GameLauncher-Go/" + Version}
	cctx, cancel := context.WithTimeout(ctx, 60*time.Second)
	defer cancel()
	d, err := c.Fetch(cctx, in.Name)
	if err != nil {
		return nil, err
	}
	var cover string
	var coverErr string
	if d.BackgroundURL != "" {
		cover, err = c.DownloadCover(cctx, in.Name, d.BackgroundURL, a.S.L.ImagesDir)
		if err != nil {
			coverErr = err.Error()
		}
	}
	err = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		g.Set("rawg_id", d.ID)
		g.Set("rawg_slug", d.Slug)
		g.Set("description", d.Description)
		g.Set("release_date", d.Released)
		g.Set("website", d.Website)
		g.Set("developers", d.Developers)
		g.Set("publishers", d.Publishers)
		g.Set("genres_api", d.Genres)
		g.Set("tags_api", d.Tags)
		g.Set("platforms", d.Platforms)
		if d.RequirementsPC != nil {
			r := ojson.NewObject()
			r.Set("minimum", d.RequirementsPC["minimum"])
			r.Set("recommended", d.RequirementsPC["recommended"])
			g.Set("requirements_pc", r)
		}
		if cover != "" {
			g.Set("cover_rawg", cover)
			cur := g.Str("cover_image")
			if in.ForceCover || cur == "" || a.resolveAsset(cur) == "" || g.Bool("_auto_cover", false) {
				g.Set("cover_image", cover)
				g.Delete("_auto_cover")
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return map[string]any{"name": d.Name, "coverError": coverErr}, nil
}

// ------------------------------------------------------------------ saves

func (a *App) savePathOf(name string) (string, error) {
	var p string
	found := false
	a.S.ReadConfig(func(cfg *ojson.Object) {
		if g := cfg.Obj("games").Obj(name); g != nil {
			found = true
			p = g.Str("save_path")
		}
	})
	if !found {
		return "", bridge.Errf("Nie znaleziono gry „%s”.", name)
	}
	return p, nil
}

func (a *App) savesList(_ context.Context, in nameIn) (any, error) {
	p, err := a.savePathOf(in.Name)
	if err != nil {
		return nil, err
	}
	list, err := saves.List(a.S.L.GamesSaves, in.Name)
	if err != nil {
		return nil, err
	}
	if list == nil {
		list = []saves.Entry{}
	}
	return map[string]any{"savePath": p, "valid": p != "" && paths.Exists(p), "entries": list}, nil
}

func (a *App) savesCreate(_ context.Context, in struct {
	Name    string `json:"name"`
	Percent int    `json:"percent"`
}) (any, error) {
	p, err := a.savePathOf(in.Name)
	if err != nil {
		return nil, err
	}
	return saves.Create(a.S.L.GamesSaves, in.Name, p, in.Percent, a.now())
}

func (a *App) savesRestore(_ context.Context, in struct {
	Name string `json:"name"`
	ID   string `json:"id"`
}) (any, error) {
	a.mu.Lock()
	_, running := a.sessions[in.Name]
	a.mu.Unlock()
	if running {
		return nil, bridge.Errf("Zamknij grę przed wczytaniem zapisu.")
	}
	p, err := a.savePathOf(in.Name)
	if err != nil {
		return nil, err
	}
	safety, err := saves.Restore(a.S.L.GamesSaves, in.Name, in.ID, p, a.now())
	if err != nil {
		return nil, err
	}
	return map[string]any{"safety": safety}, nil
}

func (a *App) savesDelete(_ context.Context, in struct {
	Name string `json:"name"`
	ID   string `json:"id"`
}) (any, error) {
	return true, saves.Delete(a.S.L.GamesSaves, in.Name, in.ID)
}

func (a *App) savesPercent(_ context.Context, in struct {
	Name    string `json:"name"`
	ID      string `json:"id"`
	Percent int    `json:"percent"`
}) (any, error) {
	return saves.SetPercent(a.S.L.GamesSaves, in.Name, in.ID, in.Percent)
}

// ---------------------------------------------------------- remote (pilot)

// remote.Backend implementation.
type remoteBackend struct{ a *App }

func (r remoteBackend) Games() []remote.Game {
	var out []remote.Game
	for _, g := range r.a.Library() {
		out = append(out, remote.Game{Name: g.Name, Playtime: fmtDuration(g.PlayTime)})
	}
	return out
}
func (r remoteBackend) Running() []string { return r.a.Running() }
func (r remoteBackend) HasGame(name string) bool {
	ok := false
	r.a.S.ReadConfig(func(cfg *ojson.Object) { ok = cfg.Obj("games").Has(name) })
	return ok
}
func (r remoteBackend) Launch(name string) error {
	_, err := r.a.Launch(name, "")
	if err == nil {
		r.a.emit("library:changed", nil)
	}
	return err
}
func (r remoteBackend) Close(name string) error { _, err := r.a.Close(name); return err }
func (r remoteBackend) CoverPath(name string) string {
	return r.a.CoverFile(name, 240)
}

// remoteFromSettings starts/stops the remote according to local_settings.
func (a *App) remoteFromSettings() {
	var enabled, lan bool
	var port int64
	var token string
	a.S.ReadLocal(func(l *ojson.Object) {
		enabled = l.Bool("remote_control_enabled", false)
		lan = l.Bool("remote_control_bind_lan", false)
		port = l.Int("remote_control_port", store.DefaultRemoteControlPort)
	})
	token = a.S.Secret("remote_control_token")
	a.mu.Lock()
	old := a.remote
	a.remote = nil
	a.remoteErr = ""
	a.mu.Unlock()
	old.Stop()
	if !enabled {
		return
	}
	if token == "" {
		token = remote.GenerateToken()
		_ = a.S.SetSecret("remote_control_token", token)
	}
	if port == store.DefaultChatServerPort || port < 1024 || port > 65535 {
		port = store.DefaultRemoteControlPort
	}
	srv, err := remote.Start(remote.BindHost(lan), int(port), token, remoteBackend{a})
	a.mu.Lock()
	if err != nil {
		a.remoteErr = err.Error()
	} else {
		a.remote = srv
	}
	a.mu.Unlock()
	if err != nil {
		log.Printf("[remote] %v", err)
	}
}

// RemoteStatus is shown in Settings.
type RemoteStatus struct {
	Enabled bool     `json:"enabled"`
	Running bool     `json:"running"`
	Port    int64    `json:"port"`
	LAN     bool     `json:"lan"`
	URLs    []string `json:"urls"` // with the token (shown only in Settings)
	Error   string   `json:"error"`
}

func (a *App) remoteStatus() RemoteStatus {
	var st RemoteStatus
	a.S.ReadLocal(func(l *ojson.Object) {
		st.Enabled = l.Bool("remote_control_enabled", false)
		st.LAN = l.Bool("remote_control_bind_lan", false)
		st.Port = l.Int("remote_control_port", store.DefaultRemoteControlPort)
	})
	a.mu.Lock()
	st.Running = a.remote != nil
	st.Error = a.remoteErr
	a.mu.Unlock()
	if st.Running {
		token := a.S.Secret("remote_control_token")
		hosts := []string{"127.0.0.1"}
		if st.LAN {
			hosts = append(hosts, remote.LANAddresses()...)
		}
		for _, h := range hosts {
			st.URLs = append(st.URLs, "http://"+h+":"+itoa(st.Port)+"/?token="+token)
		}
	}
	return st
}

func itoa(n int64) string { return strconv.FormatInt(n, 10) }

func (a *App) remoteApply(_ context.Context, in struct {
	Enabled bool  `json:"enabled"`
	Port    int64 `json:"port"`
	LAN     bool  `json:"lan"`
}) (any, error) {
	if in.Port == store.DefaultChatServerPort {
		return nil, bridge.Errf("Port %d jest zarezerwowany dla czatu.", in.Port)
	}
	if in.Port < 1024 || in.Port > 65535 {
		return nil, bridge.Errf("Port musi być w zakresie 1024–65535.")
	}
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		l.Set("remote_control_enabled", in.Enabled)
		l.Set("remote_control_port", in.Port)
		l.Set("remote_control_bind_lan", in.LAN)
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.remoteFromSettings()
	return a.remoteStatus(), nil
}

func (a *App) remoteRegenerate(_ context.Context, _ empty) (any, error) {
	if a.S.SecretFromEnv("remote_control_token") {
		return nil, bridge.Errf("Token pochodzi ze zmiennej GL_REMOTE_TOKEN – zmień ją tam.")
	}
	t := remote.GenerateToken()
	if err := a.S.SetSecret("remote_control_token", t); err != nil {
		return nil, err
	}
	a.remoteFromSettings()
	return a.remoteStatus(), nil
}
