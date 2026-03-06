import os
import logging
import re
import time
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from launcher.utils import save_config


class AddProfileDialog(tk.Toplevel):
    """Małe okno dialogowe do dodawania/edycji profilu uruchomieniowego w oknie weryfikacji."""

    def __init__(
        self, parent, game_folder, existing_profiles, callback, initial_data=None
    ):
        super().__init__(parent)
        self.parent = parent
        self.game_folder = game_folder
        self.existing_profiles = existing_profiles
        self.callback = callback
        self.result = None

        is_edit = initial_data is not None
        title = (
            "Edytuj Profil Uruchomieniowy" if is_edit else "Dodaj Profil Uruchomieniowy"
        )
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        ttk.Label(
            self, text="Nazwa profilu:", background="#1e1e1e", foreground="white"
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_var = tk.StringVar(
            value=(
                initial_data["name"]
                if is_edit
                else f"Profil {len(existing_profiles) + 1}"
            )
        )
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(
            self, text="Plik .exe:", background="#1e1e1e", foreground="white"
        ).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.exe_var = tk.StringVar(
            value=(
                initial_data["exe_path"]
                if is_edit and initial_data.get("exe_path")
                else ""
            )
        )
        self.exe_entry = ttk.Entry(self, textvariable=self.exe_var, width=40, state="readonly")
        self.exe_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        exe_btn = ttk.Button(self, text="Wybierz...", command=self._select_exe)
        exe_btn.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(
            self, text="Argumenty:", background="#1e1e1e", foreground="white"
        ).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.args_var = tk.StringVar(value=initial_data["arguments"] if is_edit else "")
        self.args_entry = ttk.Entry(self, textvariable=self.args_var, width=40)
        self.args_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        save_button = ttk.Button(btn_frame, text="Zapisz", command=self._save)
        save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(btn_frame, text="Anuluj", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.name_entry.focus_set()
        self.wait_window(self)

    def _select_exe(self):
        """Otwiera dialog wyboru pliku .exe w folderze gry."""
        path = filedialog.askopenfilename(
            title="Wybierz plik wykonywalny dla profilu",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
            initialdir=self.game_folder,
            parent=self,
        )
        if path:
            if os.path.commonpath([self.game_folder, path]) == self.game_folder:
                self.exe_var.set(path)
            else:
                messagebox.showerror(
                    "Błąd ścieżki",
                    "Plik wykonywalny musi znajdować się w folderze gry lub jego podfolderze.",
                    parent=self,
                )

    def _save(self):
        """Waliduje i zapisuje dane profilu."""
        name = self.name_var.get().strip()
        exe_path = self.exe_var.get().strip() or None
        arguments = self.args_var.get().strip()

        if not name:
            messagebox.showerror("Błąd", "Nazwa profilu jest wymagana.", parent=self)
            return
        if not exe_path:
            messagebox.showerror(
                "Błąd",
                "Ścieżka pliku .exe jest wymagana dla dodatkowego profilu.",
                parent=self,
            )
            return

        self.result = {"name": name, "exe_path": exe_path, "arguments": arguments}
        self.callback(self.result)
        self.destroy()


class ScanVerificationWindow(tk.Toplevel):
    """Okno do weryfikacji gier znalezionych podczas skanowania."""

    def __init__(self, parent, launcher_instance, potential_games):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.potential_games_data = potential_games  # Przechowuje dane {'guessed_name', 'folder_path', 'suggested_exe_path', 'import', 'profiles'}
        self.row_widgets = (
            {}
        )  # Słownik do przechowywania widgetów dla każdego wiersza {iid: {var_import, name_entry, exe_label, profiles_data}}

        self.title("Weryfikacja Znalezionych Gier")
        self.configure(bg="#1e1e1e")
        self.geometry("900x600")
        self.minsize(700, 400)
        self.grab_set()

        # Nagłówek
        ttk.Label(
            self,
            text="Przejrzyj znalezione gry i zdecyduj, które zaimportować.",
            font=("Helvetica", 12),
        ).pack(pady=(10, 5))
        ttk.Label(
            self,
            text="Możesz edytować nazwę, zmienić główny plik .exe lub dodać dodatkowe profile uruchomieniowe.",
            font=("Helvetica", 9),
        ).pack(pady=(0, 10))

        # Ramka dla Treeview i Scrollbara
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Treeview
        columns = ("Import", "Nazwa Gry", "Główny Plik EXE", "Folder Gry", "Profile")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
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
        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
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
        ttk.Button(
            edit_buttons_frame, text="Zmień Nazwę", command=self.edit_selected_name
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            edit_buttons_frame,
            text="Zmień Główny .EXE",
            command=self.change_selected_exe,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            edit_buttons_frame,
            text="+ Dodaj Profil .EXE",
            command=self.add_profile_to_selected,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            edit_buttons_frame,
            text="- Usuń Profil",
            command=self.remove_profile_from_selected,
        ).pack(
            side=tk.LEFT, padx=2
        )  # Przycisk usuwania profilu

        # Przyciski importu i anulowania
        import_cancel_frame = ttk.Frame(action_frame)
        import_cancel_frame.pack(side=tk.RIGHT)
        ttk.Button(
            import_cancel_frame,
            text="Importuj Zaznaczone",
            style="Green.TButton",
            command=self.import_selected,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Button(import_cancel_frame, text="Anuluj", command=self.destroy).pack(
            side=tk.LEFT
        )

        # Bindowanie zdarzeń
        self.tree.bind(
            "<Double-1>", self.toggle_import_selected
        )  # Podwójne kliknięcie zmienia checkbox
        self.tree.tag_configure("checked", foreground="green")
        self.tree.tag_configure("unchecked", foreground="gray")

    def populate_tree(self):
        """Wypełnia Treeview danymi potencjalnych gier."""
        self.tree.delete(*self.tree.get_children())  # Wyczyść stare wpisy
        self.row_widgets.clear()  # Wyczyść powiązane dane

        for idx, game_info in enumerate(self.potential_games_data):
            iid = f"game_{idx}"  # Unikalny identyfikator wiersza
            import_status = "✔" if game_info.get("import", True) else "✖"
            tag = "checked" if game_info.get("import", True) else "unchecked"
            profiles_str = (
                ", ".join(
                    [
                        p["name"]
                        for p in game_info["profiles"]
                        if p["name"].lower() != "default"
                    ]
                )
                or "-"
            )

            values = (
                import_status,
                game_info["guessed_name"],
                game_info["suggested_exe_path"],
                game_info["folder_path"],
                profiles_str,
            )
            self.tree.insert("", "end", iid=iid, values=values, tags=(tag,))

            # Zapisz dane powiązane z wierszem (na razie tylko stan importu)
            self.row_widgets[iid] = {
                "import": tk.BooleanVar(value=game_info.get("import", True))
            }
            # W przyszłości można tu trzymać referencje do Entry itp. jeśli zmienimy UI

    def toggle_import_selected(self, event=None):
        """Przełącza status importu dla zaznaczonego wiersza."""
        selection = self.tree.selection()
        if not selection:
            return
        selected_iid = selection[0]

        if selected_iid in self.row_widgets:
            current_state = self.row_widgets[selected_iid]["import"].get()
            new_state = not current_state
            self.row_widgets[selected_iid]["import"].set(new_state)

            # Aktualizuj dane w oryginalnej liście
            try:
                index = int(selected_iid.split("_")[1])
                self.potential_games_data[index]["import"] = new_state
                # Aktualizuj wygląd w Treeview
                import_status = "✔" if new_state else "✖"
                tag = "checked" if new_state else "unchecked"
                # Pobierz istniejące wartości i zmień tylko pierwszą kolumnę
                current_values = list(self.tree.item(selected_iid, "values"))
                current_values[0] = import_status
                self.tree.item(selected_iid, values=tuple(current_values), tags=(tag,))
            except (IndexError, ValueError):
                logging.error(
                    f"Nie można zaktualizować stanu importu dla iid: {selected_iid}"
                )

    def edit_selected_name(self):
        """Pozwala edytować nazwę zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection:
            return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split("_")[1])
            current_name = self.potential_games_data[index]["guessed_name"]
            new_name = simpledialog.askstring(
                "Zmień Nazwę Gry",
                "Podaj nową nazwę dla:",
                initialvalue=current_name,
                parent=self,
            )
            if new_name and new_name.strip():
                new_name = new_name.strip()
                # Sprawdź, czy nowa nazwa nie koliduje z istniejącą w bibliotece lub w innym wierszu tego okna
                if new_name.lower() in (
                    name.lower() for name in self.launcher.games.keys()
                ):
                    messagebox.showerror(
                        "Błąd",
                        f"Gra o nazwie '{new_name}' już istnieje w bibliotece.",
                        parent=self,
                    )
                    return
                for i, game_info in enumerate(self.potential_games_data):
                    if (
                        i != index
                        and game_info["guessed_name"].lower() == new_name.lower()
                    ):
                        messagebox.showerror(
                            "Błąd",
                            f"Nazwa '{new_name}' jest już używana przez inną grę w tym oknie.",
                            parent=self,
                        )
                        return

                self.potential_games_data[index]["guessed_name"] = new_name
                # Aktualizuj Treeview
                current_values = list(self.tree.item(selected_iid, "values"))
                current_values[1] = new_name
                self.tree.item(selected_iid, values=tuple(current_values))
        except (IndexError, ValueError):
            logging.error(f"Nie można edytować nazwy dla iid: {selected_iid}")

    def change_selected_exe(self):
        """Pozwala zmienić główny plik .exe dla zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Najpierw zaznacz grę, której plik .exe chcesz zmienić.",
                parent=self,
            )
            return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split("_")[1])
            game_folder = self.potential_games_data[index]["folder_path"]
            current_name = self.potential_games_data[index][
                "guessed_name"
            ]  # Pobierz nazwę do tytułu okna

            new_exe = filedialog.askopenfilename(
                title=f"Wybierz główny plik .exe dla '{current_name}'",  # Użyj nazwy w tytule
                filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
                initialdir=game_folder,
                parent=self,
            )
            if new_exe:
                # --- POPRAWIONA WALIDACJA ---
                game_folder_abs = os.path.normcase(os.path.abspath(game_folder))
                new_exe_abs = os.path.normcase(os.path.abspath(new_exe))

                # Sprawdź, czy ścieżka absolutna pliku EXE zaczyna się od ścieżki absolutnej folderu gry
                # Dodajemy os.sep, aby upewnić się, że nie dopasujemy np. /path/to/game_folder_extra do /path/to/game_folder
                if (
                    new_exe_abs.startswith(game_folder_abs + os.sep)
                    or new_exe_abs == game_folder_abs
                ):  # Dodano sprawdzenie równości na wszelki wypadek

                    # Aktualizuj dane tymczasowe
                    self.potential_games_data[index]["suggested_exe_path"] = (
                        os.path.abspath(new_exe)
                    )  # Zapisz ścieżkę absolutną dla spójności

                    # Aktualizuj Treeview
                    current_values = list(self.tree.item(selected_iid, "values"))
                    current_values[2] = os.path.abspath(
                        new_exe
                    )  # Wyświetl ścieżkę absolutną
                    self.tree.item(selected_iid, values=tuple(current_values))
                    logging.info(
                        f"Zmieniono główny EXE dla '{current_name}' na: {new_exe}"
                    )
                else:
                    logging.warning(
                        f"Błąd walidacji ścieżki: '{new_exe}' nie znajduje się w '{game_folder}' lub jego podfolderach."
                    )
                    messagebox.showerror(
                        "Błąd ścieżki",
                        "Plik wykonywalny musi znajdować się w folderze gry lub jego podfolderze.\n\n"
                        f"Folder gry: {game_folder}\n"
                        f"Wybrany plik: {new_exe}",
                        parent=self,
                    )

        except (IndexError, ValueError):
            logging.error(f"Nie można zmienić EXE dla iid: {selected_iid}")
        except Exception as e:
            logging.exception(
                f"Nieoczekiwany błąd w change_selected_exe dla iid: {selected_iid}"
            )
            messagebox.showerror(
                "Błąd", f"Wystąpił nieoczekiwany błąd: {e}", parent=self
            )

    def add_profile_to_selected(self):
        """Dodaje nowy profil .exe dla zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection:
            return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split("_")[1])
            game_folder = self.potential_games_data[index]["folder_path"]
            current_profiles = self.potential_games_data[index]["profiles"]

            # Callback funkcja, która zostanie wywołana przez AddProfileDialog
            def profile_added_callback(new_profile_data):
                if new_profile_data:
                    # Dodaj nowy profil do danych tymczasowych
                    current_profiles.append(new_profile_data)
                    # Odśwież kolumnę 'Profile' w Treeview
                    profiles_str = (
                        ", ".join(
                            [
                                p["name"]
                                for p in current_profiles
                                if p["name"].lower() != "default"
                            ]
                        )
                        or "-"
                    )
                    current_values = list(self.tree.item(selected_iid, "values"))
                    current_values[4] = profiles_str
                    self.tree.item(selected_iid, values=tuple(current_values))

            # Otwórz dialog dodawania profilu
            AddProfileDialog(
                self, game_folder, current_profiles, profile_added_callback
            )

        except (IndexError, ValueError):
            logging.error(f"Nie można dodać profilu dla iid: {selected_iid}")

    def remove_profile_from_selected(self):
        """Usuwa wybrany profil z zaznaczonej gry."""
        selection = self.tree.selection()
        if not selection:
            return
        selected_iid = selection[0]
        try:
            index = int(selected_iid.split("_")[1])
            current_profiles = self.potential_games_data[index]["profiles"]

            # Pobierz nazwy profili (poza 'Default') do wyświetlenia
            profile_names = [
                p["name"] for p in current_profiles if p["name"].lower() != "default"
            ]
            if not profile_names:
                messagebox.showinfo(
                    "Brak profili",
                    "Ta gra nie ma dodatkowych profili do usunięcia.",
                    parent=self,
                )
                return

            # Użyj simpledialog.askstring z comboboxem (jeśli dostępny) lub listą
            # To jest ograniczenie simpledialog, lepiej byłoby stworzyć własne okno wyboru
            # Na razie użyjemy askstring i poinformujemy użytkownika
            chosen_name = simpledialog.askstring(
                "Usuń Profil",
                "Wpisz nazwę profilu do usunięcia z listy:\n\n"
                + "\n".join(profile_names),
                parent=self,
            )

            if chosen_name:
                chosen_name = chosen_name.strip()
                profile_to_remove = None
                for profile in current_profiles:
                    if (
                        profile.get("name", "").lower() == chosen_name.lower()
                        and chosen_name.lower() != "default"
                    ):
                        profile_to_remove = profile
                        break

                if profile_to_remove:
                    current_profiles.remove(profile_to_remove)
                    # Odśwież Treeview
                    profiles_str = (
                        ", ".join(
                            [
                                p["name"]
                                for p in current_profiles
                                if p["name"].lower() != "default"
                            ]
                        )
                        or "-"
                    )
                    current_values = list(self.tree.item(selected_iid, "values"))
                    current_values[4] = profiles_str
                    self.tree.item(selected_iid, values=tuple(current_values))
                    logging.info(
                        f"Usunięto profil '{chosen_name}' dla gry (w weryfikacji): {self.potential_games_data[index]['guessed_name']}"
                    )
                else:
                    messagebox.showwarning(
                        "Nie znaleziono",
                        f"Nie znaleziono profilu o nazwie '{chosen_name}' lub jest to profil 'Default'.",
                        parent=self,
                    )

        except (IndexError, ValueError):
            logging.error(f"Nie można usunąć profilu dla iid: {selected_iid}")

    def import_selected(self):
        """Importuje zaznaczone gry do biblioteki."""
        games_to_add = {}
        imported_count = 0

        for idx, game_info in enumerate(self.potential_games_data):
            iid = f"game_{idx}"
            # Sprawdź stan importu (z self.row_widgets lub bezpośrednio z game_info)
            should_import = (
                self.row_widgets[iid]["import"].get()
                if iid in self.row_widgets
                else game_info.get("import", False)
            )

            if should_import:
                final_name = game_info["guessed_name"]
                main_exe_path = game_info["suggested_exe_path"]
                folder_path = game_info["folder_path"]
                # Przygotuj listę profili
                final_profiles = []
                # Główny exe jako profil "Default", jeśli nie ma innych profili LUB jeśli explicitnie dodano profil z tym exe
                # Logika: pierwszy profil na liście game_info['profiles'] to ZAWSZE domyślny logicznie
                default_profile_data = game_info["profiles"][
                    0
                ]  # Zawsze jest co najmniej jeden
                default_profile_data["exe_path"] = (
                    None  # Sygnalizuje użycie głównego exe gry
                )
                final_profiles.append(default_profile_data)

                # Dodaj pozostałe zdefiniowane profile (jeśli są)
                for profile_data in game_info["profiles"][
                    1:
                ]:  # Pomiń pierwszy (domyślny)
                    # Sprawdź, czy ścieżka exe nie jest taka sama jak główna
                    if profile_data.get("exe_path") != main_exe_path:
                        final_profiles.append(profile_data)
                    else:
                        # Jeśli ktoś dodał profil z tym samym exe co główny, zignoruj go,
                        # chyba że ma inne argumenty? Na razie ignorujemy.
                        logging.warning(
                            f"Profil '{profile_data.get('name')}' dla '{final_name}' używa tej samej ścieżki co główny plik. Ignorowanie nadmiarowego profilu."
                        )

                # Podstawowe dane nowej gry
                new_game_data = {
                    "name": final_name,
                    "exe_path": main_exe_path,
                    "folder_path": folder_path,  # Możemy zapisać folder dla informacji
                    "save_path": "",  # Domyślnie puste
                    "cover_image": "",  # Domyślnie puste
                    "genres": [],
                    "rating": None,
                    "version": "",
                    "tags": [],
                    "notes": "",
                    "date_added": time.time(),
                    "play_time": 0,
                    "completion": 0,
                    "last_played": None,
                    "play_sessions": [],
                    "launch_profiles": final_profiles,  # Zapisz przygotowaną listę profili
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
            self.launcher.check_and_unlock_achievements()
            # Odśwież główny interfejs
            self.launcher.reset_and_update_grid()
            self.launcher.update_tag_filter_options()
            # Zaktualizuj listę gier w comboboxie roadmapy
            if hasattr(self.launcher, "roadmap_game_name"):
                self.launcher.root.after(
                    20,
                    lambda: setattr(
                        self.launcher.roadmap_game_name,
                        "values",
                        list(self.launcher.games.keys()),
                    ),
                )
            messagebox.showinfo(
                "Import Zakończony",
                f"Pomyślnie zaimportowano {imported_count} gier.",
                parent=self.master,
            )  # parent=self.master odnosi się do głównego okna
        else:
            messagebox.showinfo(
                "Import Anulowany",
                "Nie zaznaczono żadnych gier do importu.",
                parent=self.master,
            )

        self.destroy()  # Zamknij okno weryfikacji


class AchievementForm(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji definicji osiągnięcia."""

    def __init__(self, parent, initial_data=None, launcher_instance=None):
        super().__init__(parent)
        self.parent = parent
        self._start_time = 0.0  # kiedy faktycznie gra (sec, monotonic)
        self._pause_acc = 0.0  # suma czasu spędzonego w pauzie
        self.launcher = launcher_instance
        if not self.launcher:
            # Fallback, jeśli launcher nie został przekazany (choć powinien)
            # Można by zgłosić błąd lub spróbować znaleźć instancję inaczej
            raise ValueError("AchievementForm wymaga instancji GameLauncher!")
        self.result = None  # Przechowa wynikowy słownik definicji

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
        main_frame.columnconfigure(1, weight=1)  # Rozciągnij kolumnę z polami

        # ID (nieedytowalne podczas edycji?) - Można pozwolić na edycję, ale z ostrzeżeniem
        ttk.Label(main_frame, text="ID Osiągnięcia:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.id_var = tk.StringVar(value=initial_data.get("id", "") if is_edit else "")
        self.id_entry = ttk.Entry(main_frame, textvariable=self.id_var, width=40)
        self.id_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if is_edit:
            self.id_entry.config(state="readonly")  # Zablokuj ID podczas edycji

        # Nazwa
        ttk.Label(main_frame, text="Nazwa Wyświetlana:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.name_var = tk.StringVar(
            value=initial_data.get("name", "") if is_edit else ""
        )
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # Opis
        ttk.Label(main_frame, text="Opis:").grid(
            row=2, column=0, padx=5, pady=5, sticky="nw"
        )
        self.desc_text = tk.Text(
            main_frame, height=4, width=40, wrap=tk.WORD, relief=tk.FLAT
        )
        style = ttk.Style()
        text_bg = style.lookup("TEntry", "fieldbackground")
        text_fg = style.lookup("TEntry", "foreground")
        self.desc_text.config(
            background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1
        )
        self.desc_text.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        if is_edit:
            self.desc_text.insert("1.0", initial_data.get("description", ""))
        desc_scroll = ttk.Scrollbar(
            main_frame, orient="vertical", command=self.desc_text.yview
        )
        desc_scroll.grid(row=2, column=3, sticky="ns", pady=5)
        self.desc_text.config(yscrollcommand=desc_scroll.set)

        # Ikona
        ttk.Label(main_frame, text="Ikona (ścieżka):").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )
        self.icon_var = tk.StringVar(
            value=initial_data.get("icon", "") if is_edit else ""
        )
        self.icon_entry = ttk.Entry(main_frame, textvariable=self.icon_var, width=40)
        self.icon_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        icon_btn = ttk.Button(main_frame, text="Wybierz...", command=self._select_icon)
        icon_btn.grid(row=3, column=2, padx=5, pady=5)

        # Typ Reguły
        # --- Typ Warunku (Combobox) ---
        ttk.Label(main_frame, text="Typ Warunku:").grid(
            row=4, column=0, padx=5, pady=5, sticky="w"
        )
        self.rule_type_map = self.launcher.ACHIEVEMENT_RULE_TYPES_TRANSLATED
        self.available_rule_types = list(
            self.rule_type_map.keys()
        )  # Zaczynamy od wszystkich
        # if "news_read" in self.available_rule_types: self.available_rule_types.remove("news_read") # Usuń, jeśli nie zrobione
        display_rule_types = list(self.rule_type_map.values())

        # Pobierz techniczną nazwę dla wartości początkowej
        initial_technical_rule = (
            initial_data.get("rule_type", "")
            if is_edit
            else list(self.rule_type_map.keys())[0]
        )
        # Znajdź odpowiadającą jej nazwę wyświetlaną
        initial_display_rule = self.rule_type_map.get(
            initial_technical_rule, display_rule_types[0]
        )

        self.rule_type_display_var = tk.StringVar(
            value=initial_display_rule
        )  # Zmienna przechowuje nazwę wyświetlaną
        self.rule_type_display_var.trace_add("write", self._update_value_widget)
        rule_combo = ttk.Combobox(
            main_frame,
            textvariable=self.rule_type_display_var,
            values=display_rule_types,
            state="readonly",
        )
        rule_combo.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        # --- Wartość Docelowa LUB Wybór Wartości ---
        # Ramka na widget wartości (będzie zawierać Entry LUB Combobox)
        self.value_frame = ttk.Frame(main_frame)
        self.value_frame.grid(
            row=5, column=1, columnspan=2, padx=5, pady=5, sticky="ew"
        )
        self.value_frame.columnconfigure(0, weight=1)  # Pozwól widgetowi się rozciągnąć

        ttk.Label(main_frame, text="Wartość/Cel:").grid(
            row=5, column=0, padx=5, pady=5, sticky="w"
        )

        # Widgety dla wartości (tworzone, ale początkowo ukryte/zarządzane przez _update_value_widget)
        self.target_value_var = tk.StringVar(
            value=str(initial_data.get("target_value", "")) if is_edit else "1"
        )
        self.target_value_entry = ttk.Entry(
            self.value_frame, textvariable=self.target_value_var, width=10
        )
        # Początkowo umieszczamy Entry
        self.target_value_entry.grid(row=0, column=0, sticky="w")

        self.value_select_var = tk.StringVar()  # Dla Comboboxa gatunku/tagu/grupy
        self.value_select_combo = ttk.Combobox(
            self.value_frame,
            textvariable=self.value_select_var,
            state="readonly",
            width=35,
        )
        # Nie umieszczamy Comboboxa w gridzie od razu

        self.extra_param_var = tk.StringVar(
            value=(
                initial_data.get(
                    "genre", initial_data.get("tag", initial_data.get("group", ""))
                )
                if is_edit
                else ""
            )
        )

        # Ukryty (przesunięty wiersz)
        self.hidden_var = tk.BooleanVar(
            value=initial_data.get("hidden", False) if is_edit else False
        )
        hidden_check = ttk.Checkbutton(
            main_frame, text="Ukryte (do odblokowania)", variable=self.hidden_var
        )
        hidden_check.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # Przyciski Zapisz/Anuluj (przesunięty wiersz)
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=4, pady=15)
        ttk.Button(button_frame, text="Zapisz", command=self._save).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(
            side=tk.LEFT, padx=10
        )

        # Wywołaj raz, aby ustawić poprawny widget wartości
        self._update_value_widget()

        self.name_entry.focus_set()
        self.wait_window(self)

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
            if isinstance(widget, ttk.Label):
                widget.grid_remove()

        list_selection_rules = [
            "genre_played_count",
            "tag_played_count",
            "group_played_count",
            "genre_completed_100",
            "tag_completed_100",
            "group_completed_100",
        ]
        is_list_rule_now = technical_rule_type in list_selection_rules

        if is_list_rule_now:
            # Pokaż Combobox i wypełnij go
            options = []
            current_extra_param = (
                self.extra_param_var.get()
            )  # Pobierz zapamiętaną wartość dodatkową
            selected_value = ""  # Co ustawić w Comboboxie

            if "genre" in technical_rule_type:
                options = self.launcher.get_all_genres()
                selected_value = (
                    current_extra_param
                    if current_extra_param in options
                    else (options[0] if options else "")
                )
            elif "tag" in technical_rule_type:
                options = self.launcher.get_all_tags()
                selected_value = (
                    current_extra_param
                    if current_extra_param in options
                    else (options[0] if options else "")
                )
            elif "group" in technical_rule_type:
                options = list(self.launcher.groups.keys())
                selected_value = (
                    current_extra_param
                    if current_extra_param in options
                    else (options[0] if options else "")
                )

            self.value_select_combo["values"] = options
            self.value_select_var.set(selected_value)  # Ustaw wartość w Comboboxie
            self.value_select_combo.grid(row=0, column=0, sticky="ew")

            # Pokaż etykietę i Entry dla liczby
            ttk.Label(self.value_frame, text="Liczba gier:").grid(
                row=1, column=0, sticky="w", pady=(5, 0)
            )
            if not was_list_rule:
                self.target_value_var.set("1")  # Ustaw domyślną wartość "1"
            self.target_value_entry.grid(row=1, column=1, sticky="w", pady=(5, 0))
        else:
            # Pokaż tylko Entry dla wartości docelowej
            if was_list_rule:
                # Ustaw domyślną "1" lub inną sensowną wartość? Na razie "1".
                self.target_value_var.set("1")
            self.target_value_entry.grid(row=0, column=0, sticky="w")

    def _select_icon(self):
        """Otwiera dialog wyboru pliku ikony."""
        # Zacznij w folderze 'icons' jeśli istnieje, inaczej w folderze aplikacji
        initial_dir = "icons" if os.path.isdir("icons") else "."
        path = filedialog.askopenfilename(
            title="Wybierz plik ikony osiągnięcia",
            filetypes=[("Obrazy PNG", "*.png"), ("Wszystkie pliki", "*.*")],
            initialdir=initial_dir,
            parent=self,  # Ustaw to okno jako rodzica
        )
        if path:
            # Spróbuj zapisać ścieżkę względną, jeśli jest w podfolderze 'icons'
            try:
                rel_path = os.path.relpath(path, os.getcwd())
                if not rel_path.startswith(
                    ".."
                ):  # Jeśli jest w bieżącym folderze lub podfolderze
                    self.icon_var.set(rel_path.replace("\\", "/"))  # Użyj slashy
                    return
            except ValueError:  # Różne dyski
                pass
            # Jeśli nie da się względnej, zapisz absolutną
            self.icon_var.set(path.replace("\\", "/"))

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

        target_str = ""  # Domyślnie pusty
        list_selection_rules = [
            "genre_played_count",
            "tag_played_count",
            "group_played_count",
            "genre_completed_100",
            "tag_completed_100",
            "group_completed_100",
        ]
        is_list_rule = rule_type in list_selection_rules

        if is_list_rule:
            # Pobierz wartość celu (liczbę) z Entry
            target_str = self.target_value_entry.get().strip()
            # Pobierz dodatkowy parametr (gatunek/tag/grupa) z Comboboxa
            extra_param_value = self.value_select_var.get()
            if not extra_param_value:
                messagebox.showerror(
                    "Błąd",
                    f"Wybierz {rule_type.split('_')[0]} dla tego typu warunku.",
                    parent=self,
                )
                return
            # Ustal klucz dla dodatkowego parametru
            if "genre" in rule_type:
                extra_param_key = "genre"
            elif "tag" in rule_type:
                extra_param_key = "tag"
            elif "group" in rule_type:
                extra_param_key = "group"
        else:
            # Pobierz wartość celu (liczbę/czas) z Entry
            target_str = (
                self.target_value_entry.get().strip()
            )  # Poprzednio było self.target_var

        # Walidacja podstawowa
        if not ach_id or not name or not description or not rule_type or not target_str:
            messagebox.showerror(
                "Błąd",
                "ID, Nazwa, Opis, Typ Warunku i Wartość/Cel są wymagane.",
                parent=self,
            )
            return
        if not re.match(r"^[a-zA-Z0-9_]+$", ach_id):
            messagebox.showerror("Błąd", "...", parent=self)
            return

        # Walidacja wartości docelowej
        try:
            if rule_type in ["total_playtime_hours", "playtime_single_game_hours"]:
                target_value = float(target_str)
            else:
                target_value = int(target_str)
            if target_value <= 0:
                raise ValueError("Wartość musi być dodatnia")
        except ValueError as e:
            messagebox.showerror(
                "Błąd",
                f"Nieprawidłowa wartość docelowa: Musi być liczbą większą od zera.\n({e})",
                parent=self,
            )
            return

        # Walidacja ikony
        if icon_path and not os.path.exists(icon_path):
            messagebox.showwarning("Ostrzeżenie", "...", parent=self)
            icon_path = ""

        # Przygotuj słownik wynikowy
        self.result = {
            "id": ach_id,
            "name": name,
            "description": description,
            "icon": icon_path,
            "rule_type": rule_type,
            "target_value": target_value,
            "hidden": is_hidden,
        }
        if extra_param_key and extra_param_value:
            self.result[extra_param_key] = extra_param_value

        self.destroy()


class ChatServerEditorDialog(tk.Toplevel):
    def __init__(self, parent, launcher_instance, existing_server_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None  # Przechowa dane serwera {'id':..., 'name':..., 'url':..., 'is_default':...}

        self.is_edit_mode = existing_server_data is not None
        self.existing_server_data_for_edit = (
            existing_server_data  # Zapisujemy, aby mieć dostęp w _save
        )
        self.original_server_id = (
            existing_server_data.get("id") if self.is_edit_mode else None
        )
        self.original_server_name = (
            existing_server_data.get("name") if self.is_edit_mode else None
        )

        title = (
            "Edytuj Serwer Czatu" if self.is_edit_mode else "Dodaj Nowy Serwer Czatu"
        )
        self.title(title)
        self.configure(bg=self.launcher.settings.get("background", "#1e1e1e"))
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        # --- Zmienne Tkinter ---
        self.server_name_var = tk.StringVar(
            value=(
                existing_server_data.get("name", "")
                if self.is_edit_mode
                else "Nowy Serwer"
            )
        )
        self.server_url_var = tk.StringVar(
            value=(
                existing_server_data.get("url", "http://")
                if self.is_edit_mode
                else "http://127.0.0.1:5000"
            )
        )
        self.is_default_var = tk.BooleanVar(
            value=(
                existing_server_data.get("is_default", False)
                if self.is_edit_mode
                else False
            )
        )

        # --- Główna Ramka ---
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Nazwa Serwera:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        name_entry = ttk.Entry(main_frame, textvariable=self.server_name_var, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(main_frame, text="Adres URL Serwera:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        url_entry = ttk.Entry(main_frame, textvariable=self.server_url_var, width=40)
        url_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        default_check = ttk.Checkbutton(
            main_frame, text="Ustaw jako domyślny serwer", variable=self.is_default_var
        )
        default_check.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="w")

        # Przyciski
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(button_frame, text="Zapisz", command=self._save_server_data).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT)

        name_entry.focus_set()
        if not self.is_edit_mode:  # Zaznacz tekst tylko przy dodawaniu
            name_entry.selection_range(0, tk.END)

        self.wait_window(self)

    def _save_server_data(self):
        name = self.server_name_var.get().strip()
        url = self.server_url_var.get().strip()
        is_default = self.is_default_var.get()

        if not name:
            messagebox.showerror(
                "Brak Nazwy", "Nazwa serwera nie może być pusta.", parent=self
            )
            return
        if not url:
            messagebox.showerror(
                "Brak URL", "Adres URL serwera nie może być pusty.", parent=self
            )
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror(
                "Nieprawidłowy URL",
                "Adres URL serwera musi zaczynać się od http:// lub https://",
                parent=self,
            )
            return

        # Sprawdź unikalność nazwy (poza edytowanym serwerem)
        for server in self.launcher.chat_servers_list:
            if self.is_edit_mode and server.get("id") == self.original_server_id:
                continue  # Pomiń sprawdzanie samego siebie przy edycji
            if server.get("name", "").lower() == name.lower():
                messagebox.showerror(
                    "Nazwa Zajęta",
                    f"Serwer o nazwie '{name}' już istnieje.",
                    parent=self,
                )
                return

        # Jeśli ustawiono jako domyślny, odznacz inne domyślne
        if is_default:
            for server in self.launcher.chat_servers_list:
                # Jeśli edytujemy i to jest ten sam serwer, nie odznaczaj go.
                # Inaczej, jeśli inny serwer ma być domyślny, odznacz ten.
                if self.is_edit_mode and server.get("id") == self.original_server_id:
                    pass  # Nie modyfikujemy is_default dla edytowanego serwera tutaj, zrobimy to w self.result
                elif server.get("id") != (
                    self.original_server_id if self.is_edit_mode else None
                ):  # Dla nowego, odznacz wszystkie inne
                    server["is_default"] = False

        # Przygotuj dane do zwrócenia
        current_credentials = {}
        current_remember = False
        current_auto_login = False
        last_used_timestamp = None  # Domyślnie None dla nowych

        if (
            self.is_edit_mode and self.existing_server_data_for_edit
        ):  # Użyj zapisanego atrybutu
            current_credentials = self.existing_server_data_for_edit.get(
                "credentials", {}
            )
            current_remember = self.existing_server_data_for_edit.get(
                "remember_credentials", False
            )
            current_auto_login = self.existing_server_data_for_edit.get(
                "auto_login_to_server", False
            )
            last_used_timestamp = self.existing_server_data_for_edit.get(
                "last_used"
            )  # Zachowaj last_used przy edycji

        # Jeśli zmieniono URL, najlepiej wyczyścić zapamiętane dane (lub zapytać użytkownika)
        # Na razie, jeśli URL się zmienił, a to edycja, wyczyścimy dane logowania, bo mogą nie pasować.
        if (
            self.is_edit_mode
            and self.existing_server_data_for_edit
            and self.existing_server_data_for_edit.get("url") != url
        ):
            current_credentials = {}
            current_remember = False
            current_auto_login = False
            logging.info(
                f"URL serwera '{name}' zmieniony. Wyczyszczono zapamiętane dane logowania dla tego serwera."
            )

        self.result = {
            "id": self.original_server_id if self.is_edit_mode else str(uuid.uuid4()),
            "name": name,
            "url": url,
            "is_default": is_default,
            "last_used": last_used_timestamp,
            "credentials": current_credentials,
            "remember_credentials": current_remember,
            "auto_login_to_server": current_auto_login,
        }
        self.destroy()


__all__ = [
    "AddProfileDialog",
    "ScanVerificationWindow",
    "AchievementForm",
    "ChatServerEditorDialog",
]
