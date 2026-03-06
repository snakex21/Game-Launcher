import logging
import os
import shutil
import threading
import time
from tkinter import messagebox

from launcher.utils import GAMES_FOLDER


def _create_or_overwrite_autosave(self, game_name):
    """Tworzy lub nadpisuje folder _autosave w osobnym wątku z paskiem postępu."""
    game_data = self.games.get(game_name)
    if not game_data:
        return

    save_path = game_data.get("save_path")
    backup_base_path = os.path.join(GAMES_FOLDER, game_name)

    if not save_path or not os.path.isdir(save_path):
        logging.warning(
            f"Auto-zapis dla '{game_name}' pominięty: ścieżka '{save_path}' nieprawidłowa."
        )
        return

    autosave_dir = os.path.join(backup_base_path, "_autosave")

    try:
        total_files = 0
        for root, dirs, files in os.walk(save_path):
            total_files += len(files)
        logging.info(
            f"Rozpoczynanie auto-zapisu dla '{game_name}'. Plików: {total_files}"
        )

        if total_files == 0:
            logging.info(
                f"Brak plików do skopiowania w '{save_path}'. Auto-zapis pominięty."
            )
            os.makedirs(autosave_dir, exist_ok=True)
            return

        self.show_progress_window(f"Tworzenie auto-zapisu dla {game_name}")
        self.progress_bar["maximum"] = total_files
        self.progress_bar["value"] = 0
        self.progress_bar["mode"] = "determinate"
        self.progress_label.config(text=f"0 / {total_files}")

        copy_thread = threading.Thread(
            target=self._copy_with_progress_thread,
            args=(save_path, autosave_dir, total_files),
            daemon=True,
        )
        copy_thread.start()

    except Exception as e:
        logging.exception(
            f"Błąd przed rozpoczęciem kopiowania auto-zapisu dla '{game_name}': {e}"
        )
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror(
            "Błąd Auto-Zapisu",
            f"Nie można rozpocząć auto-zapisu:\n{e}",
            parent=self.root,
        )


def _copy_with_progress_thread(self, src, dst, total_files):
    """Kopiuje pliki z src do dst, aktualizując okno postępu (działa w wątku)."""
    copied_files = 0
    os.makedirs(dst, exist_ok=True)
    last_update_time = time.time()

    try:
        for root, dirs, files in os.walk(src):
            relative_path = os.path.relpath(root, src)
            dest_root = os.path.join(dst, relative_path)
            os.makedirs(dest_root, exist_ok=True)

            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(dest_root, file)
                try:
                    shutil.copy2(source_file, dest_file)
                    copied_files += 1

                    now = time.time()
                    if now - last_update_time > 0.1 or copied_files == total_files:
                        percent = (
                            int((copied_files / total_files) * 100)
                            if total_files > 0
                            else 100
                        )
                        progress_text = f"{copied_files} / {total_files}"
                        self.root.after(
                            0, self._update_copy_progress_ui, percent, progress_text
                        )
                        last_update_time = now
                except Exception as copy_e:
                    logging.error(
                        f"Błąd kopiowania pliku {source_file} do {dest_file}: {copy_e}"
                    )

        logging.info(
            f"Zakończono kopiowanie auto-zapisu. Skopiowano {copied_files} plików."
        )
        self.root.after(100, self._destroy_progress_window)

    except Exception as thread_e:
        logging.exception(f"Błąd w wątku kopiowania auto-zapisu: {thread_e}")
        error_msg = f"Błąd podczas tworzenia auto-zapisu:\n{thread_e}"
        self.root.after(
            0,
            lambda: (
                self._destroy_progress_window(),
                messagebox.showerror("Błąd Auto-Zapisu", error_msg, parent=self.root),
            ),
        )


__all__ = ["_create_or_overwrite_autosave", "_copy_with_progress_thread"]
