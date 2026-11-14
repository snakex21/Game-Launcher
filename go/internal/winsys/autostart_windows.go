//go:build windows

package winsys

import (
	"errors"
	"strings"

	"golang.org/x/sys/windows/registry"
)

// RunKey is the HKCU Run key (tests point it at a scratch key).
var RunKey = `Software\Microsoft\Windows\CurrentVersion\Run`

// AutostartValue is the registry value name.
const AutostartValue = "GameLauncher"

// AutostartCommand is the QUOTED command line stored in HKCU\...\Run.
func AutostartCommand(exe string) string {
	return `"` + strings.ReplaceAll(exe, `"`, "") + `" -minimized`
}

// SetAutostart writes or removes the HKCU Run value.
func SetAutostart(enable bool, exe string) error {
	k, _, err := registry.CreateKey(registry.CURRENT_USER, RunKey, registry.SET_VALUE|registry.QUERY_VALUE)
	if err != nil {
		return err
	}
	defer k.Close()
	if !enable {
		if err := k.DeleteValue(AutostartValue); err != nil && !errors.Is(err, registry.ErrNotExist) {
			return err
		}
		return nil
	}
	return k.SetStringValue(AutostartValue, AutostartCommand(exe))
}

// Autostart reports the stored command ("" when off) and whether it starts this exe.
func Autostart(exe string) (cmd string, ours bool) {
	k, err := registry.OpenKey(registry.CURRENT_USER, RunKey, registry.QUERY_VALUE)
	if err != nil {
		return "", false
	}
	defer k.Close()
	v, _, err := k.GetStringValue(AutostartValue)
	if err != nil {
		return "", false
	}
	return v, strings.EqualFold(v, AutostartCommand(exe))
}
