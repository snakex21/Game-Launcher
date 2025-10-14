"""
Config Manager - Zarządzanie konfiguracją aplikacji
AI-Friendly: Centralne miejsce do odczytu/zapisu ustawień
"""

import json
from pathlib import Path
from utils.logger import get_logger
from utils.helpers import load_json, save_json, ensure_dir


class ConfigManager:
    """
    Zarządza konfiguracją aplikacji.
    
    AI Note: Użyj tej klasy do:
    - Odczytu ustawień: config.get('ui', 'theme')
    - Zapisu ustawień: config.set('ui', 'theme', 'dark')
    - Sprawdzania integracji: config.is_integration_enabled('discord')
    """
    
    def __init__(self, config_path="config.json"):
        """
        Inicjalizuje ConfigManager.
        
        Args:
            config_path (str): Ścieżka do pliku konfiguracji
        """
        self.logger = get_logger()
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._ensure_required_paths()
    
    def _load_config(self):
        """
        Ładuje konfigurację z pliku.
        
        Returns:
            dict: Załadowana konfiguracja lub domyślna
        
        AI Note: Automatycznie tworzy domyślną konfigurację jeśli nie istnieje
        """
        if not self.config_path.exists():
            self.logger.warning(f"Config file not found: {self.config_path}")
            return self._create_default_config()
        
        config = load_json(self.config_path)
        
        if not config:
            self.logger.error("Failed to load config, using defaults")
            return self._create_default_config()
        
        self.logger.info("Configuration loaded successfully")
        return config
    
    def _create_default_config(self):
        """
        Tworzy domyślną konfigurację.
        
        Returns:
            dict: Domyślna konfiguracja
        
        AI Note: Możesz dodać nowe sekcje tutaj
        """
        default_config = {
            "app": {
                "version": "1.0.0",
                "theme": "dark",
                "language": "pl"
            },
            "paths": {
                "database": "data/games.db",
                "covers": "assets/covers",
                "icons": "assets/icons",
                "screenshots": "data/screenshots"
            },
            "integrations": {
                "discord": {"enabled": False, "client_id": ""},
                "lastfm": {"enabled": False, "api_key": "", "api_secret": "", "username": ""},
                "rawg": {"enabled": False, "api_key": ""},
                "github": {"enabled": False, "token": "", "repo": ""}
            },
            "features": {
                "music_player": {"enabled": True, "volume": 0.5, "shuffle": False},
                "chat_server": {"enabled": False, "port": 5000},
                "rss_feeds": ["https://www.ign.com/feed.xml"]
            },
            "ui": {
                "window_size": "1200x800",
                "grid_columns": 3,
                "chart_color": "#3498db"
            }
        }
        
        # Zapisz domyślną konfigurację
        save_json(self.config_path, default_config)
        self.logger.info("Created default configuration file")
        
        return default_config
    
    def _ensure_required_paths(self):
        """
        Upewnia się że wymagane foldery istnieją.
        
        AI Note: Automatycznie tworzy foldery przy starcie
        """
        paths = self.config.get('paths', {})
        for key, path in paths.items():
            if key != 'database':  # Nie twórz pliku bazy, tylko folder
                ensure_dir(path)
                self.logger.debug(f"Ensured path exists: {path}")
    
    def get(self, *keys, default=None):
        """
        Pobiera wartość z konfiguracji używając ścieżki kluczy.
        
        Args:
            *keys: Klucze zagnieżdżone (np. 'ui', 'theme')
            default: Wartość domyślna jeśli klucz nie istnieje
        
        Returns:
            any: Wartość z konfiguracji lub default
        
        Examples:
            >>> config.get('ui', 'theme')
            'dark'
            >>> config.get('ui', 'nonexistent', default='light')
            'light'
        
        AI Note: Bezpieczne pobieranie - nie crashuje przy braku klucza
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, *keys, value):
        """
        Ustawia wartość w konfiguracji.
        
        Args:
            *keys: Klucze zagnieżdżone (ostatni to nazwa, reszta to ścieżka)
            value: Nowa wartość
        
        Returns:
            bool: True jeśli sukces
        
        Examples:
            >>> config.set('ui', 'theme', value='light')
            >>> config.set('integrations', 'discord', 'enabled', value=True)
        
        AI Note: Automatycznie zapisuje do pliku
        """
        if len(keys) < 1:
            self.logger.error("set() requires at least one key")
            return False
        
        # Nawiguj do odpowiedniego miejsca w słowniku
        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Ustaw wartość
        current[keys[-1]] = value
        
        # Zapisz
        return self.save()
    
    def save(self):
        """
        Zapisuje konfigurację do pliku.
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Wywołaj po zmianach żeby zapisać na dysku
        """
        if save_json(self.config_path, self.config):
            self.logger.info("Configuration saved successfully")
            return True
        else:
            self.logger.error("Failed to save configuration")
            return False
    
    def is_integration_enabled(self, integration_name):
        """
        Sprawdza czy integracja jest włączona.
        
        Args:
            integration_name (str): Nazwa integracji (discord, lastfm, rawg, github)
        
        Returns:
            bool: True jeśli włączona
        
        AI Note: Użyj przed inicjalizacją integracji
        """
        return self.get('integrations', integration_name, 'enabled', default=False)
    
    def get_database_path(self):
        """
        Zwraca ścieżkę do pliku bazy danych.
        
        Returns:
            str: Ścieżka do bazy danych
        """
        return self.get('paths', 'database', default='data/games.db')
    
    def get_integration_config(self, integration_name):
        """
        Pobiera pełną konfigurację integracji.
        
        Args:
            integration_name (str): Nazwa integracji
        
        Returns:
            dict: Konfiguracja integracji lub {}
        
        AI Note: Użyj do inicjalizacji API (np. Discord, Last.fm)
        """
        return self.get('integrations', integration_name, default={})
    
    def reload(self):
        """
        Przeładowuje konfigurację z pliku.
        
        AI Note: Użyj jeśli config.json został zmieniony ręcznie
        """
        self.config = self._load_config()
        self.logger.info("Configuration reloaded")