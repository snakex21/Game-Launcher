// Package deploy puts mod files into a game (and takes them out again) as
// journaled transactions, so the game folder can always go back to the
// state before the first deployment ("vanilla"):
//
//   - every target path is one independent, idempotent key transition
//     (before -> after); originals are copied to a backup before they are
//     overwritten and backups are only deleted after the commit;
//   - the full plan is written (and flushed) to a write-ahead log before
//     the first change; an interrupted transaction is finished forward or
//     rolled back on the next start (Recover);
//   - the manifest (what is deployed, from where, with which hash, which
//     original it hides) is replaced atomically at commit.
//
// Paths are stored relative to named roots (game, documents...), never
// with a drive letter.
package deploy

import (
	"time"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// Source is where deployed content comes from.
type Source struct {
	ModID string `json:"modId,omitempty"`
	Type  string `json:"type"` // mod type id, or "@blob" for generated files (load order)
	Rel   string `json:"rel"`
}

// Same reports whether two sources are the same stored file.
func (s Source) Same(o Source) bool { return s == o }

// Orig is a backed-up original game file.
type Orig struct {
	Backup   string `json:"backup"` // path relative to the state folder ('/')
	SHA256   string `json:"sha256"`
	Size     int64  `json:"size"`
	ReadOnly bool   `json:"readOnly,omitempty"`
	ModTime  int64  `json:"modTime"` // unix nanoseconds
}

// Entry is one deployed file.
type Entry struct {
	Target  gamedef.Location `json:"target"`
	Source  Source           `json:"source"`
	SHA256  string           `json:"sha256"`
	Size    int64            `json:"size"`
	Kind    string           `json:"kind"` // hardlink|copy
	FileID  string           `json:"fileId,omitempty"`
	ModTime int64            `json:"modTime"`
	Orig    *Orig            `json:"orig,omitempty"`
	// Mutable files (configs, load order files) may be rewritten by the
	// game or a mod while deployed: changed content is still ours.
	Mutable bool `json:"mutable,omitempty"`
}

// Manifest is the deployed state of one game install.
type Manifest struct {
	FormatVersion int                `json:"formatVersion"`
	InstallID     string             `json:"installId"`
	ProfileID     string             `json:"profileId,omitempty"`
	TxID          string             `json:"txId,omitempty"`
	Time          time.Time          `json:"time"`
	Fingerprint   map[string]string  `json:"gameFingerprint,omitempty"`
	Entries       []Entry            `json:"entries"`
	CreatedDirs   []gamedef.Location `json:"createdDirs,omitempty"`
}

// Desired is one file that should be deployed.
type Desired struct {
	Target gamedef.Location
	Source Source
	SHA256 string
	Size   int64
	Kind   string    // hardlink|copy (preference; copy is the fallback)
	MTime  time.Time // set after placing (timestamp load orders); zero = keep
	// Mutable: deployed as a writable copy; edits by the game are kept
	// while the same file stays deployed and removed by purge.
	Mutable bool
}

// State kinds of a key.
const (
	StAbsent = "absent"
	StMod    = "mod"
	StOrig   = "orig" // original/foreign content (restorable from a backup)
)

// KeyState is the content of a target path.
type KeyState struct {
	Kind   string `json:"kind"`
	Source Source `json:"source,omitempty"`
	SHA256 string `json:"sha256,omitempty"`
	Size   int64  `json:"size,omitempty"`
	Hard   bool   `json:"hard,omitempty"` // prefer a hardlink
	MTime  int64  `json:"mtime,omitempty"`
	// Mutable content may differ from the store file (edited by the game).
	Mutable bool `json:"mutable,omitempty"`
}

// Op is the transition of one target path.
type Op struct {
	Target     gamedef.Location `json:"target"`
	Before     KeyState         `json:"before"`
	After      KeyState         `json:"after"`
	OldOrig    *Orig            `json:"oldOrig,omitempty"`
	NewOrig    *Orig            `json:"newOrig,omitempty"`
	TakeBackup bool             `json:"takeBackup,omitempty"`
	// Leave: the file was changed outside the manager; it is left alone.
	Leave bool `json:"leave,omitempty"`
}

// Noop reports whether the op changes nothing on disk.
func (o *Op) Noop() bool {
	if o.Leave {
		return true
	}
	if o.TakeBackup {
		return false
	}
	if o.Before.Kind == StMod && o.After.Kind == StMod && o.Before.SHA256 == o.After.SHA256 {
		return o.Before.MTime == o.After.MTime || o.After.MTime == 0
	}
	if o.Before.Kind == StOrig && o.After.Kind == StOrig {
		return true
	}
	return o.Before.Kind == StAbsent && o.After.Kind == StAbsent
}
