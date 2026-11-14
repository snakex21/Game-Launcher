//go:build windows

// Package winapi wraps the native Windows dialogs and shell calls the
// launcher needs (file/folder pickers, message boxes, ShellExecute).
package winapi

import (
	"errors"
	"strings"
	"syscall"
	utf16pkg "unicode/utf16"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	comdlg32             = windows.NewLazySystemDLL("comdlg32.dll")
	user32               = windows.NewLazySystemDLL("user32.dll")
	shell32              = windows.NewLazySystemDLL("shell32.dll")
	procGetSaveFileNameW = comdlg32.NewProc("GetSaveFileNameW")
	procGetOpenFileNameW = comdlg32.NewProc("GetOpenFileNameW")
	procCommDlgError     = comdlg32.NewProc("CommDlgExtendedError")
	procMessageBoxW      = user32.NewProc("MessageBoxW")
	procShellExecuteW    = shell32.NewProc("ShellExecuteW")
)

type openFileName struct {
	lStructSize       uint32
	hwndOwner         uintptr
	hInstance         uintptr
	lpstrFilter       *uint16
	lpstrCustomFilter *uint16
	nMaxCustFilter    uint32
	nFilterIndex      uint32
	lpstrFile         *uint16
	nMaxFile          uint32
	lpstrFileTitle    *uint16
	nMaxFileTitle     uint32
	lpstrInitialDir   *uint16
	lpstrTitle        *uint16
	flags             uint32
	nFileOffset       uint16
	nFileExtension    uint16
	lpstrDefExt       *uint16
	lCustData         uintptr
	lpfnHook          uintptr
	lpTemplateName    *uint16
	pvReserved        uintptr
	dwReserved        uint32
	flagsEx           uint32
}

const (
	ofnOverwritePrompt = 0x00000002
	ofnHideReadOnly    = 0x00000004
	ofnNoChangeDir     = 0x00000008
	ofnPathMustExist   = 0x00000800
	ofnFileMustExist   = 0x00001000
	ofnExplorer        = 0x00080000
)

func filterString(name, ext string) []uint16 {
	pattern := "*." + ext
	if strings.Contains(ext, "*") {
		pattern = ext // e.g. "*.png;*.jpg"
	}
	if ext == "" || ext == "*" {
		pattern = "*.*"
	}
	// A double-NUL-terminated list of NUL-separated strings: it cannot go
	// through UTF16FromString, which rejects embedded NULs.
	s := name + " (" + pattern + ")\x00" + pattern + "\x00All files (*.*)\x00*.*\x00\x00"
	return utf16pkg.Encode([]rune(s))
}

func utf16(s string) []uint16 {
	r, err := windows.UTF16FromString(s)
	if err != nil {
		return []uint16{0}
	}
	return r
}

func ptr(s string) *uint16 {
	p, _ := windows.UTF16PtrFromString(s)
	return p
}

// SanitizeFileName strips path separators and characters Windows rejects.
func SanitizeFileName(name string) string {
	name = strings.ReplaceAll(name, "/", `\`)
	if i := strings.LastIndex(name, `\`); i >= 0 {
		name = name[i+1:]
	}
	name = strings.Map(func(r rune) rune {
		if r < 32 || strings.ContainsRune(`<>:"/\|?*`, r) {
			return '_'
		}
		return r
	}, name)
	if name == "." || name == ".." {
		return "file"
	}
	return name
}

func fileDialog(proc *windows.LazyProc, hwnd uintptr, title, defaultName, filterName, ext string, flags uint32) (string, bool, error) {
	buf := make([]uint16, 32768)
	copy(buf, utf16(SanitizeFileName(defaultName)))
	filter := filterString(filterName, ext)
	ofn := openFileName{
		hwndOwner:    hwnd,
		lpstrFilter:  &filter[0],
		nFilterIndex: 1,
		lpstrFile:    &buf[0],
		nMaxFile:     uint32(len(buf)),
		lpstrTitle:   ptr(title),
		flags:        flags | ofnExplorer | ofnNoChangeDir | ofnHideReadOnly,
	}
	if ext != "" && !strings.Contains(ext, "*") {
		ofn.lpstrDefExt = ptr(ext)
	}
	ofn.lStructSize = uint32(unsafe.Sizeof(ofn))
	r, _, _ := proc.Call(uintptr(unsafe.Pointer(&ofn)))
	if r == 0 {
		code, _, _ := procCommDlgError.Call()
		if code != 0 {
			return "", false, errors.New("file dialog failed")
		}
		return "", false, nil // cancelled
	}
	return windows.UTF16ToString(buf), true, nil
}

// SaveFile shows a native "Save as" dialog. ok=false means cancelled.
func SaveFile(hwnd uintptr, title, defaultName, filterName, ext string) (string, bool, error) {
	return fileDialog(procGetSaveFileNameW, hwnd, title, defaultName, filterName, ext, ofnOverwritePrompt|ofnPathMustExist)
}

// OpenFile shows a native "Open" dialog.
func OpenFile(hwnd uintptr, title, filterName, ext string) (string, bool, error) {
	return fileDialog(procGetOpenFileNameW, hwnd, title, "", filterName, ext, ofnFileMustExist|ofnPathMustExist)
}

const (
	MBOK           = 0x0
	MBYesNo        = 0x4
	MBIconWarning  = 0x30
	MBIconError    = 0x10
	MBDefButton2   = 0x100
	MBSetForegound = 0x10000
	IDYes          = 6
)

// MessageBox shows a native message box and returns the pressed button id.
func MessageBox(hwnd uintptr, title, text string, flags uint32) int {
	r, _, _ := procMessageBoxW.Call(hwnd, uintptr(unsafe.Pointer(ptr(text))), uintptr(unsafe.Pointer(ptr(title))), uintptr(flags))
	return int(r)
}

// ConfirmWarning shows a Yes/No warning (default No) and reports Yes.
func ConfirmWarning(hwnd uintptr, title, text string) bool {
	return MessageBox(hwnd, title, text, MBYesNo|MBIconWarning|MBDefButton2|MBSetForegound) == IDYes
}

// ShellOpen opens a file, folder or URL with its default handler.
func ShellOpen(target string) error {
	r, _, _ := procShellExecuteW.Call(0, uintptr(unsafe.Pointer(ptr("open"))), uintptr(unsafe.Pointer(ptr(target))), 0, 0, 1)
	if r <= 32 {
		return syscall.Errno(r)
	}
	return nil
}
