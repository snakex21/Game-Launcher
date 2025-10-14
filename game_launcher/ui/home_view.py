"""
Home View - Dashboard / Strona główna
AI-Friendly: Podsumowanie aktywności
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from utils.logger import get_logger
from utils.helpers import format_time


class HomeView(tk.Frame):
    """
    Widok strony głównej - dashboard.
    
    AI Note:
    - Ostatnio grane gry
    - Statystyki dzienne/tygodniowe
    - Skróty do funkcji
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok home.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Ładowanie danych
        self.refresh_data()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'card_bg': '#34495e',
                'text': '#ecf0f1',
                'accent': '#3498db',
                'success': '#27ae60'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'card_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'success': '#27ae60'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """Tworzy interfejs użytkownika."""
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Main container
        main = tk.Frame(self, bg=self.colors['bg'])
        main.grid(row=1, column=0, sticky='nsew', padx=20, pady=10)
        
        # Grid dla kart
        main.grid_rowconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        
        # Stats cards (górny rząd)
        self._create_stats_cards(main)
        
        # Ostatnio grane (lewy dolny)
        self._create_recent_games_card(main)
        
        # Quick actions (prawy dolny)
        self._create_quick_actions_card(main)
    
    def _create_header(self):
        """Tworzy header z powitaniem."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Powitanie
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Dzień dobry"
        elif hour < 18:
            greeting = "Dzień dobry"
        else:
            greeting = "Dobry wieczór"
        
        username = self.config.get('app', 'username', default='Graczu')
        
        title = tk.Label(
            header,
            text=f"👋 {greeting}, {username}!",
            font=('Arial', 20, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Data
        date_str = datetime.now().strftime('%A, %d %B %Y')
        date_label = tk.Label(
            header,
            text=date_str,
            font=('Arial', 11),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        date_label.pack(side='right', padx=10)
    
    def _create_stats_cards(self, parent):
        """Tworzy karty ze statystykami."""
        # Total games
        self.total_games_card = self._create_stat_card(
            parent, "🎮 Gier w bibliotece", "0", row=0, col=0
        )
        
        # Total playtime
        self.total_playtime_card = self._create_stat_card(
            parent, "⏱️ Całkowity czas gry", "0h", row=0, col=1
        )
    
    def _create_stat_card(self, parent, title, value, row, col):
        """
        Tworzy pojedynczą kartę statystyki.
        
        Args:
            parent: Widget rodzica
            title (str): Tytuł
            value (str): Wartość
            row (int): Rząd w grid
            col (int): Kolumna w grid
        
        Returns:
            dict: {'title_label', 'value_label'}
        """
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.grid(row=row, column=col, sticky='nsew', padx=10, pady=10)
        
        inner = tk.Frame(card, bg=self.colors['card_bg'])
        inner.pack(expand=True, padx=30, pady=30)
        
        title_label = tk.Label(
            inner,
            text=title,
            font=('Arial', 12),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        title_label.pack()
        
        value_label = tk.Label(
            inner,
            text=value,
            font=('Arial', 28, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        value_label.pack(pady=10)
        
        return {'title_label': title_label, 'value_label': value_label}
    
    def _create_recent_games_card(self, parent):
        """Tworzy kartę z ostatnio granymi."""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        
        # Tytuł
        title = tk.Label(
            card,
            text="🕒 Ostatnio Grane",
            font=('Arial', 14, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        title.pack(pady=15)
        
        # Lista
        self.recent_tree = ttk.Treeview(
            card,
            columns=('Game', 'Time'),
            show='headings',
            height=8
        )
        
        self.recent_tree.heading('Game', text='Gra')
        self.recent_tree.heading('Time', text='Ostatnio')
        
        self.recent_tree.column('Game', width=250)
        self.recent_tree.column('Time', width=150)
        
        self.recent_tree.pack(fill='both', expand=True, padx=15, pady=(0, 15))
    
    def _create_quick_actions_card(self, parent):
        """Tworzy kartę z quick actions."""
        card = tk.Frame(parent, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.grid(row=1, column=1, sticky='nsew', padx=10, pady=10)
        
        # Tytuł
        title = tk.Label(
            card,
            text="⚡ Szybkie Akcje",
            font=('Arial', 14, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        title.pack(pady=15)
        
        # Przyciski
        actions_frame = tk.Frame(card, bg=self.colors['card_bg'])
        actions_frame.pack(expand=True, padx=20, pady=20)
        
        actions = [
            ("📚 Biblioteka", 'library'),
            ("📊 Statystyki", 'stats'),
            ("🗓️ Roadmapa", 'roadmap'),
            ("🏆 Osiągnięcia", 'achievements'),
            ("📰 Newsy", 'news'),
            ("⚙️ Ustawienia", 'settings')
        ]
        
        for text, view_name in actions:
            btn = tk.Button(
                actions_frame,
                text=text,
                font=('Arial', 11),
                bg=self.colors['accent'],
                fg='white',
                cursor='hand2',
                relief='flat',
                padx=20,
                pady=10,
                width=20,
                command=lambda v=view_name: self._navigate_to(v)
            )
            btn.pack(pady=5)
    
    def refresh_data(self):
        """Odświeża dane na dashboardzie."""
        # Total games
        games = self.db.get_all_games()
        self.total_games_card['value_label'].config(text=str(len(games)))
        
        # Total playtime
        total_time = sum(g.get('total_playtime', 0) for g in games)
        self.total_playtime_card['value_label'].config(text=format_time(total_time))
        
        # Recent games
        recent_games = sorted(
            [g for g in games if g.get('last_played')],
            key=lambda g: g['last_played'],
            reverse=True
        )[:10]
        
        # Wyczyść recent tree
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        
        # Dodaj recent games
        for game in recent_games:
            last_played = game['last_played']
            if last_played:
                dt = datetime.fromisoformat(last_played)
                time_ago = self._time_ago(dt)
                
                self.recent_tree.insert(
                    '', 'end',
                    values=(game['name'], time_ago)
                )
        
        self.logger.info("Home view data refreshed")
    
    def _time_ago(self, dt):
        """
        Konwertuje datetime na "X czasu temu".
        
        Args:
            dt (datetime): Data
        
        Returns:
            str: Tekst "X temu"
        """
        now = datetime.now()
        delta = now - dt
        
        if delta.days > 7:
            return dt.strftime('%Y-%m-%d')
        elif delta.days > 0:
            return f"{delta.days} dni temu"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h temu"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}min temu"
        else:
            return "Przed chwilą"
    
    def _navigate_to(self, view_name):
        """
        Nawiguje do innego widoku.
        
        Args:
            view_name (str): Nazwa widoku
        
        AI Note: Wywołuje show_view z main_window
        """
        # Znajdź main window w hierarchii
        parent = self.master
        while parent and not hasattr(parent, 'show_view'):
            parent = parent.master
        
        if parent and hasattr(parent, 'show_view'):
            parent.show_view(view_name)