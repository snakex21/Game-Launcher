"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class ScanVerificationWindow(tk.Toplevel):
    """Okno do weryfikacji gier znalezionych podczas skanowania."""
    def __init__(self, parent, launcher_instance, potential_games):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.potential_games_data = potential_games # Przechowuje dane {'guessed_name', 'folder_path', 'suggested_exe_path', 'import', 'profiles'}
        self.row_widgets = {} # Słownik do przechowywania widgetów dla każdego wiersza {iid: {var_import, name_entry, exe_label, profiles_data}}

        self.title("Weryfikacja Znalezionych Gier")
        self.configure(bg="#1e1e1e")
        self.geometry("900x600")
        self.minsize(700, 400)
        self.grab_set()

        # Nagłówek
        ttk.Label(self, text="Przejrzyj znalezione gry i zdecyduj, które zaimportować.", font=("Helvetica", 12)).pack(pady=(10, 5))
        ttk.Label(self, text="Możesz edytować nazwę, zmienić główny plik .exe lub dodać dodatkowe profile uruchomieniowe.", font=("Helvetica", 9)).pack(pady=(0, 10))

        # Ramka dla Treeview i Scrollbara
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Treeview
        columns = ("Import", "Nazwa Gry", "Główny Plik EXE", "Folder Gry", "Profile")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("Import", text="Importuj?")
        self.tree.heading("Nazwa Gry", text="Sugerowana Nazwa Gry")
        self.tree.heading("Główny Plik EXE", text="Sugerowany Główny Plik EXE")
        self.tree.heading("Folder Gry", text="Folder Gry")
        self.tree.heading("Profile", text="Dodatkowe Profile")

        self.tree.column("Import", width=60, anchor=tk.CENTER, stretch=False)
        self.tree.column("Nazwa Gry", width=200, anchor=tk.W)
        self.tree.column("Główny Plik EXE", width=250, anchor=tk.W)
        self.tree.column("Folder Gry", width=250, anchor=tk.W)
        self.tree.column("Profile", width=100, anchor=tk.W)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Wypełnij Treeview danymi
        self.populate_tree()

        # Przyciski akcji pod Treeview
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Przyciski edycji dla zaznaczonego elementu
        edit_buttons_frame = ttk.Frame(action_frame)
        edit_buttons_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Button(edit_buttons_frame, text="Zmień Nazwę", command=self.edit_selected_name).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="Zmień Główny .EXE", command=self.change_selected_exe).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="+ Dodaj Profil .EXE", command=self.add_profile_to_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="- Usuń Profil", command=self.remove_profile_from_selected).pack(side=tk.LEFT, padx=2) # Przycisk usuwania profilu


        # Przyciski importu i anulowania
        import_cancel_frame = ttk.Frame(action_frame)
        import_cancel_frame.pack(side=tk.RIGHT)
        ttk.Button(import_cancel_frame, text="Importuj Zaznaczone", style="Green.TButton", command=self.import_selected).pack(side=tk.LEFT, padx=10)
        ttk.Button(import_cancel_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT)

        # Bindowanie zdarzeń
        self.tree.bind("<Double-1>", self.toggle_import_selected) # Podwójne kliknięcie zmienia checkbox
        self.tree.tag_configure('checked', foreground='green')
        self.tree.tag_configure('unchecked', foreground='gray')

    def populate_tree(self):
        """Wypełnia Treeview danymi potencjalnych gier."""
        self.tree.delete(*self.tree.get_children()) # Wyczyść stare wpisy
        self.row_widgets.clear() # Wyczyść powiązane dane

        for idx, game_info in enumerate(self.potential_games_data):
            iid = f"game_{idx}" # Unikalny identyfikator wiersza
            import_status = "✔" if game_info.get('import', True) else "✖"
            tag = 'checked' if game_info.get('import', True) else 'unchecked'
            profiles_str = ", ".join([p['name'] for p in game_info['profiles'] if p['name'].lower() != 'default']) or "-"

            values = (
                import_status,
                game_info['guessed_name'],
                game_info['suggested_exe_path'],
                game_info['folder_path'],
                profiles_str
            )
            self.tree.insert("", "end", iid=iid, values=values, tags=(tag,))

            # Zapisz dane powiązane z wierszem (na razie tylko stan importu)
            self.row_widgets[iid] = {'import': tk.BooleanVar(value=game_info.get('import', True))}
            # W przyszłości można tu trzymać referencje do Entry itp. jeśli zmienimy UI

    def toggle_import_selected(self, event=None):
        """Przełącza status importu dla zaznaczonego wiersza."""
        selection = self.tree.selection()
        if not selection: return
        selected_iid = selection[0]

        if selected_iid in self.row_widgets:
            current_state = self.row_widgets[selected_iid]['import'].get()
            new_state = not current_state
            self.row_widgets[selected_iid]['import'].set(new_state)

            # Aktualizuj dane w oryginalnej liście
            try:
                 index = int(selected_iid.split('_')[1])
                 self.potential_games_data[index]['import'] = new_state
                 # Aktualizuj wygląd w Treeview
                 import_status = "✔" if new_state else "✖"
                 tag = 'checked' if new_state else 'unchecked'
                 # Pobierz istniejące wartości i zmień tylko pierwszą kolumnę
                 current_values = list(self.tree.item(selected_iid, 'values'))
                 current_values[0] = import_status
                 self.tree.item(selected_iid, values=tuple(current_values), tags=(tag,))
            except (IndexError, ValueError):
                 logging.error(f"Nie można zaktualizować stanu importu dla iid: {selected_iid}")

    def edit_selected_name(self):
        """Pozwala edytować nazwę zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection: return
        selected_iid = selection[0]
        try:
             index = int(selected_iid.split('_')[1])
             current_name = self.potential_games_data[index]['guessed_name']
             new_name = simpledialog.askstring("Zmień Nazwę Gry", "Podaj nową nazwę dla:", initialvalue=current_name, parent=self)
             if new_name and new_name.strip():
                 new_name = new_name.strip()
                 # Sprawdź, czy nowa nazwa nie koliduje z istniejącą w bibliotece lub w innym wierszu tego okna
                 if new_name.lower() in (name.lower() for name in self.launcher.games.keys()):
                      messagebox.showerror("Błąd", f"Gra o nazwie '{new_name}' już istnieje w bibliotece.", parent=self)
                      return
                 for i, game_info in enumerate(self.potential_games_data):
                      if i != index and game_info['guessed_name'].lower() == new_name.lower():
                           messagebox.showerror("Błąd", f"Nazwa '{new_name}' jest już używana przez inną grę w tym oknie.", parent=self)
                           return

                 self.potential_games_data[index]['guessed_name'] = new_name
                 # Aktualizuj Treeview
                 current_values = list(self.tree.item(selected_iid, 'values'))
                 current_values[1] = new_name
                 self.tree.item(selected_iid, values=tuple(current_values))
        except (IndexError, ValueError):
             logging.error(f"Nie można edytować nazwy dla iid: {selected_iid}")

    def change_selected_exe(self):
        """Pozwala zmienić główny plik .exe dla zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Brak zaznaczenia", "Najpierw zaznacz grę, której plik .exe chcesz zmienić.", parent=self)
            return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split('_')[1])
            game_folder = self.potential_games_data[index]['folder_path']
            current_name = self.potential_games_data[index]['guessed_name'] # Pobierz nazwę do tytułu okna

            new_exe = filedialog.askopenfilename(
                title=f"Wybierz główny plik .exe dla '{current_name}'", # Użyj nazwy w tytule
                filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
                initialdir=game_folder,
                parent=self
            )
            if new_exe:
                # --- POPRAWIONA WALIDACJA ---
                game_folder_abs = os.path.normcase(os.path.abspath(game_folder))
                new_exe_abs = os.path.normcase(os.path.abspath(new_exe))

                # Sprawdź, czy ścieżka absolutna pliku EXE zaczyna się od ścieżki absolutnej folderu gry
                # Dodajemy os.sep, aby upewnić się, że nie dopasujemy np. /path/to/game_folder_extra do /path/to/game_folder
                if new_exe_abs.startswith(game_folder_abs + os.sep) or new_exe_abs == game_folder_abs: # Dodano sprawdzenie równości na wszelki wypadek
                    # --- KONIEC POPRAWIONEJ WALIDACJI ---

                    # Aktualizuj dane tymczasowe
                    self.potential_games_data[index]['suggested_exe_path'] = os.path.abspath(new_exe) # Zapisz ścieżkę absolutną dla spójności

                    # Aktualizuj Treeview
                    current_values = list(self.tree.item(selected_iid, 'values'))
                    current_values[2] = os.path.abspath(new_exe) # Wyświetl ścieżkę absolutną
                    self.tree.item(selected_iid, values=tuple(current_values))
                    logging.info(f"Zmieniono główny EXE dla '{current_name}' na: {new_exe}")
                else:
                    logging.warning(f"Błąd walidacji ścieżki: '{new_exe}' nie znajduje się w '{game_folder}' lub jego podfolderach.")
                    messagebox.showerror(
                        "Błąd ścieżki",
                        "Plik wykonywalny musi znajdować się w folderze gry lub jego podfolderze.\n\n"
                        f"Folder gry: {game_folder}\n"
                        f"Wybrany plik: {new_exe}",
                        parent=self
                    )

        except (IndexError, ValueError):
             logging.error(f"Nie można zmienić EXE dla iid: {selected_iid}")
        except Exception as e:
             logging.exception(f"Nieoczekiwany błąd w change_selected_exe dla iid: {selected_iid}")
             messagebox.showerror("Błąd", f"Wystąpił nieoczekiwany błąd: {e}", parent=self)

    def add_profile_to_selected(self):
        """Dodaje nowy profil .exe dla zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection: return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split('_')[1])
            game_folder = self.potential_games_data[index]['folder_path']
            current_profiles = self.potential_games_data[index]['profiles']

            # Callback funkcja, która zostanie wywołana przez AddProfileDialog
            def profile_added_callback(new_profile_data):
                if new_profile_data:
                    # Dodaj nowy profil do danych tymczasowych
                    current_profiles.append(new_profile_data)
                    # Odśwież kolumnę 'Profile' w Treeview
                    profiles_str = ", ".join([p['name'] for p in current_profiles if p['name'].lower() != 'default']) or "-"
                    current_values = list(self.tree.item(selected_iid, 'values'))
                    current_values[4] = profiles_str
                    self.tree.item(selected_iid, values=tuple(current_values))

            # Otwórz dialog dodawania profilu
            AddProfileDialog(self, game_folder, current_profiles, profile_added_callback)

        except (IndexError, ValueError):
            logging.error(f"Nie można dodać profilu dla iid: {selected_iid}")

    def remove_profile_from_selected(self):
        """Usuwa wybrany profil z zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection: return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split('_')[1])
            current_profiles = self.potential_games_data[index]['profiles']

            # Pobierz nazwy profili (poza 'Default') do wyświetlenia
            profile_names = [p['name'] for p in current_profiles if p['name'].lower() != 'default']
            if not profile_names:
                messagebox.showinfo("Brak profili", "Ta gra nie ma dodatkowych profili do usunięcia.", parent=self)
                return

            # Użyj simpledialog.askstring z comboboxem (jeśli dostępny) lub listą
            # To jest ograniczenie simpledialog, lepiej byłoby stworzyć własne okno wyboru
            # Na razie użyjemy askstring i poinformujemy użytkownika
            chosen_name = simpledialog.askstring(
                "Usuń Profil",
                "Wpisz nazwę profilu do usunięcia z listy:\n\n" + "\n".join(profile_names),
                parent=self
            )

            if chosen_name:
                chosen_name = chosen_name.strip()
                profile_to_remove = None
                for profile in current_profiles:
                    if profile.get("name", "").lower() == chosen_name.lower() and chosen_name.lower() != 'default':
                        profile_to_remove = profile
                        break

                if profile_to_remove:
                    current_profiles.remove(profile_to_remove)
                    # Odśwież Treeview
                    profiles_str = ", ".join([p['name'] for p in current_profiles if p['name'].lower() != 'default']) or "-"
                    current_values = list(self.tree.item(selected_iid, 'values'))
                    current_values[4] = profiles_str
                    self.tree.item(selected_iid, values=tuple(current_values))
                    logging.info(f"Usunięto profil '{chosen_name}' dla gry (w weryfikacji): {self.potential_games_data[index]['guessed_name']}")
                else:
                    messagebox.showwarning("Nie znaleziono", f"Nie znaleziono profilu o nazwie '{chosen_name}' lub jest to profil 'Default'.", parent=self)

        except (IndexError, ValueError):
             logging.error(f"Nie można usunąć profilu dla iid: {selected_iid}")

    def import_selected(self):
        """Importuje zaznaczone gry do biblioteki."""
        games_to_add = {}
        imported_count = 0

        for idx, game_info in enumerate(self.potential_games_data):
            iid = f"game_{idx}"
            # Sprawdź stan importu (z self.row_widgets lub bezpośrednio z game_info)
            should_import = self.row_widgets[iid]['import'].get() if iid in self.row_widgets else game_info.get('import', False)

            if should_import:
                final_name = game_info['guessed_name']
                main_exe_path = game_info['suggested_exe_path']
                folder_path = game_info['folder_path']
                # Przygotuj listę profili
                final_profiles = []
                # Główny exe jako profil "Default", jeśli nie ma innych profili LUB jeśli explicitnie dodano profil z tym exe
                # Logika: pierwszy profil na liście game_info['profiles'] to ZAWSZE domyślny logicznie
                default_profile_data = game_info['profiles'][0] # Zawsze jest co najmniej jeden
                default_profile_data['exe_path'] = None # Sygnalizuje użycie głównego exe gry
                final_profiles.append(default_profile_data)

                # Dodaj pozostałe zdefiniowane profile (jeśli są)
                for profile_data in game_info['profiles'][1:]: # Pomiń pierwszy (domyślny)
                     # Sprawdź, czy ścieżka exe nie jest taka sama jak główna
                     if profile_data.get('exe_path') != main_exe_path:
                          final_profiles.append(profile_data)
                     else:
                          # Jeśli ktoś dodał profil z tym samym exe co główny, zignoruj go,
                          # chyba że ma inne argumenty? Na razie ignorujemy.
                          logging.warning(f"Profil '{profile_data.get('name')}' dla '{final_name}' używa tej samej ścieżki co główny plik. Ignorowanie nadmiarowego profilu.")


                # Podstawowe dane nowej gry
                new_game_data = {
                    "name": final_name,
                    "exe_path": main_exe_path,
                    "folder_path": folder_path, # Możemy zapisać folder dla informacji
                    "save_path": "", # Domyślnie puste
                    "cover_image": "", # Domyślnie puste
                    "genres": [], "rating": None, "version": "", "tags": [], "notes": "",
                    "date_added": time.time(),
                    "play_time": 0, "completion": 0, "last_played": None, "play_sessions": [],
                    "launch_profiles": final_profiles # Zapisz przygotowaną listę profili
                }
                # Można dodać parsowanie NFO/folderu tutaj, jeśli chcemy
                # folder_metadata = self.launcher.parse_folder_name_metadata(os.path.basename(folder_path))
                # nfo_metadata = self.launcher.parse_nfo_file(folder_path) or {}
                # new_game_data["version"] = nfo_metadata.get('version', folder_metadata.get('year', ''))
                # ... etc ...

                # Dodaj do słownika gier do dodania
                games_to_add[final_name] = new_game_data
                imported_count += 1

        if games_to_add:
            logging.info(f"Importowanie {imported_count} gier do biblioteki.")
            # Dodaj wszystkie na raz do głównego słownika gier
            self.launcher.games.update(games_to_add)
            save_config(self.launcher.config)
            # --- NOWE: Wywołaj sprawdzenie osiągnięć w launcherze ---
            self.launcher.check_and_unlock_achievements()
            # Odśwież główny interfejs
            self.launcher.reset_and_update_grid()
            self.launcher.update_tag_filter_options()
            # Zaktualizuj listę gier w comboboxie roadmapy
            if hasattr(self.launcher, 'roadmap_game_name'):
                 self.launcher.root.after(20, lambda: setattr(self.launcher.roadmap_game_name, 'values', list(self.launcher.games.keys())))
            messagebox.showinfo("Import Zakończony", f"Pomyślnie zaimportowano {imported_count} gier.", parent=self.master) # parent=self.master odnosi się do głównego okna
        else:
            messagebox.showinfo("Import Anulowany", "Nie zaznaczono żadnych gier do importu.", parent=self.master)

        self.destroy() # Zamknij okno weryfikacji
