"""Plugin do zarządzania zrzutami ekranu."""
from __future__ import annotations

import logging
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image, ImageTk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class ScreenshotsPlugin(BasePlugin):
    name = "Screenshots"

    def register(self, context: AppContext) -> None:
        from app.services.screenshot_service import ScreenshotService
        if "screenshots" not in context.services:
            context.register_service("screenshots", ScreenshotService(context.data_manager, context.event_bus))
        
        logger.info("Zarejestrowano plugin Screenshots")


class ScreenshotsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        self.selected_game_id: str | None = None
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self._load_games()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="📸 Galeria Zrzutów Ekranu",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # Lewa strona - lista gier
        games_sidebar = ctk.CTkFrame(content_frame, fg_color=self.theme.surface_alt, corner_radius=12, width=250)
        games_sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        games_sidebar.grid_propagate(False)

        ctk.CTkLabel(
            games_sidebar,
            text="🎮 Wybierz Grę",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(16, 8))

        self.games_scrollable = ctk.CTkScrollableFrame(games_sidebar, fg_color="transparent")
        self.games_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Prawa strona - galeria screenshotów
        self.gallery_frame = ctk.CTkFrame(content_frame, fg_color=self.theme.surface, corner_radius=12)
        self.gallery_frame.grid(row=0, column=1, sticky="nsew")
        self.gallery_frame.grid_rowconfigure(1, weight=1)
        self.gallery_frame.grid_columnconfigure(0, weight=1)

        gallery_header = ctk.CTkFrame(self.gallery_frame, fg_color="transparent")
        gallery_header.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        self.gallery_title = ctk.CTkLabel(
            gallery_header,
            text="Wybierz grę z listy",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.gallery_title.pack(side="left")

        btn_add = ctk.CTkButton(
            gallery_header,
            text="➕ Dodaj Screenshot",
            command=self._add_screenshot,
            fg_color=self.theme.accent,
            width=150
        )
        btn_add.pack(side="right", padx=5)

        btn_scan = ctk.CTkButton(
            gallery_header,
            text="🔍 Skanuj",
            command=self._scan_screenshots,
            fg_color=self.theme.base_color,
            width=120
        )
        btn_scan.pack(side="right", padx=5)

        self.screenshots_scrollable = ctk.CTkScrollableFrame(self.gallery_frame, fg_color="transparent")
        self.screenshots_scrollable.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.screenshots_scrollable.grid_columnconfigure((0, 1, 2), weight=1)

    def _load_games(self) -> None:
        """Ładuje listę gier do sidebara."""
        for widget in self.games_scrollable.winfo_children():
            widget.destroy()

        games = self.context.games.games

        if not games:
            ctk.CTkLabel(
                self.games_scrollable,
                text="Brak gier\nw bibliotece",
                text_color="gray"
            ).pack(pady=50)
            return

        for game in games:
            screenshots_count = len(game.screenshots)
            
            btn = ctk.CTkButton(
                self.games_scrollable,
                text=f"{game.name}\n📸 {screenshots_count}",
                command=lambda g=game: self._select_game(g.id),
                anchor="w",
                height=60,
                fg_color=self.theme.base_color if self.selected_game_id != game.id else self.theme.accent
            )
            btn.pack(fill="x", pady=2)

    def _select_game(self, game_id: str) -> None:
        """Wybiera grę i wyświetla jej screenshoty."""
        self.selected_game_id = game_id
        game = self.context.games.get(game_id)
        
        if game:
            self.gallery_title.configure(text=f"📸 {game.name}")
        
        self._load_games()  # Odśwież listę gier (zmieni kolor wybranej)
        self._load_screenshots()

    def _load_screenshots(self) -> None:
        """Ładuje screenshoty wybranej gry."""
        for widget in self.screenshots_scrollable.winfo_children():
            widget.destroy()

        if not self.selected_game_id:
            placeholder = ctk.CTkLabel(
                self.screenshots_scrollable,
                text="Wybierz grę z listy po lewej",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, columnspan=3, pady=100)
            return

        screenshots = self.context.service("screenshots").get_game_screenshots(self.selected_game_id)

        if not screenshots:
            placeholder = ctk.CTkLabel(
                self.screenshots_scrollable,
                text="Brak screenshotów dla tej gry\n\nKliknij '➕ Dodaj Screenshot' lub '🔍 Skanuj'",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            placeholder.grid(row=0, column=0, columnspan=3, pady=100)
            return

        for index, screenshot_path in enumerate(screenshots):
            row = index // 3
            col = index % 3
            
            card = self._create_screenshot_card(screenshot_path)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _create_screenshot_card(self, screenshot_path: str) -> ctk.CTkFrame:
        """Tworzy kartę ze screenshotem."""
        card = ctk.CTkFrame(self.screenshots_scrollable, corner_radius=12, fg_color=self.theme.surface_alt)
        
        try:
            # Załaduj i przeskaluj obrazek
            img = Image.open(screenshot_path)
            img.thumbnail((300, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_label = ctk.CTkLabel(card, image=photo, text="")  # type: ignore[arg-type]
            img_label.image = photo  # type: ignore[attr-defined]  # Zachowaj referencję
            img_label.pack(padx=5, pady=5)
            
            img_label.bind("<Button-1>", lambda e, p=screenshot_path: self._open_screenshot(p))
            img_label.configure(cursor="hand2")
            
        except Exception as e:
            logger.error("Błąd ładowania obrazka %s: %s", screenshot_path, e)
            error_label = ctk.CTkLabel(
                card,
                text="❌ Błąd\nładowania",
                text_color="gray",
                width=300,
                height=200
            )
            error_label.pack(padx=5, pady=5)
        
        # Nazwa pliku
        filename = screenshot_path.split("/")[-1].split("\\")[-1]
        if len(filename) > 30:
            filename = filename[:27] + "..."
        
        name_label = ctk.CTkLabel(
            card,
            text=filename,
            font=ctk.CTkFont(size=11),
            wraplength=280
        )
        name_label.pack(pady=(0, 5))
        
        # Przycisk usuwania
        btn_delete = ctk.CTkButton(
            card,
            text="🗑️ Usuń",
            command=lambda p=screenshot_path: self._delete_screenshot(p),
            width=100,
            height=28,
            fg_color=self.theme.base_color
        )
        btn_delete.pack(pady=(0, 8))
        
        return card

    def _add_screenshot(self) -> None:
        """Dodaje screenshot ręcznie."""
        if not self.selected_game_id:
            logger.warning("Nie wybrano gry")
            return

        file_path = filedialog.askopenfilename(
            title="Wybierz zrzut ekranu",
            filetypes=[
                ("Obrazy", "*.png *.jpg *.jpeg *.bmp"),
                ("Wszystkie pliki", "*.*")
            ]
        )

        if file_path:
            self.context.service("screenshots").add_manual_screenshot(self.selected_game_id, file_path)
            self._load_games()
            self._load_screenshots()

    def _open_screenshot(self, screenshot_path: str) -> None:
        """Otwiera screenshot w domyślnej aplikacji systemowej."""
        import os
        import platform
        import subprocess
        
        try:
            if platform.system() == "Windows":
                os.startfile(screenshot_path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", screenshot_path])
            else:
                subprocess.Popen(["xdg-open", screenshot_path])
            logger.info("Otwarto screenshot: %s", screenshot_path)
        except Exception as e:
            logger.error("Błąd otwierania screenshota: %s", e)
            from tkinter import messagebox
            messagebox.showerror("Błąd", f"Nie udało się otworzyć obrazu:\n{e}")

    def _delete_screenshot(self, screenshot_path: str) -> None:
        """Usuwa screenshot."""
        if self.selected_game_id:
            self.context.service("screenshots").remove_screenshot(self.selected_game_id, screenshot_path)
            self._load_games()
            self._load_screenshots()

    def _scan_screenshots(self) -> None:
        """Skanuje foldery w poszukiwaniu screenshotów."""
        if not self.selected_game_id:
            logger.warning("Nie wybrano gry")
            return

        game = self.context.games.get(self.selected_game_id)
        if not game:
            return

        assigned = self.context.service("screenshots").auto_assign_screenshots(self.selected_game_id, game.name)
        
        if assigned > 0:
            self.context.notifications.show("Sukces", f"Znaleziono i przypisano {assigned} screenshotów!")
        else:
            self.context.notifications.show("Info", "Nie znaleziono pasujących screenshotów")
        
        self._load_games()
        self._load_screenshots()
