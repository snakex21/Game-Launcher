import json
import logging
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from ui.filters import ThemeEditorWindow

from launcher.services.theme_store import (
    delete_custom_theme,
    get_theme_filepath,
    list_custom_theme_names,
    load_available_themes,
    load_custom_theme_by_name,
    save_custom_theme,
)
from launcher.config_store import save_local_settings
from launcher.utils import CUSTOM_THEMES_DIR, THEMES, _load_theme_from_file, save_config


def _get_custom_themes_cache(self):
    cache = getattr(self, "_custom_themes_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        self._custom_themes_cache = cache
    return cache


def _invalidate_custom_themes_cache(self):
    if hasattr(self, "_custom_themes_cache"):
        del self._custom_themes_cache


def get_all_available_themes(self):
    """Zwraca połączony słownik motywów wbudowanych i niestandardowych (ładowanych z plików)."""
    all_themes, self._custom_themes_cache = load_available_themes(
        custom_themes_dir=CUSTOM_THEMES_DIR,
        builtin_themes=THEMES,
        load_theme_from_file=_load_theme_from_file,
        custom_themes_cache=_get_custom_themes_cache(self),
    )
    return all_themes


def change_theme(self, selected_theme_name):
    all_themes = self.get_all_available_themes()
    selected_theme_def = all_themes.get(selected_theme_name)

    if not selected_theme_def:
        logging.error(
            f"Nie znaleziono definicji dla motywu: {selected_theme_name}. Używam Dark."
        )
        selected_theme_name = "Dark"
        selected_theme_def = THEMES["Dark"]

    old_theme = self.settings.get("theme")
    if old_theme != selected_theme_name:
        self.settings["theme"] = selected_theme_name
        self.user["theme_change_count"] = self.user.get("theme_change_count", 0) + 1
        logging.info(f"Licznik zmian motywu: {self.user['theme_change_count']}")
        save_config(self.config)
        self.apply_theme(selected_theme_def)
        self.check_and_unlock_achievements()


def apply_theme(self, theme_def):
    if not isinstance(theme_def, dict):
        logging.error(
            f"Błąd: apply_theme otrzymało nieprawidłowy typ danych: {type(theme_def)}. Stosuję motyw Dark."
        )
        theme_def = THEMES.get("Dark", {})

    style = ttk.Style(self.root)
    default_bg = "#1e1e1e"
    default_fg = "white"
    style.configure("TFrame", background=theme_def.get("background", default_bg))
    style.configure(
        "TLabel",
        background=theme_def.get("background", default_bg),
        foreground=theme_def.get("foreground", default_fg),
    )
    style.configure(
        "TButton",
        background=theme_def.get("button_background", default_bg),
        foreground=theme_def.get("button_foreground", default_fg),
    )
    style.configure(
        "Game.TButton",
        background=theme_def.get("background", default_bg),
        foreground=theme_def.get("foreground", default_fg),
    )
    style.configure(
        "TEntry",
        fieldbackground=theme_def.get("entry_background", default_bg),
        foreground=theme_def.get("foreground", default_fg),
        insertbackground=theme_def.get("foreground", default_fg),
    )

    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme_def.get("entry_background", default_bg))],
    )
    style.map(
        "TCombobox",
        foreground=[("readonly", theme_def.get("foreground", default_fg))],
    )
    style.map("TCombobox", selectbackground=[("readonly", "#0078d7")])
    style.map("TCombobox", selectforeground=[("readonly", "white")])
    style.configure(
        "TSpinbox",
        fieldbackground=theme_def.get("entry_background", default_bg),
        foreground=theme_def.get("foreground", default_fg),
    )
    try:
        style.configure(
            "Treeview",
            background=theme_def.get("tree_background", default_bg),
            foreground=theme_def.get("foreground", default_fg),
            fieldbackground=theme_def.get("tree_background", default_bg),
        )
        style.map("Treeview", background=[("selected", "#0078d7")])
        style.configure(
            "Treeview.Heading",
            background=theme_def.get("tree_heading", default_bg),
            foreground=theme_def.get("foreground", default_fg),
        )
    except tk.TclError as e:
        logging.warning(f"Nie można ustawić niektórych stylów Treeview: {e}")

    style.configure(
        "TScrollbar",
        background=theme_def.get("scrollbar_slider", "#555555"),
        troughcolor=theme_def.get("scrollbar_trough", default_bg),
        bordercolor=theme_def.get("background", default_bg),
        arrowcolor=theme_def.get("foreground", default_fg),
    )
    style.configure(
        "Link.TButton",
        foreground=theme_def.get("link_foreground", "#66b3ff"),
        background=theme_def.get("background", default_bg),
    )

    self.root.configure(bg=theme_def.get("background", default_bg))
    if hasattr(self, "sidebar"):
        self.sidebar.configure(style="TFrame")
    if hasattr(self, "main_frame"):
        self.main_frame.configure(style="TFrame")
    if hasattr(self, "home_frame"):
        self.home_frame.configure(style="TFrame")
    if hasattr(self, "canvas") and self.canvas.winfo_exists():
        self.canvas.config(bg=theme_def.get("background", default_bg))
    if hasattr(self, "settings_page_frame"):
        settings_canvas = (
            self.settings_page_frame.winfo_children()[0]
            if self.settings_page_frame.winfo_children()
            else None
        )
        if isinstance(settings_canvas, tk.Canvas):
            settings_canvas.config(bg=theme_def.get("background", default_bg))

    self.root.update_idletasks()
    if hasattr(self, "music_player_page_instance") and self.music_player_page_instance:
        if (
            hasattr(self.music_player_page_instance, "apply_theme_colors")
            and self.music_player_page_instance.parent_frame.winfo_exists()
        ):
            logging.debug(
                "apply_theme (GameLauncher): Wywoływanie apply_theme_colors dla MusicPlayerPage."
            )
            self.music_player_page_instance.apply_theme_colors()
        else:
            logging.debug(
                "apply_theme (GameLauncher): Instancja MusicPlayerPage istnieje, ale brakuje metody apply_theme_colors lub ramka nie istnieje."
            )
    else:
        logging.debug(
            "apply_theme (GameLauncher): Instancja MusicPlayerPage nie istnieje, nie ma czego odświeżać."
        )


def _update_main_theme_selector(self):
    """Odświeża główny OptionMenu wyboru motywu."""
    if hasattr(self, "theme_menu") and self.theme_menu.winfo_exists():
        menu = self.theme_menu["menu"]
        menu.delete(0, "end")
        all_themes = self.get_all_available_themes()
        current_theme_name = self.settings.get("theme", "Dark")

        if current_theme_name not in all_themes:
            current_theme_name = "Dark"
            self.theme_var.set(current_theme_name)
            self.settings["theme"] = current_theme_name
            save_config(self.config)

        for theme_name in sorted(all_themes.keys()):
            menu.add_command(
                label=theme_name,
                command=tk._setit(self.theme_var, theme_name, self.change_theme),
            )

        self.theme_var.set(current_theme_name)
    else:
        logging.warning("Nie można zaktualizować theme_menu - widget nie istnieje.")


def _load_custom_themes_list(self):
    """Wczytuje nazwy niestandardowych motywów (z plików) do Listboxa w ustawieniach."""
    if hasattr(self, "custom_themes_listbox") and self.custom_themes_listbox.winfo_exists():
        self.custom_themes_listbox.delete(0, tk.END)
        custom_theme_names, self._custom_themes_cache = list_custom_theme_names(
            custom_themes_dir=CUSTOM_THEMES_DIR,
            builtin_themes=THEMES,
            load_theme_from_file=_load_theme_from_file,
            custom_themes_cache=_get_custom_themes_cache(self),
        )

        for theme_name in custom_theme_names:
            self.custom_themes_listbox.insert(tk.END, theme_name)


def _add_custom_theme(self):
    """Otwiera edytor dla nowego motywu niestandardowego i zapisuje go do pliku."""
    editor = ThemeEditorWindow(self.settings_page_frame, self)
    if editor.result:
        theme_name = editor.result["name"]
        theme_def = editor.result["theme_def"]

        theme_filepath = get_theme_filepath(CUSTOM_THEMES_DIR, theme_name)

        if theme_name in THEMES:
            messagebox.showerror(
                "Błąd Nazwy",
                f"Nazwa '{theme_name}' jest zarezerwowana dla motywu wbudowanego.",
                parent=self.settings_page_frame,
            )
            return

        if os.path.exists(theme_filepath):
            logging.warning(
                f"Plik motywu '{theme_filepath}' już istnieje, może wystąpił problem z walidacją nazwy."
            )

        try:
            save_custom_theme(
                theme_name=theme_name,
                theme_definition=theme_def,
                custom_themes_dir=CUSTOM_THEMES_DIR,
            )
            logging.info(f"Zapisano nowy motyw niestandardowy do pliku: {theme_filepath}")
        except Exception as e:
            messagebox.showerror(
                "Błąd Zapisu Motywu",
                f"Nie udało się zapisać motywu '{theme_name}' do pliku:\n{e}",
                parent=self.settings_page_frame,
            )
            return

        _invalidate_custom_themes_cache(self)

        self._load_custom_themes_list()
        self._update_main_theme_selector()


def _edit_custom_theme(self):
    """Otwiera edytor dla wybranego motywu niestandardowego i aktualizuje plik."""
    if not hasattr(self, "custom_themes_listbox"):
        return
    selection = self.custom_themes_listbox.curselection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz motyw niestandardowy, który chcesz edytować.",
            parent=self.settings_page_frame,
        )
        return
    theme_name_to_edit = self.custom_themes_listbox.get(selection[0])

    filepath_to_edit = get_theme_filepath(CUSTOM_THEMES_DIR, theme_name_to_edit)

    if not os.path.exists(filepath_to_edit):
        messagebox.showerror(
            "Błąd",
            f"Nie znaleziono pliku dla motywu '{theme_name_to_edit}'. Może został usunięty lub zmieniono nazwę.",
            parent=self.settings_page_frame,
        )
        self._load_custom_themes_list()
        return

    initial_data_from_file = load_custom_theme_by_name(
        theme_name=theme_name_to_edit,
        custom_themes_dir=CUSTOM_THEMES_DIR,
        load_theme_from_file=_load_theme_from_file,
    )
    if not initial_data_from_file:
        messagebox.showerror(
            "Błąd Wczytywania",
            f"Nie można wczytać danych z pliku motywu '{theme_name_to_edit}'. Plik jest uszkodzony lub ma nieprawidłową strukturę.",
            parent=self.settings_page_frame,
        )
        self._load_custom_themes_list()
        return

    editor = ThemeEditorWindow(
        self.settings_page_frame,
        self,
        theme_name=initial_data_from_file["name"],
        theme_data=initial_data_from_file["definition"],
    )

    if editor.result:
        new_name = editor.result["name"]
        new_theme_def = editor.result["theme_def"]

        new_filepath = get_theme_filepath(CUSTOM_THEMES_DIR, new_name)

        if new_name != theme_name_to_edit:
            if new_name in THEMES:
                messagebox.showerror(
                    "Błąd Nazwy",
                    f"Nowa nazwa '{new_name}' jest zarezerwowana dla motywu wbudowanego.",
                    parent=self.settings_page_frame,
                )
                return
            if os.path.exists(new_filepath) and os.path.normcase(new_filepath) != os.path.normcase(filepath_to_edit):
                if not messagebox.askyesno(
                    "Nadpisać?",
                    f"Plik dla nowej nazwy '{new_name}' już istnieje.\nCzy chcesz go nadpisać?",
                    parent=self.settings_page_frame,
                ):
                    return

            if os.path.exists(filepath_to_edit):
                try:
                    os.remove(filepath_to_edit)
                    logging.info(f"Usunięto stary plik motywu: {filepath_to_edit}")
                except OSError as e:
                    logging.error(
                        f"Nie udało się usunąć starego pliku motywu '{filepath_to_edit}': {e}"
                    )
                    messagebox.showwarning(
                        "Błąd Usuwania",
                        f"Nie udało się usunąć starego pliku motywu:\n{e}\n\nMotyw mógł nie zostać w pełni zaktualizowany.",
                        parent=self.settings_page_frame,
                    )

        try:
            save_custom_theme(
                theme_name=new_name,
                theme_definition=new_theme_def,
                custom_themes_dir=CUSTOM_THEMES_DIR,
            )
            logging.info(
                f"Zapisano zaktualizowany motyw niestandardowy do pliku: {new_filepath}"
            )
        except Exception as e:
            messagebox.showerror(
                "Błąd Zapisu Motywu",
                f"Nie udało się zapisać zaktualizowanego motywu '{new_name}' do pliku:\n{e}",
                parent=self.settings_page_frame,
            )
            return

        _invalidate_custom_themes_cache(self)

        self._load_custom_themes_list()
        self._update_main_theme_selector()

        if self.settings.get("theme") == new_name:
            self.apply_theme(self.get_all_available_themes().get(new_name, THEMES["Dark"]))


def _delete_custom_theme(self):
    """Usuwa wybrany motyw niestandardowy (pliku)."""
    if not hasattr(self, "custom_themes_listbox"):
        return
    selection = self.custom_themes_listbox.curselection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz motyw niestandardowy, który chcesz usunąć.",
            parent=self.settings_page_frame,
        )
        return
    theme_name_to_delete = self.custom_themes_listbox.get(selection[0])

    if theme_name_to_delete in THEMES:
        messagebox.showerror(
            "Błąd",
            f"Nie można usunąć wbudowanego motywu '{theme_name_to_delete}'.",
            parent=self.settings_page_frame,
        )
        return

    if messagebox.askyesno(
        "Potwierdź usunięcie",
        f"Czy na pewno chcesz usunąć motyw niestandardowy '{theme_name_to_delete}'?\nOperacja jest nieodwracalna!",
        parent=self.settings_page_frame,
    ):
        filepath_to_delete = get_theme_filepath(CUSTOM_THEMES_DIR, theme_name_to_delete)

        try:
            deleted, _ = delete_custom_theme(
                theme_name=theme_name_to_delete,
                custom_themes_dir=CUSTOM_THEMES_DIR,
            )
        except OSError as e:
            messagebox.showerror(
                "Błąd Usuwania",
                f"Nie udało się usunąć pliku motywu '{filepath_to_delete}':\n{e}\n\nSpróbuj usunąć ręcznie.",
                parent=self.settings_page_frame,
            )
            logging.error(f"Nie udało się usunąć pliku motywu '{filepath_to_delete}': {e}")
            return

        if not deleted:
            messagebox.showerror(
                "Błąd",
                f"Nie znaleziono pliku motywu '{theme_name_to_delete}' do usunięcia. Może został usunięty ręcznie?",
                parent=self.settings_page_frame,
            )
            self._load_custom_themes_list()
            return

        logging.info(f"Usunięto plik motywu: {filepath_to_delete}")

        active_theme = self.settings.get("theme")
        theme_changed_to_default = False
        if active_theme == theme_name_to_delete:
            self.settings["theme"] = "Dark"
            active_theme = "Dark"
            theme_changed_to_default = True
            logging.info(
                f"Aktywny motyw '{theme_name_to_delete}' został usunięty. Aplikacja przełączy się na motyw 'Dark'."
            )

        save_config(self.config)

        _invalidate_custom_themes_cache(self)

        self._load_custom_themes_list()
        self._update_main_theme_selector()

        if theme_changed_to_default:
            self.apply_theme(self.get_all_available_themes().get(active_theme, THEMES["Dark"]))


def _export_custom_theme_dialog(self):
    """Otwiera dialog wyboru sposobu eksportu zaznaczonego motywu niestandardowego."""
    if not hasattr(self, "custom_themes_listbox"):
        logging.error("Listbox motywów niestandardowych nie istnieje.")
        return

    selection = self.custom_themes_listbox.curselection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz motyw niestandardowy, który chcesz wyeksportować.",
            parent=self.settings_page_frame,
        )
        return
    theme_name = self.custom_themes_listbox.get(selection[0])
    theme_data_record = load_custom_theme_by_name(
        theme_name=theme_name,
        custom_themes_dir=CUSTOM_THEMES_DIR,
        load_theme_from_file=_load_theme_from_file,
    )
    theme_data = None
    if theme_data_record:
        theme_data = theme_data_record.get("definition")

    if not theme_data:
        theme_data = self.settings.get("custom_themes", {}).get(theme_name)

    if not theme_data:
        messagebox.showerror(
            "Błąd",
            f"Nie można znaleźć danych dla motywu '{theme_name}'.",
            parent=self.settings_page_frame,
        )
        return

    export_dialog = tk.Toplevel(self.settings_page_frame)
    export_dialog.title(f"Eksportuj Motyw: {theme_name}")
    active_theme_def = self.get_all_available_themes().get(
        self.settings.get("theme", "Dark"), THEMES.get("Dark")
    )
    export_dialog.configure(bg=active_theme_def.get("background", "#1e1e1e"))
    export_dialog.geometry("300x150")
    export_dialog.grab_set()
    export_dialog.resizable(False, False)
    export_dialog.transient(self.settings_page_frame)

    ttk.Label(
        export_dialog, text="Wybierz metodę eksportu:", font=("Segoe UI", 10)
    ).pack(pady=10)

    button_frame = ttk.Frame(export_dialog)
    button_frame.pack(pady=10, fill="x", expand=True)

    def export_to_clipboard():
        try:
            theme_json_string = json.dumps(
                {"name": theme_name, "definition": theme_data},
                indent=2,
                ensure_ascii=False,
            )
            self.root.clipboard_clear()
            self.root.clipboard_append(theme_json_string)
            messagebox.showinfo(
                "Skopiowano",
                "Definicja motywu została skopiowana do schowka.",
                parent=export_dialog,
            )
            export_dialog.destroy()
        except Exception as e:
            messagebox.showerror(
                "Błąd",
                f"Nie udało się skopiować do schowka:\n{e}",
                parent=export_dialog,
            )

    def export_to_file():
        try:
            default_filename = f"{theme_name.replace(' ', '_').lower()}_theme.json"
            filepath = filedialog.asksaveasfilename(
                parent=export_dialog,
                title=f"Zapisz motyw '{theme_name}' jako...",
                initialfile=default_filename,
                defaultextension=".json",
                filetypes=[("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")],
            )
            if filepath:
                theme_to_save = {"name": theme_name, "definition": theme_data}
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(theme_to_save, f, indent=2, ensure_ascii=False)
                messagebox.showinfo(
                    "Zapisano",
                    f"Motyw został zapisany do pliku:\n{filepath}",
                    parent=export_dialog,
                )
                export_dialog.destroy()
        except Exception as e:
            messagebox.showerror(
                "Błąd Zapisu",
                f"Nie udało się zapisać motywu do pliku:\n{e}",
                parent=export_dialog,
            )

    ttk.Button(button_frame, text="Kopiuj do Schowka", command=export_to_clipboard).pack(
        pady=5, padx=20, fill="x"
    )
    ttk.Button(button_frame, text="Zapisz do Pliku...", command=export_to_file).pack(
        pady=5, padx=20, fill="x"
    )


def _import_custom_theme_dialog(self):
    """Otwiera dialog do importowania motywu z tekstu lub pliku."""
    import_dialog = tk.Toplevel(self.settings_page_frame)
    import_dialog.title("Importuj Motyw Niestandardowy")
    active_theme_def = self.get_all_available_themes().get(
        self.settings.get("theme", "Dark"), THEMES.get("Dark")
    )
    import_dialog.configure(bg=active_theme_def.get("background", "#1e1e1e"))
    import_dialog.geometry("450x350")
    import_dialog.grab_set()
    import_dialog.resizable(False, False)
    import_dialog.transient(self.settings_page_frame)

    main_import_frame = ttk.Frame(import_dialog, padding=10)
    main_import_frame.pack(fill="both", expand=True)
    main_import_frame.columnconfigure(0, weight=1)
    main_import_frame.rowconfigure(1, weight=1)

    ttk.Label(
        main_import_frame,
        text="Wklej definicję motywu (JSON) poniżej LUB wybierz plik:",
    ).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")

    text_frame = ttk.Frame(main_import_frame)
    text_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5)
    text_frame.columnconfigure(0, weight=1)
    text_frame.rowconfigure(0, weight=1)

    theme_text_widget = tk.Text(text_frame, height=10, width=50, wrap=tk.WORD)
    theme_text_widget.grid(row=0, column=0, sticky="nsew")
    theme_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=theme_text_widget.yview)
    theme_scroll.grid(row=0, column=1, sticky="ns")
    theme_text_widget.config(yscrollcommand=theme_scroll.set)

    action_button_frame = ttk.Frame(main_import_frame)
    action_button_frame.grid(row=2, column=0, columnspan=2, pady=10)

    def import_from_text():
        json_string = theme_text_widget.get("1.0", tk.END).strip()
        if not json_string:
            messagebox.showwarning(
                "Puste Pole",
                "Wklej definicję motywu w formacie JSON.",
                parent=import_dialog,
            )
            return
        self._process_theme_import(json_string, parent_window=import_dialog)

    def import_from_file():
        filepath = filedialog.askopenfilename(
            parent=import_dialog,
            title="Wybierz plik motywu JSON",
            defaultextension=".json",
            filetypes=[("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")],
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    json_string = f.read()
                self._process_theme_import(json_string, parent_window=import_dialog)
            except Exception as e:
                messagebox.showerror(
                    "Błąd Odczytu Pliku",
                    f"Nie udało się wczytać motywu z pliku:\n{e}",
                    parent=import_dialog,
                )

    ttk.Button(
        action_button_frame,
        text="Importuj z Pola Tekstowego",
        command=import_from_text,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        action_button_frame, text="Importuj z Pliku...", command=import_from_file
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(action_button_frame, text="Anuluj", command=import_dialog.destroy).pack(
        side=tk.RIGHT, padx=5
    )


def _process_theme_import(self, json_string, parent_window):
    """Przetwarza importowany string JSON motywu."""
    try:
        imported_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        messagebox.showerror(
            "Błąd Formatu JSON",
            f"Nieprawidłowy format JSON definicji motywu:\n{e}",
            parent=parent_window,
        )
        return

    if (
        not isinstance(imported_data, dict)
        or "name" not in imported_data
        or "definition" not in imported_data
    ):
        messagebox.showerror(
            "Błąd Struktury",
            "Importowany motyw musi zawierać klucze 'name' i 'definition'.",
            parent=parent_window,
        )
        return

    theme_name_imported = imported_data["name"]
    theme_def_imported = imported_data["definition"]

    if not isinstance(theme_name_imported, str) or not theme_name_imported.strip():
        messagebox.showerror(
            "Błąd Nazwy",
            "Nazwa importowanego motywu nie może być pusta.",
            parent=parent_window,
        )
        return
    if not isinstance(theme_def_imported, dict):
        messagebox.showerror(
            "Błąd Definicji",
            "Definicja kolorów motywu musi być słownikiem.",
            parent=parent_window,
        )
        return

    template_keys = THEMES.get("Dark", {}).keys()
    final_theme_def = {}
    for key in template_keys:
        if key not in theme_def_imported:
            messagebox.showwarning(
                "Brakujący Klucz",
                f"Importowany motyw nie zawiera klucza '{key}'.\nUżyto wartości domyślnej.",
                parent=parent_window,
            )
            final_theme_def[key] = THEMES["Dark"].get(key, "#ffffff")
        elif not re.match(r"^#[0-9a-fA-F]{6}$", str(theme_def_imported[key])):
            messagebox.showwarning(
                "Błędny Kolor",
                f"Nieprawidłowy format koloru HEX dla '{key}': {theme_def_imported[key]}.\nUżyto wartości domyślnej.",
                parent=parent_window,
            )
            final_theme_def[key] = THEMES["Dark"].get(key, "#ffffff")
        else:
            final_theme_def[key] = str(theme_def_imported[key])

    new_name = simpledialog.askstring(
        "Nazwa Importowanego Motywu",
        "Podaj nazwę dla importowanego motywu:",
        initialvalue=theme_name_imported,
        parent=parent_window,
    )

    if not new_name or not new_name.strip():
        messagebox.showwarning(
            "Anulowano",
            "Import motywu został anulowany (brak nazwy).",
            parent=parent_window,
        )
        return

    new_name = new_name.strip()
    if new_name in THEMES:
        messagebox.showerror(
            "Błąd Nazwy",
            f"Nazwa '{new_name}' jest zarezerwowana dla motywu wbudowanego.",
            parent=parent_window,
        )
        return

    new_filepath = get_theme_filepath(CUSTOM_THEMES_DIR, new_name)
    safe_new_filename = os.path.basename(new_filepath)

    if os.path.exists(new_filepath):
        if not messagebox.askyesno(
            "Konflikt Pliku Motywu",
            f"Plik motywu o nazwie '{safe_new_filename}' już istnieje.\nCzy chcesz go nadpisać?",
            parent=parent_window,
        ):
            return

    try:
        save_custom_theme(
            theme_name=new_name,
            theme_definition=final_theme_def,
            custom_themes_dir=CUSTOM_THEMES_DIR,
        )
        logging.info(f"Zaimportowano i zapisano motyw do pliku: {new_filepath}")
    except Exception as e:
        messagebox.showerror(
            "Błąd Zapisu",
            f"Nie udało się zapisać importowanego motywu do pliku:\n{e}",
            parent=parent_window,
        )
        return

    _invalidate_custom_themes_cache(self)

    self._load_custom_themes_list()
    self._update_main_theme_selector()

    messagebox.showinfo(
        "Import Zakończony",
        f"Motyw '{new_name}' został pomyślnie zaimportowany.",
        parent=parent_window.master,
    )
    if parent_window.winfo_exists():
        parent_window.destroy()


def _save_and_apply_font_setting(self, event=None):
    """Zapisuje wybraną czcionkę i odświeża style."""
    selected_font = self.font_var.get()
    if self.local_settings.get("ui_font") != selected_font:
        self.local_settings["ui_font"] = selected_font
        save_local_settings(self.local_settings)
        logging.info(f"Zmieniono czcionkę interfejsu na: {selected_font}")
        self.apply_font_settings()


def apply_font_settings(self, selected_font=None):
    """Stosuje wybraną czcionkę do stylów ttk."""
    if selected_font is None:
        selected_font = self.local_settings.get("ui_font", "Segoe UI")

    style = ttk.Style(self.root)
    default_size = 9
    heading_size = 10
    bold_font = (selected_font, heading_size, "bold")
    normal_font = (selected_font, default_size)
    small_font = (selected_font, max(7, default_size - 1))

    try:
        style.configure("TLabel", font=normal_font)
        style.configure("TButton", font=normal_font)
        style.configure("TEntry", font=normal_font)
        style.configure("TCombobox", font=normal_font)
        style.configure("TSpinbox", font=normal_font)
        style.configure("TCheckbutton", font=normal_font)
        style.configure("TRadiobutton", font=normal_font)
        style.configure("TMenubutton", font=normal_font)
        style.configure("TNotebook.Tab", font=small_font)
        style.configure("Treeview.Heading", font=bold_font)
        style.configure("TLabelframe.Label", font=bold_font)
        style.configure("Tile.TButton", font=small_font)

        logging.info(f"Zastosowano czcionkę '{selected_font}' do stylów.")

    except tk.TclError as e:
        logging.error(
            f"Błąd TclError podczas stosowania czcionki '{selected_font}': {e}. Może brakować czcionki w systemie."
        )
        messagebox.showerror(
            "Błąd Czcionki",
            f"Nie można zastosować czcionki '{selected_font}'.\nSprawdź, czy jest zainstalowana.\n\nBłąd: {e}",
            parent=self.settings_page_frame,
        )
    except Exception as e:
        logging.exception(f"Nieoczekiwany błąd podczas stosowania czcionki: {e}")


__all__ = [
    "get_all_available_themes",
    "change_theme",
    "apply_theme",
    "_update_main_theme_selector",
    "_load_custom_themes_list",
    "_add_custom_theme",
    "_edit_custom_theme",
    "_delete_custom_theme",
    "_export_custom_theme_dialog",
    "_import_custom_theme_dialog",
    "_process_theme_import",
    "_save_and_apply_font_setting",
    "apply_font_settings",
]
