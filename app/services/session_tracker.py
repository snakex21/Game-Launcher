"""Śledzenie aktywnych sesji gier."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from app.services.game_service import Game

logger = logging.getLogger(__name__)


@dataclass
class ActiveSession:
    game_id: str
    game_name: str
    pid: int
    start_time: float


class SessionTracker:
    def __init__(self, game_service, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.game_service = game_service
        self.event_bus = event_bus
        self.active_sessions: dict[str, ActiveSession] = {}

    def start_session(self, game: "Game", pid: int) -> None:
        session = ActiveSession(
            game_id=game.id,
            game_name=game.name,
            pid=pid,
            start_time=time.time()
        )
        self.active_sessions[game.id] = session
        logger.info("Rozpoczęto sesję dla gry %s (PID: %d)", game.name, pid)
        self.event_bus.emit("session_started", game_id=game.id)

    def end_session(self, game_id: str) -> None:
        session = self.active_sessions.pop(game_id, None)
        if session:
            duration_seconds = time.time() - session.start_time
            duration_minutes = int(duration_seconds // 60)
            
            self.game_service.log_session(game_id, duration_minutes)
            logger.info("Zakończono sesję dla gry %s (czas: %d min)", session.game_name, duration_minutes)
            self.event_bus.emit("session_ended", game_id=game_id, duration=duration_minutes)

    def check_running_sessions(self) -> None:
        for game_id, session in list(self.active_sessions.items()):
            if not psutil.pid_exists(session.pid):
                self.end_session(game_id)

    def get_active_session(self, game_id: str) -> ActiveSession | None:
        return self.active_sessions.get(game_id)

    def is_game_running(self, game_id: str) -> bool:
        return game_id in self.active_sessions
