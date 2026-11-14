package gamedef

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// RootKind names a root folder that locations are relative to.
type RootKind string

// Root kinds.
const (
	RootGame         RootKind = "game"
	RootDocuments    RootKind = "documents"
	RootLocalAppData RootKind = "localAppData"
	RootAppData      RootKind = "appData"
	RootLocalLow     RootKind = "localLow"
	RootUserProfile  RootKind = "userProfile"
	RootSavedGames   RootKind = "savedGames"
	RootSteam        RootKind = "steamRoot"
	RootInstance     RootKind = "instance"
	RootProfileDir   RootKind = "profileDir"
	RootModsStaging  RootKind = "modsStaging"
)

// rootVars maps template variables to roots. {myGames} is documents/My Games.
var rootVars = map[string]RootKind{
	"game":         RootGame,
	"documents":    RootDocuments,
	"localAppData": RootLocalAppData,
	"appData":      RootAppData,
	"localLow":     RootLocalLow,
	"userProfile":  RootUserProfile,
	"savedGames":   RootSavedGames,
	"steamRoot":    RootSteam,
	"instance":     RootInstance,
	"profileDir":   RootProfileDir,
	"modsStaging":  RootModsStaging,
}

// Location is a path relative to a named root (portable: no drive letter).
type Location struct {
	Root RootKind `json:"root"`
	Rel  string   `json:"rel"`
}

func (l Location) String() string {
	if l.Rel == "" {
		return "{" + string(l.Root) + "}"
	}
	return "{" + string(l.Root) + "}/" + l.Rel
}

// Key is the case-insensitive comparison key.
func (l Location) Key() string { return string(l.Root) + ":" + relpath.Key(l.Rel) }

// Child returns a location below l.
func (l Location) Child(rel string) Location {
	return Location{Root: l.Root, Rel: relpath.Join(l.Rel, rel)}
}

// Resolver expands templates for one game install.
type Resolver struct {
	Def   *Definition
	Store string // steam|gog|epic|xbox|manual: selects storeOverrides
	// Roots maps root kinds to absolute folders on this machine.
	Roots map[RootKind]string
	// Vars are extra variables ({selectedGameDir}, {mod.folderName}...).
	Vars map[string]string
	// PathOverrides replace definition paths ({paths.modsTarget} for generic).
	PathOverrides map[string]string
}

func (r *Resolver) pathVar(name string) (string, bool) {
	if v, ok := r.PathOverrides[name]; ok && v != "" {
		return v, true
	}
	if r.Store != "" {
		if raw, ok := r.Def.StoreOverrides[r.Store]; ok {
			var so struct {
				Paths map[string]string `json:"paths"`
			}
			if json.Unmarshal(raw, &so) == nil {
				if v, ok := so.Paths[name]; ok {
					return v, true
				}
			}
		}
	}
	v, ok := r.Def.Paths[name]
	return v, ok
}

// Location expands a template into a location. The template must start
// with a root variable ({game}, {localAppData}, {paths.x} leading to one...).
func (r *Resolver) Location(t string) (Location, error) {
	return r.location(t, 0)
}

func (r *Resolver) location(t string, depth int) (Location, error) {
	if depth > 8 {
		return Location{}, fmt.Errorf("szablon %q: zbyt głębokie zagnieżdżenie", t)
	}
	t = strings.ReplaceAll(t, `\`, "/")
	if !strings.HasPrefix(t, "{") {
		return Location{}, fmt.Errorf("szablon %q nie zaczyna się od folderu bazowego", t)
	}
	end := strings.IndexByte(t, '}')
	if end < 0 {
		return Location{}, fmt.Errorf("szablon %q: brak }", t)
	}
	head, rest := t[1:end], strings.TrimPrefix(t[end+1:], "/")
	var base Location
	switch {
	case head == "myGames":
		base = Location{Root: RootDocuments, Rel: "My Games"}
	case strings.HasPrefix(head, "paths."):
		v, ok := r.pathVar(strings.TrimPrefix(head, "paths."))
		if !ok {
			return Location{}, fmt.Errorf("szablon %q: nieznana ścieżka %s", t, head)
		}
		l, err := r.location(v, depth+1)
		if err != nil {
			return Location{}, err
		}
		base = l
	default:
		kind, ok := rootVars[head]
		if !ok {
			return Location{}, fmt.Errorf("szablon %q: nieznany folder bazowy {%s}", t, head)
		}
		base = Location{Root: kind}
	}
	if rest == "" {
		return base, nil
	}
	expanded, err := r.Expand(rest)
	if err != nil {
		return Location{}, fmt.Errorf("szablon %q: %w", t, err)
	}
	clean, err := relpath.Clean(expanded)
	if err != nil {
		return Location{}, fmt.Errorf("szablon %q: %w", t, err)
	}
	return base.Child(clean), nil
}

// Expand replaces {vars} inside a relative part (no roots allowed).
func (r *Resolver) Expand(s string) (string, error) {
	var b strings.Builder
	for {
		i := strings.IndexByte(s, '{')
		if i < 0 {
			b.WriteString(s)
			return b.String(), nil
		}
		j := strings.IndexByte(s[i:], '}')
		if j < 0 {
			return "", fmt.Errorf("brak } w %q", s)
		}
		name := s[i+1 : i+j]
		v, ok := r.Vars[name]
		if !ok {
			return "", fmt.Errorf("nieznana zmienna {%s}", name)
		}
		b.WriteString(s[:i])
		b.WriteString(v)
		s = s[i+j+1:]
	}
}

// Abs turns a location into an absolute path on this machine.
func (r *Resolver) Abs(l Location) (string, error) {
	root, ok := r.Roots[l.Root]
	if !ok || root == "" {
		return "", fmt.Errorf("folder bazowy {%s} jest nieznany na tym komputerze", l.Root)
	}
	return AbsIn(root, l.Rel), nil
}

// AbsIn joins a clean relative path to an absolute root.
func AbsIn(root, rel string) string {
	if rel == "" {
		return filepath.Clean(root)
	}
	return filepath.Join(root, filepath.FromSlash(rel))
}

// AbsTemplate resolves a template straight to an absolute path.
func (r *Resolver) AbsTemplate(t string) (string, error) {
	l, err := r.Location(t)
	if err != nil {
		return "", err
	}
	return r.Abs(l)
}
