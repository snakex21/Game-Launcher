"""Widok statystyk - rozbudowany z analizami wielopoziomowymi."""
from __future__ import annotations

import logging
import threading
from collections import Counter
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from .base import BasePlugin

if TYPE_CHECKING:
    from app.core.app_context import AppContext

logger = logging.getLogger(__name__)


class StatisticsPlugin(BasePlugin):
    name = "Statistics"

    def register(self, context: AppContext) -> None:
        logger.info("Zarejestrowano plugin Statistics")


class StatisticsView(ctk.CTkFrame):
    def __init__(self, parent, context: AppContext) -> None:
        super().__init__(parent)
        self.context = context
        self.theme = context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        
        self.context.event_bus.subscribe("games_changed", self._on_data_changed)
        self.context.event_bus.subscribe("theme_changed", self._on_theme_changed)
        
        self.selected_game_id = None
        self.cached_charts = {}
        self.processing = False
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📊 Statystyki",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(side="left")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(main_container, fg_color=self.theme.surface, corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        left_title = ctk.CTkLabel(
            left_panel,
            text="🎮 Wybierz grę",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        )
        left_title.pack(padx=15, pady=(15, 10))
        
        self.games_list = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.games_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        right_panel = ctk.CTkScrollableFrame(
            main_container, 
            fg_color=self.theme.surface, 
            corner_radius=15
        )
        right_panel.grid(row=0, column=1, sticky="nsew")
        self.stats_container = right_panel

        self._load_data()

    def _on_data_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.cached_charts.clear()
        self._load_data()

    def _on_theme_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.theme = self.context.theme.get_active_theme()
        self.configure(fg_color=self.theme.background)
        self.cached_charts.clear()
        self._load_data()

    def _load_data(self) -> None:
        for widget in self.games_list.winfo_children():
            widget.destroy()

        games = sorted(self.context.games.games, key=lambda x: x.play_time, reverse=True)
        
        all_btn = ctk.CTkButton(
            self.games_list,
            text="📊 Wszystkie gry",
            command=lambda: self._show_game_stats(None),
            fg_color=self.theme.accent if self.selected_game_id is None else self.theme.base_color,
            hover_color=self.theme.surface_alt,
            anchor="w",
            height=35
        )
        all_btn.pack(fill="x", pady=5)

        for game in games:
            hours = game.play_time // 60
            btn_text = f"🎮 {game.name} ({hours}h)"
            btn = ctk.CTkButton(
                self.games_list,
                text=btn_text,
                command=lambda g=game: self._show_game_stats(g.id),
                fg_color=self.theme.accent if self.selected_game_id == game.id else self.theme.base_color,
                hover_color=self.theme.surface_alt,
                anchor="w",
                height=35
            )
            btn.pack(fill="x", pady=5)

        self._show_game_stats(self.selected_game_id)

    def _show_game_stats(self, game_id: str | None) -> None:
        self.selected_game_id = game_id
        
        for widget in self.stats_container.winfo_children():
            widget.destroy()

        if game_id is None:
            self._show_all_games_stats()
        else:
            self._show_single_game_stats(game_id)

    def _format_time_conversions(self, total_minutes: int) -> list[tuple[str, str]]:
        """Konwertuje minuty na różne jednostki czasu."""
        hours = total_minutes // 60
        minutes = total_minutes % 60
        days = hours / 24
        months = days / 30
        years = days / 365
        
        return [
            ("⏱️ Łączny czas", f"{total_minutes} minut"),
            ("🕐 W godzinach", f"{hours}h {minutes}m"),
            ("📅 W dniach", f"{days:.2f} dni"),
            ("📆 W miesiącach", f"{months:.2f} miesięcy"),
            ("📊 W latach", f"{years:.2f} lat"),
        ]

    def _calculate_advanced_stats(self, games: list) -> dict[str, Any]:
        """Oblicza zaawansowane statystyki dla wszystkich gier."""
        if not games:
            return {}
        
        # Zbierz wszystkie sesje
        all_sessions = []
        genre_times = Counter()
        
        for game in games:
            for session in game.sessions:
                all_sessions.append({
                    'game': game,
                    'duration': session.get('duration', 0),
                    'started_at': session.get('started_at', '')
                })
            
            # Agreguj czas per gatunek
            for genre in game.genres:
                genre_times[genre] += game.play_time
        
        # Najdłuższa sesja
        longest_session = max(all_sessions, key=lambda x: x['duration']) if all_sessions else None
        
        # Średnia dzienna (z ostatnich 30 dni)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_sessions = []
        for session in all_sessions:
            try:
                started_at = datetime.fromisoformat(session['started_at'])
                if started_at >= thirty_days_ago:
                    recent_sessions.append(session)
            except (ValueError, TypeError):
                pass
        
        total_recent_minutes = sum(s['duration'] for s in recent_sessions)
        daily_average = total_recent_minutes / 30 if recent_sessions else 0
        
        # Najczęściej grany gatunek
        most_played_genre = genre_times.most_common(1)[0] if genre_times else None
        
        return {
            'longest_session': longest_session,
            'daily_average': daily_average,
            'most_played_genre': most_played_genre,
            'genre_times': genre_times,
        }

    def _show_all_games_stats(self) -> None:
        games = self.context.games.games
        total_time = sum(g.play_time for g in games)
        
        title = ctk.CTkLabel(
            self.stats_container,
            text="📊 Statystyki wszystkich gier",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(padx=20, pady=(20, 15))

        # Podstawowe statystyki czasu
        stats_grid = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=10)

        stats_data = self._format_time_conversions(total_time)
        stats_data.append(("🎮 Liczba gier", str(len(games))))

        for label, value in stats_data:
            stat_frame = ctk.CTkFrame(stats_grid, fg_color=self.theme.surface_alt, corner_radius=10)
            stat_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(size=13),
                text_color=self.theme.text_muted,
                anchor="w"
            ).pack(side="left", padx=15, pady=12)
            
            ctk.CTkLabel(
                stat_frame,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.accent,
                anchor="e"
            ).pack(side="right", padx=15, pady=12)

        # Zaawansowane statystyki
        if games:
            advanced_stats = self._calculate_advanced_stats(games)
            
            advanced_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
            advanced_section.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(
                advanced_section,
                text="📈 Statystyki zaawansowane",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.text
            ).pack(padx=15, pady=(15, 10))
            
            # Średnia dzienna
            daily_avg = advanced_stats['daily_average']
            daily_hours = int(daily_avg // 60)
            daily_mins = int(daily_avg % 60)
            
            stat_row = ctk.CTkFrame(advanced_section, fg_color=self.theme.surface, corner_radius=8)
            stat_row.pack(fill="x", padx=15, pady=5)
            
            ctk.CTkLabel(
                stat_row,
                text="📊 Średnia dzienna (30 dni)",
                font=ctk.CTkFont(size=12),
                text_color=self.theme.text,
                anchor="w"
            ).pack(side="left", padx=10, pady=10)
            
            ctk.CTkLabel(
                stat_row,
                text=f"{daily_hours}h {daily_mins}m",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.theme.accent
            ).pack(side="right", padx=10, pady=10)
            
            # Najczęściej grany gatunek
            if advanced_stats['most_played_genre']:
                genre, minutes = advanced_stats['most_played_genre']
                genre_hours = minutes // 60
                
                stat_row = ctk.CTkFrame(advanced_section, fg_color=self.theme.surface, corner_radius=8)
                stat_row.pack(fill="x", padx=15, pady=5)
                
                ctk.CTkLabel(
                    stat_row,
                    text="🎯 Najczęściej grany gatunek",
                    font=ctk.CTkFont(size=12),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", padx=10, pady=10)
                
                ctk.CTkLabel(
                    stat_row,
                    text=f"{genre} ({genre_hours}h)",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.theme.accent
                ).pack(side="right", padx=10, pady=10)
            
            # Najdłuższa sesja
            if advanced_stats['longest_session']:
                longest = advanced_stats['longest_session']
                duration = longest['duration']
                session_hours = duration // 60
                session_mins = duration % 60
                game_name = longest['game'].name
                
                stat_row = ctk.CTkFrame(advanced_section, fg_color=self.theme.surface, corner_radius=8)
                stat_row.pack(fill="x", padx=15, pady=5)
                
                ctk.CTkLabel(
                    stat_row,
                    text="⏰ Najdłuższa sesja",
                    font=ctk.CTkFont(size=12),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", padx=10, pady=10)
                
                ctk.CTkLabel(
                    stat_row,
                    text=f"{game_name}: {session_hours}h {session_mins}m",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.theme.accent
                ).pack(side="right", padx=10, pady=10)

        # Top 10 najdłużej granych
        if games:
            top_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
            top_section.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(
                top_section,
                text="🏆 Top 10 najdłużej granych",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.text
            ).pack(padx=15, pady=(15, 10))

            top_games = sorted(games, key=lambda x: x.play_time, reverse=True)[:10]
            for idx, game in enumerate(top_games, 1):
                hours = game.play_time // 60
                minutes = game.play_time % 60
                
                game_row = ctk.CTkFrame(top_section, fg_color=self.theme.surface, corner_radius=8)
                game_row.pack(fill="x", padx=15, pady=5)
                
                rank_label = ctk.CTkLabel(
                    game_row,
                    text=f"#{idx}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=self.theme.accent,
                    width=40
                )
                rank_label.pack(side="left", padx=10, pady=10)
                
                ctk.CTkLabel(
                    game_row,
                    text=game.name,
                    font=ctk.CTkFont(size=12),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=5, pady=10)
                
                ctk.CTkLabel(
                    game_row,
                    text=f"{hours}h {minutes}m",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=self.theme.text_muted
                ).pack(side="right", padx=10, pady=10)
        
        # Kalendarz aktywności (heatmapa)
        if games:
            self._show_activity_calendar(games)

    def _show_activity_calendar(self, games: list) -> None:
        """Wyświetla kalendarz aktywności (heatmapę) dla wszystkich gier."""
        calendar_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
        calendar_section.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            calendar_section,
            text="📅 Kalendarz aktywności",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).pack(padx=15, pady=(15, 10))
        
        # Zbierz dane o sesjach per dzień
        daily_activity = {}
        games_per_day = {}
        
        for game in games:
            for session in game.sessions:
                try:
                    started_at = datetime.fromisoformat(session.get('started_at', ''))
                    date_key = started_at.date()
                    duration = session.get('duration', 0)
                    
                    if date_key not in daily_activity:
                        daily_activity[date_key] = 0
                        games_per_day[date_key] = set()
                    
                    daily_activity[date_key] += duration
                    games_per_day[date_key].add(game.name)
                except (ValueError, TypeError):
                    pass
        
        if not daily_activity:
            ctk.CTkLabel(
                calendar_section,
                text="Brak danych o sesjach",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            ).pack(padx=15, pady=(0, 15))
            return
        
        # Przygotuj heatmapę (ostatnie 90 dni)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=89)  # 90 dni
        
        # Wygeneruj wykres w tle
        chart_key = f"calendar_{start_date}_{end_date}"
        if chart_key in self.cached_charts:
            canvas = self.cached_charts[chart_key]
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(0, 15))
        else:
            loading_label = ctk.CTkLabel(
                calendar_section,
                text="⏳ Generowanie kalendarza...",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            )
            loading_label.pack(padx=15, pady=(0, 15))
            
            def generate_calendar():
                try:
                    fig = self._create_activity_heatmap(daily_activity, games_per_day, start_date, end_date)
                    canvas = FigureCanvasTkAgg(fig, calendar_section)
                    self.cached_charts[chart_key] = canvas
                    
                    # Aktualizuj UI w głównym wątku
                    self.after(0, lambda: self._update_calendar_ui(loading_label, canvas))
                except Exception as e:
                    logger.exception("Błąd podczas generowania kalendarza")
                    self.after(0, lambda: loading_label.configure(text=f"❌ Błąd: {e}"))
            
            thread = threading.Thread(target=generate_calendar, daemon=True)
            thread.start()

    def _update_calendar_ui(self, loading_label, canvas):
        """Aktualizuje UI z wygenerowanym kalendarzem."""
        try:
            loading_label.destroy()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(0, 15))
        except Exception as e:
            logger.exception("Błąd podczas aktualizacji UI kalendarza")

    def _create_activity_heatmap(self, daily_activity: dict, games_per_day: dict, start_date, end_date):
        """Tworzy heatmapę aktywności."""
        import numpy as np
        
        fig = Figure(figsize=(12, 3), dpi=100)
        fig.patch.set_facecolor(self.theme.surface)
        ax = fig.add_subplot(111)
        
        # Przygotuj dane
        dates = []
        values = []
        current_date = start_date
        
        while current_date <= end_date:
            dates.append(current_date)
            values.append(daily_activity.get(current_date, 0))
            current_date += timedelta(days=1)
        
        # Przekształć na tygodnie x dni tygodnia
        weeks = len(dates) // 7 + (1 if len(dates) % 7 else 0)
        heatmap_data = np.zeros((7, weeks))
        
        for i, value in enumerate(values):
            week = i // 7
            day = i % 7
            heatmap_data[day, week] = value
        
        # Rysuj heatmapę
        max_value = max(values) if values else 1
        cmap = ax.imshow(heatmap_data, cmap='YlGnBu', aspect='auto', vmin=0, vmax=max_value)
        
        # Etykiety
        ax.set_yticks(range(7))
        ax.set_yticklabels(['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd'])
        ax.set_xlabel('Tygodnie', color=self.theme.text)
        
        # Kolory tła i tekstu
        ax.set_facecolor(self.theme.surface)
        ax.tick_params(colors=self.theme.text)
        for spine in ax.spines.values():
            spine.set_color(self.theme.text_muted)
        
        # Colorbar
        cbar = fig.colorbar(cmap, ax=ax)
        cbar.set_label('Minuty gry', color=self.theme.text)
        cbar.ax.tick_params(colors=self.theme.text)
        
        fig.tight_layout()
        return fig

    def _show_single_game_stats(self, game_id: str) -> None:
        game = self.context.games.get(game_id)
        if not game:
            return

        title = ctk.CTkLabel(
            self.stats_container,
            text=f"🎮 {game.name}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.theme.text
        )
        title.pack(padx=20, pady=(20, 15))

        # Statystyki czasu
        stats_grid = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=10)

        stats_data = self._format_time_conversions(game.play_time)
        stats_data.extend([
            ("📈 Ukończenie", f"{game.completion}%"),
            ("⭐ Ocena", f"{game.rating:.1f}/10"),
            ("🎯 Gatunki", ", ".join(game.genres) if game.genres else "Brak"),
        ])

        for label, value in stats_data:
            stat_frame = ctk.CTkFrame(stats_grid, fg_color=self.theme.surface_alt, corner_radius=10)
            stat_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=ctk.CTkFont(size=13),
                text_color=self.theme.text_muted,
                anchor="w"
            ).pack(side="left", padx=15, pady=12)
            
            ctk.CTkLabel(
                stat_frame,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.accent,
                anchor="e"
            ).pack(side="right", padx=15, pady=12)

        # Wykres progresu ukończenia
        if game.sessions:
            self._show_completion_progress(game)

        # Historia sesji
        if game.sessions:
            sessions_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
            sessions_section.pack(fill="x", padx=20, pady=(20, 10))
            
            ctk.CTkLabel(
                sessions_section,
                text="📜 Historia sesji (ostatnie 10)",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.theme.text
            ).pack(padx=15, pady=(15, 10))

            recent_sessions = sorted(game.sessions, key=lambda x: x.get('started_at', ''), reverse=True)[:10]
            
            for session in recent_sessions:
                started_at = session.get('started_at', '')
                duration = session.get('duration', 0)
                
                try:
                    dt = datetime.fromisoformat(started_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = started_at

                session_row = ctk.CTkFrame(sessions_section, fg_color=self.theme.surface, corner_radius=8)
                session_row.pack(fill="x", padx=15, pady=5)
                
                ctk.CTkLabel(
                    session_row,
                    text=date_str,
                    font=ctk.CTkFont(size=11),
                    text_color=self.theme.text,
                    anchor="w"
                ).pack(side="left", padx=10, pady=8)
                
                ctk.CTkLabel(
                    session_row,
                    text=f"{duration} min",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=self.theme.accent
                ).pack(side="right", padx=10, pady=8)

    def _show_completion_progress(self, game) -> None:
        """Wyświetla wykres progresu ukończenia gry w czasie."""
        progress_section = ctk.CTkFrame(self.stats_container, fg_color=self.theme.base_color, corner_radius=12)
        progress_section.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            progress_section,
            text="📊 Progres ukończenia w czasie",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.text
        ).pack(padx=15, pady=(15, 10))
        
        chart_key = f"progress_{game.id}"
        if chart_key in self.cached_charts:
            canvas = self.cached_charts[chart_key]
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(0, 15))
        else:
            loading_label = ctk.CTkLabel(
                progress_section,
                text="⏳ Generowanie wykresu...",
                font=ctk.CTkFont(size=11),
                text_color=self.theme.text_muted
            )
            loading_label.pack(padx=15, pady=(0, 15))
            
            def generate_chart():
                try:
                    fig = self._create_completion_chart(game)
                    canvas = FigureCanvasTkAgg(fig, progress_section)
                    self.cached_charts[chart_key] = canvas
                    
                    # Aktualizuj UI w głównym wątku
                    self.after(0, lambda: self._update_chart_ui(loading_label, canvas))
                except Exception as e:
                    logger.exception("Błąd podczas generowania wykresu progresu")
                    self.after(0, lambda: loading_label.configure(text=f"❌ Błąd: {e}"))
            
            thread = threading.Thread(target=generate_chart, daemon=True)
            thread.start()

    def _update_chart_ui(self, loading_label, canvas):
        """Aktualizuje UI z wygenerowanym wykresem."""
        try:
            loading_label.destroy()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=(0, 15))
        except Exception as e:
            logger.exception("Błąd podczas aktualizacji UI wykresu")

    def _create_completion_chart(self, game):
        """Tworzy wykres liniowy pokazujący progres ukończenia."""
        fig = Figure(figsize=(10, 4), dpi=100)
        fig.patch.set_facecolor(self.theme.surface)
        ax = fig.add_subplot(111)
        
        # Zbierz dane sesji z czasami
        sessions_data = []
        cumulative_time = 0
        
        for session in sorted(game.sessions, key=lambda x: x.get('started_at', '')):
            try:
                started_at = datetime.fromisoformat(session.get('started_at', ''))
                duration = session.get('duration', 0)
                cumulative_time += duration
                sessions_data.append((started_at, cumulative_time))
            except (ValueError, TypeError):
                pass
        
        if not sessions_data:
            # Brak danych
            ax.text(0.5, 0.5, 'Brak danych o sesjach', 
                   ha='center', va='center', 
                   color=self.theme.text_muted,
                   transform=ax.transAxes)
        else:
            # Rysuj wykres
            dates = [s[0] for s in sessions_data]
            times = [s[1] for s in sessions_data]
            
            # Konwertuj na godziny dla lepszej czytelności
            times_hours = [t / 60 for t in times]
            
            ax.plot(dates, times_hours, color=self.theme.accent, linewidth=2, marker='o', markersize=4)
            ax.fill_between(dates, times_hours, alpha=0.3, color=self.theme.accent)
            
            # Dodaj linię obecnego ukończenia
            if game.completion > 0:
                ax.axhline(y=game.play_time/60, color=self.theme.text_muted, 
                          linestyle='--', linewidth=1, alpha=0.5)
                ax.text(dates[-1], game.play_time/60, f'  {game.completion}% ukończone',
                       color=self.theme.text_muted, va='center')
            
            # Formatowanie
            ax.set_xlabel('Data', color=self.theme.text)
            ax.set_ylabel('Łączny czas gry (godziny)', color=self.theme.text)
            ax.set_facecolor(self.theme.surface)
            ax.grid(True, alpha=0.2, color=self.theme.text_muted)
            
            # Kolory osi i ticków
            ax.tick_params(colors=self.theme.text)
            for spine in ax.spines.values():
                spine.set_color(self.theme.text_muted)
            
            # Format dat na osi X
            if len(dates) > 10:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
        
        fig.tight_layout()
        return fig

    def destroy(self) -> None:
        self.context.event_bus.unsubscribe("games_changed", self._on_data_changed)
        self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
        super().destroy()
