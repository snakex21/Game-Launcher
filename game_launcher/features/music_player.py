"""
Music Player - Prosty odtwarzacz muzyki w tle
AI-Friendly: Pygame mixer do odtwarzania
"""

import os
import random
from pathlib import Path
import pygame
from mutagen import File as MutagenFile
from utils.logger import get_logger


class MusicPlayer:
    """
    Odtwarzacz muzyki w tle dla launchera.
    
    AI Note:
    - Obsługa MP3, OGG, WAV
    - Shuffle, loop, volume control
    - Metadata z mutagen
    """
    
    def __init__(self, music_folder=None):
        """
        Inicjalizuje odtwarzacz.
        
        Args:
            music_folder (str): Ścieżka do folderu z muzyką
        """
        self.logger = get_logger()
        self.music_folder = Path(music_folder) if music_folder else None
        
        # Inicjalizacja pygame mixer
        try:
            pygame.mixer.init()
            self.logger.info("Music player initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize pygame mixer: {e}")
            raise
        
        # Playlista
        self.playlist = []
        self.current_index = -1
        self.current_track = None
        
        # Ustawienia
        self.volume = 0.5
        self.shuffle = False
        self.loop = False
        self.is_playing = False
        
        # Załaduj playlistę jeśli folder podany
        if self.music_folder and self.music_folder.exists():
            self.load_playlist()
    
    def load_playlist(self, folder=None):
        """
        Ładuje playlistę z folderu.
        
        Args:
            folder (str/Path): Folder z muzyką (opcjonalnie)
        
        Returns:
            int: Liczba załadowanych utworów
        
        AI Note: Skanuje folder rekurencyjnie
        """
        if folder:
            self.music_folder = Path(folder)
        
        if not self.music_folder or not self.music_folder.exists():
            self.logger.warning("Music folder not found")
            return 0
        
        self.playlist = []
        
        # Wspierane formaty
        supported_formats = {'.mp3', '.ogg', '.wav', '.flac'}
        
        # Skanuj folder
        for file_path in self.music_folder.rglob('*'):
            if file_path.suffix.lower() in supported_formats:
                self.playlist.append(str(file_path))
        
        self.logger.info(f"Loaded {len(self.playlist)} tracks from {self.music_folder}")
        return len(self.playlist)
    
    def play(self, track_index=None):
        """
        Odtwarza utwór.
        
        Args:
            track_index (int): Indeks utworu w playliście (None = kontynuuj/następny)
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Automatycznie przechodzi do następnego przy końcu
        """
        if not self.playlist:
            self.logger.warning("Playlist is empty")
            return False
        
        # Określ który utwór odtwarzać
        if track_index is not None:
            self.current_index = track_index
        elif self.current_index == -1:
            self.current_index = 0
        
        # Pobierz ścieżkę
        track_path = self.playlist[self.current_index]
        
        try:
            # Załaduj i odtwarzaj
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            
            self.current_track = track_path
            self.is_playing = True
            
            # Event na końcu utworu
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            
            self.logger.info(f"Playing: {Path(track_path).name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to play {track_path}: {e}")
            return False
    
    def pause(self):
        """
        Pauzuje odtwarzanie.
        
        AI Note: Można wznowić przez unpause()
        """
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.logger.info("Music paused")
    
    def unpause(self):
        """Wznawia odtwarzanie."""
        if not self.is_playing:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.logger.info("Music unpaused")
    
    def stop(self):
        """Zatrzymuje odtwarzanie."""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.current_track = None
        self.logger.info("Music stopped")
    
    def next_track(self):
        """
        Następny utwór.
        
        AI Note: Respektuje shuffle i loop
        """
        if not self.playlist:
            return
        
        if self.shuffle:
            # Losowy utwór (różny od obecnego)
            available = list(range(len(self.playlist)))
            if self.current_index in available:
                available.remove(self.current_index)
            
            if available:
                self.current_index = random.choice(available)
            else:
                self.current_index = 0
        else:
            # Kolejny utwór
            self.current_index = (self.current_index + 1) % len(self.playlist)
        
        self.play(self.current_index)
    
    def previous_track(self):
        """Poprzedni utwór."""
        if not self.playlist:
            return
        
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play(self.current_index)
    
    def set_volume(self, volume):
        """
        Ustawia głośność.
        
        Args:
            volume (float): Głośność 0.0 - 1.0
        """
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        self.logger.debug(f"Volume set to {self.volume}")
    
    def toggle_shuffle(self):
        """Przełącza tryb shuffle."""
        self.shuffle = not self.shuffle
        self.logger.info(f"Shuffle: {self.shuffle}")
        return self.shuffle
    
    def toggle_loop(self):
        """Przełącza tryb loop."""
        self.loop = not self.loop
        self.logger.info(f"Loop: {self.loop}")
        return self.loop
    
    def get_current_track_info(self):
        """
        Zwraca informacje o aktualnym utworze.
        
        Returns:
            dict: Metadata utworu (title, artist, album, duration)
        
        AI Note: Używa mutagen do odczytu tagów
        """
        if not self.current_track:
            return None
        
        try:
            # Mutagen do odczytu metadanych
            audio = MutagenFile(self.current_track)
            
            info = {
                'file': Path(self.current_track).name,
                'path': self.current_track,
                'title': 'Unknown',
                'artist': 'Unknown',
                'album': 'Unknown',
                'duration': 0
            }
            
            if audio:
                # Tytuł
                if 'title' in audio:
                    info['title'] = str(audio['title'][0]) if isinstance(audio['title'], list) else str(audio['title'])
                elif 'TIT2' in audio:  # MP3
                    info['title'] = str(audio['TIT2'])
                
                # Artysta
                if 'artist' in audio:
                    info['artist'] = str(audio['artist'][0]) if isinstance(audio['artist'], list) else str(audio['artist'])
                elif 'TPE1' in audio:  # MP3
                    info['artist'] = str(audio['TPE1'])
                
                # Album
                if 'album' in audio:
                    info['album'] = str(audio['album'][0]) if isinstance(audio['album'], list) else str(audio['album'])
                elif 'TALB' in audio:  # MP3
                    info['album'] = str(audio['TALB'])
                
                # Długość
                if hasattr(audio.info, 'length'):
                    info['duration'] = int(audio.info.length)
            
            # Fallback na nazwę pliku
            if info['title'] == 'Unknown':
                info['title'] = Path(self.current_track).stem
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get track info: {e}")
            return {
                'file': Path(self.current_track).name,
                'title': Path(self.current_track).stem,
                'artist': 'Unknown',
                'album': 'Unknown',
                'duration': 0
            }
    
    def get_playlist_info(self):
        """
        Zwraca informacje o playliście.
        
        Returns:
            list: Lista dict z info o utworach
        """
        playlist_info = []
        
        for track_path in self.playlist:
            try:
                audio = MutagenFile(track_path)
                title = Path(track_path).stem
                
                if audio and 'title' in audio:
                    title = str(audio['title'][0]) if isinstance(audio['title'], list) else str(audio['title'])
                
                playlist_info.append({
                    'path': track_path,
                    'title': title
                })
            except:
                playlist_info.append({
                    'path': track_path,
                    'title': Path(track_path).stem
                })
        
        return playlist_info
    
    def check_music_end(self):
        """
        Sprawdza czy utwór się skończył.
        
        Returns:
            bool: True jeśli utwór się skończył
        
        AI Note: Wywołuj w głównej pętli aplikacji dla auto-next
        """
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:
                # Utwór się skończył
                if self.loop:
                    self.play(self.current_index)  # Powtórz
                else:
                    self.next_track()  # Następny
                return True
        return False