import logging
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from launcher.utils import save_config
from ui.game_details import GameDetailsWindow


def load_autoscan_folders_list(self):
    """Ładuje listę folderów do skanowania screenshotów do listboxa w ustawieniach."""
    if hasattr(self, "autoscan_folders_listbox") and self.autoscan_folders_listbox.winfo_exists():
        self.autoscan_folders_listbox.delete(0, tk.END)
        scan_folders = self.settings.get("autoscan_screenshot_folders", [])
        for folder in scan_folders:
            self.autoscan_folders_listbox.insert(tk.END, folder)


def load_screenshot_ignored_folders(self):
    """Wczytuje listę ignorowanych folderów screenshotów do pola Text."""
    if hasattr(self, "ss_ignored_folders_text") and self.ss_ignored_folders_text.winfo_exists():
        ignored_list = self.settings.get("screenshot_scan_ignore_folders", [])
        self.ss_ignored_folders_text.delete("1.0", tk.END)
        self.ss_ignored_folders_text.insert("1.0", "\n".join(ignored_list))


def save_screenshot_ignored_folders(self):
    """Pobiera nazwy z pola Text, czyści je i zapisuje do konfiguracji (screenshoty)."""
    if hasattr(self, "ss_ignored_folders_text") and self.ss_ignored_folders_text.winfo_exists():
        raw_text = self.ss_ignored_folders_text.get("1.0", tk.END)
        ignored_list = [line.strip().lower() for line in raw_text.splitlines() if line.strip()]
        unique_ignored_list = sorted(list(set(ignored_list)))

        self.settings["screenshot_scan_ignore_folders"] = unique_ignored_list
        save_config(self.config)
        self.load_screenshot_ignored_folders()
        messagebox.showinfo(
            "Zapisano",
            "Lista ignorowanych folderów dla screenshotów została zapisana.",
            parent=self.settings_page_frame,
        )
        logging.info(
            f"Zapisano ignorowane foldery screenshotów: {unique_ignored_list}"
        )


def add_autoscan_folder(self):
    """Otwiera dialog wyboru folderu i dodaje go do listy skanowania screenshotów."""
    folder_selected = filedialog.askdirectory(
        title="Wybierz folder do skanowania screenshotów",
        parent=self.settings_page_frame,
    )
    if folder_selected:
        scan_folders = self.settings.setdefault("autoscan_screenshot_folders", [])
        if folder_selected not in scan_folders:
            scan_folders.append(folder_selected)
            save_config(self.config)
            self.load_autoscan_folders_list()
            logging.info(f"Dodano folder do skanowania screenshotów: {folder_selected}")
        else:
            messagebox.showwarning(
                "Informacja",
                "Ten folder jest już na liście.",
                parent=self.settings_page_frame,
            )


def remove_autoscan_folder(self):
    """Usuwa zaznaczony folder z listy skanowania screenshotów."""
    selected_indices = self.autoscan_folders_listbox.curselection()
    if selected_indices:
        index = selected_indices[0]
        folder_to_remove = self.autoscan_folders_listbox.get(index)
        scan_folders = self.settings.get("autoscan_screenshot_folders", [])
        if folder_to_remove in scan_folders:
            scan_folders.remove(folder_to_remove)
            save_config(self.config)
            self.load_autoscan_folders_list()
            logging.info(f"Usunięto folder ze skanowania screenshotów: {folder_to_remove}")
    else:
        messagebox.showwarning(
            "Błąd",
            "Nie wybrano folderu do usunięcia.",
            parent=self.settings_page_frame,
        )


def _save_autoscan_startup_setting(self):
    """Zapisuje ustawienie automatycznego skanowania screenshotów przy starcie."""
    self.settings["autoscan_on_startup"] = self.autoscan_on_startup_var.get()
    save_config(self.config)
    logging.info(
        f"Ustawienie autoscan_on_startup zmienione na: {self.autoscan_on_startup_var.get()}"
    )


def start_scan_screenshots_thread(self, game_to_scan=None):
    """Uruchamia skanowanie folderów screenshotów w osobnym wątku."""
    if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
        messagebox.showwarning(
            "Skanowanie w toku",
            "Inna operacja (np. synchronizacja, skanowanie) jest już w toku.",
            parent=self.root,
        )
        return

    title = (
        f"Skanowanie screenshotów dla: {game_to_scan}"
        if game_to_scan
        else "Skanowanie screenshotów..."
    )
    self.show_progress_window(title)
    self.progress_bar["mode"] = "indeterminate"
    self.progress_bar.start()
    self.progress_label.config(text="Przygotowywanie...")

    scan_thread = threading.Thread(
        target=self._scan_for_screenshots_thread,
        args=(game_to_scan,),
        daemon=True,
    )
    scan_thread.start()


def _scan_for_screenshots_thread(self, game_to_scan=None):
    """
    Skanuje skonfigurowane foldery w poszukiwaniu screenshotów pasujących do gier.
    Jeśli game_to_scan jest podane, skanuje tylko dla tej gry.
    """
    scan_folders = self.settings.get("autoscan_screenshot_folders", [])
    if not scan_folders:
        logging.warning(
            "Wykryto brak folderów do skanowania w wątku _scan_for_screenshots_thread (nie powinno się zdarzyć)."
        )
        self.root.after(0, self._destroy_progress_window)
        return

    ignored_folder_names = set(
        name.lower() for name in self.settings.get("screenshot_scan_ignore_folders", [])
    )
    logging.info(f"Ignorowane foldery screenshotów: {ignored_folder_names}")
    supported_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")
    found_new_count_total = 0
    processed_files_count = 0
    scan_start_time = time.time()

    try:
        games_to_check = {}
        if game_to_scan:
            if game_to_scan in self.games:
                games_to_check[game_to_scan] = self.games[game_to_scan]
            else:
                logging.error(
                    f"Skanowanie screenshotów: Nie znaleziono gry '{game_to_scan}'"
                )
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd",
                        f"Gra '{game_to_scan}' nie istnieje.",
                        parent=self.root,
                    ),
                )
                self.root.after(0, self._destroy_progress_window)
                return
        else:
            games_to_check = self.games.copy()

        if not games_to_check:
            logging.info("Brak gier w bibliotece do skanowania screenshotów.")
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Informacja", "Biblioteka gier jest pusta.", parent=self.root
                ),
            )
            self.root.after(0, self._destroy_progress_window)
            return

        total_folders_to_scan = len(scan_folders)
        current_folder_index = 0

        self.root.after(
            0,
            lambda: (
                self.progress_bar.stop(),
                self.progress_bar.config(mode="determinate", maximum=100, value=0),
                self.progress_label.config(text="Rozpoczynanie skanowania..."),
            ),
        )
        time.sleep(0.1)

        something_changed = False

        for folder_path in scan_folders:
            current_folder_index += 1
            folder_name = os.path.basename(folder_path)
            logging.info(
                f"Skanowanie folderu: {folder_path} ({current_folder_index}/{total_folders_to_scan})"
            )
            self.root.after(
                0,
                lambda f=folder_name, i=current_folder_index, t=total_folders_to_scan: self.progress_label.config(
                    text=f"Folder {i}/{t}: {f}"
                ),
            )

            if not os.path.isdir(folder_path):
                logging.warning(f"Folder '{folder_path}' nie istnieje. Pomijanie.")
                continue

            files_in_folder = []
            for root, dirs, files in os.walk(folder_path):
                dirs[:] = [d for d in dirs if d.lower() not in ignored_folder_names]
                for filename in files:
                    files_in_folder.append(os.path.join(root, filename))

            total_files_in_folder = len(files_in_folder)
            processed_files_in_folder = 0

            for file_path in files_in_folder:
                processed_files_count += 1
                processed_files_in_folder += 1

                now = time.time()
                if processed_files_count % 50 == 0 or now - scan_start_time > 1:
                    percent_overall = int((current_folder_index / total_folders_to_scan) * 100)
                    self.root.after(
                        0,
                        lambda p=percent_overall, fn=os.path.basename(file_path): (
                            self.progress_bar.config(value=p),
                            self.progress_label.config(
                                text=f"Folder {current_folder_index}/{total_folders_to_scan}: {fn} ({p}%)"
                            ),
                        ),
                    )
                    scan_start_time = now

                if not file_path.lower().endswith(supported_extensions):
                    continue

                filename_lower = os.path.basename(file_path).lower()

                for game_name, game_data in games_to_check.items():
                    game_name_lower = game_name.lower()
                    if filename_lower.startswith(game_name_lower):
                        autoscan_list = game_data.setdefault("autoscan_screenshots", [])
                        abs_file_path = os.path.abspath(file_path)

                        if abs_file_path not in autoscan_list:
                            manual_list = game_data.get("screenshots", [])
                            if abs_file_path not in manual_list:
                                autoscan_list.append(abs_file_path)
                                found_new_count_total += 1
                                something_changed = True
                                logging.info(
                                    f"Znaleziono nowy screenshot dla '{game_name}': {abs_file_path}"
                                )
                            else:
                                logging.debug(
                                    f"Screenshot '{abs_file_path}' już istnieje w liście ręcznej dla '{game_name}'."
                                )
                        break

        if something_changed:
            save_config(self.config)

        scan_duration = time.time() - scan_start_time
        logging.info(
            f"Skanowanie screenshotów zakończone w {scan_duration:.2f}s. Znaleziono {found_new_count_total} nowych screenshotów."
        )

        self.root.after(0, self._destroy_progress_window)
        self.root.after(
            10,
            lambda count=found_new_count_total: messagebox.showinfo(
                "Skanowanie Zakończone",
                f"Skanowanie zakończone.\nZnaleziono {count} nowych screenshotów.",
                parent=self.root,
            ),
        )

        if game_to_scan:
            self.root.after(50, lambda gn=game_to_scan: self._refresh_details_window_if_open(gn))

    except Exception as e:
        logging.exception("Błąd podczas skanowania screenshotów.")
        self.root.after(0, self._destroy_progress_window)
        self.root.after(
            0,
            lambda err=e: messagebox.showerror(
                "Błąd Skanowania",
                f"Wystąpił nieoczekiwany błąd: {err}",
                parent=self.root,
            ),
        )


def _refresh_details_window_if_open(self, game_name):
    """Sprawdza, czy okno szczegółów dla danej gry jest otwarte i je odświeża."""
    details_title = f"Szczegóły Gry - {game_name}"
    for widget in self.root.winfo_children():
        if isinstance(widget, tk.Toplevel) and widget.title() == details_title:
            if isinstance(widget, GameDetailsWindow) and widget.winfo_exists():
                logging.info(
                    f"Odświeżanie otwartego okna szczegółów dla: {game_name} po skanowaniu screenshotów."
                )
                widget.refresh_details_data()
                self._show_game_details_and_select_tab(game_name, "Screenshoty")
                break


__all__ = [
    "load_autoscan_folders_list",
    "load_screenshot_ignored_folders",
    "save_screenshot_ignored_folders",
    "add_autoscan_folder",
    "remove_autoscan_folder",
    "_save_autoscan_startup_setting",
    "start_scan_screenshots_thread",
    "_scan_for_screenshots_thread",
    "_refresh_details_window_if_open",
]
