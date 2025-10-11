class AdvancedFilterManager(tk.Toplevel):
    """Okno do zarządzania zapisanymi filtrami zaawansowanymi."""
    def __init__(self, parent, launcher_instance):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.config = self.launcher.config # Dostęp do głównej konfiguracji

        self.title("Zarządzaj Filtrami Zaawansowanymi")
        self.configure(bg="#1e1e1e")
        self.geometry("500x400")
        self.minsize(400, 300)
        self.grab_set()
        self.transient(parent)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Lista filtrów rośnie

        ttk.Label(self, text="Zapisane Filtry:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Ramka listy
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.filters_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.filters_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.filters_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.filters_listbox.config(yscrollcommand=scrollbar.set)

        # Przyciski zarządzania
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(row=2, column=0, pady=10)

        ttk.Button(buttons_frame, text="Dodaj Filtr", command=self._add_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Edytuj Zaznaczony", command=self._edit_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Usuń Zaznaczony", command=self._delete_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Zamknij", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self._load_filters() # Wczytaj filtry do listboxa

    def _load_filters(self):
        """Wczytuje nazwy zapisanych filtrów do Listboxa."""
        self.filters_listbox.delete(0, tk.END)
        saved_filters = self.config.get("saved_filters", {})
        for filter_name in sorted(saved_filters.keys(), key=str.lower):
            self.filters_listbox.insert(tk.END, filter_name)

    def _add_filter(self):
        """Otwiera okno edytora dla nowego filtra."""
        # Przekaż instancję launchera do edytora
        editor = FilterEditorWindow(self, self.launcher) # self (okno managera) jest rodzicem
        if editor.result:
            filter_name = editor.result["name"]
            filter_rules = editor.result["rules"]
            # Dodaj nowy filtr do konfiguracji
            self.config.setdefault("saved_filters", {})[filter_name] = {"name": filter_name, "rules": filter_rules}
            save_config(self.config)
            self._load_filters() # Odśwież listę w managerze
            self.launcher.update_filter_group_menu() # Odśwież menu w głównym oknie

    def _edit_filter(self):
        """Otwiera okno edytora dla zaznaczonego filtra."""
        selection = self.filters_listbox.curselection()
        if not selection:
            messagebox.showwarning("Brak zaznaczenia", "Zaznacz filtr, który chcesz edytować.", parent=self)
            return
        filter_name = self.filters_listbox.get(selection[0])
        filter_data = self.config.get("saved_filters", {}).get(filter_name)
        if not filter_data:
             messagebox.showerror("Błąd", f"Nie znaleziono danych dla filtra '{filter_name}'.", parent=self)
             self._load_filters() # Odśwież listę na wszelki wypadek
             return

        # Otwórz edytor z istniejącymi danymi
        editor = FilterEditorWindow(self, self.launcher, filter_data)
        if editor.result:
            new_filter_name = editor.result["name"]
            new_filter_rules = editor.result["rules"]
            saved_filters_dict = self.config.setdefault("saved_filters", {})

            # Usuń stary wpis tylko jeśli nazwa FAKTYCZNIE się zmieniła
            if new_filter_name != filter_name and filter_name in saved_filters_dict:
                del saved_filters_dict[filter_name]

            # Zapisz nowy/zaktualizowany filtr
            saved_filters_dict[new_filter_name] = {"name": new_filter_name, "rules": new_filter_rules}
            save_config(self.config)
            self._load_filters() # Odśwież listę w managerze
            self.launcher.update_filter_group_menu() # Odśwież menu w głównym oknie

    def _delete_filter(self):
        selection = self.filters_listbox.curselection()
        if not selection:
            messagebox.showwarning("Brak zaznaczenia", "Zaznacz filtr, który chcesz usunąć.", parent=self)
            return
        filter_name = self.filters_listbox.get(selection[0])

        if messagebox.askyesno("Potwierdź usunięcie", f"Czy na pewno chcesz usunąć filtr zaawansowany '{filter_name}'?", parent=self):
            saved_filters = self.config.get("saved_filters", {})
            if filter_name in saved_filters:
                del saved_filters[filter_name]
                save_config(self.config)
                self._load_filters() # Odśwież listę w tym oknie
                self.launcher.update_filter_group_menu() # Odśwież menu w głównym oknie
                logging.info(f"Usunięto filtr zaawansowany: {filter_name}")
            else:
                messagebox.showerror("Błąd", f"Nie znaleziono filtra '{filter_name}' do usunięcia.", parent=self)


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


class RuleEditor(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji pojedynczej reguły filtra."""
    def __init__(self, parent, launcher_instance, initial_rule_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None # Zwróci słownik reguły {'field': ..., 'operator': ..., 'value': ...}

        is_edit = initial_rule_data is not None
        title = "Edytuj Regułę Filtra" if is_edit else "Dodaj Regułę Filtra"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        # --- Dostępne Pola i Operatory ---
        # Definiujemy, jakie pola można filtrować i jakie operatory są dostępne dla każdego typu pola
        self.FIELDS = {
            "Nazwa Gry": {"type": "text", "db_field": "name"},
            "Gatunek": {"type": "list", "db_field": "genres"},
            "Tag": {"type": "list", "db_field": "tags"},
            "Ocena": {"type": "number", "db_field": "rating"},
            "Czas Gry (godz.)": {"type": "number", "db_field": "play_time"}, # Będziemy konwertować sekundy
            "Data Dodania": {"type": "date", "db_field": "date_added"},
            "Data Ost. Gry": {"type": "date", "db_field": "last_played"},
            "Typ Gry": {"type": "choice", "db_field": "game_type", "choices": ["pc", "emulator"]},
            "Emulator": {"type": "choice", "db_field": "emulator_name", "choices": list(self.launcher.config.get("emulators", {}).keys())},
            "Ukończenie (%)": {"type": "number", "db_field": "completion"}
        }
        self.OPERATORS = {
            "text": ["zawiera", "nie zawiera", "równa się", "zaczyna się od", "kończy się na"],
            "list": ["zawiera", "nie zawiera"], # Dla Gatunków i Tagów
            "number": ["==", "!=", ">", "<", ">=", "<=", "jest ustawione", "nie jest ustawione"],
            "date": ["jest równe", "jest przed", "jest po", "jest ustawione", "nie jest ustawione"],
            "choice": ["jest", "nie jest"] # Dla Typu Gry, Emulatora
        }
        # Mapowanie nazw wyświetlanych pól na klucze wewnętrzne
        self.FIELD_NAME_TO_KEY = {name: data["db_field"] for name, data in self.FIELDS.items()}
        self.FIELD_KEY_TO_NAME = {data["db_field"]: name for name, data in self.FIELDS.items()}


        # --- Zmienne Tkinter ---
        self.field_display_var = tk.StringVar()
        self.operator_var = tk.StringVar()
        self.value_var = tk.StringVar()
        self.value_date_var = tk.StringVar() # Osobna zmienna dla DateEntry

        # --- Główna Ramka ---
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        # --- Wybór Pola ---
        ttk.Label(main_frame, text="Filtruj według pola:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        field_names = sorted(list(self.FIELDS.keys()))
        self.field_combo = ttk.Combobox(main_frame, textvariable=self.field_display_var, values=field_names, state="readonly")
        self.field_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.field_combo.bind("<<ComboboxSelected>>", self._update_operator_and_value_widgets)

        # --- Wybór Operatora ---
        ttk.Label(main_frame, text="Warunek:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.operator_combo = ttk.Combobox(main_frame, textvariable=self.operator_var, state="readonly")
        self.operator_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.operator_combo.bind("<<ComboboxSelected>>", self._update_value_widget_visibility) # Pokaż/ukryj wartość

        # --- Wprowadzanie Wartości ---
        ttk.Label(main_frame, text="Wartość:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
        # Ramka na dynamiczny widget wartości
        self.value_widget_frame = ttk.Frame(main_frame)
        self.value_widget_frame.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.value_widget_frame.columnconfigure(0, weight=1)
        # Widgety wartości (tworzone, ale pokazywane dynamicznie)
        self.value_entry = ttk.Entry(self.value_widget_frame, textvariable=self.value_var)
        self.value_date_entry = DateEntry(self.value_widget_frame, textvariable=self.value_date_var, date_pattern='yyyy-mm-dd', state="readonly")
        self.value_choice_combo = ttk.Combobox(self.value_widget_frame, textvariable=self.value_var, state="readonly") # Użyj value_var dla choice też

        # --- Przyciski Zapisz/Anuluj ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="Zapisz Regułę", command=self._save_rule).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT, padx=10)

        # --- Inicjalizacja Wartości (jeśli edycja) ---
        if is_edit and initial_rule_data:
             field_key = initial_rule_data.get("field")
             field_name = self.FIELD_KEY_TO_NAME.get(field_key, field_names[0])
             self.field_display_var.set(field_name)
             self._update_operator_and_value_widgets() # To ustawi operatory i pokaże właściwy widget
             self.operator_var.set(initial_rule_data.get("operator", ""))
             # Ustaw wartość (uwzględniając typ)
             value = initial_rule_data.get("value")
             field_type = self.FIELDS.get(field_name, {}).get("type")
             if field_type == "date":
                  try: # Spróbuj ustawić datę w DateEntry
                      datetime.datetime.strptime(str(value), '%Y-%m-%d') # Walidacja formatu
                      self.value_date_var.set(value)
                  except (ValueError, TypeError):
                       self.value_date_var.set("") # Ustaw pustą, jeśli zły format
             else:
                  self.value_var.set(str(value) if value is not None else "") # Ustaw jako string

             self._update_value_widget_visibility() # Upewnij się, że widget wartości jest widoczny/ukryty poprawnie

        else:
             # Ustaw domyślne wartości dla nowego filtra
             self.field_display_var.set(field_names[0])
             self._update_operator_and_value_widgets()

        self.field_combo.focus_set()
        self.wait_window(self)


    def _update_operator_and_value_widgets(self, event=None):
        """Aktualizuje listę operatorów i widget wartości po zmianie pola."""
        selected_field_name = self.field_display_var.get()
        field_info = self.FIELDS.get(selected_field_name, {})
        field_type = field_info.get("type")

        # Aktualizuj operatory
        available_operators = self.OPERATORS.get(field_type, [])
        self.operator_combo['values'] = available_operators
        if available_operators:
            # Ustaw pierwszy operator jako domyślny, jeśli obecny nie pasuje
            if self.operator_var.get() not in available_operators:
                 self.operator_var.set(available_operators[0])
        else:
            self.operator_var.set("") # Wyczyść, jeśli brak operatorów

        # Aktualizuj widget wartości
        self._update_value_widget_visibility() # To pokaże/ukryje i skonfiguruje widget wartości

    def _update_value_widget_visibility(self, event=None):
         """Pokazuje/ukrywa widget wartości w zależności od operatora i typu pola."""
         operator = self.operator_var.get()
         selected_field_name = self.field_display_var.get()
         field_type = self.FIELDS.get(selected_field_name, {}).get("type")

         # Ukryj wszystkie widgety wartości
         self.value_entry.grid_remove()
         self.value_date_entry.grid_remove()
         self.value_choice_combo.grid_remove()

         # Pokaż odpowiedni widget, jeśli operator wymaga wartości
         if operator not in ["jest ustawione", "nie jest ustawione"]:
              if field_type == "date":
                   self.value_date_entry.grid(row=0, column=0, sticky="ew")
              elif field_type == "choice":
                   db_field = self.FIELDS[selected_field_name]["db_field"]
                   choices = self.FIELDS[selected_field_name].get("choices", [])
                   if db_field == "emulator_name": # Pobierz aktualną listę emulatorów
                        choices = list(self.launcher.config.get("emulators", {}).keys())
                   self.value_choice_combo['values'] = choices
                   # Ustaw domyślny wybór, jeśli lista nie jest pusta
                   if choices and self.value_var.get() not in choices:
                        self.value_var.set(choices[0])
                   elif not choices: # Jeśli brak opcji (np. brak emulatorów)
                        self.value_var.set("")
                        self.value_choice_combo.config(state="disabled") # Wyłącz combobox
                   else:
                        self.value_choice_combo.config(state="readonly") # Włącz, jeśli są opcje
                   self.value_choice_combo.grid(row=0, column=0, sticky="ew")
              elif field_type == "list": # Dla Gatunku/Tagu - użyj zwykłego pola tekstowego
                   self.value_entry.grid(row=0, column=0, sticky="ew")
              else: # Dla text, number
                   self.value_entry.grid(row=0, column=0, sticky="ew")


    def _save_rule(self):
        """Waliduje i zwraca zdefiniowaną regułę."""
        field_name = self.field_display_var.get()
        operator = self.operator_var.get()
        field_key = self.FIELD_NAME_TO_KEY.get(field_name)
        field_type = self.FIELDS.get(field_name, {}).get("type")
        value = None

        if not field_key or not operator:
            messagebox.showerror("Błąd", "Wybierz pole i warunek.", parent=self)
            return

        # Pobierz wartość, jeśli operator tego wymaga
        if operator not in ["jest ustawione", "nie jest ustawione"]:
            if field_type == "date":
                value_str = self.value_date_var.get()
                try:
                    # Sprawdź format daty
                    datetime.datetime.strptime(value_str, '%Y-%m-%d')
                    value = value_str
                except ValueError:
                    messagebox.showerror("Błąd Formatu", "Wprowadź datę w formacie RRRR-MM-DD.", parent=self)
                    return
            elif field_type == "choice":
                 value = self.value_var.get()
                 if not value: # Sprawdź, czy coś wybrano (szczególnie dla emulatorów)
                      messagebox.showerror("Błąd", f"Wybierz wartość dla pola '{field_name}'.", parent=self)
                      return
            # --- ZMIANA: Użyj field_type do sprawdzenia liczby ---
            elif field_type == "number":
            # --- KONIEC ZMIANY ---
                 value_str = self.value_entry.get().strip()
                 try:
                      # Sprawdźmy, czy klucz pola sugeruje float (czas, ocena, ukończenie)
                      if field_key in ["play_time", "rating", "completion"]:
                           value = float(value_str)
                      else: # Domyślnie int
                           value = int(value_str)
                 except ValueError:
                      messagebox.showerror("Błąd Wartości", f"Wartość dla pola '{field_name}' musi być liczbą.", parent=self)
                      return
            else: # Dla text i list
                value = self.value_entry.get().strip() # Użyj value_entry
                if not value: messagebox.showerror("Błąd", "Wartość nie może być pusta dla tego warunku.", parent=self); return

        # Zwróć wynikowy słownik reguły
        self.result = {"field": field_key, "operator": operator, "value": value}
        self.destroy()
from .shared_imports import tk, ttk, messagebox, simpledialog, logging
from .utils import save_config


