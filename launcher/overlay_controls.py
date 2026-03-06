import logging
import tkinter as tk
from tkinter import messagebox

from launcher.config_store import save_local_settings
from ui.overlay import TrackOverlayWindow


def _initialize_track_overlay_from_settings(self):
    """Tworzy instancję overlay'a, jeśli jest włączony w ustawieniach."""
    if self.local_settings.get("show_track_overlay", False):
        self.show_track_overlay()
    else:
        self.hide_track_overlay()


def _toggle_track_overlay_setting(self):
    """Zapisuje ustawienie pokazywania overlay'a i go pokazuje/ukrywa."""
    if not hasattr(self, "show_track_overlay_var"):
        return

    show = self.show_track_overlay_var.get()
    self.local_settings["show_track_overlay"] = show
    save_local_settings(self.local_settings)
    logging.info(f"Ustawienie pokazywania nakładki odtwarzacza zmienione na: {show}")

    if show:
        self.show_track_overlay()
        if not self.overlay_update_timer:
            self.root.after(100, self._update_overlay_regularly)
    else:
        self.hide_track_overlay()
        if self.overlay_update_timer:
            self.root.after_cancel(self.overlay_update_timer)
            self.overlay_update_timer = None


def show_track_overlay(self):
    if (
        not hasattr(self, "track_overlay")
        or not self.track_overlay
        or not self.track_overlay.winfo_exists()
    ):
        logging.info("Tworzenie nowej instancji TrackOverlayWindow.")
        initial_x = self.local_settings.get("overlay_x_pos")
        initial_y = self.local_settings.get("overlay_y_pos")
        self.track_overlay = TrackOverlayWindow(
            self.root,
            initial_x,
            initial_y,
            launcher_instance=self,
            save_settings_callback=save_local_settings,
        )

    if self.track_overlay:
        try:
            self.track_overlay.show_overlay()
        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas pokazywania overlay'a: {e}")
            self.track_overlay = None


def hide_track_overlay(self):
    """Ukrywa okno nakładki, jeśli istnieje."""
    if (
        hasattr(self, "track_overlay")
        and self.track_overlay
        and self.track_overlay.winfo_exists()
    ):
        try:
            self.track_overlay.hide_overlay()
            logging.debug("Wywołano hide_overlay() na instancji TrackOverlayWindow.")
        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas ukrywania overlay'a: {e}")
            self.track_overlay = None
    else:
        logging.debug("Próba ukrycia overlay'a, który nie istnieje lub już jest ukryty.")


def _apply_overlay_position_from_settings(self):
    """Zapisuje i stosuje pozycję overlay'a z pól w ustawieniach."""
    try:
        new_x = self.overlay_x_pos_var.get()
        new_y = self.overlay_y_pos_var.get()

        self.local_settings["overlay_x_pos"] = new_x
        self.local_settings["overlay_y_pos"] = new_y
        save_local_settings(self.local_settings)
        logging.info(f"Zapisano nową pozycję overlay'a z ustawień: X={new_x}, Y={new_y}")

        if (
            hasattr(self, "track_overlay")
            and self.track_overlay
            and self.track_overlay.winfo_exists()
        ):
            self.track_overlay.x_pos = new_x
            self.track_overlay.y_pos = new_y
            self.track_overlay.geometry(
                f"{self.track_overlay.width}x{self.track_overlay.height}+{new_x}+{new_y}"
            )
            self.track_overlay.lift()
    except tk.TclError:
        messagebox.showerror(
            "Błąd Wartości",
            "Pozycja X i Y muszą być liczbami całkowitymi.",
            parent=self.settings_page_frame,
        )
    except Exception as e:
        logging.error(f"Błąd podczas stosowania pozycji overlay'a: {e}")


def _reset_overlay_position(self):
    """Resetuje pozycję overlay'a do wartości domyślnych i zapisuje."""
    if hasattr(self, "track_overlay") and self.track_overlay:
        screen_w = self.track_overlay.winfo_screenwidth()
        screen_h = self.track_overlay.winfo_screenheight()
        overlay_w = self.track_overlay.width
        overlay_h = self.track_overlay.height
    else:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        overlay_w = 300
        overlay_h = 70

    default_x = screen_w - overlay_w - 20
    default_y = screen_h - overlay_h - 60

    self.overlay_x_pos_var.set(default_x)
    self.overlay_y_pos_var.set(default_y)

    self.local_settings["overlay_x_pos"] = default_x
    self.local_settings["overlay_y_pos"] = default_y
    save_local_settings(self.local_settings)
    logging.info("Zresetowano pozycję overlay'a do domyślnej.")

    self._apply_overlay_position_from_settings()
    messagebox.showinfo(
        "Reset Pozycji",
        "Pozycja nakładki została zresetowana.",
        parent=self.settings_page_frame,
    )


__all__ = [
    "_initialize_track_overlay_from_settings",
    "_toggle_track_overlay_setting",
    "show_track_overlay",
    "hide_track_overlay",
    "_apply_overlay_position_from_settings",
    "_reset_overlay_position",
]
