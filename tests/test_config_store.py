"""Wczytywanie konfiguracji i ustawień lokalnych (sekrety, porty, ścieżki)."""
import json
import os

import pytest

from launcher import config_store, utils
import launcher.paths as paths


@pytest.fixture
def isolated_files(tmp_path, monkeypatch):
    local = tmp_path / "config" / "local_settings.json"
    config = tmp_path / "config" / "config.json"
    monkeypatch.setattr(config_store, "LOCAL_SETTINGS_FILE", str(local))
    monkeypatch.setattr(config_store, "CONFIG_FILE", str(config))
    monkeypatch.setattr(config_store, "GAMES_FOLDER", str(tmp_path / "games_saves"))
    monkeypatch.setattr(utils, "CONFIG_FILE", str(config))
    monkeypatch.setattr(config_store, "APP_DIR", str(tmp_path / "brak_starych_plikow"))
    monkeypatch.setattr(config_store, "_env_overrides", {})
    for env in config_store.SECRET_ENV_VARS.values():
        monkeypatch.delenv(env, raising=False)
    return local, config


def test_defaults_when_no_files(isolated_files):
    settings = config_store.load_local_settings()
    assert settings["remote_control_enabled"] is False
    assert settings["remote_control_port"] == config_store.DEFAULT_REMOTE_CONTROL_PORT
    assert settings["remote_control_bind_lan"] is False
    assert settings["chat_servers"][0]["url"].endswith(":5000")
    cfg = config_store.load_config()
    assert cfg["games"] == {} and "emulators" in cfg


def test_chat_and_remote_ports_differ():
    assert config_store.DEFAULT_CHAT_SERVER_PORT == 5000
    assert config_store.DEFAULT_REMOTE_CONTROL_PORT != config_store.DEFAULT_CHAT_SERVER_PORT


def test_old_remote_port_5000_is_migrated(isolated_files):
    local, _ = isolated_files
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps({"remote_control_port": 5000}), encoding="utf-8")
    assert config_store.load_local_settings()["remote_control_port"] == 5050


def test_custom_remote_port_is_kept(isolated_files):
    local, _ = isolated_files
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps({"remote_control_port": 6123}), encoding="utf-8")
    assert config_store.load_local_settings()["remote_control_port"] == 6123


def test_corrupted_local_settings_falls_back_to_defaults(isolated_files):
    local, _ = isolated_files
    local.parent.mkdir(parents=True)
    local.write_text("{ to nie jest json", encoding="utf-8")
    assert config_store.load_local_settings()["library_view_mode"] == "tiles"


def test_corrupted_config_returns_default(isolated_files):
    _, config = isolated_files
    config.parent.mkdir(parents=True)
    config.write_text("{", encoding="utf-8")
    assert config_store.load_config()["games"] == {}


def test_profiles_get_default_entry(isolated_files):
    _, config = isolated_files
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"games": {"G": {"exe_path": "", "launch_profiles": [{"name": "Mod"}]}}}),
        encoding="utf-8",
    )
    profiles = config_store.load_config()["games"]["G"]["launch_profiles"]
    assert profiles[0]["name"] == "Default" and profiles[1]["name"] == "Mod"


def test_secret_from_env_overrides_but_is_not_saved(isolated_files, monkeypatch):
    local, _ = isolated_files
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps({"rawg_api_key": "z_pliku"}), encoding="utf-8")
    monkeypatch.setenv("GL_RAWG_API_KEY", "z_env")
    monkeypatch.setenv("GL_LASTFM_API_KEY", "lastfm_env")
    settings = config_store.load_local_settings()
    assert settings["rawg_api_key"] == "z_env"
    assert settings["lastfm_api_key"] == "lastfm_env"
    config_store.save_local_settings(settings)
    on_disk = json.loads(local.read_text(encoding="utf-8"))
    assert on_disk["rawg_api_key"] == "z_pliku"
    assert "lastfm_api_key" not in on_disk


def test_secret_changed_in_ui_is_saved(isolated_files, monkeypatch):
    local, _ = isolated_files
    monkeypatch.setenv("GL_RAWG_API_KEY", "z_env")
    settings = config_store.load_local_settings()
    settings["rawg_api_key"] = "nowy_z_ui"
    config_store.save_local_settings(settings)
    assert json.loads(local.read_text(encoding="utf-8"))["rawg_api_key"] == "nowy_z_ui"


def test_redact_settings_hides_secrets():
    data = {
        "github_token": "tajne",
        "rawg_api_key": "tajne",
        "chat_servers": [{"name": "S", "credentials": {"password": "tajne"}}],
        "chat_password": "tajne",
        "tiles_per_row": 5,
    }
    text = json.dumps(config_store.redact_settings(data))
    assert "tajne" not in text
    assert '"tiles_per_row": 5' in text


def test_config_paths_are_saved_portable_and_resolved_on_load(isolated_files, monkeypatch):
    _, config_file = isolated_files
    monkeypatch.setattr(paths, "APP_DIR", r"E:\Launcher")
    cfg = {"games": {"G": {"exe_path": r"E:\Gry\G\g.exe"}}, "settings": {}}
    utils.save_config(cfg)
    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["games"]["G"]["exe_path"] == r"\Gry\G\g.exe"
    assert cfg["games"]["G"]["exe_path"] == r"E:\Gry\G\g.exe"  # dane w pamięci bez zmian

    monkeypatch.setattr(paths, "APP_DIR", r"F:\Launcher")
    loaded = config_store.load_config()
    assert loaded["games"]["G"]["exe_path"] == r"F:\Gry\G\g.exe"


def test_example_files_are_valid_and_have_no_secrets():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("config.example.json", "local_settings.example.json"):
        with open(os.path.join(root, name), encoding="utf-8") as fh:
            data = json.load(fh)
        for key in config_store.SECRET_KEYS:
            assert not data.get(key)
            assert not data.get("settings", {}).get(key)
