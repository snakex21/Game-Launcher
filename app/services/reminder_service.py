"""Zarządzanie przypomnieniami użytkownika."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    id: str
    title: str
    message: str
    remind_at: str
    repeat: str = "none"  # none, daily, weekly, monthly
    completed: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "remind_at": self.remind_at,
            "repeat": self.repeat,
            "completed": self.completed,
            "tags": self.tags,
        }


class ReminderService:
    def __init__(self, data_manager, event_bus: EventBus) -> None:
        self.data_manager = data_manager
        self.event_bus = event_bus

    def list(self) -> list[Reminder]:
        return [Reminder(**raw) for raw in self.data_manager.get("reminders", [])]

    def add(self, reminder: Reminder) -> None:
        reminders = self.data_manager.get("reminders", [])
        reminders.append(reminder.to_dict())
        self.data_manager.set("reminders", reminders)
        logger.info("Dodano przypomnienie %s", reminder.title)
        self.event_bus.emit("reminders_changed")

    def update(self, reminder_id: str, updates: dict[str, Any]) -> Reminder | None:
        reminders = self.data_manager.get("reminders", [])
        for index, data in enumerate(reminders):
            if data.get("id") == reminder_id:
                data.update(updates)
                reminders[index] = data
                self.data_manager.set("reminders", reminders)
                logger.info("Zaktualizowano przypomnienie %s", data.get("title"))
                self.event_bus.emit("reminders_changed")
                return Reminder(**data)
        return None

    def remove(self, reminder_id: str) -> None:
        reminders = [r for r in self.data_manager.get("reminders", []) if r.get("id") != reminder_id]
        self.data_manager.set("reminders", reminders)
        logger.info("Usunięto przypomnienie %s", reminder_id)
        self.event_bus.emit("reminders_changed")

    def upcoming(self) -> list[Reminder]:
        reminders = []
        now = datetime.now()
        for reminder in self.list():
            remind_time = datetime.fromisoformat(reminder.remind_at)
            if not reminder.completed and remind_time >= now:
                reminders.append(reminder)
        return sorted(reminders, key=lambda r: r.remind_at)
