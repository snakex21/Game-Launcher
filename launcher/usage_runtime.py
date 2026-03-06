import logging
import time
from tkinter import messagebox

from launcher.config_store import save_local_settings


def _update_launcher_usage_display(self):
    """Aktualizuje etykiety z łącznym czasem użycia launchera."""
    try:
        saved_total_seconds = self.local_settings.get("total_launcher_usage_seconds", 0)
        current_session_seconds = time.time() - self.launcher_start_time
        actual_total_seconds = saved_total_seconds + current_session_seconds

        days, rem = divmod(actual_total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        txt_prefix = "Łączny czas: "
        if days > 0:
            txt = txt_prefix + f"{int(days)}d {int(hours)}h {int(minutes)}m"
        else:
            txt = txt_prefix + f"{int(hours)}h {int(minutes)}m"

        if hasattr(self, "launcher_usage_label") and self.launcher_usage_label.winfo_exists():
            self.launcher_usage_label.config(text=txt)
        if (
            hasattr(self, "total_launcher_usage_label_home")
            and self.total_launcher_usage_label_home.winfo_exists()
        ):
            self.total_launcher_usage_label_home.config(text=txt)

    except Exception as e:
        logging.error(f"Błąd w _update_launcher_usage_display: {e}")
        if (
            hasattr(self, "total_launcher_usage_label_home")
            and self.total_launcher_usage_label_home.winfo_exists()
        ):
            self.total_launcher_usage_label_home.config(text="Łączny czas: Błąd")
        if hasattr(self, "launcher_usage_label") and self.launcher_usage_label.winfo_exists():
            self.launcher_usage_label.config(text="Łączny czas: Błąd")

    if hasattr(self, "root") and self.root.winfo_exists():
        self.root.after(1000, self._update_launcher_usage_display)


def reset_launcher_usage_time(self):
    """Zeruje łączny czas spędzony w launcherze po potwierdzeniu użytkownika."""
    if not messagebox.askyesno(
        "Reset licznika", "Wyzerować zapisany czas spędzony w launcherze?"
    ):
        return

    self.local_settings["total_launcher_usage_seconds"] = 0
    save_local_settings(self.local_settings)
    self.launcher_start_time = time.time()
    self._update_launcher_usage_display()


def _update_current_session_time_display(self):
    """Aktualizuje etykietę z czasem trwania bieżącej sesji launchera."""
    if (
        hasattr(self, "launcher_usage_label_home")
        and self.launcher_usage_label_home.winfo_exists()
    ):
        current_session_seconds = time.time() - self.launcher_start_time
        hours, rem = divmod(current_session_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        self.launcher_usage_label_home.config(text=f"Czas sesji: {time_str}")

    if hasattr(self, "root") and self.root.winfo_exists():
        self.root.after(1000, self._update_current_session_time_display)


__all__ = [
    "_update_launcher_usage_display",
    "reset_launcher_usage_time",
    "_update_current_session_time_display",
]
