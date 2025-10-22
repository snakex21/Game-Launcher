"""Integracja z Discord Rich Presence."""
from __future__ import annotations

import logging
from datetime import datetime

from pypresence import Presence, PyPresenceException

logger = logging.getLogger(__name__)


class DiscordService:
    def __init__(self, data_manager) -> None:
        self.data_manager = data_manager
        self.client: Presence | None = None

    def connect(self) -> None:
        if self.client:
            return

        if not self.data_manager.get_nested("settings", "discord_enabled", default=False):
            return

        client_id = self.data_manager.get_nested("settings", "discord_client_id", default="")
        if not client_id:
            logger.warning("Brak client ID do Discord Rich Presence")
            return

        try:
            self.client = Presence(client_id)
            self.client.connect()
            logger.info("Połączono z Discord Rich Presence")
        except PyPresenceException as exc:
            logger.error("Błąd łączenia z Discord: %s", exc)
            self.client = None

    def update_activity(self, details: str, state: str | None = None) -> None:
        if not self.client:
            return
        payload = {
            "details": details,
            "start": datetime.now().timestamp(),
        }
        if state:
            payload["state"] = state

        try:
            self.client.update(**payload)
        except PyPresenceException as exc:
            logger.error("Błąd aktualizacji Discord Rich Presence: %s", exc)

    def disconnect(self) -> None:
        if not self.client:
            return
        try:
            self.client.close()
            logger.info("Rozłączono Discord Rich Presence")
        except PyPresenceException as exc:
            logger.error("Błąd rozłączania z Discord: %s", exc)
        finally:
            self.client = None
