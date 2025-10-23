"""Obsługa biblioteki gier."""
from __future__ import annotations

import logging
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class Game:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Nieznana gra"
    exe_path: str = ""
    arguments: str = ""
    saves_path: str = ""
    tags: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    rating: float = 0.0
    play_time: int = 0
    completion: int = 0
    last_played: str = ""
    cover_image: str = ""
    notes: str = ""
    checklist: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    autoscan_screenshots: list[str] = field(default_factory=list)
    launch_profiles: list[dict[str, Any]] = field(default_factory=lambda: [{"name": "Default", "exe_path": None, "arguments": ""}])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "exe_path": self.exe_path,
            "arguments": self.arguments,
            "saves_path": self.saves_path,
            "tags": self.tags,
            "groups": self.groups,
            "genres": self.genres,
            "rating": self.rating,
            "play_time": self.play_time,
            "completion": self.completion,
            "last_played": self.last_played,
            "cover_image": self.cover_image,
            "notes": self.notes,
            "checklist": self.checklist,
            "sessions": self.sessions,
            "screenshots": self.screenshots,
            "autoscan_screenshots": self.autoscan_screenshots,
            "launch_profiles": self.launch_profiles,
        }


class GameService:
    def __init__(self, data_manager, event_bus: EventBus) -> None:
        self.data_manager = data_manager
        self.event_bus = event_bus

    @property
    def games(self) -> list[Game]:
        return [Game(**game) for game in self.data_manager.get("games", [])]

    def get(self, game_id: str) -> Game | None:
        for game in self.games:
            if game.id == game_id:
                return game
        return None

    def add(self, game_data: dict[str, Any]) -> Game:
        game = Game(**game_data)
        games = self.data_manager.get("games", [])
        games.append(game.to_dict())
        self.data_manager.set("games", games)
        logger.info("Dodano grę %s", game.name)
        self.event_bus.emit("games_changed")
        self.event_bus.emit("game_added", game_id=game.id)
        return game

    def update(self, game_id: str, updates: dict[str, Any]) -> Game | None:
        games = self.data_manager.get("games", [])
        for index, data in enumerate(games):
            if data.get("id") == game_id:
                for key, value in updates.items():
                    data[key] = value
                games[index] = data
                self.data_manager.set("games", games)
                logger.info("Zaktualizowano grę %s", data.get("name"))
                self.event_bus.emit("games_changed")
                self.event_bus.emit("game_updated", game_id=game_id)
                return Game(**data)
        return None

    def delete(self, game_id: str) -> None:
        games = [game for game in self.data_manager.get("games", []) if game.get("id") != game_id]
        self.data_manager.set("games", games)
        logger.info("Usunięto grę %s", game_id)
        self.event_bus.emit("games_changed")

    def log_session(self, game_id: str, duration_minutes: int) -> None:
        games = self.data_manager.get("games", [])
        now = datetime.now().isoformat()
        for game in games:
            if game.get("id") == game_id:
                sessions = game.setdefault("sessions", [])
                sessions.append({
                    "started_at": now,
                    "duration": duration_minutes,
                })
                game["play_time"] = game.get("play_time", 0) + duration_minutes
                game["last_played"] = now
                break
        self.data_manager.set("games", games)
        self.event_bus.emit("games_changed")

    def launch(self, game: Game) -> int | None:
        """Uruchamia grę i zwraca PID procesu."""
        exe = Path(game.exe_path)
        if not exe.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku wykonywalnego: {exe}")

        try:
            pid = None
            if os.name == "nt":
                # Na Windows używamy subprocess zamiast os.startfile, żeby dostać PID
                args = [str(exe)]
                if game.arguments:
                    args.extend(game.arguments.split())
                process = subprocess.Popen(args, cwd=exe.parent)
                pid = process.pid
            else:
                args = [str(exe)]
                if game.arguments:
                    args.extend(game.arguments.split())
                process = subprocess.Popen(args, cwd=exe.parent)
                pid = process.pid
                
            logger.info("Uruchomiono grę %s (PID: %s)", game.name, pid)
            
            # Aktualizuj last_played
            now = datetime.now().isoformat()
            self.update(game.id, {"last_played": now})
            
            self.event_bus.emit("game_launched", game_id=game.id, game_name=game.name, pid=pid)
            return pid
        except Exception as exc:
            logger.exception("Nie udało się uruchomić gry %s", game.name)
            raise exc
