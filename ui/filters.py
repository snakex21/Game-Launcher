import datetime
import logging
import random
import re
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from tkcalendar import DateEntry

from launcher.utils import THEMES, save_config


class AdvancedFilterManager(tk.Toplevel):
    """Okno do zarzadzania zapisanymi filtrami zaawansowanymi."""

    def __init__(self, parent, launcher_instance):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.config = self.launcher.config

        self.title("Zarządzaj Filtrami Zaawansowanymi")
        self.configure(bg="#1e1e1e")
        self.geometry("500x400")
        self.minsize(400, 300)
        self.grab_set()
        self.transient(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Zapisane Filtry:", font=("Helvetica", 12, "bold")).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )

        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.filters_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.filters_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.filters_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.filters_listbox.config(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(row=2, column=0, pady=10)

        ttk.Button(buttons_frame, text="Dodaj Filtr", command=self._add_filter).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            buttons_frame, text="Edytuj Zaznaczony", command=self._edit_filter
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            buttons_frame, text="Usuń Zaznaczony", command=self._delete_filter
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Zamknij", command=self.destroy).pack(
            side=tk.LEFT, padx=5
        )

        self._load_filters()

    def _load_filters(self):
        self.filters_listbox.delete(0, tk.END)
        saved_filters = self.config.get("saved_filters", {})
        for filter_name in sorted(saved_filters.keys(), key=str.lower):
            self.filters_listbox.insert(tk.END, filter_name)

    def _add_filter(self):
        editor = FilterEditorWindow(self, self.launcher)
        if editor.result:
            filter_name = editor.result["name"]
            filter_rules = editor.result["rules"]
            self.config.setdefault("saved_filters", {})[filter_name] = {
                "name": filter_name,
                "rules": filter_rules,
            }
            save_config(self.config)
            self._load_filters()
            self.launcher.update_filter_group_menu()

    def _edit_filter(self):
        selection = self.filters_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia", "Zaznacz filtr, który chcesz edytować.", parent=self
            )
            return
        filter_name = self.filters_listbox.get(selection[0])
        filter_data = self.config.get("saved_filters", {}).get(filter_name)
        if not filter_data:
            messagebox.showerror(
                "Błąd",
                f"Nie znaleziono danych dla filtra '{filter_name}'.",
                parent=self,
            )
            self._load_filters()
            return

        editor = FilterEditorWindow(self, self.launcher, filter_data)
        if editor.result:
            new_filter_name = editor.result["name"]
            new_filter_rules = editor.result["rules"]
            saved_filters_dict = self.config.setdefault("saved_filters", {})

            if new_filter_name != filter_name and filter_name in saved_filters_dict:
                del saved_filters_dict[filter_name]

            saved_filters_dict[new_filter_name] = {
                "name": new_filter_name,
                "rules": new_filter_rules,
            }
            save_config(self.config)
            self._load_filters()
            self.launcher.update_filter_group_menu()

    def _delete_filter(self):
        selection = self.filters_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia", "Zaznacz filtr, który chcesz usunąć.", parent=self
            )
            return
        filter_name = self.filters_listbox.get(selection[0])

        if messagebox.askyesno(
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć filtr zaawansowany '{filter_name}'?",
            parent=self,
        ):
            saved_filters = self.config.get("saved_filters", {})
            if filter_name in saved_filters:
                del saved_filters[filter_name]
                save_config(self.config)
                self._load_filters()
                self.launcher.update_filter_group_menu()
                logging.info(f"Usunięto filtr zaawansowany: {filter_name}")
            else:
                messagebox.showerror(
                    "Błąd",
                    f"Nie znaleziono filtra '{filter_name}' do usunięcia.",
                    parent=self,
                )


class FilterEditorWindow(tk.Toplevel):
    """Okno do tworzenia i edycji reguł filtra zaawansowanego."""

    def __init__(self, parent, launcher_instance, filter_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None

        is_edit = filter_data is not None
        title = "Edytuj Filtr Zaawansowany" if is_edit else "Nowy Filtr Zaawansowany"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.geometry("750x550")
        self.minsize(600, 400)
        self.grab_set()
        self.transient(parent)

        self.filter_name = tk.StringVar(
            value=filter_data.get("name", "Nowy Filtr") if is_edit else "Nowy Filtr"
        )
        self.rules = filter_data.get("rules", []).copy() if is_edit else []
        self.original_filter_name = filter_data.get("name") if is_edit else None

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Nazwa Filtra:").grid(row=0, column=0, padx=(0, 5))
        name_entry = ttk.Entry(name_frame, textvariable=self.filter_name, width=40)
        name_entry.grid(row=0, column=1, sticky="ew")

        rule_buttons_frame = ttk.Frame(main_frame)
        rule_buttons_frame.grid(row=1, column=0, sticky="w", pady=5)
        ttk.Button(
            rule_buttons_frame, text="Dodaj Regułę", command=self._add_edit_rule
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            rule_buttons_frame,
            text="Edytuj Regułę",
            command=lambda: self._add_edit_rule(edit_mode=True),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            rule_buttons_frame, text="Usuń Regułę", command=self._delete_rule
        ).pack(side=tk.LEFT, padx=5)

        rules_list_frame = ttk.Frame(main_frame)
        rules_list_frame.grid(row=2, column=0, sticky="nsew")
        rules_list_frame.columnconfigure(0, weight=1)
        rules_list_frame.rowconfigure(0, weight=1)

        rule_cols = ("Pole", "Operator", "Wartość")
        self.rules_tree = ttk.Treeview(
            rules_list_frame,
            columns=rule_cols,
            show="headings",
            height=10,
            selectmode="browse",
        )
        self.rules_tree.heading("Pole", text="Filtrowane Pole")
        self.rules_tree.heading("Operator", text="Warunek")
        self.rules_tree.heading("Wartość", text="Wartość/Cel")
        self.rules_tree.column("Pole", width=150, anchor=tk.W)
        self.rules_tree.column("Operator", width=150, anchor=tk.W)
        self.rules_tree.column("Wartość", width=250, anchor=tk.W)

        rules_scrollbar = ttk.Scrollbar(
            rules_list_frame, orient="vertical", command=self.rules_tree.yview
        )
        self.rules_tree.configure(yscrollcommand=rules_scrollbar.set)

        self.rules_tree.grid(row=0, column=0, sticky="nsew")
        rules_scrollbar.grid(row=0, column=1, sticky="ns")

        self._populate_rules_tree()

        bottom_buttons_frame = ttk.Frame(main_frame)
        bottom_buttons_frame.grid(row=3, column=0, sticky="e", pady=(10, 0))
        ttk.Button(
            bottom_buttons_frame, text="Zapisz Filtr", command=self._save_filter
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_buttons_frame, text="Anuluj", command=self.destroy).pack(
            side=tk.LEFT, padx=5
        )

        name_entry.focus_set()
        self.wait_window(self)

    def _populate_rules_tree(self):
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        for idx, rule in enumerate(self.rules):
            field = rule.get("field", "?")
            op = rule.get("operator", "?")
            val = rule.get("value", "?")
            self.rules_tree.insert("", "end", iid=str(idx), values=(field, op, val))

    def _add_edit_rule(self, edit_mode=False):
        initial_rule_data = None
        rule_index = -1

        if edit_mode:
            selection = self.rules_tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Brak zaznaczenia",
                    "Zaznacz regułę, którą chcesz edytować.",
                    parent=self,
                )
                return
            try:
                rule_index = int(selection[0])
                initial_rule_data = self.rules[rule_index].copy()
            except (ValueError, IndexError):
                messagebox.showerror(
                    "Błąd", "Nie można odczytać danych wybranej reguły.", parent=self
                )
                return

        dialog = RuleEditor(self, self.launcher, initial_rule_data)

        if dialog.result:
            new_rule_data = dialog.result
            if edit_mode and rule_index >= 0:
                self.rules[rule_index] = new_rule_data
            else:
                self.rules.append(new_rule_data)
            self._populate_rules_tree()

    def _delete_rule(self):
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia", "Zaznacz regułę, którą chcesz usunąć.", parent=self
            )
            return
        try:
            rule_index = int(selection[0])
            rule_values = self.rules_tree.item(selection[0], "values")
            rule_desc = f"{rule_values[0]} {rule_values[1]} {rule_values[2]}"

            if messagebox.askyesno(
                "Potwierdź usunięcie",
                f"Czy na pewno chcesz usunąć regułę:\n'{rule_desc}'?",
                parent=self,
            ):
                if 0 <= rule_index < len(self.rules):
                    del self.rules[rule_index]
                    self._populate_rules_tree()
                else:
                    messagebox.showerror(
                        "Błąd", "Nie można znaleźć reguły do usunięcia.", parent=self
                    )
        except (ValueError, IndexError):
            messagebox.showerror(
                "Błąd", "Nie można zidentyfikować wybranej reguły.", parent=self
            )

    def _save_filter(self):
        new_name = self.filter_name.get().strip()
        if not new_name:
            messagebox.showerror(
                "Brak Nazwy", "Nazwa filtra nie może być pusta.", parent=self
            )
            return
        if new_name == "Wszystkie Gry" or new_name.startswith("---"):
            messagebox.showerror(
                "Błąd Nazwy",
                f"Nazwa filtra '{new_name}' jest zarezerwowana.",
                parent=self,
            )
            return

        all_filter_names = list(self.launcher.config.get("saved_filters", {}).keys())
        all_group_names = list(self.launcher.groups.keys())

        if new_name != self.original_filter_name:
            if new_name in all_group_names:
                messagebox.showerror(
                    "Konflikt Nazw",
                    f"Istnieje już grupa statyczna o nazwie '{new_name}'.",
                    parent=self,
                )
                return
            if new_name in all_filter_names:
                messagebox.showerror(
                    "Konflikt Nazw",
                    f"Istnieje już inny filtr zaawansowany o nazwie '{new_name}'.",
                    parent=self,
                )
                return

        if not self.rules:
            messagebox.showwarning(
                "Brak Reguł",
                "Filtr musi zawierać przynajmniej jedną regułę.",
                parent=self,
            )
            return

        self.result = {"name": new_name, "rules": self.rules}
        self.destroy()


class RuleEditor(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji pojedynczej reguły filtra."""

    def __init__(self, parent, launcher_instance, initial_rule_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None

        is_edit = initial_rule_data is not None
        title = "Edytuj Regułę Filtra" if is_edit else "Dodaj Regułę Filtra"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        self.FIELDS = {
            "Nazwa Gry": {"type": "text", "db_field": "name"},
            "Gatunek": {"type": "list", "db_field": "genres"},
            "Tag": {"type": "list", "db_field": "tags"},
            "Ocena": {"type": "number", "db_field": "rating"},
            "Czas Gry (godz.)": {"type": "number", "db_field": "play_time"},
            "Data Dodania": {"type": "date", "db_field": "date_added"},
            "Data Ost. Gry": {"type": "date", "db_field": "last_played"},
            "Typ Gry": {
                "type": "choice",
                "db_field": "game_type",
                "choices": ["pc", "emulator"],
            },
            "Emulator": {
                "type": "choice",
                "db_field": "emulator_name",
                "choices": list(self.launcher.config.get("emulators", {}).keys()),
            },
            "Ukończenie (%)": {"type": "number", "db_field": "completion"},
        }
        self.OPERATORS = {
            "text": [
                "zawiera",
                "nie zawiera",
                "równa się",
                "zaczyna się od",
                "kończy się na",
            ],
            "list": ["zawiera", "nie zawiera"],
            "number": [
                "==",
                "!=",
                ">",
                "<",
                ">=",
                "<=",
                "jest ustawione",
                "nie jest ustawione",
            ],
            "date": [
                "jest równe",
                "jest przed",
                "jest po",
                "jest ustawione",
                "nie jest ustawione",
            ],
            "choice": ["jest", "nie jest"],
        }
        self.FIELD_NAME_TO_KEY = {
            name: data["db_field"] for name, data in self.FIELDS.items()
        }
        self.FIELD_KEY_TO_NAME = {
            data["db_field"]: name for name, data in self.FIELDS.items()
        }

        self.field_display_var = tk.StringVar()
        self.operator_var = tk.StringVar()
        self.value_var = tk.StringVar()
        self.value_date_var = tk.StringVar()

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Filtruj według pola:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        field_names = sorted(list(self.FIELDS.keys()))
        self.field_combo = ttk.Combobox(
            main_frame,
            textvariable=self.field_display_var,
            values=field_names,
            state="readonly",
        )
        self.field_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.field_combo.bind(
            "<<ComboboxSelected>>", self._update_operator_and_value_widgets
        )

        ttk.Label(main_frame, text="Warunek:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.operator_combo = ttk.Combobox(
            main_frame, textvariable=self.operator_var, state="readonly"
        )
        self.operator_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.operator_combo.bind(
            "<<ComboboxSelected>>", self._update_value_widget_visibility
        )

        ttk.Label(main_frame, text="Wartość:").grid(
            row=2, column=0, padx=5, pady=5, sticky="nw"
        )
        self.value_widget_frame = ttk.Frame(main_frame)
        self.value_widget_frame.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.value_widget_frame.columnconfigure(0, weight=1)
        self.value_entry = ttk.Entry(
            self.value_widget_frame, textvariable=self.value_var
        )
        self.value_date_entry = DateEntry(
            self.value_widget_frame,
            textvariable=self.value_date_var,
            date_pattern="yyyy-mm-dd",
            state="readonly",
        )
        self.value_choice_combo = ttk.Combobox(
            self.value_widget_frame, textvariable=self.value_var, state="readonly"
        )

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="Zapisz Regułę", command=self._save_rule).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(
            side=tk.LEFT, padx=10
        )

        if is_edit and initial_rule_data:
            field_key = initial_rule_data.get("field")
            field_name = self.FIELD_KEY_TO_NAME.get(field_key, field_names[0])
            self.field_display_var.set(field_name)
            self._update_operator_and_value_widgets()
            self.operator_var.set(initial_rule_data.get("operator", ""))
            value = initial_rule_data.get("value")
            field_type = self.FIELDS.get(field_name, {}).get("type")
            if field_type == "date":
                try:
                    datetime.datetime.strptime(str(value), "%Y-%m-%d")
                    self.value_date_var.set(value)
                except (ValueError, TypeError):
                    self.value_date_var.set("")
            else:
                self.value_var.set(str(value) if value is not None else "")

            self._update_value_widget_visibility()

        else:
            self.field_display_var.set(field_names[0])
            self._update_operator_and_value_widgets()

        self.field_combo.focus_set()
        self.wait_window(self)

    def _update_operator_and_value_widgets(self, event=None):
        selected_field_name = self.field_display_var.get()
        field_info = self.FIELDS.get(selected_field_name, {})
        field_type = field_info.get("type")

        available_operators = self.OPERATORS.get(field_type, [])
        self.operator_combo["values"] = available_operators
        if available_operators:
            if self.operator_var.get() not in available_operators:
                self.operator_var.set(available_operators[0])
        else:
            self.operator_var.set("")

        self._update_value_widget_visibility()

    def _update_value_widget_visibility(self, event=None):
        operator = self.operator_var.get()
        selected_field_name = self.field_display_var.get()
        field_type = self.FIELDS.get(selected_field_name, {}).get("type")

        self.value_entry.grid_remove()
        self.value_date_entry.grid_remove()
        self.value_choice_combo.grid_remove()

        if operator not in ["jest ustawione", "nie jest ustawione"]:
            if field_type == "date":
                self.value_date_entry.grid(row=0, column=0, sticky="ew")
            elif field_type == "choice":
                db_field = self.FIELDS[selected_field_name]["db_field"]
                choices = self.FIELDS[selected_field_name].get("choices", [])
                if db_field == "emulator_name":
                    choices = list(self.launcher.config.get("emulators", {}).keys())
                self.value_choice_combo["values"] = choices
                if choices and self.value_var.get() not in choices:
                    self.value_var.set(choices[0])
                elif not choices:
                    self.value_var.set("")
                    self.value_choice_combo.config(state="disabled")
                else:
                    self.value_choice_combo.config(state="readonly")
                self.value_choice_combo.grid(row=0, column=0, sticky="ew")
            elif field_type == "list":
                self.value_entry.grid(row=0, column=0, sticky="ew")
            else:
                self.value_entry.grid(row=0, column=0, sticky="ew")

    def _save_rule(self):
        field_name = self.field_display_var.get()
        operator = self.operator_var.get()
        field_key = self.FIELD_NAME_TO_KEY.get(field_name)
        field_type = self.FIELDS.get(field_name, {}).get("type")
        value = None

        if not field_key or not operator:
            messagebox.showerror("Błąd", "Wybierz pole i warunek.", parent=self)
            return

        if operator not in ["jest ustawione", "nie jest ustawione"]:
            if field_type == "date":
                value_str = self.value_date_var.get()
                try:
                    datetime.datetime.strptime(value_str, "%Y-%m-%d")
                    value = value_str
                except ValueError:
                    messagebox.showerror(
                        "Błąd Formatu",
                        "Wprowadź datę w formacie RRRR-MM-DD.",
                        parent=self,
                    )
                    return
            elif field_type == "choice":
                value = self.value_var.get()
                if not value:
                    messagebox.showerror(
                        "Błąd", f"Wybierz wartość dla pola '{field_name}'.", parent=self
                    )
                    return
            elif field_type == "number":
                value_str = self.value_entry.get().strip()
                try:
                    if field_key in ["play_time", "rating", "completion"]:
                        value = float(value_str)
                    else:
                        value = int(value_str)
                except ValueError:
                    messagebox.showerror(
                        "Błąd Wartości",
                        f"Wartość dla pola '{field_name}' musi być liczbą.",
                        parent=self,
                    )
                    return
            else:
                value = self.value_entry.get().strip()
                if not value:
                    messagebox.showerror(
                        "Błąd",
                        "Wartość nie może być pusta dla tego warunku.",
                        parent=self,
                    )
                    return

        self.result = {"field": field_key, "operator": operator, "value": value}
        self.destroy()


class ThemeEditorWindow(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji niestandardowego motywu."""

    def __init__(self, parent, launcher_instance, theme_name=None, theme_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None
        self.original_name = theme_name

        self.original_scrollbar_settings = {}
        try:
            active_theme_name_main = self.launcher.settings.get("theme", "Dark")
            all_themes_main = self.launcher.get_all_available_themes()
            active_theme_def_main = all_themes_main.get(
                active_theme_name_main, THEMES.get("Dark", {})
            )

            self.original_scrollbar_settings["background"] = active_theme_def_main.get(
                "scrollbar_slider", "#555555"
            )
            self.original_scrollbar_settings["troughcolor"] = active_theme_def_main.get(
                "scrollbar_trough", "#1e1e1e"
            )
            self.original_scrollbar_settings["bordercolor"] = active_theme_def_main.get(
                "background", "#1e1e1e"
            )
            self.original_scrollbar_settings["arrowcolor"] = active_theme_def_main.get(
                "foreground", "white"
            )
            logging.debug(
                f"Zapisano oryginalne ustawienia TScrollbar: {self.original_scrollbar_settings}"
            )
        except Exception as e:
            logging.error(
                f"Błąd przy zapisywaniu oryginalnych ustawień TScrollbar: {e}"
            )

        is_edit = theme_name is not None and theme_data is not None
        title = f"Edytuj Motyw: {theme_name}" if is_edit else "Dodaj Nowy Motyw"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.geometry("550x840")
        self.minsize(500, 750)
        self.grab_set()
        self.transient(parent)

        self.COLOR_KEY_TRANSLATIONS = {
            "background": "Tło Główne",
            "foreground": "Tekst Główny",
            "button_background": "Tło Przycisku",
            "button_foreground": "Tekst Przycisku",
            "entry_background": "Tło Pola Tekst.",
            "tree_background": "Tło Listy/Drzewa",
            "tree_heading": "Nagłówek Listy",
            "scrollbar_trough": "Tło Paska Przew.",
            "scrollbar_slider": "Suwak Paska Przew.",
            "link_foreground": "Kolor Linku",
            "chart_bar_color": "Kolor Słupków Wykresu",
            "chart_axis_color": "Kolor Osi Wykresu",
        }

        active_theme_name = self.launcher.settings.get("theme", "Dark")
        all_themes = self.launcher.get_all_available_themes()
        active_theme_def = all_themes.get(active_theme_name, THEMES.get("Dark", {}))
        active_entry_bg_color = active_theme_def.get("entry_background", "#2e2e2e")
        hardcoded_fg_color = "#ffffff"

        self.hex_entry_style_name = f"HexInput{id(self)}.TEntry"
        style = ttk.Style()
        style.configure(
            self.hex_entry_style_name,
            fieldbackground=active_entry_bg_color,
            foreground=hardcoded_fg_color,
            insertcolor=hardcoded_fg_color,
        )

        content_container = ttk.Frame(self, style="TFrame")
        content_container.pack(fill="both", expand=True, padx=5, pady=5)
        content_container.rowconfigure(1, weight=0)
        content_container.rowconfigure(2, weight=1)
        content_container.columnconfigure(0, weight=1)

        name_frame = ttk.Frame(content_container, style="TFrame")
        name_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Nazwa Motywu:").grid(row=0, column=0, padx=5)
        self.name_var = tk.StringVar(value=theme_name if is_edit else "Mój Motyw")
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew")

        scrollable_frame = ttk.Frame(content_container, style="TFrame")
        scrollable_frame.grid(row=1, column=0, sticky="nsew")

        self.color_vars = {}
        template_theme = THEMES.get("Dark", {})
        current_theme_data = theme_data if is_edit else template_theme
        colors_frame = ttk.LabelFrame(
            scrollable_frame, text=" Kolory (format HEX: #RRGGBB) ", padding=10
        )
        colors_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        colors_frame.columnconfigure(1, weight=1)
        colors_frame.columnconfigure(2, weight=0)

        row_idx = 0
        for key in template_theme.keys():
            display_name = self.COLOR_KEY_TRANSLATIONS.get(key, key)
            ttk.Label(colors_frame, text=f"{display_name}:").grid(
                row=row_idx, column=0, padx=5, pady=3, sticky="w"
            )

            default_color = template_theme.get(key, "#ffffff")
            initial_value_raw = current_theme_data.get(key, default_color)
            initial_value = (
                "#ffffff" if initial_value_raw == "white" else initial_value_raw
            )

            color_var = tk.StringVar(value=initial_value)
            color_entry = ttk.Entry(
                colors_frame,
                textvariable=color_var,
                width=10,
                style=self.hex_entry_style_name,
            )
            color_entry.grid(row=row_idx, column=1, padx=5, pady=3, sticky="ew")

            color_button = tk.Button(
                colors_frame,
                text=" ",
                bg=initial_value,
                width=3,
                relief="solid",
                borderwidth=1,
                command=lambda k=key, var=color_var, dn=display_name: self._choose_color(
                    k, var, dn
                ),
            )
            color_button.grid(row=row_idx, column=2, padx=5, pady=3)

            color_var.trace_add(
                "write",
                lambda name, index, mode, var=color_var, button=color_button: self._update_color_preview(
                    var, button
                ),
            )
            self.color_vars[key] = {
                "var": color_var,
                "entry": color_entry,
                "button": color_button,
                "display_name": display_name,
            }
            row_idx += 1

        randomize_btn = ttk.Button(
            colors_frame, text="Losuj Wszystkie", command=self._randomize_colors
        )
        randomize_btn.grid(row=row_idx, column=0, columnspan=3, pady=10, sticky="ew")

        self.preview_frame = ttk.LabelFrame(
            content_container, text=" Podgląd na Żywo ", padding=10
        )
        self.preview_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.columnconfigure(2, weight=0)

        self.preview_style_prefix = f"Preview{id(self)}."
        self.preview_label = ttk.Label(
            self.preview_frame,
            text="Przykładowa etykieta",
            style=self.preview_style_prefix + "TLabel",
        )
        self.preview_label.grid(row=0, column=0, pady=3, sticky="w")
        self.preview_button = ttk.Button(
            self.preview_frame,
            text="Przycisk",
            style=self.preview_style_prefix + "TButton",
        )
        self.preview_button.grid(row=1, column=0, pady=3, sticky="w")
        self.preview_entry = ttk.Entry(
            self.preview_frame, style=self.preview_style_prefix + "TEntry"
        )
        self.preview_entry.insert(0, "Pole tekstowe")
        self.preview_entry.grid(row=2, column=0, pady=3, sticky="ew")
        self.preview_link = ttk.Button(
            self.preview_frame,
            text="Link",
            style=self.preview_style_prefix + "Link.TButton",
        )
        self.preview_link.grid(row=0, column=1, pady=3, padx=10, sticky="w")

        preview_tree_frame = ttk.Frame(self.preview_frame)
        preview_tree_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        preview_tree_frame.columnconfigure(0, weight=1)
        self.preview_tree = ttk.Treeview(
            preview_tree_frame,
            columns=("col1",),
            height=2,
            style=self.preview_style_prefix + "Treeview",
        )
        self.preview_tree.heading("col1", text="Nagłówek")
        self.preview_tree.column("col1", width=100)
        self.preview_tree.insert("", "end", text="Item 1", values=("Wartość 1",))
        self.preview_tree.insert("", "end", text="Item 2", values=("Wartość 2",))
        self.preview_tree.grid(row=0, column=0, sticky="ew")

        self.preview_scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical")
        self.preview_scrollbar.grid(row=3, column=2, pady=5, padx=(2, 0), sticky="ns")

        button_frame = ttk.Frame(self, style="TFrame")
        button_frame.pack(fill="x", pady=10, side="bottom")
        button_frame.columnconfigure((0, 1), weight=1)
        save_btn = ttk.Button(button_frame, text="Zapisz Motyw", command=self._save)
        save_btn.grid(row=0, column=0, padx=10, sticky="e")
        cancel_btn = ttk.Button(
            button_frame, text="Anuluj", command=self._on_close_editor
        )
        cancel_btn.grid(row=0, column=1, padx=10, sticky="w")

        self.protocol("WM_DELETE_WINDOW", self._on_close_editor)

        self.name_entry.focus_set()
        self._apply_preview_styles()
        self.wait_window(self)

    def _apply_preview_styles(self):
        """Odczytuje kolory z pól i aktualizuje style widgetów podglądu."""
        preview_style = ttk.Style()
        theme = {}
        valid_theme = True
        for key, data in self.color_vars.items():
            color_code = data["var"].get().strip()
            if self._is_valid_hex_color(color_code):
                theme[key] = color_code
            else:
                theme[key] = THEMES["Dark"].get(key, "#ffffff")
                valid_theme = False

        if not valid_theme:
            logging.warning(
                "Wykryto nieprawidłowe kody HEX w edytorze motywów. Podgląd używa częściowo domyślnych wartości."
            )

        prefix = self.preview_style_prefix

        try:
            preview_style.configure(
                prefix + "TLabel",
                background=theme.get("background", "#1e1e1e"),
                foreground=theme.get("foreground", "white"),
            )
            self.preview_label.configure(style=prefix + "TLabel")
            preview_style.configure(
                prefix + "TButton",
                background=theme.get("button_background", "#2e2e2e"),
                foreground=theme.get("button_foreground", "white"),
            )
            self.preview_button.configure(style=prefix + "TButton")
            preview_style.configure(
                prefix + "TEntry",
                fieldbackground=theme.get("entry_background", "#2e2e2e"),
                foreground=theme.get("foreground", "white"),
                insertbackground=theme.get("foreground", "white"),
            )
            self.preview_entry.configure(style=prefix + "TEntry")
            preview_style.configure(
                prefix + "Link.TButton",
                foreground=theme.get("link_foreground", "#66b3ff"),
                background=theme.get("background", "#1e1e1e"),
                padding=0,
                relief="flat",
                borderwidth=0,
            )
            preview_style.map(prefix + "Link.TButton", underline=[("active", 1)])
            self.preview_link.configure(style=prefix + "Link.TButton")

            preview_style.configure(
                prefix + "Treeview",
                background=theme.get("tree_background", "#2e2e2e"),
                foreground=theme.get("foreground", "white"),
                fieldbackground=theme.get("tree_background", "#2e2e2e"),
            )
            preview_style.map(prefix + "Treeview", background=[("selected", "#0078d7")])
            preview_style.configure(
                prefix + "Treeview.Heading",
                background=theme.get("tree_heading", "#3e3e3e"),
                foreground=theme.get("foreground", "white"),
            )
            self.preview_tree.configure(style=prefix + "Treeview")

            preview_style.configure(
                "TScrollbar",
                background=theme.get("scrollbar_slider", "#555555"),
                troughcolor=theme.get("scrollbar_trough", "#1e1e1e"),
                bordercolor=theme.get("background", "#1e1e1e"),
                arrowcolor=theme.get("foreground", "white"),
            )

            self.preview_frame.config(style="TFrame")

        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas stosowania stylów podglądu: {e}")
        except Exception:
            logging.exception("Nieoczekiwany błąd podczas stosowania stylów podglądu.")

    def _randomize_colors(self):
        """Generuje losowe kolory HEX dla wszystkich pól motywu."""
        logging.info("Losowanie kolorów motywu...")
        for key, data in self.color_vars.items():
            random_hex = "".join([random.choice("0123456789abcdef") for _ in range(6)])
            random_color_code = f"#{random_hex}"
            data["var"].set(random_color_code)
        messagebox.showinfo(
            "Losowanie Zakończone",
            "Kolory zostały wylosowane! Sprawdź podgląd.",
            parent=self,
        )

    def _update_color_preview(self, color_var, color_button):
        """Aktualizuje kolor tła przycisku podglądu i odświeża cały podgląd."""
        color_code = color_var.get()
        is_valid = self._is_valid_hex_color(color_code)

        try:
            color_button.config(bg=color_code if is_valid else "SystemButtonFace")
        except tk.TclError:
            color_button.config(bg="SystemButtonFace")

        self._apply_preview_styles()

    def _is_valid_hex_color(self, color_code):
        """Sprawdza prostym regexem, czy string to poprawny kod HEX."""
        return re.match(r"^#[0-9a-fA-F]{6}$", color_code)

    def _choose_color(self, key, color_var, display_name):
        """Otwiera systemowy selektor kolorów i aktualizuje zmienną oraz przycisk."""
        current_color = color_var.get()
        color_info = colorchooser.askcolor(
            initialcolor=current_color,
            title=f"Wybierz kolor dla: {display_name}",
            parent=self,
        )

        chosen_color_hex = color_info[1]

        if chosen_color_hex:
            logging.debug(f"Wybrano kolor dla '{key}': {chosen_color_hex}")
            color_var.set(chosen_color_hex)
        else:
            logging.debug(f"Anulowano wybór koloru dla '{key}'.")

    def _save(self):
        """Waliduje dane i zapisuje wynik."""
        new_name = self.name_var.get().strip()
        if not new_name:
            messagebox.showerror(
                "Błąd", "Nazwa motywu nie może być pusta.", parent=self
            )
            return

        all_builtin_themes = list(THEMES.keys())
        all_custom_themes = list(
            self.launcher.config.get("settings", {}).get("custom_themes", {}).keys()
        )

        if new_name in all_builtin_themes:
            messagebox.showerror(
                "Błąd Nazwy",
                f"Nazwa '{new_name}' jest zarezerwowana dla motywu wbudowanego.",
                parent=self,
            )
            return
        if new_name != self.original_name and new_name in all_custom_themes:
            messagebox.showerror(
                "Błąd Nazwy",
                f"Motyw niestandardowy o nazwie '{new_name}' już istnieje.",
                parent=self,
            )
            return

        theme_def = {}
        has_error = False
        for key, data in self.color_vars.items():
            color_code = data["var"].get().strip()
            if self._is_valid_hex_color(color_code):
                theme_def[key] = color_code
                data["entry"].config(foreground="SystemWindowText")
            else:
                messagebox.showerror(
                    "Błąd Koloru",
                    f"Nieprawidłowy format kodu HEX dla '{key}': {color_code}\nOczekiwano formatu #RRGGBB.",
                    parent=self,
                )
                data["entry"].config(foreground="red")
                has_error = True

        if has_error:
            return

        self.result = {"name": new_name, "theme_def": theme_def}

        try:
            active_theme_name_launcher = self.launcher.settings.get("theme", "Dark")
            all_themes_launcher = self.launcher.get_all_available_themes()
            active_theme_def_launcher = all_themes_launcher.get(
                active_theme_name_launcher, THEMES.get("Dark", {})
            )

            bg_slider = active_theme_def_launcher.get("scrollbar_slider", "#555555")
            bg_trough = active_theme_def_launcher.get("scrollbar_trough", "#1e1e1e")
            bg_border = active_theme_def_launcher.get("background", "#1e1e1e")
            fg_arrow = active_theme_def_launcher.get("foreground", "white")

            main_style = ttk.Style()
            main_style.configure(
                "TScrollbar",
                background=bg_slider,
                troughcolor=bg_trough,
                bordercolor=bg_border,
                arrowcolor=fg_arrow,
            )
            logging.info(
                "Zastosowano styl TScrollbar aktywnego motywu launchera po zapisie."
            )
            self.launcher.root.update_idletasks()
        except Exception as e:
            logging.error(
                f"Błąd przy stosowaniu stylu TScrollbar aktywnego motywu po zapisie: {e}"
            )

        self.destroy()

    def _on_close_editor(self):
        """Przywraca oryginalny styl TScrollbar przed zamknięciem edytora."""
        logging.debug(
            "Zamykanie ThemeEditorWindow, przywracanie oryginalnego TScrollbar..."
        )
        try:
            main_style = ttk.Style()
            if self.original_scrollbar_settings:
                main_style.configure(
                    "TScrollbar",
                    background=self.original_scrollbar_settings.get("background"),
                    troughcolor=self.original_scrollbar_settings.get("troughcolor"),
                    bordercolor=self.original_scrollbar_settings.get("bordercolor"),
                    arrowcolor=self.original_scrollbar_settings.get("arrowcolor"),
                )
                logging.info(
                    "Przywrócono oryginalny styl TScrollbar dla głównego okna."
                )
                self.launcher.root.update_idletasks()
            else:
                logging.warning(
                    "Brak zapisanych oryginalnych ustawień TScrollbar do przywrócenia."
                )
        except Exception as e:
            logging.error(f"Błąd przy przywracaniu oryginalnego stylu TScrollbar: {e}")
        finally:
            self.destroy()


__all__ = [
    "AdvancedFilterManager",
    "FilterEditorWindow",
    "RuleEditor",
    "ThemeEditorWindow",
]
