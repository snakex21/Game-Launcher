"""Plugin roadmapy gier - planowanie gier do ukończenia z kalendarzem i archiwum."""
from __future__ import annotations

import calendar
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import TYPE_CHECKING, Literal

import customtkinter as ctk

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)

MONTH_COLORS = {
    1: "#FFB3BA",
    2: "#FFDFBA",
    3: "#FFFFBA",
    4: "#BAFFC9",
    5: "#BAE1FF",
    6: "#FFB3E6",
    7: "#C9C9FF",
    8: "#FFD1DC",
    9: "#E0BBE4",
    10: "#FFDAB9",
    11: "#B5EAD7",
    12: "#C7CEEA",
}

MONTH_NAMES_PL = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień",
}

PRIORITY_COLORS = {
    "high": "#e74c3c",
    "medium": "#f39c12",
    "low": "#95a5a6"
}

PRIORITY_EMOJI = {
    "high": "🔴",
    "medium": "🟡",
    "low": "⚪"
}


class RoadmapPlugin(BasePlugin):
    name = "Roadmap"

    def register(self, context: AppContext) -> None:
        self._migrate_roadmap_data(context)
        logger.info("Zarejestrowano plugin Roadmap")

    def _migrate_roadmap_data(self, context: AppContext) -> None:
        roadmap = context.data_manager.get("roadmap", [])
        migrated = False
        
        for item in roadmap:
            if "color" not in item:
                item["color"] = PRIORITY_COLORS.get(item.get("priority", "medium"), PRIORITY_COLORS["medium"])
                migrated = True
            if "game_id" not in item:
                item["game_id"] = None
                migrated = True
            if "status" not in item:
                item["status"] = "Planowana" if not item.get("completed") else "Ukończona"
                migrated = True
                
        if migrated:
            context.data_manager.set("roadmap", roadmap)
            logger.info("Przeprowadzono migrację danych roadmapy")


class RoadmapView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = self.context.theme.get_active_theme()
        self.current_view: Literal["list", "calendar", "archive"] = "list"
        self.current_month = date.today().month
        self.current_year = date.today().year
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self._setup_event_listeners()
        self._load_current_view()

    def _setup_event_listeners(self) -> None:
        self.context.event_bus.on("game_session_ended", self._on_game_session_ended)

    def _on_game_session_ended(self, **kwargs) -> None:
        game_name = kwargs.get("game_name")
        if not game_name:
            return
            
        roadmap = self.context.data_manager.get("roadmap", [])
        for item in roadmap:
            if item.get("game_name") == game_name and not item.get("completed"):
                target_date_str = item.get("target_date")
                if target_date_str:
                    try:
                        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                        if date.today() >= target_date:
                            self.context.notifications.show(
                                f"🎯 Cel roadmapy osiągnięty!\n'{game_name}' - Czy czas oznaczyć jako ukończone?",
                                duration=5000
                            )
                    except ValueError:
                        pass

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))

        title = ctk.CTkLabel(
            header,
            text="🗺️ Roadmapa Gier",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(side="left", padx=10)

        view_buttons = ctk.CTkFrame(header, fg_color="transparent")
        view_buttons.pack(side="left", padx=20)

        btn_list = ctk.CTkButton(
            view_buttons,
            text="📋 Lista",
            command=lambda: self._switch_view("list"),
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.accent
        )
        btn_list.pack(side="left", padx=2)

        btn_calendar = ctk.CTkButton(
            view_buttons,
            text="📅 Kalendarz",
            command=lambda: self._switch_view("calendar"),
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.surface
        )
        btn_calendar.pack(side="left", padx=2)

        btn_archive = ctk.CTkButton(
            view_buttons,
            text="📦 Archiwum",
            command=lambda: self._switch_view("archive"),
            width=100,
            height=32,
            corner_radius=8,
            fg_color=self.theme.surface
        )
        btn_archive.pack(side="left", padx=2)

        self.view_buttons = {
            "list": btn_list,
            "calendar": btn_calendar,
            "archive": btn_archive
        }

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

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _switch_view(self, view: Literal["list", "calendar", "archive"]) -> None:
        self.current_view = view
        
        for view_name, button in self.view_buttons.items():
            if view_name == view:
                button.configure(fg_color=self.theme.accent)
            else:
                button.configure(fg_color=self.theme.surface)
        
        self._load_current_view()

    def _load_current_view(self) -> None:
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if self.current_view == "list":
            self._load_list_view()
        elif self.current_view == "calendar":
            self._load_calendar_view()
        elif self.current_view == "archive":
            self._load_archive_view()

    def _load_list_view(self) -> None:
        scrollable = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scrollable.grid(row=0, column=0, sticky="nsew")

        roadmap_items = self.context.data_manager.get("roadmap", [])
        in_progress = [item for item in roadmap_items if not item.get("completed", False)]

        if not in_progress:
            placeholder = ctk.CTkLabel(
                scrollable,
                text="Brak gier w roadmapie.\nDodaj gry, które planujesz ukończyć!",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(pady=100)
            return

        section_label = ctk.CTkLabel(
            scrollable,
            text="📝 W trakcie",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        )
        section_label.pack(fill="x", padx=10, pady=(10, 5))

        for item in in_progress:
            card = self._create_roadmap_card(scrollable, item, False)
            card.pack(fill="x", padx=10, pady=5)

    def _load_calendar_view(self) -> None:
        calendar_frame = ctk.CTkFrame(self.content_frame, fg_color=self.theme.surface, corner_radius=12)
        calendar_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        calendar_frame.grid_rowconfigure(2, weight=1)
        calendar_frame.grid_columnconfigure(0, weight=1)

        nav_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        nav_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        btn_prev = ctk.CTkButton(
            nav_frame,
            text="◀",
            command=self._prev_month,
            width=40,
            height=40,
            corner_radius=8,
            fg_color=self.theme.surface_alt
        )
        btn_prev.pack(side="left", padx=5)

        month_label = ctk.CTkLabel(
            nav_frame,
            text=f"{MONTH_NAMES_PL[self.current_month]} {self.current_year}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        month_label.pack(side="left", expand=True)
        self.month_label = month_label

        btn_next = ctk.CTkButton(
            nav_frame,
            text="▶",
            command=self._next_month,
            width=40,
            height=40,
            corner_radius=8,
            fg_color=self.theme.surface_alt
        )
        btn_next.pack(side="right", padx=5)

        weekdays_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        weekdays_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        weekdays_frame.grid_columnconfigure(tuple(range(7)), weight=1)

        weekdays = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
        for i, day in enumerate(weekdays):
            label = ctk.CTkLabel(
                weekdays_frame,
                text=day,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.theme.text_muted
            )
            label.grid(row=0, column=i, padx=2, pady=2)

        days_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        days_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        days_frame.grid_columnconfigure(tuple(range(7)), weight=1)
        
        for i in range(6):
            days_frame.grid_rowconfigure(i, weight=1)

        self._populate_calendar_days(days_frame)

        legend_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        legend_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            legend_frame,
            text="Legenda:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))

        for priority, emoji in PRIORITY_EMOJI.items():
            priority_names = {"high": "Wysoki", "medium": "Średni", "low": "Niski"}
            ctk.CTkLabel(
                legend_frame,
                text=f"{emoji} {priority_names[priority]}",
                font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=5)

    def _populate_calendar_days(self, days_frame: ctk.CTkFrame) -> None:
        roadmap_items = self.context.data_manager.get("roadmap", [])
        
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        for week_idx, week in enumerate(cal):
            for day_idx, day in enumerate(week):
                if day == 0:
                    ctk.CTkFrame(days_frame, fg_color="transparent").grid(
                        row=week_idx, column=day_idx, padx=2, pady=2
                    )
                    continue
                
                day_date = date(self.current_year, self.current_month, day)
                
                games_on_day = self._get_games_for_date(day_date, roadmap_items)
                
                day_frame = ctk.CTkFrame(
                    days_frame,
                    fg_color=self.theme.surface_alt,
                    corner_radius=8
                )
                day_frame.grid(row=week_idx, column=day_idx, sticky="nsew", padx=2, pady=2)
                
                day_label = ctk.CTkLabel(
                    day_frame,
                    text=str(day),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.theme.text_color if day_date >= date.today() else self.theme.text_muted
                )
                day_label.pack(pady=(5, 2))
                
                if games_on_day:
                    for game_info in games_on_day[:3]:
                        game_indicator = ctk.CTkLabel(
                            day_frame,
                            text=f"{game_info['emoji']} {game_info['name'][:8]}...",
                            font=ctk.CTkFont(size=9),
                            text_color=game_info['color']
                        )
                        game_indicator.pack(pady=1)
                    
                    if len(games_on_day) > 3:
                        ctk.CTkLabel(
                            day_frame,
                            text=f"+{len(games_on_day) - 3}",
                            font=ctk.CTkFont(size=8),
                            text_color=self.theme.text_muted
                        ).pack(pady=1)

    def _get_games_for_date(self, check_date: date, roadmap_items: list) -> list:
        games = []
        for item in roadmap_items:
            if item.get("completed"):
                continue
                
            start_date_str = item.get("start_date")
            target_date_str = item.get("target_date")
            
            if not start_date_str or not target_date_str:
                continue
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                
                if start_date <= check_date <= target_date:
                    priority = item.get("priority", "medium")
                    games.append({
                        "name": item.get("game_name", "Nieznana"),
                        "emoji": PRIORITY_EMOJI.get(priority, "⚪"),
                        "color": PRIORITY_COLORS.get(priority, PRIORITY_COLORS["medium"])
                    })
            except ValueError:
                continue
        
        return games

    def _prev_month(self) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        
        self._reload_calendar()

    def _next_month(self) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        
        self._reload_calendar()
    
    def _reload_calendar(self) -> None:
        if hasattr(self, "month_label"):
            self.month_label.configure(text=f"{MONTH_NAMES_PL[self.current_month]} {self.current_year}")
        
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    grid_info = child.grid_info()
                    if grid_info and grid_info.get("row") == 2:
                        for day_widget in child.winfo_children():
                            day_widget.destroy()
                        self._populate_calendar_days(child)
                        return

    def _load_archive_view(self) -> None:
        archive_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        archive_frame.grid(row=0, column=0, sticky="nsew")
        archive_frame.grid_rowconfigure(1, weight=1)
        archive_frame.grid_columnconfigure(0, weight=1)

        filter_frame = ctk.CTkFrame(archive_frame, fg_color="transparent")
        filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            filter_frame,
            text="Filtruj:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=(0, 10))

        self.archive_filter = ctk.CTkSegmentedButton(
            filter_frame,
            values=["Wszystkie", "Ukończone", "W archiwum"],
            command=self._filter_archive
        )
        self.archive_filter.set("Ukończone")
        self.archive_filter.pack(side="left", padx=5)

        scrollable = ctk.CTkScrollableFrame(archive_frame, fg_color="transparent")
        scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.archive_scrollable = scrollable
        self._populate_archive()

        legend_frame = ctk.CTkFrame(archive_frame, fg_color="transparent")
        legend_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            legend_frame,
            text="Kolory miesięcy:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))

        for month_num in range(1, 13):
            color = MONTH_COLORS[month_num]
            month_frame = ctk.CTkFrame(
                legend_frame,
                fg_color=color,
                corner_radius=6,
                width=60,
                height=25
            )
            month_frame.pack(side="left", padx=2)
            
            ctk.CTkLabel(
                month_frame,
                text=MONTH_NAMES_PL[month_num][:3],
                font=ctk.CTkFont(size=9),
                text_color="black"
            ).pack(pady=3)

    def _filter_archive(self, value: str) -> None:
        self._populate_archive()

    def _populate_archive(self) -> None:
        for widget in self.archive_scrollable.winfo_children():
            widget.destroy()

        roadmap_items = self.context.data_manager.get("roadmap", [])
        
        filter_value = self.archive_filter.get() if hasattr(self, "archive_filter") else "Ukończone"
        
        if filter_value == "Ukończone":
            items = [item for item in roadmap_items if item.get("completed", False)]
        elif filter_value == "W archiwum":
            items = [item for item in roadmap_items if item.get("completed", False)]
        else:
            items = roadmap_items

        if not items:
            placeholder = ctk.CTkLabel(
                self.archive_scrollable,
                text="Brak gier w archiwum.",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            placeholder.pack(pady=100)
            return

        for item in items:
            if item.get("completed"):
                card = self._create_archive_card(item)
                card.pack(fill="x", padx=10, pady=5)

    def _create_archive_card(self, item: dict) -> ctk.CTkFrame:
        completion_date_str = item.get("completed_date", "")
        month_color = self.theme.surface_alt
        
        if completion_date_str:
            try:
                completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d")
                month_color = MONTH_COLORS.get(completion_date.month, self.theme.surface_alt)
            except ValueError:
                pass

        card = ctk.CTkFrame(
            self.archive_scrollable,
            corner_radius=12,
            fg_color=month_color,
            border_width=2,
            border_color=self.theme.surface
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        game_name = item.get("game_name", "Nieznana gra")
        
        name_label = ctk.CTkLabel(
            header_frame,
            text=f"✅ {game_name}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="black",
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        dates_frame = ctk.CTkFrame(content, fg_color="transparent")
        dates_frame.pack(fill="x", pady=(8, 0))

        start_date = item.get("start_date", "")
        completion_date = item.get("completed_date", "")
        
        if start_date:
            ctk.CTkLabel(
                dates_frame,
                text=f"📅 Start: {start_date}",
                font=ctk.CTkFont(size=12),
                text_color="black"
            ).pack(side="left", padx=(0, 15))

        if completion_date:
            ctk.CTkLabel(
                dates_frame,
                text=f"🏆 Ukończono: {completion_date}",
                font=ctk.CTkFont(size=12),
                text_color="black"
            ).pack(side="left")

        buttons_frame = ctk.CTkFrame(content, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 0))

        btn_restore = ctk.CTkButton(
            buttons_frame,
            text="↺ Przywróć",
            command=lambda: self._mark_uncompleted(item.get("id")),
            width=120,
            height=32,
            corner_radius=8,
            fg_color=self.theme.surface,
            text_color="white",
            hover_color=self.theme.surface_alt
        )
        btn_restore.pack(side="left", padx=(0, 8))

        btn_delete = ctk.CTkButton(
            buttons_frame,
            text="🗑️ Usuń",
            command=lambda: self._delete_item(item.get("id")),
            width=100,
            height=32,
            corner_radius=8,
            fg_color="#e74c3c",
            text_color="white",
            hover_color="#c0392b"
        )
        btn_delete.pack(side="left")

        return card

    def _create_roadmap_card(self, parent, item: dict, completed: bool) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=self.theme.surface_alt if not completed else self.theme.base_color
        )

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x")

        game_name = item.get("game_name", "Nieznana gra")
        priority = item.get("priority", "medium")

        name_label = ctk.CTkLabel(
            header_frame,
            text=f"{PRIORITY_EMOJI.get(priority, '⚪')} {game_name}",
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
            try:
                target = datetime.strptime(end_date, "%Y-%m-%d").date()
                days_left = (target - date.today()).days
                
                if days_left < 0:
                    time_text = f"🎯 Termin: {end_date} (⚠️ {abs(days_left)} dni temu)"
                    time_color = "#e74c3c"
                elif days_left == 0:
                    time_text = f"🎯 Termin: {end_date} (🔥 Dziś!)"
                    time_color = "#f39c12"
                elif days_left <= 7:
                    time_text = f"🎯 Termin: {end_date} (⏰ {days_left} dni)"
                    time_color = "#f39c12"
                else:
                    time_text = f"🎯 Termin: {end_date} ({days_left} dni)"
                    time_color = self.theme.text_muted
                
                ctk.CTkLabel(
                    dates_frame,
                    text=time_text,
                    font=ctk.CTkFont(size=12),
                    text_color=time_color
                ).pack(side="left")
            except ValueError:
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
            btn_edit = ctk.CTkButton(
                buttons_frame,
                text="✏️ Edytuj",
                command=lambda: self._edit_roadmap_item(item),
                width=100,
                height=32,
                corner_radius=8,
                fg_color=self.theme.surface,
                hover_color=self.theme.surface_alt
            )
            btn_edit.pack(side="left", padx=(0, 8))

            btn_complete = ctk.CTkButton(
                buttons_frame,
                text="✅ Ukończ",
                command=lambda: self._mark_completed(item.get("id")),
                width=120,
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
        dialog = AddRoadmapDialog(self, self.context, None)
        dialog.grab_set()

    def _edit_roadmap_item(self, item: dict) -> None:
        dialog = AddRoadmapDialog(self, self.context, item)
        dialog.grab_set()

    def _mark_completed(self, item_id: str) -> None:
        roadmap = self.context.data_manager.get("roadmap", [])
        game_name = None
        
        for item in roadmap:
            if item.get("id") == item_id:
                item["completed"] = True
                item["completed_date"] = date.today().strftime("%Y-%m-%d")
                item["status"] = "Ukończona"
                game_name = item.get("game_name")
                break
        
        self.context.data_manager.set("roadmap", roadmap)
        self.context.event_bus.emit("roadmap_completed", item_id=item_id, game_name=game_name)
        
        if game_name:
            self.context.notifications.show(
                f"🎉 Gratulacje! Ukończyłeś '{game_name}' z roadmapy!",
                duration=4000
            )
        
        self._load_current_view()

    def _mark_uncompleted(self, item_id: str) -> None:
        roadmap = self.context.data_manager.get("roadmap", [])
        for item in roadmap:
            if item.get("id") == item_id:
                item["completed"] = False
                item.pop("completed_date", None)
                item["status"] = "Planowana"
                break
        self.context.data_manager.set("roadmap", roadmap)
        self.context.event_bus.emit("roadmap_updated")
        self._load_current_view()

    def _delete_item(self, item_id: str) -> None:
        roadmap = [item for item in self.context.data_manager.get("roadmap", []) if item.get("id") != item_id]
        self.context.data_manager.set("roadmap", roadmap)
        self.context.event_bus.emit("roadmap_updated")
        self._load_current_view()


class AddRoadmapDialog(ctk.CTkToplevel):
    def __init__(self, parent, context: AppContext, item: dict | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        self.item = item
        self.is_edit = item is not None
        
        title = "Edytuj wpis roadmapy" if self.is_edit else "Dodaj do Roadmapy"
        self.title(title)
        self.geometry("600x700")
        self.resizable(True, True)
        self.configure(fg_color=self.theme.background)

        self._setup_ui()
        
        if self.is_edit:
            self._populate_fields()

    def _setup_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.theme.surface, corner_radius=0)
        header.pack(fill="x", pady=(0, 20))
        
        title_text = "✏️ Edytuj wpis roadmapy" if self.is_edit else "🗺️ Dodaj Grę do Roadmapy"
        title = ctk.CTkLabel(
            header,
            text=title_text,
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
        self.entry_start.insert(0, date.today().strftime("%Y-%m-%d"))
        self.entry_start.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Data docelowa:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_target = ctk.CTkEntry(form, width=520, height=40, placeholder_text="YYYY-MM-DD")
        self.entry_target.pack(padx=20, pady=(0, 15))

        ctk.CTkLabel(form, text="Notatki:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=5)
        self.entry_notes = ctk.CTkTextbox(form, width=520, height=100)
        self.entry_notes.pack(padx=20, pady=(0, 15))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=15)

        btn_text = "💾 Zapisz" if self.is_edit else "💾 Dodaj"
        btn_save = ctk.CTkButton(
            buttons,
            text=btn_text,
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

    def _populate_fields(self) -> None:
        if not self.item:
            return
            
        game_name = self.item.get("game_name", "")
        if game_name:
            self.game_selector.set(game_name)
        
        priority = self.item.get("priority", "medium")
        priority_map = {"high": "🔴 Wysoki", "medium": "🟡 Średni", "low": "⚪ Niski"}
        self.priority_selector.set(priority_map.get(priority, "🟡 Średni"))
        
        start_date = self.item.get("start_date", "")
        if start_date:
            self.entry_start.delete(0, "end")
            self.entry_start.insert(0, start_date)
        
        target_date = self.item.get("target_date", "")
        if target_date:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, target_date)
        
        notes = self.item.get("notes", "")
        if notes:
            self.entry_notes.delete("1.0", "end")
            self.entry_notes.insert("1.0", notes)

    def _save(self) -> None:
        game_name = self.game_selector.get()
        if game_name == "Brak gier":
            return

        priority_map = {"🔴 Wysoki": "high", "🟡 Średni": "medium", "⚪ Niski": "low"}
        priority = priority_map.get(self.priority_selector.get(), "medium")

        start_date_str = self.entry_start.get().strip()
        target_date_str = self.entry_target.get().strip()
        
        try:
            if start_date_str:
                datetime.strptime(start_date_str, "%Y-%m-%d")
            if target_date_str:
                datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            self.context.notifications.show("❌ Nieprawidłowy format daty. Użyj YYYY-MM-DD", duration=3000)
            return

        roadmap = self.context.data_manager.get("roadmap", [])
        
        if self.is_edit and self.item:
            for item in roadmap:
                if item.get("id") == self.item.get("id"):
                    item["game_name"] = game_name
                    item["priority"] = priority
                    item["start_date"] = start_date_str
                    item["target_date"] = target_date_str
                    item["notes"] = self.entry_notes.get("1.0", "end").strip()
                    item["color"] = PRIORITY_COLORS[priority]
                    break
            
            logger.info("Zaktualizowano wpis roadmapy: %s", game_name)
        else:
            games = self.context.games.games
            game_id = None
            for game in games:
                if game.name == game_name:
                    game_id = game.game_id
                    break

            roadmap_item = {
                "id": str(uuid.uuid4()),
                "game_name": game_name,
                "game_id": game_id,
                "priority": priority,
                "color": PRIORITY_COLORS[priority],
                "start_date": start_date_str,
                "target_date": target_date_str,
                "notes": self.entry_notes.get("1.0", "end").strip(),
                "completed": False,
                "status": "Planowana",
                "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            roadmap.append(roadmap_item)
            logger.info("Dodano do roadmapy: %s", game_name)

        self.context.data_manager.set("roadmap", roadmap)
        self.context.event_bus.emit("roadmap_updated")

        self.destroy()
        self.master._load_current_view()
