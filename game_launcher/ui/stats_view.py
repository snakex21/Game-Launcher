"""
Stats View - Widok statystyk z wykresami
AI-Friendly: Matplotlib charts dla czasów gry
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from utils.logger import get_logger
from utils.helpers import format_time


class StatsView(tk.Frame):
    """
    Widok statystyk z wykresami czasu gry.
    
    AI Note:
    - Wykresy słupkowe czasu gry
    - Statystyki per gra
    - Filtry czasowe (tydzień, miesiąc, wszystko)
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok statystyk.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Dane
        self.games = []
        self.sessions = []
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Ładowanie danych
        self.refresh_stats()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'text': '#ecf0f1',
                'accent': '#3498db',
                'chart_bg': '#34495e'
            }
            # Ustawienia matplotlib dla ciemnego motywu
            plt.style.use('dark_background')
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'text': '#2c3e50',
                'accent': '#3498db',
                'chart_bg': '#ffffff'
            }
            plt.style.use('default')
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Header + Chart + Stats table
        """
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Main container (chart + stats)
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=2)
        main_container.grid_columnconfigure(1, weight=1)
        
        # Wykres
        self._create_chart_area(main_container)
        
        # Tabela statystyk
        self._create_stats_table(main_container)
    
    def _create_header(self):
        """Tworzy header z tytułem i filtrami."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Tytuł
        title = tk.Label(
            header,
            text="Statystyki",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Filtry czasowe
        filter_frame = tk.Frame(header, bg=self.colors['bg'])
        filter_frame.pack(side='right', padx=10)
        
        tk.Label(
            filter_frame,
            text="Okres:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left', padx=(0, 5))
        
        self.period_var = tk.StringVar(value='week')
        period_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.period_var,
            values=['week', 'month', 'all'],
            state='readonly',
            width=15
        )
        period_combo.pack(side='left')
        period_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_stats())
        
        # Mapowanie nazw
        self.period_names = {
            'week': 'Ostatni tydzień',
            'month': 'Ostatni miesiąc',
            'all': 'Cały czas'
        }
    
    def _create_chart_area(self, parent):
        """
        Tworzy obszar wykresu.
        
        Args:
            parent: Widget rodzica
        
        AI Note: Matplotlib embedded w Tkinter
        """
        chart_frame = tk.Frame(parent, bg=self.colors['chart_bg'])
        chart_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        # Figura matplotlib
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor=self.colors['chart_bg'])
        self.ax = self.figure.add_subplot(111)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.figure, chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def _create_stats_table(self, parent):
        """
        Tworzy tabelę z podsumowaniem statystyk.
        
        Args:
            parent: Widget rodzica
        """
        table_frame = tk.Frame(parent, bg=self.colors['bg'])
        table_frame.grid(row=0, column=1, sticky='nsew')
        
        # Tytuł tabeli
        tk.Label(
            table_frame,
            text="Top 10 Gier",
            font=('Arial', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        # Treeview
        columns = ('Game', 'Time')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        self.tree.heading('Game', text='Gra')
        self.tree.heading('Time', text='Czas')
        
        self.tree.column('Game', width=200)
        self.tree.column('Time', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def refresh_stats(self):
        """
        Odświeża statystyki i wykres.
        
        AI Note: Wywołaj po zmianie filtru lub nowych sesjach
        """
        # Pobierz dane
        self.games = self.db.get_all_games()
        
        # Filtruj według okresu
        period = self.period_var.get()
        filtered_games = self._filter_by_period(period)
        
        # Aktualizuj wykres
        self._update_chart(filtered_games)
        
        # Aktualizuj tabelę
        self._update_table(filtered_games)
        
        self.logger.info(f"Stats refreshed for period: {period}")
    
    def _filter_by_period(self, period):
        """
        Filtruje gry według okresu czasu.
        
        Args:
            period (str): 'week', 'month', lub 'all'
        
        Returns:
            list: Gry z przefiltrowanym czasem
        
        AI Note: Sumuje sesje w danym okresie
        """
        now = datetime.now()
        
        if period == 'week':
            cutoff = now - timedelta(days=7)
        elif period == 'month':
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        filtered_games = []
        
        for game in self.games:
            # Pobierz sesje dla tej gry
            sessions = self.db.get_game_sessions(game['id'])
            
            # Sumuj czas w okresie
            total_time = 0
            for session in sessions:
                if session['end_time']:
                    session_date = datetime.fromisoformat(session['end_time'])
                    
                    if cutoff is None or session_date >= cutoff:
                        total_time += session.get('duration', 0)
            
            if total_time > 0:
                game_copy = game.copy()
                game_copy['period_playtime'] = total_time
                filtered_games.append(game_copy)
        
        # Sortuj po czasie malejąco
        filtered_games.sort(key=lambda g: g['period_playtime'], reverse=True)
        
        return filtered_games
    
    def _update_chart(self, games):
        """
        Aktualizuje wykres słupkowy.
        
        Args:
            games (list): Lista gier z czasem
        
        AI Note: Top 10 gier jako bar chart
        """
        self.ax.clear()
        
        # Weź top 10
        top_games = games[:10]
        
        if not top_games:
            self.ax.text(
                0.5, 0.5, 'Brak danych',
                ha='center', va='center',
                transform=self.ax.transAxes,
                fontsize=16
            )
            self.canvas.draw()
            return
        
        # Przygotuj dane
        names = [g['name'][:15] + '...' if len(g['name']) > 15 else g['name'] for g in top_games]
        times = [g['period_playtime'] / 3600 for g in top_games]  # Konwersja na godziny
        
        # Kolor wykresu z configu
        chart_color = self.config.get('ui', 'chart_color', default='#3498db')
        
        # Wykres
        bars = self.ax.barh(names, times, color=chart_color)
        
        # Etykiety
        period_name = self.period_names.get(self.period_var.get(), 'Okres')
        self.ax.set_xlabel('Godziny', fontsize=12)
        self.ax.set_title(f'Czas gry - {period_name}', fontsize=14, fontweight='bold')
        
        # Dodaj wartości na słupkach
        for i, (bar, time_val) in enumerate(zip(bars, times)):
            width = bar.get_width()
            self.ax.text(
                width, bar.get_y() + bar.get_height()/2,
                f' {time_val:.1f}h',
                va='center', fontsize=9
            )
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _update_table(self, games):
        """
        Aktualizuje tabelę statystyk.
        
        Args:
            games (list): Lista gier
        """
        # Wyczyść tabelę
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Top 10
        for game in games[:10]:
            time_str = format_time(game['period_playtime'])
            self.tree.insert('', 'end', values=(game['name'], time_str))