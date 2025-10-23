"""Odtwarzacz muzyki."""
from __future__ import annotations

import logging
from tkinter import filedialog

import customtkinter as ctk

from .base import BasePlugin

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

        controls = ctk.CTkFrame(self, corner_radius=15)
        controls.pack(pady=20, padx=20)
        
        self._setup_ui(controls)
        self._sync_with_music_state()  # Synchronizuj stan przy wejściu
    
    def _setup_ui(self, controls) -> None:  # type: ignore[no-untyped-def]
        """Ustawia elementy UI."""
        self.track_label = ctk.CTkLabel(
            controls,
            text="Nie wybrano playlisty",
            font=ctk.CTkFont(size=14),
            width=400
        )
        self.track_label.pack(pady=(20, 10))
        
        # Pasek postępu utworu
        progress_container = ctk.CTkFrame(controls, fg_color="transparent")
        progress_container.pack(pady=(5, 10), padx=20, fill="x")
        
        self.time_label_current = ctk.CTkLabel(
            progress_container,
            text="0:00",
            font=ctk.CTkFont(size=11),
            width=50
        )
        self.time_label_current.pack(side="left", padx=(0, 5))
        
        self.progress_slider = ctk.CTkSlider(
            progress_container,
            from_=0,
            to=100,
            number_of_steps=1000,
            command=self._on_seek_slider_change,
            width=300
        )
        self.progress_slider.set(0)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_slider.bind("<Button-1>", self._on_seek_start)
        self.progress_slider.bind("<ButtonRelease-1>", self._on_seek_end)
        
        self.time_label_total = ctk.CTkLabel(
            progress_container,
            text="0:00",
            font=ctk.CTkFont(size=11),
            width=50
        )
        self.time_label_total.pack(side="left", padx=(5, 0))

        buttons_frame = ctk.CTkFrame(controls, fg_color="transparent")
        buttons_frame.pack(pady=10)

        self.btn_prev = ctk.CTkButton(
            buttons_frame,
            text="⏮",
            command=self._previous,
            width=60,
            state="disabled"
        )
        self.btn_prev.grid(row=0, column=0, padx=5)

        self.btn_play = ctk.CTkButton(
            buttons_frame,
            text="▶",
            command=self._play,
            width=80,
            state="disabled"
        )
        self.btn_play.grid(row=0, column=1, padx=5)

        self.btn_pause = ctk.CTkButton(
            buttons_frame,
            text="⏸",
            command=self._pause,
            width=80,
            state="disabled"
        )
        self.btn_pause.grid(row=0, column=2, padx=5)

        self.btn_next = ctk.CTkButton(
            buttons_frame,
            text="⏭",
            command=self._next,
            width=60,
            state="disabled"
        )
        self.btn_next.grid(row=0, column=3, padx=5)

        volume_frame = ctk.CTkFrame(controls, fg_color="transparent")
        volume_frame.pack(pady=15)

        ctk.CTkLabel(volume_frame, text="🔊 Głośność:").pack(side="left", padx=10)

        current_volume = self.context.data_manager.get_nested("settings", "music_volume", default=0.5)
        self.slider_volume = ctk.CTkSlider(
            volume_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            command=self._volume_changed,
            width=200
        )
        self.slider_volume.set(current_volume)
        self.slider_volume.pack(side="left", padx=10)

        btn_load = ctk.CTkButton(
            controls,
            text="📂 Wczytaj playlistę",
            command=self._load_playlist,
            width=200
        )
        btn_load.pack(pady=(10, 20))

    def _load_playlist(self) -> None:
        directory = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if directory:
            self.context.music.load_playlist(directory)
            self._enable_controls()
            self.track_label.configure(text="Playlista załadowana")

    def _enable_controls(self) -> None:
        self.btn_prev.configure(state="normal")
        self.btn_play.configure(state="normal")
        self.btn_pause.configure(state="normal")
        self.btn_next.configure(state="normal")

    def _play(self) -> None:
        self.context.music.play()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()

    def _pause(self) -> None:
        if self.context.music.is_paused:
            self.context.music.resume()
            self.btn_pause.configure(text="⏸")
            self._start_progress_updates()
        else:
            self.context.music.pause()
            self.btn_pause.configure(text="▶")
            self._stop_progress_updates()

    def _next(self) -> None:
        self.context.music.next()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()

    def _previous(self) -> None:
        self.context.music.previous()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            self._start_progress_updates()

    def _volume_changed(self, value: float) -> None:
        self.context.music.set_volume(value)
    
    def _on_seek_start(self, event) -> None:  # type: ignore[no-untyped-def]
        """Wywoływane gdy użytkownik zaczyna przesuwać suwak."""
        self.is_seeking = True
    
    def _on_seek_end(self, event) -> None:  # type: ignore[no-untyped-def]
        """Wywoływane gdy użytkownik kończy przesuwać suwak."""
        self.is_seeking = False
        position = self.progress_slider.get()
        self.context.music.seek(position)
    
    def _on_seek_slider_change(self, value: float) -> None:
        """Aktualizuje etykietę czasu podczas przesuwania suwaka."""
        if self.is_seeking:
            minutes = int(value // 60)
            seconds = int(value % 60)
            self.time_label_current.configure(text=f"{minutes}:{seconds:02d}")
    
    def _update_progress(self) -> None:
        """Aktualizuje pasek postępu i etykiety czasu."""
        if self.context.music.is_playing and not self.is_seeking:
            try:
                current_pos = self.context.music.get_pos()
                track_length = self.context.music.get_length()
                
                # Aktualizuj slider
                self.progress_slider.configure(to=track_length)
                self.progress_slider.set(current_pos)
                
                # Aktualizuj etykiety czasu
                curr_min = int(current_pos // 60)
                curr_sec = int(current_pos % 60)
                self.time_label_current.configure(text=f"{curr_min}:{curr_sec:02d}")
                
                total_min = int(track_length // 60)
                total_sec = int(track_length % 60)
                self.time_label_total.configure(text=f"{total_min}:{total_sec:02d}")
                
                # Sprawdź czy utwór się skończył
                if current_pos >= track_length - 1 and track_length > 0:
                    self.context.music.next()
                    if self.context.music.current_track:
                        self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji postępu: {e}")
        
        # Zaplanuj następną aktualizację
        self.update_timer_id = self.after(500, self._update_progress)
    
    def _start_progress_updates(self) -> None:
        """Rozpoczyna okresowe aktualizacje paska postępu."""
        if self.update_timer_id is None:
            self._update_progress()
    
    def _stop_progress_updates(self) -> None:
        """Zatrzymuje okresowe aktualizacje paska postępu."""
        if self.update_timer_id is not None:
            self.after_cancel(self.update_timer_id)
            self.update_timer_id = None
    
    def _sync_with_music_state(self) -> None:
        """Synchronizuje widok z aktualnym stanem muzyki."""
        music = self.context.music
        
        # Sprawdź czy jest playlista
        if music.playlist:
            self._enable_controls()
            
            # Sprawdź czy coś gra
            if music.current_track:
                track_name = music.current_track.name
                self.track_label.configure(text=f"Odtwarzanie: {track_name}")
                
                # Zaktualizuj przyciski
                if music.is_paused:
                    self.btn_pause.configure(text="▶")
                else:
                    self.btn_pause.configure(text="⏸")
                
                # Zaktualizuj pasek postępu
                current_pos = music.get_pos()
                track_length = music.get_length()
                
                self.progress_slider.configure(to=track_length)
                self.progress_slider.set(current_pos)
                
                # Zaktualizuj czasy
                curr_min = int(current_pos // 60)
                curr_sec = int(current_pos % 60)
                self.time_label_current.configure(text=f"{curr_min}:{curr_sec:02d}")
                
                total_min = int(track_length // 60)
                total_sec = int(track_length % 60)
                self.time_label_total.configure(text=f"{total_min}:{total_sec:02d}")
                
                # Uruchom timer jeśli muzyka gra
                if music.is_playing and not music.is_paused:
                    self._start_progress_updates()
            else:
                self.track_label.configure(text="Playlista załadowana - kliknij ▶")
        else:
            self.track_label.configure(text="Nie wybrano playlisty")
    
    def destroy(self) -> None:
        """Zatrzymaj timer przed zniszczeniem widoku."""
        self._stop_progress_updates()
        super().destroy()
