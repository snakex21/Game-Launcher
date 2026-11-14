// Package store reads and writes the launcher's existing data files:
//
//	data/config/config.json          library, settings, user, roadmap ...
//	data/config/local_settings.json  per-machine settings and secrets
//
// The format is the one written by the Python launcher (v1.5.0): key order,
// unknown keys and number formatting are preserved (see package ojson), the
// same defaults/migrations as launcher/config_store.py are applied, and game
// paths are stored in their portable form (see package paths).
//
// Secrets (RAWG / Last.fm / GitHub tokens, chat passwords) are never logged;
// values from GL_* environment variables override the file but are never
// written back to it.
package store

import (
	"errors"
	"fmt"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
	"github.com/snakex21/game-launcher/go/internal/secrets"
)

// ProgramVersion is the data format version written to config.json.
const ProgramVersion = "1.5.0"

// Ports: the chat server and the web remote must differ.
const (
	DefaultChatServerPort    = 5000
	DefaultRemoteControlPort = 5050
)

// SecretEnvVars maps local_settings keys to environment overrides.
var SecretEnvVars = map[string]string{
	"github_token":         "GL_GITHUB_TOKEN",
	"rawg_api_key":         "GL_RAWG_API_KEY",
	"lastfm_api_key":       "GL_LASTFM_API_KEY",
	"remote_control_token": "GL_REMOTE_TOKEN",
}

// Layout lists the data locations inside the app folder.
type Layout struct {
	AppDir        string
	DataDir       string
	ConfigDir     string
	ConfigFile    string
	LocalFile     string
	AchievDefFile string
	ChatDB        string
	GamesSaves    string
	ImagesDir     string
	CacheDir      string
	MusicDir      string
}

// NewLayout builds the layout for an app folder.
func NewLayout(appDir string) Layout {
	data := filepath.Join(appDir, "data")
	cfg := filepath.Join(data, "config")
	return Layout{
		AppDir:        appDir,
		DataDir:       data,
		ConfigDir:     cfg,
		ConfigFile:    filepath.Join(cfg, "config.json"),
		LocalFile:     filepath.Join(cfg, "local_settings.json"),
		AchievDefFile: filepath.Join(cfg, "achievements_def.json"),
		ChatDB:        filepath.Join(data, "chat", "chat.db"),
		GamesSaves:    filepath.Join(data, "games_saves"),
		ImagesDir:     filepath.Join(appDir, "images"),
		CacheDir:      filepath.Join(data, "go_cache"),
		MusicDir:      filepath.Join(appDir, "internal_music"),
	}
}

// Store owns both files. All access goes through its methods (goroutine safe).
type Store struct {
	L Layout

	mu          sync.Mutex
	cfg         *ojson.Object
	cfgStyle    ojson.Style
	local       *ojson.Object
	localStyle  ojson.Style
	envOverride map[string][2]any // key -> {file value, env value}
	backedUp    map[string]bool
	Remapped    int // paths remapped after a drive letter change (last load)
	Warnings    []string
	getenv      func(string) string
}

// Open loads (or creates in memory) both files.
func Open(appDir string) (*Store, error) {
	s := &Store{L: NewLayout(appDir), backedUp: map[string]bool{}, getenv: os.Getenv}
	if err := s.Load(); err != nil {
		return nil, err
	}
	return s, nil
}

// Load (re)reads both files.
func (s *Store) Load() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Warnings = nil
	s.migrateLegacyFile("config.json", s.L.ConfigFile)
	s.migrateLegacyDir("games_saves", s.L.GamesSaves)
	s.migrateLegacyFile("local_settings.json", s.L.LocalFile)

	cfg, style, err := s.readObject(s.L.ConfigFile)
	if err != nil {
		return err
	}
	if cfg == nil {
		cfg = defaultConfig()
	}
	s.cfgStyle = style
	s.Remapped = applyConfigDefaults(cfg, s.L.AppDir)
	if s.Remapped > 0 {
		log.Printf("[store] launcher drive changed - remapped %d game paths", s.Remapped)
	}
	s.cfg = cfg

	local, lstyle, err := s.readObject(s.L.LocalFile)
	if err != nil {
		return err
	}
	if local == nil {
		local = ojson.NewObject()
	}
	s.localStyle = lstyle
	applyLocalDefaults(local)
	migrated := protectPlainSecrets(local)
	s.envOverride = applySecretEnv(local, s.getenv)
	s.local = local
	if migrated > 0 {
		// Plaintext secrets from the Python version: write them back
		// encrypted right away (DPAPI) instead of keeping them readable.
		if err := s.saveLocalLocked(); err != nil {
			log.Printf("[store] could not re-save protected secrets: %v", err)
		} else {
			log.Printf("[store] %d secret value(s) moved to DPAPI", migrated)
		}
	}
	return nil
}

// readObject reads a JSON object file. A missing file gives (nil, nil). A
// broken file is kept aside (never overwritten) and defaults are used.
func (s *Store) readObject(path string) (*ojson.Object, ojson.Style, error) {
	raw, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, ojson.Style{}, nil
	}
	if err != nil {
		return nil, ojson.Style{}, fmt.Errorf("odczyt %s: %w", path, err)
	}
	o, err := ojson.DecodeObject(raw)
	if err != nil {
		broken := path + ".broken-" + time.Now().Format("20060102-150405")
		_ = os.WriteFile(broken, raw, 0o600)
		msg := fmt.Sprintf("Plik %s jest uszkodzony (%v). Kopia: %s. Używam wartości domyślnych.", filepath.Base(path), err, filepath.Base(broken))
		log.Printf("[store] %s", msg)
		s.Warnings = append(s.Warnings, msg)
		return nil, ojson.Style{}, nil
	}
	return o, ojson.DetectStyle(raw), nil
}

func (s *Store) migrateLegacyFile(name, target string) {
	if paths.Exists(target) {
		return
	}
	legacy := filepath.Join(s.L.AppDir, name)
	if !paths.Exists(legacy) {
		return
	}
	_ = os.MkdirAll(filepath.Dir(target), 0o755)
	if err := os.Rename(legacy, target); err != nil {
		log.Printf("[store] could not move legacy %s: %v", name, err)
	}
}

func (s *Store) migrateLegacyDir(name, target string) {
	if paths.Exists(target) {
		return
	}
	legacy := filepath.Join(s.L.AppDir, name)
	if st, err := os.Stat(legacy); err != nil || !st.IsDir() {
		return
	}
	_ = os.MkdirAll(filepath.Dir(target), 0o755)
	if err := os.Rename(legacy, target); err != nil {
		log.Printf("[store] could not move legacy folder %s: %v", name, err)
	}
}

func defaultConfig() *ojson.Object {
	o := ojson.NewObject()
	o.Set("version", ProgramVersion)
	o.Set("games", ojson.NewObject())
	o.Set("settings", ojson.NewObject())
	o.Set("groups", ojson.NewObject())
	o.Set("user", ojson.NewObject())
	o.Set("emulators", ojson.NewObject())
	o.Set("saved_filters", ojson.NewObject())
	return o
}

func strList(items ...string) []any {
	out := make([]any, len(items))
	for i, s := range items {
		out[i] = s
	}
	return out
}

// versionLess compares dotted versions numerically ("1.4.10" < "1.5.0").
func versionLess(a, b string) bool {
	pa, pb := strings.Split(a, "."), strings.Split(b, ".")
	for i := 0; i < len(pa) || i < len(pb); i++ {
		var x, y int
		if i < len(pa) {
			fmt.Sscanf(pa[i], "%d", &x)
		}
		if i < len(pb) {
			fmt.Sscanf(pb[i], "%d", &y)
		}
		if x != y {
			return x < y
		}
	}
	return false
}

func newDefaultProfile() *ojson.Object {
	p := ojson.NewObject()
	p.Set("name", "Default")
	p.Set("exe_path", nil)
	p.Set("arguments", "")
	return p
}

// applyConfigDefaults ports load_config(): defaults, launch profile repair
// and path resolution. Returns the number of remapped paths.
func applyConfigDefaults(data *ojson.Object, appDir string) int {
	data.SetDefault("version", "0.0.0")
	if versionLess(data.Str("version"), ProgramVersion) {
		data.Set("version", ProgramVersion)
	}
	settings := data.EnsureObj("settings")

	feeds, ok := settings.Get("rss_feeds").([]any)
	if !ok {
		f := ojson.NewObject()
		f.Set("url", "https://feeds.ign.com/ign/games-all")
		f.Set("active", true)
		f.Set("name", "IGN Games")
		settings.Set("rss_feeds", []any{f})
	} else {
		changed := false
		for i, feed := range feeds {
			if fo, ok := feed.(*ojson.Object); ok && fo.Has("url") {
				continue
			}
			str := fmt.Sprint(feed)
			if fs, ok := feed.(string); ok {
				str = fs
			}
			f := ojson.NewObject()
			f.Set("url", str)
			f.Set("active", true)
			f.Set("name", str)
			feeds[i] = f
			changed = true
		}
		if changed {
			settings.Set("rss_feeds", feeds)
		}
	}
	settings.SetDefault("news_post_limit", 10)
	settings.SetDefault("scan_ignore_folders", strList("_CommonRedist", "DirectX", "DotNet", "Redist", "Tools", "Benchmark", "support", "data", "__overlay"))
	settings.SetDefault("scan_recursively", true)
	settings.SetDefault("autoscan_screenshot_folders", []any{})
	settings.SetDefault("autoscan_on_startup", false)
	settings.SetDefault("screenshot_scan_ignore_folders", strList("thumb_cache", "cache", "temp", "thumbnails"))
	settings.SetDefault("screenshot_filename_patterns", strList("{game_name}*.png", "{game_name}*.jpg", "{game_name}*.jpeg"))

	if games := data.Obj("games"); games != nil {
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				log.Printf("[store] invalid game entry %q - skipped", name)
				continue
			}
			repairProfiles(g)
			g.SetDefault("screenshots", []any{})
			g.SetDefault("autoscan_screenshots", []any{})
			g.SetDefault("checklist", []any{})
		}
	} else {
		data.Set("games", ojson.NewObject())
	}
	data.SetDefault("emulators", ojson.NewObject())
	data.SetDefault("saved_filters", ojson.NewObject())
	data.EnsureObj("user").SetDefault("achievements", ojson.NewObject())
	return paths.ResolveConfig(data, appDir)
}

// repairProfiles: the "Default" profile always exists and comes first.
func repairProfiles(g *ojson.Object) {
	profiles, ok := g.Get("launch_profiles").([]any)
	if !ok || len(profiles) == 0 {
		g.Set("launch_profiles", []any{newDefaultProfile()})
		return
	}
	for i, p := range profiles {
		po, ok := p.(*ojson.Object)
		if !ok || !strings.EqualFold(po.Str("name"), "default") {
			continue
		}
		if i == 0 {
			return
		}
		out := append([]any{po}, append(append([]any{}, profiles[:i]...), profiles[i+1:]...)...)
		g.Set("launch_profiles", out)
		return
	}
	g.Set("launch_profiles", append([]any{newDefaultProfile()}, profiles...))
}

func applyLocalDefaults(d *ojson.Object) {
	// Single-server chat settings of old versions -> chat_servers list.
	oldURL, _ := d.Get("chat_server_url").(string)
	oldEmail, _ := d.Get("chat_email").(string)
	oldPass := d.Get("chat_password")
	oldRemember := d.Bool("chat_remember_me", false)
	oldAuto := d.Bool("chat_auto_login", false)
	for _, k := range []string{"chat_server_url", "chat_email", "chat_password", "chat_remember_me", "chat_auto_login"} {
		d.Delete(k)
	}
	servers, ok := d.Get("chat_servers").([]any)
	if !ok {
		servers = []any{}
		d.Set("chat_servers", servers)
	}
	if oldURL != "" && len(servers) == 0 {
		id := newUUID()
		e := ojson.NewObject()
		e.Set("id", id)
		e.Set("name", "Domyslny Serwer (migr.)")
		e.Set("url", oldURL)
		e.Set("is_default", true)
		e.Set("last_used", ojson.Float(float64(time.Now().UnixNano())/1e9))
		cred := ojson.NewObject()
		if oldRemember && oldEmail != "" {
			cred.Set("email", oldEmail)
			cred.Set("password", oldPass)
		}
		e.Set("credentials", cred)
		e.Set("remember_credentials", oldRemember)
		e.Set("auto_login_to_server", oldAuto && oldRemember)
		servers = append(servers, e)
		d.Set("chat_servers", servers)
		d.Set("active_chat_server_id", id)
	}
	if len(servers) == 0 {
		id := newUUID()
		e := ojson.NewObject()
		e.Set("id", id)
		e.Set("name", "Serwer Lokalny (Domyslny)")
		e.Set("url", fmt.Sprintf("http://127.0.0.1:%d", DefaultChatServerPort))
		e.Set("is_default", true)
		e.Set("last_used", nil)
		e.Set("credentials", ojson.NewObject())
		e.Set("remember_credentials", false)
		e.Set("auto_login_to_server", false)
		servers = []any{e}
		d.Set("chat_servers", servers)
		d.Set("active_chat_server_id", id)
	}
	if !d.Has("active_chat_server_id") {
		id := ""
		for _, sv := range servers {
			if so, ok := sv.(*ojson.Object); ok && so.Bool("is_default", false) {
				id = so.Str("id")
				break
			}
		}
		if id == "" {
			if so, ok := servers[0].(*ojson.Object); ok {
				id = so.Str("id")
			}
		}
		d.Set("active_chat_server_id", id)
	}

	d.SetDefault("chat_auto_connect_to_default", true)
	d.SetDefault("remote_control_enabled", false)
	d.SetDefault("remote_control_port", DefaultRemoteControlPort)
	if d.Int("remote_control_port", 0) == DefaultChatServerPort {
		d.Set("remote_control_port", DefaultRemoteControlPort) // until v1.4 the remote shared the chat port
	}
	d.SetDefault("remote_control_bind_lan", false)
	d.SetDefault("window_state", "normal")
	d.SetDefault("window_geometry", "1024x768+100+100")
	d.SetDefault("library_view_mode", "tiles")
	d.SetDefault("tiles_per_row", 3)
	d.SetDefault("discord_rpc_enabled", false)
	d.SetDefault("discord_status_text", "Korzysta z Game Launcher")
	d.SetDefault("ui_font", "Segoe UI")
	d.SetDefault("window_maximized", false)
	d.SetDefault("last_run_date", "")
	d.SetDefault("consecutive_days", 0)
	d.SetDefault("total_launcher_usage_seconds", 0)
	d.SetDefault("avatar_display_size", 48)
	d.SetDefault("music_player_volume", ojson.Float(0.5))
	d.SetDefault("music_repeat_mode", "none")
	d.SetDefault("music_shuffle_mode", false)
	d.SetDefault("music_favorite_tracks", []any{})
	d.SetDefault("named_music_playlists", ojson.NewObject())
	d.SetDefault("launcher_daily_usage_seconds", ojson.NewObject())
	d.SetDefault("show_track_overlay", false)
}

// protectPlainSecrets encrypts plaintext secrets (API keys, tokens, chat
// passwords) in place and returns how many were changed.
func protectPlainSecrets(d *ojson.Object) int {
	n := 0
	enc := func(o *ojson.Object, key string) {
		v, ok := o.Get(key).(string)
		if !ok || v == "" || secrets.IsProtected(v) {
			return
		}
		p, err := secrets.Protect(v)
		if err != nil {
			return
		}
		o.Set(key, p)
		n++
	}
	for key := range SecretEnvVars {
		enc(d, key)
	}
	for _, sv := range d.Arr("chat_servers") {
		if so, ok := sv.(*ojson.Object); ok {
			if c := so.Obj("credentials"); c != nil {
				enc(c, "password")
			}
		}
	}
	return n
}

func applySecretEnv(d *ojson.Object, getenv func(string) string) map[string][2]any {
	over := map[string][2]any{}
	for key, env := range SecretEnvVars {
		v := strings.TrimSpace(getenv(env))
		if v == "" {
			continue
		}
		cur, _ := d.Lookup(key)
		over[key] = [2]any{cur, v}
		d.Set(key, v)
	}
	return over
}

// --------------------------------------------------------------- saving

// writeAtomic writes via a temp file + rename; the first write of a session
// keeps a .bak copy of the previous file.
func (s *Store) writeAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	if !s.backedUp[path] {
		if old, err := os.ReadFile(path); err == nil {
			_ = os.WriteFile(path+".bak", old, 0o600)
		}
		s.backedUp[path] = true
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), filepath.Base(path)+".tmp-*")
	if err != nil {
		return err
	}
	name := tmp.Name()
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		os.Remove(name)
		return err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		os.Remove(name)
		return err
	}
	if err := tmp.Close(); err != nil {
		os.Remove(name)
		return err
	}
	if err := os.Rename(name, path); err != nil {
		os.Remove(name)
		return err
	}
	return nil
}

// ConfigBytes renders config.json as it would be written (portable paths,
// no settings.github_token).
func (s *Store) configBytes() []byte {
	c := paths.MakePortable(s.cfg, s.L.AppDir)
	c.EnsureObj("settings").Delete("github_token")
	return s.cfgStyle.Apply(ojson.MarshalPython(c))
}

func (s *Store) saveConfigLocked() error {
	return s.writeAtomic(s.L.ConfigFile, s.configBytes())
}

func (s *Store) localBytes() []byte {
	c := s.local.Clone()
	for key, pair := range s.envOverride {
		if v, ok := c.Get(key).(string); ok && v == pair[1] {
			if pair[0] == nil {
				c.Delete(key)
			} else {
				c.Set(key, pair[0])
			}
		}
	}
	return s.localStyle.Apply(ojson.MarshalPython(c))
}

func (s *Store) saveLocalLocked() error {
	return s.writeAtomic(s.L.LocalFile, s.localBytes())
}

// UpdateConfig runs fn on config.json under the lock and saves when fn
// returns nil.
func (s *Store) UpdateConfig(fn func(cfg *ojson.Object) error) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := fn(s.cfg); err != nil {
		return err
	}
	return s.saveConfigLocked()
}

// UpdateLocal runs fn on local_settings.json under the lock and saves.
func (s *Store) UpdateLocal(fn func(local *ojson.Object) error) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := fn(s.local); err != nil {
		return err
	}
	return s.saveLocalLocked()
}

// ReadConfig runs fn with read access to config.json.
func (s *Store) ReadConfig(fn func(cfg *ojson.Object)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	fn(s.cfg)
}

// ReadLocal runs fn with read access to local_settings.json. fn must never
// log or return secret values (see Redact).
func (s *Store) ReadLocal(fn func(local *ojson.Object)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	fn(s.local)
}

// Secret returns a secret value in plaintext (env override first). Callers
// use it for API calls only, never for logs or the UI. A value that cannot
// be decrypted (other PC/account) reads as "".
func (s *Store) Secret(key string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, err := secrets.Reveal(strings.TrimSpace(s.local.Str(key)))
	if err != nil {
		return ""
	}
	return v
}

// SecretState is "", "plik", "zmienna" or "nieczytelny".
func (s *Store) SecretState(key string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.envOverride[key]; ok {
		return "zmienna"
	}
	v := s.local.Str(key)
	if v == "" {
		return ""
	}
	if _, err := secrets.Reveal(v); err != nil {
		return "nieczytelny"
	}
	return "plik"
}

// SetSecret stores a secret encrypted with DPAPI ("" clears it).
func (s *Store) SetSecret(key, plain string) error {
	enc, err := secrets.Protect(plain)
	if err != nil {
		return err
	}
	return s.UpdateLocal(func(l *ojson.Object) error { l.Set(key, enc); return nil })
}

// ProtectValue encrypts a value for storing in local_settings.
func ProtectValue(plain string) (string, error) { return secrets.Protect(plain) }

// RevealValue decrypts a stored value.
func RevealValue(stored string) (string, error) { return secrets.Reveal(stored) }

// SecretFromEnv reports whether key comes from an environment variable.
func (s *Store) SecretFromEnv(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, ok := s.envOverride[key]
	return ok
}

// IsSecretKey reports keys whose values must never leave the process.
func IsSecretKey(key string) bool {
	if _, ok := SecretEnvVars[key]; ok {
		return true
	}
	k := strings.ToLower(key)
	return strings.Contains(k, "password") || strings.Contains(k, "token") || strings.Contains(k, "credentials") || strings.HasSuffix(k, "_key")
}

// Redact returns a copy safe for logs/UI: secret values become "***".
func Redact(v any) any {
	switch x := v.(type) {
	case *ojson.Object:
		out := ojson.NewObject()
		for _, k := range x.Keys() {
			val := x.Get(k)
			if IsSecretKey(k) {
				if val == nil || val == "" {
					out.Set(k, val)
				} else if o, ok := val.(*ojson.Object); ok && o.Len() == 0 {
					out.Set(k, o)
				} else {
					out.Set(k, "***")
				}
				continue
			}
			out.Set(k, Redact(val))
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = Redact(e)
		}
		return out
	}
	return v
}
