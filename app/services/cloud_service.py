"""Synchronizacja danych z chmurą (szkielet)."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CloudService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus

    def upload_config(self) -> None:
        logger.info("Upload konfiguracji do chmury (placeholder)")
        self.event_bus.emit("cloud_upload_finished")

    def download_config(self) -> None:
        logger.info("Pobieranie konfiguracji z chmury (placeholder)")
        self.event_bus.emit("cloud_download_finished")

    def sync(self) -> None:
        logger.info("Synchronizacja z chmurą (placeholder)")
        self.event_bus.emit("cloud_sync_finished")
