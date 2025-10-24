"""Plugin profilu użytkownika i kopii zapasowych.

UWAGA: Ten plugin jest przestarzały od wersji 2.2.0
Funkcjonalność profilu została przeniesiona do SettingsView > zakładka Personalizacja.
Ten plik jest zachowany tylko dla kompatybilności wstecznej.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk
from PIL import Image

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class ProfilePlugin(BasePlugin):
    name = "Profile"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Profile")


class ProfileView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        self.avatar_image = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._setup_ui()
        self._load_profile()
        self._load_backups()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="👤 Profil Użytkownika",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)

        self.profile_card = ctk.CTkFrame(self, corner_radius=12, fg_color=self.theme.surface_alt)
        self.profile_card.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self.profile_card.grid_rowconfigure(3, weight=1)
        self.profile_card.grid_columnconfigure(0, weight=1)

        self.backup_card = ctk.CTkFrame(self, corner_radius=12, fg_color=self.theme.surface_alt)
        self.backup_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.backup_card.grid_rowconfigure(2, weight=1)
        self.backup_card.grid_columnconfigure(0, weight=1)

        # Profil - avatar i dane
        avatar_frame = ctk.CTkFrame(self.profile_card, fg_color="transparent")
        avatar_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        avatar_frame.grid_columnconfigure(1, weight=1)

        self.avatar_label = ctk.CTkLabel(avatar_frame, text="", width=120, height=120, corner_radius=60)
        self.avatar_label.grid(row=0, column=0, rowspan=2, padx=(0, 20))

        ctk.CTkLabel(
            avatar_frame,
            text="Nazwa użytkownika:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=1, sticky="w")
        self.entry_username = ctk.CTkEntry(avatar_frame, width=260, height=36)
        self.entry_username.grid(row=1, column=1, sticky="w")

        btn_avatar = ctk.CTkButton(
            avatar_frame,
            text="🖼️ Zmień avatar",
            command=self._change_avatar,
            width=150,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent
        )
        btn_avatar.grid(row=2, column=0, padx=(0, 20), pady=(10, 0))

        btn_save = ctk.CTkButton(
            avatar_frame,
            text="💾 Zapisz profil",
            command=self._save_profile,
            width=160,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_save.grid(row=2, column=1, pady=(10, 0), sticky="w")

        # Statystyki
        stats_frame = ctk.CTkFrame(self.profile_card, fg_color="transparent")
        stats_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        self.stats_widgets = []
        for idx, (icon, label) in enumerate([
            ("🎮", "Liczba gier"),
            ("⏱️", "Godziny gry"),
            ("🏆", "Osiągnięcia"),
            ("🔧", "Mody"),
        ]):
            card = ctk.CTkFrame(stats_frame, fg_color=self.theme.surface, corner_radius=10)
            card.grid(row=idx // 2, column=idx % 2, padx=6, pady=6, sticky="ew")
            icon_label = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=32))
            icon_label.pack(side="left", padx=12, pady=12)
            value_label = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=18, weight="bold"))
            value_label.pack(anchor="w")
            value_label._subtitle = label  # type: ignore[attr-defined]
            subtitle = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color=self.theme.text_muted)
            subtitle.pack(anchor="w")
            self.stats_widgets.append(value_label)

        # Notatki / opis
        ctk.CTkLabel(
            self.profile_card,
            text="Bio / opis:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=2, column=0, padx=20, sticky="w")
        self.bio_text = ctk.CTkTextbox(self.profile_card, width=360, height=120)
        self.bio_text.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Backup karta
        ctk.CTkLabel(
            self.backup_card,
            text="💾 Kopie zapasowe",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        buttons_frame = ctk.CTkFrame(self.backup_card, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, padx=20, sticky="ew")

        btn_backup = ctk.CTkButton(
            buttons_frame,
            text="➕ Utwórz backup",
            command=self._create_backup,
            width=160,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        btn_backup.pack(side="left")

        self.backups_list = ctk.CTkScrollableFrame(self.backup_card, fg_color="transparent")
        self.backups_list.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def _load_profile(self) -> None:
        user = self.context.data_manager.get("user", {})
        username = user.get("username", "Gracz")
        avatar_path = user.get("avatar", "")
        bio = user.get("bio", "")

        self.entry_username.delete(0, "end")
        self.entry_username.insert(0, username)
        self.bio_text.delete("1.0", "end")
        self.bio_text.insert("1.0", bio)
        
        self._load_avatar(avatar_path)
        self._load_stats()

    def _load_avatar(self, avatar_path: str) -> None:
        try:
            if avatar_path and Path(avatar_path).exists():
                image = Image.open(avatar_path).resize((120, 120))
            else:
                placeholder = Path(__file__).resolve().parents[2] / "app" / "data" / "avatar_placeholder.png"
                if placeholder.exists():
                    image = Image.open(placeholder).resize((120, 120))
                else:
                    image = Image.new("RGB", (120, 120), color="#1e293b")
            self.avatar_image = ctk.CTkImage(image, size=(120, 120))
            self.avatar_label.configure(image=self.avatar_image)
        except Exception as e:
            logger.error("Błąd ładowania avatara: %s", e)

    def _load_stats(self) -> None:
        total_games = len(self.context.games.games)
        total_minutes = sum(game.play_time for game in self.context.games.games)
        total_hours = total_minutes // 60
        achievements = self.context.service("achievements").user_progress()
        unlocked = sum(1 for data in achievements.values() if data.get("unlocked"))
        mods = len(self.context.service("mods").list()) if "mods" in self.context.services else 0

        stats_values = [total_games, total_hours, unlocked, mods]
        for widget, value in zip(self.stats_widgets, stats_values):
            widget.configure(text=str(value))

    def _load_backups(self) -> None:
        for widget in self.backups_list.winfo_children():
            widget.destroy()

        backups = self.context.backup.list_backups()
        if not backups:
            placeholder = ctk.CTkLabel(
                self.backups_list,
                text="Brak kopii zapasowych",
                text_color="gray"
            )
            placeholder.pack(pady=20)
            return

        for backup in backups:
            row = ctk.CTkFrame(self.backups_list, fg_color=self.theme.surface, corner_radius=10)
            row.pack(fill="x", pady=4)

            name_label = ctk.CTkLabel(
                row,
                text=f"{backup['name']}\n📅 {backup['date']} | 📦 {backup['size']}",
                anchor="w"
            )
            name_label.pack(side="left", padx=12, pady=12)

            btn_restore = ctk.CTkButton(
                row,
                text="↺ Przywróć",
                command=lambda path=backup['path']: self._restore_backup(path),
                width=100,
                height=32,
                corner_radius=8,
                fg_color=self.theme.accent
            )
            btn_restore.pack(side="right", padx=12)

    def _change_avatar(self) -> None:
        from tkinter import filedialog

        filetypes = [
            ("Pliki graficzne", "*.png;*.jpg;*.jpeg;*.gif"),
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
        user = self.context.data_manager.get("user", {})
        user["username"] = self.entry_username.get().strip() or "Gracz"
        user["bio"] = self.bio_text.get("1.0", "end").strip()
        self.context.data_manager.set("user", user)
        self.context.event_bus.emit("profile_updated", username=user["username"])
        logger.info("Zapisano profil użytkownika")

    def _create_backup(self) -> None:
        path = self.context.backup.create_backup(reason="manual")
        if path:
            self._load_backups()

    def _restore_backup(self, path: str) -> None:
        if self.context.backup.restore_backup(path):
            self._load_profile()
            self._load_backups()
