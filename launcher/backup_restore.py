import datetime
import json
import logging
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from launcher.config_store import (
    load_config as config_load_config,
    load_local_settings as config_load_local_settings,
    save_local_settings as config_save_local_settings,
)
from launcher.utils import (
    ACHIEVEMENTS_DEFINITIONS_FILE,
    CONFIG_FILE,
    CUSTOM_THEMES_DIR,
    GAMES_FOLDER,
    IMAGES_FOLDER,
    INTERNAL_MUSIC_DIR,
    LOCAL_SETTINGS_FILE,
    THEMES,
)


def _destroy_progress_window(self):
    """Bezpiecznie zamyka okno postępu."""
    if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
        self.progress_window.destroy()


def show_progress_window(self, title):
    if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
        self.progress_window.title(title)
        self.progress_label.config(text="Rozpoczynanie...")
        self.progress_bar["value"] = 0
        self.progress_window.update_idletasks()
        return

    self.progress_window = tk.Toplevel(self.root)
    self.progress_window.title(title)
    self.progress_window.geometry("350x120")
    self.progress_window.resizable(False, False)
    ttk.Label(self.progress_window, text=title, wraplength=330).pack(pady=5)
    self.progress_bar = ttk.Progressbar(
        self.progress_window, orient="horizontal", mode="determinate", maximum=100
    )
    self.progress_bar.pack(pady=10, fill="x", padx=20)
    self.progress_label = ttk.Label(self.progress_window, text="0%", wraplength=330)
    self.progress_label.pack()
    self.progress_window.protocol("WM_DELETE_WINDOW", self.disable_event)
    self.progress_window.update_idletasks()


def backup_to_local_folder(self):
    """
    Kopiuje kluczowe pliki konfiguracyjne i foldery danych aplikacji
    do wskazanego przez użytkownika folderu backupu.
    Pokazuje prosty pasek postępu podczas operacji.
    """
    backup_dir_base = filedialog.askdirectory(
        title="Wybierz folder, gdzie zrobić backup", parent=self.root
    )
    if not backup_dir_base:
        return

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_main_folder_name = f"GameLauncher_Backup_{timestamp_str}"
    backup_destination_root = os.path.join(backup_dir_base, backup_main_folder_name)

    items_to_backup = [
        (
            "Kopiowanie: config.json",
            CONFIG_FILE,
            os.path.basename(CONFIG_FILE),
            "file",
        ),
        (
            "Kopiowanie: local_settings.json",
            LOCAL_SETTINGS_FILE,
            os.path.basename(LOCAL_SETTINGS_FILE),
            "file",
        ),
        (
            "Kopiowanie: achievements_def.json",
            ACHIEVEMENTS_DEFINITIONS_FILE,
            os.path.basename(ACHIEVEMENTS_DEFINITIONS_FILE),
            "file",
        ),
        (
            "Kopiowanie folderu: games_saves",
            GAMES_FOLDER,
            os.path.basename(GAMES_FOLDER),
            "dir",
        ),
        (
            "Kopiowanie folderu: images (okładki gier i muzyki)",
            IMAGES_FOLDER,
            IMAGES_FOLDER,
            "dir",
        ),
        (
            "Kopiowanie folderu: internal_music",
            INTERNAL_MUSIC_DIR,
            INTERNAL_MUSIC_DIR,
            "dir",
        ),
        (
            "Kopiowanie folderu: custom_themes",
            CUSTOM_THEMES_DIR,
            CUSTOM_THEMES_DIR,
            "dir",
        ),
    ]

    self.show_progress_window(f"Tworzenie Backupu: {backup_main_folder_name}")
    if not (hasattr(self, "progress_window") and self.progress_window.winfo_exists()):
        logging.error("Nie udało się utworzyć okna postępu dla tworzenia backupu.")
        return

    self.progress_bar["maximum"] = len(items_to_backup)
    self.progress_bar["value"] = 0
    self.progress_bar["mode"] = "determinate"

    def _update_simple_backup_progress(current_step_index, description):
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_bar["value"] = current_step_index + 1
            self.progress_label.config(
                text=f"Etap {current_step_index + 1}/{len(items_to_backup)}: {description}"
            )
            self.progress_window.update_idletasks()

    def _perform_simple_backup_thread():
        backup_success_thread = True
        error_message_thread = ""

        try:
            os.makedirs(backup_destination_root, exist_ok=True)
            logging.info(f"Utworzono główny folder backupu: {backup_destination_root}")

            for idx, (
                description,
                source_path_app,
                dest_name_in_backup,
                item_type,
            ) in enumerate(items_to_backup):
                self.root.after(
                    0,
                    lambda i=idx, d=description: _update_simple_backup_progress(i, d),
                )

                full_source_path_app = os.path.abspath(source_path_app)
                full_dest_path_in_backup = os.path.join(
                    backup_destination_root, dest_name_in_backup
                )

                if not os.path.exists(full_source_path_app):
                    logging.warning(
                        f"Backup: Zasób źródłowy '{full_source_path_app}' nie istnieje. Pomijanie."
                    )
                    continue

                try:
                    if item_type == "file":
                        shutil.copy2(full_source_path_app, full_dest_path_in_backup)
                        logging.info(
                            f"Backup: Skopiowano plik '{full_source_path_app}' do '{full_dest_path_in_backup}'."
                        )
                    elif item_type == "dir":
                        if os.path.exists(full_dest_path_in_backup):
                            shutil.rmtree(full_dest_path_in_backup)
                        shutil.copytree(
                            full_source_path_app,
                            full_dest_path_in_backup,
                            dirs_exist_ok=False,
                        )
                        logging.info(
                            f"Backup: Skopiowano folder '{full_source_path_app}' do '{full_dest_path_in_backup}'."
                        )
                except Exception as e_copy_item:
                    logging.error(
                        f"Backup: Błąd podczas kopiowania '{full_source_path_app}' do '{full_dest_path_in_backup}': {e_copy_item}"
                    )

        except Exception as e_thread_main:
            backup_success_thread = False
            error_message_thread = str(e_thread_main)
            logging.exception("Backup: Krytyczny błąd w wątku tworzenia backupu.")
        finally:
            if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
                self.root.after(100, self.progress_window.destroy)

            if backup_success_thread:
                self.root.after(
                    150,
                    lambda bd=backup_destination_root: messagebox.showinfo(
                        "Sukces Backup",
                        f"Backup aplikacji został pomyślnie utworzony w folderze:\n{bd}",
                        parent=self.root,
                    ),
                )
            else:
                final_err_msg_ui = (
                    "Nie udało się utworzyć pełnego backupu aplikacji.\n"
                    f"Błąd: {error_message_thread}"
                )
                self.root.after(
                    150,
                    lambda err_ui=final_err_msg_ui: messagebox.showerror(
                        "Błąd Backupu", err_ui, parent=self.root
                    ),
                )
                if os.path.exists(backup_destination_root):
                    try:
                        shutil.rmtree(backup_destination_root)
                        logging.info(
                            f"Usunięto niekompletny folder backupu: {backup_destination_root}"
                        )
                    except Exception as e_del_incomplete:
                        logging.error(
                            "Nie można usunąć niekompletnego folderu backupu "
                            f"'{backup_destination_root}': {e_del_incomplete}"
                        )

    threading.Thread(target=_perform_simple_backup_thread, daemon=True).start()


def load_local_backup(self):
    """
    Przywraca stan aplikacji z wybranego folderu backupu poprzez bezpośrednie
    kopiowanie plików i folderów.
    """
    backup_source_root = filedialog.askdirectory(
        title="Wybierz folder z backupem do przywrócenia (np. GameLauncher_Backup_...)",
        parent=self.root,
    )
    if not backup_source_root:
        return

    if not messagebox.askyesno(
        "Potwierdź Przywrócenie",
        "Czy na pewno chcesz przywrócić dane z tego backupu?\n"
        "Wszystkie obecne dane konfiguracyjne, zapisy gier, obrazy i wewnętrzna muzyka zostaną NADPISANE!\n\n"
        "Zaleca się zamknięcie aplikacji i utworzenie kopii zapasowej obecnego stanu przed kontynuacją, jeśli nie jesteś pewien.",
        icon="warning",
        parent=self.root,
    ):
        return

    items_to_restore = [
        (
            "Przywracanie: config.json",
            os.path.basename(CONFIG_FILE),
            CONFIG_FILE,
            "file",
        ),
        (
            "Przywracanie: local_settings.json",
            os.path.basename(LOCAL_SETTINGS_FILE),
            LOCAL_SETTINGS_FILE,
            "file",
        ),
        (
            "Przywracanie: achievements_def.json",
            os.path.basename(ACHIEVEMENTS_DEFINITIONS_FILE),
            ACHIEVEMENTS_DEFINITIONS_FILE,
            "file",
        ),
        (
            "Przywracanie folderu: games_saves",
            os.path.basename(GAMES_FOLDER),
            GAMES_FOLDER,
            "dir",
        ),
        ("Przywracanie folderu: images", IMAGES_FOLDER, IMAGES_FOLDER, "dir"),
        (
            "Przywracanie folderu: internal_music",
            INTERNAL_MUSIC_DIR,
            INTERNAL_MUSIC_DIR,
            "dir",
        ),
        (
            "Przywracanie folderu: custom_themes",
            CUSTOM_THEMES_DIR,
            CUSTOM_THEMES_DIR,
            "dir",
        ),
    ]

    self.show_progress_window(f"Przywracanie Backupu: {os.path.basename(backup_source_root)}")
    if not (hasattr(self, "progress_window") and self.progress_window.winfo_exists()):
        logging.error("Nie udało się utworzyć okna postępu dla przywracania backupu.")
        return

    self.progress_bar["maximum"] = len(items_to_restore)
    self.progress_bar["value"] = 0
    self.progress_bar["mode"] = "determinate"

    def _update_simple_restore_progress(current_step_index, description):
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_bar["value"] = current_step_index + 1
            self.progress_label.config(
                text=f"Etap {current_step_index + 1}/{len(items_to_restore)}: {description}"
            )
            self.progress_window.update_idletasks()

    def _perform_simple_restore_thread():
        restore_success_thread = True
        error_message_thread = ""
        app_root_path = os.getcwd()

        try:
            for idx, (
                description,
                item_name_in_backup,
                item_app_path_relative,
                item_type,
            ) in enumerate(items_to_restore):
                self.root.after(
                    0,
                    lambda i=idx, d=description: _update_simple_restore_progress(i, d),
                )

                source_path_in_backup = os.path.join(backup_source_root, item_name_in_backup)
                destination_path_in_app = os.path.join(app_root_path, item_app_path_relative)

                if not os.path.exists(source_path_in_backup):
                    logging.warning(
                        "Przywracanie: Zasób "
                        f"'{source_path_in_backup}' nie istnieje w backupie. Pomijanie."
                    )
                    continue

                try:
                    if item_type == "file":
                        if os.path.exists(destination_path_in_app):
                            os.remove(destination_path_in_app)
                        shutil.copy2(source_path_in_backup, destination_path_in_app)
                    elif item_type == "dir":
                        if os.path.exists(destination_path_in_app):
                            shutil.rmtree(destination_path_in_app)
                        shutil.copytree(
                            source_path_in_backup,
                            destination_path_in_app,
                            dirs_exist_ok=False,
                        )
                except Exception as e_copy_item_restore:
                    logging.error(
                        "Przywracanie: Błąd podczas kopiowania "
                        f"'{source_path_in_backup}' do '{destination_path_in_app}': {e_copy_item_restore}"
                    )
                    restore_success_thread = False
                    error_message_thread = (
                        f"Błąd przy '{item_name_in_backup}': {e_copy_item_restore}"
                    )

        except Exception as e_thread_main_restore:
            restore_success_thread = False
            error_message_thread = str(e_thread_main_restore)
            logging.exception("Przywracanie: Krytyczny błąd w wątku przywracania backupu.")
        finally:
            if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
                self.root.after(100, self.progress_window.destroy)

            if restore_success_thread:
                logging.info(
                    "Przywracanie backupu plików zakończone pomyślnie. "
                    "Rozpoczynanie odświeżania aplikacji."
                )

                if hasattr(self, "_custom_themes_cache"):
                    del self._custom_themes_cache

                try:
                    self.config = config_load_config()
                    self.settings = self.config.setdefault("settings", {})
                    self.games = self.config.setdefault("games", {})
                    self.groups = self.config.setdefault("groups", {})
                    self.user = self.config.setdefault("user", {})
                    self.mods_data = self.config.setdefault("mods_data", {})
                    self.archive = self.config.setdefault("archive", [])
                    self.roadmap = self.config.setdefault("roadmap", [])
                    self.local_settings = config_load_local_settings()
                    self._load_achievement_definitions()

                    self.apply_theme(THEMES.get(self.settings.get("theme", "Dark")))
                    self.apply_font_settings()
                    bg_image_path = self.settings.get("background_image", "")
                    if bg_image_path:
                        self.apply_background_image(bg_image_path)

                    if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
                        self.create_sidebar()
                    self.show_home()
                    self.root.after(200, self.update_game_grid)

                    if (
                        hasattr(self, "music_player_page_instance")
                        and self.music_player_page_instance
                    ):
                        if hasattr(self.music_player_page_instance, "_clear_cover_caches"):
                            self.music_player_page_instance._clear_cover_caches()

                        self.music_player_page_instance.named_playlists = self.local_settings.get(
                            "named_music_playlists", {}
                        )
                        self.music_player_page_instance.active_playlist_name = self.local_settings.get(
                            "active_music_playlist_name"
                        )
                        self.music_player_page_instance.current_track_index = self.local_settings.get(
                            "current_track_in_active_playlist_index", -1
                        )
                        self.music_player_page_instance.favorite_tracks = set(
                            self.local_settings.get("music_favorite_tracks", [])
                        )

                        self.music_player_page_instance._load_active_playlist()
                        self.music_player_page_instance._update_available_playlists_ui()
                        self.music_player_page_instance._update_playlist_display()

                        if (
                            self.music_player_page_instance.music_library_view_mode.get()
                            == "tiles"
                        ):
                            self.music_player_page_instance._update_music_tiles_display()
                        if not self.music_player_page_instance.is_playlist_view_active.get():
                            self.music_player_page_instance._update_focus_cover_label(
                                force=True
                            )

                        self.music_player_page_instance.apply_theme_colors()
                        if self.music_player_page_instance.current_track_index != -1:
                            self.music_player_page_instance._update_now_playing_label()
                        else:
                            self.music_player_page_instance._update_now_playing_label(
                                track_name_override="Nic nie gra"
                            )

                    self.root.after(
                        300,
                        lambda: messagebox.showinfo(
                            "Przywracanie Zakończone",
                            "Dane z backupu zostały pomyślnie przywrócone i załadowane.",
                            parent=self.root,
                        ),
                    )
                    self.root.after(350, self.refresh_ui)
                    self.root.after(360, self.show_home)

                except Exception as e_refresh_ui_after_restore:
                    logging.exception(
                        "Błąd podczas odświeżania UI po przywróceniu backupu: "
                        f"{e_refresh_ui_after_restore}"
                    )
                    messagebox.showwarning(
                        "Błąd Odświeżania",
                        "Wystąpił błąd podczas pełnego odświeżania interfejsu po przywróceniu.\n"
                        f"Szczegóły: {e_refresh_ui_after_restore}\n\n"
                        "Zalecane jest zrestartowanie aplikacji.",
                        parent=self.root,
                    )
            else:
                final_err_msg_ui_restore = (
                    "Nie udało się w pełni przywrócić danych z backupu.\n"
                    f"Błąd: {error_message_thread}"
                )
                self.root.after(
                    150,
                    lambda err_ui_restore=final_err_msg_ui_restore: messagebox.showerror(
                        "Błąd Przywracania", err_ui_restore, parent=self.root
                    ),
                )

    threading.Thread(target=_perform_simple_restore_thread, daemon=True).start()


def _update_restore_progress(
    self,
    next_step_description=None,
    increment_value=None,
    file_details=None,
    file_progress_percent=None,
):
    """Aktualizuje pasek postępu i etykietę podczas przywracania backupu."""
    if not hasattr(self, "progress_window") or not self.progress_window.winfo_exists():
        logging.warning(
            "Próba aktualizacji nieistniejącego okna postępu (_update_restore_progress)."
        )
        return

    if increment_value is not None:
        self.total_progress_accumulator += increment_value
        self.total_progress_accumulator = min(self.total_progress_accumulator, 100)

    self.progress_bar["value"] = self.total_progress_accumulator

    final_text = ""
    if file_details and file_progress_percent is not None and next_step_description:
        base_desc_for_file_progress = next_step_description.replace("...", "")
        final_text = (
            f"{base_desc_for_file_progress}: {file_details} ({file_progress_percent}%) "
            f"(Całość: {self.total_progress_accumulator}%)"
        )
    elif next_step_description:
        final_text = f"{next_step_description} ({self.total_progress_accumulator}%)"
    else:
        final_text = f"Postęp: {self.total_progress_accumulator}%"

    if hasattr(self, "progress_label") and self.progress_label.winfo_exists():
        self.progress_label.config(text=final_text)

    self.progress_window.update_idletasks()


def _perform_backup_restore_thread(self, backup_dir):
    """Wykonuje operacje przywracania backupu w osobnym wątku."""
    target_music_library_base_path = os.path.abspath(INTERNAL_MUSIC_DIR)
    os.makedirs(target_music_library_base_path, exist_ok=True)
    success = True
    error_message_details = ""
    current_step_description_for_error = "przygotowania"

    try:
        current_step_description_for_error = self.restore_steps[0][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=self.restore_steps[0][0],
                increment_value=self.restore_steps[0][1],
            ),
        )

        current_step_description_for_error = self.restore_steps[1][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )

        backed_up_local_settings_path = os.path.join(
            backup_dir, os.path.basename(LOCAL_SETTINGS_FILE)
        )
        backed_up_local_settings_data = {}
        if os.path.exists(backed_up_local_settings_path):
            with open(backed_up_local_settings_path, "r", encoding="utf-8") as f:
                backed_up_local_settings_data = json.load(f)
        else:
            logging.warning(f"Brak pliku {LOCAL_SETTINGS_FILE} w backupie.")

        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[1][1]
            ),
        )

        current_step_description_for_error = self.restore_steps[2][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )
        music_backup_source_folder = os.path.join(backup_dir, "music_library_backup")
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[2][1]
            ),
        )

        self.current_restore_step_index = 3
        step_info = self.restore_steps[self.current_restore_step_index]
        music_stage_weight = step_info[1]
        current_step_description_for_error = step_info[0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )

        music_files_to_process_from_backup = []
        if "named_music_playlists" in backed_up_local_settings_data:
            for pl_name, backed_up_entries in backed_up_local_settings_data.get(
                "named_music_playlists", {}
            ).items():
                for entry_from_backup in backed_up_entries:
                    if entry_from_backup.get("is_internal") and entry_from_backup.get(
                        "path"
                    ):
                        filename_in_backup_folder = entry_from_backup.get("path")
                        src_music_file_in_backup_storage = os.path.join(
                            music_backup_source_folder, filename_in_backup_folder
                        )
                        if os.path.exists(src_music_file_in_backup_storage):
                            music_files_to_process_from_backup.append(
                                (
                                    src_music_file_in_backup_storage,
                                    entry_from_backup,
                                    pl_name,
                                )
                            )

        total_music_files_to_restore = len(music_files_to_process_from_backup)
        processed_music_files_restore = 0

        for (
            src_file_path_from_backup,
            original_entry_from_json_backup,
            playlist_name_for_restore_update,
        ) in music_files_to_process_from_backup:
            music_filename_only = os.path.basename(src_file_path_from_backup)
            target_abs_path_in_internal_dir = os.path.join(
                target_music_library_base_path, music_filename_only
            )
            try:
                os.makedirs(os.path.dirname(target_abs_path_in_internal_dir), exist_ok=True)
                shutil.copy2(src_file_path_from_backup, target_abs_path_in_internal_dir)

                playlist_to_update = backed_up_local_settings_data[
                    "named_music_playlists"
                ].get(playlist_name_for_restore_update)
                if playlist_to_update:
                    for entry_in_pl in playlist_to_update:
                        if entry_in_pl == original_entry_from_json_backup:
                            entry_in_pl["path"] = target_abs_path_in_internal_dir
                            entry_in_pl["is_internal"] = True
                            break

                processed_music_files_restore += 1
                file_progress_percent = (
                    int((processed_music_files_restore / total_music_files_to_restore) * 100)
                    if total_music_files_to_restore > 0
                    else 0
                )
                if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
                    self.root.after(
                        0,
                        lambda f_details=music_filename_only, fp_perc=file_progress_percent, current_step_desc=current_step_description_for_error: self._update_restore_progress(
                            next_step_description=current_step_desc,
                            file_details=f_details,
                            file_progress_percent=fp_perc,
                        ),
                    )
            except Exception as e_music_restore_single:
                logging.error(
                    f"Nie udało się przywrócić pliku muzycznego '{music_filename_only}' "
                    f"z backupu: {e_music_restore_single}"
                )
                playlist_to_update = backed_up_local_settings_data[
                    "named_music_playlists"
                ].get(playlist_name_for_restore_update)
                if playlist_to_update:
                    for entry_in_pl in playlist_to_update:
                        if entry_in_pl == original_entry_from_json_backup:
                            entry_in_pl["path"] = None
                            entry_in_pl["is_internal"] = False
                            break

        self.root.after(
            0,
            lambda: self._update_restore_progress(increment_value=music_stage_weight),
        )

        current_step_description_for_error = self.restore_steps[4][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )
        self.local_settings.clear()
        self.local_settings.update(backed_up_local_settings_data)
        config_save_local_settings(self.local_settings)
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[4][1]
            ),
        )

        current_step_description_for_error = self.restore_steps[5][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )
        config_restore_map = [
            (os.path.basename(CONFIG_FILE), CONFIG_FILE),
            (
                os.path.basename(ACHIEVEMENTS_DEFINITIONS_FILE),
                ACHIEVEMENTS_DEFINITIONS_FILE,
            ),
        ]
        for config_filename, destination_path in config_restore_map:
            src_path = os.path.join(backup_dir, config_filename)
            dst_path = destination_path
            if os.path.exists(src_path):
                dst_dir = os.path.dirname(dst_path)
                if dst_dir:
                    os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src_path, dst_path)
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[5][1]
            ),
        )

        current_step_description_for_error = self.restore_steps[6][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )
        saves_src = os.path.join(backup_dir, "games_saves_backup")
        if os.path.exists(saves_src):
            if os.path.exists(GAMES_FOLDER):
                shutil.rmtree(GAMES_FOLDER)
            shutil.copytree(saves_src, GAMES_FOLDER, dirs_exist_ok=True)
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[6][1]
            ),
        )

        current_step_description_for_error = self.restore_steps[7][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )
        images_src = os.path.join(backup_dir, "images_backup")
        images_dst_app = os.path.abspath(IMAGES_FOLDER)
        if os.path.exists(images_src):
            if os.path.exists(images_dst_app):
                shutil.rmtree(images_dst_app)
            shutil.copytree(images_src, images_dst_app, dirs_exist_ok=True)
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[7][1]
            ),
        )

        current_step_description_for_error = self.restore_steps[8][0]
        self.root.after(
            0,
            lambda: self._update_restore_progress(
                next_step_description=current_step_description_for_error
            ),
        )

        self.config = config_load_config()
        self.settings = self.config.setdefault("settings", {})
        self.games = self.config.setdefault("games", {})
        self.groups = self.config.setdefault("groups", {})
        self.user = self.config.setdefault("user", {})
        self.mods_data = self.config.setdefault("mods_data", {})
        self.archive = self.config.setdefault("archive", [])
        self.roadmap = self.config.setdefault("roadmap", [])
        self._load_achievement_definitions()

        self.root.after(0, self.repair_save_paths)
        self.root.after(0, self.refresh_ui)
        self.root.after(0, self.show_home)

        if hasattr(self, "music_player_page_instance") and self.music_player_page_instance:
            self.root.after(
                0,
                lambda: (
                    setattr(
                        self.music_player_page_instance,
                        "named_playlists",
                        self.local_settings.get("named_music_playlists", {}),
                    ),
                    setattr(
                        self.music_player_page_instance,
                        "active_playlist_name",
                        self.local_settings.get("active_music_playlist_name"),
                    ),
                    setattr(
                        self.music_player_page_instance,
                        "current_track_index",
                        self.local_settings.get(
                            "current_track_in_active_playlist_index", -1
                        ),
                    ),
                    setattr(
                        self.music_player_page_instance,
                        "favorite_tracks",
                        set(self.local_settings.get("music_favorite_tracks", [])),
                    ),
                    self.music_player_page_instance._load_active_playlist(),
                    self.music_player_page_instance._update_available_playlists_ui(),
                    self.music_player_page_instance._update_playlist_display(),
                    self.music_player_page_instance.apply_theme_colors(),
                    (
                        self.music_player_page_instance._update_now_playing_label()
                        if self.music_player_page_instance.current_track_index != -1
                        else self.music_player_page_instance._update_now_playing_label(
                            track_name_override="Nic nie gra"
                        )
                    ),
                ),
            )

        self.root.after(
            0,
            lambda: self._update_restore_progress(
                increment_value=self.restore_steps[8][1]
            ),
        )
        self.root.after(
            100,
            lambda: self._update_restore_progress(
                next_step_description="Ukończono!",
                increment_value=(100 - self.total_progress_accumulator),
            ),
        )

    except json.JSONDecodeError as e:
        success = False
        error_message_details = (
            f"Błąd odczytu pliku JSON ({current_step_description_for_error}): {e}"
        )
        logging.error(error_message_details)
    except IOError as e:
        success = False
        error_message_details = (
            f"Błąd operacji plikowej ({current_step_description_for_error}): {e}"
        )
        logging.error(error_message_details)
    except Exception as e:
        success = False
        error_message_details = (
            "Nie udało się w pełni wczytać backupu aplikacji "
            f"({current_step_description_for_error}): {e}"
        )
        logging.exception(error_message_details)
    finally:
        self.root.after(200, self._destroy_progress_window)
        if success:
            self.root.after(
                250,
                lambda bp=target_music_library_base_path: messagebox.showinfo(
                    "Sukces",
                    "Przywrócono backup z wybranego folderu.\n\n"
                    "Ścieżki muzyki zostały zaktualizowane i wskazują na wewnętrzną bibliotekę:\n"
                    f"{bp}",
                    parent=self.root,
                ),
            )
        else:
            final_error_msg = (
                error_message_details
                if error_message_details
                else "Wystąpił nieznany błąd podczas przywracania."
            )
            self.root.after(
                250,
                lambda em=final_error_msg: messagebox.showerror(
                    "Błąd Przywracania", em, parent=self.root
                ),
            )


__all__ = [
    "_destroy_progress_window",
    "show_progress_window",
    "backup_to_local_folder",
    "load_local_backup",
    "_update_restore_progress",
    "_perform_backup_restore_thread",
]
