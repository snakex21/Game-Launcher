"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

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
