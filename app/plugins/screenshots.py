"""Plugin do zarządzania zrzutami ekranu."""
from __future__ import annotations

import logging
import os
import platform
import subprocess
from datetime import datetime
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
        
        # Pobierz metadane
        screenshot_service = self.context.service("screenshots")
        metadata = screenshot_service.get_screenshot_metadata(screenshot_path)
        abs_path = screenshot_service._to_absolute_path(screenshot_path)
        
        try:
            # Załaduj i przeskaluj obrazek
            img = Image.open(abs_path)
            img.thumbnail((300, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_label = ctk.CTkLabel(card, image=photo, text="")  # type: ignore[arg-type]
            img_label.image = photo  # type: ignore[attr-defined]  # Zachowaj referencję
            img_label.pack(padx=5, pady=5)
            
            # Kliknięcie otwiera podgląd w aplikacji
            img_label.bind("<Button-1>", lambda e, p=abs_path: self._show_preview(p))
            img_label.bind("<Double-Button-1>", lambda e, p=abs_path: self._open_in_system_browser(p))
            img_label.configure(cursor="hand2")
            
        except Exception as e:
            logger.error("Błąd ładowania obrazka %s: %s", abs_path, e)
            error_label = ctk.CTkLabel(
                card,
                text="❌ Błąd\nładowania",
                text_color="gray",
                width=300,
                height=200
            )
            error_label.pack(padx=5, pady=5)
        
        # Nazwa pliku
        filename = abs_path.split("/")[-1].split("\\")[-1]
        if len(filename) > 30:
            filename = filename[:27] + "..."
        
        name_label = ctk.CTkLabel(
            card,
            text=filename,
            font=ctk.CTkFont(size=11, weight="bold"),
            wraplength=280
        )
        name_label.pack(pady=(0, 3))
        
        # Metadane
        if metadata["exists"]:
            # Rozdzielczość
            resolution_label = ctk.CTkLabel(
                card,
                text=f"📐 {metadata['resolution']}",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            resolution_label.pack(pady=1)
            
            # Data utworzenia
            if metadata["created"]:
                date_str = metadata["created"].strftime("%d.%m.%Y %H:%M")
                date_label = ctk.CTkLabel(
                    card,
                    text=f"📅 {date_str}",
                    font=ctk.CTkFont(size=10),
                    text_color="gray"
                )
                date_label.pack(pady=1)
            
            # Rozmiar pliku
            size_mb = metadata["size"] / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb >= 0.01 else f"{metadata['size'] / 1024:.0f} KB"
            size_label = ctk.CTkLabel(
                card,
                text=f"💾 {size_str}",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            size_label.pack(pady=(1, 5))
        
        # Przyciski
        buttons_frame = ctk.CTkFrame(card, fg_color="transparent")
        buttons_frame.pack(pady=(0, 8), padx=5)
        
        btn_preview = ctk.CTkButton(
            buttons_frame,
            text="🔍 Podgląd",
            command=lambda p=abs_path: self._show_preview(p),
            width=90,
            height=28,
            fg_color=self.theme.accent
        )
        btn_preview.pack(side="left", padx=2)
        
        btn_open = ctk.CTkButton(
            buttons_frame,
            text="🌐 Otwórz",
            command=lambda p=abs_path: self._open_in_system_browser(p),
            width=90,
            height=28,
            fg_color=self.theme.base_color
        )
        btn_open.pack(side="left", padx=2)
        
        btn_delete = ctk.CTkButton(
            buttons_frame,
            text="🗑️",
            command=lambda p=screenshot_path: self._delete_screenshot(p),
            width=40,
            height=28,
            fg_color="#8B0000"
        )
        btn_delete.pack(side="left", padx=2)
        
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

    def _show_preview(self, screenshot_path: str) -> None:
        """Wyświetla podgląd screenshota w oknie aplikacji."""
        try:
            preview_window = ctk.CTkToplevel(self)
            preview_window.title("Podgląd screenshota")
            
            # Pobierz rozdzielczość ekranu
            screen_width = preview_window.winfo_screenwidth()
            screen_height = preview_window.winfo_screenheight()
            
            # Załaduj obraz
            img = Image.open(screenshot_path)
            original_width, original_height = img.size
            
            # Oblicz maksymalny rozmiar (80% ekranu)
            max_width = int(screen_width * 0.8)
            max_height = int(screen_height * 0.8)
            
            # Przeskaluj jeśli potrzeba
            if original_width > max_width or original_height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            # Ustaw rozmiar okna
            window_width = img.width + 40
            window_height = img.height + 100
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            preview_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # Ramka na obraz
            img_frame = ctk.CTkFrame(preview_window, fg_color="transparent")
            img_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
            
            img_label = ctk.CTkLabel(img_frame, image=photo, text="")  # type: ignore[arg-type]
            img_label.image = photo  # type: ignore[attr-defined]
            img_label.pack()
            
            # Ramka na przyciski
            btn_frame = ctk.CTkFrame(preview_window, fg_color="transparent")
            btn_frame.pack(pady=(0, 10))
            
            btn_open = ctk.CTkButton(
                btn_frame,
                text="🌐 Otwórz w przeglądarce systemowej",
                command=lambda: self._open_in_system_browser(screenshot_path),
                fg_color=self.theme.accent
            )
            btn_open.pack(side="left", padx=5)
            
            btn_close = ctk.CTkButton(
                btn_frame,
                text="❌ Zamknij",
                command=preview_window.destroy,
                fg_color=self.theme.base_color
            )
            btn_close.pack(side="left", padx=5)
            
            # ESC zamyka okno
            preview_window.bind("<Escape>", lambda e: preview_window.destroy())
            
            logger.info("Wyświetlono podgląd screenshota: %s", screenshot_path)
            
        except Exception as e:
            logger.error("Błąd wyświetlania podglądu: %s", e)
            from tkinter import messagebox
            messagebox.showerror("Błąd", f"Nie udało się wyświetlić podglądu:\n{e}")
    
    def _open_in_system_browser(self, screenshot_path: str) -> None:
        """Otwiera screenshot w domyślnej aplikacji systemowej."""
        try:
            if platform.system() == "Windows":
                os.startfile(screenshot_path)  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", screenshot_path])
            else:
                subprocess.Popen(["xdg-open", screenshot_path])
            logger.info("Otwarto screenshot w przeglądarce systemowej: %s", screenshot_path)
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
