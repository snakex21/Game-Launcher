"""
Game Tracker - Automatyczne śledzenie czasu gry
AI-Friendly: Monitoruje procesy i zapisuje sesje
"""

import threading
import time
from datetime import datetime
from utils.logger import get_logger
from utils.helpers import is_process_running, get_process_by_name


class GameTracker:
    """
    Śledzi czas gry w tle.
    
    AI Note:
    - Sprawdza czy proces gry działa
    - Automatycznie startuje/kończy sesje
    - Thread-safe tracking w tle
    """
    
    def __init__(self, database):
        """
        Inicjalizuje tracker.
        
        Args:
            database (Database): Obiekt bazy danych
        """
        self.db = database
        self.logger = get_logger()
        
        # Aktywne sesje {game_id: {'session_id': int, 'start_time': float, 'process_name': str}}
        self.active_sessions = {}
        
        # Thread tracking
        self.tracking_thread = None
        self.is_tracking = False
        self.check_interval = 5  # Sprawdzaj co 5 sekund
    
    def start_tracking(self):
        """
        Startuje wątek trackingu.
        
        AI Note: Wywołaj przy starcie aplikacji
        """
        if self.is_tracking:
            self.logger.warning("Tracking already running")
            return
        
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        self.logger.info("Game tracking started")
    
    def stop_tracking(self):
        """
        Zatrzymuje tracking i kończy wszystkie sesje.
        
        AI Note: Wywołaj przy zamykaniu aplikacji
        """
        self.is_tracking = False
        
        # Zakończ wszystkie aktywne sesje
        for game_id in list(self.active_sessions.keys()):
            self._end_session(game_id)
        
        if self.tracking_thread:
            self.tracking_thread.join(timeout=2)
        
        self.logger.info("Game tracking stopped")
    
    def register_game(self, game_id, process_name):
        """
        Rejestruje grę do trackingu.
        
        Args:
            game_id (int): ID gry w bazie
            process_name (str): Nazwa procesu (np. "game.exe")
        
        AI Note: Wywołaj po uruchomieniu gry z launchera
        """
        if game_id in self.active_sessions:
            self.logger.warning(f"Game {game_id} already being tracked")
            return
        
        # Sprawdź czy proces już działa
        if is_process_running(process_name):
            self._start_session(game_id, process_name)
            self.logger.info(f"Started tracking game {game_id} ({process_name})")
        else:
            self.logger.warning(f"Process {process_name} not found, will wait for it")
    
    def unregister_game(self, game_id):
        """
        Wyrejestrowuje grę z trackingu.
        
        Args:
            game_id (int): ID gry
        
        AI Note: Opcjonalne - tracking sam wykryje zamknięcie
        """
        if game_id in self.active_sessions:
            self._end_session(game_id)
            self.logger.info(f"Unregistered game {game_id}")
    
    def _tracking_loop(self):
        """
        Główna pętla trackingu (działa w tle).
        
        AI Note: Automatycznie wykrywa start/stop procesów
        """
        self.logger.info("Tracking loop started")
        
        while self.is_tracking:
            try:
                # Sprawdź wszystkie aktywne sesje
                for game_id in list(self.active_sessions.keys()):
                    session_data = self.active_sessions[game_id]
                    process_name = session_data['process_name']
                    
                    # Sprawdź czy proces jeszcze działa
                    if not is_process_running(process_name):
                        self._end_session(game_id)
                        self.logger.info(f"Game {game_id} process ended")
                
                # TODO: Opcjonalnie - automatyczne wykrywanie nowych procesów gier
                # Można dodać monitoring wszystkich gier z bazy
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in tracking loop: {e}")
                time.sleep(self.check_interval)
        
        self.logger.info("Tracking loop ended")
    
    def _start_session(self, game_id, process_name):
        """
        Rozpoczyna sesję gry.
        
        Args:
            game_id (int): ID gry
            process_name (str): Nazwa procesu
        """
        # Start sesji w bazie
        session_id = self.db.start_play_session(game_id)
        
        if session_id:
            self.active_sessions[game_id] = {
                'session_id': session_id,
                'start_time': time.time(),
                'process_name': process_name
            }
            self.logger.info(f"Started session {session_id} for game {game_id}")
    
    def _end_session(self, game_id):
        """
        Kończy sesję gry.
        
        Args:
            game_id (int): ID gry
        """
        if game_id not in self.active_sessions:
            return
        
        session_data = self.active_sessions[game_id]
        session_id = session_data['session_id']
        start_time = session_data['start_time']
        
        # Oblicz czas trwania
        duration = int(time.time() - start_time)
        
        # Zakończ sesję w bazie
        self.db.end_play_session(session_id, duration)
        
        # Usuń z aktywnych
        del self.active_sessions[game_id]
        
        self.logger.info(f"Ended session {session_id} for game {game_id}, duration: {duration}s")
    
    def get_active_sessions(self):
        """
        Zwraca aktywne sesje.
        
        Returns:
            dict: Słownik aktywnych sesji
        
        AI Note: Użyj do wyświetlania "teraz grasz w..."
        """
        return self.active_sessions.copy()
    
    def is_game_running(self, game_id):
        """
        Sprawdza czy gra jest aktualnie uruchomiona.
        
        Args:
            game_id (int): ID gry
        
        Returns:
            bool: True jeśli gra działa
        """
        return game_id in self.active_sessions