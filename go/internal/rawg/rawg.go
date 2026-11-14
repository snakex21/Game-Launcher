// Package rawg fetches game metadata and covers from RAWG.io and maps them
// to the fields the launcher stores (rawg_id, rawg_slug, description,
// release_date, website, developers, publishers, genres_api, tags_api,
// platforms, requirements_pc, cover_rawg).
package rawg

import (
	"context"
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
)

// BaseURL of the API (tests point it at httptest).
var BaseURL = "https://api.rawg.io/api/games"

// MaxCoverBytes bounds a downloaded cover.
const MaxCoverBytes = 25 << 20

// Client calls the API.
type Client struct {
	HTTP      *http.Client
	Key       string
	UserAgent string
}

// Details is the mapped result.
type Details struct {
	ID             int64             `json:"rawg_id"`
	Slug           string            `json:"rawg_slug"`
	Name           string            `json:"name"`
	Description    string            `json:"description"`
	Released       string            `json:"release_date"`
	Website        string            `json:"website"`
	Developers     []string          `json:"developers"`
	Publishers     []string          `json:"publishers"`
	Genres         []string          `json:"genres_api"`
	Tags           []string          `json:"tags_api"`
	Platforms      []string          `json:"platforms"`
	RequirementsPC map[string]string `json:"requirements_pc,omitempty"`
	BackgroundURL  string            `json:"-"`
}

// ErrNotFound means the search returned nothing.
var ErrNotFound = errors.New("Nie znaleziono gry w bazie RAWG.")

type named struct {
	Name string `json:"name"`
}

func names(in []named) []string {
	out := []string{}
	for _, n := range in {
		if n.Name != "" {
			out = append(out, n.Name)
		}
	}
	return out
}

func (c *Client) get(ctx context.Context, u string, into any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return err
	}
	if c.UserAgent != "" {
		req.Header.Set("User-Agent", c.UserAgent)
	}
	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: 20 * time.Second}
	}
	resp, err := hc.Do(req)
	if err != nil {
		// never leak the key (it is in the URL) into messages
		var ue *url.Error
		if errors.As(err, &ue) {
			err = ue.Err
		}
		return fmt.Errorf("Błąd połączenia z RAWG: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return errors.New("RAWG odrzucił klucz API (sprawdź klucz w Ustawieniach).")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("RAWG zwrócił błąd HTTP %d.", resp.StatusCode)
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, 8<<20)).Decode(into); err != nil {
		return errors.New("Błąd przetwarzania danych z RAWG.")
	}
	return nil
}

// Fetch searches for the game and returns its details.
func (c *Client) Fetch(ctx context.Context, gameName string) (*Details, error) {
	if strings.TrimSpace(c.Key) == "" {
		return nil, errors.New("Brak klucza API RAWG. Dodaj go w Ustawieniach → Klucze API (albo zmienna GL_RAWG_API_KEY).")
	}
	q := url.Values{"key": {c.Key}, "search": {gameName}, "page_size": {"1"}}
	var search struct {
		Results []struct {
			ID   int64  `json:"id"`
			Slug string `json:"slug"`
		} `json:"results"`
	}
	if err := c.get(ctx, BaseURL+"?"+q.Encode(), &search); err != nil {
		return nil, err
	}
	if len(search.Results) == 0 || search.Results[0].ID == 0 {
		return nil, ErrNotFound
	}
	id := search.Results[0].ID
	var d struct {
		Name            string  `json:"name"`
		Slug            string  `json:"slug"`
		DescriptionRaw  string  `json:"description_raw"`
		Released        string  `json:"released"`
		Website         string  `json:"website"`
		BackgroundImage string  `json:"background_image"`
		Developers      []named `json:"developers"`
		Publishers      []named `json:"publishers"`
		Genres          []named `json:"genres"`
		Tags            []named `json:"tags"`
		Platforms       []struct {
			Platform struct {
				Name string `json:"name"`
				Slug string `json:"slug"`
			} `json:"platform"`
			Requirements *struct {
				Minimum     string `json:"minimum"`
				Recommended string `json:"recommended"`
			} `json:"requirements"`
		} `json:"platforms"`
	}
	if err := c.get(ctx, fmt.Sprintf("%s/%d?%s", BaseURL, id, url.Values{"key": {c.Key}}.Encode()), &d); err != nil {
		return nil, err
	}
	out := &Details{
		ID: id, Slug: d.Slug, Name: d.Name, Description: d.DescriptionRaw, Released: d.Released, Website: d.Website,
		Developers: names(d.Developers), Publishers: names(d.Publishers), Genres: names(d.Genres), Tags: names(d.Tags),
		Platforms: []string{}, BackgroundURL: d.BackgroundImage,
	}
	if out.Slug == "" {
		out.Slug = search.Results[0].Slug
	}
	for _, p := range d.Platforms {
		if p.Platform.Name != "" {
			out.Platforms = append(out.Platforms, p.Platform.Name)
		}
		if p.Platform.Slug == "pc" && p.Requirements != nil {
			out.RequirementsPC = map[string]string{"minimum": p.Requirements.Minimum, "recommended": p.Requirements.Recommended}
		}
	}
	return out, nil
}

var unsafeChars = regexp.MustCompile(`[\\/*?:"<>|]`)

// SafeName makes a file-name-safe game name (same rule as Python).
func SafeName(name string) string { return unsafeChars.ReplaceAllString(name, "_") }

// DownloadCover saves the image to imagesDir/<game>_rawg_cover.<ext> and
// returns the stored (app-relative) path "images\<file>".
func (c *Client) DownloadCover(ctx context.Context, gameName, imageURL, imagesDir string) (string, error) {
	u, err := url.Parse(imageURL)
	if err != nil || u.Scheme != "https" {
		return "", errors.New("nieprawidłowy adres okładki")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, imageURL, nil)
	if err != nil {
		return "", err
	}
	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: 30 * time.Second}
	}
	resp, err := hc.Do(req)
	if err != nil {
		return "", fmt.Errorf("pobieranie okładki: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("pobieranie okładki: HTTP %d", resp.StatusCode)
	}
	ct := resp.Header.Get("Content-Type")
	ext := ".jpg"
	switch {
	case strings.Contains(ct, "png"):
		ext = ".png"
	case strings.Contains(ct, "webp"):
		ext = ".webp"
	case strings.Contains(ct, "gif"):
		ext = ".gif"
	case strings.Contains(ct, "jpeg"), strings.Contains(ct, "jpg"):
		ext = ".jpg"
	case ct == "" || strings.HasPrefix(ct, "application/octet-stream"):
		for _, e := range []string{".png", ".webp", ".jpg", ".jpeg", ".gif"} {
			if strings.HasSuffix(strings.ToLower(u.Path), e) {
				ext = e
			}
		}
	default:
		if !strings.HasPrefix(ct, "image/") {
			return "", fmt.Errorf("serwer nie zwrócił obrazu (%s)", ct)
		}
	}
	if err := os.MkdirAll(imagesDir, 0o755); err != nil {
		return "", err
	}
	file := SafeName(gameName) + "_rawg_cover" + ext
	tmp, err := os.CreateTemp(imagesDir, ".cover-*")
	if err != nil {
		return "", err
	}
	n, err := io.Copy(tmp, io.LimitReader(resp.Body, MaxCoverBytes+1))
	tmp.Close()
	if err != nil || n > MaxCoverBytes {
		os.Remove(tmp.Name())
		if err == nil {
			err = errors.New("okładka jest za duża")
		}
		return "", err
	}
	dest := filepath.Join(imagesDir, file)
	if err := os.Rename(tmp.Name(), dest); err != nil {
		os.Remove(tmp.Name())
		return "", err
	}
	return `images\` + file, nil
}
