import logging
import time
import tkinter as tk
from tkinter import messagebox

from pypresence import Presence, PyPresenceException

from launcher.config_store import save_local_settings


def _start_discord_rpc(self):
    if self.rpc or self._is_connecting_rpc:
        return
    if not self.discord_rpc_enabled_var.get():
        logging.info("RPC wyłączone w UI.")
        return

    logging.info("Próba uruchomienia Discord RPC...")
    self._is_connecting_rpc = True

    try:
        self.rpc = Presence(client_id=self.DISCORD_CLIENT_ID)
        self.rpc.connect()
        logging.info("Połączono z Discord RPC.")
        activity = (
            self.current_section
            if hasattr(self, "current_section") and self.current_section
            else self.translator.gettext("W menu głównym")
        )
        self._update_discord_status(status_type="browsing", activity_details=activity)

    except PyPresenceException as e:
        logging.warning(f"Nie udało się połączyć z Discord RPC (w _start_discord_rpc): {e}")
        self.rpc = None
    except ConnectionRefusedError:
        logging.warning(
            "Nie udało się połączyć z Discord RPC: Connection refused. Discord prawdopodobnie nie jest uruchomiony."
        )
        self.rpc = None
    except Exception as e:
        logging.exception("Nieoczekiwany (inny) błąd podczas uruchamiania Discord RPC.")
        self.rpc = None
        if hasattr(self, "discord_rpc_enabled_var"):
            self.discord_rpc_enabled_var.set(False)
        self.local_settings["discord_rpc_enabled"] = False
        save_local_settings(self.local_settings)
        self.root.after(
            0,
            lambda err_msg=str(e): messagebox.showerror(
                "Błąd Krytyczny RPC",
                f"Wystąpił krytyczny błąd RPC i zostało ono wyłączone:\n{err_msg}",
                parent=self.root,
            ),
        )
    finally:
        self._is_connecting_rpc = False


def _monitor_discord_connection(self):
    logging.info("Uruchomiono wątek monitorujący połączenie Discord RPC.")
    while True:
        time.sleep(30)

        try:
            if not self.root.winfo_exists():
                logging.info("Monitor RPC: Okno główne nie istnieje, zatrzymuję wątek.")
                break

            is_enabled = False
            if hasattr(self, "discord_rpc_enabled_var"):
                try:
                    is_enabled = self.discord_rpc_enabled_var.get()
                except tk.TclError:
                    logging.warning(
                        "Monitor RPC: Błąd odczytu discord_rpc_enabled_var (okno mogło zostać zamknięte)."
                    )
                    continue

            if is_enabled and not self.rpc and not self._is_connecting_rpc:
                logging.info(
                    "Monitor RPC: Wykryto potrzebę połączenia. Zlecanie _start_discord_rpc głównemu wątkowi."
                )
                self.root.after(0, self._start_discord_rpc)

        except Exception:
            logging.exception("Nieoczekiwany błąd w pętli monitorującej Discord RPC.")


def _handle_rpc_connection_error(self, error_message: str, is_critical: bool = True):
    """Obsługuje błędy połączenia RPC w głównym wątku GUI."""
    if not self.root.winfo_exists():
        return

    log_message = f"Obsługa błędu RPC: {error_message}"
    if is_critical:
        logging.error(log_message)
        if "pipe" not in error_message.lower():
            messagebox.showwarning(
                "Discord RPC",
                f"Problem z połączeniem Discord:\n{error_message}",
                parent=self.root,
            )
    else:
        logging.warning(log_message)

    if hasattr(self, "discord_rpc_enabled_var") and self.discord_rpc_enabled_var.get():
        self.discord_rpc_enabled_var.set(False)

    if self.local_settings.get("discord_rpc_enabled", False):
        self.local_settings["discord_rpc_enabled"] = False
        save_local_settings(self.local_settings)
        logging.info(
            "RPC zostało wyłączone w ustawieniach z powodu błędu połączenia/aktualizacji."
        )

    if self.rpc:
        try:
            self.rpc.close()
        except Exception:
            pass
        self.rpc = None
    self._is_connecting_rpc = False


def _toggle_discord_rpc(self):
    """Włącza lub wyłącza integrację z Discord RPC na podstawie checkboxa."""
    is_enabled = self.discord_rpc_enabled_var.get()
    if self.local_settings.get("discord_rpc_enabled") != is_enabled:
        self.local_settings["discord_rpc_enabled"] = is_enabled
        save_local_settings(self.local_settings)
        logging.info(f"Zmieniono ustawienie Discord RPC na: {is_enabled}")

    if is_enabled:
        if not self.rpc and not self._is_connecting_rpc:
            logging.info("RPC włączone przez użytkownika. Próba połączenia...")
            self._start_discord_rpc()
        elif self.rpc:
            logging.info("RPC już działa.")
            self._update_discord_status(status_type="idle")
    else:
        logging.info("RPC wyłączone przez użytkownika. Zatrzymywanie połączenia...")
        self._stop_discord_rpc()


def _update_discord_status(
    self,
    status_type="idle",
    game_name=None,
    profile_name=None,
    start_time=None,
    activity_details=None,
):
    if not self.discord_rpc_enabled_var.get() or not self.rpc:
        return

    try:
        state_text = ""
        details_text = ""
        large_image_key = "gl_logo"
        small_image_key = None
        small_image_text = None
        start_timestamp = None

        is_game_actually_running = game_name and status_type == "in_game"
        current_music_track_info = None

        if (
            hasattr(self, "music_player_page_instance")
            and self.music_player_page_instance
            and hasattr(self.music_player_page_instance, "is_playing")
            and self.music_player_page_instance.is_playing
            and not self.music_player_page_instance.is_paused
            and hasattr(self.music_player_page_instance, "current_track_index")
            and self.music_player_page_instance.current_track_index != -1
            and hasattr(self.music_player_page_instance, "playlist")
            and self.music_player_page_instance.current_track_index
            < len(self.music_player_page_instance.playlist)
        ):
            try:
                player = self.music_player_page_instance
                track_entry = player.playlist[player.current_track_index]
                music_display_name = (
                    player._get_display_name_for_track(track_entry)
                    .replace("♥ ", "")
                    .strip()
                )
                if music_display_name:
                    current_music_track_info = {
                        "display_name": music_display_name,
                        "start_time_monotonic": getattr(player, "_start_time", 0),
                        "pause_accumulator": getattr(player, "_pause_acc", 0),
                    }
            except Exception as e_music_info:
                logging.error(
                    f"Błąd pobierania informacji o muzyce dla Discord: {e_music_info}"
                )
                current_music_track_info = None

        if is_game_actually_running:
            state_text = f"Gra w: {game_name}"
            details_list = []

            if profile_name and profile_name.lower() != "default":
                details_list.append(f"Profil: {profile_name}")
            else:
                details_list.append("Uruchomiono z GL")

            if current_music_track_info:
                details_list.append(f"🎧 {current_music_track_info['display_name'][:40]}")
                small_image_key = "music_note_icon"
                small_image_text = "Słucha muzyki"

            details_text = " | ".join(details_list)
            start_timestamp = int(start_time) if start_time else None
            large_image_key = "gaming_status"

        elif current_music_track_info:
            state_text = "Słucha Muzyki 🎧"
            details_text = current_music_track_info["display_name"][:128]
            large_image_key = "music_icon"

            try:
                if current_music_track_info["start_time_monotonic"] > 0:
                    current_track_elapsed = (
                        time.monotonic()
                        - current_music_track_info["start_time_monotonic"]
                        - current_music_track_info["pause_accumulator"]
                    )
                    track_start_for_discord = time.time() - current_track_elapsed
                    start_timestamp = int(track_start_for_discord)
            except Exception as e_timestamp_music:
                logging.warning(
                    f"Błąd obliczania timestampu muzyki dla Discord: {e_timestamp_music}"
                )
                start_timestamp = None

        elif status_type == "browsing" and activity_details:
            state_text = self.discord_status_text_var.get() or "Korzysta z Game Launcher"
            details_text = activity_details
            large_image_key = "gl_logo"
        else:
            state_text = self.discord_status_text_var.get() or "Korzysta z Game Launcher"
            details_text = (
                self.current_section
                if hasattr(self, "current_section")
                else "W menu głównym"
            )
            large_image_key = "gl_logo"

        self.rpc.update(
            state=state_text[:128],
            details=details_text[:128],
            large_image=large_image_key,
            small_image=small_image_key,
            small_text=small_image_text,
            start=start_timestamp,
        )
        logging.info(
            f"Discord RPC Update: State='{state_text}', Details='{details_text}', LargeImg='{large_image_key}', SmallImg='{small_image_key}', Start='{start_timestamp}'"
        )

    except PyPresenceException as e:
        logging.error(f"Błąd PyPresence Discord podczas aktualizacji statusu: {e}")
        if "pipe" in str(e).lower():
            logging.warning(
                "Discord pipe closed. RPC zatrzymane, monitor spróbuje połączyć ponownie."
            )
            self._stop_discord_rpc()
        else:
            self._handle_rpc_connection_error(str(e), is_critical=True)
    except Exception:
        logging.exception("Nieoczekiwany błąd podczas aktualizacji statusu Discord.")


def _stop_discord_rpc(self):
    """Zatrzymuje połączenie Discord RPC i czyści instancję."""
    self._is_connecting_rpc = False
    if self.rpc:
        try:
            self.rpc.close()
            logging.info("Połączenie Discord RPC zamknięte.")
        except PyPresenceException as e:
            logging.error(f"Błąd PyPresence podczas zamykania połączenia RPC: {e}")
        except Exception:
            logging.exception("Nieoczekiwany błąd podczas zamykania RPC.")
        finally:
            self.rpc = None


def _save_discord_settings(self):
    """Zapisuje ustawienia Discord RPC z interfejsu."""
    new_status_text = self.discord_status_text_var.get()
    if self.local_settings.get("discord_status_text") != new_status_text:
        self.local_settings["discord_status_text"] = new_status_text
        save_local_settings(self.local_settings)
        logging.info(f"Zapisano nowy tekst statusu Discord: {new_status_text}")
        if self.discord_rpc_enabled and self.rpc:
            if not self.tracking_games:
                self._update_discord_status(status_type="idle")


__all__ = [
    "_start_discord_rpc",
    "_monitor_discord_connection",
    "_handle_rpc_connection_error",
    "_toggle_discord_rpc",
    "_update_discord_status",
    "_stop_discord_rpc",
    "_save_discord_settings",
]
