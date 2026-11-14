package app

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/procwatch"
	"github.com/snakex21/game-launcher/go/internal/scan"
	"github.com/snakex21/game-launcher/go/internal/store"
)

type scanCandidate = scan.Candidate

type fakeHost struct {
	mu     sync.Mutex
	events []string
}

func (h *fakeHost) Emit(e string, _ any) { h.mu.Lock(); h.events = append(h.events, e); h.mu.Unlock() }
func (h *fakeHost) HWND() uintptr        { return 0 }
func (h *fakeHost) has(e string) bool {
	h.mu.Lock()
	defer h.mu.Unlock()
	for _, x := range h.events {
		if x == e {
			return true
		}
	}
	return false
}

type fakeDialogs struct{ file, folder string }

func (d fakeDialogs) OpenFile(uintptr, string, string, string) (string, bool, error) {
	return d.file, d.file != "", nil
}
func (d fakeDialogs) PickFolder(uintptr, string) (string, bool, error) {
	return d.folder, d.folder != "", nil
}
func (fakeDialogs) ShellOpen(string) error { return nil }

type fakeProcs struct {
	mu    sync.Mutex
	list  []procwatch.Process
	kills []uint32
}

func (p *fakeProcs) List() ([]procwatch.Process, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	return append([]procwatch.Process(nil), p.list...), nil
}
func (p *fakeProcs) Terminate(pid uint32) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.kills = append(p.kills, pid)
	var keep []procwatch.Process
	for _, x := range p.list {
		if x.PID != pid {
			keep = append(keep, x)
		}
	}
	p.list = keep
	return nil
}

type env struct {
	dir              string
	a                *App
	host             *fakeHost
	procs            *fakeProcs
	clock            time.Time
	gameExe, saveDir string
	started          []string
}

func newEnv(t *testing.T) *env {
	t.Helper()
	e := &env{dir: t.TempDir(), host: &fakeHost{}, procs: &fakeProcs{}, clock: time.Date(2026, 11, 10, 20, 0, 0, 0, time.Local)}
	e.gameExe = filepath.Join(e.dir, "Gry", "Gothic", "Gothic.exe")
	e.saveDir = filepath.Join(e.dir, "Saves", "Gothic")
	os.MkdirAll(filepath.Dir(e.gameExe), 0o755)
	os.WriteFile(e.gameExe, []byte("MZ"), 0o644)
	os.MkdirAll(e.saveDir, 0o755)
	os.WriteFile(filepath.Join(e.saveDir, "save1.sav"), []byte("1"), 0o644)
	cfg := map[string]any{
		"games": map[string]any{
			"Gothic": map[string]any{
				"exe_path": e.gameExe, "save_path": e.saveDir, "play_time": 100.5, "play_count": 2,
				"checklist":   []any{map[string]any{"task": "Rozdział 1", "done": true}},
				"screenshots": []any{"images\\a.png"}, "rawg_id": 42, "description": "Opis z RAWG", "cover_rawg": "images\\Gothic_rawg_cover.jpg",
				"launch_profiles": []any{map[string]any{"name": "Default", "exe_path": nil, "arguments": ""}, map[string]any{"name": "Mod", "exe_path": nil, "arguments": "-mod"}},
				"genres":          []any{"RPG"}, "tags": []any{"klasyk"},
			},
		},
		"groups":   map[string]any{"Ulubione": []any{"Gothic"}},
		"roadmap":  []any{map[string]any{"game_name": "Gothic", "start_date": "2026-11-01", "end_date": "2026-11-05", "time_spent": 0, "status": "Planowana"}},
		"settings": map[string]any{},
	}
	b, _ := json.MarshalIndent(cfg, "", "    ")
	os.MkdirAll(filepath.Join(e.dir, "data", "config"), 0o755)
	os.WriteFile(filepath.Join(e.dir, "data", "config", "config.json"), b, 0o644)
	os.WriteFile(filepath.Join(e.dir, "data", "config", "local_settings.json"), []byte(`{"rawg_api_key": "SEKRET-123", "chat_servers": [{"id":"1","name":"L","url":"http://127.0.0.1:5000","credentials":{"password":"HASLO"}}]}`), 0o644)
	st, err := store.Open(e.dir)
	if err != nil {
		t.Fatal(err)
	}
	e.a = New(st, e.host, fakeDialogs{})
	e.a.procs = e.procs
	e.a.now = func() time.Time { return e.clock }
	e.a.StartProcess = func(game string, cmd []string, cwd string) (uint32, error) {
		e.started = append(e.started, game+"|"+strings.Join(cmd, " ")+"|"+cwd)
		e.procs.mu.Lock()
		e.procs.list = append(e.procs.list, procwatch.Process{PID: 4242, Name: "gothic.exe", Exe: cmd[0]})
		e.procs.mu.Unlock()
		return 4242, nil
	}
	return e
}

func (e *env) game(t *testing.T) *ojson.Object {
	var g *ojson.Object
	e.a.S.ReadConfig(func(c *ojson.Object) { g = c.Obj("games").Obj("Gothic").Clone() })
	if g == nil {
		t.Fatal("game missing")
	}
	return g
}

// Editing must keep checklist, screenshots, RAWG data and stats.
func TestEditKeepsAllFields(t *testing.T) {
	e := newEnv(t)
	rating := 9.0
	_, err := e.a.gameSave(context.Background(), GameForm{Original: "Gothic", Name: "Gothic", Type: "pc", Exe: e.gameExe, SavePath: e.saveDir,
		Genres: []string{"RPG", "rpg", " Akcja "}, Tags: []string{"klasyk"}, Rating: &rating, Notes: "nowe",
		Profiles: []Profile{{Name: "Mod", Args: "-mod -x"}, {Name: "Default"}}})
	if err != nil {
		t.Fatal(err)
	}
	g := e.game(t)
	if len(g.Arr("checklist")) != 1 || len(g.Arr("screenshots")) != 1 || g.Int("rawg_id", 0) != 42 || g.Str("description") != "Opis z RAWG" ||
		g.Float("play_time", 0) != 100.5 || g.Str("cover_rawg") == "" || g.Int("play_count", 0) != 2 {
		t.Fatalf("fields lost: %s", ojson.MarshalCompact(g))
	}
	if g.Str("notes") != "nowe" || len(g.Arr("genres")) != 2 {
		t.Fatalf("form not applied: %s", ojson.MarshalCompact(g))
	}
	profs := g.Arr("launch_profiles")
	if profs[0].(*ojson.Object).Str("name") != "Default" || profs[1].(*ojson.Object).Str("arguments") != "-mod -x" {
		t.Fatalf("profiles: %s", ojson.MarshalCompact(profs))
	}
}

func TestRenameUpdatesGroupsRoadmapAndBackups(t *testing.T) {
	e := newEnv(t)
	os.MkdirAll(filepath.Join(e.a.S.L.GamesSaves, "Gothic", "saves", "Save_1%_20260101_000000"), 0o755)
	if _, err := e.a.gameSave(context.Background(), GameForm{Original: "Gothic", Name: "Gothic I", Type: "pc", Exe: e.gameExe}); err != nil {
		t.Fatal(err)
	}
	e.a.S.ReadConfig(func(c *ojson.Object) {
		if !c.Obj("games").Has("Gothic I") || c.Obj("games").Has("Gothic") {
			t.Fatal("not renamed")
		}
		if c.Obj("groups").Strings("Ulubione")[0] != "Gothic I" || c.Arr("roadmap")[0].(*ojson.Object).Str("game_name") != "Gothic I" {
			t.Fatal("references not renamed")
		}
	})
	if _, err := os.Stat(filepath.Join(e.a.S.L.GamesSaves, "Gothic I", "saves")); err != nil {
		t.Fatal("backups not moved")
	}
}

func TestAddValidations(t *testing.T) {
	e := newEnv(t)
	ctx := context.Background()
	if _, err := e.a.gameSave(ctx, GameForm{Name: "gothic", Type: "pc", Exe: e.gameExe}); err == nil {
		t.Fatal("case-insensitive duplicate accepted")
	}
	if _, err := e.a.gameSave(ctx, GameForm{Name: "X", Type: "pc", Exe: filepath.Join(e.dir, "brak.exe")}); err == nil {
		t.Fatal("missing exe accepted")
	}
	if _, err := e.a.gameSave(ctx, GameForm{Name: "Nowa", Type: "pc", Exe: e.gameExe}); err != nil {
		t.Fatal(err)
	}
	e.a.S.ReadConfig(func(c *ojson.Object) {
		g := c.Obj("games").Obj("Nowa")
		if g == nil || len(g.Arr("launch_profiles")) != 1 || g.Get("date_added") == nil || !g.Has("checklist") {
			t.Fatalf("%s", ojson.MarshalCompact(g))
		}
	})
}

// Launch -> process seen -> process ends -> play time, session, roadmap, autosave.
func TestLaunchSessionAndAutosave(t *testing.T) {
	e := newEnv(t)
	res, err := e.a.Launch("Gothic", "Mod")
	if err != nil {
		t.Fatal(err)
	}
	want := "Gothic|" + e.gameExe + " -mod|" + filepath.Dir(e.gameExe)
	if len(e.started) != 1 || !strings.EqualFold(e.started[0], want) || res.PID != 4242 {
		t.Fatalf("started %v, want %s", e.started, want)
	}
	if _, err := e.a.Launch("Gothic", ""); err == nil {
		t.Fatal("double launch allowed")
	}
	if e.game(t).Int("play_count", 0) != 3 {
		t.Fatal("play_count not incremented")
	}
	e.clock = e.clock.Add(30 * time.Minute)
	e.a.Poll()
	if len(e.a.Running()) != 1 {
		t.Fatal("not running")
	}
	// game exits
	e.procs.mu.Lock()
	e.procs.list = nil
	e.procs.mu.Unlock()
	e.clock = e.clock.Add(30 * time.Minute)
	e.a.Poll()
	if len(e.a.Running()) != 0 {
		t.Fatal("still running")
	}
	g := e.game(t)
	if pt := g.Float("play_time", 0); pt < 100.5+3599 || pt > 100.5+3601 {
		t.Fatalf("play_time %v", pt)
	}
	if len(g.Arr("play_sessions")) != 1 {
		t.Fatal("session not recorded")
	}
	e.a.S.ReadConfig(func(c *ojson.Object) {
		if c.Arr("roadmap")[0].(*ojson.Object).Float("time_spent", 0) < 3599 {
			t.Fatal("roadmap time not added")
		}
	})
	if _, err := os.Stat(filepath.Join(e.a.S.L.GamesSaves, "Gothic", "_autosave", "save1.sav")); err != nil {
		t.Fatal("autosave missing")
	}
	if !e.host.has("game:stopped") {
		t.Fatal("no stop event")
	}
}

func TestDetectsGameStartedOutsideAndClose(t *testing.T) {
	e := newEnv(t)
	e.procs.list = []procwatch.Process{{PID: 77, Name: "gothic.exe", Exe: e.gameExe}, {PID: 78, PPID: 77, Name: "helper.exe", Exe: `C:\x\helper.exe`}}
	e.a.Poll()
	if len(e.a.Running()) != 1 {
		t.Fatal("external game not detected")
	}
	n, err := e.a.Close("Gothic")
	if err != nil || n != 2 || e.procs.kills[0] != 78 {
		t.Fatalf("close: %d %v %v", n, err, e.procs.kills)
	}
}

func TestLaunchErrorIsReadable(t *testing.T) {
	e := newEnv(t)
	os.Remove(e.gameExe)
	_, err := e.a.Launch("Gothic", "")
	ue, ok := err.(*bridge.UserError)
	if !ok || ue.Title != "Nie znaleziono gry" || !strings.Contains(ue.Message, e.gameExe) {
		t.Fatalf("%#v", err)
	}
}

func TestStatsRangeSplitsMidnight(t *testing.T) {
	e := newEnv(t)
	start := time.Date(2026, 11, 9, 23, 0, 0, 0, time.Local)
	e.a.recordSession("Gothic", start, start.Add(2*time.Hour)) // 1 h on the 9th, 1 h on the 10th
	st, err := e.a.ComputeStats("2026-11-10", "2026-11-10", time.Local)
	if err != nil {
		t.Fatal(err)
	}
	if st.RangeTotal < 3599 || st.RangeTotal > 3601 || len(st.Days) != 1 {
		t.Fatalf("%+v", st)
	}
	st, _ = e.a.ComputeStats("2026-11-01", "2026-11-30", time.Local)
	if st.RangeTotal < 7199 || len(st.Days) != 30 {
		t.Fatalf("month: %v %d", st.RangeTotal, len(st.Days))
	}
	if _, err := e.a.ComputeStats("2026-11-30", "2026-11-01", time.Local); err == nil {
		t.Fatal("reversed range accepted")
	}
}

func TestRoadmapLateAndReminders(t *testing.T) {
	e := newEnv(t)
	e.a.checkRoadmap()
	v := e.a.roadmapView()
	if v.Current[0]["status"] != statusLate {
		t.Fatalf("%v", v.Current[0])
	}
	if _, err := e.a.remindersAdd(context.Background(), struct {
		When    string `json:"when"`
		Message string `json:"message"`
	}{e.clock.Add(time.Hour).Format("2006-01-02T15:04"), "Zagraj"}); err != nil {
		t.Fatal(err)
	}
	e.a.checkReminders()
	if e.host.has("reminder") {
		t.Fatal("fired too early")
	}
	e.clock = e.clock.Add(2 * time.Hour)
	e.a.checkReminders()
	if !e.host.has("reminder") {
		t.Fatal("reminder not fired")
	}
	if _, err := e.a.roadmapComplete(context.Background(), nameIn{Name: "Gothic"}); err != nil {
		t.Fatal(err)
	}
	if v := e.a.roadmapView(); len(v.Current) != 0 || len(v.Archive) != 1 {
		t.Fatal("not archived")
	}
}

func TestAchievements(t *testing.T) {
	e := newEnv(t)
	os.WriteFile(e.a.S.L.AchievDefFile, []byte(`[{"id":"first_launch","name":"Pierwsze Kroki","rule_type":"games_launched_count","target_value":1},
	{"id":"rpg","name":"RPG","rule_type":"genre_played_count","genre":"RPG","target_value":2},
	{"id":"lib","name":"Lib","rule_type":"library_size","target_value":1}]`), 0o644)
	got := e.a.achievements()
	byID := map[string]Achievement{}
	for _, x := range got {
		byID[x.ID] = x
	}
	if !byID["first_launch"].Unlocked || byID["rpg"].Unlocked || byID["rpg"].Progress != 1 || !byID["lib"].Unlocked {
		t.Fatalf("%+v", got)
	}
}

func TestSettingsNeverReturnSecrets(t *testing.T) {
	e := newEnv(t)
	b, _ := json.Marshal(e.a.Settings())
	c, _ := json.Marshal(e.a.chatArchive())
	for _, s := range []string{"SEKRET-123", "HASLO"} {
		if strings.Contains(string(b), s) || strings.Contains(string(c), s) {
			t.Fatalf("secret %s leaked to the UI", s)
		}
	}
	if e.a.Settings().Secrets["rawg_api_key"] != "plik" {
		t.Fatal("secret presence not reported")
	}
	if _, err := e.a.settingsSetSecret(context.Background(), struct {
		Key   string `json:"key"`
		Value string `json:"value"`
	}{"chat_servers", "x"}); err == nil {
		t.Fatal("arbitrary key accepted")
	}
}

func TestGroupsFiltersScanImport(t *testing.T) {
	e := newEnv(t)
	ctx := context.Background()
	if _, err := e.a.groupsSave(ctx, struct {
		Old  string `json:"old"`
		Name string `json:"name"`
	}{"", "RPG-i"}); err != nil {
		t.Fatal(err)
	}
	if _, err := e.a.groupsToggle(ctx, struct {
		Group string `json:"group"`
		Game  string `json:"game"`
		In    bool   `json:"in"`
	}{"RPG-i", "Gothic", true}); err != nil {
		t.Fatal(err)
	}
	m := e.a.filtersMeta()
	if len(m.Fields) == 0 {
		t.Fatal("no fields")
	}
	other := filepath.Join(e.dir, "Gry", "Teardown", "teardown.exe")
	os.MkdirAll(filepath.Dir(other), 0o755)
	os.WriteFile(other, []byte("MZ"), 0o644)
	e.a.settingsSave(ctx, settingsIn{ScanFolders: &[]string{filepath.Join(e.dir, "Gry")}})
	res, err := e.a.scanRun(ctx, empty{})
	if err != nil {
		t.Fatal(err)
	}
	cands := res.([]scanCandidate)
	if len(cands) != 1 || cands[0].Name != "Teardown" {
		t.Fatalf("%+v", cands)
	}
	r, err := e.a.scanImport(ctx, struct {
		Games []scanCandidate `json:"games"`
	}{cands})
	if err != nil || r.(map[string]any)["added"] != 1 {
		t.Fatal(r, err)
	}
}

func TestRelocate(t *testing.T) {
	e := newEnv(t)
	from := filepath.Join(e.dir, "Gry")
	n, err := e.a.gameRelocate(context.Background(), struct {
		From string `json:"from"`
		To   string `json:"to"`
	}{from, `Z:\Nowe`})
	if err != nil || n.(int) != 1 {
		t.Fatal(n, err)
	}
	if got := e.game(t).Str("exe_path"); got != `Z:\Nowe\Gothic\Gothic.exe` {
		t.Fatal(got)
	}
}
