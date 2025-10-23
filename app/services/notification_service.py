"""Powiadomienia systemowe."""
from __future__ import annotations

import logging

from plyer import notification

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, data_manager) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager

    def show(self, title: str, message: str, timeout: int = 10) -> None:
        enabled = self.data_manager.get_nested("settings", "show_notifications", default=True)
        if not enabled:
            return

        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Game Launcher",
                timeout=timeout,
            )
            logger.info("Powiadomienie: %s - %s", title, message)
        except Exception as e:
            logger.error("Błąd wyświetlania powiadomienia: %s", e)
