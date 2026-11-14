// Package paths holds the launcher folder and the portable game paths.
//
// It is a port of launcher/paths.py (v1.5.0) and keeps its on-disk format:
//
//   - The app folder (AppDir) is the folder of the exe, independent of the
//     current working directory. It holds data/, images/ and so on.
//   - Game paths on the same drive as the launcher are stored in config.json
//     without the drive letter ("\Gry\Gothic\Gothic.exe"); games inside the
//     launcher folder are stored relative to it ("Gry\Gothic\Gothic.exe").
//     After the USB drive gets another letter (E: -> F:) they resolve against
//     the new letter.
//   - Absolute paths that still carry the letter of the drive the launcher
//     used to live on (settings.launcher_drive) are remapped to the new one.
//
// All path logic uses Windows semantics explicitly (independent of the OS
// the tests run on).
package paths

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

// AppDir returns the launcher folder: GL_APP_DIR when set (tests, dev
// runs), otherwise the folder of the executable.
func AppDir() string {
	if d := strings.TrimSpace(os.Getenv("GL_APP_DIR")); d != "" {
		if abs, err := filepath.Abs(d); err == nil {
			return abs
		}
		return d
	}
	exe, err := os.Executable()
	if err != nil {
		wd, _ := os.Getwd()
		return wd
	}
	if r, err := filepath.EvalSymlinks(exe); err == nil {
		exe = r
	}
	return filepath.Dir(exe)
}

// ------------------------------------------------------------ Windows paths

func isSep(c byte) bool { return c == '\\' || c == '/' }

// splitDrive mirrors ntpath.splitdrive: "C:" or "\\server\share".
func splitDrive(p string) (drive, rest string) {
	if len(p) >= 2 && p[1] == ':' && isLetter(p[0]) {
		return p[:2], p[2:]
	}
	if len(p) >= 2 && isSep(p[0]) && isSep(p[1]) && (len(p) == 2 || !isSep(p[2])) {
		// UNC: \\server\share
		rest := p[2:]
		i := strings.IndexAny(rest, `\/`)
		if i < 0 {
			return p, ""
		}
		j := strings.IndexAny(rest[i+1:], `\/`)
		if j < 0 {
			return p, ""
		}
		end := 2 + i + 1 + j
		return p[:end], p[end:]
	}
	return "", p
}

func isLetter(c byte) bool { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') }

// DriveOf returns "E:" (upper case) or "" for UNC / relative paths.
func DriveOf(p string) string {
	if p == "" {
		return ""
	}
	d, _ := splitDrive(p)
	if len(d) == 2 && d[1] == ':' {
		return strings.ToUpper(d)
	}
	return ""
}

// IsDriveRelative reports "\Gry\x.exe": rooted but without a drive letter.
func IsDriveRelative(p string) bool {
	if p == "" {
		return false
	}
	d, _ := splitDrive(p)
	return d == "" && isSep(p[0]) && !(len(p) >= 2 && isSep(p[1]))
}

func isUNC(p string) bool { return len(p) >= 2 && isSep(p[0]) && isSep(p[1]) }

// NormPath is ntpath.normpath: unify separators, collapse "." and "..".
func NormPath(p string) string {
	if p == "" {
		return "."
	}
	p = strings.ReplaceAll(p, "/", `\`)
	drive, rest := splitDrive(p)
	prefix := ""
	if strings.HasPrefix(rest, `\`) {
		prefix = `\`
		rest = strings.TrimLeft(rest, `\`)
	}
	var out []string
	for _, part := range strings.Split(rest, `\`) {
		switch part {
		case "", ".":
			continue
		case "..":
			if len(out) > 0 && out[len(out)-1] != ".." {
				out = out[:len(out)-1]
			} else if prefix == "" {
				out = append(out, "..")
			}
		default:
			out = append(out, part)
		}
	}
	res := drive + prefix + strings.Join(out, `\`)
	if res == "" {
		return "."
	}
	return res
}

// Join is ntpath.join for the cases the launcher needs.
func Join(base string, elems ...string) string {
	res := base
	for _, e := range elems {
		if e == "" {
			continue
		}
		if DriveOf(e) != "" || isUNC(e) {
			res = e
			continue
		}
		if isSep(e[0]) {
			res = DriveOf(res) + e
			continue
		}
		if res != "" && !isSep(res[len(res)-1]) {
			res += `\`
		}
		res += e
	}
	return res
}

func hasPrefixFold(s, prefix string) bool {
	return len(s) >= len(prefix) && strings.EqualFold(s[:len(prefix)], prefix)
}

// ToPortable converts a path for storing in config.json: on the launcher's
// drive it drops the drive letter (or becomes relative to the launcher
// folder); other drives, UNC and relative paths stay as they are (with
// normalised separators).
func ToPortable(p, appDir string) string {
	if p == "" {
		return p
	}
	appDrive := DriveOf(appDir)
	pathDrive := DriveOf(p)
	if pathDrive == "" {
		if IsDriveRelative(p) {
			return NormPath(p)
		}
		return p
	}
	normalized := NormPath(p)
	if appDrive != "" && pathDrive == appDrive {
		appNorm := strings.TrimRight(NormPath(appDir), `\`)
		if hasPrefixFold(normalized, appNorm+`\`) {
			return normalized[len(appNorm)+1:]
		}
		return normalized[2:]
	}
	return normalized
}

// Resolve converts a stored path into an absolute path for the current
// launcher location.
func Resolve(p, appDir string) string {
	if p == "" {
		return p
	}
	if IsDriveRelative(p) {
		if d := DriveOf(appDir); d != "" {
			return NormPath(d + p)
		}
		return NormPath(p)
	}
	if DriveOf(p) != "" || isUNC(p) {
		return NormPath(p)
	}
	if strings.HasPrefix(p, "%") || strings.HasPrefix(p, "~") {
		return p // environment variables / home folder: untouched
	}
	return NormPath(Join(appDir, p))
}

// RemapDrive replaces the drive letter oldDrive with newDrive.
func RemapDrive(p, oldDrive, newDrive string) string {
	if p == "" || oldDrive == "" || newDrive == "" {
		return p
	}
	if DriveOf(p) == strings.ToUpper(oldDrive) {
		return strings.ToUpper(newDrive) + NormPath(p)[2:]
	}
	return p
}

// ------------------------------------------------------- whole-config ops

// Keys that hold paths (same as paths.py).
var (
	GamePathKeys     = []string{"exe_path", "rom_path", "save_path"}
	ProfilePathKeys  = []string{"exe_path"}
	EmulatorPathKeys = []string{"path"}
)

type slot struct {
	o   *ojson.Object
	key string
}

func pathSlots(cfg *ojson.Object) []slot {
	var out []slot
	add := func(o *ojson.Object, keys []string) {
		for _, k := range keys {
			if s, ok := o.Get(k).(string); ok && s != "" {
				out = append(out, slot{o, k})
			}
		}
	}
	if games := cfg.Obj("games"); games != nil {
		for _, name := range games.Keys() {
			g := games.Obj(name)
			if g == nil {
				continue
			}
			add(g, GamePathKeys)
			for _, p := range g.Arr("launch_profiles") {
				if po, ok := p.(*ojson.Object); ok {
					add(po, ProfilePathKeys)
				}
			}
		}
	}
	switch emus := cfg.Get("emulators").(type) {
	case *ojson.Object:
		for _, k := range emus.Keys() {
			if e := emus.Obj(k); e != nil {
				add(e, EmulatorPathKeys)
			}
		}
	case []any:
		for _, e := range emus {
			if eo, ok := e.(*ojson.Object); ok {
				add(eo, EmulatorPathKeys)
			}
		}
	}
	return out
}

// MakePortable returns a deep copy of cfg with game/emulator paths in their
// stored (portable) form and settings.launcher_drive set.
func MakePortable(cfg *ojson.Object, appDir string) *ojson.Object {
	c := cfg.Clone()
	for _, s := range pathSlots(c) {
		s.o.Set(s.key, ToPortable(s.o.Str(s.key), appDir))
	}
	if d := DriveOf(appDir); d != "" {
		c.EnsureObj("settings").Set("launcher_drive", d)
	}
	return c
}

// ResolveConfig resolves the paths in cfg (in place) for the current
// launcher location and returns how many were remapped from the previous
// launcher drive letter.
func ResolveConfig(cfg *ojson.Object, appDir string) int {
	newDrive := DriveOf(appDir)
	settings := cfg.EnsureObj("settings")
	oldDrive := strings.ToUpper(settings.Str("launcher_drive"))
	remapped := 0
	for _, s := range pathSlots(cfg) {
		orig := s.o.Str(s.key)
		v := orig
		if oldDrive != "" && newDrive != "" && oldDrive != newDrive {
			v = RemapDrive(v, oldDrive, newDrive)
			if v != orig {
				remapped++
			}
		}
		s.o.Set(s.key, Resolve(v, appDir))
	}
	if newDrive != "" {
		settings.Set("launcher_drive", newDrive)
	}
	return remapped
}

// FindExisting returns p when it exists, otherwise the same path on the
// launcher's drive when that exists (the games drive got another letter but
// config.json still has the old one), otherwise "".
func FindExisting(p, appDir string, exists func(string) bool) string {
	if p == "" {
		return ""
	}
	if exists(p) {
		return p
	}
	appDrive, pathDrive := DriveOf(appDir), DriveOf(p)
	if appDrive != "" && pathDrive != "" && appDrive != pathDrive {
		if c := RemapDrive(p, pathDrive, appDrive); exists(c) {
			return c
		}
	}
	return ""
}

// Exists reports whether a file or folder exists.
func Exists(p string) bool {
	if p == "" {
		return false
	}
	_, err := os.Stat(p)
	return err == nil
}

// Dir is ntpath.dirname.
func Dir(p string) string {
	drive, rest := splitDrive(p)
	i := strings.LastIndexAny(rest, `\/`)
	if i < 0 {
		return drive
	}
	head := rest[:i+1]
	if strings.Trim(head, `\/`) != "" {
		head = strings.TrimRight(head, `\/`)
	}
	return drive + head
}

// Base is ntpath.basename.
func Base(p string) string {
	_, rest := splitDrive(p)
	if i := strings.LastIndexAny(rest, `\/`); i >= 0 {
		return rest[i+1:]
	}
	return rest
}
