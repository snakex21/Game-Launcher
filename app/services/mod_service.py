"""Zarządzanie modami gier."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ModService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus

    def list(self) -> list[dict[str, Any]]:
        return self.data_manager.get("mods", [])

    def list_by_game(self, game_name: str) -> list[dict[str, Any]]:
        return [mod for mod in self.list() if mod.get("game_name") == game_name]

    def add_mod(self, mod_data: dict[str, Any]) -> dict[str, Any]:
        mods = self.list()
        mod = {
            "id": str(uuid.uuid4()),
            "game_name": mod_data.get("game_name"),
            "mod_name": mod_data.get("mod_name"),
            "version": mod_data.get("version", "1.0"),
            "status": mod_data.get("status", "enabled"),
            "installed_at": datetime.now().isoformat(),
            "notes": mod_data.get("notes", ""),
            "author": mod_data.get("author", ""),
            "url": mod_data.get("url", ""),
        }
        mods.append(mod)
        self.data_manager.set("mods", mods)
        logger.info("Dodano mod %s do gry %s", mod["mod_name"], mod["game_name"])
        self.event_bus.emit("mods_changed", game_name=mod["game_name"])
        self.event_bus.emit("mod_added", mod_id=mod["id"], game_name=mod["game_name"])
        return mod

    def update_mod(self, mod_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        mods = self.list()
        for index, mod in enumerate(mods):
            if mod.get("id") == mod_id:
                mod.update(updates)
                mods[index] = mod
                self.data_manager.set("mods", mods)
                logger.info("Zaktualizowano mod %s", mod.get("mod_name"))
                self.event_bus.emit("mods_changed", game_name=mod.get("game_name"))
                return mod
        return None

    def toggle_status(self, mod_id: str) -> dict[str, Any] | None:
        mods = self.list()
        for mod in mods:
            if mod.get("id") == mod_id:
                mod["status"] = "disabled" if mod.get("status") == "enabled" else "enabled"
                self.data_manager.set("mods", mods)
                logger.info("Zmiana statusu modu %s -> %s", mod.get("mod_name"), mod.get("status"))
                self.event_bus.emit("mods_changed", game_name=mod.get("game_name"))
                return mod
        return None

    def delete_mod(self, mod_id: str) -> None:
        mods = [mod for mod in self.list() if mod.get("id") != mod_id]
        self.data_manager.set("mods", mods)
        logger.info("Usunięto mod %s", mod_id)
        self.event_bus.emit("mods_changed")
