"""Budowanie polecenia uruchomienia gry (bez Tk, testowalne).

``build_launch_command`` zwraca ``LaunchSpec`` (polecenie + katalog roboczy)
albo rzuca ``LaunchError`` z polskim tytułem i treścią do pokazania w oknie błędu.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from typing import Callable, Optional

from launcher.paths import APP_DIR, drive_of, remap_drive


class LaunchError(Exception):
    """Błąd konfiguracji gry - title/message są gotowe do messagebox.showerror."""

    def __init__(self, title: str, message: str):
        super().__init__(message)
        self.title = title
        self.message = message


@dataclass
class LaunchSpec:
    command: list
    cwd: Optional[str]
    profile_name: str
    description: str


def _split_args(args_str: str, title: str, message: str) -> list:
    if not args_str:
        return []
    try:
        # posix=False: zachowuje backslashe w ścieżkach Windows (C:\Gry\...).
        parts = shlex.split(args_str, posix=False)
    except ValueError as error:
        raise LaunchError(title, f"{message}\n\n{args_str}\n\nSzczegóły: {error}") from error
    return [p[1:-1] if len(p) >= 2 and p[0] == p[-1] == '"' else p for p in parts]


def find_existing_path(path, exists: Callable[[str], bool] = os.path.exists, app_dir: str = None):
    """Zwraca istniejącą ścieżkę: oryginał albo tę samą ścieżkę na dysku launchera.

    Pomaga, gdy pendrive/dysk z grami dostał inną literę, a config ma jeszcze starą.
    """
    if not path:
        return None
    if exists(path):
        return path
    app_drive = drive_of(APP_DIR if app_dir is None else app_dir)
    path_drive = drive_of(path)
    if app_drive and path_drive and path_drive != app_drive:
        candidate = remap_drive(path, path_drive, app_drive)
        if exists(candidate):
            return candidate
    return None


def build_launch_command(
    game_name: str,
    game: dict,
    emulators: dict,
    profile: Optional[dict] = None,
    exists: Callable[[str], bool] = os.path.exists,
    app_dir: str = None,
) -> LaunchSpec:
    game_type = game.get("game_type", "pc")

    if game_type == "pc":
        exe_to_run = game.get("exe_path")
        profile_name = "Default (PC)"
        args = []
        if profile and isinstance(profile, dict):
            profile_name = profile.get("name", "Profil bez nazwy")
            if profile.get("exe_path"):
                exe_to_run = profile["exe_path"]
                profile_name += " (exe profilu)"
            elif not exe_to_run:
                raise LaunchError(
                    "Brak pliku gry",
                    f"Profil „{profile_name}” gry „{game_name}” nie ma własnego pliku .exe, "
                    "a gra nie ma ustawionej domyślnej ścieżki.\n\n"
                    "Ustaw plik wykonywalny w edycji gry.",
                )
            args = _split_args(
                profile.get("arguments", ""),
                "Błąd argumentów",
                f"Nie można odczytać argumentów profilu „{profile_name}” gry „{game_name}”. "
                "Sprawdź, czy wszystkie cudzysłowy są domknięte:",
            )
        elif not exe_to_run:
            raise LaunchError(
                "Brak pliku gry",
                f"Gra „{game_name}” nie ma ustawionej ścieżki do pliku .exe.\n\n"
                "Ustaw ją w edycji gry (prawy przycisk → Edytuj).",
            )

        resolved_exe = find_existing_path(exe_to_run, exists, app_dir)
        if not resolved_exe:
            raise LaunchError(
                "Nie znaleziono gry",
                f"Nie znaleziono pliku gry „{game_name}”:\n{exe_to_run}\n\n"
                "Jeśli gra została przeniesiona albo zmieniła się litera dysku, "
                "wskaż nową lokalizację w edycji gry.",
            )
        return LaunchSpec(
            command=[resolved_exe] + args,
            cwd=os.path.dirname(resolved_exe) or None,
            profile_name=profile_name,
            description=f"gra PC: {game_name} (profil: {profile_name})",
        )

    if game_type == "emulator":
        emulator_name = game.get("emulator_name")
        rom_path = game.get("rom_path")
        profile_name = f"Emulator: {emulator_name}"
        if not emulator_name or not rom_path:
            missing = "emulatora" if not emulator_name else "pliku ROM/ISO"
            raise LaunchError(
                "Błąd konfiguracji",
                f"Gra „{game_name}” nie ma ustawionego {missing}.\n\n"
                "Uzupełnij dane w edycji gry.",
            )
        emulator_config = (emulators or {}).get(emulator_name)
        if not emulator_config or not emulator_config.get("path"):
            raise LaunchError(
                "Błąd emulatora",
                f"Emulator „{emulator_name}” nie jest skonfigurowany (brak ścieżki do programu).\n\n"
                "Dodaj go w Ustawienia → Emulatory.",
            )
        emulator_exe = find_existing_path(emulator_config["path"], exists, app_dir)
        if not emulator_exe:
            raise LaunchError(
                "Nie znaleziono emulatora",
                f"Nie znaleziono pliku emulatora „{emulator_name}”:\n{emulator_config['path']}\n\n"
                "Popraw ścieżkę w Ustawienia → Emulatory.",
            )
        resolved_rom = find_existing_path(rom_path, exists, app_dir)
        if not resolved_rom:
            raise LaunchError(
                "Nie znaleziono pliku ROM",
                f"Nie znaleziono pliku ROM/ISO gry „{game_name}”:\n{rom_path}\n\n"
                "Wskaż nową lokalizację w edycji gry.",
            )
        args = _split_args(
            game.get("emulator_args", ""),
            "Błąd argumentów",
            f"Nie można odczytać argumentów emulatora dla gry „{game_name}”. "
            "Sprawdź, czy wszystkie cudzysłowy są domknięte:",
        )
        return LaunchSpec(
            command=[emulator_exe] + args + [resolved_rom],
            cwd=os.path.dirname(emulator_exe) or None,
            profile_name=profile_name,
            description=f"gra emulowana: {game_name} (emulator: {emulator_name})",
        )

    raise LaunchError("Błąd", f"Nieznany typ gry „{game_type}” dla „{game_name}”.")


__all__ = ["LaunchError", "LaunchSpec", "build_launch_command", "find_existing_path"]
