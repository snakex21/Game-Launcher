"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

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
