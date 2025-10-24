"""Plugin strony głównej."""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import TYPE_CHECKING

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
        self.context.event_bus.subscribe("roadmap_updated", self._on_data_changed)
        self.context.event_bus.subscribe("roadmap_completed", self._on_data_changed)
        self.context.event_bus.subscribe("achievements_changed", self._on_data_changed)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Nagłówek z powitaniem
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        username = self.context.data_manager.get("user", {}).get("username", "Graczu")
        
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
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme.text
        )
        greeting_label.pack(side="left")

        # Główny kontener przewijany
        main_scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_scrollable.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_scrollable.grid_columnconfigure((0, 1, 2), weight=1)

        # ===== SEKCJA 1: Kafelki statystyk (3 kolumny) =====
        stats_container = ctk.CTkFrame(main_scrollable, fg_color="transparent")
        stats_container.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        stats_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_tiles = []
        stat_configs = [
            ("🎮", "Biblioteka", "games"),
            ("⏱️", "Czas gry", "playtime"),
            ("🏆", "Osiągnięcia", "achievements"),
            ("🗺️", "Roadmapa", "roadmap"),
        ]
        
        for idx, (icon, label, key) in enumerate(stat_configs):
            tile = self._create_stat_tile(stats_container, icon, label, key)
            tile.grid(row=0, column=idx, padx=5, pady=5, sticky="nsew")
            self.stat_tiles.append((tile, key))

        # ===== SEKCJA 2: Ostatnio grane + Losowe gry =====
        games_row = ctk.CTkFrame(main_scrollable, fg_color="transparent")
        games_row.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 15), padx=(0, 7))
        games_row.grid_columnconfigure((0, 1), weight=1)
        games_row.grid_rowconfigure(0, weight=1)

        self.recent_frame = self._create_section_frame(games_row, "📅 Ostatnio Grane")
        self.recent_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        
        self.random_frame = self._create_section_frame(games_row, "🎲 Losowe Gry")
        self.random_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        # ===== SEKCJA 3: Roadmapa Preview =====
        self.roadmap_frame = self._create_section_frame(main_scrollable, "🗺️ Roadmapa - Najbliższe Cele")
        self.roadmap_frame.grid(row=1, column=2, sticky="nsew", pady=(0, 15), padx=(7, 0), rowspan=2)

        # ===== SEKCJA 4: Osiągnięcia Preview =====
        self.achievements_frame = self._create_section_frame(main_scrollable, "🏆 Ostatnie Osiągnięcia")
        self.achievements_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 15), padx=(0, 7))

        # ===== SEKCJA 5: Ostatnie Screenshoty =====
        self.screenshots_frame = self._create_section_frame(main_scrollable, "📸 Ostatnie Zrzuty Ekranu")
        self.screenshots_frame.grid(row=2, column=1, sticky="nsew", pady=(0, 15), padx=(7, 0))

        # ===== SEKCJA 6: Statystyki szczegółowe =====
        self.stats_detail_frame = self._create_section_frame(main_scrollable, "📊 Szczegółowe Statystyki")
        self.stats_detail_frame.grid(row=3, column=0, columnspan=3, sticky="nsew")

    def _create_section_frame(self, parent, title: str) -> ctk.CTkFrame:
        """Tworzy ramkę sekcji z nagłówkiem."""
        container = ctk.CTkFrame(parent, fg_color=self.theme.surface, corner_radius=15)
        
        title_label = ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text,
            anchor="w"
        )
        title_label.pack(padx=15, pady=(15, 10), anchor="w", fill="x")
        
        return container

    def _create_stat_tile(self, parent, icon: str, label: str, key: str) -> ctk.CTkFrame:
        """Tworzy kafelek statystyki."""
        tile = ctk.CTkFrame(parent, fg_color=self.theme.surface, corner_radius=12, height=100)
        tile.grid_propagate(False)
        
        icon_label = ctk.CTkLabel(
            tile,
            text=icon,
            font=ctk.CTkFont(size=36)
        )
        icon_label.pack(pady=(15, 5))
        
        value_label = ctk.CTkLabel(
            tile,
            text="0",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.accent
        )
        value_label.pack()
        tile._value_label = value_label  # type: ignore[attr-defined]
        
        name_label = ctk.CTkLabel(
            tile,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_muted
        )
        name_label.pack(pady=(0, 10))
        
        return tile

    def _on_data_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_data()

    def _on_theme_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        self._load_data()

    def _load_data(self) -> None:
        """Ładuje wszystkie dane na stronie głównej."""
        self._load_stat_tiles()
        self._load_recent_games()
        self._load_random_games()
        self._load_roadmap_preview()
        self._load_achievements_preview()
        self._load_screenshots_preview()
        self._load_detailed_stats()

    def _load_stat_tiles(self) -> None:
        """Aktualizuje kafelki statystyk."""
        games = self.context.games.games
        total_games = len(games)
        total_minutes = sum(g.play_time for g in games)
        total_hours = total_minutes // 60
        
        # Osiągnięcia
        achievements_service = self.context.service("achievements")
        progress = achievements_service.user_progress()
        unlocked = sum(1 for data in progress.values() if data.get("unlocked"))
        total_achievements = len(achievements_service.catalog())
        
        # Roadmapa
        roadmap = self.context.data_manager.get("roadmap", [])
        roadmap_total = len(roadmap)
        roadmap_completed = sum(1 for item in roadmap if item.get("completed", False))
        
        stat_values = {
            "games": str(total_games),
            "playtime": f"{total_hours}h",
            "achievements": f"{unlocked}/{total_achievements}",
            "roadmap": f"{roadmap_completed}/{roadmap_total}"
        }
        
        for tile, key in self.stat_tiles:
            if hasattr(tile, "_value_label"):
                tile._value_label.configure(text=stat_values.get(key, "0"))  # type: ignore[attr-defined]

    def _load_recent_games(self) -> None:
        """Ładuje ostatnio grane gry."""
        # Usuń stare widgety (oprócz tytułu)
        for widget in self.recent_frame.winfo_children()[1:]:
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

    def _load_random_games(self) -> None:
        """Ładuje losowe gry."""
        for widget in self.random_frame.winfo_children()[1:]:
            widget.destroy()

        games = self.context.games.games
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

    def _load_roadmap_preview(self) -> None:
        """Ładuje podgląd roadmapy."""
        for widget in self.roadmap_frame.winfo_children()[1:]:
            widget.destroy()

        roadmap_items = self.context.data_manager.get("roadmap", [])
        in_progress = [item for item in roadmap_items if not item.get("completed", False)]
        
        if in_progress:
            # Sortuj po priorytecie: high > medium > low
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_items = sorted(in_progress, key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
            
            for item in sorted_items[:5]:  # Pokaż max 5
                self._create_roadmap_mini_card(self.roadmap_frame, item)
        else:
            placeholder = ctk.CTkLabel(
                self.roadmap_frame,
                text="Brak zadań w roadmapie\nDodaj cele w zakładce Roadmapa!",
                text_color=self.theme.text_muted,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            placeholder.pack(padx=15, pady=30)

    def _create_roadmap_mini_card(self, parent, item: dict) -> None:  # type: ignore[type-arg]
        """Tworzy mini kartę roadmapy."""
        card = ctk.CTkFrame(parent, fg_color=self.theme.base_color, corner_radius=8)
        card.pack(fill="x", padx=15, pady=4)
        
        game_name = item.get("game_name", "Nieznana gra")
        priority = item.get("priority", "medium")
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "⚪"}
        
        label = ctk.CTkLabel(
            card,
            text=f"{priority_emoji.get(priority, '⚪')} {game_name}",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text,
            anchor="w"
        )
        label.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        
        target_date = item.get("target_date", "")
        if target_date:
            date_label = ctk.CTkLabel(
                card,
                text=f"🎯 {target_date}",
                font=ctk.CTkFont(size=10),
                text_color=self.theme.text_muted
            )
            date_label.pack(side="right", padx=10, pady=8)

    def _load_achievements_preview(self) -> None:
        """Ładuje podgląd osiągnięć."""
        for widget in self.achievements_frame.winfo_children()[1:]:
            widget.destroy()

        achievements_service = self.context.service("achievements")
        progress = achievements_service.user_progress()
        catalog = achievements_service.catalog()
        
        # Znajdź ostatnio odblokowane osiągnięcia
        unlocked = []
        for key, data in progress.items():
            if data.get("unlocked") and key in catalog:
                unlocked.append({
                    "key": key,
                    "data": data,
                    "definition": catalog[key]
                })
        
        # Sortuj po timestamp
        unlocked.sort(key=lambda x: x["data"].get("timestamp", 0), reverse=True)
        
        if unlocked:
            for ach in unlocked[:4]:  # Pokaż 4 ostatnie
                self._create_achievement_mini_card(self.achievements_frame, ach)
        else:
            placeholder = ctk.CTkLabel(
                self.achievements_frame,
                text="Brak odblokowanych osiągnięć\nZacznij grać, aby je zdobywać!",
                text_color=self.theme.text_muted,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            placeholder.pack(padx=15, pady=30)

    def _create_achievement_mini_card(self, parent, achievement: dict) -> None:  # type: ignore[type-arg]
        """Tworzy mini kartę osiągnięcia."""
        card = ctk.CTkFrame(parent, fg_color=self.theme.base_color, corner_radius=8)
        card.pack(fill="x", padx=15, pady=4)
        
        definition = achievement["definition"]
        name = definition.get("name", "Osiągnięcie")
        
        label = ctk.CTkLabel(
            card,
            text=f"🏆 {name}",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text,
            anchor="w"
        )
        label.pack(side="left", padx=10, pady=8, fill="x", expand=True)

    def _load_screenshots_preview(self) -> None:
        """Ładuje podgląd ostatnich screenshotów."""
        for widget in self.screenshots_frame.winfo_children()[1:]:
            widget.destroy()

        # Zbierz screenshoty ze wszystkich gier
        all_screenshots = []
        games = self.context.games.games
        
        for game in games:
            for screenshot_path in game.screenshots:
                try:
                    path = Path(screenshot_path)
                    if path.exists():
                        mtime = os.path.getmtime(screenshot_path)
                        all_screenshots.append({
                            "game_name": game.name,
                            "path": screenshot_path,
                            "mtime": mtime
                        })
                except Exception:
                    continue
        
        if all_screenshots:
            # Sortuj po czasie modyfikacji
            sorted_screenshots = sorted(all_screenshots, key=lambda x: x.get("mtime", 0), reverse=True)
            
            for screenshot in sorted_screenshots[:4]:  # Pokaż 4 ostatnie
                game_name = screenshot.get("game_name", "Nieznana gra")
                
                card = ctk.CTkFrame(self.screenshots_frame, fg_color=self.theme.base_color, corner_radius=8)
                card.pack(fill="x", padx=15, pady=4)
                
                label = ctk.CTkLabel(
                    card,
                    text=f"📸 {game_name}",
                    font=ctk.CTkFont(size=12),
                    text_color=self.theme.text,
                    anchor="w"
                )
                label.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        else:
            placeholder = ctk.CTkLabel(
                self.screenshots_frame,
                text="Brak zrzutów ekranu\nDodaj je w zakładce Screenshoty!",
                text_color=self.theme.text_muted,
                font=ctk.CTkFont(size=12),
                justify="center"
            )
            placeholder.pack(padx=15, pady=30)

    def _load_detailed_stats(self) -> None:
        """Ładuje szczegółowe statystyki."""
        for widget in self.stats_detail_frame.winfo_children()[1:]:
            widget.destroy()

        scrollable_stats = ctk.CTkScrollableFrame(
            self.stats_detail_frame,
            fg_color="transparent",
            height=250
        )
        scrollable_stats.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        games = self.context.games.games
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
        """Uruchamia grę."""
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
        """Czyszczenie subskrypcji."""
        self.context.event_bus.unsubscribe("games_changed", self._on_data_changed)
        self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
        self.context.event_bus.unsubscribe("session_started", self._on_data_changed)
        self.context.event_bus.unsubscribe("session_ended", self._on_data_changed)
        self.context.event_bus.unsubscribe("roadmap_updated", self._on_data_changed)
        self.context.event_bus.unsubscribe("roadmap_completed", self._on_data_changed)
        self.context.event_bus.unsubscribe("achievements_changed", self._on_data_changed)
        super().destroy()
