package app

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/updater"
)

// UpdateRepo is where releases are published.
const UpdateRepo = "snakex21/Game-Launcher"

// Quitter is implemented by the window host.
type Quitter interface{ Quit() }

func (a *App) updateChecker() *updater.Checker {
	c := &updater.Checker{Repo: UpdateRepo}
	if a.updateBase != "" {
		c.Base = a.updateBase
	}
	return c
}

func (a *App) updateCheck(ctx context.Context, _ empty) (any, error) {
	cctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	u, err := a.updateChecker().Check(cctx, Version)
	if err != nil {
		return nil, err
	}
	if u == nil {
		return map[string]any{"current": Version, "available": false}, nil
	}
	return map[string]any{"current": Version, "available": true, "version": u.Version, "notes": u.Notes, "asset": u.Asset.Name}, nil
}

// updateInstall downloads, verifies (SHA-256), swaps the exe and restarts.
func (a *App) updateInstall(ctx context.Context, _ empty) (any, error) {
	exe, err := os.Executable()
	if err != nil {
		return nil, err
	}
	if exe, err = filepath.EvalSymlinks(exe); err != nil {
		return nil, err
	}
	cctx, cancel := context.WithTimeout(ctx, 10*time.Minute)
	defer cancel()
	c := a.updateChecker()
	u, err := c.Check(cctx, Version)
	if err != nil {
		return nil, err
	}
	if u == nil {
		return nil, bridge.Errf("Masz najnowszą wersję.")
	}
	nf, err := c.Download(cctx, u, exe)
	if err != nil {
		return nil, err
	}
	if err := updater.Swap(exe, nf, Version, u.Version); err != nil {
		os.Remove(nf)
		return nil, err
	}
	cmd := exec.Command(exe, "-post-update", "-app-dir", a.appDir())
	cmd.Dir = filepath.Dir(exe)
	if err := cmd.Start(); err != nil {
		_ = updater.Rollback(exe)
		return nil, bridge.Errf("Nowa wersja nie uruchomiła się (%v) – przywrócono poprzednią.", err)
	}
	if q, ok := a.host.(Quitter); ok {
		go func() { time.Sleep(300 * time.Millisecond); q.Quit() }()
	}
	return map[string]any{"version": u.Version}, nil
}
