// Package app is the launcher's application layer: the bridge channels the
// UI calls, background monitors (game sessions, roadmap, reminders) and the
// media lookups for the UI server. It has no webview dependency, so it is
// tested with a fake host.
package app

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/procwatch"
	"github.com/snakex21/game-launcher/go/internal/remote"
	"github.com/snakex21/game-launcher/go/internal/store"
	"github.com/snakex21/game-launcher/go/internal/thumbs"
)

// Version of the Go launcher (set by main).
var Version = "dev"

// Host is the window side (events to the UI, native window handle).
type Host interface {
	Emit(event string, payload any)
	HWND() uintptr
}

// Dialogs are the native dialogs (faked in tests).
type Dialogs interface {
	OpenFile(hwnd uintptr, title, filterName, patterns string) (string, bool, error)
	PickFolder(hwnd uintptr, title string) (string, bool, error)
	ShellOpen(target string) error
}

// Procs abstracts the process list (faked in tests).
type Procs interface {
	List() ([]procwatch.Process, error)
	Terminate(pid uint32) error
}

type realProcs struct{}

func (realProcs) List() ([]procwatch.Process, error) { return procwatch.List() }
func (realProcs) Terminate(pid uint32) error         { return procwatch.Terminate(pid) }

// session is a running game being timed.
type session struct {
	start    time.Time
	launched bool      // started by us
	grace    time.Time // until then "not running" does not end the session
	pids     map[uint32]bool
}

// App is the application.
type App struct {
	S      *store.Store
	host   Host
	dlg    Dialogs
	procs  Procs
	thumbs *thumbs.Cache
	now    func() time.Time

	mu        sync.Mutex
	sessions  map[string]*session
	owned     map[uint32]string // pid -> game we started
	tracks    map[string]string // music id -> file
	trackOrig map[string]string // file -> path as stored in the playlist
	remote    *remote.Server
	remoteErr string
	started   time.Time
	missing   map[string]bool

	chat chatState
	sys  sysState

	// cloudBase overrides the GitHub API URL (tests).
	cloudBase string
	// updateBase overrides the releases API URL (tests).
	updateBase string

	scanMu     sync.Mutex
	scanCancel context.CancelFunc

	// StartProcess starts a game (replaced in tests).
	StartProcess func(game string, command []string, cwd string) (pid uint32, err error)
}

// New creates the app.
func New(s *store.Store, host Host, dlg Dialogs) *App {
	a := &App{
		S: s, host: host, dlg: dlg, procs: realProcs{},
		thumbs:    thumbs.New(filepath.Join(s.L.CacheDir, "thumbs")),
		now:       time.Now,
		sessions:  map[string]*session{},
		owned:     map[uint32]string{},
		tracks:    map[string]string{},
		trackOrig: map[string]string{},
		missing:   map[string]bool{},
		started:   time.Now(),
	}
	a.StartProcess = a.startProcess
	return a
}

func (a *App) emit(event string, payload any) {
	if a.host != nil {
		a.host.Emit(event, payload)
	}
}

func (a *App) hwnd() uintptr {
	if a.host == nil {
		return 0
	}
	return a.host.HWND()
}

// handler adapts a typed function to a bridge handler.
func handler[T any](fn func(ctx context.Context, in T) (any, error)) bridge.Handler {
	return func(ctx context.Context, p json.RawMessage) (any, error) {
		var in T
		if len(p) > 0 && string(p) != "null" {
			if err := bridge.Decode(p, &in); err != nil {
				return nil, err
			}
		}
		return fn(ctx, in)
	}
}

type nameIn struct {
	Name string `json:"name"`
}

type empty struct{}

// Register wires all channels.
func (a *App) Register(d *bridge.Dispatcher) {
	reg := func(ch string, h bridge.Handler) { d.Handle(ch, h) }
	reg("app.boot", handler(func(_ context.Context, _ empty) (any, error) { return a.Boot(), nil }))
	reg("app.openURL", handler(a.openURL))
	reg("app.openPath", handler(a.openPath))
	reg("dialog.openFile", handler(a.dialogOpenFile))
	reg("dialog.pickFolder", handler(a.dialogPickFolder))

	reg("library.list", handler(func(_ context.Context, _ empty) (any, error) { return a.Library(), nil }))
	reg("library.checkFiles", handler(func(_ context.Context, _ empty) (any, error) { return a.CheckFiles(), nil }))
	reg("game.get", handler(a.gameGet))
	reg("game.save", handler(a.gameSave))
	reg("game.delete", handler(a.gameDelete))
	reg("game.patch", handler(a.gamePatch))
	reg("game.resetStats", handler(a.gameResetStats))
	reg("game.launch", handler(a.gameLaunch))
	reg("game.close", handler(a.gameClose))
	reg("game.rawg", handler(a.gameRAWG))
	reg("game.cover", handler(a.gameCover))
	reg("game.relocate", handler(a.gameRelocate))

	reg("saves.list", handler(a.savesList))
	reg("saves.create", handler(a.savesCreate))
	reg("saves.restore", handler(a.savesRestore))
	reg("saves.delete", handler(a.savesDelete))
	reg("saves.percent", handler(a.savesPercent))

	reg("groups.save", handler(a.groupsSave))
	reg("groups.delete", handler(a.groupsDelete))
	reg("groups.toggleGame", handler(a.groupsToggle))
	reg("filters.meta", handler(func(_ context.Context, _ empty) (any, error) { return a.filtersMeta(), nil }))
	reg("filters.save", handler(a.filtersSave))
	reg("filters.delete", handler(a.filtersDelete))
	reg("genres.save", handler(a.genresSave))

	reg("scan.run", handler(a.scanRun))
	reg("scan.cancel", handler(func(_ context.Context, _ empty) (any, error) { a.scanStop(); return true, nil }))
	reg("scan.import", handler(a.scanImport))

	reg("settings.get", handler(func(_ context.Context, _ empty) (any, error) { return a.Settings(), nil }))
	reg("settings.save", handler(a.settingsSave))
	reg("settings.setSecret", handler(a.settingsSetSecret))
	reg("emulators.save", handler(a.emulatorSave))
	reg("emulators.delete", handler(a.emulatorDelete))
	reg("remote.apply", handler(a.remoteApply))
	reg("remote.regenerate", handler(a.remoteRegenerate))

	reg("stats.get", handler(a.statsGet))
	reg("roadmap.get", handler(func(_ context.Context, _ empty) (any, error) { return a.roadmapView(), nil }))
	reg("roadmap.add", handler(a.roadmapAdd))
	reg("roadmap.complete", handler(a.roadmapComplete))
	reg("roadmap.delete", handler(a.roadmapDelete))
	reg("reminders.add", handler(a.remindersAdd))
	reg("reminders.delete", handler(a.remindersDelete))
	reg("achievements.list", handler(func(_ context.Context, _ empty) (any, error) { return a.achievements(), nil }))
	reg("music.list", handler(func(_ context.Context, _ empty) (any, error) { return a.musicList(), nil }))
	reg("music.savePlaylist", handler(a.musicSavePlaylist))
	reg("music.deletePlaylist", handler(a.musicDeletePlaylist))
	reg("music.addFolder", handler(a.musicAddFolder))
	reg("music.state", handler(a.musicState))
	reg("news.get", handler(a.newsGet))
	reg("news.save", handler(a.newsSave))
	reg("library.duplicates", handler(func(_ context.Context, _ empty) (any, error) { return a.Duplicates(), nil }))
	reg("themes.get", handler(func(_ context.Context, _ empty) (any, error) { return a.themes(), nil }))
	reg("themes.save", handler(a.themeSave))
	reg("themes.apply", handler(a.themeApply))
	reg("themes.delete", handler(a.themeDelete))
	reg("achdefs.get", handler(a.achDefs))
	reg("achdefs.save", handler(a.achDefSave))
	reg("achdefs.delete", handler(a.achDefDelete))
	reg("backup.create", handler(a.backupCreate))
	reg("backup.restore", handler(a.backupRestore))
	reg("shots.scan", handler(a.scanScreenshots))
	reg("shots.add", handler(a.screenshotAdd))
	reg("shots.remove", handler(a.screenshotRemove))
	reg("music.cover", handler(a.musicCover))
	reg("system.get", handler(func(_ context.Context, _ empty) (any, error) { return a.systemSettings(), nil }))
	reg("system.save", handler(a.systemSave))
	reg("update.check", handler(a.updateCheck))
	reg("update.install", handler(a.updateInstall))
	reg("cloud.backup", handler(a.cloudBackup))
	reg("cloud.restore", handler(a.cloudRestore))
	reg("chat.status", handler(func(_ context.Context, _ empty) (any, error) { return a.chatStatus(), nil }))
	reg("chat.connect", handler(a.chatConnect))
	reg("chat.logout", handler(a.chatLogout))
	reg("chat.send", handler(a.chatSend))
	reg("chat.upload", handler(a.chatUpload))
	reg("chat.fetch", handler(a.chatFetch))
	reg("chat.host", handler(a.chatHost))
	reg("chat.serverSave", handler(a.chatServerSave))
	reg("chat.serverDelete", handler(a.chatServerDelete))
}

// --------------------------------------------------------------- helpers

func (a *App) appDir() string { return a.S.L.AppDir }

// resolveAsset turns a stored asset path (cover, screenshot) into an
// absolute path: relative paths are relative to the launcher folder.
func (a *App) resolveAsset(p string) string {
	if p == "" {
		return ""
	}
	r := paths.Resolve(p, a.appDir())
	return paths.FindExisting(r, a.appDir(), paths.Exists)
}

func (a *App) openURL(_ context.Context, in struct{ URL string }) (any, error) {
	u, err := url.Parse(in.URL)
	if err != nil || (u.Scheme != "https" && u.Scheme != "http") || u.Host == "" {
		return nil, bridge.Errf("Niedozwolony adres.")
	}
	return true, a.dlg.ShellOpen(u.String())
}

// openPath opens a folder of a game (exe or save folder) or a data folder.
func (a *App) openPath(_ context.Context, in struct {
	Name  string `json:"name"`
	Which string `json:"which"`
}) (any, error) {
	var target string
	switch in.Which {
	case "data":
		target = a.S.L.DataDir
	case "backups":
		target = filepath.Join(a.S.L.GamesSaves)
	default:
		a.S.ReadConfig(func(cfg *ojson.Object) {
			g := cfg.Obj("games").Obj(in.Name)
			if g == nil {
				return
			}
			switch in.Which {
			case "save":
				target = g.Str("save_path")
			case "exe":
				p := g.Str("exe_path")
				if g.Str("game_type") == "emulator" {
					p = g.Str("rom_path")
				}
				if p != "" {
					target = paths.Dir(paths.FindExisting(p, a.appDir(), paths.Exists))
				}
			}
		})
	}
	if target == "" || !paths.Exists(target) {
		return nil, bridge.Errf("Folder nie istnieje: %s", target)
	}
	return true, a.dlg.ShellOpen(target)
}

func (a *App) dialogOpenFile(_ context.Context, in struct {
	Title string `json:"title"`
	Kind  string `json:"kind"`
}) (any, error) {
	name, pat := "Wszystkie pliki", "*"
	switch in.Kind {
	case "exe":
		name, pat = "Programy", "*.exe;*.bat;*.cmd;*.lnk;*.url"
	case "image":
		name, pat = "Obrazy", "*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp"
	case "rom":
		name, pat = "Obrazy gier", "*.iso;*.bin;*.cue;*.chd;*.cso;*.img;*.zip;*.7z;*.nes;*.sfc;*.smc;*.gba;*.gb;*.gbc;*.nds;*.n64;*.z64;*.gcm;*.rvz;*.wbfs;*.elf;*"
	}
	p, ok, err := a.dlg.OpenFile(a.hwnd(), in.Title, name, pat)
	if err != nil || !ok {
		return nil, err
	}
	return p, nil
}

func (a *App) dialogPickFolder(_ context.Context, in struct {
	Title string `json:"title"`
}) (any, error) {
	p, ok, err := a.dlg.PickFolder(a.hwnd(), in.Title)
	if err != nil || !ok {
		return nil, err
	}
	return p, nil
}

func fmtDuration(sec float64) string {
	if sec < 60 {
		return "0 min"
	}
	h := int(sec) / 3600
	m := (int(sec) % 3600) / 60
	if h == 0 {
		return fmt.Sprintf("%d min", m)
	}
	return fmt.Sprintf("%d h %d min", h, m)
}

// Shutdown stops background work and records launcher usage.
func (a *App) Shutdown() {
	a.scanStop()
	a.mu.Lock()
	r := a.remote
	a.remote = nil
	a.mu.Unlock()
	r.Stop()
	a.stopChat()
	a.stopSystem()
	a.recordUsage()
}

// recordUsage adds this run's time to local_settings (same keys as Python).
func (a *App) recordUsage() {
	elapsed := a.now().Sub(a.started).Seconds()
	if elapsed <= 0 {
		return
	}
	day := a.now().Format("2006-01-02")
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		l.Set("total_launcher_usage_seconds", ojson.Float(l.Float("total_launcher_usage_seconds", 0)+elapsed))
		daily := l.EnsureObj("launcher_daily_usage_seconds")
		daily.Set(day, ojson.Float(daily.Float(day, 0)+elapsed))
		return nil
	})
	if err != nil {
		log.Printf("[usage] %v", err)
	}
}

// markRunDay updates last_run_date / consecutive_days at start.
func (a *App) markRunDay() {
	today := a.now().Format("2006-01-02")
	yesterday := a.now().AddDate(0, 0, -1).Format("2006-01-02")
	_ = a.S.UpdateLocal(func(l *ojson.Object) error {
		last := l.Str("last_run_date")
		switch last {
		case today:
			return nil
		case yesterday:
			l.Set("consecutive_days", l.Int("consecutive_days", 0)+1)
		default:
			l.Set("consecutive_days", 1)
		}
		l.Set("last_run_date", today)
		return nil
	})
}

// Start runs the startup work that must not delay the first paint.
func (a *App) Start(ctx context.Context) {
	go func() {
		a.markRunDay()
		a.remoteFromSettings()
		a.emit("library:files", a.CheckFiles())
		a.startChatHost()
		a.chatAutoConnect()
		a.discordIdle()
	}()
	go a.monitor(ctx)
}

func lower(s string) string { return strings.ToLower(s) }

func fileExists(p string) bool {
	st, err := os.Stat(p)
	return err == nil && !st.IsDir()
}
