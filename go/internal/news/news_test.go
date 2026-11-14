package news

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const rssDoc = `<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Nowa gra &amp; patch</title><link>https://example.invalid/a</link><description>&lt;p&gt;Opis &lt;script&gt;x()&lt;/script&gt;&lt;b&gt;pogrubiony&lt;/b&gt;&lt;/p&gt;</description><pubDate>Mon, 10 Nov 2026 10:00:00 +0000</pubDate></item>
<item><title>Stara</title><link>javascript:alert(1)</link><description>x</description><pubDate>Mon, 03 Nov 2026 10:00:00 +0000</pubDate></item>
</channel></rss>`

const atomDoc = `<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom wpis</title>
<link rel="alternate" href="https://example.invalid/b"/><summary>Sum</summary><updated>2026-11-12T08:00:00Z</updated></entry></feed>`

func TestParseAndFetch(t *testing.T) {
	items, err := Parse("IGN", []byte(rssDoc))
	if err != nil || len(items) != 2 {
		t.Fatal(items, err)
	}
	if items[0].Title != "Nowa gra & patch" || strings.Contains(items[0].Summary, "<") || items[1].Link != "" {
		t.Fatalf("%+v", items)
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/rss":
			w.Write([]byte(rssDoc))
		case "/atom":
			w.Write([]byte(atomDoc))
		default:
			w.WriteHeader(404)
		}
	}))
	defer srv.Close()
	got, errs := Fetch(context.Background(), srv.Client(), []Feed{{"A", srv.URL + "/rss"}, {"B", srv.URL + "/atom"}, {"C", srv.URL + "/none"}}, 2)
	if len(got) != 2 || got[0].Title != "Atom wpis" || got[1].Title != "Nowa gra & patch" || errs["C"] == "" {
		t.Fatalf("%+v %v", got, errs)
	}
	if _, err := Parse("x", []byte("<html></html>")); err == nil {
		t.Fatal("html accepted as feed")
	}
}
