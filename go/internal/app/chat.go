package app

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/snakex21/game-launcher/go/internal/bridge"
	"github.com/snakex21/game-launcher/go/internal/chatclient"
	"github.com/snakex21/game-launcher/go/internal/chatserver"
	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/store"
)

// chatState is the launcher's chat connection and optional local server.
type chatState struct {
	mu        sync.Mutex
	client    *chatclient.Client
	cancel    context.CancelFunc
	serverID  string
	server    *chatserver.Server
	serverErr string
}

// ChatServerView is a configured server (no credentials).
type ChatServerView struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	URL       string `json:"url"`
	Default   bool   `json:"default"`
	Remember  bool   `json:"remember"`
	AutoLogin bool   `json:"autoLogin"`
	Login     string `json:"login"` // e-mail/username, not secret
	HasPass   bool   `json:"hasPassword"`
}

// ChatStatus is the chat page state.
type ChatStatus struct {
	Servers   []ChatServerView `json:"servers"`
	Active    string           `json:"active"`
	Connected bool             `json:"connected"`
	User      any              `json:"user"`
	Host      map[string]any   `json:"host"`
}

func (a *App) chatServers() (list []ChatServerView, active string) {
	a.S.ReadLocal(func(l *ojson.Object) {
		active = l.Str("active_chat_server_id")
		for _, s := range l.Arr("chat_servers") {
			o, ok := s.(*ojson.Object)
			if !ok {
				continue
			}
			c := o.Obj("credentials")
			list = append(list, ChatServerView{ID: o.Str("id"), Name: o.Str("name"), URL: o.Str("url"), Default: o.Bool("is_default", false),
				Remember: o.Bool("remember_credentials", false), AutoLogin: o.Bool("auto_login_to_server", false),
				Login: c.Str("email"), HasPass: c.Str("password") != ""})
		}
	})
	if list == nil {
		list = []ChatServerView{}
	}
	return
}

func (a *App) chatStatus() ChatStatus {
	st := ChatStatus{}
	st.Servers, st.Active = a.chatServers()
	a.chat.mu.Lock()
	if a.chat.client != nil && a.chat.client.Connected() {
		st.Connected = true
		if s := a.chat.client.Session(); s != nil {
			st.User = s.User
		}
		st.Active = a.chat.serverID
	}
	host := map[string]any{"running": a.chat.server != nil, "error": a.chat.serverErr}
	if a.chat.server != nil {
		host["addr"] = a.chat.server.Addr
	}
	a.chat.mu.Unlock()
	a.S.ReadLocal(func(l *ojson.Object) {
		host["enabled"] = l.Bool("chat_host_server", false)
		host["port"] = l.Int("chat_host_port", store.DefaultChatServerPort)
		host["lan"] = l.Bool("chat_host_lan", false)
	})
	host["db"] = a.S.L.ChatDB
	st.Host = host
	return st
}

// startChatHost runs the embedded chat server when enabled in settings.
// data/chat/chat.db is created only here (i.e. when chat hosting is used).
func (a *App) startChatHost() {
	var enabled, lan bool
	var port int64
	a.S.ReadLocal(func(l *ojson.Object) {
		enabled = l.Bool("chat_host_server", false)
		lan = l.Bool("chat_host_lan", false)
		port = l.Int("chat_host_port", store.DefaultChatServerPort)
	})
	a.chat.mu.Lock()
	old := a.chat.server
	a.chat.server, a.chat.serverErr = nil, ""
	a.chat.mu.Unlock()
	if old != nil {
		old.Stop()
		_ = old.DB.Close()
	}
	if !enabled {
		return
	}
	db, err := chatserver.OpenDB(a.S.L.ChatDB)
	if err != nil {
		a.chat.mu.Lock()
		a.chat.serverErr = err.Error()
		a.chat.mu.Unlock()
		return
	}
	srv := chatserver.New(db, filepath.Join(filepath.Dir(a.S.L.ChatDB), "uploads"))
	host := "127.0.0.1"
	if lan {
		host = "0.0.0.0"
	}
	if err := srv.Start(net.JoinHostPort(host, fmt.Sprint(port))); err != nil {
		db.Close()
		a.chat.mu.Lock()
		a.chat.serverErr = err.Error()
		a.chat.mu.Unlock()
		return
	}
	log.Printf("[chat] local server on %s", srv.Addr)
	a.chat.mu.Lock()
	a.chat.server = srv
	a.chat.mu.Unlock()
}

func (a *App) stopChat() {
	a.chat.mu.Lock()
	c, cancel, srv := a.chat.client, a.chat.cancel, a.chat.server
	a.chat.client, a.chat.cancel, a.chat.server = nil, nil, nil
	a.chat.mu.Unlock()
	if cancel != nil {
		cancel()
	}
	if c != nil {
		c.Close()
	}
	if srv != nil {
		srv.Stop()
		_ = srv.DB.Close()
	}
}

func (a *App) chatHost(_ context.Context, in struct {
	Enabled bool  `json:"enabled"`
	Port    int64 `json:"port"`
	LAN     bool  `json:"lan"`
}) (any, error) {
	if in.Port < 1024 || in.Port > 65535 {
		return nil, bridge.Errf("Port musi być w zakresie 1024–65535.")
	}
	var remotePort int64
	a.S.ReadLocal(func(l *ojson.Object) { remotePort = l.Int("remote_control_port", store.DefaultRemoteControlPort) })
	if in.Port == remotePort {
		return nil, bridge.Errf("Ten port zajmuje pilot WWW.")
	}
	if err := a.S.UpdateLocal(func(l *ojson.Object) error {
		l.Set("chat_host_server", in.Enabled)
		l.Set("chat_host_port", in.Port)
		l.Set("chat_host_lan", in.LAN)
		return nil
	}); err != nil {
		return nil, err
	}
	a.startChatHost()
	return a.chatStatus(), nil
}

type chatConnectIn struct {
	ServerID  string `json:"serverId"`
	Login     string `json:"login"`
	Password  string `json:"password"` // "" = use the remembered one
	Email     string `json:"email"`
	Register  bool   `json:"register"`
	Remember  bool   `json:"remember"`
	AutoLogin bool   `json:"autoLogin"`
}

func (a *App) chatConnect(ctx context.Context, in chatConnectIn) (any, error) {
	var url, savedLogin, savedPass string
	found := false
	a.S.ReadLocal(func(l *ojson.Object) {
		for _, s := range l.Arr("chat_servers") {
			if o, ok := s.(*ojson.Object); ok && o.Str("id") == in.ServerID {
				found = true
				url = o.Str("url")
				savedLogin = o.Obj("credentials").Str("email")
				savedPass = o.Obj("credentials").Str("password")
			}
		}
	})
	if !found {
		return nil, bridge.Errf("Wybierz serwer czatu.")
	}
	login, pass := strings.TrimSpace(in.Login), in.Password
	if login == "" {
		login = savedLogin
	}
	if pass == "" && savedPass != "" {
		p, err := store.RevealValue(savedPass)
		if err != nil {
			return nil, bridge.Errf("Zapamiętane hasło jest nieczytelne na tym komputerze – wpisz je ponownie.")
		}
		pass = p
	}
	if login == "" || pass == "" {
		return nil, bridge.Errf("Podaj login i hasło.")
	}
	c, err := chatclient.New(url)
	if err != nil {
		return nil, err
	}
	if in.Register {
		_, err = c.Register(ctx, login, in.Email, pass)
	} else {
		_, err = c.Login(ctx, login, pass)
	}
	if err != nil {
		return nil, err
	}
	a.chatDisconnect()
	cctx, cancel := context.WithCancel(context.Background())
	if err := c.Connect(cctx, func(ev chatclient.Event) { a.emit("chat:event", ev) }); err != nil {
		cancel()
		return nil, err
	}
	a.chat.mu.Lock()
	a.chat.client, a.chat.cancel, a.chat.serverID = c, cancel, in.ServerID
	a.chat.mu.Unlock()
	// remember (DPAPI) or forget the credentials
	enc := ""
	if in.Remember {
		enc, err = store.ProtectValue(pass)
		if err != nil {
			return nil, err
		}
	}
	_ = a.S.UpdateLocal(func(l *ojson.Object) error {
		for _, s := range l.Arr("chat_servers") {
			if o, ok := s.(*ojson.Object); ok && o.Str("id") == in.ServerID {
				cred := ojson.NewObject()
				if in.Remember {
					cred.Set("email", login)
					cred.Set("password", enc)
				}
				o.Set("credentials", cred)
				o.Set("remember_credentials", in.Remember)
				o.Set("auto_login_to_server", in.Remember && in.AutoLogin)
			}
		}
		l.Set("active_chat_server_id", in.ServerID)
		return nil
	})
	return a.chatStatus(), nil
}

// chatAutoConnect logs in to the active server when auto login is on.
func (a *App) chatAutoConnect() {
	list, active := a.chatServers()
	for _, s := range list {
		if s.ID == active && s.AutoLogin && s.HasPass {
			if _, err := a.chatConnect(context.Background(), chatConnectIn{ServerID: s.ID, Remember: true, AutoLogin: true}); err != nil {
				log.Printf("[chat] auto login: %v", err)
			}
		}
	}
}

func (a *App) chatDisconnect() {
	a.chat.mu.Lock()
	c, cancel := a.chat.client, a.chat.cancel
	a.chat.client, a.chat.cancel = nil, nil
	a.chat.mu.Unlock()
	if cancel != nil {
		cancel()
	}
	if c != nil {
		c.Close()
	}
}

func (a *App) chatLogout(ctx context.Context, _ empty) (any, error) {
	a.chat.mu.Lock()
	c := a.chat.client
	a.chat.mu.Unlock()
	if c != nil {
		c.Logout(ctx)
	}
	a.chatDisconnect()
	return a.chatStatus(), nil
}

var chatEventTypes = map[string]bool{
	"list_rooms": true, "list_users": true, "create_room": true, "join_specific_room": true, "leave_room": true,
	"history": true, "send_message": true, "edit_message": true, "delete_message": true, "typing": true,
	"mark_read": true, "block": true, "ping": true,
}

func (a *App) chatSend(_ context.Context, in struct {
	Type string         `json:"type"`
	Data map[string]any `json:"data"`
}) (any, error) {
	if !chatEventTypes[in.Type] {
		return nil, bridge.Errf("Niedozwolone zdarzenie czatu.")
	}
	a.chat.mu.Lock()
	c := a.chat.client
	a.chat.mu.Unlock()
	if c == nil {
		return nil, bridge.Errf("Nie połączono z czatem.")
	}
	return c.Send(in.Type, in.Data)
}

func (a *App) chatUpload(ctx context.Context, _ empty) (any, error) {
	a.chat.mu.Lock()
	c := a.chat.client
	a.chat.mu.Unlock()
	if c == nil {
		return nil, bridge.Errf("Nie połączono z czatem.")
	}
	p, ok, err := a.dlg.OpenFile(a.hwnd(), "Załącz plik (maks. 10 MB)", "Obrazy, tekst, PDF, ZIP", "*.png;*.jpg;*.jpeg;*.gif;*.webp;*.txt;*.pdf;*.zip")
	if err != nil || !ok {
		return nil, err
	}
	return c.Upload(ctx, p)
}

func (a *App) chatFileDir() string { return filepath.Join(a.S.L.CacheDir, "chat_files") }

func safeChatName(n string) bool {
	return n != "" && len(n) <= 64 && !strings.ContainsAny(n, `/\:`) && !strings.HasPrefix(n, ".")
}

// chatFetch downloads an attachment into the cache; returns its media URL.
func (a *App) chatFetch(ctx context.Context, in struct {
	Name string `json:"name"`
	Open bool   `json:"open"`
}) (any, error) {
	if !safeChatName(in.Name) {
		return nil, bridge.Errf("Nieprawidłowy plik.")
	}
	a.chat.mu.Lock()
	c := a.chat.client
	a.chat.mu.Unlock()
	if c == nil {
		return nil, bridge.Errf("Nie połączono z czatem.")
	}
	dst := filepath.Join(a.chatFileDir(), in.Name)
	if !fileExists(dst) {
		if err := c.Download(ctx, in.Name, dst); err != nil {
			_ = os.Remove(dst)
			return nil, err
		}
	}
	if in.Open {
		return true, a.dlg.ShellOpen(filepath.Dir(dst))
	}
	return "/media/chatfile/" + in.Name, nil
}

// ChatFile implements webui.Media (cached attachments only).
func (a *App) ChatFile(name string) string {
	if !safeChatName(name) {
		return ""
	}
	p := filepath.Join(a.chatFileDir(), name)
	if !fileExists(p) {
		return ""
	}
	return p
}

func (a *App) chatServerSave(_ context.Context, in struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	URL     string `json:"url"`
	Default bool   `json:"default"`
}) (any, error) {
	if _, err := chatclient.New(in.URL); err != nil {
		return nil, err
	}
	name := strings.TrimSpace(in.Name)
	if name == "" {
		return nil, bridge.Errf("Podaj nazwę serwera.")
	}
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		list := l.Arr("chat_servers")
		var target *ojson.Object
		for _, s := range list {
			if o, ok := s.(*ojson.Object); ok {
				if o.Str("id") == in.ID && in.ID != "" {
					target = o
				} else if strings.EqualFold(o.Str("name"), name) {
					return bridge.Errf("Serwer o tej nazwie już istnieje.")
				}
			}
		}
		if target == nil {
			target = ojson.NewObject()
			target.Set("id", store.NewID())
			target.Set("credentials", ojson.NewObject())
			target.Set("remember_credentials", false)
			target.Set("auto_login_to_server", false)
			list = append(list, target)
		}
		target.Set("name", name)
		target.Set("url", strings.TrimRight(strings.TrimSpace(in.URL), "/"))
		if in.Default {
			for _, s := range list {
				if o, ok := s.(*ojson.Object); ok {
					o.Set("is_default", o == target)
				}
			}
		} else {
			target.SetDefault("is_default", false)
		}
		l.Set("chat_servers", list)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return a.chatStatus(), nil
}

func (a *App) chatServerDelete(_ context.Context, in struct {
	ID string `json:"id"`
}) (any, error) {
	err := a.S.UpdateLocal(func(l *ojson.Object) error {
		var keep []any
		for _, s := range l.Arr("chat_servers") {
			if o, ok := s.(*ojson.Object); ok && o.Str("id") == in.ID {
				continue
			}
			keep = append(keep, s)
		}
		if len(keep) == 0 {
			return errors.New("musi zostać co najmniej jeden serwer")
		}
		l.Set("chat_servers", keep)
		return nil
	})
	if err != nil {
		return nil, bridge.Errf("%v", err)
	}
	return a.chatStatus(), nil
}
