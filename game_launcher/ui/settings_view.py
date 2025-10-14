"""
Settings View - Panel ustawień aplikacji
AI-Friendly: Wszystkie ustawienia w jednym miejscu
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from utils.logger import get_logger


class SettingsView(tk.Frame):
    """
    Widok ustawień - konfiguracja aplikacji.
    
    AI Note:
    - Motyw (ciemny/jasny)
    - API Keys (Discord, Last.fm, RAWG, GitHub)
    - Ścieżki
    - Odtwarzacz muzyki
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok ustawień.
        
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
        
        # Załaduj aktualne ustawienia
        self._load_settings()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'section_bg': '#34495e',
                'text': '#ecf0f1',
                'accent': '#3498db'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'section_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Sekcje z różnymi kategoriami ustawień
        """
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Scrollable area dla sekcji
        self._create_scrollable_area()
        
        # Sekcje ustawień
        self._create_appearance_section()
        self._create_integrations_section()
        self._create_music_section()
        self._create_advanced_section()
        
        # Footer z przyciskami
        self._create_footer()
    
    def _create_header(self):
        """Tworzy header z tytułem."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        title = tk.Label(
            header,
            text="Ustawienia",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
    
    def _create_scrollable_area(self):
        """Tworzy scrollable obszar dla sekcji."""
        container = tk.Frame(self, bg=self.colors['bg'])
        container.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        
        # Canvas
        self.canvas = tk.Canvas(container, bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame dla sekcji
        self.sections_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.sections_frame, anchor='nw')
        
        self.sections_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
    
    def _create_section(self, title):
        """
        Tworzy sekcję ustawień.
        
        Args:
            title (str): Tytuł sekcji
        
        Returns:
            tk.Frame: Frame sekcji
        """
        section = tk.Frame(
            self.sections_frame,
            bg=self.colors['section_bg'],
            relief='raised',
            borderwidth=1
        )
        section.pack(fill='x', pady=10, padx=10)
        
        # Tytuł sekcji
        title_label = tk.Label(
            section,
            text=title,
            font=('Arial', 14, 'bold'),
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            anchor='w'
        )
        title_label.pack(fill='x', padx=15, pady=10)
        
        # Frame dla zawartości
        content_frame = tk.Frame(section, bg=self.colors['section_bg'])
        content_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        return content_frame
    
    def _create_appearance_section(self):
        """Sekcja wyglądu."""
        section = self._create_section("🎨 Wygląd")
        
        # Motyw
        theme_frame = tk.Frame(section, bg=self.colors['section_bg'])
        theme_frame.pack(fill='x', pady=5)
        
        tk.Label(
            theme_frame,
            text="Motyw:",
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            width=20,
            anchor='w'
        ).pack(side='left')
        
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=['dark', 'light'],
            state='readonly',
            width=30
        )
        theme_combo.pack(side='left', padx=10)
        
        # Kolor wykresów
        chart_frame = tk.Frame(section, bg=self.colors['section_bg'])
        chart_frame.pack(fill='x', pady=5)
        
        tk.Label(
            chart_frame,
            text="Kolor wykresów:",
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            width=20,
            anchor='w'
        ).pack(side='left')
        
        self.chart_color_var = tk.StringVar()
        chart_color_entry = tk.Entry(chart_frame, textvariable=self.chart_color_var, width=15)
        chart_color_entry.pack(side='left', padx=10)
        
        tk.Button(
            chart_frame,
            text="Wybierz kolor",
            command=self._choose_chart_color
        ).pack(side='left')
        
        # Liczba kolumn w grid
        columns_frame = tk.Frame(section, bg=self.colors['section_bg'])
        columns_frame.pack(fill='x', pady=5)
        
        tk.Label(
            columns_frame,
            text="Kolumny w bibliotece:",
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            width=20,
            anchor='w'
        ).pack(side='left')
        
        self.grid_columns_var = tk.StringVar()
        columns_spin = tk.Spinbox(
            columns_frame,
            from_=1,
            to=6,
            textvariable=self.grid_columns_var,
            width=10
        )
        columns_spin.pack(side='left', padx=10)
    
    def _create_integrations_section(self):
        """Sekcja integracji z API."""
        section = self._create_section("🔗 Integracje API")
        
        # Discord
        discord_frame = self._create_api_config(section, "Discord Rich Presence", "discord")
        self.discord_enabled_var = tk.BooleanVar()
        self.discord_client_id_var = tk.StringVar()
        
        tk.Checkbutton(
            discord_frame,
            text="Włącz",
            variable=self.discord_enabled_var,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['section_bg']
        ).grid(row=0, column=0, sticky='w', pady=5)
        
        tk.Label(discord_frame, text="Client ID:", bg=self.colors['section_bg'], fg=self.colors['text']).grid(row=1, column=0, sticky='w')
        tk.Entry(discord_frame, textvariable=self.discord_client_id_var, width=40).grid(row=1, column=1, padx=10)
        
        # Last.fm
        lastfm_frame = self._create_api_config(section, "Last.fm", "lastfm")
        self.lastfm_enabled_var = tk.BooleanVar()
        self.lastfm_api_key_var = tk.StringVar()
        self.lastfm_api_secret_var = tk.StringVar()
        
        tk.Checkbutton(
            lastfm_frame,
            text="Włącz",
            variable=self.lastfm_enabled_var,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['section_bg']
        ).grid(row=0, column=0, sticky='w', pady=5)
        
        tk.Label(lastfm_frame, text="API Key:", bg=self.colors['section_bg'], fg=self.colors['text']).grid(row=1, column=0, sticky='w')
        tk.Entry(lastfm_frame, textvariable=self.lastfm_api_key_var, width=40).grid(row=1, column=1, padx=10)
        
        tk.Label(lastfm_frame, text="API Secret:", bg=self.colors['section_bg'], fg=self.colors['text']).grid(row=2, column=0, sticky='w')
        tk.Entry(lastfm_frame, textvariable=self.lastfm_api_secret_var, width=40, show="*").grid(row=2, column=1, padx=10)
        
        # RAWG
        rawg_frame = self._create_api_config(section, "RAWG", "rawg")
        self.rawg_enabled_var = tk.BooleanVar()
        self.rawg_api_key_var = tk.StringVar()
        
        tk.Checkbutton(
            rawg_frame,
            text="Włącz",
            variable=self.rawg_enabled_var,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['section_bg']
        ).grid(row=0, column=0, sticky='w', pady=5)
        
        tk.Label(rawg_frame, text="API Key:", bg=self.colors['section_bg'], fg=self.colors['text']).grid(row=1, column=0, sticky='w')
        tk.Entry(rawg_frame, textvariable=self.rawg_api_key_var, width=40).grid(row=1, column=1, padx=10)
    
    def _create_api_config(self, parent, name, api_key):
        """Helper do tworzenia sekcji API."""
        frame = tk.LabelFrame(
            parent,
            text=name,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            font=('Arial', 10, 'bold')
        )
        frame.pack(fill='x', pady=10)
        
        inner = tk.Frame(frame, bg=self.colors['section_bg'])
        inner.pack(fill='x', padx=10, pady=10)
        
        return inner
    
    def _create_music_section(self):
        """Sekcja odtwarzacza muzyki."""
        section = self._create_section("🎵 Odtwarzacz Muzyki")
        
        # Włącz/wyłącz
        music_enabled_frame = tk.Frame(section, bg=self.colors['section_bg'])
        music_enabled_frame.pack(fill='x', pady=5)
        
        self.music_enabled_var = tk.BooleanVar()
        tk.Checkbutton(
            music_enabled_frame,
            text="Włącz odtwarzacz muzyki",
            variable=self.music_enabled_var,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['section_bg']
        ).pack(side='left')
        
        # Folder z muzyką
        folder_frame = tk.Frame(section, bg=self.colors['section_bg'])
        folder_frame.pack(fill='x', pady=5)
        
        tk.Label(
            folder_frame,
            text="Folder z muzyką:",
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            width=20,
            anchor='w'
        ).pack(side='left')
        
        self.music_folder_var = tk.StringVar()
        tk.Entry(folder_frame, textvariable=self.music_folder_var, width=40).pack(side='left', padx=10)
        
        tk.Button(
            folder_frame,
            text="Przeglądaj...",
            command=self._browse_music_folder
        ).pack(side='left')
        
        # Głośność
        volume_frame = tk.Frame(section, bg=self.colors['section_bg'])
        volume_frame.pack(fill='x', pady=5)
        
        tk.Label(
            volume_frame,
            text="Głośność:",
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            width=20,
            anchor='w'
        ).pack(side='left')
        
        self.volume_var = tk.DoubleVar()
        volume_scale = tk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient='horizontal',
            variable=self.volume_var,
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            highlightthickness=0,
            length=200
        )
        volume_scale.pack(side='left', padx=10)
    
    def _create_advanced_section(self):
        """Sekcja zaawansowanych ustawień."""
        section = self._create_section("⚙️ Zaawansowane")
        
        # Reset bazy danych
        reset_frame = tk.Frame(section, bg=self.colors['section_bg'])
        reset_frame.pack(fill='x', pady=10)
        
        tk.Label(
            reset_frame,
            text="⚠️ Opcje niebezpieczne",
            font=('Arial', 10, 'bold'),
            bg=self.colors['section_bg'],
            fg='#e74c3c'
        ).pack(side='left')
        
        tk.Button(
            reset_frame,
            text="Zresetuj bazę danych",
            bg='#e74c3c',
            fg='white',
            command=self._reset_database
        ).pack(side='right')
    
    def _create_footer(self):
        """Footer z przyciskami akcji."""
        footer = tk.Frame(self, bg=self.colors['bg'])
        footer.grid(row=2, column=0, sticky='ew', pady=10)
        
        # Zapisz
        save_btn = tk.Button(
            footer,
            text="💾 Zapisz Ustawienia",
            font=('Arial', 11, 'bold'),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=30,
            pady=10,
            command=self._save_settings
        )
        save_btn.pack(side='right', padx=10)
        
        # Anuluj
        cancel_btn = tk.Button(
            footer,
            text="Anuluj",
            font=('Arial', 11),
            bg=self.colors['section_bg'],
            fg=self.colors['text'],
            cursor='hand2',
            relief='flat',
            padx=20,
            pady=10,
            command=self._load_settings
        )
        cancel_btn.pack(side='right', padx=10)
    
    def _load_settings(self):
        """Ładuje aktualne ustawienia z configu."""
        # Wygląd
        self.theme_var.set(self.config.get('app', 'theme', default='dark'))
        self.chart_color_var.set(self.config.get('ui', 'chart_color', default='#3498db'))
        self.grid_columns_var.set(str(self.config.get('ui', 'grid_columns', default=3)))
        
        # Discord
        discord_config = self.config.get_integration_config('discord')
        self.discord_enabled_var.set(discord_config.get('enabled', False))
        self.discord_client_id_var.set(discord_config.get('client_id', ''))
        
        # Last.fm
        lastfm_config = self.config.get_integration_config('lastfm')
        self.lastfm_enabled_var.set(lastfm_config.get('enabled', False))
        self.lastfm_api_key_var.set(lastfm_config.get('api_key', ''))
        self.lastfm_api_secret_var.set(lastfm_config.get('api_secret', ''))
        
        # RAWG
        rawg_config = self.config.get_integration_config('rawg')
        self.rawg_enabled_var.set(rawg_config.get('enabled', False))
        self.rawg_api_key_var.set(rawg_config.get('api_key', ''))
        
        # Muzyka
        music_config = self.config.get('features', 'music_player', default={})
        self.music_enabled_var.set(music_config.get('enabled', True))
        self.volume_var.set(music_config.get('volume', 0.5) * 100)
        # Folder muzyki można dodać do configu
        
        self.logger.info("Settings loaded")
    
    def _save_settings(self):
        """Zapisuje ustawienia do configu."""
        try:
            # Wygląd
            self.config.set('app', 'theme', value=self.theme_var.get())
            self.config.set('ui', 'chart_color', value=self.chart_color_var.get())
            self.config.set('ui', 'grid_columns', value=int(self.grid_columns_var.get()))
            
            # Discord
            self.config.set('integrations', 'discord', 'enabled', value=self.discord_enabled_var.get())
            self.config.set('integrations', 'discord', 'client_id', value=self.discord_client_id_var.get())
            
            # Last.fm
            self.config.set('integrations', 'lastfm', 'enabled', value=self.lastfm_enabled_var.get())
            self.config.set('integrations', 'lastfm', 'api_key', value=self.lastfm_api_key_var.get())
            self.config.set('integrations', 'lastfm', 'api_secret', value=self.lastfm_api_secret_var.get())
            
            # RAWG
            self.config.set('integrations', 'rawg', 'enabled', value=self.rawg_enabled_var.get())
            self.config.set('integrations', 'rawg', 'api_key', value=self.rawg_api_key_var.get())
            
            # Muzyka
            self.config.set('features', 'music_player', 'enabled', value=self.music_enabled_var.get())
            self.config.set('features', 'music_player', 'volume', value=self.volume_var.get() / 100)
            
            # Zapisz
            self.config.save()
            
            messagebox.showinfo(
                "Sukces",
                "Ustawienia zostały zapisane!\n\nNiektóre zmiany wymagają restartu aplikacji."
            )
            self.logger.info("Settings saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Błąd", f"Nie udało się zapisać ustawień:\n{str(e)}")
    
    def _choose_chart_color(self):
        """Dialog wyboru koloru wykresów."""
        current_color = self.chart_color_var.get()
        color = colorchooser.askcolor(initialcolor=current_color, title="Wybierz kolor wykresów")
        
        if color[1]:  # color[1] to hex string
            self.chart_color_var.set(color[1])
    
    def _browse_music_folder(self):
        """Dialog wyboru folderu z muzyką."""
        folder = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if folder:
            self.music_folder_var.set(folder)
    
    def _reset_database(self):
        """Resetuje bazę danych (usuwa wszystkie dane)."""
        confirm = messagebox.askyesno(
            "⚠️ UWAGA",
            "Czy na pewno chcesz zresetować bazę danych?\n\n"
            "To usunie:\n"
            "- Wszystkie gry\n"
            "- Statystyki\n"
            "- Osiągnięcia\n"
            "- Roadmapę\n\n"
            "Ta operacja jest NIEODWRACALNA!",
            icon='warning'
        )
        
        if not confirm:
            return
        
        # Druga weryfikacja
        confirm2 = messagebox.askyesno(
            "Ostatnie potwierdzenie",
            "Jesteś absolutnie pewien?\n\nWszystkie dane zostaną utracone!",
            icon='warning'
        )
        
        if confirm2:
            try:
                # Usuń wszystkie dane
                cursor = self.db.conn.cursor()
                cursor.execute("DELETE FROM games")
                cursor.execute("DELETE FROM play_sessions")
                cursor.execute("DELETE FROM achievements")
                cursor.execute("DELETE FROM roadmap")
                self.db.conn.commit()
                
                messagebox.showinfo("Sukces", "Baza danych została zresetowana.")
                self.logger.warning("Database reset by user")
                
            except Exception as e:
                self.logger.error(f"Failed to reset database: {e}")
                messagebox.showerror("Błąd", f"Nie udało się zresetować bazy:\n{str(e)}")