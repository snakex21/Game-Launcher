// Package modstore keeps installed mods outside the game folder:
//
//	<root>/store/<gameKey>/<modId>/mod.json
//	<root>/store/<gameKey>/<modId>/files/<modType>/<path...>
//	<root>/downloads/<gameKey>/<modId>-<archive name>   (original archive)
//
// A mod is extracted into store/<gameKey>/.tmp-<id> and renamed into place
// only when complete, so an interrupted import leaves no half mod (leftover
// .tmp-* folders are removed by CleanupTemp). Stored files are read-only.
package modstore

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/archive"
	"github.com/snakex21/game-launcher/go/internal/modmgr/fsx"
	"github.com/snakex21/game-launcher/go/internal/modmgr/ids"
	"github.com/snakex21/game-launcher/go/internal/modmgr/install"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// File is one stored file.
type File struct {
	Type   string `json:"type"`
	Rel    string `json:"rel"`
	Size   int64  `json:"size"`
	SHA256 string `json:"sha256"`
}

// SourceInfo describes where the mod came from.
type SourceInfo struct {
	Kind   string `json:"kind"` // zip|7z|folder|file
	Name   string `json:"name"`
	SHA256 string `json:"sha256,omitempty"`
	Size   int64  `json:"size,omitempty"`
}

// Mod is mod.json.
type Mod struct {
	FormatVersion     int        `json:"formatVersion"`
	ID                string     `json:"id"`
	GameKey           string     `json:"gameKey"`
	Name              string     `json:"name"`
	Version           string     `json:"version,omitempty"`
	Source            SourceInfo `json:"source"`
	Installed         time.Time  `json:"installed"`
	Root              string     `json:"root"`
	ModType           string     `json:"modType"`
	Format            string     `json:"format"`
	Files             []File     `json:"files"`
	ExecutableContent bool       `json:"executableContent"`
	ExecutableFiles   []string   `json:"executableFiles,omitempty"`
	ExecAcknowledged  bool       `json:"execAcknowledged,omitempty"`
	Archive           string     `json:"archive,omitempty"` // file name in downloads/<gameKey>
	Warnings          []string   `json:"warnings,omitempty"`
}

// TotalSize is the sum of file sizes.
func (m *Mod) TotalSize() int64 {
	var n int64
	for _, f := range m.Files {
		n += f.Size
	}
	return n
}

// Store is the mod store.
type Store struct {
	Root   string
	Limits archive.Limits
	// FreeSpace reports free bytes for a folder (nil = not checked).
	FreeSpace func(string) (int64, error)
	// KeepArchives copies source archives into downloads/.
	KeepArchives bool
}

// New opens the store under root (created on demand).
func New(root string) *Store {
	return &Store{Root: root, Limits: archive.DefaultLimits, FreeSpace: fsx.FreeSpace, KeepArchives: true}
}

// ErrDuplicate is returned when the same archive is already installed.
type ErrDuplicate struct{ Existing *Mod }

func (e *ErrDuplicate) Error() string {
	return fmt.Sprintf("to archiwum jest już zainstalowane jako „%s”", e.Existing.Name)
}

// ErrNotFound means the mod does not exist.
var ErrNotFound = errors.New("mod nie istnieje w magazynie")

func checkKey(gameKey string) error {
	if gameKey == "" || strings.ContainsAny(gameKey, `/\:*?"<>|`) || strings.Contains(gameKey, "..") {
		return fmt.Errorf("nieprawidłowy klucz gry %q", gameKey)
	}
	return nil
}

func (s *Store) gameDir(gameKey string) string { return filepath.Join(s.Root, "store", gameKey) }

// ModDir is the folder of a mod.
func (s *Store) ModDir(gameKey, id string) string { return filepath.Join(s.gameDir(gameKey), id) }

// FilePath is the absolute path of a stored file.
func (s *Store) FilePath(gameKey, id, typ, rel string) string {
	return filepath.Join(s.ModDir(gameKey, id), "files", typ, filepath.FromSlash(rel))
}

// ImportOptions control Import.
type ImportOptions struct {
	AllowDuplicate bool
	Version        string
}

// Import extracts the planned files of src into the store.
func (s *Store) Import(gameKey string, src archive.Source, srcPath string, plan *install.Plan, opt ImportOptions) (*Mod, error) {
	if err := checkKey(gameKey); err != nil {
		return nil, err
	}
	info := SourceInfo{Kind: src.Kind(), Name: filepath.Base(srcPath)}
	if src.Kind() != "folder" {
		sum, size, err := archive.HashFile(srcPath)
		if err != nil {
			return nil, err
		}
		info.SHA256, info.Size = sum, size
		if !opt.AllowDuplicate {
			mods, _ := s.List(gameKey)
			for _, m := range mods {
				if m.Source.SHA256 == sum {
					return nil, &ErrDuplicate{Existing: m}
				}
			}
		}
	}
	id := ids.New()
	tmp := filepath.Join(s.gameDir(gameKey), ".tmp-"+id)
	if err := os.MkdirAll(tmp, 0o755); err != nil {
		return nil, err
	}
	ok := false
	defer func() {
		if !ok {
			fsx.RemoveAll(tmp)
		}
	}()
	byPath := map[string]archive.Entry{}
	for _, e := range src.Entries() {
		byPath[e.Path] = e
	}
	jobs := make([]archive.Job, 0, len(plan.Files))
	dests := map[string]bool{}
	for _, f := range plan.Files {
		e, found := byPath[f.Source]
		if !found {
			return nil, fmt.Errorf("w źródle nie ma pliku %s", f.Source)
		}
		dest := relpath.Join("files", f.ModType, f.Rel)
		if dests[relpath.Key(dest)] {
			return nil, fmt.Errorf("dwa pliki moda trafiłyby w to samo miejsce: %s", f.Rel)
		}
		dests[relpath.Key(dest)] = true
		jobs = append(jobs, archive.Job{Entry: e, Dest: dest})
	}
	written, err := archive.Extract(src, jobs, tmp, s.Limits, s.FreeSpace)
	if err != nil {
		return nil, err
	}
	m := &Mod{
		FormatVersion: 1, ID: id, GameKey: gameKey, Name: plan.ModName, Version: plan.Version,
		Source: info, Installed: time.Now().UTC().Truncate(time.Second), Root: plan.Root, ModType: plan.ModType, Format: plan.Format,
		ExecutableContent: plan.ExecutableContent, ExecutableFiles: plan.ExecutableFiles, Warnings: plan.Warnings,
	}
	if opt.Version != "" {
		m.Version = opt.Version
	}
	for i, w := range written {
		f := plan.Files[i]
		m.Files = append(m.Files, File{Type: f.ModType, Rel: f.Rel, Size: w.Size, SHA256: w.SHA256})
	}
	if s.KeepArchives && src.Kind() != "folder" {
		name := id + "-" + safeName(filepath.Base(srcPath))
		dl := filepath.Join(s.Root, "downloads", gameKey)
		if err := copyVerified(srcPath, filepath.Join(dl, name), info.SHA256); err != nil {
			return nil, fmt.Errorf("kopia archiwum: %w", err)
		}
		m.Archive = name
	}
	if err := fsx.WriteJSONAtomic(filepath.Join(tmp, "mod.json"), m); err != nil {
		return nil, err
	}
	final := s.ModDir(gameKey, id)
	if err := os.Rename(tmp, final); err != nil {
		if m.Archive != "" {
			os.Remove(filepath.Join(s.Root, "downloads", gameKey, m.Archive))
		}
		return nil, err
	}
	ok = true
	s.protect(m)
	return m, nil
}

func safeName(n string) string {
	return strings.Map(func(r rune) rune {
		if r < 0x20 || strings.ContainsRune(`<>:"/\|?*`, r) {
			return '_'
		}
		return r
	}, n)
}

func copyVerified(src, dst, wantSHA string) error {
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	tmp := dst + ".part"
	out, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o644)
	if err != nil {
		return err
	}
	h := sha256.New()
	_, err = io.Copy(io.MultiWriter(out, h), in)
	if err == nil {
		err = out.Sync()
	}
	if cerr := out.Close(); err == nil {
		err = cerr
	}
	if err == nil && hex.EncodeToString(h.Sum(nil)) != wantSHA {
		err = errors.New("archiwum zmieniło się w trakcie kopiowania")
	}
	if err != nil {
		os.Remove(tmp)
		return err
	}
	return os.Rename(tmp, dst)
}

// protect marks the stored files read-only (hardlinks share the attribute,
// so writes "through" a link fail instead of changing the store).
func (s *Store) protect(m *Mod) {
	for _, f := range m.Files {
		_ = os.Chmod(s.FilePath(m.GameKey, m.ID, f.Type, f.Rel), 0o444)
	}
}

// Protect re-applies the read-only attribute (after a deployment that had
// to clear it on a hardlink).
func (s *Store) Protect(gameKey, id string) {
	if m, err := s.Get(gameKey, id); err == nil {
		s.protect(m)
	}
}

// Get loads mod.json.
func (s *Store) Get(gameKey, id string) (*Mod, error) {
	if err := checkKey(gameKey); err != nil {
		return nil, err
	}
	if !ids.Valid(id) {
		return nil, ErrNotFound
	}
	b, err := os.ReadFile(filepath.Join(s.ModDir(gameKey, id), "mod.json"))
	if errors.Is(err, os.ErrNotExist) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	var m Mod
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, fmt.Errorf("uszkodzony mod.json (%s): %w", id, err)
	}
	if m.ID != id {
		return nil, fmt.Errorf("mod.json (%s) ma inne id", id)
	}
	return &m, nil
}

// Save rewrites mod.json (name/version/flags edits).
func (s *Store) Save(m *Mod) error {
	if _, err := s.Get(m.GameKey, m.ID); err != nil {
		return err
	}
	return fsx.WriteJSONAtomic(filepath.Join(s.ModDir(m.GameKey, m.ID), "mod.json"), m)
}

// List returns the mods of a game, oldest first.
func (s *Store) List(gameKey string) ([]*Mod, error) {
	if err := checkKey(gameKey); err != nil {
		return nil, err
	}
	ents, err := os.ReadDir(s.gameDir(gameKey))
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var out []*Mod
	for _, e := range ents {
		if !e.IsDir() || !ids.Valid(e.Name()) {
			continue
		}
		m, err := s.Get(gameKey, e.Name())
		if err != nil {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out, nil
}

// Remove deletes a mod and its archive copy.
func (s *Store) Remove(gameKey, id string) error {
	m, err := s.Get(gameKey, id)
	if err != nil {
		return err
	}
	// rename first so a half-deleted mod never looks valid
	dir := s.ModDir(gameKey, id)
	trash := filepath.Join(s.gameDir(gameKey), ".del-"+id)
	if err := os.Rename(dir, trash); err != nil {
		return err
	}
	if m.Archive != "" {
		os.Remove(filepath.Join(s.Root, "downloads", gameKey, m.Archive))
	}
	return fsx.RemoveAll(trash)
}

// CleanupTemp removes leftovers of interrupted imports and removals.
func (s *Store) CleanupTemp() []string {
	var removed []string
	games, _ := os.ReadDir(filepath.Join(s.Root, "store"))
	for _, g := range games {
		if !g.IsDir() {
			continue
		}
		ents, _ := os.ReadDir(filepath.Join(s.Root, "store", g.Name()))
		for _, e := range ents {
			if e.IsDir() && (strings.HasPrefix(e.Name(), ".tmp-") || strings.HasPrefix(e.Name(), ".del-")) {
				p := filepath.Join(s.Root, "store", g.Name(), e.Name())
				if fsx.RemoveAll(p) == nil {
					removed = append(removed, p)
				}
			}
		}
	}
	dls, _ := filepath.Glob(filepath.Join(s.Root, "downloads", "*", "*.part"))
	for _, p := range dls {
		if os.Remove(p) == nil {
			removed = append(removed, p)
		}
	}
	return removed
}

// Problem is a stored file that is missing or changed.
type Problem struct {
	Rel    string `json:"rel"`
	Reason string `json:"reason"`
}

// Verify checks sizes and hashes of the stored files.
func (s *Store) Verify(gameKey, id string) ([]Problem, error) {
	m, err := s.Get(gameKey, id)
	if err != nil {
		return nil, err
	}
	var out []Problem
	for _, f := range m.Files {
		p := s.FilePath(gameKey, id, f.Type, f.Rel)
		sum, size, err := archive.HashFile(p)
		switch {
		case err != nil:
			out = append(out, Problem{Rel: f.Rel, Reason: "brak pliku"})
		case size != f.Size || sum != f.SHA256:
			out = append(out, Problem{Rel: f.Rel, Reason: "plik zmieniony"})
		}
	}
	return out, nil
}

// Repair re-extracts changed/missing files from the kept archive.
func (s *Store) Repair(gameKey, id string, def func(entries []archive.Entry) (*install.Plan, error)) error {
	m, err := s.Get(gameKey, id)
	if err != nil {
		return err
	}
	if m.Archive == "" {
		return errors.New("brak kopii archiwum – zainstaluj mod ponownie")
	}
	src, err := archive.Open(filepath.Join(s.Root, "downloads", gameKey, m.Archive))
	if err != nil {
		return err
	}
	defer src.Close()
	plan, err := def(src.Entries())
	if err != nil {
		return err
	}
	tmp := filepath.Join(s.gameDir(gameKey), ".tmp-"+ids.New())
	defer fsx.RemoveAll(tmp)
	byPath := map[string]archive.Entry{}
	for _, e := range src.Entries() {
		byPath[e.Path] = e
	}
	want := map[string]File{}
	for _, f := range m.Files {
		want[f.Type+"/"+f.Rel] = f
	}
	var jobs []archive.Job
	for _, f := range plan.Files {
		if _, ok := want[f.ModType+"/"+f.Rel]; ok {
			jobs = append(jobs, archive.Job{Entry: byPath[f.Source], Dest: relpath.Join(f.ModType, f.Rel)})
		}
	}
	got, err := archive.Extract(src, jobs, tmp, s.Limits, s.FreeSpace)
	if err != nil {
		return err
	}
	for _, g := range got {
		parts := strings.SplitN(g.Path, "/", 2)
		w := want[g.Path]
		if g.SHA256 != w.SHA256 {
			return fmt.Errorf("archiwum nie zawiera oryginalnej wersji pliku %s", w.Rel)
		}
		dst := s.FilePath(gameKey, id, parts[0], parts[1])
		_ = os.Chmod(dst, 0o644)
		if err := fsx.ReplaceFile(filepath.Join(tmp, filepath.FromSlash(g.Path)), dst); err != nil {
			return err
		}
	}
	s.protect(m)
	return nil
}
