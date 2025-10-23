"""Interfejs bazowy pluginów."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class BasePlugin:
    """Bazowa klasa pluginów."""

    name: str = "BasePlugin"

    def register(self, context: AppContext) -> None:
        pass

    def unregister(self) -> None:
        pass
