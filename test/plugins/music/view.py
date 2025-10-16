# plugins/music/view.py
import customtkinter as ctk
from tkinter import filedialog
import os

def format_time(seconds):
    if seconds is None: return "0:00"
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes}:{seconds:02d}"

class MusicView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.is_seeking = False
        self._setup_ui()
        
        self.app_context.event_manager.subscribe("song_changed", self._on_song_changed)
        self.app_context.event_manager.subscribe("playback_state_changed", self._update_play_button)
        self.app_context.event_manager.subscribe("player_mode_changed", self._update_mode_buttons)

    def refresh_view(self):
        music_data = self.app_context.data_manager.get_plugin_data("music")
        folder = music_data.get("music_folder")
        if folder and os.path.isdir(folder):
            self.folder_label.configure(text=f"Folder: {os.path.basename(folder)}")
            self.app_context.music_service.load_playlist(folder)
        else:
            self.folder_label.configure(text="Nie wybrano folderu z muzyką.")
        
        self.app_context.music_service.loop_mode = music_data.get("loop_mode", "none")
        self.app_context.music_service.shuffle = music_data.get("shuffle_enabled", False)
        self._update_mode_buttons()

    def _setup_ui(self):
        self.pack_propagate(False)
        container = ctk.CTkFrame(self); container.pack(expand=True, padx=20, pady=20)
        
        self.current_song_label = ctk.CTkLabel(container, text="Wybierz folder z muzyką", font=("Roboto", 18, "bold"), wraplength=400)
        self.current_song_label.pack(pady=(10, 5))
        
        # --- ZMIENIONA LOGIKA SUWAKA ---
        progress_container = ctk.CTkFrame(container, fg_color="transparent")
        progress_container.pack(fill="x", padx=10, pady=5)
        self.time_elapsed_label = ctk.CTkLabel(progress_container, text="0:00", width=40); self.time_elapsed_label.pack(side="left")
        
        # Usuwamy 'command', aby uniknąć ciągłego wywoływania
        self.progress_slider = ctk.CTkSlider(progress_container, from_=0, to=100) 
        self.progress_slider.bind("<Button-1>", self._on_seek_start)
        self.progress_slider.bind("<ButtonRelease-1>", self._on_seek_release)
        self.progress_slider.set(0)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=10)
        self.total_time_label = ctk.CTkLabel(progress_container, text="0:00", width=40); self.total_time_label.pack(side="left")

        # ... (reszta UI bez zmian) ...
        controls_frame = ctk.CTkFrame(container, fg_color="transparent")
        controls_frame.pack(pady=10)
        self.shuffle_button = ctk.CTkButton(controls_frame, text="🔀", width=50, command=self._toggle_shuffle); self.shuffle_button.pack(side="left", padx=5)
        ctk.CTkButton(controls_frame, text="⏮", width=60, command=self.app_context.music_service.prev_song).pack(side="left", padx=5)
        self.play_pause_button = ctk.CTkButton(controls_frame, text="▶", width=80, command=self.app_context.music_service.toggle_play_pause); self.play_pause_button.pack(side="left", padx=5)
        ctk.CTkButton(controls_frame, text="⏭", width=60, command=self.app_context.music_service.next_song).pack(side="left", padx=5)
        self.loop_button = ctk.CTkButton(controls_frame, text="🔁", width=50, command=self._cycle_loop); self.loop_button.pack(side="left", padx=5)

        folder_frame = ctk.CTkFrame(self); folder_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        self.folder_label = ctk.CTkLabel(folder_frame, text="..."); self.folder_label.pack(side="left", padx=10)
        ctk.CTkButton(folder_frame, text="Wybierz folder...", command=self._select_folder).pack(side="right", padx=10, pady=10)

        self._update_progress()

    def _update_progress(self):
        if not self.is_seeking and self.app_context.music_service.state in ["playing", "paused"]:
            info = self.app_context.music_service.get_playback_info()
            self.time_elapsed_label.configure(text=format_time(info['position']))
            self.total_time_label.configure(text=format_time(info['length']))
            if info['length'] > 0:
                # Aktualizuj suwak tylko jeśli nie jest "chwycony" przez użytkownika
                self.progress_slider.set(info['position'] / info['length'] * 100)
        
        self.after(500, self._update_progress) # Odświeżaj trochę częściej dla płynności

    # --- NOWE FUNKCJE OBSŁUGI SUWAKA ---
    def _on_seek_start(self, event):
        """Wywoływane po kliknięciu na suwak."""
        self.is_seeking = True

    def _on_seek_release(self, event):
        """Wywoływane po puszczeniu suwaka - tutaj dzieje się magia."""
        self.is_seeking = False
        # Pobierz wartość suwaka w momencie puszczenia
        slider_value = self.progress_slider.get()
        length = self.app_context.music_service.get_playback_info()['length']
        if length > 0:
            seek_time = length * (slider_value / 100)
            self.app_context.music_service.seek(seek_time)

    def _on_song_changed(self, song_title):
        self.current_song_label.configure(text=song_title.rsplit('.', 1)[0])
        self.progress_slider.set(0)
        
    def _update_play_button(self, state):
        self.play_pause_button.configure(text="⏸" if state == "playing" else "▶")

    def _toggle_shuffle(self):
        self.app_context.music_service.toggle_shuffle()
        self._save_player_modes()
        
    def _cycle_loop(self):
        self.app_context.music_service.cycle_loop_mode()
        self._save_player_modes()

    def _update_mode_buttons(self, mode=None, value=None):
        loop_mode = self.app_context.music_service.loop_mode
        if loop_mode == "song": self.loop_button.configure(text="🔁¹")
        elif loop_mode == "playlist": self.loop_button.configure(text="🔁")
        else: self.loop_button.configure(text="➡")
        
        is_shuffled = self.app_context.music_service.shuffle
        active_color = ("#3B8ED0", "#1F6AA5"); default_color = self.shuffle_button.cget("fg_color")
        self.shuffle_button.configure(fg_color=active_color if is_shuffled else default_color)

    def _save_player_modes(self):
        music_data = self.app_context.data_manager.get_plugin_data("music")
        music_data["loop_mode"] = self.app_context.music_service.loop_mode
        music_data["shuffle_enabled"] = self.app_context.music_service.shuffle
        self.app_context.data_manager.save_plugin_data("music", music_data)

    def _select_folder(self):
        folder_path = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if folder_path:
            music_data = self.app_context.data_manager.get_plugin_data("music")
            music_data["music_folder"] = folder_path
            self.app_context.data_manager.save_plugin_data("music", music_data)
            self.refresh_view()