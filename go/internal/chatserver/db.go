// Package chatserver is the launcher's chat server: REST for accounts and
// files, plain WebSocket (JSON events) for messaging. It replaces the
// Flask-SocketIO chat_server.py with a cleaner protocol (no Socket.IO).
//
// Security: bcrypt password hashes, random session tokens (only their
// SHA-256 is stored) that the socket must present before anything else,
// per-IP and per-user rate limits, size/type limits on uploads, blocking
// enforced on the server.
//
// Storage: data/chat/chat.db (SQLite). Table and column names follow the
// old SQLAlchemy models where it makes sense (user, chat_room,
// room_membership, message, blocked_relationship, email_blacklist), plus
// a new "session" table. A broken existing file is never overwritten.
package chatserver

import (
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE COLLATE NOCASE,
  email VARCHAR(120) NOT NULL UNIQUE COLLATE NOCASE,
  password_hash VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_banned BOOLEAN NOT NULL DEFAULT 0,
  is_admin BOOLEAN NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chat_room (
  id INTEGER PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE COLLATE NOCASE,
  creator_id INTEGER REFERENCES user(id) ON DELETE SET NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  password_hash VARCHAR(128)
);
CREATE TABLE IF NOT EXISTS room_membership (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  room_id INTEGER NOT NULL REFERENCES chat_room(id) ON DELETE CASCADE,
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT _user_room_uc UNIQUE (user_id, room_id)
);
CREATE TABLE IF NOT EXISTS message (
  id INTEGER PRIMARY KEY,
  sender_id INTEGER REFERENCES user(id) ON DELETE SET NULL,
  receiver_id INTEGER REFERENCES user(id) ON DELETE SET NULL,
  room_id INTEGER REFERENCES chat_room(id) ON DELETE CASCADE,
  content TEXT,
  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  edited_at DATETIME,
  replied_to_message_id INTEGER REFERENCES message(id) ON DELETE SET NULL,
  attachment_server_filename VARCHAR(255),
  attachment_original_filename VARCHAR(255),
  attachment_mimetype VARCHAR(100),
  is_read_by_receiver BOOLEAN NOT NULL DEFAULT 0,
  is_deleted BOOLEAN NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_message_room ON message(room_id, id);
CREATE INDEX IF NOT EXISTS ix_message_dm ON message(sender_id, receiver_id, id);
CREATE TABLE IF NOT EXISTS blocked_relationship (
  id INTEGER PRIMARY KEY,
  blocker_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  blocked_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT _blocker_blocked_uc UNIQUE (blocker_id, blocked_id)
);
CREATE TABLE IF NOT EXISTS email_blacklist (
  id INTEGER PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE COLLATE NOCASE,
  reason VARCHAR(255),
  added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS session (
  token_hash CHAR(64) PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
INSERT OR IGNORE INTO meta(key, value) VALUES ('schema', 'gl-go-chat-1');
`

// ErrCorrupt means an existing chat.db cannot be used.
var ErrCorrupt = errors.New("plik chat.db jest uszkodzony – przenieś go lub usuń; serwer czatu go nie nadpisze")

func dsn(path string) (string, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	segs := strings.Split(filepath.ToSlash(abs), "/")
	for i, s := range segs {
		segs[i] = url.PathEscape(s)
	}
	return "file:" + strings.Join(segs, "/") + "?_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)", nil
}

// OpenDB opens (or creates, only when missing) the chat database.
func OpenDB(path string) (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	existed := false
	if st, err := os.Stat(path); err == nil && st.Size() > 0 {
		existed = true
	}
	d, err := dsn(path)
	if err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", d)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // SQLite: one writer; keeps ordering simple
	if existed {
		var ok string
		if err := db.QueryRow("PRAGMA quick_check").Scan(&ok); err != nil || ok != "ok" {
			db.Close()
			return nil, ErrCorrupt
		}
	}
	if existed {
		// A valid chat.db of the Python server: add the columns it lacks.
		var has int
		_ = db.QueryRow(`SELECT COUNT(*) FROM pragma_table_info('message') WHERE name = 'is_deleted'`).Scan(&has)
		var tbl int
		_ = db.QueryRow(`SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'message'`).Scan(&tbl)
		if tbl == 1 && has == 0 {
			if _, err := db.Exec(`ALTER TABLE message ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0`); err != nil {
				db.Close()
				return nil, err
			}
		}
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		if existed {
			return nil, fmt.Errorf("%w (%v)", ErrCorrupt, err)
		}
		return nil, err
	}
	return db, nil
}
