package app

import (
	"context"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/winsys"
)

// System integration hooks (implemented on Windows by winsys; nil in tests).
type sysState struct {
	mu      sync.Mutex
	tray    trayAPI
	discord *winsys.Discord
	exe     string
}

type trayAPI interface {
	Notify(title, text string)
	SetHotkeys(map[int]winsys.Hotkey)
	FailedHotkeys() []int
	Close()
}

// Music hotkey actions (keys of local_settings.music_hotkeys, as in Python).
var musicActions = []string{"play_pause", "next_track", "prev_track", "stop_music", "volume_up", "volume_down"}

const hotkeyShow = 100

// DefaultMusicHotkeys are used when local_settings has none.
var DefaultMusicHotkeys = map[string]string{
	"play_pause": "<alt>+<space>", "next_track": "<alt>+<right>", "prev_track": "<alt>+<left>",
	"stop_music": "<alt>+s", "volume_up": "<alt>+<up>", "volume_down": "<alt>+<down>",
}

// Notify shows a system notification (tray balloon/toast) if available.
func (a *App) Notify(title, text string) {
	a.sys.mu.Lock()
	t := a.sys.tray
	a.sys.mu.Unlock()
	if t != nil {
		t.Notify(title, text)
	}
}

// StartSystem creates the tray icon, hotkeys and Discord presence. iconPath
// is an .ico file; show/hide/quit act on the main window.
func (a *App) StartSystem(iconPath string, show func(bool), quit func()) {
	exe, _ := os.Executable()
	a.sys.mu.Lock()
	a.sys.exe = exe
	a.sys.mu.Unlock()
	items := []winsys.MenuItem{{ID: 1, Label: "Pokaż launcher"}, {ID: 2, Label: "Biblioteka"}, {ID: 3, Label: "Statystyki"}, {},
		{ID: 10, Label: "Muzyka: odtwórz / pauza"}, {ID: 11, Label: "Muzyka: następny"}, {ID: 12, Label: "Muzyka: poprzedni"}, {ID: 13, Label: "Muzyka: stop"}, {},
		{ID: 20, Label: "Ustawienia"}, {}, {ID: 99, Label: "Zakończ"}}
	tray, err := winsys.StartTray("Game Launcher", iconPath, items)
	if err != nil {
		log.Printf("[tray] %v", err)
		return
	}
	nav := func(page string) { show(true); a.emit("nav", page) }
	tray.OnClick = func() { show(true) }
	tray.OnMenu = func(id int) {
		switch id {
		case 1:
			show(true)
		case 2:
			nav("library")
		case 3:
			nav("stats")
		case 20:
			nav("settings")
		case 10, 11, 12, 13:
			a.emit("music:cmd", []string{"play_pause", "next_track", "prev_track", "stop_music"}[id-10])
		case 99:
			quit()
		}
	}
	tray.OnHotkey = func(id int) {
		if id == hotkeyShow {
			show(true)
			return
		}
		if id >= 1 && id <= len(musicActions) {
			a.emit("music:cmd", musicActions[id-1])
		}
	}
	a.sys.mu.Lock()
	a.sys.tray = tray
	a.sys.mu.Unlock()
	a.applyHotkeys()
}

// applyHotkeys (re)registers global hotkeys from local_settings.
func (a *App) applyHotkeys() map[string]string {
	a.sys.mu.Lock()
	t := a.sys.tray
	a.sys.mu.Unlock()
	errs := map[string]string{}
	keys := map[int]winsys.Hotkey{}
	a.S.ReadLocal(func(l *ojson.Object) {
		// RegisterHotKey swallows the key system-wide (pynput in the Python
		// version only listened), so global hotkeys are opt-in.
		if l.Bool("global_hotkeys_enabled", false) {
			hk := l.Obj("music_hotkeys")
			for i, act := range musicActions {
				s := hk.Str(act)
				if hk == nil {
					s = DefaultMusicHotkeys[act]
				}
				if s == "" {
					continue
				}
				k, err := winsys.ParseHotkey(s)
				if err != nil {
					errs[act] = err.Error()
					continue
				}
				keys[i+1] = k
			}
		}
		if s := l.Str("launcher_hotkey"); s != "" && l.Bool("global_hotkeys_enabled", false) {
			if k, err := winsys.ParseHotkey(s); err == nil {
				keys[hotkeyShow] = k
			} else {
				errs["launcher_hotkey"] = err.Error()
			}
		}
	})
	if t != nil {
		t.SetHotkeys(keys)
		time.Sleep(150 * time.Millisecond)
		for _, id := range t.FailedHotkeys() {
			name := "launcher_hotkey"
			if id >= 1 && id <= len(musicActions) {
				name = musicActions[id-1]
			}
			errs[name] = "skrót zajęty przez inny program"
		}
	}
	return errs
}

// ---------------------------------------------------------------- discord

func (a *App) discordEnabled() bool {
	on := false
	a.S.ReadLocal(func(l *ojson.Object) { on = l.Bool("discord_rpc_enabled", false) })
	return on
}

func (a *App) discordSet(act *winsys.Activity) {
	if !a.discordEnabled() {
		return
	}
	a.sys.mu.Lock()
	if a.sys.discord == nil {
		a.sys.discord = &winsys.Discord{}
	}
	d := a.sys.discord
	a.sys.mu.Unlock()
	go func() {
		if err := d.Set(act); err != nil {
			log.Printf("[discord] %v", err)
		}
	}()
}

func (a *App) discordIdle() {
	var text string
	a.S.ReadLocal(func(l *ojson.Object) { text = l.Str("discord_status_text") })
	if text == "" {
		text = "W bibliotece gier"
	}
	a.discordSet(&winsys.Activity{Details: text, State: "Game Launcher"})
}

func (a *App) stopSystem() {
	a.sys.mu.Lock()
	t, d := a.sys.tray, a.sys.discord
	a.sys.tray, a.sys.discord = nil, nil
	a.sys.mu.Unlock()
	if t != nil {
		t.Close()
	}
	if d != nil {
		d.Close()
	}
}

// ------------------------------------------------------------- settings

// SystemSettings for the UI.
type SystemSettings struct {
	Autostart      bool              `json:"autostart"`
	AutostartOther string            `json:"autostartOther"` // value pointing at another exe
	Discord        bool              `json:"discord"`
	DiscordText    string            `json:"discordText"`
	HotkeysOn      bool              `json:"hotkeysOn"`
	Hotkeys        map[string]string `json:"hotkeys"`
	LauncherKey    string            `json:"launcherHotkey"`
	HotkeyErrors   map[string]string `json:"hotkeyErrors"`
	Actions        []string          `json:"actions"`
}

func (a *App) systemSettings() SystemSettings {
	s := SystemSettings{Hotkeys: map[string]string{}, Actions: musicActions, HotkeyErrors: map[string]string{}}
	a.sys.mu.Lock()
	exe := a.sys.exe
	a.sys.mu.Unlock()
	if exe != "" {
		cmd, ours := winsys.Autostart(exe)
		s.Autostart = ours
		if cmd != "" && !ours {
			s.AutostartOther = cmd
		}
	}
	a.S.ReadLocal(func(l *ojson.Object) {
		s.Discord = l.Bool("discord_rpc_enabled", false)
		s.DiscordText = l.Str("discord_status_text")
		s.HotkeysOn = l.Bool("global_hotkeys_enabled", false)
		hk := l.Obj("music_hotkeys")
		for _, act := range musicActions {
			if hk == nil {
				s.Hotkeys[act] = DefaultMusicHotkeys[act]
			} else {
				s.Hotkeys[act] = hk.Str(act)
			}
		}
		s.LauncherKey = l.Str("launcher_hotkey")
	})
	return s
}

func (a *App) systemSave(_ context.Context, in SystemSettings) (any, error) {
	for act, v := range in.Hotkeys {
		if v == "" {
			continue
		}
		if _, err := winsys.ParseHotkey(v); err != nil {
			return nil, bridge.Errf("%s: %v", act, err)
		}
	}
	if in.LauncherKey != "" {
		if _, err := winsys.ParseHotkey(in.LauncherKey); err != nil {
			return nil, bridge.Errf("Skrót launchera: %v", err)
		}
	}
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		l.Set("discord_rpc_enabled", in.Discord)
		l.Set("discord_status_text", strings.TrimSpace(in.DiscordText))
		l.Set("global_hotkeys_enabled", in.HotkeysOn)
		hk := l.EnsureObj("music_hotkeys")
		for _, act := range musicActions {
			if v, ok := in.Hotkeys[act]; ok {
				hk.Set(act, strings.TrimSpace(v))
			}
		}
		l.Set("launcher_hotkey", strings.TrimSpace(in.LauncherKey))
		return nil
	})
	if err != nil {
		return nil, err
	}
	// autostart lives in the registry (HKCU Run) - Python kept a copy in
	// settings.autostart, which we keep in sync for compatibility.
	a.sys.mu.Lock()
	exe := a.sys.exe
	a.sys.mu.Unlock()
	if exe != "" {
		if err := winsys.SetAutostart(in.Autostart, exe); err != nil {
			return nil, bridge.Errf("Autostart: %v", err)
		}
		_ = a.S.UpdateConfig(func(cfg *ojson.Object) error { cfg.EnsureObj("settings").Set("autostart", in.Autostart); return nil })
	}
	errs := a.applyHotkeys()
	if in.Discord {
		a.discordIdle()
	} else {
		a.sys.mu.Lock()
		d := a.sys.discord
		a.sys.discord = nil
		a.sys.mu.Unlock()
		if d != nil {
			d.Close()
		}
	}
	out := a.systemSettings()
	out.HotkeyErrors = errs
	return out, nil
}

// IconPath writes the embedded icon for the tray once.
func IconPath(cacheDir string, ico []byte) string {
	p := filepath.Join(cacheDir, "tray.ico")
	if b, err := os.ReadFile(p); err == nil && len(b) == len(ico) {
		return p
	}
	_ = os.MkdirAll(cacheDir, 0o755)
	_ = os.WriteFile(p, ico, 0o644)
	return p
}
