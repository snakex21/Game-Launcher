package app

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/chatdb"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/scan"
)

// ---------------------------------------------------------------- settings

// SettingsDTO never carries secret values, only whether they are set.
type SettingsDTO struct {
	Username        string            `json:"username"`
	ScanFolders     []string          `json:"scanFolders"`
	ScanRecursive   bool              `json:"scanRecursive"`
	ScanIgnore      []string          `json:"scanIgnore"`
	AutoBackup      bool              `json:"autoBackupOnExit"`
	View            string            `json:"view"`
	TilesPerRow     int64             `json:"tilesPerRow"`
	Emulators       map[string]string `json:"emulators"`
	CustomGenres    []string          `json:"customGenres"`
	Secrets         map[string]string `json:"secrets"` // key -> "" | "plik" | "zmienna"
	Remote          RemoteStatus      `json:"remote"`
	AppDir          string            `json:"appDir"`
	LauncherDrive   string            `json:"launcherDrive"`
	WebView2Profile string            `json:"webview2Profile"`
	Version         string            `json:"version"`
	TotalUsage      float64           `json:"totalUsage"`
	ConsecutiveDays int64             `json:"consecutiveDays"`
}

// Settings returns the settings view.
func (a *App) Settings() SettingsDTO {
	d := SettingsDTO{Emulators: map[string]string{}, Secrets: map[string]string{}, AppDir: a.appDir(), Version: Version,
		WebView2Profile: os.Getenv("WEBVIEW_GO_USER_DATA_FOLDER")}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		st := cfg.Obj("settings")
		d.Username = cfg.Obj("user").Str("username")
		d.ScanFolders = st.Strings("scan_folders")
		d.ScanRecursive = st.Bool("scan_recursively", true)
		d.ScanIgnore = st.Strings("scan_ignore_folders")
		d.AutoBackup = st.Bool("auto_backup_on_exit", true)
		d.CustomGenres = st.Strings("custom_genres")
		d.LauncherDrive = st.Str("launcher_drive")
		if e := cfg.Obj("emulators"); e != nil {
			for _, k := range e.Keys() {
				d.Emulators[k] = e.Obj(k).Str("path")
			}
		}
	})
	a.S.ReadLocal(func(l *ojson.Object) {
		d.View = l.Str("library_view_mode")
		d.TilesPerRow = l.Int("tiles_per_row", 5)
		d.TotalUsage = l.Float("total_launcher_usage_seconds", 0)
		d.ConsecutiveDays = l.Int("consecutive_days", 0)
	})
	for _, k := range []string{"rawg_api_key", "lastfm_api_key", "github_token"} {
		switch {
		case a.S.SecretFromEnv(k):
			d.Secrets[k] = "zmienna"
		case a.S.Secret(k) != "":
			d.Secrets[k] = "plik"
		default:
			d.Secrets[k] = ""
		}
	}
	d.Remote = a.remoteStatus()
	return d
}

type settingsIn struct {
	Username      *string   `json:"username"`
	ScanFolders   *[]string `json:"scanFolders"`
	ScanRecursive *bool     `json:"scanRecursive"`
	ScanIgnore    *[]string `json:"scanIgnore"`
	AutoBackup    *bool     `json:"autoBackupOnExit"`
	View          *string   `json:"view"`
	TilesPerRow   *int64    `json:"tilesPerRow"`
}

func (a *App) settingsSave(_ context.Context, in settingsIn) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		st := cfg.EnsureObj("settings")
		if in.Username != nil {
			u := strings.TrimSpace(*in.Username)
			if u == "" || len(u) > 60 {
				return bridge.Errf("Nazwa użytkownika: 1–60 znaków.")
			}
			cfg.EnsureObj("user").Set("username", u)
		}
		if in.ScanFolders != nil {
			st.Set("scan_folders", cleanList(*in.ScanFolders))
		}
		if in.ScanRecursive != nil {
			st.Set("scan_recursively", *in.ScanRecursive)
		}
		if in.ScanIgnore != nil {
			st.Set("scan_ignore_folders", cleanList(*in.ScanIgnore))
		}
		if in.AutoBackup != nil {
			st.Set("auto_backup_on_exit", *in.AutoBackup)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	if in.View != nil || in.TilesPerRow != nil {
		err = a.S.UpdateLocal(func(l *ojson.Object) error {
			if in.View != nil && (*in.View == "tiles" || *in.View == "list") {
				l.Set("library_view_mode", *in.View)
			}
			if in.TilesPerRow != nil && *in.TilesPerRow >= 2 && *in.TilesPerRow <= 12 {
				l.Set("tiles_per_row", *in.TilesPerRow)
			}
			return nil
		})
	}
	return a.Settings(), err
}

// settingsSetSecret stores an API key; the value is never sent back.
func (a *App) settingsSetSecret(_ context.Context, in struct {
	Key   string `json:"key"`
	Value string `json:"value"`
}) (any, error) {
	switch in.Key {
	case "rawg_api_key", "lastfm_api_key", "github_token":
	default:
		return nil, bridge.Errf("Nieznany klucz.")
	}
	if a.S.SecretFromEnv(in.Key) {
		return nil, bridge.Errf("Ten klucz jest ustawiony zmienną środowiskową – zmień go tam.")
	}
	v := strings.TrimSpace(in.Value)
	if len(v) > 200 || strings.ContainsAny(v, "\r\n\t ") {
		return nil, bridge.Errf("Nieprawidłowy klucz.")
	}
	err := a.S.UpdateLocal(func(l *ojson.Object) error { l.Set(in.Key, v); return nil })
	return a.Settings(), err
}

func (a *App) emulatorSave(_ context.Context, in struct {
	Old  string `json:"old"`
	Name string `json:"name"`
	Path string `json:"path"`
}) (any, error) {
	name := strings.TrimSpace(in.Name)
	if name == "" {
		return nil, bridge.Errf("Podaj nazwę emulatora.")
	}
	if !fileExists(in.Path) {
		return nil, bridge.Errf("Plik emulatora nie istnieje:\n%s", in.Path)
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		emus := cfg.EnsureObj("emulators")
		if in.Old != "" && in.Old != name {
			if emus.Has(name) {
				return bridge.Errf("Emulator „%s” już istnieje.", name)
			}
			if err := emus.Rename(in.Old, name); err != nil {
				return err
			}
			games := cfg.Obj("games")
			for _, gn := range games.Keys() {
				if g := games.Obj(gn); g != nil && g.Str("emulator_name") == in.Old {
					g.Set("emulator_name", name)
				}
			}
		} else if in.Old == "" && emus.Has(name) {
			return bridge.Errf("Emulator „%s” już istnieje.", name)
		}
		emus.EnsureObj(name).Set("path", paths.NormPath(in.Path))
		return nil
	})
	if err != nil {
		return nil, err
	}
	return a.Settings(), nil
}

func (a *App) emulatorDelete(_ context.Context, in nameIn) (any, error) {
	var used []string
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.Obj("games")
		for _, gn := range games.Keys() {
			if g := games.Obj(gn); g != nil && g.Str("emulator_name") == in.Name {
				used = append(used, gn)
			}
		}
		if len(used) > 0 {
			return bridge.Errf("Emulator jest używany przez: %s", strings.Join(used, ", "))
		}
		cfg.EnsureObj("emulators").Delete(in.Name)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return a.Settings(), nil
}

// -------------------------------------------------------------------- scan

func (a *App) scanStop() {
	a.scanMu.Lock()
	if a.scanCancel != nil {
		a.scanCancel()
		a.scanCancel = nil
	}
	a.scanMu.Unlock()
}

func (a *App) scanRun(ctx context.Context, _ empty) (any, error) {
	var opt scan.Options
	opt.KnownNames = map[string]bool{}
	known := map[string]bool{} // exe paths already in the library
	a.S.ReadConfig(func(cfg *ojson.Object) {
		st := cfg.Obj("settings")
		opt.Folders = st.Strings("scan_folders")
		opt.Recursive = st.Bool("scan_recursively", true)
		opt.Ignored = st.Strings("scan_ignore_folders")
		games := cfg.Obj("games")
		for _, n := range games.Keys() {
			opt.KnownNames[lower(n)] = true
			if g := games.Obj(n); g != nil && g.Str("exe_path") != "" {
				known[lower(paths.NormPath(g.Str("exe_path")))] = true
			}
		}
	})
	if len(opt.Folders) == 0 {
		return nil, bridge.Errf("Dodaj foldery do skanowania w Ustawieniach → Skanowanie.")
	}
	sctx, cancel := context.WithCancel(ctx)
	a.scanMu.Lock()
	if a.scanCancel != nil {
		a.scanMu.Unlock()
		cancel()
		return nil, bridge.Errf("Skanowanie już trwa.")
	}
	a.scanCancel = cancel
	a.scanMu.Unlock()
	defer a.scanStop()
	opt.Progress = func(done, _ int, cur string) { a.emit("scan:progress", map[string]any{"done": done, "current": cur}) }
	res, err := scan.Run(sctx, opt)
	if err != nil && sctx.Err() != nil {
		return nil, bridge.Errf("Skanowanie przerwane.")
	}
	out := []scan.Candidate{}
	for _, c := range res {
		if !known[lower(paths.NormPath(c.Exe))] {
			out = append(out, c)
		}
	}
	return out, nil
}

func (a *App) scanImport(_ context.Context, in struct {
	Games []scan.Candidate `json:"games"`
}) (any, error) {
	added := 0
	var skipped []string
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.EnsureObj("games")
		for _, c := range in.Games {
			name := strings.TrimSpace(c.Name)
			if validName(name) != nil || games.Has(name) || hasFold(games.Keys(), name) || !fileExists(c.Exe) {
				skipped = append(skipped, name)
				continue
			}
			g := ojson.NewObject()
			g.Set("name", name)
			g.Set("exe_path", paths.NormPath(c.Exe))
			g.Set("folder_path", paths.NormPath(c.Folder))
			g.Set("save_path", "")
			g.Set("cover_image", "")
			g.Set("genres", []any{})
			g.Set("rating", nil)
			g.Set("version", "")
			g.Set("tags", []any{})
			g.Set("notes", "")
			g.Set("date_added", ojson.Float(float64(a.now().UnixNano())/1e9))
			g.Set("play_time", 0)
			g.Set("completion", 0)
			g.Set("last_played", nil)
			g.Set("play_sessions", []any{})
			p := ojson.NewObject()
			p.Set("name", "Default")
			p.Set("exe_path", nil)
			p.Set("arguments", "")
			g.Set("launch_profiles", []any{p})
			g.Set("screenshots", []any{})
			g.Set("autoscan_screenshots", []any{})
			g.Set("checklist", []any{})
			games.Set(name, g)
			added++
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	go a.emit("library:files", a.CheckFiles())
	return map[string]any{"added": added, "skipped": skipped}, nil
}

// ------------------------------------------------------------------- stats

// Stats for the statistics page.
type Stats struct {
	Total      float64            `json:"total"`
	PC         float64            `json:"pc"`
	Emulators  map[string]float64 `json:"emulators"`
	Games      int                `json:"games"`
	Played     int                `json:"played"`
	Completed  int                `json:"completed"`
	Top        []TopGame          `json:"top"`
	Days       []DayStat          `json:"days"`
	RangeTotal float64            `json:"rangeTotal"`
	RangeGames []TopGame          `json:"rangeGames"`
	Genres     map[string]float64 `json:"genres"`
	Launcher   float64            `json:"launcherUsage"`
	From       string             `json:"from"`
	To         string             `json:"to"`
}

// TopGame is a game with a time.
type TopGame struct {
	Name    string  `json:"name"`
	Seconds float64 `json:"seconds"`
	Count   int64   `json:"count"`
}

// DayStat is time per day.
type DayStat struct {
	Day     string  `json:"day"`
	Seconds float64 `json:"seconds"`
}

func (a *App) statsGet(_ context.Context, in struct {
	From string `json:"from"`
	To   string `json:"to"`
}) (any, error) {
	return a.ComputeStats(in.From, in.To, time.Local)
}

// ComputeStats aggregates play time; sessions are split across midnight so a
// custom range [from, to] (inclusive days) is exact.
func (a *App) ComputeStats(from, to string, loc *time.Location) (*Stats, error) {
	now := a.now().In(loc)
	if to == "" {
		to = now.Format("2006-01-02")
	}
	if from == "" {
		from = now.AddDate(0, 0, -29).Format("2006-01-02")
	}
	f, err1 := time.ParseInLocation("2006-01-02", from, loc)
	t, err2 := time.ParseInLocation("2006-01-02", to, loc)
	if err1 != nil || err2 != nil {
		return nil, bridge.Errf("Daty muszą mieć format RRRR-MM-DD.")
	}
	if t.Before(f) {
		return nil, bridge.Errf("Data końcowa jest wcześniejsza niż początkowa.")
	}
	if t.Sub(f) > 3660*24*time.Hour {
		return nil, bridge.Errf("Zakres może mieć najwyżej 10 lat.")
	}
	end := t.AddDate(0, 0, 1)
	st := &Stats{Emulators: map[string]float64{}, Genres: map[string]float64{}, From: from, To: to}
	perDay := map[string]float64{}
	perGameRange := map[string]float64{}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		games := cfg.Obj("games")
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			pt := g.Float("play_time", 0)
			st.Games++
			st.Total += pt
			if g.Str("game_type") == "emulator" {
				st.Emulators[g.Str("emulator_name")] += pt
			} else {
				st.PC += pt
			}
			if g.Int("play_count", 0) > 0 || pt > 0 {
				st.Played++
			}
			if g.Float("completion", 0) >= 100 {
				st.Completed++
			}
			st.Top = append(st.Top, TopGame{Name: name, Seconds: pt, Count: g.Int("play_count", 0)})
			for _, gen := range g.Strings("genres") {
				st.Genres[gen] += pt
			}
			for _, s := range g.Arr("play_sessions") {
				so, ok := s.(*ojson.Object)
				if !ok {
					continue
				}
				ss, se := so.Float("start", 0), so.Float("end", 0)
				if se <= ss || ss <= 0 {
					continue
				}
				sStart := time.Unix(0, int64(ss*1e9)).In(loc)
				sEnd := time.Unix(0, int64(se*1e9)).In(loc)
				if sEnd.Before(f) || !sStart.Before(end) {
					continue
				}
				if sStart.Before(f) {
					sStart = f
				}
				if sEnd.After(end) {
					sEnd = end
				}
				for cur := sStart; cur.Before(sEnd); {
					dayEnd := time.Date(cur.Year(), cur.Month(), cur.Day()+1, 0, 0, 0, 0, loc)
					if dayEnd.After(sEnd) {
						dayEnd = sEnd
					}
					sec := dayEnd.Sub(cur).Seconds()
					perDay[cur.Format("2006-01-02")] += sec
					perGameRange[name] += sec
					cur = dayEnd
				}
			}
		}
	})
	sort.SliceStable(st.Top, func(i, j int) bool { return st.Top[i].Seconds > st.Top[j].Seconds })
	if len(st.Top) > 10 {
		st.Top = st.Top[:10]
	}
	for d := f; d.Before(end); d = d.AddDate(0, 0, 1) {
		k := d.Format("2006-01-02")
		st.Days = append(st.Days, DayStat{Day: k, Seconds: perDay[k]})
		st.RangeTotal += perDay[k]
	}
	for n, s := range perGameRange {
		st.RangeGames = append(st.RangeGames, TopGame{Name: n, Seconds: s})
	}
	sort.SliceStable(st.RangeGames, func(i, j int) bool { return st.RangeGames[i].Seconds > st.RangeGames[j].Seconds })
	a.S.ReadLocal(func(l *ojson.Object) { st.Launcher = l.Float("total_launcher_usage_seconds", 0) })
	return st, nil
}

// --------------------------------------------------------- roadmap/remind

const (
	statusPlanned = "Planowana"
	statusDone    = "Ukończona"
	statusLate    = "Nie ukończona na czas"
)

func (a *App) roadmapAdd(_ context.Context, in struct {
	Game  string `json:"game"`
	Start string `json:"start"`
	End   string `json:"end"`
}) (any, error) {
	s, e1 := time.Parse("2006-01-02", in.Start)
	e, e2 := time.Parse("2006-01-02", in.End)
	if e1 != nil || e2 != nil {
		return nil, bridge.Errf("Daty muszą mieć format RRRR-MM-DD.")
	}
	if e.Before(s) {
		return nil, bridge.Errf("Data zakończenia nie może być wcześniejsza niż rozpoczęcia.")
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		if !cfg.Obj("games").Has(in.Game) {
			return bridge.Errf("Wybierz grę z biblioteki.")
		}
		for _, it := range cfg.Arr("roadmap") {
			if o, ok := it.(*ojson.Object); ok && o.Str("game_name") == in.Game {
				return bridge.Errf("„%s” jest już w roadmapie.", in.Game)
			}
		}
		o := ojson.NewObject()
		o.Set("game_name", in.Game)
		o.Set("start_date", in.Start)
		o.Set("end_date", in.End)
		o.Set("time_spent", ojson.Float(0))
		o.Set("status", statusPlanned)
		cfg.Set("roadmap", append(cfg.Arr("roadmap"), o))
		return nil
	})
	return a.roadmapView(), err
}

func (a *App) roadmapEdit(game string, fn func(cfg *ojson.Object, idx int, o *ojson.Object) error) error {
	return a.S.UpdateConfig(func(cfg *ojson.Object) error {
		for i, it := range cfg.Arr("roadmap") {
			if o, ok := it.(*ojson.Object); ok && o.Str("game_name") == game {
				return fn(cfg, i, o)
			}
		}
		return bridge.Errf("Brak „%s” w roadmapie.", game)
	})
}

func removeAt(arr []any, i int) []any {
	out := append([]any{}, arr[:i]...)
	return append(out, arr[i+1:]...)
}

func (a *App) roadmapComplete(_ context.Context, in nameIn) (any, error) {
	err := a.roadmapEdit(in.Name, func(cfg *ojson.Object, i int, o *ojson.Object) error {
		o.Set("status", statusDone)
		o.Set("completion_date", a.now().Format("2006-01-02"))
		cfg.Set("archive", append(cfg.Arr("archive"), o))
		cfg.Set("roadmap", removeAt(cfg.Arr("roadmap"), i))
		return nil
	})
	if err == nil {
		a.evaluateAchievements()
	}
	return a.roadmapView(), err
}

func (a *App) roadmapDelete(_ context.Context, in nameIn) (any, error) {
	err := a.roadmapEdit(in.Name, func(cfg *ojson.Object, i int, _ *ojson.Object) error {
		cfg.Set("roadmap", removeAt(cfg.Arr("roadmap"), i))
		return nil
	})
	return a.roadmapView(), err
}

// RoadmapView lists both tabs.
type RoadmapView struct {
	Current   []map[string]any `json:"current"`
	Archive   []map[string]any `json:"archive"`
	Reminders []map[string]any `json:"reminders"`
}

func (a *App) roadmapView() RoadmapView {
	v := RoadmapView{Current: []map[string]any{}, Archive: []map[string]any{}, Reminders: []map[string]any{}}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		conv := func(key string) []map[string]any {
			out := []map[string]any{}
			for _, it := range cfg.Arr(key) {
				if o, ok := it.(*ojson.Object); ok {
					m := map[string]any{}
					for _, k := range o.Keys() {
						m[k] = ojson.ToPlain(o.Get(k))
					}
					out = append(out, m)
				}
			}
			return out
		}
		v.Current, v.Archive, v.Reminders = conv("roadmap"), conv("archive"), conv("reminders")
	})
	return v
}

// checkRoadmap: planned items past their end date become late (the Python
// monitor_roadmap was never started).
func (a *App) checkRoadmap() {
	today := a.now().Format("2006-01-02")
	changed := false
	_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		for _, it := range cfg.Arr("roadmap") {
			if o, ok := it.(*ojson.Object); ok && o.Str("status") == statusPlanned && o.Str("end_date") != "" && o.Str("end_date") < today {
				o.Set("status", statusLate)
				changed = true
			}
		}
		if !changed {
			return errNoChange
		}
		return nil
	})
	if changed {
		a.emit("roadmap:changed", nil)
	}
}

var errNoChange = &bridge.UserError{Message: "no change"}

func (a *App) remindersAdd(_ context.Context, in struct {
	When    string `json:"when"` // "2006-01-02T15:04" (local)
	Message string `json:"message"`
}) (any, error) {
	t, err := time.ParseInLocation("2006-01-02T15:04", in.When, time.Local)
	if err != nil {
		return nil, bridge.Errf("Podaj datę i godzinę.")
	}
	if !t.After(a.now()) {
		return nil, bridge.Errf("Przypomnienie musi być w przyszłości.")
	}
	msg := strings.TrimSpace(in.Message)
	if msg == "" {
		return nil, bridge.Errf("Podaj treść przypomnienia.")
	}
	err = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		o := ojson.NewObject()
		o.Set("time", ojson.Float(float64(t.Unix())))
		o.Set("message", msg)
		cfg.Set("reminders", append(cfg.Arr("reminders"), o))
		return nil
	})
	return a.roadmapView(), err
}

func (a *App) remindersDelete(_ context.Context, in struct {
	Index int `json:"index"`
}) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		arr := cfg.Arr("reminders")
		if in.Index < 0 || in.Index >= len(arr) {
			return bridge.Errf("Brak przypomnienia.")
		}
		cfg.Set("reminders", removeAt(arr, in.Index))
		return nil
	})
	return a.roadmapView(), err
}

func (a *App) checkReminders() {
	now := float64(a.now().Unix())
	var due []string
	_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		for _, it := range cfg.Arr("reminders") {
			o, ok := it.(*ojson.Object)
			if !ok || o.Bool("notified", false) {
				continue
			}
			if t, ok := ojson.ToFloat(o.Get("time")); ok && t <= now {
				o.Set("notified", true)
				due = append(due, o.Str("message"))
			}
		}
		if len(due) == 0 {
			return errNoChange
		}
		return nil
	})
	for _, m := range due {
		a.emit("reminder", map[string]any{"message": m})
	}
}

// ------------------------------------------------------------ achievements

// Achievement for the UI.
type Achievement struct {
	ID          string  `json:"id"`
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Hidden      bool    `json:"hidden"`
	Unlocked    bool    `json:"unlocked"`
	Timestamp   float64 `json:"timestamp"`
	Progress    float64 `json:"progress"`
	Target      float64 `json:"target"`
}

func (a *App) loadAchievementDefs() []*ojson.Object {
	raw, err := os.ReadFile(a.S.L.AchievDefFile)
	if err != nil {
		return nil
	}
	v, err := ojson.Decode(raw)
	if err != nil {
		return nil
	}
	var out []*ojson.Object
	if arr, ok := v.([]any); ok {
		for _, it := range arr {
			if o, ok := it.(*ojson.Object); ok {
				out = append(out, o)
			}
		}
	}
	return out
}

// achievementValue computes a rule's current value (same rules as Python).
func achievementValue(def *ojson.Object, cfg *ojson.Object, consecutive int64, progress *ojson.Object) (float64, bool) {
	games := cfg.Obj("games")
	count := func(pred func(*ojson.Object) bool) float64 {
		n := 0.0
		for _, k := range games.Keys() {
			if g := games.Obj(k); g != nil && pred(g) {
				n++
			}
		}
		return n
	}
	has := func(list []string, v string) bool {
		for _, x := range list {
			if x == v {
				return true
			}
		}
		return false
	}
	played := func(g *ojson.Object) bool { return g.Int("play_count", 0) > 0 }
	done := func(g *ojson.Object) bool { return g.Float("completion", 0) >= 100 }
	switch def.Str("rule_type") {
	case "games_launched_count":
		return count(played), true
	case "library_size":
		return float64(games.Len()), true
	case "total_playtime_hours":
		s := 0.0
		for _, k := range games.Keys() {
			s += games.Obj(k).Float("play_time", 0)
		}
		return math.Round(s/36) / 100, true
	case "games_completed_100":
		return count(done), true
	case "playtime_single_game_hours":
		m := 0.0
		for _, k := range games.Keys() {
			m = math.Max(m, games.Obj(k).Float("play_time", 0)/3600)
		}
		return math.Round(m*100) / 100, true
	case "genre_played_count", "genre_completed_100":
		genre := def.Str("genre")
		if genre == "" {
			return 0, false
		}
		pred := played
		if def.Str("rule_type") == "genre_completed_100" {
			pred = done
		}
		return count(func(g *ojson.Object) bool { return pred(g) && has(g.Strings("genres"), genre) }), true
	case "tag_played_count", "tag_completed_100":
		tag := def.Str("tag")
		if tag == "" {
			return 0, false
		}
		pred := played
		if def.Str("rule_type") == "tag_completed_100" {
			pred = done
		}
		return count(func(g *ojson.Object) bool { return pred(g) && has(g.Strings("tags"), tag) }), true
	case "group_played_count", "group_completed_100":
		grp := cfg.Obj("groups").Strings(def.Str("group"))
		if !cfg.Obj("groups").Has(def.Str("group")) {
			return 0, false
		}
		n := 0.0
		for _, name := range grp {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			if (def.Str("rule_type") == "group_played_count" && played(g)) || (def.Str("rule_type") == "group_completed_100" && done(g)) {
				n++
			}
		}
		return n, true
	case "roadmap_completed_count":
		return float64(len(cfg.Arr("archive"))), true
	case "games_rated_count":
		return count(func(g *ojson.Object) bool { return g.Get("rating") != nil }), true
	case "groups_created":
		return float64(cfg.Obj("groups").Len()), true
	case "games_with_tags":
		return count(func(g *ojson.Object) bool { return len(g.Arr("tags")) > 0 }), true
	case "roadmap_items_added":
		return float64(len(cfg.Arr("roadmap"))), true
	case "themes_changed":
		return float64(cfg.Obj("user").Int("theme_change_count", 0)), true
	case "game_launched_at_night":
		if progress.Bool("_triggered_at_night", false) {
			return 1, true
		}
		return 0, true
	case "consecutive_days_used":
		return float64(consecutive), true
	case "mods_installed":
		n := 0.0
		if md := cfg.Obj("mods_data"); md != nil {
			for _, gk := range md.Keys() {
				profs := md.Obj(gk).Obj("profiles")
				for _, pk := range profs.Keys() {
					n += float64(profs.Obj(pk).Obj("mods").Len())
				}
			}
		}
		return n, true
	}
	return 0, false
}

// evaluateAchievements updates progress/unlocks in user.achievements.
func (a *App) evaluateAchievements() []string {
	defs := a.loadAchievementDefs()
	if len(defs) == 0 {
		return nil
	}
	var consecutive int64
	a.S.ReadLocal(func(l *ojson.Object) { consecutive = l.Int("consecutive_days", 0) })
	var unlocked []string
	_ = a.S.UpdateConfig(func(cfg *ojson.Object) error {
		ach := cfg.EnsureObj("user").EnsureObj("achievements")
		changed := false
		for _, d := range defs {
			id := d.Str("id")
			if id == "" {
				continue
			}
			p := ach.Obj(id)
			if p != nil && p.Bool("unlocked", false) {
				continue
			}
			target, ok := ojson.ToFloat(d.Get("target_value"))
			if !ok {
				continue
			}
			val, ok := achievementValue(d, cfg, consecutive, p)
			if !ok {
				continue
			}
			if p == nil {
				p = ojson.NewObject()
				p.Set("unlocked", false)
				p.Set("timestamp", nil)
				p.Set("current_progress", 0)
				ach.Set(id, p)
				changed = true
			}
			if cur, _ := ojson.ToFloat(p.Get("current_progress")); cur != val {
				p.Set("current_progress", val)
				changed = true
			}
			if val >= target-0.001 {
				p.Set("unlocked", true)
				p.Set("timestamp", ojson.Float(float64(a.now().UnixNano())/1e9))
				unlocked = append(unlocked, d.Str("name"))
				changed = true
			}
		}
		if !changed {
			return errNoChange
		}
		return nil
	})
	for _, n := range unlocked {
		a.emit("achievement", map[string]any{"name": n})
	}
	return unlocked
}

func (a *App) achievements() []Achievement {
	a.evaluateAchievements()
	defs := a.loadAchievementDefs()
	out := []Achievement{}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		ach := cfg.Obj("user").Obj("achievements")
		for _, d := range defs {
			p := ach.Obj(d.Str("id"))
			t, _ := ojson.ToFloat(d.Get("target_value"))
			x := Achievement{ID: d.Str("id"), Name: d.Str("name"), Description: d.Str("description"), Hidden: d.Bool("hidden", false), Target: t}
			if p != nil {
				x.Unlocked = p.Bool("unlocked", false)
				x.Timestamp = p.Float("timestamp", 0)
				x.Progress = p.Float("current_progress", 0)
			}
			out = append(out, x)
		}
	})
	return out
}

// ------------------------------------------------------------------- music

// Track is a playable file.
type Track struct {
	ID     string `json:"id"`
	Title  string `json:"title"`
	Path   string `json:"path"`
	Exists bool   `json:"exists"`
}

// MusicView lists the internal folder and the saved playlists.
type MusicView struct {
	Internal  []Track            `json:"internal"`
	Playlists map[string][]Track `json:"playlists"`
	Active    string             `json:"active"`
	Volume    float64            `json:"volume"`
	Repeat    string             `json:"repeat"`
	Shuffle   bool               `json:"shuffle"`
	Favorites []string           `json:"favorites"`
}

var audioExt = map[string]bool{".mp3": true, ".ogg": true, ".wav": true, ".flac": true, ".m4a": true, ".aac": true, ".opus": true, ".webm": true}

func (a *App) track(p string) Track {
	h := sha1.Sum([]byte(strings.ToLower(paths.NormPath(p))))
	id := hex.EncodeToString(h[:10])
	abs := p
	if !filepath.IsAbs(abs) && paths.DriveOf(abs) == "" {
		abs = paths.Resolve(p, a.appDir())
	}
	a.mu.Lock()
	a.tracks[id] = abs
	a.mu.Unlock()
	title := strings.TrimSuffix(paths.Base(p), filepath.Ext(p))
	return Track{ID: id, Title: title, Path: p, Exists: fileExists(abs)}
}

func (a *App) musicList() MusicView {
	v := MusicView{Playlists: map[string][]Track{}, Internal: []Track{}}
	if entries, err := os.ReadDir(a.S.L.MusicDir); err == nil {
		for _, e := range entries {
			if !e.IsDir() && audioExt[strings.ToLower(filepath.Ext(e.Name()))] {
				v.Internal = append(v.Internal, a.track(filepath.Join(a.S.L.MusicDir, e.Name())))
			}
		}
	}
	a.S.ReadLocal(func(l *ojson.Object) {
		// named_music_playlists is the current format; music_named_playlists
		// (older) is shown when a name is missing from the new one.
		for _, key := range []string{"named_music_playlists", "music_named_playlists"} {
			pl := l.Obj(key)
			for _, name := range pl.Keys() {
				if _, done := v.Playlists[name]; done {
					continue
				}
				list := []Track{}
				for _, p := range pl.Strings(name) {
					list = append(list, a.track(p))
				}
				v.Playlists[name] = list
			}
		}
		v.Active = l.Str("active_music_playlist_name")
		v.Volume = l.Float("music_player_volume", 0.5)
		v.Repeat = l.Str("music_repeat_mode")
		v.Shuffle = l.Bool("music_shuffle_mode", false)
		v.Favorites = l.Strings("music_favorite_tracks")
	})
	return v
}

// TrackFile implements webui.Media (only ids listed by music.list).
func (a *App) TrackFile(id string) string {
	a.mu.Lock()
	p := a.tracks[id]
	a.mu.Unlock()
	if p == "" || !audioExt[strings.ToLower(filepath.Ext(p))] {
		return ""
	}
	return p
}

func (a *App) musicSavePlaylist(_ context.Context, in struct {
	Old    string   `json:"old"`
	Name   string   `json:"name"`
	Tracks []string `json:"tracks"` // track ids or paths
}) (any, error) {
	name := strings.TrimSpace(in.Name)
	if name == "" || len(name) > 100 {
		return nil, bridge.Errf("Podaj nazwę playlisty.")
	}
	var list []any
	a.mu.Lock()
	for _, t := range in.Tracks {
		if p, ok := a.tracks[t]; ok {
			list = append(list, p)
		} else if fileExists(t) {
			list = append(list, t)
		}
	}
	a.mu.Unlock()
	if list == nil {
		list = []any{}
	}
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		pl := l.EnsureObj("named_music_playlists")
		if in.Old == "" && pl.Has(name) {
			return bridge.Errf("Playlista „%s” już istnieje.", name)
		}
		if in.Old != "" && in.Old != name {
			if pl.Has(name) {
				return bridge.Errf("Playlista „%s” już istnieje.", name)
			}
			_ = pl.Rename(in.Old, name)
		}
		pl.Set(name, list)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return a.musicList(), nil
}

func (a *App) musicDeletePlaylist(_ context.Context, in nameIn) (any, error) {
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		l.EnsureObj("named_music_playlists").Delete(in.Name)
		if l.Str("active_music_playlist_name") == in.Name {
			l.Set("active_music_playlist_name", nil)
		}
		return nil
	})
	return a.musicList(), err
}

func (a *App) musicAddFolder(_ context.Context, in struct {
	Playlist string `json:"playlist"`
}) (any, error) {
	dir, ok, err := a.dlg.PickFolder(a.hwnd(), "Wybierz folder z muzyką")
	if err != nil || !ok {
		return nil, err
	}
	var files []any
	_ = filepath.WalkDir(dir, func(p string, d os.DirEntry, err error) error {
		if err == nil && !d.IsDir() && audioExt[strings.ToLower(filepath.Ext(p))] && len(files) < 5000 {
			files = append(files, p)
		}
		return nil
	})
	name := strings.TrimSpace(in.Playlist)
	if name == "" {
		name = filepath.Base(dir)
	}
	err = a.S.UpdateLocal(func(l *ojson.Object) error {
		pl := l.EnsureObj("named_music_playlists")
		pl.Set(name, append(pl.Arr(name), files...))
		l.Set("last_music_folder", dir)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return a.musicList(), nil
}

func (a *App) musicState(_ context.Context, in struct {
	Volume  *float64 `json:"volume"`
	Active  *string  `json:"active"`
	Repeat  *string  `json:"repeat"`
	Shuffle *bool    `json:"shuffle"`
}) (any, error) {
	return true, a.S.UpdateLocal(func(l *ojson.Object) error {
		if in.Volume != nil && *in.Volume >= 0 && *in.Volume <= 1 {
			l.Set("music_player_volume", ojson.Float(*in.Volume))
		}
		if in.Active != nil {
			l.Set("active_music_playlist_name", *in.Active)
		}
		if in.Repeat != nil && (*in.Repeat == "none" || *in.Repeat == "one" || *in.Repeat == "all") {
			l.Set("music_repeat_mode", *in.Repeat)
		}
		if in.Shuffle != nil {
			l.Set("music_shuffle_mode", *in.Shuffle)
		}
		return nil
	})
}

// -------------------------------------------------------------------- chat

// ChatView: configured servers (no credentials) + the local archive.
type ChatView struct {
	Servers []map[string]any `json:"servers"`
	Active  string           `json:"active"`
	Archive *chatdb.Summary  `json:"archive"`
	Error   string           `json:"error"`
	DBPath  string           `json:"dbPath"`
}

func (a *App) chatArchive() ChatView {
	v := ChatView{Servers: []map[string]any{}, DBPath: a.S.L.ChatDB}
	a.S.ReadLocal(func(l *ojson.Object) {
		for _, s := range l.Arr("chat_servers") {
			if o, ok := s.(*ojson.Object); ok {
				v.Servers = append(v.Servers, map[string]any{"id": o.Str("id"), "name": o.Str("name"), "url": o.Str("url"), "default": o.Bool("is_default", false)})
			}
		}
		v.Active = l.Str("active_chat_server_id")
	})
	s, err := chatdb.Read(a.S.L.ChatDB, 50)
	if err != nil {
		v.Error = err.Error()
	} else {
		v.Archive = s
	}
	return v
}
