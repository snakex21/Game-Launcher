"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class FilterEditorWindow(tk.Toplevel):
    """Okno do tworzenia i edycji reguł filtra zaawansowanego."""
    def __init__(self, parent, launcher_instance, filter_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None # Przechowa {'name': ..., 'rules': [...]}

        is_edit = filter_data is not None
        title = "Edytuj Filtr Zaawansowany" if is_edit else "Nowy Filtr Zaawansowany"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.geometry("750x550") # Domyślny rozmiar
        self.minsize(600, 400)
        self.grab_set()
        self.transient(parent)

        # --- Struktura danych ---
        self.filter_name = tk.StringVar(value=filter_data.get("name", "Nowy Filtr") if is_edit else "Nowy Filtr")
        # Użyj kopii listy reguł, aby nie modyfikować oryginału przed zapisem
        self.rules = filter_data.get("rules", []).copy() if is_edit else []
        self.original_filter_name = filter_data.get("name") if is_edit else None # Do sprawdzania zmiany nazwy

        # --- Główna ramka ---
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1) # Kolumna z Treeview rośnie
        main_frame.rowconfigure(2, weight=1) # Wiersz z Treeview rośnie

        # --- Nazwa Filtra ---
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Nazwa Filtra:").grid(row=0, column=0, padx=(0, 5))
        name_entry = ttk.Entry(name_frame, textvariable=self.filter_name, width=40)
        name_entry.grid(row=0, column=1, sticky="ew")

        # --- Przyciski zarządzania regułami ---
        rule_buttons_frame = ttk.Frame(main_frame)
        rule_buttons_frame.grid(row=1, column=0, sticky="w", pady=5)
        ttk.Button(rule_buttons_frame, text="Dodaj Regułę", command=self._add_edit_rule).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(rule_buttons_frame, text="Edytuj Regułę", command=lambda: self._add_edit_rule(edit_mode=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(rule_buttons_frame, text="Usuń Regułę", command=self._delete_rule).pack(side=tk.LEFT, padx=5)

        # --- Lista Reguł (Treeview) ---
        rules_list_frame = ttk.Frame(main_frame)
        rules_list_frame.grid(row=2, column=0, sticky="nsew")
        rules_list_frame.columnconfigure(0, weight=1)
        rules_list_frame.rowconfigure(0, weight=1)

        rule_cols = ("Pole", "Operator", "Wartość")
        self.rules_tree = ttk.Treeview(rules_list_frame, columns=rule_cols, show="headings", height=10, selectmode="browse")
        self.rules_tree.heading("Pole", text="Filtrowane Pole")
        self.rules_tree.heading("Operator", text="Warunek")
        self.rules_tree.heading("Wartość", text="Wartość/Cel")
        self.rules_tree.column("Pole", width=150, anchor=tk.W)
        self.rules_tree.column("Operator", width=150, anchor=tk.W)
        self.rules_tree.column("Wartość", width=250, anchor=tk.W) # Szersza kolumna na wartość

        rules_scrollbar = ttk.Scrollbar(rules_list_frame, orient="vertical", command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=rules_scrollbar.set)

        self.rules_tree.grid(row=0, column=0, sticky="nsew")
        rules_scrollbar.grid(row=0, column=1, sticky="ns")

        # Wypełnij listę reguł
        self._populate_rules_tree()

        # --- Przyciski Zapisz/Anuluj ---
        bottom_buttons_frame = ttk.Frame(main_frame)
        bottom_buttons_frame.grid(row=3, column=0, sticky="e", pady=(10, 0))
        ttk.Button(bottom_buttons_frame, text="Zapisz Filtr", command=self._save_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_buttons_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT, padx=5)

        # Ustaw fokus na nazwie i czekaj
        name_entry.focus_set()
        self.wait_window(self)

    def _populate_rules_tree(self):
        """Wypełnia Treeview aktualną listą reguł."""
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # TODO: Przetłumaczyć nazwy pól i operatorów dla wyświetlenia
        for idx, rule in enumerate(self.rules):
             field = rule.get("field", "?")
             op = rule.get("operator", "?")
             val = rule.get("value", "?")
             # Na razie wyświetlamy techniczne nazwy
             self.rules_tree.insert("", "end", iid=str(idx), values=(field, op, val))

    def _add_edit_rule(self, edit_mode=False):
        """Otwiera okno dialogowe do dodania/edycji reguły."""
        initial_rule_data = None
        rule_index = -1 # Indeks edytowanej reguły w self.rules

        if edit_mode:
             selection = self.rules_tree.selection()
             if not selection:
                  messagebox.showwarning("Brak zaznaczenia", "Zaznacz regułę, którą chcesz edytować.", parent=self)
                  return
             try:
                  rule_index = int(selection[0]) # iid to indeks
                  initial_rule_data = self.rules[rule_index].copy()
             except (ValueError, IndexError):
                  messagebox.showerror("Błąd", "Nie można odczytać danych wybranej reguły.", parent=self)
                  return

        # Otwórz edytor reguł
        dialog = RuleEditor(self, self.launcher, initial_rule_data) # Przekaż launchera

        if dialog.result:
            new_rule_data = dialog.result
            if edit_mode and rule_index >= 0:
                self.rules[rule_index] = new_rule_data # Zaktualizuj istniejącą
            else:
                self.rules.append(new_rule_data) # Dodaj nową
            self._populate_rules_tree() # Odśwież listę reguł w tym oknie

    def _delete_rule(self):
        """Usuwa zaznaczoną regułę."""
        selection = self.rules_tree.selection()
        if not selection:
             messagebox.showwarning("Brak zaznaczenia", "Zaznacz regułę, którą chcesz usunąć.", parent=self)
             return
        try:
            rule_index = int(selection[0])
            # Pobierz bardziej opisowe przedstawienie reguły do potwierdzenia
            rule_values = self.rules_tree.item(selection[0], "values")
            rule_desc = f"{rule_values[0]} {rule_values[1]} {rule_values[2]}"

            if messagebox.askyesno("Potwierdź usunięcie", f"Czy na pewno chcesz usunąć regułę:\n'{rule_desc}'?", parent=self):
                if 0 <= rule_index < len(self.rules):
                    del self.rules[rule_index]
                    self._populate_rules_tree() # Odśwież listę
                else: messagebox.showerror("Błąd", "Nie można znaleźć reguły do usunięcia.", parent=self)
        except (ValueError, IndexError): messagebox.showerror("Błąd", "Nie można zidentyfikować wybranej reguły.", parent=self)


    def _save_filter(self):
        """Waliduje nazwę filtra i zwraca wynik."""
        new_name = self.filter_name.get().strip()
        if not new_name:
            messagebox.showerror("Brak Nazwy", "Nazwa filtra nie może być pusta.", parent=self)
            return
        if new_name == "Wszystkie Gry" or new_name.startswith("---"):
            messagebox.showerror("Błąd Nazwy", f"Nazwa filtra '{new_name}' jest zarezerwowana.", parent=self)
            return

        # Sprawdź, czy nazwa nie koliduje z inną grupą lub filtrem (poza sobą, jeśli edytujemy)
        all_filter_names = list(self.launcher.config.get("saved_filters", {}).keys())
        all_group_names = list(self.launcher.groups.keys())

        if new_name != self.original_filter_name: # Sprawdzaj tylko jeśli nazwa się zmieniła lub dodajemy nowy
            if new_name in all_group_names:
                 messagebox.showerror("Konflikt Nazw", f"Istnieje już grupa statyczna o nazwie '{new_name}'.", parent=self)
                 return
            if new_name in all_filter_names:
                 messagebox.showerror("Konflikt Nazw", f"Istnieje już inny filtr zaawansowany o nazwie '{new_name}'.", parent=self)
                 return

        if not self.rules:
             messagebox.showwarning("Brak Reguł", "Filtr musi zawierać przynajmniej jedną regułę.", parent=self)
             return

        # Zwróć wynik
        self.result = {"name": new_name, "rules": self.rules}
        self.destroy()
