package winsys

import (
	"crypto/rand"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"sync"
	"time"
)

// DiscordClientID is the public application id the Python launcher used.
const DiscordClientID = "1300136792636522517"

// Discord is a minimal Rich Presence client over the local IPC pipe
// (\\.\pipe\discord-ipc-N). It is optional: when Discord is not running
// every call is a no-op that reports an error once.
type Discord struct {
	ClientID string
	Dial     func() (io.ReadWriteCloser, error) // replaced in tests

	mu   sync.Mutex
	conn io.ReadWriteCloser
}

const (
	opHandshake = 0
	opFrame     = 1
	opClose     = 2
)

func writeFrame(w io.Writer, op uint32, payload any) error {
	b, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	hdr := make([]byte, 8)
	binary.LittleEndian.PutUint32(hdr[0:], op)
	binary.LittleEndian.PutUint32(hdr[4:], uint32(len(b)))
	_, err = w.Write(append(hdr, b...))
	return err
}

func readFrame(r io.Reader) (uint32, []byte, error) {
	hdr := make([]byte, 8)
	if _, err := io.ReadFull(r, hdr); err != nil {
		return 0, nil, err
	}
	op, n := binary.LittleEndian.Uint32(hdr[0:]), binary.LittleEndian.Uint32(hdr[4:])
	if n > 1<<20 {
		return 0, nil, errors.New("discord: frame too large")
	}
	b := make([]byte, n)
	_, err := io.ReadFull(r, b)
	return op, b, err
}

func dialPipe() (io.ReadWriteCloser, error) {
	for i := 0; i < 10; i++ {
		f, err := os.OpenFile(fmt.Sprintf(`\\.\pipe\discord-ipc-%d`, i), os.O_RDWR, 0)
		if err == nil {
			return f, nil
		}
	}
	return nil, errors.New("Discord nie jest uruchomiony")
}

func nonce() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func (d *Discord) connect() error {
	if d.conn != nil {
		return nil
	}
	dial := d.Dial
	if dial == nil {
		dial = dialPipe
	}
	c, err := dial()
	if err != nil {
		return err
	}
	id := d.ClientID
	if id == "" {
		id = DiscordClientID
	}
	if err := writeFrame(c, opHandshake, map[string]any{"v": 1, "client_id": id}); err != nil {
		c.Close()
		return err
	}
	if _, _, err := readFrame(c); err != nil { // READY
		c.Close()
		return err
	}
	d.conn = c
	return nil
}

// Activity is what Discord shows.
type Activity struct {
	Details string
	State   string
	Start   time.Time // zero = no elapsed timer
}

// Set updates the presence (nil clears it).
func (d *Discord) Set(a *Activity) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	if err := d.connect(); err != nil {
		return err
	}
	var act any
	if a != nil {
		m := map[string]any{"details": trunc(a.Details), "state": trunc(a.State),
			"assets": map[string]string{"large_image": "logo", "large_text": "Game Launcher"}}
		if !a.Start.IsZero() {
			m["timestamps"] = map[string]int64{"start": a.Start.Unix()}
		}
		act = m
	}
	err := writeFrame(d.conn, opFrame, map[string]any{"cmd": "SET_ACTIVITY", "nonce": nonce(),
		"args": map[string]any{"pid": os.Getpid(), "activity": act}})
	if err == nil {
		_, _, err = readFrame(d.conn)
	}
	if err != nil {
		d.conn.Close()
		d.conn = nil
	}
	return err
}

func trunc(s string) string {
	r := []rune(s)
	if len(r) > 120 {
		return string(r[:120])
	}
	if len(r) == 1 {
		return s + " " // Discord needs >= 2 characters
	}
	return s
}

// Close ends the connection.
func (d *Discord) Close() {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.conn != nil {
		_ = writeFrame(d.conn, opClose, map[string]any{})
		d.conn.Close()
		d.conn = nil
	}
}
