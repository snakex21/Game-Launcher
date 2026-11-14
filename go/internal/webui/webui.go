// Package webui serves the embedded UI (web/) and the local media the UI
// shows (cover thumbnails, screenshots, music) to the WebView2 window from
// 127.0.0.1.
//
// There is no API here: the UI talks to Go through the webview binding.
// Guards (same as BenchForge's host):
//   - Host must be exactly 127.0.0.1:<port> (DNS rebinding);
//   - Origin, when present, must be ours; Sec-Fetch-Site same-origin/none;
//   - GET/HEAD only; a per-session token on the index request (?t=) is
//     swapped for an HttpOnly SameSite=Strict cookie required for everything;
//   - media are looked up by game name / track id through the app, never by
//     a path taken from the request;
//   - strict CSP: no remote scripts, styles, fonts, frames or connections.
package webui

import (
	"crypto/rand"
	"crypto/subtle"
	"embed"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

//go:embed web
var web embed.FS

// CSP for the UI.
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; " +
	"font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-src 'none'; " +
	"base-uri 'none'; form-action 'none'; frame-ancestors 'none'"

const cookieName = "gl_session"

// Media resolves media requests to files.
type Media interface {
	// CoverFile returns a file to serve for the game's cover at width w
	// (a cached thumbnail; "" = none).
	CoverFile(game string, w int) string
	// ScreenshotFile returns the i-th screenshot of a game ("" = none).
	ScreenshotFile(game string, i int, w int) string
	// TrackFile returns a music file by id ("" = none).
	TrackFile(id string) string
	// ChatFile returns a downloaded chat attachment ("" = none).
	ChatFile(name string) string
}

// Server is the running UI server.
type Server struct {
	URL    string // http://127.0.0.1:<port>/?t=<token>
	Origin string
	Token  string
	srv    *http.Server
}

// Assets returns the embedded UI.
func Assets() fs.FS {
	sub, err := fs.Sub(web, "web")
	if err != nil {
		panic(err)
	}
	return sub
}

func newToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// Start listens on 127.0.0.1:preferredPort (a stable origin keeps the
// WebView2 storage), falling back to a random port.
func Start(preferredPort int, media Media) (*Server, error) {
	var ln net.Listener
	var err error
	if preferredPort > 0 {
		ln, err = net.Listen("tcp", "127.0.0.1:"+strconv.Itoa(preferredPort))
	}
	if ln == nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			return nil, err
		}
	}
	token, err := newToken()
	if err != nil {
		ln.Close()
		return nil, err
	}
	port := ln.Addr().(*net.TCPAddr).Port
	s := &Server{Origin: fmt.Sprintf("http://127.0.0.1:%d", port), Token: token}
	s.URL = s.Origin + "/?t=" + token
	s.srv = &http.Server{Handler: Handler(Assets(), media, port, token), ReadHeaderTimeout: 5 * time.Second, IdleTimeout: 120 * time.Second, MaxHeaderBytes: 32 << 10}
	go func() {
		if err := s.srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Printf("[webui] %v", err)
		}
	}()
	return s, nil
}

// Close stops the server.
func (s *Server) Close() error {
	if s == nil || s.srv == nil {
		return nil
	}
	return s.srv.Close()
}

var (
	logMu   sync.Mutex
	lastLog = map[string]time.Time{}
)

// forbidden rejects a request; repeated rejections (e.g. a foreign page
// polling the port) are logged at most once a minute.
func forbidden(w http.ResponseWriter, r *http.Request, reason string) {
	key := reason + " " + r.URL.Path
	logMu.Lock()
	if time.Since(lastLog[key]) > time.Minute {
		lastLog[key] = time.Now()
		log.Printf("[webui][security] rejected %s %s: %s", r.Method, r.URL.Path, reason)
	}
	logMu.Unlock()
	http.Error(w, "Forbidden", http.StatusForbidden)
}

func serveFile(w http.ResponseWriter, r *http.Request, path string, cache string) {
	if path == "" {
		http.NotFound(w, r)
		return
	}
	f, err := os.Open(path)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Cache-Control", cache)
	http.ServeContent(w, r, st.Name(), st.ModTime(), f)
}

// Handler builds the guarded handler (exported for tests).
func Handler(assets fs.FS, media Media, port int, token string) http.Handler {
	host := fmt.Sprintf("127.0.0.1:%d", port)
	origin := "http://" + host
	files := http.FileServer(http.FS(assets))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Host != host {
			forbidden(w, r, "bad Host")
			return
		}
		if o := r.Header.Get("Origin"); o != "" && o != origin {
			forbidden(w, r, "foreign Origin")
			return
		}
		if sfs := r.Header.Get("Sec-Fetch-Site"); sfs != "" && sfs != "same-origin" && sfs != "none" {
			forbidden(w, r, "cross-site request")
			return
		}
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		authorized := false
		if c, err := r.Cookie(cookieName); err == nil && subtle.ConstantTimeCompare([]byte(c.Value), []byte(token)) == 1 {
			authorized = true
		}
		if t := r.URL.Query().Get("t"); t != "" && subtle.ConstantTimeCompare([]byte(t), []byte(token)) == 1 && (r.URL.Path == "/" || r.URL.Path == "/index.html") {
			http.SetCookie(w, &http.Cookie{Name: cookieName, Value: token, Path: "/", HttpOnly: true, SameSite: http.SameSiteStrictMode})
			authorized = true
		}
		if !authorized {
			forbidden(w, r, "missing session token")
			return
		}
		h := w.Header()
		h.Set("Content-Security-Policy", CSP)
		h.Set("X-Content-Type-Options", "nosniff")
		h.Set("X-Frame-Options", "DENY")
		h.Set("Referrer-Policy", "no-referrer")
		h.Set("Cross-Origin-Resource-Policy", "same-origin")
		q := r.URL.Query()
		width := func() int {
			n, _ := strconv.Atoi(q.Get("w"))
			if n < 64 || n > 1200 {
				n = 360
			}
			return n
		}
		switch {
		case r.URL.Path == "/media/cover":
			serveFile(w, r, media.CoverFile(q.Get("g"), width()), "private, max-age=300")
		case r.URL.Path == "/media/shot":
			i, err := strconv.Atoi(q.Get("i"))
			if err != nil {
				http.NotFound(w, r)
				return
			}
			serveFile(w, r, media.ScreenshotFile(q.Get("g"), i, width()), "private, max-age=300")
		case strings.HasPrefix(r.URL.Path, "/media/track/"):
			serveFile(w, r, media.TrackFile(strings.TrimPrefix(r.URL.Path, "/media/track/")), "private, no-cache")
		case strings.HasPrefix(r.URL.Path, "/media/chatfile/"):
			h.Set("Content-Security-Policy", "default-src 'none'; img-src 'self'")
			serveFile(w, r, media.ChatFile(strings.TrimPrefix(r.URL.Path, "/media/chatfile/")), "private, max-age=3600")
		case strings.HasPrefix(r.URL.Path, "/media/"):
			http.NotFound(w, r)
		default:
			h.Set("Cache-Control", "no-store")
			files.ServeHTTP(w, r)
		}
	})
}
