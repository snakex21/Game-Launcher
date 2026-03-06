import logging
import tkinter as tk
from tkinter import simpledialog

from launcher.utils import save_config


def _on_root_resize(self, event):
    """Obsługuje zmianę rozmiaru głównego okna z opóźnieniem przy realnej zmianie."""
    if event.widget == self.root:
        new_width = event.width
        new_height = event.height

        size_changed = (
            new_width != self._last_root_width or new_height != self._last_root_height
        )

        if size_changed:
            logging.debug(
                f"Wykryto zmianę rozmiaru okna: {self._last_root_width}x{self._last_root_height} -> {new_width}x{new_height}"
            )
            self._last_root_width = new_width
            self._last_root_height = new_height

            if self._resize_timer:
                self.root.after_cancel(self._resize_timer)

            if (
                hasattr(self, "main_frame")
                and hasattr(self, "library_view_mode")
                and hasattr(self, "current_frame")
            ):
                if self.current_frame == self.main_frame and self.library_view_mode.get() == "tiles":
                    self._resize_timer = self.root.after(250, self.reset_and_update_grid)


def _center_window(self, root, width, height):
    """Oblicza i ustawia geometrię okna, aby wyśrodkować je na ekranie."""
    root.update_idletasks()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    try:
        root.geometry(f"{width}x{height}+{x}+{y}")
        logging.info(f"Ustawiono okno na środku ekranu: {width}x{height}+{x}+{y}")
    except tk.TclError as e:
        logging.error(
            f"Błąd TclError podczas centrowania okna {width}x{height}+{x}+{y}: {e}. Używam domyślnej pozycji."
        )
        root.geometry(f"{width}x{height}+100+100")


def ask_for_username(self):
    username = simpledialog.askstring("Nazwa Użytkownika", "Podaj swoją nazwę użytkownika:")
    if username:
        self.user["username"] = username
    else:
        self.user["username"] = "Gracz"
    save_config(self.config)


__all__ = [
    "_on_root_resize",
    "_center_window",
    "ask_for_username",
]
