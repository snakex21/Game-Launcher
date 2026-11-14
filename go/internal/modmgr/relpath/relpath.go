// Package relpath validates and matches the relative paths the mod manager
// works with: archive entries, FOMOD/manifest paths and deployment targets.
//
// A clean relative path uses '/', has no drive, no leading '/', no '.' or
// '..' segments, no empty segments, no NTFS stream (':'), no reserved
// Windows device names and no segment ending in a dot or a space.
package relpath

import (
	"errors"
	"fmt"
	"path"
	"strings"
	"unicode/utf8"
)

// ErrInvalid is wrapped by every validation error.
var ErrInvalid = errors.New("niedozwolona ścieżka")

func invalid(raw, why string) error {
	return fmt.Errorf("%w %q: %s", ErrInvalid, raw, why)
}

var reserved = map[string]bool{
	"con": true, "prn": true, "aux": true, "nul": true,
	"com1": true, "com2": true, "com3": true, "com4": true, "com5": true, "com6": true, "com7": true, "com8": true, "com9": true,
	"lpt1": true, "lpt2": true, "lpt3": true, "lpt4": true, "lpt5": true, "lpt6": true, "lpt7": true, "lpt8": true, "lpt9": true,
	"conin$": true, "conout$": true,
	// Windows also opens devices for superscript digits
	"com¹": true, "com²": true, "com³": true, "lpt¹": true, "lpt²": true, "lpt³": true,
}

// Clean validates raw (from an archive, a manifest or a definition) and
// returns it normalised. "." segments are dropped; everything else that is
// unsafe is rejected rather than "fixed".
func Clean(raw string) (string, error) {
	if raw == "" {
		return "", invalid(raw, "pusta")
	}
	if !utf8.ValidString(raw) {
		return "", invalid(raw, "nieprawidłowe kodowanie")
	}
	p := strings.ReplaceAll(raw, `\`, "/")
	if strings.HasPrefix(p, "/") {
		return "", invalid(raw, "ścieżka bezwzględna")
	}
	if len(p) >= 2 && p[1] == ':' {
		return "", invalid(raw, "litera dysku")
	}
	segs := strings.Split(p, "/")
	out := segs[:0]
	for i, s := range segs {
		switch s {
		case "":
			if i == len(segs)-1 { // trailing slash (directory entry)
				continue
			}
			return "", invalid(raw, "pusty element")
		case ".":
			continue
		case "..":
			return "", invalid(raw, "wyjście poza katalog (..)")
		}
		if err := checkSegment(s); err != nil {
			return "", invalid(raw, err.Error())
		}
		out = append(out, s)
	}
	if len(out) == 0 {
		return "", invalid(raw, "pusta")
	}
	return strings.Join(out, "/"), nil
}

func checkSegment(s string) error {
	for _, r := range s {
		if r < 0x20 || r == 0x7f {
			return errors.New("znak sterujący")
		}
		switch r {
		case ':':
			return errors.New("dwukropek (strumień NTFS)")
		case '<', '>', '"', '|', '?', '*':
			return fmt.Errorf("znak %q", r)
		}
	}
	if strings.HasSuffix(s, ".") || strings.HasSuffix(s, " ") {
		return errors.New("nazwa kończy się kropką lub spacją")
	}
	base := strings.ToLower(s)
	if i := strings.IndexByte(base, '.'); i >= 0 {
		base = base[:i]
	}
	if reserved[strings.TrimRight(base, " ")] {
		return errors.New("zarezerwowana nazwa urządzenia Windows")
	}
	return nil
}

// Key is the comparison key of a clean path (case-insensitive).
func Key(rel string) string { return strings.ToLower(rel) }

// Join joins clean relative paths (empty elements skipped).
func Join(elems ...string) string {
	var parts []string
	for _, e := range elems {
		e = strings.Trim(e, "/")
		if e != "" {
			parts = append(parts, e)
		}
	}
	return strings.Join(parts, "/")
}

// Base is the last segment.
func Base(rel string) string { return path.Base(rel) }

// Dir is everything before the last segment ("" at the top).
func Dir(rel string) string {
	if i := strings.LastIndexByte(rel, '/'); i >= 0 {
		return rel[:i]
	}
	return ""
}

// HasPrefixDir reports whether rel is dir or lies inside dir (case-insensitive).
func HasPrefixDir(rel, dir string) bool {
	if dir == "" {
		return true
	}
	if len(rel) < len(dir) || !strings.EqualFold(rel[:len(dir)], dir) {
		return false
	}
	return len(rel) == len(dir) || rel[len(dir)] == '/'
}

// TrimDir returns rel relative to dir (rel must be inside dir).
func TrimDir(rel, dir string) string {
	if dir == "" {
		return rel
	}
	if len(rel) <= len(dir) {
		return ""
	}
	return rel[len(dir)+1:]
}

// Match reports whether rel matches the glob pattern (case-insensitive).
// A pattern without '/' is matched against the last segment only; with '/'
// against the whole path. '*' and '?' never cross '/', '**' matches any
// number of segments (also none).
func Match(pattern, rel string) bool {
	pattern = strings.ToLower(strings.ReplaceAll(pattern, `\`, "/"))
	rel = strings.ToLower(rel)
	if !strings.Contains(pattern, "/") {
		return matchSeg(pattern, Base(rel))
	}
	return matchSegs(strings.Split(pattern, "/"), strings.Split(rel, "/"))
}

// MatchAny reports whether any pattern matches.
func MatchAny(patterns []string, rel string) bool {
	for _, p := range patterns {
		if Match(p, rel) {
			return true
		}
	}
	return false
}

func matchSegs(pat, segs []string) bool {
	for len(pat) > 0 {
		if pat[0] == "**" {
			pat = pat[1:]
			if len(pat) == 0 {
				return true
			}
			for i := 0; i <= len(segs); i++ {
				if matchSegs(pat, segs[i:]) {
					return true
				}
			}
			return false
		}
		if len(segs) == 0 || !matchSeg(pat[0], segs[0]) {
			return false
		}
		pat, segs = pat[1:], segs[1:]
	}
	return len(segs) == 0
}

// matchSeg matches one segment with '*' and '?' (no character classes, so
// names with '[' are literal).
func matchSeg(pat, s string) bool {
	p := []rune(pat)
	r := []rune(s)
	pi, si := 0, 0
	star, mark := -1, 0
	for si < len(r) {
		switch {
		case pi < len(p) && (p[pi] == '?' || p[pi] == r[si]):
			pi++
			si++
		case pi < len(p) && p[pi] == '*':
			star, mark = pi, si
			pi++
		case star >= 0:
			pi = star + 1
			mark++
			si = mark
		default:
			return false
		}
	}
	for pi < len(p) && p[pi] == '*' {
		pi++
	}
	return pi == len(p)
}
