"""Plugin osiągnięć użytkownika."""
from __future__ import annotations

import logging
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
        context.service("achievements").unlock("first_launch")
        
        logger.info("Zarejestrowano plugin Achievements")

    def _on_achievement_unlocked(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        key = kwargs.get("key")
        logger.info(f"Odblokowano osiągnięcie: {key}")


class AchievementsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        
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

        self.stats_frame = ctk.CTkFrame(self, fg_color=self.theme.surface_alt, corner_radius=12)
        self.stats_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        self.scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.scrollable.grid_columnconfigure((0, 1), weight=1)

    def _load_achievements(self) -> None:
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        achievements_service = self.context.service("achievements")
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

        progress_bar = ctk.CTkProgressBar(progress_frame, width=300)
        progress_bar.set(completion)
        progress_bar.pack(anchor="w", pady=(5, 0))

        ctk.CTkLabel(
            progress_frame,
            text=f"{completion*100:.1f}%",
            font=ctk.CTkFont(size=14),
            text_color=self.theme.accent
        ).pack(anchor="w")

        points_frame = ctk.CTkFrame(stats_container, fg_color=self.theme.accent, corner_radius=10)
        points_frame.pack(side="right", padx=(20, 0))

        ctk.CTkLabel(
            points_frame,
            text=f"⭐ {total_points}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        ).pack(padx=20, pady=10)

        for index, item in enumerate(catalog):
            key = item["key"]
            is_unlocked = progress.get(key, {}).get("unlocked", False)
            
            row = index // 2
            col = index % 2
            
            card = self._create_achievement_card(item, is_unlocked, progress.get(key, {}))
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def _create_achievement_card(self, item: dict, is_unlocked: bool, user_data: dict) -> ctk.CTkFrame:  # type: ignore[type-arg]
        card = ctk.CTkFrame(
            self.scrollable,
            corner_radius=12,
            fg_color=self.theme.surface_alt if is_unlocked else self.theme.base_color,
            border_width=2 if is_unlocked else 0,
            border_color=self.theme.accent if is_unlocked else "transparent"
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        trophy_emoji = "🏆" if is_unlocked else "🔒"
        name_label = ctk.CTkLabel(
            header_frame,
            text=f"{trophy_emoji} {item['name']}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        points_badge = ctk.CTkLabel(
            header_frame,
            text=f"⭐ {item['points']}",
            font=ctk.CTkFont(size=12),
            fg_color=self.theme.accent if is_unlocked else self.theme.surface,
            corner_radius=6,
            text_color="white"
        )
        points_badge.pack(side="right", padx=(10, 0), pady=2, ipadx=8, ipady=4)

        desc_label = ctk.CTkLabel(
            content,
            text=item["description"],
            font=ctk.CTkFont(size=12),
            text_color=self.theme.text_muted,
            wraplength=350,
            justify="left",
            anchor="w"
        )
        desc_label.pack(fill="x", pady=(8, 0))

        if is_unlocked and user_data.get("timestamp"):
            timestamp = user_data["timestamp"][:10]
            date_label = ctk.CTkLabel(
                content,
                text=f"🎉 Odblokowano: {timestamp}",
                font=ctk.CTkFont(size=10),
                text_color="#2ecc71"
            )
            date_label.pack(anchor="w", pady=(8, 0))

        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.pack(fill="x", pady=(10, 0))

        if is_unlocked:
            btn_reset = ctk.CTkButton(
                buttons,
                text="↺ Zresetuj",
                command=lambda key=item['key']: self._reset_achievement(key),
                width=100,
                height=30,
                corner_radius=8,
                fg_color=self.theme.base_color,
                hover_color=self.theme.surface
            )
            btn_reset.pack(side="left")
        else:
            btn_unlock = ctk.CTkButton(
                buttons,
                text="🔓 Odblokuj",
                command=lambda key=item['key']: self._unlock_achievement(key),
                width=120,
                height=30,
                corner_radius=8,
                fg_color=self.theme.accent,
                font=ctk.CTkFont(size=13, weight="bold")
            )
            btn_unlock.pack(side="left")

        return card

    def _unlock_achievement(self, key: str) -> None:
        self.context.service("achievements").unlock(key)
        self._load_achievements()

    def _reset_achievement(self, key: str) -> None:
        self.context.service("achievements").lock(key)
        self._load_achievements()
