package app

import (
	"context"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/backupzip"
	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/lastfm"
	"github.com/snakex21/game-launcher/go/internal/news"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/rawg"
	"github.com/snakex21/game-launcher/go/internal/saves"
)

// ------------------------------------------------------------------- news

type feedIn struct {
	Name   string `json:"name"`
	URL    string `json:"url"`
	Active bool   `json:"active"`
}

func (a *App) newsGet(ctx context.Context, _ empty) (any, error) {
	var feeds []news.Feed
	var all []feedIn
	limit := 10
	a.S.ReadConfig(func(cfg *ojson.Object) {
		st := cfg.Obj("settings")
		limit = int(st.Int("news_post_limit", 10))
		for _, f := range st.Arr("rss_feeds") {
			if o, ok := f.(*ojson.Object); ok {
				fi := feedIn{Name: strings.TrimSpace(o.Str("name")), URL: strings.TrimSpace(o.Str("url")), Active: o.Bool("active", true)}
				if fi.Name == "" {
					fi.Name = fi.URL
				}
				all = append(all, fi)
				if fi.Active {
					feeds = append(feeds, news.Feed{Name: fi.Name, URL: fi.URL})
				}
			}
		}
	})
	cctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	items, errs := news.Fetch(cctx, nil, feeds, limit)
	if items == nil {
		items = []news.Item{}
	}
	if all == nil {
		all = []feedIn{}
	}
	return map[string]any{"items": items, "errors": errs, "feeds": all, "limit": limit}, nil
}

func (a *App) newsSave(_ context.Context, in struct {
	Feeds []feedIn `json:"feeds"`
	Limit int      `json:"limit"`
}) (any, error) {
	if in.Limit < 1 || in.Limit > 200 {
		return nil, bridge.Errf("Limit wpisów: 1–200.")
	}
	var list []any
	for _, f := range in.Feeds {
		u := strings.TrimSpace(f.URL)
		if !strings.HasPrefix(u, "http://") && !strings.HasPrefix(u, "https://") {
			return nil, bridge.Errf("Adres kanału musi zaczynać się od http(s)://: %s", u)
		}
		o := ojson.NewObject()
		o.Set("url", u)
		o.Set("active", f.Active)
		name := strings.TrimSpace(f.Name)
		if name == "" {
			name = u
		}
		o.Set("name", name)
		list = append(list, o)
	}
	if list == nil {
		list = []any{}
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		st := cfg.EnsureObj("settings")
		st.Set("rss_feeds", list)
		st.Set("news_post_limit", in.Limit)
		return nil
	})
	return true, err
}

// ------------------------------------------------------------- duplicates

var nonAlnum = regexp.MustCompile(`[^a-z0-9]+`)

// Duplicates groups games whose names match after removing everything but
// letters and digits (case-insensitive).
func (a *App) Duplicates() [][]GameDTO {
	groups := map[string][]GameDTO{}
	for _, g := range a.Library() {
		k := nonAlnum.ReplaceAllString(strings.ToLower(g.Name), "")
		if k == "" {
			continue
		}
		groups[k] = append(groups[k], g)
	}
	out := [][]GameDTO{}
	for _, g := range groups {
		if len(g) > 1 {
			out = append(out, g)
		}
	}
	sort.Slice(out, func(i, j int) bool { return lower(out[i][0].Name) < lower(out[j][0].Name) })
	return out
}

// ----------------------------------------------------------------- themes

// ThemeKeys are the keys of a theme definition (Python format).
var ThemeKeys = []string{"background", "foreground", "button_background", "button_foreground", "entry_background",
	"tree_background", "tree_heading", "scrollbar_trough", "scrollbar_slider", "link_foreground", "chart_bar_color", "chart_axis_color"}

// BuiltinThemes match the Python THEMES (extended with the Go defaults).
var BuiltinThemes = map[string]map[string]string{
	"Dark": {"background": "#0f1116", "foreground": "#e7eaf3", "button_background": "#242a3d", "button_foreground": "#e7eaf3", "entry_background": "#161922",
		"tree_background": "#1c2030", "tree_heading": "#8d94aa", "link_foreground": "#7aa2ff", "chart_bar_color": "#5b8cff"},
	"Light": {"background": "#f4f5f8", "foreground": "#1b1e27", "button_background": "#e3e6ee", "button_foreground": "#1b1e27", "entry_background": "#ffffff",
		"tree_background": "#ffffff", "tree_heading": "#5d6475", "link_foreground": "#2f5fd0", "chart_bar_color": "#3b6cf0"},
	"Blue": {"background": "#141a2e", "foreground": "#e6ecff", "button_background": "#26305a", "button_foreground": "#e6ecff", "entry_background": "#1a2140",
		"tree_background": "#1d2547", "tree_heading": "#98a3cc", "link_foreground": "#8fb0ff", "chart_bar_color": "#6c8cff"},
}

var colorRe = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)

// ThemeView for the UI.
type ThemeView struct {
	Current string                       `json:"current"`
	Themes  map[string]map[string]string `json:"themes"`
	Custom  []string                     `json:"custom"`
	Keys    []string                     `json:"keys"`
}

func (a *App) themes() ThemeView {
	v := ThemeView{Themes: map[string]map[string]string{}, Keys: ThemeKeys, Custom: []string{}}
	for k, d := range BuiltinThemes {
		v.Themes[k] = d
	}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		st := cfg.Obj("settings")
		v.Current = st.Str("theme")
		ct := st.Obj("custom_themes")
		for _, name := range ct.Keys() {
			d := map[string]string{}
			o := ct.Obj(name)
			for _, k := range ThemeKeys {
				if c := o.Str(k); colorRe.MatchString(c) {
					d[k] = c
				}
			}
			v.Themes[name] = d
			v.Custom = append(v.Custom, name)
		}
	})
	if _, ok := v.Themes[v.Current]; !ok {
		// Python stored "dark"/"Dark"
		for k := range BuiltinThemes {
			if strings.EqualFold(k, v.Current) {
				v.Current = k
			}
		}
		if _, ok := v.Themes[v.Current]; !ok {
			v.Current = "Dark"
		}
	}
	return v
}

func (a *App) themeSave(_ context.Context, in struct {
	Name  string            `json:"name"`
	Def   map[string]string `json:"def"`
	Apply bool              `json:"apply"`
}) (any, error) {
	name := strings.TrimSpace(in.Name)
	if name == "" || len(name) > 60 {
		return nil, bridge.Errf("Podaj nazwę motywu.")
	}
	if _, builtin := BuiltinThemes[name]; builtin {
		return nil, bridge.Errf("Nie można nadpisać motywu wbudowanego – użyj innej nazwy.")
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		st := cfg.EnsureObj("settings")
		o := ojson.NewObject()
		for _, k := range ThemeKeys {
			if c := in.Def[k]; c != "" {
				if !colorRe.MatchString(c) {
					return bridge.Errf("Kolor %s: %q nie jest kolorem #RRGGBB.", k, c)
				}
				o.Set(k, c)
			}
		}
		st.EnsureObj("custom_themes").Set(name, o)
		if in.Apply {
			st.Set("theme", name)
			u := cfg.EnsureObj("user")
			u.Set("theme_change_count", u.Int("theme_change_count", 0)+1)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("theme", a.themes())
	return a.themes(), nil
}

func (a *App) themeApply(_ context.Context, in nameIn) (any, error) {
	if _, ok := a.themes().Themes[in.Name]; !ok {
		return nil, bridge.Errf("Nie ma motywu „%s”.", in.Name)
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		cfg.EnsureObj("settings").Set("theme", in.Name)
		u := cfg.EnsureObj("user")
		u.Set("theme_change_count", u.Int("theme_change_count", 0)+1)
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.evaluateAchievements()
	return a.themes(), nil
}

func (a *App) themeDelete(_ context.Context, in nameIn) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		st := cfg.EnsureObj("settings")
		st.EnsureObj("custom_themes").Delete(in.Name)
		if st.Str("theme") == in.Name {
			st.Set("theme", "Dark")
		}
		return nil
	})
	return a.themes(), err
}

// --------------------------------------------------- achievement editor

// RuleTypes for the definition editor (same as Python).
var RuleTypes = []string{"games_launched_count", "library_size", "total_playtime_hours", "games_completed_100",
	"playtime_single_game_hours", "genre_played_count", "tag_played_count", "group_played_count",
	"genre_completed_100", "tag_completed_100", "group_completed_100", "roadmap_completed_count",
	"games_rated_count", "groups_created", "games_with_tags", "mods_installed", "roadmap_items_added",
	"themes_changed", "game_launched_at_night", "consecutive_days_used"}

func (a *App) achDefs(_ context.Context, _ empty) (any, error) {
	defs := []map[string]any{}
	for _, d := range a.loadAchievementDefs() {
		m := map[string]any{}
		for _, k := range d.Keys() {
			m[k] = ojson.ToPlain(d.Get(k))
		}
		defs = append(defs, m)
	}
	return map[string]any{"defs": defs, "ruleTypes": RuleTypes}, nil
}

func (a *App) achDefSave(_ context.Context, in struct {
	Old string         `json:"old"`
	Def map[string]any `json:"def"`
}) (any, error) {
	id, _ := in.Def["id"].(string)
	id = strings.TrimSpace(id)
	if id == "" || len(id) > 60 {
		return nil, bridge.Errf("Podaj identyfikator osiągnięcia.")
	}
	rt, _ := in.Def["rule_type"].(string)
	known := false
	for _, r := range RuleTypes {
		known = known || r == rt
	}
	if !known {
		return nil, bridge.Errf("Nieznany typ warunku.")
	}
	if _, ok := in.Def["target_value"].(float64); !ok {
		return nil, bridge.Errf("Wartość docelowa musi być liczbą.")
	}
	defs := a.loadAchievementDefs()
	raw, _ := os.ReadFile(a.S.L.AchievDefFile)
	style := ojson.DetectStyle(raw)
	var out []any
	replaced := false
	for _, d := range defs {
		if d.Str("id") == id && id != in.Old {
			return nil, bridge.Errf("Osiągnięcie „%s” już istnieje.", id)
		}
		if d.Str("id") == in.Old && in.Old != "" {
			d = mergeDef(d, in.Def, id)
			replaced = true
		}
		out = append(out, d)
	}
	if !replaced {
		out = append(out, mergeDef(ojson.NewObject(), in.Def, id))
	}
	if err := writeJSONFile(a.S.L.AchievDefFile, out, style); err != nil {
		return nil, err
	}
	return a.achDefs(context.Background(), empty{})
}

func mergeDef(d *ojson.Object, in map[string]any, id string) *ojson.Object {
	d.Set("id", id)
	for _, k := range []string{"name", "description", "icon", "rule_type", "genre", "tag", "group"} {
		if v, ok := in[k].(string); ok {
			if v == "" && (k == "genre" || k == "tag" || k == "group") {
				d.Delete(k)
				continue
			}
			d.Set(k, v)
		}
	}
	if f, ok := in["target_value"].(float64); ok {
		if f == float64(int64(f)) {
			d.Set("target_value", int64(f))
		} else {
			d.Set("target_value", ojson.Float(f))
		}
	}
	if h, ok := in["hidden"].(bool); ok {
		d.Set("hidden", h)
	}
	return d
}

func (a *App) achDefDelete(_ context.Context, in struct {
	ID string `json:"id"`
}) (any, error) {
	raw, _ := os.ReadFile(a.S.L.AchievDefFile)
	var out []any
	for _, d := range a.loadAchievementDefs() {
		if d.Str("id") != in.ID {
			out = append(out, d)
		}
	}
	if out == nil {
		out = []any{}
	}
	if err := writeJSONFile(a.S.L.AchievDefFile, out, ojson.DetectStyle(raw)); err != nil {
		return nil, err
	}
	return a.achDefs(context.Background(), empty{})
}

func writeJSONFile(path string, v any, style ojson.Style) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	if b, err := os.ReadFile(path); err == nil {
		_ = os.WriteFile(path+".bak", b, 0o600)
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, style.Apply(ojson.MarshalPython(v)), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// --------------------------------------------------- full backup (zip)

func (a *App) backupCreate(_ context.Context, _ empty) (any, error) {
	dir, ok, err := a.dlg.PickFolder(a.hwnd(), "Gdzie zapisać kopię launchera?")
	if err != nil || !ok {
		return nil, err
	}
	name := "GameLauncher_Backup_" + a.now().Format("20060102_150405") + ".zip"
	n, err := backupzip.Create(a.appDir(), filepath.Join(dir, name), Version)
	if err != nil {
		return nil, err
	}
	return map[string]any{"path": filepath.Join(dir, name), "files": n}, nil
}

func (a *App) backupRestore(_ context.Context, _ empty) (any, error) {
	a.mu.Lock()
	running := len(a.sessions)
	a.mu.Unlock()
	if running > 0 {
		return nil, bridge.Errf("Zamknij gry przed przywracaniem kopii.")
	}
	p, ok, err := a.dlg.OpenFile(a.hwnd(), "Wybierz kopię launchera (.zip)", "Kopie", "*.zip")
	if err != nil || !ok {
		return nil, err
	}
	a.stopChat() // chat.db may be replaced
	n, err := backupzip.Restore(a.appDir(), p)
	if err != nil {
		return nil, err
	}
	if err := a.S.Load(); err != nil {
		return nil, err
	}
	a.startChatHost()
	a.emit("library:changed", nil)
	return map[string]any{"files": n}, nil
}

// ------------------------------------------------------------ screenshots

var imageExt = map[string]bool{".png": true, ".jpg": true, ".jpeg": true, ".webp": true, ".gif": true, ".bmp": true}

// scanScreenshots finds files matching settings.screenshot_filename_patterns
// ("{game_name}*.png") in settings.autoscan_screenshot_folders.
func (a *App) scanScreenshots(_ context.Context, _ empty) (any, error) {
	var folders, patterns, ignore []string
	recursive := true
	var names []string
	a.S.ReadConfig(func(cfg *ojson.Object) {
		st := cfg.Obj("settings")
		folders = st.Strings("autoscan_screenshot_folders")
		patterns = st.Strings("screenshot_filename_patterns")
		ignore = st.Strings("screenshot_scan_ignore_folders")
		recursive = st.Bool("screenshot_scan_recursive", true)
		names = cfg.Obj("games").Keys()
	})
	if len(folders) == 0 {
		return nil, bridge.Errf("Dodaj foldery screenshotów w Ustawieniach.")
	}
	ign := map[string]bool{}
	for _, i := range ignore {
		ign[lower(i)] = true
	}
	var files []string
	for _, f := range folders {
		root := paths.Resolve(f, a.appDir())
		depth0 := strings.Count(filepath.Clean(root), string(filepath.Separator))
		_ = filepath.WalkDir(root, func(p string, d os.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if d.IsDir() {
				if p != root && (ign[lower(d.Name())] || !recursive || strings.Count(p, string(filepath.Separator))-depth0 > 6) {
					return filepath.SkipDir
				}
				return nil
			}
			if imageExt[lower(filepath.Ext(p))] && len(files) < 200000 {
				files = append(files, p)
			}
			return nil
		})
	}
	found := map[string][]any{}
	for _, name := range names {
		for _, pat := range patterns {
			glob := lower(strings.ReplaceAll(pat, "{game_name}", name))
			for _, f := range files {
				if ok, _ := filepath.Match(glob, lower(filepath.Base(f))); ok {
					found[name] = append(found[name], f)
				}
			}
		}
	}
	total := 0
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.Obj("games")
		for _, name := range names {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			list := found[name]
			if list == nil {
				list = []any{}
			}
			total += len(list)
			g.Set("autoscan_screenshots", list)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return map[string]any{"found": total, "games": len(found)}, nil
}

func (a *App) screenshotAdd(_ context.Context, in nameIn) (any, error) {
	p, ok, err := a.dlg.OpenFile(a.hwnd(), "Dodaj screenshot", "Obrazy", "*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp")
	if err != nil || !ok {
		return nil, err
	}
	dir := filepath.Join(a.S.L.ImagesDir, "screenshots", rawg.SafeName(in.Name))
	dst := filepath.Join(dir, filepath.Base(p))
	if _, err := saves.CopyTree(p, dst); err != nil {
		return nil, err
	}
	stored := `images\screenshots\` + rawg.SafeName(in.Name) + `\` + filepath.Base(p)
	err = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		g.Set("screenshots", append(g.Arr("screenshots"), stored))
		return nil
	})
	return true, err
}

func (a *App) screenshotRemove(_ context.Context, in struct {
	Name  string `json:"name"`
	Index int    `json:"index"`
}) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry.")
		}
		list := a.screenshotList(g)
		if in.Index < 0 || in.Index >= len(list) {
			return bridge.Errf("Nie ma takiego screenshotu.")
		}
		target := list[in.Index]
		for _, key := range []string{"screenshots", "autoscan_screenshots"} {
			var keep []any
			for _, v := range g.Arr(key) {
				if s, ok := v.(string); ok && strings.EqualFold(s, target) {
					continue
				}
				keep = append(keep, v)
			}
			if keep == nil {
				keep = []any{}
			}
			g.Set(key, keep)
		}
		return nil
	})
	return true, err
}

// --------------------------------------------------------- Last.fm covers

func (a *App) musicCover(ctx context.Context, in struct {
	ID string `json:"id"`
}) (any, error) {
	path := a.TrackFile(in.ID)
	if path == "" {
		return nil, bridge.Errf("Nie ma takiego utworu.")
	}
	c := &lastfm.Client{Key: a.S.Secret("lastfm_api_key")}
	tags := lastfm.ReadTags(path)
	cctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	u, err := c.CoverURL(cctx, tags)
	if err != nil {
		return nil, err
	}
	dir := filepath.Join(a.S.L.ImagesDir, "music_covers", "lastfm")
	file, err := c.Download(cctx, u, dir, tags)
	if err != nil {
		return nil, err
	}
	stored := `images\music_covers\lastfm\` + file
	err = a.S.UpdateLocal(func(l *ojson.Object) error {
		l.EnsureObj("music_track_covers").Set(a.trackKey(path), stored)
		return nil
	})
	return map[string]string{"cover": stored}, err
}

// trackKey is the key of music_track_covers: the path as stored in the
// playlist (Python used the playlist string itself).
func (a *App) trackKey(abs string) string {
	a.mu.Lock()
	defer a.mu.Unlock()
	if k, ok := a.trackOrig[abs]; ok {
		return k
	}
	return abs
}

// TrackCoverFile implements webui.Media (cover of a track id).
func (a *App) TrackCoverFile(id string, w int) string {
	path := a.TrackFile(id)
	if path == "" {
		return ""
	}
	key := a.trackKey(path)
	var stored string
	a.S.ReadLocal(func(l *ojson.Object) { stored = l.Obj("music_track_covers").Str(key) })
	src := a.resolveAsset(stored)
	if src == "" {
		return ""
	}
	if t, err := a.thumbs.Get(src, w); err == nil {
		return t
	}
	return src
}
