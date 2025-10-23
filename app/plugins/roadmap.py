"""Plugin roadmapy gier - planowanie gier do ukończenia."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class RoadmapPlugin(BasePlugin):
    name = "Roadmap"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Roadmap")


class RoadmapView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self._load_roadmap()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="🗺️ Roadmapa Gier",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)

        btn_add = ctk.CTkButton(
            header,
            text="➕ Dodaj do Roadmapy",
            command=self._add_to_roadmap,
            width=160,
            height=36,
            corner_radius=10,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        btn_add.pack(side="right", padx=10)

        self.scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def _load_roadmap(self) -> None:
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        roadmap_items = self.context.data_manager.get("roadmap", [])

        if not roadmap_items:
            placeholder = ctk.CTkLabel(
                self.scrollable,
                text="Brak gier w roadmapie.\nDodaj gry, które planujesz ukończyć!",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(pady=100)
            return

        in_progress = [item for item in roadmap_items if not item.get("completed", False)]
        completed = [item for item in roadmap_items if item.get("completed", False)]

        if in_progress:
            section_label = ctk.CTkLabel(
                self.scrollable,
                text="📝 W trakcie",
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w"
            )
            section_label.pack(fill="x", padx=10, pady=(10, 5))

            for item in in_progress:
                card = self._create_roadmap_card(item, False)
                card.pack(fill="x", padx=10, pady=5)

        if completed:
            section_label = ctk.CTkLabel(
                self.scrollable,
                text="✅ Ukończone",
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w"
            )
            section_label.pack(fill="x", padx=10, pady=(20, 5))

            for item in completed:
                card = self._create_roadmap_card(item, True)
                card.pack(fill="x", padx=10, pady=5)

    def _create_roadmap_card(self, item: dict, completed: bool) -> ctk.CTkFrame:  # type: ignore[type-arg]
        card = ctk.CTkFrame(
            self.scrollable,
            corner_radius=12,
            fg_color=self.theme.surface_alt if not completed else self.theme.base_color
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        game_name = item.get("game_name", "Nieznana gra")
        priority = item.get("priority", "medium")
        priority_colors = {"high": "#e74c3c", "medium": "#f39c12", "low": "#95a5a6"}
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "⚪"}

        name_label = ctk.CTkLabel(
            header_frame,
            text=f"{priority_emoji.get(priority, '⚪')} {game_name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        if completed:
            completed_badge = ctk.CTkLabel(
                header_frame,
                text="✅ Ukończono",
                font=ctk.CTkFont(size=12),
                fg_color="#2ecc71",
                corner_radius=6,
                text_color="white"
            )
            completed_badge.pack(side="right", padx=(10, 0), pady=2, ipadx=8, ipady=4)

        dates_frame = ctk.CTkFrame(content, fg_color="transparent")
        dates_frame.pack(fill="x", pady=(8, 0))

        start_date = item.get("start_date", "")
        end_date = item.get("target_date", "")
        
        if start_date:
            ctk.CTkLabel(
                dates_frame,
                text=f"📅 Start: {start_date}",
                font=ctk.CTkFont(size=12),
                text_color=self.theme.text_muted
            ).pack(side="left", padx=(0, 15))

        if end_date:
            ctk.CTkLabel(
                dates_frame,
                text=f"🎯 Cel: {end_date}",
                font=ctk.CTkFont(size=12),
                text_color=self.theme.text_muted
            ).pack(side="left")

        notes = item.get("notes", "")
        if notes:
            notes_label = ctk.CTkLabel(
                content,
                text=notes,
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted,
                wraplength=700,
                justify="left",
                anchor="w"
            )
            notes_label.pack(fill="x", pady=(8, 0))

        buttons_frame = ctk.CTkFrame(content, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        if not completed:
            btn_complete = ctk.CTkButton(
                buttons_frame,
                text="✅ Oznacz jako ukończone",
                command=lambda: self._mark_completed(item.get("id")),
                width=180,
                height=32,
                corner_radius=8,
                fg_color="#2ecc71",
                hover_color="#27ae60"
            )
            btn_complete.pack(side="left", padx=(0, 8))
        else:
            btn_uncomplete = ctk.CTkButton(
                buttons_frame,
                text="↺ Przywróć",
                command=lambda: self._mark_uncompleted(item.get("id")),
                width=120,
                height=32,
                corner_radius=8,
                fg_color=self.theme.surface,
                hover_color=self.theme.surface_alt
            )
            btn_uncomplete.pack(side="left", padx=(0, 8))

        btn_delete = ctk.CTkButton(
            buttons_frame,
            text="🗑️ Usuń",
            command=lambda: self._delete_item(item.get("id")),
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.base_color,
            hover_color=self.theme.surface
        )
        btn_delete.pack(side="left")

        return card

    def _add_to_roadmap(self) -> None:
        dialog = AddRoadmapDialog(self, self.context)
        dialog.grab_set()

    def _mark_completed(self, item_id: str) -> None:
        roadmap = self.context.data_manager.get("roadmap", [])
        for item in roadmap:
            if item.get("id") == item_id:
                item["completed"] = True
                item["completed_date"] = datetime.now().strftime("%Y-%m-%d")
                break
        self.context.data_manager.set("roadmap", roadmap)
        self.context.event_bus.emit("roadmap_completed", item_id=item_id)
        self._load_roadmap()

    def _mark_uncompleted(self, item_id: str) -> None:
        roadmap = self.context.data_manager.get("roadmap", [])
        for item in roadmap:
            if item.get("id") == item_id:
                item["completed"] = False
                item.pop("completed_date", None)
                break
        self.context.data_manager.set("roadmap", roadmap)
        self._load_roadmap()

    def _delete_item(self, item_id: str) -> None:
        roadmap = [item for item in self.context.data_manager.get("roadmap", []) if item.get("id") != item_id]
        self.context.data_manager.set("roadmap", roadmap)
        self._load_roadmap()


class AddRoadmapDialog(ctk.CTkToplevel):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        
        self.title("Dodaj do Roadmapy")
        self.geometry("600x550")
        self.resizable(False, False)
        self.configure(fg_color=self.theme.background)

        self._setup_ui()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="🗺️ Dodaj Grę do Roadmapy",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=20)

        form = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(form, text="Wybierz grę:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        games = self.context.games.games
        game_names = [game.name for game in games]
        
        self.game_selector = ctk.CTkOptionMenu(form, values=game_names if game_names else ["Brak gier"], width=520, height=40)
        self.game_selector.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Priorytet:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.priority_selector = ctk.CTkOptionMenu(form, values=["🔴 Wysoki", "🟡 Średni", "⚪ Niski"], width=520, height=40)
        self.priority_selector.set("🟡 Średni")
        self.priority_selector.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Data rozpoczęcia:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_start = ctk.CTkEntry(form, width=520, height=40, placeholder_text="YYYY-MM-DD")
        self.entry_start.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entry_start.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Data docelowa:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_target = ctk.CTkEntry(form, width=520, height=40, placeholder_text="YYYY-MM-DD")
        self.entry_target.pack(padx=20, pady=(0, 15))

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
        game_name = self.game_selector.get()
        if game_name == "Brak gier":
            return

        priority_map = {"🔴 Wysoki": "high", "🟡 Średni": "medium", "⚪ Niski": "low"}
        priority = priority_map.get(self.priority_selector.get(), "medium")

        roadmap_item = {
            "id": str(uuid.uuid4()),
            "game_name": game_name,
            "priority": priority,
            "start_date": self.entry_start.get().strip(),
            "target_date": self.entry_target.get().strip(),
            "notes": self.entry_notes.get("1.0", "end").strip(),
            "completed": False,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        roadmap = self.context.data_manager.get("roadmap", [])
        roadmap.append(roadmap_item)
        self.context.data_manager.set("roadmap", roadmap)

        logger.info("Dodano do roadmapy: %s", game_name)
        self.destroy()
        self.master._load_roadmap()  # type: ignore[attr-defined]
