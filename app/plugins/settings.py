"""Widok ustawień."""
from __future__ import annotations

import logging
from tkinter import colorchooser

import customtkinter as ctk

from .base import BasePlugin

logger = logging.getLogger(__name__)


class SettingsPlugin(BasePlugin):
    name = "Settings"

    def register(self, context) -> None:  # type: ignore[no-untyped-def]
        logger.info("Zarejestrowano plugin Settings")


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.context = context

        self.columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self,
            text="⚙ Ustawienia",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        card.columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Motyw:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.theme_option = ctk.CTkOptionMenu(
            card,
            values=[theme.name for theme in self.context.theme.available_themes()],
            command=lambda theme: self.context.theme.set_theme(theme)
        )
        self.theme_option.set(self.context.theme.get_active_theme().name)
        self.theme_option.grid(row=0, column=1, padx=20, pady=15, sticky="e")

        ctk.CTkLabel(card, text="Kolor akcentu:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=20, pady=15, sticky="w")
        self.accent_preview = ctk.CTkLabel(card, text="█████", font=ctk.CTkFont(size=20))
        self.accent_preview.grid(row=1, column=1, padx=20, pady=15, sticky="w")
        self.accent_preview.configure(text_color=self.context.theme.get_active_theme().accent)

        accent_button = ctk.CTkButton(
            card,
            text="Wybierz kolor",
            command=self._choose_accent
        )
        accent_button.grid(row=1, column=2, padx=20, pady=15)

        notifications_card = ctk.CTkFrame(self, corner_radius=12)
        notifications_card.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        notifications_card.columnconfigure(0, weight=1)

        notify_switch = ctk.CTkSwitch(
            notifications_card,
            text="Powiadomienia systemowe",
            command=self._toggle_notifications
        )
        current_state = self.context.data_manager.get_nested("settings", "show_notifications", default=True)
        notify_switch.select() if current_state else notify_switch.deselect()
        notify_switch.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        rss_card = ctk.CTkFrame(self, corner_radius=12)
        rss_card.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        rss_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(rss_card, text="Kanały RSS", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.feeds_box = ctk.CTkTextbox(rss_card, height=150)
        feeds = self.context.data_manager.get_nested("settings", "rss_feeds", default=[])
        feeds_text = "\n".join(feeds)
        self.feeds_box.insert("1.0", feeds_text)
        self.feeds_box.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        save_feeds = ctk.CTkButton(rss_card, text="Zapisz kanały", command=self._save_rss)
        save_feeds.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="e")

    def _choose_accent(self) -> None:
        color = colorchooser.askcolor(title="Wybierz kolor akcentu")
        if color and color[1]:
            hex_color = color[1]
            self.accent_preview.configure(text_color=hex_color)
            self.context.theme.set_accent(hex_color)

    def _toggle_notifications(self) -> None:
        current = self.context.data_manager.get_nested("settings", "show_notifications", default=True)
        self.context.data_manager.set_nested("settings", "show_notifications", value=not current)

    def _save_rss(self) -> None:
        feeds_text = self.feeds_box.get("1.0", "end").strip()
        feeds = [line.strip() for line in feeds_text.splitlines() if line.strip()]
        self.context.data_manager.set_nested("settings", "rss_feeds", value=feeds)
        logger.info("Zapisano kanały RSS")
