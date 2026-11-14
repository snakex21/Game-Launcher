//go:build windows

package archive

import "golang.org/x/sys/windows"

var procGetOEMCP = windows.NewLazySystemDLL("kernel32.dll").NewProc("GetOEMCP")

func systemOEMPage() uint32 {
	if err := procGetOEMCP.Find(); err != nil {
		return 437
	}
	r, _, _ := procGetOEMCP.Call()
	return uint32(r)
}
