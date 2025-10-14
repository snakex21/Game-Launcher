"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

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
