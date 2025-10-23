"""JSON-based data store, the central database for the application."""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DataManager:
    """Zarządza wczytywaniem i zapisywaniem danych w formacie JSON."""

    def __init__(self, config_file: str = "config.json", event_bus=None) -> None:
        self.config_file = Path(config_file)
        self.event_bus = event_bus
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.config_file.exists() and self.config_file.stat().st_size > 0:
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"Załadowano konfigurację z {self.config_file}")
            except json.JSONDecodeError as e:
                logger.error(f"Błąd parsowania JSON w {self.config_file}: {e}")
                self._create_backup()
                self.data = self._get_defaults()
        else:
            if self.config_file.exists():
                logger.info(f"Plik {self.config_file} jest pusty – tworzenie domyślnej konfiguracji")
            else:
                logger.info(f"Plik {self.config_file} nie istnieje, tworzenie domyślnej konfiguracji")
            self.data = self._get_defaults()
        
        self._ensure_structure()
        self.save()

    def _create_backup(self) -> None:
        if self.config_file.exists():
            backup_name = f"{self.config_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.config_file.parent / backup_name
            try:
                shutil.copy2(self.config_file, backup_path)
                logger.info(f"Utworzono backup: {backup_path}")
            except Exception as e:
                logger.error(f"Nie można utworzyć backupu: {e}")

    def _get_defaults(self) -> dict[str, Any]:
        data_path = Path(__file__).resolve().parents[1] / "data" / "database.json"
        if data_path.exists():
            try:
                with open(data_path, encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as exc:
                logger.error("Nieprawidłowy plik domyślnych danych: %s", exc)

        return {
            "games": [],
            "groups": [],
            "genres": [],
            "mods": [],
            "roadmap": [],
            "reminders": [],
            "achievements": {},
            "achievements_catalog": [],
            "emulators": {},
            "saved_filters": {},
            "user": {
                "username": "Gracz",
                "avatar": "",
                "bio": "",
                "achievements": {}
            },
            "settings": {
                "theme": "dark-blue",
                "background": "",
                "auto_start": False,
                "minimize_to_tray": False,
                "show_notifications": True,
                "rss_feeds": [
                    "https://www.gamespot.com/feeds/news/",
                    "https://www.ign.com/feed/rss",
                ],
                "rss_limit": 10,
                "news_refresh_minutes": 30,
                "discord_enabled": False,
                "discord_client_id": "",
                "graph_color": "#3498db",
                "music_volume": 0.5,
                "controller_enabled": False,
            },
        }

    def _ensure_structure(self) -> None:
        defaults = self._get_defaults()
        for key, value in defaults.items():
            self.data.setdefault(key, value)
        
        if "settings" in self.data:
            for key, value in defaults["settings"].items():
                self.data["settings"].setdefault(key, value)

        if "user" in self.data:
            self.data["user"].setdefault("username", "Gracz")
            self.data["user"].setdefault("avatar", "")
            self.data["user"].setdefault("bio", "")
            self.data["user"].setdefault("achievements", {})
        
        for game in self.data.get("games", []):
            game.setdefault("name", "Nieznana Gra")
            game.setdefault("exe_path", "")
            game.setdefault("saves_path", "")
            game.setdefault("cover_image", "")
            game.setdefault("play_time", 0)
            game.setdefault("last_played", "")
            game.setdefault("completion", 0)
            game.setdefault("groups", [])
            game.setdefault("genres", [])
            game.setdefault("rating", 0)
            game.setdefault("sessions", [])
            game.setdefault("notes", "")
            game.setdefault("screenshots", [])
            game.setdefault("autoscan_screenshots", [])
            game.setdefault("checklist", [])
            game.setdefault("launch_profiles", [{"name": "Default", "exe_path": None, "arguments": ""}])

    def save(self) -> None:
        try:
            data_copy = self.data.copy()
            if "settings" in data_copy and "github_token" in data_copy["settings"]:
                data_copy["settings"].pop("github_token")
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data_copy, f, indent=2, ensure_ascii=False)
            
            if self.event_bus:
                self.event_bus.emit("data_saved")
        except Exception as e:
            logger.error(f"Błąd zapisu konfiguracji: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        current = self.data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current if current is not None else default

    def set_nested(self, *keys: str, value: Any) -> None:
        if len(keys) < 2:
            raise ValueError("set_nested requires at least 2 keys")
        
        current = self.data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save()
