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
        self.theme = context.theme.get_active_theme()
        self.selected_feeds: set[str] = set()
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📰 Aktualności",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left")
        
        btn_refresh = ctk.CTkButton(
            header,
            text="🔄 Odśwież",
            command=self._load_news,
            width=120,
            fg_color=self.theme.accent
        )
        btn_refresh.pack(side="right")

        filters_frame = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=10)
        filters_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            filters_frame,
            text="Źródła:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=15, pady=10)
        
        self.filters_container = ctk.CTkFrame(filters_frame, fg_color="transparent")
        self.filters_container.pack(side="left", fill="x", expand=True, padx=(0, 15), pady=10)

        self.scrollable = ctk.CTkScrollableFrame(self)
        self.scrollable.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self._setup_filters()
        self._load_news()

    def _setup_filters(self) -> None:
        """Tworzy checkboxy dla źródeł RSS."""
        feeds = self.context.data_manager.get_nested("settings", "rss_feeds", default=[])
        
        if not feeds:
            return
        
        self.selected_feeds = set(feeds)
        
        btn_all = ctk.CTkButton(
            self.filters_container,
            text="Wszystkie",
            command=self._select_all_feeds,
            width=80,
            height=28,
            fg_color=self.theme.base_color
        )
        btn_all.pack(side="left", padx=5)
        
        feed_names = {
            "pcgamer": "PC Gamer",
            "ign": "IGN",
            "gamespot": "GameSpot",
            "polygon": "Polygon",
            "eurogamer": "Eurogamer",
        }
        
        self.feed_checkboxes = {}
        for feed_url in feeds:
            feed_name = None
            for key, name in feed_names.items():
                if key in feed_url.lower():
                    feed_name = name
                    break
            if not feed_name:
                feed_name = feed_url.split("//")[-1].split("/")[0][:15]
            
            var = ctk.BooleanVar(value=True)
            checkbox = ctk.CTkCheckBox(
                self.filters_container,
                text=feed_name,
                variable=var,
                command=lambda url=feed_url, v=var: self._toggle_feed(url, v),
                width=100
            )
            checkbox.pack(side="left", padx=5)
            self.feed_checkboxes[feed_url] = var

    def _select_all_feeds(self) -> None:
        """Zaznacza wszystkie źródła."""
        feeds = self.context.data_manager.get_nested("settings", "rss_feeds", default=[])
        self.selected_feeds = set(feeds)
        for var in self.feed_checkboxes.values():
            var.set(True)
        self._load_news()

    def _toggle_feed(self, feed_url: str, var: ctk.BooleanVar) -> None:
        """Przełącza źródło RSS."""
        if var.get():
            self.selected_feeds.add(feed_url)
        else:
            self.selected_feeds.discard(feed_url)
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
            if feed_url not in self.selected_feeds:
                continue
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:limit]:
                    entry['_source'] = feed_url
                    all_entries.append(entry)
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
