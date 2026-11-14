//go:build windows

package winsys

import (
	"errors"
	"runtime"
	"sync"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	user32               = windows.NewLazySystemDLL("user32.dll")
	shell32              = windows.NewLazySystemDLL("shell32.dll")
	kernel32             = windows.NewLazySystemDLL("kernel32.dll")
	pRegisterClassExW    = user32.NewProc("RegisterClassExW")
	pCreateWindowExW     = user32.NewProc("CreateWindowExW")
	pDefWindowProcW      = user32.NewProc("DefWindowProcW")
	pGetMessageW         = user32.NewProc("GetMessageW")
	pTranslateMessage    = user32.NewProc("TranslateMessage")
	pDispatchMessageW    = user32.NewProc("DispatchMessageW")
	pPostMessageW        = user32.NewProc("PostMessageW")
	pDestroyWindow       = user32.NewProc("DestroyWindow")
	pPostQuitMessage     = user32.NewProc("PostQuitMessage")
	pCreatePopupMenu     = user32.NewProc("CreatePopupMenu")
	pAppendMenuW         = user32.NewProc("AppendMenuW")
	pTrackPopupMenu      = user32.NewProc("TrackPopupMenu")
	pDestroyMenu         = user32.NewProc("DestroyMenu")
	pGetCursorPos        = user32.NewProc("GetCursorPos")
	pSetForegroundWindow = user32.NewProc("SetForegroundWindow")
	pLoadImageW          = user32.NewProc("LoadImageW")
	pRegisterHotKey      = user32.NewProc("RegisterHotKey")
	pUnregisterHotKey    = user32.NewProc("UnregisterHotKey")
	pShowWindow          = user32.NewProc("ShowWindow")
	pIsWindowVisible     = user32.NewProc("IsWindowVisible")
	pShellNotifyIconW    = shell32.NewProc("Shell_NotifyIconW")
	pGetModuleHandleW    = kernel32.NewProc("GetModuleHandleW")
)

const (
	wmDestroy      = 0x0002
	wmCommand      = 0x0111
	wmHotkey       = 0x0312
	wmApp          = 0x8000
	wmTray         = wmApp + 1
	wmApplyHotkeys = wmApp + 2
	wmNotify       = wmApp + 3
	wmQuit         = wmApp + 4
	wmLButtonUp    = 0x0202
	wmRButtonUp    = 0x0205
	ninBalloonClk  = 0x0405

	nimAdd     = 0
	nimModify  = 1
	nimDelete  = 2
	nifMessage = 0x1
	nifIcon    = 0x2
	nifTip     = 0x4
	nifInfo    = 0x10
	niifInfo   = 0x1

	mfString    = 0x0
	mfSeparator = 0x800
	tpmRetCmd   = 0x0100
	tpmRightBtn = 0x0002

	// SW constants for ShowMain.
	swHide    = 0
	swRestore = 9
)

type wndClassEx struct {
	Size, Style                        uint32
	WndProc                            uintptr
	ClsExtra, WndExtra                 int32
	Instance, Icon, Cursor, Background uintptr
	MenuName, ClassName                *uint16
	IconSm                             uintptr
}

type point struct{ X, Y int32 }

type msg struct {
	Hwnd    uintptr
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      point
}

type notifyIconData struct {
	Size             uint32
	Hwnd             uintptr
	ID               uint32
	Flags            uint32
	CallbackMessage  uint32
	Icon             uintptr
	Tip              [128]uint16
	State, StateMask uint32
	Info             [256]uint16
	Version          uint32
	InfoTitle        [64]uint16
	InfoFlags        uint32
	GUID             windows.GUID
	BalloonIcon      uintptr
}

// MenuItem of the tray menu ("" label = separator).
type MenuItem struct {
	ID    int
	Label string
}

// Tray is the notification-area icon plus the hidden window that receives
// tray clicks, menu commands and WM_HOTKEY.
type Tray struct {
	OnMenu   func(id int)
	OnClick  func()
	OnHotkey func(id int)

	mu      sync.Mutex
	hwnd    uintptr
	items   []MenuItem
	hotkeys map[int]Hotkey
	want    map[int]Hotkey
	failed  map[int]bool
	note    [2]string
	nid     notifyIconData
	ready   chan error
}

var (
	trayMu   sync.Mutex
	trayByHW = map[uintptr]*Tray{}
	wndProc  = syscall.NewCallback(trayWndProc)
)

func utf16Fill(dst []uint16, s string) {
	u, _ := windows.UTF16FromString(s)
	if len(u) > len(dst) {
		u = u[:len(dst)]
		u[len(u)-1] = 0
	}
	copy(dst, u)
}

// StartTray creates the icon (iconPath: .ico file) on its own OS thread.
func StartTray(tooltip, iconPath string, items []MenuItem) (*Tray, error) {
	t := &Tray{items: items, hotkeys: map[int]Hotkey{}, failed: map[int]bool{}, ready: make(chan error, 1)}
	go t.loop(tooltip, iconPath)
	if err := <-t.ready; err != nil {
		return nil, err
	}
	return t, nil
}

func (t *Tray) loop(tooltip, iconPath string) {
	runtime.LockOSThread()
	inst, _, _ := pGetModuleHandleW.Call(0)
	cls, _ := windows.UTF16PtrFromString("GameLauncherTrayWindow")
	wc := wndClassEx{WndProc: wndProc, Instance: inst, ClassName: cls}
	wc.Size = uint32(unsafe.Sizeof(wc))
	pRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc))) // may already exist: fine
	title, _ := windows.UTF16PtrFromString("Game Launcher tray")
	hwnd, _, err := pCreateWindowExW.Call(0, uintptr(unsafe.Pointer(cls)), uintptr(unsafe.Pointer(title)), 0, 0, 0, 0, 0, 0, 0, inst, 0)
	if hwnd == 0 {
		t.ready <- err
		return
	}
	trayMu.Lock()
	trayByHW[hwnd] = t
	trayMu.Unlock()
	t.mu.Lock()
	t.hwnd = hwnd
	t.mu.Unlock()

	var icon uintptr
	if p, err := windows.UTF16PtrFromString(iconPath); err == nil {
		icon, _, _ = pLoadImageW.Call(0, uintptr(unsafe.Pointer(p)), 1 /*IMAGE_ICON*/, 16, 16, 0x10 /*LR_LOADFROMFILE*/)
	}
	t.nid = notifyIconData{Hwnd: hwnd, ID: 1, Flags: nifMessage | nifIcon | nifTip, CallbackMessage: wmTray, Icon: icon}
	t.nid.Size = uint32(unsafe.Sizeof(t.nid))
	utf16Fill(t.nid.Tip[:], tooltip)
	if r, _, _ := pShellNotifyIconW.Call(nimAdd, uintptr(unsafe.Pointer(&t.nid))); r == 0 {
		pDestroyWindow.Call(hwnd)
		t.ready <- errors.New("nie można dodać ikony w zasobniku")
		return
	}
	t.ready <- nil
	var m msg
	for {
		r, _, _ := pGetMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		if int32(r) <= 0 {
			break
		}
		pTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
		pDispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
	}
}

func trayWndProc(hwnd uintptr, m uint32, wp, lp uintptr) uintptr {
	trayMu.Lock()
	t := trayByHW[hwnd]
	trayMu.Unlock()
	if t == nil {
		r, _, _ := pDefWindowProcW.Call(hwnd, uintptr(m), wp, lp)
		return r
	}
	switch m {
	case wmTray:
		switch uint32(lp & 0xffff) {
		case wmLButtonUp, ninBalloonClk:
			if t.OnClick != nil {
				go t.OnClick()
			}
		case wmRButtonUp:
			t.showMenu()
		}
		return 0
	case wmCommand:
		if t.OnMenu != nil {
			id := int(wp & 0xffff)
			go t.OnMenu(id)
		}
		return 0
	case wmHotkey:
		if t.OnHotkey != nil {
			id := int(wp)
			go t.OnHotkey(id)
		}
		return 0
	case wmApplyHotkeys:
		t.applyHotkeys()
		return 0
	case wmNotify:
		t.mu.Lock()
		title, text := t.note[0], t.note[1]
		t.mu.Unlock()
		n := t.nid
		n.Flags = nifInfo
		n.InfoFlags = niifInfo
		utf16Fill(n.InfoTitle[:], title)
		utf16Fill(n.Info[:], text)
		pShellNotifyIconW.Call(nimModify, uintptr(unsafe.Pointer(&n)))
		return 0
	case wmQuit:
		pShellNotifyIconW.Call(nimDelete, uintptr(unsafe.Pointer(&t.nid)))
		t.mu.Lock()
		for id := range t.hotkeys {
			pUnregisterHotKey.Call(hwnd, uintptr(id))
		}
		t.mu.Unlock()
		pDestroyWindow.Call(hwnd)
		return 0
	case wmDestroy:
		trayMu.Lock()
		delete(trayByHW, hwnd)
		trayMu.Unlock()
		pPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := pDefWindowProcW.Call(hwnd, uintptr(m), wp, lp)
	return r
}

func (t *Tray) showMenu() {
	menu, _, _ := pCreatePopupMenu.Call()
	if menu == 0 {
		return
	}
	defer pDestroyMenu.Call(menu)
	t.mu.Lock()
	items := append([]MenuItem(nil), t.items...)
	t.mu.Unlock()
	for _, it := range items {
		if it.Label == "" {
			pAppendMenuW.Call(menu, mfSeparator, 0, 0)
			continue
		}
		p, _ := windows.UTF16PtrFromString(it.Label)
		pAppendMenuW.Call(menu, mfString, uintptr(it.ID), uintptr(unsafe.Pointer(p)))
	}
	var pt point
	pGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	pSetForegroundWindow.Call(t.hwnd)
	pTrackPopupMenu.Call(menu, tpmRightBtn, uintptr(pt.X), uintptr(pt.Y), 0, t.hwnd, 0)
}

func (t *Tray) post(m uint32) {
	t.mu.Lock()
	h := t.hwnd
	t.mu.Unlock()
	if h != 0 {
		pPostMessageW.Call(h, uintptr(m), 0, 0)
	}
}

// Notify shows a balloon notification (Windows 10/11 shows it as a toast).
func (t *Tray) Notify(title, text string) {
	t.mu.Lock()
	t.note = [2]string{title, text}
	t.mu.Unlock()
	t.post(wmNotify)
}

// SetHotkeys replaces the global hotkeys (id -> key); registration happens
// on the tray thread. Failed ids (taken by another program) are reported
// by FailedHotkeys after a moment.
func (t *Tray) SetHotkeys(keys map[int]Hotkey) {
	t.mu.Lock()
	t.want = keys
	t.mu.Unlock()
	t.post(wmApplyHotkeys)
}

func (t *Tray) applyHotkeys() {
	t.mu.Lock()
	defer t.mu.Unlock()
	for id := range t.hotkeys {
		pUnregisterHotKey.Call(t.hwnd, uintptr(id))
	}
	t.hotkeys = map[int]Hotkey{}
	t.failed = map[int]bool{}
	for id, hk := range t.want {
		r, _, _ := pRegisterHotKey.Call(t.hwnd, uintptr(id), uintptr(hk.Mods|ModNoRepeat), uintptr(hk.VK))
		if r == 0 {
			t.failed[id] = true
			continue
		}
		t.hotkeys[id] = hk
	}
}

// FailedHotkeys lists ids that could not be registered.
func (t *Tray) FailedHotkeys() []int {
	t.mu.Lock()
	defer t.mu.Unlock()
	var out []int
	for id := range t.failed {
		out = append(out, id)
	}
	return out
}

// Close removes the icon and unregisters hotkeys.
func (t *Tray) Close() { t.post(wmQuit) }

// ShowMain shows/restores (or hides) a top-level window.
func ShowMain(hwnd uintptr, show bool) {
	if show {
		pShowWindow.Call(hwnd, swRestore)
		pSetForegroundWindow.Call(hwnd)
		return
	}
	pShowWindow.Call(hwnd, swHide)
}

// Visible reports whether a window is visible.
func Visible(hwnd uintptr) bool {
	r, _, _ := pIsWindowVisible.Call(hwnd)
	return r != 0
}
