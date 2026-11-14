// Package lastfm fetches album covers for music files from Last.fm
// (track.getInfo / album.getInfo). Artist/title/album come from ID3v2 tags
// or, without tags, from an "Artist - Title" file name.
package lastfm

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode/utf16"
)

// API endpoint (tests use a fake).
var API = "https://ws.audioscrobbler.com/2.0/"

// Tags of a track.
type Tags struct{ Artist, Title, Album string }

// ReadTags reads ID3v2.3/2.4 TPE1/TIT2/TALB; falls back to the file name.
func ReadTags(path string) Tags {
	t := readID3(path)
	if t.Artist == "" || t.Title == "" {
		base := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
		base = regexp.MustCompile(`^\d+[_. -]+`).ReplaceAllString(base, "")
		if i := strings.Index(base, " - "); i > 0 {
			if t.Artist == "" {
				t.Artist = strings.TrimSpace(base[:i])
			}
			if t.Title == "" {
				t.Title = strings.TrimSpace(base[i+3:])
			}
		}
	}
	return t
}

func readID3(path string) Tags {
	var t Tags
	f, err := os.Open(path)
	if err != nil {
		return t
	}
	defer f.Close()
	hdr := make([]byte, 10)
	if _, err := io.ReadFull(f, hdr); err != nil || string(hdr[:3]) != "ID3" {
		return t
	}
	ver := hdr[3]
	size := int(hdr[6]&0x7f)<<21 | int(hdr[7]&0x7f)<<14 | int(hdr[8]&0x7f)<<7 | int(hdr[9]&0x7f)
	if size > 4<<20 || (ver != 3 && ver != 4) {
		return t
	}
	data := make([]byte, size)
	if _, err := io.ReadFull(f, data); err != nil {
		return t
	}
	for i := 0; i+10 <= len(data); {
		id := string(data[i : i+4])
		if id[0] == 0 {
			break
		}
		var fs int
		if ver == 4 {
			fs = int(data[i+4]&0x7f)<<21 | int(data[i+5]&0x7f)<<14 | int(data[i+6]&0x7f)<<7 | int(data[i+7]&0x7f)
		} else {
			fs = int(binary.BigEndian.Uint32(data[i+4 : i+8]))
		}
		if fs <= 0 || i+10+fs > len(data) {
			break
		}
		body := data[i+10 : i+10+fs]
		switch id {
		case "TPE1":
			t.Artist = textFrame(body)
		case "TIT2":
			t.Title = textFrame(body)
		case "TALB":
			t.Album = textFrame(body)
		}
		i += 10 + fs
	}
	return t
}

func textFrame(b []byte) string {
	if len(b) < 2 {
		return ""
	}
	enc, b := b[0], b[1:]
	var s string
	switch enc {
	case 1, 2: // UTF-16 (with BOM) / UTF-16BE
		be := enc == 2
		if len(b) >= 2 && b[0] == 0xFE && b[1] == 0xFF {
			be, b = true, b[2:]
		} else if len(b) >= 2 && b[0] == 0xFF && b[1] == 0xFE {
			be, b = false, b[2:]
		}
		u := make([]uint16, 0, len(b)/2)
		for i := 0; i+1 < len(b); i += 2 {
			if be {
				u = append(u, uint16(b[i])<<8|uint16(b[i+1]))
			} else {
				u = append(u, uint16(b[i+1])<<8|uint16(b[i]))
			}
		}
		s = string(utf16.Decode(u))
	case 3:
		s = string(b)
	default: // ISO-8859-1
		r := make([]rune, len(b))
		for i, c := range b {
			r[i] = rune(c)
		}
		s = string(r)
	}
	if i := strings.IndexRune(s, 0); i >= 0 {
		s = s[:i]
	}
	return strings.TrimSpace(s)
}

// Client calls Last.fm.
type Client struct {
	Key  string
	HTTP *http.Client
	Base string
}

type lfmImage struct {
	URL  string `json:"#text"`
	Size string `json:"size"`
}

func best(imgs []lfmImage) string {
	order := map[string]int{"small": 1, "medium": 2, "large": 3, "extralarge": 4, "mega": 5}
	b, bs := "", 0
	for _, im := range imgs {
		if im.URL != "" && order[im.Size] >= bs {
			b, bs = im.URL, order[im.Size]
		}
	}
	return b
}

func (c *Client) call(ctx context.Context, q url.Values, out any) error {
	if c.Key == "" {
		return errors.New("brak klucza Last.fm – dodaj go w Ustawieniach → Klucze API")
	}
	q.Set("api_key", c.Key)
	q.Set("format", "json")
	base := c.Base
	if base == "" {
		base = API
	}
	req, err := http.NewRequestWithContext(ctx, "GET", base+"?"+q.Encode(), nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "GameLauncher-Go")
	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: 15 * time.Second}
	}
	resp, err := hc.Do(req)
	if err != nil {
		var ue *url.Error
		if errors.As(err, &ue) {
			err = ue.Err // never print the URL (it holds the key)
		}
		return fmt.Errorf("Last.fm: %v", err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
	var e struct {
		Error   int    `json:"error"`
		Message string `json:"message"`
	}
	if json.Unmarshal(b, &e) == nil && e.Error != 0 {
		return fmt.Errorf("Last.fm: %s", e.Message)
	}
	return json.Unmarshal(b, out)
}

// CoverURL finds a cover for the tags (album first, then track's album).
func (c *Client) CoverURL(ctx context.Context, t Tags) (string, error) {
	if t.Artist == "" || (t.Album == "" && t.Title == "") {
		return "", errors.New("brak wykonawcy/tytułu (tagi ID3 albo nazwa pliku „Wykonawca - Tytuł”)")
	}
	if t.Album != "" {
		var r struct {
			Album struct {
				Image []lfmImage `json:"image"`
			} `json:"album"`
		}
		if err := c.call(ctx, url.Values{"method": {"album.getinfo"}, "artist": {t.Artist}, "album": {t.Album}}, &r); err == nil {
			if u := best(r.Album.Image); u != "" {
				return u, nil
			}
		}
	}
	var r struct {
		Track struct {
			Album struct {
				Image []lfmImage `json:"image"`
			} `json:"album"`
		} `json:"track"`
	}
	if err := c.call(ctx, url.Values{"method": {"track.getinfo"}, "artist": {t.Artist}, "track": {t.Title}}, &r); err != nil {
		return "", err
	}
	if u := best(r.Track.Album.Image); u != "" {
		return u, nil
	}
	return "", errors.New("Last.fm nie ma okładki dla tego utworu")
}

var unsafe = regexp.MustCompile(`[\\/*?:"<>|]`)

// Download saves the cover into dir and returns the file name.
func (c *Client) Download(ctx context.Context, coverURL, dir string, t Tags) (string, error) {
	u, err := url.Parse(coverURL)
	if err != nil || u.Scheme != "https" {
		return "", errors.New("nieprawidłowy adres okładki")
	}
	req, err := http.NewRequestWithContext(ctx, "GET", coverURL, nil)
	if err != nil {
		return "", err
	}
	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: 20 * time.Second}
	}
	resp, err := hc.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(io.LimitReader(resp.Body, 10<<20))
	if err != nil || resp.StatusCode != 200 {
		return "", fmt.Errorf("pobieranie okładki: HTTP %d", resp.StatusCode)
	}
	ext := ".jpg"
	switch http.DetectContentType(data) {
	case "image/png":
		ext = ".png"
	case "image/jpeg":
	case "image/webp":
		ext = ".webp"
	case "image/gif":
		ext = ".gif"
	default:
		return "", errors.New("Last.fm nie zwrócił obrazu")
	}
	name := unsafe.ReplaceAllString("lfm_cover_"+t.Artist+"_"+firstNonEmpty(t.Album, t.Title), "_")
	if len(name) > 120 {
		name = name[:120]
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	return name + ext, os.WriteFile(filepath.Join(dir, name+ext), data, 0o644)
}

func firstNonEmpty(a, b string) string {
	if a != "" {
		return a
	}
	return b
}
