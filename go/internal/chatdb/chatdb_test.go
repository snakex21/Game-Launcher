package chatdb

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
)

// Schema as Flask-SQLAlchemy creates it for chat_server.py.
const schema = `
CREATE TABLE user (id INTEGER NOT NULL PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(128) NOT NULL, created_at DATETIME, is_banned BOOLEAN NOT NULL, is_admin BOOLEAN NOT NULL);
CREATE TABLE chat_room (id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, creator_id INTEGER, created_at DATETIME, password_hash VARCHAR(128));
CREATE TABLE room_membership (id INTEGER NOT NULL PRIMARY KEY, user_id INTEGER NOT NULL, room_id INTEGER NOT NULL, joined_at DATETIME,
  CONSTRAINT _user_room_uc UNIQUE (user_id, room_id));
CREATE TABLE message (id INTEGER NOT NULL PRIMARY KEY, sender_id INTEGER, receiver_id INTEGER, room_id INTEGER, content TEXT,
  timestamp DATETIME, edited_at DATETIME, replied_to_message_id INTEGER, attachment_server_filename VARCHAR(255),
  attachment_original_filename VARCHAR(255), attachment_mimetype VARCHAR(100), is_read_by_receiver BOOLEAN NOT NULL);
INSERT INTO user VALUES (1,'ala','a@x','h',NULL,0,0),(2,'olek','o@x','h',NULL,0,1);
INSERT INTO chat_room VALUES (1,'Ogólny',1,NULL,NULL),(2,'Tajny',2,NULL,'hash');
INSERT INTO room_membership VALUES (1,1,1,NULL),(2,2,1,NULL);
INSERT INTO message VALUES (1,1,2,NULL,'cześć','2026-03-01 10:00:00.000000',NULL,NULL,NULL,NULL,NULL,1),
  (2,2,NULL,1,'hej wszystkim','2026-03-01 10:05:00.000000','2026-03-01 10:06:00',NULL,NULL,'plik.png','image/png',0);
`

func makeDB(t *testing.T, dir string) string {
	p := filepath.Join(dir, "chat dir", "chat.db") // space in the path on purpose
	os.MkdirAll(filepath.Dir(p), 0o755)
	db, err := sql.Open("sqlite", p)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(schema); err != nil {
		t.Fatal(err)
	}
	db.Close()
	return p
}

func TestReadOnlySummary(t *testing.T) {
	p := makeDB(t, t.TempDir())
	before, _ := os.ReadFile(p)
	s, err := Read(p, 10)
	if err != nil {
		t.Fatal(err)
	}
	if s.Users != 2 || s.Messages != 2 || s.Private != 1 || len(s.Rooms) != 2 || len(s.Recent) != 2 {
		t.Fatalf("%+v", s)
	}
	if s.Recent[0].Room != "Ogólny" || !s.Recent[0].Edited || s.Recent[0].Attachment != "plik.png" || s.Recent[1].Receiver != "olek" {
		t.Fatalf("%+v", s.Recent)
	}
	if !s.Rooms[1].Locked || s.Rooms[0].Members != 2 {
		t.Fatalf("%+v", s.Rooms)
	}
	after, _ := os.ReadFile(p)
	if string(before) != string(after) {
		t.Fatal("chat.db was modified")
	}
	entries, _ := os.ReadDir(filepath.Dir(p))
	if len(entries) != 1 {
		t.Fatal("journal/wal files created")
	}
}

func TestMissingAndCorrupt(t *testing.T) {
	dir := t.TempDir()
	if _, err := Read(filepath.Join(dir, "none.db"), 5); err != ErrMissing {
		t.Fatal(err)
	}
	p := makeDB(t, dir)
	b, _ := os.ReadFile(p)
	// the user's real copy is corrupt in the same way: bytes inserted mid-file
	bad := append(append(append([]byte{}, b[:5000]...), []byte("\r\r\r\r")...), b[5000:]...)
	os.WriteFile(p, bad, 0o644)
	if _, err := Read(p, 5); err == nil {
		t.Fatal("corrupt database accepted")
	}
	if src := os.Getenv("GL_TEST_USERDATA"); src != "" {
		_, err := Read(filepath.Join(src, "data", "chat", "chat.db"), 0)
		t.Logf("user copy chat.db: %v", err)
	}
}
