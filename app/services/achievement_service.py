"""Obsługa osiągnięć użytkownika."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ACHIEVEMENTS = [
    {
        "key": "first_launch",
        "name": "Pierwsze uruchomienie",
        "description": "Uruchom aplikację po raz pierwszy.",
        "points": 10,
    },
    {
        "key": "library_10",
        "name": "Kolekcjoner",
        "description": "Dodaj 10 gier do biblioteki.",
        "points": 25,
    },
    {
        "key": "mod_master",
        "name": "Mod Master",
        "description": "Zainstaluj 5 modów.",
        "points": 20,
    },
    {
        "key": "marathon",
        "name": "Maratończyk",
        "description": "Zagraj łącznie 100 godzin.",
        "points": 40,
    },
    {
        "key": "roadmap_pro",
        "name": "Planista",
        "description": "Ukończ 3 pozycje w roadmapie.",
        "points": 30,
    },
]


class AchievementService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        self._ensure_catalog()

    def _ensure_catalog(self) -> None:
        catalog = self.data_manager.get("achievements_catalog")
        if not isinstance(catalog, list) or not catalog:
            self.data_manager.set("achievements_catalog", DEFAULT_ACHIEVEMENTS)
        
        user = self.data_manager.get("user", {})
        achievements = user.get("achievements")
        if not isinstance(achievements, dict):
            achievements = {}

        catalog_keys = {item["key"] for item in self.data_manager.get("achievements_catalog", [])}
        for key in catalog_keys:
            achievements.setdefault(key, {"unlocked": False, "timestamp": None})

        user["achievements"] = achievements
        self.data_manager.set("user", user)

    def catalog(self) -> list[dict[str, Any]]:
        return self.data_manager.get("achievements_catalog", DEFAULT_ACHIEVEMENTS)

    def user_progress(self) -> dict[str, dict[str, Any]]:
        user = self.data_manager.get("user", {})
        return user.get("achievements", {})

    def unlock(self, key: str) -> None:
        achievements = self.user_progress()
        if key in achievements and not achievements[key].get("unlocked"):
            achievements[key] = {
                "unlocked": True,
                "timestamp": datetime.now().isoformat(),
            }
            self.data_manager.set_nested("user", "achievements", value=achievements)
            logger.info("Odblokowano osiągnięcie: %s", key)
            self.event_bus.emit("achievements_changed", key=key)

    def lock(self, key: str) -> None:
        achievements = self.user_progress()
        if key in achievements and achievements[key].get("unlocked"):
            achievements[key] = {
                "unlocked": False,
                "timestamp": None,
            }
            self.data_manager.set_nested("user", "achievements", value=achievements)
            logger.info("Zresetowano osiągnięcie: %s", key)
            self.event_bus.emit("achievements_changed", key=key)

    def completion_rate(self) -> float:
        progress = self.user_progress()
        if not progress:
            return 0.0
        unlocked = sum(1 for data in progress.values() if data.get("unlocked"))
        return unlocked / len(progress)
