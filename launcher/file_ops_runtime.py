import logging
import os
import shutil
import threading
import time
import tkinter as tk
from tkinter import messagebox


def _copy_or_delete_with_progress(
    self,
    operation_type,
    source_path,
    dest_path,
    operation_title,
    parent_window=None,
    callback_on_success=None,
):
    """Wykonuje kopiowanie (copytree) lub usuwanie (rmtree) w tle z paskiem postępu."""
    if parent_window is None:
        parent_window = self.root

    logging.info(
        f"Rozpoczynanie operacji '{operation_type}' dla '{source_path}' -> '{dest_path}'"
    )

    if not source_path or not os.path.exists(source_path):
        messagebox.showerror(
            "Błąd",
            f"Ścieżka źródłowa nie istnieje:\n{source_path}",
            parent=parent_window,
        )
        return False
    if operation_type == "copy" and not dest_path:
        messagebox.showerror(
            "Błąd",
            "Ścieżka docelowa jest wymagana do kopiowania.",
            parent=parent_window,
        )
        return False

    try:
        total_files = 0
        if os.path.isdir(source_path) and operation_type == "copy":
            for _, _, files_in_dir_count in os.walk(source_path):
                total_files += len(files_in_dir_count)
        elif os.path.isfile(source_path) and operation_type == "copy":
            total_files = 1
        elif operation_type == "delete":
            total_files = 1

        if total_files == 0 and operation_type == "copy":
            if dest_path:
                os.makedirs(dest_path, exist_ok=True)
            messagebox.showinfo(
                "Informacja", "Folder źródłowy jest pusty.", parent=parent_window
            )
            if callback_on_success:
                self.root.after(0, callback_on_success)
            return True

        self.show_progress_window(operation_title)
        self.progress_bar["maximum"] = total_files
        self.progress_bar["value"] = 0
        self.progress_bar["mode"] = "determinate"
        self.progress_label.config(text=f"0 / {total_files}")

        op_thread = threading.Thread(
            target=self._perform_file_operation_thread,
            kwargs={
                "operation_type": operation_type,
                "src": source_path,
                "dst": dest_path,
                "total_files": total_files,
                "callback_on_success": callback_on_success,
            },
            daemon=True,
        )
        op_thread.start()
        return True

    except Exception as e:
        logging.exception(f"Błąd przed rozpoczęciem operacji '{operation_type}': {e}")
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror(
            f"Błąd {operation_title}",
            f"Nie można rozpocząć operacji:\n{e}",
            parent=parent_window,
        )
        return False


def _perform_file_operation_thread(
    self, operation_type, src, dst, total_files, callback_on_success=None
):
    """Wykonuje kopiowanie lub usuwanie plików w osobnym wątku."""
    processed_files = 0
    last_update_time = time.time()
    operation_completed_successfully = False

    try:
        if operation_type == "copy":
            os.makedirs(dst, exist_ok=True)
            for root_dir, dirs, files_in_dir_loop in os.walk(src):
                relative_path_loop = os.path.relpath(root_dir, src)
                dest_root_loop = os.path.join(dst, relative_path_loop)
                os.makedirs(dest_root_loop, exist_ok=True)

                for file_item_loop in files_in_dir_loop:
                    source_file_loop = os.path.join(root_dir, file_item_loop)
                    dest_file_loop = os.path.join(dest_root_loop, file_item_loop)
                    try:
                        shutil.copy2(source_file_loop, dest_file_loop)
                        processed_files += 1
                        now = time.time()
                        if now - last_update_time > 0.1 or processed_files == total_files:
                            percent = (
                                int((processed_files / total_files) * 100)
                                if total_files > 0
                                else 100
                            )
                            progress_text = f"{processed_files} / {total_files}"
                            if hasattr(self, "_update_copy_progress_ui"):
                                self.root.after(
                                    0,
                                    self._update_copy_progress_ui,
                                    percent,
                                    progress_text,
                                )
                            last_update_time = now
                    except Exception as copy_e:
                        logging.error(f"Błąd kopiowania {source_file_loop}: {copy_e}")
                        raise copy_e
            operation_completed_successfully = True

        elif operation_type == "delete":
            if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
                if hasattr(self, "_update_copy_progress_ui"):
                    self.root.after(0, self._update_copy_progress_ui, 50, "Usuwanie...")
            shutil.rmtree(src)
            processed_files = total_files
            if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
                if hasattr(self, "_update_copy_progress_ui"):
                    self.root.after(0, self._update_copy_progress_ui, 100, "Zakończono")
            operation_completed_successfully = True

        logging.info(
            f"Operacja '{operation_type}' zakończona. Przetworzono ~{processed_files} plików."
        )

        if operation_completed_successfully and callback_on_success:
            self.root.after(0, callback_on_success)

    except Exception as thread_e:
        operation_completed_successfully = False
        logging.exception(
            f"Błąd w wątku operacji '{operation_type}' dla '{src}': {thread_e}"
        )
    finally:
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.root.after(150, self._destroy_progress_window)

        if not operation_completed_successfully:
            parent_for_error = self.root
            active_toplevels = [
                win
                for win in self.root.winfo_children()
                if isinstance(win, tk.Toplevel) and win.winfo_exists()
            ]
            for tl in active_toplevels:
                if hasattr(tl, "game_name") and hasattr(tl, "save_path"):
                    parent_for_error = tl
                    break

            self.root.after(
                200,
                lambda em_op=operation_type, pf=parent_for_error: messagebox.showerror(
                    f"Błąd {em_op.capitalize()}",
                    f"Wystąpił błąd podczas operacji {em_op}. Szczegóły w logach.",
                    parent=pf,
                ),
            )


__all__ = [
    "_copy_or_delete_with_progress",
    "_perform_file_operation_thread",
]
