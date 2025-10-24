"""Widok ustawień z wieloma sekcjami."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from tkinter import colorchooser, filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class SettingsPlugin(BasePlugin):
    name = "Settings"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Settings")


class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        self.avatar_image = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        # Nagłówek
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header,
            text="⚙️ Ustawienia",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(side="left")

        # Tabview z sekcjami
        self.tabview = ctk.CTkTabview(self, corner_radius=12, fg_color=self.theme.surface)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        # Dodaj zakładki
        self.tabview.add("Ogólne")
        self.tabview.add("Personalizacja")
        self.tabview.add("Dane")
        self.tabview.add("Chmura")

        # Konfiguruj każdą zakładkę
        self._setup_general_tab()
        self._setup_personalization_tab()
        self._setup_data_tab()
        self._setup_cloud_tab()

    def _setup_general_tab(self) -> None:
        """Zakładka ogólnych ustawień."""
        tab = self.tabview.tab("Ogólne")
        tab.grid_columnconfigure(0, weight=1)

        # Powiadomienia
        notify_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        notify_card.grid(row=0, column=0, sticky="ew", padx=20, pady=10)

        ctk.CTkLabel(
            notify_card,
            text="🔔 Powiadomienia",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.notify_switch = ctk.CTkSwitch(
            notify_card,
            text="Powiadomienia systemowe",
            command=self._toggle_notifications
        )
        self.notify_switch.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Kanały RSS
        rss_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        rss_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        rss_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            rss_card,
            text="📰 Kanały RSS",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.feeds_box = ctk.CTkTextbox(rss_card, height=150)
        self.feeds_box.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        save_feeds_btn = ctk.CTkButton(
            rss_card,
            text="💾 Zapisz kanały",
            command=self._save_rss,
            fg_color=self.theme.accent,
            height=32
        )
        save_feeds_btn.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="e")

    def _setup_personalization_tab(self) -> None:
        """Zakładka personalizacji."""
        tab = self.tabview.tab("Personalizacja")
        tab.grid_columnconfigure(0, weight=1)

        # Profil użytkownika
        profile_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        profile_card.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        profile_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            profile_card,
            text="👤 Profil Użytkownika",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 15), sticky="w")

        # Avatar
        self.avatar_label = ctk.CTkLabel(
            profile_card,
            text="",
            width=100,
            height=100,
            corner_radius=50
        )
        self.avatar_label.grid(row=1, column=0, rowspan=3, padx=20, pady=(0, 20))

        btn_avatar = ctk.CTkButton(
            profile_card,
            text="🖼️ Zmień avatar",
            command=self._change_avatar,
            width=140,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent
        )
        btn_avatar.grid(row=4, column=0, padx=20, pady=(0, 20))

        # Nazwa użytkownika
        ctk.CTkLabel(
            profile_card,
            text="Nazwa użytkownika:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=1, column=1, padx=(20, 10), pady=(0, 5), sticky="w")

        self.entry_username = ctk.CTkEntry(profile_card, width=300, height=36)
        self.entry_username.grid(row=2, column=1, padx=(20, 10), pady=(0, 10), sticky="w")

        # Bio
        ctk.CTkLabel(
            profile_card,
            text="Bio / opis:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=3, column=1, padx=(20, 10), pady=(0, 5), sticky="w")

        self.bio_text = ctk.CTkTextbox(profile_card, width=300, height=100)
        self.bio_text.grid(row=4, column=1, padx=(20, 10), pady=(0, 20), sticky="w")

        btn_save_profile = ctk.CTkButton(
            profile_card,
            text="💾 Zapisz profil",
            command=self._save_profile,
            width=140,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_save_profile.grid(row=5, column=1, padx=(20, 10), pady=(0, 20), sticky="w")

        # Motyw
        theme_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        theme_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        theme_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            theme_card,
            text="🎨 Motyw i Wygląd",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 15), sticky="w")

        ctk.CTkLabel(
            theme_card,
            text="Motyw:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.theme_option = ctk.CTkOptionMenu(
            theme_card,
            values=[theme.name for theme in self.context.theme.available_themes()],
            command=lambda theme: self.context.theme.set_theme(theme),
            width=200
        )
        self.theme_option.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        ctk.CTkLabel(
            theme_card,
            text="Kolor akcentu:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=2, column=0, padx=20, pady=15, sticky="w")

        self.accent_preview = ctk.CTkLabel(
            theme_card,
            text="█████",
            font=ctk.CTkFont(size=20)
        )
        self.accent_preview.grid(row=2, column=1, padx=20, pady=15, sticky="w")

        accent_button = ctk.CTkButton(
            theme_card,
            text="Wybierz kolor",
            command=self._choose_accent,
            width=140
        )
        accent_button.grid(row=2, column=2, padx=20, pady=15)

        # Zarządzanie motywami
        ctk.CTkLabel(
            theme_card,
            text="Własne motywy:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=3, column=0, padx=20, pady=15, sticky="w")

        buttons_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        buttons_frame.grid(row=3, column=1, columnspan=2, padx=20, pady=15, sticky="w")

        btn_export_theme = ctk.CTkButton(
            buttons_frame,
            text="📤 Eksportuj motyw",
            command=self._export_theme,
            width=140,
            height=32
        )
        btn_export_theme.pack(side="left", padx=(0, 10))

        btn_import_theme = ctk.CTkButton(
            buttons_frame,
            text="📥 Importuj motyw",
            command=self._import_theme,
            width=140,
            height=32
        )
        btn_import_theme.pack(side="left")

        # Spacer na dole
        ctk.CTkLabel(theme_card, text="").grid(row=4, column=0, pady=10)

    def _setup_data_tab(self) -> None:
        """Zakładka zarządzania danymi."""
        tab = self.tabview.tab("Dane")
        tab.grid_columnconfigure(0, weight=1)

        # Kopie zapasowe
        backup_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        backup_card.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        backup_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            backup_card,
            text="💾 Kopie Zapasowe",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # Lokalizacja backupu
        location_frame = ctk.CTkFrame(backup_card, fg_color="transparent")
        location_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        location_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            location_frame,
            text="Lokalizacja kopii:",
            font=ctk.CTkFont(size=13),
            text_color=self.theme.text
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.backup_location_label = ctk.CTkLabel(
            location_frame,
            text="backups/",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_muted,
            anchor="w"
        )
        self.backup_location_label.grid(row=0, column=1, sticky="ew")

        btn_change_backup_location = ctk.CTkButton(
            location_frame,
            text="📁 Zmień",
            command=self._change_backup_location,
            width=100,
            height=28
        )
        btn_change_backup_location.grid(row=0, column=2, padx=(10, 0))

        # Przyciski akcji
        buttons_frame = ctk.CTkFrame(backup_card, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="ew")

        btn_create_backup = ctk.CTkButton(
            buttons_frame,
            text="➕ Utwórz backup",
            command=self._create_backup,
            width=160,
            height=32,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_create_backup.pack(side="left", padx=(0, 10))

        btn_export_backup = ctk.CTkButton(
            buttons_frame,
            text="📤 Eksportuj backup",
            command=self._export_backup,
            width=160,
            height=32
        )
        btn_export_backup.pack(side="left", padx=(0, 10))

        btn_import_backup = ctk.CTkButton(
            buttons_frame,
            text="📥 Importuj backup",
            command=self._import_backup,
            width=160,
            height=32
        )
        btn_import_backup.pack(side="left")

        # Lista backupów
        ctk.CTkLabel(
            backup_card,
            text="Dostępne kopie zapasowe:",
            font=ctk.CTkFont(size=13),
            text_color=self.theme.text
        ).grid(row=3, column=0, padx=20, pady=(20, 10), sticky="w")

        self.backups_list = ctk.CTkScrollableFrame(
            backup_card,
            fg_color=self.theme.surface,
            height=250
        )
        self.backups_list.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def _setup_cloud_tab(self) -> None:
        """Zakładka chmury."""
        tab = self.tabview.tab("Chmura")
        tab.grid_columnconfigure(0, weight=1)

        # Konfiguracja chmury
        cloud_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=self.theme.surface_alt)
        cloud_card.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        cloud_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cloud_card,
            text="☁️ Synchronizacja Chmury",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # Google Drive
        ctk.CTkLabel(
            cloud_card,
            text="Google Drive:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=1, column=0, padx=20, pady=10, sticky="w")

        self.gdrive_switch = ctk.CTkSwitch(
            cloud_card,
            text="Włącz synchronizację",
            command=self._toggle_gdrive
        )
        self.gdrive_switch.grid(row=1, column=1, padx=20, pady=10, sticky="w")

        btn_gdrive_auth = ctk.CTkButton(
            cloud_card,
            text="🔑 Autoryzuj Google Drive",
            command=self._authorize_gdrive,
            width=180,
            height=32,
            state="disabled"
        )
        btn_gdrive_auth.grid(row=2, column=1, padx=20, pady=(0, 10), sticky="w")

        # GitHub
        ctk.CTkLabel(
            cloud_card,
            text="GitHub:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=3, column=0, padx=20, pady=10, sticky="w")

        self.github_switch = ctk.CTkSwitch(
            cloud_card,
            text="Włącz synchronizację",
            command=self._toggle_github
        )
        self.github_switch.grid(row=3, column=1, padx=20, pady=10, sticky="w")

        self.github_token_entry = ctk.CTkEntry(
            cloud_card,
            placeholder_text="Token GitHub",
            width=300,
            height=32,
            state="disabled"
        )
        self.github_token_entry.grid(row=4, column=1, padx=20, pady=(0, 10), sticky="w")

        btn_save_github = ctk.CTkButton(
            cloud_card,
            text="💾 Zapisz token",
            command=self._save_github_token,
            width=140,
            height=32,
            state="disabled"
        )
        btn_save_github.grid(row=5, column=1, padx=20, pady=(0, 10), sticky="w")

        # Akcje synchronizacji
        ctk.CTkLabel(
            cloud_card,
            text="Akcje:",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.text
        ).grid(row=6, column=0, padx=20, pady=(20, 10), sticky="w")

        sync_buttons = ctk.CTkFrame(cloud_card, fg_color="transparent")
        sync_buttons.grid(row=6, column=1, padx=20, pady=(20, 10), sticky="w")

        btn_upload = ctk.CTkButton(
            sync_buttons,
            text="⬆️ Wyślij do chmury",
            command=self._cloud_upload,
            width=140,
            height=32
        )
        btn_upload.pack(side="left", padx=(0, 10))

        btn_download = ctk.CTkButton(
            sync_buttons,
            text="⬇️ Pobierz z chmury",
            command=self._cloud_download,
            width=140,
            height=32
        )
        btn_download.pack(side="left", padx=(0, 10))

        btn_sync = ctk.CTkButton(
            sync_buttons,
            text="🔄 Synchronizuj",
            command=self._cloud_sync,
            width=140,
            height=32,
            fg_color=self.theme.accent
        )
        btn_sync.pack(side="left")

        # Info
        info_label = ctk.CTkLabel(
            cloud_card,
            text="⚠️ Funkcje chmury są w trakcie rozwoju.\nObecnie działają jako placeholder.",
            font=ctk.CTkFont(size=11),
            text_color=self.theme.text_muted,
            justify="left"
        )
        info_label.grid(row=7, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="w")

    def _load_data(self) -> None:
        """Wczytaj dane do wszystkich zakładek."""
        # Ogólne
        current_state = self.context.data_manager.get_nested("settings", "show_notifications", default=True)
        if current_state:
            self.notify_switch.select()
        else:
            self.notify_switch.deselect()

        feeds = self.context.data_manager.get_nested("settings", "rss_feeds", default=[])
        feeds_text = "\n".join(feeds)
        self.feeds_box.delete("1.0", "end")
        self.feeds_box.insert("1.0", feeds_text)

        # Personalizacja
        user = self.context.data_manager.get("user", {})
        username = user.get("username", "Gracz")
        avatar_path = user.get("avatar", "")
        bio = user.get("bio", "")

        self.entry_username.delete(0, "end")
        self.entry_username.insert(0, username)
        self.bio_text.delete("1.0", "end")
        self.bio_text.insert("1.0", bio)

        self._load_avatar(avatar_path)

        self.theme_option.set(self.context.theme.get_active_theme().name)
        self.accent_preview.configure(text_color=self.context.theme.get_active_theme().accent)

        # Dane
        backup_dir = self.context.data_manager.get_nested("settings", "backup_location", default="backups")
        self.backup_location_label.configure(text=str(backup_dir))
        self._load_backups()

        # Chmura
        gdrive_enabled = self.context.data_manager.get_nested("settings", "gdrive_enabled", default=False)
        if gdrive_enabled:
            self.gdrive_switch.select()
        else:
            self.gdrive_switch.deselect()

        github_enabled = self.context.data_manager.get_nested("settings", "github_enabled", default=False)
        if github_enabled:
            self.github_switch.select()
        else:
            self.github_switch.deselect()

    def _load_avatar(self, avatar_path: str) -> None:
        """Wczytaj avatar użytkownika."""
        try:
            if avatar_path and Path(avatar_path).exists():
                image = Image.open(avatar_path).resize((100, 100))
            else:
                # Utwórz placeholder z inicjałem
                from PIL import ImageDraw, ImageFont
                username = self.entry_username.get() or "Gracz"
                image = Image.new("RGB", (100, 100), color=self.theme.accent)
                draw = ImageDraw.Draw(image)
                initial = username[0].upper() if username else "G"
                try:
                    font = ImageFont.truetype("arial.ttf", 50)
                except Exception:
                    font = ImageFont.load_default()

                bbox = draw.textbbox((0, 0), initial, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                draw.text(
                    ((100 - text_w) // 2, (100 - text_h) // 2 - 5),
                    initial,
                    fill="white",
                    font=font
                )

            self.avatar_image = ctk.CTkImage(image, size=(100, 100))
            self.avatar_label.configure(image=self.avatar_image)
        except Exception as e:
            logger.error("Błąd ładowania avatara: %s", e)

    def _change_avatar(self) -> None:
        """Zmień avatar użytkownika."""
        filetypes = [
            ("Pliki graficzne", "*.png *.jpg *.jpeg *.gif"),
            ("Wszystkie pliki", "*.*"),
        ]
        path = filedialog.askopenfilename(title="Wybierz avatar", filetypes=filetypes)
        if path:
            self._load_avatar(path)
            user = self.context.data_manager.get("user", {})
            user["avatar"] = path
            self.context.data_manager.set("user", user)
            self.context.event_bus.emit("profile_updated", avatar_path=path)
            logger.info("Zmieniono avatar na %s", path)

    def _save_profile(self) -> None:
        """Zapisz profil użytkownika."""
        user = self.context.data_manager.get("user", {})
        user["username"] = self.entry_username.get().strip() or "Gracz"
        user["bio"] = self.bio_text.get("1.0", "end").strip()
        self.context.data_manager.set("user", user)
        self.context.event_bus.emit("profile_updated", username=user["username"])
        logger.info("Zapisano profil użytkownika")
        self.context.notification.show("Profil", "Profil użytkownika został zapisany")

    def _toggle_notifications(self) -> None:
        """Przełącz powiadomienia."""
        current = self.context.data_manager.get_nested("settings", "show_notifications", default=True)
        self.context.data_manager.set_nested("settings", "show_notifications", value=not current)

    def _save_rss(self) -> None:
        """Zapisz kanały RSS."""
        feeds_text = self.feeds_box.get("1.0", "end").strip()
        feeds = [line.strip() for line in feeds_text.splitlines() if line.strip()]
        self.context.data_manager.set_nested("settings", "rss_feeds", value=feeds)
        logger.info("Zapisano kanały RSS")
        self.context.notification.show("RSS", "Kanały RSS zostały zapisane")

    def _choose_accent(self) -> None:
        """Wybierz kolor akcentu."""
        color = colorchooser.askcolor(title="Wybierz kolor akcentu")
        if color and color[1]:
            hex_color = color[1]
            self.accent_preview.configure(text_color=hex_color)
            self.context.theme.set_accent(hex_color)

    def _export_theme(self) -> None:
        """Eksportuj aktualny motyw do pliku."""
        theme = self.context.theme.get_active_theme()
        theme_data = {
            "name": theme.name,
            "base_color": theme.base_color,
            "background": theme.background,
            "surface": theme.surface,
            "surface_alt": theme.surface_alt,
            "text": theme.text,
            "text_muted": theme.text_muted,
            "accent": theme.accent,
        }

        filepath = filedialog.asksaveasfilename(
            title="Eksportuj motyw",
            defaultextension=".json",
            filetypes=[("Plik JSON", "*.json"), ("Wszystkie pliki", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(theme_data, f, indent=2, ensure_ascii=False)
                logger.info("Wyeksportowano motyw do %s", filepath)
                self.context.notification.show("Motyw", f"Motyw wyeksportowany do {Path(filepath).name}")
            except Exception as e:
                logger.error("Błąd eksportu motywu: %s", e)
                self.context.notification.show("Błąd", "Nie udało się wyeksportować motywu")

    def _import_theme(self) -> None:
        """Importuj motyw z pliku."""
        filepath = filedialog.askopenfilename(
            title="Importuj motyw",
            filetypes=[("Plik JSON", "*.json"), ("Wszystkie pliki", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    theme_data = json.load(f)

                # Walidacja
                required_keys = ["name", "base_color", "background", "surface", "surface_alt", "text", "text_muted", "accent"]
                if not all(key in theme_data for key in required_keys):
                    raise ValueError("Nieprawidłowy format motywu")

                self.context.theme.set_custom_theme(theme_data)
                self.context.theme.set_theme(theme_data["name"])
                logger.info("Zaimportowano motyw z %s", filepath)
                self.context.notification.show("Motyw", f"Zaimportowano motyw {theme_data['name']}")

                # Odśwież listę motywów
                self.theme_option.configure(values=[theme.name for theme in self.context.theme.available_themes()])
            except Exception as e:
                logger.error("Błąd importu motywu: %s", e)
                self.context.notification.show("Błąd", "Nie udało się zaimportować motywu")

    def _change_backup_location(self) -> None:
        """Zmień lokalizację kopii zapasowych."""
        directory = filedialog.askdirectory(title="Wybierz folder dla kopii zapasowych")
        if directory:
            self.context.data_manager.set_nested("settings", "backup_location", value=directory)
            self.backup_location_label.configure(text=directory)
            # Zaktualizuj BackupService
            self.context.backup.backup_dir = Path(directory)
            self.context.backup.backup_dir.mkdir(exist_ok=True)
            logger.info("Zmieniono lokalizację backupów na %s", directory)
            self._load_backups()

    def _create_backup(self) -> None:
        """Utwórz nową kopię zapasową."""
        path = self.context.backup.create_backup(reason="manual")
        if path:
            self.context.notification.show("Backup", "Kopia zapasowa została utworzona")
            self._load_backups()

    def _export_backup(self) -> None:
        """Eksportuj kopię zapasową do wskazanej lokalizacji."""
        directory = filedialog.askdirectory(title="Wybierz folder docelowy")
        if directory:
            path = self.context.backup.create_backup(reason="export")
            if path:
                import shutil
                dest = Path(directory) / path.name
                shutil.copy2(path, dest)
                logger.info("Wyeksportowano backup do %s", dest)
                self.context.notification.show("Backup", f"Backup wyeksportowany do {dest.name}")

    def _import_backup(self) -> None:
        """Importuj kopię zapasową ze wskazanej lokalizacji."""
        filepath = filedialog.askopenfilename(
            title="Wybierz plik kopii zapasowej",
            filetypes=[("Plik JSON", "*.json"), ("Wszystkie pliki", "*.*")]
        )
        if filepath:
            if self.context.backup.restore_backup(filepath):
                self.context.notification.show("Backup", "Backup został przywrócony")
                self._load_data()
            else:
                self.context.notification.show("Błąd", "Nie udało się przywrócić backupu")

    def _load_backups(self) -> None:
        """Wczytaj listę kopii zapasowych."""
        for widget in self.backups_list.winfo_children():
            widget.destroy()

        backups = self.context.backup.list_backups()
        if not backups:
            placeholder = ctk.CTkLabel(
                self.backups_list,
                text="Brak kopii zapasowych",
                text_color=self.theme.text_muted
            )
            placeholder.pack(pady=20)
            return

        for backup in backups:
            row = ctk.CTkFrame(self.backups_list, fg_color=self.theme.surface_alt, corner_radius=10)
            row.pack(fill="x", pady=4)

            name_label = ctk.CTkLabel(
                row,
                text=f"{backup['name']}\n📅 {backup['date']} | 📦 {backup['size']}",
                anchor="w",
                font=ctk.CTkFont(size=12)
            )
            name_label.pack(side="left", padx=12, pady=12, fill="x", expand=True)

            btn_restore = ctk.CTkButton(
                row,
                text="↺ Przywróć",
                command=lambda path=backup['path']: self._restore_backup(path),
                width=100,
                height=28,
                corner_radius=8,
                fg_color=self.theme.accent
            )
            btn_restore.pack(side="right", padx=12)

    def _restore_backup(self, path: str) -> None:
        """Przywróć kopię zapasową."""
        if self.context.backup.restore_backup(path):
            self.context.notification.show("Backup", "Backup został przywrócony")
            self._load_data()

    def _toggle_gdrive(self) -> None:
        """Przełącz synchronizację Google Drive."""
        current = self.context.data_manager.get_nested("settings", "gdrive_enabled", default=False)
        self.context.data_manager.set_nested("settings", "gdrive_enabled", value=not current)

    def _authorize_gdrive(self) -> None:
        """Autoryzuj Google Drive (placeholder)."""
        logger.info("Autoryzacja Google Drive (placeholder)")
        self.context.notification.show("Google Drive", "Funkcja w trakcie implementacji")

    def _toggle_github(self) -> None:
        """Przełącz synchronizację GitHub."""
        current = self.context.data_manager.get_nested("settings", "github_enabled", default=False)
        self.context.data_manager.set_nested("settings", "github_enabled", value=not current)

    def _save_github_token(self) -> None:
        """Zapisz token GitHub."""
        token = self.github_token_entry.get().strip()
        if token:
            self.context.data_manager.set_nested("settings", "github_token", value=token)
            logger.info("Zapisano token GitHub")
            self.context.notification.show("GitHub", "Token został zapisany")

    def _cloud_upload(self) -> None:
        """Wyślij dane do chmury."""
        self.context.cloud.upload_config()
        self.context.notification.show("Chmura", "Dane wysłane do chmury (placeholder)")

    def _cloud_download(self) -> None:
        """Pobierz dane z chmury."""
        self.context.cloud.download_config()
        self.context.notification.show("Chmura", "Dane pobrane z chmury (placeholder)")

    def _cloud_sync(self) -> None:
        """Synchronizuj z chmurą."""
        self.context.cloud.sync()
        self.context.notification.show("Chmura", "Synchronizacja zakończona (placeholder)")
