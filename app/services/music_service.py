"""Odtwarzacz muzyki oparty na pygame."""
from __future__ import annotations

import json
import logging
import os
import random
from enum import Enum
from pathlib import Path
from typing import Any

import pygame

logger = logging.getLogger(__name__)


class LoopMode(Enum):
    """Tryby zapętlenia."""
    NO_LOOP = "no_loop"
    LOOP_TRACK = "loop_track"
    LOOP_PLAYLIST = "loop_playlist"


class MusicService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        self.current_track: Path | None = None
        self.playlist: list[Path] = []
        self.playlist_name: str = "Domyślna"
        self.playlists: dict[str, list[str]] = {}  # Nazwa playlisty -> lista ścieżek
        self.current_index: int = 0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.shuffle_mode: bool = False
        self.loop_mode: LoopMode = LoopMode.NO_LOOP
        self.shuffle_history: list[int] = []  # Historia odtwarzanych utworów w trybie losowym
        self.seek_offset: float = 0.0
        self.track_length_cache: dict[str, float] = {}
        
        try:
            pygame.mixer.init()
            logger.info("Zainicjalizowano pygame.mixer")
        except Exception as e:
            logger.error("Błąd inicjalizacji pygame.mixer: %s", e)
            self.event_bus.emit("music_error", error="Nie udało się zainicjalizować pygame.mixer. Sprawdź czy są zainstalowane odpowiednie kodeki audio.")
        
        self._load_config()
        self._load_playlists()

    def _load_config(self) -> None:
        """Wczytaj konfigurację muzyki z config.json."""
        music_config = self.data_manager.get_nested("settings", "music", default={})
        
        self.shuffle_mode = music_config.get("shuffle", False)
        loop_mode_str = music_config.get("loop_mode", "no_loop")
        try:
            self.loop_mode = LoopMode(loop_mode_str)
        except ValueError:
            self.loop_mode = LoopMode.NO_LOOP
        
        # Wczytaj foldery muzyczne
        self.music_folders: list[str] = music_config.get("music_folders", [])
        
        # Dodaj wewnętrzny katalog launchera jeśli istnieje
        internal_music_dir = Path(__file__).resolve().parents[1] / "data" / "music"
        if internal_music_dir.exists() and str(internal_music_dir) not in self.music_folders:
            self.music_folders.append(str(internal_music_dir))
            self._save_config()

    def _save_config(self) -> None:
        """Zapisz konfigurację muzyki do config.json."""
        music_config = {
            "shuffle": self.shuffle_mode,
            "loop_mode": self.loop_mode.value,
            "music_folders": self.music_folders,
        }
        self.data_manager.set_nested("settings", "music", value=music_config)

    def _load_playlists(self) -> None:
        """Wczytaj playlisty z plików."""
        playlists_dir = Path(__file__).resolve().parents[1] / "data" / "playlists"
        playlists_dir.mkdir(exist_ok=True)
        
        self.playlists = {}
        
        # Wczytaj playlisty JSON
        for playlist_file in playlists_dir.glob("*.json"):
            try:
                with open(playlist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    playlist_name = data.get("name", playlist_file.stem)
                    tracks = data.get("tracks", [])
                    self.playlists[playlist_name] = tracks
                    logger.info(f"Załadowano playlistę: {playlist_name} ({len(tracks)} utworów)")
            except Exception as e:
                logger.error(f"Błąd wczytywania playlisty {playlist_file}: {e}")
        
        # Wczytaj playlisty M3U
        for playlist_file in playlists_dir.glob("*.m3u"):
            try:
                with open(playlist_file, "r", encoding="utf-8") as f:
                    tracks = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    playlist_name = playlist_file.stem
                    self.playlists[playlist_name] = tracks
                    logger.info(f"Załadowano playlistę M3U: {playlist_name} ({len(tracks)} utworów)")
            except Exception as e:
                logger.error(f"Błąd wczytywania playlisty M3U {playlist_file}: {e}")

    def save_playlist(self, name: str, format: str = "json") -> bool:
        """Zapisz aktualną playlistę do pliku."""
        playlists_dir = Path(__file__).resolve().parents[1] / "data" / "playlists"
        playlists_dir.mkdir(exist_ok=True)
        
        tracks = [str(track) for track in self.playlist]
        
        try:
            if format == "json":
                playlist_file = playlists_dir / f"{name}.json"
                data = {
                    "name": name,
                    "tracks": tracks
                }
                with open(playlist_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == "m3u":
                playlist_file = playlists_dir / f"{name}.m3u"
                with open(playlist_file, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    for track in tracks:
                        f.write(f"{track}\n")
            else:
                logger.error(f"Nieznany format playlisty: {format}")
                return False
            
            self.playlists[name] = tracks
            logger.info(f"Zapisano playlistę: {name} ({len(tracks)} utworów)")
            self.event_bus.emit("playlist_saved", name=name)
            return True
        except Exception as e:
            logger.error(f"Błąd zapisywania playlisty {name}: {e}")
            self.event_bus.emit("music_error", error=f"Nie udało się zapisać playlisty: {e}")
            return False

    def load_playlist_by_name(self, name: str) -> bool:
        """Wczytaj playlistę po nazwie."""
        if name not in self.playlists:
            logger.warning(f"Playlista {name} nie istnieje")
            return False
        
        self.playlist = [Path(track) for track in self.playlists[name] if Path(track).exists()]
        self.playlist_name = name
        self.current_index = 0
        self.shuffle_history = []
        
        logger.info(f"Załadowano playlistę: {name} ({len(self.playlist)} utworów)")
        self.event_bus.emit("playlist_loaded", tracks=len(self.playlist), name=name)
        return True

    def delete_playlist(self, name: str) -> bool:
        """Usuń playlistę."""
        if name not in self.playlists:
            return False
        
        playlists_dir = Path(__file__).resolve().parents[1] / "data" / "playlists"
        
        # Usuń pliki
        for ext in ["json", "m3u"]:
            playlist_file = playlists_dir / f"{name}.{ext}"
            if playlist_file.exists():
                try:
                    playlist_file.unlink()
                except Exception as e:
                    logger.error(f"Błąd usuwania pliku playlisty {playlist_file}: {e}")
        
        # Usuń z pamięci
        del self.playlists[name]
        logger.info(f"Usunięto playlistę: {name}")
        self.event_bus.emit("playlist_deleted", name=name)
        return True

    def add_music_folder(self, folder_path: str) -> None:
        """Dodaj folder muzyczny do konfiguracji."""
        if folder_path not in self.music_folders:
            self.music_folders.append(folder_path)
            self._save_config()
            logger.info(f"Dodano folder muzyczny: {folder_path}")

    def remove_music_folder(self, folder_path: str) -> None:
        """Usuń folder muzyczny z konfiguracji."""
        if folder_path in self.music_folders:
            self.music_folders.remove(folder_path)
            self._save_config()
            logger.info(f"Usunięto folder muzyczny: {folder_path}")

    def scan_music_folders(self) -> list[Path]:
        """Przeskanuj wszystkie foldery muzyczne i zwróć listę plików."""
        all_tracks: list[Path] = []
        
        for folder in self.music_folders:
            path = Path(folder)
            if not path.exists():
                logger.warning(f"Katalog z muzyką nie istnieje: {folder}")
                continue
            
            for ext in ["*.mp3", "*.wav", "*.ogg", "*.flac"]:
                all_tracks.extend(path.glob(ext))
        
        logger.info(f"Przeskanowano foldery, znaleziono {len(all_tracks)} utworów")
        return all_tracks

    def load_playlist(self, directory: str) -> None:
        """Wczytaj playlistę z katalogu (legacy)."""
        path = Path(directory)
        if not path.exists():
            logger.warning(f"Katalog z muzyką nie istnieje: {directory}")
            self.event_bus.emit("music_error", error=f"Katalog nie istnieje: {directory}")
            return

        self.playlist = []
        for ext in ["*.mp3", "*.wav", "*.ogg", "*.flac"]:
            self.playlist.extend(path.glob(ext))
        
        self.shuffle_history = []
        logger.info(f"Załadowano playlistę: {len(self.playlist)} utworów")
        self.event_bus.emit("playlist_loaded", tracks=len(self.playlist), name="Domyślna")

    def set_shuffle(self, enabled: bool) -> None:
        """Włącz/wyłącz tryb losowy."""
        self.shuffle_mode = enabled
        self.shuffle_history = []
        self._save_config()
        logger.info(f"Tryb losowy: {'włączony' if enabled else 'wyłączony'}")
        self.event_bus.emit("shuffle_changed", enabled=enabled)

    def set_loop_mode(self, mode: LoopMode) -> None:
        """Ustaw tryb zapętlenia."""
        self.loop_mode = mode
        self._save_config()
        logger.info(f"Tryb zapętlenia: {mode.value}")
        self.event_bus.emit("loop_mode_changed", mode=mode.value)

    def cycle_loop_mode(self) -> LoopMode:
        """Przełącz tryb zapętlenia na kolejny."""
        modes = [LoopMode.NO_LOOP, LoopMode.LOOP_TRACK, LoopMode.LOOP_PLAYLIST]
        current_idx = modes.index(self.loop_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.set_loop_mode(modes[next_idx])
        return self.loop_mode

    def _get_next_track_index(self) -> int:
        """Zwróć indeks następnego utworu uwzględniając shuffle i loop."""
        if not self.playlist:
            return 0
        
        if self.shuffle_mode:
            # W trybie losowym wybierz losowy utwór (pomijając ostatnio odtwarzane)
            available = [i for i in range(len(self.playlist)) if i not in self.shuffle_history[-10:]]
            if not available:
                self.shuffle_history = []
                available = list(range(len(self.playlist)))
            
            next_idx = random.choice(available)
            self.shuffle_history.append(next_idx)
            return next_idx
        else:
            # Normalny tryb sekwencyjny
            return (self.current_index + 1) % len(self.playlist)

    def play(self, track_index: int | None = None) -> None:
        """Odtwórz utwór."""
        if not self.playlist:
            logger.warning("Playlista jest pusta")
            self.event_bus.emit("music_error", error="Playlista jest pusta. Wczytaj playlistę lub dodaj utwory.")
            return

        if track_index is not None:
            self.current_index = track_index
            if self.shuffle_mode:
                self.shuffle_history.append(track_index)

        try:
            track = self.playlist[self.current_index]
            pygame.mixer.music.load(str(track))
            volume = self.data_manager.get_nested("settings", "music_volume", default=0.5)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            self.seek_offset = 0.0
            logger.info(f"Odtwarzanie: {track.name}")
            self.event_bus.emit("music_started", track=track.name, index=self.current_index)
        except Exception as e:
            error_msg = f"Błąd odtwarzania: {e}. Sprawdź czy plik istnieje i jest w obsługiwanym formacie."
            logger.error(error_msg)
            self.event_bus.emit("music_error", error=error_msg)

    def pause(self) -> None:
        """Wstrzymaj odtwarzanie."""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            logger.info("Wstrzymano odtwarzanie")
            self.event_bus.emit("music_paused")

    def resume(self) -> None:
        """Wznów odtwarzanie."""
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            logger.info("Wznowiono odtwarzanie")
            self.event_bus.emit("music_resumed")

    def stop(self) -> None:
        """Zatrzymaj odtwarzanie."""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        logger.info("Zatrzymano odtwarzanie")
        self.event_bus.emit("music_stopped")

    def next(self) -> None:
        """Następny utwór."""
        if not self.playlist:
            return
        
        if self.loop_mode == LoopMode.LOOP_TRACK:
            # Powtórz ten sam utwór
            self.play(self.current_index)
        else:
            self.current_index = self._get_next_track_index()
            self.play()

    def previous(self) -> None:
        """Poprzedni utwór."""
        if not self.playlist:
            return
        
        if self.shuffle_mode and self.shuffle_history:
            # W trybie losowym wróć do poprzedniego z historii
            if len(self.shuffle_history) > 1:
                self.shuffle_history.pop()  # Usuń aktualny
                prev_idx = self.shuffle_history[-1]
                self.current_index = prev_idx
        else:
            self.current_index = (self.current_index - 1) % len(self.playlist)
        
        self.play()

    def set_volume(self, volume: float) -> None:
        """Ustaw głośność."""
        clamped = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(clamped)
        self.data_manager.set_nested("settings", "music_volume", value=clamped)
        logger.info(f"Ustawiono głośność: {clamped:.2f}")
    
    def get_pos(self) -> float:
        """Zwraca aktualną pozycję w utworze w sekundach."""
        if self.is_playing and not self.is_paused:
            return self.seek_offset + (pygame.mixer.music.get_pos() / 1000.0)
        return self.seek_offset
    
    def get_length(self) -> float:
        """Zwraca długość aktualnego utworu w sekundach."""
        if not self.current_track:
            return 0.0
        
        track_path = str(self.current_track)
        if track_path in self.track_length_cache:
            return self.track_length_cache[track_path]
        
        length = 0.0
        try:
            from mutagen import File
            audio = File(track_path)
            if audio and hasattr(audio.info, 'length'):
                length = audio.info.length
                self.track_length_cache[track_path] = length
                return length
        except Exception:
            pass
        
        length = 180.0
        self.track_length_cache[track_path] = length
        return length
    
    def seek(self, position: float) -> None:
        """Przewija utwór do podanej pozycji w sekundach."""
        if not self.current_track:
            return
            
        was_paused = self.is_paused
        
        try:
            pygame.mixer.music.load(str(self.current_track))
            volume = self.data_manager.get_nested("settings", "music_volume", default=0.5)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(start=position)
            
            self.seek_offset = position
            self.is_playing = True
            
            if was_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
            else:
                self.is_paused = False
            
            logger.info(f"Przewinięto do pozycji: {position:.2f}s")
            self.event_bus.emit("music_seeked", position=position)
        except Exception as e:
            logger.error(f"Błąd podczas przewijania: {e}")
            self.event_bus.emit("music_error", error=f"Błąd przewijania: {e}")

    def check_track_ended(self) -> bool:
        """Sprawdź czy utwór się zakończył i obsłuż autoplay."""
        if not self.is_playing or self.is_paused:
            return False
        
        pos = self.get_pos()
        length = self.get_length()
        
        if pos >= length - 1 and length > 0:
            if self.loop_mode == LoopMode.LOOP_TRACK:
                self.play(self.current_index)
            elif self.loop_mode == LoopMode.LOOP_PLAYLIST:
                self.next()
            elif self.loop_mode == LoopMode.NO_LOOP:
                # Sprawdź czy to ostatni utwór
                next_idx = (self.current_index + 1) % len(self.playlist)
                if next_idx != 0:  # Nie pierwszy utwór, więc nie koniec playlisty
                    self.next()
                else:
                    # Koniec playlisty
                    self.stop()
            return True
        return False
