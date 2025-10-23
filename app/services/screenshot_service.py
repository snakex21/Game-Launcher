"""Zarządzanie zrzutami ekranu gier."""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScreenshotService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        
        # Domyślne wzorce nazw plików
        self.default_patterns = [
            r"screenshot.*\.(png|jpg|jpeg|bmp)",
            r".*_screenshot.*\.(png|jpg|jpeg|bmp)",
            r"screen\d+\.(png|jpg|jpeg|bmp)",
            r"\d{8}_\d{6}\.(png|jpg|jpeg|bmp)",  # YYYYMMDD_HHMMSS
        ]
        
        # Foldery do ignorowania
        self.ignore_folders = ["thumb_cache", "cache", "temp", "thumbnails", "__pycache__"]
    
    def get_scan_folders(self) -> list[str]:
        """Zwraca listę folderów do skanowania."""
        return self.data_manager.get_nested("settings", "autoscan_screenshot_folders", default=[])
    
    def add_scan_folder(self, folder_path: str) -> None:
        """Dodaje folder do listy skanowania."""
        folders = self.get_scan_folders()
        if folder_path not in folders:
            folders.append(folder_path)
            self.data_manager.set_nested("settings", "autoscan_screenshot_folders", value=folders)
            logger.info("Dodano folder do skanowania: %s", folder_path)
            self.event_bus.emit("screenshot_folders_changed")
    
    def remove_scan_folder(self, folder_path: str) -> None:
        """Usuwa folder z listy skanowania."""
        folders = self.get_scan_folders()
        if folder_path in folders:
            folders.remove(folder_path)
            self.data_manager.set_nested("settings", "autoscan_screenshot_folders", value=folders)
            logger.info("Usunięto folder ze skanowania: %s", folder_path)
            self.event_bus.emit("screenshot_folders_changed")
    
    def scan_for_screenshots(self) -> list[dict[str, Any]]:
        """Skanuje wszystkie foldery w poszukiwaniu screenshotów."""
        found_screenshots: list[dict[str, Any]] = []
        folders = self.get_scan_folders()
        
        for folder in folders:
            path = Path(folder)
            if not path.exists():
                logger.warning("Folder nie istnieje: %s", folder)
                continue
            
            try:
                for file_path in path.rglob("*"):
                    # Pomijaj foldery do ignorowania
                    if any(ignore in str(file_path).lower() for ignore in self.ignore_folders):
                        continue
                    
                    # Sprawdź czy pasuje do wzorców
                    if file_path.is_file() and self._matches_pattern(file_path.name):
                        found_screenshots.append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        })
            except Exception as e:
                logger.error("Błąd skanowania folderu %s: %s", folder, e)
        
        logger.info("Znaleziono %d screenshotów", len(found_screenshots))
        return found_screenshots
    
    def _matches_pattern(self, filename: str) -> bool:
        """Sprawdza czy nazwa pliku pasuje do wzorców screenshotów."""
        filename_lower = filename.lower()
        for pattern in self.default_patterns:
            if re.match(pattern, filename_lower):
                return True
        return False
    
    def add_manual_screenshot(self, game_id: str, screenshot_path: str) -> None:
        """Dodaje ręcznie wybrany screenshot do gry."""
        games = self.data_manager.get("games", [])
        for game in games:
            if game.get("id") == game_id:
                screenshots = game.setdefault("screenshots", [])
                if screenshot_path not in screenshots:
                    screenshots.append(screenshot_path)
                    self.data_manager.set("games", games)
                    logger.info("Dodano screenshot do gry %s: %s", game.get("name"), screenshot_path)
                    self.event_bus.emit("screenshot_added", game_id=game_id, path=screenshot_path)
                break
    
    def remove_screenshot(self, game_id: str, screenshot_path: str) -> None:
        """Usuwa screenshot z gry."""
        games = self.data_manager.get("games", [])
        for game in games:
            if game.get("id") == game_id:
                screenshots = game.get("screenshots", [])
                if screenshot_path in screenshots:
                    screenshots.remove(screenshot_path)
                    self.data_manager.set("games", games)
                    logger.info("Usunięto screenshot z gry %s", game.get("name"))
                    self.event_bus.emit("screenshot_removed", game_id=game_id, path=screenshot_path)
                break
    
    def get_game_screenshots(self, game_id: str) -> list[str]:
        """Zwraca listę screenshotów dla danej gry."""
        games = self.data_manager.get("games", [])
        for game in games:
            if game.get("id") == game_id:
                return game.get("screenshots", [])
        return []
    
    def auto_assign_screenshots(self, game_id: str, game_name: str) -> int:
        """Automatycznie przypisuje znalezione screenshoty do gry na podstawie nazwy."""
        found = self.scan_for_screenshots()
        assigned = 0
        
        # Szukaj plików zawierających nazwę gry
        game_name_lower = game_name.lower()
        for screenshot in found:
            if game_name_lower in screenshot["name"].lower():
                self.add_manual_screenshot(game_id, screenshot["path"])
                assigned += 1
        
        logger.info("Automatycznie przypisano %d screenshotów do gry %s", assigned, game_name)
        return assigned
