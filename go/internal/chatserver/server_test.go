package chatserver_test

import (
	"context"
	"database/sql"
	"encoding/json"
	"image"
	"image/png"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"

	"github.com/snakex21/game-launcher/go/internal/chatclient"
	"github.com/snakex21/game-launcher/go/internal/chatserver"
)

type inbox struct {
	mu     sync.Mutex
	events []chatclient.Event
	ch     chan struct{}
}

func newInbox() *inbox { return &inbox{ch: make(chan struct{}, 1000)} }
func (b *inbox) add(e chatclient.Event) {
	b.mu.Lock()
	b.events = append(b.events, e)
	b.mu.Unlock()
	b.ch <- struct{}{}
}

// wait returns the first event of type typ (matching pred) within 5 s.
func (b *inbox) wait(t *testing.T, typ string, pred func(json.RawMessage) bool) json.RawMessage {
	t.Helper()
	deadline := time.After(5 * time.Second)
	seen := 0
	for {
		b.mu.Lock()
		for ; seen < len(b.events); seen++ {
			e := b.events[seen]
			if e.Type == typ && (pred == nil || pred(e.Data)) {
				b.mu.Unlock()
				return e.Data
			}
		}
		b.mu.Unlock()
		select {
		case <-b.ch:
		case <-deadline:
			t.Fatalf("no %q event", typ)
		}
	}
}

func setup(t *testing.T) (*httptest.Server, *chatserver.Server, string) {
	dir := t.TempDir()
	db, err := chatserver.OpenDB(filepath.Join(dir, "chat", "chat.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	s := chatserver.New(db, filepath.Join(dir, "chat", "uploads"))
	ts := httptest.NewServer(s.Handler())
	t.Cleanup(ts.Close)
	t.Cleanup(s.Stop)
	return ts, s, dir
}

func user(t *testing.T, base, name string) (*chatclient.Client, *inbox) {
	c, err := chatclient.New(base)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := c.Register(context.Background(), name, name+"@example.invalid", "haslo-"+name+"-123"); err != nil {
		t.Fatal(err)
	}
	in := newInbox()
	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)
	if err := c.Connect(ctx, in.add); err != nil {
		t.Fatal(err)
	}
	return c, in
}

func TestAccountsAndAuth(t *testing.T) {
	ts, _, _ := setup(t)
	c, _ := chatclient.New(ts.URL)
	ctx := context.Background()
	if _, err := c.Register(ctx, "ala", "ala@example.invalid", "krotkie"); err == nil {
		t.Fatal("short password accepted")
	}
	s, err := c.Register(ctx, "ala", "ala@example.invalid", "dlugie-haslo")
	if err != nil || !s.User.Admin {
		t.Fatal("first user should be admin", err)
	}
	if _, err := c.Register(ctx, "ALA", "x@example.invalid", "dlugie-haslo"); err == nil {
		t.Fatal("duplicate username (case-insensitive) accepted")
	}
	if _, err := c.Login(ctx, "ala", "zle-haslo"); err == nil {
		t.Fatal("bad password accepted")
	}
	if _, err := c.Login(ctx, "ala@example.invalid", "dlugie-haslo"); err != nil {
		t.Fatal(err)
	}
	// rate limit: repeated bad logins from one IP get 429
	var last error
	for i := 0; i < 8; i++ {
		_, last = c.Login(ctx, "ala", "zle")
	}
	if last == nil || !strings.Contains(last.Error(), "Za dużo") {
		t.Fatal("no login rate limit:", last)
	}
}

// A socket that does not authenticate first (or uses a user id instead of
// a token) gets nothing.
func TestSocketRequiresToken(t *testing.T) {
	ts, _, _ := setup(t)
	url := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws"
	for _, first := range []any{
		map[string]any{"type": "list_rooms"},
		map[string]any{"type": "auth", "user_id": 1},
		map[string]any{"type": "auth", "token": "zmyslony"},
	} {
		conn, _, err := websocket.DefaultDialer.Dial(url, nil)
		if err != nil {
			t.Fatal(err)
		}
		conn.WriteJSON(first)
		var ev map[string]any
		_ = conn.ReadJSON(&ev)
		if ev["type"] == "hello" {
			t.Fatalf("accepted %v", first)
		}
		conn.Close()
	}
	// foreign browser origin refused
	h := http.Header{"Origin": {"http://evil.example"}}
	if _, _, err := websocket.DefaultDialer.Dial(url, h); err == nil {
		t.Fatal("foreign origin accepted")
	}
}

func TestRoomsMessagesBlockingUploads(t *testing.T) {
	ts, _, dir := setup(t)
	ala, alaIn := user(t, ts.URL, "ala")
	ola, olaIn := user(t, ts.URL, "ola")

	ala.Send("create_room", map[string]any{"name": "Gracze", "password": "tajne"})
	joined := alaIn.wait(t, "room_joined", nil)
	var rj struct {
		Room struct{ ID int64 } `json:"room"`
	}
	json.Unmarshal(joined, &rj)

	ola.Send("join_specific_room", map[string]any{"room_id": rj.Room.ID, "password": "zle"})
	olaIn.wait(t, "error", func(d json.RawMessage) bool { return strings.Contains(string(d), "hasło") })
	ola.Send("join_specific_room", map[string]any{"room_id": rj.Room.ID, "password": "tajne"})
	olaIn.wait(t, "room_joined", nil)

	ala.Send("send_message", map[string]any{"room_id": rj.Room.ID, "content": "Cześć 🎮"})
	msg := olaIn.wait(t, "message", func(d json.RawMessage) bool { return strings.Contains(string(d), "Cześć 🎮") })
	var m chatserver.Message
	json.Unmarshal(msg, &m)

	ola.Send("edit_message", map[string]any{"message_id": m.ID, "content": "hack"})
	olaIn.wait(t, "error", func(d json.RawMessage) bool { return strings.Contains(string(d), "swoje") })
	ala.Send("edit_message", map[string]any{"message_id": m.ID, "content": "Cześć wszystkim"})
	olaIn.wait(t, "message_edited", func(d json.RawMessage) bool { return strings.Contains(string(d), "wszystkim") })
	ala.Send("delete_message", map[string]any{"message_id": m.ID})
	olaIn.wait(t, "message_deleted", nil)

	// DM + read receipt
	ala.Send("send_message", map[string]any{"to_user_id": ola.Session().User.ID, "content": "prywatnie"})
	olaIn.wait(t, "message", func(d json.RawMessage) bool { return strings.Contains(string(d), "prywatnie") })
	ola.Send("mark_read", map[string]any{"from_user_id": ala.Session().User.ID})
	alaIn.wait(t, "read", nil)

	// blocking stops DMs both ways
	ola.Send("block", map[string]any{"user_id": ala.Session().User.ID, "on": true})
	olaIn.wait(t, "blocked", nil)
	ala.Send("send_message", map[string]any{"to_user_id": ola.Session().User.ID, "content": "spam"})
	alaIn.wait(t, "error", func(d json.RawMessage) bool { return strings.Contains(string(d), "blokada") })

	// uploads: an image is accepted, an exe is not, and only participants may download
	img := filepath.Join(dir, "a.png")
	f, _ := os.Create(img)
	png.Encode(f, image.NewRGBA(image.Rect(0, 0, 4, 4)))
	f.Close()
	att, err := ala.Upload(context.Background(), img)
	if err != nil || att["mimetype"] != "image/png" {
		t.Fatal(att, err)
	}
	exe := filepath.Join(dir, "x.exe")
	os.WriteFile(exe, append([]byte("MZ"), make([]byte, 600)...), 0o644)
	if _, err := ala.Upload(context.Background(), exe); err == nil {
		t.Fatal("exe upload accepted")
	}
	ala.Send("send_message", map[string]any{"room_id": rj.Room.ID, "content": "", "attachment": att})
	olaIn.wait(t, "message", func(d json.RawMessage) bool { return strings.Contains(string(d), "server_filename") })
	if err := ola.Download(context.Background(), att["server_filename"].(string), filepath.Join(dir, "got.png")); err != nil {
		t.Fatal(err)
	}
	ewa, _ := user(t, ts.URL, "ewa")
	if err := ewa.Download(context.Background(), att["server_filename"].(string), filepath.Join(dir, "no.png")); err == nil {
		t.Fatal("non-member downloaded the attachment")
	}

	// history and user list
	ola.Send("history", map[string]any{"user_id": ala.Session().User.ID})
	olaIn.wait(t, "history", func(d json.RawMessage) bool { return strings.Contains(string(d), "prywatnie") })
	ola.Send("list_users", nil)
	olaIn.wait(t, "users", func(d json.RawMessage) bool { return strings.Contains(string(d), `"blocked":true`) })
}

func TestMessageRateLimit(t *testing.T) {
	ts, _, _ := setup(t)
	ala, in := user(t, ts.URL, "ala")
	for i := 0; i < 30; i++ {
		ala.Send("ping", nil)
	}
	in.wait(t, "error", func(d json.RawMessage) bool { return strings.Contains(string(d), "Zwolnij") })
}

func TestCorruptDBNotOverwritten(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "chat.db")
	junk := append([]byte("SQLite format 3\x00"), make([]byte, 5000)...)
	os.WriteFile(p, junk, 0o644)
	if _, err := chatserver.OpenDB(p); err == nil {
		t.Fatal("corrupt db accepted")
	}
	b, _ := os.ReadFile(p)
	if len(b) != len(junk) {
		t.Fatal("corrupt db modified")
	}
}

// A valid database of the Python server: tables kept, column added, a
// werkzeug pbkdf2 password still logs in (and is re-hashed with bcrypt).
func TestLegacyPythonDB(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "chat.db")
	db, _ := sql.Open("sqlite", p)
	_, err := db.Exec(`CREATE TABLE user (id INTEGER NOT NULL PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, email VARCHAR(120) NOT NULL UNIQUE,
		password_hash VARCHAR(128) NOT NULL, created_at DATETIME, is_banned BOOLEAN NOT NULL, is_admin BOOLEAN NOT NULL);
	CREATE TABLE message (id INTEGER NOT NULL PRIMARY KEY, sender_id INTEGER, receiver_id INTEGER, room_id INTEGER, content TEXT,
		timestamp DATETIME, edited_at DATETIME, replied_to_message_id INTEGER, attachment_server_filename VARCHAR(255),
		attachment_original_filename VARCHAR(255), attachment_mimetype VARCHAR(100), is_read_by_receiver BOOLEAN NOT NULL);
	INSERT INTO user VALUES (1, 'stary', 's@example.invalid',
		'pbkdf2:sha256:1000$salt1234$` + legacyHash + `', NULL, 0, 0);`)
	if err != nil {
		t.Fatal(err)
	}
	db.Close()
	db2, err := chatserver.OpenDB(p)
	if err != nil {
		t.Fatal(err)
	}
	s := chatserver.New(db2, dir)
	ts := httptest.NewServer(s.Handler())
	defer ts.Close()
	c, _ := chatclient.New(ts.URL)
	if _, err := c.Login(context.Background(), "stary", "haslo123"); err != nil {
		t.Fatal(err)
	}
	var h string
	db2.QueryRow(`SELECT password_hash FROM user WHERE id = 1`).Scan(&h)
	if !strings.HasPrefix(h, "$2") {
		t.Fatal("not re-hashed")
	}
	db2.Close()
}

// pbkdf2-hmac-sha256("haslo123", "salt1234", 1000, 32) in hex.
var legacyHash = func() string {
	return pbkdf2Hex("haslo123", "salt1234", 1000)
}()
