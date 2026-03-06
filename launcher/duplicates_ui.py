import datetime
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from launcher.utils import GAMES_FOLDER, IMAGES_FOLDER, save_config


def _normalize_game_name_for_duplicates(self, name):
    """Tworzy 'klucz' do porównywania nazw gier, ignorując drobne różnice."""
    normalized = name.lower()
    normalized = re.sub(r"[^a-z]", "", normalized)
    return normalized


def start_duplicate_scan_thread(self):
    """Uruchamia skanowanie w poszukiwaniu duplikatów w osobnym wątku."""
    if not self.games:
        messagebox.showinfo("Informacja", "Biblioteka gier jest pusta.")
        return

    self.show_progress_window("Wyszukiwanie duplikatów...")
    self.progress_bar["mode"] = "indeterminate"
    self.progress_bar.start()
    self.progress_label.config(text="Analizowanie biblioteki...")

    scan_thread = threading.Thread(target=self.find_potential_duplicates, daemon=True)
    scan_thread.start()


def find_potential_duplicates(self):
    """Logika wyszukiwania potencjalnych duplikatów."""
    logging.info("Rozpoczynanie wyszukiwania duplikatów...")
    potential_duplicates = {}
    processed_count = 0
    total_games = len(self.games)

    try:
        for original_name in list(self.games.keys()):
            normalized = self._normalize_game_name_for_duplicates(original_name)
            if not normalized:
                continue

            if normalized not in potential_duplicates:
                potential_duplicates[normalized] = []
            potential_duplicates[normalized].append(original_name)

        _ = processed_count
        _ = total_games
        duplicate_groups = {
            norm_name: games_list
            for norm_name, games_list in potential_duplicates.items()
            if len(games_list) > 1
        }

        logging.info(
            f"Znaleziono {len(duplicate_groups)} grup potencjalnych duplikatów."
        )

        self.root.after(0, self.stop_scan_progress)
        self.root.after(10, lambda groups=duplicate_groups: self.show_duplicate_results(groups))

    except Exception:
        logging.exception("Błąd podczas wyszukiwania duplikatów.")
        self.root.after(0, self.stop_scan_progress)
        self.root.after(
            0,
            lambda: messagebox.showerror(
                "Błąd", f"Wystąpił błąd podczas szukania duplikatów:\n{e}"
            ),
        )


def show_duplicate_results(self, duplicate_groups):
    """Wyświetla okno z wynikami skanowania duplikatów (z licznikiem zaznaczenia)."""
    if not duplicate_groups:
        messagebox.showinfo("Duplikaty", "Nie znaleziono potencjalnych duplikatów.")
        return

    results_window = tk.Toplevel(self.root)
    results_window.title("Potencjalne Duplikaty Gier")
    results_window.geometry("850x500")
    results_window.configure(bg="#1e1e1e")
    results_window.grab_set()

    ttk.Label(
        results_window,
        text="Znaleziono następujące grupy potencjalnych duplikatów:",
        font=("Helvetica", 12),
    ).pack(pady=10)

    tree_frame = ttk.Frame(results_window)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    columns = ("Nazwa Gry", "Czas Gry", "Data Dodania", "Ścieżka Pliku")
    self.duplicate_tree = ttk.Treeview(
        tree_frame, columns=columns, show="headings", selectmode="extended"
    )

    self.duplicate_tree.heading(
        "Nazwa Gry",
        text="Nazwa Gry",
        command=lambda: self._sort_duplicate_tree("Nazwa Gry"),
    )
    self.duplicate_tree.column("Nazwa Gry", width=200, anchor=tk.W)
    self.duplicate_tree.heading(
        "Czas Gry",
        text="Czas Gry",
        command=lambda: self._sort_duplicate_tree("Czas Gry"),
    )
    self.duplicate_tree.column("Czas Gry", width=80, anchor=tk.CENTER)
    self.duplicate_tree.heading(
        "Data Dodania",
        text="Data Dodania",
        command=lambda: self._sort_duplicate_tree("Data Dodania"),
    )
    self.duplicate_tree.column("Data Dodania", width=110, anchor=tk.CENTER)
    self.duplicate_tree.heading(
        "Ścieżka Pliku",
        text="Ścieżka Pliku",
        command=lambda: self._sort_duplicate_tree("Ścieżka Pliku"),
    )
    self.duplicate_tree.column("Ścieżka Pliku", width=300, anchor=tk.W)

    tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.duplicate_tree.yview)
    self.duplicate_tree.configure(yscrollcommand=tree_scrollbar.set)

    tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    self.duplicate_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    self._duplicate_sort_col = "Nazwa Gry"
    self._duplicate_sort_rev = False

    group_id_counter = 0
    self.duplicate_tree_data = {}
    for normalized_name, game_list in duplicate_groups.items():
        group_iid = f"group_{group_id_counter}"
        self.duplicate_tree.insert(
            "",
            "end",
            iid=group_iid,
            values=(
                f"--- Grupa: {normalized_name} ({len(game_list)} gry) ---",
                "",
                "",
                "",
            ),
            tags=("group_header",),
        )
        self.duplicate_tree.tag_configure("group_header", background="#3e3e3e", foreground="white")

        for game_name in game_list:
            game_data = self.games.get(game_name, {})
            exe_path = game_data.get("exe_path", "Brak ścieżki")
            play_time_str = self.format_play_time(game_data.get("play_time", 0))
            try:
                added_timestamp = game_data.get("date_added")
                added_date_str = (
                    datetime.datetime.fromtimestamp(added_timestamp).strftime("%Y-%m-%d %H:%M")
                    if added_timestamp
                    else ""
                )
            except Exception:
                added_date_str = ""

            values = (game_name, play_time_str, added_date_str, exe_path)
            self.duplicate_tree.insert(group_iid, "end", iid=game_name, values=values)
            self.duplicate_tree_data[game_name] = game_data

        group_id_counter += 1

    action_frame = ttk.Frame(results_window)
    action_frame.pack(pady=10, fill=tk.X)

    left_action_frame = ttk.Frame(action_frame)
    left_action_frame.pack(side=tk.LEFT, padx=10)
    ttk.Button(
        left_action_frame,
        text="Otwórz Lokalizację",
        command=self._open_selected_duplicate_location,
    ).pack(side=tk.LEFT)

    self.duplicate_count_label = ttk.Label(left_action_frame, text="Zaznaczono: 0 gier")
    self.duplicate_count_label.pack(side=tk.LEFT, padx=10)

    right_action_frame = ttk.Frame(action_frame)
    right_action_frame.pack(side=tk.RIGHT, padx=10)

    def delete_selected():
        selected_items = self.duplicate_tree.selection()
        games_to_delete = [item for item in selected_items if not item.startswith("group_")]

        if not games_to_delete:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Zaznacz gry, które chcesz usunąć.",
                parent=results_window,
            )
            return

        confirm_msg = f"Czy na pewno chcesz usunąć {len(games_to_delete)} zaznaczone gry?"
        if messagebox.askyesno("Potwierdź Usunięcie", confirm_msg, parent=results_window):
            deleted_count = 0
            for game_name_to_delete in games_to_delete:
                if game_name_to_delete in self.games:
                    try:
                        logging.info(f"Usuwanie duplikatu: {game_name_to_delete}")
                        cover_image = self.games[game_name_to_delete].get("cover_image")
                        if (
                            cover_image
                            and os.path.exists(cover_image)
                            and os.path.dirname(os.path.abspath(cover_image))
                            == os.path.abspath(IMAGES_FOLDER)
                        ):
                            os.remove(cover_image)
                        backup_path = os.path.join(GAMES_FOLDER, game_name_to_delete)
                        if os.path.exists(backup_path):
                            shutil.rmtree(backup_path)
                        for group in self.groups.values():
                            if game_name_to_delete in group:
                                group.remove(game_name_to_delete)
                        del self.games[game_name_to_delete]
                        deleted_count += 1
                    except Exception as e:
                        logging.error(
                            f"Błąd podczas usuwania duplikatu '{game_name_to_delete}': {e}"
                        )
                        messagebox.showerror(
                            "Błąd Usuwania",
                            f"Nie udało się usunąć gry '{game_name_to_delete}':\n{e}",
                            parent=results_window,
                        )

            if deleted_count > 0:
                save_config(self.config)
                self.reset_and_update_grid()
                self.update_tag_filter_options()
                messagebox.showinfo(
                    "Usunięto",
                    f"Usunięto {deleted_count} gier.",
                    parent=results_window.master,
                )
                results_window.destroy()

    ttk.Button(right_action_frame, text="Usuń Zaznaczone Gry", command=delete_selected).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(right_action_frame, text="Zamknij", command=results_window.destroy).pack(
        side=tk.LEFT, padx=5
    )

    self.duplicate_tree.bind("<<TreeviewSelect>>", self._update_duplicate_selection_count)
    self._update_duplicate_selection_count()


def _update_duplicate_selection_count(self, event=None):
    """Aktualizuje etykietę pokazującą liczbę zaznaczonych gier (nie grup)."""
    if (
        hasattr(self, "duplicate_tree")
        and self.duplicate_tree.winfo_exists()
        and hasattr(self, "duplicate_count_label")
        and self.duplicate_count_label.winfo_exists()
    ):
        try:
            selected_items = self.duplicate_tree.selection()
            game_items = [item for item in selected_items if not item.startswith("group_")]
            count = len(game_items)
            self.duplicate_count_label.config(text=f"Zaznaczono: {count} gier")
        except tk.TclError as e:
            logging.warning(
                f"Błąd TclError podczas aktualizacji licznika zaznaczenia: {e}"
            )
        except Exception:
            logging.exception(
                "Nieoczekiwany błąd podczas aktualizacji licznika zaznaczenia."
            )


def _sort_duplicate_tree(self, column_name):
    """Sortuje dane w Treeview okna duplikatów."""
    if not hasattr(self, "duplicate_tree") or not self.duplicate_tree.winfo_exists():
        return

    reverse_sort = self._duplicate_sort_rev
    if column_name == self._duplicate_sort_col:
        reverse_sort = not reverse_sort
    else:
        self._duplicate_sort_col = column_name
        reverse_sort = False
    self._duplicate_sort_rev = reverse_sort

    items_to_sort = []
    for iid in self.duplicate_tree_data:
        if not iid.startswith("group_") and iid in self.duplicate_tree_data:
            game_data = self.duplicate_tree_data[iid]
            items_to_sort.append((iid, game_data))

    key_func = None
    if column_name == "Nazwa Gry":
        key_func = lambda item: item[0].lower()
    elif column_name == "Czas Gry":
        key_func = lambda item: item[1].get("play_time", 0)
    elif column_name == "Data Dodania":
        key_func = lambda item: item[1].get("date_added", 0)
    elif column_name == "Ścieżka Pliku":
        key_func = lambda item: item[1].get("exe_path", "").lower()

    if not key_func:
        return

    items_to_sort.sort(key=key_func, reverse=reverse_sort)

    for group_iid in self.duplicate_tree.get_children(""):
        group_children_iids = self.duplicate_tree.get_children(group_iid)
        sorted_children_in_group = [
            item[0] for item in items_to_sort if item[0] in group_children_iids
        ]
        for i, child_iid in enumerate(sorted_children_in_group):
            self.duplicate_tree.move(child_iid, group_iid, i)

    for col in self.duplicate_tree["columns"]:
        text = col
        if col == column_name:
            text += " ▲" if not reverse_sort else " ▼"
        self.duplicate_tree.heading(col, text=text)


def _open_selected_duplicate_location(self):
    """Otwiera folder zawierający plik .exe zaznaczonej gry."""
    selection = self.duplicate_tree.selection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz grę, której lokalizację chcesz otworzyć.",
            parent=self.root,
        )
        return
    if len(selection) > 1:
        messagebox.showwarning(
            "Wiele zaznaczonych",
            "Zaznacz tylko jedną grę, aby otworzyć jej lokalizację.",
            parent=self.root,
        )
        return

    selected_iid = selection[0]
    if selected_iid.startswith("group_"):
        messagebox.showwarning(
            "Zaznaczono grupę",
            "Zaznacz konkretną grę, a nie nagłówek grupy.",
            parent=self.root,
        )
        return

    game_data = self.duplicate_tree_data.get(selected_iid)
    if not game_data:
        messagebox.showerror(
            "Błąd",
            f"Nie znaleziono danych dla gry: {selected_iid}",
            parent=self.root,
        )
        return

    exe_path = game_data.get("exe_path")
    if not exe_path or not os.path.exists(exe_path):
        messagebox.showerror(
            "Brak ścieżki",
            f"Nie można zlokalizować pliku wykonywalnego dla gry: {selected_iid}\nŚcieżka: {exe_path}",
            parent=self.root,
        )
        return

    folder_path = os.path.dirname(exe_path)
    try:
        if sys.platform == "win32":
            os.startfile(os.path.normpath(folder_path))
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path])
        else:
            subprocess.run(["xdg-open", folder_path])
        logging.info(f"Otwieranie folderu: {folder_path}")
    except Exception as e:
        logging.error(f"Nie można otworzyć folderu '{folder_path}': {e}")
        messagebox.showerror(
            "Błąd",
            f"Nie można otworzyć folderu:\n{folder_path}\n\nBłąd: {e}",
            parent=self.root,
        )


__all__ = [
    "_normalize_game_name_for_duplicates",
    "start_duplicate_scan_thread",
    "find_potential_duplicates",
    "show_duplicate_results",
    "_update_duplicate_selection_count",
    "_sort_duplicate_tree",
    "_open_selected_duplicate_location",
]
