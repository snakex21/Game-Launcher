// Package modmgr is the reserved place for the mod manager (not built yet).
//
// Design: scratchpad mod_manager_design.md (game definitions in JSON, a mod
// store on the launcher drive, deployments with a write-ahead journal and
// a manifest so the game folder can always return to vanilla, file-level
// conflicts). Integration boundary agreed there (§1.11): the launcher
// passes the portable root (the folder of GameLauncher.exe) and the
// WebView2 profile already lives on that drive (data\webview2).
//
// The launcher side is ready for it:
//   - UI: the "Mody" page (internal/webui/web/app.js, PAGES.mods);
//   - data: config.json → mods_data / last_mod_locations of the Python
//     version are preserved untouched by the Go store;
//   - bridge: channels will be registered under "mods.*".
package modmgr

// Service is the boundary the launcher will call.
type Service interface {
	// Root is the portable root (folder of GameLauncher.exe).
	Root() string
}

// New will construct the service for the portable root.
func New(root string) Service { return service{root: root} }

type service struct{ root string }

func (s service) Root() string { return s.root }
