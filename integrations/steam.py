"""
Integracja Steam
Wykrywanie zainstalowanych gier Steam i odczyt danych.
"""

import os
import logging
import winreg
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


class SteamIntegration:
    """
    Klasa do integracji z Steam.
    Wykrywa zainstalowane gry i pobiera podstawowe informacje.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje integrację Steam.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.steam_path: Optional[Path] = None
        self.library_folders: List[Path] = []
        
        # Wykryj Steam
        self._detect_steam()
        
        logger.debug("SteamIntegration zainicjalizowany")
    
    def _detect_steam(self) -> bool:
        """
        Wykrywa instalację Steam w systemie.
        
        Returns:
            True jeśli znaleziono Steam
        """
        try:
            # Sprawdź rejestr Windows
            if os.name == 'nt':  # Windows
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Valve\Steam"
                    )
                    steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                    winreg.CloseKey(key)
                    
                    self.steam_path = Path(steam_path)
                    
                    if self.steam_path.exists():
                        logger.info(f"Znaleziono Steam: {self.steam_path}")
                        self._find_library_folders()
                        return True
                    
                except WindowsError:
                    logger.warning("Nie znaleziono Steam w rejestrze")
            
            # Sprawdź domyślne lokalizacje
            default_paths = [
                Path("C:/Program Files (x86)/Steam"),
                Path("C:/Program Files/Steam"),
                Path.home() / ".steam" / "steam",  # Linux
                Path.home() / "Library/Application Support/Steam"  # macOS
            ]
            
            for path in default_paths:
                if path.exists():
                    self.steam_path = path
                    logger.info(f"Znaleziono Steam: {self.steam_path}")
                    self._find_library_folders()
                    return True
            
            logger.warning("Nie znaleziono instalacji Steam")
            return False
            
        except Exception as e:
            logger.error(f"Błąd wykrywania Steam: {e}")
            return False
    
    def _find_library_folders(self):
        """Znajduje wszystkie foldery bibliotek Steam."""
        try:
            if not self.steam_path:
                return
            
            # Główny folder biblioteki
            main_library = self.steam_path / "steamapps"
            if main_library.exists():
                self.library_folders.append(main_library)
            
            # Dodatkowe foldery z libraryfolders.vdf
            vdf_path = main_library / "libraryfolders.vdf"
            
            if vdf_path.exists():
                with open(vdf_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Prosta parsowanie VDF (nie idealne, ale wystarczające)
                    import re
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    
                    for path_str in paths:
                        lib_path = Path(path_str) / "steamapps"
                        if lib_path.exists() and lib_path not in self.library_folders:
                            self.library_folders.append(lib_path)
            
            logger.info(f"Znaleziono {len(self.library_folders)} folderów bibliotek Steam")
            
        except Exception as e:
            logger.error(f"Błąd znajdowania folderów bibliotek: {e}")
    
    def get_installed_games(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę zainstalowanych gier Steam.
        
        Returns:
            Lista słowników z informacjami o grach
        """
        games = []
        
        try:
            for library_folder in self.library_folders:
                # Szukaj plików .acf (manifest gier)
                acf_files = library_folder.glob("appmanifest_*.acf")
                
                for acf_file in acf_files:
                    game_info = self._parse_acf_file(acf_file)
                    if game_info:
                        games.append(game_info)
            
            logger.info(f"Znaleziono {len(games)} zainstalowanych gier Steam")
            return games
            
        except Exception as e:
            logger.error(f"Błąd pobierania listy gier Steam: {e}")
            return []
    
    def _parse_acf_file(self, acf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parsuje plik .acf z manifestem gry.
        
        Args:
            acf_path: Ścieżka do pliku .acf
            
        Returns:
            Słownik z informacjami o grze lub None
        """
        try:
            with open(acf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Proste parsowanie (nie idealne, ale działa)
            import re
            
            appid = re.search(r'"appid"\s+"(\d+)"', content)
            name = re.search(r'"name"\s+"([^"]+)"', content)
            install_dir = re.search(r'"installdir"\s+"([^"]+)"', content)
            
            if not (appid and name):
                return None
            
            # Ścieżka do gry
            game_path = None
            if install_dir:
                game_dir = acf_path.parent / "common" / install_dir.group(1)
                if game_dir.exists():
                    game_path = str(game_dir)
            
            return {
                'appid': appid.group(1),
                'name': name.group(1),
                'install_dir': install_dir.group(1) if install_dir else None,
                'game_path': game_path,
                'library_folder': str(acf_path.parent)
            }
            
        except Exception as e:
            logger.error(f"Błąd parsowania {acf_path}: {e}")
            return None
    
    def get_game_executable(self, game_info: Dict[str, Any]) -> Optional[str]:
        """
        Próbuje znaleźć główny plik wykonywalny gry.
        
        Args:
            game_info: Informacje o grze z get_installed_games()
            
        Returns:
            Ścieżka do pliku .exe lub None
        """
        try:
            if not game_info.get('game_path'):
                return None
            
            game_path = Path(game_info['game_path'])
            
            # Szukaj plików .exe
            exe_files = list(game_path.glob("*.exe"))
            
            if not exe_files:
                # Szukaj w podfolderach
                exe_files = list(game_path.rglob("*.exe"))
            
            # Filtruj instalatory, updatery itp.
            excluded_keywords = ['setup', 'install', 'uninstall', 'update', 'crash', 'launcher']
            
            exe_files = [
                exe for exe in exe_files
                if not any(keyword in exe.name.lower() for keyword in excluded_keywords)
            ]
            
            if exe_files:
                # Zwróć pierwszy znaleziony
                return str(exe_files[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd znajdowania exe dla gry: {e}")
            return None
    
    def launch_game_via_steam(self, appid: str) -> bool:
        """
        Uruchamia grę przez Steam (steam://rungameid/).
        
        Args:
            appid: Steam App ID
            
        Returns:
            True jeśli uruchomiono
        """
        try:
            import webbrowser
            steam_url = f"steam://rungameid/{appid}"
            webbrowser.open(steam_url)
            
            logger.info(f"Uruchomiono grę Steam (App ID: {appid})")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania gry Steam: {e}")
            return False
    
    def is_steam_installed(self) -> bool:
        """
        Sprawdza czy Steam jest zainstalowany.
        
        Returns:
            True jeśli zainstalowany
        """
        return self.steam_path is not None and self.steam_path.exists()
    
    def get_steam_path(self) -> Optional[Path]:
        """
        Zwraca ścieżkę instalacji Steam.
        
        Returns:
            Path do Steam lub None
        """
        return self.steam_path
    
    def get_library_folders(self) -> List[Path]:
        """
        Zwraca listę folderów bibliotek Steam.
        
        Returns:
            Lista ścieżek do folderów
        """
        return self.library_folders.copy()
    
    def import_steam_games_to_launcher(self) -> int:
        """
        Importuje gry Steam do launchera.
        
        Returns:
            Liczba zaimportowanych gier
        """
        try:
            if not self.launcher or not hasattr(self.launcher, 'game_manager'):
                logger.error("Brak dostępu do game_manager")
                return 0
            
            steam_games = self.get_installed_games()
            imported = 0
            
            for game in steam_games:
                exe_path = self.get_game_executable(game)
                
                if exe_path:
                    game_data = {
                        'name': game['name'],
                        'exe_path': exe_path,
                        'working_dir': game.get('game_path', ''),
                        'tags': ['Steam'],
                        'notes': f"Steam App ID: {game['appid']}"
                    }
                    
                    if self.launcher.game_manager.add_game(game_data):
                        imported += 1
            
            logger.info(f"Zaimportowano {imported} gier Steam")
            return imported
            
        except Exception as e:
            logger.error(f"Błąd importu gier Steam: {e}")
            return 0
    
    def cleanup(self):
        """Czyści zasoby Steam integration."""
        logger.info("SteamIntegration oczyszczona")
