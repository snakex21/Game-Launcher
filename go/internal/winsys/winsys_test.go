package winsys

import (
	"encoding/json"
	"io"
	"net"
	"strings"
	"testing"
	"time"
)

func TestParseHotkey(t *testing.T) {
	cases := map[string]Hotkey{
		"<ctrl>+<insert>":    {ModControl, 0x2D},
		"<ctrl>+<page_down>": {ModControl, 0x22},
		"<alt>+s":            {ModAlt, 'S'},
		"Ctrl+Alt+P":         {ModControl | ModAlt, 'P'},
		"shift+f12":          {ModShift, 0x7B},
		"<alt>+<space>":      {ModAlt, 0x20},
		"media_play_pause":   {0, 0xB3},
	}
	for in, want := range cases {
		got, err := ParseHotkey(in)
		if err != nil || got != want {
			t.Errorf("ParseHotkey(%q) = %+v, %v; want %+v", in, got, err, want)
		}
	}
	for _, bad := range []string{"", "ctrl", "a", "ctrl+a+b", "ctrl+nieznany"} {
		if _, err := ParseHotkey(bad); err == nil {
			t.Errorf("%q accepted", bad)
		}
	}
}

// The Run value must quote the path (spaces in the launcher folder).
func TestAutostartCommandQuoted(t *testing.T) {
	cmd := AutostartCommand(`J:\Projekty\Game Launcher\GameLauncher.exe`)
	if cmd != `"J:\Projekty\Game Launcher\GameLauncher.exe" -minimized` {
		t.Fatal(cmd)
	}
}

// Discord IPC: handshake, then SET_ACTIVITY frames (fake Discord on a pipe).
func TestDiscordFrames(t *testing.T) {
	a, b := net.Pipe()
	got := make(chan map[string]any, 4)
	go func() {
		for {
			op, data, err := readFrame(b)
			if err != nil {
				return
			}
			var m map[string]any
			json.Unmarshal(data, &m)
			m["_op"] = float64(op)
			got <- m
			writeFrame(b, 1, map[string]any{"evt": "READY"})
		}
	}()
	d := &Discord{Dial: func() (io.ReadWriteCloser, error) { return a, nil }}
	if err := d.Set(&Activity{Details: "Gra: Gothic", State: "Profil: Default", Start: time.Unix(100, 0)}); err != nil {
		t.Fatal(err)
	}
	hs := <-got
	if hs["_op"] != 0.0 || hs["client_id"] != DiscordClientID {
		t.Fatalf("handshake %v", hs)
	}
	act := <-got
	b2, _ := json.Marshal(act)
	if act["cmd"] != "SET_ACTIVITY" || !strings.Contains(string(b2), "Gothic") || !strings.Contains(string(b2), `"start":100`) {
		t.Fatalf("activity %s", b2)
	}
	d.Close()
	if (&Discord{Dial: func() (io.ReadWriteCloser, error) { return nil, io.EOF }}).Set(nil) == nil {
		t.Fatal("no error without Discord")
	}
}
