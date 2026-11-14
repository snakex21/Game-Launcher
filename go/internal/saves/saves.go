// Package saves manages save-game backups in the Python launcher's layout:
//
//	data/games_saves/<game>/saves/Save_<pct>%_<YYYYmmdd_HHMMSS>/   manual
//	data/games_saves/<game>/_autosave/                              automatic
//
// A backup is a copy of the game's save_path folder.
package saves

import (
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// AutosaveID identifies the automatic backup.
const AutosaveID = "_autosave_"

// Entry is one backup.
type Entry struct {
	ID       string  `json:"id"` // folder name, or AutosaveID
	Name     string  `json:"name"`
	Percent  int     `json:"percent"`
	Modified float64 `json:"modified"` // unix seconds
	Auto     bool    `json:"auto"`
	Files    int     `json:"files"`
	Bytes    int64   `json:"bytes"`
}

var (
	pctRe      = regexp.MustCompile(`Save_(\d+)%`)
	invalidDir = regexp.MustCompile(`[\\/:*?"<>|]`)
)

// GameDir returns the backup folder of a game (the raw game name, like the
// Python version; characters Windows forbids are replaced).
func GameDir(root, game string) string {
	return filepath.Join(root, strings.TrimRight(invalidDir.ReplaceAllString(game, "_"), ". "))
}

func validID(id string) error {
	if id == "" || id == "." || id == ".." || strings.ContainsAny(id, `\/:`) {
		return errors.New("nieprawidłowa nazwa zapisu")
	}
	return nil
}

func dirPath(root, game, id string) (string, error) {
	if id == AutosaveID {
		return filepath.Join(GameDir(root, game), "_autosave"), nil
	}
	if err := validID(id); err != nil {
		return "", err
	}
	return filepath.Join(GameDir(root, game), "saves", id), nil
}

func stats(dir string) (files int, size int64) {
	_ = filepath.WalkDir(dir, func(_ string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() {
			files++
			if info, err := d.Info(); err == nil {
				size += info.Size()
			}
		}
		return nil
	})
	return
}

// List returns the autosave first, then manual saves newest first.
func List(root, game string) ([]Entry, error) {
	var out []Entry
	base := GameDir(root, game)
	if st, err := os.Stat(filepath.Join(base, "_autosave")); err == nil && st.IsDir() {
		f, b := stats(filepath.Join(base, "_autosave"))
		out = append(out, Entry{ID: AutosaveID, Name: "Automatyczny zapis", Modified: float64(st.ModTime().Unix()), Auto: true, Files: f, Bytes: b})
	}
	entries, err := os.ReadDir(filepath.Join(base, "saves"))
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return out, err
	}
	var manual []Entry
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		info, err := e.Info()
		var mod float64
		if err == nil {
			mod = float64(info.ModTime().Unix())
		}
		pct := 0
		if m := pctRe.FindStringSubmatch(e.Name()); m != nil {
			pct, _ = strconv.Atoi(m[1])
		}
		f, b := stats(filepath.Join(base, "saves", e.Name()))
		manual = append(manual, Entry{ID: e.Name(), Name: e.Name(), Percent: pct, Modified: mod, Files: f, Bytes: b})
	}
	sort.SliceStable(manual, func(i, j int) bool {
		if manual[i].Modified != manual[j].Modified {
			return manual[i].Modified > manual[j].Modified
		}
		return manual[i].Percent > manual[j].Percent
	})
	return append(out, manual...), nil
}

// CopyTree copies src into dst (merging, overwriting files).
func CopyTree(src, dst string) (int, error) {
	n := 0
	err := filepath.WalkDir(src, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, p)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		if !d.Type().IsRegular() {
			return nil // skip links/devices
		}
		if err := copyFile(p, target); err != nil {
			return err
		}
		n++
		return nil
	})
	return n, err
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	info, err := in.Stat()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return err
	}
	if err := out.Close(); err != nil {
		return err
	}
	return os.Chtimes(dst, info.ModTime(), info.ModTime())
}

func checkSource(savePath string) error {
	if savePath == "" {
		return errors.New("gra nie ma ustawionego folderu zapisów (edytuj grę)")
	}
	st, err := os.Stat(savePath)
	if err != nil || !st.IsDir() {
		return fmt.Errorf("folder zapisów gry nie istnieje: %s", savePath)
	}
	return nil
}

// Create copies savePath to a new manual backup.
func Create(root, game, savePath string, percent int, now time.Time) (Entry, error) {
	if err := checkSource(savePath); err != nil {
		return Entry{}, err
	}
	if percent < 0 || percent > 100 {
		return Entry{}, errors.New("procent musi być w zakresie 0–100")
	}
	id := fmt.Sprintf("Save_%d%%_%s", percent, now.Format("20060102_150405"))
	dst := filepath.Join(GameDir(root, game), "saves", id)
	if _, err := os.Stat(dst); err == nil {
		return Entry{}, fmt.Errorf("zapis „%s” już istnieje", id)
	}
	if _, err := CopyTree(savePath, dst); err != nil {
		_ = os.RemoveAll(dst)
		return Entry{}, err
	}
	f, b := stats(dst)
	return Entry{ID: id, Name: id, Percent: percent, Modified: float64(now.Unix()), Files: f, Bytes: b}, nil
}

// Autosave replaces _autosave with a fresh copy of savePath (copy to a temp
// folder first, so a failed copy never destroys the previous autosave).
func Autosave(root, game, savePath string) (int, error) {
	if err := checkSource(savePath); err != nil {
		return 0, err
	}
	base := GameDir(root, game)
	if err := os.MkdirAll(base, 0o755); err != nil {
		return 0, err
	}
	tmp, err := os.MkdirTemp(base, "_autosave.tmp-")
	if err != nil {
		return 0, err
	}
	n, err := CopyTree(savePath, tmp)
	if err != nil {
		os.RemoveAll(tmp)
		return 0, err
	}
	final := filepath.Join(base, "_autosave")
	old := final + ".old"
	_ = os.RemoveAll(old)
	if _, err := os.Stat(final); err == nil {
		if err := os.Rename(final, old); err != nil {
			os.RemoveAll(tmp)
			return 0, err
		}
	}
	if err := os.Rename(tmp, final); err != nil {
		_ = os.Rename(old, final)
		return 0, err
	}
	_ = os.RemoveAll(old)
	now := time.Now()
	_ = os.Chtimes(final, now, now)
	return n, nil
}

// Restore copies a backup over savePath. The current saves are first kept
// as a manual backup "Save_<pct>%_<ts>_przed_wczytaniem" so a restore can
// be undone.
func Restore(root, game, id, savePath string, now time.Time) (string, error) {
	src, err := dirPath(root, game, id)
	if err != nil {
		return "", err
	}
	if st, err := os.Stat(src); err != nil || !st.IsDir() {
		return "", fmt.Errorf("kopia „%s” nie istnieje", id)
	}
	if savePath == "" {
		return "", errors.New("gra nie ma ustawionego folderu zapisów")
	}
	safety := ""
	if st, err := os.Stat(savePath); err == nil && st.IsDir() {
		safety = fmt.Sprintf("Save_0%%_%s_przed_wczytaniem", now.Format("20060102_150405"))
		if _, err := CopyTree(savePath, filepath.Join(GameDir(root, game), "saves", safety)); err != nil {
			return "", fmt.Errorf("nie udało się zabezpieczyć obecnych zapisów: %v", err)
		}
	}
	if _, err := CopyTree(src, savePath); err != nil {
		return safety, err
	}
	return safety, nil
}

// Delete removes a backup.
func Delete(root, game, id string) error {
	p, err := dirPath(root, game, id)
	if err != nil {
		return err
	}
	if _, err := os.Stat(p); err != nil {
		return fmt.Errorf("kopia „%s” nie istnieje", id)
	}
	return os.RemoveAll(p)
}

// SetPercent renames a manual backup to a new percentage, keeping its time stamp.
func SetPercent(root, game, id string, percent int) (string, error) {
	if id == AutosaveID {
		return "", errors.New("nie można zmienić automatycznego zapisu")
	}
	if percent < 0 || percent > 100 {
		return "", errors.New("procent musi być w zakresie 0–100")
	}
	p, err := dirPath(root, game, id)
	if err != nil {
		return "", err
	}
	stamp := regexp.MustCompile(`\d{8}_\d{6}`).FindString(id)
	if stamp == "" {
		stamp = time.Now().Format("20060102_150405")
	}
	newID := fmt.Sprintf("Save_%d%%_%s", percent, stamp)
	if newID == id {
		return id, nil
	}
	np := filepath.Join(filepath.Dir(p), newID)
	if _, err := os.Stat(np); err == nil {
		return "", fmt.Errorf("zapis „%s” już istnieje", newID)
	}
	return newID, os.Rename(p, np)
}
