"""Plugin osiągnięć - rozbudowany z możliwością dodawania własnych."""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class AchievementsPlugin(BasePlugin):
    name = "Achievements"

    def register(self, context: AppContext) -> None:
        from app.services.achievement_service import AchievementService
        if "achievements" not in context.services:
            context.register_service("achievements", AchievementService(context.data_manager, context.event_bus))
        
        context.event_bus.subscribe("achievements_changed", self._on_achievement_unlocked)
        
        context.event_bus.subscribe("game_added", lambda **kw: context.service("achievements").check_and_update_progress())
        context.event_bus.subscribe("game_launched", lambda **kw: context.service("achievements").check_and_update_progress())
        context.event_bus.subscribe("roadmap_completed", lambda **kw: context.service("achievements").check_and_update_progress())
        context.event_bus.subscribe("mod_added", lambda **kw: context.service("achievements").check_and_update_progress())
        
        context.service("achievements").unlock("first_launch")
        context.service("achievements").check_and_update_progress()
        
        logger.info("Zarejestrowano plugin Achievements")

    def _on_achievement_unlocked(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        key = kwargs.get("key")
        logger.info(f"Odblokowano osiągnięcie: {key}")


class AchievementsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        
        self.context.event_bus.subscribe("achievements_changed", self._on_achievements_changed)
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self._load_achievements()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="🏆 Osiągnięcia",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)
        
        btn_add = ctk.CTkButton(
            header,
            text="➕ Dodaj Osiągnięcie",
            command=self._add_achievement,
            width=160,
            height=36,
            corner_radius=10,
            fg_color=self.theme.accent,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        btn_add.pack(side="right", padx=10)

        self.stats_frame = ctk.CTkFrame(self, fg_color=self.theme.surface_alt, corner_radius=12)
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        self.scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.scrollable.grid_columnconfigure((0, 1), weight=1)

    def _on_achievements_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._load_achievements()

    def _load_achievements(self) -> None:
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        achievements_service = self.context.service("achievements")
        achievements_service.check_and_update_progress()
        
        catalog = achievements_service.catalog()
        progress = achievements_service.user_progress()
        completion = achievements_service.completion_rate()

        unlocked_count = sum(1 for data in progress.values() if data.get("unlocked"))
        total_points = sum(item["points"] for item in catalog if progress.get(item["key"], {}).get("unlocked"))

        stats_container = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stats_container.pack(fill="both", padx=20, pady=15)

        progress_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        progress_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            progress_frame,
            text=f"Postęp: {unlocked_count}/{len(catalog)}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        progress_bar = ctk.CTkProgressBar(progress_frame, width=300, height=16)
        progress_bar.set(completion)
        progress_bar.pack(anchor="w", pady=(8, 0))

        points_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        points_frame.pack(side="right", padx=(20, 0))

        ctk.CTkLabel(
            points_frame,
            text=f"🌟 {total_points}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.theme.accent
        ).pack()

        ctk.CTkLabel(
            points_frame,
            text="Punkty",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_muted
        ).pack()

        for idx, achievement in enumerate(catalog):
            row = idx // 2
            col = idx % 2
            
            key = achievement["key"]
            user_data = progress.get(key, {})
            unlocked = user_data.get("unlocked", False)
            current_progress = user_data.get("current_progress", 0)
            
            card = self._create_achievement_card(achievement, unlocked, current_progress)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _create_achievement_card(self, achievement: dict, unlocked: bool, current_progress: float) -> ctk.CTkFrame:  # type: ignore[type-arg]
        card = ctk.CTkFrame(
            self.scrollable,
            corner_radius=15,
            fg_color=self.theme.accent if unlocked else self.theme.surface_alt,
            border_width=2,
            border_color=self.theme.accent if unlocked else "transparent"
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=15)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")

        icon_label = ctk.CTkLabel(
            header,
            text=achievement.get("icon", "🏆"),
            font=ctk.CTkFont(size=32)
        )
        icon_label.pack(side="left", padx=(0, 12))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="both", expand=True)

        name_label = ctk.CTkLabel(
            title_frame,
            text=achievement["name"],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x")

        points_label = ctk.CTkLabel(
            title_frame,
            text=f"🌟 {achievement['points']} punktów",
            font=ctk.CTkFont(size=11),
            text_color=self.theme.text_muted if not unlocked else "white",
            anchor="w"
        )
        points_label.pack(fill="x")

        desc_label = ctk.CTkLabel(
            content,
            text=achievement["description"],
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_muted if not unlocked else "white",
            wraplength=280,
            justify="left"
        )
        desc_label.pack(fill="x", pady=(10, 0))

        if not unlocked and achievement.get("condition_type") != "manual":
            target = achievement.get("target_value", 1)
            progress_text = f"Postęp: {current_progress:.0f}/{target}"
            
            progress_label = ctk.CTkLabel(
                content,
                text=progress_text,
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            )
            progress_label.pack(anchor="w", pady=(8, 4))
            
            progress_bar = ctk.CTkProgressBar(content, width=260, height=8)
            progress_bar.set(min(current_progress / target, 1.0) if target > 0 else 0)
            progress_bar.pack(fill="x")

        buttons_frame = ctk.CTkFrame(content, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        if achievement.get("custom", False):
            btn_edit = ctk.CTkButton(
                buttons_frame,
                text="✏️ Edytuj",
                command=lambda: self._edit_achievement(achievement["key"]),
                width=90,
                height=28,
                fg_color=self.theme.base_color if not unlocked else self.theme.surface
            )
            btn_edit.pack(side="left", padx=(0, 5))

            btn_delete = ctk.CTkButton(
                buttons_frame,
                text="🗑️ Usuń",
                command=lambda: self._delete_achievement(achievement["key"]),
                width=80,
                height=28,
                fg_color="#e74c3c" if not unlocked else "#c0392b"
            )
            btn_delete.pack(side="left")

        return card

    def _add_achievement(self) -> None:
        dialog = AddAchievementDialog(self, self.context)
        dialog.grab_set()

    def _edit_achievement(self, key: str) -> None:
        achievements_service = self.context.service("achievements")
        catalog = achievements_service.catalog()
        achievement = next((a for a in catalog if a["key"] == key), None)
        if achievement:
            dialog = EditAchievementDialog(self, self.context, achievement)
            dialog.grab_set()

    def _delete_achievement(self, key: str) -> None:
        from tkinter import messagebox
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz usunąć to osiągnięcie?"):
            catalog = self.context.data_manager.get("achievements_catalog", [])
            catalog = [a for a in catalog if a["key"] != key]
            self.context.data_manager.set("achievements_catalog", catalog)
            
            user = self.context.data_manager.get("user", {})
            achievements = user.get("achievements", {})
            if key in achievements:
                del achievements[key]
                user["achievements"] = achievements
                self.context.data_manager.set("user", user)
            
            self.context.event_bus.emit("achievements_changed")

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("achievements_changed", self._on_achievements_changed)
        super().destroy()


class AddAchievementDialog(ctk.CTkToplevel):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        
        self.title("Dodaj Osiągnięcie")
        self.geometry("650x750")
        self.resizable(True, True)
        self.configure(fg_color=self.theme.background)

        self._setup_ui()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title = ctk.CTkLabel(
            header,
            text="🏆 Dodaj Własne Osiągnięcie",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=20)

        form = ctk.CTkScrollableFrame(self, fg_color=self.theme.surface, corner_radius=12)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(form, text="Nazwa osiągnięcia:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.entry_name = ctk.CTkEntry(form, width=560, height=40)
        self.entry_name.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Opis (opcjonalny):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_desc = ctk.CTkTextbox(form, width=560, height=80)
        self.entry_desc.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Ikona emoji:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_icon = ctk.CTkEntry(form, width=560, height=40, placeholder_text="np. 🎮, 🏆, ⭐")
        self.entry_icon.insert(0, "🏆")
        self.entry_icon.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Punkty:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_points = ctk.CTkEntry(form, width=560, height=40, placeholder_text="np. 10, 25, 50")
        self.entry_points.insert(0, "10")
        self.entry_points.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Warunek zakończenia:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        
        conditions = [
            "Ręczne odblokowywanie",
            "Osiągnąć liczbę gier w bibliotece",
            "Uruchomić X razy grę/gry",
            "Zagrać o określonej godzinie",
            "Osiągnąć X% ukończenia gry",
            "Zagrać X godzin łącznie",
            "Ukończyć X gier",
        ]
        
        self.condition_var = ctk.StringVar(value=conditions[0])
        self.condition_menu = ctk.CTkOptionMenu(form, variable=self.condition_var, values=conditions, width=560, height=40)
        self.condition_menu.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Wartość docelowa:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_target = ctk.CTkEntry(form, width=560, height=40, placeholder_text="np. 10, 50, 100")
        self.entry_target.insert(0, "1")
        self.entry_target.pack(padx=20, pady=(0, 15))

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
        name = self.entry_name.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showwarning("Błąd", "Nazwa osiągnięcia nie może być pusta!")
            return

        condition_map = {
            "Ręczne odblokowywanie": "manual",
            "Osiągnąć liczbę gier w bibliotece": "library_size",
            "Uruchomić X razy grę/gry": "games_launched_count",
            "Zagrać o określonej godzinie": "play_at_hour",
            "Osiągnąć X% ukończenia gry": "completion_percent",
            "Zagrać X godzin łącznie": "play_time_hours",
            "Ukończyć X gier": "games_completed",
        }

        achievement = {
            "key": str(uuid.uuid4()),
            "name": name,
            "description": self.entry_desc.get("1.0", "end").strip() or "Własne osiągnięcie",
            "icon": self.entry_icon.get().strip() or "🏆",
            "points": int(self.entry_points.get().strip() or "10"),
            "condition_type": condition_map.get(self.condition_var.get(), "manual"),
            "target_value": float(self.entry_target.get().strip() or "1"),
            "custom": True,
        }

        catalog = self.context.data_manager.get("achievements_catalog", [])
        catalog.append(achievement)
        self.context.data_manager.set("achievements_catalog", catalog)

        user = self.context.data_manager.get("user", {})
        achievements = user.get("achievements", {})
        achievements[achievement["key"]] = {"unlocked": False, "timestamp": None, "current_progress": 0}
        user["achievements"] = achievements
        self.context.data_manager.set("user", user)

        self.context.event_bus.emit("achievements_changed")
        logger.info("Dodano własne osiągnięcie: %s", name)
        self.destroy()


class EditAchievementDialog(AddAchievementDialog):
    def __init__(self, parent, context: AppContext, achievement: dict) -> None:  # type: ignore[type-arg]
        self.achievement = achievement
        super().__init__(parent, context)
        self.title("Edytuj Osiągnięcie")
        self._populate_fields()

    def _populate_fields(self) -> None:
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, self.achievement["name"])
        
        self.entry_desc.delete("1.0", "end")
        self.entry_desc.insert("1.0", self.achievement.get("description", ""))
        
        self.entry_icon.delete(0, "end")
        self.entry_icon.insert(0, self.achievement.get("icon", "🏆"))
        
        self.entry_points.delete(0, "end")
        self.entry_points.insert(0, str(self.achievement.get("points", 10)))
        
        self.entry_target.delete(0, "end")
        self.entry_target.insert(0, str(self.achievement.get("target_value", 1)))

    def _save(self) -> None:
        name = self.entry_name.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showwarning("Błąd", "Nazwa osiągnięcia nie może być pusta!")
            return

        condition_map = {
            "Ręczne odblokowywanie": "manual",
            "Osiągnąć liczbę gier w bibliotece": "library_size",
            "Uruchomić X razy grę/gry": "games_launched_count",
            "Zagrać o określonej godzinie": "play_at_hour",
            "Osiągnąć X% ukończenia gry": "completion_percent",
            "Zagrać X godzin łącznie": "play_time_hours",
            "Ukończyć X gier": "games_completed",
        }

        catalog = self.context.data_manager.get("achievements_catalog", [])
        for idx, ach in enumerate(catalog):
            if ach["key"] == self.achievement["key"]:
                catalog[idx].update({
                    "name": name,
                    "description": self.entry_desc.get("1.0", "end").strip() or "Własne osiągnięcie",
                    "icon": self.entry_icon.get().strip() or "🏆",
                    "points": int(self.entry_points.get().strip() or "10"),
                    "condition_type": condition_map.get(self.condition_var.get(), "manual"),
                    "target_value": float(self.entry_target.get().strip() or "1"),
                })
                break

        self.context.data_manager.set("achievements_catalog", catalog)
        self.context.event_bus.emit("achievements_changed")
        logger.info("Zaktualizowano osiągnięcie: %s", name)
        self.destroy()
