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
        self._setup_ui()
        self._load_games()

    def _setup_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        title = ctk.CTkLabel(
            header,
            text="📚 Biblioteka Gier",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=10)

        btn_add = ctk.CTkButton(
            header,
            text="+ Dodaj Grę",
            command=self._add_game,
            width=120
        )
        btn_add.pack(side="right", padx=10)

        btn_refresh = ctk.CTkButton(
            header,
            text="🔄 Odśwież",
            command=self._load_games,
            width=100
        )
        btn_refresh.pack(side="right", padx=5)

        self.scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.scrollable.grid_columnconfigure((0, 1, 2), weight=1)

    def _on_games_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_games()

    def _load_games(self) -> None:
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        games = self.context.games.games

        if not games:
            placeholder = ctk.CTkLabel(
                self.scrollable,
                text="Brak gier w bibliotece.\nKliknij '+ Dodaj Grę' aby rozpocząć!",
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

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("games_changed", self._on_games_changed)
        super().destroy()

    def _create_game_card(self, game):  # type: ignore[no-untyped-def]
        card = ctk.CTkFrame(self.scrollable, corner_radius=10, width=300, height=200)
        card.grid_propagate(False)

        name_label = ctk.CTkLabel(
            card,
            text=game.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=280
        )
        name_label.pack(pady=(15, 5))

        info = f"⏱ {game.play_time} min | 🏆 {game.completion}%"
        info_label = ctk.CTkLabel(card, text=info, font=ctk.CTkFont(size=12))
        info_label.pack(pady=5)

        if game.genres:
            genres_text = ", ".join(game.genres[:3])
            genres_label = ctk.CTkLabel(
                card,
                text=genres_text,
                font=ctk.CTkFont(size=11),
                text_color="gray"
            )
            genres_label.pack(pady=2)

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=10)

        btn_launch = ctk.CTkButton(
            btn_frame,
            text="▶ Uruchom",
            command=lambda: self._launch_game(game.id),
            width=100
        )
        btn_launch.pack(side="left", padx=5)

        btn_edit = ctk.CTkButton(
            btn_frame,
            text="✏ Edytuj",
            command=lambda: self._edit_game(game.id),
            width=80,
            fg_color="gray40",
            hover_color="gray30"
        )
        btn_edit.pack(side="left", padx=5)

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
        self.title("Dodaj Nową Grę")
        self.geometry("600x500")
        self.resizable(False, False)

        self._setup_ui()

    def _setup_ui(self) -> None:
        title = ctk.CTkLabel(
            self,
            text="Dodaj Nową Grę",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=20)

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(form, text="Nazwa gry:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_name = ctk.CTkEntry(form, width=500, height=35)
        self.entry_name.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Ścieżka do pliku .exe:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=5)
        path_frame = ctk.CTkFrame(form, fg_color="transparent")
        path_frame.pack(padx=20, pady=(0, 15))
        self.entry_exe = ctk.CTkEntry(path_frame, width=400, height=35)
        self.entry_exe.pack(side="left", padx=(0, 5))
        btn_browse = ctk.CTkButton(path_frame, text="Przeglądaj...", width=90, command=self._browse_exe)
        btn_browse.pack(side="left")

        ctk.CTkLabel(form, text="Gatunki (oddzielone przecinkami):", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=5)
        self.entry_genres = ctk.CTkEntry(form, width=500, height=35)
        self.entry_genres.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Ocena (0-10):", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=20, pady=5)
        self.entry_rating = ctk.CTkEntry(form, width=100, height=35)
        self.entry_rating.insert(0, "0")
        self.entry_rating.pack(anchor="w", padx=20, pady=(0, 15))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=10)

        btn_save = ctk.CTkButton(buttons, text="💾 Zapisz", command=self._save, width=150)
        btn_save.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            buttons,
            text="❌ Anuluj",
            command=self.destroy,
            width=150,
            fg_color="gray40",
            hover_color="gray30"
        )
        btn_cancel.pack(side="left", padx=10)

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
        try:
            rating = float(self.entry_rating.get())
        except ValueError:
            rating = 0.0

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
