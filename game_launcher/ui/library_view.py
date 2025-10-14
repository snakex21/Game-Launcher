"""
Library View - Widok biblioteki gier z kafelkami
AI-Friendly: Grid layout z okładkami gier
"""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from features import ScreenshotManager
from integrations import GitHubBackup, LastFMIntegration, RAWGApi
from utils.helpers import format_time
from utils.logger import get_logger


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

        # Funkcje dodatkowe / integracje
        screenshots_path = self.config.get(
            'paths',
            'screenshots',
            default='data/screenshots',
        )
        self.screenshot_manager = ScreenshotManager(screenshots_path)
        self.github_backup = None
        self.lastfm_client = None
        self.rawg_client = None
        
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

        # Panel opcji dodatkowych
        options_frame = tk.Frame(footer, bg=self.colors['bg'])
        options_frame.pack(side='left', padx=5)

        option_style = {
            'font': ('Arial', 10),
            'bg': self.colors['card_bg'],
            'fg': self.colors['text'],
            'activebackground': self.colors['hover'],
            'activeforeground': self.colors['text'],
            'cursor': 'hand2',
            'relief': 'flat',
            'padx': 12,
            'pady': 6,
        }

        buttons = [
            ("📸 Zrzut", self._capture_screenshot),
            ("🖼️ Galeria", self._show_screenshots_browser),
            ("☁️ GitHub", self._open_backup_dialog),
            ("🎵 Last.fm", self._open_lastfm_dialog),
            ("ℹ️ RAWG", self._open_rawg_dialog),
        ]

        for text, command in buttons:
            btn = tk.Button(options_frame, text=text, command=command, **option_style)
            btn.pack(side='left', padx=4)

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
        if getattr(self, 'canvas', None) and self.canvas.winfo_exists():
            delta = int(-1 * (event.delta / 120))
            if delta != 0:
                self.canvas.yview_scroll(delta, 'units')

    # ------------------------------------------------------------------
    def destroy(self):
        """Ensure global bindings są sprzątane przy niszczeniu widoku."""
        if getattr(self, 'canvas', None):
            self.canvas.unbind_all('<MouseWheel>')
        super().destroy()

    # ------------------------------------------------------------------
    def _capture_screenshot(self):
        """Wykonuje szybki zrzut ekranu korzystając z ScreenshotManagera."""
        path = self.screenshot_manager.capture_screenshot()

        if path:
            messagebox.showinfo("Zapisano zrzut", f"Plik zapisano w:\n{path}")
        else:
            messagebox.showerror(
                "Błąd zrzutu",
                "Nie udało się wykonać zrzutu ekranu. Upewnij się, że środowisko"
                " graficzne jest dostępne.",
            )

    # ------------------------------------------------------------------
    def _show_screenshots_browser(self):
        """Pokazuje proste okno z listą zapisanych zrzutów ekranu."""
        screenshots = self.screenshot_manager.list_screenshots()

        if not screenshots:
            messagebox.showinfo(
                "Brak zrzutów",
                "Katalog zrzutów ekranu jest pusty.",
            )
            return

        browser = tk.Toplevel(self)
        browser.title("Zapisane zrzuty ekranu")
        browser.configure(bg=self.colors['bg'])
        browser.geometry("400x320")

        listbox = tk.Listbox(browser, activestyle='none')
        listbox.pack(fill='both', expand=True, padx=10, pady=10)

        for item in screenshots:
            listbox.insert('end', item.name)

        def open_selected():
            selection = listbox.curselection()
            if not selection:
                return
            path = screenshots[selection[0]]
            try:
                if sys.platform.startswith('win'):
                    os.startfile(path)  # type: ignore[attr-defined]
                elif sys.platform == 'darwin':
                    subprocess.run(['open', str(path)], check=False)
                else:
                    subprocess.run(['xdg-open', str(path)], check=False)
            except Exception as exc:
                messagebox.showerror("Błąd", f"Nie można otworzyć pliku:\n{exc}")

        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                return

            index = selection[0]
            path = screenshots[index]

            if messagebox.askyesno(
                "Usuń zrzut",
                f"Czy na pewno usunąć plik {path.name}?",
            ):
                if self.screenshot_manager.delete_screenshot(path):
                    listbox.delete(index)
                    screenshots.pop(index)
                else:
                    messagebox.showerror(
                        "Błąd",
                        "Nie udało się usunąć wskazanego zrzutu.",
                    )

        buttons_frame = tk.Frame(browser, bg=self.colors['bg'])
        buttons_frame.pack(fill='x', padx=10, pady=(0, 10))

        tk.Button(
            buttons_frame,
            text="Otwórz",
            command=open_selected,
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=14,
            pady=6,
        ).pack(side='left', padx=5)

        tk.Button(
            buttons_frame,
            text="Usuń",
            command=delete_selected,
            bg='#c0392b',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=14,
            pady=6,
        ).pack(side='right', padx=5)

    # ------------------------------------------------------------------
    def _open_backup_dialog(self):
        """Wyświetla panel obsługi kopii zapasowej GitHub."""
        config = self.config.get('integrations', 'github', default={}) or {}

        if not config.get('enabled'):
            messagebox.showinfo(
                "GitHub Backup",
                "Integracja GitHub jest wyłączona. Włącz ją w ustawieniach.",
            )
            return

        token = config.get('token')
        repo = config.get('repo')
        branch = config.get('branch', 'main')

        if not token or not repo:
            messagebox.showwarning(
                "GitHub Backup",
                "Brakuje tokenu lub nazwy repozytorium w konfiguracji.",
            )
            return

        if self.github_backup is None:
            self.github_backup = GitHubBackup(token, repo, branch=branch)

        dialog = tk.Toplevel(self)
        dialog.title("Kopia zapasowa - GitHub")
        dialog.configure(bg=self.colors['bg'])
        dialog.geometry("420x240")

        status_var = tk.StringVar(value="Nie połączono")

        def connect():
            if self.github_backup and self.github_backup.connect():
                status_var.set(f"Połączono z {repo}")
            else:
                status_var.set("Błąd połączenia")

        def upload_file():
            if not self.github_backup:
                return
            if not self.github_backup.repo and not self.github_backup.connect():
                messagebox.showerror("GitHub", "Nie udało się połączyć z repozytorium.")
                return

            local_path = filedialog.askopenfilename(title="Wybierz plik do wysłania")
            if not local_path:
                return

            default_remote = Path(local_path).name
            remote_path = remote_entry.get().strip() or default_remote

            if self.github_backup.upload_file(local_path, remote_path):
                messagebox.showinfo(
                    "GitHub",
                    f"Plik {remote_path} został wysłany do repozytorium.",
                )
            else:
                messagebox.showerror(
                    "GitHub",
                    "Nie udało się przesłać pliku.",
                )

        def download_file():
            if not self.github_backup:
                return
            if not self.github_backup.repo and not self.github_backup.connect():
                messagebox.showerror("GitHub", "Nie udało się połączyć z repozytorium.")
                return

            remote_path = remote_entry.get().strip()
            if not remote_path:
                messagebox.showwarning("GitHub", "Podaj ścieżkę pliku w repozytorium.")
                return

            local_path = filedialog.asksaveasfilename(initialfile=Path(remote_path).name)
            if not local_path:
                return

            if self.github_backup.download_file(remote_path, local_path):
                messagebox.showinfo(
                    "GitHub",
                    f"Plik zapisano jako:\n{local_path}",
                )
            else:
                messagebox.showerror("GitHub", "Nie udało się pobrać pliku.")

        tk.Label(
            dialog,
            text="Status:",
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor='w'
        ).pack(fill='x', padx=10, pady=(15, 2))

        tk.Label(
            dialog,
            textvariable=status_var,
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            anchor='w',
            relief='flat',
            padx=10,
            pady=6,
        ).pack(fill='x', padx=10)

        tk.Button(
            dialog,
            text="Połącz", 
            command=connect,
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=16,
            pady=8,
        ).pack(padx=10, pady=10, anchor='w')

        tk.Label(
            dialog,
            text="Ścieżka w repozytorium:",
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor='w',
        ).pack(fill='x', padx=10, pady=(10, 2))

        remote_entry = tk.Entry(dialog)
        remote_entry.pack(fill='x', padx=10)

        actions = tk.Frame(dialog, bg=self.colors['bg'])
        actions.pack(fill='x', padx=10, pady=15)

        tk.Button(
            actions,
            text="Wyślij plik",
            command=upload_file,
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=16,
            pady=8,
        ).pack(side='left', padx=5)

        tk.Button(
            actions,
            text="Pobierz plik",
            command=download_file,
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            relief='flat',
            cursor='hand2',
            padx=16,
            pady=8,
        ).pack(side='left', padx=5)

    # ------------------------------------------------------------------
    def _open_lastfm_dialog(self):
        """Wyświetla ostatnio odtwarzane utwory z Last.fm."""
        config = self.config.get('integrations', 'lastfm', default={}) or {}

        if not config.get('enabled'):
            messagebox.showinfo(
                "Last.fm",
                "Integracja Last.fm jest wyłączona. Aktywuj ją w ustawieniach.",
            )
            return

        api_key = config.get('api_key')
        api_secret = config.get('api_secret')

        if not api_key or not api_secret:
            messagebox.showwarning(
                "Last.fm",
                "Brakuje danych API w konfiguracji.",
            )
            return

        if self.lastfm_client is None:
            self.lastfm_client = LastFMIntegration(
                api_key,
                api_secret,
                username=config.get('username') or None,
                password_hash=config.get('password_hash') or None,
            )

        if not getattr(self.lastfm_client, 'network', None):
            if not self.lastfm_client.connect():
                messagebox.showerror("Last.fm", "Nie udało się połączyć z API Last.fm.")
                return

        recent_tracks = self.lastfm_client.get_recent_tracks(limit=10)

        if not recent_tracks:
            messagebox.showinfo("Last.fm", "Brak historii do wyświetlenia.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Ostatnie utwory - Last.fm")
        dialog.configure(bg=self.colors['bg'])
        dialog.geometry("420x320")

        listbox = tk.Listbox(dialog, activestyle='none')
        listbox.pack(fill='both', expand=True, padx=10, pady=10)

        for played in recent_tracks:
            track = getattr(played, 'track', None)
            if track is None:
                listbox.insert('end', str(played))
                continue

            artist = getattr(track, 'artist', None)
            artist_name = getattr(artist, 'name', str(artist)) if artist else 'Nieznany'
            title = getattr(track, 'title', str(track))
            played_at = getattr(played, 'playback_date', None)
            if played_at:
                listbox.insert('end', f"{artist_name} – {title} ({played_at})")
            else:
                listbox.insert('end', f"{artist_name} – {title}")

    # ------------------------------------------------------------------
    def _open_rawg_dialog(self):
        """Umożliwia wyszukanie gry w API RAWG."""
        config = self.config.get('integrations', 'rawg', default={}) or {}

        if self.rawg_client is None:
            self.rawg_client = RAWGApi(config.get('api_key'))

        dialog = tk.Toplevel(self)
        dialog.title("Wyszukiwarka RAWG")
        dialog.configure(bg=self.colors['bg'])
        dialog.geometry("460x360")

        tk.Label(
            dialog,
            text="Nazwa gry:",
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor='w',
        ).pack(fill='x', padx=10, pady=(15, 2))

        search_var = tk.StringVar()
        search_entry = tk.Entry(dialog, textvariable=search_var)
        search_entry.pack(fill='x', padx=10)

        results_list: list[dict] = []

        listbox = tk.Listbox(dialog, activestyle='none')
        listbox.pack(fill='both', expand=True, padx=10, pady=10)

        def perform_search():
            query = search_var.get().strip()
            if not query:
                messagebox.showinfo("RAWG", "Wpisz frazę wyszukiwania.")
                return

            listbox.delete(0, 'end')
            listbox.insert('end', 'Wyszukiwanie...')
            dialog.update_idletasks()

            nonlocal results_list
            results_list = self.rawg_client.search_games(query, page_size=10)

            listbox.delete(0, 'end')
            if not results_list:
                listbox.insert('end', 'Brak wyników dla podanej frazy.')
                return

            for item in results_list:
                name = item.get('name', 'Nieznana gra')
                released = item.get('released') or 'brak daty'
                rating = item.get('rating')
                if rating is None:
                    listbox.insert('end', f"{name} (premiera: {released})")
                else:
                    listbox.insert('end', f"{name} • ocena {rating}/5 (premiera: {released})")

        def show_details(event=None):
            selection = listbox.curselection()
            if not selection:
                return
            index = selection[0]
            if index >= len(results_list):
                return

            item = results_list[index]
            game_id = item.get('id')
            details = self.rawg_client.get_game_details(game_id) if game_id else None

            if not details:
                messagebox.showinfo("RAWG", "Nie udało się pobrać szczegółów gry.")
                return

            description = details.get('description_raw') or 'Brak opisu.'
            genres = ', '.join(g['name'] for g in details.get('genres', [])) or 'brak danych'
            platforms = ', '.join(p['platform']['name'] for p in details.get('platforms', [])) or 'brak danych'

            info = (
                f"Tytuł: {details.get('name', 'Nieznana gra')}\n"
                f"Premiera: {details.get('released', 'brak danych')}\n"
                f"Ocena: {details.get('rating', 'brak danych')}\n"
                f"Gatunki: {genres}\n"
                f"Platformy: {platforms}\n\n"
                f"Opis:\n{description[:800]}"
            )

            messagebox.showinfo("Szczegóły gry", info)

        tk.Button(
            dialog,
            text="Szukaj",
            command=perform_search,
            bg=self.colors['accent'],
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=16,
            pady=8,
        ).pack(padx=10, pady=(0, 10), anchor='w')

        listbox.bind('<Double-Button-1>', show_details)
        search_entry.bind('<Return>', lambda _event: perform_search())
