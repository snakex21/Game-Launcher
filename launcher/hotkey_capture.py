import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pynput import keyboard


def _set_music_hotkey_dialog(
    self,
    action_key: str,
    string_var_to_update: tk.StringVar,
    entry_widget_to_update: ttk.Entry,
):
    """
    Otwiera okno/logikę do nasłuchiwania i ustawiania nowego skrótu klawiszowego.
    Używa pynput.keyboard.Listener.
    """
    logging.debug(f"Rozpoczęto ustawianie skrótu dla akcji: {action_key}")
    if (
        hasattr(self, "key_combination_listener")
        and self.key_combination_listener
        and self.key_combination_listener.is_alive()
    ):
        messagebox.showwarning(
            "Uwaga",
            "Już jesteś w trakcie ustawiania innego skrótu.\nZakończ lub anuluj poprzednią próbę.",
            parent=(
                self.settings_page_frame
                if hasattr(self, "settings_page_frame")
                else self.root
            ),
        )
        if (
            hasattr(self, "capturing_hotkey_toplevel")
            and self.capturing_hotkey_toplevel.winfo_exists()
        ):
            self.capturing_hotkey_toplevel.lift()
        return

    self.current_new_hotkey_action = action_key
    self.current_new_hotkey_stringvar = string_var_to_update
    self._pressed_keys_for_new_hotkey = set()

    self.capturing_hotkey_toplevel = tk.Toplevel(
        self.settings_page_frame
        if hasattr(self, "settings_page_frame")
        else self.root
    )
    self.capturing_hotkey_toplevel.title("Ustawianie Skrótu")

    parent_for_geometry = (
        self.settings_page_frame
        if hasattr(self, "settings_page_frame")
        and self.settings_page_frame.winfo_exists()
        else self.root
    )
    parent_x = parent_for_geometry.winfo_rootx()
    parent_y = parent_for_geometry.winfo_rooty()
    parent_w = parent_for_geometry.winfo_width()
    parent_h = parent_for_geometry.winfo_height()
    dialog_w = 350
    dialog_h = 130
    pos_x = parent_x + (parent_w // 2) - (dialog_w // 2)
    pos_y = parent_y + (parent_h // 2) - (dialog_h // 2)
    self.capturing_hotkey_toplevel.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")

    self.capturing_hotkey_toplevel.transient(parent_for_geometry)
    self.capturing_hotkey_toplevel.grab_set()
    self.capturing_hotkey_toplevel.resizable(False, False)

    display_action_name = self.hotkey_actions_display_names.get(action_key, action_key)

    ttk.Label(
        self.capturing_hotkey_toplevel,
        text=f"Naciśnij nową kombinację klawiszy dla:\n'{display_action_name}'",
        wraplength=330,
        justify="center",
        anchor="center",
    ).pack(pady=(10, 5), fill="x", expand=True)
    self.capturing_hotkey_label = ttk.Label(
        self.capturing_hotkey_toplevel,
        text="...",
        font=("Segoe UI", 10, "bold"),
        anchor="center",
    )
    self.capturing_hotkey_label.pack(pady=5, fill="x", expand=True)
    ttk.Button(
        self.capturing_hotkey_toplevel,
        text="Anuluj",
        command=self._cancel_hotkey_capture,
    ).pack(pady=(0, 10))

    self.capturing_hotkey_toplevel.protocol("WM_DELETE_WINDOW", self._cancel_hotkey_capture)
    self.capturing_hotkey_toplevel.focus_force()

    if (
        hasattr(self, "global_hotkeys_listener")
        and self.global_hotkeys_listener
        and self.global_hotkeys_listener.is_alive()
    ):
        self.global_hotkeys_listener.stop()
        logging.debug(
            "Tymczasowo zatrzymano GlobalHotKeys na czas ustawiania nowego skrótu."
        )

    try:
        self.key_combination_listener = keyboard.Listener(
            on_press=self._on_press_for_new_hotkey,
            on_release=self._on_release_for_new_hotkey,
            suppress=True,
        )
        self.key_combination_listener.start()
        logging.debug(
            "Uruchomiono listenera pynput (keyboard.Listener) dla nowego skrótu (suppress=True)."
        )
    except Exception as e:
        logging.error(
            f"Nie udało się uruchomić listenera pynput (keyboard.Listener): {e}"
        )
        messagebox.showerror(
            "Błąd Listenera",
            "Nie można było uruchomić nasłuchiwania klawiatury.",
            parent=(
                self.capturing_hotkey_toplevel
                if hasattr(self, "capturing_hotkey_toplevel")
                and self.capturing_hotkey_toplevel.winfo_exists()
                else self.root
            ),
        )
        self._cancel_hotkey_capture()
        self._reregister_all_global_hotkeys()


__all__ = [
    "_set_music_hotkey_dialog",
    "_cancel_hotkey_capture",
]


def _cancel_hotkey_capture(self):
    """Anuluje proces ustawiania nowego skrótu i przywraca globalne skróty."""
    if (
        hasattr(self, "key_combination_listener")
        and self.key_combination_listener
        and self.key_combination_listener.is_alive()
    ):
        self.key_combination_listener.stop()
        self.key_combination_listener.join(timeout=0.1)
        logging.debug("Anulowano i zatrzymano listenera dla nowego skrótu.")
    self.key_combination_listener = None

    if (
        hasattr(self, "capturing_hotkey_toplevel")
        and self.capturing_hotkey_toplevel.winfo_exists()
    ):
        self.capturing_hotkey_toplevel.destroy()

    if self.local_settings.get("music_hotkeys_enabled", True):
        self._reregister_all_global_hotkeys()

    self.current_new_hotkey_action = None
    self.current_new_hotkey_stringvar = None
    if hasattr(self, "_pressed_keys_for_new_hotkey"):
        self._pressed_keys_for_new_hotkey.clear()
