"""Odtwarzacz muzyki oparty na pygame."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pygame

logger = logging.getLogger(__name__)


class MusicService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        self.current_track: Path | None = None
        self.playlist: list[Path] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.is_paused: bool = False
        
        try:
            pygame.mixer.init()
            logger.info("Zainicjalizowano pygame.mixer")
        except Exception as e:
            logger.error("Błąd inicjalizacji pygame.mixer: %s", e)

    def load_playlist(self, directory: str) -> None:
        path = Path(directory)
        if not path.exists():
            logger.warning("Katalog z muzyką nie istnieje: %s", directory)
            return

        self.playlist = []
        for ext in ["*.mp3", "*.wav", "*.ogg", "*.flac"]:
            self.playlist.extend(path.glob(ext))
        
        logger.info("Załadowano playlistę: %d utworów", len(self.playlist))
        self.event_bus.emit("playlist_loaded", tracks=len(self.playlist))

    def play(self, track_index: int | None = None) -> None:
        if not self.playlist:
            logger.warning("Playlista jest pusta")
            return

        if track_index is not None:
            self.current_index = track_index

        try:
            track = self.playlist[self.current_index]
            pygame.mixer.music.load(str(track))
            volume = self.data_manager.get_nested("settings", "music_volume", default=0.5)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            logger.info("Odtwarzanie: %s", track.name)
            self.event_bus.emit("music_started", track=track.name)
        except Exception as e:
            logger.error("Błąd odtwarzania: %s", e)

    def pause(self) -> None:
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            logger.info("Wstrzymano odtwarzanie")
            self.event_bus.emit("music_paused")

    def resume(self) -> None:
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            logger.info("Wznowiono odtwarzanie")
            self.event_bus.emit("music_resumed")

    def stop(self) -> None:
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        logger.info("Zatrzymano odtwarzanie")
        self.event_bus.emit("music_stopped")

    def next(self) -> None:
        if not self.playlist:
            return
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play()

    def previous(self) -> None:
        if not self.playlist:
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play()

    def set_volume(self, volume: float) -> None:
        clamped = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(clamped)
        self.data_manager.set_nested("settings", "music_volume", value=clamped)
        logger.info("Ustawiono głośność: %.2f", clamped)
    
    def get_pos(self) -> float:
        """Zwraca aktualną pozycję w utworze w sekundach."""
        if self.is_playing:
            return pygame.mixer.music.get_pos() / 1000.0
        return 0.0
    
    def get_length(self) -> float:
        """Zwraca długość aktualnego utworu w sekundach (wymaga pygame-ce lub mutagen)."""
        if not self.current_track:
            return 0.0
        
        try:
            # Próba użycia mutagen do odczytu długości
            from mutagen import File
            audio = File(str(self.current_track))
            if audio and hasattr(audio.info, 'length'):
                return audio.info.length
        except Exception:
            pass
        
        # Fallback - szacowanie na podstawie rozmiaru pliku (bardzo przybliżone)
        return 180.0  # Domyślnie 3 minuty
    
    def seek(self, position: float) -> None:
        """Przewija utwór do podanej pozycji w sekundach."""
        if self.is_playing and self.current_track:
            try:
                # pygame.mixer.music.set_pos działa tylko dla niektórych formatów (OGG, MP3)
                pygame.mixer.music.set_pos(position)
                logger.info("Przewinięto do pozycji: %.2fs", position)
                self.event_bus.emit("music_seeked", position=position)
            except Exception as e:
                # Jeśli set_pos nie działa, próbujemy załadować od nowa i rozpocząć od pozycji
                logger.warning("set_pos nie działa dla tego formatu, reloading: %s", e)
                try:
                    pygame.mixer.music.load(str(self.current_track))
                    volume = self.data_manager.get_nested("settings", "music_volume", default=0.5)
                    pygame.mixer.music.set_volume(volume)
                    pygame.mixer.music.play(start=position)
                    self.is_paused = False
                except Exception as e2:
                    logger.error("Błąd podczas przewijania: %s", e2)
