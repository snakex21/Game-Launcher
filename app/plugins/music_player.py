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

        title = ctk.CTkLabel(
            self,
            text="🎵 Odtwarzacz Muzyki",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=20)

        controls = ctk.CTkFrame(self, corner_radius=15)
        controls.pack(pady=20, padx=20)

        self.track_label = ctk.CTkLabel(
            controls,
            text="Nie wybrano playlisty",
            font=ctk.CTkFont(size=14),
            width=400
        )
        self.track_label.pack(pady=(20, 10))

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

    def _pause(self) -> None:
        if self.context.music.is_paused:
            self.context.music.resume()
            self.btn_pause.configure(text="⏸")
        else:
            self.context.music.pause()
            self.btn_pause.configure(text="▶")

    def _next(self) -> None:
        self.context.music.next()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")

    def _previous(self) -> None:
        self.context.music.previous()
        if self.context.music.current_track:
            self.track_label.configure(text=f"Odtwarzanie: {self.context.music.current_track.name}")

    def _volume_changed(self, value: float) -> None:
        self.context.music.set_volume(value)
