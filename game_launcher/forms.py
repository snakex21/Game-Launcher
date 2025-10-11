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


class SaveManager:
    def __init__(self, parent, game_name, game_data, launcher_instance):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Zarządzanie zapisami - {game_name}")
        self.top.configure(bg="#1e1e1e")
        self.top.grab_set()

        # --- NOWE: Zapisz referencję do launchera ---
        self.launcher = launcher_instance
        # --- KONIEC NOWEGO ---

        ttk.Label(self.top, text=f"Zarządzanie zapisami - {game_name}", font=("Helvetica", 14)).pack(pady=10)

        self.game_name = game_name
        self.save_path = game_data.get("save_path")
        self.backup_path = os.path.join(GAMES_FOLDER, game_name)

        # Sprawdź poprawność ścieżki do zapisów gry
        self.is_save_path_valid = self.save_path and os.path.isdir(self.save_path)

        # Lista zapisów (w backupie)
        # --- ZMIANA: Zamiast Listbox użyj Treeview ---
        list_frame = ttk.Frame(self.top)
        list_frame.pack(pady=5, fill=tk.BOTH, expand=True, padx=10) # Dodano expand=True, fill=tk.BOTH
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1) # Pozwól Treeview rosnąć

        # Definicja kolumn
        save_cols = ("Procent", "Data", "Godzina", "Nazwa Folderu")
        self.saves_tree = ttk.Treeview(list_frame, columns=save_cols, show="headings", height=8, selectmode="browse") # Ustaw wysokość

        # Nagłówki i szerokości kolumn
        self.saves_tree.heading("Procent", text="% Ukoń.")
        self.saves_tree.column("Procent", width=60, anchor='center', stretch=False)
        self.saves_tree.heading("Data", text="Data Zapisu")
        self.saves_tree.column("Data", width=100, anchor='center', stretch=False)
        self.saves_tree.heading("Godzina", text="Godzina")
        self.saves_tree.column("Godzina", width=70, anchor='center', stretch=False)
        self.saves_tree.heading("Nazwa Folderu", text="Nazwa Folderu (Techniczna)")
        self.saves_tree.column("Nazwa Folderu", width=200, anchor='w') # Pozostała szerokość

        # Scrollbar (bez zmian, ale dla Treeview)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.saves_tree.yview)
        self.saves_tree.configure(yscrollcommand=scrollbar.set)

        self.saves_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindowanie podwójnego kliknięcia do wczytania zapisu
        self.saves_tree.bind("<Double-1>", lambda e: self.load_save())

        # Zastąp self.saves_listbox nowym drzewem w innych miejscach, gdzie jest używane do pobrania zaznaczenia
        # np. w load_save, edit_save, delete_save użyj self.saves_tree.selection() i self.saves_tree.item(iid, 'values') lub iid

        self.update_saves_list() # Wypełnij nowe Treeview
        # --- KONIEC ZMIANY ---

        # Ramka na przyciski akcji
        button_frame = ttk.Frame(self.top)
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        # Rozłóżmy przyciski w siatce dla lepszego układu
        button_frame.columnconfigure((0, 1), weight=1) # Dwie kolumny

        # Przyciski (rozmieszczone w gridzie)
        ttk.Button(button_frame, text="Utwórz Zapis", command=self.create_save,
                   state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED).grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        ttk.Button(button_frame, text="Wczytaj Zapis", command=self.load_save,
                   state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED).grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        ttk.Button(button_frame, text="Edytuj Zapis", command=self.edit_save).grid(row=1, column=0, padx=5, pady=3, sticky="ew") # Edycja nazwy backupu zawsze możliwa
        ttk.Button(button_frame, text="Usuń Zapis", command=self.delete_save).grid(row=1, column=1, padx=5, pady=3, sticky="ew") # Usuwanie backupu zawsze możliwe

        # --- NOWE: Przycisk Otwórz Folder Zapisów ---
        open_save_folder_btn = ttk.Button(
            button_frame,
            text="Otwórz Folder Zapisów Gry",
            command=lambda: self.launcher._open_folder(self.save_path), # Użyj metody z launchera
            state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED # Stan zależny od poprawności ścieżki
        )
        open_save_folder_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=8, sticky="ew") # Rozciągnij na dwie kolumny
        # --- KONIEC NOWEGO ---

        ttk.Button(button_frame, text="Zamknij", command=self.top.destroy).grid(row=3, column=0, columnspan=2, padx=5, pady=(15, 5), sticky="ew")

    def update_saves_list(self):
        """Wczytuje zapisy ręczne i automatyczne do Treeview, sortując je."""
        if not hasattr(self, 'saves_tree') or not self.saves_tree.winfo_exists(): return
        for item in self.saves_tree.get_children():
            self.saves_tree.delete(item)

        autosave_path = os.path.join(self.backup_path, '_autosave')
        if os.path.isdir(autosave_path):
            try:
                mtime = os.path.getmtime(autosave_path)
                autosave_date = datetime.datetime.fromtimestamp(mtime)
                self.saves_tree.insert("", 0, iid="_autosave_", values=(
                    "AUTO", 
                    autosave_date.strftime('%Y-%m-%d'), 
                    autosave_date.strftime('%H:%M:%S'), 
                    "Automatyczny Zapis" 
                ), tags=('autosave',))
                self.saves_tree.tag_configure('autosave', foreground='lightblue', font=('Segoe UI', 9, 'italic')) # Dodano font dla lepszej czytelności
            except Exception as e: 
                logging.error(f"Błąd odczytu daty modyfikacji dla auto-zapisu: {e}")


        saves_folder = os.path.join(self.backup_path, 'saves')
        manual_saves_data = []
        if os.path.exists(saves_folder):
            for save_name_folder in os.listdir(saves_folder):
                save_full_path = os.path.join(saves_folder, save_name_folder)
                if os.path.isdir(save_full_path):
                      try:
                           mtime = os.path.getmtime(save_full_path)
                           percent = 0
                           match = re.search(r'Save_(\d+)%', save_name_folder) # Szukaj procentu w nazwie folderu
                           if match: percent = int(match.group(1))
                           manual_saves_data.append({"name": save_name_folder, "mtime": mtime, "percent": percent})
                      except OSError: 
                           manual_saves_data.append({"name": save_name_folder, "mtime": 0, "percent": 0}) # Fallback

            manual_saves_data.sort(key=lambda item: (item["mtime"], item["percent"]), reverse=True)

            for save_data_item in manual_saves_data:
                 save_date_item = datetime.datetime.fromtimestamp(save_data_item["mtime"])
                 self.saves_tree.insert("", "end", iid=save_data_item["name"], values=(
                      f"{save_data_item['percent']}%", 
                      save_date_item.strftime('%Y-%m-%d'), 
                      save_date_item.strftime('%H:%M:%S'), 
                      save_data_item["name"] 
                 ))

        children_items = self.saves_tree.get_children()
        if children_items:
             self.saves_tree.focus(children_items[0])
             self.saves_tree.selection_set(children_items[0])


    def create_save(self):
        """Tworzy nowy nazwany zapis (z paskiem postępu)."""
        if not self.is_save_path_valid: # Użyj flagi sprawdzonej w __init__
            messagebox.showwarning("Błąd", "Ścieżka do zapisów gry jest nieprawidłowa lub nie istnieje.", parent=self.top)
            return

        percent = simpledialog.askinteger("Procent ukończenia", "Podaj procent ukończenia gry dla tego zapisu:", parent=self.top)
        if percent is not None:
            save_name = f"Save_{percent}%_{time.strftime('%Y%m%d_%H%M%S')}"
            destination = os.path.join(self.backup_path, 'saves', save_name)

            # Sprawdź, czy zapis o tej nazwie już istnieje (na wszelki wypadek)
            if os.path.exists(destination):
                 messagebox.showerror("Błąd", f"Zapis o nazwie '{save_name}' już istnieje.", parent=self.top)
                 return

            # Wywołaj kopiowanie z postępem
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='copy',
                 source_path=self.save_path,
                 dest_path=destination,
                 operation_title=f"Tworzenie zapisu '{save_name}'",
                 parent_window=self.top
            )

            if success:
                # Informuj użytkownika, że proces się rozpoczął
                messagebox.showinfo("Rozpoczęto", f"Rozpoczęto tworzenie zapisu '{save_name}'.", parent=self.top)
                # Odśwież listę zapisów od razu, aby pokazać nowy wpis (nawet jeśli kopiowanie trwa)
                # LUB lepiej - dodaj callback do wątku, który odświeży listę PO zakończeniu.
                # Na razie odświeżamy od razu:
                self.update_saves_list()
            # Jeśli success == False, błąd został już pokazany w _copy_or_delete_with_progress

    def _get_selected_save_info(self):
        """Pomocnicza funkcja do pobierania informacji o zaznaczonym zapisie."""
        selection = self.saves_tree.selection()
        if not selection: return None, None, False # Zwraca (ścieżka, nazwa dla logu, czy_autosave)

        selected_iid = selection[0]
        is_autosave = (selected_iid == "_autosave_")

        if is_autosave:
             source_path = os.path.join(self.backup_path, '_autosave')
             save_name_for_log = "Automatyczny Zapis"
        else:
             # iid to teraz nazwa folderu
             save_folder_name = selected_iid
             source_path = os.path.join(self.backup_path, 'saves', save_folder_name)
             save_name_for_log = save_folder_name

        return source_path, save_name_for_log, is_autosave

    def load_save(self):
        """Wczytuje zaznaczony zapis (ręczny lub automatyczny) z Treeview z paskiem postępu."""
        # --- NOWE ZMIANY: Użycie _get_selected_save_info ---
        source_path, save_name_for_log, _ = self._get_selected_save_info() # Nie potrzebujemy tu is_autosave osobno
        
        if not source_path: # Jeśli nic nie zaznaczono
            messagebox.showwarning("Błąd", "Nie wybrano żadnego zapisu.", parent=self.top)
            return
        # --- KONIEC NOWYCH ZMIAN ---

        if not os.path.isdir(source_path):
            messagebox.showerror("Błąd", f"Ścieżka źródłowa zapisu '{source_path}' nie istnieje lub nie jest folderem.", parent=self.top)
            self.update_saves_list() 
            return

        if not self.is_save_path_valid:
            messagebox.showerror("Błąd", "Ścieżka do zapisów gry jest nieprawidłowa.\nUstaw ją w edycji gry.", parent=self.top)
            return

        if messagebox.askyesno("Potwierdź Wczytanie", f"Czy na pewno chcesz wczytać zapis '{save_name_for_log}'?\nSpowoduje to nadpisanie aktualnych zapisów gry!", parent=self.top):
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='copy',
                 source_path=source_path,
                 dest_path=self.save_path, 
                 operation_title=f"Wczytywanie zapisu '{save_name_for_log}'",
                 parent_window=self.top
            )

            if success:
                messagebox.showinfo("Rozpoczęto", f"Rozpoczęto wczytywanie zapisu '{save_name_for_log}'.", parent=self.top)
                # Po zakończeniu wątku, można zamknąć okno jeśli chcemy, lub poinformować
                # Aktualnie okno postępu zamyka się samo w wątku.
            # Błąd jest już obsługiwany w _copy_or_delete_with_progress

    # Metoda edit_save - powinna działać tylko dla zapisów ręcznych
    def edit_save(self):
        """Edytuje nazwę/procent zaznaczonego zapisu RĘCZNEGO."""
        # --- NOWE ZMIANY: Użycie _get_selected_save_info ---
        selected_save_path, old_save_name_folder, is_autosave = self._get_selected_save_info()
        
        if not selected_save_path: # Nic nie zaznaczono
             messagebox.showwarning("Błąd", "Nie wybrano zapisu do edycji.", parent=self.top)
             return

        if is_autosave:
             messagebox.showinfo("Informacja", "Nie można zmienić nazwy automatycznego zapisu.", parent=self.top)
             return
        # --- KONIEC NOWYCH ZMIAN ---

        # old_save_name_folder to teraz bezpośrednio nazwa folderu zapisu (bez 'saves/')
        
        percent = simpledialog.askinteger("Edytuj Procent Ukończenia", "Podaj nowy procent ukończenia dla tego zapisu (tylko dla nazwy):", parent=self.top)
        if percent is not None:
            try:
                 parts = old_save_name_folder.split('_')
                 timestamp_part = f"{parts[-2]}_{parts[-1]}" if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit() else time.strftime('%Y%m%d_%H%M%S')
                 new_save_folder_name = f"Save_{percent}%_{timestamp_part}"
                 
                 if new_save_folder_name == old_save_name_folder: return 

                 saves_base_folder = os.path.join(self.backup_path, 'saves')
                 new_full_path_check = os.path.join(saves_base_folder, new_save_folder_name)
                 
                 if os.path.exists(new_full_path_check):
                      messagebox.showerror("Błąd", f"Zapis o nazwie '{new_save_folder_name}' już istnieje.", parent=self.top)
                      return

                 old_full_path = os.path.join(saves_base_folder, old_save_name_folder) # To samo co selected_save_path
                 
                 os.rename(old_full_path, new_full_path_check)
                 messagebox.showinfo("Sukces", "Nazwa zapisu została zaktualizowana.", parent=self.top)
                 self.update_saves_list()
            except IndexError:
                 messagebox.showerror("Błąd Nazwy", "Nie można przetworzyć starej nazwy zapisu do zmiany procentu.", parent=self.top)
            except Exception as e:
                 logging.exception(f"Błąd podczas zmiany nazwy zapisu '{old_save_name_folder}': {e}")
                 messagebox.showerror("Błąd", f"Nie udało się zaktualizować nazwy zapisu:\n{e}", parent=self.top)

    def delete_save(self):
        """Usuwa zaznaczony zapis (ręczny lub automatyczny) z Treeview z paskiem postępu."""
        path_to_delete, save_name_for_log, _ = self._get_selected_save_info()
        
        if not path_to_delete:
             messagebox.showwarning("Błąd", "Nie wybrano zapisu do usunięcia.", parent=self.top)
             return

        if not os.path.isdir(path_to_delete):
             messagebox.showerror("Błąd", f"Folder zapisu '{save_name_for_log}' nie istnieje:\n{path_to_delete}", parent=self.top)
             self.update_saves_list()
             return

        if messagebox.askyesno("Potwierdź Usunięcie", f"Czy na pewno chcesz trwale usunąć zapis '{save_name_for_log}'?", parent=self.top):
            # --- NOWA ZMIANA: Przekazanie self.update_saves_list jako callbacku ---
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='delete',
                 source_path=path_to_delete, 
                 dest_path=None,             
                 operation_title=f"Usuwanie zapisu '{save_name_for_log}'",
                 parent_window=self.top,
                 callback_on_success=self.update_saves_list # <--- TUTAJ PRZEKAZUJEMY CALLBACK
            )
            # --- KONIEC NOWEJ ZMIANY ---

            if success: # Jeśli operacja została poprawnie zainicjowana (nie oznacza to jeszcze zakończenia wątku)
                 messagebox.showinfo("Rozpoczęto", f"Rozpoczęto usuwanie zapisu '{save_name_for_log}'.\nLista zostanie odświeżona po zakończeniu.", parent=self.top)


class GameDetailsWindow(tk.Toplevel):
    def __init__(self, parent, launcher_instance, game_name):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.root = launcher_instance.root
        self.game_name = game_name
        # --- ZMIANA: Użyj setdefault od razu, aby zapewnić istnienie kluczy ---
        self.game_data = self.launcher.games.setdefault(game_name, {}) # Pobierz lub utwórz pusty słownik
        self.game_data.setdefault("screenshots", []) # Upewnij się, że klucz checklist istnieje
        # --- NOWE ZMIANY ---
        self.game_data.setdefault("autoscan_screenshots", []) # Upewnij się, że klucz autoscan istnieje
        # --- KONIEC NOWYCH ZMIAN ---
        self.game_data.setdefault("checklist", []) # Upewnij się, że klucz checklist istnieje
        # --- KONIEC ZMIANY ---
        self.game_data.setdefault("checklist", []) # Upewnij się, że klucz checklist istnieje
        # --- KONIEC ZMIANY ---

        if not self.game_data:
            messagebox.showerror("Błąd", f"Nie znaleziono danych dla gry: {game_name}", parent=self)
            self.destroy(); return

        self.title(f"Szczegóły Gry - {game_name}")
        self.configure(bg="#1e1e1e")
        self.geometry("800x650")
        self.minsize(700, 600)
        self.grab_set()

        main_frame = ttk.Frame(self, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1) # Notebook będzie się rozciągał

        # Lewa Kolumna (Okładka) - bez zmian
        cover_frame = ttk.Frame(main_frame, width=300)
        cover_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10)) # rowspan=3 by objąć statystyki
        cover_frame.grid_propagate(False)
        cover_frame.rowconfigure(0, weight=1); cover_frame.columnconfigure(0, weight=1)
        self.cover_label = ttk.Label(cover_frame, anchor=tk.CENTER)
        self.cover_label.grid(row=0, column=0, sticky="nsew")
        # --- Dodaj bindowanie prawego przycisku do okładki ---
        self.cover_label.bind("<Button-3>", self.show_cover_context_menu)
        # --- Koniec ---
        self.load_cover_image(size=(300, 450))

        # Prawa Kolumna (Dane i Akcje)
        details_frame = ttk.Frame(main_frame)
        details_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 5))
        details_frame.columnconfigure(0, weight=1)
        title_label = ttk.Label(details_frame, text=game_name, font=("Helvetica", 18, "bold"), anchor="w", wraplength=450)
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        basic_info_frame = ttk.Frame(details_frame)
        basic_info_frame.grid(row=1, column=0, sticky="ew", pady=(0,10))
        # ... (kod basic_info_frame bez zmian) ...
        self.release_label = ttk.Label(basic_info_frame, text="Data wydania: -", font=("Segoe UI", 9))
        self.release_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.developer_label = ttk.Label(basic_info_frame, text="Deweloper: -", font=("Segoe UI", 9), wraplength=180)
        self.developer_label.grid(row=0, column=2, sticky="w", padx=(10, 5))
        self.publisher_label = ttk.Label(basic_info_frame, text="Wydawca: -", font=("Segoe UI", 9), wraplength=180)
        self.publisher_label.grid(row=1, column=2, sticky="w", padx=(10, 5))
        self.website_button = ttk.Button(basic_info_frame, text="Strona WWW", style="Link.TButton", state=tk.DISABLED, command=self.open_website)
        button_style = ttk.Style()
        button_style.configure("Link.TButton", foreground="lightblue", padding=0)
        self.website_button.grid(row=1, column=0, sticky="w", padx=(0, 5))


        # Notebook dla zakładek
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=1, sticky="nsew", pady=5) # Zajmuje główną przestrzeń

        # Zakładka Opis/Notatki (bez zmian)
        desc_notes_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(desc_notes_frame, text="Opis / Notatki")
        # ... (kod notes_text, scrollbara, przycisku edycji bez zmian) ...
        desc_notes_frame.columnconfigure(0, weight=1)
        desc_notes_frame.rowconfigure(0, weight=1)
        self.notes_text = tk.Text(desc_notes_frame, wrap=tk.WORD, height=8, relief=tk.FLAT, state=tk.DISABLED)
        notes_style = ttk.Style()
        text_bg = notes_style.lookup('TEntry', 'fieldbackground')
        text_fg = notes_style.lookup('TEntry', 'foreground')
        self.notes_text.config(background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9))
        notes_scroll = ttk.Scrollbar(desc_notes_frame, orient="vertical", command=self.notes_text.yview)
        self.notes_text.config(yscrollcommand=notes_scroll.set)
        self.notes_text.grid(row=0, column=0, sticky="nsew")
        notes_scroll.grid(row=0, column=1, sticky="ns")
        self.edit_notes_button = ttk.Button(desc_notes_frame, text="Edytuj Notatki", command=self.toggle_notes_edit)
        self.edit_notes_button.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky="e")


        # Zakładka Wymagania / Info (bez zmian)
        req_info_frame = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(req_info_frame, text="Info / Wymagania")
        # ... (kod req_text i etykiet API bez zmian) ...
        req_info_frame.columnconfigure(0, weight=1)
        req_info_frame.rowconfigure(1, weight=1)
        api_info_frame = ttk.Frame(req_info_frame)
        api_info_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        api_info_frame.columnconfigure(1, weight=1)
        self.platforms_label = ttk.Label(api_info_frame, text="Platformy: -", wraplength=500, justify=tk.LEFT, font=("Segoe UI", 9))
        self.platforms_label.grid(row=0, column=0, columnspan=2, sticky="w")
        self.genres_api_label = ttk.Label(api_info_frame, text="Gatunki (API): -", wraplength=500, justify=tk.LEFT, font=("Segoe UI", 9))
        self.genres_api_label.grid(row=1, column=0, columnspan=2, sticky="w")
        self.tags_api_label = ttk.Label(api_info_frame, text="Tagi (API): -", wraplength=500, justify=tk.LEFT, font=("Segoe UI", 9))
        self.tags_api_label.grid(row=2, column=0, columnspan=2, sticky="w")
        self.req_text = tk.Text(req_info_frame, wrap=tk.WORD, height=6, relief=tk.FLAT, state=tk.DISABLED)
        req_style = ttk.Style()
        req_text_bg = req_style.lookup('TEntry', 'fieldbackground')
        req_text_fg = req_style.lookup('TEntry', 'foreground')
        self.req_text.config(background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 8))
        req_scroll = ttk.Scrollbar(req_info_frame, orient="vertical", command=self.req_text.yview)
        self.req_text.config(yscrollcommand=req_scroll.set)
        self.req_text.grid(row=1, column=0, sticky="nsew")
        req_scroll.grid(row=1, column=1, sticky="ns")

        # Zakładka Screenshoty
        self.screenshots_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.screenshots_frame, text="Screenshoty")
        # --- NOWE ZMIANY ---
        self.screenshots_frame.columnconfigure(1, weight=1) # Daj miejsce na przycisk skanowania
        # --- KONIEC NOWYCH ZMIAN ---
        self.screenshots_frame.rowconfigure(1, weight=1)

        # Ramka na górne przyciski
        ss_top_button_frame = ttk.Frame(self.screenshots_frame)
        ss_top_button_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5) # columnspan=2
        ss_top_button_frame.columnconfigure(1, weight=1) # Rozciągnij przestrzeń

        ttk.Button(ss_top_button_frame, text="Dodaj Screenshoty...", command=self.add_screenshots).grid(row=0, column=0, sticky="w")

        # --- NOWE ZMIANY ---
        # Przycisk skanowania teraz dla tej gry
        scan_now_btn = ttk.Button(
            ss_top_button_frame,
            text="Skanuj Foldery Teraz (dla tej gry)",
            command=self.start_scan_for_this_game # Nowa metoda
        )
        scan_now_btn.grid(row=0, column=1, sticky="e", padx=(10, 0)) # Wyrównaj do prawej
        # --- KONIEC NOWYCH ZMIAN ---

        self.screenshot_canvas = tk.Canvas(self.screenshots_frame, bg="#1e1e1e", highlightthickness=0)
        ss_scrollbar = ttk.Scrollbar(self.screenshots_frame, orient="vertical", command=self.screenshot_canvas.yview)
        self.screenshot_inner_frame = ttk.Frame(self.screenshot_canvas)
        self.screenshot_canvas_window_id = self.screenshot_canvas.create_window((0, 0), window=self.screenshot_inner_frame, anchor="nw")
        self.screenshot_canvas.configure(yscrollcommand=ss_scrollbar.set)
        self.screenshot_canvas.grid(row=1, column=0, sticky="nsew") # Zostaje w kolumnie 0
        ss_scrollbar.grid(row=1, column=1, sticky="ns") # Scrollbar w kolumnie 1
        self.screenshot_canvas.bind("<Configure>", lambda e: self.screenshot_canvas.itemconfig(self.screenshot_canvas_window_id, width=e.width))
        self.screenshot_inner_frame.bind("<Configure>", lambda e: self.screenshot_canvas.configure(scrollregion=self.screenshot_canvas.bbox("all")))
        self.screenshot_canvas.bind_all("<MouseWheel>", self._on_screenshot_mousewheel, add='+') # Zmieniono bind na bind_all z add='+'

        # --- NOWA ZAKŁADKA: Checklista ---
        self.checklist_tab_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.checklist_tab_frame, text="Checklista")
        self.checklist_tab_frame.columnconfigure(0, weight=1) # Kolumna z Treeview rośnie
        self.checklist_tab_frame.rowconfigure(0, weight=1)    # Wiersz z Treeview rośnie

        # Treeview dla checklisty
        checklist_cols = ('status', 'task')
        self.checklist_tree = ttk.Treeview(self.checklist_tab_frame, columns=checklist_cols, show="headings", height=8, selectmode="browse")
        self.checklist_tree.heading('status', text='✓') # Nagłówek dla statusu
        self.checklist_tree.heading('task', text='Zadanie')
        self.checklist_tree.column('status', width=40, stretch=False, anchor='center') # Wąska kolumna dla statusu
        self.checklist_tree.column('task', width=400, anchor='w') # Główna kolumna na opis

        # Scrollbar dla Treeview checklisty
        checklist_scrollbar = ttk.Scrollbar(self.checklist_tab_frame, orient="vertical", command=self.checklist_tree.yview)
        self.checklist_tree.configure(yscrollcommand=checklist_scrollbar.set)

        self.checklist_tree.grid(row=0, column=0, sticky="nsew")
        checklist_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindowanie do przełączania statusu
        self.checklist_tree.bind("<Double-1>", self._toggle_task_status_event) # Podwójne kliknięcie przełącza
        # Można też dodać bindowanie do Spacji

        # Ramka na przyciski pod checklistą
        checklist_buttons_frame = ttk.Frame(self.checklist_tab_frame)
        checklist_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        ttk.Button(checklist_buttons_frame, text="Dodaj Zadanie", command=self._add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(checklist_buttons_frame, text="Edytuj Zaznaczone", command=self._edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(checklist_buttons_frame, text="Usuń Zaznaczone", command=self._delete_task).pack(side=tk.LEFT, padx=5)
        # --- KONIEC NOWEJ ZAKŁADKI ---

        # --- NOWA ZAKŁADKA: Akcje (z przewijaniem) ---
        actions_tab_outer_frame = ttk.Frame(self.notebook) # Ramka zewnętrzna dla Canvas i Scrollbar
        self.notebook.add(actions_tab_outer_frame, text="Akcje / Zarządzanie")
        actions_tab_outer_frame.rowconfigure(0, weight=1)    # Canvas rośnie
        actions_tab_outer_frame.columnconfigure(0, weight=1) # Canvas rośnie

        # Canvas do przewijania
        actions_canvas = tk.Canvas(actions_tab_outer_frame, bg="#1e1e1e", highlightthickness=0)
        actions_canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        actions_scrollbar = ttk.Scrollbar(actions_tab_outer_frame, orient="vertical", command=actions_canvas.yview)
        actions_scrollbar.grid(row=0, column=1, sticky="ns")
        actions_canvas.configure(yscrollcommand=actions_scrollbar.set)

        # Wewnętrzna ramka na zawartość (przyciski)
        scrollable_actions_frame = ttk.Frame(actions_canvas, style="TFrame")
        scrollable_actions_frame_window_id = actions_canvas.create_window((0, 0), window=scrollable_actions_frame, anchor="nw")


        # Bindowanie resize i scroll
        def _configure_actions_canvas(event):
             if actions_canvas.winfo_exists() and scrollable_actions_frame.winfo_exists():
                 canvas_width = event.width
                 actions_canvas.itemconfig(scrollable_actions_frame_window_id, width=canvas_width)
                 actions_canvas.configure(scrollregion=actions_canvas.bbox("all"))
        actions_canvas.bind("<Configure>", _configure_actions_canvas)
        scrollable_actions_frame.bind("<Configure>", lambda e: actions_canvas.configure(scrollregion=actions_canvas.bbox("all")) if actions_canvas.winfo_exists() else None)

        # Bindowanie kółka myszy (tylko dla tego obszaru)
        def _on_actions_mousewheel(event):
             # Sprawdź, czy kursor jest nad canvasem akcji
             widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)
             is_actions_area = False
             curr = widget_under_cursor
             while curr is not None:
                 if curr == actions_canvas: is_actions_area = True; break
                 if curr == self: break # Ogranicz do okna szczegółów
                 try: curr = curr.master
                 except tk.TclError: break

             if is_actions_area and actions_canvas.winfo_exists():
                 scroll_val = -1 * int(event.delta / 120)
                 view_start, view_end = actions_canvas.yview()
                 if (scroll_val < 0 and view_start > 0.0) or (scroll_val > 0 and view_end < 1.0):
                     actions_canvas.yview_scroll(scroll_val, "units")
                     return "break" # Zatrzymaj dalszą propagację

        # Użyj bind zamiast bind_all, aby ograniczyć do tego canvasu i jego dzieci
        actions_canvas.bind_all("<MouseWheel>", _on_actions_mousewheel, add='+') # Dodaj, ale pozwól też innym działać

        # --- Umieść LabelFrame'y WEWNĄTRZ scrollable_actions_frame ---
        scrollable_actions_frame.columnconfigure(0, weight=1) # Pozwól LabelFrame'om wypełnić szerokość

        # Sekcja: Główne Akcje
        main_actions_frame = ttk.LabelFrame(scrollable_actions_frame, text=" Zarządzanie Grą ", padding=(10, 5))
        # Użyj grid zamiast pack, aby lepiej kontrolować rozciąganie
        main_actions_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        # Przyciski wewnątrz LabelFrame nadal mogą używać pack
        ttk.Button(main_actions_frame, text="Edytuj Dane Gry...", command=lambda: self.launcher.edit_game(self.game_name)).pack(pady=3, anchor='w', fill='x')
        ttk.Button(main_actions_frame, text="Zarządzaj Zapisami...", command=lambda: self.launcher.manage_saves(self.game_name)).pack(pady=3, anchor='w', fill='x')
        ttk.Button(main_actions_frame, text="Przejdź do Menedżera Modów", command=self.show_mods_for_game).pack(pady=3, anchor='w', fill='x')
        ttk.Button(main_actions_frame, text="Resetuj Statystyki...", command=lambda: self.launcher.reset_stats(self.game_name)).pack(pady=3, anchor='w', fill='x')

        # Sekcja: Zarządzanie Okładką
        cover_actions_frame = ttk.LabelFrame(scrollable_actions_frame, text=" Zarządzanie Okładką ", padding=(10, 5))
        cover_actions_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(cover_actions_frame, text="Ustaw Własną Okładkę...", command=self.select_custom_cover).pack(pady=3, anchor='w', fill='x')
        ttk.Button(cover_actions_frame, text="Pobierz/Użyj Okładki z RAWG", command=lambda: self.fetch_cover_from_rawg(force=True)).pack(pady=3, anchor='w', fill='x')
        ttk.Button(cover_actions_frame, text="Usuń Okładkę (przywróć domyślną)", command=self.remove_cover).pack(pady=3, anchor='w', fill='x')
        # --- KONIEC NOWEJ ZAKŁADKI ---


        # Ramka Statystyk Launchera (bez zmian)
        self.launcher_stats_frame = ttk.Frame(main_frame) # Zmieniono parent na main_frame
        self.launcher_stats_frame.grid(row=2, column=1, sticky="ew", pady=(5,0)) # Zmieniono parent na main_frame
        self.create_launcher_stats_labels(self.launcher_stats_frame)

        # --- ZMIANA: Dolny Pasek Przycisków (tylko kluczowe) ---
        bottom_action_frame = ttk.Frame(main_frame) # Zmieniono parent na main_frame
        bottom_action_frame.grid(row=3, column=1, sticky="ew", pady=(10, 0)) # Zmieniono parent na main_frame
        bottom_action_frame.columnconfigure((0, 1, 2), weight=1) # Rozłóż przyciski równomiernie

        self.fetch_api_button = ttk.Button(bottom_action_frame, text="Pobierz Dane z RAWG", command=self.start_fetch_details_thread)
        self.fetch_api_button.grid(row=0, column=0, padx=5, pady=2, sticky="ew")

        # Przycisk Uruchom (w środku)
        self.create_launch_button_with_profiles(bottom_action_frame, start_column=1) # Przekaż ramkę i kolumnę

        close_btn = ttk.Button(bottom_action_frame, text="Zamknij", command=self.destroy)
        close_btn.grid(row=0, column=2, padx=5, pady=2, sticky="ew")
        # --- KONIEC ZMIANY ---


        # Ładowanie danych początkowych
        self.refresh_details_data()
    # --- NOWA METODA ---
    def start_scan_for_this_game(self):
        """Wywołuje skanowanie screenshotów tylko dla bieżącej gry."""
        logging.info(f"Ręczne uruchomienie skanowania screenshotów dla gry: {self.game_name}")
        # Wywołaj metodę w launcherze, przekazując nazwę gry
        self.launcher.start_scan_screenshots_thread(game_to_scan=self.game_name)
    # --- KONIEC NOWEJ METODY ---

    # --- NOWE METODY dla przycisków w zakładce Akcje ---
    def select_custom_cover(self):
        """Otwiera dialog wyboru pliku i zapisuje jako nową okładkę."""
        path = filedialog.askopenfilename(
            title="Wybierz własny plik okładki",
            filetypes=[("Obrazy", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("Wszystkie pliki", "*.*")],
            parent=self
        )
        if path and os.path.exists(path):
            # Logika kopiowania, usuwania starej i zapisu nowej ścieżki
            # (Podobna do tej z GameForm.save, ale działająca na self.game_data)
            original_cover_path = self.game_data.get("cover_image")
            safe_game_name = re.sub(r'[\\/*?:"<>|]', "_", self.game_name)
            source_abs = os.path.abspath(path)
            _, ext = os.path.splitext(source_abs)
            dest_filename = f"{safe_game_name}_cover{ext}"
            dest_path = os.path.join(IMAGES_FOLDER, dest_filename)
            dest_abs = os.path.abspath(dest_path)
            norm_source_abs = os.path.normcase(source_abs)
            norm_dest_abs = os.path.normcase(dest_abs)
            norm_original_abs = os.path.normcase(os.path.abspath(original_cover_path)) if original_cover_path else None

            cover_changed = False
            if norm_source_abs != norm_original_abs or not original_cover_path:
                cover_changed = True
                try:
                    os.makedirs(IMAGES_FOLDER, exist_ok=True)
                    # Usuń starą (jeśli istniała i inna)
                    if original_cover_path and os.path.exists(original_cover_path) and norm_original_abs != norm_dest_abs:
                         try: os.remove(original_cover_path)
                         except OSError as e: logging.error(f"Błąd usuwania starej okładki {original_cover_path}: {e}")
                    # Kopiuj nową (jeśli trzeba)
                    if norm_source_abs != norm_dest_abs:
                         shutil.copy(source_abs, dest_abs)
                    self.game_data["cover_image"] = dest_path # Ustaw nową ścieżkę
                    self.game_data["cover_custom"] = dest_path # Zapisz jako własną
                    self.game_data.pop("_auto_cover", None)    # Usuń flagę auto
                    save_config(self.launcher.config)
                    if cover_changed: load_photoimage_from_path.cache_clear()
                    self.refresh_details_data() # Odśwież widok szczegółów
                    # Wymuś odświeżenie kafelka w tle
                    self.launcher.root.after(150, lambda gn=self.game_name: self.launcher._force_refresh_tile(gn))
                except Exception as e:
                     messagebox.showerror("Błąd", f"Nie udało się ustawić nowej okładki: {e}", parent=self)
                     logging.exception(f"Błąd przy ustawianiu własnej okładki dla {self.game_name}")

    # --- NOWA METODA ---
    def start_scan_for_this_game(self):
        """Wywołuje skanowanie screenshotów tylko dla bieżącej gry."""
        logging.info(f"Ręczne uruchomienie skanowania screenshotów dla gry: {self.game_name}")

        # --- NOWE ZMIANY ---
        # Sprawdź, czy foldery są zdefiniowane PRZED wywołaniem wątku
        scan_folders = self.launcher.settings.get("autoscan_screenshot_folders", [])
        if not scan_folders:
            messagebox.showinfo(
                "Brak Folderów",
                "Nie zdefiniowano żadnych folderów do skanowania screenshotów.\n"
                "Dodaj je najpierw w Ustawieniach.",
                parent=self  # Ustaw okno szczegółów jako rodzica komunikatu
            )
            return # Nie kontynuuj, jeśli nie ma folderów
        # --- KONIEC NOWYCH ZMIAN ---

        # Wywołaj metodę w launcherze, przekazując nazwę gry
        self.launcher.start_scan_screenshots_thread(game_to_scan=self.game_name)
    # --- KONIEC NOWEJ METODY ---


# W klasie GameDetailsWindow:
    def load_cover_image(self, size=(300, 450)):
        """Ładuje okładkę gry w odpowiednim rozmiarze (bez miniaturek)."""
        original_path = self.game_data.get("cover_image")

        # --- ZMIANA: Ładuj bezpośrednio z oryginalnej ścieżki ---
        self.cover_photo = load_photoimage_from_path(original_path, size)
        # --- KONIEC ZMIANY ---

        if self.cover_photo:
            self.cover_label.config(image=self.cover_photo)
            self.cover_label.image = self.cover_photo # Trzymaj referencję
        else:
            logging.warning(f"Nie można załadować dużej okładki dla {self.game_name} ({original_path}). Używanie placeholdera tekstowego.")
            self.cover_label.config(image=None, text="Brak Okładki") # Użyj tekstu, jeśli ładowanie zawiedzie



    def create_stats_labels(self, parent_frame):
        """Tworzy etykiety ze statystykami."""
        stats = {
            "Czas gry:": self.launcher.format_play_time(self.game_data.get("play_time", 0)),
            "Ukończenie:": f"{self.game_data.get('completion', 0)}%",
            "Ocena:": str(self.game_data.get('rating', 'Brak')),
            "Wersja:": self.game_data.get('version', 'Nieznana'),
            "Data dodania:": datetime.datetime.fromtimestamp(self.game_data.get('date_added', 0)).strftime('%Y-%m-%d') if self.game_data.get('date_added') else "Brak",
            "Ostatnio grane:": datetime.datetime.fromtimestamp(self.game_data.get('last_played', 0)).strftime('%Y-%m-%d %H:%M') if self.game_data.get('last_played') else "Nigdy",
            "Gatunki:": ", ".join(self.game_data.get('genres', []) or ["Brak"]),
            "Tagi:": ", ".join(self.game_data.get('tags', []) or ["Brak"]),
        }
        row = 0
        for label, value in stats.items():
            ttk.Label(parent_frame, text=label, font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", padx=2)
            # Dodaj wraplength dla wartości, aby się zawijały
            value_label = ttk.Label(parent_frame, text=value, wraplength=350, justify=tk.LEFT, font=("Segoe UI", 9))
            value_label.grid(row=row, column=1, sticky="w", padx=2)
            row += 1
        parent_frame.columnconfigure(1, weight=1)

    def load_description_and_notes(self):
        """Ładuje opis i notatki do pola tekstowego."""
        self.notes_text.config(state=tk.NORMAL) # Włącz edycję
        self.notes_text.delete("1.0", tk.END)
        # Najpierw opis (jeśli istnieje)
        description = self.game_data.get("description") # Nowe pole
        if description:
            self.notes_text.insert("1.0", f"--- OPIS ---\n{description}\n\n")
        # Potem notatki
        notes = self.game_data.get("notes", "")
        if notes:
             self.notes_text.insert(tk.END, f"--- NOTATKI UŻYTKOWNIKA ---\n{notes}")
        elif not description: # Jeśli nie ma ani opisu, ani notatek
             self.notes_text.insert("1.0", "(Brak opisu i notatek)")

        self.notes_text.config(state=tk.DISABLED) # Wyłącz edycję z powrotem

    def fetch_online_description_stub(self):
        """Placeholder dla funkcji pobierania opisu online."""
        messagebox.showinfo("Wkrótce", "Funkcja pobierania opisu online zostanie dodana w przyszłości.", parent=self)
        # Tutaj w przyszłości będzie logika API (wątek, request, parsowanie, update)
        # np. self.launcher.start_online_fetch_thread(self.game_name, self.update_description_field)

    # def update_description_field(self, description):
    #     """Aktualizuje pole tekstowe nowym opisem."""
    #     self.game_data["description"] = description
    #     self.load_description_and_notes()
    #     save_config(self.launcher.config) # Zapisz config z nowym opisem

    def create_action_buttons(self, parent_frame):
        """Tworzy przyciski akcji na dole okna."""
        # Przycisk Uruchom (z profilami)
        profiles = self.game_data.get("launch_profiles", [])
        if not profiles: profiles = [{"name": "Default", "exe_path": None, "arguments": ""}]
        default_profile = profiles[0]

        launch_btn_frame = ttk.Frame(parent_frame)
        launch_btn_frame.grid(row=0, column=0, padx=2, sticky="ew")

        if len(profiles) == 1 and default_profile.get("name", "").lower() == "default":
            launch_btn_text = "Uruchom"
        else:
            launch_btn_text = f"Uruchom: {default_profile.get('name', 'Profil')}"

        launch_cmd = lambda p=default_profile: self.launcher.launch_game(self.game_name, profile=p)
        self.launch_button = ttk.Button(launch_btn_frame, text=launch_btn_text, style="Green.TButton", command=launch_cmd)

        if len(profiles) > 1:
             self.launch_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
             profile_menu_btn = ttk.Menubutton(launch_btn_frame, text="▼", width=2, style="Toolbutton")
             profile_menu_btn.pack(side=tk.LEFT, fill=tk.Y)
             profile_menu = tk.Menu(profile_menu_btn, tearoff=0, background="#2e2e2e", foreground="white")
             profile_menu_btn["menu"] = profile_menu
             for profile in profiles:
                  profile_name = profile.get("name", "Brak Nazwy")
                  cmd = lambda p=profile: self.launcher.launch_game(self.game_name, profile=p)
                  profile_menu.add_command(label=profile_name, command=cmd)
        else:
             self.launch_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Pozostałe przyciski
        edit_btn = ttk.Button(parent_frame, text="Edytuj", command=lambda: self.launcher.edit_game(self.game_name))
        edit_btn.grid(row=0, column=1, padx=2, sticky="ew")

        saves_btn = ttk.Button(parent_frame, text="Zapisy", command=lambda: self.launcher.manage_saves(self.game_name))
        saves_btn.grid(row=0, column=2, padx=2, sticky="ew")

        mods_btn = ttk.Button(parent_frame, text="Mody", command=self.show_mods_for_game)
        mods_btn.grid(row=0, column=3, padx=2, sticky="ew")

        close_btn = ttk.Button(parent_frame, text="Zamknij", command=self.destroy)
        close_btn.grid(row=0, column=4, padx=2, sticky="ew")

    def show_mods_for_game(self):
        """Przełącza do Menedżera Modów i wybiera bieżącą grę."""
        self.launcher.show_mod_manager()
        # Poczekaj chwilę, aż UI menedżera modów się zainicjuje
        self.launcher.root.after(100, lambda: self.launcher.extended_mod_manager.select_game_in_manager(self.game_name))

    def add_screenshots(self):
         """Otwiera dialog wyboru plików i dodaje screenshoty."""
         files = filedialog.askopenfilenames(
             title="Wybierz screenshoty",
             filetypes=[("Obrazy", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Wszystkie pliki", "*.*")],
             parent=self
         )
         if not files: return

         screenshot_dir = os.path.join(IMAGES_FOLDER, "screenshots", re.sub(r'[\\/*?:"<>|]', "_", self.game_name))
         os.makedirs(screenshot_dir, exist_ok=True)

         added_paths = []
         current_screenshots = self.game_data.setdefault("screenshots", [])

         for f_path in files:
             try:
                 filename = os.path.basename(f_path)
                 destination_path = os.path.join(screenshot_dir, filename)
                 # Unikaj kopiowania, jeśli plik już istnieje (można dodać opcję nadpisania)
                 if not os.path.exists(destination_path):
                      shutil.copy(f_path, destination_path)
                      # Zapisz ścieżkę względną lub bezwzględną - tu bezwzględna dla prostoty
                      if destination_path not in current_screenshots:
                          current_screenshots.append(destination_path)
                          added_paths.append(destination_path)
                 else:
                      logging.warning(f"Screenshot '{filename}' już istnieje w folderze docelowym. Pomijanie.")
             except Exception as e:
                 logging.error(f"Nie udało się skopiować screenshota '{f_path}': {e}")
                 messagebox.showerror("Błąd Kopiowania", f"Nie udało się skopiować pliku:\n{f_path}\n\nBłąd: {e}", parent=self)

         if added_paths:
             save_config(self.launcher.config)
             self.refresh_details_data() # Odśwież galerię
             messagebox.showinfo("Sukces", f"Dodano {len(added_paths)} screenshotów.", parent=self)

# W klasie GameDetailsWindow, metoda load_screenshots

    def load_screenshots(self):
         """Ładuje miniaturki screenshotów (ręcznych i automatycznych)."""
         # Wyczyść poprzednie
         for widget in self.screenshot_inner_frame.winfo_children():
             widget.destroy()

         # --- NOWE ZMIANY: Normalizacja ścieżek przed połączeniem ---
         # Pobierz obie listy
         manual_paths_raw = self.game_data.get("screenshots", [])
         auto_paths_raw = self.game_data.get("autoscan_screenshots", [])

         # Znormalizuj ścieżki (abspath i normcase dla porównania niezależnego od wielkości liter i separatorów)
         # Używamy setów do przechowywania znormalizowanych ścieżek dla łatwego łączenia i unikania duplikatów
         normalized_manual_paths = {os.path.normcase(os.path.abspath(p)) for p in manual_paths_raw if p}
         normalized_auto_paths = {os.path.normcase(os.path.abspath(p)) for p in auto_paths_raw if p}

         # Połącz znormalizowane ścieżki
         all_normalized_paths = normalized_manual_paths.union(normalized_auto_paths)

         # Potrzebujemy mapowania znormalizowanej ścieżki z powrotem na *oryginalną* ścieżkę
         # (aby zachować oryginalny format w UI i przy usuwaniu).
         # Dajemy priorytet ścieżkom z listy ręcznej, jeśli wystąpią w obu.
         path_map = {}
         for p in manual_paths_raw:
             if p: path_map[os.path.normcase(os.path.abspath(p))] = p
         for p in auto_paths_raw:
              norm_p = os.path.normcase(os.path.abspath(p)) if p else None
              if norm_p and norm_p not in path_map: # Dodaj tylko jeśli nie ma już w mapie (z listy ręcznej)
                   path_map[norm_p] = p

         # Ostateczna lista oryginalnych, unikalnych ścieżek do wyświetlenia, posortowana
         all_paths_to_display = sorted([path_map[norm_p] for norm_p in all_normalized_paths if norm_p in path_map], key=str.lower)
         # --- KONIEC NOWYCH ZMIAN ---

         if not all_paths_to_display: # Użyj nowej listy
             ttk.Label(self.screenshot_inner_frame, text="(Brak screenshotów)").pack(pady=20)
             return

         thumb_size = (120, 80)
         row, col = 0, 0
         try:
             parent_width = self.screenshot_canvas.winfo_width()
             if parent_width <= 1: parent_width = self.winfo_width() - 60
         except tk.TclError:
             parent_width = 600
         max_cols = max(1, parent_width // (thumb_size[0] + 10))


         for i, img_path in enumerate(all_paths_to_display): # Użyj nowej listy
             # --- NOWE ZMIANY: Sprawdzanie pochodzenia na podstawie znormalizowanych list ---
             normalized_img_path = os.path.normcase(os.path.abspath(img_path))
             is_manual = normalized_img_path in normalized_manual_paths
             is_auto = normalized_img_path in normalized_auto_paths
             # --- KONIEC NOWYCH ZMIAN ---

             if not os.path.exists(img_path):
                  logging.warning(f"Plik screenshota nie istnieje: {img_path}. Pomijanie.")
                  # --- NOWE ZMIANY: Usuń nieistniejącą ścieżkę z konfiguracji ---
                  self._remove_stale_screenshot_path(img_path, is_manual, is_auto)
                  # --- KONIEC NOWYCH ZMIAN ---
                  continue

             try:
                 # ... (reszta kodu ładowania i wyświetlania miniaturki bez zmian) ...
                 with Image.open(img_path) as img:
                     img.thumbnail(thumb_size, resampling)
                     photo = ImageTk.PhotoImage(img)

                 thumb_label = ttk.Label(self.screenshot_inner_frame, image=photo, relief="solid", borderwidth=1)
                 thumb_label.image = photo
                 thumb_label.grid(row=row, column=col, padx=5, pady=5)
                 thumb_label.bind("<Button-1>", lambda e, p=img_path: self.view_screenshot(p))

                 tooltip_text = ""
                 if is_manual and is_auto:
                     tooltip_text = "Screenshot dodany ręcznie (również znaleziony automatycznie)"
                 elif is_manual:
                     tooltip_text = "Screenshot dodany ręcznie"
                 elif is_auto:
                     tooltip_text = "Screenshot znaleziony automatycznie"

                 ToolTip(thumb_label, tooltip_text)
                 # Dostosuj menu kontekstowe - przekaż oba statusy
                 thumb_label.bind("<Button-3>", lambda e, p=img_path, man=is_manual, auto=is_auto: self.screenshot_context_menu(e, p, is_manual=man, is_auto=auto))

                 col += 1
                 if col >= max_cols:
                     col = 0
                     row += 1
             except Exception as e:
                 # ... (obsługa błędu ładowania miniaturki bez zmian) ...
                 logging.error(f"Błąd ładowania miniaturki screenshota '{img_path}': {e}")
                 error_label = ttk.Label(self.screenshot_inner_frame, text="Błąd", relief="solid", borderwidth=1, width=thumb_size[0]//8, height=thumb_size[1]//15)
                 error_label.grid(row=row, column=col, padx=5, pady=5)
                 col += 1
                 if col >= max_cols: col = 0; row += 1

         # Aktualizacja scrollregion po dodaniu wszystkich elementów
         self.screenshot_inner_frame.update_idletasks()
         self.screenshot_canvas.configure(scrollregion=self.screenshot_canvas.bbox("all"))

    # --- NOWA METODA POMOCNICZA ---
    def _remove_stale_screenshot_path(self, stale_path, was_manual, was_auto):
        """Usuwa nieistniejącą już ścieżkę screenshota z konfiguracji."""
        logging.warning(f"Usuwanie nieistniejącej ścieżki screenshota z konfiguracji: {stale_path}")
        path_removed = False
        if was_manual:
            manual_list = self.game_data.get("screenshots", [])
            if stale_path in manual_list:
                manual_list.remove(stale_path)
                path_removed = True
        if was_auto:
            auto_list = self.game_data.get("autoscan_screenshots", [])
            if stale_path in auto_list:
                auto_list.remove(stale_path)
                path_removed = True

        if path_removed:
            save_config(self.launcher.config)
            # Nie trzeba odświeżać UI, bo jesteśmy w trakcie odświeżania
    # --- KONIEC NOWEJ METODY ---

    def view_screenshot(self, image_path):
         """Otwiera pełnowymiarowy screenshot (używając domyślnej przeglądarki systemowej)."""
         try:
             if sys.platform == "win32":
                 os.startfile(os.path.normpath(image_path))
             elif sys.platform == "darwin": # macOS
                 subprocess.run(['open', image_path])
             else: # linux variants
                 subprocess.run(['xdg-open', image_path])
         except Exception as e:
             logging.error(f"Nie można otworzyć screenshota '{image_path}': {e}")
             messagebox.showerror("Błąd", f"Nie można otworzyć pliku:\n{image_path}\n\nBłąd: {e}", parent=self)

    def screenshot_context_menu(self, event, image_path, is_manual, is_auto): # Dodano is_auto
         """Wyświetla menu kontekstowe dla miniaturki screenshota."""
         menu = tk.Menu(self, tearoff=0, background="#2e2e2e", foreground="white")
         menu.add_command(label="Otwórz", command=lambda: self.view_screenshot(image_path))
         menu.add_separator()
         # --- NOWE ZMIANY: Logika przycisku Usuń ---
         # Dodaj opcję usunięcia z listy ręcznej, jeśli jest na niej
         if is_manual:
              menu.add_command(label="Usuń z listy ręcznej", command=lambda p=image_path: self.delete_screenshot(p, delete_manual=True))
         # Dodaj opcję usunięcia z listy automatycznej, jeśli jest na niej
         if is_auto:
              menu.add_command(label="Usuń z listy automatycznej", command=lambda p=image_path: self.delete_screenshot(p, delete_auto=True))
         # --- KONIEC NOWYCH ZMIAN ---
         menu.post(event.x_root, event.y_root)

    def delete_screenshot(self, image_path_to_delete, delete_manual=False, delete_auto=False):
         """Usuwa screenshot z odpowiednich list w konfiguracji."""
         # --- NOWE ZMIANY: Przepisana logika usuwania ---
         if not delete_manual and not delete_auto:
             logging.warning("Wywołano delete_screenshot bez określenia, z której listy usunąć.")
             return

         confirm_msg = "Czy na pewno chcesz usunąć ten screenshot z wybranej listy(list)?"
         if delete_auto and not delete_manual:
             confirm_msg += "\n(Plik na dysku NIE zostanie usunięty)." # Wyjaśnienie dla auto

         if messagebox.askyesno("Potwierdź Usunięcie", confirm_msg, parent=self):
             path_removed = False
             try:
                 # Usuń z listy ręcznej, jeśli zażądano
                 if delete_manual:
                     manual_screenshots = self.game_data.get("screenshots", [])
                     if image_path_to_delete in manual_screenshots:
                          manual_screenshots.remove(image_path_to_delete)
                          logging.info(f"Usunięto screenshot z listy ręcznej: {image_path_to_delete}")
                          path_removed = True
                     else: logging.warning(f"Screenshot {image_path_to_delete} nie znaleziony na liście ręcznej.")

                 # Usuń z listy automatycznej, jeśli zażądano
                 if delete_auto:
                     auto_screenshots = self.game_data.get("autoscan_screenshots", [])
                     if image_path_to_delete in auto_screenshots:
                          auto_screenshots.remove(image_path_to_delete)
                          logging.info(f"Usunięto screenshot z listy automatycznej: {image_path_to_delete}")
                          path_removed = True
                     else: logging.warning(f"Screenshot {image_path_to_delete} nie znaleziony na liście automatycznej.")

                 # Zapisz i odśwież, jeśli coś usunięto
                 if path_removed:
                     save_config(self.launcher.config)
                     self.refresh_details_data() # Odśwież galerię
                 else:
                      messagebox.showinfo("Informacja", "Screenshot nie został znaleziony na wybranej liście.", parent=self)

             except Exception as e:
                 logging.error(f"Błąd podczas usuwania screenshota '{image_path_to_delete}': {e}")
                 messagebox.showerror("Błąd", f"Nie udało się usunąć screenshota z listy:\n{e}", parent=self)
         # --- KONIEC NOWYCH ZMIAN ---
         else:
              # Ten komunikat nie powinien się pojawić, jeśli przycisk jest poprawnie wyłączany
              messagebox.showinfo("Informacja", "Tego screenshota nie można usunąć, ponieważ został znaleziony automatycznie lub już go usunięto z listy ręcznej.", parent=self)
              logging.warning(f"Próba usunięcia screenshota, którego nie ma na liście ręcznej lub jest tylko auto: {image_path_to_delete}")
         # --- KONIEC NOWYCH ZMIAN ---

    def _on_screenshot_mousewheel(self, event):
        """Przewija canvas ze screenshotami."""
        # --- ZMIANA: Użyj bind_all w __init__ i dodaj sprawdzanie widgetu ---
        try:
            widget_under_cursor = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError): # Obsługa błędów, gdy kursor jest poza oknem lub nad menu
             return

        is_ss_canvas_area = False
        curr = widget_under_cursor
        while curr is not None:
            if curr == self.screenshot_canvas:
                is_ss_canvas_area = True
                break
            if curr == self: # Ogranicz do tego okna Toplevel
                break
            try:
                curr = curr.master
            except tk.TclError: # Na wypadek zniszczonego widgetu
                 break

        if is_ss_canvas_area and self.screenshot_canvas.winfo_exists():
             scroll_val = -1 * int(event.delta / 120)
             view_start, view_end = self.screenshot_canvas.yview()
             if (scroll_val < 0 and view_start > 0.0) or \
                (scroll_val > 0 and view_end < 1.0):
                  self.screenshot_canvas.yview_scroll(scroll_val, "units")
                  return "break" # Zatrzymaj dalszą propagację
        # --- KONIEC ZMIANY ---

    # Zmodyfikuj refresh_details_data, aby ładowała checklistę
    def refresh_details_data(self):
         """Odświeża wszystkie dynamiczne dane w oknie szczegółów."""
         self.game_data = self.launcher.games.get(self.game_name)
         if not self.game_data: self.destroy(); return

         self.update_basic_info()
         self.load_description_and_notes()
         self.update_api_info()
         self.update_requirements()
         self.load_screenshots()
         # --- NOWE: Załaduj checklistę ---
         self._load_checklist()
         # --- KONIEC NOWEGO ---
         if hasattr(self, 'launcher_stats_frame'): # Sprawdź czy ramka istnieje
             self.create_launcher_stats_labels(self.launcher_stats_frame)
         if hasattr(self, 'action_buttons_frame'): # Sprawdź czy ramka istnieje
             self.create_launch_button_with_profiles(self.action_buttons_frame)


    def _load_checklist(self):
        """Wczytuje checklistę zadań do Treeview."""
        if not hasattr(self, 'checklist_tree') or not self.checklist_tree.winfo_exists():
             return

        # Wyczyść stare wpisy
        for item in self.checklist_tree.get_children():
            self.checklist_tree.delete(item)

        # Zdefiniuj tagi dla wyglądu
        self.checklist_tree.tag_configure('done', foreground='gray', font=('Segoe UI', 9, 'overstrike')) # Przekreślone dla ukończonych
        self.checklist_tree.tag_configure('pending', foreground='white', font=('Segoe UI', 9)) # Normalne dla oczekujących

        checklist_data = self.game_data.get("checklist", [])
        logging.debug(f"Ładowanie checklisty dla {self.game_name}: {len(checklist_data)} zadań.")

        for idx, item_data in enumerate(checklist_data):
             task_text = item_data.get("task", "Brak opisu")
             is_done = item_data.get("done", False)
             status_char = "☑" if is_done else "☐" # Użyj unicode checkboxów
             tag = 'done' if is_done else 'pending'
             # Użyjemy indeksu listy jako iid dla uproszczenia (uwaga na usuwanie!)
             iid = str(idx)
             self.checklist_tree.insert("", "end", iid=iid, values=(status_char, task_text), tags=(tag,))

    def _toggle_task_status_event(self, event):
         """Obsługuje zdarzenie przełączenia statusu zadania (np. podwójne kliknięcie)."""
         selected_items = self.checklist_tree.selection()
         if not selected_items: return
         selected_iid = selected_items[0]
         self._toggle_task_status(selected_iid)


    def _toggle_task_status(self, item_iid):
         """Przełącza status 'done' dla zadania o danym iid (indeksie)."""
         try:
              index = int(item_iid)
              checklist = self.game_data.setdefault("checklist", [])
              if 0 <= index < len(checklist):
                   # Przełącz stan 'done'
                   checklist[index]["done"] = not checklist[index].get("done", False)
                   # Zapisz zmiany
                   save_config(self.launcher.config)
                   # Odśwież tylko ten wiersz w Treeview dla lepszej wydajności
                   is_done = checklist[index]["done"]
                   status_char = "☑" if is_done else "☐"
                   tag = 'done' if is_done else 'pending'
                   self.checklist_tree.item(item_iid, values=(status_char, checklist[index].get("task")), tags=(tag,))
                   logging.info(f"Zmieniono status zadania {index} na {is_done} dla gry {self.game_name}")
              else:
                   logging.warning(f"Próba przełączenia statusu dla nieprawidłowego indeksu {index} w checkliście.")
         except (ValueError, IndexError) as e:
              logging.error(f"Błąd podczas przełączania statusu zadania (iid={item_iid}): {e}")


    def _add_task(self):
        """Dodaje nowe zadanie do checklisty."""
        new_task_desc = simpledialog.askstring("Nowe Zadanie", "Wpisz opis nowego zadania:", parent=self)
        if new_task_desc and new_task_desc.strip():
             new_task_desc = new_task_desc.strip()
             checklist = self.game_data.setdefault("checklist", [])
             checklist.append({"task": new_task_desc, "done": False})
             save_config(self.launcher.config)
             self._load_checklist() # Odśwież całą listę
             logging.info(f"Dodano nowe zadanie '{new_task_desc}' dla gry {self.game_name}")


    def _edit_task(self):
        """Edytuje opis zaznaczonego zadania."""
        selection = self.checklist_tree.selection()
        if not selection:
             messagebox.showwarning("Brak zaznaczenia", "Zaznacz zadanie, które chcesz edytować.", parent=self)
             return
        selected_iid = selection[0]

        try:
            index = int(selected_iid)
            checklist = self.game_data.setdefault("checklist", [])
            if 0 <= index < len(checklist):
                 current_desc = checklist[index].get("task", "")
                 new_desc = simpledialog.askstring("Edytuj Zadanie", "Wpisz nowy opis zadania:", initialvalue=current_desc, parent=self)
                 if new_desc and new_desc.strip() and new_desc.strip() != current_desc:
                      checklist[index]["task"] = new_desc.strip()
                      save_config(self.launcher.config)
                      self._load_checklist() # Odśwież całą listę
                      logging.info(f"Zmieniono opis zadania {index} na '{new_desc.strip()}' dla gry {self.game_name}")
            else:
                 logging.warning(f"Próba edycji nieprawidłowego indeksu {index} w checkliście.")
        except (ValueError, IndexError) as e:
            logging.error(f"Błąd podczas edycji zadania (iid={selected_iid}): {e}")

    def _delete_task(self):
        """Usuwa zaznaczone zadanie z checklisty."""
        selection = self.checklist_tree.selection()
        if not selection:
             messagebox.showwarning("Brak zaznaczenia", "Zaznacz zadanie, które chcesz usunąć.", parent=self)
             return
        selected_iid = selection[0]

        try:
            index = int(selected_iid)
            checklist = self.game_data.setdefault("checklist", [])
            if 0 <= index < len(checklist):
                 task_desc = checklist[index].get("task", f"Zadanie {index}")
                 if messagebox.askyesno("Potwierdź usunięcie", f"Czy na pewno chcesz usunąć zadanie:\n'{task_desc}'?", parent=self):
                      del checklist[index]
                      save_config(self.launcher.config)
                      self._load_checklist() # Odśwież całą listę
                      logging.info(f"Usunięto zadanie {index} ('{task_desc}') dla gry {self.game_name}")
            else:
                 logging.warning(f"Próba usunięcia nieprawidłowego indeksu {index} w checkliście.")
        except (ValueError, IndexError) as e:
             logging.error(f"Błąd podczas usuwania zadania (iid={selected_iid}): {e}")

    # --- KONIEC NOWYCH METOD ---

    def update_basic_info(self):
         """Aktualizuje podstawowe informacje (data, dev, pub, www)."""
         # Priorytet dla danych z API
         release = self.game_data.get("release_date", "-")
         devs = self.game_data.get("developers", [])
         pubs = self.game_data.get("publishers", [])
         website = self.game_data.get("website")

         self.release_label.config(text=f"Data wydania: {release}")
         self.developer_label.config(text=f"Deweloper: {', '.join(devs) if devs else '-'}")
         self.publisher_label.config(text=f"Wydawca: {', '.join(pubs) if pubs else '-'}")

         if website:
             self.website_button.config(state=tk.NORMAL)
         else:
             self.website_button.config(state=tk.DISABLED)

    def open_website(self):
        """Otwiera stronę WWW gry w przeglądarce."""
        url = self.game_data.get("website")
        if url:
            try:
                 # Dodajmy http:// jeśli brakuje
                 if not url.startswith(('http://', 'https://')):
                     url = 'http://' + url
                 # Użyj webbrowser do otwarcia
                 import webbrowser
                 webbrowser.open(url, new=2) # new=2 otwiera w nowej karcie
            except Exception as e:
                 logging.error(f"Nie można otworzyć strony WWW '{url}': {e}")
                 messagebox.showerror("Błąd", f"Nie można otworzyć adresu URL:\n{url}\n\nBłąd: {e}", parent=self)

    def create_launcher_stats_labels(self, parent_frame):
         """Tworzy etykiety ze statystykami z launchera (czas gry itp.)."""
         # Wyczyść starą zawartość, jeśli istnieje
         for widget in parent_frame.winfo_children():
             widget.destroy()
         parent_frame.columnconfigure(1, weight=1) # Ustawienie wagi dla tej ramki

         stats = {
             "Czas gry:": self.launcher.format_play_time(self.game_data.get('play_time', 0)),
             "Ukończenie:": f"{self.game_data.get('completion', 0)}%",
             "Ocena (moja):": str(self.game_data.get('rating', 'Brak')),
             "Wersja (moja):": self.game_data.get('version', '-'),
             "Ostatnio grane:": datetime.datetime.fromtimestamp(self.game_data.get('last_played', 0)).strftime('%Y-%m-%d %H:%M') if self.game_data.get('last_played') else "Nigdy",
             "Data dodania:": datetime.datetime.fromtimestamp(self.game_data.get('date_added', 0)).strftime('%Y-%m-%d') if self.game_data.get('date_added') else "-",
             "Gatunki (moje):": ", ".join(self.game_data.get('genres', []) or ["-"]),
             "Tagi (moje):": ", ".join(self.game_data.get('tags', []) or ["-"]),
         }
         row = 0
         # Wyświetl w dwóch kolumnach dla oszczędności miejsca
         items_per_col = (len(stats) + 1) // 2
         col = 0
         for i, (label, value) in enumerate(stats.items()):
              ttk.Label(parent_frame, text=label, font=("Segoe UI", 8, "bold")).grid(row=row, column=col*2, sticky="w", padx=2, pady=1)
              ttk.Label(parent_frame, text=value, font=("Segoe UI", 8)).grid(row=row, column=col*2+1, sticky="w", padx=2, pady=1)
              row += 1
              if row >= items_per_col:
                  row = 0
                  col += 1
         # Zapisz referencję do ramki dla odświeżania
         self.launcher_stats_frame = parent_frame


    def update_api_info(self):
        """Aktualizuje etykiety z danymi z API (platformy, gatunki, tagi)."""
        platforms = self.game_data.get("platforms", [])
        genres_api = self.game_data.get("genres_api", []) # Nowe pole na gatunki z API
        tags_api = self.game_data.get("tags_api", [])     # Nowe pole na tagi z API

        self.platforms_label.config(text=f"Platformy: {', '.join(platforms) if platforms else '-'}")
        self.genres_api_label.config(text=f"Gatunki (API): {', '.join(genres_api) if genres_api else '-'}")
        self.tags_api_label.config(text=f"Tagi (API): {', '.join(tags_api) if tags_api else '-'}")

    def update_requirements(self):
         """Aktualizuje pole tekstowe z wymaganiami systemowymi."""
         self.req_text.config(state=tk.NORMAL)
         self.req_text.delete("1.0", tk.END)
         req_pc = self.game_data.get("requirements_pc", {})
         req_str = ""
         if req_pc.get("minimum"):
             req_str += "Minimalne (PC):\n" + req_pc["minimum"] + "\n\n"
         if req_pc.get("recommended"):
             req_str += "Zalecane (PC):\n" + req_pc["recommended"] + "\n\n"
         # Można dodać wymagania dla innych platform, jeśli API je zwraca
         self.req_text.insert("1.0", req_str if req_str else "(Brak danych o wymaganiach)")
         self.req_text.config(state=tk.DISABLED)

    def toggle_notes_edit(self):
        """Przełącza tryb edycji pola notatek."""
        if self.notes_text['state'] == tk.DISABLED:
            self.notes_text.config(state=tk.NORMAL)
            self.edit_notes_button.config(text="Zapisz Notatki")
            self.notes_text.focus_set()
        else:
            # Zapisz notatki (tylko część użytkownika)
            full_text = self.notes_text.get("1.0", tk.END).strip()
            # Znajdź separator lub koniec opisu
            desc_end_marker = "--- NOTATKI UŻYTKOWNIKA ---"
            marker_pos = full_text.find(desc_end_marker)
            if marker_pos != -1:
                user_notes = full_text[marker_pos + len(desc_end_marker):].strip()
            else:
                # Jeśli nie ma markera, sprawdź czy był opis
                desc_marker = "--- OPIS ---"
                desc_pos = full_text.find(desc_marker)
                if self.game_data.get("description") and desc_pos != -1:
                     # Jeśli był opis, ale nie było markera notatek, to co jest poniżej to notatki
                     # Trzeba by to lepiej obsłużyć, np. zawsze wstawiać marker
                     user_notes = full_text # Na razie zapisz całość jako notatki
                else:
                     # Jeśli nie było opisu ani markera, całość to notatki
                     user_notes = full_text

            self.game_data["notes"] = user_notes
            save_config(self.launcher.config)
            self.notes_text.config(state=tk.DISABLED)
            self.edit_notes_button.config(text="Edytuj Notatki")
            messagebox.showinfo("Zapisano", "Notatki zostały zapisane.", parent=self)

    def create_launch_button_with_profiles(self, parent_frame, start_column=1): # Dodano start_column
        """Tworzy przycisk uruchomienia z menu profili w DANEJ KOLUMNIE."""
        # Wyczyść TYLKO przyciski uruchomienia (w zadanej kolumnie)
        for widget in parent_frame.winfo_children():
            grid_info = widget.grid_info()
            # Sprawdź, czy widget jest w odpowiedniej kolumnie
            if grid_info and grid_info.get("column") == start_column:
                 widget.destroy()

        profiles = self.game_data.get("launch_profiles", [])
        if not profiles: profiles = [{"name": "Default", "exe_path": None, "arguments": ""}]
        default_profile = profiles[0]

        # Ramka tylko dla przycisku uruchomienia i ewentualnego menu
        launch_btn_frame = ttk.Frame(parent_frame)
        # Umieść tę ramkę w przekazanej kolumnie
        launch_btn_frame.grid(row=0, column=start_column, padx=2, pady=2, sticky="nsew") # Użyj start_column

        # Skrócony tekst dla przycisku (może wystarczy samo "Uruchom")
        if len(profiles) == 1 and default_profile.get("name", "").lower() == "default":
            launch_btn_text = "Uruchom"
        else:
            launch_btn_text = f"Uruchom ({default_profile.get('name', '?')})" # Krótszy format

        launch_cmd = lambda p=default_profile: self.launcher.launch_game(self.game_name, profile=p)
        self.launch_button = ttk.Button(launch_btn_frame, text=launch_btn_text, style="Green.TButton", command=launch_cmd)

        if len(profiles) > 1:
            self.launch_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            profile_menu_btn = ttk.Menubutton(launch_btn_frame, text="▼", width=2, style="Toolbutton")
            profile_menu_btn.pack(side=tk.LEFT, fill=tk.Y, padx=(1, 0)) # Mały odstęp
            profile_menu = tk.Menu(profile_menu_btn, tearoff=0, background="#2e2e2e", foreground="white")
            profile_menu_btn["menu"] = profile_menu
            for profile in profiles:
                profile_name = profile.get("name", "Brak Nazwy")
                cmd = lambda p=profile: self.launcher.launch_game(self.game_name, profile=p)
                profile_menu.add_command(label=profile_name, command=cmd)
        else:
            self.launch_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Zapisz referencję do GŁÓWNEJ ramki akcji dla odświeżania w refresh_details_data
        self.action_buttons_frame = parent_frame
        
    def start_fetch_details_thread(self):
        """Inicjuje pobieranie danych w tle."""
        logging.info(f"Rozpoczynanie pobierania danych RAWG dla: {self.game_name}")
        # Wywołaj funkcję w GameLauncher, przekazując siebie jako instancję okna
        self.launcher.start_fetch_details_thread(self.game_name, self)

    def _on_details_fetched(self, result):
        logging.debug(f"Otrzymano wynik pobierania RAWG dla {self.game_name}: Success={result['success']}")
        if not self.winfo_exists():
             logging.warning("Okno szczegółów zamknięte przed zakończeniem pobierania RAWG."); return

        # Przywróć stan przycisku niezależnie od wyniku
        if hasattr(self, 'fetch_api_button'):
             self.fetch_api_button.config(text="Pobierz Dane", state=tk.NORMAL)

        if result["success"] and result["data"]:
            fetched_data = result["data"]
            data_changed = False
            cover_set_from_rawg = False
            force_cover_update = result.get("force_cover", False)

            # --- AKTUALIZACJA OKŁADKI (ostrożna) ---
            downloaded_cover_path = fetched_data.get("downloaded_cover_path") # Będzie None, jeśli pobieranie zawiodło

            if downloaded_cover_path and os.path.exists(downloaded_cover_path): # Sprawdź, czy mamy poprawną ścieżkę
                # Zapisz ścieżkę RAWG, nawet jeśli jej nie użyjemy teraz
                if self.game_data.get("cover_rawg") != downloaded_cover_path:
                    self.game_data["cover_rawg"] = downloaded_cover_path
                    data_changed = True

                current_cover = self.game_data.get("cover_image")
                should_set_cover = False

                if force_cover_update: # Wymuszone przez użytkownika
                    should_set_cover = True
                    logging.info(f"Wymuszone ustawienie okładki RAWG dla '{self.game_name}'.")
                elif self.game_data.get("_auto_cover"): # Obecna to placeholder
                     should_set_cover = True
                     logging.info(f"Ustawianie okładki RAWG dla '{self.game_name}' (zastępuje placeholder).")
                elif not current_cover or not os.path.exists(current_cover): # Brak okładki lub stara nie istnieje
                    should_set_cover = True
                    logging.info(f"Ustawianie pobranej okładki RAWG dla '{self.game_name}', ponieważ brak istniejącej.")

                if should_set_cover:
                    if self.game_data.get("cover_image") != downloaded_cover_path:
                        self.game_data["cover_image"] = downloaded_cover_path
                        self.game_data.pop("_auto_cover", None)
                        # Zapisz też ścieżkę jako własną, jeśli nie było wcześniej własnej? Raczej nie.
                        # self.game_data.setdefault("cover_custom", downloaded_cover_path)
                        data_changed = True
                        cover_set_from_rawg = True
                else:
                    logging.info(f"Gra '{self.game_name}' ma już własną okładkę. Pobrano RAWG, ale nie ustawiono jako aktywnej.")

            elif downloaded_cover_path: # Ścieżka była zwrócona, ale plik nie istnieje (błąd zapisu?)
                 logging.error(f"Pobrana ścieżka okładki RAWG '{downloaded_cover_path}' nie wskazuje na istniejący plik.")
            # Jeśli downloaded_cover_path to None, nic nie robimy z cover_image
            # --- KONIEC AKTUALIZACJI OKŁADKI ---


            # --- AKTUALIZACJA POZOSTAŁYCH DANYCH (bez zmian) ---
            fields_to_update = ["rawg_id", "rawg_slug", "description", "release_date", "website", "developers", "publishers", "genres_api", "tags_api", "platforms", "requirements_pc"]
            for field in fields_to_update:
                if field in fetched_data:
                    old_value = self.game_data.get(field)
                    new_value = fetched_data[field]
                    if old_value != new_value:
                         self.game_data[field] = new_value
                         data_changed = True
            # --- KONIEC AKTUALIZACJI POZOSTAŁYCH DANYCH ---


            # --- ZAPIS KONFIGURACJI (tylko jeśli coś się zmieniło) ---
            if data_changed:
                logging.info(f"Dane gry '{self.game_name}' zostały zaktualizowane. Zapisywanie konfiguracji.")
                save_config(self.launcher.config)
            else:
                 logging.info(f"Dane z RAWG dla '{self.game_name}' nie różniły się od istniejących.")


            # --- ODŚWIEŻENIE UI ---
            self.refresh_details_data()

            # --- WYCZYSZCZENIE CACHE (jeśli ustawiono nową okładkę) ---
            if cover_set_from_rawg:
                try:
                    load_photoimage_from_path.cache_clear()
                    logging.info("Wyczyszczono cache load_photoimage_from_path z powodu ustawienia okładki z RAWG.")
                    self.launcher.root.after(150, lambda gn=self.game_name: self.launcher._force_refresh_tile(gn))
                except Exception as e:
                    logging.error(f"Nie udało się wyczyścić cache PhotoImage po pobraniu okładki RAWG: {e}")

            if data_changed or cover_set_from_rawg: # Pokaż sukces jeśli cokolwiek się zmieniło lub ustawiono okładkę
                messagebox.showinfo("Sukces", "Pobrano i zaktualizowano dane gry.", parent=self)
            else:
                messagebox.showinfo("Informacja", "Pobrano dane gry, ale nie wymagały one aktualizacji.", parent=self)


        elif result["error"]:
            messagebox.showerror("Błąd Pobierania", f"Nie udało się pobrać danych z RAWG:\n{result['error']}", parent=self)
        else:
             messagebox.showerror("Błąd", "Wystąpił nieznany błąd podczas pobierania danych.", parent=self)

    def remove_cover(self):
        """Usuwa obecną okładkę i ustawia pustą ścieżkę (co spowoduje użycie domyślnej)."""
        original_cover_path = self.game_data.get("cover_image")
        cover_changed = False
        if original_cover_path:
            cover_changed = True
            # Usuń plik tylko jeśli był zarządzany (w IMAGES_FOLDER)
            if os.path.exists(original_cover_path) and os.path.dirname(os.path.abspath(original_cover_path)) == os.path.abspath(IMAGES_FOLDER):
                try:
                    os.remove(original_cover_path)
                    logging.info(f"Usunięto zarządzaną okładkę: {original_cover_path}")
                except OSError as e:
                    logging.error(f"Nie udało się usunąć pliku okładki {original_cover_path}: {e}")

            self.game_data["cover_image"] = "" # Ustaw pustą ścieżkę
            self.game_data.pop("cover_custom", None) # Usuń ścieżkę własną
            self.game_data.pop("cover_rawg", None)   # Usuń ścieżkę rawg
            save_config(self.launcher.config)
            if cover_changed: load_photoimage_from_path.cache_clear()
            self.refresh_details_data() # Odśwież widok szczegółów
            self.launcher.root.after(150, lambda gn=self.game_name: self.launcher._force_refresh_tile(gn))
        else:
            messagebox.showinfo("Informacja", "Brak okładki do usunięcia.", parent=self)

    def fetch_cover_from_rawg(self, force=False):
        """Pobiera (lub próbuje użyć zapisanej) okładki z RAWG."""
        rawg_cover_path = self.game_data.get("cover_rawg")

        if rawg_cover_path and os.path.exists(rawg_cover_path) and not force:
             # Mamy zapisaną i istniejącą okładkę RAWG, użyjmy jej
             if self.game_data.get("cover_image") != rawg_cover_path:
                  self.game_data["cover_image"] = rawg_cover_path
                  self.game_data.pop("_auto_cover", None)
                  save_config(self.launcher.config)
                  load_photoimage_from_path.cache_clear()
                  self.refresh_details_data()
                  self.launcher.root.after(150, lambda gn=self.game_name: self.launcher._force_refresh_tile(gn))
                  logging.info(f"Ustawiono zapisaną okładkę RAWG dla {self.game_name}")
             else:
                  messagebox.showinfo("Informacja", "Okładka z RAWG jest już ustawiona.", parent=self)
        else:
             # Nie mamy zapisanej lub chcemy wymusić pobranie nowej
             logging.info(f"Rozpoczynam pobieranie danych RAWG (force_cover={force}) dla {self.game_name}, aby uzyskać okładkę.")
             self.launcher.start_fetch_details_thread(self.game_name, self, force=force)

    # --- NOWE: Menu kontekstowe okładki ---
    def show_cover_context_menu(self, event):
         """Wyświetla menu kontekstowe dla obrazka okładki."""
         menu = tk.Menu(self, tearoff=0, background="#2e2e2e", foreground="white")
         menu.add_command(label="Ustaw Własną Okładkę...", command=self.select_custom_cover)
         # Opcja użycia okładki RAWG tylko jeśli jest zapisana ścieżka
         if self.game_data.get("cover_rawg"):
              menu.add_command(label="Użyj Okładki z RAWG", command=lambda: self.fetch_cover_from_rawg(force=False)) # force=False tylko użyje zapisanej
         menu.add_command(label="Pobierz Ponownie z RAWG", command=lambda: self.fetch_cover_from_rawg(force=True)) # force=True wymusi pobranie
         # Opcja usunięcia tylko jeśli jest jakaś okładka ustawiona
         if self.game_data.get("cover_image"):
              menu.add_separator()
              menu.add_command(label="Usuń Okładkę", command=self.remove_cover)
         menu.post(event.x_root, event.y_root)

    def toggle_cover_source(self):
        """Przełącza między okładką własną, RAWG i placeholderem."""
        curr   = self.game_data.get("cover_image")
        rawg   = self.game_data.get("cover_rawg")
        custom = self.game_data.get("cover_custom")
        if curr == custom and rawg:
            self.game_data["cover_image"] = rawg
        elif curr == rawg and custom:
            self.game_data["cover_image"] = custom
        else:
            self.game_data["cover_image"] = ""
            self.game_data["_auto_cover"] = True
        save_config(self.launcher.config)
        load_photoimage_from_path.cache_clear()
        self.launcher.update_game_grid()
        self.refresh_details_data()


class AddProfileDialog(tk.Toplevel):
    """Małe okno dialogowe do dodawania/edycji profilu uruchomieniowego w oknie weryfikacji."""
    def __init__(self, parent, game_folder, existing_profiles, callback, initial_data=None):
        super().__init__(parent)
        self.parent = parent # Rodzicem jest ScanVerificationWindow
        self.game_folder = game_folder
        self.existing_profiles = existing_profiles # Lista profili już dodanych dla tej gry w oknie weryfikacji
        self.callback = callback # Funkcja do wywołania po zapisaniu
        self.result = None # Przechowa dane profilu

        is_edit = initial_data is not None
        title = "Edytuj Profil Uruchomieniowy" if is_edit else "Dodaj Profil Uruchomieniowy"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent) # Ustaw jako okno zależne od rodzica

        # Pola
        ttk.Label(self, text="Nazwa profilu:", background="#1e1e1e", foreground="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_var = tk.StringVar(value=initial_data['name'] if is_edit else f"Profil {len(existing_profiles) + 1}")
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(self, text="Plik .exe:", background="#1e1e1e", foreground="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.exe_var = tk.StringVar(value=initial_data['exe_path'] if is_edit and initial_data.get('exe_path') else "")
        self.exe_entry = ttk.Entry(self, textvariable=self.exe_var, width=40, state='readonly') # Tylko do odczytu, zmieniane przez przycisk
        self.exe_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        exe_btn = ttk.Button(self, text="Wybierz...", command=self._select_exe)
        exe_btn.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(self, text="Argumenty:", background="#1e1e1e", foreground="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.args_var = tk.StringVar(value=initial_data['arguments'] if is_edit else "")
        self.args_entry = ttk.Entry(self, textvariable=self.args_var, width=40)
        self.args_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Przyciski
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        save_button = ttk.Button(btn_frame, text="Zapisz", command=self._save)
        save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(btn_frame, text="Anuluj", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.name_entry.focus_set()
        self.wait_window(self) # Czekaj na zamknięcie tego okna

    def _select_exe(self):
        """Otwiera dialog wyboru pliku .exe w folderze gry."""
        path = filedialog.askopenfilename(
            title="Wybierz plik wykonywalny dla profilu",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
            initialdir=self.game_folder, # Zaczynaj w folderze gry
            parent=self # Rodzicem jest to okno dialogowe
        )
        if path:
            # Sprawdź, czy wybrany plik jest w folderze gry lub jego podfolderze
            if os.path.commonpath([self.game_folder, path]) == self.game_folder:
                 self.exe_var.set(path)
            else:
                 messagebox.showerror("Błąd ścieżki", "Plik wykonywalny musi znajdować się w folderze gry lub jego podfolderze.", parent=self)


    def _save(self):
        """Waliduje i zapisuje dane profilu."""
        name = self.name_var.get().strip()
        exe_path = self.exe_var.get().strip() or None # Zapisz None, jeśli puste (oznacza użycie głównego exe)
        arguments = self.args_var.get().strip()

        if not name:
            messagebox.showerror("Błąd", "Nazwa profilu jest wymagana.", parent=self)
            return
        if not exe_path:
            messagebox.showerror("Błąd", "Ścieżka pliku .exe jest wymagana dla dodatkowego profilu.", parent=self)
            return

        # Sprawdź unikalność nazwy wśród istniejących (w tej sesji weryfikacji)
        # Pomijamy sprawdzanie, jeśli edytujemy (bo initial_data będzie miało starą nazwę)
        # Trzeba by przekazać indeks edytowanego profilu, aby to zaimplementować poprawnie.
        # Na razie uproszczenie - zakładamy, że użytkownik nie stworzy duplikatu ręcznie.
        # is_edit = initial_data is not None ...

        self.result = {"name": name, "exe_path": exe_path, "arguments": arguments}
        self.callback(self.result) # Wywołaj callback z wynikiem
        self.destroy()


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


class ThemeEditorWindow(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji niestandardowego motywu."""
# W klasie ThemeEditorWindow

    def __init__(self, parent, launcher_instance, theme_name=None, theme_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None
        self.original_name = theme_name

        # --- NOWE: Zapisz oryginalne ustawienia TScrollbar ---
        self.original_scrollbar_settings = {}
        try:
            active_theme_name_main = self.launcher.settings.get('theme', 'Dark')
            all_themes_main = self.launcher.get_all_available_themes()
            active_theme_def_main = all_themes_main.get(active_theme_name_main, THEMES.get('Dark', {}))

            # Klucze, które chcemy zapisać i przywrócić dla TScrollbar
            scrollbar_keys_to_save = ['background', 'troughcolor', 'bordercolor', 'arrowcolor']
            # UWAGA: 'background' w ttk.Scrollbar to kolor suwaka, 'troughcolor' to tło
            # Musimy mapować klucze z naszego motywu na opcje stylu TScrollbar
            # 'scrollbar_slider' -> 'background' w stylu
            # 'scrollbar_trough' -> 'troughcolor' w stylu
            # 'background' (ogólne tło) -> 'bordercolor' w stylu
            # 'foreground' (ogólny tekst) -> 'arrowcolor' w stylu

            self.original_scrollbar_settings['background'] = active_theme_def_main.get('scrollbar_slider', '#555555')
            self.original_scrollbar_settings['troughcolor'] = active_theme_def_main.get('scrollbar_trough', '#1e1e1e')
            self.original_scrollbar_settings['bordercolor'] = active_theme_def_main.get('background', '#1e1e1e')
            self.original_scrollbar_settings['arrowcolor'] = active_theme_def_main.get('foreground', 'white')
            logging.debug(f"Zapisano oryginalne ustawienia TScrollbar: {self.original_scrollbar_settings}")
        except Exception as e:
            logging.error(f"Błąd przy zapisywaniu oryginalnych ustawień TScrollbar: {e}")
        # --- KONIEC NOWEGO ---

        is_edit = theme_name is not None and theme_data is not None
        title = f"Edytuj Motyw: {theme_name}" if is_edit else "Dodaj Nowy Motyw"
        self.title(title)
        self.configure(bg="#1e1e1e")
        # --- ZMIANA: Zwiększ wysokość okna ---
        # Poprzednio było 550x780, spróbujmy np. 550x820 lub nawet więcej
        # Dostosuj tę wartość, aby pasowała do Twojego ekranu i liczby pól kolorów
        self.geometry("550x840") # Przykładowa nowa wysokość
        self.minsize(500, 750)  # Odpowiednio zwiększ minimalną wysokość
        # --- KONIEC ZMIANY ---
        self.grab_set()
        self.transient(parent)

        # --- Słownik tłumaczeń dla kluczy kolorów ---
        self.COLOR_KEY_TRANSLATIONS = {
            'background': 'Tło Główne',
            'foreground': 'Tekst Główny',
            'button_background': 'Tło Przycisku',
            'button_foreground': 'Tekst Przycisku',
            'entry_background': 'Tło Pola Tekst.',
            'tree_background': 'Tło Listy/Drzewa',
            'tree_heading': 'Nagłówek Listy',
            'scrollbar_trough': 'Tło Paska Przew.',
            'scrollbar_slider': 'Suwak Paska Przew.',
            'link_foreground': 'Kolor Linku',
            # --- NOWE TŁUMACZENIA ---
            'chart_bar_color': 'Kolor Słupków Wykresu',
            'chart_axis_color': 'Kolor Osi Wykresu',
            # --- KONIEC NOWYCH ---
        }
        # --- Koniec słownika tłumaczeń ---

        # Pobierz kolor tła Entry z aktywnego motywu
        active_theme_name = self.launcher.settings.get('theme', 'Dark')
        all_themes = self.launcher.get_all_available_themes()
        active_theme_def = all_themes.get(active_theme_name, THEMES.get('Dark', {}))
        active_entry_bg_color = active_theme_def.get('entry_background', '#2e2e2e')
        hardcoded_fg_color = '#ffffff'

        # Styl dla Entry
        self.hex_entry_style_name = f"HexInput{id(self)}.TEntry"
        style = ttk.Style()
        style.configure(
            self.hex_entry_style_name,
            fieldbackground=active_entry_bg_color,
            foreground=hardcoded_fg_color,
            insertcolor=hardcoded_fg_color
        )

        # --- Główny kontener ---
        content_container = ttk.Frame(self, style="TFrame")
        content_container.pack(fill="both", expand=True, padx=5, pady=5)
        content_container.rowconfigure(1, weight=0)
        content_container.rowconfigure(2, weight=1)
        content_container.columnconfigure(0, weight=1)

        # --- Pole Nazwy Motywu ---
        name_frame = ttk.Frame(content_container, style="TFrame")
        name_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Nazwa Motywu:").grid(row=0, column=0, padx=5)
        self.name_var = tk.StringVar(value=theme_name if is_edit else "Mój Motyw")
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew")

        # --- Ramka na pola kolorów ---
        scrollable_frame = ttk.Frame(content_container, style="TFrame")
        scrollable_frame.grid(row=1, column=0, sticky="nsew")

        # --- Pola Edycji Kolorów ---
        self.color_vars = {}
        template_theme = THEMES.get('Dark', {})
        current_theme_data = theme_data if is_edit else template_theme
        colors_frame = ttk.LabelFrame(scrollable_frame, text=" Kolory (format HEX: #RRGGBB) ", padding=10)
        colors_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        colors_frame.columnconfigure(1, weight=1)
        colors_frame.columnconfigure(2, weight=0)

        row_idx = 0
        for key in template_theme.keys():
            # --- ZMIANA: Użyj polskiej nazwy dla etykiety ---
            display_name = self.COLOR_KEY_TRANSLATIONS.get(key, key) # Pobierz tłumaczenie lub użyj klucza
            ttk.Label(colors_frame, text=f"{display_name}:").grid(row=row_idx, column=0, padx=5, pady=3, sticky="w")
            # --- KONIEC ZMIANY ---

            default_color = template_theme.get(key, "#ffffff")
            initial_value_raw = current_theme_data.get(key, default_color)
            initial_value = "#ffffff" if initial_value_raw == "white" else initial_value_raw

            color_var = tk.StringVar(value=initial_value)
            color_entry = ttk.Entry(colors_frame, textvariable=color_var, width=10, style=self.hex_entry_style_name)
            color_entry.grid(row=row_idx, column=1, padx=5, pady=3, sticky="ew")

            color_button = tk.Button(
                colors_frame, text=" ", bg=initial_value, width=3, relief="solid",
                borderwidth=1,
                # --- ZMIANA: Przekaż polską nazwę do _choose_color ---
                command=lambda k=key, var=color_var, dn=display_name: self._choose_color(k, var, dn)
                # --- KONIEC ZMIANY ---
            )
            color_button.grid(row=row_idx, column=2, padx=5, pady=3)

            color_var.trace_add("write", lambda name, index, mode, var=color_var, button=color_button: self._update_color_preview(var, button))
            # --- ZMIANA: Zapisz też polską nazwę ---
            self.color_vars[key] = {"var": color_var, "entry": color_entry, "button": color_button, "display_name": display_name}
            # --- KONIEC ZMIANY ---
            row_idx += 1
        
        # --- NOWY PRZYCISK: Losuj Kolory (obok etykiety LabelFrame) ---
        randomize_btn = ttk.Button(colors_frame, text="Losuj Wszystkie", command=self._randomize_colors)
        # Umieśćmy go np. w prawym górnym rogu LabelFrame lub pod listą kolorów
        # Dla prostoty na razie pod listą:
        randomize_btn.grid(row=row_idx, column=0, columnspan=3, pady=10, sticky="ew") # Rozciągnij na wszystkie kolumny
        # --- KONIEC NOWEGO PRZYCISKU ---

        # --- Ramka podglądu ---
        self.preview_frame = ttk.LabelFrame(content_container, text=" Podgląd na Żywo ", padding=10)
        self.preview_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.preview_frame.columnconfigure(0, weight=1)
        # --- NOWE: Kolumna dla scrollbara ---
        self.preview_frame.columnconfigure(2, weight=0) # Dodano kolumnę 2
        # --- KONIEC NOWEGO ---

        # Widgety podglądu
        self.preview_style_prefix = f"Preview{id(self)}."
        # ... (kod tworzenia preview_label, preview_button, preview_entry, preview_link) ...
        self.preview_label = ttk.Label(self.preview_frame, text="Przykładowa etykieta", style=self.preview_style_prefix + "TLabel")
        self.preview_label.grid(row=0, column=0, pady=3, sticky="w")
        self.preview_button = ttk.Button(self.preview_frame, text="Przycisk", style=self.preview_style_prefix + "TButton")
        self.preview_button.grid(row=1, column=0, pady=3, sticky="w")
        self.preview_entry = ttk.Entry(self.preview_frame, style=self.preview_style_prefix + "TEntry")
        self.preview_entry.insert(0, "Pole tekstowe")
        self.preview_entry.grid(row=2, column=0, pady=3, sticky="ew")
        self.preview_link = ttk.Button(self.preview_frame, text="Link", style=self.preview_style_prefix + "Link.TButton")
        self.preview_link.grid(row=0, column=1, pady=3, padx=10, sticky="w")


        # Podgląd Treeview
        preview_tree_frame = ttk.Frame(self.preview_frame)
        # --- ZMIANA: Umieść w kolumnie 0, columnspan=2 ---
        preview_tree_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        # --- KONIEC ZMIANY ---
        preview_tree_frame.columnconfigure(0, weight=1)
        self.preview_tree = ttk.Treeview(preview_tree_frame, columns=("col1",), height=2, style=self.preview_style_prefix + "Treeview")
        self.preview_tree.heading("col1", text="Nagłówek")
        self.preview_tree.column("col1", width=100)
        self.preview_tree.insert("", "end", text="Item 1", values=("Wartość 1",))
        self.preview_tree.insert("", "end", text="Item 2", values=("Wartość 2",))
        self.preview_tree.grid(row=0, column=0, sticky="ew")

        # --- NOWE: Dodanie podglądu Scrollbar ---
        # Usuwamy opcję style=...
        self.preview_scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical")
        self.preview_scrollbar.grid(row=3, column=2, pady=5, padx=(2,0), sticky="ns")
        # --- KONIEC ZMIANY ---

        # --- Przyciski na Dole Okna ---
        button_frame = ttk.Frame(self, style="TFrame")
        button_frame.pack(fill="x", pady=10, side="bottom")
        button_frame.columnconfigure((0, 1), weight=1)
        save_btn = ttk.Button(button_frame, text="Zapisz Motyw", command=self._save)
        save_btn.grid(row=0, column=0, padx=10, sticky="e")
        cancel_btn = ttk.Button(button_frame, text="Anuluj", command=self._on_close_editor)
        cancel_btn.grid(row=0, column=1, padx=10, sticky="w")

        # --- NOWE: Bindowanie do własnej metody zamykania ---
        self.protocol("WM_DELETE_WINDOW", self._on_close_editor)
        # --- KONIEC NOWEGO ---

        # --- Finalizacja ---
        self.name_entry.focus_set()
        self._apply_preview_styles()
        self.wait_window(self)

    # --- NOWA METODA: Aplikuje style do widgetów podglądu ---
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
                theme[key] = THEMES['Dark'].get(key, "#ffffff")
                valid_theme = False
                # Nie oznaczamy już błędu w Entry tutaj, bo _update_color_preview tego nie robi

        if not valid_theme:
            logging.warning("Wykryto nieprawidłowe kody HEX w edytorze motywów. Podgląd używa częściowo domyślnych wartości.")

        prefix = self.preview_style_prefix

        try:
            # ... (style Label, Button, Entry, Link bez zmian) ...
            preview_style.configure(prefix + "TLabel", background=theme.get('background', '#1e1e1e'), foreground=theme.get('foreground', 'white'))
            self.preview_label.configure(style=prefix + "TLabel")
            preview_style.configure(prefix + "TButton", background=theme.get('button_background', '#2e2e2e'), foreground=theme.get('button_foreground', 'white'))
            self.preview_button.configure(style=prefix + "TButton")
            preview_style.configure(prefix + "TEntry", fieldbackground=theme.get('entry_background', '#2e2e2e'), foreground=theme.get('foreground', 'white'), insertbackground=theme.get('foreground', 'white'))
            self.preview_entry.configure(style=prefix + "TEntry")
            preview_style.configure(prefix + "Link.TButton", foreground=theme.get('link_foreground', '#66b3ff'), background=theme.get('background', '#1e1e1e'), padding=0, relief="flat", borderwidth=0)
            preview_style.map(prefix + "Link.TButton", underline=[('active', 1)])
            self.preview_link.configure(style=prefix + "Link.TButton")

            # Styl Treeview (bez zmian)
            preview_style.configure(prefix + "Treeview", background=theme.get('tree_background', '#2e2e2e'), foreground=theme.get('foreground', 'white'), fieldbackground=theme.get('tree_background', '#2e2e2e'))
            preview_style.map(prefix + "Treeview", background=[('selected', '#0078d7')])
            preview_style.configure(prefix + "Treeview.Heading", background=theme.get('tree_heading', '#3e3e3e'), foreground=theme.get('foreground', 'white'))
            self.preview_tree.configure(style=prefix + "Treeview")

            # --- ZMIANA: Konfiguruj globalny styl TScrollbar dla tego okna ---
            preview_style.configure(
                "TScrollbar", # Zamiast prefix + "TScrollbar"
                background=theme.get('scrollbar_slider', '#555555'),
                troughcolor=theme.get('scrollbar_trough', '#1e1e1e'),
                bordercolor=theme.get('background', '#1e1e1e'),
                arrowcolor=theme.get('foreground', 'white')
            )
            # Usunięto: self.preview_scrollbar.configure(style=...)
            # Styl zostanie zastosowany automatycznie do wszystkich TScrollbar w tym oknie
            # --- KONIEC ZMIANY ---

            self.preview_frame.config(style="TFrame")

        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas stosowania stylów podglądu: {e}")
        except Exception as e:
             logging.exception("Nieoczekiwany błąd podczas stosowania stylów podglądu.")

    # --- KONIEC NOWEJ METODY ---

    # --- ZMIANA: Aktualizuje tło przycisku ---
    # Zmień sygnaturę, aby przyjmowała domyślny kolor tekstu (fg)
# W klasie ThemeEditorWindow
    # --- NOWA METODA ---
    def _randomize_colors(self):
        """Generuje losowe kolory HEX dla wszystkich pól motywu."""
        logging.info("Losowanie kolorów motywu...")
        for key, data in self.color_vars.items():
            # Generuj 6 losowych cyfr szesnastkowych
            random_hex = ''.join([random.choice('0123456789abcdef') for _ in range(6)])
            random_color_code = f"#{random_hex}"

            # Ustaw nową wartość w StringVar (to wywoła _update_color_preview i _apply_preview_styles)
            data["var"].set(random_color_code)
        messagebox.showinfo("Losowanie Zakończone", "Kolory zostały wylosowane! Sprawdź podgląd.", parent=self)
    # --- KONIEC NOWEJ METODY ---
# W klasie ThemeEditorWindow

    # Zaktualizowana metoda - usuwa parametr color_entry i logikę z nim związaną
    def _update_color_preview(self, color_var, color_button):
        """Aktualizuje kolor tła przycisku podglądu i odświeża cały podgląd."""
        color_code = color_var.get()
        is_valid = self._is_valid_hex_color(color_code)

        try:
            # Ustaw tło przycisku (nawet jeśli kod jest zły, użyje koloru zastępczego)
            color_button.config(bg=color_code if is_valid else "SystemButtonFace")
            # Usunięto logikę zmiany koloru tekstu Entry
        except tk.TclError:
            color_button.config(bg="SystemButtonFace")
            # Usunięto logikę zmiany koloru tekstu Entry

        # Odśwież cały podgląd, aby zobaczyć efekt w innych widgetach
        self._apply_preview_styles()

    def _is_valid_hex_color(self, color_code):
        """Sprawdza prostym regexem, czy string to poprawny kod HEX."""
        return re.match(r'^#[0-9a-fA-F]{6}$', color_code)

    # --- NOWA METODA: Otwiera selektor kolorów ---
    # Dodano argument display_name
    def _choose_color(self, key, color_var, display_name):
        """Otwiera systemowy selektor kolorów i aktualizuje zmienną oraz przycisk."""
        current_color = color_var.get()
        # --- ZMIANA: Użyj display_name w tytule ---
        color_info = colorchooser.askcolor(initialcolor=current_color, title=f"Wybierz kolor dla: {display_name}", parent=self)
        # --- KONIEC ZMIANY ---

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
            messagebox.showerror("Błąd", "Nazwa motywu nie może być pusta.", parent=self)
            return

        # Sprawdź, czy nazwa nie koliduje (poza sobą, jeśli edytujemy)
        # --- ZMIANA: Użyj globalnego THEMES ---
        all_builtin_themes = list(THEMES.keys())
        # --- KONIEC ZMIANY ---
        all_custom_themes = list(self.launcher.config.get("settings", {}).get("custom_themes", {}).keys())

        if new_name in all_builtin_themes:
            messagebox.showerror("Błąd Nazwy", f"Nazwa '{new_name}' jest zarezerwowana dla motywu wbudowanego.", parent=self)
            return
        if new_name != self.original_name and new_name in all_custom_themes:
            messagebox.showerror("Błąd Nazwy", f"Motyw niestandardowy o nazwie '{new_name}' już istnieje.", parent=self)
            return

        # Zbierz i zwaliduj kolory
        theme_def = {}
        has_error = False
        for key, data in self.color_vars.items():
            color_code = data["var"].get().strip()
            if self._is_valid_hex_color(color_code):
                theme_def[key] = color_code
                data["entry"].config(foreground="SystemWindowText") # Resetuj kolor tekstu
            else:
                messagebox.showerror("Błąd Koloru", f"Nieprawidłowy format kodu HEX dla '{key}': {color_code}\nOczekiwano formatu #RRGGBB.", parent=self)
                data["entry"].config(foreground="red") # Oznacz błędne pole
                has_error = True
                # Nie przerywamy, żeby oznaczyć wszystkie błędy
                # return

        if has_error:
            return # Przerwij, jeśli były błędy w kolorach

        # Zwróć wynik
        self.result = {"name": new_name, "theme_def": theme_def}

        # --- NOWE: Po zapisie, zastosuj styl aktywnego motywu launchera ---
        # To jest ważne, jeśli edytowany motyw nie stał się od razu aktywny
        # lub jeśli anulujemy zmiany w motywie, który był aktywny.
        try:
            active_theme_name_launcher = self.launcher.settings.get('theme', 'Dark')
            all_themes_launcher = self.launcher.get_all_available_themes()
            active_theme_def_launcher = all_themes_launcher.get(active_theme_name_launcher, THEMES.get('Dark', {}))

            # Klucze dla TScrollbar
            bg_slider = active_theme_def_launcher.get('scrollbar_slider', '#555555')
            bg_trough = active_theme_def_launcher.get('scrollbar_trough', '#1e1e1e')
            bg_border = active_theme_def_launcher.get('background', '#1e1e1e')
            fg_arrow = active_theme_def_launcher.get('foreground', 'white')

            main_style = ttk.Style()
            main_style.configure(
                "TScrollbar",
                background=bg_slider,
                troughcolor=bg_trough,
                bordercolor=bg_border,
                arrowcolor=fg_arrow
            )
            logging.info("Zastosowano styl TScrollbar aktywnego motywu launchera po zapisie.")
            self.launcher.root.update_idletasks()
        except Exception as e:
            logging.error(f"Błąd przy stosowaniu stylu TScrollbar aktywnego motywu po zapisie: {e}")
        # --- KONIEC NOWEGO ---

        self.destroy()
    # --- NOWA METODA ---
    def _on_close_editor(self):
        """Przywraca oryginalny styl TScrollbar przed zamknięciem edytora."""
        logging.debug("Zamykanie ThemeEditorWindow, przywracanie oryginalnego TScrollbar...")
        try:
            # Zastosuj zapisane oryginalne ustawienia do globalnego stylu TScrollbar
            # używanego przez główną aplikację.
            # Musimy odwołać się do instancji stylu launchera,
            # ale `ttk.Style()` powinno dać nam tę samą instancję.
            main_style = ttk.Style() # Powinno dać referencję do globalnego stylu
            if self.original_scrollbar_settings:
                main_style.configure(
                    "TScrollbar", # Konfigurujemy globalny styl TScrollbar
                    background=self.original_scrollbar_settings.get('background'),
                    troughcolor=self.original_scrollbar_settings.get('troughcolor'),
                    bordercolor=self.original_scrollbar_settings.get('bordercolor'),
                    arrowcolor=self.original_scrollbar_settings.get('arrowcolor')
                )
                logging.info("Przywrócono oryginalny styl TScrollbar dla głównego okna.")
                # Wymuś odświeżenie UI launchera, aby zmiana była widoczna
                self.launcher.root.update_idletasks()
            else:
                logging.warning("Brak zapisanych oryginalnych ustawień TScrollbar do przywrócenia.")
        except Exception as e:
            logging.error(f"Błąd przy przywracaniu oryginalnego stylu TScrollbar: {e}")
        finally:
            self.destroy() # Zamknij okno edytora
from .shared_imports import (
    tk,
    ttk,
    filedialog,
    messagebox,
    simpledialog,
    logging,
    os,
    shutil,
    re,
    datetime,
    Image,
    ImageTk,
)
from .constants import IMAGES_FOLDER, resampling, THEMES
from .utils import save_config, load_photoimage_from_path


