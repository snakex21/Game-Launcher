package webui

import (
	"io/fs"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type media struct{ cover string }

func (m media) CoverFile(g string, w int) string {
	if g == "Gothic" {
		return m.cover
	}
	return ""
}
func (media) ScreenshotFile(string, int, int) string { return "" }
func (media) TrackFile(string) string                { return "" }
func (media) ChatFile(string) string                 { return "" }
func (media) TrackCoverFile(string, int) string      { return "" }

const port = 47999

func req(t *testing.T, h http.Handler, path string, mod func(*http.Request)) *httptest.ResponseRecorder {
	r := httptest.NewRequest("GET", path, nil)
	r.Host = "127.0.0.1:47999"
	if mod != nil {
		mod(r)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestAssetsEmbedded(t *testing.T) {
	for _, f := range []string{"index.html", "app.js", "app.css", "icon.svg"} {
		if _, err := fs.Stat(Assets(), f); err != nil {
			t.Fatalf("%s missing: %v", f, err)
		}
	}
	b, _ := fs.ReadFile(Assets(), "app.js")
	if strings.Contains(string(b), ".innerHTML") {
		t.Fatal("UI must not use innerHTML (user data goes through textContent)")
	}
}

func TestGuards(t *testing.T) {
	dir := t.TempDir()
	cover := filepath.Join(dir, "c.jpg")
	os.WriteFile(cover, []byte("JPG"), 0o644)
	h := Handler(Assets(), media{cover}, port, "tok")
	cookie := func(r *http.Request) { r.AddCookie(&http.Cookie{Name: cookieName, Value: "tok"}) }

	if w := req(t, h, "/", nil); w.Code != 403 {
		t.Fatal("no token accepted", w.Code)
	}
	w := req(t, h, "/?t=tok", nil)
	if w.Code != 200 || !strings.Contains(w.Header().Get("Set-Cookie"), "HttpOnly") || !strings.Contains(w.Header().Get("Content-Security-Policy"), "default-src 'self'") {
		t.Fatal("index with token", w.Code, w.Header())
	}
	if w := req(t, h, "/app.js?t=tok", nil); w.Code != 403 {
		t.Fatal("token accepted outside the index")
	}
	if w := req(t, h, "/app.js", cookie); w.Code != 200 {
		t.Fatal("asset with cookie", w.Code)
	}
	if w := req(t, h, "/app.js", func(r *http.Request) { cookie(r); r.Host = "evil.example:47999" }); w.Code != 403 {
		t.Fatal("bad host accepted")
	}
	if w := req(t, h, "/app.js", func(r *http.Request) { cookie(r); r.Header.Set("Origin", "http://evil.example") }); w.Code != 403 {
		t.Fatal("foreign origin accepted")
	}
	if w := req(t, h, "/app.js", func(r *http.Request) { cookie(r); r.Header.Set("Sec-Fetch-Site", "cross-site") }); w.Code != 403 {
		t.Fatal("cross-site accepted")
	}
	if w := req(t, h, "/media/cover?g=Gothic&w=300", cookie); w.Code != 200 || w.Body.String() != "JPG" {
		t.Fatal("cover", w.Code)
	}
	if w := req(t, h, "/media/cover?g=..%2F..%2Fwindows", cookie); w.Code != 404 {
		t.Fatal("unknown cover served", w.Code)
	}
	if w := req(t, h, "/media/track/abc", cookie); w.Code != 404 {
		t.Fatal("unknown track served")
	}
	r := httptest.NewRequest("POST", "/", nil)
	r.Host = "127.0.0.1:47999"
	cookie(r)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, r)
	if rec.Code != 405 {
		t.Fatal("POST accepted")
	}
}
