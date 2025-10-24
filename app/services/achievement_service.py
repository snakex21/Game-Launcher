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
        "builtin": True,
    },
    {
        "key": "library_10",
        "name": "Kolekcjoner",
        "description": "Dodaj 10 gier do biblioteki.",
        "points": 25,
        "icon": "📚",
        "condition_type": "library_size",
        "target_value": 10,
        "builtin": True,
    },
    {
        "key": "library_50",
        "name": "Mega Kolekcjoner",
        "description": "Dodaj 50 gier do biblioteki.",
        "points": 50,
        "icon": "🏛️",
        "condition_type": "library_size",
        "target_value": 50,
        "builtin": True,
    },
    {
        "key": "library_100",
        "name": "Archiwalny Strażnik",
        "description": "Dodaj 100 gier do biblioteki.",
        "points": 100,
        "icon": "📖",
        "condition_type": "library_size",
        "target_value": 100,
        "builtin": True,
    },
    {
        "key": "mod_master",
        "name": "Mistrz Modyfikacji",
        "description": "Zainstaluj 5 modów.",
        "points": 20,
        "icon": "🔧",
        "condition_type": "mods_count",
        "target_value": 5,
        "builtin": True,
    },
    {
        "key": "mod_enthusiast",
        "name": "Entuzjasta Modów",
        "description": "Zainstaluj 20 modów.",
        "points": 40,
        "icon": "🛠️",
        "condition_type": "mods_count",
        "target_value": 20,
        "builtin": True,
    },
    {
        "key": "marathon",
        "name": "Maratończyk",
        "description": "Zagraj łącznie 100 godzin.",
        "points": 40,
        "icon": "⏱️",
        "condition_type": "play_time_hours",
        "target_value": 100,
        "builtin": True,
    },
    {
        "key": "ultra_marathon",
        "name": "Ultra Maratończyk",
        "description": "Zagraj łącznie 500 godzin.",
        "points": 80,
        "icon": "⏰",
        "condition_type": "play_time_hours",
        "target_value": 500,
        "builtin": True,
    },
    {
        "key": "time_lord",
        "name": "Władca Czasu",
        "description": "Zagraj łącznie 1000 godzin.",
        "points": 150,
        "icon": "⌚",
        "condition_type": "play_time_hours",
        "target_value": 1000,
        "builtin": True,
    },
    {
        "key": "roadmap_pro",
        "name": "Planista",
        "description": "Ukończ 3 pozycje w roadmapie.",
        "points": 30,
        "icon": "🗺️",
        "condition_type": "roadmap_completed",
        "target_value": 3,
        "builtin": True,
    },
    {
        "key": "roadmap_master",
        "name": "Mistrz Planowania",
        "description": "Ukończ 10 pozycji w roadmapie.",
        "points": 60,
        "icon": "🗓️",
        "condition_type": "roadmap_completed",
        "target_value": 10,
        "builtin": True,
    },
    {
        "key": "games_5_launched",
        "name": "Gracz Debiutant",
        "description": "Uruchom 5 różnych gier.",
        "points": 15,
        "icon": "🎮",
        "condition_type": "games_launched_count",
        "target_value": 5,
        "builtin": True,
    },
    {
        "key": "games_20_launched",
        "name": "Weteran Gamingu",
        "description": "Uruchom 20 różnych gier.",
        "points": 35,
        "icon": "🎯",
        "condition_type": "games_launched_count",
        "target_value": 20,
        "builtin": True,
    },
    {
        "key": "games_50_launched",
        "name": "Ekspert Rozgrywki",
        "description": "Uruchom 50 różnych gier.",
        "points": 70,
        "icon": "🏅",
        "condition_type": "games_launched_count",
        "target_value": 50,
        "builtin": True,
    },
    {
        "key": "game_launch_10",
        "name": "Oddany Gracz",
        "description": "Uruchom jedną grę 10 razy.",
        "points": 20,
        "icon": "🔄",
        "condition_type": "single_game_launches",
        "target_value": 10,
        "builtin": True,
    },
    {
        "key": "game_launch_50",
        "name": "Fanatyk Gry",
        "description": "Uruchom jedną grę 50 razy.",
        "points": 45,
        "icon": "🔁",
        "condition_type": "single_game_launches",
        "target_value": 50,
        "builtin": True,
    },
    {
        "key": "game_launch_100",
        "name": "Legenda Rozgrywki",
        "description": "Uruchom jedną grę 100 razy.",
        "points": 80,
        "icon": "♾️",
        "condition_type": "single_game_launches",
        "target_value": 100,
        "builtin": True,
    },
    {
        "key": "night_owl",
        "name": "Nocny Maraton",
        "description": "Zagraj grę między 23:00 a 5:00.",
        "points": 15,
        "icon": "🦉",
        "condition_type": "play_at_night",
        "target_value": 1,
        "builtin": True,
    },
    {
        "key": "early_bird",
        "name": "Poranny Ptaszek",
        "description": "Zagraj grę między 5:00 a 8:00.",
        "points": 15,
        "icon": "🐦",
        "condition_type": "play_at_morning",
        "target_value": 1,
        "builtin": True,
    },
    {
        "key": "completionist",
        "name": "Perfekcjonista",
        "description": "Ukończ grę w 100%.",
        "points": 50,
        "icon": "💯",
        "condition_type": "completion_percent",
        "target_value": 100,
        "builtin": True,
    },
    {
        "key": "game_finisher",
        "name": "Finalizator",
        "description": "Ukończ 5 gier.",
        "points": 30,
        "icon": "🏁",
        "condition_type": "games_completed",
        "target_value": 5,
        "builtin": True,
    },
    {
        "key": "game_finisher_pro",
        "name": "Mistrz Ukończeń",
        "description": "Ukończ 20 gier.",
        "points": 70,
        "icon": "🎖️",
        "condition_type": "games_completed",
        "target_value": 20,
        "builtin": True,
    },
    {
        "key": "rating_critic",
        "name": "Krytyk Gier",
        "description": "Oceń 10 gier.",
        "points": 20,
        "icon": "⭐",
        "condition_type": "games_rated",
        "target_value": 10,
        "builtin": True,
    },
    {
        "key": "screenshot_artist",
        "name": "Artysta Screenshotów",
        "description": "Zrób 50 zrzutów ekranu.",
        "points": 25,
        "icon": "📸",
        "condition_type": "screenshots_count",
        "target_value": 50,
        "builtin": True,
    },
    {
        "key": "organizer",
        "name": "Organizator",
        "description": "Utwórz 5 grup gier.",
        "points": 15,
        "icon": "📁",
        "condition_type": "groups_count",
        "target_value": 5,
        "builtin": True,
    },
    {
        "key": "dedicated_player",
        "name": "Zaangażowany Gracz",
        "description": "Graj przez 10 dni z rzędu.",
        "points": 40,
        "icon": "📅",
        "condition_type": "consecutive_days",
        "target_value": 10,
        "builtin": True,
    },
    {
        "key": "session_master",
        "name": "Mistrz Sesji",
        "description": "Zakończ 100 sesji gier.",
        "points": 35,
        "icon": "📊",
        "condition_type": "session_count",
        "target_value": 100,
        "builtin": True,
    },
]


class AchievementService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        self._ensure_catalog()
        self._separate_builtin_from_custom()

    def _ensure_catalog(self) -> None:
        catalog = self.data_manager.get("achievements_catalog")
        if not isinstance(catalog, list) or not catalog:
            self.data_manager.set("achievements_catalog", DEFAULT_ACHIEVEMENTS)
        else:
            # Dodaj nowe wbudowane osiągnięcia jeśli ich nie ma
            existing_keys = {item["key"] for item in catalog}
            for default_ach in DEFAULT_ACHIEVEMENTS:
                if default_ach["key"] not in existing_keys:
                    catalog.append(default_ach)
            self.data_manager.set("achievements_catalog", catalog)
        
        user = self.data_manager.get("user", {})
        achievements = user.get("achievements")
        if not isinstance(achievements, dict):
            achievements = {}

        catalog_keys = {item["key"] for item in self.data_manager.get("achievements_catalog", [])}
        for key in catalog_keys:
            achievements.setdefault(key, {"unlocked": False, "timestamp": None, "current_progress": 0})

        user["achievements"] = achievements
        self.data_manager.set("user", user)
    
    def _separate_builtin_from_custom(self) -> None:
        """Rozdziela wbudowane osiągnięcia od niestandardowych w katalogu."""
        catalog = self.data_manager.get("achievements_catalog", [])
        
        # Upewnij się, że wszystkie wbudowane mają flagę builtin=True
        for ach in catalog:
            if ach["key"] in {d["key"] for d in DEFAULT_ACHIEVEMENTS}:
                ach["builtin"] = True
            else:
                ach.setdefault("custom", True)
        
        self.data_manager.set("achievements_catalog", catalog)

    def catalog(self) -> list[dict[str, Any]]:
        return self.data_manager.get("achievements_catalog", DEFAULT_ACHIEVEMENTS)
    
    def builtin_achievements(self) -> list[dict[str, Any]]:
        """Zwraca tylko wbudowane osiągnięcia."""
        return [ach for ach in self.catalog() if ach.get("builtin", False)]
    
    def custom_achievements(self) -> list[dict[str, Any]]:
        """Zwraca tylko niestandardowe osiągnięcia."""
        return [ach for ach in self.catalog() if ach.get("custom", False)]

    def user_progress(self) -> dict[str, dict[str, Any]]:
        user = self.data_manager.get("user", {})
        return user.get("achievements", {})

    def unlock(self, key: str) -> None:
        achievements = self.user_progress()
        if key in achievements and not achievements[key].get("unlocked"):
            # Znajdź dane osiągnięcia
            catalog = self.catalog()
            achievement_data = next((a for a in catalog if a["key"] == key), None)
            
            achievements[key] = {
                "unlocked": True,
                "timestamp": datetime.now().isoformat(),
                "current_progress": achievements[key].get("current_progress", 0),
            }
            self.data_manager.set_nested("user", "achievements", value=achievements)
            logger.info("Odblokowano osiągnięcie: %s", key)
            
            # Emituj event z danymi osiągnięcia
            self.event_bus.emit("achievement_unlocked", key=key, achievement=achievement_data)
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
        
        groups = self.data_manager.get("groups", [])
        groups_count = len(groups)
        
        # Liczba uruchomionych gier
        games_launched = sum(1 for game in games if game.get("last_played"))
        
        # Całkowity czas gry w godzinach
        total_play_time = sum(game.get("play_time", 0) for game in games) / 3600.0
        
        # Liczba ukończonych gier (completion >= 100)
        games_completed = sum(1 for game in games if game.get("completion", 0) >= 100)
        
        # Maksymalna wartość completion dla osiągnięcia perfekcjonisty
        max_completion = max((game.get("completion", 0) for game in games), default=0)
        
        # Liczba ocenionych gier
        games_rated = sum(1 for game in games if game.get("rating", 0) > 0)
        
        # Liczba zrzutów ekranu
        screenshots_count = sum(
            len(game.get("screenshots", [])) + len(game.get("autoscan_screenshots", []))
            for game in games
        )
        
        # Maksymalna liczba uruchomień jednej gry
        max_single_game_launches = max(
            (len(game.get("sessions", [])) for game in games),
            default=0
        )
        
        # Całkowita liczba sesji
        total_sessions = sum(len(game.get("sessions", [])) for game in games)
        
        # Liczba kolejnych dni z graniem
        consecutive_days = self._calculate_consecutive_days(games)
        
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
            elif condition_type == "games_completed":
                current_value = games_completed
            elif condition_type == "completion_percent":
                current_value = max_completion
            elif condition_type == "games_rated":
                current_value = games_rated
            elif condition_type == "screenshots_count":
                current_value = screenshots_count
            elif condition_type == "single_game_launches":
                current_value = max_single_game_launches
            elif condition_type == "session_count":
                current_value = total_sessions
            elif condition_type == "groups_count":
                current_value = groups_count
            elif condition_type == "consecutive_days":
                current_value = consecutive_days
            elif condition_type in ("play_at_night", "play_at_morning"):
                # Te osiągnięcia są odblokowywane przez event handler
                continue
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
    
    def _calculate_consecutive_days(self, games: list[dict[str, Any]]) -> int:
        """Oblicza liczbę kolejnych dni z graniem."""
        from datetime import datetime, timedelta
        
        all_dates = set()
        for game in games:
            for session in game.get("sessions", []):
                start_time = session.get("start_time")
                if start_time:
                    try:
                        dt = datetime.fromisoformat(start_time)
                        all_dates.add(dt.date())
                    except (ValueError, TypeError):
                        continue
        
        if not all_dates:
            return 0
        
        sorted_dates = sorted(all_dates, reverse=True)
        consecutive = 1
        
        for i in range(len(sorted_dates) - 1):
            if sorted_dates[i] - sorted_dates[i + 1] == timedelta(days=1):
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def check_time_based_achievements(self) -> None:
        """Sprawdza osiągnięcia związane z czasem gry."""
        from datetime import datetime
        
        current_hour = datetime.now().hour
        
        # Nocny Maraton: 23:00 - 5:00
        if current_hour >= 23 or current_hour < 5:
            achievements = self.user_progress()
            if "night_owl" in achievements and not achievements["night_owl"].get("unlocked"):
                self.unlock("night_owl")
        
        # Poranny Ptaszek: 5:00 - 8:00
        if 5 <= current_hour < 8:
            achievements = self.user_progress()
            if "early_bird" in achievements and not achievements["early_bird"].get("unlocked"):
                self.unlock("early_bird")
    
    def export_custom_achievements(self, filepath: str) -> bool:
        """Eksportuje niestandardowe osiągnięcia do pliku JSON."""
        import json
        from pathlib import Path
        
        try:
            custom = self.custom_achievements()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(custom, f, indent=2, ensure_ascii=False)
            logger.info(f"Wyeksportowano {len(custom)} niestandardowych osiągnięć do {filepath}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas eksportu osiągnięć: {e}")
            return False
    
    def import_custom_achievements(self, filepath: str) -> int:
        """Importuje niestandardowe osiągnięcia z pliku JSON."""
        import json
        from pathlib import Path
        
        try:
            with open(filepath, encoding="utf-8") as f:
                imported = json.load(f)
            
            if not isinstance(imported, list):
                logger.error("Nieprawidłowy format pliku osiągnięć")
                return 0
            
            catalog = self.catalog()
            existing_keys = {ach["key"] for ach in catalog}
            count = 0
            
            for ach in imported:
                if not isinstance(ach, dict) or "key" not in ach:
                    continue
                
                # Nie importuj jeśli już istnieje
                if ach["key"] in existing_keys:
                    continue
                
                # Oznacz jako custom
                ach["custom"] = True
                ach.pop("builtin", None)
                
                catalog.append(ach)
                count += 1
                
                # Dodaj do user progress
                user = self.data_manager.get("user", {})
                achievements = user.get("achievements", {})
                achievements[ach["key"]] = {"unlocked": False, "timestamp": None, "current_progress": 0}
                user["achievements"] = achievements
                self.data_manager.set("user", user)
            
            self.data_manager.set("achievements_catalog", catalog)
            logger.info(f"Zaimportowano {count} nowych osiągnięć")
            self.event_bus.emit("achievements_changed")
            return count
        except Exception as e:
            logger.error(f"Błąd podczas importu osiągnięć: {e}")
            return 0
