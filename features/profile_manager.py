"""
Menedżer profili gier
Zarządza różnymi profilami uruchamiania dla gier (mody, ustawienia, saves).
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProfileManager:
    """Klasa zarządzająca profilami uruchamiania gier."""
    
    def __init__(self, launcher_instance=None):
        self.launcher = launcher_instance
        self.profiles: Dict[str, List[Dict]] = {}  # {game_id: [profiles]}
        logger.debug("ProfileManager zainicjalizowany")
    
    def add_profile(self, game_id: str, profile_data: Dict[str, Any]) -> Optional[str]:
        """
        Dodaje nowy profil dla gry.
        
        Args:
            game_id: ID gry
            profile_data: Dane profilu (name, arguments, mods, etc.)
            
        Returns:
            ID utworzonego profilu
        """
        try:
            profile_id = str(uuid.uuid4())
            
            profile = {
                'id': profile_id,
                'name': profile_data.get('name', 'Nowy profil'),
                'description': profile_data.get('description', ''),
                'arguments': profile_data.get('arguments', ''),
                'working_dir': profile_data.get('working_dir', ''),
                'mods': profile_data.get('mods', []),
                'config_files': profile_data.get('config_files', {}),
                'is_default': profile_data.get('is_default', False)
            }
            
            if game_id not in self.profiles:
                self.profiles[game_id] = []
            
            # Jeśli to domyślny profil, odznacz inne
            if profile['is_default']:
                for p in self.profiles[game_id]:
                    p['is_default'] = False
            
            self.profiles[game_id].append(profile)
            
            logger.info(f"Dodano profil: {profile['name']} dla gry {game_id}")
            return profile_id
            
        except Exception as e:
            logger.error(f"Błąd dodawania profilu: {e}")
            return None
    
    def remove_profile(self, game_id: str, profile_id: str) -> bool:
        """Usuwa profil."""
        try:
            if game_id not in self.profiles:
                return False
            
            self.profiles[game_id] = [
                p for p in self.profiles[game_id]
                if p['id'] != profile_id
            ]
            
            logger.info(f"Usunięto profil {profile_id} dla gry {game_id}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd usuwania profilu: {e}")
            return False
    
    def get_profiles_for_game(self, game_id: str) -> List[Dict[str, Any]]:
        """Zwraca wszystkie profile dla gry."""
        return self.profiles.get(game_id, [])
    
    def get_default_profile(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Zwraca domyślny profil dla gry."""
        profiles = self.get_profiles_for_game(game_id)
        
        for profile in profiles:
            if profile.get('is_default', False):
                return profile
        
        # Jeśli nie ma domyślnego, zwróć pierwszy
        return profiles[0] if profiles else None
    
    def apply_profile(self, game_id: str, profile_id: str) -> bool:
        """
        Aplikuje profil przed uruchomieniem gry.
        
        Args:
            game_id: ID gry
            profile_id: ID profilu
            
        Returns:
            True jeśli zastosowano pomyślnie
        """
        # TODO: Implementacja kopiowania plików konfiguracyjnych, włączania modów, etc.
        logger.debug(f"Aplikowanie profilu {profile_id} dla gry {game_id}")
        return True
