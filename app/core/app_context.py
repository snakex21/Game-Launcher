"""Kontekst aplikacji odpowiedzialny za inicjalizację usług i pluginów."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .data_manager import DataManager
from .event_bus import EventBus

if TYPE_CHECKING:
    from app.services.game_service import GameService
    from app.services.reminder_service import ReminderService
    from app.services.session_tracker import SessionTracker
    from app.services.music_service import MusicService
    from app.services.theme_service import ThemeService
    from app.services.cloud_service import CloudService
    from app.services.discord_service import DiscordService
    from app.services.notification_service import NotificationService
    from app.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class AppContext:
    """Kontener zależności aplikacji."""

    def __init__(self, config_path: str | None = None) -> None:
        self.event_bus = EventBus()
        self.config_path = config_path or "config.json"
        self.data_manager = DataManager(self.config_path, event_bus=self.event_bus)
        self.services: dict[str, object] = {}
        self.plugins: list["BasePlugin"] = []

    def register_service(self, key: str, service: object) -> None:
        if key in self.services:
            logger.warning("Service %s already registered, overriding", key)
        self.services[key] = service

    def service(self, key: str):  # type: ignore[no-untyped-def]
        return self.services[key]

    def add_plugin(self, plugin: "BasePlugin") -> None:
        self.plugins.append(plugin)

    def bootstrap(self) -> None:
        for plugin in self.plugins:
            logger.debug("Inicjalizacja pluginu: %s", plugin.__class__.__name__)
            plugin.register(self)

    @property
    def games(self) -> "GameService":
        return self.services["games"]  # type: ignore[return-value]

    @property
    def reminders(self) -> "ReminderService":
        return self.services["reminders"]  # type: ignore[return-value]

    @property
    def sessions(self) -> "SessionTracker":
        return self.services["sessions"]  # type: ignore[return-value]

    @property
    def music(self) -> "MusicService":
        return self.services["music"]  # type: ignore[return-value]

    @property
    def theme(self) -> "ThemeService":
        return self.services["theme"]  # type: ignore[return-value]

    @property
    def cloud(self) -> "CloudService":
        return self.services["cloud"]  # type: ignore[return-value]

    @property
    def discord(self) -> "DiscordService":
        return self.services["discord"]  # type: ignore[return-value]

    @property
    def notifications(self) -> "NotificationService":
        return self.services["notifications"]  # type: ignore[return-value]
