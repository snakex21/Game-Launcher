import logging
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from launcher.utils import THEMES


def show_home(self):
    self.home_frame.tkraise()
    self.current_frame = self.home_frame
    self.current_section = "Na Stronie Głównej"
    self._update_discord_status(status_type="browsing", activity_details=self.current_section)


def show_mod_manager(self):
    """Pokazuje Menedżera Modów, tworząc go przy pierwszym użyciu."""
    self._hide_library_components()
    self._ensure_mod_manager()
    if self.extended_mod_manager:
        self.extended_mod_manager.frame.grid()
        self.extended_mod_manager.frame.tkraise()
        self.current_frame = self.extended_mod_manager.frame
        self.current_section = "Zarządza Modami"
        self._update_discord_status(
            status_type="browsing", activity_details=self.current_section
        )
    else:
        logging.error("Nie udało się stworzyć lub pokazać Menedżera Modów.")


def refresh_ui(self):
    logging.info("Odświeżanie interfejsu użytkownika...")

    self.create_sidebar()
    self.create_home_page()

    if (
        self._roadmap_initialized
        and hasattr(self, "roadmap_frame")
        and self.roadmap_frame.winfo_exists()
    ):
        self._populate_roadmap_and_archive_data()

    if (
        self._settings_initialized
        and hasattr(self, "settings_page_frame")
        and self.settings_page_frame.winfo_exists()
    ):
        self.load_scan_folders_list()
        self.populate_rss_management_frame()
        self.load_ignored_folders()
        self.load_screenshot_ignored_folders()
        self._load_emulators_list()
        self._load_custom_themes_list()
        self._load_and_display_settings_avatar()

    if (
        self._library_initialized
        and hasattr(self, "filter_menu")
        and self.filter_menu.winfo_exists()
    ):
        self.update_filter_group_menu()
        self.update_tag_filter_options()
        self.update_genre_menu()
        self.reset_and_update_grid()

    theme_name_from_settings = self.settings.get("theme", "Dark")
    theme_def_to_apply = self.get_all_available_themes().get(
        theme_name_from_settings, THEMES["Dark"]
    )
    self.apply_theme(theme_def_to_apply)
    self.apply_font_settings()

    logging.info("Zakończono odświeżanie interfejsu.")


def _show_developer_console(self):
    """Otwiera okno konsoli deweloperskiej z pomiarem czasu startu."""
    dev_console_window = tk.Toplevel(self.root)
    dev_console_window.title("Developer Console")
    dev_console_window.configure(bg="#1e1e1e")
    dev_console_window.geometry("500x700")
    dev_console_window.minsize(400, 600)
    dev_console_window.grab_set()

    time_frame = ttk.LabelFrame(
        dev_console_window, text=" Czasy uruchomienia (ms) ", padding=(10, 5)
    )
    time_frame.pack(fill="both", expand=True, padx=10, pady=10)
    time_frame.columnconfigure(1, weight=1)

    current_row_idx = 0
    previous_time = 0

    sorted_checkpoints = sorted(self.start_up_time_points.items(), key=lambda item: item[1])

    total_start_time = sorted_checkpoints[-1][1] if sorted_checkpoints else 0
    ttk.Label(time_frame, text="Całkowity czas uruchomienia:").grid(
        row=current_row_idx, column=0, padx=5, pady=2, sticky="w"
    )
    ttk.Label(
        time_frame, text=f"{total_start_time:.2f} ms", font=("Segoe UI", 9, "bold")
    ).grid(row=current_row_idx, column=1, padx=5, pady=2, sticky="e")
    current_row_idx += 1

    ttk.Separator(time_frame, orient="horizontal").grid(
        row=current_row_idx, column=0, columnspan=2, sticky="ew", pady=(5, 10)
    )
    current_row_idx += 1

    for checkpoint_name, elapsed_time in sorted_checkpoints:
        duration_from_previous = elapsed_time - previous_time
        previous_time = elapsed_time

        ttk.Label(time_frame, text=f"-> {checkpoint_name}:").grid(
            row=current_row_idx, column=0, padx=5, pady=2, sticky="w"
        )
        ttk.Label(time_frame, text=f"{elapsed_time:.2f} ms", font=("Segoe UI", 8)).grid(
            row=current_row_idx, column=1, padx=5, pady=2, sticky="e"
        )
        _ = duration_from_previous
        current_row_idx += 1

    ttk.Button(dev_console_window, text="Zamknij", command=dev_console_window.destroy).pack(
        pady=10
    )
    dev_console_window.wait_window(dev_console_window)


def show_library(self):
    self.main_frame.grid()
    self.main_frame.tkraise()
    self.current_frame = self.main_frame

    if not self._library_initialized:
        logging.info("Tworzenie zawartości strony Biblioteki po raz pierwszy (lazy init).")
        self.create_header()
        self.create_game_grid()
        self._library_initialized = True

    self.update_game_grid()
    self.current_section = "Przegląda Bibliotekę"
    self._update_discord_status(status_type="browsing", activity_details=self.current_section)


def _open_folder(self, folder_path):
    """Bezpiecznie otwiera podany folder w eksploratorze plików."""
    if not folder_path:
        logging.warning("Próba otwarcia pustej ścieżki folderu.")
        messagebox.showwarning(
            "Brak Ścieżki",
            "Ścieżka do folderu nie jest zdefiniowana.",
            parent=self.root,
        )
        return

    norm_path = os.path.normpath(folder_path)

    if not os.path.isdir(norm_path):
        logging.warning(f"Próba otwarcia ścieżki, która nie jest folderem: {norm_path}")
        messagebox.showerror(
            "Błąd Ścieżki",
            f"Podana ścieżka nie jest prawidłowym folderem:\n{norm_path}",
            parent=self.root,
        )
        return

    try:
        if sys.platform == "win32":
            os.startfile(norm_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", norm_path])
        else:
            subprocess.run(["xdg-open", norm_path])
        logging.info(f"Otwieranie folderu: {norm_path}")
    except Exception as e:
        logging.error(f"Nie można otworzyć folderu '{norm_path}': {e}")
        messagebox.showerror(
            "Błąd",
            f"Nie można otworzyć folderu:\n{norm_path}\n\nBłąd: {e}",
            parent=self.root,
        )


def show_music_page_from_tray(self):
    """Pokazuje okno launchera i przechodzi do strony odtwarzacza muzyki."""
    self.show_window()
    self.root.after_idle(self.show_music_page)


def preload_library_view(self):
    if self._library_initialized:
        return

    try:
        self.create_header()
        self.create_game_grid()
        self._library_initialized = True
        self.update_game_grid()
        logging.info("Preload biblioteki zakończony.")
    except Exception as error:
        logging.debug(f"Preload biblioteki nieudany: {error}")


def preload_roadmap_view(self):
    try:
        if not hasattr(self, "roadmap_frame") or not self.roadmap_frame.winfo_exists():
            self.create_roadmap_page(show_frame=False)
        if hasattr(self, "roadmap_frame") and self.roadmap_frame.winfo_exists():
            self.roadmap_frame.grid_remove()
        logging.info("Preload roadmapy zakończony.")
    except Exception as error:
        logging.debug(f"Preload roadmapy nieudany: {error}")


def preload_music_page(self):
    if getattr(self, "music_player_page_instance", None) is not None:
        return

    try:
        from ui.music_player import MusicPlayerPage

        self.music_player_page_instance = MusicPlayerPage(
            self.music_page_frame,
            self,
            show_init_errors=False,
        )
        self.music_page_frame.grid_remove()
        logging.info("Preload strony muzyki zakończony.")
    except Exception as error:
        logging.debug(f"Preload strony muzyki nieudany: {error}")


__all__ = [
    "show_home",
    "show_mod_manager",
    "refresh_ui",
    "_show_developer_console",
    "show_library",
    "_open_folder",
    "show_music_page_from_tray",
    "preload_library_view",
    "preload_roadmap_view",
    "preload_music_page",
]
