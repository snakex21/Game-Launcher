# plugins/library/post_session_window.py
import customtkinter as ctk

def format_duration(seconds):
    """Konwertuje sekundy na format Xm Ys."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"

class PostSessionWindow(ctk.CTkToplevel):
    def __init__(self, parent, game_data, session_duration, on_save_callback):
        super().__init__(parent)
        self.game_data = game_data
        self.on_save_callback = on_save_callback

        self.title("Podsumowanie Sesji")
        self.geometry("450x300")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close) # Obsługa zamknięcia okna krzyżykiem

        ctk.CTkLabel(self, text=f"Zakończono sesję dla:", font=("Roboto", 14)).pack(pady=(20, 0))
        ctk.CTkLabel(self, text=game_data.get('name'), font=("Roboto", 20, "bold")).pack()
        ctk.CTkLabel(self, text=f"Czas trwania: {format_duration(session_duration)}", font=("Roboto", 12)).pack(pady=(0, 20))

        ctk.CTkLabel(self, text="Zaktualizuj postęp ukończenia gry:").pack()
        
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.pack(fill="x", padx=20, pady=10)

        initial_progress = game_data.get('completion_percent', 0)
        self.progress_slider = ctk.CTkSlider(slider_frame, from_=0, to=100, number_of_steps=100, command=self._update_progress_label)
        self.progress_slider.set(initial_progress)
        self.progress_slider.pack(side="left", fill="x", expand=True)
        
        self.progress_label = ctk.CTkLabel(slider_frame, text=f"{initial_progress}%", width=40)
        self.progress_label.pack(side="left", padx=(10, 0))

        ctk.CTkButton(self, text="Zapisz i zamknij", command=self._save_and_close).pack(pady=20)

    def _update_progress_label(self, value):
        self.progress_label.configure(text=f"{int(value)}%")

    def _save_and_close(self):
        new_completion = int(self.progress_slider.get())
        if self.on_save_callback:
            self.on_save_callback(self.game_data.get('id'), new_completion)
        self.destroy()

    def _on_close(self):
        # Jeśli użytkownik zamknie okno bez zapisywania, zapisz tylko czas gry (bez zmiany postępu)
        if self.on_save_callback:
            current_completion = self.game_data.get('completion_percent', 0)
            self.on_save_callback(self.game_data.get('id'), current_completion)
        self.destroy()