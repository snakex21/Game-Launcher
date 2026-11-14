//go:build windows

package winapi

import (
	"runtime"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	ole32                     = windows.NewLazySystemDLL("ole32.dll")
	procCoInitializeEx        = ole32.NewProc("CoInitializeEx")
	procCoUninitialize        = ole32.NewProc("CoUninitialize")
	procCoTaskMemFree         = ole32.NewProc("CoTaskMemFree")
	procSHBrowseForFolderW    = shell32.NewProc("SHBrowseForFolderW")
	procSHGetPathFromIDListEx = shell32.NewProc("SHGetPathFromIDListEx")
)

type browseInfo struct {
	hwndOwner      uintptr
	pidlRoot       uintptr
	pszDisplayName *uint16
	lpszTitle      *uint16
	ulFlags        uint32
	lpfn           uintptr
	lParam         uintptr
	iImage         int32
}

// PickFolder shows the folder picker. ok=false means cancelled.
func PickFolder(hwnd uintptr, title string) (string, bool, error) {
	// The new-style dialog needs COM (apartment-threaded) on this thread.
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	const coinitApartmentThreaded = 0x2
	r, _, _ := procCoInitializeEx.Call(0, coinitApartmentThreaded)
	if r == 0 || r == 1 { // S_OK / S_FALSE
		defer procCoUninitialize.Call()
	}
	display := make([]uint16, windows.MAX_PATH)
	const bifReturnOnlyFSDirs, bifNewDialogStyle, bifEditBox = 0x1, 0x40, 0x10
	bi := browseInfo{hwndOwner: hwnd, pszDisplayName: &display[0], lpszTitle: ptr(title), ulFlags: bifReturnOnlyFSDirs | bifNewDialogStyle | bifEditBox}
	pidl, _, _ := procSHBrowseForFolderW.Call(uintptr(unsafe.Pointer(&bi)))
	if pidl == 0 {
		return "", false, nil
	}
	defer procCoTaskMemFree.Call(pidl)
	buf := make([]uint16, 32768)
	ok, _, _ := procSHGetPathFromIDListEx.Call(pidl, uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)), 0)
	if ok == 0 {
		return "", false, nil
	}
	return windows.UTF16ToString(buf), true, nil
}
