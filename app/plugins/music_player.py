"""Odtwarzacz muzyki."""
from __future__ import annotations

import logging
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

import customtkinter as ctk

from .base import BasePlugin
from app.services.music_service import LoopMode

logger = logging.getLogger(__name__)


class MusicPlayerPlugin(BasePlugin):
    name = "MusicPlayer"

    def register(self, context) -> None:  # type: ignore[no-untyped-def]
        logger.info("Zarejestrowano plugin MusicPlayer")


class MusicPlayerView(ctk.CTkFrame):
    def __init__(self, parent, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.context = context
        self.is_seeking = False
        self.update_timer_id: str | None = None

        title = ctk.CTkLabel(
            self,
            text="🎵 Odtwarzacz Muzyki",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=20)

        main_container = ctk.CTkFrame(self, corner_radius=15)
        main_container.pack(pady=10, padx=20, fill="both", expand=True)
        
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_rowconfigure(0, weight=1)
        
        self._setup_playlist_panel(main_container)
        self._setup_player_panel(main_container)
        
        self._sync_with_music_state()
        self._subscribe_events()
    
    def _subscribe_events(self) -> None:
        """Subskrybuj wydarzenia muzyczne."""
        self.context.event_bus.subscribe("music_error", self._on_music_error)
        self.context.event_bus.subscribe("playlist_loaded", self._on_playlist_loaded)
        self.context.event_bus.subscribe("shuffle_changed", self._on_shuffle_changed)
        self.context.event_bus.subscribe("loop_mode_changed", self._on_loop_mode_changed)
    
    def _on_music_error(self, error: str = "", **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Obsłuż błąd muzyczny."""
        messagebox.showerror("Błąd odtwarzacza", error)
    
    def _on_playlist_loaded(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Odśwież listę utworów po załadowaniu playlisty."""
        self._refresh_track_list()
    
    def _on_shuffle_changed(self, enabled: bool = False, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Zaktualizuj przycisk shuffle."""
        self._update_shuffle_button()
    
    def _on_loop_mode_changed(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Zaktualizuj przycisk loop."""
        self._update_loop_button()
    
    def _setup_playlist_panel(self, parent) -> None:  # type: ignore[no-untyped-def]
        """Panel zarządzania playlistami i listą utworów."""
        playlist_panel = ctk.CTkFrame(parent, corner_radius=10)
        playlist_panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        
        playlist_header = ctk.CTkLabel(
            playlist_panel,
            text="📋 Playlisty",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        playlist_header.pack(pady=(10, 5))
        
        playlist_buttons = ctk.CTkFrame(playlist_panel, fg_color="transparent")
        playlist_buttons.pack(pady=5, fill="x", padx=10)
        
        btn_load_folder = ctk.CTkButton(
            playlist_buttons,
            text="📂 Wczytaj folder",
            command=self._load_from_folder,
            width=140,
            height=32
        )
        btn_load_folder.pack(side="left", padx=2)
        
        btn_save_playlist = ctk.CTkButton(
            playlist_buttons,
            text="💾 Zapisz",
            command=self._save_playlist,
            width=100,
            height=32
        )
        btn_save_playlist.pack(side="left", padx=2)
        
        self.playlist_selector = ctk.CTkOptionMenu(
            playlist_panel,
            values=["Brak"],
            command=self._on_playlist_selected,
            width=200,
            height=32
        )
        self.playlist_selector.pack(pady=5, padx=10)
        self._refresh_playlist_selector()
        
        ctk.CTkLabel(
            playlist_panel,
            text="🎵 Utwory",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))
        
        track_list_container = ctk.CTkFrame(playlist_panel, fg_color="transparent")
        track_list_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.track_listbox = ctk.CTkScrollableFrame(
            track_list_container,
            fg_color=("gray90", "gray20")
        )
        self.track_listbox.pack(fill="both", expand=True)
        
        track_controls = ctk.CTkFrame(playlist_panel, fg_color="transparent")
        track_controls.pack(pady=10, fill="x", padx=10)
        
        btn_add_tracks = ctk.CTkButton(
            track_controls,
            text="➕ Dodaj",
            command=self._add_tracks,
            width=80,
            height=28
        )
        btn_add_tracks.pack(side="left", padx=2)
        
        btn_remove_track = ctk.CTkButton(
            track_controls,
            text="➖ Usuń",
            command=self._remove_selected_track,
            width=80,
            height=28
        )
        btn_remove_track.pack(side="left", padx=2)
        
        btn_clear = ctk.CTkButton(
            track_controls,
            text="🗑️ Wyczyść",
            command=self._clear_playlist,
            width=80,
            height=28
        )
        btn_clear.pack(side="left", padx=2)
    
    def _setup_player_panel(self, parent) -> None:  # type: ignore[no-untyped-def]
        """Panel odtwarzacza."""
        player_panel = ctk.CTkFrame(parent, corner_radius=10)
        player_panel.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        
        self.track_label = ctk.CTkLabel(
            player_panel,
            text="Nie wybrano playlisty",
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=400
        )
        self.track_label.pack(pady=(30, 10))
        
        progress_container = ctk.CTkFrame(player_panel, fg_color="transparent")
        progress_container.pack(pady=(10, 15), padx=30, fill="x")
        
        self.time_label_current = ctk.CTkLabel(
            progress_container,
            text="0:00",
            font=ctk.CTkFont(size=12),
            width=50
        )
        self.time_label_current.pack(side="left", padx=(0, 10))
        
        self.progress_slider = ctk.CTkSlider(
            progress_container,
            from_=0,
            to=100,
            number_of_steps=1000,
            command=self._on_seek_slider_change,
            height=20
        )
        self.progress_slider.set(0)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_slider.bind("<Button-1>", self._on_seek_start)
        self.progress_slider.bind("<ButtonRelease-1>", self._on_seek_end)
        
        self.time_label_total = ctk.CTkLabel(
            progress_container,
            text="0:00",
            font=ctk.CTkFont(size=12),
            width=50
        )
        self.time_label_total.pack(side="left", padx=(10, 0))

        buttons_frame = ctk.CTkFrame(player_panel, fg_color="transparent")
        buttons_frame.pack(pady=20)
        
        self.btn_shuffle = ctk.CTkButton(
            buttons_frame,
            text="🔀",
            command=self._toggle_shuffle,
            width=60,
            height=50,
            font=ctk.CTkFont(size=20),
            fg_color=("gray70", "gray30")
        )
        self.btn_shuffle.grid(row=0, column=0, padx=5)
        self._create_tooltip(self.btn_shuffle, "Tryb losowy")

        self.btn_prev = ctk.CTkButton(
            buttons_frame,
            text="⏮",
            command=self._previous,
            width=70,
            height=50,
            font=ctk.CTkFont(size=20),
            state="disabled"
        )
        self.btn_prev.grid(row=0, column=1, padx=5)
        self._create_tooltip(self.btn_prev, "Poprzedni utwór")

        self.btn_play_pause = ctk.CTkButton(
            buttons_frame,
            text="▶",
            command=self._toggle_play_pause,
            width=90,
            height=50,
            font=ctk.CTkFont(size=24),
            state="disabled"
        )
        self.btn_play_pause.grid(row=0, column=2, padx=5)
        self._create_tooltip(self.btn_play_pause, "Odtwórz/Wstrzymaj")

        self.btn_next = ctk.CTkButton(
            buttons_frame,
            text="⏭",
            command=self._next,
            width=70,
            height=50,
            font=ctk.CTkFont(size=20),
            state="disabled"
        )
        self.btn_next.grid(row=0, column=3, padx=5)
        self._create_tooltip(self.btn_next, "Następny utwór")

        self.btn_loop = ctk.CTkButton(
            buttons_frame,
            text="🔁",
            command=self._cycle_loop,
            width=60,
            height=50,
            font=ctk.CTkFont(size=20),
            fg_color=("gray70", "gray30")
        )
        self.btn_loop.grid(row=0, column=4, padx=5)
        self._create_tooltip(self.btn_loop, "Zapętlenie: wyłączone")

        volume_frame = ctk.CTkFrame(player_panel, fg_color="transparent")
        volume_frame.pack(pady=20)

        ctk.CTkLabel(
            volume_frame,
            text="🔊 Głośność:",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=10)

        current_volume = self.context.data_manager.get_nested("settings", "music_volume", default=0.5)
        self.slider_volume = ctk.CTkSlider(
            volume_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            command=self._volume_changed,
            width=300,
            height=20
        )
        self.slider_volume.set(current_volume)
        self.slider_volume.pack(side="left", padx=10)
        
        self.volume_label = ctk.CTkLabel(
            volume_frame,
            text=f"{int(current_volume * 100)}%",
            font=ctk.CTkFont(size=12),
            width=40
        )
        self.volume_label.pack(side="left", padx=5)
    
    def _create_tooltip(self, widget, text: str) -> None:  # type: ignore[no-untyped-def]
        """Utwórz tooltip dla widgetu."""
        def show_tooltip(event) -> None:  # type: ignore[no-untyped-def]
            tooltip = ctk.CTkToplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            label = ctk.CTkLabel(
                tooltip,
                text=text,
                fg_color=("gray80", "gray20"),
                corner_radius=6,
                padx=10,
                pady=5
            )
            label.pack()
            widget._tooltip = tooltip
        
        def hide_tooltip(event) -> None:  # type: ignore[no-untyped-def]
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                delattr(widget, '_tooltip')
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def _refresh_playlist_selector(self) -> None:
        """Odśwież listę dostępnych playlist."""
        playlists = list(self.context.music.playlists.keys())
        if not playlists:
            playlists = ["Brak"]
        self.playlist_selector.configure(values=playlists)
        if self.context.music.playlist_name in playlists:
            self.playlist_selector.set(self.context.music.playlist_name)
        elif playlists:
            self.playlist_selector.set(playlists[0])
    
    def _on_playlist_selected(self, name: str) -> None:
        """Obsłuż wybór playlisty."""
        if name == "Brak":
            return
        
        success = self.context.music.load_playlist_by_name(name)
        if success:
            self._enable_controls()
            self.track_label.configure(text=f"Playlista: {name}")
    
    def _refresh_track_list(self) -> None:
        """Odśwież listę utworów."""
        for widget in self.track_listbox.winfo_children():
            widget.destroy()
        
        for idx, track in enumerate(self.context.music.playlist):
            track_frame = ctk.CTkFrame(self.track_listbox, fg_color="transparent")
            track_frame.pack(fill="x", pady=2, padx=5)
            
            is_current = idx == self.context.music.current_index
            
            btn = ctk.CTkButton(
                track_frame,
                text=f"{'▶ ' if is_current else ''}{track.name}",
                command=lambda i=idx: self._play_track(i),
                anchor="w",
                fg_color=("gray80", "gray25") if is_current else "transparent",
                hover_color=("gray70", "gray30"),
                height=32
            )
            btn.pack(side="left", fill="x", expand=True)
    
    def _play_track(self, index: int) -> None:
        """Odtwórz wybrany utwór."""
        self.context.music.play(index)
        self._refresh_track_list()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()

    def _load_from_folder(self) -> None:
        """Wczytaj utwory z folderu."""
        directory = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if directory:
            self.context.music.load_playlist(directory)
            self.context.music.add_music_folder(directory)
            self._enable_controls()
            self._refresh_track_list()
            self.track_label.configure(text="Playlista załadowana z folderu")

    def _add_tracks(self) -> None:
        """Dodaj utwory do playlisty."""
        filetypes = [
            ("Pliki audio", "*.mp3 *.wav *.ogg *.flac"),
            ("Wszystkie pliki", "*.*")
        ]
        files = filedialog.askopenfilenames(title="Wybierz utwory", filetypes=filetypes)
        if files:
            for file in files:
                track_path = Path(file)
                if track_path not in self.context.music.playlist:
                    self.context.music.playlist.append(track_path)
            self._refresh_track_list()
            logger.info(f"Dodano {len(files)} utworów do playlisty")

    def _remove_selected_track(self) -> None:
        """Usuń aktualnie wybrany utwór."""
        music = self.context.music
        if music.playlist and music.current_index < len(music.playlist):
            removed_track = music.playlist.pop(music.current_index)
            logger.info(f"Usunięto utwór: {removed_track.name}")
            if music.current_index >= len(music.playlist) and music.playlist:
                music.current_index = len(music.playlist) - 1
            self._refresh_track_list()

    def _clear_playlist(self) -> None:
        """Wyczyść całą playlistę."""
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz wyczyścić całą playlistę?"):
            self.context.music.stop()
            self.context.music.playlist = []
            self.context.music.current_index = 0
            self._refresh_track_list()
            self.track_label.configure(text="Playlista wyczyszczona")

    def _save_playlist(self) -> None:
        """Zapisz aktualną playlistę."""
        if not self.context.music.playlist:
            messagebox.showwarning("Brak utworów", "Playlista jest pusta. Dodaj najpierw utwory.")
            return
        
        name = simpledialog.askstring("Zapisz playlistę", "Podaj nazwę playlisty:")
        if name:
            success = self.context.music.save_playlist(name)
            if success:
                messagebox.showinfo("Sukces", f"Zapisano playlistę: {name}")
                self._refresh_playlist_selector()
            else:
                messagebox.showerror("Błąd", "Nie udało się zapisać playlisty")

    def _enable_controls(self) -> None:
        """Włącz kontrolki odtwarzacza."""
        self.btn_prev.configure(state="normal")
        self.btn_play_pause.configure(state="normal")
        self.btn_next.configure(state="normal")

    def _toggle_play_pause(self) -> None:
        """Przełącz odtwarzanie/pauzę."""
        music = self.context.music
        if music.is_paused:
            music.resume()
            self.btn_play_pause.configure(text="⏸")
            self._start_progress_updates()
        elif music.is_playing:
            music.pause()
            self.btn_play_pause.configure(text="▶")
            self._stop_progress_updates()
        else:
            music.play()
            if music.current_track:
                self.track_label.configure(text=f"Odtwarzanie: {music.current_track.name}")
                self.btn_play_pause.configure(text="⏸")
                self._start_progress_updates()
                self._refresh_track_list()

    def _next(self) -> None:
        """Następny utwór."""
        self.context.music.next()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()
            self._refresh_track_list()

    def _previous(self) -> None:
        """Poprzedni utwór."""
        self.context.music.previous()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()
            self._refresh_track_list()

    def _toggle_shuffle(self) -> None:
        """Przełącz tryb losowy."""
        self.context.music.set_shuffle(not self.context.music.shuffle_mode)
        self._update_shuffle_button()

    def _update_shuffle_button(self) -> None:
        """Zaktualizuj wygląd przycisku shuffle."""
        if self.context.music.shuffle_mode:
            self.btn_shuffle.configure(fg_color=self.context.theme.get_active_theme().accent)
            self._create_tooltip(self.btn_shuffle, "Tryb losowy: włączony")
        else:
            self.btn_shuffle.configure(fg_color=("gray70", "gray30"))
            self._create_tooltip(self.btn_shuffle, "Tryb losowy: wyłączony")

    def _cycle_loop(self) -> None:
        """Przełącz tryb zapętlenia."""
        self.context.music.cycle_loop_mode()
        self._update_loop_button()

    def _update_loop_button(self) -> None:
        """Zaktualizuj wygląd przycisku loop."""
        loop_mode = self.context.music.loop_mode
        
        if loop_mode == LoopMode.NO_LOOP:
            self.btn_loop.configure(
                text="🔁",
                fg_color=("gray70", "gray30")
            )
            tooltip = "Zapętlenie: wyłączone"
        elif loop_mode == LoopMode.LOOP_TRACK:
            self.btn_loop.configure(
                text="🔂",
                fg_color=self.context.theme.get_active_theme().accent
            )
            tooltip = "Zapętlenie: utwór"
        else:  # LOOP_PLAYLIST
            self.btn_loop.configure(
                text="🔁",
                fg_color=self.context.theme.get_active_theme().accent
            )
            tooltip = "Zapętlenie: playlista"
        
        self._create_tooltip(self.btn_loop, tooltip)

    def _volume_changed(self, value: float) -> None:
        """Obsłuż zmianę głośności."""
        self.context.music.set_volume(value)
        self.volume_label.configure(text=f"{int(value * 100)}%")
    
    def _on_seek_start(self, event) -> None:  # type: ignore[no-untyped-def]
        """Rozpocznij przewijanie."""
        self.is_seeking = True
    
    def _on_seek_end(self, event) -> None:  # type: ignore[no-untyped-def]
        """Zakończ przewijanie."""
        self.is_seeking = False
        position = self.progress_slider.get()
        self.context.music.seek(position)
    
    def _on_seek_slider_change(self, value: float) -> None:
        """Aktualizuj etykietę czasu podczas przewijania."""
        if self.is_seeking:
            minutes = int(value // 60)
            seconds = int(value % 60)
            self.time_label_current.configure(text=f"{minutes}:{seconds:02d}")
    
    def _update_progress(self) -> None:
        """Aktualizuj pasek postępu."""
        music = self.context.music
        
        if music.is_playing and not self.is_seeking:
            try:
                current_pos = music.get_pos()
                track_length = music.get_length()
                
                self.progress_slider.configure(to=track_length)
                self.progress_slider.set(current_pos)
                
                curr_min = int(current_pos // 60)
                curr_sec = int(current_pos % 60)
                self.time_label_current.configure(text=f"{curr_min}:{curr_sec:02d}")
                
                total_min = int(track_length // 60)
                total_sec = int(track_length % 60)
                self.time_label_total.configure(text=f"{total_min}:{total_sec:02d}")
                
                if music.check_track_ended():
                    self._refresh_track_list()
                    if music.current_track:
                        self.track_label.configure(text=f"Odtwarzanie: {music.current_track.name}")
                    elif not music.is_playing:
                        self.btn_play_pause.configure(text="▶")
            except Exception as e:
                logger.error(f"Błąd aktualizacji postępu: {e}")
        
        self.update_timer_id = self.after(500, self._update_progress)
    
    def _start_progress_updates(self) -> None:
        """Rozpocznij aktualizacje postępu."""
        if self.update_timer_id is None:
            self._update_progress()
    
    def _stop_progress_updates(self) -> None:
        """Zatrzymaj aktualizacje postępu."""
        if self.update_timer_id is not None:
            self.after_cancel(self.update_timer_id)
            self.update_timer_id = None
    
    def _sync_with_music_state(self) -> None:
        """Synchronizuj widok z aktualnym stanem muzyki."""
        music = self.context.music
        
        if music.playlist:
            self._enable_controls()
            self._refresh_track_list()
            
            if music.current_track:
                track_name = music.current_track.name
                self.track_label.configure(text=f"Odtwarzanie: {track_name}")
                
                if music.is_paused:
                    self.btn_play_pause.configure(text="▶")
                else:
                    self.btn_play_pause.configure(text="⏸")
                
                current_pos = music.get_pos()
                track_length = music.get_length()
                
                self.progress_slider.configure(to=track_length)
                self.progress_slider.set(current_pos)
                
                curr_min = int(current_pos // 60)
                curr_sec = int(current_pos % 60)
                self.time_label_current.configure(text=f"{curr_min}:{curr_sec:02d}")
                
                total_min = int(track_length // 60)
                total_sec = int(track_length % 60)
                self.time_label_total.configure(text=f"{total_min}:{total_sec:02d}")
                
                if music.is_playing and not music.is_paused:
                    self._start_progress_updates()
            else:
                self.track_label.configure(text="Playlista załadowana - kliknij ▶")
        else:
            self.track_label.configure(text="Nie wybrano playlisty")
        
        self._update_shuffle_button()
        self._update_loop_button()
    
    def destroy(self) -> None:
        """Zatrzymaj timer przed zniszczeniem widoku."""
        self._stop_progress_updates()
        super().destroy()
