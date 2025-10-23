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
        "icon": "🚀",
        "condition_type": "manual",
        "target_value": 1,
    },
    {
        "key": "library_10",
        "name": "Kolekcjoner",
        "description": "Dodaj 10 gier do biblioteki.",
        "points": 25,
        "icon": "📚",
        "condition_type": "library_size",
        "target_value": 10,
    },
    {
        "key": "mod_master",
        "name": "Mod Master",
        "description": "Zainstaluj 5 modów.",
        "points": 20,
        "icon": "🔧",
        "condition_type": "mods_count",
        "target_value": 5,
    },
    {
        "key": "marathon",
        "name": "Maratończyk",
        "description": "Zagraj łącznie 100 godzin.",
        "points": 40,
        "icon": "⏱️",
        "condition_type": "play_time_hours",
        "target_value": 100,
    },
    {
        "key": "roadmap_pro",
        "name": "Planista",
        "description": "Ukończ 3 pozycje w roadmapie.",
        "points": 30,
        "icon": "🗺️",
        "condition_type": "roadmap_completed",
        "target_value": 3,
    },
    {
        "key": "games_5_launched",
        "name": "Gracz Debiutant",
        "description": "Uruchom 5 różnych gier.",
        "points": 15,
        "icon": "🎮",
        "condition_type": "games_launched_count",
        "target_value": 5,
    },
    {
        "key": "library_50",
        "name": "Mega Kolekcjoner",
        "description": "Dodaj 50 gier do biblioteki.",
        "points": 50,
        "icon": "🏛️",
        "condition_type": "library_size",
        "target_value": 50,
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
            achievements.setdefault(key, {"unlocked": False, "timestamp": None, "current_progress": 0})

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
    
    def check_and_update_progress(self) -> None:
        """Sprawdza i aktualizuje postęp osiągnięć na podstawie aktualnych statystyk."""
        games = self.data_manager.get("games", [])
        library_size = len(games)
        
        mods = self.data_manager.get("mods", [])
        mods_count = len(mods)
        
        roadmap = self.data_manager.get("roadmap", [])
        roadmap_completed = sum(1 for item in roadmap if item.get("completed"))
        
        # Liczba uruchomionych gier
        games_launched = sum(1 for game in games if game.get("last_played"))
        
        # Całkowity czas gry w godzinach
        total_play_time = sum(game.get("play_time", 0) for game in games) / 3600.0
        
        catalog = self.catalog()
        achievements = self.user_progress()
        
        for ach_def in catalog:
            key = ach_def["key"]
            condition_type = ach_def.get("condition_type")
            target_value = ach_def.get("target_value", 1)
            
            current_value = 0
            
            if condition_type == "library_size":
                current_value = library_size
            elif condition_type == "mods_count":
                current_value = mods_count
            elif condition_type == "roadmap_completed":
                current_value = roadmap_completed
            elif condition_type == "games_launched_count":
                current_value = games_launched
            elif condition_type == "play_time_hours":
                current_value = int(total_play_time)
            elif condition_type == "manual":
                continue  # Pomijamy ręczne osiągnięcia
            
            # Aktualizuj postęp
            if key in achievements:
                old_progress = achievements[key].get("current_progress", 0)
                achievements[key]["current_progress"] = current_value
                
                # Automatycznie odblokuj jeśli cel osiągnięty
                if current_value >= target_value and not achievements[key].get("unlocked"):
                    self.unlock(key)
                    logger.info(f"Auto-odblokowano osiągnięcie: {key} ({current_value}/{target_value})")
                elif old_progress != current_value:
                    # Zapisz zmianę postępu
                    self.data_manager.set_nested("user", "achievements", value=achievements)
                    logger.debug(f"Zaktualizowano postęp osiągnięcia {key}: {current_value}/{target_value}")
