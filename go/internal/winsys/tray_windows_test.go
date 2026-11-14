//go:build windows

package winsys

import (
	"testing"
	"time"
)

// Integration test of the tray window: the icon is added and removed, a
// global hotkey that nobody uses is registered (and unregistered on Close),
// a hotkey taken twice is reported, and WM_HOTKEY / WM_COMMAND posted to
// our own hidden window reach the callbacks. No keys are pressed and no
// other window is touched (no balloon notification either).
func TestTrayHotkeysAndMenu(t *testing.T) {
	if testing.Short() {
		t.Skip("short")
	}
	tr, err := StartTray("Game Launcher – test", "", []MenuItem{{ID: 7, Label: "Pokaż"}})
	if err != nil {
		t.Skip("no notification area here:", err)
	}
	defer tr.Close()
	hot := make(chan int, 4)
	menu := make(chan int, 4)
	tr.OnHotkey = func(id int) { hot <- id }
	tr.OnMenu = func(id int) { menu <- id }

	hk, err := ParseHotkey("Ctrl+Alt+Shift+F12")
	if err != nil {
		t.Fatal(err)
	}
	tr.SetHotkeys(map[int]Hotkey{1: hk})
	time.Sleep(200 * time.Millisecond)
	if f := tr.FailedHotkeys(); len(f) != 0 {
		t.Skipf("Ctrl+Alt+Shift+F12 is taken by another program on this machine (%v)", f)
	}
	// a second registration of the same key in this process must fail
	tr2, err := StartTray("Game Launcher – test 2", "", nil)
	if err != nil {
		t.Fatal(err)
	}
	tr2.SetHotkeys(map[int]Hotkey{5: hk})
	time.Sleep(200 * time.Millisecond)
	if f := tr2.FailedHotkeys(); len(f) != 1 || f[0] != 5 {
		t.Fatalf("taken hotkey not reported: %v", f)
	}
	tr2.Close()

	tr.mu.Lock()
	h := tr.hwnd
	tr.mu.Unlock()
	pPostMessageW.Call(h, wmHotkey, 1, 0)
	pPostMessageW.Call(h, wmCommand, 7, 0)
	select {
	case id := <-hot:
		if id != 1 {
			t.Fatal(id)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("WM_HOTKEY not delivered")
	}
	select {
	case id := <-menu:
		if id != 7 {
			t.Fatal(id)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("menu command not delivered")
	}
}
