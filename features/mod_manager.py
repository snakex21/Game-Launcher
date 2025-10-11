"""
Menedżer modów
Zarządza modyfikacjami dla gier.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.file_utils import safe_json_load, safe_json_save
from config.constants import MOD_MANAGER_FILE

logger = logging.getLogger(__name__)


class ModManager:
    """Klasa zarządzająca modami dla gier."""
    
    def __init__(self, launcher_instance=None):
        self.launcher = launcher_instance
        self.config_file = Path(MOD_MANAGER_FILE)
        self.mods: Dict[str, List[Dict]] = {}  # {game_id: [mods]}
        
        self.load_mods()
        logger.debug("ModManager zainicjalizowany")
    
    def load_mods(self) -> bool:
        """Ładuje konfigurację modów."""
        try:
            self.mods = safe_json_load(self.config_file, default={})
            logger.info(f"Załadowano mody dla {len(self.mods)} gier")
            return True
        except Exception as e:
            logger.error(f"Błąd ładowania modów: {e}")
            return False
    
    def save_mods(self) -> bool:
        """Zapisuje konfigurację modów."""
        try:
            return safe_json_save(self.config_file, self.mods)
        except Exception as e:
            logger.error(f"Błąd zapisywania modów: {e}")
            return False
    
    def add_mod(self, game_id: str, mod_data: Dict[str, Any]) -> Optional[str]:
        """
        Dodaje nowy mod dla gry.
        
        Args:
            game_id: ID gry
            mod_data: Dane moda (name, path, enabled, etc.)
            
        Returns:
            ID utworzonego moda
        """
        try:
            mod_id = str(uuid.uuid4())
            
            mod = {
                'id': mod_id,
                'name': mod_data.get('name', 'Nowy mod'),
                'description': mod_data.get('description', ''),
                'version': mod_data.get('version', '1.0'),
                'author': mod_data.get('author', 'Nieznany'),
                'path': mod_data.get('path', ''),
                'enabled': mod_data.get('enabled', True),
                'load_order': mod_data.get('load_order', 0),
                'conflicts': mod_data.get('conflicts', []),
                'dependencies': mod_data.get('dependencies', [])
            }
            
            if game_id not in self.mods:
                self.mods[game_id] = []
            
            self.mods[game_id].append(mod)
            self.save_mods()
            
            logger.info(f"Dodano mod: {mod['name']} dla gry {game_id}")
            return mod_id
            
        except Exception as e:
            logger.error(f"Błąd dodawania moda: {e}")
            return None
    
    def remove_mod(self, game_id: str, mod_id: str) -> bool:
        """Usuwa mod."""
        try:
            if game_id not in self.mods:
                return False
            
            self.mods[game_id] = [
                m for m in self.mods[game_id]
                if m['id'] != mod_id
            ]
            
            self.save_mods()
            logger.info(f"Usunięto mod {mod_id} dla gry {game_id}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd usuwania moda: {e}")
            return False
    
    def toggle_mod(self, game_id: str, mod_id: str) -> bool:
        """Włącza/wyłącza mod."""
        try:
            if game_id not in self.mods:
                return False
            
            for mod in self.mods[game_id]:
                if mod['id'] == mod_id:
                    mod['enabled'] = not mod.get('enabled', True)
                    self.save_mods()
                    
                    status = "włączony" if mod['enabled'] else "wyłączony"
                    logger.info(f"Mod {mod['name']} {status}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd przełączania moda: {e}")
            return False
    
    def get_mods_for_game(self, game_id: str, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Zwraca listę modów dla gry.
        
        Args:
            game_id: ID gry
            enabled_only: Czy tylko włączone mody
            
        Returns:
            Lista modów
        """
        mods = self.mods.get(game_id, [])
        
        if enabled_only:
            mods = [m for m in mods if m.get('enabled', True)]
        
        # Sortuj według load_order
        mods.sort(key=lambda m: m.get('load_order', 0))
        
        return mods
    
    def check_conflicts(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Sprawdza konflikty między modami.
        
        Args:
            game_id: ID gry
            
        Returns:
            Lista konfliktów
        """
        # TODO: Implementacja wykrywania konfliktów
        conflicts = []
        
        enabled_mods = self.get_mods_for_game(game_id, enabled_only=True)
        
        for mod in enabled_mods:
            conflict_ids = mod.get('conflicts', [])
            
            for other_mod in enabled_mods:
                if other_mod['id'] in conflict_ids:
                    conflicts.append({
                        'mod1': mod['name'],
                        'mod2': other_mod['name'],
                        'severity': 'warning'
                    })
        
        return conflicts
    
    def update_load_order(self, game_id: str, mod_id: str, new_order: int) -> bool:
        """Aktualizuje kolejność ładowania moda."""
        try:
            if game_id not in self.mods:
                return False
            
            for mod in self.mods[game_id]:
                if mod['id'] == mod_id:
                    mod['load_order'] = new_order
                    self.save_mods()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji kolejności: {e}")
            return False
