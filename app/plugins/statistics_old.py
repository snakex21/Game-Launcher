"""Widok statystyk."""
from __future__ import annotations

import logging
from collections import Counter

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .base import BasePlugin

logger = logging.getLogger(__name__)


class StatisticsPlugin(BasePlugin):
    name = "Statistics"

    def register(self, context) -> None:  # type: ignore[no-untyped-def]
        logger.info("Zarejestrowano plugin Statistics")


class StatisticsView(ctk.CTkFrame):
    def __init__(self, parent, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.context = context
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            self,
            text="📊 Statystyki",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.chart_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        self._draw_charts()

    def _draw_charts(self) -> None:
        for child in self.chart_frame.winfo_children():
            child.destroy()

        games = self.context.games.games
        play_times = [game.play_time for game in games]
        labels = [game.name for game in games]

        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(121)
        if play_times:
            ax.barh(labels, play_times, color="#6366f1")
            ax.set_title("Czas gry (min)")
        else:
            ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        
        genres_counter = Counter()
        for game in games:
            genres_counter.update(game.genres)

        ax2 = fig.add_subplot(122)
        if genres_counter:
            labels = list(genres_counter.keys())
            sizes = list(genres_counter.values())
            ax2.pie(sizes, labels=labels, autopct="%1.0f%%")
            ax2.set_title("Podział gatunków")
        else:
            ax2.text(0.5, 0.5, "Brak danych", ha="center", va="center")

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
