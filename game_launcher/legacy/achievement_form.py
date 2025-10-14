"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class AchievementForm(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji definicji osiągnięcia."""
    # --- ZMIANA: Dodaj argument launcher_instance ---
    def __init__(self, parent, initial_data=None, launcher_instance=None):
        super().__init__(parent)
        self.parent = parent
        # --- NOWE: Zapisz referencję do launchera ---
        self._start_time = 0.0        # kiedy faktycznie gra (sec, monotonic)
        self._pause_acc = 0.0         # suma czasu spędzonego w pauzie
        self.launcher = launcher_instance
        if not self.launcher:
             # Fallback, jeśli launcher nie został przekazany (choć powinien)
             # Można by zgłosić błąd lub spróbować znaleźć instancję inaczej
             raise ValueError("AchievementForm wymaga instancji GameLauncher!")
        # --- KONIEC NOWEGO ---
        self.result = None # Przechowa wynikowy słownik definicji

        is_edit = initial_data is not None
        title = "Edytuj Osiągnięcie" if is_edit else "Dodaj Nowe Osiągnięcie"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        # --- Pola formularza ---
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1) # Rozciągnij kolumnę z polami

        # ID (nieedytowalne podczas edycji?) - Można pozwolić na edycję, ale z ostrzeżeniem
        ttk.Label(main_frame, text="ID Osiągnięcia:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.id_var = tk.StringVar(value=initial_data.get("id", "") if is_edit else "")
        self.id_entry = ttk.Entry(main_frame, textvariable=self.id_var, width=40)
        self.id_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if is_edit:
            self.id_entry.config(state='readonly') # Zablokuj ID podczas edycji

        # Nazwa
        ttk.Label(main_frame, text="Nazwa Wyświetlana:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.name_var = tk.StringVar(value=initial_data.get("name", "") if is_edit else "")
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Opis
        ttk.Label(main_frame, text="Opis:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
        self.desc_text = tk.Text(main_frame, height=4, width=40, wrap=tk.WORD, relief=tk.FLAT)
        style = ttk.Style(); text_bg = style.lookup('TEntry', 'fieldbackground'); text_fg = style.lookup('TEntry', 'foreground')
        self.desc_text.config(background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1)
        self.desc_text.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if is_edit: self.desc_text.insert("1.0", initial_data.get("description", ""))
        desc_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=self.desc_text.yview)
        desc_scroll.grid(row=2, column=3, sticky="ns", pady=5)
        self.desc_text.config(yscrollcommand=desc_scroll.set)

        # Ikona
        ttk.Label(main_frame, text="Ikona (ścieżka):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.icon_var = tk.StringVar(value=initial_data.get("icon", "") if is_edit else "")
        self.icon_entry = ttk.Entry(main_frame, textvariable=self.icon_var, width=40)
        self.icon_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        icon_btn = ttk.Button(main_frame, text="Wybierz...", command=self._select_icon)
        icon_btn.grid(row=3, column=2, padx=5, pady=5)

        # Typ Reguły
        # --- ZMIANA: Typ Warunku z tłumaczeniami ---
        # --- Typ Warunku (Combobox) ---
        ttk.Label(main_frame, text="Typ Warunku:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.rule_type_map = self.launcher.ACHIEVEMENT_RULE_TYPES_TRANSLATED
        # --- ZMIANA: Dodaj nowe typy reguł, usuń te nieimplementowane ---
        self.available_rule_types = list(self.rule_type_map.keys()) # Zaczynamy od wszystkich
        # if "news_read" in self.available_rule_types: self.available_rule_types.remove("news_read") # Usuń, jeśli nie zrobione
        # --- KONIEC ZMIANY ---
        display_rule_types = list(self.rule_type_map.values())

        # Pobierz techniczną nazwę dla wartości początkowej
        initial_technical_rule = initial_data.get("rule_type", "") if is_edit else list(self.rule_type_map.keys())[0]
        # Znajdź odpowiadającą jej nazwę wyświetlaną
        initial_display_rule = self.rule_type_map.get(initial_technical_rule, display_rule_types[0])

        self.rule_type_display_var = tk.StringVar(value=initial_display_rule) # Zmienna przechowuje nazwę wyświetlaną
        # --- ZMIANA: Dodaj śledzenie zmian typu warunku ---
        self.rule_type_display_var.trace_add("write", self._update_value_widget)
        # --- KONIEC ZMIANY ---
        rule_combo = ttk.Combobox(main_frame, textvariable=self.rule_type_display_var, values=display_rule_types, state="readonly")
        rule_combo.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        # --- KONIEC ZMIANY ---

        # --- Wartość Docelowa LUB Wybór Wartości ---
        # Ramka na widget wartości (będzie zawierać Entry LUB Combobox)
        self.value_frame = ttk.Frame(main_frame)
        self.value_frame.grid(row=5, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.value_frame.columnconfigure(0, weight=1) # Pozwól widgetowi się rozciągnąć

        ttk.Label(main_frame, text="Wartość/Cel:").grid(row=5, column=0, padx=5, pady=5, sticky="w")

        # Widgety dla wartości (tworzone, ale początkowo ukryte/zarządzane przez _update_value_widget)
        self.target_value_var = tk.StringVar(value=str(initial_data.get("target_value", "")) if is_edit else "1")
        self.target_value_entry = ttk.Entry(self.value_frame, textvariable=self.target_value_var, width=10)
        # Początkowo umieszczamy Entry
        self.target_value_entry.grid(row=0, column=0, sticky="w")

        self.value_select_var = tk.StringVar() # Dla Comboboxa gatunku/tagu/grupy
        self.value_select_combo = ttk.Combobox(self.value_frame, textvariable=self.value_select_var, state="readonly", width=35)
        # Nie umieszczamy Comboboxa w gridzie od razu

        # --- NOWE: Przechowaj dodatkowy parametr (np. gatunek) ---
        self.extra_param_var = tk.StringVar(value=initial_data.get("genre", initial_data.get("tag", initial_data.get("group", ""))) if is_edit else "")
        # --- KONIEC NOWEGO ---

        # Ukryty (przesunięty wiersz)
        self.hidden_var = tk.BooleanVar(value=initial_data.get("hidden", False) if is_edit else False)
        hidden_check = ttk.Checkbutton(main_frame, text="Ukryte (do odblokowania)", variable=self.hidden_var)
        hidden_check.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # Przyciski Zapisz/Anuluj (przesunięty wiersz)
        button_frame = ttk.Frame(main_frame); button_frame.grid(row=7, column=0, columnspan=4, pady=15)
        ttk.Button(button_frame, text="Zapisz", command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT, padx=10)

        # Wywołaj raz, aby ustawić poprawny widget wartości
        self._update_value_widget()

        self.name_entry.focus_set()
        self.wait_window(self)



    # --- NOWA METODA: Aktualizuje widget dla wartości docelowej ---
    def _update_value_widget(self, *args):
         """Pokazuje Entry lub Combobox w zależności od typu reguły i resetuje wartość."""
         selected_display_rule = self.rule_type_display_var.get()
         technical_rule_type = None
         for tech, display in self.rule_type_map.items():
              if display == selected_display_rule:
                   technical_rule_type = tech
                   break

         # Zapamiętaj, czy poprzednio był widoczny Combobox
         was_list_rule = self.value_select_combo.winfo_ismapped()

         # Ukryj oba widgety i dodatkową etykietę
         self.target_value_entry.grid_remove()
         self.value_select_combo.grid_remove()
         for widget in self.value_frame.winfo_children():
             if isinstance(widget, ttk.Label): widget.grid_remove()


         list_selection_rules = [
              "genre_played_count", "tag_played_count", "group_played_count",
              "genre_completed_100", "tag_completed_100", "group_completed_100"
         ]
         is_list_rule_now = technical_rule_type in list_selection_rules

         if is_list_rule_now:
              # Pokaż Combobox i wypełnij go
              options = []
              current_extra_param = self.extra_param_var.get() # Pobierz zapamiętaną wartość dodatkową
              selected_value = "" # Co ustawić w Comboboxie

              if "genre" in technical_rule_type:
                   options = self.launcher.get_all_genres()
                   selected_value = current_extra_param if current_extra_param in options else (options[0] if options else "")
              elif "tag" in technical_rule_type:
                   options = self.launcher.get_all_tags()
                   selected_value = current_extra_param if current_extra_param in options else (options[0] if options else "")
              elif "group" in technical_rule_type:
                   options = list(self.launcher.groups.keys())
                   selected_value = current_extra_param if current_extra_param in options else (options[0] if options else "")

              self.value_select_combo['values'] = options
              self.value_select_var.set(selected_value) # Ustaw wartość w Comboboxie
              self.value_select_combo.grid(row=0, column=0, sticky="ew")

              # Pokaż etykietę i Entry dla liczby
              ttk.Label(self.value_frame, text="Liczba gier:").grid(row=1, column=0, sticky="w", pady=(5,0))
              # --- ZMIANA: Resetuj wartość liczbową, jeśli zmieniono typ z nielistowego na listowy ---
              if not was_list_rule:
                   self.target_value_var.set("1") # Ustaw domyślną wartość "1"
              # --- KONIEC ZMIANY ---
              self.target_value_entry.grid(row=1, column=1, sticky="w", pady=(5,0))
         else:
              # Pokaż tylko Entry dla wartości docelowej
              # --- ZMIANA: Resetuj wartość liczbową, jeśli zmieniono typ z listowego na nielistowy ---
              if was_list_rule:
                  # Ustaw domyślną "1" lub inną sensowną wartość? Na razie "1".
                  self.target_value_var.set("1")
              # --- KONIEC ZMIANY ---
              self.target_value_entry.grid(row=0, column=0, sticky="w")


    def _select_icon(self):
        """Otwiera dialog wyboru pliku ikony."""
        # Zacznij w folderze 'icons' jeśli istnieje, inaczej w folderze aplikacji
        initial_dir = "icons" if os.path.isdir("icons") else "."
        path = filedialog.askopenfilename(
            title="Wybierz plik ikony osiągnięcia",
            filetypes=[("Obrazy PNG", "*.png"), ("Wszystkie pliki", "*.*")],
            initialdir=initial_dir,
            parent=self # Ustaw to okno jako rodzica
        )
        if path:
            # Spróbuj zapisać ścieżkę względną, jeśli jest w podfolderze 'icons'
            try:
                rel_path = os.path.relpath(path, os.getcwd())
                if not rel_path.startswith('..'): # Jeśli jest w bieżącym folderze lub podfolderze
                    self.icon_var.set(rel_path.replace('\\', '/')) # Użyj slashy
                    return
            except ValueError: # Różne dyski
                pass
            # Jeśli nie da się względnej, zapisz absolutną
            self.icon_var.set(path.replace('\\', '/'))


    def _save(self):
        """Waliduje dane i przygotowuje wynik."""
        ach_id = self.id_var.get().strip()
        name = self.name_var.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        icon_path = self.icon_var.get().strip()
        selected_display_rule = self.rule_type_display_var.get()
        rule_type = None
        for tech_name, display_name in self.rule_type_map.items():
            if display_name == selected_display_rule:
                rule_type = tech_name
                break

        is_hidden = self.hidden_var.get()
        extra_param_key = None
        extra_param_value = None

        # --- ZMIANA: Pobierz target_str i extra_param_value z odpowiednich widgetów ---
        target_str = "" # Domyślnie pusty
        list_selection_rules = [
            "genre_played_count", "tag_played_count", "group_played_count",
            "genre_completed_100", "tag_completed_100", "group_completed_100"
        ]
        is_list_rule = rule_type in list_selection_rules

        if is_list_rule:
            # Pobierz wartość celu (liczbę) z Entry
            target_str = self.target_value_entry.get().strip()
            # Pobierz dodatkowy parametr (gatunek/tag/grupa) z Comboboxa
            extra_param_value = self.value_select_var.get()
            if not extra_param_value:
                 messagebox.showerror("Błąd", f"Wybierz {rule_type.split('_')[0]} dla tego typu warunku.", parent=self)
                 return
            # Ustal klucz dla dodatkowego parametru
            if "genre" in rule_type: extra_param_key = "genre"
            elif "tag" in rule_type: extra_param_key = "tag"
            elif "group" in rule_type: extra_param_key = "group"
        else:
            # Pobierz wartość celu (liczbę/czas) z Entry
            target_str = self.target_value_entry.get().strip() # Poprzednio było self.target_var
        # --- KONIEC ZMIANY ---


        # Walidacja podstawowa
        if not ach_id or not name or not description or not rule_type or not target_str:
             messagebox.showerror("Błąd", "ID, Nazwa, Opis, Typ Warunku i Wartość/Cel są wymagane.", parent=self)
             return
        if not re.match(r'^[a-zA-Z0-9_]+$', ach_id): messagebox.showerror("Błąd", "...", parent=self); return

        # Walidacja wartości docelowej
        try:
            if rule_type in ["total_playtime_hours", "playtime_single_game_hours"]: target_value = float(target_str)
            else: target_value = int(target_str)
            if target_value <= 0: raise ValueError("Wartość musi być dodatnia")
        except ValueError as e:
             messagebox.showerror("Błąd", f"Nieprawidłowa wartość docelowa: Musi być liczbą większą od zera.\n({e})", parent=self)
             return

        # Walidacja ikony
        if icon_path and not os.path.exists(icon_path): messagebox.showwarning("Ostrzeżenie", f"...", parent=self); icon_path = ""

        # Przygotuj słownik wynikowy
        self.result = {
            "id": ach_id, "name": name, "description": description, "icon": icon_path,
            "rule_type": rule_type, "target_value": target_value, "hidden": is_hidden
        }
        if extra_param_key and extra_param_value:
             self.result[extra_param_key] = extra_param_value

        self.destroy()
