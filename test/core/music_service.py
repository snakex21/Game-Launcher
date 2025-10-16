# core/music_service.py
import os
import random
import threading
import time
from pygame import mixer, error as PygameError

VALID_MUSIC_EXT = ('.mp3', '.wav', '.ogg', '.flac')

class MusicService:
    def __init__(self, app_context):
        self.app_context = app_context
        mixer.init()
        self.playlist = []
        self.original_playlist = [] # Do przywracania po wyłączeniu shuffle
        self.current_song_index = -1
        self.current_song_length = 0
        self.state = "stopped"
        self._stop_event = threading.Event()

        # Nowe stany
        self.shuffle = False
        self.loop_mode = "none" # "none", "song", "playlist"

    def start(self):
        threading.Thread(target=self._monitor_playback, daemon=True).start()

    def shutdown(self):
        self._stop_event.set()
        self.stop()

    def load_playlist(self, folder_path):
        self.stop()
        self.original_playlist = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(VALID_MUSIC_EXT)]
        self.playlist = list(self.original_playlist)
        if self.shuffle: self._shuffle_playlist()
        self.current_song_index = 0 if self.playlist else -1
        print(f"Załadowano {len(self.playlist)} utworów.")

    def play(self, index=None):
        if not self.playlist: return
        if index is not None: self.current_song_index = index
        
        try:
            song_path = self.playlist[self.current_song_index]
            mixer.music.load(song_path)
            # Potrzebujemy osobnego obiektu Sound do pobrania długości utworu
            sound = mixer.Sound(song_path)
            self.current_song_length = sound.get_length()
            mixer.music.play()
            self.state = "playing"
            
            song_title = os.path.basename(song_path)
            self.app_context.event_manager.emit("song_changed", song_title=song_title)
            self.app_context.event_manager.emit("playback_state_changed", state=self.state)
        except PygameError as e:
            print(f"Błąd Pygame podczas odtwarzania: {e}")
            self.next_song() # Spróbuj następny utwór

    def toggle_play_pause(self):
        if self.state == "playing": self.pause()
        elif self.state == "paused": self.unpause()
        else: self.play(0 if self.current_song_index == -1 else self.current_song_index)

    def pause(self): mixer.music.pause(); self.state = "paused"; self.app_context.event_manager.emit("playback_state_changed", state=self.state)
    def unpause(self): mixer.music.unpause(); self.state = "playing"; self.app_context.event_manager.emit("playback_state_changed", state=self.state)
    def stop(self): mixer.music.stop(); self.state = "stopped"; self.app_context.event_manager.emit("playback_state_changed", state=self.state)

    def next_song(self):
        if not self.playlist: return
        if self.shuffle:
            self.current_song_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
        self.play()

    def prev_song(self):
        if not self.playlist: return
        self.current_song_index = (self.current_song_index - 1) % len(self.playlist)
        self.play()
        
    def cycle_loop_mode(self):
        modes = ["none", "playlist", "song"]
        current_idx = modes.index(self.loop_mode)
        self.loop_mode = modes[(current_idx + 1) % len(modes)]
        self.app_context.event_manager.emit("player_mode_changed", mode="loop", value=self.loop_mode)
        return self.loop_mode

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        if self.shuffle: self._shuffle_playlist()
        else: self.playlist = list(self.original_playlist)
        self.app_context.event_manager.emit("player_mode_changed", mode="shuffle", value=self.shuffle)
        return self.shuffle

    def _shuffle_playlist(self):
        if not self.original_playlist: return
        current_song = self.playlist[self.current_song_index] if self.current_song_index != -1 else None
        self.playlist = list(self.original_playlist)
        random.shuffle(self.playlist)
        if current_song and current_song in self.playlist:
            # Upewnij się, że aktualny utwór jest na początku po przemieszaniu
            self.playlist.insert(0, self.playlist.pop(self.playlist.index(current_song)))
            self.current_song_index = 0

    def get_playback_info(self):
        if self.state == "stopped": return {"position": 0, "length": 0}
        pos_seconds = mixer.music.get_pos() / 1000
        return {"position": pos_seconds, "length": self.current_song_length}

    def seek(self, position_seconds):
        if self.state != "stopped":
            mixer.music.set_pos(position_seconds)

    def _monitor_playback(self):
        while not self._stop_event.is_set():
            if self.state == "playing" and not mixer.music.get_busy():
                if self.loop_mode == "song":
                    self.play() # Odtwórz ten sam utwór od nowa
                elif self.loop_mode == "playlist":
                    self.next_song()
                elif self.current_song_index == len(self.playlist) - 1:
                    self.stop() # Koniec playlisty, zatrzymaj
                else:
                    self.next_song()
            time.sleep(1)