// Package testkit builds fake games, fake user folders and generated mod
// archives inside a test's temporary folder. Nothing here touches real
// game installs, real user folders or the network.
package testkit

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// Folders creates fake known folders (documents, AppData...) under base.
func Folders(t testing.TB, base string) map[gamedef.RootKind]string {
	t.Helper()
	out := map[gamedef.RootKind]string{}
	for k, name := range map[gamedef.RootKind]string{
		gamedef.RootDocuments: "Dokumenty użytkownika", gamedef.RootLocalAppData: "AppData/Local", gamedef.RootAppData: "AppData/Roaming",
		gamedef.RootLocalLow: "AppData/LocalLow", gamedef.RootUserProfile: "Profil", gamedef.RootSavedGames: "Zapisane gry",
	} {
		p := filepath.Join(base, filepath.FromSlash(name))
		if err := os.MkdirAll(p, 0o755); err != nil {
			t.Fatal(err)
		}
		out[k] = p
	}
	return out
}

// Game creates a fake install of a definition: its required files (and the
// first of anyOfFiles) with small fake contents.
func Game(t testing.TB, def *gamedef.Definition, dir string) {
	t.Helper()
	files := append([]string{}, def.Detection.RequiredFiles...)
	if len(def.Detection.AnyOfFiles) > 0 {
		files = append(files, def.Detection.AnyOfFiles[0])
	}
	for _, x := range def.Executables {
		if strings.HasPrefix(x.Path, "{game}/") && x.Default {
			files = append(files, strings.TrimPrefix(x.Path, "{game}/"))
		}
	}
	files = append(files, "vanilla/readme.txt")
	for _, f := range files {
		Write(t, dir, f, "oryginał "+f)
	}
}

// Write creates a file (and its folders).
func Write(t testing.TB, root, rel, content string) string {
	t.Helper()
	p := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	_ = os.Chmod(p, 0o644)
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

// Zip writes a zip archive with the given files (path -> content).
func Zip(t testing.TB, path string, files map[string]string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	w := zip.NewWriter(f)
	names := make([]string, 0, len(files))
	for n := range files {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		h := &zip.FileHeader{Name: n, Method: zip.Deflate}
		h.Modified = time.Date(2024, 5, 1, 12, 0, 0, 0, time.UTC)
		zw, err := w.CreateHeader(h)
		if err != nil {
			t.Fatal(err)
		}
		zw.Write([]byte(files[n]))
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}
	f.Close()
	return path
}

// Snapshot describes a folder tree: rel path -> sha256|ro (dirs as "dir").
func Snapshot(t testing.TB, root string) map[string]string {
	t.Helper()
	out := map[string]string{}
	filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		if d.IsDir() {
			out[rel+"/"] = "dir"
			return nil
		}
		b, _ := os.ReadFile(p)
		st, _ := os.Stat(p)
		h := sha256.Sum256(b)
		out[rel] = fmt.Sprintf("%s|ro=%v", hex.EncodeToString(h[:8]), st.Mode().Perm()&0o200 == 0)
		return nil
	})
	return out
}

// Diff lists the differences of two snapshots ("" when equal).
func Diff(a, b map[string]string) string {
	var d []string
	for k, v := range a {
		if b[k] != v {
			d = append(d, fmt.Sprintf("%s: %q -> %q", k, v, b[k]))
		}
	}
	for k, v := range b {
		if _, ok := a[k]; !ok {
			d = append(d, fmt.Sprintf("%s: (brak) -> %q", k, v))
		}
	}
	sort.Strings(d)
	return strings.Join(d, "\n")
}
