import json
import logging
import os
import shutil
import time
import uuid

from packaging import version

from launcher.utils import (
    CONFIG_FILE,
    GAMES_FOLDER,
    LOCAL_SETTINGS_FILE,
    DEFAULT_MUSIC_HOTKEYS,
    PROGRAM_VERSION,
)


def _migrate_legacy_file(legacy_filename: str, target_path: str):
    if os.path.exists(target_path):
        return

    legacy_path = os.path.join(os.getcwd(), legacy_filename)
    if not os.path.exists(legacy_path):
        return

    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    try:
        os.replace(legacy_path, target_path)
        logging.info(f"Zmigrowano plik '{legacy_filename}' do '{target_path}'.")
    except OSError as error:
        logging.warning(
            f"Nie udalo sie przeniesc pliku '{legacy_filename}' do '{target_path}': {error}"
        )


def _migrate_legacy_directory(legacy_dirname: str, target_path: str):
    if os.path.exists(target_path):
        return

    legacy_path = os.path.join(os.getcwd(), legacy_dirname)
    if not os.path.isdir(legacy_path):
        return

    target_parent = os.path.dirname(target_path)
    if target_parent:
        os.makedirs(target_parent, exist_ok=True)

    try:
        os.replace(legacy_path, target_path)
        logging.info(f"Zmigrowano folder '{legacy_dirname}' do '{target_path}'.")
        return
    except OSError:
        pass

    try:
        shutil.copytree(legacy_path, target_path, dirs_exist_ok=True)
        shutil.rmtree(legacy_path)
        logging.info(f"Zmigrowano folder '{legacy_dirname}' do '{target_path}'.")
    except OSError as error:
        logging.warning(
            f"Nie udalo sie przeniesc folderu '{legacy_dirname}' do '{target_path}': {error}"
        )


def load_local_settings():
    _migrate_legacy_file("local_settings.json", LOCAL_SETTINGS_FILE)

    if os.path.exists(LOCAL_SETTINGS_FILE):
        try:
            with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(
                f"Blad odczytu pliku {LOCAL_SETTINGS_FILE}: {e}. Uzywam domyslnych."
            )
            data = {}
    else:
        data = {}

    old_chat_server_url = data.pop("chat_server_url", None)
    old_chat_email = data.pop("chat_email", None)
    old_chat_password = data.pop("chat_password", None)
    old_chat_remember_me = data.pop("chat_remember_me", False)
    old_chat_auto_login = data.pop("chat_auto_login", False)

    if "chat_servers" not in data or not isinstance(data["chat_servers"], list):
        data["chat_servers"] = []

    if old_chat_server_url and not data["chat_servers"]:
        migrated_server_id = str(uuid.uuid4())
        migrated_server_entry = {
            "id": migrated_server_id,
            "name": "Domyslny Serwer (migr.)",
            "url": old_chat_server_url,
            "is_default": True,
            "last_used": time.time(),
            "credentials": {},
            "remember_credentials": old_chat_remember_me,
            "auto_login_to_server": old_chat_auto_login and old_chat_remember_me,
        }
        if old_chat_remember_me and old_chat_email:
            migrated_server_entry["credentials"]["email"] = old_chat_email
            migrated_server_entry["credentials"]["password"] = old_chat_password

        data["chat_servers"].append(migrated_server_entry)
        data["active_chat_server_id"] = migrated_server_id
        logging.info(
            f"Migrowano ustawienia pojedynczego serwera czatu: {old_chat_server_url}"
        )

    if not data["chat_servers"]:
        default_server_id = str(uuid.uuid4())
        data["chat_servers"] = [
            {
                "id": default_server_id,
                "name": "Serwer Lokalny (Domyslny)",
                "url": "http://127.0.0.1:5000",
                "is_default": True,
                "last_used": None,
                "credentials": {},
                "remember_credentials": False,
                "auto_login_to_server": False,
            }
        ]
        data["active_chat_server_id"] = default_server_id

    if data["chat_servers"] and "active_chat_server_id" not in data:
        default_server = next(
            (s for s in data["chat_servers"] if s.get("is_default")), None
        )
        data["active_chat_server_id"] = (
            default_server["id"] if default_server else data["chat_servers"][0]["id"]
        )

    data.setdefault("chat_auto_connect_to_default", True)
    data.setdefault("remote_control_enabled", False)
    data.setdefault("remote_control_port", 5000)
    data.setdefault("window_state", "normal")
    data.setdefault("window_geometry", "1024x768+100+100")
    data.setdefault("library_view_mode", "tiles")
    data.setdefault("tiles_per_row", 3)
    data.setdefault("discord_rpc_enabled", False)
    data.setdefault("discord_status_text", "Korzysta z Game Launcher")
    data.setdefault("ui_font", "Segoe UI")
    data.setdefault("window_maximized", False)
    data.setdefault("last_run_date", "")
    data.setdefault("consecutive_days", 0)
    data.setdefault("total_launcher_usage_seconds", 0)
    data.setdefault("chat_remember_me", False)
    data.setdefault("chat_auto_login", False)
    data.setdefault("avatar_display_size", 48)
    data.setdefault("music_player_volume", 0.5)
    data.setdefault("last_music_folder", os.path.expanduser("~"))
    data.setdefault("music_hotkeys", DEFAULT_MUSIC_HOTKEYS.copy())
    data.setdefault("music_hotkeys_enabled", True)
    data.setdefault("named_music_playlists", {})
    data.setdefault("active_music_playlist_name", None)
    data.setdefault("current_track_in_active_playlist_index", -1)
    data.setdefault("chat_last_email", "")
    data.setdefault("chat_last_user_id", None)
    data.setdefault("music_repeat_mode", "none")
    data.setdefault("music_shuffle_mode", False)
    data.setdefault("music_favorite_tracks", [])
    data.setdefault("launcher_daily_usage_seconds", {})
    data.setdefault("show_track_overlay", False)
    data.setdefault("overlay_x_pos", None)
    data.setdefault("overlay_y_pos", None)
    return data


def save_local_settings(data):
    target_dir = os.path.dirname(LOCAL_SETTINGS_FILE)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def _default_config():
    return {
        "version": PROGRAM_VERSION,
        "games": {},
        "settings": {},
        "groups": {},
        "user": {},
        "emulators": {},
        "saved_filters": {},
    }


def load_config():
    _migrate_legacy_file("config.json", CONFIG_FILE)
    _migrate_legacy_directory("games_saves", GAMES_FOLDER)

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                logging.error(f"Blad odczytu pliku {CONFIG_FILE}: {e}. Tworzenie nowego.")
                return _default_config()
    else:
        data = _default_config()

    data.setdefault("version", "0.0.0")
    if version.parse(PROGRAM_VERSION) > version.parse(data.get("version", "0.0.0")):
        data["version"] = PROGRAM_VERSION

    settings = data.setdefault("settings", {})
    if "rss_feeds" not in settings or not isinstance(settings["rss_feeds"], list):
        settings["rss_feeds"] = [
            {
                "url": "https://feeds.ign.com/ign/games-all",
                "active": True,
                "name": "IGN Games",
            }
        ]
    else:
        if all(isinstance(feed, str) for feed in settings["rss_feeds"]):
            settings["rss_feeds"] = [
                {"url": feed, "active": True, "name": feed}
                for feed in settings["rss_feeds"]
            ]
        settings["rss_feeds"] = [
            (
                feed
                if isinstance(feed, dict) and "url" in feed
                else {"url": str(feed), "active": True, "name": str(feed)}
            )
            for feed in settings["rss_feeds"]
        ]

    settings.setdefault("news_post_limit", 10)
    settings.setdefault(
        "scan_ignore_folders",
        [
            "_CommonRedist",
            "DirectX",
            "DotNet",
            "Redist",
            "Tools",
            "Benchmark",
            "support",
            "data",
            "__overlay",
        ],
    )
    settings.setdefault("scan_recursively", True)
    settings.setdefault("autoscan_screenshot_folders", [])
    settings.setdefault("autoscan_on_startup", False)
    settings.setdefault(
        "screenshot_scan_ignore_folders", ["thumb_cache", "cache", "temp", "thumbnails"]
    )
    settings.setdefault(
        "screenshot_filename_patterns",
        ["{game_name}*.png", "{game_name}*.jpg", "{game_name}*.jpeg"],
    )

    for game_name, game_data in data.get("games", {}).items():
        if not isinstance(game_data, dict):
            logging.warning(
                f"Nieprawidlowy format danych dla gry '{game_name}'. Pomijam profile."
            )
            continue

        if (
            "launch_profiles" not in game_data
            or not isinstance(game_data.get("launch_profiles"), list)
            or not game_data.get("launch_profiles")
        ):
            game_data["launch_profiles"] = [
                {"name": "Default", "exe_path": None, "arguments": ""}
            ]
        else:
            default_found_at_zero = False
            default_found_elsewhere = False
            default_index = -1

            for i, p in enumerate(game_data["launch_profiles"]):
                if isinstance(p, dict) and p.get("name", "").lower() == "default":
                    if i == 0:
                        default_found_at_zero = True
                    else:
                        default_found_elsewhere = True
                        default_index = i
                    break

            if default_found_elsewhere:
                default_profile_obj = game_data["launch_profiles"].pop(default_index)
                game_data["launch_profiles"].insert(0, default_profile_obj)
            elif not default_found_at_zero:
                game_data["launch_profiles"].insert(
                    0, {"name": "Default", "exe_path": None, "arguments": ""}
                )

        game_data.setdefault("screenshots", [])
        game_data.setdefault("autoscan_screenshots", [])
        game_data.setdefault("checklist", [])

    data.setdefault("emulators", {})
    data.setdefault("saved_filters", {})
    user_data = data.setdefault("user", {})
    user_data.setdefault("achievements", {})

    return data
