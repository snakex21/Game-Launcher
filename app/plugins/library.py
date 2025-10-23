"""Plugin biblioteki gier."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class LibraryPlugin(BasePlugin):
    name = "Library"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Library")


class LibraryView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.context.event_bus.subscribe("games_changed", self._on_games_changed)
        self.context.event_bus.subscribe("theme_changed", self._on_theme_changed)
        self._setup_ui()
        self._load_games()

    def _setup_ui(self) -> None:
        self.theme = self.context.theme.get_active_theme()
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))

        self.title_label = ctk.CTkLabel(
            header,
            text="📚 Biblioteka Gier",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(side="left", padx=10)

        self.btn_add = ctk.CTkButton(
            header,
            text="➕ Dodaj Grę",
            command=self._add_game,
            width=140,
            height=36,
            corner_radius=10,
            fg_color=self.theme.accent,
            hover_color=self._adjust_color(self.theme.accent, -15),
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_add.pack(side="right", padx=10)

        self.btn_refresh = ctk.CTkButton(
            header,
            text="🔄 Odśwież",
            command=self._load_games,
            width=120,
            height=36,
            corner_radius=10,
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface_alt
        )
        self.btn_refresh.pack(side="right", padx=6)

        self.summary_container = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_container.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.summary_container.grid_columnconfigure((0, 1, 2), weight=1)

        self.scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.scrollable.grid_columnconfigure((0, 1, 2), weight=1)

    def _on_games_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_games()

    def _on_theme_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.theme = self.context.theme.get_active_theme()
        self._load_games()

    def _load_games(self) -> None:
        for widget in self.summary_container.winfo_children():
            widget.destroy()
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        games = self.context.games.games

        self.configure(fg_color=self.theme.background)
        self.title_label.configure(text_color=self.theme.text)
        self.btn_add.configure(
            fg_color=self.theme.accent,
            hover_color=self._adjust_color(self.theme.accent, -15)
        )
        self.btn_refresh.configure(
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface_alt
        )

        self._create_summary_cards(games)

        if not games:
            placeholder = ctk.CTkLabel(
                self.scrollable,
                text="Brak gier w bibliotece.\nKliknij '➕ Dodaj Grę' aby rozpocząć!",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, columnspan=3, pady=100)
            return

        for index, game in enumerate(games):
            row = index // 3
            col = index % 3
            
            card = self._create_game_card(game)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _create_summary_cards(self, games: list) -> None:  # type: ignore[type-arg]
        total_games = len(games)
        total_hours = sum(game.play_time for game in games) // 60
        avg_completion = sum(game.completion for game in games) / total_games if total_games > 0 else 0

        cards_data = [
            ("🎮", "Liczba gier", str(total_games), self.theme.accent),
            ("⏱️", "Godziny gry", f"{total_hours}h", "#3498db"),
            ("📈", "Śr. ukończenie", f"{avg_completion:.1f}%", "#2ecc71")
        ]

        for idx, (icon, label, value, color) in enumerate(cards_data):
            card = ctk.CTkFrame(self.summary_container, corner_radius=12, fg_color=self.theme.surface_alt)
            card.grid(row=0, column=idx, padx=8, pady=8, sticky="ew")

            icon_label = ctk.CTkLabel(
                card,
                text=icon,
                font=ctk.CTkFont(size=28)
            )
            icon_label.pack(side="left", padx=(16, 12), pady=16)

            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                text_frame,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_frame,
                text=value,
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color=color
            ).pack(anchor="w")

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("games_changed", self._on_games_changed)
        self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
        super().destroy()

    def _adjust_color(self, hex_color: str, amount: int) -> str:
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, min(255, c + amount)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _create_game_card(self, game):  # type: ignore[no-untyped-def]
        theme = self.context.theme.get_active_theme()
        card = ctk.CTkFrame(
            self.scrollable, 
            corner_radius=15, 
            width=320, 
            height=240,
            fg_color=theme.surface_alt,
            border_width=2,
            border_color=theme.accent if game.rating >= 8.0 else "transparent"
        )
        card.grid_propagate(False)

        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        name_label = ctk.CTkLabel(
            header_frame,
            text=game.name,
            font=ctk.CTkFont(size=17, weight="bold"),
            wraplength=280,
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        if game.rating > 0:
            rating_frame = ctk.CTkFrame(header_frame, fg_color=theme.accent, corner_radius=8)
            rating_frame.pack(side="right")
            rating_label = ctk.CTkLabel(
                rating_frame,
                text=f"⭐ {game.rating:.1f}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=theme.background
            )
            rating_label.pack(padx=8, pady=4)

        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=8)

        hours = game.play_time // 60
        minutes = game.play_time % 60
        time_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        time_label = ctk.CTkLabel(
            stats_frame,
            text=f"⏱️ {time_text}",
            font=ctk.CTkFont(size=12),
            text_color=theme.text_muted
        )
        time_label.pack(side="left", padx=(0, 15))

        progress_label = ctk.CTkLabel(
            stats_frame,
            text=f"📈 {game.completion}%",
            font=ctk.CTkFont(size=12),
            text_color=theme.text_muted
        )
        progress_label.pack(side="left")

        if game.completion > 0:
            progress_bar = ctk.CTkProgressBar(
                card,
                width=280,
                height=8,
                corner_radius=4,
                progress_color=theme.accent
            )
            progress_bar.set(game.completion / 100)
            progress_bar.pack(padx=15, pady=(0, 10))

        if game.genres:
            genres_frame = ctk.CTkFrame(card, fg_color="transparent")
            genres_frame.pack(fill="x", padx=15, pady=5)
            
            for genre in game.genres[:3]:
                genre_badge = ctk.CTkLabel(
                    genres_frame,
                    text=genre,
                    font=ctk.CTkFont(size=10),
                    fg_color=theme.base_color,
                    corner_radius=6,
                    text_color=theme.text_muted
                )
                genre_badge.pack(side="left", padx=2, pady=2, ipadx=6, ipady=2)

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=12)

        btn_launch = ctk.CTkButton(
            btn_frame,
            text="▶️ Uruchom",
            command=lambda: self._launch_game(game.id),
            width=110,
            height=35,
            corner_radius=8,
            fg_color=theme.accent,
            hover_color=self._adjust_color(theme.accent, -20),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_launch.pack(side="left", padx=4)

        btn_edit = ctk.CTkButton(
            btn_frame,
            text="✏️ Edytuj",
            command=lambda: self._edit_game(game.id),
            width=90,
            height=35,
            corner_radius=8,
            fg_color=theme.base_color,
            hover_color=theme.surface,
            font=ctk.CTkFont(size=13)
        )
        btn_edit.pack(side="left", padx=4)

        return card

    def _add_game(self) -> None:
        logger.info("Otwieranie formularza dodawania gry")
        dialog = AddGameDialog(self, self.context)
        dialog.grab_set()

    def _edit_game(self, game_id: str) -> None:
        logger.info("Edycja gry: %s", game_id)

    def _launch_game(self, game_id: str) -> None:
        game = self.context.games.get(game_id)
        if game:
            try:
                self.context.games.launch(game)
                self.context.notifications.show("Uruchomiono", f"Gra {game.name} została uruchomiona!")
            except Exception as e:
                logger.error("Błąd uruchamiania gry: %s", e)


class AddGameDialog(ctk.CTkToplevel):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        
        self.title("Dodaj Nową Grę")
        self.geometry("650x620")
        self.resizable(False, False)
        
        self.configure(fg_color=self.theme.background)

        self._setup_ui()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="➕ Dodaj Nową Grę",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=20)

        form = ctk.CTkScrollableFrame(self, fg_color=self.theme.surface, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(
            form, 
            text="Nazwa gry:", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_name = ctk.CTkEntry(form, width=560, height=40, corner_radius=8)
        self.entry_name.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(
            form, 
            text="Ścieżka do pliku wykonywalnego:", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=5)
        path_frame = ctk.CTkFrame(form, fg_color="transparent")
        path_frame.pack(padx=20, pady=(0, 15))
        self.entry_exe = ctk.CTkEntry(path_frame, width=450, height=40, corner_radius=8)
        self.entry_exe.pack(side="left", padx=(0, 8))
        btn_browse = ctk.CTkButton(
            path_frame, 
            text="📁 Przeglądaj", 
            width=100, 
            height=40,
            corner_radius=8,
            command=self._browse_exe
        )
        btn_browse.pack(side="left")

        ctk.CTkLabel(
            form, 
            text="Gatunki (oddzielone przecinkami):", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=5)
        self.entry_genres = ctk.CTkEntry(form, width=560, height=40, corner_radius=8, placeholder_text="np. RPG, Akcja, Przygodowa")
        self.entry_genres.pack(padx=20, pady=(0, 15))

        rating_frame = ctk.CTkFrame(form, fg_color="transparent")
        rating_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            rating_frame, 
            text="Ocena (0-10):", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        self.rating_slider = ctk.CTkSlider(
            rating_frame,
            from_=0,
            to=10,
            number_of_steps=20,
            width=300
        )
        self.rating_slider.set(0)
        self.rating_slider.pack(side="left", padx=(15, 10))
        
        self.rating_label = ctk.CTkLabel(
            rating_frame,
            text="0.0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.accent,
            width=50
        )
        self.rating_label.pack(side="left")
        self.rating_slider.configure(command=self._update_rating_label)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=15)

        btn_save = ctk.CTkButton(
            buttons, 
            text="💾 Zapisz", 
            command=self._save, 
            width=160,
            height=40,
            corner_radius=10,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        btn_save.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            buttons,
            text="❌ Anuluj",
            command=self.destroy,
            width=160,
            height=40,
            corner_radius=10,
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface,
            font=ctk.CTkFont(size=14)
        )
        btn_cancel.pack(side="left", padx=10)

    def _update_rating_label(self, value: float) -> None:
        self.rating_label.configure(text=f"{value:.1f}")

    def _browse_exe(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Wybierz plik wykonywalny",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")]
        )
        if path:
            self.entry_exe.delete(0, "end")
            self.entry_exe.insert(0, path)

    def _save(self) -> None:
        name = self.entry_name.get().strip()
        exe = self.entry_exe.get().strip()

        if not name:
            logger.warning("Nazwa gry nie może być pusta")
            return

        genres = [g.strip() for g in self.entry_genres.get().split(",") if g.strip()]
        rating = float(self.rating_slider.get())

        game_data = {
            "name": name,
            "exe_path": exe,
            "genres": genres,
            "rating": rating,
        }

        self.context.games.add(game_data)
        logger.info("Dodano grę: %s", name)
        self.destroy()
        self.master._load_games()  # type: ignore[attr-defined]
