"""Simple publish-subscribe event bus used across the application."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, DefaultDict


class EventBus:
    """Lightweight synchronous event bus."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback not in self._listeners[event]:
            self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)
            if not self._listeners[event]:
                del self._listeners[event]

    def emit(self, event: str, /, **payload: Any) -> None:
        for callback in list(self._listeners.get(event, [])):
            callback(**payload)
