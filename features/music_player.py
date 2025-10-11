"""
Odtwarzacz muzyki
Zarządza odtwarzaniem muzyki, playlistą i integracją z Last.fm.
"""

import os
import logging
import pygame
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from mutagen import File as MutagenFile

from config.constants import SUPPORTED_AUDIO_FORMATS

logger = logging.getLogger(__name__)


class MusicPlayer:
    """
    Klasa zarządzająca odtwarzaniem muzyki.
    Obsługuje playlistę, shuffle, repeat i metadata utworów.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje odtwarzacz muzyki.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        
        # Inicjalizacja pygame mixer
        try:
            pygame.mixer.init()
            logger.info("Pygame mixer zainicjalizowany")
        except Exception as e:
            logger.error(f"Błąd inicjalizacji pygame mixer: {e}")
        
        # Playlista i stan
        self.playlist: List[Path] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.is_paused: bool = False
        
        # Ustawienia
        self.volume: float = 0.5
        self.shuffle_enabled: bool = False
        self.repeat_enabled: bool = False
        
        # Shuffle history (żeby nie powtarzać utworów)
        self.shuffle_history: List[int] = []
        
        # Metadata aktualnego utworu
        self.current_track_info: Dict[str, Any] = {}
        
        # Timer dla aktualizacji pozycji
        self.position_update_job = None
        
        # Załaduj ustawienia
        self._load_settings()
        
        logger.debug("MusicPlayer zainicjalizowany")
    
    def _load_settings(self):
        """Ładuje ustawienia odtwarzacza z konfiguracji."""
        if self.launcher and self.launcher.settings:
            self.volume = self.launcher.settings.get("music.volume", 0.5)
            self.shuffle_enabled = self.launcher.settings.get("music.shuffle", False)
            self.repeat_enabled = self.launcher.settings.get("music.repeat", False)
            
            # Ustaw głośność
            pygame.mixer.music.set_volume(self.volume)
            
            logger.debug(f"Załadowano ustawienia muzyki: vol={self.volume}, shuffle={self.shuffle_enabled}")
    
    def load_folder(self, folder_path: str) -> int:
        """
        Ładuje wszystkie pliki muzyczne z katalogu.
        
        Args:
            folder_path: Ścieżka do katalogu z muzyką
            
        Returns:
            Liczba załadowanych plików
        """
        try:
            folder = Path(folder_path)
            
            if not folder.exists() or not folder.is_dir():
                logger.warning(f"Katalog nie istnieje: {folder_path}")
                return 0
            
            # Znajdź wszystkie pliki audio
            audio_files = []
            for ext in SUPPORTED_AUDIO_FORMATS:
                audio_files.extend(folder.rglob(f"*{ext}"))
            
            # Sortuj alfabetycznie
            audio_files.sort()
            
            self.playlist = audio_files
            self.current_index = 0
            
            logger.info(f"Załadowano {len(self.playlist)} utworów z {folder_path}")
            return len(self.playlist)
            
        except Exception as e:
            logger.error(f"Błąd ładowania katalogu muzyki {folder_path}: {e}")
            return 0
    
    def add_to_playlist(self, filepath: str) -> bool:
        """
        Dodaje plik do playlisty.
        
        Args:
            filepath: Ścieżka do pliku audio
            
        Returns:
            True jeśli dodano pomyślnie
        """
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                logger.warning(f"Plik nie istnieje: {filepath}")
                return False
            
            if filepath.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
                logger.warning(f"Nieobsługiwany format: {filepath.suffix}")
                return False
            
            self.playlist.append(filepath)
            logger.debug(f"Dodano do playlisty: {filepath.name}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd dodawania do playlisty {filepath}: {e}")
            return False
    
    def clear_playlist(self):
        """Czyści playlistę."""
        self.playlist.clear()
        self.current_index = 0
        logger.debug("Playlista wyczyszczona")
    
    def play(self, index: Optional[int] = None) -> bool:
        """
        Rozpoczyna odtwarzanie.
        
        Args:
            index: Indeks utworu do odtworzenia (None = aktualny)
            
        Returns:
            True jeśli rozpoczęto odtwarzanie
        """
        try:
            if not self.playlist:
                logger.warning("Playlista pusta")
                return False
            
            # Ustaw indeks jeśli podany
            if index is not None:
                self.current_index = max(0, min(index, len(self.playlist) - 1))
            
            # Załaduj i odtwórz
            current_track = self.playlist[self.current_index]
            pygame.mixer.music.load(str(current_track))
            pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            
            # Załaduj metadata
            self._load_track_metadata(current_track)
            
            # Powiadom launcher o zmianie utworu
            if self.launcher:
                self._notify_track_change()
            
            logger.info(f"Odtwarzanie: {current_track.name}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd odtwarzania: {e}")
            return False
    
    def pause(self):
        """Pauzuje odtwarzanie."""
        try:
            if self.is_playing and not self.is_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
                logger.debug("Odtwarzanie zapauzowane")
        except Exception as e:
            logger.error(f"Błąd pauzowania: {e}")
    
    def unpause(self):
        """Wznawia odtwarzanie."""
        try:
            if self.is_playing and self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                logger.debug("Odtwarzanie wznowione")
        except Exception as e:
            logger.error(f"Błąd wznawiania: {e}")
    
    def stop(self):
        """Zatrzymuje odtwarzanie."""
        try:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            logger.debug("Odtwarzanie zatrzymane")
        except Exception as e:
            logger.error(f"Błąd zatrzymywania: {e}")
    
    def next_track(self) -> bool:
        """
        Przechodzi do następnego utworu.
        
        Returns:
            True jeśli przeskoczono do następnego
        """
        try:
            if not self.playlist:
                return False
            
            if self.shuffle_enabled:
                # Losowy utwór (ale nie ostatnio grany)
                self._next_shuffle()
            else:
                # Kolejny utwór
                self.current_index = (self.current_index + 1) % len(self.playlist)
            
            return self.play(self.current_index)
            
        except Exception as e:
            logger.error(f"Błąd przechodzenia do następnego utworu: {e}")
            return False
    
    def previous_track(self) -> bool:
        """
        Przechodzi do poprzedniego utworu.
        
        Returns:
            True jeśli przeskoczono do poprzedniego
        """
        try:
            if not self.playlist:
                return False
            
            if self.shuffle_enabled and self.shuffle_history:
                # Cofnij się w historii shuffle
                self.current_index = self.shuffle_history.pop()
            else:
                # Poprzedni utwór
                self.current_index = (self.current_index - 1) % len(self.playlist)
            
            return self.play(self.current_index)
            
        except Exception as e:
            logger.error(f"Błąd przechodzenia do poprzedniego utworu: {e}")
            return False
    
    def _next_shuffle(self):
        """Wybiera następny losowy utwór."""
        if len(self.playlist) <= 1:
            return
        
        # Zapisz aktualny indeks do historii
        self.shuffle_history.append(self.current_index)
        
        # Ogranicz historię
        if len(self.shuffle_history) > 50:
            self.shuffle_history = self.shuffle_history[-50:]
        
        # Wybierz losowy indeks (inny niż aktualny)
        available_indices = [i for i in range(len(self.playlist)) if i != self.current_index]
        self.current_index = random.choice(available_indices)
    
    def set_volume(self, volume: float):
        """
        Ustawia głośność.
        
        Args:
            volume: Głośność (0.0 - 1.0)
        """
        try:
            self.volume = max(0.0, min(1.0, volume))
            pygame.mixer.music.set_volume(self.volume)
            
            # Zapisz do ustawień
            if self.launcher and self.launcher.settings:
                self.launcher.settings.set("music.volume", self.volume)
            
            logger.debug(f"Głośność ustawiona: {self.volume:.2f}")
        except Exception as e:
            logger.error(f"Błąd ustawiania głośności: {e}")
    
    def toggle_shuffle(self):
        """Przełącza tryb shuffle."""
        self.shuffle_enabled = not self.shuffle_enabled
        
        # Wyczyść historię przy włączeniu
        if self.shuffle_enabled:
            self.shuffle_history.clear()
        
        # Zapisz do ustawień
        if self.launcher and self.launcher.settings:
            self.launcher.settings.set("music.shuffle", self.shuffle_enabled)
        
        logger.debug(f"Shuffle: {self.shuffle_enabled}")
    
    def toggle_repeat(self):
        """Przełącza tryb repeat."""
        self.repeat_enabled = not self.repeat_enabled
        
        # Zapisz do ustawień
        if self.launcher and self.launcher.settings:
            self.launcher.settings.set("music.repeat", self.repeat_enabled)
        
        logger.debug(f"Repeat: {self.repeat_enabled}")
    
    def get_position(self) -> int:
        """
        Zwraca aktualną pozycję odtwarzania w sekundach.
        
        Returns:
            Pozycja w sekundach
        """
        try:
            if self.is_playing:
                # pygame zwraca pozycję w milisekundach
                return int(pygame.mixer.music.get_pos() / 1000)
            return 0
        except Exception as e:
            logger.error(f"Błąd pobierania pozycji: {e}")
            return 0
    
    def _load_track_metadata(self, filepath: Path):
        """
        Ładuje metadata utworu.
        
        Args:
            filepath: Ścieżka do pliku audio
        """
        try:
            audio = MutagenFile(str(filepath))
            
            if audio is None:
                # Brak metadata, użyj nazwy pliku
                self.current_track_info = {
                    'title': filepath.stem,
                    'artist': 'Nieznany',
                    'album': '',
                    'duration': 0,
                    'filepath': str(filepath)
                }
                return
            
            # Wyciągnij metadata
            self.current_track_info = {
                'title': str(audio.get('title', [filepath.stem])[0]) if audio.get('title') else filepath.stem,
                'artist': str(audio.get('artist', ['Nieznany'])[0]) if audio.get('artist') else 'Nieznany',
                'album': str(audio.get('album', [''])[0]) if audio.get('album') else '',
                'duration': int(audio.info.length) if hasattr(audio, 'info') else 0,
                'filepath': str(filepath)
            }
            
            logger.debug(f"Załadowano metadata: {self.current_track_info['title']} - {self.current_track_info['artist']}")
            
        except Exception as e:
            logger.error(f"Błąd ładowania metadata {filepath}: {e}")
            self.current_track_info = {
                'title': filepath.stem,
                'artist': 'Nieznany',
                'album': '',
                'duration': 0,
                'filepath': str(filepath)
            }
    
    def _notify_track_change(self):
        """Powiadamia launcher o zmianie utworu."""
        try:
            # Aktualizuj overlay
            if hasattr(self.launcher, 'track_overlay_window') and self.launcher.track_overlay_window:
                track_name = f"{self.current_track_info.get('artist', 'Nieznany')} - {self.current_track_info.get('title', 'Nieznany')}"
                self.launcher.track_overlay_window.update_track_info(
                    track_name,
                    0,
                    self.current_track_info.get('duration', 0)
                )
            
            # Scrobbluj do Last.fm (jeśli włączone)
            # TODO: Implementacja scrobblowania
            
        except Exception as e:
            logger.error(f"Błąd powiadamiania o zmianie utworu: {e}")
    
    def check_if_ended(self) -> bool:
        """
        Sprawdza czy utwór się skończył.
        
        Returns:
            True jeśli utwór się skończył
        """
        try:
            if self.is_playing and not pygame.mixer.music.get_busy():
                # Utwór się skończył
                if self.repeat_enabled:
                    # Powtórz ten sam
                    self.play(self.current_index)
                else:
                    # Następny
                    self.next_track()
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd sprawdzania końca utworu: {e}")
            return False
    
    def get_current_track_info(self) -> Dict[str, Any]:
        """
        Zwraca informacje o aktualnym utworze.
        
        Returns:
            Słownik z informacjami o utworze
        """
        return self.current_track_info.copy()
    
    def get_playlist_info(self) -> List[Dict[str, str]]:
        """
        Zwraca informacje o wszystkich utworach w playliście.
        
        Returns:
            Lista słowników z informacjami o utworach
        """
        playlist_info = []
        
        for filepath in self.playlist:
            playlist_info.append({
                'filename': filepath.name,
                'path': str(filepath)
            })
        
        return playlist_info
    
    def cleanup(self):
        """Czyści zasoby odtwarzacza."""
        try:
            self.stop()
            pygame.mixer.quit()
            logger.info("MusicPlayer oczyszczony")
        except Exception as e:
            logger.error(f"Błąd czyszczenia MusicPlayer: {e}")
