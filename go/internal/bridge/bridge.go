// Package bridge connects the embedded UI to Go: one webview binding
// (__gl_invoke) carries {token, id, channel, payload}; handlers run off the
// UI thread and settle a JS promise. Go-to-UI events go through __glEmit.
//
// The per-session token is injected only into our own origin (see shim.js),
// so a page that somehow got into the window cannot call Go.
package bridge

import (
	"context"
	"crypto/subtle"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"runtime/debug"
	"strings"
	"sync"
)

//go:embed shim.js
var shimJS string

// MaxPayload bounds one call's JSON payload.
const MaxPayload = 8 << 20

// Handler serves one channel. payload is the raw JSON argument (may be "null").
type Handler func(ctx context.Context, payload json.RawMessage) (any, error)

// UserError is shown to the user as-is (Polish text).
type UserError struct {
	Title   string `json:"title,omitempty"`
	Message string `json:"message"`
}

func (e *UserError) Error() string { return e.Message }

// Errf builds a UserError.
func Errf(format string, a ...any) error { return &UserError{Message: fmt.Sprintf(format, a...)} }

// Settler delivers a result to the UI.
type Settler func(id int64, ok bool, payload any)

// Dispatcher owns the channel registry.
type Dispatcher struct {
	token    string
	mu       sync.RWMutex
	handlers map[string]Handler
	ctx      context.Context
	wg       sync.WaitGroup
}

// New creates a dispatcher.
func New(ctx context.Context, token string) *Dispatcher {
	return &Dispatcher{token: token, handlers: map[string]Handler{}, ctx: ctx}
}

// Handle registers a channel.
func (d *Dispatcher) Handle(channel string, h Handler) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if _, dup := d.handlers[channel]; dup {
		panic("duplicate bridge channel " + channel)
	}
	d.handlers[channel] = h
}

// Has reports whether a channel exists.
func (d *Dispatcher) Has(channel string) bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	_, ok := d.handlers[channel]
	return ok
}

// Invoke validates and runs one call asynchronously.
func (d *Dispatcher) Invoke(token string, id float64, channel, payload string, settle Settler) error {
	if len(token) != len(d.token) || subtle.ConstantTimeCompare([]byte(token), []byte(d.token)) != 1 {
		log.Printf("[bridge][security] rejected call to %q: bad token", channel)
		return errors.New("forbidden")
	}
	if id != math.Trunc(id) || id < 0 || id > 1<<53 {
		return errors.New("invalid call id")
	}
	cid := int64(id)
	d.mu.RLock()
	h, ok := d.handlers[channel]
	d.mu.RUnlock()
	if !ok {
		settle(cid, false, &UserError{Message: "Nieznany kanał: " + channel})
		return nil
	}
	if len(payload) > MaxPayload {
		settle(cid, false, &UserError{Message: "Żądanie jest za duże."})
		return nil
	}
	if strings.TrimSpace(payload) == "" {
		payload = "null"
	}
	if !json.Valid([]byte(payload)) {
		settle(cid, false, &UserError{Message: "Nieprawidłowe dane żądania."})
		return nil
	}
	d.wg.Add(1)
	go func() {
		defer d.wg.Done()
		defer func() {
			if r := recover(); r != nil {
				log.Printf("[bridge] panic in %s: %v\n%s", channel, r, debug.Stack())
				settle(cid, false, &UserError{Message: "Błąd wewnętrzny (szczegóły w logu)."})
			}
		}()
		res, err := h(d.ctx, json.RawMessage(payload))
		if err != nil {
			var ue *UserError
			if errors.As(err, &ue) {
				settle(cid, false, ue)
				return
			}
			settle(cid, false, &UserError{Message: err.Error()})
			return
		}
		settle(cid, true, res)
	}()
	return nil
}

// Wait blocks until in-flight calls finish.
func (d *Dispatcher) Wait() { d.wg.Wait() }

func jsString(s string) string {
	b, _ := json.Marshal(s)
	return string(b)
}

// InitScript returns the shim with origin, token and boot data inlined.
// boot is pre-serialised JSON (the cached library for the first paint).
func InitScript(origin, token string, boot []byte) string {
	if len(boot) == 0 {
		boot = []byte("null")
	}
	r := strings.NewReplacer("__GL_ORIGIN__", jsString(origin), "__GL_TOKEN__", jsString(token), "__GL_BOOT__", string(boot))
	return r.Replace(shimJS)
}

// SettleScript renders the JS that resolves a pending call.
func SettleScript(id int64, ok bool, payload any) string {
	data, err := json.Marshal(payload)
	if err != nil {
		ok, data = false, []byte(`{"message":"Nie można przesłać wyniku."}`)
	}
	return fmt.Sprintf("window.__glSettle&&window.__glSettle(%d,%t,%s);", id, ok, data)
}

// EmitScript renders the JS that delivers an event.
func EmitScript(event string, payload any) string {
	data, err := json.Marshal(payload)
	if err != nil {
		data = []byte("null")
	}
	return fmt.Sprintf("window.__glEmit&&window.__glEmit(%s,%s);", jsString(event), data)
}

// Decode unmarshals a payload into v with a Polish error.
func Decode(payload json.RawMessage, v any) error {
	if err := json.Unmarshal(payload, v); err != nil {
		return &UserError{Message: "Nieprawidłowe dane: " + err.Error()}
	}
	return nil
}
