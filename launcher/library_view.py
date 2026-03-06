import logging
import tkinter as tk

from launcher.config_store import save_local_settings


def toggle_library_view(self):
    """Przełącza tryb widoku biblioteki i odświeża UI."""
    current_mode = self.library_view_mode.get()
    new_mode = "list" if current_mode == "tiles" else "tiles"
    self.library_view_mode.set(new_mode)
    self.local_settings["library_view_mode"] = new_mode
    save_local_settings(self.local_settings)

    self.update_view_mode_button_text()
    self.reset_and_update_grid()


def _capture_initial_root_size(self):
    """Pobiera i zapisuje początkowy rozmiar okna po jego utworzeniu."""
    try:
        self.root.update_idletasks()
        self._last_root_width = self.root.winfo_width()
        self._last_root_height = self.root.winfo_height()
        logging.info(
            f"Początkowy rozmiar okna: {self._last_root_width}x{self._last_root_height}"
        )
    except tk.TclError as e:
        logging.warning(f"Błąd podczas pobierania początkowego rozmiaru okna: {e}")


def update_view_mode_button_text(self):
    """Aktualizuje tekst przycisku przełączania widoku."""
    if hasattr(self, "view_mode_button") and self.view_mode_button.winfo_exists():
        current_mode = self.library_view_mode.get()
        if current_mode == "tiles":
            self.view_mode_button.config(text="Widok: Lista")
        else:
            self.view_mode_button.config(text="Widok: Kafelki")


__all__ = [
    "toggle_library_view",
    "_capture_initial_root_size",
    "update_view_mode_button_text",
    "toggle_fullscreen",
]


def toggle_fullscreen(self):
    is_fullscreen = self.fullscreen_var.get()
    self.root.attributes("-fullscreen", is_fullscreen)
    if self.current_frame == self.main_frame and self.library_view_mode.get() == "tiles":
        self.root.after(100, self.reset_and_update_grid)
