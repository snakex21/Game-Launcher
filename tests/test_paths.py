"""Ścieżki aplikacji i przenośność ścieżek gier (zmiana litery dysku)."""
import copy
import os
import sys

import pytest

from launcher import paths
from launcher.paths import (
    drive_of,
    make_config_portable,
    remap_drive,
    resolve_config_paths,
    resolve_path,
    to_portable,
)

APP_E = r"E:\Launchery\Game_Launcher"
APP_F = r"F:\Launchery\Game_Launcher"


def test_app_dir_is_repo_root_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.normcase(paths.get_app_dir()) == os.path.normcase(repo_root)
    assert os.path.isfile(os.path.join(paths.get_app_dir(), "game_launcher.py"))


def test_app_dir_frozen_uses_executable_folder(monkeypatch, tmp_path):
    exe = tmp_path / "GameLauncher" / "GameLauncher.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert paths.get_app_dir() == str(exe.parent)


def test_data_constants_are_absolute_and_inside_app_dir():
    from launcher import utils

    for value in (utils.DATA_DIR, utils.CONFIG_FILE, utils.LOCAL_SETTINGS_FILE, utils.CHAT_DB_FILE):
        assert os.path.isabs(value)
        assert os.path.normcase(value).startswith(os.path.normcase(paths.APP_DIR))


@pytest.mark.parametrize(
    "path, expected",
    [
        (r"E:\Gry\Gothic\Gothic.exe", "E:"),
        ("e:/gry/x.exe", "E:"),
        (r"\Gry\x.exe", ""),
        (r"\\nas\gry\x.exe", ""),
        ("images/x.png", ""),
        ("", ""),
    ],
)
def test_drive_of(path, expected):
    assert drive_of(path) == expected


def test_same_drive_path_is_stored_without_drive_letter():
    assert to_portable(r"E:\Gry\Gothic\Gothic.exe", APP_E) == r"\Gry\Gothic\Gothic.exe"
    assert to_portable("e:/Gry/Gothic/Gothic.exe", APP_E) == r"\Gry\Gothic\Gothic.exe"


def test_path_inside_launcher_folder_is_stored_relative():
    assert to_portable(APP_E + r"\Gry\DSJ4\DSJ4.exe", APP_E) == r"Gry\DSJ4\DSJ4.exe"


def test_other_drive_and_unc_paths_are_kept():
    assert to_portable("D:/Gry/x.exe", APP_E) == r"D:\Gry\x.exe"
    assert to_portable(r"\\nas\gry\x.exe", APP_E) == r"\\nas\gry\x.exe"
    assert to_portable(None, APP_E) is None
    assert to_portable("", APP_E) == ""


def test_resolve_uses_current_launcher_drive():
    stored = to_portable(r"E:\Gry\Gothic\Gothic.exe", APP_E)
    assert resolve_path(stored, APP_E) == r"E:\Gry\Gothic\Gothic.exe"
    # pendrive dostał literę F: -> ta sama gra na F:
    assert resolve_path(stored, APP_F) == r"F:\Gry\Gothic\Gothic.exe"


def test_resolve_relative_against_app_dir():
    assert resolve_path(r"Gry\DSJ4\DSJ4.exe", APP_F) == APP_F + r"\Gry\DSJ4\DSJ4.exe"


def test_env_and_home_paths_are_not_touched():
    assert resolve_path(r"%APPDATA%\Gra\save", APP_F) == r"%APPDATA%\Gra\save"
    assert resolve_path(r"~\Saved Games", APP_F) == r"~\Saved Games"
    assert to_portable(r"%APPDATA%\Gra\save", APP_E) == r"%APPDATA%\Gra\save"


def test_remap_drive():
    assert remap_drive(r"E:\Gry\x.exe", "E:", "F:") == r"F:\Gry\x.exe"
    assert remap_drive(r"D:\Gry\x.exe", "E:", "F:") == r"D:\Gry\x.exe"


def _sample_config():
    return {
        "games": {
            "Gothic": {
                "exe_path": r"E:\Gry\Gothic\System\Gothic.exe",
                "save_path": r"C:\Users\gracz\Saved Games\Gothic",
                "launch_profiles": [
                    {"name": "Default", "exe_path": None, "arguments": ""},
                    {"name": "Mod", "exe_path": "E:/Gry/Gothic/System/GothicMod.exe"},
                ],
            },
            "Okami": {"game_type": "emulator", "emulator_name": "PCSX2", "rom_path": r"E:\ROM\okami.iso"},
            "DSJ4": {"exe_path": APP_E + r"\Gry\DSJ4\DSJ4.exe"},
        },
        "emulators": {"PCSX2": {"path": r"E:\Emu\PCSX2\pcsx2.exe"}},
        "settings": {},
    }


def test_round_trip_after_drive_letter_change():
    """Zapis na E:, odczyt po zmianie litery na F: - ścieżki z E: wskazują na F:."""
    saved = make_config_portable(_sample_config(), APP_E)
    assert saved["games"]["Gothic"]["exe_path"] == r"\Gry\Gothic\System\Gothic.exe"
    assert saved["games"]["Gothic"]["launch_profiles"][1]["exe_path"] == r"\Gry\Gothic\System\GothicMod.exe"
    assert saved["games"]["Okami"]["rom_path"] == r"\ROM\okami.iso"
    assert saved["emulators"]["PCSX2"]["path"] == r"\Emu\PCSX2\pcsx2.exe"
    assert saved["games"]["DSJ4"]["exe_path"] == r"Gry\DSJ4\DSJ4.exe"
    # inne dyski bez zmian
    assert saved["games"]["Gothic"]["save_path"] == r"C:\Users\gracz\Saved Games\Gothic"
    assert saved["settings"]["launcher_drive"] == "E:"

    loaded = copy.deepcopy(saved)
    resolve_config_paths(loaded, APP_F)
    assert loaded["games"]["Gothic"]["exe_path"] == r"F:\Gry\Gothic\System\Gothic.exe"
    assert loaded["games"]["Okami"]["rom_path"] == r"F:\ROM\okami.iso"
    assert loaded["emulators"]["PCSX2"]["path"] == r"F:\Emu\PCSX2\pcsx2.exe"
    assert loaded["games"]["DSJ4"]["exe_path"] == APP_F + r"\Gry\DSJ4\DSJ4.exe"
    assert loaded["games"]["Gothic"]["save_path"] == r"C:\Users\gracz\Saved Games\Gothic"
    assert loaded["settings"]["launcher_drive"] == "F:"


def test_legacy_absolute_paths_are_remapped_when_launcher_drive_changed():
    """Stary config (absolutne E:\\...) + zapamiętany dysk E:, launcher teraz na F:."""
    config = _sample_config()
    config["settings"]["launcher_drive"] = "E:"
    remapped = resolve_config_paths(config, APP_F)
    assert remapped == 5  # exe, profil, rom, emulator, DSJ4
    assert config["games"]["Gothic"]["exe_path"] == r"F:\Gry\Gothic\System\Gothic.exe"
    assert config["games"]["Gothic"]["save_path"] == r"C:\Users\gracz\Saved Games\Gothic"


def test_no_remap_without_known_previous_drive():
    config = _sample_config()
    assert resolve_config_paths(config, APP_F) == 0
    assert config["games"]["Gothic"]["exe_path"] == r"E:\Gry\Gothic\System\Gothic.exe"


def test_make_portable_does_not_mutate_in_memory_config():
    config = _sample_config()
    before = copy.deepcopy(config)
    make_config_portable(config, APP_E)
    assert config == before
