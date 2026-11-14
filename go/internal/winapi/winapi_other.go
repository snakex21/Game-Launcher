//go:build !windows

package winapi

import "errors"

var errUnsupported = errors.New("native dialogs are only available on Windows")

func SanitizeFileName(name string) string { return name }
func SaveFile(uintptr, string, string, string, string) (string, bool, error) {
	return "", false, errUnsupported
}
func OpenFile(uintptr, string, string, string) (string, bool, error) {
	return "", false, errUnsupported
}
func MessageBox(uintptr, string, string, uint32) int { return 0 }
func ConfirmWarning(uintptr, string, string) bool    { return false }
func ShellOpen(string) error                         { return errUnsupported }

func PickFolder(uintptr, string) (string, bool, error) { return "", false, errUnsupported }
