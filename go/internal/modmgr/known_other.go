//go:build !windows

package modmgr

import "github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"

// SystemFolders is empty outside Windows.
func SystemFolders() map[gamedef.RootKind]string { return map[gamedef.RootKind]string{} }

// SteamRoot is unknown outside Windows.
func SteamRoot() string { return "" }
