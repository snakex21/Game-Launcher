package rawg

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFetchMapsFields(t *testing.T) {
	var srv *httptest.Server
	srv = httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.URL.Path, "/img/") && r.URL.Query().Get("key") != "K" {
			w.WriteHeader(401)
			return
		}
		switch r.URL.Path {
		case "/api/games":
			if r.URL.Query().Get("search") != "Stray" {
				w.Write([]byte(`{"results":[]}`))
				return
			}
			w.Write([]byte(`{"results":[{"id":42,"slug":"stray"}]}`))
		case "/api/games/42":
			w.Write([]byte(`{"name":"Stray","slug":"stray","description_raw":"Kot.","released":"2022-07-19","website":"https://x",
			"background_image":"` + srv.URL + `/img/a.jpg","developers":[{"name":"BlueTwelve"}],"publishers":[{"name":"Annapurna"}],
			"genres":[{"name":"Adventure"}],"tags":[{"name":"Cats"},{"name":""}],
			"platforms":[{"platform":{"name":"PC","slug":"pc"},"requirements":{"minimum":"min","recommended":"rec"}},{"platform":{"name":"PS5","slug":"ps5"}}]}`))
		case "/img/a.jpg":
			w.Header().Set("Content-Type", "image/jpeg")
			w.Write([]byte("JPEGDATA"))
		default:
			w.WriteHeader(404)
		}
	}))
	defer srv.Close()
	old := BaseURL
	BaseURL = srv.URL + "/api/games"
	defer func() { BaseURL = old }()

	c := &Client{HTTP: srv.Client(), Key: "K"}
	d, err := c.Fetch(context.Background(), "Stray")
	if err != nil {
		t.Fatal(err)
	}
	if d.ID != 42 || d.Slug != "stray" || d.Description != "Kot." || d.Released != "2022-07-19" ||
		strings.Join(d.Tags, ",") != "Cats" || strings.Join(d.Platforms, ",") != "PC,PS5" || d.RequirementsPC["recommended"] != "rec" {
		t.Fatalf("%+v", d)
	}
	dir := t.TempDir()
	rel, err := c.DownloadCover(context.Background(), `Stray: "Kot"`, d.BackgroundURL, dir)
	if err != nil {
		t.Fatal(err)
	}
	if rel != `images\Stray_ _Kot__rawg_cover.jpg` {
		t.Fatal(rel)
	}
	if b, _ := os.ReadFile(filepath.Join(dir, `Stray_ _Kot__rawg_cover.jpg`)); string(b) != "JPEGDATA" {
		t.Fatal("cover not written")
	}

	if _, err := c.Fetch(context.Background(), "Nic"); err != ErrNotFound {
		t.Fatal(err)
	}
	bad := &Client{HTTP: srv.Client(), Key: "zly"}
	if _, err := bad.Fetch(context.Background(), "Stray"); err == nil || strings.Contains(err.Error(), "zly") {
		t.Fatalf("bad key: %v", err)
	}
	if _, err := (&Client{}).Fetch(context.Background(), "x"); err == nil {
		t.Fatal("missing key accepted")
	}
	if _, err := c.DownloadCover(context.Background(), "x", "http://insecure/x.jpg", dir); err == nil {
		t.Fatal("http cover accepted")
	}
}
