package deploy

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"hash/crc32"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/snakex21/game-launcher/go/internal/modmgr/fsx"
)

// record is one journal line: "<crc32 hex> <json>\n".
type record struct {
	T    string `json:"t"`
	Tx   string `json:"tx,omitempty"`
	Plan *Plan  `json:"plan,omitempty"`
	I    int    `json:"i,omitempty"`
}

type wal struct {
	f       *os.File
	pending int
}

const syncEvery = 64

func (e *Engine) walPath(tx string) string {
	return filepath.Join(e.StateDir, "journal", tx+".wal")
}

func createWAL(path string) (*wal, error) {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return nil, err
	}
	return &wal{f: f}, nil
}

func encodeRecord(r record) ([]byte, error) {
	b, err := json.Marshal(r)
	if err != nil {
		return nil, err
	}
	return []byte(fmt.Sprintf("%08x %s\n", crc32.ChecksumIEEE(b), b)), nil
}

func (w *wal) write(r record) error {
	b, err := encodeRecord(r)
	if err != nil {
		return err
	}
	if _, err := w.f.Write(b); err != nil {
		return err
	}
	w.pending++
	if w.pending >= syncEvery {
		return w.sync()
	}
	return nil
}

func (w *wal) writeSync(r record) error {
	if err := w.write(r); err != nil {
		return err
	}
	return w.sync()
}

func (w *wal) sync() error {
	w.pending = 0
	return w.f.Sync()
}

func (w *wal) close() {
	if w.f != nil {
		w.f.Sync()
		w.f.Close()
		w.f = nil
	}
}

// readWAL parses a journal; a torn or corrupted line ends it.
func readWAL(path string) ([]record, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []record
	sc := bufio.NewScanner(bytes.NewReader(b))
	sc.Buffer(make([]byte, 1<<20), 1<<30)
	for sc.Scan() {
		line := sc.Text()
		if len(line) < 10 || line[8] != ' ' {
			break
		}
		var crc uint32
		if _, err := fmt.Sscanf(line[:8], "%08x", &crc); err != nil {
			break
		}
		body := []byte(line[9:])
		if crc32.ChecksumIEEE(body) != crc {
			break
		}
		var r record
		if err := json.Unmarshal(body, &r); err != nil {
			break
		}
		out = append(out, r)
	}
	return out, nil
}

// pendingWAL lists journals of unfinished transactions.
func (e *Engine) pendingWAL() ([]string, error) {
	m, err := filepath.Glob(filepath.Join(e.StateDir, "journal", "*.wal"))
	sort.Strings(m)
	return m, err
}

// finishTx archives the journal (keeps the last 5 in journal/done) and
// removes the transaction's backups if it was rolled back.
func (e *Engine) finishTx(tx string, committed bool) {
	src := e.walPath(tx)
	doneDir := filepath.Join(e.StateDir, "journal", "done")
	if err := os.MkdirAll(doneDir, 0o755); err == nil {
		suffix := ".committed"
		if !committed {
			suffix = ".rolledback"
		}
		if os.Rename(src, filepath.Join(doneDir, tx+suffix)) != nil {
			os.Remove(src)
		}
		old, _ := os.ReadDir(doneDir)
		var names []string
		for _, o := range old {
			names = append(names, o.Name())
		}
		sort.Strings(names)
		for len(names) > 5 {
			os.Remove(filepath.Join(doneDir, names[0]))
			names = names[1:]
		}
	} else {
		os.Remove(src)
	}
	if !committed {
		fsx.RemoveAll(filepath.Join(e.StateDir, "backups", tx))
	}
}

// RecoveryReport says what Recover did.
type RecoveryReport struct {
	TxID   string `json:"txId"`
	Action string `json:"action"` // none|discarded|forward|rollback|committed
	Detail string `json:"detail,omitempty"`
}

// Recover finishes or rolls back an interrupted transaction. Roll-forward
// is preferred; when a source file is missing (store on an unplugged
// drive) the transaction is rolled back instead.
func (e *Engine) Recover() ([]RecoveryReport, error) {
	pend, err := e.pendingWAL()
	if err != nil || len(pend) == 0 {
		return nil, err
	}
	lock, err := fsx.TryLock(filepath.Join(e.StateDir, "lock"))
	if err != nil {
		return nil, err
	}
	defer lock.Unlock()
	var reports []RecoveryReport
	for _, path := range pend {
		tx := strings.TrimSuffix(filepath.Base(path), ".wal")
		recs, err := readWAL(path)
		if err != nil {
			return reports, err
		}
		var plan *Plan
		state := ""
		for _, r := range recs {
			switch r.T {
			case "PLAN":
				plan = r.Plan
			case "COMMIT", "ROLLBACK", "ROLLBACK-FAILED":
				state = r.T
			}
		}
		rep := RecoveryReport{TxID: tx}
		switch {
		case plan == nil:
			// nothing was changed before the plan was durable
			os.Remove(path)
			rep.Action = "discarded"
		case state == "COMMIT":
			e.finishTx(tx, true)
			rep.Action = "committed"
		case state == "ROLLBACK":
			e.finishTx(tx, false)
			rep.Action = "rollback"
		default:
			rep, err = e.recoverPlan(path, plan)
			if err != nil {
				return append(reports, rep), err
			}
		}
		reports = append(reports, rep)
	}
	return reports, nil
}

func (e *Engine) recoverPlan(path string, p *Plan) (RecoveryReport, error) {
	rep := RecoveryReport{TxID: p.TxID}
	man, err := e.Manifest()
	if err != nil {
		return rep, err
	}
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return rep, err
	}
	w := &wal{f: f}
	if man.TxID == p.TxID {
		// crashed after the manifest was written: it is committed
		w.writeSync(record{T: "COMMIT"})
		w.close()
		e.cleanup(p, man)
		rep.Action = "committed"
		return rep, nil
	}
	forward := true
	missing := ""
	for i := range p.Ops {
		if p.Ops[i].After.Kind != StMod || p.Ops[i].Noop() {
			continue
		}
		src, err := e.SourcePath(p.Ops[i].After.Source)
		if err != nil || !fsx.Exists(src) {
			forward, missing = false, src
			break
		}
	}
	if forward {
		var errs []string
		for i := range p.Ops {
			if p.Ops[i].Noop() {
				continue
			}
			if err := e.forward(&p.Ops[i]); err != nil {
				errs = append(errs, fmt.Sprintf("%s: %v", p.Ops[i].Target, err))
				forward = false
				break
			}
		}
		if forward {
			saved := e.FailAt
			e.FailAt = nil
			err := e.commit(w, p, man)
			e.FailAt = saved
			if err != nil {
				return rep, err
			}
			rep.Action = "forward"
			return rep, nil
		}
		rep.Detail = strings.Join(errs, "; ")
	} else {
		rep.Detail = "brak pliku źródłowego: " + missing
	}
	// roll back everything (each step checks the disk, so order is safe)
	var errs []string
	for i := len(p.Ops) - 1; i >= 0; i-- {
		if err := e.backward(&p.Ops[i]); err != nil {
			errs = append(errs, fmt.Sprintf("%s: %v", p.Ops[i].Target, err))
		}
	}
	e.removeCreatedDirs(p.CreatedDirs, man.Entries)
	if len(errs) > 0 {
		w.close()
		rep.Action = "rollback-failed"
		return rep, errors.New("nie udało się wycofać przerwanej operacji: " + strings.Join(errs, "; "))
	}
	w.writeSync(record{T: "ROLLBACK"})
	w.close()
	e.finishTx(p.TxID, false)
	rep.Action = "rollback"
	return rep, nil
}

// Pending reports whether an unfinished transaction exists.
func (e *Engine) Pending() bool {
	p, _ := e.pendingWAL()
	return len(p) > 0
}
