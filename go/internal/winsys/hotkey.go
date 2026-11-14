// Package winsys holds the Windows integrations: autostart (HKCU Run),
// tray icon with menu and balloon/toast notifications, global hotkeys
// (RegisterHotKey) and Discord Rich Presence (local IPC pipe).
package winsys

import (
	"fmt"
	"strings"
)

// Modifier flags for RegisterHotKey.
const (
	ModAlt      = 0x0001
	ModControl  = 0x0002
	ModShift    = 0x0004
	ModWin      = 0x0008
	ModNoRepeat = 0x4000
)

// Hotkey is a parsed key combination.
type Hotkey struct {
	Mods uint32
	VK   uint32
}

var vkNames = map[string]uint32{
	"space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "backspace": 0x08,
	"left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
	"insert": 0x2D, "ins": 0x2D, "delete": 0x2E, "del": 0x2E, "home": 0x24, "end": 0x23,
	"page_up": 0x21, "pageup": 0x21, "pgup": 0x21, "page_down": 0x22, "pagedown": 0x22, "pgdn": 0x22,
	"media_play_pause": 0xB3, "media_next": 0xB0, "media_previous": 0xB1, "media_stop": 0xB2,
	"volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD, "pause": 0x13,
}

// ParseHotkey reads both the pynput format stored by the Python launcher
// ("<ctrl>+<insert>", "<alt>+s") and "Ctrl+Alt+P".
func ParseHotkey(s string) (Hotkey, error) {
	var hk Hotkey
	parts := strings.Split(strings.ToLower(strings.TrimSpace(s)), "+")
	for _, p := range parts {
		p = strings.Trim(strings.TrimSpace(p), "<>")
		switch p {
		case "":
			continue
		case "ctrl", "control", "ctrl_l", "ctrl_r":
			hk.Mods |= ModControl
		case "alt", "alt_l", "alt_r", "alt_gr":
			hk.Mods |= ModAlt
		case "shift", "shift_l", "shift_r":
			hk.Mods |= ModShift
		case "win", "cmd", "super":
			hk.Mods |= ModWin
		default:
			if hk.VK != 0 {
				return hk, fmt.Errorf("skrót %q ma więcej niż jeden klawisz", s)
			}
			switch {
			case len(p) == 1 && (p[0] >= 'a' && p[0] <= 'z'):
				hk.VK = uint32(p[0] - 'a' + 'A')
			case len(p) == 1 && (p[0] >= '0' && p[0] <= '9'):
				hk.VK = uint32(p[0])
			case len(p) >= 2 && p[0] == 'f':
				var n int
				if _, err := fmt.Sscanf(p[1:], "%d", &n); err == nil && n >= 1 && n <= 24 {
					hk.VK = uint32(0x70 + n - 1)
				}
			default:
				hk.VK = vkNames[p]
			}
			if hk.VK == 0 {
				return hk, fmt.Errorf("nieznany klawisz %q w skrócie %q", p, s)
			}
		}
	}
	if hk.VK == 0 {
		return hk, fmt.Errorf("skrót %q nie ma klawisza", s)
	}
	if hk.Mods == 0 && (hk.VK < 0xAD || hk.VK > 0xB3) {
		return hk, fmt.Errorf("skrót %q musi mieć Ctrl, Alt, Shift albo Win", s)
	}
	return hk, nil
}
