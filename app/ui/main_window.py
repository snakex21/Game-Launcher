"""Główne okno aplikacji z nawigacją."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context

        self.title("Game Launcher 2.0")
        self.geometry("1400x800")
        
        self.theme = self.context.theme.get_active_theme()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=self.theme.background)

        self._setup_ui()
        self._connect_events()

    def _setup_ui(self) -> None:
        theme = self.theme
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=theme.surface)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🎮 Game Launcher",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=theme.text
        )
        self.logo_label.grid(row=0, column=0, padx=24, pady=(32, 18))

        self.nav_font = ctk.CTkFont(size=14)
        self.nav_font_active = ctk.CTkFont(size=14, weight="bold")

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("Home", "home"),
            ("Biblioteka", "library"),
            ("Statystyki", "statistics"),
            ("Roadmapa", "roadmap"),
            ("Mody", "mods"),
            ("Osiągnięcia", "achievements"),
            ("Screenshoty", "screenshots"),
            ("Newsy", "news"),
            ("Przypomnienia", "reminders"),
            ("Odtwarzacz", "music"),
            ("Profil", "profile"),
            ("Ustawienia", "settings"),
        ]

        icons = {
            "home": "🏠",
            "library": "📚",
            "statistics": "📊",
            "roadmap": "🗺️",
            "mods": "🔧",
            "achievements": "🏆",
            "screenshots": "📸",
            "news": "📰",
            "reminders": "⏰",
            "music": "🎵",
            "profile": "👤",
            "settings": "⚙️"
        }

        for index, (label, view_id) in enumerate(nav_items, start=1):
            icon = icons.get(view_id, "•")
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {label}",
                command=lambda v=view_id: self.show_view(v),
                corner_radius=8,
                height=44,
                border_spacing=12,
                fg_color="transparent",
                hover_color=theme.surface_alt,
                text_color=theme.text_muted,
                anchor="w",
                font=self.nav_font
            )
            btn.grid(row=index, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[view_id] = btn

        # Mini kontrolka muzyki na dole (początkowo ukryta)
        self.music_control_frame = ctk.CTkFrame(self.sidebar, fg_color=theme.base_color, corner_radius=8)
        self.music_control_visible = False
        
        self.music_track_label = ctk.CTkLabel(
            self.music_control_frame,
            text="🎵 Brak playlisty",
            font=ctk.CTkFont(size=10),
            text_color=theme.text_muted
        )
        self.music_track_label.pack(pady=(8, 4))
        
        music_buttons = ctk.CTkFrame(self.music_control_frame, fg_color="transparent")
        music_buttons.pack(pady=(0, 8))
        
        self.music_btn_prev = ctk.CTkButton(
            music_buttons, text="⏮", width=35, height=28,
            command=self._music_previous, fg_color=theme.surface
        )
        self.music_btn_prev.pack(side="left", padx=2)
        
        self.music_btn_play = ctk.CTkButton(
            music_buttons, text="▶", width=35, height=28,
            command=self._music_play, fg_color=theme.accent
        )
        self.music_btn_play.pack(side="left", padx=2)
        
        self.music_btn_next = ctk.CTkButton(
            music_buttons, text="⏭", width=35, height=28,
            command=self._music_next, fg_color=theme.surface
        )
        self.music_btn_next.pack(side="left", padx=2)
        
        # Timer do aktualizacji statusu muzyki
        self._update_music_status()

        self.main_content = ctk.CTkFrame(self, corner_radius=12, fg_color=theme.surface)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        self.current_view = None
        self.current_view_id = ""
        self.show_view("home")

    def _connect_events(self) -> None:
        self.context.event_bus.subscribe("theme_changed", self._on_theme_changed)

    def _on_theme_changed(self, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        logger.info("Zmieniono motyw, aktualizacja UI")
        self.theme = self.context.theme.get_active_theme()
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = self.theme
        self.configure(fg_color=theme.background)
        self.sidebar.configure(fg_color=theme.surface)
        self.logo_label.configure(text_color=theme.text)
        self.main_content.configure(fg_color=theme.surface)
        for button in self.nav_buttons.values():
            button.configure(hover_color=theme.surface_alt)
        if self.current_view and hasattr(self.current_view, "configure"):
            try:
                self.current_view.configure(fg_color=theme.surface)
            except Exception:
                pass
        if self.current_view_id:
            self._update_nav_highlight(self.current_view_id)

    def show_view(self, view_id: str) -> None:
        if self.current_view:
            self.current_view.destroy()

        logger.info("Pokazuję widok: %s", view_id)
        self.current_view_id = view_id

        if view_id == "home":
            from app.plugins.home import HomeView
            self.current_view = HomeView(self.main_content, self.context)
        elif view_id == "library":
            from app.plugins.library import LibraryView
            self.current_view = LibraryView(self.main_content, self.context)
        elif view_id == "statistics":
            from app.plugins.statistics import StatisticsView
            self.current_view = StatisticsView(self.main_content, self.context)
        elif view_id == "roadmap":
            from app.plugins.roadmap import RoadmapView
            self.current_view = RoadmapView(self.main_content, self.context)
        elif view_id == "mods":
            from app.plugins.mods import ModsView
            self.current_view = ModsView(self.main_content, self.context)
        elif view_id == "achievements":
            from app.plugins.achievements import AchievementsView
            self.current_view = AchievementsView(self.main_content, self.context)
        elif view_id == "screenshots":
            from app.plugins.screenshots import ScreenshotsView
            self.current_view = ScreenshotsView(self.main_content, self.context)
        elif view_id == "news":
            from app.plugins.news import NewsView
            self.current_view = NewsView(self.main_content, self.context)
        elif view_id == "reminders":
            from app.plugins.reminders import RemindersView
            self.current_view = RemindersView(self.main_content, self.context)
        elif view_id == "music":
            from app.plugins.music_player import MusicPlayerView
            self.current_view = MusicPlayerView(self.main_content, self.context)
        elif view_id == "profile":
            from app.plugins.profile import ProfileView
            self.current_view = ProfileView(self.main_content, self.context)
        elif view_id == "settings":
            from app.plugins.settings import SettingsView
            self.current_view = SettingsView(self.main_content, self.context)
        else:
            placeholder = ctk.CTkLabel(
                self.main_content,
                text=f"🚧 Widok '{view_id}' w budowie...",
                font=ctk.CTkFont(size=20),
                text_color="gray"
            )
            placeholder.pack(expand=True)
            self.current_view = placeholder

        self._update_nav_highlight(view_id)

        if hasattr(self.current_view, "pack"):
            self.current_view.pack(fill="both", expand=True)

    def _update_nav_highlight(self, view_id: str) -> None:
        theme = self.theme
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == view_id:
                btn.configure(
                    fg_color=theme.accent,
                    text_color=theme.text,
                    hover_color=theme.accent,
                    font=self.nav_font_active
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=theme.text_muted,
                    hover_color=theme.surface_alt,
                    font=self.nav_font
                )

    def _music_play(self) -> None:
        """Odtwarzaj/pauza muzyki."""
        music = self.context.music
        if music.is_paused:
            music.resume()
            self.music_btn_play.configure(text="⏸")
        elif music.is_playing:
            music.pause()
            self.music_btn_play.configure(text="▶")
        else:
            if music.playlist:
                music.play()
                self.music_btn_play.configure(text="⏸")

    def _music_next(self) -> None:
        """Następny utwór."""
        self.context.music.next()

    def _music_previous(self) -> None:
        """Poprzedni utwór."""
        self.context.music.previous()

    def _update_music_status(self) -> None:
        """Aktualizuj status muzyki w mini kontrolce."""
        music = self.context.music
        
        should_show = music.current_track and music.is_playing or music.playlist
        
        if should_show and not self.music_control_visible:
            self.music_control_frame.grid(row=11, column=0, padx=12, pady=12, sticky="ew")
            self.music_control_visible = True
        elif not should_show and self.music_control_visible:
            self.music_control_frame.grid_forget()
            self.music_control_visible = False
        
        if music.current_track and music.is_playing:
            track_name = music.current_track.name
            if len(track_name) > 20:
                track_name = track_name[:17] + "..."
            
            pos = music.get_pos()
            length = music.get_length()
            
            pos_min = int(pos // 60)
            pos_sec = int(pos % 60)
            len_min = int(length // 60)
            len_sec = int(length % 60)
            
            status_text = f"🎵 {track_name}\n{pos_min}:{pos_sec:02d} / {len_min}:{len_sec:02d}"
            self.music_track_label.configure(text=status_text)
            
            if music.is_paused:
                self.music_btn_play.configure(text="▶")
            else:
                self.music_btn_play.configure(text="⏸")
        elif music.playlist:
            self.music_track_label.configure(text="🎵 Playlista gotowa\nKliknij ▶")
            self.music_btn_play.configure(text="▶")
        else:
            self.music_track_label.configure(text="🎵 Brak playlisty")
            self.music_btn_play.configure(text="▶")
        
        # Sprawdź czy utwór się skończył
        if music.is_playing and not music.is_paused:
            pos = music.get_pos()
            length = music.get_length()
            if pos >= length - 1 and length > 0:
                music.next()
        
        # Zaplanuj następną aktualizację
        self.after(500, self._update_music_status)

