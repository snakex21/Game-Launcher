"""Obsługa motywów kolorystycznych aplikacji."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.event_bus import EventBus


@dataclass(frozen=True)
class Theme:
    name: str
    base_color: str
    background: str
    surface: str
    surface_alt: str
    text: str
    text_muted: str
    accent: str


DEFAULT_THEMES = {
    "midnight": Theme(
        name="midnight",
        base_color="#0b1120",
        background="#0f172a",
        surface="#1e293b",
        surface_alt="#273449",
        text="#e2e8f0",
        text_muted="#94a3b8",
        accent="#6366f1",
    ),
    "emerald": Theme(
        name="emerald",
        base_color="#062817",
        background="#0f3d25",
        surface="#114d2d",
        surface_alt="#146639",
        text="#f3faf7",
        text_muted="#9edbc6",
        accent="#34d399",
    ),
    "sunset": Theme(
        name="sunset",
        base_color="#1f0a16",
        background="#2d0f1f",
        surface="#471124",
        surface_alt="#5d152d",
        text="#ffe4e6",
        text_muted="#f9a8d4",
        accent="#fb7185",
    ),
}


class ThemeService:
    def __init__(self, data_manager, event_bus: EventBus) -> None:
        self.data_manager = data_manager
        self.event_bus = event_bus

    def available_themes(self) -> list[Theme]:
        result = list(DEFAULT_THEMES.values())
        custom_theme = self.data_manager.get_nested("settings", "custom_theme", default=None)
        if custom_theme:
            result.append(Theme(**custom_theme))
        return result

    def get_active_theme(self) -> Theme:
        theme_name = self.data_manager.get_nested("settings", "theme", default="midnight")
        accent = self.data_manager.get_nested("settings", "accent", default=None)
        theme = DEFAULT_THEMES.get(theme_name, DEFAULT_THEMES["midnight"])
        if accent and accent.startswith("#"):
            return Theme(**{**theme.__dict__, "accent": accent})
        return theme

    def set_theme(self, theme_name: str) -> None:
        self.data_manager.set_nested("settings", "theme", value=theme_name)
        self.event_bus.emit("theme_changed", theme=theme_name)

    def set_accent(self, hex_color: str) -> None:
        self.data_manager.set_nested("settings", "accent", value=hex_color)
        self.event_bus.emit("theme_changed", accent=hex_color)

    def set_custom_theme(self, theme_data: dict[str, Any]) -> None:
        self.data_manager.set_nested("settings", "custom_theme", value=theme_data)
        self.event_bus.emit("theme_changed")
