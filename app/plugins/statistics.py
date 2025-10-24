"""Widok statystyk - rozbudowany."""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class StatisticsPlugin(BasePlugin):
    name = "Statistics"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Statistics")


class StatisticsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        
        self.context.event_bus.subscribe("games_changed", self._on_data_changed)
        self.context.event_bus.subscribe("theme_changed", self._on_theme_changed)
        
        self.selected_game_id = None
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📊 Statystyki",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(side="left")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(main_container, fg_color=self.theme.surface, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        left_title = ctk.CTkLabel(
            left_panel,
            text="🎮 Wybierz grę",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        )
        left_title.pack(padx=15, pady=(15, 10))
        
        self.games_list = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.games_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        right_panel = ctk.CTkScrollableFrame(
            main_container, 
            fg_color=self.theme.surface, 
            corner_radius=15
        )
        right_panel.grid(row=0, column=1, sticky="nsew")
        self.stats_container = right_panel

        self._load_data()

    def _on_data_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_data()

    def _on_theme_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        self._load_data()

    def _load_data(self) -> None:
        for widget in self.games_list.winfo_children():
            widget.destroy()

        games = sorted(self.context.games.games, key=lambda x: x.play_time, reverse=True)
        
        all_btn = ctk.CTkButton(
            self.games_list,
            text="📊 Wszystkie gry",
            command=lambda: self._show_game_stats(None),
            fg_color=self.theme.accent if self.selected_game_id is None else self.theme.base_color,
            hover_color=self.theme.surface_alt,
            anchor="w",
            height=35
        )
        all_btn.pack(fill="x", pady=5)

        for game in games:
            hours = game.play_time // 60
            btn_text = f"🎮 {game.name} ({hours}h)"
            btn = ctk.CTkButton(
                self.games_list,
                text=btn_text,
                command=lambda g=game: self._show_game_stats(g.id),
                fg_color=self.theme.accent if self.selected_game_id == game.id else self.theme.base_color,
                hover_color=self.theme.surface_alt,
                anchor="w",
                height=35
            )
            btn.pack(fill="x", pady=5)

        self._show_game_stats(self.selected_game_id)

    def _show_game_stats(self, game_id: str | None) -> None:
        self.selected_game_id = game_id
        
        for widget in self.stats_container.winfo_children():
            widget.destroy()

        if game_id is None:
            self._show_all_games_stats()
        else:
            self._show_single_game_stats(game_id)

    def _show_all_games_stats(self) -> None:
        games = self.context.games.games
        total_time = sum(g.play_time for g in games)
        
        title = ctk.CTkLabel(
            self.stats_container,
            text="📊 Statystyki wszystkich gier",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(padx=20, pady=(20, 15))

        stats_grid = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=10)

        hours = total_time // 60
        minutes = total_time % 60
        days = hours / 24
        months = days / 30
        years = days / 365

        stats_data = [
            ("⏱️ Łączny czas", f"{total_time} minut"),
            ("🕐 W godzinach", f"{hours}h {minutes}m"),
            ("📅 W dniach", f"{days:.2f} dni"),
            ("📆 W miesiącach", f"{months:.2f} miesięcy"),
            ("📊 W latach", f"{years:.2f} lat"),
            ("🎮 Liczba gier", str(len(games))),
        ]

        for idx, (label, value) in enumerate(stats_data):
            stat_frame = ctk.CTkFrame(stats_grid, fg_color=self.theme.surface_alt, corner_radius=10)
            stat_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(size=13),
                text_color=self.theme.text_muted,
                anchor="w"
            ).pack(side="left", padx=15, pady=12)
            
            ctk.CTkLabel(
                stat_frame,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.accent,
                anchor="e"
            ).pack(side="right", padx=15, pady=12)

        if games:
            top_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
            top_section.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(
                top_section,
                text="🏆 Top 10 najdłużej granych",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.text
            ).pack(padx=15, pady=(15, 10))

            top_games = sorted(games, key=lambda x: x.play_time, reverse=True)[:10]
            for idx, game in enumerate(top_games, 1):
                hours = game.play_time // 60
                minutes = game.play_time % 60
                
                game_row = ctk.CTkFrame(top_section, fg_color=self.theme.surface, corner_radius=8)
                game_row.pack(fill="x", padx=15, pady=5)
                
                rank_label = ctk.CTkLabel(
                    game_row,
                    text=f"#{idx}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.theme.accent,
                    width=40
                )
                rank_label.pack(side="left", padx=10, pady=10)
                
                ctk.CTkLabel(
                    game_row,
                    text=game.name,
                    font=ctk.CTkFont(size=12),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=5, pady=10)
                
                ctk.CTkLabel(
                    game_row,
                    text=f"{hours}h {minutes}m",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.theme.text_muted
                ).pack(side="right", padx=10, pady=10)

    def _show_single_game_stats(self, game_id: str) -> None:
        game = self.context.games.get(game_id)
        if not game:
            return

        title = ctk.CTkLabel(
            self.stats_container,
            text=f"🎮 {game.name}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(padx=20, pady=(20, 15))

        stats_grid = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=10)

        hours = game.play_time // 60
        minutes = game.play_time % 60
        days = hours / 24
        months = days / 30
        years = days / 365

        stats_data = [
            ("⏱️ Łączny czas", f"{game.play_time} minut"),
            ("🕐 W godzinach", f"{hours}h {minutes}m"),
            ("📅 W dniach", f"{days:.2f} dni"),
            ("📆 W miesiącach", f"{months:.2f} miesięcy"),
            ("📊 W latach", f"{years:.2f} lat"),
            ("📈 Ukończenie", f"{game.completion}%"),
            ("⭐ Ocena", f"{game.rating:.1f}/10"),
            ("🎯 Gatunki", ", ".join(game.genres) if game.genres else "Brak"),
        ]

        for label, value in stats_data:
            stat_frame = ctk.CTkFrame(stats_grid, fg_color=self.theme.surface_alt, corner_radius=10)
            stat_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(size=13),
                text_color=self.theme.text_muted,
                anchor="w"
            ).pack(side="left", padx=15, pady=12)
            
            ctk.CTkLabel(
                stat_frame,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.accent,
                anchor="e"
            ).pack(side="right", padx=15, pady=12)

        if game.sessions:
            sessions_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
            sessions_section.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(
                sessions_section,
                text="📜 Historia sesji",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.text
            ).pack(padx=15, pady=(15, 10))

            recent_sessions = sorted(game.sessions, key=lambda x: x.get('started_at', ''), reverse=True)[:10]
            
            for session in recent_sessions:
                started_at = session.get('started_at', '')
                duration = session.get('duration', 0)
                
                try:
                    dt = datetime.fromisoformat(started_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = started_at

                session_row = ctk.CTkFrame(sessions_section, fg_color=self.theme.surface, corner_radius=8)
                session_row.pack(fill="x", padx=15, pady=5)
                
                ctk.CTkLabel(
                    session_row,
                    text=date_str,
                    font=ctk.CTkFont(size=11),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", padx=10, pady=8)
                
                ctk.CTkLabel(
                    session_row,
                    text=f"{duration} min",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=self.theme.accent
                ).pack(side="right", padx=10, pady=8)

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("games_changed", self._on_data_changed)
        self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
        super().destroy()
