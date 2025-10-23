"""Śledzenie aktywnych sesji gier."""
from __future__ import annotations

import logging
import os
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import psutil

if TYPE_CHECKING:
    from app.services.game_service import Game

logger = logging.getLogger(__name__)


@dataclass
class ActiveSession:
    game_id: str
    game_name: str
    pid: Optional[int]
    start_time: float
    exe_path: Optional[str] = None
    process_name: Optional[str] = None


class SessionTracker:
    def __init__(self, game_service, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.game_service = game_service
        self.event_bus = event_bus
        self.active_sessions: dict[str, ActiveSession] = {}
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False

    def start_monitoring(self) -> None:
        """Uruchamia wątek monitorujący aktywne sesje."""
        if not self.running:
            self.running = True
            self.monitoring_thread = threading.Thread(target=self._monitor_sessions, daemon=True)
            self.monitoring_thread.start()
            logger.info("Uruchomiono monitoring sesji gier")

    def stop_monitoring(self) -> None:
        """Zatrzymuje wątek monitorujący."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
            logger.info("Zatrzymano monitoring sesji gier")

    def _monitor_sessions(self) -> None:
        """Wątek monitorujący - sprawdza czy gry nadal działają."""
        while self.running:
            try:
                self.check_running_sessions()
            except Exception:
                logger.exception("Błąd podczas monitorowania sesji")
            time.sleep(2)

    def start_session(self, game: "Game", pid: Optional[int] = None) -> None:
        """Rozpoczyna nową sesję gry."""
        exe_path = game.exe_path
        process_name = os.path.basename(exe_path).lower() if exe_path else None
        
        session = ActiveSession(
            game_id=game.id,
            game_name=game.name,
            pid=pid,
            start_time=time.time(),
            exe_path=exe_path,
            process_name=process_name
        )
        self.active_sessions[game.id] = session
        logger.info("Rozpoczęto sesję dla gry %s (PID: %s)", game.name, pid)
        self.event_bus.emit("session_started", game_id=game.id, game_name=game.name)

    def end_session(self, game_id: str, ask_completion: bool = True) -> None:
        """Kończy sesję gry."""
        session = self.active_sessions.pop(game_id, None)
        if session:
            duration_seconds = time.time() - session.start_time
            duration_minutes = int(duration_seconds // 60)
            
            self.game_service.log_session(game_id, duration_minutes)
            logger.info("Zakończono sesję dla gry %s (czas: %d min)", session.game_name, duration_minutes)
            self.event_bus.emit("session_ended", 
                              game_id=game_id, 
                              game_name=session.game_name,
                              duration=duration_minutes,
                              ask_completion=ask_completion)

    def stop_game(self, game_id: str) -> bool:
        """Zatrzymuje uruchomioną grę."""
        session = self.active_sessions.get(game_id)
        if not session:
            logger.warning("Próba zatrzymania gry %s, która nie jest uruchomiona", game_id)
            return False

        try:
            killed = False
            # Znajdź i zabij proces
            if session.pid and psutil.pid_exists(session.pid):
                try:
                    proc = psutil.Process(session.pid)
                    # Zabij dzieci
                    for child in proc.children(recursive=True):
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    # Zabij proces główny
                    proc.kill()
                    killed = True
                    logger.info("Zabito proces %s (PID: %d)", session.game_name, session.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning("Nie udało się zabić procesu (PID: %d): %s", session.pid, e)
            
            # Jeśli nie udało się przez PID, spróbuj przez nazwę
            if not killed and session.process_name:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                        if proc_name == session.process_name:
                            parent = psutil.Process(proc.info['pid'])
                            for child in parent.children(recursive=True):
                                try:
                                    child.kill()
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                            parent.kill()
                            killed = True
                            logger.info("Zabito proces %s przez nazwę", session.game_name)
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Zakończ sesję
            self.end_session(game_id, ask_completion=True)
            return True
            
        except Exception:
            logger.exception("Błąd podczas zatrzymywania gry %s", game_id)
            return False

    def check_running_sessions(self) -> None:
        """Sprawdza czy aktywne sesje nadal działają."""
        for game_id, session in list(self.active_sessions.items()):
            is_running = False
            
            # Sprawdź przez PID
            if session.pid and psutil.pid_exists(session.pid):
                is_running = True
            # Sprawdź przez nazwę procesu
            elif session.process_name:
                for proc in psutil.process_iter(['name']):
                    try:
                        proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                        if proc_name == session.process_name:
                            is_running = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            if not is_running:
                self.end_session(game_id, ask_completion=True)

    def get_active_session(self, game_id: str) -> ActiveSession | None:
        return self.active_sessions.get(game_id)

    def is_game_running(self, game_id: str) -> bool:
        return game_id in self.active_sessions
    
    def get_session_duration(self, game_id: str) -> int:
        """Zwraca czas trwania sesji w sekundach."""
        session = self.active_sessions.get(game_id)
        if session:
            return int(time.time() - session.start_time)
        return 0
