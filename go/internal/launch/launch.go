// Package launch builds and starts the command for a game (port of
// launcher/launch_command.py): PC games start with the working directory set
// to the game's folder, emulated games run "<emulator> [args] <rom>" in the
// emulator's folder. Errors carry Polish title/message for the UI.
package launch

import (
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"syscall"

	"github.com/snakex21/game-launcher/go/internal/ojson"
	"github.com/snakex21/game-launcher/go/internal/paths"
)

// Error is a configuration problem with a user-facing title and message.
type Error struct {
	Title   string
	Message string
}

func (e *Error) Error() string { return e.Message }

func lerr(title, format string, a ...any) *Error {
	return &Error{Title: title, Message: fmt.Sprintf(format, a...)}
}

// Spec is a resolved launch.
type Spec struct {
	Command     []string `json:"command"`
	Cwd         string   `json:"cwd"`
	ProfileName string   `json:"profile"`
	Description string   `json:"description"`
}

// SplitArgs splits an argument string like Python's
// shlex.split(s, posix=False) followed by stripping one pair of surrounding
// double quotes from every token (what launch_command.py does).
func SplitArgs(s string) ([]string, error) {
	var out []string
	var cur strings.Builder
	inTok := false
	var quote byte
	for i := 0; i < len(s); i++ {
		c := s[i]
		if quote != 0 {
			cur.WriteByte(c)
			if c == quote {
				quote = 0
			}
			continue
		}
		switch {
		case c == ' ' || c == '\t' || c == '\n' || c == '\r':
			if inTok {
				out = append(out, cur.String())
				cur.Reset()
				inTok = false
			}
		case c == '"' || c == '\'':
			quote = c
			inTok = true
			cur.WriteByte(c)
		default:
			inTok = true
			cur.WriteByte(c)
		}
	}
	if quote != 0 {
		return nil, errors.New("No closing quotation")
	}
	if inTok {
		out = append(out, cur.String())
	}
	for i, p := range out {
		if len(p) >= 2 && p[0] == '"' && p[len(p)-1] == '"' {
			out[i] = p[1 : len(p)-1]
		}
	}
	return out, nil
}

func splitArgsErr(args, title, message string) ([]string, error) {
	if args == "" {
		return nil, nil
	}
	parts, err := SplitArgs(args)
	if err != nil {
		return nil, lerr(title, "%s\n\n%s\n\nSzczegóły: %v", message, args, err)
	}
	return parts, nil
}

// Build resolves the launch command for a game. profile may be nil.
func Build(gameName string, game, emulators, profile *ojson.Object, appDir string, exists func(string) bool) (*Spec, error) {
	gameType := game.Str("game_type")
	if gameType == "" {
		gameType = "pc"
	}
	switch gameType {
	case "pc":
		exe := game.Str("exe_path")
		profileName := "Default (PC)"
		var args []string
		if profile != nil {
			profileName = profile.Str("name")
			if profileName == "" {
				profileName = "Profil bez nazwy"
			}
			if pe := profile.Str("exe_path"); pe != "" {
				exe = pe
				profileName += " (exe profilu)"
			} else if exe == "" {
				return nil, lerr("Brak pliku gry",
					"Profil „%s” gry „%s” nie ma własnego pliku .exe, a gra nie ma ustawionej domyślnej ścieżki.\n\nUstaw plik wykonywalny w edycji gry.",
					profileName, gameName)
			}
			var err error
			args, err = splitArgsErr(profile.Str("arguments"), "Błąd argumentów",
				fmt.Sprintf("Nie można odczytać argumentów profilu „%s” gry „%s”. Sprawdź, czy wszystkie cudzysłowy są domknięte:", profileName, gameName))
			if err != nil {
				return nil, err
			}
		} else if exe == "" {
			return nil, lerr("Brak pliku gry",
				"Gra „%s” nie ma ustawionej ścieżki do pliku .exe.\n\nUstaw ją w edycji gry.", gameName)
		}
		resolved := paths.FindExisting(exe, appDir, exists)
		if resolved == "" {
			return nil, lerr("Nie znaleziono gry",
				"Nie znaleziono pliku gry „%s”:\n%s\n\nJeśli gra została przeniesiona albo zmieniła się litera dysku, wskaż nową lokalizację w edycji gry.",
				gameName, exe)
		}
		return &Spec{
			Command:     append([]string{resolved}, args...),
			Cwd:         paths.Dir(resolved),
			ProfileName: profileName,
			Description: fmt.Sprintf("gra PC: %s (profil: %s)", gameName, profileName),
		}, nil

	case "emulator":
		emuName := game.Str("emulator_name")
		rom := game.Str("rom_path")
		if emuName == "" || rom == "" {
			missing := "pliku ROM/ISO"
			if emuName == "" {
				missing = "emulatora"
			}
			return nil, lerr("Błąd konfiguracji", "Gra „%s” nie ma ustawionego %s.\n\nUzupełnij dane w edycji gry.", gameName, missing)
		}
		emu := emulators.Obj(emuName)
		if emu == nil || emu.Str("path") == "" {
			return nil, lerr("Błąd emulatora",
				"Emulator „%s” nie jest skonfigurowany (brak ścieżki do programu).\n\nDodaj go w Ustawienia → Emulatory.", emuName)
		}
		emuExe := paths.FindExisting(emu.Str("path"), appDir, exists)
		if emuExe == "" {
			return nil, lerr("Nie znaleziono emulatora",
				"Nie znaleziono pliku emulatora „%s”:\n%s\n\nPopraw ścieżkę w Ustawienia → Emulatory.", emuName, emu.Str("path"))
		}
		resolvedRom := paths.FindExisting(rom, appDir, exists)
		if resolvedRom == "" {
			return nil, lerr("Nie znaleziono pliku ROM",
				"Nie znaleziono pliku ROM/ISO gry „%s”:\n%s\n\nWskaż nową lokalizację w edycji gry.", gameName, rom)
		}
		args, err := splitArgsErr(game.Str("emulator_args"), "Błąd argumentów",
			fmt.Sprintf("Nie można odczytać argumentów emulatora dla gry „%s”. Sprawdź, czy wszystkie cudzysłowy są domknięte:", gameName))
		if err != nil {
			return nil, err
		}
		cmd := append([]string{emuExe}, args...)
		return &Spec{
			Command:     append(cmd, resolvedRom),
			Cwd:         paths.Dir(emuExe),
			ProfileName: "Emulator: " + emuName,
			Description: fmt.Sprintf("gra emulowana: %s (emulator: %s)", gameName, emuName),
		}, nil
	}
	return nil, lerr("Błąd", "Nieznany typ gry „%s” dla „%s”.", gameType, gameName)
}

// errorElevationRequired is ERROR_ELEVATION_REQUIRED (WinError 740).
const errorElevationRequired = syscall.Errno(740)

// Starter starts a process; replaced in tests.
type Starter func(cmd *exec.Cmd) error

// DefaultStarter calls cmd.Start.
func DefaultStarter(cmd *exec.Cmd) error { return cmd.Start() }

// Start runs the spec detached from the launcher (the game keeps running
// when the launcher exits). It returns the started command.
func Start(gameName string, spec *Spec, start Starter) (*exec.Cmd, error) {
	cmd := exec.Command(spec.Command[0], spec.Command[1:]...)
	cmd.Dir = spec.Cwd
	detach(cmd)
	if start == nil {
		start = DefaultStarter
	}
	if err := start(cmd); err != nil {
		if errors.Is(err, errorElevationRequired) {
			return nil, lerr("Błąd uprawnień",
				"Nie można uruchomić gry „%s”.\n\nTa gra wymaga uprawnień administratora, a launcher działa bez nich.\n\n"+
					"Możliwe rozwiązania:\n1. Uruchom launcher jako administrator (mniej bezpieczne).\n"+
					"2. We właściwościach pliku .exe gry (zakładka Zgodność) odznacz „Uruchom ten program jako administrator”, jeśli to możliwe.", gameName)
		}
		return nil, lerr("Błąd uruchamiania", "Nie udało się uruchomić gry „%s”:\n%v", gameName, err)
	}
	return cmd, nil
}
