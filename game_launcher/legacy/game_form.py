"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class GameForm:
    def __init__(self, parent, title, game_name="", game_data=None):
        self.parent = parent
        self.top = tk.Toplevel(parent.root)
        self.top.title(title)
        self.top.configure(bg="#1e1e1e")
        self.top.grab_set()
        self.top.minsize(600, 700) # Zwiększmy trochę minimalną wysokość

        self._current_profiles = game_data.get("launch_profiles", []) if game_data else [{"name": "Default", "exe_path": None, "arguments": ""}]
        # Zapewnij istnienie domyślnego profilu
        if not any(p.get("name", "").lower() == "default" for p in self._current_profiles):
            self._current_profiles.insert(0, {"name": "Default", "exe_path": None, "arguments": ""})

        self.result = None
        self.game_data = game_data.copy() if game_data else {} # Pracuj na kopii

        # --- NOWE: Typ Gry ---
        self.game_type_var = tk.StringVar(value=self.game_data.get("game_type", "pc")) # Domyślnie "pc"
        self.game_type_var.trace_add("write", self._on_game_type_change) # Śledź zmiany

        ttk.Label(self.top, text="Typ gry:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        game_type_combo = ttk.Combobox(self.top, textvariable=self.game_type_var, values=["pc", "emulator"], state="readonly", width=15)
        game_type_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        # --- KONIEC NOWEGO ---

        # --- ZMIANA: Przesunięcie Nazwy Gry do wiersza 1 ---
        ttk.Label(self.top, text="Nazwa gry:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = ttk.Entry(self.top)
        self.name_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.name_entry.insert(0, game_name)
        # --- KONIEC ZMIANY ---

        # --- Pola specyficzne dla "Gra PC" ---
        self.pc_game_widgets = [] # Lista widgetów do pokazywania/ukrywania
        self.pc_exe_label = ttk.Label(self.top, text="Ścieżka .exe (PC):")
        self.pc_exe_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.exe_entry = ttk.Entry(self.top)
        self.exe_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.pc_exe_btn = ttk.Button(self.top, text="Wybierz...", command=self.select_exe)
        self.pc_exe_btn.grid(row=2, column=2, padx=5, pady=5)
        self.pc_game_widgets.extend([self.pc_exe_label, self.exe_entry, self.pc_exe_btn])

        # --- Pola specyficzne dla "Gra Emulowana" ---
        self.emulator_game_widgets = [] # Lista widgetów do pokazywania/ukrywania
        self.emu_select_label = ttk.Label(self.top, text="Wybierz Emulator:")
        self.emu_select_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.emulator_var = tk.StringVar()
        # Pobierz listę nazw skonfigurowanych emulatorów
        emulator_names = list(self.parent.config.get("emulators", {}).keys())
        self.emulator_combo = ttk.Combobox(self.top, textvariable=self.emulator_var, values=emulator_names, state="readonly")
        self.emulator_combo.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.emulator_game_widgets.extend([self.emu_select_label, self.emulator_combo])

        self.rom_label = ttk.Label(self.top, text="Ścieżka ROM/ISO:")
        self.rom_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.rom_entry = ttk.Entry(self.top)
        self.rom_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.rom_btn = ttk.Button(self.top, text="Wybierz...", command=self.select_rom)
        self.rom_btn.grid(row=4, column=2, padx=5, pady=5)
        self.emulator_game_widgets.extend([self.rom_label, self.rom_entry, self.rom_btn])

        self.emu_args_label = ttk.Label(self.top, text="Argumenty Emulatora:")
        self.emu_args_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.emu_args_entry = ttk.Entry(self.top)
        self.emu_args_entry.grid(row=5, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.emulator_game_widgets.extend([self.emu_args_label, self.emu_args_entry])

        # --- Pozostałe pola (wspólne lub przesunięte) ---
        current_form_row = 6 # Zacznij od następnego wolnego wiersza

        ttk.Label(self.top, text="Ścieżka zapisów:").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="w"); current_form_row += 1
        self.save_entry = ttk.Entry(self.top)
        self.save_entry.grid(row=current_form_row -1, column=1, padx=10, pady=5, sticky="ew") # Użyj poprzedniego wiersza
        save_btn = ttk.Button(self.top, text="Wybierz...", command=self.select_save)
        save_btn.grid(row=current_form_row -1, column=2, padx=5, pady=5)

        ttk.Label(self.top, text="Okładka:").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="w"); current_form_row += 1
        self.cover_entry = ttk.Entry(self.top)
        self.cover_entry.grid(row=current_form_row -1, column=1, padx=10, pady=5, sticky="ew")
        cover_btn = ttk.Button(self.top, text="Wybierz...", command=self.select_cover)
        cover_btn.grid(row=current_form_row -1, column=2, padx=5, pady=5)

        # Gatunki
        ttk.Label(self.top, text="Gatunki:").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="nw"); current_form_row += 1
        genres_frame = ttk.Frame(self.top)
        genres_frame.grid(row=current_form_row -1, column=1, padx=10, pady=5, sticky="nsew") # Użyj poprzedniego wiersza
        genres_frame.columnconfigure(0, weight=1); genres_frame.rowconfigure(0, weight=1)
        self.genres_listbox = tk.Listbox(genres_frame, selectmode=tk.MULTIPLE, height=5)
        self.genres_listbox.grid(row=0, column=0, sticky="nsew")
        genres_scrollbar = ttk.Scrollbar(genres_frame, orient="vertical", command=self.genres_listbox.yview)
        genres_scrollbar.grid(row=0, column=1, sticky="ns")
        self.genres_listbox.config(yscrollcommand=genres_scrollbar.set)
        genres_btn = ttk.Button(self.top, text="Zarządzaj Gatunkami", command=self.parent.manage_genres)
        genres_btn.grid(row=current_form_row -1, column=2, padx=5, pady=5, sticky="n")
        self.all_genres = self.parent.get_all_genres()
        for genre in self.all_genres: self.genres_listbox.insert(tk.END, genre)

        ttk.Label(self.top, text="Ocena (1-10):").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="w"); current_form_row += 1
        self.rating_entry = ttk.Entry(self.top)
        self.rating_entry.grid(row=current_form_row -1, column=1, columnspan=2, padx=10, pady=5, sticky="ew") # Użyj poprzedniego wiersza

        ttk.Label(self.top, text="Wersja gry:").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="w"); current_form_row += 1
        self.version_entry = ttk.Entry(self.top)
        self.version_entry.grid(row=current_form_row -1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(self.top, text="Tagi (oddzielone przecinkami):").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="w"); current_form_row += 1
        self.tags_entry = ttk.Entry(self.top)
        self.tags_entry.grid(row=current_form_row -1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(self.top, text="Notatki:").grid(row=current_form_row, column=0, padx=10, pady=5, sticky="nw"); current_form_row += 1
        self.notes_text = tk.Text(self.top, height=6, wrap=tk.WORD, relief=tk.FLAT)
        style = ttk.Style(); text_bg = style.lookup('TEntry', 'fieldbackground'); text_fg = style.lookup('TEntry', 'foreground')
        self.notes_text.config(background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1)
        self.notes_text.grid(row=current_form_row -1, column=1, columnspan=2, padx=10, pady=5, sticky="nsew")
        notes_scrollbar = ttk.Scrollbar(self.top, orient="vertical", command=self.notes_text.yview)
        notes_scrollbar.grid(row=current_form_row -1, column=3, padx=(0,10), pady=5, sticky="ns")
        self.notes_text.config(yscrollcommand=notes_scrollbar.set)

        # Profile Uruchomieniowe (ukryte dla gier emulowanych)
        self.pc_profiles_frame = ttk.LabelFrame(self.top, text=" Profile Uruchomieniowe (PC) ", padding=(10, 5))
        self.pc_profiles_frame.grid(row=current_form_row, column=0, columnspan=4, sticky="nsew", padx=10, pady=(10, 5))
        self.pc_profiles_frame.columnconfigure(0, weight=1)
        self.pc_profiles_frame.rowconfigure(0, weight=1)
        self.pc_game_widgets.append(self.pc_profiles_frame) # Dodaj do listy ukrywanych
        # ... (kod Treeview i przycisków dla profili PC wewnątrz pc_profiles_frame) ...
        profile_tree_frame = ttk.Frame(self.pc_profiles_frame); profile_tree_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5); profile_tree_frame.columnconfigure(0, weight=1); profile_tree_frame.rowconfigure(0, weight=1)
        profile_columns = ("Profil", "Argumenty", "Spec. EXE"); self.profile_tree = ttk.Treeview(profile_tree_frame, columns=profile_columns, show="headings", height=4, selectmode="browse")
        self.profile_tree.heading("Profil", text="Nazwa Profilu"); self.profile_tree.heading("Argumenty", text="Argumenty"); self.profile_tree.heading("Spec. EXE", text="Ścieżka EXE (jeśli inna)")
        self.profile_tree.column("Profil", width=120, anchor=tk.W); self.profile_tree.column("Argumenty", width=150, anchor=tk.W); self.profile_tree.column("Spec. EXE", width=180, anchor=tk.W)
        profile_scrollbar = ttk.Scrollbar(profile_tree_frame, orient="vertical", command=self.profile_tree.yview); self.profile_tree.configure(yscrollcommand=profile_scrollbar.set)
        self.profile_tree.grid(row=0, column=0, sticky="nsew"); profile_scrollbar.grid(row=0, column=1, sticky="ns")
        profile_buttons_frame = ttk.Frame(self.pc_profiles_frame); profile_buttons_frame.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(profile_buttons_frame, text="Dodaj Profil", command=self.add_edit_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(profile_buttons_frame, text="Edytuj Zaznaczony", command=lambda: self.add_edit_profile(edit_mode=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(profile_buttons_frame, text="Usuń Zaznaczony", command=self.delete_profile).pack(side=tk.LEFT, padx=5)
        current_form_row += 1


        # Przyciski Główne (Zapisz, Anuluj, etc.)
        button_frame = ttk.Frame(self.top)
        button_frame.grid(row=current_form_row, column=0, columnspan=4, pady=15, sticky="e") # Użyj ostatniego wiersza
        # ... (przyciski Parsuj, Zapisz, Anuluj) ...
        parse_nfo_btn = ttk.Button(button_frame, text="Parsuj .NFO", command=self.parse_nfo_action); parse_nfo_btn.pack(side=tk.LEFT, padx=5)
        parse_folder_btn = ttk.Button(button_frame, text="Parsuj Nazwę Fold.", command=self.parse_folder_action); parse_folder_btn.pack(side=tk.LEFT, padx=5)
        save_btn = ttk.Button(button_frame, text="Zapisz", command=self.save); save_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(button_frame, text="Anuluj", command=self.top.destroy); cancel_btn.pack(side=tk.LEFT, padx=5)

        # Konfiguracja rozciągania
        self.top.columnconfigure(1, weight=1)
        self.top.rowconfigure(current_form_row -1, weight=1) # Ostatni wiersz z zawartością (np. Profile lub Notatki) się rozciąga

        # Wypełnianie danych (jeśli edycja)
        if self.game_data:
            # Nazwa gry jest zablokowana tylko w trybie edycji
            if title == "Edytuj Grę":
                 self.name_entry.config(state='disabled')

            # Ustaw wartości dla typu gry
            self.game_type_var.set(self.game_data.get("game_type", "pc"))
            if self.game_data.get("game_type") == "emulator":
                self.emulator_var.set(self.game_data.get("emulator_name", ""))
                self.rom_entry.insert(0, self.game_data.get("rom_path", ""))
                self.emu_args_entry.insert(0, self.game_data.get("emulator_args", ""))
            else: # Dla PC
                self.exe_entry.insert(0, self.game_data.get("exe_path", ""))
                self.refresh_profile_treeview() # Wypełnij profile PC

            # Wypełnij resztę pól (już z uwzględnieniem None)
            save_path = self.game_data.get("save_path")
            self.save_entry.insert(0, save_path if save_path is not None else "")
            cover_path = self.game_data.get("cover_image")
            self.cover_entry.insert(0, cover_path if cover_path is not None else "")
            rating_value = self.game_data.get("rating")
            self.rating_entry.insert(0, str(rating_value) if rating_value is not None else "")
            version_val = self.game_data.get("version")
            self.version_entry.insert(0, version_val if version_val is not None else "")
            tags_list = self.game_data.get("tags", [])
            self.tags_entry.insert(0, ", ".join(tags_list) if tags_list else "")
            notes_val = self.game_data.get("notes", "")
            self.notes_text.insert("1.0", notes_val if notes_val is not None else "")
            if self.game_data.get("genres"):
                for genre in self.game_data["genres"]:
                    if genre in self.all_genres:
                        try: index = self.all_genres.index(genre); self.genres_listbox.selection_set(index)
                        except ValueError: logging.warning(f"Gatunek '{genre}' z danych gry nie znaleziony w liście.")

        # Wywołaj raz, aby ustawić początkową widoczność pól
        self._on_game_type_change()

    # --- NOWA METODA: Obsługa zmiany typu gry ---
    def _on_game_type_change(self, *args):
        """Pokazuje/ukrywa pola w zależności od wybranego typu gry."""
        game_type = self.game_type_var.get()
        if game_type == "emulator":
            # Pokaż widgety emulatora, ukryj widgety PC
            for widget in self.pc_game_widgets:
                widget.grid_remove()
            for widget in self.emulator_game_widgets:
                widget.grid() # Użyj grid() bez parametrów, aby przywrócić do siatki
        else: # game_type == "pc"
            # Pokaż widgety PC, ukryj widgety emulatora
            for widget in self.emulator_game_widgets:
                widget.grid_remove()
            for widget in self.pc_game_widgets:
                widget.grid()

    # --- NOWA METODA: Wybór ROM/ISO ---
    def select_rom(self):
        """Otwiera dialog wyboru pliku ROM/ISO."""
        # Można dodać sugerowane typy plików
        filetypes = [
            ("Wszystkie obsługiwane", "*.iso *.bin *.cue *.gcm *.rvz *.wbfs *.wad *.nca *.nsp *.xci *.rom *.nes *.sfc *.smc *.md *.gen *.sms *.gg *.pce *.sgx *.zip *.7z"),
            ("Obrazy Dysków", "*.iso *.bin *.cue *.gcm *.rvz *.wbfs"),
            ("Pliki Nintendo", "*.wad *.nca *.nsp *.xci *.nes *.sfc *.smc"),
            ("Pliki Sega", "*.md *.gen *.sms *.gg"),
            ("Pliki PC Engine", "*.pce *.sgx"),
            ("Archiwa", "*.zip *.7z"),
            ("Wszystkie pliki", "*.*")
        ]
        path = filedialog.askopenfilename(title="Wybierz plik ROM/ISO gry", filetypes=filetypes)
        if path:
            self.rom_entry.delete(0, tk.END)
            self.rom_entry.insert(0, path)

    # --- NOWA METODA: Aktualizacja listy emulatorów ---
    def update_emulator_list(self):
        """Odświeża listę emulatorów w Combobox."""
        if hasattr(self, 'emulator_combo') and self.emulator_combo.winfo_exists():
            emulator_names = list(self.parent.config.get("emulators", {}).keys())
            self.emulator_combo['values'] = emulator_names
            # Opcjonalnie: sprawdź, czy aktualnie wybrany nadal istnieje
            current_emu = self.emulator_var.get()
            if current_emu not in emulator_names:
                self.emulator_var.set("") # Wyczyść wybór, jeśli emulator został usunięty

    # --- Istniejące metody select_* ---
    def select_exe(self):
        """Otwiera dialog wyboru pliku .exe, zaczynając w folderze bieżącego pliku."""
        current_path = self.exe_entry.get()
        initial_dir = "." # Domyślnie bieżący folder
        # --- ZMIANA: Ustaw initialdir na folder nadrzędny bieżącego pliku ---
        if current_path and os.path.exists(current_path):
             initial_dir = os.path.dirname(current_path)
        # --- KONIEC ZMIANY ---
        path = filedialog.askopenfilename(
             title="Wybierz plik wykonywalny",
             filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
             initialdir=initial_dir,
             parent=self.top # Ważne dla modalności
        )
        if path:
            self.exe_entry.delete(0, tk.END)
            self.exe_entry.insert(0, path)

    def select_save(self):
        """Otwiera dialog wyboru folderu zapisów, zaczynając od folderu nadrzędnego."""
        current_path = self.save_entry.get()
        initial_dir = os.path.expanduser("~") # Domyślnie folder domowy użytkownika
        # --- ZMIANA: Ustaw initialdir na folder nadrzędny bieżącej ścieżki ---
        if current_path and os.path.isdir(current_path): # Sprawdź, czy to folder
             # Weź folder nadrzędny, aby łatwiej było wybrać inny folder obok
             parent_dir = os.path.dirname(current_path)
             if os.path.isdir(parent_dir): # Sprawdź, czy folder nadrzędny istnieje
                  initial_dir = parent_dir
        # --- KONIEC ZMIANY ---
        path = filedialog.askdirectory(
             title="Wybierz folder z zapisami gry",
             initialdir=initial_dir,
             parent=self.top
        )
        if path:
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, path)

    def select_cover(self):
        """Otwiera dialog wyboru pliku okładki."""
        current_path = self.cover_entry.get()
        initial_dir = IMAGES_FOLDER # Domyślnie folder obrazków launchera
        # --- ZMIANA: Ustaw initialdir na folder bieżącego pliku, jeśli istnieje ---
        if current_path and os.path.exists(current_path):
            dir_path = os.path.dirname(current_path)
            if os.path.isdir(dir_path):
                 initial_dir = dir_path
        # --- KONIEC ZMIANY ---
        path = filedialog.askopenfilename(
             title="Wybierz plik okładki",
             filetypes=[("Obrazy", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("Wszystkie pliki", "*.*")],
             initialdir=initial_dir,
             parent=self.top
        )
        if path:
            self.cover_entry.delete(0, tk.END)
            self.cover_entry.insert(0, path)

    # --- NOWE Metody Akcji dla Przycisków Parsowania ---
    def parse_nfo_action(self):
        """Wywołuje parsowanie .nfo dla bieżącej gry i aktualizuje pola formularza."""
        if not self.game_data or not self.game_data.get("exe_path"):
            messagebox.showwarning("Brak informacji", "Nie można parsować .nfo bez ścieżki do pliku .exe gry.")
            return

        game_folder = os.path.dirname(self.game_data.get("exe_path", ""))
        if not os.path.isdir(game_folder):
             messagebox.showerror("Błąd", f"Folder gry nie istnieje: {game_folder}")
             return

        nfo_data = self.parent.parse_nfo_file(game_folder) # Wywołujemy funkcję z głównej klasy
        logging.info(f"Otrzymano dane z NFO w formularzu: {nfo_data}") # Dodaj ten log
        if not nfo_data:
            messagebox.showinfo("Informacja", "Nie znaleziono pliku .nfo lub nie udało się sparsować danych.")
            return

        # Aktualizuj pola formularza (tylko jeśli są puste?) - Można dodać logikę pytania użytkownika
        # W tej wersji nadpisujemy lub wypełniamy
        if nfo_data.get("title") and not self.name_entry.get(): # Nazwy nie zmieniamy jeśli jest edycja
             pass # self.name_entry.insert(0, nfo_data["title"])
        if nfo_data.get("release_date") and not self.version_entry.get(): # Użyjmy pola wersji dla daty z NFO
            self.version_entry.delete(0, tk.END)
            self.version_entry.insert(0, f"NFO Date: {nfo_data['release_date']}")
        if nfo_data.get("genre"):
            current_tags = self.tags_entry.get().split(',')
            current_tags = [tag.strip() for tag in current_tags if tag.strip()]
            if nfo_data["genre"] not in current_tags:
                 current_tags.append(f"NFO Genre: {nfo_data['genre']}")
                 self.tags_entry.delete(0, tk.END)
                 self.tags_entry.insert(0, ", ".join(current_tags))
        # Można dodać więcej pól np. publisher, developer do notatek
        if nfo_data.get("publisher"):
            self.notes_text.insert("1.0", f"NFO Publisher: {nfo_data['publisher']}\n")
        messagebox.showinfo("Sukces", "Sparsowano dane z pliku .nfo.")


    def parse_folder_action(self):
        """Wywołuje parsowanie nazwy folderu i aktualizuje pola formularza."""
        if not self.game_data or not self.game_data.get("exe_path"):
             messagebox.showwarning("Brak informacji", "Nie można parsować nazwy folderu bez ścieżki do pliku .exe gry.")
             return

        game_folder = os.path.dirname(self.game_data.get("exe_path", ""))
        folder_name = os.path.basename(game_folder)

        folder_data = self.parent.parse_folder_name_metadata(folder_name) # Wywołujemy funkcję z głównej klasy

        if not folder_data:
             messagebox.showinfo("Informacja", "Nie udało się sparsować dodatkowych danych z nazwy folderu.")
             return

        # Aktualizuj pola formularza
        if folder_data.get("year") and not self.version_entry.get(): # Użyjmy pola wersji dla roku z folderu
             self.version_entry.delete(0, tk.END)
             self.version_entry.insert(0, f"Year: {folder_data['year']}")
        if folder_data.get("publisher"):
             self.notes_text.insert("1.0", f"Folder Publisher: {folder_data['publisher']}\n")

        messagebox.showinfo("Sukces", "Sparsowano dane z nazwy folderu.")

    def save(self):
        # Pobierz nazwę gry
        if self.game_data and 'name' in self.game_data: # Edycja
            name_key = self.game_data['name']
        else: # Dodawanie
            name_key = self.name_entry.get().strip()
            if not name_key:
                 messagebox.showwarning("Błąd", "Nazwa gry jest wymagana.", parent=self.top)
                 return
            if name_key in self.parent.games:
                 messagebox.showerror("Błąd", f"Gra o nazwie '{name_key}' już istnieje.", parent=self.top)
                 return

        game_type = self.game_type_var.get()
        game_data_to_save = {"name": name_key, "game_type": game_type} # Zacznij od nazwy i typu

        # Zbierz dane zależne od typu
        if game_type == "pc":
            exe_path = self.exe_entry.get().strip()
            if not exe_path:
                messagebox.showwarning("Błąd", "Ścieżka do pliku wykonywalnego (PC) jest wymagana.", parent=self.top)
                return
            if not os.path.exists(exe_path): # Sprawdź istnienie dla PC
                messagebox.showerror("Błąd", f"Plik wykonywalny PC nie istnieje:\n{exe_path}", parent=self.top)
                return
            game_data_to_save["exe_path"] = exe_path
            game_data_to_save["launch_profiles"] = self._current_profiles # Zapisz profile tylko dla PC
            # Ustaw pola emulatora na puste/None dla pewności
            game_data_to_save["emulator_name"] = None
            game_data_to_save["rom_path"] = None
            game_data_to_save["emulator_args"] = None

        elif game_type == "emulator":
            emulator_name = self.emulator_var.get()
            rom_path = self.rom_entry.get().strip()
            emulator_args = self.emu_args_entry.get().strip()

                # --- DODANO: Definicja profile_name_for_log dla emulatora ---
            profile_name_for_log = emulator_name # Użyj nazwy emulatora jako informacji o "profilu"
                # --- KONIEC DODATKU --
            if not emulator_name:
                messagebox.showwarning("Błąd", "Wybierz emulator dla gry emulowanej.", parent=self.top)
                return
            if not rom_path:
                messagebox.showwarning("Błąd", "Ścieżka do pliku ROM/ISO jest wymagana.", parent=self.top)
                return
            if not os.path.exists(rom_path): # Sprawdź istnienie ROMu
                 messagebox.showerror("Błąd", f"Plik ROM/ISO nie istnieje:\n{rom_path}", parent=self.top)
                 return

            # Sprawdź, czy wybrany emulator istnieje w konfiguracji
            if emulator_name not in self.parent.config.get("emulators", {}):
                 messagebox.showerror("Błąd", f"Wybrany emulator '{emulator_name}' nie jest skonfigurowany w Ustawieniach.", parent=self.top)
                 return

            game_data_to_save["emulator_name"] = emulator_name
            game_data_to_save["rom_path"] = rom_path
            game_data_to_save["emulator_args"] = emulator_args
            # Ustaw pola PC na puste/None
            game_data_to_save["exe_path"] = None
            game_data_to_save["launch_profiles"] = [] # Gry emulowane nie mają profili w ten sam sposób

        # Zbierz wspólne dane
        game_data_to_save["save_path"] = self.save_entry.get().strip()

        # Przetwarzanie okładki (uproszczona logika z poprzedniej odpowiedzi)
        cover_path_from_entry = self.cover_entry.get().strip()
        original_cover_path = self.game_data.get('cover_image')
        final_cover_image = original_cover_path
        cover_changed = False

        if cover_path_from_entry:
             if os.path.exists(cover_path_from_entry):
                 # Jeśli ścieżka jest inna niż oryginał, oznacz zmianę
                 if os.path.normcase(os.path.abspath(cover_path_from_entry)) != os.path.normcase(os.path.abspath(original_cover_path or "")):
                      cover_changed = True
                 final_cover_image = cover_path_from_entry # Zapisz ścieżkę z pola
             else:
                 messagebox.showerror("Błąd Ścieżki", f"Podana ścieżka do okładki nie istnieje:\n{cover_path_from_entry}", parent=self.top)
                 return
        elif original_cover_path: # Pole puste, ale była okładka -> usuwamy
             cover_changed = True
             final_cover_image = "" # Zapisz pusty string

        game_data_to_save["cover_image"] = final_cover_image


        selected_indices = self.genres_listbox.curselection()
        game_data_to_save["genres"] = [self.all_genres[i] for i in selected_indices]

        try:
            rating_str = self.rating_entry.get().strip()
            game_data_to_save["rating"] = float(rating_str) if rating_str else None
        except ValueError:
            messagebox.showwarning("Błąd", "Ocena musi być liczbą (np. 7.5) lub pusta.", parent=self.top)
            return

        game_data_to_save["version"] = self.version_entry.get().strip()
        tags_str = self.tags_entry.get().strip()
        game_data_to_save["tags"] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        game_data_to_save["notes"] = self.notes_text.get("1.0", tk.END).strip()

        # Wyczyszczenie cache, jeśli okładka się zmieniła
        if cover_changed:
            try:
                load_photoimage_from_path.cache_clear()
                logging.info("Wyczyszczono cache load_photoimage_from_path z powodu zmiany okładki.")
            except Exception as e:
                logging.error(f"Nie udało się wyczyścić cache PhotoImage: {e}")

        self.result = (name_key, game_data_to_save) # Zwróć klucz i nowe dane
        self.top.destroy()

    def refresh_profile_treeview(self):
        """Odświeża zawartość Treeview z profilami."""
        # Wyczyść stare wpisy
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        # Dodaj aktualne profile
        for idx, profile in enumerate(self._current_profiles):
            name = profile.get("name", f"Profil {idx+1}")
            args = profile.get("arguments", "")
            exe = profile.get("exe_path", "") or "(Domyślny)" # Pokaż "Domyślny", jeśli exe_path to None lub ""
            # Użyj indeksu jako iid dla łatwiejszej edycji/usuwania
            self.profile_tree.insert("", "end", iid=str(idx), values=(name, args, exe))

    def add_edit_profile(self, edit_mode=False):
        """Otwiera okno do dodawania lub edycji profilu."""
        selected_iid = None
        initial_data = {"name": "", "exe_path": "", "arguments": ""}

        if edit_mode:
            selection = self.profile_tree.selection()
            if not selection:
                messagebox.showwarning("Brak zaznaczenia", "Zaznacz profil, który chcesz edytować.")
                return
            selected_iid = selection[0] # iid to indeks na liście _current_profiles
            try:
                 profile_index = int(selected_iid)
                 # Kopiuj dane, aby nie modyfikować oryginału przed zapisem
                 initial_data = self._current_profiles[profile_index].copy()
                 # Zastąp None pustym stringiem dla pól Entry
                 initial_data["exe_path"] = initial_data.get("exe_path") or ""
                 initial_data["arguments"] = initial_data.get("arguments") or ""
            except (ValueError, IndexError):
                 messagebox.showerror("Błąd", "Nie można odczytać danych wybranego profilu.")
                 return
        else:
             # Ustaw domyślną nazwę dla nowego profilu
            initial_data["name"] = f"Profil {len(self._current_profiles) + 1}"


        # Utwórz okno dialogowe
        profile_window = tk.Toplevel(self.top)
        title = "Edytuj Profil" if edit_mode else "Dodaj Nowy Profil"
        profile_window.title(title)
        profile_window.configure(bg="#1e1e1e")
        profile_window.grab_set()
        profile_window.resizable(False, False)

        # Pola do edycji
        ttk.Label(profile_window, text="Nazwa profilu:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_var = tk.StringVar(value=initial_data.get("name", ""))
        name_entry = ttk.Entry(profile_window, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(profile_window, text="Ścieżka .exe (opcjonalna):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        exe_var = tk.StringVar(value=initial_data.get("exe_path", ""))
        exe_entry = ttk.Entry(profile_window, textvariable=exe_var, width=40)
        exe_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        exe_btn = ttk.Button(profile_window, text="Wybierz...", command=lambda v=exe_var: self.select_profile_exe(v))
        exe_btn.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(profile_window, text="Argumenty linii komend:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        args_var = tk.StringVar(value=initial_data.get("arguments", ""))
        args_entry = ttk.Entry(profile_window, textvariable=args_var, width=40)
        args_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Funkcja zapisu
        def save_profile_data():
            new_name = name_var.get().strip()
            new_exe = exe_var.get().strip() or None # Zapisz None jeśli puste
            new_args = args_var.get().strip()

            if not new_name:
                messagebox.showwarning("Brak nazwy", "Nazwa profilu nie może być pusta.", parent=profile_window)
                return

            # Sprawdź unikalność nazwy (poza edytowanym profilem)
            for i, prof in enumerate(self._current_profiles):
                 if edit_mode and i == profile_index:
                     continue # Pomiń sprawdzanie samego siebie
                 if prof.get("name", "").lower() == new_name.lower():
                     messagebox.showwarning("Nazwa zajęta", f"Profil o nazwie '{new_name}' już istnieje.", parent=profile_window)
                     return

            # Stwórz słownik nowego/zmienionego profilu
            profile_data = {
                "name": new_name,
                "exe_path": new_exe,
                "arguments": new_args
            }

            if edit_mode:
                self._current_profiles[profile_index] = profile_data
            else:
                self._current_profiles.append(profile_data)

            self.refresh_profile_treeview() # Odśwież listę w GameForm
            profile_window.destroy()

        # Przyciski okna dialogowego
        btn_frame = ttk.Frame(profile_window)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        save_button = ttk.Button(btn_frame, text="Zapisz", command=save_profile_data)
        save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(btn_frame, text="Anuluj", command=profile_window.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

    def select_profile_exe(self, string_var):
        """Pozwala wybrać plik exe dla profilu."""
        # Spróbuj zacząć w folderze gry
        initial_dir = ""
        if self.game_data and self.game_data.get("exe_path"):
             initial_dir = os.path.dirname(self.game_data["exe_path"])

        path = filedialog.askopenfilename(
            title="Wybierz plik wykonywalny dla profilu",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
            initialdir=initial_dir,
            parent=self.top # Ustaw rodzica okna dialogowego
            )
        if path:
            string_var.set(path) # Ustaw wartość zmiennej powiązanej z Entry

    def delete_profile(self):
        """Usuwa zaznaczony profil."""
        selection = self.profile_tree.selection()
        if not selection:
            messagebox.showwarning("Brak zaznaczenia", "Zaznacz profil, który chcesz usunąć.")
            return
        selected_iid = selection[0]
        try:
            profile_index = int(selected_iid)
            profile_name = self._current_profiles[profile_index].get("name", f"Profil {profile_index+1}")

            # Nie pozwól usunąć ostatniego profilu ani profilu "Default", jeśli jest jedyny
            if len(self._current_profiles) <= 1:
                 messagebox.showerror("Błąd", "Nie można usunąć ostatniego profilu.", parent=self.top)
                 return
            if profile_name.lower() == "default" and len(self._current_profiles) == 1:
                 messagebox.showerror("Błąd", "Nie można usunąć profilu 'Default', gdy jest jedyny.", parent=self.top)
                 return
            # Zezwól na usunięcie 'Default', jeśli są inne profile
            # if profile_name.lower() == "default":
            #     messagebox.showerror("Błąd", "Nie można usunąć profilu 'Default'.", parent=self.top)
            #     return

            if messagebox.askyesno("Potwierdź usunięcie", f"Czy na pewno chcesz usunąć profil '{profile_name}'?", parent=self.top):
                del self._current_profiles[profile_index]
                self.refresh_profile_treeview()
        except (ValueError, IndexError):
             messagebox.showerror("Błąd", "Nie można zidentyfikować wybranego profilu.", parent=self.top)
