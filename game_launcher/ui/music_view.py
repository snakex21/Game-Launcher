"""
Music View - Panel kontrolny odtwarzacza muzyki
AI-Friendly: GUI do kontroli muzyki
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from utils.logger import get_logger
from features.music_player import MusicPlayer


class MusicView(tk.Frame):
    """
    Widok odtwarzacza muzyki.
    
    AI Note:
    - Play/Pause/Stop/Next/Previous
    - Lista utworów
    - Volume control
    - Shuffle/Loop
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok muzyki.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Music player
        music_config = self.config.get('features', 'music_player', default={})
        music_folder = music_config.get('folder', None)
        
        try:
            self.player = MusicPlayer(music_folder=music_folder)
            if music_folder:
                self.player.load_playlist(music_folder)
        except Exception as e:
            self.logger.error(f"Failed to initialize music player: {e}")
            self.player = None
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Update loop dla statusu
        self._update_status()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'player_bg': '#34495e',
                'text': '#ecf0f1',
                'accent': '#3498db',
                'button_bg': '#1a252f'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'player_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'button_bg': '#95a5a6'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """Tworzy interfejs użytkownika."""
        if not self.player:
            # Error message
            error_label = tk.Label(
                self,
                text="❌ Odtwarzacz muzyki nie jest dostępny\n\nSkonfiguruj folder z muzyką w Ustawieniach",
                font=('Arial', 14),
                bg=self.colors['bg'],
                fg=self.colors['text']
            )
            error_label.place(relx=0.5, rely=0.5, anchor='center')
            return
        
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Main container
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.grid(row=1, column=0, sticky='nsew', padx=20, pady=20)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=2)
        main_container.grid_columnconfigure(1, weight=1)
        
        # Player controls (lewa strona)
        self._create_player_controls(main_container)
        
        # Playlist (prawa strona)
        self._create_playlist(main_container)
    
    def _create_header(self):
        """Tworzy header z tytułem."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        title = tk.Label(
            header,
            text="🎵 Odtwarzacz Muzyki",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Przycisk ładowania folderu
        load_btn = tk.Button(
            header,
            text="📁 Załaduj folder",
            font=('Arial', 11),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=15,
            pady=5,
            command=self._load_folder
        )
        load_btn.pack(side='right', padx=10)
    
    def _create_player_controls(self, parent):
        """Tworzy panel kontrolny odtwarzacza."""
        player_frame = tk.Frame(parent, bg=self.colors['player_bg'], relief='raised', borderwidth=2)
        player_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        # Padding
        inner = tk.Frame(player_frame, bg=self.colors['player_bg'])
        inner.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Now Playing
        now_playing_label = tk.Label(
            inner,
            text="Teraz gra:",
            font=('Arial', 12),
            bg=self.colors['player_bg'],
            fg=self.colors['text']
        )
        now_playing_label.pack(pady=(0, 10))
        
        # Track info
        self.track_title_label = tk.Label(
            inner,
            text="Nie wybrano utworu",
            font=('Arial', 16, 'bold'),
            bg=self.colors['player_bg'],
            fg=self.colors['accent'],
            wraplength=400
        )
        self.track_title_label.pack(pady=5)
        
        self.track_artist_label = tk.Label(
            inner,
            text="",
            font=('Arial', 12),
            bg=self.colors['player_bg'],
            fg=self.colors['text']
        )
        self.track_artist_label.pack(pady=5)
        
        # Separator
        separator = tk.Frame(inner, height=2, bg=self.colors['accent'])
        separator.pack(fill='x', pady=20)
        
        # Control buttons
        controls_frame = tk.Frame(inner, bg=self.colors['player_bg'])
        controls_frame.pack(pady=20)
        
        # Previous
        prev_btn = tk.Button(
            controls_frame,
            text="⏮️",
            font=('Arial', 20),
            bg=self.colors['button_bg'],
            fg=self.colors['text'],
            cursor='hand2',
            relief='flat',
            width=3,
            command=self._previous_track
        )
        prev_btn.pack(side='left', padx=5)
        
        # Play/Pause
        self.play_pause_btn = tk.Button(
            controls_frame,
            text="▶️",
            font=('Arial', 24),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            width=3,
            command=self._toggle_play_pause
        )
        self.play_pause_btn.pack(side='left', padx=5)
        
        # Stop
        stop_btn = tk.Button(
            controls_frame,
            text="⏹️",
            font=('Arial', 20),
            bg=self.colors['button_bg'],
            fg=self.colors['text'],
            cursor='hand2',
            relief='flat',
            width=3,
            command=self._stop
        )
        stop_btn.pack(side='left', padx=5)
        
        # Next
        next_btn = tk.Button(
            controls_frame,
            text="⏭️",
            font=('Arial', 20),
            bg=self.colors['button_bg'],
            fg=self.colors['text'],
            cursor='hand2',
            relief='flat',
            width=3,
            command=self._next_track
        )
        next_btn.pack(side='left', padx=5)
        
        # Volume
        volume_frame = tk.Frame(inner, bg=self.colors['player_bg'])
        volume_frame.pack(pady=20)
        
        tk.Label(
            volume_frame,
            text="🔊 Głośność:",
            font=('Arial', 11),
            bg=self.colors['player_bg'],
            fg=self.colors['text']
        ).pack(side='left', padx=10)
        
        self.volume_var = tk.DoubleVar(value=self.player.volume * 100)
        volume_scale = tk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient='horizontal',
            variable=self.volume_var,
            command=self._change_volume,
            bg=self.colors['player_bg'],
            fg=self.colors['text'],
            highlightthickness=0,
            length=200
        )
        volume_scale.pack(side='left')
        
        # Shuffle & Loop
        options_frame = tk.Frame(inner, bg=self.colors['player_bg'])
        options_frame.pack(pady=20)
        
        self.shuffle_var = tk.BooleanVar(value=self.player.shuffle)
        shuffle_check = tk.Checkbutton(
            options_frame,
            text="🔀 Shuffle",
            variable=self.shuffle_var,
            command=self._toggle_shuffle,
            bg=self.colors['player_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['player_bg'],
            font=('Arial', 11)
        )
        shuffle_check.pack(side='left', padx=20)
        
        self.loop_var = tk.BooleanVar(value=self.player.loop)
        loop_check = tk.Checkbutton(
            options_frame,
            text="🔁 Loop",
            variable=self.loop_var,
            command=self._toggle_loop,
            bg=self.colors['player_bg'],
            fg=self.colors['text'],
            selectcolor=self.colors['player_bg'],
            font=('Arial', 11)
        )
        loop_check.pack(side='left', padx=20)
    
    def _create_playlist(self, parent):
        """Tworzy listę utworów."""
        playlist_frame = tk.Frame(parent, bg=self.colors['bg'])
        playlist_frame.grid(row=0, column=1, sticky='nsew')
        
        # Tytuł
        tk.Label(
            playlist_frame,
            text="Playlista",
            font=('Arial', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        # Treeview
        self.playlist_tree = ttk.Treeview(
            playlist_frame,
            columns=('Title',),
            show='tree headings',
            height=20
        )
        
        self.playlist_tree.heading('#0', text='#')
        self.playlist_tree.heading('Title', text='Tytuł')
        
        self.playlist_tree.column('#0', width=50)
        self.playlist_tree.column('Title', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(playlist_frame, orient='vertical', command=self.playlist_tree.yview)
        self.playlist_tree.configure(yscrollcommand=scrollbar.set)
        
        self.playlist_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Double click to play
        self.playlist_tree.bind('<Double-Button-1>', self._play_selected_track)
        
        # Załaduj playlistę
        self._refresh_playlist()
    
    def _refresh_playlist(self):
        """Odświeża wyświetlaną playlistę."""
        # Wyczyść
        for item in self.playlist_tree.get_children():
            self.playlist_tree.delete(item)
        
        # Dodaj utwory
        playlist_info = self.player.get_playlist_info()
        
        for idx, track in enumerate(playlist_info):
            self.playlist_tree.insert(
                '',
                'end',
                text=str(idx + 1),
                values=(track['title'],),
                tags=(str(idx),)
            )
    
    def _toggle_play_pause(self):
        """Przełącza play/pause."""
        if self.player.is_playing:
            self.player.pause()
            self.play_pause_btn.config(text="▶️")
        else:
            if self.player.current_track:
                self.player.unpause()
            else:
                self.player.play()
                self._update_track_info()
            self.play_pause_btn.config(text="⏸️")
    
    def _stop(self):
        """Zatrzymuje odtwarzanie."""
        self.player.stop()
        self.play_pause_btn.config(text="▶️")
        self.track_title_label.config(text="Zatrzymano")
        self.track_artist_label.config(text="")
    
    def _next_track(self):
        """Następny utwór."""
        self.player.next_track()
        self._update_track_info()
        self.play_pause_btn.config(text="⏸️")
    
    def _previous_track(self):
        """Poprzedni utwór."""
        self.player.previous_track()
        self._update_track_info()
        self.play_pause_btn.config(text="⏸️")
    
    def _play_selected_track(self, event):
        """Odtwarza wybrany utwór z listy."""
        selection = self.playlist_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.playlist_tree.item(item, 'tags')
        track_index = int(tags[0])
        
        self.player.play(track_index)
        self._update_track_info()
        self.play_pause_btn.config(text="⏸️")
    
    def _change_volume(self, value):
        """Zmienia głośność."""
        volume = float(value) / 100
        self.player.set_volume(volume)
    
    def _toggle_shuffle(self):
        """Przełącza shuffle."""
        self.player.toggle_shuffle()
    
    def _toggle_loop(self):
        """Przełącza loop."""
        self.player.toggle_loop()
    
    def _load_folder(self):
        """Dialog wyboru folderu z muzyką."""
        folder = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if folder:
            count = self.player.load_playlist(folder)
            self._refresh_playlist()
            messagebox.showinfo("Sukces", f"Załadowano {count} utworów")
    
    def _update_track_info(self):
        """Aktualizuje wyświetlane info o utworze."""
        track_info = self.player.get_current_track_info()
        
        if track_info:
            self.track_title_label.config(text=track_info['title'])
            artist_album = f"{track_info['artist']} - {track_info['album']}"
            self.track_artist_label.config(text=artist_album)
        else:
            self.track_title_label.config(text="Brak utworu")
            self.track_artist_label.config(text="")
    
    def _update_status(self):
        """Update loop - sprawdza czy utwór się skończył."""
        if self.player:
            # Sprawdź czy utwór się skończył (auto-next)
            self.player.check_music_end()
            
            # Aktualizuj info jeśli gra
            if self.player.is_playing and self.player.current_track:
                self._update_track_info()
        
        # Powtórz co 1 sekundę
        self.after(1000, self._update_status)