"""Ścieżki aplikacji i przenośne ścieżki gier.

Moduł bez zależności od Tk, żeby dało się go testować.

* ``APP_DIR`` to folder launchera (obok ``game_launcher.py`` albo obok exe
  z PyInstallera), niezależny od bieżącego katalogu (CWD).
* Ścieżki gier na tym samym dysku co launcher zapisujemy w config.json bez
  litery dysku (np. ``\\Gry\\Gothic\\Gothic.exe``), a gry w folderze
  launchera - względnie do niego (np. ``Gry\\Gothic\\Gothic.exe``). Po zmianie litery
  pendrive'a/dysku (E: -> F:) wczytujemy je z nową literą.
* Ścieżki zapisane bezwzględnie z literą dysku, na którym launcher był
  poprzednio (``settings.launcher_drive``), są przepisywane na nową literę.
"""

from __future__ import annotations

import copy
import ntpath
import os
import sys

__all__ = [
    "APP_DIR",
    "get_app_dir",
    "app_path",
    "resource_path",
    "drive_of",
    "to_portable",
    "resolve_path",
    "remap_drive",
    "GAME_PATH_KEYS",
    "PROFILE_PATH_KEYS",
    "EMULATOR_PATH_KEYS",
    "make_config_portable",
    "resolve_config_paths",
]


def get_app_dir() -> str:
    """Folder aplikacji: obok exe (PyInstaller) albo katalog główny repo."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_DIR = get_app_dir()


def app_path(*parts: str) -> str:
    """Ścieżka bezwzględna wewnątrz folderu aplikacji (dane użytkownika)."""
    return os.path.join(APP_DIR, *parts)


def resource_path(*parts: str) -> str:
    """Zasób tylko do odczytu (ikony). Najpierw obok aplikacji, potem w paczce PyInstallera."""
    candidate = app_path(*parts)
    if os.path.exists(candidate):
        return candidate
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        bundled = os.path.join(bundle_dir, *parts)
        if os.path.exists(bundled):
            return bundled
    return candidate


# --- Przenośne ścieżki (Windows: litery dysków) ---------------------------------
# Używamy ntpath jawnie, żeby logika (i testy) działały identycznie na każdym OS.


def drive_of(path: str) -> str:
    """Litera dysku w postaci 'E:' (wielka litera) albo '' (UNC, ścieżka względna)."""
    if not path:
        return ""
    drive = ntpath.splitdrive(path)[0]
    if len(drive) == 2 and drive[1] == ":":
        return drive.upper()
    return ""


def _is_drive_relative(path: str) -> bool:
    """'\\Gry\\x.exe' - zakorzeniona, ale bez litery dysku."""
    return bool(path) and not ntpath.splitdrive(path)[0] and path[:1] in ("\\", "/") and path[:2] not in ("\\\\", "//")


def to_portable(path, app_dir: str = None):
    """Ścieżka do zapisu w config.json.

    Na dysku launchera -> bez litery dysku; inne dyski, UNC i ścieżki względne
    bez zmian (tylko znormalizowane separatory).
    """
    if not path or not isinstance(path, str):
        return path
    app_dir = APP_DIR if app_dir is None else app_dir
    app_drive = drive_of(app_dir)
    path_drive = drive_of(path)
    if not path_drive:
        if _is_drive_relative(path):
            return ntpath.normpath(path)
        return path
    normalized = ntpath.normpath(path)
    if app_drive and path_drive == app_drive:
        app_norm = ntpath.normpath(app_dir)
        # Gra wewnątrz folderu launchera -> ścieżka względna (przenośna razem z folderem).
        if normalized.lower().startswith(app_norm.lower().rstrip("\\") + "\\"):
            return ntpath.relpath(normalized, app_norm)
        return normalized[2:]
    return normalized


def resolve_path(path, app_dir: str = None):
    """Ścieżka z config.json -> ścieżka bezwzględna do użycia w programie."""
    if not path or not isinstance(path, str):
        return path
    app_dir = APP_DIR if app_dir is None else app_dir
    if _is_drive_relative(path):
        app_drive = drive_of(app_dir)
        return ntpath.normpath(app_drive + path) if app_drive else ntpath.normpath(path)
    if drive_of(path) or path.startswith(("\\\\", "//")):
        return ntpath.normpath(path)
    # Względna (np. images/okladka.jpg) - względem folderu aplikacji.
    return ntpath.normpath(ntpath.join(app_dir, path))


def remap_drive(path, old_drive: str, new_drive: str):
    """Zamienia literę dysku old_drive -> new_drive (bez zmian, jeśli dysk inny)."""
    if not path or not isinstance(path, str) or not old_drive or not new_drive:
        return path
    if drive_of(path) == old_drive.upper():
        return new_drive.upper() + ntpath.normpath(path)[2:]
    return path


# --- Operacje na całym config.json ------------------------------------------------

GAME_PATH_KEYS = ("exe_path", "rom_path", "save_path")
PROFILE_PATH_KEYS = ("exe_path",)
EMULATOR_PATH_KEYS = ("path",)


def _iter_path_slots(config):
    """Zwraca (dict, klucz) dla każdej przechowywanej ścieżki gry/emulatora."""
    for game in (config.get("games") or {}).values():
        if not isinstance(game, dict):
            continue
        for key in GAME_PATH_KEYS:
            if game.get(key):
                yield game, key
        for profile in game.get("launch_profiles") or []:
            if isinstance(profile, dict):
                for key in PROFILE_PATH_KEYS:
                    if profile.get(key):
                        yield profile, key
    emulators = config.get("emulators") or {}
    emulator_entries = emulators.values() if isinstance(emulators, dict) else emulators
    for emulator in emulator_entries:
        if isinstance(emulator, dict):
            for key in EMULATOR_PATH_KEYS:
                if emulator.get(key):
                    yield emulator, key


def make_config_portable(config, app_dir: str = None):
    """Kopia konfiguracji do zapisu: ścieżki na dysku launchera bez litery dysku."""
    app_dir = APP_DIR if app_dir is None else app_dir
    portable = copy.deepcopy(config)
    for container, key in _iter_path_slots(portable):
        container[key] = to_portable(container[key], app_dir)
    drive = drive_of(app_dir)
    if drive:
        portable.setdefault("settings", {})["launcher_drive"] = drive
    return portable


def resolve_config_paths(config, app_dir: str = None):
    """Rozwiązuje ścieżki w konfiguracji (w miejscu) dla bieżącej lokalizacji launchera.

    Zwraca liczbę ścieżek przemapowanych z poprzedniej litery dysku launchera.
    """
    app_dir = APP_DIR if app_dir is None else app_dir
    new_drive = drive_of(app_dir)
    settings = config.setdefault("settings", {})
    old_drive = (settings.get("launcher_drive") or "").upper()
    remapped = 0
    for container, key in _iter_path_slots(config):
        original = container[key]
        value = original
        if old_drive and new_drive and old_drive != new_drive:
            value = remap_drive(value, old_drive, new_drive)
            if value != original:
                remapped += 1
        container[key] = resolve_path(value, app_dir)
    if new_drive:
        settings["launcher_drive"] = new_drive
    return remapped
