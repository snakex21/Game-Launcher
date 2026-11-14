//go:build windows

package main

import (
	"os"
	"path/filepath"
	"syscall"
	"unsafe"
)

var (
	user32          = syscall.NewLazyDLL("user32.dll")
	procLoadImageW  = user32.NewProc("LoadImageW")
	procSendMessage = user32.NewProc("SendMessageW")
)

// setWindowIcon sets the title-bar/taskbar icon from the embedded .ico.
func setWindowIcon(hwnd unsafe.Pointer, ico []byte) {
	if hwnd == nil || len(ico) == 0 {
		return
	}
	path := filepath.Join(os.TempDir(), "game-launcher-go-icon.ico")
	if err := os.WriteFile(path, ico, 0o644); err != nil {
		return
	}
	p, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return
	}
	const imageIcon, lrLoadFromFile, wmSetIcon = 1, 0x10, 0x0080
	for _, size := range []struct{ kind, px uintptr }{{0, 16}, {1, 32}} {
		h, _, _ := procLoadImageW.Call(0, uintptr(unsafe.Pointer(p)), imageIcon, size.px, size.px, lrLoadFromFile)
		if h != 0 {
			_, _, _ = procSendMessage.Call(uintptr(hwnd), wmSetIcon, size.kind, h)
		}
	}
}
