// Package news reads RSS 2.0 and Atom feeds (settings.rss_feeds) and
// returns plain-text items (HTML is stripped; nothing from a feed is ever
// rendered as HTML in the launcher).
package news

import (
	"context"
	"encoding/xml"
	"errors"
	"fmt"
	"html"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

// Item is one news entry.
type Item struct {
	Feed    string    `json:"feed"`
	Title   string    `json:"title"`
	Link    string    `json:"link"`
	Summary string    `json:"summary"`
	Date    time.Time `json:"date"`
}

// Feed source.
type Feed struct {
	Name string
	URL  string
}

type rss struct {
	Channel struct {
		Items []struct {
			Title       string `xml:"title"`
			Link        string `xml:"link"`
			Description string `xml:"description"`
			PubDate     string `xml:"pubDate"`
			Date        string `xml:"http://purl.org/dc/elements/1.1/ date"`
		} `xml:"item"`
	} `xml:"channel"`
}

type atom struct {
	Entries []struct {
		Title string `xml:"title"`
		Links []struct {
			Href string `xml:"href,attr"`
			Rel  string `xml:"rel,attr"`
		} `xml:"link"`
		Summary   string `xml:"summary"`
		Content   string `xml:"content"`
		Updated   string `xml:"updated"`
		Published string `xml:"published"`
	} `xml:"entry"`
}

var (
	tagRe   = regexp.MustCompile(`(?s)<[^>]*>`)
	spaceRe = regexp.MustCompile(`\s+`)
)

// PlainText strips HTML and collapses whitespace.
func PlainText(s string) string {
	s = tagRe.ReplaceAllString(s, " ")
	s = html.UnescapeString(s)
	return strings.TrimSpace(spaceRe.ReplaceAllString(s, " "))
}

var dateLayouts = []string{time.RFC1123Z, time.RFC1123, time.RFC3339, "Mon, 2 Jan 2006 15:04:05 -0700", "Mon, 2 Jan 2006 15:04:05 MST", "2006-01-02T15:04:05Z07:00", "2006-01-02"}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, l := range dateLayouts {
		if t, err := time.Parse(l, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func safeLink(s string) string {
	u, err := url.Parse(strings.TrimSpace(s))
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") {
		return ""
	}
	return u.String()
}

func clip(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n]) + "…"
	}
	return s
}

// Parse reads a feed document.
func Parse(feedName string, data []byte) ([]Item, error) {
	var out []Item
	var r rss
	if err := xml.Unmarshal(data, &r); err == nil && len(r.Channel.Items) > 0 {
		for _, it := range r.Channel.Items {
			d := parseDate(it.PubDate)
			if d.IsZero() {
				d = parseDate(it.Date)
			}
			out = append(out, Item{Feed: feedName, Title: PlainText(it.Title), Link: safeLink(it.Link), Summary: clip(PlainText(it.Description), 400), Date: d})
		}
		return out, nil
	}
	var a atom
	if err := xml.Unmarshal(data, &a); err == nil && len(a.Entries) > 0 {
		for _, e := range a.Entries {
			link := ""
			for _, l := range e.Links {
				if l.Rel == "" || l.Rel == "alternate" {
					link = l.Href
					break
				}
			}
			sum := e.Summary
			if sum == "" {
				sum = e.Content
			}
			d := parseDate(e.Published)
			if d.IsZero() {
				d = parseDate(e.Updated)
			}
			out = append(out, Item{Feed: feedName, Title: PlainText(e.Title), Link: safeLink(link), Summary: clip(PlainText(sum), 400), Date: d})
		}
		return out, nil
	}
	return nil, errors.New("to nie jest kanał RSS/Atom")
}

// Fetch downloads all feeds in parallel and returns the newest `limit`
// items plus per-feed errors.
func Fetch(ctx context.Context, client *http.Client, feeds []Feed, limit int) ([]Item, map[string]string) {
	if client == nil {
		client = &http.Client{Timeout: 15 * time.Second}
	}
	var mu sync.Mutex
	var wg sync.WaitGroup
	var all []Item
	errs := map[string]string{}
	for _, f := range feeds {
		f := f
		wg.Add(1)
		go func() {
			defer wg.Done()
			items, err := fetchOne(ctx, client, f)
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				errs[f.Name] = err.Error()
				return
			}
			all = append(all, items...)
		}()
	}
	wg.Wait()
	sort.SliceStable(all, func(i, j int) bool { return all[i].Date.After(all[j].Date) })
	if limit > 0 && len(all) > limit {
		all = all[:limit]
	}
	return all, errs
}

func fetchOne(ctx context.Context, client *http.Client, f Feed) ([]Item, error) {
	u := safeLink(f.URL)
	if u == "" {
		return nil, errors.New("nieprawidłowy adres kanału")
	}
	req, err := http.NewRequestWithContext(ctx, "GET", u, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 GameLauncher-Go")
	resp, err := client.Do(req)
	if err != nil {
		var ue *url.Error
		if errors.As(err, &ue) {
			err = ue.Err
		}
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, 5<<20))
	if err != nil {
		return nil, err
	}
	return Parse(f.Name, data)
}
