package app

import (
	"context"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/cloud"
	"github.com/snakex21/game-launcher/go/internal/ojson"
)

// CloudPrefixes are backed up to GitHub. local_settings.json (secrets) and
// the chat database are never uploaded.
var CloudPrefixes = []string{
	"data/config/config.json",
	"data/config/achievements_def.json",
	"data/games_saves",
	"images",
	"custom_themes",
}

// DefaultCloudRepo is the repository name the Python version used.
const DefaultCloudRepo = "game_launcher_saves"

func (a *App) cloudRepoName() string {
	name := DefaultCloudRepo
	a.S.ReadLocal(func(l *ojson.Object) {
		if v := strings.TrimSpace(l.Str("github_backup_repo")); v != "" {
			name = v
		}
	})
	return name
}

func (a *App) cloudClient() *cloud.Client {
	c := cloud.New(a.S.Secret("github_token"))
	if a.cloudBase != "" {
		c.Base = a.cloudBase
	}
	return c
}

func (a *App) cloudBackup(ctx context.Context, in struct {
	Repo string `json:"repo"`
}) (any, error) {
	if in.Repo != "" {
		if err := a.S.UpdateLocal(func(l *ojson.Object) error { l.Set("github_backup_repo", strings.TrimSpace(in.Repo)); return nil }); err != nil {
			return nil, err
		}
	}
	cctx, cancel := context.WithTimeout(ctx, 20*time.Minute)
	defer cancel()
	c := a.cloudClient()
	repo, err := c.EnsureRepo(cctx, a.cloudRepoName())
	if err != nil {
		return nil, err
	}
	files, skipped, err := cloud.Collect(a.appDir(), CloudPrefixes)
	if err != nil {
		return nil, err
	}
	res, err := c.Backup(cctx, repo, files, CloudPrefixes, func(done, total int) {
		a.emit("cloud:progress", map[string]int{"done": done, "total": total})
	})
	if err != nil {
		return nil, err
	}
	res.Skipped = skipped
	_ = a.S.UpdateLocal(func(l *ojson.Object) error {
		l.Set("github_last_backup", a.now().Format("2006-01-02 15:04"))
		return nil
	})
	return res, nil
}

func (a *App) cloudRestore(ctx context.Context, _ empty) (any, error) {
	a.mu.Lock()
	running := len(a.sessions)
	a.mu.Unlock()
	if running > 0 {
		return nil, bridge.Errf("Zamknij gry przed przywracaniem kopii.")
	}
	cctx, cancel := context.WithTimeout(ctx, 20*time.Minute)
	defer cancel()
	c := a.cloudClient()
	repo, err := c.EnsureRepo(cctx, a.cloudRepoName())
	if err != nil {
		return nil, err
	}
	res, err := c.Restore(cctx, repo, a.appDir(), CloudPrefixes)
	if err != nil {
		return nil, err
	}
	if err := a.S.Load(); err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return res, nil
}
