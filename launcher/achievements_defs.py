import json
import logging
import os
from tkinter import messagebox

from ui.dialogs import AchievementForm
from launcher.utils import ACHIEVEMENTS_DEFINITIONS_FILE


def _migrate_legacy_achievements_file():
    if os.path.exists(ACHIEVEMENTS_DEFINITIONS_FILE):
        return

    legacy_path = os.path.join(os.getcwd(), "achievements_def.json")
    if not os.path.exists(legacy_path):
        return

    target_dir = os.path.dirname(ACHIEVEMENTS_DEFINITIONS_FILE)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    try:
        os.replace(legacy_path, ACHIEVEMENTS_DEFINITIONS_FILE)
        logging.info(
            f"Zmigrowano plik definicji osiągnięć do '{ACHIEVEMENTS_DEFINITIONS_FILE}'."
        )
    except OSError as error:
        logging.warning(
            "Nie udało się zmigrować legacy achievements_def.json: "
            f"{error}. Używam starej lokalizacji."
        )


def _load_achievement_definitions(self):
    """Wczytuje definicje osiągnięć z pliku JSON."""
    _migrate_legacy_achievements_file()
    definitions_file = ACHIEVEMENTS_DEFINITIONS_FILE
    try:
        if os.path.exists(definitions_file):
            with open(definitions_file, "r", encoding="utf-8") as f:
                self.achievement_definitions = json.load(f)
                logging.info(
                    f"Załadowano {len(self.achievement_definitions)} definicji osiągnięć."
                )
        else:
            logging.warning(f"Plik definicji osiągnięć '{definitions_file}' nie znaleziony.")
            self.achievement_definitions = []
    except json.JSONDecodeError as e:
        logging.error(f"Błąd odczytu pliku definicji osiągnięć: {e}")
        messagebox.showerror(
            "Błąd Osiągnięć", f"Nie można wczytać definicji osiągnięć.\nBłąd: {e}"
        )
        self.achievement_definitions = []
    except Exception:
        logging.exception("Nieoczekiwany błąd podczas ładowania definicji osiągnięć.")
        self.achievement_definitions = []


def _load_achievement_def_list(self):
    """Wczytuje definicje osiągnięć do Treeview w Ustawieniach."""
    if not hasattr(self, "achievements_def_tree") or not self.achievements_def_tree.winfo_exists():
        return
    for item in self.achievements_def_tree.get_children():
        self.achievements_def_tree.delete(item)
    if not hasattr(self, "achievement_definitions") or not self.achievement_definitions:
        self._load_achievement_definitions()

    if not hasattr(self, "ACHIEVEMENT_RULE_TYPES_TRANSLATED"):
        self.ACHIEVEMENT_RULE_TYPES_TRANSLATED = {
            "games_launched_count": "Liczba uruchomionych gier",
            "library_size": "Rozmiar biblioteki",
            "total_playtime_hours": "Łączny czas gry (godziny)",
            "games_completed_100": "Gry ukończone w 100%",
        }

    for ach_def in self.achievement_definitions:
        ach_id = ach_def.get("id", "-")
        name = ach_def.get("name", "Brak Nazwy")
        desc = ach_def.get("description", "")
        rule_type = ach_def.get("rule_type", "N/A")
        target = ach_def.get("target_value", "-")
        condition_str = (
            f"{self.ACHIEVEMENT_RULE_TYPES_TRANSLATED.get(rule_type, rule_type)}: {target}"
        )

        self.achievements_def_tree.insert(
            "", "end", iid=ach_id, values=(ach_id, name, desc, condition_str)
        )


def _delete_achievement_def(self):
    """Usuwa zaznaczoną definicję osiągnięcia (wybraną w Ustawieniach)."""
    parent_window = self.settings_page_frame
    if not hasattr(self, "achievements_def_tree") or not self.achievements_def_tree.winfo_exists():
        messagebox.showerror(
            "Błąd",
            "Lista definicji w Ustawieniach nie jest dostępna.",
            parent=parent_window,
        )
        return
    selection = self.achievements_def_tree.selection()
    if not selection:
        messagebox.showwarning(
            "Brak zaznaczenia",
            "Zaznacz osiągnięcie na liście w Ustawieniach, które chcesz usunąć.",
            parent=parent_window,
        )
        return

    ach_id = selection[0]
    ach_name = self.achievements_def_tree.item(ach_id, "values")[1]

    if messagebox.askyesno(
        "Potwierdź usunięcie",
        f"Czy na pewno chcesz usunąć definicję osiągnięcia:\n'{ach_name}' ({ach_id})?",
        parent=parent_window,
    ):
        original_length = len(self.achievement_definitions)
        self.achievement_definitions = [
            ach for ach in self.achievement_definitions if ach.get("id") != ach_id
        ]

        if len(self.achievement_definitions) < original_length:
            if self._save_achievement_definitions_to_file():
                self._reset_single_achievement_progress(ach_id)
                self.check_and_unlock_achievements()
                logging.info(f"Usunięto definicję osiągnięcia: {ach_id}")
            else:
                self._load_achievement_definitions()
                self._load_achievement_def_list()
        else:
            messagebox.showerror(
                "Błąd",
                "Nie znaleziono osiągnięcia do usunięcia.",
                parent=parent_window,
            )


def _save_achievement_definitions_to_file(self):
    """Zapisuje aktualny stan self.achievement_definitions do pliku JSON."""
    definitions_file = ACHIEVEMENTS_DEFINITIONS_FILE
    try:
        target_dir = os.path.dirname(definitions_file)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with open(definitions_file, "w", encoding="utf-8") as f:
            json.dump(self.achievement_definitions, f, indent=2, ensure_ascii=False)
        logging.info(
            f"Zapisano {len(self.achievement_definitions)} definicji osiągnięć do pliku {definitions_file}."
        )
        return True
    except TypeError as e:
        logging.error(f"Błąd serializacji definicji osiągnięć do JSON: {e}")
        messagebox.showerror(
            "Błąd Zapisu Osiągnięć",
            f"Nie można zapisać definicji osiągnięć z powodu błędu typu danych: {e}",
            parent=self.settings_page_frame,
        )
        return False
    except Exception as e:
        logging.exception("Nieoczekiwany błąd podczas zapisu definicji osiągnięć.")
        messagebox.showerror(
            "Błąd Zapisu Osiągnięć",
            f"Wystąpił nieoczekiwany błąd podczas zapisu definicji osiągnięć: {e}",
            parent=self.settings_page_frame,
        )
        return False


def _add_edit_achievement_def(self, edit_mode=False, parent_window=None):
    """Otwiera okno dialogowe do dodawania lub edycji definicji osiągnięcia."""
    if parent_window is None:
        parent_window = self.achievements_frame

    initial_data = None
    original_id = None

    if edit_mode:
        if not hasattr(self, "achievements_def_tree") or not self.achievements_def_tree.winfo_exists():
            messagebox.showerror(
                "Błąd",
                "Lista definicji osiągnięć nie jest dostępna.",
                parent=parent_window,
            )
            return
        selection = self.achievements_def_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Zaznacz osiągnięcie na liście poniżej, które chcesz edytować.",
                parent=parent_window,
            )
            return
        original_id = selection[0]
        initial_data = next(
            (item for item in self.achievement_definitions if item.get("id") == original_id),
            None,
        )
        if not initial_data:
            messagebox.showerror(
                "Błąd",
                f"Nie znaleziono danych dla osiągnięcia o ID: {original_id}",
                parent=parent_window,
            )
            return
        initial_data = initial_data.copy()

    dialog = AchievementForm(parent_window, initial_data, launcher_instance=self)

    if dialog.result:
        new_ach_data = dialog.result
        new_id = new_ach_data.get("id")

        for existing_ach in self.achievement_definitions:
            if (
                edit_mode
                and existing_ach.get("id") == original_id
                and new_id == original_id
            ):
                continue
            if existing_ach.get("id") == new_id:
                messagebox.showerror(
                    "Błąd ID",
                    f"Osiągnięcie o ID '{new_id}' już istnieje!",
                    parent=parent_window,
                )
                return

        if edit_mode and original_id:
            found = False
            for i, ach in enumerate(self.achievement_definitions):
                if ach.get("id") == original_id:
                    self.achievement_definitions[i] = new_ach_data
                    found = True
                    break
            if not found:
                self.achievement_definitions.append(new_ach_data)
        else:
            self.achievement_definitions.append(new_ach_data)

        if self._save_achievement_definitions_to_file():
            self._load_achievement_def_list()
            if hasattr(self, "achievements_frame") and self.current_frame == self.achievements_frame:
                self.create_achievements_page()
        else:
            logging.error(
                "Zapis definicji osiągnięć nie powiódł się. Zmiany w pamięci mogą nie odpowiadać plikowi."
            )


__all__ = [
    "_load_achievement_definitions",
    "_load_achievement_def_list",
    "_delete_achievement_def",
    "_save_achievement_definitions_to_file",
    "_add_edit_achievement_def",
]
