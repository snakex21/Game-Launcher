import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from launcher.utils import save_config


def _load_emulators_list(self):
    """Wczytuje skonfigurowane emulatory do Treeview w ustawieniach."""
    if not hasattr(self, "emulators_tree") or not self.emulators_tree.winfo_exists():
        return

    for item in self.emulators_tree.get_children():
        self.emulators_tree.delete(item)

    emulators = self.config.get("emulators", {})
    for name in sorted(emulators.keys(), key=str.lower):
        path = emulators[name].get("path", "Brak ścieżki")
        self.emulators_tree.insert("", "end", iid=name, values=(name, path))


def _add_edit_emulator(self, edit_mode=False):
    """Otwiera okno dialogowe do dodawania lub edycji konfiguracji emulatora."""
    initial_name = ""
    initial_path = ""
    original_name = None

    if edit_mode:
        selection = self.emulators_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Zaznacz emulator, który chcesz edytować.",
                parent=self.settings_page_frame,
            )
            return
        original_name = selection[0]
        emulator_data = self.config.get("emulators", {}).get(original_name)
        if not emulator_data:
            messagebox.showerror(
                "Błąd",
                f"Nie znaleziono danych dla emulatora: {original_name}",
                parent=self.settings_page_frame,
            )
            return
        initial_name = original_name
        initial_path = emulator_data.get("path", "")

    dialog = tk.Toplevel(self.settings_page_frame)
    dialog.title("Dodaj/Edytuj Emulator")
    dialog.configure(bg="#1e1e1e")
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.transient(self.settings_page_frame)

    ttk.Label(dialog, text="Nazwa Emulatora:").grid(
        row=0, column=0, padx=10, pady=5, sticky="w"
    )
    name_var = tk.StringVar(value=initial_name)
    name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
    name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

    ttk.Label(dialog, text="Ścieżka do .exe:").grid(
        row=1, column=0, padx=10, pady=5, sticky="w"
    )
    path_var = tk.StringVar(value=initial_path)
    path_entry = ttk.Entry(dialog, textvariable=path_var, width=40)
    path_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    path_btn = ttk.Button(
        dialog,
        text="Wybierz...",
        command=lambda v=path_var: self._select_emulator_exe(v, dialog),
    )
    path_btn.grid(row=1, column=2, padx=5, pady=5)

    def save_emulator():
        new_name = name_var.get().strip()
        new_path = path_var.get().strip()

        if not new_name or not new_path:
            messagebox.showerror(
                "Błąd",
                "Nazwa emulatora i ścieżka do pliku .exe są wymagane.",
                parent=dialog,
            )
            return
        if not os.path.isfile(new_path):
            messagebox.showerror(
                "Błąd",
                f"Podana ścieżka nie wskazuje na istniejący plik:\n{new_path}",
                parent=dialog,
            )
            return

        emulators = self.config.setdefault("emulators", {})

        if new_name != original_name and new_name in emulators:
            messagebox.showerror(
                "Błąd",
                f"Emulator o nazwie '{new_name}' już istnieje.",
                parent=dialog,
            )
            return

        if edit_mode and new_name != original_name and original_name in emulators:
            del emulators[original_name]

        emulators[new_name] = {"path": new_path}
        save_config(self.config)
        self._load_emulators_list()
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and hasattr(widget, "update_emulator_list"):
                widget.update_emulator_list()
        dialog.destroy()

    button_frame = ttk.Frame(dialog)
    button_frame.grid(row=2, column=0, columnspan=3, pady=15)
    ttk.Button(button_frame, text="Zapisz", command=save_emulator).pack(
        side=tk.LEFT, padx=10
    )
    ttk.Button(button_frame, text="Anuluj", command=dialog.destroy).pack(
        side=tk.LEFT, padx=10
    )

    name_entry.focus_set()


def _select_emulator_exe(self, string_var, parent_dialog):
    """Otwiera dialog wyboru pliku .exe dla emulatora."""
    path = filedialog.askopenfilename(
        title="Wybierz plik wykonywalny emulatora",
        filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
        parent=parent_dialog,
    )
    if path:
        string_var.set(path)


def _delete_emulator(self):
    """Usuwa zaznaczony emulator z konfiguracji."""
    selection = self.emulators_tree.selection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz emulator, który chcesz usunąć.",
            parent=self.settings_page_frame,
        )
        return

    emulator_name = selection[0]

    if messagebox.askyesno(
        "Potwierdź usunięcie",
        f"Czy na pewno chcesz usunąć emulator '{emulator_name}'?",
        parent=self.settings_page_frame,
    ):
        emulators = self.config.get("emulators", {})
        if emulator_name in emulators:
            del emulators[emulator_name]
            save_config(self.config)
            self._load_emulators_list()
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and hasattr(widget, "update_emulator_list"):
                    widget.update_emulator_list()
            logging.info(f"Usunięto emulator: {emulator_name}")
        else:
            messagebox.showerror(
                "Błąd",
                f"Nie znaleziono emulatora '{emulator_name}' do usunięcia.",
                parent=self.settings_page_frame,
            )


__all__ = [
    "_load_emulators_list",
    "_add_edit_emulator",
    "_select_emulator_exe",
    "_delete_emulator",
]
