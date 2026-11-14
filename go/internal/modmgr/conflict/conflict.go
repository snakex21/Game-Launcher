// Package conflict builds the file-level conflict index of a profile: for
// every target path the list of enabled mods that provide it, and the
// winner (a per-file override first, then the last mod in profile order;
// the game's own files always lose and are backed up).
package conflict

import (
	"sort"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// File is one file a mod provides, already resolved to its target.
type File struct {
	Target gamedef.Location
	Type   string
	Rel    string // inside the type (store path)
	SHA256 string
	Size   int64
}

// Mod is one mod in profile order.
type Mod struct {
	ID      string
	Name    string
	Enabled bool
	Files   []File
}

// Provider is one mod offering a target path.
type Provider struct {
	ModID  string `json:"modId"`
	Name   string `json:"name"`
	Order  int    `json:"order"`
	SHA256 string `json:"sha256"`
	Size   int64  `json:"size"`
	file   File
}

// Entry is one target path.
type Entry struct {
	Key        string           `json:"key"`
	Target     gamedef.Location `json:"target"`
	Providers  []Provider       `json:"providers"` // profile order
	Winner     string           `json:"winner"`
	Rule       string           `json:"rule"` // priority|override
	Identical  bool             `json:"identical"`
	winnerFile File
}

// Conflicted reports whether more than one mod provides the path.
func (e *Entry) Conflicted() bool { return len(e.Providers) > 1 }

// WinnerFile is the file that gets deployed.
func (e *Entry) WinnerFile() File { return e.winnerFile }

// Summary counts a mod's conflicts.
type Summary struct {
	Wins       int `json:"wins"`
	Loses      int `json:"loses"`
	Identical  int `json:"identical"`
	ByOverride int `json:"overriddenByRule"`
}

// Index is the conflict index of one profile.
type Index struct {
	Entries map[string]*Entry
	order   []string
}

// Build indexes the enabled mods. overrides maps a target key to the mod
// that must win it (ignored when that mod is disabled or does not provide
// the path).
func Build(mods []Mod, overrides map[string]string) *Index {
	idx := &Index{Entries: map[string]*Entry{}}
	for i, m := range mods {
		if !m.Enabled {
			continue
		}
		for _, f := range m.Files {
			k := f.Target.Key()
			e := idx.Entries[k]
			if e == nil {
				e = &Entry{Key: k, Target: f.Target}
				idx.Entries[k] = e
				idx.order = append(idx.order, k)
			}
			// one mod providing the same target twice (two types): last wins
			replaced := false
			for j := range e.Providers {
				if e.Providers[j].ModID == m.ID {
					e.Providers[j] = Provider{ModID: m.ID, Name: m.Name, Order: i, SHA256: f.SHA256, Size: f.Size, file: f}
					replaced = true
				}
			}
			if !replaced {
				e.Providers = append(e.Providers, Provider{ModID: m.ID, Name: m.Name, Order: i, SHA256: f.SHA256, Size: f.Size, file: f})
			}
		}
	}
	for _, k := range idx.order {
		e := idx.Entries[k]
		win := len(e.Providers) - 1
		e.Rule = "priority"
		if want, ok := overrides[k]; ok {
			for j, p := range e.Providers {
				if p.ModID == want {
					win = j
					if j != len(e.Providers)-1 {
						e.Rule = "override"
					}
				}
			}
		}
		e.Winner = e.Providers[win].ModID
		e.winnerFile = e.Providers[win].file
		e.Identical = len(e.Providers) > 1
		for _, p := range e.Providers {
			if p.SHA256 != e.Providers[0].SHA256 {
				e.Identical = false
			}
		}
	}
	sort.Strings(idx.order)
	return idx
}

// Keys returns the target keys, sorted.
func (x *Index) Keys() []string { return x.order }

// Conflicts lists the paths with more than one provider.
func (x *Index) Conflicts() []*Entry {
	var out []*Entry
	for _, k := range x.order {
		if e := x.Entries[k]; e.Conflicted() {
			out = append(out, e)
		}
	}
	return out
}

// Summaries counts wins/losses per mod.
func (x *Index) Summaries() map[string]Summary {
	out := map[string]Summary{}
	for _, k := range x.order {
		e := x.Entries[k]
		if !e.Conflicted() {
			continue
		}
		for _, p := range e.Providers {
			s := out[p.ModID]
			switch {
			case e.Identical:
				s.Identical++
			case p.ModID == e.Winner:
				s.Wins++
				if e.Rule == "override" {
					s.ByOverride++
				}
			default:
				s.Loses++
			}
			out[p.ModID] = s
		}
	}
	return out
}

// ForMod lists the conflicted entries a mod takes part in.
func (x *Index) ForMod(modID string) []*Entry {
	var out []*Entry
	for _, e := range x.Conflicts() {
		for _, p := range e.Providers {
			if p.ModID == modID {
				out = append(out, e)
				break
			}
		}
	}
	return out
}

// CleanOverrides drops rules pointing to mods that no longer provide the path.
func CleanOverrides(mods []Mod, overrides map[string]string) map[string]string {
	provides := map[string]map[string]bool{}
	for _, m := range mods {
		for _, f := range m.Files {
			k := f.Target.Key()
			if provides[k] == nil {
				provides[k] = map[string]bool{}
			}
			provides[k][m.ID] = true
		}
	}
	out := map[string]string{}
	for k, id := range overrides {
		if provides[k][id] {
			out[k] = id
		}
	}
	return out
}
