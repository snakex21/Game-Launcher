"""Budowanie polecenia uruchomienia gry."""
import os

import pytest

from launcher.launch_command import LaunchError, build_launch_command, find_existing_path

APP = r"F:\Launcher"


def exists_in(*present):
    present = {os.path.normcase(p) for p in present}
    return lambda p: os.path.normcase(p) in present


def test_pc_game_uses_exe_folder_as_cwd():
    game = {"exe_path": r"D:\Gry\DSJ4\DSJ4.exe"}
    spec = build_launch_command("DSJ4", game, {}, exists=exists_in(r"D:\Gry\DSJ4\DSJ4.exe"), app_dir=APP)
    assert spec.command == [r"D:\Gry\DSJ4\DSJ4.exe"]
    assert spec.cwd == r"D:\Gry\DSJ4"


def test_profile_exe_and_arguments():
    game = {"exe_path": r"D:\Gry\GTA\gta_sa.exe"}
    profile = {
        "name": "Mody",
        "exe_path": r"D:\Gry\GTA\gta_sa_mod.exe",
        "arguments": r'-windowed -cfg "D:\Gry\GTA\my cfg.ini"',
    }
    spec = build_launch_command(
        "GTA SA", game, {}, profile=profile, exists=exists_in(r"D:\Gry\GTA\gta_sa_mod.exe"), app_dir=APP
    )
    assert spec.command == [r"D:\Gry\GTA\gta_sa_mod.exe", "-windowed", "-cfg", r"D:\Gry\GTA\my cfg.ini"]
    assert spec.cwd == r"D:\Gry\GTA"
    assert "Mody" in spec.profile_name


def test_profile_without_exe_falls_back_to_game_exe():
    game = {"exe_path": r"D:\Gry\x\x.exe"}
    spec = build_launch_command(
        "X",
        game,
        {},
        profile={"name": "Default", "exe_path": None, "arguments": ""},
        exists=exists_in(r"D:\Gry\x\x.exe"),
        app_dir=APP,
    )
    assert spec.command == [r"D:\Gry\x\x.exe"]


def test_emulator_command_and_cwd():
    game = {
        "game_type": "emulator",
        "emulator_name": "PCSX2",
        "rom_path": r"H:\ROM\okami.iso",
        "emulator_args": "-fullscreen -nogui",
    }
    emulators = {"PCSX2": {"path": r"H:\Emu\PCSX2\pcsx2-qt.exe"}}
    spec = build_launch_command(
        "Okami",
        game,
        emulators,
        exists=exists_in(r"H:\ROM\okami.iso", r"H:\Emu\PCSX2\pcsx2-qt.exe"),
        app_dir=APP,
    )
    assert spec.command == [r"H:\Emu\PCSX2\pcsx2-qt.exe", "-fullscreen", "-nogui", r"H:\ROM\okami.iso"]
    assert spec.cwd == r"H:\Emu\PCSX2"


def test_missing_exe_on_old_drive_is_found_on_launcher_drive():
    game = {"exe_path": r"E:\Gry\Gothic\Gothic.exe"}
    spec = build_launch_command("Gothic", game, {}, exists=exists_in(r"F:\Gry\Gothic\Gothic.exe"), app_dir=APP)
    assert spec.command == [r"F:\Gry\Gothic\Gothic.exe"]
    assert spec.cwd == r"F:\Gry\Gothic"


def test_find_existing_path_none():
    assert find_existing_path(r"E:\nope.exe", exists=lambda p: False, app_dir=APP) is None
    assert find_existing_path("", exists=lambda p: True, app_dir=APP) is None


UNCLOSED_ARGS = '-a "niedomkniety'


@pytest.mark.parametrize(
    "game, emulators, profile, fragment",
    [
        ({}, {}, None, "nie ma ustawionej ścieżki"),
        ({"exe_path": r"D:\brak.exe"}, {}, None, r"D:\brak.exe"),
        ({}, {}, {"name": "P1", "exe_path": None}, "Profil \u201eP1\u201d"),
        ({"exe_path": r"D:\x.exe"}, {}, {"name": "P", "arguments": UNCLOSED_ARGS}, "cudzysłowy"),
        ({"game_type": "emulator", "emulator_name": "PCSX2"}, {}, None, "ROM/ISO"),
        ({"game_type": "emulator", "emulator_name": "PCSX2", "rom_path": "r.iso"}, {}, None, "nie jest skonfigurowany"),
        (
            {"game_type": "emulator", "emulator_name": "E", "rom_path": "r.iso"},
            {"E": {"path": r"D:\e.exe"}},
            None,
            "emulatora \u201eE\u201d",
        ),
        ({"game_type": "dos"}, {}, None, "Nieznany typ gry"),
    ],
)
def test_errors_have_real_polish_messages(game, emulators, profile, fragment):
    with pytest.raises(LaunchError) as info:
        build_launch_command("Gra", game, emulators, profile=profile, exists=exists_in(r"D:\x.exe"), app_dir=APP)
    assert fragment in info.value.message
    assert info.value.message.strip() != "..."
    assert info.value.title


def test_rom_missing_message():
    game = {"game_type": "emulator", "emulator_name": "E", "rom_path": r"D:\r.iso"}
    with pytest.raises(LaunchError) as info:
        build_launch_command("Gra", game, {"E": {"path": r"D:\e.exe"}}, exists=exists_in(r"D:\e.exe"), app_dir=APP)
    assert r"D:\r.iso" in info.value.message


def test_runtime_launch_passes_cwd_to_popen(monkeypatch, tmp_path):
    """launch_game przekazuje cwd = folder gry do subprocess.Popen."""
    from launcher import game_process_runtime as gpr

    exe = tmp_path / "Gra" / "gra.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"")
    calls = {}

    class FakePopen:
        def __init__(self, command, cwd=None):
            calls["command"], calls["cwd"] = command, cwd

    monkeypatch.setattr(gpr.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(gpr, "save_config", lambda cfg: None)
    errors = []
    monkeypatch.setattr(gpr.messagebox, "showerror", lambda *a, **k: errors.append(a))

    class FakeLauncher:
        def __init__(self):
            self.games = {"Gra": {"exe_path": str(exe)}}
            self.config = {"games": self.games}
            self.user = {}
            self.processes = {}
            self.game_start_times = {}
            self._launch_buttons = {}
            self.root = None

        def _update_discord_status(self, **kwargs):
            pass

    gpr.launch_game(FakeLauncher(), "Gra")
    assert not errors
    assert calls["command"] == [str(exe)]
    assert os.path.normcase(calls["cwd"]) == os.path.normcase(str(exe.parent))


def test_runtime_shows_error_dialog_for_missing_exe(monkeypatch):
    from launcher import game_process_runtime as gpr

    errors = []
    monkeypatch.setattr(gpr.messagebox, "showerror", lambda title, msg, **k: errors.append((title, msg)))
    monkeypatch.setattr(gpr.subprocess, "Popen", lambda *a, **k: pytest.fail("nie powinno startować"))

    class FakeLauncher:
        games = {"Brak": {"exe_path": r"Q:\nie\istnieje.exe"}}
        config = {}
        root = None

    gpr.launch_game(FakeLauncher(), "Brak")
    assert len(errors) == 1
    title, msg = errors[0]
    assert title == "Nie znaleziono gry"
    assert r"Q:\nie\istnieje.exe" in msg
