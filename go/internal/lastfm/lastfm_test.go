package lastfm

import (
	"context"
	"image"
	"image/png"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func id3(frames map[string]string) []byte {
	var body []byte
	for id, v := range frames {
		data := append([]byte{3}, []byte(v)...)
		n := len(data)
		body = append(body, []byte(id)...)
		body = append(body, byte(n>>24), byte(n>>16), byte(n>>8), byte(n), 0, 0)
		body = append(body, data...)
	}
	s := len(body)
	hdr := []byte{'I', 'D', '3', 3, 0, 0, byte(s >> 21 & 0x7f), byte(s >> 14 & 0x7f), byte(s >> 7 & 0x7f), byte(s & 0x7f)}
	return append(hdr, body...)
}

func TestReadTags(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "x.mp3")
	os.WriteFile(p, id3(map[string]string{"TPE1": "DMX", "TIT2": "X Gon' Give It To Ya", "TALB": "Cradle 2 the Grave"}), 0o644)
	if tg := ReadTags(p); tg.Artist != "DMX" || tg.Album != "Cradle 2 the Grave" || tg.Title == "" {
		t.Fatalf("%+v", tg)
	}
	q := filepath.Join(dir, "07 ABBA - Gimme! Gimme! Gimme!.mp3")
	os.WriteFile(q, []byte("no tags"), 0o644)
	if tg := ReadTags(q); tg.Artist != "ABBA" || tg.Title != "Gimme! Gimme! Gimme!" {
		t.Fatalf("%+v", tg)
	}
}

func TestCover(t *testing.T) {
	var srv *httptest.Server
	srv = httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/img.png" {
			png.Encode(w, image.NewRGBA(image.Rect(0, 0, 2, 2)))
			return
		}
		if r.URL.Query().Get("api_key") != "K" {
			w.Write([]byte(`{"error":10,"message":"Invalid API key"}`))
			return
		}
		if r.URL.Query().Get("method") == "album.getinfo" {
			w.Write([]byte(`{"error":6,"message":"Album not found"}`))
			return
		}
		w.Write([]byte(`{"track":{"album":{"image":[{"#text":"` + srv.URL + `/small.png","size":"small"},{"#text":"` + srv.URL + `/img.png","size":"extralarge"}]}}}`))
	}))
	defer srv.Close()
	c := &Client{Key: "K", HTTP: srv.Client(), Base: srv.URL + "/2.0/"}
	tags := Tags{Artist: "ABBA", Title: "Gimme", Album: "X"}
	u, err := c.CoverURL(context.Background(), tags)
	if err != nil || !strings.HasSuffix(u, "/img.png") {
		t.Fatal(u, err)
	}
	dir := t.TempDir()
	name, err := c.Download(context.Background(), u, dir, tags)
	if err != nil || name != "lfm_cover_ABBA_X.png" {
		t.Fatal(name, err)
	}
	bad := &Client{Key: "zly", HTTP: srv.Client(), Base: srv.URL + "/2.0/"}
	if _, err := bad.CoverURL(context.Background(), tags); err == nil || strings.Contains(err.Error(), "zly") {
		t.Fatal(err)
	}
}
