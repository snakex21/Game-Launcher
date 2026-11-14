// Package chatdb reads data/chat/chat.db, the SQLite database of the
// Python chat server (Flask-SQLAlchemy models User, ChatRoom, Message,
// RoomMembership). It opens the file strictly read-only (mode=ro,
// immutable=1): no journal, no WAL, no writes. Password hashes and e-mail
// addresses are never read.
package chatdb

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

// Summary of the archive.
type Summary struct {
	Users    int       `json:"users"`
	Rooms    []Room    `json:"rooms"`
	Messages int       `json:"messages"`
	Private  int       `json:"private"`
	Recent   []Message `json:"recent"`
}

// Room is a chat room.
type Room struct {
	ID       int64  `json:"id"`
	Name     string `json:"name"`
	Members  int    `json:"members"`
	Messages int    `json:"messages"`
	Locked   bool   `json:"locked"`
}

// Message is one message (attachments by name only).
type Message struct {
	ID         int64  `json:"id"`
	Sender     string `json:"sender"`
	Receiver   string `json:"receiver,omitempty"`
	Room       string `json:"room,omitempty"`
	Content    string `json:"content"`
	Timestamp  string `json:"timestamp"`
	Edited     bool   `json:"edited"`
	Attachment string `json:"attachment,omitempty"`
}

// ErrMissing means there is no chat.db.
var ErrMissing = errors.New("brak pliku chat.db")

func open(path string) (*sql.DB, error) {
	if _, err := os.Stat(path); err != nil {
		return nil, ErrMissing
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	segs := strings.Split(filepath.ToSlash(abs), "/")
	for i, seg := range segs {
		segs[i] = url.PathEscape(seg)
	}
	dsn := "file:" + strings.Join(segs, "/") + "?mode=ro&immutable=1&_pragma=query_only(1)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	return db, nil
}

func friendly(err error) error {
	if err == nil {
		return nil
	}
	msg := err.Error()
	if strings.Contains(msg, "malformed") || strings.Contains(msg, "not a database") {
		return fmt.Errorf("plik chat.db jest uszkodzony (%s); launcher nie zmienia tego pliku", msg)
	}
	return err
}

// Read loads a summary with up to recent messages (newest first).
func Read(path string, recent int) (*Summary, error) {
	db, err := open(path)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	var ok string
	if err := db.QueryRow("PRAGMA quick_check").Scan(&ok); err != nil {
		return nil, friendly(err)
	}
	if ok != "ok" {
		return nil, friendly(fmt.Errorf("database disk image is malformed: %s", ok))
	}
	s := &Summary{Rooms: []Room{}, Recent: []Message{}}
	if err := db.QueryRow(`SELECT COUNT(*) FROM user`).Scan(&s.Users); err != nil {
		return nil, friendly(err)
	}
	if err := db.QueryRow(`SELECT COUNT(*), COALESCE(SUM(room_id IS NULL),0) FROM message`).Scan(&s.Messages, &s.Private); err != nil {
		return nil, friendly(err)
	}
	rows, err := db.Query(`SELECT r.id, r.name, r.password_hash IS NOT NULL AND r.password_hash <> '',
		(SELECT COUNT(*) FROM room_membership m WHERE m.room_id = r.id),
		(SELECT COUNT(*) FROM message g WHERE g.room_id = r.id)
		FROM chat_room r ORDER BY r.name`)
	if err != nil {
		return nil, friendly(err)
	}
	for rows.Next() {
		var r Room
		if err := rows.Scan(&r.ID, &r.Name, &r.Locked, &r.Members, &r.Messages); err != nil {
			rows.Close()
			return nil, friendly(err)
		}
		s.Rooms = append(s.Rooms, r)
	}
	rows.Close()
	if recent > 0 {
		rows, err := db.Query(`SELECT m.id, COALESCE(su.username, '(usunięty)'), COALESCE(ru.username, ''), COALESCE(cr.name, ''),
			COALESCE(m.content, ''), COALESCE(CAST(m.timestamp AS TEXT), ''), m.edited_at IS NOT NULL, COALESCE(m.attachment_original_filename, '')
			FROM message m
			LEFT JOIN user su ON su.id = m.sender_id
			LEFT JOIN user ru ON ru.id = m.receiver_id
			LEFT JOIN chat_room cr ON cr.id = m.room_id
			ORDER BY m.timestamp DESC, m.id DESC LIMIT ?`, recent)
		if err != nil {
			return nil, friendly(err)
		}
		defer rows.Close()
		for rows.Next() {
			var m Message
			if err := rows.Scan(&m.ID, &m.Sender, &m.Receiver, &m.Room, &m.Content, &m.Timestamp, &m.Edited, &m.Attachment); err != nil {
				return nil, friendly(err)
			}
			s.Recent = append(s.Recent, m)
		}
	}
	return s, nil
}
