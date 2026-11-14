// Package updater updates GameLauncher.exe from GitHub Releases:
//   - the newest release by semantic version (not the first or the oldest);
//   - the asset chosen by a name pattern (not "assets[0]");
//   - SHA-256 verification is mandatory (from "<asset>.sha256" or a
//     SHA256SUMS file); without a checksum nothing is installed;
//   - self-replace on Windows: the running exe is renamed to *.old, the new
//     file takes its name, the new version is started with -post-update;
//     a marker file allows rollback when the new version never reaches its
//     first paint.
package updater

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// API base (tests use a fake).
var API = "https://api.github.com"

// Version is a parsed semantic version.
type Version struct {
	Major, Minor, Patch int
	Pre                 string
	Raw                 string
}

var semverRe = regexp.MustCompile(`^v?(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$`)

// Parse reads "v1.2.3", "1.2", "1.2.3-beta.1".
func Parse(s string) (Version, error) {
	m := semverRe.FindStringSubmatch(strings.TrimSpace(s))
	if m == nil {
		return Version{}, fmt.Errorf("nie jest wersją: %q", s)
	}
	v := Version{Raw: s, Pre: m[4]}
	v.Major, _ = strconv.Atoi(m[1])
	v.Minor, _ = strconv.Atoi(m[2])
	v.Patch, _ = strconv.Atoi(m[3])
	return v, nil
}

func cmpInt(a, b int) int {
	switch {
	case a < b:
		return -1
	case a > b:
		return 1
	}
	return 0
}

// Compare follows semver precedence (pre-releases sort before releases).
func Compare(a, b Version) int {
	if c := cmpInt(a.Major, b.Major); c != 0 {
		return c
	}
	if c := cmpInt(a.Minor, b.Minor); c != 0 {
		return c
	}
	if c := cmpInt(a.Patch, b.Patch); c != 0 {
		return c
	}
	switch {
	case a.Pre == b.Pre:
		return 0
	case a.Pre == "":
		return 1
	case b.Pre == "":
		return -1
	}
	ap, bp := strings.Split(a.Pre, "."), strings.Split(b.Pre, ".")
	for i := 0; i < len(ap) && i < len(bp); i++ {
		ai, aerr := strconv.Atoi(ap[i])
		bi, berr := strconv.Atoi(bp[i])
		switch {
		case aerr == nil && berr == nil:
			if c := cmpInt(ai, bi); c != 0 {
				return c
			}
		case aerr == nil:
			return -1
		case berr == nil:
			return 1
		default:
			if c := strings.Compare(ap[i], bp[i]); c != 0 {
				return c
			}
		}
	}
	return cmpInt(len(ap), len(bp))
}

// Asset of a release.
type Asset struct {
	Name string `json:"name"`
	URL  string `json:"browser_download_url"`
	Size int64  `json:"size"`
}

// Release from the API.
type Release struct {
	Tag        string  `json:"tag_name"`
	Name       string  `json:"name"`
	Body       string  `json:"body"`
	Draft      bool    `json:"draft"`
	Prerelease bool    `json:"prerelease"`
	Assets     []Asset `json:"assets"`
	version    Version
}

// Update is an available update.
type Update struct {
	Version  string `json:"version"`
	Notes    string `json:"notes"`
	Asset    Asset  `json:"asset"`
	SumAsset Asset  `json:"sumAsset"`
}

// Checker finds updates.
type Checker struct {
	Repo         string         // "owner/name"
	AssetPattern *regexp.Regexp // e.g. ^GameLauncher.*\.exe$
	Prerelease   bool
	HTTP         *http.Client
	Base         string
}

// DefaultAssetPattern matches the release exe.
var DefaultAssetPattern = regexp.MustCompile(`(?i)^GameLauncher([-_.].*)?(windows[-_])?(amd64|x64)?.*\.exe$`)

func (c *Checker) client() *http.Client {
	if c.HTTP != nil {
		return c.HTTP
	}
	return &http.Client{Timeout: 30 * time.Second}
}

// Check returns the newest update newer than current, or nil.
func (c *Checker) Check(ctx context.Context, current string) (*Update, error) {
	cur, err := Parse(current)
	if err != nil {
		cur = Version{} // "dev": every release is newer
	}
	base := c.Base
	if base == "" {
		base = API
	}
	req, err := http.NewRequestWithContext(ctx, "GET", base+"/repos/"+c.Repo+"/releases?per_page=50", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", "GameLauncher-Go-updater")
	resp, err := c.client().Do(req)
	if err != nil {
		return nil, fmt.Errorf("sprawdzanie aktualizacji: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("sprawdzanie aktualizacji: HTTP %d", resp.StatusCode)
	}
	var rels []Release
	if err := json.NewDecoder(io.LimitReader(resp.Body, 8<<20)).Decode(&rels); err != nil {
		return nil, err
	}
	var best *Release
	for i := range rels {
		r := &rels[i]
		if r.Draft || (r.Prerelease && !c.Prerelease) {
			continue
		}
		v, err := Parse(r.Tag)
		if err != nil {
			continue
		}
		r.version = v
		if Compare(v, cur) <= 0 {
			continue
		}
		if best == nil || Compare(v, best.version) > 0 {
			best = r
		}
	}
	if best == nil {
		return nil, nil
	}
	pat := c.AssetPattern
	if pat == nil {
		pat = DefaultAssetPattern
	}
	u := &Update{Version: best.Tag, Notes: best.Body}
	for _, a := range best.Assets {
		if pat.MatchString(a.Name) {
			u.Asset = a
			break
		}
	}
	if u.Asset.Name == "" {
		return nil, fmt.Errorf("wydanie %s nie ma pliku pasującego do %s", best.Tag, pat)
	}
	for _, a := range best.Assets {
		n := strings.ToLower(a.Name)
		if n == strings.ToLower(u.Asset.Name)+".sha256" || n == "sha256sums" || n == "sha256sums.txt" || n == "checksums.txt" {
			u.SumAsset = a
			if strings.HasSuffix(n, ".sha256") {
				break
			}
		}
	}
	if u.SumAsset.Name == "" {
		return nil, fmt.Errorf("wydanie %s nie ma sumy SHA-256 – aktualizacja odrzucona", best.Tag)
	}
	return u, nil
}

func (c *Checker) get(ctx context.Context, url string, w io.Writer, limit int64) error {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "GameLauncher-Go-updater")
	resp, err := c.client().Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("pobieranie: HTTP %d", resp.StatusCode)
	}
	n, err := io.Copy(w, io.LimitReader(resp.Body, limit+1))
	if err == nil && n > limit {
		return errors.New("plik jest za duży")
	}
	return err
}

// expectedSum finds the hex digest for name in a checksum file.
func expectedSum(data, name string) (string, error) {
	sc := bufio.NewScanner(strings.NewReader(data))
	for sc.Scan() {
		f := strings.Fields(sc.Text())
		if len(f) == 0 {
			continue
		}
		if len(f) == 1 && len(f[0]) == 64 { // "<asset>.sha256" with only the digest
			return strings.ToLower(f[0]), nil
		}
		if len(f) >= 2 && strings.TrimPrefix(f[len(f)-1], "*") == name && len(f[0]) == 64 {
			return strings.ToLower(f[0]), nil
		}
	}
	return "", fmt.Errorf("brak sumy SHA-256 dla %s", name)
}

// Download fetches the asset next to exePath (same volume, so the swap is
// a rename) and verifies SHA-256. Returns the downloaded file path.
func (c *Checker) Download(ctx context.Context, u *Update, exePath string) (string, error) {
	var sums strings.Builder
	if err := c.get(ctx, u.SumAsset.URL, &sums, 1<<20); err != nil {
		return "", fmt.Errorf("suma SHA-256: %v", err)
	}
	want, err := expectedSum(sums.String(), u.Asset.Name)
	if err != nil {
		return "", err
	}
	dst := exePath + ".new"
	f, err := os.Create(dst)
	if err != nil {
		return "", err
	}
	h := sha256.New()
	err = c.get(ctx, u.Asset.URL, io.MultiWriter(f, h), 300<<20)
	f.Close()
	if err != nil {
		os.Remove(dst)
		return "", err
	}
	if got := hex.EncodeToString(h.Sum(nil)); got != want {
		os.Remove(dst)
		return "", fmt.Errorf("niezgodna suma SHA-256 (oczekiwano %s, jest %s) – plik usunięty", want, got)
	}
	return dst, nil
}

// Marker records an update in progress (for rollback).
type Marker struct {
	From     string `json:"from"`
	To       string `json:"to"`
	Attempts int    `json:"attempts"`
}

func markerPath(exe string) string { return exe + ".update.json" }

// Swap replaces exe with newFile, keeping the old one as exe.old. On any
// error the original exe is put back.
func Swap(exe, newFile, from, to string) error {
	old := exe + ".old"
	_ = os.Remove(old)
	if err := os.Rename(exe, old); err != nil { // a running exe can be renamed on Windows
		return fmt.Errorf("nie można przenieść działającego pliku: %v", err)
	}
	if err := os.Rename(newFile, exe); err != nil {
		_ = os.Rename(old, exe)
		return fmt.Errorf("nie można podmienić pliku: %v", err)
	}
	b, _ := json.Marshal(Marker{From: from, To: to})
	if err := os.WriteFile(markerPath(exe), b, 0o644); err != nil {
		_ = Rollback(exe)
		return err
	}
	return nil
}

// Rollback restores exe.old.
func Rollback(exe string) error {
	old := exe + ".old"
	if _, err := os.Stat(old); err != nil {
		return errors.New("brak poprzedniej wersji do przywrócenia")
	}
	bad := exe + ".failed"
	_ = os.Remove(bad)
	if err := os.Rename(exe, bad); err != nil {
		return err
	}
	if err := os.Rename(old, exe); err != nil {
		_ = os.Rename(bad, exe)
		return err
	}
	_ = os.Remove(markerPath(exe))
	return nil
}

// StartupState is what main must do at start.
type StartupState int

const (
	// Normal start, no update pending.
	Normal StartupState = iota
	// Trial: first run(s) of a new version; call Confirm after the first paint.
	Trial
	// RolledBack: the new version failed before; the old exe was restored
	// and should be started instead.
	RolledBack
)

// MaxAttempts before a rollback.
const MaxAttempts = 2

// OnStartup checks the marker. Each start of a not-yet-confirmed version
// counts an attempt; after MaxAttempts failed starts the old exe returns.
func OnStartup(exe string) (StartupState, *Marker) {
	b, err := os.ReadFile(markerPath(exe))
	if err != nil {
		return Normal, nil
	}
	var m Marker
	if json.Unmarshal(b, &m) != nil {
		_ = os.Remove(markerPath(exe))
		return Normal, nil
	}
	m.Attempts++
	if m.Attempts > MaxAttempts {
		if Rollback(exe) == nil {
			return RolledBack, &m
		}
		return Normal, &m
	}
	nb, _ := json.Marshal(m)
	_ = os.WriteFile(markerPath(exe), nb, 0o644)
	return Trial, &m
}

// Confirm marks the new version good: removes the marker and the old exe.
func Confirm(exe string) {
	_ = os.Remove(markerPath(exe))
	_ = os.Remove(exe + ".old")
	_ = os.Remove(exe + ".failed")
}
