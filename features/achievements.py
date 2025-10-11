"""
Menedżer osiągnięć
Zarządza systemem osiągnięć w grach.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from utils.file_utils import safe_json_load, safe_json_save
from config.constants import ACHIEVEMENTS_FILE

logger = logging.getLogger(__name__)


class AchievementsManager:
    """
    Klasa zarządzająca osiągnięciami w grach.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje menedżer osiągnięć.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.achievements_file = Path(ACHIEVEMENTS_FILE)
        self.achievements: Dict[str, List[Dict]] = {}  # {game_id: [achievements]}
        
        self.load_achievements()
        logger.debug("AchievementsManager zainicjalizowany")
    
    def load_achievements(self) -> bool:
        """Ładuje osiągnięcia z pliku."""
        try:
            self.achievements = safe_json_load(self.achievements_file, default={})
            logger.info(f"Załadowano osiągnięcia dla {len(self.achievements)} gier")
            return True
        except Exception as e:
            logger.error(f"Błąd ładowania osiągnięć: {e}")
            return False
    
    def save_achievements(self) -> bool:
        """Zapisuje osiągnięcia do pliku."""
        try:
            return safe_json_save(self.achievements_file, self.achievements)
        except Exception as e:
            logger.error(f"Błąd zapisywania osiągnięć: {e}")
            return False
    
    def add_achievement(self, game_id: str, achievement_data: Dict[str, Any]) -> Optional[str]:
        """Dodaje nowe osiągnięcie do gry."""
        try:
            achievement_id = str(uuid.uuid4())
            
            achievement = {
                'id': achievement_id,
                'name': achievement_data.get('name', 'Nowe osiągnięcie'),
                'description': achievement_data.get('description', ''),
                'icon': achievement_data.get('icon', ''),
                'unlocked': False,
                'unlock_date': None,
                'hidden': achievement_data.get('hidden', False),
                'points': achievement_data.get('points', 0)
            }
            
            if game_id not in self.achievements:
                self.achievements[game_id] = []
            
            self.achievements[game_id].append(achievement)
            self.save_achievements()
            
            logger.info(f"Dodano osiągnięcie: {achievement['name']} dla gry {game_id}")
            return achievement_id
            
        except Exception as e:
            logger.error(f"Błąd dodawania osiągnięcia: {e}")
            return None
    
    def unlock_achievement(self, game_id: str, achievement_id: str) -> bool:
        """Odblokowuje osiągnięcie."""
        try:
            if game_id not in self.achievements:
                return False
            
            for achievement in self.achievements[game_id]:
                if achievement['id'] == achievement_id:
                    achievement['unlocked'] = True
                    achievement['unlock_date'] = datetime.now().isoformat()
                    self.save_achievements()
                    
                    # Powiadomienie
                    logger.info(f"Odblokowano osiągnięcie: {achievement['name']}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd odblokowywania osiągnięcia: {e}")
            return False
    
    def get_achievements_for_game(self, game_id: str) -> List[Dict[str, Any]]:
        """Zwraca wszystkie osiągnięcia dla gry."""
        return self.achievements.get(game_id, [])
    
    def get_achievement_progress(self, game_id: str) -> Dict[str, Any]:
        """Zwraca postęp osiągnięć dla gry."""
        achievements = self.get_achievements_for_game(game_id)
        
        if not achievements:
            return {'total': 0, 'unlocked': 0, 'percentage': 0}
        
        unlocked = sum(1 for a in achievements if a.get('unlocked', False))
        
        return {
            'total': len(achievements),
            'unlocked': unlocked,
            'percentage': (unlocked / len(achievements)) * 100 if achievements else 0
        }
