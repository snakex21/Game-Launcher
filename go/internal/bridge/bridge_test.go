package bridge

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"sync"
	"testing"
)

type result struct {
	id      int64
	ok      bool
	payload any
}

func collect() (Settler, func() []result) {
	var mu sync.Mutex
	var out []result
	return func(id int64, ok bool, p any) {
			mu.Lock()
			out = append(out, result{id, ok, p})
			mu.Unlock()
		}, func() []result {
			mu.Lock()
			defer mu.Unlock()
			return append([]result(nil), out...)
		}
}

func TestInvoke(t *testing.T) {
	d := New(context.Background(), "tok")
	d.Handle("echo", func(_ context.Context, p json.RawMessage) (any, error) {
		var v struct{ N int }
		if err := Decode(p, &v); err != nil {
			return nil, err
		}
		return v.N * 2, nil
	})
	d.Handle("fail", func(context.Context, json.RawMessage) (any, error) { return nil, errors.New("zły") })
	d.Handle("panic", func(context.Context, json.RawMessage) (any, error) { panic("x") })
	settle, got := collect()

	if err := d.Invoke("bad", 1, "echo", `{"N":2}`, settle); err == nil {
		t.Fatal("bad token accepted")
	}
	if err := d.Invoke("tok", 1.5, "echo", `{}`, settle); err == nil {
		t.Fatal("fractional id accepted")
	}
	for i, c := range []string{"echo", "fail", "panic", "nope"} {
		payload := `{"N":21}`
		if c == "panic" {
			payload = "not json"
		}
		_ = d.Invoke("tok", float64(i+1), c, payload, settle)
	}
	d.Wait()
	res := got()
	byID := map[int64]result{}
	for _, r := range res {
		byID[r.id] = r
	}
	if r := byID[1]; !r.ok || r.payload != 42 {
		t.Fatalf("echo: %+v", r)
	}
	if r := byID[2]; r.ok || r.payload.(*UserError).Message != "zły" {
		t.Fatalf("fail: %+v", r)
	}
	if r := byID[3]; r.ok || !strings.Contains(r.payload.(*UserError).Message, "Nieprawidłowe") {
		t.Fatalf("invalid json: %+v", r)
	}
	if r := byID[4]; r.ok {
		t.Fatalf("unknown channel: %+v", r)
	}
}

func TestPanicIsRecovered(t *testing.T) {
	d := New(context.Background(), "t")
	d.Handle("p", func(context.Context, json.RawMessage) (any, error) { panic("boom") })
	settle, got := collect()
	_ = d.Invoke("t", 7, "p", "null", settle)
	d.Wait()
	if r := got(); len(r) != 1 || r[0].ok {
		t.Fatal(r)
	}
}

func TestScripts(t *testing.T) {
	s := InitScript("http://127.0.0.1:1", `t"x`, []byte(`{"games":[]}`))
	if !strings.Contains(s, `"t\"x"`) || !strings.Contains(s, `{"games":[]}`) || strings.Contains(s, "__GL_") {
		t.Fatal("init script substitution")
	}
	if e := EmitScript("game:started", map[string]string{"name": "</script>"}); !strings.Contains(e, `"game:started"`) {
		t.Fatal(e)
	}
}
