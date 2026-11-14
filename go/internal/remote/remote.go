// Package remote is the web remote ("pilot WWW"): a phone/browser page that
// lists the library and launches or closes games.
//
// Security (same contract as the Python v1.5.0 remote, tightened):
//   - every request needs the token: header X-Remote-Token, ?token= on the
//     first visit (swapped for an HttpOnly SameSite=Strict cookie and removed
//     from the address bar) or the cookie;
//   - state changes only via POST, and a POST with a foreign Origin is refused;
//   - it listens on 127.0.0.1 unless LAN access is enabled explicitly;
//   - it uses its own port (default 5050), never the chat port (5000).
package remote

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	_ "embed"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

// Header / cookie names.
const (
	TokenHeader = "X-Remote-Token"
	TokenCookie = "gl_remote_token"
)

//go:embed remote.html
var indexHTML []byte

const unauthorizedHTML = `<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Game Launcher – pilot</title>
<style>body{font-family:system-ui,sans-serif;background:#14161b;color:#ddd;padding:24px;max-width:560px;margin:auto}</style></head>
<body><h1>Brak dostępu</h1><p>Otwórz pełny adres z tokenem, który widać w launcherze: <b>Ustawienia → Pilot WWW</b>.</p></body></html>`

// GenerateToken returns a random URL-safe token.
func GenerateToken() string {
	b := make([]byte, 24)
	_, _ = rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}

// BindHost returns the listen address host.
func BindHost(allowLAN bool) string {
	if allowLAN {
		return "0.0.0.0"
	}
	return "127.0.0.1"
}

// TokenMatches compares in constant time; empty never matches.
func TokenMatches(expected, provided string) bool {
	if expected == "" || provided == "" {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(expected), []byte(provided)) == 1
}

// Game is one library entry for the remote.
type Game struct {
	Name     string `json:"name"`
	Playtime string `json:"playtime"`
	CoverURL string `json:"cover_url"`
}

// Backend connects the remote with the launcher.
type Backend interface {
	Games() []Game
	Running() []string
	HasGame(name string) bool
	Launch(name string) error
	Close(name string) error
	CoverPath(name string) string // "" when none
}

// NewHandler builds the HTTP handler (exported for tests).
func NewHandler(token string, b Backend) (http.Handler, error) {
	if token == "" {
		return nil, errors.New("pilot WWW wymaga niepustego tokenu")
	}
	mux := http.NewServeMux()
	writeJSON := func(w http.ResponseWriter, code int, v any) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(code)
		_ = json.NewEncoder(w).Encode(v)
	}
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Has("token") {
			http.SetCookie(w, &http.Cookie{Name: TokenCookie, Value: token, Path: "/", HttpOnly: true, SameSite: http.SameSiteStrictMode, MaxAge: 30 * 24 * 3600})
			http.Redirect(w, r, "/", http.StatusFound)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
		_, _ = w.Write(indexHTML)
	})
	mux.HandleFunc("GET /api/games", func(w http.ResponseWriter, r *http.Request) {
		games := b.Games()
		for i := range games {
			games[i].CoverURL = "/cover/" + url.PathEscape(games[i].Name)
		}
		writeJSON(w, 200, games)
	})
	mux.HandleFunc("GET /api/status", func(w http.ResponseWriter, r *http.Request) {
		running := b.Running()
		var first any
		if len(running) > 0 {
			first = running[0]
		}
		writeJSON(w, 200, map[string]any{"running_game": first, "running": running})
	})
	action := func(kind string, fn func(string) error) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			name := r.PathValue("name")
			if !b.HasGame(name) {
				writeJSON(w, 404, map[string]string{"error": fmt.Sprintf("Nie znaleziono gry „%s” w bibliotece.", name)})
				return
			}
			if err := fn(name); err != nil {
				writeJSON(w, 409, map[string]string{"error": err.Error()})
				return
			}
			writeJSON(w, 200, map[string]any{"ok": true, "action": kind, "game": name})
		}
	}
	mux.HandleFunc("POST /api/launch/{name...}", action("launch", b.Launch))
	mux.HandleFunc("POST /api/close/{name...}", action("close", b.Close))
	mux.HandleFunc("GET /cover/{name...}", func(w http.ResponseWriter, r *http.Request) {
		p := b.CoverPath(r.PathValue("name"))
		if p == "" {
			http.NotFound(w, r)
			return
		}
		if st, err := os.Stat(p); err != nil || st.IsDir() {
			http.NotFound(w, r)
			return
		}
		http.ServeFile(w, r, p)
	})

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h := w.Header()
		h.Set("X-Content-Type-Options", "nosniff")
		h.Set("Referrer-Policy", "no-referrer")
		h.Set("Cache-Control", "no-store")
		h.Set("X-Frame-Options", "DENY")
		provided := r.Header.Get(TokenHeader)
		if provided == "" {
			provided = r.URL.Query().Get("token")
		}
		if provided == "" {
			if c, err := r.Cookie(TokenCookie); err == nil {
				provided = c.Value
			}
		}
		if !TokenMatches(token, provided) {
			if strings.HasPrefix(r.URL.Path, "/api/") {
				writeJSON(w, 401, map[string]string{"error": "Brak autoryzacji - nieprawidłowy token."})
				return
			}
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			w.WriteHeader(401)
			_, _ = w.Write([]byte(unauthorizedHTML))
			return
		}
		if r.Method == http.MethodPost {
			if o := r.Header.Get("Origin"); o != "" && o != "http://"+r.Host {
				writeJSON(w, 403, map[string]string{"error": "Niedozwolone źródło żądania."})
				return
			}
		}
		mux.ServeHTTP(w, r)
	}), nil
}

// Server is a running remote.
type Server struct {
	mu   sync.Mutex
	srv  *http.Server
	Addr string
}

// Start listens on host:port.
func Start(host string, port int, token string, b Backend) (*Server, error) {
	h, err := NewHandler(token, b)
	if err != nil {
		return nil, err
	}
	ln, err := net.Listen("tcp", net.JoinHostPort(host, fmt.Sprint(port)))
	if err != nil {
		return nil, fmt.Errorf("port %d jest zajęty albo niedostępny: %v", port, err)
	}
	s := &Server{Addr: ln.Addr().String(), srv: &http.Server{Handler: h, ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 16 << 10}}
	srv := s.srv
	go func() {
		if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Printf("[remote] %v", err)
		}
	}()
	return s, nil
}

// Stop shuts the server down (each Server owns its own http.Server, so a
// late stop of an old instance can never disable a new one).
func (s *Server) Stop() {
	if s == nil {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.srv != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		_ = s.srv.Shutdown(ctx)
		cancel()
		s.srv = nil
	}
}

// LANAddresses lists IPv4 addresses for showing the LAN URL.
func LANAddresses() []string {
	var out []string
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return nil
	}
	for _, a := range addrs {
		if ipn, ok := a.(*net.IPNet); ok && ipn.IP.To4() != nil && !ipn.IP.IsLoopback() && !ipn.IP.IsLinkLocalUnicast() {
			out = append(out, ipn.IP.String())
		}
	}
	return out
}
