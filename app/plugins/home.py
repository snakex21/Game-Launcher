"""Plugin strony głównej."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import random

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class HomePlugin(BasePlugin):
    name = "Home"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Home")


class HomeView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.context.event_bus.subscribe("games_changed", self._on_data_changed)
        self.context.event_bus.subscribe("theme_changed", self._on_theme_changed)
        self.context.event_bus.subscribe("session_started", self._on_data_changed)
        self.context.event_bus.subscribe("session_ended", self._on_data_changed)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)

        avatar_frame = ctk.CTkFrame(header, width=64, height=64, corner_radius=32, fg_color=self.theme.accent)
        avatar_frame.grid(row=0, column=0, rowspan=2, padx=(0, 15))
        avatar_frame.grid_propagate(False)
        
        username = self.context.data_manager.get("user", {}).get("username", "Graczu")
        initial = username[0].upper() if username else "G"
        
        avatar_label = ctk.CTkLabel(
            avatar_frame,
            text=initial,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.theme.background
        )
        avatar_label.place(relx=0.5, rely=0.5, anchor="center")

        greetings = [
            f"Witaj, {username}!",
            f"Co dzisiaj gramy, {username}?",
            f"Jak się masz, {username}?",
            f"Miło Cię widzieć, {username}!",
            f"Gotowy na nowe wyzwania, {username}?",
        ]
        
        greeting_label = ctk.CTkLabel(
            header,
            text=random.choice(greetings),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text
        )
        greeting_label.grid(row=0, column=1, sticky="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        body.grid_columnconfigure((0, 1), weight=1)
        body.grid_rowconfigure((0, 1), weight=1)

        self.recent_frame = ctk.CTkFrame(body, fg_color=self.theme.surface, corner_radius=15)
        self.recent_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        
        recent_title = ctk.CTkLabel(
            self.recent_frame,
            text="📅 Ostatnio Grane",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        )
        recent_title.pack(padx=15, pady=(15, 10), anchor="w")

        self.random_frame = ctk.CTkFrame(body, fg_color=self.theme.surface, corner_radius=15)
        self.random_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        random_title = ctk.CTkLabel(
            self.random_frame,
            text="🎲 Losowe Gry",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        )
        random_title.pack(padx=15, pady=(15, 10), anchor="w")

        self.stats_frame = ctk.CTkFrame(body, fg_color=self.theme.surface, corner_radius=15)
        self.stats_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        
        stats_title = ctk.CTkLabel(
            self.stats_frame,
            text="📊 Statystyki",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        )
        stats_title.pack(padx=15, pady=(15, 10), anchor="w")

    def _on_data_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_data()

    def _on_theme_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        self._load_data()

    def _load_data(self) -> None:
        for widget in self.recent_frame.winfo_children()[1:]:
            widget.destroy()
        for widget in self.random_frame.winfo_children()[1:]:
            widget.destroy()
        for widget in self.stats_frame.winfo_children()[1:]:
            widget.destroy()

        games = self.context.games.games
        
        recent_games = sorted(
            [g for g in games if g.last_played],
            key=lambda x: x.last_played,
            reverse=True
        )[:5]

        if recent_games:
            for game in recent_games:
                btn = ctk.CTkButton(
                    self.recent_frame,
                    text=f"🎮 {game.name}",
                    command=lambda g=game: self._launch_game(g.id),
                    fg_color=self.theme.base_color,
                    hover_color=self.theme.surface_alt,
                    anchor="w",
                    height=35
                )
                btn.pack(padx=15, pady=5, fill="x")
        else:
            placeholder = ctk.CTkLabel(
                self.recent_frame,
                text="Brak ostatnio granych gier",
                text_color=self.theme.text_muted,
                font=ctk.CTkFont(size=12)
            )
            placeholder.pack(padx=15, pady=20)

        if games:
            random_games = random.sample(games, min(5, len(games)))
            for game in random_games:
                btn = ctk.CTkButton(
                    self.random_frame,
                    text=f"🎮 {game.name}",
                    command=lambda g=game: self._launch_game(g.id),
                    fg_color=self.theme.base_color,
                    hover_color=self.theme.surface_alt,
                    anchor="w",
                    height=35
                )
                btn.pack(padx=15, pady=5, fill="x")
        else:
            placeholder = ctk.CTkLabel(
                self.random_frame,
                text="Brak gier w bibliotece",
                text_color=self.theme.text_muted,
                font=ctk.CTkFont(size=12)
            )
            placeholder.pack(padx=15, pady=20)

        scrollable_stats = ctk.CTkScrollableFrame(
            self.stats_frame,
            fg_color="transparent"
        )
        scrollable_stats.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        total_games = len(games)
        total_time = sum(g.play_time for g in games)
        
        hours = total_time // 60
        days = hours // 24
        months = days // 30
        years = months // 12
        
        stats_data = [
            ("🎮 Liczba gier", str(total_games)),
            ("⏱️ Łączny czas", f"{hours}h ({days}d)"),
            ("📅 Dni gry", str(days)),
            ("📆 Miesięcy gry", str(months)),
            ("📊 Lat gry", str(years)),
        ]

        for label, value in stats_data:
            stat_frame = ctk.CTkFrame(scrollable_stats, fg_color=self.theme.surface_alt, corner_radius=10)
            stat_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted,
                anchor="w"
            ).pack(side="left", padx=10, pady=8)
            
            ctk.CTkLabel(
                stat_frame,
                text=value,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=self.theme.accent,
                anchor="e"
            ).pack(side="right", padx=10, pady=8)

        if games:
            top_games = sorted(games, key=lambda x: x.play_time, reverse=True)[:5]
            
            ctk.CTkLabel(
                scrollable_stats,
                text="🏆 Najdłużej grane",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.theme.text
            ).pack(anchor="w", pady=(15, 5))
            
            for idx, game in enumerate(top_games, 1):
                hours = game.play_time // 60
                game_frame = ctk.CTkFrame(scrollable_stats, fg_color=self.theme.base_color, corner_radius=8)
                game_frame.pack(fill="x", pady=3)
                
                ctk.CTkLabel(
                    game_frame,
                    text=f"{idx}. {game.name}",
                    font=ctk.CTkFont(size=11),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", padx=10, pady=6)
                
                ctk.CTkLabel(
                    game_frame,
                    text=f"{hours}h",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=self.theme.accent,
                    anchor="e"
                ).pack(side="right", padx=10, pady=6)

    def _launch_game(self, game_id: str) -> None:
        game = self.context.games.get(game_id)
        if game:
            try:
                pid = self.context.games.launch(game)
                self.context.sessions.start_session(game, pid)
                self.context.notifications.show("Uruchomiono", f"Gra {game.name} została uruchomiona!")
            except Exception as e:
                logger.error("Błąd uruchamiania gry: %s", e)
                from tkinter import messagebox
                messagebox.showerror("Błąd", f"Nie udało się uruchomić gry:\n{e}")

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("games_changed", self._on_data_changed)
        self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
        self.context.event_bus.unsubscribe("session_started", self._on_data_changed)
        self.context.event_bus.unsubscribe("session_ended", self._on_data_changed)
        super().destroy()
