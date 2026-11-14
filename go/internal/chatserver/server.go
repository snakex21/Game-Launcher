package chatserver

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/mail"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/gorilla/websocket"
)

// Limits.
const (
	MaxUpload       = 10 << 20
	MaxMessageRunes = 4000
	SessionTTL      = 30 * 24 * time.Hour
	historyPage     = 50
)

// AllowedUploadTypes maps sniffed content types to file extensions.
var AllowedUploadTypes = map[string]string{
	"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp",
	"text/plain; charset=utf-8": ".txt", "application/pdf": ".pdf", "application/zip": ".zip",
}

// Server is a running chat server.
type Server struct {
	DB         *sql.DB
	UploadDir  string
	loginLimit *Limiter
	regLimit   *Limiter
	msgLimit   *Limiter
	upLimit    *Limiter
	now        func() time.Time

	mu      sync.Mutex
	clients map[*client]bool
	http    *http.Server
	Addr    string
}

// New creates a server on an open DB.
func New(db *sql.DB, uploadDir string) *Server {
	return &Server{
		DB: db, UploadDir: uploadDir,
		loginLimit: NewLimiter(0.2, 5), // 5 tries, then 1 per 5 s per IP
		regLimit:   NewLimiter(0.05, 3),
		msgLimit:   NewLimiter(3, 10), // per user
		upLimit:    NewLimiter(0.2, 5),
		now:        time.Now,
		clients:    map[*client]bool{},
	}
}

// User is public account info.
type User struct {
	ID       int64  `json:"id"`
	Username string `json:"username"`
	Admin    bool   `json:"admin,omitempty"`
	Online   bool   `json:"online"`
}

type apiError struct {
	Error string `json:"error"`
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func clientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// Handler builds the HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /api/register", s.register)
	mux.HandleFunc("POST /api/login", s.login)
	mux.HandleFunc("POST /api/logout", s.logout)
	mux.HandleFunc("POST /api/upload", s.upload)
	mux.HandleFunc("GET /api/file/{name}", s.file)
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, 200, map[string]string{"server": "gl-chat", "version": "1"})
	})
	mux.HandleFunc("GET /ws", s.ws)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		r.Body = http.MaxBytesReader(w, r.Body, MaxUpload+(1<<20))
		mux.ServeHTTP(w, r)
	})
}

// Start listens on addr ("127.0.0.1:5000").
func (s *Server) Start(addr string) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("port czatu zajęty albo niedostępny (%s): %v", addr, err)
	}
	s.Addr = ln.Addr().String()
	s.http = &http.Server{Handler: s.Handler(), ReadHeaderTimeout: 10 * time.Second, MaxHeaderBytes: 32 << 10}
	go func() {
		if err := s.http.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Printf("[chat] %v", err)
		}
	}()
	return nil
}

// Stop shuts down the server and closes all sockets.
func (s *Server) Stop() {
	if s.http != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		_ = s.http.Shutdown(ctx)
		cancel()
	}
	s.mu.Lock()
	for c := range s.clients {
		c.conn.Close()
	}
	s.mu.Unlock()
}

// ------------------------------------------------------------- accounts

func validUsername(u string) bool {
	if l := utf8.RuneCountInString(u); l < 3 || l > 32 {
		return false
	}
	for _, r := range u {
		if r < 32 || strings.ContainsRune(`<>"'/\`, r) {
			return false
		}
	}
	return true
}

func (s *Server) register(w http.ResponseWriter, r *http.Request) {
	if !s.regLimit.Allow(clientIP(r)) {
		writeJSON(w, 429, apiError{"Za dużo prób rejestracji – spróbuj później."})
		return
	}
	var in struct{ Username, Email, Password string }
	if err := json.NewDecoder(io.LimitReader(r.Body, 8<<10)).Decode(&in); err != nil {
		writeJSON(w, 400, apiError{"Nieprawidłowe dane."})
		return
	}
	in.Username = strings.TrimSpace(in.Username)
	in.Email = strings.TrimSpace(in.Email)
	if !validUsername(in.Username) {
		writeJSON(w, 400, apiError{"Nazwa użytkownika: 3–32 znaki, bez < > \" ' / \\."})
		return
	}
	if _, err := mail.ParseAddress(in.Email); err != nil || len(in.Email) > 120 {
		writeJSON(w, 400, apiError{"Nieprawidłowy adres e-mail."})
		return
	}
	if l := len(in.Password); l < 8 || l > 72 {
		writeJSON(w, 400, apiError{"Hasło: 8–72 znaki."})
		return
	}
	var black int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM email_blacklist WHERE email = ?`, in.Email).Scan(&black)
	if black > 0 {
		writeJSON(w, 403, apiError{"Ten adres e-mail jest zablokowany."})
		return
	}
	hash, err := HashPassword(in.Password)
	if err != nil {
		writeJSON(w, 500, apiError{"Błąd serwera."})
		return
	}
	var count int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM user`).Scan(&count)
	res, err := s.DB.Exec(`INSERT INTO user(username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)`, in.Username, in.Email, hash, count == 0)
	if err != nil {
		writeJSON(w, 409, apiError{"Nazwa użytkownika lub e-mail jest już zajęty."})
		return
	}
	id, _ := res.LastInsertId()
	s.issueSession(w, id)
}

func (s *Server) issueSession(w http.ResponseWriter, userID int64) {
	token, hash := NewToken()
	exp := s.now().Add(SessionTTL).UTC().Format("2006-01-02 15:04:05")
	if _, err := s.DB.Exec(`INSERT INTO session(token_hash, user_id, expires_at) VALUES (?, ?, ?)`, hash, userID, exp); err != nil {
		writeJSON(w, 500, apiError{"Błąd serwera."})
		return
	}
	u, _ := s.userByID(userID)
	writeJSON(w, 200, map[string]any{"token": token, "user": u})
}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	if !s.loginLimit.Allow(clientIP(r)) {
		writeJSON(w, 429, apiError{"Za dużo prób logowania – odczekaj chwilę."})
		return
	}
	var in struct{ Login, Password string }
	if err := json.NewDecoder(io.LimitReader(r.Body, 8<<10)).Decode(&in); err != nil {
		writeJSON(w, 400, apiError{"Nieprawidłowe dane."})
		return
	}
	var id int64
	var hash string
	var banned bool
	err := s.DB.QueryRow(`SELECT id, password_hash, is_banned FROM user WHERE username = ? OR email = ?`, strings.TrimSpace(in.Login), strings.TrimSpace(in.Login)).Scan(&id, &hash, &banned)
	if err != nil {
		_, _ = HashPassword("timing-equaliser")
		writeJSON(w, 401, apiError{"Nieprawidłowy login lub hasło."})
		return
	}
	ok, legacy := CheckPassword(hash, in.Password)
	if !ok {
		writeJSON(w, 401, apiError{"Nieprawidłowy login lub hasło."})
		return
	}
	if banned {
		writeJSON(w, 403, apiError{"Konto jest zablokowane."})
		return
	}
	if legacy {
		if nh, err := HashPassword(in.Password); err == nil {
			_, _ = s.DB.Exec(`UPDATE user SET password_hash = ? WHERE id = ?`, nh, id)
		}
	}
	s.issueSession(w, id)
}

func bearer(r *http.Request) string {
	h := r.Header.Get("Authorization")
	if strings.HasPrefix(h, "Bearer ") {
		return strings.TrimSpace(h[7:])
	}
	return ""
}

// Authenticate returns the user of a session token.
func (s *Server) Authenticate(token string) (*User, error) {
	if token == "" {
		return nil, errors.New("brak tokenu")
	}
	var id int64
	err := s.DB.QueryRow(`SELECT s.user_id FROM session s JOIN user u ON u.id = s.user_id
		WHERE s.token_hash = ? AND s.expires_at > ? AND u.is_banned = 0`, TokenHash(token), s.now().UTC().Format("2006-01-02 15:04:05")).Scan(&id)
	if err != nil {
		return nil, errors.New("sesja wygasła – zaloguj się ponownie")
	}
	return s.userByID(id)
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	_, _ = s.DB.Exec(`DELETE FROM session WHERE token_hash = ?`, TokenHash(bearer(r)))
	writeJSON(w, 200, map[string]bool{"ok": true})
}

func (s *Server) userByID(id int64) (*User, error) {
	u := &User{ID: id}
	err := s.DB.QueryRow(`SELECT username, is_admin FROM user WHERE id = ?`, id).Scan(&u.Username, &u.Admin)
	if err != nil {
		return nil, err
	}
	u.Online = s.online(id)
	return u, nil
}

// --------------------------------------------------------------- files

func randomName() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func (s *Server) upload(w http.ResponseWriter, r *http.Request) {
	u, err := s.Authenticate(bearer(r))
	if err != nil {
		writeJSON(w, 401, apiError{err.Error()})
		return
	}
	if !s.upLimit.Allow(fmt.Sprint(u.ID)) {
		writeJSON(w, 429, apiError{"Za dużo plików naraz."})
		return
	}
	f, hdr, err := r.FormFile("file")
	if err != nil {
		writeJSON(w, 400, apiError{"Brak pliku albo plik większy niż 10 MB."})
		return
	}
	defer f.Close()
	if hdr.Size > MaxUpload {
		writeJSON(w, 413, apiError{"Plik jest większy niż 10 MB."})
		return
	}
	head := make([]byte, 512)
	n, _ := io.ReadFull(f, head)
	ctype := http.DetectContentType(head[:n])
	ext, ok := AllowedUploadTypes[ctype]
	if !ok {
		writeJSON(w, 415, apiError{"Niedozwolony typ pliku (" + ctype + "). Dozwolone: obrazy, txt, pdf, zip."})
		return
	}
	if err := os.MkdirAll(s.UploadDir, 0o755); err != nil {
		writeJSON(w, 500, apiError{"Błąd serwera."})
		return
	}
	name := randomName() + ext
	out, err := os.Create(filepath.Join(s.UploadDir, name))
	if err != nil {
		writeJSON(w, 500, apiError{"Błąd serwera."})
		return
	}
	_, _ = out.Write(head[:n])
	written, err := io.Copy(out, io.LimitReader(f, MaxUpload))
	out.Close()
	if err != nil || written+int64(n) > MaxUpload {
		os.Remove(filepath.Join(s.UploadDir, name))
		writeJSON(w, 413, apiError{"Plik jest większy niż 10 MB."})
		return
	}
	orig := filepath.Base(strings.ReplaceAll(hdr.Filename, `\`, "/"))
	if len(orig) > 200 {
		orig = orig[:200]
	}
	writeJSON(w, 200, map[string]any{"server_filename": name, "original_filename": orig, "mimetype": strings.Split(ctype, ";")[0], "size": written + int64(n)})
}

func (s *Server) file(w http.ResponseWriter, r *http.Request) {
	u, err := s.Authenticate(bearer(r))
	if err != nil {
		writeJSON(w, 401, apiError{err.Error()})
		return
	}
	name := r.PathValue("name")
	if len(name) > 64 || strings.ContainsAny(name, `/\:`) || strings.HasPrefix(name, ".") {
		http.NotFound(w, r)
		return
	}
	// only participants may download: room member or DM party
	var allowed int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM message m WHERE m.attachment_server_filename = ?1 AND m.is_deleted = 0 AND (
		m.sender_id = ?2 OR m.receiver_id = ?2 OR m.room_id IN (SELECT room_id FROM room_membership WHERE user_id = ?2))`, name, u.ID).Scan(&allowed)
	if allowed == 0 {
		var orig string
		if err := s.DB.QueryRow(`SELECT attachment_original_filename FROM message WHERE attachment_server_filename = ? LIMIT 1`, name).Scan(&orig); err == nil {
			http.Error(w, "Forbidden", 403)
			return
		}
	}
	w.Header().Set("Content-Disposition", "attachment")
	w.Header().Set("Content-Security-Policy", "default-src 'none'")
	http.ServeFile(w, r, filepath.Join(s.UploadDir, name))
}

// -------------------------------------------------------------- sockets

type client struct {
	s      *Server
	conn   *websocket.Conn
	user   *User
	send   chan []byte
	mu     sync.Mutex
	closed bool
	rooms  map[int64]bool // rooms joined on this socket
}

var upgrader = websocket.Upgrader{
	ReadBufferSize: 4096, WriteBufferSize: 4096,
	// The launcher's Go client sends no Origin; browsers must be same-host.
	CheckOrigin: func(r *http.Request) bool {
		o := r.Header.Get("Origin")
		return o == "" || o == "http://"+r.Host || o == "https://"+r.Host
	},
}

func (s *Server) online(id int64) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	for c := range s.clients {
		if c.user != nil && c.user.ID == id {
			return true
		}
	}
	return false
}

// ws: the first frame must be {"type":"auth","token":"..."} within 10 s.
func (s *Server) ws(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	conn.SetReadLimit(64 << 10)
	_ = conn.SetReadDeadline(s.now().Add(10 * time.Second))
	var first struct{ Type, Token string }
	if err := conn.ReadJSON(&first); err != nil || first.Type != "auth" {
		_ = conn.WriteJSON(Event{Type: "error", Data: map[string]string{"message": "Wymagane uwierzytelnienie."}})
		conn.Close()
		return
	}
	u, err := s.Authenticate(first.Token)
	if err != nil {
		_ = conn.WriteJSON(Event{Type: "auth_failed", Data: map[string]string{"message": err.Error()}})
		conn.Close()
		return
	}
	c := &client{s: s, conn: conn, user: u, send: make(chan []byte, 256), rooms: map[int64]bool{}}
	s.mu.Lock()
	s.clients[c] = true
	s.mu.Unlock()
	go c.writer()
	u.Online = true
	c.emit("hello", map[string]any{"user": u})
	s.broadcastPresence(u.ID, true)
	c.reader()
}

// Event is one socket frame.
type Event struct {
	Type string          `json:"type"`
	ID   int64           `json:"id,omitempty"` // client request id, echoed in replies
	Data any             `json:"data,omitempty"`
	Raw  json.RawMessage `json:"-"`
}

type inbound struct {
	Type string          `json:"type"`
	ID   int64           `json:"id"`
	Data json.RawMessage `json:"data"`
}

func (c *client) emit(typ string, data any) { c.emitID(typ, 0, data) }

func (c *client) emitID(typ string, id int64, data any) {
	b, err := json.Marshal(Event{Type: typ, ID: id, Data: data})
	if err != nil {
		return
	}
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return
	}
	select {
	case c.send <- b:
		c.mu.Unlock()
	default: // slow client: drop it
		c.mu.Unlock()
		c.close()
	}
}

func (c *client) close() {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return
	}
	c.closed = true
	close(c.send)
	c.mu.Unlock()
	c.s.mu.Lock()
	delete(c.s.clients, c)
	c.s.mu.Unlock()
	c.conn.Close()
	if !c.s.online(c.user.ID) {
		c.s.broadcastPresence(c.user.ID, false)
	}
}

func (c *client) writer() {
	ping := time.NewTicker(30 * time.Second)
	defer ping.Stop()
	for {
		select {
		case b, ok := <-c.send:
			if !ok {
				return
			}
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.TextMessage, b); err != nil {
				c.close()
				return
			}
		case <-ping.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				c.close()
				return
			}
		}
	}
}

func (c *client) reader() {
	defer c.close()
	c.conn.SetPongHandler(func(string) error { return c.conn.SetReadDeadline(time.Now().Add(90 * time.Second)) })
	for {
		_ = c.conn.SetReadDeadline(time.Now().Add(90 * time.Second))
		var in inbound
		if err := c.conn.ReadJSON(&in); err != nil {
			return
		}
		if !c.s.msgLimit.Allow(fmt.Sprint(c.user.ID)) {
			c.emitID("error", in.ID, map[string]string{"message": "Zwolnij – za dużo wiadomości."})
			continue
		}
		if err := c.s.handle(c, in); err != nil {
			c.emitID("error", in.ID, map[string]string{"message": err.Error()})
		}
	}
}

// each runs fn for every connected client (outside the lock).
func (s *Server) each(fn func(c *client)) {
	s.mu.Lock()
	list := make([]*client, 0, len(s.clients))
	for c := range s.clients {
		list = append(list, c)
	}
	s.mu.Unlock()
	for _, c := range list {
		fn(c)
	}
}

func (s *Server) broadcastPresence(userID int64, on bool) {
	s.each(func(c *client) { c.emit("presence", map[string]any{"user_id": userID, "online": on}) })
}
