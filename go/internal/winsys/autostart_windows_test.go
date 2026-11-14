//go:build windows

package winsys

import (
	"testing"

	"golang.org/x/sys/windows/registry"
)

// Uses a scratch key under HKCU, never the real Run key.
func TestAutostartRoundTrip(t *testing.T) {
	old := RunKey
	RunKey = `Software\GameLauncherGoTest\Run`
	defer func() {
		RunKey = old
		_ = registry.DeleteKey(registry.CURRENT_USER, `Software\GameLauncherGoTest\Run`)
		_ = registry.DeleteKey(registry.CURRENT_USER, `Software\GameLauncherGoTest`)
	}()
	exe := `C:\Gry z spacja\GameLauncher.exe`
	if err := SetAutostart(true, exe); err != nil {
		t.Fatal(err)
	}
	cmd, ours := Autostart(exe)
	if !ours || cmd[0] != '"' {
		t.Fatal(cmd)
	}
	if _, ours := Autostart(`D:\inny\GameLauncher.exe`); ours {
		t.Fatal("other exe reported as ours")
	}
	if err := SetAutostart(false, exe); err != nil {
		t.Fatal(err)
	}
	if cmd, _ := Autostart(exe); cmd != "" {
		t.Fatal("not removed")
	}
	if err := SetAutostart(false, exe); err != nil {
		t.Fatal("removing twice:", err)
	}
}
