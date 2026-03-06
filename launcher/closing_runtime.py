import datetime
import logging
import time
import tkinter as tk
from tkinter import messagebox

from launcher.config_store import save_local_settings


def on_closing(self):
    if messagebox.askokcancel("Wyjście", "Czy na pewno chcesz wyjść?"):

        try:
            elapsed_launcher_time = time.time() - self.launcher_start_time
            current_total_usage = self.local_settings.get(
                "total_launcher_usage_seconds", 0
            )
            if elapsed_launcher_time > 1:
                new_total_usage = current_total_usage + elapsed_launcher_time
                self.local_settings["total_launcher_usage_seconds"] = new_total_usage
                logging.info(f"Przygotowano łączny czas do zapisu: {new_total_usage:.0f}s")
            else:
                logging.debug(
                    "Sesja launchera zbyt krótka, nie aktualizuję łącznego czasu."
                )

            is_zoomed = False
            try:
                is_zoomed = bool(self.root.wm_attributes("-zoomed"))
            except tk.TclError:
                if self.root.state() == "zoomed":
                    is_zoomed = True
            self.local_settings["window_state"] = "zoomed" if is_zoomed else "normal"
            if not is_zoomed and self.root.state() == "normal":
                self.local_settings["window_geometry"] = self.root.geometry()

            self.local_settings["library_view_mode"] = self.library_view_mode.get()
            if hasattr(self, "discord_status_text_var"):
                self.local_settings["discord_status_text"] = (
                    self.discord_status_text_var.get()
                )

        except Exception as e:
            logging.error(
                f"Błąd podczas przygotowywania danych do zapisu w on_closing: {e}"
            )

            session_start = self.launcher_start_time
            session_end = time.time()
            cur_date = datetime.date.fromtimestamp(session_start)
            last_date = datetime.date.fromtimestamp(session_end)
            daily_usage = self.local_settings.setdefault("launcher_daily_usage_seconds", {})
            while cur_date <= last_date:
                day_start_ts = time.mktime(cur_date.timetuple())
                day_end_ts = day_start_ts + 86400
                overlap_start = max(session_start, day_start_ts)
                overlap_end = min(session_end, day_end_ts)
                seconds_on_day = max(0, overlap_end - overlap_start)
                if seconds_on_day:
                    daily_usage[cur_date.isoformat()] = (
                        daily_usage.get(cur_date.isoformat(), 0) + seconds_on_day
                    )
                cur_date += datetime.timedelta(days=1)

            if hasattr(self, "music_player_page_instance") and self.music_player_page_instance:
                try:
                    self.music_player_page_instance._save_player_settings()
                    logging.info("Zapisano ustawienia odtwarzacza muzyki.")
                except Exception as e_music_save:
                    logging.error(
                        f"Błąd podczas zapisywania ustawień odtwarzacza muzyki: {e_music_save}"
                    )

            if (
                hasattr(self, "track_overlay")
                and self.track_overlay
                and self.track_overlay.winfo_exists()
                and self.track_overlay.winfo_viewable()
            ):
                try:
                    self.local_settings["overlay_x_pos"] = self.track_overlay.winfo_x()
                    self.local_settings["overlay_y_pos"] = self.track_overlay.winfo_y()
                    logging.debug("Zapisano pozycję overlay'a przed zamknięciem.")
                except tk.TclError:
                    logging.warning(
                        "Nie można było odczytać pozycji overlay'a (mógł zostać zniszczony)."
                    )

            if hasattr(self, "show_track_overlay_var"):
                self.local_settings["show_track_overlay"] = self.show_track_overlay_var.get()
                logging.debug(
                    f"Zapisano stan overlay'a: {self.show_track_overlay_var.get()}"
                )

        except Exception as e_prep:
            logging.error(
                f"Błąd podczas przygotowywania danych do zapisu w on_closing: {e_prep}"
            )

        try:
            save_local_settings(self.local_settings)
            logging.info("Zapisano ustawienia lokalne przy zamykaniu.")
        except Exception as e_save:
            logging.error(f"Błąd zapisu ustawień lokalnych przy zamykaniu: {e_save}")

        if hasattr(self, "_server_running") and self._server_running:
            self._stop_flask_server()

        if hasattr(self, "_stop_discord_rpc"):
            self._stop_discord_rpc()

        if (
            hasattr(self, "key_combination_listener")
            and self.key_combination_listener
            and self.key_combination_listener.is_alive()
        ):
            logging.info("Zatrzymywanie listenera przechwytywania nowego skrótu...")
            try:
                self.key_combination_listener.stop()
            except Exception as e_pynput_stop_capture:
                logging.error(
                    f"Błąd zatrzymywania listenera przechwytywania: {e_pynput_stop_capture}"
                )

        if (
            hasattr(self, "global_hotkeys_listener")
            and self.global_hotkeys_listener
            and self.global_hotkeys_listener.is_alive()
        ):
            logging.info("Zatrzymywanie listenera GlobalHotKeys...")
            try:
                self.global_hotkeys_listener.stop()
            except Exception as e_pynput_stop:
                logging.error(f"Błąd zatrzymywania GlobalHotKeys: {e_pynput_stop}")

        if (
            hasattr(self, "tray_icon")
            and hasattr(self.tray_icon, "visible")
            and self.tray_icon.visible
        ):
            try:
                self.tray_icon.stop()
            except Exception as e_tray:
                logging.error(f"Błąd zatrzymywania ikony zasobnika: {e_tray}")

        self.root.quit()


__all__ = ["on_closing"]
