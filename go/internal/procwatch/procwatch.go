// Package procwatch lists running processes (one snapshot for all games,
// instead of one process walk per game like the Python version) and decides
// which games are running.
package procwatch

import (
	"strings"

	"github.com/snakex21/game-launcher/go/internal/paths"
)

// Process is one running process.
type Process struct {
	PID     uint32
	PPID    uint32
	Name    string // lower-case exe file name
	Exe     string // full path when readable, else ""
	cmdline func() string
}

// CmdLine returns the command line (loaded lazily, may be "").
func (p Process) CmdLine() string {
	if p.cmdline == nil {
		return ""
	}
	return p.cmdline()
}

// Target describes how to recognise a game's process.
type Target struct {
	Game     string
	Emulator bool
	Exes     []string // PC: game exe + profile exes; emulator: emulator exe
	ROM      string   // emulator: ROM path expected in the command line
}

// Match returns the PIDs of processes that belong to the target.
//
// PC games: the full exe path matches, or (when the path cannot be read)
// the file name matches. Emulated games: the emulator exe matches and the
// ROM path is in the command line; when the command line is unreadable the
// process counts only if it is one we started for this game (owned).
func Match(t Target, procs []Process, owned map[uint32]bool) []uint32 {
	var out []uint32
	names := map[string]bool{}
	fulls := map[string]bool{}
	for _, e := range t.Exes {
		if e == "" {
			continue
		}
		fulls[strings.ToLower(paths.NormPath(e))] = true
		names[strings.ToLower(paths.Base(e))] = true
	}
	if len(names) == 0 {
		return nil
	}
	for _, p := range procs {
		if owned[p.PID] {
			out = append(out, p.PID)
			continue
		}
		pathMatch := p.Exe != "" && fulls[strings.ToLower(paths.NormPath(p.Exe))]
		nameMatch := p.Exe == "" && names[p.Name]
		if !pathMatch && !nameMatch {
			continue
		}
		if !t.Emulator {
			out = append(out, p.PID)
			continue
		}
		cl := strings.ToLower(p.CmdLine())
		if cl != "" && t.ROM != "" && strings.Contains(cl, strings.ToLower(paths.NormPath(t.ROM))) {
			out = append(out, p.PID)
		}
	}
	return out
}

// Descendants returns pids plus all their child processes (for closing a
// game that started helpers).
func Descendants(pids []uint32, procs []Process) []uint32 {
	set := map[uint32]bool{}
	for _, p := range pids {
		set[p] = true
	}
	for changed := true; changed; {
		changed = false
		for _, p := range procs {
			if !set[p.PID] && set[p.PPID] && p.PPID != 0 {
				set[p.PID] = true
				changed = true
			}
		}
	}
	out := make([]uint32, 0, len(set))
	// children first, then parents
	for _, p := range procs {
		if set[p.PID] && !contains(pids, p.PID) {
			out = append(out, p.PID)
		}
	}
	return append(out, pids...)
}

func contains(s []uint32, v uint32) bool {
	for _, x := range s {
		if x == v {
			return true
		}
	}
	return false
}
