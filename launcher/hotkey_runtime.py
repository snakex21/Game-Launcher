import functools
import logging
from tkinter import messagebox

from pynput import keyboard

from launcher.utils import DEFAULT_MUSIC_HOTKEYS


def _music_action_callback(self, action_key):
    """Ogólny callback dla skrótów muzycznych."""
    logging.info(f"Globalny skrót muzyczny aktywowany: {action_key}")
    if action_key == "play_pause":
        self._music_control_play_pause()
    elif action_key == "next_track":
        self._music_control_next_track()
    elif action_key == "prev_track":
        self._music_control_prev_track()
    elif action_key == "stop_music":
        self._music_control_stop()
    elif action_key == "volume_up":
        self._music_control_volume_up()
    elif action_key == "volume_down":
        self._music_control_volume_down()


def _register_music_hotkeys(self):
    """Rejestruje globalne skróty klawiszowe dla muzyki."""
    if not self.local_settings.get("music_hotkeys_enabled", True):
        logging.info(
            "Globalne skróty muzyczne są wyłączone w ustawieniach. Pomijanie rejestracji."
        )
        if self.global_hotkeys_listener and self.global_hotkeys_listener.is_alive():
            self.global_hotkeys_listener.stop()
            self.global_hotkeys_listener = None
        return

    if self.global_hotkeys_listener and self.global_hotkeys_listener.is_alive():
        self.global_hotkeys_listener.stop()
        self.global_hotkeys_listener = None
        logging.info("Zatrzymano poprzedniego listenera GlobalHotKeys.")

    hotkey_config = self.local_settings.get(
        "music_hotkeys", DEFAULT_MUSIC_HOTKEYS.copy()
    )
    self.active_hotkeys = {}

    callbacks_map = {}
    for action, combination_str in hotkey_config.items():
        if combination_str:
            callback = functools.partial(self._music_action_callback, action)
            callbacks_map[combination_str] = callback
            logging.debug(
                f"Przygotowano do rejestracji: '{combination_str}' -> {action}"
            )
        else:
            logging.debug(
                f"Pominięto rejestrację dla akcji '{action}', brak zdefiniowanego skrótu."
            )

    if not callbacks_map:
        logging.info("Brak skrótów do zarejestrowania dla muzyki.")
        return

    try:
        self.global_hotkeys_listener = keyboard.GlobalHotKeys(callbacks_map)
        self.global_hotkeys_listener.start()
        logging.info("Pomyślnie uruchomiono listenera GlobalHotKeys dla muzyki.")
    except Exception as e:
        logging.error(f"Nie udało się uruchomić GlobalHotKeys: {e}")
        messagebox.showerror(
            "Błąd Skrótów Globalnych",
            f"Nie można było zarejestrować globalnych skrótów klawiszowych dla muzyki:\n{e}",
            parent=self.root,
        )
        self.global_hotkeys_listener = None


def _reregister_all_global_hotkeys(self):
    """Zatrzymuje i ponownie rejestruje wszystkie globalne skróty (np. po zmianie)."""
    logging.info("Ponowna rejestracja globalnych skrótów klawiszowych...")
    self._register_music_hotkeys()


def _music_control_stop(self):
    if hasattr(self, "track_overlay") and self.track_overlay and self.track_overlay.winfo_exists():
        self.track_overlay.update_display("Nic nie gra...", 0, 0, False)


def _music_control_volume_up(self):
    if hasattr(self, "music_player_page_instance") and self.music_player_page_instance:
        self.root.after(0, lambda: self.music_player_page_instance._change_volume_by_step(10))


def _music_control_volume_down(self):
    if hasattr(self, "music_player_page_instance") and self.music_player_page_instance:
        self.root.after(0, lambda: self.music_player_page_instance._change_volume_by_step(-10))


__all__ = [
    "_music_action_callback",
    "_register_music_hotkeys",
    "_reregister_all_global_hotkeys",
    "_music_control_stop",
    "_music_control_volume_up",
    "_music_control_volume_down",
]
