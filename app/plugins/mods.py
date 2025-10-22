"""Plugin menedżera modów."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class ModsPlugin(BasePlugin):
    name = "Mods"

    def register(self, context: AppContext) -> None:
        from app.services.mod_service import ModService
        if "mods" not in context.services:
            context.register_service("mods", ModService(context.data_manager, context.event_bus))
        logger.info("Zarejestrowano plugin Mods")


class ModsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        self.selected_game = None
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._setup_ui()
        self._load_games()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="🔧 Menedżer Modów",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)

        self.btn_add_mod = ctk.CTkButton(
            header,
            text="➕ Dodaj Mod",
            command=self._add_mod,
            width=140,
            height=36,
            corner_radius=10,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.btn_add_mod.pack(side="right", padx=10)

        games_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=self.theme.surface_alt, width=240)
        games_frame.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        games_frame.grid_propagate(False)

        games_label = ctk.CTkLabel(
            games_frame,
            text="📚 Twoje Gry",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        games_label.pack(padx=15, pady=(15, 10))

        self.games_list = ctk.CTkScrollableFrame(games_frame, fg_color="transparent")
        self.games_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.mods_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.mods_container.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))

    def _load_games(self) -> None:
        for widget in self.games_list.winfo_children():
            widget.destroy()

        games = self.context.games.games

        if not games:
            placeholder = ctk.CTkLabel(
                self.games_list,
                text="Brak gier",
                text_color="gray"
            )
            placeholder.pack(pady=20)
            return

        for game in games:
            mods_count = len(self.context.service("mods").list_by_game(game.name))
            
            btn = ctk.CTkButton(
                self.games_list,
                text=f"{game.name}\n({mods_count} modów)",
                command=lambda g=game.name: self._select_game(g),
                corner_radius=8,
                height=60,
                fg_color="transparent",
                hover_color=self.theme.surface,
                anchor="w",
                font=ctk.CTkFont(size=13)
            )
            btn.pack(fill="x", pady=2)

    def _select_game(self, game_name: str) -> None:
        self.selected_game = game_name
        self.btn_add_mod.configure(state="normal")
        self._load_mods()

        for widget in self.games_list.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                if game_name in widget.cget("text"):
                    widget.configure(fg_color=self.theme.accent, text_color=self.theme.text)
                else:
                    widget.configure(fg_color="transparent", text_color=self.theme.text_muted)

    def _load_mods(self) -> None:
        for widget in self.mods_container.winfo_children():
            widget.destroy()

        if not self.selected_game:
            placeholder = ctk.CTkLabel(
                self.mods_container,
                text="Wybierz grę z listy po lewej",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(expand=True)
            return

        mods = self.context.service("mods").list_by_game(self.selected_game)

        if not mods:
            placeholder = ctk.CTkLabel(
                self.mods_container,
                text=f"Brak modów dla gry {self.selected_game}\nKliknij '➕ Dodaj Mod' aby rozpocząć!",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(pady=100)
            return

        for mod in mods:
            card = self._create_mod_card(mod)
            card.pack(fill="x", padx=10, pady=5)

    def _create_mod_card(self, mod: dict) -> ctk.CTkFrame:  # type: ignore[type-arg]
        is_enabled = mod.get("status") == "enabled"
        
        card = ctk.CTkFrame(
            self.mods_container,
            corner_radius=12,
            fg_color=self.theme.surface_alt if is_enabled else self.theme.base_color
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        status_emoji = "✅" if is_enabled else "❌"
        name_label = ctk.CTkLabel(
            header_frame,
            text=f"{status_emoji} {mod.get('mod_name', 'Nieznany mod')}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        if mod.get("version"):
            version_badge = ctk.CTkLabel(
                header_frame,
                text=f"v{mod.get('version')}",
                font=ctk.CTkFont(size=11),
                fg_color=self.theme.accent,
                corner_radius=6,
                text_color="white"
            )
            version_badge.pack(side="right", padx=(10, 0), pady=2, ipadx=6, ipady=2)

        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(fill="x", pady=(8, 0))

        if mod.get("author"):
            ctk.CTkLabel(
                info_frame,
                text=f"👤 {mod.get('author')}",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            ).pack(side="left", padx=(0, 15))

        if mod.get("installed_at"):
            ctk.CTkLabel(
                info_frame,
                text=f"📅 {mod.get('installed_at')[:10]}",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            ).pack(side="left")

        if mod.get("notes"):
            notes_label = ctk.CTkLabel(
                content,
                text=mod.get("notes"),
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted,
                wraplength=600,
                justify="left",
                anchor="w"
            )
            notes_label.pack(fill="x", pady=(8, 0))

        buttons_frame = ctk.CTkFrame(content, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        btn_toggle = ctk.CTkButton(
            buttons_frame,
            text="✅ Włączony" if is_enabled else "❌ Wyłączony",
            command=lambda: self._toggle_mod(mod.get("id")),
            width=120,
            height=32,
            corner_radius=8,
            fg_color="#2ecc71" if is_enabled else "#e74c3c",
            hover_color="#27ae60" if is_enabled else "#c0392b"
        )
        btn_toggle.pack(side="left", padx=(0, 8))

        if mod.get("url"):
            btn_url = ctk.CTkButton(
                buttons_frame,
                text="🔗 Link",
                command=lambda: self._open_url(mod.get("url")),
                width=80,
                height=32,
                corner_radius=8,
                fg_color=self.theme.surface,
                hover_color=self.theme.surface_alt
            )
            btn_url.pack(side="left", padx=(0, 8))

        btn_delete = ctk.CTkButton(
            buttons_frame,
            text="🗑️ Usuń",
            command=lambda: self._delete_mod(mod.get("id")),
            width=80,
            height=32,
            corner_radius=8,
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface
        )
        btn_delete.pack(side="left")

        return card

    def _add_mod(self) -> None:
        if not self.selected_game:
            return
        dialog = AddModDialog(self, self.context, self.selected_game)
        dialog.grab_set()

    def _toggle_mod(self, mod_id: str) -> None:
        self.context.service("mods").toggle_status(mod_id)
        self._load_mods()
        self._load_games()

    def _delete_mod(self, mod_id: str) -> None:
        self.context.service("mods").delete_mod(mod_id)
        self._load_mods()
        self._load_games()

    def _open_url(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)


class AddModDialog(ctk.CTkToplevel):
    def __init__(self, parent, context: AppContext, game_name: str) -> None:
        super().__init__(parent)
        self.context = context
        self.game_name = game_name
        self.theme = context.theme.get_active_theme()
        
        self.title(f"Dodaj Mod - {game_name}")
        self.geometry("600x550")
        self.resizable(False, False)
        self.configure(fg_color=self.theme.background)

        self._setup_ui()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text=f"🔧 Dodaj Mod\n{self.game_name}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=20)

        form = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(form, text="Nazwa moda:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_name = ctk.CTkEntry(form, width=520, height=40)
        self.entry_name.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Wersja:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_version = ctk.CTkEntry(form, width=520, height=40, placeholder_text="np. 1.0.0")
        self.entry_version.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Autor:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_author = ctk.CTkEntry(form, width=520, height=40)
        self.entry_author.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Link (opcjonalnie):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_url = ctk.CTkEntry(form, width=520, height=40, placeholder_text="https://...")
        self.entry_url.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Notatki:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_notes = ctk.CTkTextbox(form, width=520, height=80)
        self.entry_notes.pack(padx=20, pady=(0, 15))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=15)

        btn_save = ctk.CTkButton(
            buttons,
            text="💾 Dodaj",
            command=self._save,
            width=150,
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
            width=150,
            height=40,
            corner_radius=10,
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface,
            font=ctk.CTkFont(size=14)
        )
        btn_cancel.pack(side="left", padx=10)

    def _save(self) -> None:
        mod_name = self.entry_name.get().strip()
        if not mod_name:
            logger.warning("Nazwa moda nie może być pusta")
            return

        mod_data = {
            "game_name": self.game_name,
            "mod_name": mod_name,
            "version": self.entry_version.get().strip() or "1.0",
            "author": self.entry_author.get().strip(),
            "url": self.entry_url.get().strip(),
            "notes": self.entry_notes.get("1.0", "end").strip(),
            "status": "enabled"
        }

        self.context.service("mods").add_mod(mod_data)
        logger.info("Dodano mod: %s", mod_name)
        self.destroy()
        self.master._load_mods()  # type: ignore[attr-defined]
        self.master._load_games()  # type: ignore[attr-defined]
