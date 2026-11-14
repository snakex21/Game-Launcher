package app

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/filters"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/rawg"
	"github.com/snakex21/game-launcher/go/internal/saves"
)

// Profile is a launch profile.
type Profile struct {
	Name string `json:"name"`
	Exe  string `json:"exe"`
	Args string `json:"args"`
}

// GameDTO is a library entry for the UI.
type GameDTO struct {
	Name       string    `json:"name"`
	Type       string    `json:"type"`
	Emulator   string    `json:"emulator,omitempty"`
	Exe        string    `json:"exe,omitempty"`
	ROM        string    `json:"rom,omitempty"`
	EmuArgs    string    `json:"emuArgs,omitempty"`
	SavePath   string    `json:"savePath,omitempty"`
	Cover      string    `json:"cover,omitempty"` // cache-busting version, "" = no cover
	PlayTime   float64   `json:"playTime"`
	LastPlayed float64   `json:"lastPlayed"`
	PlayCount  int64     `json:"playCount"`
	Completion float64   `json:"completion"`
	Rating     *float64  `json:"rating"`
	Genres     []string  `json:"genres"`
	Tags       []string  `json:"tags"`
	Version    string    `json:"version,omitempty"`
	DateAdded  float64   `json:"dateAdded"`
	Profiles   []Profile `json:"profiles"`
	Running    bool      `json:"running"`
	Missing    bool      `json:"missing"`
}

// BootData is everything the first paint needs.
type BootData struct {
	Version  string         `json:"version"`
	Games    []GameDTO      `json:"games"`
	Groups   map[string]any `json:"groups"`
	Filters  []string       `json:"filters"`
	Genres   []string       `json:"customGenres"`
	View     string         `json:"view"`
	Tiles    int64          `json:"tilesPerRow"`
	Username string         `json:"username"`
	Warnings []string       `json:"warnings"`
	Remapped int            `json:"remapped"`
	Started  int64          `json:"started"`
	// StartPage (GL_START_PAGE, for demos/screenshots): "stats" or "game:<name>".
	StartPage string            `json:"startPage,omitempty"`
	Theme     map[string]string `json:"theme"`
}

func profilesOf(g *ojson.Object) []Profile {
	out := []Profile{}
	for _, p := range g.Arr("launch_profiles") {
		if po, ok := p.(*ojson.Object); ok {
			out = append(out, Profile{Name: po.Str("name"), Exe: po.Str("exe_path"), Args: po.Str("arguments")})
		}
	}
	return out
}

func (a *App) gameDTO(name string, g *ojson.Object) GameDTO {
	t := g.Str("game_type")
	if t == "" {
		t = "pc"
	}
	d := GameDTO{
		Name: name, Type: t, Emulator: g.Str("emulator_name"), Exe: g.Str("exe_path"), ROM: g.Str("rom_path"), EmuArgs: g.Str("emulator_args"),
		SavePath: g.Str("save_path"), PlayTime: g.Float("play_time", 0), LastPlayed: g.Float("last_played", 0),
		PlayCount: g.Int("play_count", 0), Completion: g.Float("completion", 0), Genres: g.Strings("genres"), Tags: g.Strings("tags"),
		Version: g.Str("version"), DateAdded: g.Float("date_added", 0), Profiles: profilesOf(g),
	}
	if r, ok := ojson.ToFloat(g.Get("rating")); ok {
		d.Rating = &r
	}
	return d
}

// Library returns all games (sorted by name) with runtime state. Cover
// files are stat'ed outside the store lock.
func (a *App) Library() []GameDTO {
	var out []GameDTO
	var covers []string
	a.S.ReadConfig(func(cfg *ojson.Object) {
		games := cfg.Obj("games")
		for _, name := range games.Keys() {
			if g := games.Obj(name); g != nil {
				out = append(out, a.gameDTO(name, g))
				covers = append(covers, g.Str("cover_image"))
			}
		}
	})
	for i := range out {
		out[i].Cover = a.coverVersionPath(covers[i])
	}
	a.mu.Lock()
	for i := range out {
		_, out[i].Running = a.sessions[out[i].Name]
		out[i].Missing = a.missing[out[i].Name]
	}
	a.mu.Unlock()
	sort.SliceStable(out, func(i, j int) bool { return lower(out[i].Name) < lower(out[j].Name) })
	return out
}

func (a *App) coverVersionPath(stored string) string {
	p := a.resolveAsset(stored)
	if p == "" {
		return ""
	}
	st, err := os.Stat(p)
	if err != nil || st.IsDir() {
		return ""
	}
	return fmt.Sprintf("%x", st.ModTime().UnixNano()^st.Size())
}

// Boot returns the first-paint snapshot.
func (a *App) Boot() BootData {
	b := BootData{Version: Version, Games: a.Library(), Groups: map[string]any{}, Filters: []string{}, Genres: []string{}, Started: a.started.Unix()}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		if gr := cfg.Obj("groups"); gr != nil {
			for _, k := range gr.Keys() {
				b.Groups[k] = gr.Strings(k)
			}
		}
		if f := cfg.Obj("saved_filters"); f != nil {
			b.Filters = f.Keys()
		}
		b.Genres = cfg.Obj("settings").Strings("custom_genres")
		b.Username = cfg.Obj("user").Str("username")
	})
	a.S.ReadLocal(func(l *ojson.Object) {
		b.View = l.Str("library_view_mode")
		b.Tiles = l.Int("tiles_per_row", 5)
	})
	b.Warnings = a.S.Warnings
	b.StartPage = os.Getenv("GL_START_PAGE")
	tv := a.themes()
	b.Theme = tv.Themes[tv.Current]
	b.Remapped = a.S.Remapped
	return b
}

// CheckFiles marks games whose exe/ROM is missing (run off the UI path:
// a stat on a disconnected drive can be slow).
func (a *App) CheckFiles() map[string]bool {
	type item struct{ name, path string }
	var items []item
	a.S.ReadConfig(func(cfg *ojson.Object) {
		games := cfg.Obj("games")
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			p := g.Str("exe_path")
			if g.Str("game_type") == "emulator" {
				p = g.Str("rom_path")
			}
			items = append(items, item{name, p})
		}
	})
	res := map[string]bool{}
	for _, it := range items {
		res[it.name] = it.path == "" || paths.FindExisting(it.path, a.appDir(), paths.Exists) == ""
	}
	a.mu.Lock()
	a.missing = res
	a.mu.Unlock()
	return res
}

// GameDetails is the full record for the details view.
type GameDetails struct {
	GameDTO
	Description  string            `json:"description"`
	Notes        string            `json:"notes"`
	Released     string            `json:"releaseDate"`
	Website      string            `json:"website"`
	Developers   []string          `json:"developers"`
	Publishers   []string          `json:"publishers"`
	GenresAPI    []string          `json:"genresApi"`
	TagsAPI      []string          `json:"tagsApi"`
	Platforms    []string          `json:"platforms"`
	Requirements map[string]string `json:"requirements"`
	Checklist    []map[string]any  `json:"checklist"`
	Screenshots  int               `json:"screenshots"`
	HasRAWGCover bool              `json:"hasRawgCover"`
	Sessions     int               `json:"sessions"`
	Groups       []string          `json:"groups"`
	ResolvedExe  string            `json:"resolvedExe"`
}

func (a *App) gameGet(_ context.Context, in nameIn) (any, error) {
	var d *GameDetails
	a.S.ReadConfig(func(cfg *ojson.Object) {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return
		}
		d = &GameDetails{GameDTO: a.gameDTO(in.Name, g)}
		d.Description = g.Str("description")
		d.Notes = g.Str("notes")
		d.Released = g.Str("release_date")
		d.Website = g.Str("website")
		d.Developers = g.Strings("developers")
		d.Publishers = g.Strings("publishers")
		d.GenresAPI = g.Strings("genres_api")
		d.TagsAPI = g.Strings("tags_api")
		d.Platforms = g.Strings("platforms")
		if r := g.Obj("requirements_pc"); r != nil {
			d.Requirements = map[string]string{"minimum": r.Str("minimum"), "recommended": r.Str("recommended")}
		}
		d.Checklist = []map[string]any{}
		for _, it := range g.Arr("checklist") {
			if o, ok := it.(*ojson.Object); ok {
				d.Checklist = append(d.Checklist, map[string]any{"task": o.Str("task"), "done": o.Bool("done", false)})
			}
		}
		d.Screenshots = len(a.screenshotList(g))
		d.HasRAWGCover = g.Str("cover_rawg") != ""
		d.Sessions = len(g.Arr("play_sessions"))
		if gr := cfg.Obj("groups"); gr != nil {
			for _, k := range gr.Keys() {
				for _, n := range gr.Strings(k) {
					if n == in.Name {
						d.Groups = append(d.Groups, k)
					}
				}
			}
		}
	})
	if d == nil {
		return nil, bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
	}
	p := d.Exe
	if d.Type == "emulator" {
		p = d.ROM
	}
	d.ResolvedExe = paths.FindExisting(p, a.appDir(), paths.Exists)
	d.Missing = d.ResolvedExe == ""
	d.Cover = a.coverVersionPath(func() string {
		var c string
		a.S.ReadConfig(func(cfg *ojson.Object) { c = cfg.Obj("games").Obj(in.Name).Str("cover_image") })
		return c
	}())
	a.mu.Lock()
	_, d.Running = a.sessions[in.Name]
	a.mu.Unlock()
	return d, nil
}

// GameForm is the add/edit form payload.
type GameForm struct {
	Original string    `json:"original"` // "" = add
	Name     string    `json:"name"`
	Type     string    `json:"type"`
	Exe      string    `json:"exe"`
	Emulator string    `json:"emulator"`
	ROM      string    `json:"rom"`
	EmuArgs  string    `json:"emuArgs"`
	SavePath string    `json:"savePath"`
	Cover    *string   `json:"cover"` // nil = unchanged; "" = remove
	Genres   []string  `json:"genres"`
	Tags     []string  `json:"tags"`
	Rating   *float64  `json:"rating"`
	Version  string    `json:"version"`
	Notes    string    `json:"notes"`
	Profiles []Profile `json:"profiles"`
	Complete *float64  `json:"completion"`
}

func cleanList(in []string) []any {
	out := []any{}
	seen := map[string]bool{}
	for _, s := range in {
		s = strings.TrimSpace(s)
		if s == "" || seen[lower(s)] {
			continue
		}
		seen[lower(s)] = true
		out = append(out, s)
	}
	return out
}

func validName(n string) error {
	n = strings.TrimSpace(n)
	if n == "" {
		return bridge.Errf("Nazwa gry jest wymagana.")
	}
	if len(n) > 200 {
		return bridge.Errf("Nazwa gry jest za długa.")
	}
	return nil
}

// gameSave adds or edits a game. Editing MERGES the form fields into the
// existing record: checklist, screenshots, RAWG data, statistics and every
// unknown key are kept (the Python form rebuilt the record and lost them).
func (a *App) gameSave(_ context.Context, f GameForm) (any, error) {
	f.Name = strings.TrimSpace(f.Name)
	if err := validName(f.Name); err != nil {
		return nil, err
	}
	if f.Type != "emulator" {
		f.Type = "pc"
	}
	switch f.Type {
	case "pc":
		if strings.TrimSpace(f.Exe) == "" {
			return nil, bridge.Errf("Ścieżka do pliku gry (.exe) jest wymagana.")
		}
		if !paths.Exists(f.Exe) {
			return nil, bridge.Errf("Plik gry nie istnieje:\n%s", f.Exe)
		}
	case "emulator":
		if f.Emulator == "" || f.ROM == "" {
			return nil, bridge.Errf("Wybierz emulator i plik ROM/ISO.")
		}
		if !paths.Exists(f.ROM) {
			return nil, bridge.Errf("Plik ROM/ISO nie istnieje:\n%s", f.ROM)
		}
	}
	if f.Rating != nil && (*f.Rating < 0 || *f.Rating > 10) {
		return nil, bridge.Errf("Ocena musi być w zakresie 0–10.")
	}
	var coverAbs string
	if f.Cover != nil && *f.Cover != "" {
		if !fileExists(*f.Cover) {
			return nil, bridge.Errf("Plik okładki nie istnieje:\n%s", *f.Cover)
		}
		coverAbs = *f.Cover
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.EnsureObj("games")
		var g *ojson.Object
		if f.Original == "" {
			if games.Has(f.Name) || hasFold(games.Keys(), f.Name) {
				return bridge.Errf("Gra o nazwie „%s” już istnieje.", f.Name)
			}
			g = ojson.NewObject()
			g.Set("name", f.Name)
			g.Set("date_added", ojson.Float(float64(a.now().UnixNano())/1e9))
			g.Set("play_time", 0)
			g.Set("completion", 0)
			g.Set("last_played", nil)
			g.Set("play_sessions", []any{})
			g.Set("screenshots", []any{})
			g.Set("autoscan_screenshots", []any{})
			g.Set("checklist", []any{})
			games.Set(f.Name, g)
		} else {
			g = games.Obj(f.Original)
			if g == nil {
				return bridge.Errf("Nie znaleziono gry „%s”.", f.Original)
			}
			if f.Name != f.Original {
				if games.Has(f.Name) {
					return bridge.Errf("Gra o nazwie „%s” już istnieje.", f.Name)
				}
				if err := games.Rename(f.Original, f.Name); err != nil {
					return err
				}
				if g.Has("name") {
					g.Set("name", f.Name)
				}
				renameEverywhere(cfg, f.Original, f.Name)
				a.renameRuntime(f.Original, f.Name)
				// keep the save backups with the game
				oldDir, newDir := saves.GameDir(a.S.L.GamesSaves, f.Original), saves.GameDir(a.S.L.GamesSaves, f.Name)
				if paths.Exists(oldDir) && !paths.Exists(newDir) {
					_ = os.Rename(oldDir, newDir)
				}
			}
		}
		g.Set("game_type", f.Type)
		if f.Type == "pc" {
			g.Set("exe_path", paths.NormPath(f.Exe))
			if g.Has("emulator_name") {
				g.Set("emulator_name", nil)
				g.Set("rom_path", nil)
				g.Set("emulator_args", nil)
			}
			profs := []any{}
			hasDefault := false
			for _, p := range f.Profiles {
				name := strings.TrimSpace(p.Name)
				if name == "" {
					continue
				}
				po := ojson.NewObject()
				po.Set("name", name)
				if strings.TrimSpace(p.Exe) == "" {
					po.Set("exe_path", nil)
				} else {
					po.Set("exe_path", paths.NormPath(p.Exe))
				}
				po.Set("arguments", p.Args)
				if strings.EqualFold(name, "default") {
					if hasDefault {
						continue
					}
					hasDefault = true
					profs = append([]any{po}, profs...)
					continue
				}
				profs = append(profs, po)
			}
			if !hasDefault {
				d := ojson.NewObject()
				d.Set("name", "Default")
				d.Set("exe_path", nil)
				d.Set("arguments", "")
				profs = append([]any{d}, profs...)
			}
			g.Set("launch_profiles", profs)
		} else {
			g.Set("emulator_name", f.Emulator)
			g.Set("rom_path", paths.NormPath(f.ROM))
			g.Set("emulator_args", f.EmuArgs)
			if !g.Has("launch_profiles") {
				g.Set("launch_profiles", []any{})
			}
		}
		if strings.TrimSpace(f.SavePath) == "" {
			g.Set("save_path", "")
		} else {
			g.Set("save_path", paths.NormPath(f.SavePath))
		}
		g.Set("genres", cleanList(f.Genres))
		g.Set("tags", cleanList(f.Tags))
		if f.Rating == nil {
			g.Set("rating", nil)
		} else {
			g.Set("rating", ojson.Float(*f.Rating))
		}
		g.Set("version", f.Version)
		g.Set("notes", f.Notes)
		if f.Complete != nil {
			c := *f.Complete
			if c < 0 || c > 100 {
				return bridge.Errf("Ukończenie musi być w zakresie 0–100%%.")
			}
			g.Set("completion", int64(c))
		}
		if f.Cover != nil {
			if *f.Cover == "" {
				g.Set("cover_image", "")
			} else {
				stored, err := a.importCover(f.Name, coverAbs)
				if err != nil {
					return err
				}
				g.Set("cover_image", stored)
				g.Set("cover_custom", stored)
			}
		}
		g.SetDefault("cover_image", "")
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return f.Name, nil
}

func hasFold(keys []string, name string) bool {
	for _, k := range keys {
		if strings.EqualFold(k, name) {
			return true
		}
	}
	return false
}

// importCover copies a chosen image into images/ (so the cover travels with
// the launcher) unless it is already there; returns the stored path.
func (a *App) importCover(game, src string) (string, error) {
	imagesAbs, _ := filepath.Abs(a.S.L.ImagesDir)
	srcAbs, _ := filepath.Abs(src)
	if rel, err := filepath.Rel(imagesAbs, srcAbs); err == nil && !strings.HasPrefix(rel, "..") {
		return `images\` + rel, nil
	}
	ext := strings.ToLower(filepath.Ext(src))
	if ext == "" {
		ext = ".png"
	}
	name := rawg.SafeName(game) + "_cover" + ext
	if err := os.MkdirAll(a.S.L.ImagesDir, 0o755); err != nil {
		return "", err
	}
	if _, err := saves.CopyTree(src, filepath.Join(a.S.L.ImagesDir, name)); err != nil {
		return "", bridge.Errf("Nie udało się skopiować okładki: %v", err)
	}
	return `images\` + name, nil
}

// renameEverywhere updates references to a renamed game.
func renameEverywhere(cfg *ojson.Object, oldName, newName string) {
	if gr := cfg.Obj("groups"); gr != nil {
		for _, k := range gr.Keys() {
			arr := gr.Arr(k)
			for i, v := range arr {
				if v == oldName {
					arr[i] = newName
				}
			}
		}
	}
	for _, key := range []string{"roadmap", "archive"} {
		for _, it := range cfg.Arr(key) {
			if o, ok := it.(*ojson.Object); ok && o.Str("game_name") == oldName {
				o.Set("game_name", newName)
			}
		}
	}
	if md := cfg.Obj("mods_data"); md != nil && md.Has(oldName) && !md.Has(newName) {
		_ = md.Rename(oldName, newName)
	}
}

func (a *App) renameRuntime(oldName, newName string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if s, ok := a.sessions[oldName]; ok {
		delete(a.sessions, oldName)
		a.sessions[newName] = s
	}
	for pid, g := range a.owned {
		if g == oldName {
			a.owned[pid] = newName
		}
	}
}

func (a *App) gameDelete(_ context.Context, in struct {
	Name          string `json:"name"`
	DeleteBackups bool   `json:"deleteBackups"`
}) (any, error) {
	var coverFile string
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.Obj("games")
		g := games.Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		coverFile = g.Str("cover_image")
		games.Delete(in.Name)
		if gr := cfg.Obj("groups"); gr != nil {
			for _, k := range gr.Keys() {
				var keep []any
				for _, v := range gr.Arr(k) {
					if v != in.Name {
						keep = append(keep, v)
					}
				}
				if keep == nil {
					keep = []any{}
				}
				gr.Set(k, keep)
			}
		}
		var rm []any
		for _, it := range cfg.Arr("roadmap") {
			if o, ok := it.(*ojson.Object); ok && o.Str("game_name") == in.Name {
				continue
			}
			rm = append(rm, it)
		}
		if cfg.Has("roadmap") {
			if rm == nil {
				rm = []any{}
			}
			cfg.Set("roadmap", rm)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	// Covers in images/ that belong to this game only.
	if p := a.resolveAsset(coverFile); p != "" {
		imagesAbs, _ := filepath.Abs(a.S.L.ImagesDir)
		if strings.HasPrefix(strings.ToLower(p), strings.ToLower(imagesAbs)+string(filepath.Separator)) {
			_ = os.Remove(p)
		}
	}
	if in.DeleteBackups {
		_ = os.RemoveAll(saves.GameDir(a.S.L.GamesSaves, in.Name))
	}
	a.mu.Lock()
	delete(a.sessions, in.Name)
	a.mu.Unlock()
	a.emit("library:changed", nil)
	return true, nil
}

// gamePatch updates small fields from the details view.
func (a *App) gamePatch(_ context.Context, in struct {
	Name       string           `json:"name"`
	Notes      *string          `json:"notes"`
	Checklist  []map[string]any `json:"checklist"`
	Completion *float64         `json:"completion"`
	Rating     *float64         `json:"rating"`
	SetRating  bool             `json:"setRating"`
}) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		if in.Notes != nil {
			g.Set("notes", *in.Notes)
		}
		if in.Checklist != nil {
			list := []any{}
			for _, it := range in.Checklist {
				task, _ := it["task"].(string)
				done, _ := it["done"].(bool)
				if strings.TrimSpace(task) == "" {
					continue
				}
				o := ojson.NewObject()
				o.Set("task", strings.TrimSpace(task))
				o.Set("done", done)
				list = append(list, o)
			}
			g.Set("checklist", list)
		}
		if in.Completion != nil {
			if *in.Completion < 0 || *in.Completion > 100 {
				return bridge.Errf("Ukończenie musi być w zakresie 0–100%%.")
			}
			g.Set("completion", int64(*in.Completion))
		}
		if in.SetRating {
			if in.Rating == nil {
				g.Set("rating", nil)
			} else {
				g.Set("rating", ojson.Float(*in.Rating))
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return true, nil
}

func (a *App) gameResetStats(_ context.Context, in nameIn) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		g.Set("play_time", 0)
		g.Set("completion", 0)
		g.Set("play_sessions", []any{})
		return nil
	})
	if err == nil {
		a.emit("library:changed", nil)
	}
	return true, err
}

// gameCover: "pick" (file dialog), "rawg" (use the RAWG copy), "clear".
func (a *App) gameCover(_ context.Context, in struct {
	Name   string `json:"name"`
	Action string `json:"action"`
}) (any, error) {
	var stored string
	switch in.Action {
	case "pick":
		p, ok, err := a.dlg.OpenFile(a.hwnd(), "Wybierz okładkę", "Obrazy", "*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp")
		if err != nil || !ok {
			return false, err
		}
		s, err := a.importCover(in.Name, p)
		if err != nil {
			return nil, err
		}
		stored = s
	case "rawg", "clear":
	default:
		return nil, bridge.Errf("Nieznana akcja.")
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		g := cfg.Obj("games").Obj(in.Name)
		if g == nil {
			return bridge.Errf("Nie znaleziono gry „%s”.", in.Name)
		}
		switch in.Action {
		case "pick":
			g.Set("cover_image", stored)
			g.Set("cover_custom", stored)
		case "rawg":
			if g.Str("cover_rawg") == "" {
				return bridge.Errf("Brak okładki z RAWG – najpierw pobierz dane.")
			}
			g.Set("cover_image", g.Str("cover_rawg"))
		case "clear":
			g.Set("cover_image", "")
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return true, nil
}

// gameRelocate rewrites a path prefix in all games and emulators
// ("E:\Gry" -> "F:\Gry"), for libraries moved to another drive/folder.
func (a *App) gameRelocate(_ context.Context, in struct {
	From string `json:"from"`
	To   string `json:"to"`
}) (any, error) {
	from := strings.TrimRight(paths.NormPath(strings.TrimSpace(in.From)), `\`)
	to := strings.TrimRight(paths.NormPath(strings.TrimSpace(in.To)), `\`)
	if from == "." || to == "." || from == "" || to == "" {
		return nil, bridge.Errf("Podaj oba prefiksy ścieżek.")
	}
	n := 0
	swap := func(o *ojson.Object, key string) {
		p, ok := o.Get(key).(string)
		if !ok || p == "" {
			return
		}
		np := paths.NormPath(p)
		if strings.EqualFold(np, from) || (len(np) > len(from) && strings.EqualFold(np[:len(from)], from) && np[len(from)] == '\\') {
			o.Set(key, to+np[len(from):])
			n++
		}
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		games := cfg.Obj("games")
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			for _, k := range []string{"exe_path", "rom_path", "save_path", "folder_path"} {
				swap(g, k)
			}
			for _, p := range g.Arr("launch_profiles") {
				if po, ok := p.(*ojson.Object); ok {
					swap(po, "exe_path")
				}
			}
		}
		if emus := cfg.Obj("emulators"); emus != nil {
			for _, k := range emus.Keys() {
				if e := emus.Obj(k); e != nil {
					swap(e, "path")
				}
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:files", a.CheckFiles())
	a.emit("library:changed", nil)
	return n, nil
}

// ------------------------------------------------------------- groups etc.

func reservedName(n string) bool {
	return n == "" || strings.HasPrefix(n, "---") || strings.EqualFold(n, "Wszystkie gry")
}

func (a *App) groupsSave(_ context.Context, in struct {
	Old  string `json:"old"`
	Name string `json:"name"`
}) (any, error) {
	name := strings.TrimSpace(in.Name)
	if reservedName(name) {
		return nil, bridge.Errf("Nieprawidłowa nazwa grupy.")
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		gr := cfg.EnsureObj("groups")
		if cfg.Obj("saved_filters").Has(name) {
			return bridge.Errf("Ta nazwa jest zajęta przez filtr.")
		}
		if in.Old == "" {
			if gr.Has(name) {
				return bridge.Errf("Grupa „%s” już istnieje.", name)
			}
			gr.Set(name, []any{})
			return nil
		}
		return gr.Rename(in.Old, name)
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return name, nil
}

func (a *App) groupsDelete(_ context.Context, in nameIn) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		cfg.EnsureObj("groups").Delete(in.Name)
		return nil
	})
	a.emit("library:changed", nil)
	return true, err
}

func (a *App) groupsToggle(_ context.Context, in struct {
	Group string `json:"group"`
	Game  string `json:"game"`
	In    bool   `json:"in"`
}) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		gr := cfg.EnsureObj("groups")
		if !gr.Has(in.Group) {
			return bridge.Errf("Grupa „%s” nie istnieje.", in.Group)
		}
		var list []any
		present := false
		for _, v := range gr.Arr(in.Group) {
			if v == in.Game {
				present = true
				if !in.In {
					continue
				}
			}
			list = append(list, v)
		}
		if in.In && !present {
			list = append(list, in.Game)
		}
		if list == nil {
			list = []any{}
		}
		gr.Set(in.Group, list)
		return nil
	})
	a.emit("library:changed", nil)
	return true, err
}

type filtersMeta struct {
	Fields    []filters.Field           `json:"fields"`
	Operators map[string][]string       `json:"operators"`
	Saved     map[string][]filters.Rule `json:"saved"`
	Emulators []string                  `json:"emulators"`
	Matches   map[string][]string       `json:"matches"` // filter -> matching games
}

func (a *App) filtersMeta() filtersMeta {
	m := filtersMeta{Fields: filters.Fields, Operators: filters.Operators, Saved: map[string][]filters.Rule{}, Matches: map[string][]string{}}
	a.S.ReadConfig(func(cfg *ojson.Object) {
		sf := cfg.Obj("saved_filters")
		games := cfg.Obj("games")
		for _, k := range sf.Keys() {
			rules := filters.RulesOf(sf.Obj(k))
			if rules == nil {
				rules = []filters.Rule{}
			}
			m.Saved[k] = rules
			hits := []string{}
			if len(rules) > 0 {
				for _, name := range games.Keys() {
					if g := games.Obj(name); g != nil && filters.Match(name, g, rules, time.Local) {
						hits = append(hits, name)
					}
				}
			}
			m.Matches[k] = hits
		}
		if e := cfg.Obj("emulators"); e != nil {
			m.Emulators = e.Keys()
		}
	})
	return m
}

func (a *App) filtersSave(_ context.Context, in struct {
	Old   string         `json:"old"`
	Name  string         `json:"name"`
	Rules []filters.Rule `json:"rules"`
}) (any, error) {
	name := strings.TrimSpace(in.Name)
	if reservedName(name) {
		return nil, bridge.Errf("Nieprawidłowa nazwa filtra.")
	}
	if len(in.Rules) == 0 {
		return nil, bridge.Errf("Filtr musi mieć co najmniej jedną regułę.")
	}
	for _, r := range in.Rules {
		if err := filters.Validate(r); err != nil {
			return nil, bridge.Errf("Reguła: %v", err)
		}
	}
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		sf := cfg.EnsureObj("saved_filters")
		if cfg.Obj("groups").Has(name) {
			return bridge.Errf("Ta nazwa jest zajęta przez grupę.")
		}
		if name != in.Old && sf.Has(name) {
			return bridge.Errf("Filtr „%s” już istnieje.", name)
		}
		o := ojson.NewObject()
		o.Set("name", name)
		rules := []any{}
		for _, r := range in.Rules {
			ro := ojson.NewObject()
			ro.Set("field", r.Field)
			ro.Set("operator", r.Operator)
			ro.Set("value", r.Value)
			rules = append(rules, ro)
		}
		o.Set("rules", rules)
		if in.Old != "" && in.Old != name && sf.Has(in.Old) {
			_ = sf.Rename(in.Old, name)
		}
		sf.Set(name, o)
		return nil
	})
	if err != nil {
		return nil, err
	}
	a.emit("library:changed", nil)
	return name, nil
}

func (a *App) filtersDelete(_ context.Context, in nameIn) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		cfg.EnsureObj("saved_filters").Delete(in.Name)
		return nil
	})
	a.emit("library:changed", nil)
	return true, err
}

func (a *App) genresSave(_ context.Context, in struct {
	Genres []string `json:"genres"`
}) (any, error) {
	err := a.S.UpdateConfig(func(cfg *ojson.Object) error {
		cfg.EnsureObj("settings").Set("custom_genres", cleanList(in.Genres))
		return nil
	})
	a.emit("library:changed", nil)
	return true, err
}

// ------------------------------------------------------------------ media

// CoverFile implements webui.Media.
func (a *App) CoverFile(game string, w int) string {
	var stored string
	a.S.ReadConfig(func(cfg *ojson.Object) {
		if g := cfg.Obj("games").Obj(game); g != nil {
			stored = g.Str("cover_image")
		}
	})
	src := a.resolveAsset(stored)
	if src == "" {
		return ""
	}
	if t, err := a.thumbs.Get(src, w); err == nil {
		return t
	}
	return src // undecodable here (e.g. bmp): let the browser try
}

func (a *App) screenshotList(g *ojson.Object) []string {
	var out []string
	seen := map[string]bool{}
	for _, key := range []string{"screenshots", "autoscan_screenshots"} {
		for _, v := range g.Arr(key) {
			s, ok := v.(string)
			if !ok {
				if o, ok2 := v.(*ojson.Object); ok2 {
					s = o.Str("path")
				}
			}
			if s != "" && !seen[lower(s)] {
				seen[lower(s)] = true
				out = append(out, s)
			}
		}
	}
	return out
}

// ScreenshotFile implements webui.Media.
func (a *App) ScreenshotFile(game string, i, w int) string {
	var list []string
	a.S.ReadConfig(func(cfg *ojson.Object) {
		if g := cfg.Obj("games").Obj(game); g != nil {
			list = a.screenshotList(g)
		}
	})
	if i < 0 || i >= len(list) {
		return ""
	}
	src := a.resolveAsset(list[i])
	if src == "" {
		return ""
	}
	if t, err := a.thumbs.Get(src, w); err == nil {
		return t
	}
	return src
}
