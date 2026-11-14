package deploy

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/archive"
	"github.com/snakex21/game-launcher/go/internal/modmgr/fsx"
	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
	"github.com/snakex21/game-launcher/go/internal/modmgr/ids"
	"github.com/snakex21/game-launcher/go/internal/modmgr/relpath"
)

// Engine deploys into one game install.
type Engine struct {
	InstallID string
	StateDir  string // <modmgr>/state/<installId>
	// Roots resolves target roots to absolute folders.
	Roots map[gamedef.RootKind]string
	// SourcePath resolves a source to an absolute file.
	SourcePath func(Source) (string, error)
	// Protected are glob patterns (relative to the game root) that need consent.
	Protected []string
	// FailAt injects a failure before step i (tests): returning ErrCrash
	// stops without rolling back (power loss), any other error rolls back.
	FailAt func(step int) error
	// Now is the clock (tests).
	Now func() time.Time
}

// ErrCrash simulates a power loss in tests.
var ErrCrash = errors.New("symulowana awaria")

// Plan is a computed transaction.
type Plan struct {
	TxID        string             `json:"txId"`
	Kind        string             `json:"kind"` // deploy|purge
	ProfileID   string             `json:"profileId,omitempty"`
	FromTx      string             `json:"fromTx,omitempty"`
	Ops         []Op               `json:"ops"`
	CreatedDirs []gamedef.Location `json:"createdDirs,omitempty"`
	Fingerprint map[string]string  `json:"fingerprint,omitempty"`
	// Protected lists targets matching protected paths (consent needed).
	Protected []string `json:"protected,omitempty"`
	// Drift lists files changed outside the manager that are left alone.
	Drift []string `json:"drift,omitempty"`
}

// Changes counts the ops that touch the disk.
func (p *Plan) Changes() int {
	n := 0
	for i := range p.Ops {
		if !p.Ops[i].Noop() {
			n++
		}
	}
	return n
}

func (e *Engine) now() time.Time {
	if e.Now != nil {
		return e.Now()
	}
	return time.Now()
}

func (e *Engine) manifestPath() string { return filepath.Join(e.StateDir, "manifest.json") }

// Manifest loads the current manifest (empty if none).
func (e *Engine) Manifest() (*Manifest, error) {
	var m Manifest
	err := fsx.ReadJSON(e.manifestPath(), &m)
	if errors.Is(err, fs.ErrNotExist) {
		return &Manifest{FormatVersion: 1, InstallID: e.InstallID}, nil
	}
	if err != nil {
		// a damaged manifest must not be silently replaced
		if prevErr := fsx.ReadJSON(filepath.Join(e.StateDir, "manifest.prev.json"), &m); prevErr == nil {
			return nil, fmt.Errorf("manifest wdrożenia jest uszkodzony (%v); dostępna jest poprzednia wersja manifest.prev.json – przywróć ją ręcznie po sprawdzeniu", err)
		}
		return nil, fmt.Errorf("manifest wdrożenia jest uszkodzony: %w", err)
	}
	return &m, nil
}

func (e *Engine) abs(l gamedef.Location) (string, error) {
	root, ok := e.Roots[l.Root]
	if !ok || root == "" {
		return "", fmt.Errorf("folder {%s} nie jest dostępny", l.Root)
	}
	return gamedef.AbsIn(root, l.Rel), nil
}

func (e *Engine) backupAbs(rel string) string {
	return filepath.Join(e.StateDir, filepath.FromSlash(rel))
}

// disk describes what is at a target path.
type disk struct {
	exists   bool
	sha      string
	size     int64
	readOnly bool
	mtime    int64
}

// observe looks at a target; the hash is only computed when the cheap
// checks cannot prove the file is the deployed one.
func (e *Engine) observe(abs string, cur *Entry) (disk, error) {
	st, err := os.Lstat(abs)
	if errors.Is(err, fs.ErrNotExist) {
		return disk{}, nil
	}
	if err != nil {
		return disk{}, err
	}
	if !st.Mode().IsRegular() {
		return disk{}, fmt.Errorf("%s nie jest zwykłym plikiem (folder albo dowiązanie) – nie zostanie nadpisany", abs)
	}
	d := disk{exists: true, size: st.Size(), readOnly: st.Mode().Perm()&0o200 == 0, mtime: st.ModTime().UnixNano()}
	if cur != nil && st.Size() == cur.Size {
		if cur.Kind == "hardlink" && cur.FileID != "" {
			if id, err := fsx.FileID(abs); err == nil && id == cur.FileID {
				d.sha = cur.SHA256
				return d, nil
			}
		}
		if cur.Kind == "copy" && cur.ModTime != 0 && cur.ModTime == d.mtime {
			d.sha = cur.SHA256
			return d, nil
		}
	}
	sum, _, err := archive.HashFile(abs)
	if err != nil {
		return disk{}, err
	}
	d.sha = sum
	return d, nil
}

// PlanTo computes the transaction that makes the disk match desired
// (an empty desired list is a purge).
func (e *Engine) PlanTo(desired []Desired, profileID string, fingerprint map[string]string) (*Plan, error) {
	man, err := e.Manifest()
	if err != nil {
		return nil, err
	}
	p := &Plan{TxID: ids.New(), Kind: "deploy", ProfileID: profileID, FromTx: man.TxID, Fingerprint: fingerprint}
	if len(desired) == 0 {
		p.Kind = "purge"
	}
	cur := map[string]*Entry{}
	for i := range man.Entries {
		cur[man.Entries[i].Target.Key()] = &man.Entries[i]
	}
	want := map[string]*Desired{}
	var keys []string
	for i := range desired {
		k := desired[i].Target.Key()
		if _, dup := want[k]; dup {
			return nil, fmt.Errorf("dwa pliki w to samo miejsce: %s", desired[i].Target)
		}
		want[k] = &desired[i]
		keys = append(keys, k)
	}
	for k := range cur {
		if want[k] == nil {
			keys = append(keys, k)
		}
	}
	sort.Strings(keys)
	dirSeen := map[string]bool{}
	for _, k := range keys {
		c, w := cur[k], want[k]
		var target gamedef.Location
		if w != nil {
			target = w.Target
		} else {
			target = c.Target
		}
		abs, err := e.abs(target)
		if err != nil {
			return nil, err
		}
		d, err := e.observe(abs, c)
		if err != nil {
			return nil, err
		}
		op := Op{Target: target}
		if c != nil {
			op.OldOrig = c.Orig
		}
		// what is on disk now
		switch {
		case !d.exists:
			op.Before = KeyState{Kind: StAbsent}
		case c != nil && d.sha == c.SHA256:
			op.Before = KeyState{Kind: StMod, Source: c.Source, SHA256: c.SHA256, Size: c.Size, Hard: c.Kind == "hardlink", MTime: c.ModTime}
		default:
			op.Before = KeyState{Kind: StOrig, SHA256: d.sha, Size: d.size}
		}
		foreign := op.Before.Kind == StOrig && (c == nil || c.Orig == nil || c.Orig.SHA256 != d.sha)
		if w != nil {
			mt := int64(0)
			if !w.MTime.IsZero() {
				mt = w.MTime.UnixNano()
			}
			op.After = KeyState{Kind: StMod, Source: w.Source, SHA256: w.SHA256, Size: w.Size, Hard: w.Kind == "hardlink" && mt == 0, MTime: mt}
			op.NewOrig = op.OldOrig
			if foreign {
				// a game file (or a newer one after a game update) becomes the original
				op.TakeBackup = true
				op.NewOrig = &Orig{Backup: relpath.Join("backups", p.TxID, string(target.Root), target.Rel), SHA256: d.sha, Size: d.size, ReadOnly: d.readOnly, ModTime: d.mtime}
				if c != nil {
					p.Drift = append(p.Drift, target.String()+" – zmieniony poza menedżerem (np. aktualizacja gry); nowa wersja zapisana jako oryginał")
				}
			}
			if target.Root == gamedef.RootGame && relpath.MatchAny(e.Protected, target.Rel) {
				p.Protected = append(p.Protected, target.Rel)
			}
			// folders that will be created for this file
			for dir := relpath.Dir(target.Rel); dir != ""; dir = relpath.Dir(dir) {
				l := gamedef.Location{Root: target.Root, Rel: dir}
				if dirSeen[l.Key()] {
					break
				}
				dirSeen[l.Key()] = true
				if da, _ := e.abs(l); !fsx.Exists(da) {
					p.CreatedDirs = append(p.CreatedDirs, l)
				}
			}
		} else {
			// back to the original
			op.After = KeyState{Kind: StOrig}
			switch {
			case op.Before.Kind == StMod || op.Before.Kind == StAbsent:
				op.NewOrig = op.OldOrig
				if op.NewOrig != nil {
					op.After.SHA256, op.After.Size = op.NewOrig.SHA256, op.NewOrig.Size
				} else {
					op.After.Kind = StAbsent
				}
			case foreign:
				op.Leave = true
				p.Drift = append(p.Drift, target.String()+" – zmieniony poza menedżerem; pozostawiony bez zmian")
			}
		}
		p.Ops = append(p.Ops, op)
	}
	sort.Slice(p.CreatedDirs, func(i, j int) bool { return p.CreatedDirs[i].Key() < p.CreatedDirs[j].Key() })
	return p, nil
}

// Result reports a finished transaction.
type Result struct {
	TxID     string   `json:"txId"`
	Changed  int      `json:"changed"`
	Drift    []string `json:"drift,omitempty"`
	Warnings []string `json:"warnings,omitempty"`
}

// ApplyOptions control Apply.
type ApplyOptions struct {
	AllowProtected bool
}

// Apply executes a plan as one transaction.
func (e *Engine) Apply(p *Plan, opt ApplyOptions) (*Result, error) {
	if len(p.Protected) > 0 && !opt.AllowProtected {
		return nil, &ProtectedError{Paths: p.Protected}
	}
	if err := os.MkdirAll(filepath.Join(e.StateDir, "journal"), 0o755); err != nil {
		return nil, err
	}
	lock, err := fsx.TryLock(filepath.Join(e.StateDir, "lock"))
	if err != nil {
		return nil, err
	}
	defer lock.Unlock()
	if pending, _ := e.pendingWAL(); len(pending) > 0 {
		return nil, errors.New("poprzednia operacja nie została dokończona – uruchom odzyskiwanie")
	}
	man, err := e.Manifest()
	if err != nil {
		return nil, err
	}
	if man.TxID != p.FromTx {
		return nil, errors.New("stan wdrożenia zmienił się od przygotowania planu – spróbuj ponownie")
	}
	w, err := createWAL(e.walPath(p.TxID))
	if err != nil {
		return nil, err
	}
	if err := w.write(record{T: "BEGIN", Tx: p.TxID}); err == nil {
		err = w.writeSync(record{T: "PLAN", Plan: p})
	}
	if err != nil {
		w.close()
		os.Remove(e.walPath(p.TxID))
		return nil, err
	}
	res := &Result{TxID: p.TxID, Drift: p.Drift}
	for i := range p.Ops {
		if err := e.fail(i); err != nil {
			if errors.Is(err, ErrCrash) {
				w.close()
				return nil, err
			}
			return nil, e.abort(w, p, i, err)
		}
		op := &p.Ops[i]
		if op.Noop() {
			continue
		}
		if err := e.forward(op); err != nil {
			return nil, e.abort(w, p, i, fmt.Errorf("%s: %w", op.Target, err))
		}
		res.Changed++
		if err := w.write(record{T: "DONE", I: i}); err != nil {
			return nil, e.abort(w, p, i, err)
		}
	}
	if err := e.fail(len(p.Ops)); err != nil {
		if errors.Is(err, ErrCrash) {
			w.close()
			return nil, err
		}
		return nil, e.abort(w, p, len(p.Ops)-1, err)
	}
	if err := e.commit(w, p, man); err != nil {
		if errors.Is(err, ErrCrash) {
			return nil, err
		}
		return nil, err
	}
	return res, nil
}

// ProtectedError lists protected paths that would be overwritten.
type ProtectedError struct{ Paths []string }

func (e *ProtectedError) Error() string {
	return "wdrożenie nadpisze chronione pliki gry: " + strings.Join(e.Paths, ", ")
}

func (e *Engine) fail(step int) error {
	if e.FailAt == nil {
		return nil
	}
	return e.FailAt(step)
}

// abort rolls back ops 0..last and removes the transaction.
func (e *Engine) abort(w *wal, p *Plan, last int, cause error) error {
	var rbErrs []string
	for i := last; i >= 0; i-- {
		if err := e.backward(&p.Ops[i]); err != nil {
			rbErrs = append(rbErrs, fmt.Sprintf("%s: %v", p.Ops[i].Target, err))
		}
	}
	e.removeCreatedDirs(p.CreatedDirs, nil)
	if len(rbErrs) > 0 {
		w.writeSync(record{T: "ROLLBACK-FAILED"})
		w.close()
		return fmt.Errorf("%v; wycofanie zmian nie powiodło się dla: %s (szczegóły w dzienniku %s)", cause, strings.Join(rbErrs, "; "), e.walPath(p.TxID))
	}
	w.writeSync(record{T: "ROLLBACK"})
	w.close()
	e.finishTx(p.TxID, false)
	return fmt.Errorf("operacja przerwana, zmiany wycofane: %w", cause)
}

// commit writes the new manifest and cleans up.
func (e *Engine) commit(w *wal, p *Plan, old *Manifest) error {
	nm := &Manifest{FormatVersion: 1, InstallID: e.InstallID, ProfileID: p.ProfileID, TxID: p.TxID, Time: e.now().UTC(), Fingerprint: p.Fingerprint}
	if p.Kind == "purge" {
		nm.ProfileID = ""
	}
	for i := range p.Ops {
		op := &p.Ops[i]
		if op.After.Kind != StMod {
			continue
		}
		en := Entry{Target: op.Target, Source: op.After.Source, SHA256: op.After.SHA256, Size: op.After.Size, Kind: "copy", Orig: op.NewOrig}
		if abs, err := e.abs(op.Target); err == nil {
			if st, err := os.Stat(abs); err == nil {
				en.ModTime = st.ModTime().UnixNano()
			}
			if op.After.Hard {
				if src, err := e.SourcePath(op.After.Source); err == nil {
					a, err1 := fsx.FileID(abs)
					b, err2 := fsx.FileID(src)
					if err1 == nil && err2 == nil && a == b {
						en.Kind, en.FileID = "hardlink", a
					}
				}
			}
		}
		nm.Entries = append(nm.Entries, en)
	}
	// created folders: old ones still in use + new ones
	dirs := append(append([]gamedef.Location{}, old.CreatedDirs...), p.CreatedDirs...)
	nm.CreatedDirs = e.removeCreatedDirs(dirs, nm.Entries)
	if err := e.fail(len(p.Ops) + 1); err != nil {
		if errors.Is(err, ErrCrash) {
			w.close()
			return err
		}
		return e.abort(w, p, len(p.Ops)-1, err)
	}
	if b, err := os.ReadFile(e.manifestPath()); err == nil {
		_ = fsx.WriteFileAtomic(filepath.Join(e.StateDir, "manifest.prev.json"), b, 0o644)
	}
	if err := fsx.WriteJSONAtomic(e.manifestPath(), nm); err != nil {
		return e.abort(w, p, len(p.Ops)-1, err)
	}
	if err := e.fail(len(p.Ops) + 2); err != nil && errors.Is(err, ErrCrash) {
		w.close()
		return err
	}
	w.writeSync(record{T: "COMMIT"})
	w.close()
	e.cleanup(p, nm)
	return nil
}

// cleanup removes backups the new manifest no longer references.
func (e *Engine) cleanup(p *Plan, nm *Manifest) {
	keep := map[string]bool{}
	for _, en := range nm.Entries {
		if en.Orig != nil {
			keep[en.Orig.Backup] = true
		}
	}
	for i := range p.Ops {
		if o := p.Ops[i].OldOrig; o != nil && !keep[o.Backup] {
			fsx.Remove(e.backupAbs(o.Backup))
		}
		if o := p.Ops[i].NewOrig; o != nil && !keep[o.Backup] {
			fsx.Remove(e.backupAbs(o.Backup))
		}
	}
	e.finishTx(p.TxID, true)
	e.pruneBackupDirs(nm)
}

// removeCreatedDirs removes empty created folders that no entry needs and
// returns the ones still in use.
func (e *Engine) removeCreatedDirs(dirs []gamedef.Location, entries []Entry) []gamedef.Location {
	used := map[string]bool{}
	for _, en := range entries {
		for d := relpath.Dir(en.Target.Rel); d != ""; d = relpath.Dir(d) {
			used[gamedef.Location{Root: en.Target.Root, Rel: d}.Key()] = true
		}
	}
	seen := map[string]bool{}
	var uniq []gamedef.Location
	for _, d := range dirs {
		if !seen[d.Key()] {
			seen[d.Key()] = true
			uniq = append(uniq, d)
		}
	}
	// deepest first
	sort.Slice(uniq, func(i, j int) bool {
		di, dj := strings.Count(uniq[i].Rel, "/"), strings.Count(uniq[j].Rel, "/")
		if di != dj {
			return di > dj
		}
		return uniq[i].Key() < uniq[j].Key()
	})
	var keep []gamedef.Location
	for _, d := range uniq {
		if used[d.Key()] {
			keep = append(keep, d)
			continue
		}
		abs, err := e.abs(d)
		if err != nil {
			keep = append(keep, d)
			continue
		}
		err = os.Remove(abs) // fails when not empty: then it is kept on the list
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			keep = append(keep, d)
		}
	}
	sort.Slice(keep, func(i, j int) bool { return keep[i].Key() < keep[j].Key() })
	return keep
}

// pruneBackupDirs removes empty backup folders and blob folders of old
// transactions that the manifest no longer references.
func (e *Engine) pruneBackupDirs(nm *Manifest) {
	usedBlobs := map[string]bool{}
	for _, en := range nm.Entries {
		if en.Source.Type == "@blob" {
			usedBlobs[strings.SplitN(en.Source.Rel, "/", 2)[0]] = true
		}
	}
	blobs, _ := os.ReadDir(filepath.Join(e.StateDir, "blobs"))
	for _, b := range blobs {
		if !usedBlobs[b.Name()] {
			fsx.RemoveAll(filepath.Join(e.StateDir, "blobs", b.Name()))
		}
	}
	root := filepath.Join(e.StateDir, "backups")
	var dirs []string
	filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err == nil && d.IsDir() {
			dirs = append(dirs, p)
		}
		return nil
	})
	sort.Slice(dirs, func(i, j int) bool { return len(dirs[i]) > len(dirs[j]) })
	for _, d := range dirs {
		os.Remove(d) // only empty ones go
	}
}

// ------------------------------------------------------------- key transitions

// content checks whether the file at abs has the sha (cheap checks first).
func (e *Engine) content(abs string) (disk, error) { return e.observe(abs, nil) }

// reprotect restores the read-only attribute of store files whose
// hardlink had to be made writable to be replaced or removed.
func (e *Engine) reprotect(op *Op) {
	for _, st := range []KeyState{op.Before, op.After} {
		if st.Kind != StMod || st.Source.Type == "@blob" {
			continue
		}
		if src, err := e.SourcePath(st.Source); err == nil && !fsx.IsReadOnly(src) {
			_ = os.Chmod(src, 0o444)
		}
	}
}

func (e *Engine) forward(op *Op) error {
	defer e.reprotect(op)
	abs, err := e.abs(op.Target)
	if err != nil {
		return err
	}
	if op.TakeBackup {
		if err := e.takeBackup(abs, op.NewOrig); err != nil {
			return fmt.Errorf("kopia oryginału: %w", err)
		}
	}
	switch op.After.Kind {
	case StMod:
		return e.place(abs, op, op.After)
	case StOrig:
		return e.restore(abs, op, op.NewOrig)
	case StAbsent:
		return e.removeOurs(abs, op)
	}
	return nil
}

func (e *Engine) backward(op *Op) error {
	if op.Noop() {
		return nil
	}
	defer e.reprotect(op)
	abs, err := e.abs(op.Target)
	if err != nil {
		return err
	}
	switch op.Before.Kind {
	case StAbsent:
		return e.removeOurs(abs, op)
	case StMod:
		if src, err := e.SourcePath(op.Before.Source); err == nil && fsx.Exists(src) {
			return e.place(abs, op, op.Before)
		}
		if op.OldOrig != nil {
			return e.restore(abs, op, op.OldOrig)
		}
		return e.removeOurs(abs, op)
	case StOrig:
		o := op.OldOrig
		if op.TakeBackup {
			o = op.NewOrig
		}
		if o == nil || !fsx.Exists(e.backupAbs(o.Backup)) {
			return nil // the original was never touched
		}
		return e.restore(abs, op, o)
	}
	return nil
}

// known reports whether sha is one of the contents this op may find.
func known(op *Op, sha string) bool {
	if sha == op.Before.SHA256 || sha == op.After.SHA256 {
		return true
	}
	if op.OldOrig != nil && sha == op.OldOrig.SHA256 {
		return true
	}
	return op.NewOrig != nil && sha == op.NewOrig.SHA256
}

func (e *Engine) takeBackup(abs string, o *Orig) error {
	dst := e.backupAbs(o.Backup)
	if d, err := e.content(dst); err == nil && d.exists && d.sha == o.SHA256 {
		return nil
	}
	d, err := e.content(abs)
	if err != nil {
		return err
	}
	if !d.exists || d.sha != o.SHA256 {
		return errors.New("plik gry zmienił się w trakcie operacji")
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	tmp := dst + ".gl-new"
	fsx.Remove(tmp)
	if err := fsx.CopyFile(abs, tmp); err != nil {
		return err
	}
	if b, err := e.content(tmp); err != nil || b.sha != o.SHA256 {
		fsx.Remove(tmp)
		return errors.New("kopia zapasowa nie zgadza się z oryginałem")
	}
	return fsx.ReplaceFile(tmp, dst)
}

func (e *Engine) place(abs string, op *Op, st KeyState) error {
	d, err := e.content(abs)
	if err != nil {
		return err
	}
	if d.exists && d.sha == st.SHA256 && (st.MTime == 0 || d.mtime == st.MTime) {
		return nil
	}
	if d.exists && !known(op, d.sha) {
		return errors.New("plik zmienił się w trakcie operacji – nie nadpisuję")
	}
	if d.exists && op.Before.Kind == StOrig && !(op.TakeBackup || (op.OldOrig != nil && op.OldOrig.SHA256 == d.sha)) {
		return errors.New("brak kopii oryginału – nie nadpisuję")
	}
	src, err := e.SourcePath(st.Source)
	if err != nil {
		return err
	}
	if !fsx.Exists(src) {
		return fmt.Errorf("brak pliku źródłowego %s", src)
	}
	if err := os.MkdirAll(filepath.Dir(abs), 0o755); err != nil {
		return err
	}
	tmp := abs + ".gl-new"
	fsx.Remove(tmp)
	linked := false
	if st.Hard {
		linked = os.Link(src, tmp) == nil
	}
	if !linked {
		if err := fsx.CopyFile(src, tmp); err != nil {
			return err
		}
		// copies are normal game files: writable
		_ = fsx.MakeWritable(tmp)
	}
	if st.MTime != 0 {
		_ = fsx.SetModTime(tmp, time.Unix(0, st.MTime))
	}
	if err := fsx.ReplaceFile(tmp, abs); err != nil {
		fsx.Remove(tmp)
		return err
	}
	return nil
}

func (e *Engine) restore(abs string, op *Op, o *Orig) error {
	if o == nil {
		return e.removeOurs(abs, op)
	}
	d, err := e.content(abs)
	if err != nil {
		return err
	}
	if d.exists && d.sha == o.SHA256 {
		return nil
	}
	if d.exists && !known(op, d.sha) {
		return errors.New("plik zmienił się w trakcie operacji – nie nadpisuję")
	}
	src := e.backupAbs(o.Backup)
	if !fsx.Exists(src) {
		return fmt.Errorf("brak kopii oryginału %s", src)
	}
	if err := os.MkdirAll(filepath.Dir(abs), 0o755); err != nil {
		return err
	}
	tmp := abs + ".gl-new"
	fsx.Remove(tmp)
	if err := fsx.CopyFile(src, tmp); err != nil {
		return err
	}
	if o.ModTime != 0 {
		_ = fsx.SetModTime(tmp, time.Unix(0, o.ModTime))
	}
	if o.ReadOnly {
		_ = os.Chmod(tmp, 0o444)
	} else {
		_ = fsx.MakeWritable(tmp)
	}
	if err := fsx.ReplaceFile(tmp, abs); err != nil {
		fsx.Remove(tmp)
		return err
	}
	return nil
}

// removeOurs deletes the target only if it holds a mod content of this op.
func (e *Engine) removeOurs(abs string, op *Op) error {
	d, err := e.content(abs)
	if err != nil {
		return err
	}
	if !d.exists {
		return nil
	}
	ours := (op.Before.Kind == StMod && d.sha == op.Before.SHA256) || (op.After.Kind == StMod && d.sha == op.After.SHA256)
	if !ours {
		return nil // not ours: leave it
	}
	return fsx.Remove(abs)
}

// ------------------------------------------------------------- verification

// DriftItem is one deployed file that is not as deployed.
type DriftItem struct {
	Target string `json:"target"`
	State  string `json:"state"` // missing|changed|original
}

// Verify compares the disk with the manifest.
func (e *Engine) Verify() ([]DriftItem, *Manifest, error) {
	man, err := e.Manifest()
	if err != nil {
		return nil, nil, err
	}
	var out []DriftItem
	for i := range man.Entries {
		en := &man.Entries[i]
		abs, err := e.abs(en.Target)
		if err != nil {
			out = append(out, DriftItem{Target: en.Target.String(), State: "missing"})
			continue
		}
		d, err := e.observe(abs, en)
		switch {
		case err != nil || !d.exists:
			out = append(out, DriftItem{Target: en.Target.String(), State: "missing"})
		case d.sha == en.SHA256:
		case en.Orig != nil && d.sha == en.Orig.SHA256:
			out = append(out, DriftItem{Target: en.Target.String(), State: "original"})
		default:
			out = append(out, DriftItem{Target: en.Target.String(), State: "changed"})
		}
	}
	return out, man, nil
}
