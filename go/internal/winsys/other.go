//go:build !windows

package winsys

import "errors"

var errNA = errors.New("dostępne tylko w Windows")

// MenuItem of the tray menu.
type MenuItem struct {
	ID    int
	Label string
}

// Tray is unavailable outside Windows.
type Tray struct {
	OnMenu   func(int)
	OnClick  func()
	OnHotkey func(int)
}

func StartTray(string, string, []MenuItem) (*Tray, error) { return nil, errNA }
func (*Tray) Notify(string, string)                       {}
func (*Tray) SetHotkeys(map[int]Hotkey)                   {}
func (*Tray) FailedHotkeys() []int                        { return nil }
func (*Tray) Close()                                      {}
func ShowMain(uintptr, bool)                              {}
func Visible(uintptr) bool                                { return true }
func AutostartCommand(exe string) string                  { return `"` + exe + `" -minimized` }
func SetAutostart(bool, string) error                     { return errNA }
func Autostart(string) (string, bool)                     { return "", false }
