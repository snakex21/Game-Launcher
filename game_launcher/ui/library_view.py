"""
Library View - Widok biblioteki gier z kafelkami
AI-Friendly: Grid layout z okładkami gier
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from pathlib import Path
from utils.logger import get_logger
from utils.helpers import format_time


class LibraryView(tk.Frame):
    """
    Widok biblioteki gier - siatka kafelków z okładkami.
    
    AI Note:
    - Pokazuje gry w grid layout
    - Filtry i sortowanie
    - Dodawanie nowych gier
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok biblioteki.
        
        Args:
            parent: Widget rodzica (content_area)
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Dane
        self.games = []
        self.filtered_games = []
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Ładowanie gier
        self.refresh_games()
        
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
                'hover': '#4a5f7f'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'card_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'hover': '#95a5a6'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Struktura: Header (filtry) + Grid (gry) + Footer (przyciski)
        """
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header z filtrami i przyciskami
        self._create_header()
        
        # Scrollable area dla gier
        self._create_games_grid()
        
        # Footer z przyciskami akcji
        self._create_footer()
    
    def _create_header(self):
        """
        Tworzy header z wyszukiwarką i filtrami.
        
        AI Note: Wyszukiwarka + sortowanie
        """
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Tytuł
        title = tk.Label(
            header,
            text="Biblioteka Gier",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Wyszukiwarka
        search_frame = tk.Frame(header, bg=self.colors['bg'])
        search_frame.pack(side='right', padx=10)
        
        tk.Label(
            search_frame,
            text="Szukaj:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_games())
        
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=30
        )
        search_entry.pack(side='left')
        
        # Sortowanie
        tk.Label(
            search_frame,
            text="Sortuj:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left', padx=(20, 5))
        
        self.sort_var = tk.StringVar(value='name')
        sort_combo = ttk.Combobox(
            search_frame,
            textvariable=self.sort_var,
            values=['name', 'playtime', 'recent'],
            state='readonly',
            width=15
        )
        sort_combo.pack(side='left')
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self._sort_games())
    
    def _create_games_grid(self):
        """
        Tworzy scrollable grid dla kafelków gier.
        
        AI Note: Canvas + Scrollbar dla przewijania
        """
        # Container z scrollbarem
        container = tk.Frame(self, bg=self.colors['bg'])
        container.grid(row=1, column=0, sticky='nsew')
        
        # Canvas
        self.canvas = tk.Canvas(container, bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame wewnątrz canvas dla gier
        self.games_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.games_frame, anchor='nw')
        
        # Update scroll region
        self.games_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scroll
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def _create_footer(self):
        """
        Tworzy footer z przyciskami akcji.
        
        AI Note: Przyciski do dodawania gier
        """
        footer = tk.Frame(self, bg=self.colors['bg'])
        footer.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        
        # Przycisk dodawania gry
        add_btn = tk.Button(
            footer,
            text="➕ Dodaj Grę",
            font=('Arial', 11, 'bold'),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=20,
            pady=8,
            command=self._add_game_dialog
        )
        add_btn.pack(side='left', padx=10)
        
        # Info o liczbie gier
        self.games_count_label = tk.Label(
            footer,
            text="Gier: 0",
            font=('Arial', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        self.games_count_label.pack(side='right', padx=10)
    
    def refresh_games(self):
        """
        Odświeża listę gier z bazy danych.
        
        AI Note: Wywołaj po dodaniu/usunięciu gry
        """
        self.games = self.db.get_all_games()
        self._filter_games()
        self.logger.info(f"Loaded {len(self.games)} games")
    
    def _filter_games(self):
        """
        Filtruje gry według wyszukiwania.
        
        AI Note: Filtruje po nazwie, gatunku, platformie
        """
        search_text = self.search_var.get().lower()
        
        if not search_text:
            self.filtered_games = self.games.copy()
        else:
            self.filtered_games = [
                game for game in self.games
                if search_text in game['name'].lower() or
                   (game.get('genre') and search_text in game['genre'].lower()) or
                   (game.get('platform') and search_text in game['platform'].lower())
            ]
        
        self._sort_games()
    
    def _sort_games(self):
        """
        Sortuje przefiltrowane gry.
        
        AI Note: Różne metody sortowania
        """
        sort_by = self.sort_var.get()
        
        if sort_by == 'name':
            self.filtered_games.sort(key=lambda g: g['name'].lower())
        elif sort_by == 'playtime':
            self.filtered_games.sort(key=lambda g: g.get('total_playtime', 0), reverse=True)
        elif sort_by == 'recent':
            self.filtered_games.sort(key=lambda g: g.get('last_played', ''), reverse=True)
        
        self._display_games()
    
    def _display_games(self):
        """
        Wyświetla kafelki gier w grid.
        
        AI Note: Dynamiczny grid - liczba kolumn z configu
        """
        # Wyczyść poprzednie kafelki
        for widget in self.games_frame.winfo_children():
            widget.destroy()
        
        # Pobierz liczbę kolumn
        columns = self.config.get('ui', 'grid_columns', default=3)
        
        # Tworzenie kafelków
        for idx, game in enumerate(self.filtered_games):
            row = idx // columns
            col = idx % columns
            
            card = self._create_game_card(game)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        
        # Aktualizuj licznik
        self.games_count_label.config(text=f"Gier: {len(self.filtered_games)}")
    
    def _create_game_card(self, game):
        """
        Tworzy kafelek dla pojedynczej gry.
        
        Args:
            game (dict): Dane gry
        
        Returns:
            tk.Frame: Kafelek gry
        
        AI Note: Okładka + nazwa + czas gry
        """
        card = tk.Frame(
            self.games_frame,
            bg=self.colors['card_bg'],
            relief='raised',
            borderwidth=1,
            width=200,
            height=280
        )
        card.grid_propagate(False)
        
        # Okładka
        cover_label = self._create_cover_image(game)
        cover_label.pack(pady=10)
        
        # Nazwa gry
        name_label = tk.Label(
            card,
            text=game['name'][:25] + ('...' if len(game['name']) > 25 else ''),
            font=('Arial', 11, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        name_label.pack(pady=5)
        
        # Czas gry
        playtime = format_time(game.get('total_playtime', 0))
        time_label = tk.Label(
            card,
            text=f"⏱️ {playtime}",
            font=('Arial', 9),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        time_label.pack()
        
        # Przycisk uruchom
        play_btn = tk.Button(
            card,
            text="▶ Uruchom",
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            command=lambda: self._launch_game(game)
        )
        play_btn.pack(pady=10)
        
        # Hover effect
        card.bind('<Enter>', lambda e: card.config(bg=self.colors['hover']))
        card.bind('<Leave>', lambda e: card.config(bg=self.colors['card_bg']))
        
        return card
    
    def _create_cover_image(self, game):
        """
        Tworzy widget z okładką gry.
        
        Args:
            game (dict): Dane gry
        
        Returns:
            tk.Label: Label z obrazem
        
        AI Note: Ładuje okładkę lub pokazuje placeholder
        """
        cover_path = game.get('cover_path')
        
        try:
            if cover_path and Path(cover_path).exists():
                img = Image.open(cover_path)
            else:
                # Placeholder - szary prostokąt
                img = Image.new('RGB', (150, 200), color='#7f8c8d')
            
            # Resize
            img = img.resize((150, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            label = tk.Label(self.games_frame, image=photo, bg=self.colors['card_bg'])
            label.image = photo  # Keep reference
            return label
            
        except Exception as e:
            self.logger.error(f"Failed to load cover for {game['name']}: {e}")
            # Fallback placeholder
            label = tk.Label(
                self.games_frame,
                text="[Brak okładki]",
                width=20,
                height=10,
                bg='#7f8c8d',
                fg='white'
            )
            return label
    
    def _launch_game(self, game):
        """
        Uruchamia grę.
        
        Args:
            game (dict): Dane gry
        
        AI Note: Tutaj zintegruj tracking czasu gry
        """
        exe_path = game.get('exe_path')
        
        if not exe_path or not Path(exe_path).exists():
            messagebox.showerror("Błąd", f"Nie znaleziono pliku gry:\n{exe_path}")
            return
        
        try:
            import subprocess
            subprocess.Popen([exe_path])
            self.logger.info(f"Launched game: {game['name']}")
            
            # TODO: Start tracking sesji gry
            # session_id = self.db.start_play_session(game['id'])
            
        except Exception as e:
            self.logger.error(f"Failed to launch {game['name']}: {e}")
            messagebox.showerror("Błąd uruchamiania", str(e))
    
    def _add_game_dialog(self):
        """
        Dialog dodawania nowej gry.
        
        AI Note: Prosty dialog - nazwa + exe + okładka
        """
        dialog = tk.Toplevel(self)
        dialog.title("Dodaj Grę")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg'])
        
        # Nazwa
        tk.Label(dialog, text="Nazwa gry:", bg=self.colors['bg'], fg=self.colors['text']).pack(pady=5)
        name_entry = tk.Entry(dialog, width=40)
        name_entry.pack(pady=5)
        
        # Ścieżka do exe
        tk.Label(dialog, text="Plik .exe:", bg=self.colors['bg'], fg=self.colors['text']).pack(pady=5)
        exe_entry = tk.Entry(dialog, width=40)
        exe_entry.pack(pady=5)
        
        def browse_exe():
            path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
            if path:
                exe_entry.delete(0, tk.END)
                exe_entry.insert(0, path)
        
        tk.Button(dialog, text="Przeglądaj...", command=browse_exe).pack(pady=5)
        
        # Okładka (opcjonalnie)
        tk.Label(dialog, text="Okładka (opcjonalnie):", bg=self.colors['bg'], fg=self.colors['text']).pack(pady=5)
        cover_entry = tk.Entry(dialog, width=40)
        cover_entry.pack(pady=5)
        
        def browse_cover():
            path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
            if path:
                cover_entry.delete(0, tk.END)
                cover_entry.insert(0, path)
        
        tk.Button(dialog, text="Przeglądaj...", command=browse_cover).pack(pady=5)
        
        # Przycisk dodaj
        def add_game():
            name = name_entry.get().strip()
            exe = exe_entry.get().strip()
            cover = cover_entry.get().strip() or None
            
            if not name or not exe:
                messagebox.showwarning("Błąd", "Nazwa i plik .exe są wymagane!")
                return
            
            game_id = self.db.add_game(name, exe, cover_path=cover)
            
            if game_id:
                messagebox.showinfo("Sukces", f"Dodano grę: {name}")
                dialog.destroy()
                self.refresh_games()
            else:
                messagebox.showerror("Błąd", "Nie udało się dodać gry.")
        
        tk.Button(
            dialog,
            text="Dodaj Grę",
            bg=self.colors['accent'],
            fg='white',
            command=add_game
        ).pack(pady=20)
    
    def _on_frame_configure(self, event):
        """Update scroll region."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Resize games frame to canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Scroll with mouse wheel."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')