"""Obsługa motywów kolorystycznych aplikacji."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


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
        """Zwraca wszystkie dostępne motywy (systemowe + własne)."""
        result = list(DEFAULT_THEMES.values())
        
        # Dodaj własne motywy
        custom_themes = self.data_manager.get_nested("settings", "custom_themes", default={})
        for theme_data in custom_themes.values():
            try:
                result.append(Theme(**theme_data))
            except Exception as e:
                logger.error("Błąd ładowania własnego motywu: %s", e)
        
        # Zachowaj kompatybilność z pojedynczym custom_theme
        custom_theme = self.data_manager.get_nested("settings", "custom_theme", default=None)
        if custom_theme and custom_theme.get("name") not in [t.name for t in result]:
            try:
                result.append(Theme(**custom_theme))
            except Exception:
                pass
        
        return result

    def get_active_theme(self) -> Theme:
        """Zwraca aktualnie aktywny motyw."""
        theme_name = self.data_manager.get_nested("settings", "theme", default="midnight")
        accent = self.data_manager.get_nested("settings", "accent", default=None)
        
        # Sprawdź czy to motyw systemowy
        theme = DEFAULT_THEMES.get(theme_name)
        
        # Jeśli nie, szukaj w własnych motywach
        if not theme:
            custom_themes = self.data_manager.get_nested("settings", "custom_themes", default={})
            theme_data = custom_themes.get(theme_name)
            if theme_data:
                theme = Theme(**theme_data)
            else:
                # Fallback do midnight
                theme = DEFAULT_THEMES["midnight"]
        
        # Nadpisz accent jeśli ustawiony
        if accent and accent.startswith("#"):
            return Theme(**{**theme.__dict__, "accent": accent})
        
        return theme

    def set_theme(self, theme_name: str) -> None:
        """Ustaw aktywny motyw."""
        self.data_manager.set_nested("settings", "theme", value=theme_name)
        self.event_bus.emit("theme_changed", theme=theme_name)

    def set_accent(self, hex_color: str) -> None:
        """Ustaw kolor akcentu."""
        self.data_manager.set_nested("settings", "accent", value=hex_color)
        self.event_bus.emit("theme_changed", accent=hex_color)

    def set_custom_theme(self, theme_data: dict[str, Any]) -> None:
        """Zachowano dla kompatybilności wstecznej."""
        self.data_manager.set_nested("settings", "custom_theme", value=theme_data)
        self.event_bus.emit("theme_changed")

    def save_custom_theme(self, theme_name: str, theme_data: dict[str, Any]) -> bool:
        """Zapisz własny motyw."""
        # Sprawdź czy nazwa nie koliduje z systemowym motywem
        if theme_name in DEFAULT_THEMES:
            logger.error("Nie można nadpisać motywu systemowego: %s", theme_name)
            return False
        
        # Walidacja danych
        required_keys = ["name", "base_color", "background", "surface", "surface_alt", "text", "text_muted", "accent"]
        if not all(key in theme_data for key in required_keys):
            logger.error("Nieprawidłowe dane motywu - brakuje wymaganych pól")
            return False
        
        # Walidacja kolorów hex
        for key in required_keys[1:]:  # Pomijamy 'name'
            color = theme_data[key]
            if not (isinstance(color, str) and color.startswith("#") and len(color) in [4, 7]):
                logger.error("Nieprawidłowy kolor hex dla %s: %s", key, color)
                return False
        
        # Zapisz motyw
        custom_themes = self.data_manager.get_nested("settings", "custom_themes", default={})
        custom_themes[theme_name] = theme_data
        self.data_manager.set_nested("settings", "custom_themes", value=custom_themes)
        
        logger.info("Zapisano własny motyw: %s", theme_name)
        self.event_bus.emit("custom_themes_changed")
        return True

    def delete_custom_theme(self, theme_name: str) -> bool:
        """Usuń własny motyw."""
        # Zabezpieczenie przed usunięciem motywów systemowych
        if theme_name in DEFAULT_THEMES:
            logger.error("Nie można usunąć motywu systemowego: %s", theme_name)
            return False
        
        custom_themes = self.data_manager.get_nested("settings", "custom_themes", default={})
        
        if theme_name not in custom_themes:
            logger.warning("Motyw %s nie istnieje", theme_name)
            return False
        
        # Usuń motyw
        del custom_themes[theme_name]
        self.data_manager.set_nested("settings", "custom_themes", value=custom_themes)
        
        # Jeśli usuwany motyw był aktywny, przełącz na midnight
        current_theme = self.data_manager.get_nested("settings", "theme", default="midnight")
        if current_theme == theme_name:
            self.set_theme("midnight")
        
        logger.info("Usunięto własny motyw: %s", theme_name)
        self.event_bus.emit("custom_themes_changed")
        return True

    def is_system_theme(self, theme_name: str) -> bool:
        """Sprawdź czy motyw jest motywem systemowym."""
        return theme_name in DEFAULT_THEMES

    def get_custom_themes(self) -> dict[str, dict[str, Any]]:
        """Zwraca wszystkie własne motywy."""
        return self.data_manager.get_nested("settings", "custom_themes", default={})
