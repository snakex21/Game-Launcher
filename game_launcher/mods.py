class ExtendedModManager:
    def __init__(self, parent_launcher, root):
        self.launcher = parent_launcher
        self.root = root
        self.last_mod_locations = {}
        self.mods_data = self.launcher.config.setdefault("mods_data", {})

        # Główna ramka - zajmuje całą dostępną przestrzeń
        self.frame = ttk.Frame(self.root)
        self.frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)  # Główna zawartość będzie się rozciągać

        # Nagłówek - wyśrodkowany
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=10)
        header_frame.columnconfigure(0, weight=1)
        
        ttk.Label(
            header_frame, 
            text="Rozbudowany Menedżer Modów", 
            font=("Helvetica", 16, "bold")
        ).grid(row=0, column=0)  # Wyśrodkowany dzięki weight=1 w header_frame

        # Główna zawartość - teraz z lepszym wykorzystaniem przestrzeni
        content_frame = ttk.Frame(self.frame)
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(1, weight=3)  # Więcej miejsca dla tabeli modów
        content_frame.columnconfigure(0, weight=1)  # Mniej dla panelu bocznego
        content_frame.rowconfigure(0, weight=1)     # Rozciąganie w pionie

        # Lewy panel - wybór gry i profilu (teraz węższy)
        left_panel = ttk.Frame(content_frame, padding=(10, 5))
        left_panel.grid(row=0, column=0, sticky="nswe", padx=5, pady=5)
        left_panel.columnconfigure(0, weight=1)

        ttk.Label(left_panel, text="Wybierz grę:").pack(pady=5, anchor="w")
        self.game_var = tk.StringVar(value="Wybierz grę")
        games = list(self.launcher.games.keys())
        self.game_menu = ttk.OptionMenu(left_panel, self.game_var, self.game_var.get(), *games, command=self.on_game_change)
        self.game_menu.pack(pady=5, fill="x")

        ttk.Label(left_panel, text="Profil:").pack(pady=5, anchor="w")
        self.profile_var = tk.StringVar(value="default")
        self.profile_menu = ttk.OptionMenu(left_panel, self.profile_var, self.profile_var.get(), "default")
        self.profile_menu.pack(pady=5, fill="x")

        ttk.Button(left_panel, text="Utwórz Profil", command=self.create_profile).pack(pady=5, fill="x")
        ttk.Button(left_panel, text="Usuń Profil", command=self.delete_profile).pack(pady=5, fill="x")

        # Prawy panel - tabela modów (teraz większa)
        right_panel = ttk.Frame(content_frame)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)  # Tabela zajmuje całą dostępną przestrzeń

        # Tabela modów - większa i z lepszym rozciąganiem
        columns = ("Nazwa", "Aktywny", "Priorytet")
        self.mods_tree = ttk.Treeview(
            right_panel, 
            columns=columns, 
            show="headings", 
            selectmode="browse",
            height=15  # Większa domyślna wysokość
        )
        for col in columns:
            self.mods_tree.heading(col, text=col)
            self.mods_tree.column(col, stretch=True)  # Wszystkie kolumny się rozciągają

        self.mods_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.mods_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.mods_tree.configure(yscrollcommand=scrollbar.set)

        # Panel przycisków - teraz bardziej kompaktowy
        buttons_frame = ttk.Frame(content_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        buttons_frame.columnconfigure((0,1,2,3,4,5), weight=1)  # Równe rozłożenie przycisków

        buttons = [
            ("Zainstaluj Mod", self.install_mod),
            ("Zainstaluj z ZIP", self.install_mod_zip_flow),
            ("Dezaktywuj Mod", self.deactivate_mod),
            ("Odinstaluj Mod", self.uninstall_mod),
            ("Zwiększ Priorytet", self.increase_priority),
            ("Zmniejsz Priorytet", self.decrease_priority)
        ]

        for idx, (text, command) in enumerate(buttons):
            ttk.Button(
                buttons_frame, 
                text=text, 
                command=command
            ).grid(row=0, column=idx, sticky="ew", padx=2)

        # Przycisk Odśwież na dole osobno
        refresh_btn = ttk.Button(content_frame, text="Odśwież", command=self.load_current_game_profile)
        refresh_btn.grid(row=3, column=0, columnspan=2, pady=5, sticky="e")

        # Inicjalizacja
        self.last_mod_locations = self.launcher.config.setdefault("last_mod_locations", {})
        self.load_current_game_profile()

    def select_game_in_manager(self, game_name_to_select):
        """Programowo wybiera grę w menedżerze modów (Ulepszona wersja)."""
        logging.debug(f"Próba programowego wybrania gry: '{game_name_to_select}'")
        if not hasattr(self, 'game_menu') or not self.game_menu.winfo_exists():
             logging.warning("OptionMenu gier nie istnieje w menedżerze modów.")
             return

        # --- ULEPSZONY SPOSÓB POBIERANIA OPCJI ---
        menu = self.game_menu["menu"]
        options = []
        try:
            # Iteruj po indeksach menu, aby uzyskać etykiety
            last_index = menu.index("end")
            if last_index is not None: # Sprawdź, czy menu nie jest puste
                for i in range(last_index + 1):
                    try:
                         label = menu.entrycget(i, "label")
                         if label: # Dodaj tylko niepuste etykiety
                              options.append(label)
                    except tk.TclError: # Ignoruj błędy przy pobieraniu np. separatorów
                         continue
            # Usuń domyślny element "Wybierz grę", jeśli tam jest
            if "Wybierz grę" in options:
                 options.remove("Wybierz grę")

        except tk.TclError:
            logging.error("Błąd TclError podczas pobierania opcji menu w select_game_in_manager.")
            options = [] # Użyj pustej listy jako fallback
        except Exception as e:
             logging.exception(f"Nieoczekiwany błąd podczas pobierania opcji menu: {e}")
             options = []
        # --- KONIEC ULEPSZONEGO POBIERANIA ---

        logging.debug(f"Dostępne gry w dropdown menedżera modów: {options}")

        game_found = False
        if game_name_to_select in options:
            try:
                # Ustaw wartość StringVar - to powinno zaktualizować OptionMenu
                self.game_var.set(game_name_to_select)
                # Ręcznie wywołaj funkcję on_game_change, aby załadować profile i mody
                self.on_game_change(game_name_to_select)
                game_found = True
                logging.info(f"Programowo wybrano grę '{game_name_to_select}' w menedżerze modów.")
            except Exception as e:
                 logging.error(f"Błąd podczas ustawiania game_var lub wywoływania on_game_change dla '{game_name_to_select}': {e}")
        else:
             logging.warning(f"Nie można znaleźć gry '{game_name_to_select}' wśród opcji dropdown menedżera modów: {options}")
             # Opcjonalnie: Ustaw na "Wybierz grę", jeśli gra nie została znaleziona?
             # self.game_var.set("Wybierz grę")
             # self.on_game_change("Wybierz grę")


        if not game_found:
             # Logika, która była wcześniej (już niepotrzebna, jeśli powyższe działa)
             # available_games = self.game_menu['menu'].winfo_children()
             # for menu_item in available_games:
             #     if menu_item.cget('label') == game_name_to_select:
             #         # ... (stary kod) ...
             pass # Usuwamy starą logikę

    def deactivate_mod(self):
        """Dezaktywuje wybrany mod - przywraca oryginalne pliki"""
        game = self.game_var.get()
        profile = self.profile_var.get()
        selection = self.mods_tree.selection()
        if not selection:
            messagebox.showwarning("Błąd", "Nie wybrano żadnego moda do dezaktywacji.")
            return
        
        mod_name = self.mods_tree.item(selection, "values")[0]
        profile_data = self.mods_data[game]["profiles"][profile]
        mod_info = profile_data["mods"].get(mod_name)
        
        if not mod_info:
            return
        
        # Sprawdź czy mod jest aktywny
        if not mod_info.get("active", False):
            messagebox.showinfo("Informacja", f"Mod '{mod_name}' jest już dezaktywowany.")
            return

        # Pobierz ścieżkę do folderu gry
        exe_path = self.launcher.games[game].get("exe_path", "")
        game_folder = os.path.dirname(exe_path)
        
        # Przywróć pliki z backupu
        backup_folder = mod_info.get("backup_folder")
        if not backup_folder or not os.path.isdir(backup_folder):
            messagebox.showerror("Błąd", f"Nie znaleziono backupu dla moda '{mod_name}'.")
            return

        try:
            for rel_path in mod_info.get("files_changed", []):
                backed_file = os.path.join(backup_folder, rel_path)
                original_in_game = os.path.join(game_folder, rel_path)
                
                if os.path.exists(backed_file):
                    try:
                        shutil.copy2(backed_file, original_in_game)
                    except Exception as e:
                        logging.error(f"Nie udało się przywrócić {original_in_game}: {e}")

            # Oznacz mod jako nieaktywny
            mod_info["active"] = False
            self.save_mods_data()
            self.load_current_game_profile()
            messagebox.showinfo("Sukces", f"Mod '{mod_name}' został dezaktywowany.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się dezaktywować moda: {e}")

    def on_game_change(self, selected_game):
        """Gdy użytkownik zmienia grę, załaduj listę dostępnych profili"""
        if selected_game == "Wybierz grę":
            return
        game_data = self.mods_data.setdefault(selected_game, {"profiles": {}})
        profiles = list(game_data["profiles"].keys())
        if "default" not in profiles:
            # Inicjuj standardowy profil
            game_data["profiles"]["default"] = {
                "mods": {},
                "load_order": []
            }
            self.save_mods_data()
            profiles.append("default")

        # Odtwórz menu profili
        menu = self.profile_menu['menu']
        menu.delete(0, "end")
        for p in profiles:
            menu.add_command(label=p, command=lambda val=p: self.profile_var.set(val))

        # Ustaw jako default, jeśli istnieje, w innym razie pierwszy
        self.profile_var.set("default")
        self.load_current_game_profile()

    def load_current_game_profile(self):
        """Ładuje listę modów i priorytety dla wybranego profilu"""
        game = self.game_var.get()
        if game == "Wybierz grę":
            self.clear_tree()
            return
        
        profile = self.profile_var.get()
        game_data = self.mods_data.setdefault(game, {"profiles": {}})
        profile_data = game_data["profiles"].get(profile, {"mods": {}, "load_order": []})

        self.clear_tree()

        # Załaduj mody w kolejności load_order
        load_order = profile_data["load_order"]
        for mod_name in load_order:
            mod_info = profile_data["mods"].get(mod_name, {})
            self.mods_tree.insert("", "end", values=(
                mod_name,
                "Tak" if mod_info.get("active", False) else "Nie",
                mod_info.get("priority", 0)
            ))

    def clear_tree(self):
        for item in self.mods_tree.get_children():
            self.mods_tree.delete(item)

    def create_profile(self):
        """Tworzy nowy profil dla aktualnie wybranej gry"""
        game = self.game_var.get()
        if game == "Wybierz grę":
            messagebox.showwarning("Błąd", "Najpierw wybierz grę.")
            return

        profile_name = tk.simpledialog.askstring("Nazwa profilu", "Podaj nazwę nowego profilu:")
        if not profile_name:
            return
        
        game_data = self.mods_data.setdefault(game, {"profiles": {}})
        if profile_name in game_data["profiles"]:
            messagebox.showwarning("Błąd", f"Profil '{profile_name}' już istnieje.")
            return

        game_data["profiles"][profile_name] = {
            "mods": {},
            "load_order": []
        }
        self.save_mods_data()
        messagebox.showinfo("Sukces", f"Profil '{profile_name}' został utworzony.")
        self.on_game_change(game)

    def delete_profile(self):
        """Usuwa wybrany profil"""
        game = self.game_var.get()
        profile = self.profile_var.get()
        if game == "Wybierz grę":
            return
        if profile == "default":
            messagebox.showwarning("Błąd", "Nie można usunąć profilu 'default'.")
            return

        game_data = self.mods_data.setdefault(game, {"profiles": {}})
        if profile not in game_data["profiles"]:
            return

        confirm = messagebox.askyesno("Potwierdzenie", f"Czy na pewno chcesz usunąć profil '{profile}'?")
        if confirm:
            del game_data["profiles"][profile]
            self.save_mods_data()
            messagebox.showinfo("Sukces", f"Profil '{profile}' został usunięty.")
            self.profile_var.set("default")
            self.load_current_game_profile()

    def install_mod_zip_flow(self):
        """Pozwala użytkownikowi wybrać plik ZIP i instaluje go do folderu modów"""
        game = self.game_var.get()
        if game == "Wybierz grę":
            messagebox.showwarning("Błąd", "Najpierw wybierz grę z listy po lewej.")
            return

        # Zapytaj o plik ZIP
        zip_file = filedialog.askopenfilename(
            title="Wybierz plik ZIP z modem",
            filetypes=[("Archiwa ZIP", "*.zip")]
        )
        if not zip_file:
            return  # Anulowano

        # Pobierz nazwę moda z nazwy pliku ZIP (bez rozszerzenia)
        mod_name = os.path.splitext(os.path.basename(zip_file))[0]
        
        # Zapytaj użytkownika o potwierdzenie nazwy moda
        mod_name = simpledialog.askstring(
            "Nazwa Moda", 
            f"Podaj nazwę moda (domyślnie '{mod_name}'):", 
            initialvalue=mod_name
        )
        if not mod_name:
            return  # Anulowano

        # Pobierz ostatnie lokalizacje dla tej gry
        last_locations = self.last_mod_locations.get(game, [])
        
        # Okno wyboru lokalizacji instalacji
        location_window = tk.Toplevel(self.root)
        location_window.title("Wybierz lokalizację instalacji moda")
        location_window.grab_set()
        
        ttk.Label(location_window, text="Wybierz gdzie zainstalować mod:").pack(pady=10)
        
        # Ramka na przyciski ostatnich lokalizacji
        last_locations_frame = ttk.Frame(location_window)
        last_locations_frame.pack(pady=5)
        
        # Przyciski dla ostatnich lokalizacji
        for location in last_locations:
            btn = ttk.Button(last_locations_frame, text=location, 
                            command=lambda loc=location: self.select_location(location_window, loc, zip_file, mod_name))
            btn.pack(side="top", fill="x", padx=5, pady=2)
        
        # Przycisk wyboru nowej lokalizacji
        new_location_btn = ttk.Button(location_window, text="Wybierz inną lokalizację...",
                                    command=lambda: self.select_new_location(location_window, zip_file, game, mod_name))
        new_location_btn.pack(pady=10)
        
    def select_location(self, window, location, zip_file, mod_name):
        """Obsługuje wybór istniejącej lokalizacji"""
        window.destroy()
        self.install_mod_from_zip(zip_file, location, mod_name)
        
    def select_new_location(self, window, zip_file, game, mod_name):
        """Pozwala wybrać nową lokalizację"""
        location = filedialog.askdirectory(title="Wybierz folder instalacji modów")
        if location:
            window.destroy()
            # Dodaj nową lokalizację do historii
            if game not in self.last_mod_locations:
                self.last_mod_locations[game] = []
            if location not in self.last_mod_locations[game]:
                self.last_mod_locations[game].insert(0, location)
                # Ogranicz do np. 5 ostatnich lokalizacji
                self.last_mod_locations[game] = self.last_mod_locations[game][:5]
                self.launcher.config["last_mod_locations"] = self.last_mod_locations
                save_config(self.launcher.config)
            self.install_mod_from_zip(zip_file, location, mod_name)

    def install_mod_from_zip(self, zip_path, mods_folder, mod_name):
        """Rozpakowuje pliki z archiwum ZIP do folderu 'mods_folder' i dodaje mod do listy"""
        if not os.path.exists(mods_folder):
            os.makedirs(mods_folder, exist_ok=True)

        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Rozpakuj pliki
            zf.extractall(mods_folder)

        # Dodaj mod do listy w aktualnym profilu
        game = self.game_var.get()
        profile = self.profile_var.get()
        
        game_data = self.mods_data.setdefault(game, {"profiles": {}})
        profile_data = game_data["profiles"].setdefault(profile, {"mods": {}, "load_order": []})
        
        # Zapytaj czy mod ma być od razu aktywny
        make_active = messagebox.askyesno("Aktywować od razu?", "Czy chcesz od razu aktywować ten mod?")
        
        # Dodaj mod do profilu
        profile_data["mods"][mod_name] = {
            "active": make_active,
            "priority": 0,
            "location": mods_folder,
            "zip_file": os.path.basename(zip_path)
        }
        
        if mod_name not in profile_data["load_order"]:
            profile_data["load_order"].append(mod_name)
        
        self.save_mods_data()

        # --- NOWE: Wywołaj sprawdzenie osiągnięć ---
        if hasattr(self.launcher, 'check_and_unlock_achievements'):
            self.launcher.check_and_unlock_achievements()
        # --- KONIEC NOWEGO ---

        self.load_current_game_profile()  # Odśwież widok listy modów
        messagebox.showinfo("Sukces", f"Mod '{mod_name}' został zainstalowany (aktywny: {make_active}).")

    def install_mod(self):
        """Instaluje nowy mod do wybranej gry i aktywnego profilu"""
        game = self.game_var.get()
        if game == "Wybierz grę":
            messagebox.showwarning("Błąd", "Najpierw wybierz grę.")
            return
        profile = self.profile_var.get()

        # Pobierz ostatnie lokalizacje dla tej gry
        last_locations = self.last_mod_locations.get(game, [])
        
        # Okno wyboru lokalizacji moda
        location_window = tk.Toplevel(self.root)
        location_window.title("Wybierz lokalizację moda")
        location_window.grab_set()
        
        ttk.Label(location_window, text="Wybierz folder z modem:").pack(pady=10)
        
        # Ramka na przyciski ostatnich lokalizacji
        last_locations_frame = ttk.Frame(location_window)
        last_locations_frame.pack(pady=5)
        
        # Przyciski dla ostatnich lokalizacji
        for location in last_locations:
            btn = ttk.Button(last_locations_frame, text=location, 
                            command=lambda loc=location: self.select_mod_location(location_window, loc))
            btn.pack(side="top", fill="x", padx=5, pady=2)
        
        # Przycisk wyboru nowej lokalizacji
        new_location_btn = ttk.Button(location_window, text="Wybierz inną lokalizację...",
                                    command=lambda: self.select_new_mod_location(location_window, game))
        new_location_btn.pack(pady=10)
        
    def select_mod_location(self, window, location):
        """Obsługuje wybór istniejącej lokalizacji moda"""
        window.destroy()
        self.process_mod_installation(location)
        
    def select_new_mod_location(self, window, game):
        """Pozwala wybrać nową lokalizację moda"""
        location = filedialog.askdirectory(title="Wybierz folder z modem")
        if location:
            window.destroy()
            # Dodaj nową lokalizację do historii
            if game not in self.last_mod_locations:
                self.last_mod_locations[game] = []
            if location not in self.last_mod_locations[game]:
                self.last_mod_locations[game].insert(0, location)
                # Ogranicz do np. 5 ostatnich lokalizacji
                self.last_mod_locations[game] = self.last_mod_locations[game][:5]
                self.launcher.config["last_mod_locations"] = self.last_mod_locations
                save_config(self.launcher.config)
            self.process_mod_installation(location)

    def process_mod_installation(self, mod_dir):
        """Przetwarza instalację moda z wybranego folderu"""
        game = self.game_var.get()
        profile = self.profile_var.get()

        mod_name = os.path.basename(mod_dir)
        answer = tk.simpledialog.askstring("Nazwa Moda", f"Podaj nazwę moda (domyślnie '{mod_name}'):", initialvalue=mod_name)
        if not answer:
            return
        mod_name = answer.strip()

        # Ścieżka do folderu gry
        exe_path = self.launcher.games[game].get("exe_path", "")
        game_folder = os.path.dirname(exe_path)
        if not os.path.isdir(game_folder):
            messagebox.showerror("Błąd", "Folder gry nie istnieje - sprawdź ścieżkę exe_path.")
            return

        # Przygotuj strukturę w configu
        game_data = self.mods_data.setdefault(game, {"profiles": {}})
        profile_data = game_data["profiles"].setdefault(profile, {"mods": {}, "load_order": []})
        if mod_name in profile_data["mods"]:
            messagebox.showwarning("Uwaga", f"Mod '{mod_name}' jest już zainstalowany w tym profilu.")
            return

        # Zapytaj czy mod ma być od razu aktywny
        make_active = messagebox.askyesno("Aktywować od razu?", "Czy chcesz od razu aktywować ten mod?")

        # Tworzymy listę plików do skopiowania
        files_to_copy = []
        for root, dirs, filenames in os.walk(mod_dir):
            for f in filenames:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, mod_dir)
                destination_path = os.path.join(game_folder, rel_path)
                files_to_copy.append((full_path, destination_path))

        # Tworzymy backup oryginalnych plików
        backup_folder = os.path.join(game_folder, f"_backup_{mod_name}_{int(time.time())}")
        os.makedirs(backup_folder, exist_ok=True)

        files_changed = []
        for src, dst in files_to_copy:
            if os.path.exists(dst):
                # zrób backup
                rel_in_game = os.path.relpath(dst, game_folder)
                backup_dst = os.path.join(backup_folder, rel_in_game)
                os.makedirs(os.path.dirname(backup_dst), exist_ok=True)
                shutil.copy2(dst, backup_dst)
                files_changed.append(rel_in_game)
        
        # Skopiuj pliki moda do gry
        for src, dst in files_to_copy:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

        # Zapisz informacje w configu
        profile_data["mods"][mod_name] = {
            "active": make_active,
            "priority": 0,
            "files_changed": files_changed,
            "backup_folder": backup_folder,
            "location": mod_dir
        }
        if mod_name not in profile_data["load_order"]:
            profile_data["load_order"].append(mod_name)

        self.save_mods_data()

        # --- NOWE: Wywołaj sprawdzenie osiągnięć ---
        if hasattr(self.launcher, 'check_and_unlock_achievements'):
            self.launcher.check_and_unlock_achievements()
        # --- KONIEC NOWEGO ---

        self.load_current_game_profile()  # Odśwież widok listy modów
        messagebox.showinfo("Sukces", f"Mod '{mod_name}' został zainstalowany (aktywny: {make_active}).")

    def uninstall_mod(self):
        """
        Odinstalowuje mod:
          1. Przywraca oryginalne pliki z backupu
          2. Usuwa folder backupu
          3. Usuwa wpis moda z profilu
        """
        game = self.game_var.get()
        profile = self.profile_var.get()
        selection = self.mods_tree.selection()
        if not selection:
            messagebox.showwarning("Błąd", "Nie wybrano żadnego moda do odinstalowania.")
            return
        
        mod_name = self.mods_tree.item(selection, "values")[0]
        profile_data = self.mods_data[game]["profiles"][profile]
        mod_info = profile_data["mods"].get(mod_name)
        
        if not mod_info:
            return

        confirm = messagebox.askyesno("Potwierdzenie", 
                                    f"Czy na pewno chcesz odinstalować mod '{mod_name}'?\n"
                                    "Spowoduje to trwałe usunięcie moda z systemu.")
        if not confirm:
            return

        # Pobierz ścieżkę do folderu gry
        exe_path = self.launcher.games[game].get("exe_path", "")
        game_folder = os.path.dirname(exe_path)
        
        # 1. Przywróć pliki z backupu
        backup_folder = mod_info.get("backup_folder")
        if backup_folder and os.path.isdir(backup_folder):
            try:
                for rel_path in mod_info.get("files_changed", []):
                    backed_file = os.path.join(backup_folder, rel_path)
                    original_in_game = os.path.join(game_folder, rel_path)
                    
                    if os.path.exists(backed_file):
                        try:
                            shutil.copy2(backed_file, original_in_game)
                        except Exception as e:
                            logging.error(f"Nie udało się przywrócić {original_in_game}: {e}")
                
                # 2. Usuń folder backupu
                shutil.rmtree(backup_folder)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się przywrócić oryginalnych plików: {e}")
                return

        # 3. Usuń wpis moda z profilu
        if mod_name in profile_data["load_order"]:
            profile_data["load_order"].remove(mod_name)
        del profile_data["mods"][mod_name]

        self.save_mods_data()
        self.load_current_game_profile()
        messagebox.showinfo("Sukces", f"Mod '{mod_name}' został odinstalowany.")

    def increase_priority(self):
        """Zwiększ priorytet wybranego moda"""
        selection = self.mods_tree.selection()
        if not selection:
            return
        mod_name = self.mods_tree.item(selection, "values")[0]
        game = self.game_var.get()
        profile = self.profile_var.get()
        profile_data = self.mods_data[game]["profiles"][profile]
        mod_info = profile_data["mods"][mod_name]

        mod_info["priority"] += 1
        self.reorder_load_list(game, profile)
        self.save_mods_data()
        self.load_current_game_profile()

    def decrease_priority(self):
        """Zmniejsz priorytet wybranego moda"""
        selection = self.mods_tree.selection()
        if not selection:
            return
        mod_name = self.mods_tree.item(selection, "values")[0]
        game = self.game_var.get()
        profile = self.profile_var.get()
        profile_data = self.mods_data[game]["profiles"][profile]
        mod_info = profile_data["mods"][mod_name]

        mod_info["priority"] -= 1
        self.reorder_load_list(game, profile)
        self.save_mods_data()
        self.load_current_game_profile()

    def reorder_load_list(self, game, profile):
        """Sortuje 'load_order' na podstawie priorytetów modów"""
        profile_data = self.mods_data[game]["profiles"][profile]
        # Sortuj mod_name w kolejności: priority malejąco
        sorted_mods = sorted(profile_data["mods"].items(), key=lambda kv: kv[1]["priority"], reverse=True)
        new_load_order = [m[0] for m in sorted_mods]
        profile_data["load_order"] = new_load_order

    def save_mods_data(self):
        """Zapisuje `self.mods_data` do configu launchera"""
        self.launcher.config["mods_data"] = self.mods_data
        save_config(self.launcher.config)
from .shared_imports import tk, ttk, messagebox, filedialog, logging, os, time, shutil
from .utils import save_config


