"""
Menedżer gier
Zarządza biblioteką gier, uruchamianiem i statystykami.
"""

import os
import json
import uuid
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.file_utils import safe_json_load, safe_json_save
from config.constants import CONFIG_FILE

logger = logging.getLogger(__name__)


class GameManager:
    """
    Klasa zarządzająca biblioteką gier.
    Obsługuje dodawanie, usuwanie, edycję i uruchamianie gier.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje menedżer gier.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.games: List[Dict[str, Any]] = []
        self.config_file = Path(CONFIG_FILE)
        
        # Załaduj gry
        self.load_games()
        
        logger.debug(f"GameManager zainicjalizowany, załadowano {len(self.games)} gier")
    
    def load_games(self) -> bool:
        """
        Ładuje listę gier z pliku JSON.
        
        Returns:
            True jeśli załadowano pomyślnie
        """
        try:
            data = safe_json_load(self.config_file, default={'games': []})
            self.games = data.get('games', [])
            
            logger.info(f"Załadowano {len(self.games)} gier z {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd ładowania gier: {e}")
            self.games = []
            return False
    
    def save_games(self) -> bool:
        """
        Zapisuje listę gier do pliku JSON.
        
        Returns:
            True jeśli zapisano pomyślnie
        """
        try:
            data = {'games': self.games}
            return safe_json_save(self.config_file, data)
            
        except Exception as e:
            logger.error(f"Błąd zapisywania gier: {e}")
            return False
    
    def add_game(self, game_data: Dict[str, Any]) -> Optional[str]:
        """
        Dodaje nową grę do biblioteki.
        
        Args:
            game_data: Słownik z danymi gry (name, exe_path, etc.)
            
        Returns:
            ID dodanej gry lub None w przypadku błędu
        """
        try:
            # Walidacja wymaganych pól
            if not game_data.get('name'):
                logger.error("Brak nazwy gry")
                return None
            
            if not game_data.get('exe_path'):
                logger.error("Brak ścieżki do pliku exe")
                return None
            
            # Sprawdź czy plik istnieje
            exe_path = Path(game_data['exe_path'])
            if not exe_path.exists():
                logger.warning(f"Plik exe nie istnieje: {exe_path}")
            
            # Utwórz nową grę
            game_id = str(uuid.uuid4())
            
            new_game = {
                'id': game_id,
                'name': game_data['name'],
                'exe_path': str(exe_path),
                'working_dir': game_data.get('working_dir', str(exe_path.parent)),
                'arguments': game_data.get('arguments', ''),
                'icon_path': game_data.get('icon_path', ''),
                'cover_image': game_data.get('cover_image', ''),
                'description': game_data.get('description', ''),
                'tags': game_data.get('tags', []),
                'favorite': game_data.get('favorite', False),
                'hidden': game_data.get('hidden', False),
                'added_date': datetime.now().isoformat(),
                'last_played': None,
                'total_playtime': 0,  # w sekundach
                'launch_count': 0,
                'notes': game_data.get('notes', '')
            }
            
            self.games.append(new_game)
            self.save_games()
            
            logger.info(f"Dodano grę: {new_game['name']} (ID: {game_id})")
            return game_id
            
        except Exception as e:
            logger.error(f"Błąd dodawania gry: {e}")
            return None
    
    def remove_game(self, game_id: str) -> bool:
        """
        Usuwa grę z biblioteki.
        
        Args:
            game_id: ID gry do usunięcia
            
        Returns:
            True jeśli usunięto pomyślnie
        """
        try:
            game = self.get_game_by_id(game_id)
            if not game:
                logger.warning(f"Gra o ID {game_id} nie została znaleziona")
                return False
            
            self.games = [g for g in self.games if g['id'] != game_id]
            self.save_games()
            
            logger.info(f"Usunięto grę: {game['name']} (ID: {game_id})")
            return True
            
        except Exception as e:
            logger.error(f"Błąd usuwania gry {game_id}: {e}")
            return False
    
    def update_game(self, game_id: str, game_data: Dict[str, Any]) -> bool:
        """
        Aktualizuje dane gry.
        
        Args:
            game_id: ID gry do aktualizacji
            game_data: Nowe dane gry
            
        Returns:
            True jeśli zaktualizowano pomyślnie
        """
        try:
            game = self.get_game_by_id(game_id)
            if not game:
                logger.warning(f"Gra o ID {game_id} nie została znaleziona")
                return False
            
            # Aktualizuj pola
            for key, value in game_data.items():
                if key != 'id':  # Nie zmieniaj ID
                    game[key] = value
            
            self.save_games()
            
            logger.info(f"Zaktualizowano grę: {game['name']} (ID: {game_id})")
            return True
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji gry {game_id}: {e}")
            return False
    
    def get_game_by_id(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera grę po ID.
        
        Args:
            game_id: ID gry
            
        Returns:
            Słownik z danymi gry lub None
        """
        for game in self.games:
            if game['id'] == game_id:
                return game
        return None
    
    def get_all_games(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie gry.
        
        Args:
            include_hidden: Czy uwzględnić ukryte gry
            
        Returns:
            Lista gier
        """
        if include_hidden:
            return self.games.copy()
        else:
            return [g for g in self.games if not g.get('hidden', False)]
    
    def search_games(self, query: str, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        Wyszukuje gry po nazwie.
        
        Args:
            query: Zapytanie wyszukiwania
            include_hidden: Czy uwzględnić ukryte gry
            
        Returns:
            Lista pasujących gier
        """
        query_lower = query.lower()
        games = self.get_all_games(include_hidden)
        
        return [
            g for g in games
            if query_lower in g['name'].lower() or
               query_lower in g.get('description', '').lower() or
               any(query_lower in tag.lower() for tag in g.get('tags', []))
        ]
    
    def filter_games(self, **filters) -> List[Dict[str, Any]]:
        """
        Filtruje gry według kryteriów.
        
        Args:
            **filters: Filtry (favorite=True, tags=['RPG'], etc.)
            
        Returns:
            Lista przefiltrowanych gier
        """
        filtered = self.games.copy()
        
        # Filtr ulubionych
        if 'favorite' in filters:
            filtered = [g for g in filtered if g.get('favorite') == filters['favorite']]
        
        # Filtr tagów
        if 'tags' in filters and filters['tags']:
            tag_list = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            filtered = [
                g for g in filtered
                if any(tag in g.get('tags', []) for tag in tag_list)
            ]
        
        # Filtr ukrytych
        if 'hidden' in filters:
            filtered = [g for g in filtered if g.get('hidden') == filters['hidden']]
        
        return filtered
    
    def launch_game(self, game_id: str, profile_id: Optional[str] = None) -> bool:
        """
        Uruchamia grę.
        
        Args:
            game_id: ID gry do uruchomienia
            profile_id: Opcjonalny ID profilu
            
        Returns:
            True jeśli uruchomiono pomyślnie
        """
        try:
            game = self.get_game_by_id(game_id)
            if not game:
                logger.error(f"Gra o ID {game_id} nie została znaleziona")
                return False
            
            exe_path = Path(game['exe_path'])
            if not exe_path.exists():
                logger.error(f"Plik exe nie istnieje: {exe_path}")
                return False
            
            # Katalog roboczy
            working_dir = game.get('working_dir', str(exe_path.parent))
            
            # Argumenty
            args = game.get('arguments', '')
            
            # TODO: Obsługa profili (jeśli profile_id podany)
            
            # Uruchom grę
            command = [str(exe_path)]
            if args:
                command.extend(args.split())
            
            subprocess.Popen(
                command,
                cwd=working_dir,
                shell=False
            )
            
            # Aktualizuj statystyki
            self._update_game_stats(game_id)
            
            # Powiadom launcher
            if self.launcher:
                self._notify_game_launched(game_id)
            
            logger.info(f"Uruchomiono grę: {game['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania gry {game_id}: {e}")
            return False
    
    def _update_game_stats(self, game_id: str):
        """
        Aktualizuje statystyki gry po uruchomieniu.
        
        Args:
            game_id: ID gry
        """
        try:
            game = self.get_game_by_id(game_id)
            if game:
                game['last_played'] = datetime.now().isoformat()
                game['launch_count'] = game.get('launch_count', 0) + 1
                self.save_games()
                
                logger.debug(f"Zaktualizowano statystyki gry: {game['name']}")
        except Exception as e:
            logger.error(f"Błąd aktualizacji statystyk gry {game_id}: {e}")
    
    def _notify_game_launched(self, game_id: str):
        """
        Powiadamia launcher o uruchomieniu gry.
        
        Args:
            game_id: ID gry
        """
        try:
            # Aktualizuj Discord RPC
            if hasattr(self.launcher, 'update_discord_presence'):
                game = self.get_game_by_id(game_id)
                if game:
                    self.launcher.update_discord_presence(
                        state="Gra w:",
                        details=game['name']
                    )
            
            # Pokaż powiadomienie
            # TODO: Implementacja powiadomień
            
        except Exception as e:
            logger.error(f"Błąd powiadamiania o uruchomieniu gry: {e}")
    
    def toggle_favorite(self, game_id: str) -> bool:
        """
        Przełącza status ulubionej gry.
        
        Args:
            game_id: ID gry
            
        Returns:
            Nowy status favorite
        """
        game = self.get_game_by_id(game_id)
        if game:
            game['favorite'] = not game.get('favorite', False)
            self.save_games()
            return game['favorite']
        return False
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę ulubionych gier.
        
        Returns:
            Lista ulubionych gier
        """
        return [g for g in self.games if g.get('favorite', False)]
    
    def get_recently_played(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Zwraca ostatnio grane gry.
        
        Args:
            limit: Maksymalna liczba gier
            
        Returns:
            Lista ostatnio granych gier
        """
        # Filtruj gry z last_played
        played_games = [g for g in self.games if g.get('last_played')]
        
        # Sortuj po dacie
        played_games.sort(
            key=lambda g: g.get('last_played', ''),
            reverse=True
        )
        
        return played_games[:limit]
    
    def get_most_played(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Zwraca najczęściej grane gry.
        
        Args:
            limit: Maksymalna liczba gier
            
        Returns:
            Lista najczęściej granych gier
        """
        # Sortuj po liczbie uruchomień
        sorted_games = sorted(
            self.games,
            key=lambda g: g.get('launch_count', 0),
            reverse=True
        )
        
        return sorted_games[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Zwraca ogólne statystyki biblioteki.
        
        Returns:
            Słownik ze statystykami
        """
        return {
            'total_games': len(self.games),
            'favorites': len([g for g in self.games if g.get('favorite', False)]),
            'hidden': len([g for g in self.games if g.get('hidden', False)]),
            'total_playtime': sum(g.get('total_playtime', 0) for g in self.games),
            'total_launches': sum(g.get('launch_count', 0) for g in self.games)
        }
