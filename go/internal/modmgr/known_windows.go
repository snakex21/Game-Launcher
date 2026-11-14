//go:build windows

package modmgr

import (
	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

// SystemFolders returns this user's known folders (never used in tests).
func SystemFolders() map[gamedef.RootKind]string {
	out := map[gamedef.RootKind]string{}
	for kind, id := range map[gamedef.RootKind]*windows.KNOWNFOLDERID{
		gamedef.RootDocuments:    windows.FOLDERID_Documents,
		gamedef.RootLocalAppData: windows.FOLDERID_LocalAppData,
		gamedef.RootAppData:      windows.FOLDERID_RoamingAppData,
		gamedef.RootLocalLow:     windows.FOLDERID_LocalAppDataLow,
		gamedef.RootUserProfile:  windows.FOLDERID_Profile,
		gamedef.RootSavedGames:   windows.FOLDERID_SavedGames,
	} {
		if p, err := windows.KnownFolderPath(id, 0); err == nil && p != "" {
			out[kind] = p
		}
	}
	if p := SteamRoot(); p != "" {
		out[gamedef.RootSteam] = p
	}
	return out
}

// SteamRoot reads the Steam folder from the registry ("" if not installed).
func SteamRoot() string {
	if k, err := registry.OpenKey(registry.CURRENT_USER, `Software\Valve\Steam`, registry.QUERY_VALUE); err == nil {
		defer k.Close()
		if v, _, err := k.GetStringValue("SteamPath"); err == nil && v != "" {
			return v
		}
	}
	if k, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Valve\Steam`, registry.QUERY_VALUE); err == nil {
		defer k.Close()
		if v, _, err := k.GetStringValue("InstallPath"); err == nil {
			return v
		}
	}
	return ""
}
