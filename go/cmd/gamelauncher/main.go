// Command gamelauncher is the Go + WebView2 Game Launcher. It reads the data
// of the Python launcher (data/config/config.json, local_settings.json,
// data/games_saves, images/) from the folder of the exe, so it can replace
// game_launcher.py in the same portable folder.
package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	rdebug "runtime/debug"
	"sync/atomic"
	"time"
	"unsafe"

	webview "github.com/webview/webview_go"

	"github.com/snakex21/game-launcher/go/internal/app"
	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/store"
	"github.com/snakex21/game-launcher/go/internal/webui"
	"github.com/snakex21/game-launcher/go/internal/winapi"
)

// version is set at build time (-X main.version=...).
var version = "dev"

const preferredPort = 47831

//go:embed icon.ico
var appIcon []byte

type windowHost struct {
	w      webview.WebView
	closed atomic.Bool
}

func (h *windowHost) dispatchEval(script string) {
	if h.closed.Load() {
		return
	}
	h.w.Dispatch(func() {
		if !h.closed.Load() {
			h.w.Eval(script)
		}
	})
}

func (h *windowHost) Emit(event string, payload any) {
	h.dispatchEval(bridge.EmitScript(event, payload))
}
func (h *windowHost) settle(id int64, ok bool, payload any) {
	h.dispatchEval(bridge.SettleScript(id, ok, payload))
}
func (h *windowHost) HWND() uintptr { return uintptr(h.w.Window()) }

type dialogs struct{}

func (dialogs) OpenFile(hwnd uintptr, title, filterName, patterns string) (string, bool, error) {
	return winapi.OpenFile(hwnd, title, filterName, patterns)
}
func (dialogs) PickFolder(hwnd uintptr, title string) (string, bool, error) {
	return winapi.PickFolder(hwnd, title)
}
func (dialogs) ShellOpen(target string) error { return winapi.ShellOpen(target) }

func main() { os.Exit(run()) }

func run() int {
	debug := flag.Bool("debug", false, "enable WebView2 devtools")
	appDirFlag := flag.String("app-dir", "", "launcher folder with data/ (default: folder of the exe)")
	flag.Parse()
	if *appDirFlag != "" {
		_ = os.Setenv("GL_APP_DIR", *appDirFlag)
	}
	app.Version = version
	procStart := processStart()

	appDir := paths.AppDir()
	logDir := filepath.Join(appDir, "data", "logs")
	_ = os.MkdirAll(logDir, 0o755)
	if f, err := os.OpenFile(filepath.Join(logDir, "go_launcher.log"), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644); err == nil {
		log.SetOutput(io.MultiWriter(f, os.Stderr))
		defer f.Close()
		_ = rdebug.SetCrashOutput(f, rdebug.CrashOptions{})
	}
	log.Printf("Game Launcher (Go/WebView2) %s, app=%s", version, appDir)

	// Portable WebView2 profile next to the data (the patched webview_go
	// reads this instead of %APPDATA%\<exe>), so it travels with the drive.
	if os.Getenv("WEBVIEW_GO_USER_DATA_FOLDER") == "" {
		_ = os.Setenv("WEBVIEW_GO_USER_DATA_FOLDER", filepath.Join(appDir, "data", "webview2"))
	}

	st, err := store.Open(appDir)
	if err != nil {
		fatal("Nie można wczytać danych launchera:\n" + err.Error())
		return 1
	}
	host := &windowHost{}
	a := app.New(st, host, dialogs{})
	boot, _ := json.Marshal(a.Boot())
	tBoot := time.Since(procStart)

	server, err := webui.Start(preferredPort, a)
	if err != nil {
		fatal("Nie można uruchomić serwera interfejsu:\n" + err.Error())
		return 1
	}
	defer server.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	w := webview.New(*debug)
	if w == nil {
		fatal("Wymagany jest Microsoft Edge WebView2 Runtime.\nPobierz: https://developer.microsoft.com/microsoft-edge/webview2/")
		return 1
	}
	host.w = w
	w.SetTitle("Game Launcher")
	w.SetSize(1360, 860, webview.HintNone)
	w.SetSize(900, 600, webview.HintMin)
	setWindowIcon(unsafe.Pointer(w.Window()), appIcon)
	tWindow := time.Since(procStart)

	d := bridge.New(ctx, server.Token)
	a.Register(d)
	var painted atomic.Bool
	d.Handle("app.painted", func(_ context.Context, p json.RawMessage) (any, error) {
		if painted.Swap(true) {
			return nil, nil
		}
		var in struct {
			Games int     `json:"games"`
			JSMs  float64 `json:"jsMs"`
		}
		_ = json.Unmarshal(p, &in)
		total := time.Since(procStart)
		log.Printf("[perf] boot data %v, window %v, first paint %v (%d games)", tBoot.Round(time.Millisecond), tWindow.Round(time.Millisecond), total.Round(time.Millisecond), in.Games)
		if out := os.Getenv("GL_PERF_OUT"); out != "" {
			b, _ := json.Marshal(map[string]any{"boot_ms": tBoot.Milliseconds(), "window_ms": tWindow.Milliseconds(), "first_paint_ms": total.Milliseconds(), "games": in.Games, "pid": os.Getpid()})
			_ = os.WriteFile(out, b, 0o644)
		}
		return nil, nil
	})
	if err := w.Bind("__gl_invoke", func(token string, id float64, channel, payload string) error {
		return d.Invoke(token, id, channel, payload, host.settle)
	}); err != nil {
		fatal("Nie można połączyć interfejsu: " + err.Error())
		return 1
	}
	w.Init(bridge.InitScript(server.Origin, server.Token, boot))
	w.Navigate(server.URL)
	a.Start(ctx)

	w.Run()

	host.closed.Store(true)
	cancel()
	a.Shutdown()
	waitTimeout(d.Wait, 3*time.Second)
	w.Destroy()
	log.Printf("Game Launcher exited")
	return 0
}

func waitTimeout(fn func(), dur time.Duration) {
	done := make(chan struct{})
	go func() { fn(); close(done) }()
	select {
	case <-done:
	case <-time.After(dur):
	}
}

func fatal(msg string) {
	log.Print(msg)
	winapi.MessageBox(0, "Game Launcher", msg, winapi.MBOK|winapi.MBIconError)
	fmt.Fprintln(os.Stderr, msg)
}
