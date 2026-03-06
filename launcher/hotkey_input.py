import logging
import tkinter as tk
from tkinter import messagebox

from pynput import keyboard

from launcher.config_store import save_local_settings
from launcher.utils import DEFAULT_MUSIC_HOTKEYS


def _get_pynput_key_string(self, key):
    """Konwertuje obiekt klawisza pynput na string, gotowy do użycia w GlobalHotKeys."""
    if hasattr(key, "char") and key.char is not None:
        return key.char

    key_name = None
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            return key.char
    elif isinstance(key, keyboard.Key):
        key_name = key.name

    if key_name:
        if key_name in ["ctrl_l", "ctrl_r", "ctrl"]:
            return "ctrl"
        if key_name in ["alt_l", "alt_r", "alt_gr", "alt"]:
            return "alt"
        if key_name in ["shift_l", "shift_r", "shift"]:
            return "shift"
        if key_name in ["cmd", "cmd_l", "cmd_r", "win_l", "win_r"]:
            return "cmd"

        if key_name in [
            "space",
            "enter",
            "tab",
            "esc",
            "up",
            "down",
            "left",
            "right",
            "home",
            "end",
            "page_up",
            "page_down",
            "delete",
            "insert",
        ] or key_name.startswith("f"):
            return f"<{key_name}>"
        return key_name

    return str(key)


def _build_hotkey_string_from_set(self, pressed_keys_set: set) -> str | None:
    """Tworzy string skrótu z setu wciśniętych klawiszy pynput w formacie GlobalHotKeys."""
    modifiers = set()
    primary_key_str = None
    known_modifiers_internal = {"ctrl", "alt", "shift", "cmd", "super"}

    processed_key_objects = list(pressed_keys_set)

    for key_obj in list(processed_key_objects):
        internal_rep = self._get_pynput_internal_representation(key_obj)
        if internal_rep in known_modifiers_internal:
            mod_string = f"<{internal_rep}>"
            if mod_string not in modifiers:
                modifiers.add(mod_string)
            processed_key_objects.remove(key_obj)

    if processed_key_objects:
        main_key_obj = processed_key_objects[0]
        main_key_internal_rep = self._get_pynput_internal_representation(main_key_obj)

        if len(main_key_internal_rep) == 1 and main_key_internal_rep.isalnum():
            primary_key_str = main_key_internal_rep
        else:
            primary_key_str = f"<{main_key_internal_rep}>"

    if not primary_key_str:
        logging.debug(
            "_build_hotkey_string_from_set: Brak klawisza głównego w kombinacji."
        )
        return None

    sorted_modifiers_list = sorted(list(modifiers))
    if sorted_modifiers_list:
        return "+".join(sorted_modifiers_list) + "+" + primary_key_str
    return primary_key_str


def _get_pynput_internal_representation(self, key) -> str:
    """Pomocnicza, zwraca prosty string dla klawisza (bez <> dla modyfikatorów na tym etapie)."""
    if hasattr(key, "char") and key.char:
        return key.char.lower()
    if hasattr(key, "name"):
        name = key.name.lower()
        if name.startswith("ctrl"):
            return "ctrl"
        if name.startswith("alt"):
            return "alt"
        if name.startswith("shift"):
            return "shift"
        if name.startswith("cmd") or name.startswith("win") or name == "super":
            return "cmd"
        return name
    return str(key).lower()


def _on_press_for_new_hotkey(self, key):
    """Callback dla Listenera - zbiera wciśnięte klawisze."""
    if not hasattr(self, "_pressed_keys_for_new_hotkey"):
        self._pressed_keys_for_new_hotkey = set()

    self._pressed_keys_for_new_hotkey.add(key)

    current_combination = self._build_hotkey_string_from_set(
        self._pressed_keys_for_new_hotkey
    )
    if (
        hasattr(self, "capturing_hotkey_label")
        and self.capturing_hotkey_label.winfo_exists()
    ):
        self.capturing_hotkey_label.config(
            text=current_combination or "Naciśnij klawisze..."
        )
    logging.debug(
        f"Naciśnięto w listenerze: {key}, Aktualna kombinacja: {current_combination}"
    )


def _on_release_for_new_hotkey(self, key):
    """Callback dla Listenera - finalizuje ustawianie skrótu po zwolnieniu 'głównego' klawisza."""
    if (
        not hasattr(self, "_pressed_keys_for_new_hotkey")
        or not self._pressed_keys_for_new_hotkey
    ):
        if self.key_combination_listener and self.key_combination_listener.is_alive():
            self.key_combination_listener.stop()
        if (
            hasattr(self, "capturing_hotkey_toplevel")
            and self.capturing_hotkey_toplevel.winfo_exists()
        ):
            try:
                self.capturing_hotkey_toplevel.destroy()
            except tk.TclError:
                pass
        return False

    is_main_key_released = False
    released_key_internal_rep = self._get_pynput_internal_representation(key)
    if released_key_internal_rep not in ["ctrl", "alt", "shift", "cmd", "super"]:
        is_main_key_released = True
    elif (
        len(self._pressed_keys_for_new_hotkey) == 1
        and key in self._pressed_keys_for_new_hotkey
    ):
        is_main_key_released = True

    if not is_main_key_released:
        if key in self._pressed_keys_for_new_hotkey:
            self._pressed_keys_for_new_hotkey.remove(key)
        current_combination = self._build_hotkey_string_from_set(
            self._pressed_keys_for_new_hotkey
        )
        if (
            hasattr(self, "capturing_hotkey_label")
            and self.capturing_hotkey_label.winfo_exists()
        ):
            try:
                self.capturing_hotkey_label.config(
                    text=current_combination or "Naciśnij klawisze..."
                )
            except tk.TclError:
                pass
        return True

    final_hotkey_string = self._build_hotkey_string_from_set(
        self._pressed_keys_for_new_hotkey
    )
    self._pressed_keys_for_new_hotkey.clear()

    if self.key_combination_listener and self.key_combination_listener.is_alive():
        self.key_combination_listener.stop()
        self.key_combination_listener = None
        logging.debug(
            "Zatrzymano listenera pynput (keyboard.Listener) dla nowego skrótu."
        )

    if (
        hasattr(self, "capturing_hotkey_toplevel")
        and self.capturing_hotkey_toplevel.winfo_exists()
    ):
        try:
            self.capturing_hotkey_toplevel.destroy()
        except tk.TclError:
            pass

    is_valid_hotkey_format = False
    if final_hotkey_string:
        parts = final_hotkey_string.split("+")
        has_non_modifier_primary_key = any(
            part.lower() not in ["<ctrl>", "<alt>", "<shift>", "<cmd>", "<super>"]
            for part in parts
        )
        if has_non_modifier_primary_key:
            is_valid_hotkey_format = True

    if (
        is_valid_hotkey_format
        and self.current_new_hotkey_action
        and self.current_new_hotkey_stringvar
    ):
        logging.info(
            f"Ustawiono nowy skrót dla '{self.current_new_hotkey_action}': {final_hotkey_string}"
        )
        self.current_new_hotkey_stringvar.set(final_hotkey_string)
        current_hotkeys = self.local_settings.get(
            "music_hotkeys", DEFAULT_MUSIC_HOTKEYS.copy()
        )
        current_hotkeys[self.current_new_hotkey_action] = final_hotkey_string
        self.local_settings["music_hotkeys"] = current_hotkeys
        save_local_settings(self.local_settings)
        self.root.after(0, self._reregister_all_global_hotkeys)
        display_name = self.hotkey_actions_display_names.get(
            self.current_new_hotkey_action, self.current_new_hotkey_action
        )
        self.root.after(
            0,
            lambda d=display_name, h=final_hotkey_string: messagebox.showinfo(
                "Skrót Ustawiony",
                f"Nowy skrót dla '{d}' to: {h}",
                parent=(
                    self.settings_page_frame
                    if hasattr(self, "settings_page_frame")
                    and self.settings_page_frame.winfo_exists()
                    else self.root
                ),
            ),
        )
    elif self.current_new_hotkey_action:
        old_hotkey = self.local_settings.get("music_hotkeys", {}).get(
            self.current_new_hotkey_action, ""
        )
        if self.current_new_hotkey_stringvar:
            self.current_new_hotkey_stringvar.set(old_hotkey)
        self.root.after(
            0,
            lambda: messagebox.showwarning(
                "Anulowano Ustawianie Skrótu",
                "Nie udało się przechwycić poprawnej kombinacji klawiszy lub skrót jest nieprawidłowy (np. składa się tylko z modyfikatorów).\nPrzywrócono poprzedni skrót.",
                parent=(
                    self.settings_page_frame
                    if hasattr(self, "settings_page_frame")
                    and self.settings_page_frame.winfo_exists()
                    else self.root
                ),
            ),
        )

    self.current_new_hotkey_action = None
    self.current_new_hotkey_stringvar = None
    return False


__all__ = [
    "_get_pynput_key_string",
    "_build_hotkey_string_from_set",
    "_get_pynput_internal_representation",
    "_on_press_for_new_hotkey",
    "_on_release_for_new_hotkey",
]
