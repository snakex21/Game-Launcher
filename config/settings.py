"""
Zarządzanie ustawieniami aplikacji Game Launcher
Obsługuje ładowanie, zapisywanie i aktualizację ustawień użytkownika.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from .constants import *

logger = logging.getLogger(__name__)


class Settings:
    """
    Klasa zarządzająca ustawieniami aplikacji.
    Obsługuje ładowanie z pliku JSON, zapisywanie i dostęp do ustawień.
    """
    
    def __init__(self, settings_file: str = SETTINGS_FILE):
        """
        Inicjalizuje menedżer ustawień.
        
        Args:
            settings_file: Nazwa pliku z ustawieniami
        """
        self.settings_file = Path(settings_file)
        self._settings: Dict[str, Any] = {}
        self._default_settings = self._get_default_settings()
        self.load()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Zwraca domyślne ustawienia aplikacji.
        
        Returns:
            Słownik z domyślnymi ustawieniami
        """
        return {
            # Okno główne
            "window": {
                "width": WINDOW_DEFAULT_WIDTH,
                "height": WINDOW_DEFAULT_HEIGHT,
                "maximized": False,
                "x": None,
                "y": None
            },
            
            # Overlay odtwarzacza
            "overlay": {
                "enabled": True,
                "x": None,
                "y": None,
                "show_progress": True,
                "show_time": True
            },
            
            # Odtwarzacz muzyki
            "music": {
                "volume": 0.5,
                "shuffle": False,
                "repeat": False,
                "show_notifications": True,
                "music_folder": None,
                "lastfm_enabled": False,
                "lastfm_username": None,
                "lastfm_password_hash": None,
                "graph_color": "#0078d4"  # Kolor wykresów
            },
            
            # Discord Rich Presence
            "discord": {
                "enabled": True,
                "show_game_name": True,
                "show_time_elapsed": True,
                "show_library_size": True
            },
            
            # Powiadomienia
            "notifications": {
                "enabled": True,
                "show_on_game_launch": True,
                "show_on_achievement": True,
                "show_on_music_change": False
            },
            
            # Wygląd
            "appearance": {
                "theme": "dark",
                "accent_color": COLOR_ACCENT,
                "font_size": FONT_SIZE_NORMAL,
                "show_thumbnails": True,
                "thumbnail_size": "medium"  # small, medium, large
            },
            
            # Gamepad
            "gamepad": {
                "enabled": True,
                "vibration": True,
                "deadzone": GAMEPAD_DEADZONE,
                "button_mapping": {}
            },
            
            # Serwer czatu
            "chat": {
                "enabled": False,
                "server_host": CHAT_SERVER_HOST,
                "server_port": CHAT_SERVER_PORT,
                "username": None,
                "servers_list": []
            },
            
            # Statystyki
            "stats": {
                "track_playtime": True,
                "track_launches": True,
                "show_in_discord": True
            },
            
            # Automatyczne funkcje
            "auto": {
                "save_enabled": True,
                "save_interval": AUTO_SAVE_INTERVAL,
                "backup_enabled": True,
                "check_updates": True
            },
            
            # Zaawansowane
            "advanced": {
                "debug_mode": False,
                "log_level": "INFO",
                "cache_enabled": True,
                "max_cache_size": MAX_CACHE_SIZE_MB,
                "use_hardware_acceleration": True
            },
            
            # System
            "system": {
                "minimize_to_tray": True,
                "start_with_windows": False,
                "close_to_tray": True,
                "language": DEFAULT_LANGUAGE
            },
            
            # Ostatnio używane
            "recent": {
                "last_game_id": None,
                "last_profile_id": None,
                "last_tab": "games",
                "recent_searches": []
            }
        }
    
    def load(self) -> bool:
        """
        Ładuje ustawienia z pliku JSON.
        Jeśli plik nie istnieje, używa domyślnych ustawień.
        
        Returns:
            True jeśli załadowano pomyślnie, False w przeciwnym razie
        """
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Merge z domyślnymi (na wypadek nowych ustawień)
                self._settings = self._merge_settings(self._default_settings, loaded_settings)
                logger.info(f"Załadowano ustawienia z: {self.settings_file}")
                return True
            else:
                logger.info("Plik ustawień nie istnieje, używam domyślnych")
                self._settings = self._default_settings.copy()
                self.save()  # Zapisz domyślne ustawienia
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON: {e}")
            self._settings = self._default_settings.copy()
            return False
            
        except Exception as e:
            logger.error(f"Błąd ładowania ustawień: {e}")
            self._settings = self._default_settings.copy()
            return False
    
    def save(self) -> bool:
        """
        Zapisuje aktualne ustawienia do pliku JSON.
        
        Returns:
            True jeśli zapisano pomyślnie, False w przeciwnym razie
        """
        try:
            # Utwórz katalog jeśli nie istnieje
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Zapisano ustawienia do: {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd zapisywania ustawień: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość ustawienia używając notacji z kropką (np. "music.volume").
        
        Args:
            key: Klucz ustawienia (może zawierać kropki)
            default: Wartość domyślna jeśli klucz nie istnieje
            
        Returns:
            Wartość ustawienia lub default
        """
        try:
            keys = key.split('.')
            value = self._settings
            
            for k in keys:
                value = value[k]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any, auto_save: bool = True) -> bool:
        """
        Ustawia wartość ustawienia używając notacji z kropką.
        
        Args:
            key: Klucz ustawienia (może zawierać kropki)
            value: Nowa wartość
            auto_save: Czy automatycznie zapisać po zmianie
            
        Returns:
            True jeśli ustawiono pomyślnie, False w przeciwnym razie
        """
        try:
            keys = key.split('.')
            current = self._settings
            
            # Przejdź do przedostatniego klucza
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Ustaw ostatni klucz
            current[keys[-1]] = value
            
            if auto_save:
                self.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd ustawiania wartości '{key}': {e}")
            return False
    
    def reset(self, section: Optional[str] = None) -> bool:
        """
        Resetuje ustawienia do domyślnych.
        
        Args:
            section: Nazwa sekcji do zresetowania (None = wszystko)
            
        Returns:
            True jeśli zresetowano pomyślnie
        """
        try:
            if section:
                if section in self._default_settings:
                    self._settings[section] = self._default_settings[section].copy()
                    logger.info(f"Zresetowano sekcję: {section}")
                else:
                    logger.warning(f"Nieznana sekcja: {section}")
                    return False
            else:
                self._settings = self._default_settings.copy()
                logger.info("Zresetowano wszystkie ustawienia")
            
            self.save()
            return True
            
        except Exception as e:
            logger.error(f"Błąd resetowania ustawień: {e}")
            return False
    
    def _merge_settings(self, defaults: Dict, loaded: Dict) -> Dict:
        """
        Łączy załadowane ustawienia z domyślnymi (dodaje brakujące klucze).
        
        Args:
            defaults: Domyślne ustawienia
            loaded: Załadowane ustawienia
            
        Returns:
            Połączone ustawienia
        """
        result = defaults.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def export_to_file(self, filepath: Path) -> bool:
        """
        Eksportuje ustawienia do pliku.
        
        Args:
            filepath: Ścieżka do pliku eksportu
            
        Returns:
            True jeśli wyeksportowano pomyślnie
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Wyeksportowano ustawienia do: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd eksportu ustawień: {e}")
            return False
    
    def import_from_file(self, filepath: Path) -> bool:
        """
        Importuje ustawienia z pliku.
        
        Args:
            filepath: Ścieżka do pliku importu
            
        Returns:
            True jeśli zaimportowano pomyślnie
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            
            self._settings = self._merge_settings(self._default_settings, imported)
            self.save()
            
            logger.info(f"Zaimportowano ustawienia z: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd importu ustawień: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Zwraca wszystkie ustawienia.
        
        Returns:
            Pełny słownik ustawień
        """
        return self._settings.copy()
    
    def __repr__(self) -> str:
        return f"Settings(file='{self.settings_file}')"
