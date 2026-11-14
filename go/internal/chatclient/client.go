// Package chatclient talks to a chatserver: REST login/register/upload and
// a WebSocket that authenticates with the session token in its first frame.
package chatclient

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Event from the server.
type Event struct {
	Type string          `json:"type"`
	ID   int64           `json:"id,omitempty"`
	Data json.RawMessage `json:"data,omitempty"`
}

// Session is a logged-in account.
type Session struct {
	Token string `json:"-"`
	User  struct {
		ID       int64  `json:"id"`
		Username string `json:"username"`
		Admin    bool   `json:"admin"`
	} `json:"user"`
}

// Client is one server connection.
type Client struct {
	Base string // http://host:port
	HTTP *http.Client

	mu   sync.Mutex
	conn *websocket.Conn
	seq  int64
	sess *Session
}

// New validates the base URL (http/https only).
func New(base string) (*Client, error) {
	u, err := url.Parse(strings.TrimRight(strings.TrimSpace(base), "/"))
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" {
		return nil, errors.New("adres serwera musi zaczynać się od http:// lub https://")
	}
	return &Client{Base: u.String(), HTTP: &http.Client{Timeout: 20 * time.Second}}, nil
}

func (c *Client) post(ctx context.Context, path string, in, out any, token string) error {
	b, _ := json.Marshal(in)
	req, err := http.NewRequestWithContext(ctx, "POST", c.Base+path, bytes.NewReader(b))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	return c.do(req, out)
}

func (c *Client) do(req *http.Request, out any) error {
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return fmt.Errorf("brak połączenia z serwerem czatu: %v", unwrapURL(err))
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if resp.StatusCode != 200 {
		var e struct{ Error string }
		if json.Unmarshal(body, &e) == nil && e.Error != "" {
			return errors.New(e.Error)
		}
		return fmt.Errorf("serwer czatu: HTTP %d", resp.StatusCode)
	}
	if out != nil {
		return json.Unmarshal(body, out)
	}
	return nil
}

func unwrapURL(err error) error {
	var ue *url.Error
	if errors.As(err, &ue) {
		return ue.Err
	}
	return err
}

func (c *Client) auth(ctx context.Context, path string, in any) (*Session, error) {
	var out struct {
		Token string          `json:"token"`
		User  json.RawMessage `json:"user"`
	}
	if err := c.post(ctx, path, in, &out, ""); err != nil {
		return nil, err
	}
	s := &Session{Token: out.Token}
	_ = json.Unmarshal(out.User, &s.User)
	c.mu.Lock()
	c.sess = s
	c.mu.Unlock()
	return s, nil
}

// Login with username or e-mail.
func (c *Client) Login(ctx context.Context, login, password string) (*Session, error) {
	return c.auth(ctx, "/api/login", map[string]string{"login": login, "password": password})
}

// Register a new account.
func (c *Client) Register(ctx context.Context, username, email, password string) (*Session, error) {
	return c.auth(ctx, "/api/register", map[string]string{"username": username, "email": email, "password": password})
}

// Session returns the current session (nil when logged out).
func (c *Client) Session() *Session {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.sess
}

func (c *Client) token() string {
	if s := c.Session(); s != nil {
		return s.Token
	}
	return ""
}

// Connect opens the socket and delivers events to fn until ctx ends or
// the connection drops (then fn gets {"type":"disconnected"}).
func (c *Client) Connect(ctx context.Context, fn func(Event)) error {
	tok := c.token()
	if tok == "" {
		return errors.New("najpierw się zaloguj")
	}
	wsURL := "ws" + strings.TrimPrefix(c.Base, "http") + "/ws"
	d := websocket.Dialer{HandshakeTimeout: 15 * time.Second}
	conn, _, err := d.DialContext(ctx, wsURL, nil)
	if err != nil {
		return fmt.Errorf("brak połączenia z serwerem czatu: %v", err)
	}
	if err := conn.WriteJSON(map[string]string{"type": "auth", "token": tok}); err != nil {
		conn.Close()
		return err
	}
	_ = conn.SetReadDeadline(time.Now().Add(15 * time.Second))
	var first Event
	if err := conn.ReadJSON(&first); err != nil {
		conn.Close()
		return err
	}
	if first.Type != "hello" {
		conn.Close()
		var m struct{ Message string }
		_ = json.Unmarshal(first.Data, &m)
		return errors.New(m.Message)
	}
	_ = conn.SetReadDeadline(time.Time{})
	c.mu.Lock()
	c.conn = conn
	c.mu.Unlock()
	fn(first)
	go func() {
		<-ctx.Done()
		conn.Close()
	}()
	go func() {
		defer func() {
			c.mu.Lock()
			if c.conn == conn {
				c.conn = nil
			}
			c.mu.Unlock()
			fn(Event{Type: "disconnected"})
		}()
		for {
			var ev Event
			if err := conn.ReadJSON(&ev); err != nil {
				return
			}
			fn(ev)
		}
	}()
	return nil
}

// Send emits an event; returns the request id echoed in the reply.
func (c *Client) Send(typ string, data any) (int64, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.conn == nil {
		return 0, errors.New("brak połączenia z czatem")
	}
	c.seq++
	_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
	return c.seq, c.conn.WriteJSON(map[string]any{"type": typ, "id": c.seq, "data": data})
}

// Connected reports an open socket.
func (c *Client) Connected() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.conn != nil
}

// Close ends the socket.
func (c *Client) Close() {
	c.mu.Lock()
	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}
	c.mu.Unlock()
}

// Logout ends the session on the server.
func (c *Client) Logout(ctx context.Context) {
	if t := c.token(); t != "" {
		_ = c.post(ctx, "/api/logout", map[string]string{}, nil, t)
	}
	c.Close()
	c.mu.Lock()
	c.sess = nil
	c.mu.Unlock()
}

// Upload sends a file; returns the attachment fields for send_message.
func (c *Client) Upload(ctx context.Context, path string) (map[string]any, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	part, err := mw.CreateFormFile("file", filepath.Base(path))
	if err != nil {
		return nil, err
	}
	if _, err := io.Copy(part, io.LimitReader(f, 11<<20)); err != nil {
		return nil, err
	}
	mw.Close()
	req, err := http.NewRequestWithContext(ctx, "POST", c.Base+"/api/upload", &buf)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", mw.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+c.token())
	var out map[string]any
	return out, c.do(req, &out)
}

// Download saves an attachment to dst.
func (c *Client) Download(ctx context.Context, serverName, dst string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", c.Base+"/api/file/"+url.PathEscape(serverName), nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+c.token())
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return unwrapURL(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("pobieranie pliku: HTTP %d", resp.StatusCode)
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	_, err = io.Copy(out, io.LimitReader(resp.Body, 11<<20))
	out.Close()
	return err
}
