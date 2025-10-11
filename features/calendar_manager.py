"""
Menedżer kalendarza
Zarządza wydarzeniami i terminami związanymi z grami.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from utils.file_utils import safe_json_load, safe_json_save
from config.constants import CALENDAR_EVENTS_FILE

logger = logging.getLogger(__name__)


class CalendarManager:
    """Klasa zarządzająca kalendarzem wydarzeń."""
    
    def __init__(self, launcher_instance=None):
        self.launcher = launcher_instance
        self.events_file = Path(CALENDAR_EVENTS_FILE)
        self.events: List[Dict[str, Any]] = []
        
        self.load_events()
        logger.debug("CalendarManager zainicjalizowany")
    
    def load_events(self) -> bool:
        """Ładuje wydarzenia z pliku."""
        try:
            self.events = safe_json_load(self.events_file, default=[])
            logger.info(f"Załadowano {len(self.events)} wydarzeń")
            return True
        except Exception as e:
            logger.error(f"Błąd ładowania wydarzeń: {e}")
            return False
    
    def save_events(self) -> bool:
        """Zapisuje wydarzenia do pliku."""
        try:
            return safe_json_save(self.events_file, self.events)
        except Exception as e:
            logger.error(f"Błąd zapisywania wydarzeń: {e}")
            return False
    
    def add_event(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Dodaje nowe wydarzenie."""
        try:
            event_id = str(uuid.uuid4())
            
            event = {
                'id': event_id,
                'title': event_data.get('title', 'Nowe wydarzenie'),
                'description': event_data.get('description', ''),
                'date': event_data.get('date', datetime.now().isoformat()),
                'game_id': event_data.get('game_id'),
                'type': event_data.get('type', 'generic'),  # release, tournament, update, etc.
                'reminder': event_data.get('reminder', False),
                'completed': False
            }
            
            self.events.append(event)
            self.save_events()
            
            logger.info(f"Dodano wydarzenie: {event['title']}")
            return event_id
            
        except Exception as e:
            logger.error(f"Błąd dodawania wydarzenia: {e}")
            return None
    
    def remove_event(self, event_id: str) -> bool:
        """Usuwa wydarzenie."""
        try:
            self.events = [e for e in self.events if e['id'] != event_id]
            self.save_events()
            return True
        except Exception as e:
            logger.error(f"Błąd usuwania wydarzenia: {e}")
            return False
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Zwraca nadchodzące wydarzenia."""
        # TODO: Implementacja filtrowania po dacie
        return self.events
    
    def get_events_for_game(self, game_id: str) -> List[Dict[str, Any]]:
        """Zwraca wydarzenia dla konkretnej gry."""
        return [e for e in self.events if e.get('game_id') == game_id]
