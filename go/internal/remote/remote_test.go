package remote

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

const token = "test-token-123"

type fake struct {
	mu    sync.Mutex
	calls []string
}

func (f *fake) Games() []Game {
	return []Game{{Name: "Gothic II", Playtime: "1 h"}, {Name: "Mafia", Playtime: "0 min"}}
}
func (f *fake) Running() []string       { return []string{"Mafia"} }
func (f *fake) HasGame(n string) bool   { return n == "Gothic II" || n == "Mafia" }
func (f *fake) CoverPath(string) string { return "" }
func (f *fake) Launch(n string) error   { f.add("launch:" + n); return nil }
func (f *fake) Close(n string) error    { f.add("close:" + n); return nil }
func (f *fake) add(s string)            { f.mu.Lock(); f.calls = append(f.calls, s); f.mu.Unlock() }

func do(t *testing.T, h http.Handler, method, path string, hdr map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, nil)
	for k, v := range hdr {
		req.Header.Set(k, v)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func setup(t *testing.T) (http.Handler, *fake) {
	f := &fake{}
	h, err := NewHandler(token, f)
	if err != nil {
		t.Fatal(err)
	}
	return h, f
}

func TestBasics(t *testing.T) {
	if BindHost(false) != "127.0.0.1" || BindHost(true) != "0.0.0.0" {
		t.Fatal("bind host")
	}
	if _, err := NewHandler("", &fake{}); err == nil {
		t.Fatal("empty token accepted")
	}
	if !TokenMatches("abc", "abc") || TokenMatches("abc", "abd") || TokenMatches("", "") || TokenMatches("abc", "") {
		t.Fatal("TokenMatches")
	}
	if a, b := GenerateToken(), GenerateToken(); a == b || len(a) < 30 {
		t.Fatal("token generation")
	}
}

func TestRejectsWithoutOrWrongToken(t *testing.T) {
	h, f := setup(t)
	for _, p := range []string{"/", "/api/games", "/api/status", "/cover/Mafia"} {
		if c := do(t, h, "GET", p, nil).Code; c != 401 {
			t.Errorf("%s: %d", p, c)
		}
	}
	if do(t, h, "GET", "/api/games", map[string]string{TokenHeader: "zly"}).Code != 401 ||
		do(t, h, "POST", "/api/launch/Mafia", map[string]string{TokenHeader: "zly"}).Code != 401 ||
		do(t, h, "GET", "/?token=zly", nil).Code != 401 {
		t.Fatal("wrong token accepted")
	}
	if len(f.calls) != 0 {
		t.Fatal(f.calls)
	}
}

func TestGamesAndActions(t *testing.T) {
	h, f := setup(t)
	auth := map[string]string{TokenHeader: token}
	rec := do(t, h, "GET", "/api/games", auth)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), `"cover_url":"/cover/Gothic%20II"`) {
		t.Fatal(rec.Code, rec.Body.String())
	}
	if c := do(t, h, "GET", "/api/launch/Mafia", auth).Code; c != 405 {
		t.Fatalf("GET launch: %d", c)
	}
	if do(t, h, "POST", "/api/launch/Gothic%20II", auth).Code != 200 || do(t, h, "POST", "/api/close/Mafia", auth).Code != 200 {
		t.Fatal("actions failed")
	}
	rec = do(t, h, "POST", "/api/launch/Nieznana", auth)
	if rec.Code != 404 || !strings.Contains(rec.Body.String(), "Nieznana") {
		t.Fatal(rec.Code)
	}
	if strings.Join(f.calls, ",") != "launch:Gothic II,close:Mafia" {
		t.Fatal(f.calls)
	}
	// cross-site POST with a valid cookie is refused
	req := httptest.NewRequest("POST", "/api/launch/Mafia", nil)
	req.AddCookie(&http.Cookie{Name: TokenCookie, Value: token})
	req.Header.Set("Origin", "http://evil.example")
	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != 403 {
		t.Fatal("foreign origin accepted", rec.Code)
	}
}

func TestQueryTokenSetsCookieAndStripsURL(t *testing.T) {
	h, _ := setup(t)
	rec := do(t, h, "GET", "/?token="+token, nil)
	if rec.Code != 302 || rec.Header().Get("Location") != "/" {
		t.Fatal(rec.Code, rec.Header())
	}
	sc := rec.Header().Get("Set-Cookie")
	if !strings.Contains(sc, TokenCookie) || !strings.Contains(sc, "HttpOnly") || !strings.Contains(sc, "SameSite=Strict") {
		t.Fatal(sc)
	}
	req := httptest.NewRequest("GET", "/", nil)
	req.AddCookie(&http.Cookie{Name: TokenCookie, Value: token})
	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Game Launcher") || strings.Contains(rec.Body.String(), token) {
		t.Fatal("index page wrong or leaks the token")
	}
}

func TestStartStop(t *testing.T) {
	s, err := Start("127.0.0.1", 0, token, &fake{})
	if err != nil {
		t.Fatal(err)
	}
	resp, err := http.Get("http://" + s.Addr + "/api/status?token=" + token)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatal(resp.StatusCode)
	}
	s.Stop()
	s.Stop()
}
