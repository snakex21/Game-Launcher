"""Plugin newsów z RSS."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk
import feedparser

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class NewsPlugin(BasePlugin):
    name = "News"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin News")


class NewsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self,
            text="📰 Aktualności",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.scrollable = ctk.CTkScrollableFrame(self)
        self.scrollable.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self._load_news()

    def _load_news(self) -> None:
        for child in self.scrollable.winfo_children():
            child.destroy()

        feeds = self.context.data_manager.get_nested("settings", "rss_feeds", default=[])
        limit = self.context.data_manager.get_nested("settings", "rss_limit", default=6)

        if not feeds:
            placeholder = ctk.CTkLabel(
                self.scrollable,
                text="Brak kanałów RSS.\nDodaj je w Ustawieniach.",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(pady=50)
            return

        all_entries = []
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                all_entries.extend(feed.entries[:limit])
            except Exception as e:
                logger.error("Błąd pobierania RSS %s: %s", feed_url, e)

        for entry in all_entries[:limit]:
            news_card = ctk.CTkFrame(self.scrollable, corner_radius=10)
            news_card.pack(fill="x", padx=10, pady=5)

            title = ctk.CTkLabel(
                news_card,
                text=entry.get("title", "Brak tytułu"),
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            title.pack(fill="x", padx=15, pady=(10, 5))

            summary = entry.get("summary", "Brak opisu")[:200] + "..."
            desc = ctk.CTkLabel(
                news_card,
                text=summary,
                font=ctk.CTkFont(size=12),
                anchor="w",
                wraplength=700,
                justify="left"
            )
            desc.pack(fill="x", padx=15, pady=5)

            link = entry.get("link", "")
            if link:
                btn = ctk.CTkButton(
                    news_card,
                    text="Czytaj więcej →",
                    command=lambda url=link: self._open_link(url),
                    width=120,
                    height=28
                )
                btn.pack(anchor="w", padx=15, pady=(5, 10))

    def _open_link(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)
