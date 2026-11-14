// Package backupzip makes and restores a full launcher backup (zip):
// data/config, data/games_saves, data/chat, images, custom_themes.
// Restore refuses entries outside these folders (zip-slip, absolute paths)
// and extracts to a staging folder before swapping, so a broken archive
// never leaves half-restored data.
package backupzip

import (
	"archive/zip"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"
)

// Roots included in a backup (relative to the launcher folder).
var Roots = []string{"data/config", "data/games_saves", "data/chat", "images", "custom_themes"}

// Manifest name inside the zip.
const Manifest = "GameLauncherBackup.txt"

// MaxEntry bounds one extracted file (zip bomb guard).
const MaxEntry = 2 << 30

func allowed(name string) bool {
	if name == Manifest {
		return true
	}
	for _, r := range Roots {
		if name == r || strings.HasPrefix(name, r+"/") {
			return true
		}
	}
	return false
}

// Create writes a backup of appDir to zipPath. Returns the file count.
func Create(appDir, zipPath, version string) (int, error) {
	tmp := zipPath + ".part"
	f, err := os.Create(tmp)
	if err != nil {
		return 0, err
	}
	zw := zip.NewWriter(f)
	n := 0
	fail := func(err error) (int, error) {
		zw.Close()
		f.Close()
		os.Remove(tmp)
		return 0, err
	}
	w, err := zw.Create(Manifest)
	if err != nil {
		return fail(err)
	}
	fmt.Fprintf(w, "Game Launcher backup\nversion=%s\ncreated=%s\n", version, time.Now().Format(time.RFC3339))
	for _, root := range Roots {
		abs := filepath.Join(appDir, filepath.FromSlash(root))
		if _, err := os.Stat(abs); err != nil {
			continue
		}
		err := filepath.WalkDir(abs, func(p string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			if d.IsDir() || !d.Type().IsRegular() {
				return nil
			}
			rel, err := filepath.Rel(appDir, p)
			if err != nil {
				return err
			}
			name := filepath.ToSlash(rel)
			if strings.HasSuffix(name, ".tmp") || strings.Contains(name, ".tmp-") || strings.HasSuffix(name, "-wal") || strings.HasSuffix(name, "-shm") {
				return nil
			}
			info, err := d.Info()
			if err != nil {
				return err
			}
			hdr, err := zip.FileInfoHeader(info)
			if err != nil {
				return err
			}
			hdr.Name = name
			hdr.Method = zip.Deflate
			zf, err := zw.CreateHeader(hdr)
			if err != nil {
				return err
			}
			src, err := os.Open(p)
			if err != nil {
				return err
			}
			_, err = io.Copy(zf, src)
			src.Close()
			n++
			return err
		})
		if err != nil {
			return fail(err)
		}
	}
	if err := zw.Close(); err != nil {
		f.Close()
		os.Remove(tmp)
		return 0, err
	}
	if err := f.Close(); err != nil {
		os.Remove(tmp)
		return 0, err
	}
	return n, os.Rename(tmp, zipPath)
}

// Restore extracts zipPath over appDir. Existing roots that are present in
// the archive are moved aside to <root>.before-restore-<ts> first (kept,
// not deleted). Returns the file count.
func Restore(appDir, zipPath string) (int, error) {
	zr, err := zip.OpenReader(zipPath)
	if err != nil {
		return 0, fmt.Errorf("to nie jest poprawne archiwum zip: %v", err)
	}
	defer zr.Close()
	hasManifest := false
	for _, f := range zr.File {
		if f.Name == Manifest {
			hasManifest = true
		}
		clean := path.Clean(strings.ReplaceAll(f.Name, `\`, "/"))
		if clean != f.Name && !(strings.HasSuffix(f.Name, "/") && clean+"/" == f.Name) || strings.HasPrefix(clean, "../") || strings.HasPrefix(clean, "/") || strings.Contains(clean, ":") {
			return 0, fmt.Errorf("niebezpieczna ścieżka w archiwum: %q", f.Name)
		}
		if !allowed(strings.TrimSuffix(clean, "/")) {
			return 0, fmt.Errorf("archiwum zawiera nieoczekiwany plik: %q", f.Name)
		}
	}
	if !hasManifest {
		return 0, errors.New("to nie jest kopia Game Launchera (brak " + Manifest + ")")
	}
	stage, err := os.MkdirTemp(appDir, ".restore-")
	if err != nil {
		return 0, err
	}
	defer os.RemoveAll(stage)
	n := 0
	present := map[string]bool{}
	for _, f := range zr.File {
		if f.FileInfo().IsDir() || f.Name == Manifest {
			continue
		}
		if f.UncompressedSize64 > MaxEntry {
			return 0, fmt.Errorf("plik %s jest za duży", f.Name)
		}
		for _, r := range Roots {
			if strings.HasPrefix(f.Name, r+"/") {
				present[r] = true
			}
		}
		dst := filepath.Join(stage, filepath.FromSlash(f.Name))
		if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
			return 0, err
		}
		rc, err := f.Open()
		if err != nil {
			return 0, err
		}
		out, err := os.Create(dst)
		if err != nil {
			rc.Close()
			return 0, err
		}
		written, err := io.Copy(out, io.LimitReader(rc, MaxEntry+1))
		rc.Close()
		out.Close()
		if err != nil {
			return 0, err
		}
		if written > MaxEntry {
			return 0, fmt.Errorf("plik %s jest za duży", f.Name)
		}
		n++
	}
	ts := time.Now().Format("20060102-150405")
	for _, r := range Roots {
		if !present[r] {
			continue
		}
		target := filepath.Join(appDir, filepath.FromSlash(r))
		if _, err := os.Stat(target); err == nil {
			if err := os.Rename(target, target+".before-restore-"+ts); err != nil {
				return 0, fmt.Errorf("nie można odłożyć %s: %v", r, err)
			}
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return 0, err
		}
		if err := os.Rename(filepath.Join(stage, filepath.FromSlash(r)), target); err != nil {
			_ = os.Rename(target+".before-restore-"+ts, target)
			return 0, err
		}
	}
	return n, nil
}
