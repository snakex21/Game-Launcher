class MusicPlayerPage:
    def __init__(self, parent_frame, launcher_instance):
            self.parent_frame = parent_frame
            self.launcher = launcher_instance
            self.config = self.launcher.config
            self.local_settings = self.launcher.local_settings
            
            # Cache dla okładek (możemy to później zoptymalizować, jeśli będzie potrzeba)
            self._current_focus_cover_id = None 
            self._cover_cache: dict[str, ImageTk.PhotoImage] = {} 
            self._focus_cover_cache: dict[str, ImageTk.PhotoImage] = {}
            self._focus_cover_loading_path: str | None = None
            self._bottom_bar_thumbnail_cache: dict[str, ImageTk.PhotoImage] = {} # Cache dla miniaturek na dolnym pasku
            
            try:
                pygame.mixer.init()
                logging.info("Pygame mixer zainicjalizowany.")
            except pygame.error as e:
                logging.error(f"Nie można zainicjalizować pygame.mixer: {e}")
                messagebox.showerror("Błąd Odtwarzacza", f"Nie można uruchomić modułu audio (pygame.mixer):\n{e}\nOdtwarzacz muzyki może nie działać.", parent=self.parent_frame)

            # --- START SEKCJI INICJALIZACJI DANYCH PLAYLIST ---
            self.named_playlists = self.local_settings.get("named_music_playlists", {})
            
            # --- NOWE ZMIANY: Tworzenie predefiniowanych playlist ---
            PREDEFINED_MAIN_QUEUE = "Główna Kolejka"
            PREDEFINED_INTERNAL_MUSIC = "Muzyka Wewnętrzna"
            self.permanent_playlists = {PREDEFINED_MAIN_QUEUE, PREDEFINED_INTERNAL_MUSIC} # Zbiór nazw playlist, których nie można usunąć

            # Upewnij się, że predefiniowane playlisty istnieją
            if PREDEFINED_MAIN_QUEUE not in self.named_playlists:
                self.named_playlists[PREDEFINED_MAIN_QUEUE] = []
            if PREDEFINED_INTERNAL_MUSIC not in self.named_playlists:
                self.named_playlists[PREDEFINED_INTERNAL_MUSIC] = []
            # --- KONIEC NOWYCH ZMIAN ---

            self.active_playlist_name = self.local_settings.get("active_music_playlist_name")
            
            # Jeśli aktywna playlista nie jest ustawiona lub nie istnieje, ustaw na Główną Kolejkę
            if not self.active_playlist_name or self.active_playlist_name not in self.named_playlists:
                self.active_playlist_name = PREDEFINED_MAIN_QUEUE
            
            # --- Koniec zmian w sekcji inicjalizacji ---

            self.playlist: list[dict] = [] 
            self.original_playlist_order: list[dict] = []
            
            self.current_track_index = self.local_settings.get("current_track_in_active_playlist_index", -1)
            # --- KONIEC SEKCJI INICJALIZACJI DANYCH PLAYLIST ---
            
            self.is_playing = False
            self.is_paused = False
            self._seeking = False 
            self.last_music_folder = self.local_settings.get("last_music_folder", os.path.expanduser("~"))
            self._start_time = 0.0 
            self._pause_acc = 0.0
            self._current_track_duration_sec = 0.0

            self._play_pause_debounce_timer = None
            self._debounce_delay_ms = 200 
            self._search_update_timer = None
            self._search_debounce_ms = 350

            self.repeat_mode = self.local_settings.get("music_repeat_mode", "none")
            self.shuffle_mode = self.local_settings.get("music_shuffle_mode", False)
            self.autoplay = self.local_settings.get("music_autoplay_enabled", True)
            self.favorite_tracks = set(self.local_settings.get("music_favorite_tracks", []))
            
            self.currently_displayed_paths: list[dict] = []

            self.music_library_view_mode = tk.StringVar(value="list") 
            self.is_playlist_view_active = tk.BooleanVar(value=True)

            self._build_ui() 
            self._update_available_playlists_ui() # To ustawi self.active_playlist_var
            self._load_player_settings() # To ustawi głośność, folder
            self._load_active_playlist() # To załaduje self.playlist i self.original_playlist_order
            self._update_playlist_display() # To wypełni listbox i currently_displayed_paths

            # --- Logika ustawiania początkowego zaznaczenia ---
            if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                track_entry_to_select = self.playlist[self.current_track_index]
                if track_entry_to_select in self.currently_displayed_paths:
                    try:
                        display_idx_to_select = self.currently_displayed_paths.index(track_entry_to_select)
                        if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
                            self.playlist_listbox.selection_clear(0, tk.END)
                            self.playlist_listbox.selection_set(display_idx_to_select)
                            self.playlist_listbox.activate(display_idx_to_select)
                            self.playlist_listbox.see(display_idx_to_select)
                    except (tk.TclError, ValueError) as e:
                        logging.warning(f"Błąd przy ustawianiu zaznaczenia w __init__ ({self.current_track_index}): {e}")
                        self.current_track_index = -1 # Resetuj, jeśli coś poszło nie tak
                else: 
                    logging.debug(f"Aktualny utwór '{track_entry_to_select.get('path')}' nie jest na liście wyświetlanych, resetuję current_track_index.")
                    self.current_track_index = -1
                self._update_now_playing_label() 
            else: 
                if self.playlist: # Jeśli nie ma zapisanego indeksu, ale playlista nie jest pusta
                    self.current_track_index = 0
                    if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists() and self.currently_displayed_paths:
                        # Upewnij się, że próbujemy zaznaczyć pierwszy element *widoczny*
                        entry_to_select_at_zero = self.currently_displayed_paths[0]
                        if entry_to_select_at_zero in self.playlist : # Dodatkowe sprawdzenie spójności
                            try:
                                self.playlist_listbox.selection_clear(0, tk.END)
                                self.playlist_listbox.selection_set(0) # Zaznacz pierwszy widoczny
                                self.playlist_listbox.activate(0)
                            except tk.TclError: pass # Ignoruj błąd, jeśli listbox jest pusty
                    self._update_now_playing_label()
                else: # Pusta playlista, brak indeksu
                    self.current_track_index = -1
                    self._update_now_playing_label(track_name_override="Nic nie gra")
            
            # Ustawienie domyślnego widoku po załadowaniu playlisty
            if self.playlist:
                self.music_library_view_mode.set("list")
                self.is_playlist_view_active.set(True)
            else:
                self.music_library_view_mode.set("tiles")
                self.is_playlist_view_active.set(False)
            
            self._apply_music_content_view() # Zastosuj widok Lista/Kafelki
            
            # Aktualizacja przycisków (po zbudowaniu UI i załadowaniu stanu)
            self._update_autoplay_button_text()
            self._update_repeat_button_text()
            self._update_shuffle_button_text()
            self._update_fav_button_text()
            self._update_music_view_mode_button_text()
            # --- NOWE ZMIANY ---
            self._update_delete_playlist_button_state() # Wywołaj przy inicjalizacji
            # --- KONIEC NOWYCH ZMIAN ---
            self.apply_theme_colors() # Zastosuj kolory motywu
            
            # Uruchom cykliczną aktualizację overlay'a, jeśli launcher istnieje i ma tę metodę
            if hasattr(self.launcher, '_update_overlay_regularly'):
                self.launcher.root.after(100, self.launcher._update_overlay_regularly)

    def _update_autoplay_button_text(self):
        if hasattr(self, 'autoplay_button') and self.autoplay_button: # Sprawdź, czy przycisk istnieje
            text = "Auto-play: Wł." if self.autoplay else "Auto-play: Wył."
            self.autoplay_button.config(text=text)

    # --- NOWA METODA ---
    def _update_playlist_display(self):
        """
        Odświeża zawartość Listboxa playlisty, uwzględniając filtr ulubionych ORAZ wyszukiwanie.
        Operuje na liście słowników.
        """
        if not hasattr(self, 'playlist_listbox') or not self.playlist_listbox.winfo_exists():
            logging.warning("_update_playlist_display: Listbox nie istnieje.")
            return

        self.playlist_listbox.delete(0, tk.END)
        self.currently_displayed_paths = [] # Lista słowników aktualnie wyświetlanych

        # `self.playlist` to teraz lista słowników {'path': ..., 'focus_cover_path': ...}
        base_tracks_to_filter = list(self.playlist) 

        if self.show_favorites_only_var.get():
            # --- ZMIANA: Filtruj listę słowników po kluczu 'path' ---
            base_tracks_to_filter = [track_entry for track_entry in base_tracks_to_filter if track_entry.get('path') in self.favorite_tracks]
            # --- KONIEC ZMIANY ---

        search_term = self.search_music_var.get().lower().strip()
        if search_term:
            filtered_tracks_for_display = []
            for track_entry in base_tracks_to_filter:
                # --- ZMIANA: Przekaż cały słownik do _get_display_name_for_track ---
                display_name_for_search = self._get_display_name_for_track(track_entry).replace("♥ ", "").lower()
                # --- KONIEC ZMIANY ---
                if search_term in display_name_for_search:
                    filtered_tracks_for_display.append(track_entry)
        else:
            filtered_tracks_for_display = base_tracks_to_filter
        
        for track_entry in filtered_tracks_for_display:
            # --- ZMIANA: Przekaż cały słownik ---
            display_name_for_listbox = self._get_display_name_for_track(track_entry)
            # --- KONIEC ZMIANY ---
            self.playlist_listbox.insert(tk.END, display_name_for_listbox)
            self.currently_displayed_paths.append(track_entry)

        path_entry_to_highlight = None # Będzie słownikiem
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            path_entry_to_highlight = self.playlist[self.current_track_index]
        
        if path_entry_to_highlight and path_entry_to_highlight in self.currently_displayed_paths:
            try:
                new_view_index = self.currently_displayed_paths.index(path_entry_to_highlight)
                self.playlist_listbox.selection_clear(0, tk.END)
                self.playlist_listbox.selection_set(new_view_index)
                self.playlist_listbox.activate(new_view_index)
                self.playlist_listbox.see(new_view_index)
            except (ValueError, tk.TclError) as e:
                logging.warning(f"Nie udało się przywrócić zaznaczenia w _update_playlist_display: {e}")
        elif not self.currently_displayed_paths:
             self.playlist_listbox.selection_clear(0, tk.END)
        
        self._update_move_buttons_state()

    def _load_player_settings(self):
        initial_volume = self.local_settings.get("music_player_volume", 0.5)
        if hasattr(self, 'volume_scale'):
            self.volume_scale.set(initial_volume * 100)
            pygame.mixer.music.set_volume(initial_volume)
            # --- NOWE: Ustaw etykietę procentów ---
            if hasattr(self, 'volume_percent_label'):
                self.volume_percent_label.config(text=f"{int(initial_volume * 100)}%")
            # --- KONIEC NOWEGO ---
        # Wczytaj ostatnio używany folder (opcjonalnie)
        # self.last_music_folder = self.local_settings.get("last_music_folder", os.path.expanduser("~"))

    def _save_player_settings(self):
        """Zapisuje ustawienia odtwarzacza, w tym nową strukturę playlist."""
        if hasattr(self, 'volume_scale'):
            self.local_settings["music_player_volume"] = self.volume_scale.get() / 100
        if hasattr(self, 'last_music_folder'):
            self.local_settings["last_music_folder"] = self.last_music_folder

        # --- ZMIANA: Zapis named_playlists (powinna już być listą słowników) ---
        # Upewnij się, że wszystkie playlisty w named_playlists są listami słowników
        sanitized_named_playlists = {}
        for pl_name, pl_entries_raw in self.named_playlists.items():
            sanitized_entries = []
            for item in pl_entries_raw:
                if isinstance(item, str): # Konwersja na wszelki wypadek, jeśli coś się prześlizgnęło
                    sanitized_entries.append({'path': item, 'focus_cover_path': None})
                elif isinstance(item, dict) and 'path' in item:
                    item.setdefault('focus_cover_path', None)
                    sanitized_entries.append(item)
            sanitized_named_playlists[pl_name] = sanitized_entries
        self.local_settings["named_music_playlists"] = sanitized_named_playlists
        # --- KONIEC ZMIANY ---

        self.local_settings["active_music_playlist_name"] = self.active_playlist_name
        self.local_settings["current_track_in_active_playlist_index"] = self.current_track_index
        self.local_settings["music_repeat_mode"] = self.repeat_mode
        self.local_settings["music_shuffle_mode"] = self.shuffle_mode
        self.local_settings["music_autoplay_enabled"] = self.autoplay
        # Zapis ulubionych pozostaje bez zmian, bo favorite_tracks to set ścieżek
        self.local_settings["music_favorite_tracks"] = list(self.favorite_tracks)
        
        save_local_settings(self.local_settings)


    # --- NOWA METODA ---
    def _refresh_internal_music_playlist(self):
        """
        Skanuje folder INTERNAL_MUSIC_DIR i synchronizuje playlistę "Muzyka Wewnętrzna".
        Dodaje nowe pliki, usuwa wpisy dla plików, których już nie ma.
        Nie usuwa fizycznie plików, tylko wpisy z playlisty.
        """
        if self.active_playlist_name != "Muzyka Wewnętrzna":
            messagebox.showwarning("Nieaktywna Playlista", "Ta operacja dotyczy tylko playlisty 'Muzyka Wewnętrzna'.", parent=self.parent_frame)
            return

        if not os.path.isdir(INTERNAL_MUSIC_DIR):
            logging.warning(f"Folder wewnętrznej biblioteki '{INTERNAL_MUSIC_DIR}' nie istnieje. Nie można odświeżyć.")
            messagebox.showerror("Błąd Folderu", f"Folder biblioteki wewnętrznej nie istnieje:\n{INTERNAL_MUSIC_DIR}", parent=self.parent_frame)
            self.named_playlists["Muzyka Wewnętrzna"] = [] # Wyczyść, jeśli folder zniknął
            self._load_active_playlist()
            self._update_playlist_display()
            self._save_player_settings()
            return

        logging.info(f"Rozpoczynanie odświeżania playlisty 'Muzyka Wewnętrzna' z folderu: {INTERNAL_MUSIC_DIR}")

        # Pokaż okno postępu
        scan_operation_title = "Odświeżanie playlisty 'Muzyka Wewnętrzna'"
        self.launcher.show_progress_window(scan_operation_title)
        if not (hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists()):
            return
        self.launcher.progress_bar['value'] = 0
        self.launcher.progress_bar['mode'] = 'indeterminate' # Najpierw indeterminate
        self.launcher.progress_label.config(text="Skanowanie folderu wewnętrznej biblioteki...")
        self.launcher.progress_window.update_idletasks()
        self.launcher.progress_bar.start(20)


        def refresh_thread_worker():
            current_files_in_internal_dir = set()
            supported_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
            try:
                for filename in os.listdir(INTERNAL_MUSIC_DIR):
                    if filename.lower().endswith(supported_extensions):
                        full_path = os.path.join(INTERNAL_MUSIC_DIR, filename)
                        if os.path.isfile(full_path): # Upewnij się, że to plik
                            current_files_in_internal_dir.add(os.path.abspath(full_path))
            except OSError as e:
                logging.error(f"Błąd odczytu folderu {INTERNAL_MUSIC_DIR} podczas odświeżania: {e}")
                self.launcher.root.after(0, lambda: (
                    self.launcher.progress_window.destroy() if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists() else None,
                    messagebox.showerror("Błąd Odczytu Folderu", f"Nie można odczytać zawartości folderu wewnętrznej biblioteki:\n{e}", parent=self.parent_frame)
                ))
                return

            # Pobierz aktualne wpisy z playlisty "Muzyka Wewnętrzna"
            # Musimy operować na kopii, aby móc modyfikować oryginał
            # Ważne: active_playlist_tracks_current będzie zawierać referencje do słowników!
            active_playlist_tracks_current = list(self.named_playlists.get("Muzyka Wewnętrzna", []))
            
            paths_on_playlist_before_refresh = {entry.get('path') for entry in active_playlist_tracks_current if entry.get('path')}
            
            newly_added_to_playlist_count = 0
            removed_from_playlist_count = 0
            
            # 1. Dodaj nowe pliki znalezione w folderze, których nie ma na playliście
            for file_path_in_dir in current_files_in_internal_dir:
                if file_path_in_dir not in paths_on_playlist_before_refresh:
                    new_entry = {
                        "path": file_path_in_dir,
                        "focus_cover_path": None,
                        "lastfm_cover_path": None,
                        "is_internal": True # Z definicji, bo skanujemy INTERNAL_MUSIC_DIR
                    }
                    active_playlist_tracks_current.append(new_entry)
                    newly_added_to_playlist_count += 1
                    logging.info(f"Odświeżanie: Dodano nowy plik do playlisty 'Muzyka Wewnętrzna': {os.path.basename(file_path_in_dir)}")

            # 2. Usuń z playlisty wpisy dla plików, których już nie ma w folderze
            # Ważne: iterujemy po kopii, a modyfikujemy listę, którą potem przypiszemy
            final_tracks_for_playlist = []
            for entry_on_playlist in active_playlist_tracks_current:
                path_on_playlist = entry_on_playlist.get('path')
                if path_on_playlist and os.path.abspath(path_on_playlist).startswith(os.path.abspath(INTERNAL_MUSIC_DIR)): # Dotyczy tylko plików, które miały być wewnętrzne
                    if os.path.abspath(path_on_playlist) in current_files_in_internal_dir:
                        final_tracks_for_playlist.append(entry_on_playlist) # Plik nadal istnieje, zachowaj wpis
                    else:
                        # Pliku nie ma w folderze, nie dodawaj go do final_tracks_for_playlist
                        removed_from_playlist_count += 1
                        logging.info(f"Odświeżanie: Usunięto wpis dla brakującego pliku z playlisty 'Muzyka Wewnętrzna': {os.path.basename(path_on_playlist)}")
                else: # Jeśli to był wpis zewnętrzny lub z błędną ścieżką, zachowaj go (chociaż nie powinien tu być)
                    final_tracks_for_playlist.append(entry_on_playlist)
            
            # Aktualizuj named_playlists
            self.named_playlists["Muzyka Wewnętrzna"] = final_tracks_for_playlist
            
            # Finalizuj w głównym wątku
            self.launcher.root.after(0, self._finalize_refresh_internal_playlist, newly_added_to_playlist_count, removed_from_playlist_count)

        threading.Thread(target=refresh_thread_worker, daemon=True).start()

    def _finalize_refresh_internal_playlist(self, added_count, removed_count):
        """Metoda pomocnicza do finalizacji odświeżania w głównym wątku."""
        if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
            self.launcher.progress_bar.stop()
            self.launcher.progress_window.destroy()

        was_playing_before_refresh = self.is_playing
        current_playing_path_before_refresh = None
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist): # Użyj self.playlist (stan przed przeładowaniem)
             current_playing_path_before_refresh = self.playlist[self.current_track_index].get('path')

        self._load_active_playlist() # To przeładuje self.playlist z zaktualizowanej named_playlists
        self._update_playlist_display() # Odśwież widok listbox/kafelków
        self._save_player_settings() # Zapisz zmiany w `named_playlists`

        # Spróbuj przywrócić stan odtwarzania/zaznaczenia
        if was_playing_before_refresh and current_playing_path_before_refresh:
            new_index_after_refresh = -1
            for i, entry in enumerate(self.playlist): # Użyj zaktualizowanej self.playlist
                if entry.get('path') == current_playing_path_before_refresh:
                    new_index_after_refresh = i
                    break
            
            if new_index_after_refresh != -1: # Znaleziono poprzednio grany utwór
                # Jeśli był odtwarzany, spróbuj go odtworzyć ponownie
                # Ale tylko jeśli ścieżka wciąż istnieje! (na wypadek gdyby plik zniknął, a potem został dodany z powrotem z inną nazwą)
                if os.path.exists(current_playing_path_before_refresh):
                     self._play_track(new_index_after_refresh)
                else: # Pliku już nie ma, zatrzymaj
                     self._stop_music()
                     self.current_track_index = 0 if self.playlist else -1 # Ustaw na pierwszy, jeśli playlista nie jest pusta
                     self._update_now_playing_label() # Zaktualizuj etykietę
            else: # Poprzednio grany utwór został usunięty z playlisty
                self._stop_music()
                self.current_track_index = 0 if self.playlist else -1
                self._update_now_playing_label()
        elif self.playlist: # Jeśli nic nie grało, a są utwory, ustaw na pierwszy
            self.current_track_index = 0
            self._update_now_playing_label()
            if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists() and self.currently_displayed_paths:
                entry_to_sel = self.playlist[0]
                if entry_to_sel in self.currently_displayed_paths:
                    try: self.playlist_listbox.selection_set(self.currently_displayed_paths.index(entry_to_sel))
                    except (ValueError, tk.TclError): pass
        else: # Pusta playlista
            self._stop_music() # Na wszelki wypadek
            self.current_track_index = -1
            self._update_now_playing_label()

        if self.music_library_view_mode.get() == "tiles": # Dodatkowe odświeżenie kafelków
            self._update_music_tiles_display()

        summary_message = "Odświeżanie playlisty 'Muzyka Wewnętrzna' zakończone.\n"
        if added_count > 0: summary_message += f"\nDodano nowych utworów: {added_count}"
        if removed_count > 0: summary_message += f"\nUsunięto wpisów dla brakujących plików: {removed_count}"
        if added_count == 0 and removed_count == 0: summary_message += "\nNie znaleziono zmian."
        
        messagebox.showinfo("Odświeżono Playlistę", summary_message, parent=self.parent_frame)
    # --- KONIEC NOWEJ METODY ---


    # --- NOWA METODA ---
    def _load_active_playlist(self):
        """
        Ładuje utwory (jako słowniki) z aktywnej nazwanej playlisty do self.playlist
        oraz do self.original_playlist_order.
        """
        if not self.active_playlist_name:
            if self.named_playlists:
                self.active_playlist_name = next(iter(self.named_playlists))
            else:
                self.active_playlist_name = "Główna Kolejka"
                # --- ZMIANA: Upewnij się, że tworzona playlista to lista słowników (pusta na start) ---
                self.named_playlists[self.active_playlist_name] = [] 
                # --- KONIEC ZMIANY ---
                self._save_player_settings()

        # --- ZMIANA: `tracks_for_active_playlist` to teraz lista słowników ---
        tracks_for_active_playlist_raw = self._get_tracks_for_active_playlist(
            external_only = self.active_playlist_name.endswith(".m3u")  # <- przykład detekcji
        )
        # Upewnij się, że każdy element jest słownikiem z wymaganymi kluczami
        tracks_for_active_playlist = []
        for item in tracks_for_active_playlist_raw:
            if isinstance(item, str): # Konwersja starych danych (tylko ścieżki)
                tracks_for_active_playlist.append({'path': item, 'focus_cover_path': None})
            elif isinstance(item, dict) and 'path' in item:
                item.setdefault('focus_cover_path', None) # Upewnij się, że klucz focus_cover_path istnieje
                tracks_for_active_playlist.append(item)
            else:
                logging.warning(f"Pominięto nieprawidłowy element w playliście '{self.active_playlist_name}': {item}")
        
        # Zaktualizuj named_playlists, jeśli dokonano konwersji
        if len(tracks_for_active_playlist) != len(tracks_for_active_playlist_raw) or \
           any(isinstance(item, str) for item in tracks_for_active_playlist_raw):
            self.named_playlists[self.active_playlist_name] = tracks_for_active_playlist
            # Nie zapisujemy tutaj od razu, _save_player_settings zrobi to w odpowiednim momencie
            
        self.original_playlist_order = list(tracks_for_active_playlist) # Głęboka kopia listy słowników
        self.playlist = list(self.original_playlist_order) # Druga głęboka kopia
        # --- KONIEC ZMIANY ---

        if self.shuffle_mode and self.playlist:
            current_playing_entry_if_any = None
            if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                current_playing_entry_if_any = self.playlist[self.current_track_index] # To jest słownik

            random.shuffle(self.playlist)

            if current_playing_entry_if_any and current_playing_entry_if_any in self.playlist: # Porównanie słowników
                self.playlist.remove(current_playing_entry_if_any)
                self.playlist.insert(0, current_playing_entry_if_any)
                self.current_track_index = 0
            elif self.playlist:
                self.current_track_index = 0
            else:
                self.current_track_index = -1
        elif not self.playlist:
            self.current_track_index = -1
        # Jeśli self.current_track_index jest poza zakresem nowej self.playlist (np. playlista skrócona)
        elif self.current_track_index >= len(self.playlist):
             self.current_track_index = len(self.playlist) -1 if self.playlist else -1


        logging.info(f"Załadowano aktywną playlistę: '{self.active_playlist_name}' ({len(self.playlist)} utworów). Shuffle: {self.shuffle_mode}")


    def _build_ui(self):
        """Buduje interfejs użytkownika dla strony odtwarzacza muzyki z przełączanym widokiem."""
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        self.parent_frame.rowconfigure(0, weight=0) # top_panel_frame
        self.parent_frame.rowconfigure(1, weight=1, minsize=300) # Główny obszar treści
        self.parent_frame.rowconfigure(2, weight=0) # bottom_bar_frame
        self.parent_frame.columnconfigure(0, weight=1)

        # === Górny Panel ===
        top_panel_frame = ttk.Frame(self.parent_frame, padding=(0, 0, 0, 5))
        top_panel_frame.grid(row=0, column=0, sticky="new")
        
        top_panel_frame.columnconfigure(0, weight=0) 
        top_panel_frame.columnconfigure(1, weight=1) 
        top_panel_frame.columnconfigure(2, weight=0) 

        # --- Lewa strona górnego panelu ---
        left_actions_frame = ttk.Frame(top_panel_frame)
        left_actions_frame.grid(row=0, column=0, sticky="w", padx=(10,5))

        self.add_music_menubutton = ttk.Menubutton(left_actions_frame, text="➕ Dodaj/Importuj")
        add_music_menu = tk.Menu(self.add_music_menubutton, tearoff=0)
        add_music_menu.add_command(label="Dodaj Folder...", command=self._add_music_folder)
        add_music_menu.add_command(label="Dodaj Pliki...", command=self._add_music_files)
        add_music_menu.add_separator()
        add_music_menu.add_command(label="Importuj Folder (do wewn.)", command=lambda: self._add_music_folder(import_to_internal=True))
        add_music_menu.add_command(label="Importuj Pliki (do wewn.)", command=lambda: self._add_music_files(import_to_internal=True))
        self.add_music_menubutton["menu"] = add_music_menu
        self.add_music_menubutton.pack(side=tk.LEFT, padx=(0,5))
        ToolTip(self.add_music_menubutton, "Dodaj muzykę z folderów/plików lub zaimportuj do wewnętrznej biblioteki.")

        self.fetch_all_covers_button = ttk.Button(left_actions_frame, text="🌍 Okładki", 
                                                  command=self._fetch_covers_for_active_playlist)
        self.fetch_all_covers_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.fetch_all_covers_button, "Pobierz okładki z Last.fm dla wszystkich utworów w aktywnej playliście")
        
        ttk.Button(left_actions_frame, text="🗑️ Wyczyść", command=self._clear_current_queue).pack(side=tk.LEFT, padx=5)
        ToolTip(left_actions_frame.winfo_children()[-1], "Wyczyść aktywną kolejkę/playlistę")

        self.show_favorites_only_var = tk.BooleanVar(value=False)
        favorites_check = ttk.Checkbutton(
            left_actions_frame, 
            text="♥ Ulubione",
            variable=self.show_favorites_only_var,
            command=lambda: (
                self._update_playlist_display(),
                (self._update_music_tiles_display() if self.music_library_view_mode.get() == "tiles" else None)
            )
        )
        favorites_check.pack(side=tk.LEFT, padx=(10,0)) 
        
        # Środkowa część - Wyszukiwarka
        search_frame = ttk.Frame(top_panel_frame)
        search_frame.grid(row=0, column=1, sticky="ew", padx=5)
        search_frame.columnconfigure(0, weight=1) 
        self.search_music_var = tk.StringVar()
        self.search_music_var.trace_add("write", lambda *args: self._debounce_search_update())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_music_var, width=30)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0,2))
        search_entry.bind("<Return>", lambda event: "break")
        ToolTip(search_entry, "Wyszukaj utwory na playliście...")
        clear_search_btn = ttk.Button(search_frame, text="✖", command=self._clear_search_music, width=3, style="Toolbutton.TButton")
        clear_search_btn.grid(row=0, column=1, sticky="e")

        # --- NOWE ZMIANY: Modyfikacja prawej strony górnego panelu ---
        right_controls_frame = ttk.Frame(top_panel_frame)
        right_controls_frame.grid(row=0, column=2, sticky="e", padx=(5,10)) 

        self.music_view_mode_button = ttk.Button(right_controls_frame, command=self._toggle_music_view_mode, width=8) # Stała szerokość
        self.music_view_mode_button.pack(side=tk.LEFT, padx=(0,10)) # Tekst ustawiany w _update_music_view_mode_button_text
        # Tooltip zostanie dodany w _update_music_view_mode_button_text
        
        # Sortowanie - ukrywamy etykietę "Sortuj:"
        sort_sub_frame = ttk.Frame(right_controls_frame) 
        sort_sub_frame.pack(side=tk.LEFT, padx=2) # Zmniejszony padx
        # ttk.Label(sort_sub_frame, text="Sortuj:").pack(side=tk.LEFT) # <-- UKRYTE
        self.sort_criteria_var = tk.StringVar(value="Domyślnie")
        self.SORT_OPTIONS = { 
            "Domyślnie": ("default", False), 
            "Tytuł A-Z": ("title_az", False), "Tytuł Z-A": ("title_za", True), 
            "Ścieżka A-Z": ("path_az", False), "Ścieżka Z-A": ("path_za", True), 
        }
        self.sort_option_menu = ttk.OptionMenu( 
            sort_sub_frame, self.sort_criteria_var, self.sort_criteria_var.get(), 
            *list(self.SORT_OPTIONS.keys()), 
            command=lambda sel_opt: self._on_sort_criteria_change()
        )
        self.sort_option_menu.config(width=10) # Zmniejszona szerokość
        self.sort_option_menu.pack(side=tk.LEFT)
        ToolTip(self.sort_option_menu, "Sortuj playlistę według...")

        # Zarządzanie playlistami - ukrywamy etykietę "Playlista:"
        playlist_mgmt_sub_frame = ttk.Frame(right_controls_frame) 
        playlist_mgmt_sub_frame.pack(side=tk.LEFT, padx=(5,0)) # Zmniejszony padx
        # ttk.Label(playlist_mgmt_sub_frame, text="Playlista:").pack(side=tk.LEFT) # <-- UKRYTE
        self.active_playlist_var = tk.StringVar()
        self.playlist_choice_combo = ttk.Combobox( playlist_mgmt_sub_frame, textvariable=self.active_playlist_var, state="readonly", width=15 ) # Zmniejszona szerokość
        self.playlist_choice_combo.pack(side=tk.LEFT, padx=(0,1)) # Minimalny padx
        self.playlist_choice_combo.bind("<<ComboboxSelected>>", self._switch_active_playlist_event)
        ToolTip(self.playlist_choice_combo, "Wybierz aktywną playlistę")
        
        ttk.Button(playlist_mgmt_sub_frame, text="+", command=self._create_new_playlist_dialog, width=2, style="Toolbutton.TButton").pack(side=tk.LEFT, padx=(1,1)) # Szerokość 2
        ToolTip(playlist_mgmt_sub_frame.winfo_children()[-1], "Nowa playlista")
        
        self.delete_playlist_button = ttk.Button(playlist_mgmt_sub_frame, text="-", command=self._delete_active_playlist_dialog, width=2, style="Toolbutton.TButton") # Szerokość 2
        self.delete_playlist_button.pack(side=tk.LEFT)
        ToolTip(self.delete_playlist_button, "Usuń aktywną playlistę")
        # --- KONIEC NOWYCH ZMIAN ---


        # === Sekcja 2: Główny obszar treści ===
        self.playlist_outer_frame = ttk.Frame(self.parent_frame)
        self.playlist_outer_frame.rowconfigure(0, weight=1)
        self.playlist_outer_frame.columnconfigure(0, weight=1)
        self.playlist_outer_frame.columnconfigure(2, weight=0) 
        self.playlist_listbox = tk.Listbox(self.playlist_outer_frame, selectmode=tk.EXTENDED, bg="#2e2e2e", fg="white", height=15, activestyle='none', exportselection=False)
        self.playlist_listbox.grid(row=0, column=0, sticky="nsew")
        playlist_scrollbar = ttk.Scrollbar(self.playlist_outer_frame, orient="vertical", command=self.playlist_listbox.yview)
        playlist_scrollbar.grid(row=0, column=1, sticky="ns")
        self.playlist_listbox.config(yscrollcommand=playlist_scrollbar.set)
        self.playlist_listbox.bind("<Double-1>", self._play_selected_from_playlist)
        self.playlist_listbox.bind("<Button-3>", self._show_playlist_context_menu)
        self.playlist_listbox.bind("<<ListboxSelect>>", self._update_move_buttons_state)
        move_buttons_frame = ttk.Frame(self.playlist_outer_frame)
        move_buttons_frame.grid(row=0, column=2, padx=(5,0), pady=(0,0), sticky="ns")
        self.move_up_button = ttk.Button(move_buttons_frame, text="▲", command=self._move_track_up, width=3, style="Toolbutton.TButton", state=tk.DISABLED)
        self.move_up_button.pack(side=tk.TOP, pady=(0,2)); ToolTip(self.move_up_button, "Przesuń w górę")
        self.move_down_button = ttk.Button(move_buttons_frame, text="▼", command=self._move_track_down, width=3, style="Toolbutton.TButton", state=tk.DISABLED)
        self.move_down_button.pack(side=tk.TOP, pady=(2,0)); ToolTip(self.move_down_button, "Przesuń w dół")
        
        # --- Ramka dla widoku kafelków ---
        self.music_tiles_canvas_frame = ttk.Frame(self.parent_frame)
        self.music_tiles_canvas_frame.rowconfigure(0, weight=1)
        self.music_tiles_canvas_frame.columnconfigure(0, weight=1)
        self.music_tiles_canvas = tk.Canvas(self.music_tiles_canvas_frame, bg="#1c1c1c", highlightthickness=0)
        self.music_tiles_canvas.grid(row=0, column=0, sticky="nsew")
        self.music_tiles_scrollbar = ttk.Scrollbar(self.music_tiles_canvas_frame, orient="vertical", command=self.music_tiles_canvas.yview)
        self.music_tiles_scrollbar.grid(row=0, column=1, sticky="ns")
        self.music_tiles_canvas.configure(yscrollcommand=self.music_tiles_scrollbar.set)
        self.music_tiles_inner_frame = ttk.Frame(self.music_tiles_canvas, style="TFrame")
        self.music_tiles_canvas_window_id = self.music_tiles_canvas.create_window(
            (0, 0), window=self.music_tiles_inner_frame, anchor="nw"
        )
        self.music_tiles_canvas.bind("<Configure>", self._on_music_tiles_canvas_configure)
        self.music_tiles_inner_frame.bind("<Configure>", lambda e: self.music_tiles_canvas.configure(scrollregion=self.music_tiles_canvas.bbox("all")) if hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists() else None)
                # --- NOWE ZMIANY: Bindowanie kółka myszy dla kafelków ---
        # Bind do canvasu ORAZ do jego wewnętrznej ramki, aby przewijanie działało
        # gdy kursor jest nad pustym miejscem canvasu lub nad samymi kafelkami.
        # Używamy add='+', aby nie nadpisać innych potencjalnych bindowań na root.
        self.music_tiles_canvas.bind_all("<MouseWheel>", self._on_music_tiles_mousewheel, add='+')
        # Można też spróbować bindować bezpośrednio do widgetów, jeśli bind_all powoduje konflikty
        # self.music_tiles_canvas.bind("<MouseWheel>", self._on_music_tiles_mousewheel)
        # self.music_tiles_inner_frame.bind("<MouseWheel>", self._on_music_tiles_mousewheel) # Dla przewijania nad kafelkami
        # --- KONIEC NOWYCH ZMIAN ---


        # --- Ramka Focus View ---
        self.now_playing_focus_frame = ttk.Frame(self.parent_frame, style="TFrame", padding=20)
        self.now_playing_focus_frame.columnconfigure(0, weight=1)
        self.now_playing_focus_frame.rowconfigure(0, weight=1) 
        self.now_playing_focus_frame.rowconfigure(1, weight=0) 
        self.now_playing_focus_frame.rowconfigure(2, weight=1) 
        self.focus_cover_label = ttk.Label(self.now_playing_focus_frame, text="[ Miejsce na Dużą Okładkę ]", font=("Segoe UI", 24, "italic"), anchor="center", style="TLabel")
        self.focus_cover_label.grid(row=0, column=0, sticky="nsew", pady=(20, 10))
        self.focus_title_artist_label = ttk.Label(self.now_playing_focus_frame, text="Tytuł Utworu - Wykonawca", font=("Segoe UI", 18, "bold"), anchor="center", wraplength=500, style="TLabel")
        self.focus_title_artist_label.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        # === Sekcja 3: Dolny Pasek Kontrolny ===
        # (Stylizacja paska przeniesiona tutaj dla pewności, że jest wywołana przed jego elementami)
        active_theme_name_main = self.launcher.settings.get('theme', 'Dark')
        all_themes_main = self.launcher.get_all_available_themes()
        active_theme_def_main = all_themes_main.get(active_theme_name_main, THEMES.get('Dark', {}))
        default_bottom_bar_bg = "#2a2a2a"
        bottom_bar_bg_color = active_theme_def_main.get('entry_background', default_bottom_bar_bg)
        style = ttk.Style()
        style.configure("MusicTileSelected.TFrame",
                        background=active_theme_def_main.get('link_foreground', '#aabbff'),
                        relief="solid", borderwidth=2)
        style.configure("BottomBar.TFrame", background=bottom_bar_bg_color)
        style.configure("BottomBar.Controls.TFrame", background=bottom_bar_bg_color)
        style.configure("BottomBar.Controls.TLabel", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('foreground', 'white'))
        style.configure("BottomBar.NowPlaying.TLabel", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('foreground', 'white'), font=("Segoe UI", 10, "bold"))
        style.configure("BottomBar.TrackTime.TLabel", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('foreground', 'gray'))
        style.configure("Music.Toolbutton.TButton", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('button_foreground', 'white'), padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.Toolbutton.TButton", foreground=[('active', active_theme_def_main.get('link_foreground', '#aabbff')), ('hover', active_theme_def_main.get('link_foreground', '#aabbff'))], background=[('active', bottom_bar_bg_color), ('hover', bottom_bar_bg_color)])
        style.configure("Music.PlayPause.TButton", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('button_foreground', 'white'), padding=6, font=("Segoe UI", 12, "bold"), relief="flat", borderwidth=0)
        style.map("Music.PlayPause.TButton", foreground=[('active', active_theme_def_main.get('link_foreground', '#aabbff')), ('hover', active_theme_def_main.get('link_foreground', '#aabbff'))], background=[('active', bottom_bar_bg_color), ('hover', bottom_bar_bg_color)])
        style.configure("Music.FavOn.TButton", background=bottom_bar_bg_color, foreground="MediumPurple1", padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.FavOn.TButton", foreground=[('active', "MediumPurple3"), ('hover', "MediumPurple2")], background=[('active', bottom_bar_bg_color), ('hover', bottom_bar_bg_color)])
        style.configure("Music.FavOff.TButton", background=bottom_bar_bg_color, foreground=active_theme_def_main.get('foreground', 'gray'), padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.FavOff.TButton", foreground=[('active', "MediumPurple1"), ('hover', "MediumPurple1")], background=[('active', bottom_bar_bg_color), ('hover', bottom_bar_bg_color)])
        try: # Definicje stylów suwaków (pozostawiam jak były, ale upewnij się, że są w odpowiednim miejscu)
            scale_trough_color = bottom_bar_bg_color; scale_slider_color = active_theme_def_main.get('scrollbar_slider', '#555555'); disabled_scale_slider_color = "#404040"
            style.configure("MusicProgress.Horizontal.TScale", troughcolor=scale_trough_color, background=scale_slider_color, sliderrelief='flat', borderwidth=0)
            style.map("MusicProgress.Horizontal.TScale", background=[('disabled', disabled_scale_slider_color)])
            style.configure("MusicVolume.Horizontal.TScale", troughcolor=scale_trough_color, background=scale_slider_color, sliderrelief='flat', borderwidth=0)
            style.map("MusicVolume.Horizontal.TScale", background=[('disabled', disabled_scale_slider_color)])
        except tk.TclError as e: logging.warning(f"Nie można w pełni skonfigurować stylu suwaków: {e}")

        bottom_bar_frame = ttk.Frame(self.parent_frame, style="BottomBar.TFrame", height=80, padding=(10,5))
        bottom_bar_frame.grid(row=2, column=0, sticky="sew")
        bottom_bar_frame.columnconfigure(0, weight=3); bottom_bar_frame.columnconfigure(1, weight=4); bottom_bar_frame.columnconfigure(2, weight=2)
        # --- Lewa Strona Paska (Info o utworze i Ulubione) ---
        now_playing_area = ttk.Frame(bottom_bar_frame, style="BottomBar.Controls.TFrame")
        now_playing_area.grid(row=0, column=0, sticky="nsw", padx=(0,10), pady=(0,5))
        # Kolumny dla now_playing_area: 0-Miniaturka, 1-Przycisk Fav, 2-Tekst Utworu
        now_playing_area.columnconfigure(0, weight=0) # Stała szerokość dla miniaturki
        now_playing_area.columnconfigure(1, weight=0) # Stała szerokość dla Fav
        now_playing_area.columnconfigure(2, weight=1) # Tekst się rozciąga

        # --- NOWY ELEMENT: Etykieta na miniaturkę okładki na dolnym pasku ---
        self.bottom_bar_cover_label = ttk.Label(now_playing_area, anchor="center")
        # Ustawimy stały, mały rozmiar, np. 40x40 lub 50x50
        # Placeholder będzie musiał być w tym rozmiarze lub obrazek będzie skalowany
        # Wysokość będzie determinowana przez rowspan, a szerokość przez content
        self.bottom_bar_cover_label.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 8))
        # Na razie nie ustawiamy obrazka ani tekstu, zrobi to metoda aktualizująca.
        # --- KONIEC NOWEGO ELEMENTU ---

        self.fav_button = ttk.Button(now_playing_area, command=self._toggle_favorite_current_track, width=3, style="Music.Toolbutton.TButton")
        # --- ZMIANA: fav_button teraz w kolumnie 1 ---
        self.fav_button.grid(row=0, column=1, rowspan=2, sticky="nsw", padx=(0,8), pady=(2,0))
        # self._update_fav_button_text() # Wywoływane w __init__

        self.now_playing_label = ttk.Label(now_playing_area, text="Nic nie gra", style="BottomBar.NowPlaying.TLabel", anchor="w", wraplength=180) # Zmniejszono wraplength, bo jest miniaturka
        # --- ZMIANA: now_playing_label teraz w kolumnie 2 ---
        self.now_playing_label.grid(row=0, column=2, sticky="new")

        self.track_time_label = ttk.Label(now_playing_area, text="0:00 / 0:00", style="BottomBar.TrackTime.TLabel", anchor="w")
        # --- ZMIANA: track_time_label teraz w kolumnie 2 ---
        self.track_time_label.grid(row=1, column=2, sticky="new")
        center_controls_area = ttk.Frame(bottom_bar_frame, style="BottomBar.Controls.TFrame")
        center_controls_area.grid(row=0, column=1, sticky="nsew", padx=10)
        center_controls_area.columnconfigure(0, weight=1)
        player_buttons_frame = ttk.Frame(center_controls_area, style="BottomBar.Controls.TFrame")
        player_buttons_frame.pack(pady=(0,3))
        self.shuffle_button = ttk.Button(player_buttons_frame, command=self._toggle_shuffle_mode, width=8, style="Music.Toolbutton.TButton")
        self.shuffle_button.pack(side=tk.LEFT, padx=5);
        self.prev_button = ttk.Button(player_buttons_frame, text="⏮", command=self._prev_track, width=3, style="Music.Toolbutton.TButton")
        self.prev_button.pack(side=tk.LEFT, padx=5)
        self.play_pause_button = ttk.Button(player_buttons_frame, text="▶", command=self._toggle_play_pause, width=4, style="Music.PlayPause.TButton")
        self.play_pause_button.pack(side=tk.LEFT, padx=8)
        self.next_button = ttk.Button(player_buttons_frame, text="⏭", command=self._next_track, width=3, style="Music.Toolbutton.TButton")
        self.next_button.pack(side=tk.LEFT, padx=5)
        self.repeat_button = ttk.Button(player_buttons_frame, command=self._toggle_repeat_mode, width=10, style="Music.Toolbutton.TButton")
        self.repeat_button.pack(side=tk.LEFT, padx=5); 
        self.autoplay_button = ttk.Button(player_buttons_frame, command=self._toggle_autoplay, width=12, style="Music.Toolbutton.TButton")
        self.autoplay_button.pack(side=tk.LEFT, padx=5); 
        self.progress_scale_var = tk.DoubleVar(value=0.0)
        self.progress_scale = ttk.Scale( center_controls_area, orient=tk.HORIZONTAL, variable=self.progress_scale_var, from_=0, to=100, command=self._on_progress_scale_drag, state=tk.DISABLED, style="MusicProgress.Horizontal.TScale")
        self.progress_scale.pack(fill="x", padx=2, pady=(2,0))
        self.progress_scale.bind("<ButtonPress-1>", self._begin_seek)
        self.progress_scale.bind("<ButtonRelease-1>", self._end_seek)
        volume_area = ttk.Frame(bottom_bar_frame, style="BottomBar.Controls.TFrame")
        volume_area.grid(row=0, column=2, sticky="nse", padx=(10,0))
        ttk.Label(volume_area, text="🔊", style="BottomBar.Controls.TLabel", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0,3))
        self.volume_scale = ttk.Scale(volume_area, from_=0, to=100, orient=tk.HORIZONTAL, command=self._set_volume, length=100, style="MusicVolume.Horizontal.TScale")
        self.volume_scale.pack(side=tk.LEFT, padx=3)
        self.volume_percent_label = ttk.Label(volume_area, text="50%", style="BottomBar.Controls.TLabel", width=5, anchor="w")
        self.volume_percent_label.pack(side=tk.LEFT, padx=(3,0))
        self.toggle_queue_button = ttk.Button(volume_area, text="☰", command=self._toggle_queue_view, width=3, style="Music.Toolbutton.TButton")
        self.toggle_queue_button.pack(side=tk.LEFT, padx=(10, 0))
        ToolTip(self.toggle_queue_button, "Pokaż/Ukryj Kolejkę")
        
        # Te wywołania są teraz na końcu __init__
        # self._update_repeat_button_text()
        # self._update_shuffle_button_text()
        # self._update_fav_button_text() 
        # self._update_autoplay_button_text()

        selected_bg_color = active_theme_def_main.get('link_foreground', '#aabbff')
        selected_fg_color = active_theme_def_main.get('background', '#1e1e1e')
        if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
            self.playlist_listbox.configure( selectbackground=selected_bg_color, selectforeground=selected_fg_color, borderwidth=0, highlightthickness=0)

    # --- NOWE METODY DLA WYSZUKIWARKI ---
    def _debounce_search_update(self):
        """Opóźnia aktualizację playlisty po wpisaniu tekstu w wyszukiwarce."""
        if self._search_update_timer:
            self.parent_frame.after_cancel(self._search_update_timer)
        self._search_update_timer = self.parent_frame.after(
            self._search_debounce_ms,
            lambda: (
                self._update_playlist_display(),
                # jeśli jesteśmy w trybie kafelków, to też je odśwież
                (self._update_music_tiles_display() if self.music_library_view_mode.get() == "tiles" else None)
            )
        )

    def _clear_search_music(self):
        """Czyści pole wyszukiwania i odświeża playlistę."""
        self.search_music_var.set("")
        # _update_playlist_display zostanie wywołane przez trace na search_music_var lub przez _debounce_search_update
        # Aby wymusić natychmiastowe, można też dodać:
        # self._update_playlist_display()
    # --- KONIEC NOWYCH METOD ---

    # --- Metoda do aktualizacji tekstu/ikony przycisku Ulubione (NOWA) ---
    # W _update_fav_button_text, upewnij się, że używasz ścieżki do sprawdzenia:
    def _update_fav_button_text(self):
        if not (hasattr(self, 'fav_button') and self.fav_button.winfo_exists()):
            return

        is_current_track_a_favorite = False
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_track_entry = self.playlist[self.current_track_index]
            current_track_path = current_track_entry.get('path') # Pobierz ścieżkę
            if current_track_path and current_track_path in self.favorite_tracks: # Sprawdź po ścieżce
                is_current_track_a_favorite = True
            # --- KONIEC ZMIANY ---
        
        tooltip_text = ""
        if is_current_track_a_favorite:
            self.fav_button.config(text="♥", style="Music.FavOn.TButton")
            tooltip_text = "Usuń z ulubionych"
        else:
            self.fav_button.config(text="♡", style="Music.FavOff.TButton")
            tooltip_text = "Dodaj do ulubionych"
        
        # Zaktualizuj lub stwórz tooltip
        if hasattr(self.fav_button, 'tooltip') and self.fav_button.tooltip:
            self.fav_button.tooltip.update_text(tooltip_text)
        else:
            ToolTip(self.fav_button, tooltip_text)

    # --- NOWA METODA OBSŁUGI KÓŁKA MYSZY DLA KAFELKÓW ---
    def _on_music_tiles_mousewheel(self, event):
        """Przewija canvas z kafelkami muzycznymi za pomocą kółka myszy."""
        if not (hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists()):
            return

        # Sprawdź, czy kursor jest nad obszarem kafelków muzycznych
        # (lub jego dziećmi - inner_frame)
        widget_under_cursor = None
        try:
            widget_under_cursor = self.parent_frame.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError):
            widget_under_cursor = None

        is_music_tiles_area = False
        current_widget = widget_under_cursor
        while current_widget is not None:
            if current_widget == self.music_tiles_canvas or current_widget == self.music_tiles_inner_frame:
                is_music_tiles_area = True
                break
            if current_widget == self.parent_frame: # Ograniczamy do ramki strony muzyki
                break
            try:
                current_widget = current_widget.master
            except tk.TclError: # Widget mógł zostać zniszczony
                break
        
        if is_music_tiles_area:
            # Określ kierunek przewijania w zależności od platformy
            if event.num == 5 or event.delta < 0: # Przewijanie w dół
                scroll_val = 1
            elif event.num == 4 or event.delta > 0: # Przewijanie w górę
                scroll_val = -1
            else: # Nierozpoznane zdarzenie kółka
                return

            # Sprawdź granice przed przewinięciem, aby uniknąć "odbijania"
            view_start, view_end = self.music_tiles_canvas.yview()
            if (scroll_val < 0 and view_start > 0.0001) or \
               (scroll_val > 0 and view_end < 0.9999):
                self.music_tiles_canvas.yview_scroll(scroll_val, "units")
                # Można dodać tu wywołanie lazy loadingu, jeśli będzie zaimplementowany dla kafelków
                # np. self._trigger_music_tiles_lazy_load()
                return "break" # Zatrzymaj dalszą propagację zdarzenia, jeśli przewinięto
        # Jeśli nie jesteśmy nad obszarem kafelków, pozwól zdarzeniu się propagować
        # (może inne canvasy/listboxy chcą je przechwycić)
    # --- KONIEC NOWEJ METODY ---

    # --- NOWA METODA POMOCNICZA DO POBIERANIA TYTUŁU/ARTYSTY DLA SORTOWANIA ---
    def _get_sortable_title_artist(self, track_entry_or_path) -> str: # Akceptuje słownik lub ścieżkę
        """Pobiera 'Tytuł - Artysta' lub nazwę pliku dla celów sortowania (zwraca lowercase)."""
        track_path = None
        # --- NOWE ZMIANY: Logika pobierania ścieżki ---
        if isinstance(track_entry_or_path, dict):
            track_path = track_entry_or_path.get('path')
        elif isinstance(track_entry_or_path, str):
            track_path = track_entry_or_path
        # --- KONIEC NOWYCH ZMIAN ---
        
        if not track_path or not os.path.exists(track_path):
            return "" 

        title_str = None; artist_str = None
        try:
            audio = MutagenFile(track_path, easy=True)
            if audio:
                if 'title' in audio and audio['title']: title_str = str(audio['title'][0]).strip()
                elif 'TIT2' in audio : title_str = str(audio['TIT2']).strip()
                
                if 'artist' in audio and audio['artist']: artist_str = str(audio['artist'][0]).strip()
                elif 'TPE1' in audio : artist_str = str(audio['TPE1']).strip()
                elif 'albumartist' in audio and audio['albumartist'] and not artist_str:
                    artist_str = str(audio['albumartist'][0]).strip()
        except Exception:
            pass 

        if title_str and artist_str: return f"{title_str} - {artist_str}".lower()
        if title_str: return title_str.lower()
        
        # Zwracamy nazwę pliku (bez rozszerzenia), jeśli brak tagów lub tylko artysta
        return os.path.splitext(os.path.basename(track_path))[0].lower()


    def _on_sort_criteria_change(self, event=None):
        """Obsługuje zmianę kryterium sortowania."""
        selected_display_option = self.sort_criteria_var.get()
        # --- ZMIANA: Usunięto "Domyślnie" z logiki sortowania, jeśli modyfikujemy named_playlists ---
        # Jeśli "Domyślnie" ma coś robić (np. przywracać kolejność zapisu), trzeba by to zaimplementować.
        # Na razie zakładamy, że "Domyślnie" oznacza brak jawnego sortowania - używana jest kolejność z named_playlists.
        # Po ręcznym przesuwaniu, ta kolejność jest zapisywana.
        # Wywołanie _sort_playlist z kluczem "default" może nic nie robić, lub możemy usunąć tę opcję z SORT_OPTIONS.
        # Dla tego przykładu, jeśli jest "Domyślnie", po prostu odświeżymy widok bez sortowania (na wypadek
        # gdyby sortowanie miało jakiś wizualny wskaźnik, który chcemy usunąć).
        # LUB: Możemy założyć, że "Domyślnie" oznacza, że _sort_playlist po prostu załaduje
        # playlistę bez dodatkowego sortowania (co i tak się stanie po modyfikacji `named_playlists` i `_load_active_playlist`).

        sort_key_internal, reverse_order = self.SORT_OPTIONS.get(selected_display_option, ("default", False))
        
        # Jeśli użytkownik wybrał "Domyślnie", po prostu przeładuj i odśwież playlistę,
        # aby mieć pewność, że jest w kolejności z `named_playlists` (po ewentualnych ręcznych przesunięciach).
        # Ta sama logika i tak zajdzie w _sort_playlist, jeśli `sort_key_internal` jest "default"
        # i `_sort_playlist` nie robi nic dla tego klucza.
        self._sort_playlist(sort_key_internal, reverse_order)
        # --- KONIEC ZMIANY ---

    # --- NOWA METODA: Logika sortowania ---
    def _sort_playlist(self, sort_key: str, reverse: bool = False):
        """Sortuje aktywną nazwaną playlistę (listę słowników) według podanego klucza."""
        if not self.active_playlist_name or self.active_playlist_name not in self.named_playlists:
            logging.warning("_sort_playlist: Brak aktywnej playlisty do posortowania.")
            return

        active_named_list_of_entries = self.named_playlists.get(self.active_playlist_name)
        if not active_named_list_of_entries: return

        # Zapamiętaj aktualnie odtwarzany/zaznaczony wpis (słownik)
        current_entry_to_maintain_focus = None
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_entry_to_maintain_focus = self.playlist[self.current_track_index] # To jest słownik
        elif hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists() and self.playlist_listbox.curselection():
            try:
                view_idx = self.playlist_listbox.curselection()[0]
                current_entry_to_maintain_focus = self._get_actual_entry_from_view_index(view_idx) # Zwraca słownik
            except IndexError:
                pass

        if sort_key == "default":
            # Dla "Domyślnie", nie sortujemy, ale musimy przeładować `self.playlist`
            # na wypadek, gdyby `named_playlists` zostało zmienione ręcznie (co powinno się dziać przez metody),
            # lub po prostu dla spójności odświeżenia.
            # `_load_active_playlist()` i tak zostanie wywołane poniżej.
            logging.debug(f"Wybrano sortowanie 'Domyślnie' dla playlisty '{self.active_playlist_name}'. Kolejność pozostaje wg zapisu.")
            pass # Przejdziemy do _load_active_playlist() i reszty
        elif sort_key in ["title_az", "title_za"]:
            # --- ZMIANA: Sortuj listę słowników po 'path' klucza przekazanego do _get_sortable_title_artist ---
            active_named_list_of_entries.sort(key=lambda track_entry: self._get_sortable_title_artist(track_entry.get('path')), reverse=reverse)
            # --- KONIEC ZMIANY ---
        elif sort_key in ["path_az", "path_za"]:
            # --- ZMIANA: Sortuj listę słowników po 'path' ---
            active_named_list_of_entries.sort(key=lambda track_entry: track_entry.get('path', "").lower(), reverse=reverse)
            # --- KONIEC ZMIANY ---
        else:
            logging.warning(f"Nieznany klucz sortowania: {sort_key}")
            return

        logging.info(f"Posortowano playlistę '{self.active_playlist_name}' według: {sort_key}, reverse={reverse}")

        self._load_active_playlist()    # To zaktualizuje self.playlist i self.original_playlist_order z posortowanej named_list
        self._update_playlist_display() 

        # --- ZMIANA: Przywracanie zaznaczenia na podstawie słownika ---
        if current_entry_to_maintain_focus and current_entry_to_maintain_focus in self.playlist: # Sprawdź, czy słownik jest w nowej self.playlist
            try:
                new_idx_of_maintained_entry = self.playlist.index(current_entry_to_maintain_focus)
                self.current_track_index = new_idx_of_maintained_entry
                
                if current_entry_to_maintain_focus in self.currently_displayed_paths:
                    new_view_idx = self.currently_displayed_paths.index(current_entry_to_maintain_focus)
                    if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
                        self.playlist_listbox.selection_clear(0, tk.END)
                        self.playlist_listbox.selection_set(new_view_idx)
                        self.playlist_listbox.activate(new_view_idx)
                        self.playlist_listbox.see(new_view_idx)
                
                if self.is_playing or self.is_paused:
                    self._update_now_playing_label()
                elif self.current_track_index != -1: # Zaktualizuj, nawet jeśli nie gra, ale jest "aktywny"
                     self._update_now_playing_label()

            except ValueError:
                logging.warning(f"Nie można było znaleźć wpisu '{current_entry_to_maintain_focus.get('path')}' po sortowaniu.")
                self.current_track_index = 0 if self.playlist else -1
        elif self.playlist:
            self.current_track_index = 0
        else:
            self.current_track_index = -1
        # --- KONIEC ZMIANY ---

        self._update_move_buttons_state() 
        self._save_player_settings()
        # --- NOWA ZMIANA: Odśwież aktywny widok (listę LUB kafelki) ---
        self._apply_music_content_view() 
        # --- KONIEC NOWEJ ZMIANY ---

    # --- Metoda do przełączania ulubionego dla obecnego utworu (NOWA) ---
    def _toggle_favorite_current_track(self):
        """Przełącza status 'ulubiony' dla aktualnie odtwarzanego/zaznaczonego utworu."""
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            # --- ZMIANA: Pobierz ścieżkę ze słownika ---
            track_entry_to_toggle = self.playlist[self.current_track_index]
            track_path_to_toggle = track_entry_to_toggle.get('path')
            if track_path_to_toggle: # Upewnij się, że ścieżka istnieje
                self._toggle_favorite(track_path_to_toggle) # Przekaż string ścieżki
                # _update_fav_button_text() zostanie wywołane wewnątrz _toggle_favorite
            else:
                logging.warning("_toggle_favorite_current_track: Brak ścieżki dla bieżącego utworu.")
            # --- KONIEC ZMIANY ---
        else:
            messagebox.showinfo("Brak Utworu", "Nie wybrano utworu do oznaczenia jako ulubiony.", parent=self.parent_frame)

    # Metoda _toggle_favorite(self, track_path_to_toggle: str) była już poprawna (przyjmowała string).
    # Problem był w tym, co było do niej przekazywane z _toggle_favorite_current_track.
    # Upewnijmy się, że jej sygnatura i logika są takie:
    
    def _update_autoplay_button_text(self):
        if hasattr(self, 'autoplay_button') and self.autoplay_button:
            text = "Autoplay: Wł." if self.autoplay else "Autoplay: Wył."
            self.autoplay_button.config(text=text)
            tooltip_text = "Automatyczne odtwarzanie następnego utworu: " + ("Włączone" if self.autoplay else "Wyłączone")
            # Użyj istniejącej metody do tooltipów, jeśli chcesz spójności
            self._update_button_tooltip_with_delay_logic(self.autoplay_button, tooltip_text)


    def _toggle_autoplay(self):
        self.autoplay = not self.autoplay
        self._update_autoplay_button_text()
        self._save_player_settings()
        logging.info(f"Tryb Autoplay zmieniony na: {self.autoplay}")
        # Aktualizacja statusu Discord nie jest tu bezpośrednio potrzebna,
        # bo sama zmiana autoplay nie zmienia od razu tego, co widzi Discord.
        # Wpłynie to dopiero na zachowanie po zakończeniu utworu.


    # --- NOWE METODY ---
    def _toggle_queue_view(self):
        """Przełącza widoczność playlisty (kolejki) i widoku koncentracji na utworze."""
        self.is_playlist_view_active.set(not self.is_playlist_view_active.get())
        self._apply_current_view_mode()
        
        # Zaktualizuj tekst/ikonę przycisku (opcjonalnie)
        if hasattr(self, 'toggle_queue_button'):
            text = "🖼️" if self.is_playlist_view_active.get() else "☰" # Np. ikona obrazka/widoku focus vs lista
            self.toggle_queue_button.config(text=text)
            tooltip_text = "Pokaż Widok 'Teraz Odtwarzane'" if self.is_playlist_view_active.get() else "Pokaż Kolejkę"
            ToolTip(self.toggle_queue_button, tooltip_text)


    def _update_music_view_mode_button_text(self):
        if hasattr(self, 'music_view_mode_button') and self.music_view_mode_button.winfo_exists():
            current_mode = self.music_library_view_mode.get()
            # --- NOWE ZMIANY: Krótsze teksty dla przycisku zmiany widoku ---
            if current_mode == "tiles":
                self.music_view_mode_button.config(text="Lista") 
                ToolTip(self.music_view_mode_button, "Przełącz na widok listy")
            else: # current_mode == "list"
                self.music_view_mode_button.config(text="Kafelki")
                ToolTip(self.music_view_mode_button, "Przełącz na widok kafelkowy")
            # --- KONIEC NOWYCH ZMIAN ---

    def _toggle_music_view_mode(self):
        """Przełącza tryb widoku playlisty muzycznej (lista/kafelki)."""
        current_mode = self.music_library_view_mode.get()
        new_mode = "tiles" if current_mode == "list" else "list"
        self.music_library_view_mode.set(new_mode)
        
        # TODO: W przyszłości zapisz `new_mode` do `self.local_settings` jeśli chcesz, aby wybór był trwały
        # self.local_settings["music_player_default_view"] = new_mode
        # self._save_player_settings() # Wywołaj save jeśli zmieniasz local_settings
        
        logging.info(f"Zmieniono widok odtwarzacza muzyki na: {new_mode}")
        self._update_music_view_mode_button_text()
        self._apply_music_content_view()

    def _apply_music_content_view(self):
        """Pokazuje/ukrywa odpowiednią ramkę (listy lub kafelków)."""
        mode = self.music_library_view_mode.get()
        
        # Najpierw ukryj wszystko, co mogło być w głównym obszarze (row=1)
        if hasattr(self, 'playlist_outer_frame') and self.playlist_outer_frame.winfo_ismapped():
            self.playlist_outer_frame.grid_remove()
        if hasattr(self, 'music_tiles_canvas_frame') and self.music_tiles_canvas_frame.winfo_ismapped():
            self.music_tiles_canvas_frame.grid_remove()
        # Jeśli w przyszłości wrócimy do focus_view, też go tu ukryj
        # if hasattr(self, 'now_playing_focus_frame') and self.now_playing_focus_frame.winfo_ismapped():
        #     self.now_playing_focus_frame.grid_remove()

        if mode == "list":
            logging.debug("Aktywowanie widoku listy dla muzyki.")
            self.playlist_outer_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5))
            self._update_playlist_display() # Odśwież zawartość listy
        elif mode == "tiles":
            logging.debug("Aktywowanie widoku kafelków dla muzyki.")
            self.music_tiles_canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5))
            self._update_music_tiles_display() # Odśwież/stwórz kafelki
        
        # Zaktualizuj tytuł i okładkę w widoku "Focus", jeśli nadal używasz tych etykiet gdzie indziej
        # lub jeśli planujesz trzeci widok. Na razie to może nie być potrzebne przy tylko dwóch trybach.
        # self._update_focus_view_labels() 


    def _on_music_tiles_canvas_configure(self, event):
        """Obsługuje zmianę rozmiaru canvasa dla kafelków muzycznych."""
        if hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists():
            canvas_width = event.width
            self.music_tiles_canvas.itemconfig(self.music_tiles_canvas_window_id, width=canvas_width)
            # TODO: W przyszłości, po dodaniu kafelków, wywołaj odświeżenie ich układu
            # np. self._update_music_tiles_layout_or_lazy_load()
            # Na razie, jeśli są już jakieś kafelki:
            if self.music_tiles_inner_frame.winfo_children():
                 self._update_music_tiles_display() # Proste odświeżenie
            self.music_tiles_canvas.configure(scrollregion=self.music_tiles_canvas.bbox("all"))

    # --- PLACEHOLDER DLA WYŚWIETLANIA KAFELKÓW ---
# W klasie MusicPlayerPage

    def _update_music_tiles_display(self):
        """Wypełnia ramkę music_tiles_inner_frame kafelkami utworów."""
        if not (hasattr(self, 'music_tiles_inner_frame') and self.music_tiles_inner_frame.winfo_exists() and \
                hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists()):
            logging.warning("_update_music_tiles_display: Wymagane widgety dla kafelków nie istnieją.")
            return

        for widget in self.music_tiles_inner_frame.winfo_children():
            widget.destroy()

        tracks_to_tile = self.currently_displayed_paths

        if not tracks_to_tile:
            ttk.Label(self.music_tiles_inner_frame, text="Brak utworów do wyświetlenia.",
                      font=("Segoe UI", 12), style="TLabel").pack(padx=20, pady=50, anchor="center") # Skrócony tekst
            self.music_tiles_inner_frame.update_idletasks()
            if hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists():
                self.music_tiles_canvas.configure(scrollregion=self.music_tiles_canvas.bbox("all"))
            return
        
        tile_padding_x = 10
        tile_padding_y = 10
        tile_width = 160 
        cover_height_ratio = 0.70
        tile_total_height = 220 
        
        cover_width = tile_width - 4 # Uwzględniając padx=2 dla cover_label z obu stron
        cover_height = int(tile_total_height * cover_height_ratio)
        cover_target_size = (cover_width, cover_height)
        
        internal_padding_cover = 2 
        internal_padding_info = 3
        info_height = tile_total_height - cover_height - (2 * internal_padding_cover) - (2 * internal_padding_info)
        info_height = max(20, info_height)
        
        self.music_tiles_canvas.update_idletasks()
        canvas_width = self.music_tiles_canvas.winfo_width()
        if canvas_width <= 1: canvas_width = 600 
        num_columns = max(1, (canvas_width - tile_padding_x) // (tile_width + tile_padding_x))

        for i in range(num_columns):
            self.music_tiles_inner_frame.columnconfigure(i, weight=1, minsize=tile_width)

        style_instance = ttk.Style() # Potrzebne do lookup stylu dla placeholderu

        row, col = 0, 0
        for track_entry_from_current_view in tracks_to_tile:
            track_path = track_entry_from_current_view.get('path')
            if not track_path: continue

            is_current_playing_or_selected_tile = False
            if self.is_playing or self.is_paused:
                if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                    if self.playlist[self.current_track_index].get('path') == track_path:
                        is_current_playing_or_selected_tile = True
            
            tile_frame_style = "MusicTileSelected.TFrame" if is_current_playing_or_selected_tile else "NormalMusicTile.TFrame"
            # Zakładam, że styl "NormalMusicTile.TFrame" jest zdefiniowany w apply_theme_colors
            # Jeśli nie, użyj "Game.TFrame" i upewnij się, że jest poprawnie stylizowany.
            
            tile_frame = ttk.Frame(
                self.music_tiles_inner_frame,
                style=tile_frame_style,
                width=tile_width, height=tile_total_height
            )
            tile_frame.grid(row=row, column=col, padx=tile_padding_x, pady=tile_padding_y, sticky="nsew")
            tile_frame.grid_propagate(False)
            tile_frame.rowconfigure(0, weight=0) # Okładka
            tile_frame.rowconfigure(1, weight=1) # Info
            tile_frame.columnconfigure(0, weight=1)

            cover_label = ttk.Label(tile_frame, anchor="center") 
            cover_label.grid(row=0, column=0, sticky="ew", padx=2, pady=(2,0)) 
            
            cover_path_to_load = track_entry_from_current_view.get('focus_cover_path') or track_entry_from_current_view.get('lastfm_cover_path')
            tile_cover_photo = None

            if cover_path_to_load and os.path.exists(cover_path_to_load):
                cache_key = f"{cover_path_to_load}_{cover_target_size[0]}x{cover_target_size[1]}"
                if cache_key in self._cover_cache:
                    tile_cover_photo = self._cover_cache[cache_key]
                else:
                    try:
                        with Image.open(cover_path_to_load) as img:
                            img.thumbnail(cover_target_size, Image.Resampling.LANCZOS)
                            tile_cover_photo = ImageTk.PhotoImage(img)
                            self._cover_cache[cache_key] = tile_cover_photo
                    except Exception as e_cover:
                        logging.warning(f"Błąd ładowania okładki dla kafelka '{track_path}': {e_cover}")
            
            if tile_cover_photo:
                cover_label.config(image=tile_cover_photo, text="", style="TLabel") 
                cover_label.image = tile_cover_photo
            else:
                # Używamy stylu ramki kafelka dla tła placeholdera nutki
                current_tile_bg_for_placeholder = style_instance.lookup(tile_frame_style, "background")
                cover_label.config(text="🎵", font=("Segoe UI Symbol", cover_height // 3), 
                                   relief="flat", background=current_tile_bg_for_placeholder, 
                                   anchor="center", image=None, style="TLabel")
                try: 
                    # Próba wyśrodkowania pionowego symbolu (może wymagać dostosowania)
                    font_obj = ImageFont.truetype("seguisym.ttf", cover_height // 3) if os.path.exists("seguisym.ttf") else ImageFont.load_default()
                    # Dla ImageFont.load_default() nie ma bbox, więc to może nie być idealne
                    # To jest złożone, aby idealnie wyśrodkować tekst w Label bez obrazka.
                    # Prostsze `ipady` może być wystarczające.
                    text_bbox = (0,0,0,0) # Fallback
                    try:
                        # Prawdziwy bbox tylko z Pillow.ImageDraw, co jest nadmiarowe tutaj.
                        # Możemy przyjąć, że wysokość fontu to ok. cover_height // 3
                        pass
                    except:
                        pass
                    # ipady_val = (cover_height - (cover_height // 3) * 1.2) // 2 # *1.2 to przybliżona wysokość znaku
                    ipady_val = (cover_height - (cover_height // 2)) // 2 # Prostsze przybliżenie
                    if ipady_val > 0:
                       cover_label.grid_configure(ipady=int(ipady_val))
                except Exception as e_ipad:
                    logging.debug(f"Problem z ustawieniem ipady dla placeholder: {e_ipad}")
                    pass

            # --- TUTAJ ZACZYNAŁ SIĘ ZDUBLOWANY I BŁĘDNY BLOK, ZOSTAŁ USUNIĘTY ---
            # (Usunięto powtórzone cover_label.grid, cover_path_to_load, if tile_cover_photo itd.
            #  oraz problematyczne cover_label.configure(background=bg))
            # --- KONIEC USUWANEGO BLOKU ---

            info_frame = ttk.Frame(tile_frame, height=info_height, style="TFrame")
            info_frame.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
            info_frame.grid_propagate(False)
            info_frame.columnconfigure(0, weight=1); info_frame.rowconfigure(0, weight=1)
            
            display_name_on_tile = self._get_display_name_for_track(track_entry_from_current_view).replace("♥ ", "")
            if is_current_playing_or_selected_tile:
                prefix = "▶ " if self.is_playing and not self.is_paused else "❚❚ " if self.is_paused else "● " # Dodano ● dla zaznaczonego, niegrającego
                display_name_on_tile = f"{prefix}{display_name_on_tile}"

            name_label_style_to_use = "ActiveMusicTile.TLabel" if is_current_playing_or_selected_tile else "MusicTile.TLabel"
            track_name_label = ttk.Label(info_frame, text=display_name_on_tile, 
                                         anchor="center", justify="center", wraplength=tile_width - 10,
                                         style=name_label_style_to_use) 
            track_name_label.place(relx=0.5, rely=0.5, anchor="center")

            from functools import partial 
            play_command = partial(self._play_track_from_tile_click, track_entry_from_current_view)
            tile_frame.bind("<Button-1>", play_command)
            cover_label.bind("<Button-1>", play_command)
            info_frame.bind("<Button-1>", play_command)
            track_name_label.bind("<Button-1>", play_command)
            
            context_menu_command = partial(self._show_playlist_context_menu_for_tile, track_entry_from_current_view)
            tile_frame.bind("<Button-3>", context_menu_command)
            cover_label.bind("<Button-3>", context_menu_command)
            info_frame.bind("<Button-3>", context_menu_command)
            track_name_label.bind("<Button-3>", context_menu_command)

            col += 1
            if col >= num_columns: col = 0; row += 1
        
        self.music_tiles_inner_frame.update_idletasks()
        if hasattr(self, 'music_tiles_canvas') and self.music_tiles_canvas.winfo_exists():
             self.music_tiles_canvas.config(scrollregion=self.music_tiles_canvas.bbox("all"))
             
    # --- NOWE METODY POMOCNICZE DLA KAFELKÓW ---
    def _play_track_from_tile_click(self, track_entry_clicked: dict, event=None):
        """Odtwarza utwór po kliknięciu na jego kafelek, porównując po ścieżce."""
        if track_entry_clicked and isinstance(track_entry_clicked, dict) and 'path' in track_entry_clicked:
            clicked_track_path = track_entry_clicked.get('path')
            
            found_index_in_playlist = -1
            for i, entry_in_playlist in enumerate(self.playlist): # self.playlist to lista słowników
                if entry_in_playlist.get('path') == clicked_track_path:
                    found_index_in_playlist = i
                    break
            
            if found_index_in_playlist != -1:
                logging.debug(f"Kafelek kliknięty: '{clicked_track_path}', znaleziono w self.playlist na indeksie {found_index_in_playlist}.")
                self._play_track(found_index_in_playlist)
            else:
                logging.warning(f"Kafelek kliknięty dla '{clicked_track_path}', ale nie znaleziono go w aktualnej self.playlist. Próbuję odświeżyć widok.")
                # Może się zdarzyć, jeśli playlista została mocno zmodyfikowana tuż przed kliknięciem
                # Odświeżenie widoków może pomóc zsynchronizować stan.
                self._load_active_playlist()
                self._update_playlist_display()
                if self.music_library_view_mode.get() == "tiles":
                    self._update_music_tiles_display()
        else:
            logging.warning(f"Kliknięto na kafelek, ale przekazano nieprawidłowy wpis utworu: {track_entry_clicked}")

    def _show_playlist_context_menu_for_tile(self, track_entry_clicked: dict, event=None):
        """Wyświetla menu kontekstowe dla utworu z kafelka."""
        # Ta metoda może być bardzo podobna do _show_playlist_context_menu,
        # ale operuje na przekazanym `track_entry_clicked`.
        # Na razie, dla uproszczenia, możemy spróbować "symulować" zaznaczenie w Listboxie
        # i wywołać standardowe menu. To nie jest idealne, ale na początek może wystarczyć.
        
        if track_entry_clicked and track_entry_clicked in self.currently_displayed_paths:
            try:
                view_index = self.currently_displayed_paths.index(track_entry_clicked)
                if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
                    self.playlist_listbox.selection_clear(0, tk.END)
                    self.playlist_listbox.selection_set(view_index)
                    self.playlist_listbox.activate(view_index)
                    # Teraz wywołaj standardowe menu kontekstowe, które odczyta zaznaczenie z Listboxa
                    self._show_playlist_context_menu(event) 
            except (ValueError, tk.TclError):
                logging.warning("Nie można ustawić zaznaczenia dla menu kontekstowego kafelka.")
        else:
            logging.warning("Próba otwarcia menu kontekstowego dla kafelka bez odpowiadającego wpisu.")

    def _apply_current_view_mode(self):
        """Stosuje aktualnie wybrany tryb widoku (playlista vs focus)."""
        if self.is_playlist_view_active.get():
            # Pokaż widok playlisty
            logging.debug("Przełączanie na widok playlisty.")
            self.now_playing_focus_frame.grid_remove() # Najpierw ukryj drugi
            self.playlist_outer_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5)) # Potem pokaż ten
            self._update_playlist_display() 
        else:
            # Pokaż widok koncentracji na utworze
            logging.debug("Przełączanie na widok koncentracji.")
            self.playlist_outer_frame.grid_remove() # Najpierw ukryj drugi
            self.now_playing_focus_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0) # Potem pokaż ten
            self._update_focus_cover_label()
            self._update_focus_view_labels()

    def _update_focus_view_labels(self):
        """Aktualizuje duże etykiety w widoku koncentracji na utworze."""
        if hasattr(self, 'focus_title_artist_label') and self.focus_title_artist_label.winfo_exists():
            display_text = "Nic nie gra"
            if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                full_path = self.playlist[self.current_track_index]
                formatted_name = self._get_display_name_for_track(full_path).replace("♥ ", "").strip()
                display_text = formatted_name
            self.focus_title_artist_label.config(text=display_text)
            self._update_focus_cover_label()

        # W przyszłości:
        # if hasattr(self, 'focus_cover_label') and self.focus_cover_label.winfo_exists():
        #     # Tutaj logika ładowania i wyświetlania dużej okładki
        #     # self.focus_cover_label.config(image=duza_okladka_photo)
        #     # self.focus_cover_label.image = duza_okladka_photo
        #     pass
    # --- KONIEC NOWYCH METOD ---

    # --- NOWE METODY (niektóre to placeholdery na razie) ---
    def _update_available_playlists_ui(self):
        """Odświeża listę nazwanych playlist w Comboboxie."""
        if hasattr(self, 'playlist_choice_combo'):
            playlist_names = sorted(list(self.named_playlists.keys()))
            self.playlist_choice_combo['values'] = playlist_names
            if self.active_playlist_name in playlist_names:
                self.active_playlist_var.set(self.active_playlist_name)
            elif playlist_names: # Jeśli aktywna nie istnieje, ustaw pierwszą z listy
                self.active_playlist_name = playlist_names[0]
                self.active_playlist_var.set(self.active_playlist_name)
                self._load_active_playlist() # Przeładuj dane
                self._update_playlist_display()
            else: # Brak jakichkolwiek playlist
                self.active_playlist_var.set("")
                # Utwórz domyślną "Główna Kolejka", jeśli jeszcze nie istnieje
                if "Główna Kolejka" not in self.named_playlists:
                    self.named_playlists["Główna Kolejka"] = []
                self.active_playlist_name = "Główna Kolejka"
                self.playlist_choice_combo['values'] = ["Główna Kolejka"]
                self.active_playlist_var.set(self.active_playlist_name)
                self._load_active_playlist()
                self._update_playlist_display()

    # --- NOWA METODA POMOCNICZA DLA MINIATURKI NA PASKU ---
    def _update_bottom_bar_cover_thumbnail(self):
        if not (hasattr(self, 'bottom_bar_cover_label') and self.bottom_bar_cover_label.winfo_exists()):
            return

        thumbnail_path = None
        thumbnail_size = (48, 48) 

        # Sprawdź, czy mamy aktywny utwór
        active_track_has_cover = False
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_track_entry = self.playlist[self.current_track_index]
            path_to_try = current_track_entry.get('focus_cover_path') or current_track_entry.get('lastfm_cover_path')
            if path_to_try and os.path.exists(path_to_try):
                thumbnail_path = path_to_try
                active_track_has_cover = True # Oznacz, że dla TEGO utworu jest okładka
        
        loaded_thumbnail_photo = None
        if thumbnail_path: # Jeśli znaleziono ścieżkę do okładki dla bieżącego utworu
            cache_key = f"bottombar_{thumbnail_path}_{thumbnail_size[0]}x{thumbnail_size[1]}"
            if cache_key in self._bottom_bar_thumbnail_cache:
                loaded_thumbnail_photo = self._bottom_bar_thumbnail_cache[cache_key]
            else:
                try:
                    with Image.open(thumbnail_path) as img:
                        img_copy = img.copy() 
                        img_copy.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                        loaded_thumbnail_photo = ImageTk.PhotoImage(img_copy)
                        self._bottom_bar_thumbnail_cache[cache_key] = loaded_thumbnail_photo
                except Exception as e_thumb:
                    logging.warning(f"Błąd ładowania miniaturki dla dolnego paska '{thumbnail_path}': {e_thumb}")
        
        if loaded_thumbnail_photo:
            # Mamy nową okładkę do wyświetlenia
            self.bottom_bar_cover_label.config(image=loaded_thumbnail_photo, text="")
            self.bottom_bar_cover_label.image = loaded_thumbnail_photo # Ważne: trzymaj referencję
        else:
            # Nie ma okładki dla bieżącego utworu LUB wystąpił błąd ładowania
            # Pokaż placeholder
            style = ttk.Style()
            try:
                bar_control_bg = style.lookup("BottomBar.Controls.TFrame", "background")
            except tk.TclError:
                bar_control_bg = self.launcher.local_settings.get('themes', {}).get(self.launcher.settings.get('theme', 'Dark'), {}).get('entry_background', "#2a2a2a")

            if not hasattr(self, '_placeholder_thumb_img_ref'): # Stwórz placeholder raz
                placeholder_pil_img = Image.new('RGBA', thumbnail_size, (0,0,0,0)) # Przezroczysty
                self._placeholder_thumb_img_ref = ImageTk.PhotoImage(placeholder_pil_img)

            # --- KLUCZOWA ZMIANA: Zawsze ustawiaj image, nawet jeśli to placeholder ---
            self.bottom_bar_cover_label.config(
                image=self._placeholder_thumb_img_ref, # Ustaw przezroczysty obrazek tła
                text="🎵", 
                font=("Segoe UI Symbol", 20), 
                compound="center",             
                background=bar_control_bg, 
                foreground="gray"
            )
            self.bottom_bar_cover_label.image = self._placeholder_thumb_img_ref # Trzymaj referencję do placeholdera
            # --- KONIEC KLUCZOWEJ ZMIANY ---


    # --- NOWE METODY ---
    def _update_move_buttons_state(self, event=None):
        """Aktualizuje stan przycisków przesuwania."""
        if not (hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists() and \
                hasattr(self, 'move_up_button') and self.move_up_button.winfo_exists() and \
                hasattr(self, 'move_down_button') and self.move_down_button.winfo_exists()):
            return

        selection_indices = self.playlist_listbox.curselection()
        num_displayed = len(self.currently_displayed_paths) # Użyj długości listy faktycznie wyświetlanych

        can_move_up = False
        can_move_down = False

        if len(selection_indices) == 1: # Na razie tylko pojedyncze zaznaczenie
            selected_view_index = selection_indices[0]
            if selected_view_index > 0:
                can_move_up = True
            if selected_view_index < num_displayed - 1:
                can_move_down = True
        
        self.move_up_button.config(state=tk.NORMAL if can_move_up else tk.DISABLED)
        self.move_down_button.config(state=tk.NORMAL if can_move_down else tk.DISABLED)

    # --- ZMIANA: Zwraca teraz cały słownik utworu, a nie tylko ścieżkę ---
    def _get_actual_entry_from_view_index(self, view_index: int) -> dict | None:
        """Zwraca słownik utworu na podstawie jego indeksu w currently_displayed_paths."""
        if 0 <= view_index < len(self.currently_displayed_paths):
            return self.currently_displayed_paths[view_index] # Zwróć cały słownik
        return None
    # --- KONIEC ZMIANY ---

    def _move_track_up(self):
        if not (hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists()): return
        selection_indices = self.playlist_listbox.curselection()
        if not selection_indices or len(selection_indices) != 1: return

        selected_view_index = selection_indices[0]
        # --- ZMIANA: Pobierz cały słownik ---
        track_entry_to_move = self._get_actual_entry_from_view_index(selected_view_index)
        if not track_entry_to_move:
            logging.warning("_move_track_up: Nie udało się pobrać wpisu dla zaznaczonego elementu.")
            return
        # --- KONIEC ZMIANY ---

        active_named_list = self.named_playlists.get(self.active_playlist_name)
        # --- ZMIANA: Porównuj całe słowniki lub po unikalnym identyfikatorze (na razie po 'path') ---
        if not active_named_list or not any(entry.get('path') == track_entry_to_move.get('path') for entry in active_named_list):
            logging.warning(f"_move_track_up: Wpis dla '{track_entry_to_move.get('path')}' nie znaleziony w '{self.active_playlist_name}'.")
            self._update_playlist_display(); return
        
        try: # Znajdź indeks porównując po ścieżce (zakładając unikalność ścieżek w playliście)
            current_original_index = -1
            for i, entry in enumerate(active_named_list):
                if entry.get('path') == track_entry_to_move.get('path'):
                    current_original_index = i
                    break
            if current_original_index == -1 : raise ValueError("Track not found by path")
        # --- KONIEC ZMIANY ---
        except ValueError:
            logging.warning(f"_move_track_up: Nie znaleziono '{track_entry_to_move.get('path')}' w active_named_list (index)."); return

        if current_original_index > 0:
            # --- ZMIANA: `item_to_move` to teraz słownik ---
            item_to_move = active_named_list.pop(current_original_index)
            active_named_list.insert(current_original_index - 1, item_to_move)
            # --- KONIEC ZMIANY ---

            self._load_active_playlist()
            self._update_playlist_display()

            # --- ZMIANA: Przywracanie zaznaczenia na podstawie słownika ---
            if track_entry_to_move in self.currently_displayed_paths:
                new_view_index = self.currently_displayed_paths.index(track_entry_to_move)
            # --- KONIEC ZMIANY ---
                self.playlist_listbox.selection_clear(0, tk.END)
                self.playlist_listbox.selection_set(new_view_index)
                self.playlist_listbox.activate(new_view_index)
                self.playlist_listbox.see(new_view_index)

            # --- ZMIANA: Aktualizacja current_track_index na podstawie słownika ---
            if self.is_playing and self.playlist:
                try:
                    self.current_track_index = self.playlist.index(track_entry_to_move) # Znajdź słownik w self.playlist
                except ValueError:
                    self.current_track_index = -1 # Nie znaleziono (nie powinno się zdarzyć)
            # --- KONIEC ZMIANY ---
            self._update_move_buttons_state()
            self._save_player_settings()

    def _move_track_down(self):
        if not (hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists()): return
        selection_indices = self.playlist_listbox.curselection()
        if not selection_indices or len(selection_indices) != 1: return

        selected_view_index = selection_indices[0]
        # --- ZMIANA: Pobierz cały słownik ---
        track_entry_to_move = self._get_actual_entry_from_view_index(selected_view_index)
        if not track_entry_to_move:
            logging.warning("_move_track_down: Nie udało się pobrać wpisu dla zaznaczonego elementu.")
            return
        # --- KONIEC ZMIANY ---
        
        active_named_list = self.named_playlists.get(self.active_playlist_name)
        # --- ZMIANA: Porównuj całe słowniki lub po unikalnym identyfikatorze ---
        if not active_named_list or not any(entry.get('path') == track_entry_to_move.get('path') for entry in active_named_list):
            logging.warning(f"_move_track_down: Wpis dla '{track_entry_to_move.get('path')}' nie znaleziony w '{self.active_playlist_name}'.")
            self._update_playlist_display(); return
        
        try:
            current_original_index = -1
            for i, entry in enumerate(active_named_list):
                if entry.get('path') == track_entry_to_move.get('path'):
                    current_original_index = i
                    break
            if current_original_index == -1 : raise ValueError("Track not found by path")
        # --- KONIEC ZMIANY ---
        except ValueError:
            logging.warning(f"_move_track_down: Nie znaleziono '{track_entry_to_move.get('path')}' w active_named_list (index)."); return


        if current_original_index < len(active_named_list) - 1:
            # --- ZMIANA: `item_to_move` to słownik, poprawiona logika indeksu wstawienia ---
            item_to_move = active_named_list.pop(current_original_index)
            active_named_list.insert(current_original_index + 1, item_to_move) # Wstaw o jedno miejsce dalej
            # --- KONIEC ZMIANY ---

            self._load_active_playlist()
            self._update_playlist_display()

            # --- ZMIANA: Przywracanie zaznaczenia na podstawie słownika ---
            if track_entry_to_move in self.currently_displayed_paths:
                new_view_index = self.currently_displayed_paths.index(track_entry_to_move)
            # --- KONIEC ZMIANY ---
                self.playlist_listbox.selection_clear(0, tk.END)
                self.playlist_listbox.selection_set(new_view_index)
                self.playlist_listbox.activate(new_view_index)
                self.playlist_listbox.see(new_view_index)

            # --- ZMIANA: Aktualizacja current_track_index na podstawie słownika ---
            if self.is_playing and self.playlist:
                try:
                    self.current_track_index = self.playlist.index(track_entry_to_move)
                except ValueError:
                    self.current_track_index = -1
            # --- KONIEC ZMIANY ---
            self._update_move_buttons_state()
            self._save_player_settings()
        else:
            logging.debug(f"_move_track_down: Utwór '{track_entry_to_move.get('path')}' jest już na dole listy.")

    def _create_new_playlist_dialog(self):
        """Otwiera dialog do tworzenia nowej, pustej playlisty."""
        new_playlist_name = simpledialog.askstring(
            "Nowa Playlista",
            "Podaj nazwę dla nowej playlisty:",
            parent=self.parent_frame
        )
        if new_playlist_name and new_playlist_name.strip():
            new_playlist_name = new_playlist_name.strip()
            if new_playlist_name in self.named_playlists:
                messagebox.showwarning("Playlista Istnieje", f"Playlista o nazwie '{new_playlist_name}' już istnieje.", parent=self.parent_frame)
            else:
                self.named_playlists[new_playlist_name] = [] # Stwórz pustą playlistę
                self.active_playlist_name = new_playlist_name # Ustaw jako aktywną
                self._save_player_settings()
                self._load_active_playlist()
                self._update_available_playlists_ui() # Odśwież combobox
                self._update_playlist_display()       # Odśwież listbox (będzie pusty)
                self._stop_music() # Zatrzymaj, jeśli coś grało na starej playliście
                self._update_now_playing_label(track_name="Nic nie gra")
                logging.info(f"Utworzono nową playlistę: '{new_playlist_name}'")
                self._apply_music_content_view() # Odświeży odpowiedni widok (listę lub puste kafelki)
                                # --- NOWE ZMIANY ---
                self._update_delete_playlist_button_state() # Aktualizuj stan przycisku
                # --- KONIEC NOWYCH ZMIAN --
        elif new_playlist_name is not None: # Jeśli użytkownik wpisał spacje lub nic
            messagebox.showwarning("Nieprawidłowa Nazwa", "Nazwa playlisty nie może być pusta.", parent=self.parent_frame)

    def _switch_active_playlist_event(self, event=None):
        """Obsługuje wybór nowej playlisty z Comboboxa."""
        selected_name = self.active_playlist_var.get()
        if selected_name and selected_name != self.active_playlist_name:
            if selected_name in self.named_playlists:
                # Zatrzymaj obecne odtwarzanie przed przełączeniem
                if self.is_playing or self.is_paused:
                    self._stop_music()

                self.active_playlist_name = selected_name
                self.current_track_index = -1 # Zresetuj indeks dla nowej playlisty
                self._load_active_playlist() # Załaduj utwory, zastosuj shuffle jeśli trzeba
                self._update_playlist_display() # Odśwież listbox

                # Spróbuj ustawić pierwszy utwór, jeśli playlista nie jest pusta
                if self.playlist:
                    self.current_track_index = 0
                    path_to_select = self.playlist[self.current_track_index]
                    if path_to_select in self.currently_displayed_paths:
                        try:
                            display_idx_to_select = self.currently_displayed_paths.index(path_to_select)
                            self.playlist_listbox.selection_clear(0, tk.END)
                            self.playlist_listbox.selection_set(display_idx_to_select)
                            self.playlist_listbox.activate(display_idx_to_select)
                        except (tk.TclError, ValueError):
                            logging.warning(f"Nie udało się zaznaczyć pierwszego utworu playlisty '{selected_name}'.")
                    self._update_now_playing_label()
                else:
                    # --- ZMIANA ---
                    self._update_now_playing_label(track_name_override="Playlista pusta")
                    # --- KONIEC ZMIANY ---

                self._save_player_settings()
                logging.info(f"Przełączono na playlistę: '{self.active_playlist_name}'")
                self._apply_music_content_view()
                                # --- NOWE ZMIANY ---
                self._update_delete_playlist_button_state() # Aktualizuj stan przycisku
                # --- KONIEC NOWYCH ZMIAN ---
            else:
                logging.warning(f"Próba przełączenia na nieistniejącą playlistę: {selected_name}")
                self.active_playlist_var.set(self.active_playlist_name) # Przywróć poprzednią wartość w comboboxie
    # --- KONIEC NOWYCH METOD ---

    # --- NOWA METODA ---
    def _show_playlist_context_menu(self, event):
        if not hasattr(self, 'playlist_listbox') or not self.playlist_listbox.winfo_exists():
            logging.warning("_show_playlist_context_menu: Listbox nie istnieje.")
            return

        clicked_item_index_in_view = self.playlist_listbox.nearest(event.y)
        listbox_item_bounds = None
        if clicked_item_index_in_view != -1 and clicked_item_index_in_view < self.playlist_listbox.size():
             listbox_item_bounds = self.playlist_listbox.bbox(clicked_item_index_in_view)

        is_click_on_item = False
        if listbox_item_bounds:
            item_x, item_y, item_width, item_height = listbox_item_bounds
            if item_x <= event.x < item_x + item_width and \
               item_y <= event.y < item_y + item_height:
                is_click_on_item = True

        selected_indices = self.playlist_listbox.curselection()
        context_menu = tk.Menu(self.parent_frame, tearoff=0, background="#2e2e2e", foreground="white")

        if not is_click_on_item and not selected_indices: # Kliknięto na pustym miejscu
            context_menu.add_command(label="➕ Nowa Playlista...", command=self._create_new_playlist_dialog)
            # --- NOWA ZMIANA: Dodanie opcji Odśwież dla Muzyki Wewnętrznej na pustym miejscu ---
            if self.active_playlist_name == "Muzyka Wewnętrzna":
                context_menu.add_separator()
                context_menu.add_command(label="🔁 Odśwież Playlistę 'Muzyka Wewnętrzna'",
                                         command=self._refresh_internal_music_playlist)
            # --- KONIEC NOWEJ ZMIANY ---
            if self.active_playlist_name and len(self.named_playlists) > 0:
                can_delete_active = self.active_playlist_name not in self.permanent_playlists
                if can_delete_active:
                    context_menu.add_command(
                        label=f"❌ Usuń Playlistę '{self.active_playlist_name}'",
                        command=self._delete_active_playlist_dialog
                    )
            context_menu.post(event.x_root, event.y_root)
            return

        if not selected_indices and is_click_on_item and clicked_item_index_in_view != -1 :
            self.playlist_listbox.selection_clear(0, tk.END)
            self.playlist_listbox.selection_set(clicked_item_index_in_view)
            self.playlist_listbox.activate(clicked_item_index_in_view)
            selected_indices = (clicked_item_index_in_view,)

        if not selected_indices:
            return
            
        selected_index_in_view = selected_indices[0]
        current_track_entry = self._get_actual_entry_from_view_index(selected_index_in_view)
        if not current_track_entry: return
        actual_track_path = current_track_entry.get('path')
        if not actual_track_path: return

        is_fav = actual_track_path in self.favorite_tracks
        if is_fav: context_menu.add_command(label="💔 Usuń z Ulubionych", command=lambda p=actual_track_path: self._toggle_favorite(p))
        else: context_menu.add_command(label="♥ Dodaj do Ulubionych", command=lambda p=actual_track_path: self._toggle_favorite(p))
        
        other_playlists_exist = any(pl_name != self.active_playlist_name for pl_name in self.named_playlists.keys())
        if other_playlists_exist: # ... (logika Kopiuj do... bez zmian) ...
            copy_to_menu = tk.Menu(context_menu, tearoff=0, background="#2e2e2e", foreground="white")
            can_copy_to_any = False
            for pl_name in sorted(self.named_playlists.keys()):
                if pl_name != self.active_playlist_name:
                    target_playlist_entries = self.named_playlists.get(pl_name, [])
                    if not any(entry.get('path') == actual_track_path for entry in target_playlist_entries):
                        copy_to_menu.add_command(
                            label=pl_name,
                            command=lambda src_path=actual_track_path, dest_pl_name=pl_name: self._copy_track_to_playlist(src_path, dest_pl_name)
                        )
                        can_copy_to_any = True
                    else:
                        copy_to_menu.add_command(label=f"{pl_name} (już zawiera)", state=tk.DISABLED)
            if can_copy_to_any:
                context_menu.add_cascade(label="↪ Kopiuj do...", menu=copy_to_menu)
            else:
                context_menu.add_command(label="↪ Kopiuj do...", state=tk.DISABLED)

        context_menu.add_command(label="❌ Usuń z Playlisty", command=lambda p=actual_track_path: self._remove_track_from_playlist(p))
        context_menu.add_separator()
        context_menu.add_command(label="🖼️ Przypisz okładkę Focus...", 
                                 command=lambda entry=current_track_entry: self._assign_focus_cover_dialog(entry))
        if current_track_entry.get('focus_cover_path'):
            context_menu.add_command(label="🗑️ Usuń okładkę Focus",
                                     command=lambda entry=current_track_entry: self._remove_focus_cover(entry))
        context_menu.add_separator()
        context_menu.add_command(label="🌍 Pobierz okładkę (Last.fm)", 
                                 command=lambda entry=current_track_entry: self._start_lastfm_cover_fetch_thread(entry.copy(), force_update_focus_cover=False))
        
        # --- NOWE ZMIANY: Dodanie opcji Odśwież do menu kontekstowego DLA ELEMENTU ---
        if self.active_playlist_name == "Muzyka Wewnętrzna":
            context_menu.add_separator()
            context_menu.add_command(label="🔁 Odśwież Playlistę 'Muzyka Wewnętrzna'",
                                     command=self._refresh_internal_music_playlist)
        # --- KONIEC NOWYCH ZMIAN ---

        context_menu.post(event.x_root, event.y_root)

    # --- NOWA METODA ---
    def _remove_focus_cover(self, track_entry_to_modify: dict):
        """Usuwa przypisaną okładkę focus dla danego utworu (ustawia ją na None)."""
        if not track_entry_to_modify or 'path' not in track_entry_to_modify:
            logging.warning("_remove_focus_cover: Brak informacji o utworze (przekazano błędny entry).")
            messagebox.showerror("Błąd Wewnętrzny", "Brak danych utworu do modyfikacji okładki.", parent=self.parent_frame)
            return

        original_track_path = track_entry_to_modify.get('path')
        if not original_track_path: # Dodatkowe zabezpieczenie
            logging.warning("_remove_focus_cover: Przekazany wpis utworu nie ma klucza 'path'.")
            messagebox.showerror("Błąd Wewnętrzny", "Brak ścieżki dla modyfikowanego utworu.", parent=self.parent_frame)
            return
            
        track_display_name_cleaned = self._get_display_name_for_track(track_entry_to_modify).replace("♥ ", "").strip()

        # Sprawdź, czy faktycznie jest co usuwać w self.named_playlists (źródło prawdy)
        active_named_list = self.named_playlists.get(self.active_playlist_name)
        entry_in_named_playlist_to_update = None
        entry_index_in_named_playlist = -1

        if active_named_list:
            for i, entry_in_list in enumerate(active_named_list):
                if entry_in_list.get('path') == original_track_path:
                    entry_in_named_playlist_to_update = entry_in_list
                    entry_index_in_named_playlist = i
                    break
        
        if not entry_in_named_playlist_to_update:
            logging.error(f"_remove_focus_cover: Nie znaleziono utworu '{original_track_path}' w aktywnej nazwanej playliście '{self.active_playlist_name}'.")
            messagebox.showerror("Błąd Wewnętrzny", "Nie można znaleźć utworu na playliście, aby usunąć jego okładkę.", parent=self.parent_frame)
            return

        if not entry_in_named_playlist_to_update.get('focus_cover_path'):
            messagebox.showinfo("Informacja", f"Utwór '{track_display_name_cleaned}' nie ma aktualnie przypisanej niestandardowej okładki Focus.", parent=self.parent_frame)
            return
            
        # Usuń focus_cover_path z wpisu w self.named_playlists
        # --- ZMIANA: Usuń obie ścieżki okładek (focus i lastfm) ---
        self.named_playlists[self.active_playlist_name][entry_index_in_named_playlist]['focus_cover_path'] = None
        self.named_playlists[self.active_playlist_name][entry_index_in_named_playlist]['lastfm_cover_path'] = None # DODANE
        self._save_player_settings()
        logging.info(f"Usunięto focus_cover_path i lastfm_cover_path dla utworu '{original_track_path}'.")
        # --- KONIEC ZMIANY ---

        # Przeładuj self.playlist, aby odzwierciedlić zmianę w słowniku utworu
        current_playing_path_before_reload = None
        # Zapamiętaj ścieżkę utworu, który był na current_track_index, jeśli jakiś był
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_playing_path_before_reload = self.playlist[self.current_track_index].get('path')
        
        self._load_active_playlist() # To odbuduje self.playlist z zaktualizowanych named_playlists

        # Spróbuj przywrócić self.current_track_index na podstawie ścieżki,
        # preferując utwór, którego okładkę właśnie zmodyfikowano (original_track_path).
        new_current_track_index = -1
        
        # Najpierw sprawdź, czy modyfikowany utwór jest w nowej self.playlist
        for idx, entry_after_reload in enumerate(self.playlist):
            if entry_after_reload.get('path') == original_track_path:
                new_current_track_index = idx
                break
        
        # Jeśli nie znaleziono modyfikowanego (nie powinno się zdarzyć, jeśli nie usuwamy całego utworu),
        # spróbuj znaleźć ten, który grał przed przeładowaniem.
        if new_current_track_index == -1 and current_playing_path_before_reload:
            for idx, entry_after_reload in enumerate(self.playlist):
                if entry_after_reload.get('path') == current_playing_path_before_reload:
                    new_current_track_index = idx
                    break
        
        # Jeśli nadal -1, a playlista nie jest pusta, ustaw na pierwszy.
        if new_current_track_index == -1 and self.playlist:
            new_current_track_index = 0
            
        self.current_track_index = new_current_track_index
        logging.debug(f"_remove_focus_cover: Po przeładowaniu i re-indeksacji, self.current_track_index = {self.current_track_index}")
        
        # Zawsze odświeżaj etykiety i okładkę focus, bo stan się zmienił
        self._update_now_playing_label() # To wywoła _update_focus_cover_label, jeśli focus view jest aktywny

        # Odśwież Listbox na wypadek, gdyby coś w _get_display_name_for_track zależało od focus_cover_path
        # (chociaż obecnie tak nie jest, ale dla bezpieczeństwa)
        self._update_playlist_display() 
        # Dodatkowo, jeśli widok kafelkowy jest aktywny, odśwież go
        if self.music_library_view_mode.get() == "tiles":
            self._update_music_tiles_display() # Odśwież kafelki        
        messagebox.showinfo("Okładka Usunięta", 
                            f"Niestandardowa okładka dla widoku 'Teraz Odtwarzane' utworu:\n'{track_display_name_cleaned}'\nzostała usunięta (powrót do domyślnej/placeholdera).",
                            parent=self.parent_frame)

    # --- NOWA METODA: Wywoływana z menu kontekstowego ---
    def _assign_focus_cover_dialog(self, track_entry_to_modify: dict):
        """Otwiera dialog wyboru pliku obrazu i przypisuje go jako okładkę focus dla danego utworu."""
        if not track_entry_to_modify or 'path' not in track_entry_to_modify:
            messagebox.showerror("Błąd", "Nie można przypisać okładki, brak informacji o utworze.", parent=self.parent_frame)
            return

        original_track_path = track_entry_to_modify.get('path')
        # Użyj nazwy wyświetlanej utworu (bez serduszka) w tytule dialogu
        track_display_name_cleaned = self._get_display_name_for_track(track_entry_to_modify).replace("♥ ", "").strip()

        new_cover_path = filedialog.askopenfilename(
            title=f"Wybierz okładkę Focus dla: {track_display_name_cleaned}",
            filetypes=[("Obrazy", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("Wszystkie pliki", "*.*")],
            parent=self.parent_frame
        )

        if new_cover_path and os.path.exists(new_cover_path):
            active_named_list = self.named_playlists.get(self.active_playlist_name)
            if active_named_list:
                found_and_updated = False
                original_track_path = track_entry_to_modify.get('path')

                for i, entry_in_named_list in enumerate(active_named_list):
                    if entry_in_named_list.get('path') == original_track_path:
                        # przypisujemy nową ścieżkę okładki
                        self.named_playlists[self.active_playlist_name][i]['focus_cover_path'] = new_cover_path
                        found_and_updated = True
                        break

                if found_and_updated:
                    # 1) zapisujemy ustawienia
                    self._save_player_settings()

                    # 2) przeładowujemy playlistę (self.playlist zawiera teraz zaktualizowane słowniki)
                    current_playing_path_before_reload = None
                    if 0 <= self.current_track_index < len(self.playlist):
                        current_playing_path_before_reload = self.playlist[self.current_track_index].get('path')
                    self._load_active_playlist()

                    # 3) przywracamy indeks bieżącego utworu
                    if current_playing_path_before_reload:
                        for idx, entry in enumerate(self.playlist):
                            if entry.get('path') == current_playing_path_before_reload:
                                self.current_track_index = idx
                                break

                    # ——— tutaj dodajemy ODŚWIEŻANIE WIDOKÓW ———
                    # zawsze odśwież listę (synchronizacja currently_displayed_paths)
                    self._update_playlist_display()
                    # jeśli jesteśmy w trybie „kafelki”, to je przerysuj
                    if self.music_library_view_mode.get() == "tiles":
                        self._update_music_tiles_display()

                    # 4) komunikat dla użytkownika
                    messagebox.showinfo(
                        "Okładka Ustawiona",
                        f"Ustawiono okładkę dla widoku 'Teraz Odtwarzane' dla:\n{track_display_name_cleaned}",
                        parent=self.parent_frame
                    )
                else:
                    logging.error(f"Nie można było znaleźć wpisu dla '{original_track_path}' w aktywnej playliście, aby ustawić okładkę focus.")
        elif new_cover_path: # Ścieżka wybrana, ale plik nie istnieje
             messagebox.showerror("Błąd Pliku", f"Wybrany plik okładki nie istnieje:\n{new_cover_path}", parent=self.parent_frame)

    # --- NOWA METODA ---
    def _copy_track_to_playlist(self, source_track_path: str, destination_playlist_name: str):
        """Kopiuje (dodaje) utwór do wskazanej nazwanej playlisty."""
        if not source_track_path or not destination_playlist_name:
            logging.warning("Brak ścieżki źródłowej lub nazwy playlisty docelowej do skopiowania.")
            return

        if destination_playlist_name not in self.named_playlists:
            messagebox.showerror("Błąd", f"Playlista docelowa '{destination_playlist_name}' nie istnieje.", parent=self.parent_frame)
            return

        # Używamy `setdefault` na wypadek, gdyby klucz istniał, ale wartość była None (mało prawdopodobne)
        target_playlist_tracks = self.named_playlists.setdefault(destination_playlist_name, [])

        if source_track_path not in target_playlist_tracks:
            target_playlist_tracks.append(source_track_path)
            self._save_player_settings() # Zapisz zmiany w local_settings (bo self.named_playlists się zmieniło)
            
            # Przygotuj nazwę utworu do komunikatu (bez serduszka i rozszerzenia)
            display_name_no_fav_no_ext = os.path.splitext(os.path.basename(source_track_path))[0]
            messagebox.showinfo("Skopiowano Utwór", f"Utwór '{display_name_no_fav_no_ext}' został skopiowany do playlisty '{destination_playlist_name}'.", parent=self.parent_frame)
            logging.info(f"Skopiowano '{source_track_path}' do playlisty '{destination_playlist_name}'.")

            # Jeśli aktywna playlista to playlista docelowa, odśwież jej widok
            if self.active_playlist_name == destination_playlist_name:
                # Nie ma potrzeby _load_active_playlist(), bo modyfikowaliśmy bezpośrednio
                # listę w self.named_playlists, a _load_active_playlist wczytuje Z TEGO miejsca.
                # self.playlist i self.original_playlist_order dla aktywnej playlisty
                # MUSZĄ zostać zaktualizowane, jeśli dodajemy do aktywnej.
                self._load_active_playlist() # To zapewni, że self.playlist jest aktualna
                self._update_playlist_display()
        else:
            display_name_no_fav_no_ext = os.path.splitext(os.path.basename(source_track_path))[0]
            messagebox.showinfo("Utwór Już Istnieje", f"Utwór '{display_name_no_fav_no_ext}' już znajduje się na playliście '{destination_playlist_name}'.", parent=self.parent_frame)
    # --- KONIEC NOWEJ METODY ---


    # --- NOWA METODA ---
    def _delete_active_playlist_dialog(self):
        """Wyświetla dialog potwierdzenia i usuwa aktywną nazwaną playlistę."""
        active_name = self.active_playlist_name
        if not active_name:
            messagebox.showerror("Błąd", "Brak aktywnej playlisty do usunięcia.", parent=self.parent_frame)
            return

        # Zabezpieczenie: Nie pozwalaj na usunięcie, jeśli to jedyna playlista
        if len(self.named_playlists) <= 1:
            messagebox.showwarning("Ostrzeżenie", f"Nie można usunąć ostatniej playlisty ('{active_name}').", parent=self.parent_frame)
            return
        
        if messagebox.askyesno("Potwierdź Usunięcie Playlisty", f"Czy na pewno chcesz usunąć playlistę '{active_name}'?\nOperacja jest nieodwracalna.", parent=self.parent_frame):
            self._delete_active_playlist(active_name)
    # --- KONIEC NOWEJ METODY ---

    # --- NOWA METODA ---
    def _delete_active_playlist(self, playlist_name_to_delete: str): # Ta metoda może pozostać bez zmian
        """Logika usuwania playlisty (bezpośrednio wywoływana po potwierdzeniu)."""
        # --- UPEWNIJ SIĘ, ŻE TA METODA NIE JEST JUŻ WOŁANA BEZPOŚREDNIO Z MENU KONTEKSTOWEGO, 
        # TYLKO PRZEZ _delete_active_playlist_dialog ---

        if playlist_name_to_delete in self.named_playlists:
            # Dodatkowe zabezpieczenie w samej logice usuwania
            if playlist_name_to_delete in self.permanent_playlists:
                logging.warning(f"Próba usunięcia permanentnej playlisty '{playlist_name_to_delete}' przez _delete_active_playlist. Pomijanie.")
                # Powrót do Głównej Kolejki, jeśli jakimś cudem to nie ona była usuwana
                self.active_playlist_name = "Główna Kolejka"
                self._load_active_playlist()
                self._update_available_playlists_ui()
                self._update_playlist_display()
                self._update_delete_playlist_button_state()
                return

            del self.named_playlists[playlist_name_to_delete]
            logging.info(f"Usunięto playlistę: '{playlist_name_to_delete}'")

            if self.active_playlist_name == playlist_name_to_delete:
                self._stop_music()
                self.current_track_index = -1

            # Wybierz nową aktywną playlistę - priorytet dla "Główna Kolejka"
            if "Główna Kolejka" in self.named_playlists:
                self.active_playlist_name = "Główna Kolejka"
            elif "Muzyka Wewnętrzna" in self.named_playlists: # Drugi priorytet
                self.active_playlist_name = "Muzyka Wewnętrzna"
            elif self.named_playlists: # Jakakolwiek inna, jeśli istnieją
                self.active_playlist_name = next(iter(self.named_playlists.keys()))
            else: 
                # To nie powinno się zdarzyć, jeśli permanentne są zawsze.
                # Ale na wszelki wypadek, stwórzmy je ponownie.
                self.active_playlist_name = "Główna Kolejka"
                self.named_playlists[self.active_playlist_name] = []
                if "Muzyka Wewnętrzna" not in self.named_playlists:
                    self.named_playlists["Muzyka Wewnętrzna"] = []
                logging.error("Wszystkie playlisty (nawet permanentne) zostały usunięte! Odtworzono domyślne.")

            self._load_active_playlist()
            self._update_available_playlists_ui() 
            self._update_playlist_display()   

            # Zaktualizuj etykietę "teraz odtwarzane"
            if self.playlist:
                self.current_track_index = 0
                self._update_now_playing_label()
            else:
                self._update_now_playing_label(track_name_override="Nic nie gra")

            self._save_player_settings()
            # Zaktualizuj przycisk usuwania (może być nieaktywny, jeśli została tylko jedna playlista)
            self._update_delete_playlist_button_state()
            self._apply_music_content_view() # Upewnij się, że widok jest poprawny (lista/kafelki)
            
            messagebox.showinfo("Playlista Usunięta", f"Playlista '{playlist_name_to_delete}' została usunięta.", parent=self.parent_frame)

        else:
            messagebox.showerror("Błąd", f"Nie znaleziono playlisty '{playlist_name_to_delete}' do usunięcia.", parent=self.parent_frame)
            logging.warning(f"Próba usunięcia nieistniejącej playlisty: {playlist_name_to_delete}")
        # Odświeżenie widoku kafelków, jeśli aktywny
        if self.music_library_view_mode.get() == "tiles":
            self._update_music_tiles_display()
    # --- KONIEC NOWEJ METODY ---

    # --- NOWA METODA: Aktualizacja stanu przycisku "Usuń Playlistę" ---
    def _update_delete_playlist_button_state(self):
        """Aktualizuje stan przycisku usuwania playlisty."""
        if hasattr(self, 'delete_playlist_button') and self.delete_playlist_button.winfo_exists():
            # --- NOWE ZMIANY: Sprawdź, czy aktywna playlista jest permanentna ---
            can_delete = True
            if self.active_playlist_name in self.permanent_playlists: # self.permanent_playlists zdefiniowane w __init__
                can_delete = False
            elif len(self.named_playlists) <= len(self.permanent_playlists): # Jeśli zostały tylko permanentne
                 # Pozwól usunąć nie-permanentną, jeśli jest więcej niż len(self.permanent_playlists)
                 # W praktyce, jeśli mamy tylko "Główną" i "Wewnętrzną", nie możemy usunąć żadnej z nich,
                 # chyba że logika jest bardziej skomplikowana (np. pozwalamy usunąć Główną, jeśli jest pusta,
                 # a są inne, w tym Wewnętrzna). Na razie proste: nie można usunąć, jeśli jest w permanent_playlists.
                 pass # can_delete pozostaje True, ale logika poniżej to zweryfikuje dokładniej
            
            # Dodatkowe sprawdzenie: jeśli to ostatnia *jakakolwiek* playlista (nie powinno się zdarzyć
            # jeśli permanentne zawsze istnieją, ale dla bezpieczeństwa)
            if len(self.named_playlists) <= 1:
                 can_delete = False

            self.delete_playlist_button.config(state=tk.NORMAL if can_delete else tk.DISABLED)
            # --- KONIEC NOWYCH ZMIAN ---

    # --- NOWA METODA (Placeholder, wywoływana z menu kontekstowego dla pustego miejsca) ---
    def _delete_active_playlist_dialog(self):
        """Wyświetla dialog potwierdzenia i usuwa aktywną nazwaną playlistę."""
        active_name = self.active_playlist_name
        if not active_name: # ... (bez zmian) ...
            messagebox.showerror("Błąd", "Brak aktywnej playlisty do usunięcia.", parent=self.parent_frame)
            return

        # --- NOWE ZMIANY: Sprawdzenie permanentnych playlist ---
        if active_name in self.permanent_playlists:
            messagebox.showwarning("Niedozwolone", f"Nie można usunąć predefiniowanej playlisty '{active_name}'.", parent=self.parent_frame)
            return
        # Usunięto stare zabezpieczenie "nie można usunąć ostatniej", bo permanentne to obsłużą
        # --- KONIEC NOWYCH ZMIAN ---
        
        if messagebox.askyesno("Potwierdź Usunięcie Playlisty", f"Czy na pewno chcesz usunąć playlistę '{active_name}'?\nOperacja jest nieodwracalna.", parent=self.parent_frame):
            self._delete_active_playlist(active_name) # Wywołaj istniejącą logikę usuwania



    # --- NOWA METODA ---
    def _toggle_favorite(self, track_path_to_toggle: str): # Argument to nadal ścieżka
        """Dodaje lub usuwa utwór (na podstawie ścieżki) z listy ulubionych."""
        if not track_path_to_toggle: return # Nic nie rób, jeśli ścieżka jest pusta

        if track_path_to_toggle in self.favorite_tracks:
            self.favorite_tracks.remove(track_path_to_toggle)
            logging.info(f"Usunięto z ulubionych: {os.path.basename(track_path_to_toggle)}")
        else:
            self.favorite_tracks.add(track_path_to_toggle)
            logging.info(f"Dodano do ulubionych: {os.path.basename(track_path_to_toggle)}")

        self.local_settings["music_favorite_tracks"] = list(self.favorite_tracks)
        self._save_player_settings()
        
        self._update_playlist_display()
        self._update_fav_button_text() # Ta metoda też musi używać ścieżki do sprawdzenia



    def _remove_track_from_playlist(self, track_path_to_remove: str):
        """Usuwa utwór (na podstawie ścieżki) z aktywnej nazwanej playlisty.
        Jeśli to playlista "Muzyka Wewnętrzna" i utwór jest wewnętrzny, usuwa też plik muzyczny z dysku.
        Dodatkowo, usuwa powiązane, zarządzane przez launcher okładki Focus i LastFM, jeśli utwór jest
        usuwany z ostatniej playlisty, na której występuje LUB jeśli plik muzyczny jest fizycznie usuwany."""
        if not track_path_to_remove:
            logging.warning("Próba usunięcia pustej ścieżki z playlisty.")
            return

        active_named_list = self.named_playlists.get(self.active_playlist_name)
        if not active_named_list:
            logging.warning(f"_remove_track_from_playlist: Aktywna playlista '{self.active_playlist_name}' nie istnieje lub jest pusta.")
            return

        removed_from_current_playlist_successfully = False
        was_currently_playing = False
        current_playing_path_if_any = None
        track_entry_being_removed_from_current_playlist = None 

        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_playing_entry = self.playlist[self.current_track_index]
            if current_playing_entry.get('path') == track_path_to_remove:
                was_currently_playing = True
                track_entry_being_removed_from_current_playlist = current_playing_entry.copy() 
            current_playing_path_if_any = current_playing_entry.get('path')
        
        if not track_entry_being_removed_from_current_playlist:
            for entry in active_named_list:
                if entry.get('path') == track_path_to_remove:
                    track_entry_being_removed_from_current_playlist = entry.copy()
                    break
        
        # Jeśli nie znaleziono wpisu na aktywnej playliście (nie powinno się zdarzyć, jeśli menu kontekstowe działa na aktywnej)
        if not track_entry_being_removed_from_current_playlist:
            logging.warning(f"Nie znaleziono utworu '{track_path_to_remove}' na aktywnej playliście '{self.active_playlist_name}' do usunięcia wpisu.")
            self._update_playlist_display()
            return

        original_len = len(active_named_list)
        self.named_playlists[self.active_playlist_name] = [
            entry for entry in active_named_list if entry.get('path') != track_path_to_remove
        ]
        if len(self.named_playlists[self.active_playlist_name]) < original_len:
            removed_from_current_playlist_successfully = True
            logging.info(f"Usunięto wpis dla '{os.path.basename(track_path_to_remove)}' z nazwanej playlisty '{self.active_playlist_name}'.")

            # Sprawdź, czy ten utwór (ta sama ścieżka) istnieje jeszcze na JAKIEJKOLWIEK innej playliście
            is_on_other_playlist = False
            for pl_name, entries in self.named_playlists.items():
                if pl_name != self.active_playlist_name: # Nie sprawdzaj ponownie aktywnej, z której właśnie usunęliśmy
                    if any(entry.get('path') == track_path_to_remove for entry in entries):
                        is_on_other_playlist = True
                        logging.debug(f"Utwór '{track_path_to_remove}' wciąż istnieje na playliście '{pl_name}'. Okładki nie będą usuwane na razie.")
                        break
            
            physical_file_deleted = False
            # Fizyczne usuwanie pliku muzycznego (TYLKO dla wewnętrznej playlisty)
            if self.active_playlist_name == "Muzyka Wewnętrzna" and \
               track_entry_being_removed_from_current_playlist.get('is_internal') is True:
                
                physical_path_to_delete_music = track_entry_being_removed_from_current_playlist.get('path')
                if physical_path_to_delete_music and os.path.exists(physical_path_to_delete_music) and \
                   os.path.abspath(physical_path_to_delete_music).startswith(os.path.abspath(INTERNAL_MUSIC_DIR)):
                    confirm_delete_file = messagebox.askyesno(
                        "Usuń Plik Fizycznie",
                        f"Czy chcesz również fizycznie usunąć plik muzyczny:\n{os.path.basename(physical_path_to_delete_music)}\n"
                        f"z folderu wewnętrznej biblioteki?\n\nŚcieżka: {physical_path_to_delete_music}\n\n"
                        "Tej operacji NIE MOŻNA cofnąć!",
                        parent=self.parent_frame, icon='warning'
                    )
                    if confirm_delete_file:
                        try:
                            os.remove(physical_path_to_delete_music)
                            logging.info(f"Fizycznie usunięto plik z wewnętrznej biblioteki: {physical_path_to_delete_music}")
                            physical_file_deleted = True # Ustaw flagę, że plik fizycznie usunięto
                        except OSError as e:
                            logging.error(f"Nie udało się fizycznie usunąć pliku '{physical_path_to_delete_music}': {e}")
                            # Informujemy, ale kontynuujemy usuwanie wpisów z playlisty
            
            # --- NOWE ZMIANY: Usuwanie okładek, jeśli plik muzyczny został fizycznie usunięty LUB jeśli nie ma go już na żadnej playliście ---
            if physical_file_deleted or not is_on_other_playlist:
                logging.info(f"Rozpoczynanie usuwania powiązanych okładek dla '{track_path_to_remove}' (plik usunięty: {physical_file_deleted}, nie na innych playlistach: {not is_on_other_playlist})")
                
                focus_cover_to_delete = track_entry_being_removed_from_current_playlist.get('focus_cover_path')
                lastfm_cover_to_delete = track_entry_being_removed_from_current_playlist.get('lastfm_cover_path')
                abs_images_music_covers_dir = os.path.abspath(os.path.join(IMAGES_FOLDER, "music_covers"))

                if focus_cover_to_delete and os.path.exists(focus_cover_to_delete) and \
                   os.path.abspath(focus_cover_to_delete).startswith(abs_images_music_covers_dir):
                    try:
                        os.remove(focus_cover_to_delete)
                        logging.info(f"Usunięto powiązaną okładkę Focus: {focus_cover_to_delete}")
                    except OSError as e_fc:
                        logging.error(f"Błąd usuwania okładki Focus '{focus_cover_to_delete}': {e_fc}")
                
                if lastfm_cover_to_delete and os.path.exists(lastfm_cover_to_delete) and \
                   os.path.abspath(lastfm_cover_to_delete).startswith(abs_images_music_covers_dir):
                    try:
                        os.remove(lastfm_cover_to_delete)
                        logging.info(f"Usunięto powiązaną okładkę LastFM: {lastfm_cover_to_delete}")
                    except OSError as e_lfm:
                        logging.error(f"Błąd usuwania okładki LastFM '{lastfm_cover_to_delete}': {e_lfm}")
                
                # Po usunięciu okładek, usuń również ścieżki do nich z WSZYSTKICH pozostałych playlist,
                # na których ten utwór MÓGŁBY jeszcze być (na wypadek niespójności, choć `is_on_other_playlist` powinno być False).
                # To jest dodatkowe zabezpieczenie.
                if not is_on_other_playlist or physical_file_deleted: # Tylko jeśli to była ostatnia instancja LUB plik muzyczny usunięto
                    for pl_name_iter, entries_iter in self.named_playlists.items():
                        for entry_iter in entries_iter:
                            if entry_iter.get('path') == track_path_to_remove: # Znajdź ten sam utwór na innych playlistach
                                entry_iter['focus_cover_path'] = None
                                entry_iter['lastfm_cover_path'] = None
                    logging.debug(f"Wyczyszczono ścieżki okładek dla '{track_path_to_remove}' na wszystkich playlistach, bo był ostatnią instancją lub plik został usunięty.")
            # --- KONIEC NOWYCH ZMIAN DLA OKŁADEK ---

        else:
            logging.warning(f"Nie znaleziono '{os.path.basename(track_path_to_remove)}' w nazwanej playliście '{self.active_playlist_name}' do usunięcia.")
            self._update_playlist_display() # Na wszelki wypadek odśwież
            return

        # Jeśli coś usunięto, przeładuj self.playlist i self.original_playlist_order
        self._load_active_playlist() 

        if was_currently_playing:
            self._stop_music() # Zatrzymaj i zresetuj current_track_index
            # Spróbuj odtworzyć następny, jeśli autoplay jest włączone i coś zostało
            if self.autoplay and self.playlist:
                next_idx_after_removal = self._get_next_track_index_for_auto_advance() # Ta metoda powinna być ok
                if next_idx_after_removal != -1:
                    self.parent_frame.after(100, lambda idx=next_idx_after_removal: self._play_track(idx))
            # Jeśli nie autoplay, current_track_index pozostanie -1 (po stopie) lub zostanie ustawiony na 0 poniżej
        else:
            # Jeśli usunięto inny utwór niż odtwarzany, spróbuj utrzymać odtwarzanie/zaznaczenie
            if current_playing_path_if_any and self.playlist: # Czy coś grało i czy playlista nie jest pusta
                self.current_track_index = -1 # Zresetuj
                for i, entry in enumerate(self.playlist):
                    if entry.get('path') == current_playing_path_if_any:
                        self.current_track_index = i
                        break
                if self.current_track_index == -1 and self.playlist: # Jeśli nie znaleziono, ustaw na pierwszy
                    self.current_track_index = 0
            elif self.playlist: # Jeśli nic nie grało, a są utwory, ustaw na pierwszy
                 self.current_track_index = 0
            else: # Playlista pusta
                 self.current_track_index = -1

        self._update_playlist_display()
        self._update_now_playing_label() # Zaktualizuj etykiety

        # Zaktualizuj zaznaczenie w Listboxie, jeśli coś jest na playliście
        if self.current_track_index != -1 and self.playlist_listbox.size() > 0:
            if self.current_track_index < self.playlist_listbox.size(): # Upewnij się, że indeks jest w zakresie widoku
                 entry_to_select_in_view = self.playlist[self.current_track_index] # To jest słownik
                 if entry_to_select_in_view in self.currently_displayed_paths:
                     try:
                         idx_in_view = self.currently_displayed_paths.index(entry_to_select_in_view)
                         self.playlist_listbox.selection_clear(0, tk.END)
                         self.playlist_listbox.selection_set(idx_in_view)
                         self.playlist_listbox.activate(idx_in_view)
                     except (ValueError, tk.TclError): pass


        self._save_player_settings()
        # --- NOWA ZMIANA: Odśwież widok kafelków, jeśli jest aktywny ---
        if self.music_library_view_mode.get() == "tiles":
            logging.debug("_remove_track_from_playlist: Wykryto widok kafelkowy, odświeżanie kafelków.")
            self._update_music_tiles_display()
        # --- KONIEC NOWEJ ZMIANY ---

    def _begin_seek(self, event):
        """Użytkownik zaczął ciągnąć suwak – wstrzymaj automatyczny update."""
        self._seeking = True           # flaga własna
        # nie kasujemy after() – za chwilę znów będzie potrzebny

    # W MusicPlayerPage
    def _toggle_autoplay(self):
        self.autoplay = not self.autoplay
        self._update_autoplay_button_text()
        self._save_player_settings()
        logging.info(f"Tryb Auto-play zmieniony na: {self.autoplay}")
        if hasattr(self.launcher, '_update_discord_status'):
            # --- ZMIANA ---
            # Jeśli nic nie gra, a jesteśmy na stronie muzyki, odśwież status "Przegląda Muzykę"
            # W przeciwnym razie, jeśli coś gra, status zaktualizuje się przy następnym utworze/stopie.
            # Jeśli nie gra, a jesteśmy na innej stronie, Discord i tak pokaże tę stronę.
            if not self.is_playing and self.launcher.current_frame == self.launcher.music_page_frame:
                self.launcher._update_discord_status(status_type="browsing", activity_details=self.launcher.current_section)
            # --- KONIEC ZMIANY ---

    def _end_seek(self, event):
        """Użytkownik puścił suwak – przewiń muzykę i wznów timer."""
        self._seeking = False
        new_pos = float(self.progress_scale_var.get())
        self._seek_to_position(new_pos)

    # Przykład dla _seek_to_position:
    def _seek_to_position(self, new_pos_sec: float):
        if (not pygame.mixer.get_init() or not self.is_playing or self.current_track_index == -1 or
                self.current_track_index >= len(self.playlist)): # Dodatkowe sprawdzenie zakresu
            return

        was_paused = self.is_paused
        # --- ZMIANA: Pobierz ścieżkę ze słownika ---
        track_entry = self.playlist[self.current_track_index]
        track_path = track_entry.get('path')
        if not track_path:
            logging.error("Błąd przewijania: brak ścieżki dla aktualnego utworu.")
            return
        # --- KONIEC ZMIANY ---

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(track_path) # Użyj pobranej ścieżki
            pygame.mixer.music.play(start=new_pos_sec)
            self._start_time = time.monotonic() - new_pos_sec
            self._pause_acc = 0.0
            if was_paused:
                pygame.mixer.music.pause()
            else:
                self.is_paused = False
                if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
                    self.play_pause_button.config(text="❚❚")

            self._update_now_playing_label(
                duration_sec=getattr(self, '_current_track_duration_sec', 0), # Użyj getattr dla bezpieczeństwa
                current_pos_sec=new_pos_sec
            )
            if hasattr(self, 'progress_scale_var'): self.progress_scale_var.set(new_pos_sec)
            self.parent_frame.after(150, self._update_track_progress)
        except pygame.error as e:
            logging.error(f"Nie udało się przewinąć pliku '{track_path}': {e}")

    # --- NOWA METODA ---
    def _get_track_length(self, path: str) -> float:
        """Zwraca długość utworu w sekundach albo 0.0, jeśli nieznana."""
        try:
            audio = MutagenFile(path) # Obsługuje różne typy plików, w tym MP3, FLAC, M4A, OGG, WAV
            if audio and audio.info and audio.info.length:
                logging.debug(f"Mutagen - Długość dla '{os.path.basename(path)}': {audio.info.length:.2f}s")
                return float(audio.info.length)
        except Exception as e:
            logging.warning(f"Mutagen nie odczytał długości dla '{os.path.basename(path)}': {e}")

        # Fallback na pygame.mixer.Sound (głównie dla WAV/krótkich OGG)
        try:
            sound = pygame.mixer.Sound(path)
            length = sound.get_length()
            logging.debug(f"Pygame.mixer.Sound - Długość dla '{os.path.basename(path)}': {length:.2f}s")
            return length
        except pygame.error as e_pygame:
            logging.warning(f"Pygame.mixer.Sound nie odczytał długości dla '{os.path.basename(path)}': {e_pygame}")

        return 0.0 # Zwróć 0.0, jeśli nie udało się odczytać
    # --- KONIEC NOWEJ METODY ---

    # --- NOWA METODA ---
    def _seek_relative(self, seconds_offset: int):
        """Przewija utwór o zadaną liczbę sekund do przodu (+) lub do tyłu (-)."""
        if not pygame.mixer.get_init() or not self.is_playing or self.current_track_index == -1:
            # Dodajmy informację, jeśli użytkownik próbuje przewinąć, gdy nic nie gra
            if not self.is_playing and self.playlist: # Jeśli jest playlista, ale nic nie gra
                messagebox.showinfo("Informacja", "Najpierw uruchom odtwarzanie, aby móc przewijać.", parent=self.parent_frame)
            return

        # --- ZMIANA: Użyj getattr dla _start_time_monotonic ---
        # Użyj czasu startu bieżącego utworu, a jeśli nie ma, użyj aktualnego czasu jako fallback
        # (chociaż jeśli is_playing jest True, _start_time_monotonic powinno być ustawione)
        start_time_mono = getattr(self, '_start_time', time.monotonic())
        pause_acc       = getattr(self, '_pause_acc', 0.0)
        current_pos_sec = time.monotonic() - start_time_mono - pause_acc
        current_pos_sec = max(0, current_pos_sec)
        # --- KONIEC ZMIANY ---

        new_position_sec = current_pos_sec + seconds_offset
        track_duration = getattr(self, '_current_track_duration_sec', 0)

        if track_duration > 0:
            new_position_sec = max(0, min(new_position_sec, track_duration - 0.1))
        else:
            if seconds_offset > 0:
                logging.warning("Nie można przewinąć do przodu utworu o nieznanej długości.")
                return
            new_position_sec = max(0, new_position_sec)

        logging.debug(f"Próba przewinięcia z {current_pos_sec:.2f}s do {new_position_sec:.2f}s (offset: {seconds_offset}s)")
        self._seek_to_position(new_position_sec)
    # --- KONIEC NOWEJ METODY ---

    # --- Placeholdery dla metod ---
    def _add_music_folder(self, *, import_to_internal: bool = False):
        if not pygame.mixer.get_init(): # ... (reszta bez zmian) ...
            messagebox.showerror("Błąd Mixera", "Moduł audio nie jest zainicjalizowany.", parent=self.parent_frame)
            return

        initial_dir = self.local_settings.get("last_music_folder", os.path.expanduser("~"))
        folder_path = filedialog.askdirectory(
            title=f"Wybierz folder z muzyką {'do importu wewnętrznego' if import_to_internal else ''}",
            initialdir=initial_dir,
            parent=self.parent_frame
        )

        if folder_path:
            self.local_settings["last_music_folder"] = folder_path
            
            # --- NOWE ZMIANY: Wybór docelowej playlisty ---
            target_playlist_name = "Muzyka Wewnętrzna" if import_to_internal else "Główna Kolejka"
            
            if target_playlist_name not in self.named_playlists:
                logging.error(f"Docelowa playlista '{target_playlist_name}' nie istnieje!")
                messagebox.showerror("Błąd Wewnętrzny", f"Playlista '{target_playlist_name}' nie została znaleziona.", parent=self.parent_frame)
                return

            active_playlist_tracks = self.named_playlists.get(target_playlist_name, [])
            # --- KONIEC NOWYCH ZMIAN ---
            
            added_count = 0
            skipped_due_to_error_count = 0
            supported_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
            
            files_to_process_list = [f for f in os.listdir(folder_path) if f.lower().endswith(supported_extensions)]
            total_files_in_folder = len(files_to_process_list)
            
            if total_files_in_folder == 0: # ... (bez zmian) ...
                messagebox.showinfo("Informacja", "Wybrany folder nie zawiera obsługiwanych plików muzycznych.", parent=self.parent_frame)
                return

            operation_label = (
                'Importowanie do "Muzyka Wewnętrzna"'
                if import_to_internal
                else 'Dodawanie do "Główna Kolejka"'
            )
            operation_title = f"{operation_label}: {os.path.basename(folder_path)}"
            self.launcher.show_progress_window(operation_title)
            if not (hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists()): # ... (bez zmian) ...
                logging.error("Nie udało się utworzyć okna postępu w GameLauncher.")
                return
            
            self.launcher.progress_bar['maximum'] = total_files_in_folder
            self.launcher.progress_bar['value'] = 0
            self.launcher.progress_bar['mode'] = 'determinate'
            self.launcher.progress_label.config(text="Przygotowywanie...")

            def process_folder_thread():
                nonlocal added_count, skipped_due_to_error_count 

                for idx, filename in enumerate(files_to_process_list):
                    # ... (aktualizacja UI paska postępu bez zmian) ...
                    progress_text_ui = f"Plik {idx+1}/{total_files_in_folder}: {filename}"
                    if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                        self.launcher.root.after(0, lambda prog_txt=progress_text_ui, val=idx : (
                            setattr(self.launcher.progress_bar, 'value', val),
                            self.launcher.progress_label.config(text=prog_txt)
                        ))
                    else: 
                        logging.info("Okno postępu zamknięte, przerywanie importu folderu.")
                        break

                    src_full_path = os.path.join(folder_path, filename)
                    path_to_add_to_playlist = None
                    is_internal_flag = False

                    if import_to_internal:
                        path_to_add_to_playlist = self._copy_into_internal_library(src_full_path)
                        if path_to_add_to_playlist: 
                            is_internal_flag = True
                        else: 
                            skipped_due_to_error_count +=1
                            continue 
                    else:
                        path_to_add_to_playlist = os.path.abspath(src_full_path)
                        is_internal_flag = False # Dla "Głównej Kolejki" domyślnie zewnętrzne
                    
                    if path_to_add_to_playlist:
                        if not any(entry.get('path') == path_to_add_to_playlist for entry in active_playlist_tracks):
                            active_playlist_tracks.append({
                                "path": path_to_add_to_playlist,
                                "focus_cover_path": None, 
                                "lastfm_cover_path": None,
                                "is_internal": is_internal_flag # WAŻNE: Ustawienie flagi
                            })
                            added_count += 1
                
                if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                     self.launcher.root.after(100, self.launcher.progress_window.destroy)
                
                # --- NOWA ZMIANA: Przekazanie target_playlist_name do finalizacji ---
                self.launcher.root.after(150, self._finalize_add_operation, added_count, skipped_due_to_error_count, import_to_internal, target_playlist_name, "folder")
            
            threading.Thread(target=process_folder_thread, daemon=True).start()
        else: 
            logging.debug("Anulowano wybór folderu z muzyką.")

    def _finalize_folder_import(self, added_count, skipped_count, was_internal_import):
        """Metoda pomocnicza wywoływana po zakończeniu wątku importu folderu."""
        if added_count > 0:
            action_verb = "Zaimportowano" if was_internal_import else "Dodano"
            logging.info(f"{action_verb} {added_count} utworów do playlisty '{self.active_playlist_name}'.")
            # Named_playlists już powinno być zaktualizowane w wątku (jeśli active_playlist_tracks było referencją)
            # Ale dla pewności, jeśli active_playlist_tracks było kopią:
            # self.named_playlists[self.active_playlist_name] = active_playlist_tracks_z_watku 
            
            self._load_active_playlist()    
            self._update_playlist_display() 
            if self.music_library_view_mode.get() == "tiles":
                self._update_music_tiles_display()

            if not self.is_playing and not self.is_paused and self.playlist and self.current_track_index == -1:
                self.current_track_index = 0
                self._update_now_playing_label()
                # Zaznacz w Listboxie (kod jak wcześniej)
            self._save_player_settings()
        
        msg_parts = []
        if added_count > 0: msg_parts.append(f"Dodano pomyślnie: {added_count} utworów.")
        if skipped_count > 0: msg_parts.append(f"Pominięto z powodu błędów: {skipped_count} utworów.")
        if not msg_parts: msg_parts.append("Nie znaleziono nowych plików muzycznych lub wszystkie już są na playliście.")
        
        messagebox.showinfo("Zakończono", "\n".join(msg_parts), parent=self.parent_frame)

    # --- NOWE METODY DLA POWTARZANIA ---
    def _toggle_repeat_mode(self):
        if self.repeat_mode == "none": self.repeat_mode = "one"
        elif self.repeat_mode == "one": self.repeat_mode = "all"
        else: self.repeat_mode = "none" # Wróć do "none"
        self._update_repeat_button_text()
        self._save_player_settings() # Zapisz zmianę
        logging.info(f"Tryb powtarzania zmieniony na: {self.repeat_mode}")

    def _update_repeat_button_text(self):
        if hasattr(self, 'repeat_button'):
            text = ""
            tooltip_text_base = "Tryb powtarzania: "
            # ... (logika ustalania text i tooltip_text_base) ...
            if self.repeat_mode == "one":
                text = "🔁¹ Jeden"
                tooltip_text_final = tooltip_text_base + "Jeden utwór"
            elif self.repeat_mode == "all":
                text = "🔁 Lista"
                tooltip_text_final = tooltip_text_base + "Cała playlista"
            else: # none
                text = "🔁 Brak"
                tooltip_text_final = tooltip_text_base + "Wyłączone"
            self.repeat_button.config(text=text)
            self._update_button_tooltip_with_delay_logic(self.repeat_button, tooltip_text_final)

    # --- NOWE METODY DLA LOSOWEGO ODTWARZANIA ---
    def _toggle_shuffle_mode(self):
        self.shuffle_mode = not self.shuffle_mode
        
        current_playing_path_before_toggle = None
        # --- NOWE ZMIANY: Zapamiętaj ścieżkę aktualnie odtwarzanego/zaznaczonego utworu ---
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_playing_path_before_toggle = self.playlist[self.current_track_index]
        elif self.playlist_listbox.curselection(): # Jeśli nic nie gra, ale coś jest zaznaczone
            try:
                selected_view_idx = self.playlist_listbox.curselection()[0]
                # Upewnij się, że pobieramy ścieżkę z currently_displayed_paths, jeśli jest filtrowane
                current_playing_path_before_toggle = self._get_actual_path_from_view_index(selected_view_idx)
            except IndexError:
                pass
        # --- KONIEC NOWYCH ZMIAN ---

        if self.shuffle_mode:
            # Zapamiętaj oryginalną kolejność, jeśli jeszcze nie zapamiętano
            # lub jeśli obecna `self.playlist` (po potencjalnym sortowaniu/przesuwaniu)
            # ma być nową bazą dla tasowania.
            # Najlepiej zawsze bazować na `self.named_playlists[self.active_playlist_name]` jako źródle oryginalnej kolejności.
            self._load_active_playlist() # To ustawi self.original_playlist_order i self.playlist na bazie named_playlists

            if self.playlist:
                # Przetasuj `self.playlist`
                random.shuffle(self.playlist)

                # Spróbuj umieścić zapamiętany utwór na początku (lub odnaleźć jego nową pozycję)
                if current_playing_path_before_toggle and current_playing_path_before_toggle in self.playlist:
                    self.playlist.remove(current_playing_path_before_toggle)
                    self.playlist.insert(0, current_playing_path_before_toggle)
                    self.current_track_index = 0
                elif self.playlist: # Jeśli nie było granego lub go nie ma, ustaw na pierwszy z przetasowanej
                    self.current_track_index = 0
                else: # Pusta playlista po shuffle
                    self.current_track_index = -1
        else: # Wyłączono shuffle, przywróć oryginalną kolejność
            self._load_active_playlist() # To przywróci self.playlist i self.original_playlist_order z named_playlist

            # Spróbuj znaleźć zapamiętany utwór w przywróconej liście
            if current_playing_path_before_toggle and current_playing_path_before_toggle in self.playlist:
                try:
                    self.current_track_index = self.playlist.index(current_playing_path_before_toggle)
                except ValueError: # Nie powinno się zdarzyć
                    self.current_track_index = 0 if self.playlist else -1
            elif self.playlist:
                self.current_track_index = 0 # Ustaw na pierwszy
            else:
                self.current_track_index = -1

        self._update_playlist_display() # Odśwież widok playlisty
        self._update_shuffle_button_text()
        self._save_player_settings()

        # --- NOWE ZMIANY: Aktualizacja zaznaczenia i etykiety "teraz odtwarzane" ---
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            path_to_select_in_listbox = self.playlist[self.current_track_index]
            if path_to_select_in_listbox in self.currently_displayed_paths:
                try:
                    view_idx_to_select = self.currently_displayed_paths.index(path_to_select_in_listbox)
                    self.playlist_listbox.selection_clear(0, tk.END)
                    self.playlist_listbox.selection_set(view_idx_to_select)
                    self.playlist_listbox.activate(view_idx_to_select)
                    self.playlist_listbox.see(view_idx_to_select)
                except (ValueError, tk.TclError):
                    logging.warning("Nie udało się zaznaczyć utworu po zmianie trybu shuffle.")
            # Jeśli utwór grał, zaktualizuj label
            if self.is_playing or self.is_paused:
                self._update_now_playing_label()
            # Jeśli nic nie grało, ale teraz mamy zaznaczony utwór, też zaktualizuj
            elif self.current_track_index != -1:
                 self._update_now_playing_label()
        else: # Jeśli current_track_index to -1 (pusta playlista lub błąd)
            self.playlist_listbox.selection_clear(0, tk.END)
            if not (self.is_playing or self.is_paused): # Tylko jeśli nic nie gra
                self._update_now_playing_label(track_name="Nic nie gra")
        # --- KONIEC NOWYCH ZMIAN ---

        logging.info(f"Tryb losowego odtwarzania zmieniony na: {self.shuffle_mode}")

    def _update_button_tooltip_with_delay_logic(self, button_widget, new_tooltip_text):
        """
        Aktualizuje tekst tooltipa dla danego przycisku i zarządza jego widocznością,
        aby uniknąć "zawieszania się" starego tooltipa po zmianie stanu przycisku.
        """
        if hasattr(button_widget, 'tooltip') and button_widget.tooltip:
            # Jeśli tooltip jest aktualnie widoczny, ukryj go
            if button_widget.tooltip.tooltip_window:
                button_widget.tooltip.hide_tooltip()
            
            # Zaktualizuj tekst w istniejącej instancji tooltipa
            button_widget.tooltip.update_text(new_tooltip_text)
            
            # Możemy dodać małe opóźnienie przed ponownym pokazaniem tooltipa,
            # jeśli kursor nadal jest nad widgetem.
            # Jednak standardowy ToolTip powinien sam obsłużyć ponowne pokazanie przy <Enter>.
            # Kluczowe jest, aby .update_text() poprawnie aktualizowało tekst,
            # a .hide_tooltip() faktycznie go niszczyło, aby <Enter> musiało go stworzyć na nowo.
        else:
            # Jeśli tooltip nie istnieje, stwórz go
            ToolTip(button_widget, new_tooltip_text)

    # --- Metody aktualizujące przyciski (Shuffle, Repeat) ---
    def _update_shuffle_button_text(self):
        if hasattr(self, 'shuffle_button'):
            text = "🔀 Wł." if self.shuffle_mode else "🔀 Wył."
            self.shuffle_button.config(text=text)
            tooltip_text = "Odtwarzanie losowe: " + ("Włączone" if self.shuffle_mode else "Wyłączone")
            self._update_button_tooltip_with_delay_logic(self.shuffle_button, tooltip_text)

    def _update_now_playing_label(self, track_name_override=None, duration_sec=0.0, current_pos_sec=0.0, *, time_only: bool = False):
        """
        Aktualizuje napisy na dolnym pasku i (opcjonalnie) cover w widoku Focus.
        • gdy `time_only=True` ➜ pomiń odświeżanie okładki (używaj w timerze i przy drag‑sliderze)
        """
        # -------- tekst utworu ------------
        if track_name_override is not None:
            display_text = track_name_override
        else:
            if 0 <= self.current_track_index < len(self.playlist):
                entry = self.playlist[self.current_track_index]
                display_text = self._get_display_name_for_track(entry).replace("♥ ", "").strip()
            else:
                display_text = "Nic nie gra"

        if hasattr(self, "now_playing_label") and self.now_playing_label.winfo_exists():
            self.now_playing_label.config(text=display_text)

        # -------- czas ------------
        cur_m, cur_s = divmod(int(current_pos_sec), 60)
        tot_m, tot_s = divmod(int(duration_sec   ), 60)
        if hasattr(self, "track_time_label") and self.track_time_label.winfo_exists():
            self.track_time_label.config(text=f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

        # -------- focus‑view ------------
        if not time_only:
            if hasattr(self, "focus_title_artist_label") and self.focus_title_artist_label.winfo_exists():
                self.focus_title_artist_label.config(text=display_text)
            self._update_focus_cover_label()      # ← zostaje, ale wywoływany rzadziej
            # --- NOWE WYWOŁANIE: Aktualizuj miniaturkę na dolnym pasku ---
            self._update_bottom_bar_cover_thumbnail()
            # --- KONIEC NOWEGO WYWOŁANIA ---
        # --- NOWA METODA ---
        
    def _update_focus_cover_label(self, *, force: bool = False):
        """
        Ustawia dużą okładkę w widoku 'Teraz odtwarzane'.

        • korzysta z cache (`self._cover_cache`) – każdy plik graficzny wczytywany max 1×
        • gdy okładka się nie zmieniła → nic nie robi
        • `force=True` – wymuś ponowne przerysowanie (na wypadek manualnego odświeżania)
        """
        if not (hasattr(self, "focus_cover_label") and self.focus_cover_label.winfo_exists()):
            return

        # --- jaka okładka powinna być? -----------------------------
        cover_path = None
        if 0 <= self.current_track_index < len(self.playlist):
            cover_path = self.playlist[self.current_track_index].get("focus_cover_path")
            if cover_path and not os.path.exists(cover_path):
                cover_path = None

        desired_id = cover_path or "placeholder"     # identyfikator grafiki/placeholdera

        # --- jeśli już ustawiona → wyjdź ---------------------------
        if not force and desired_id == getattr(self, "_current_focus_cover_id", None):
            return

        # --- przygotuj ImageTk -------------------------------------
        if desired_id == "placeholder":
            img = None
            text = "[ Miejsce na Dużą Okładkę ]"
        else:
            # spróbuj z cache
            img = self._cover_cache.get(cover_path)
            if img is None:
                try:
                    from PIL import Image, ImageTk   # import lokalny, gdyby ktoś nie miał PIL w globalu
                    pil_img = Image.open(cover_path)
                    pil_img.thumbnail((320, 320), Image.LANCZOS)
                    img = ImageTk.PhotoImage(pil_img)
                    self._cover_cache[cover_path] = img
                except Exception as e:
                    logging.warning(f"Nie udało się wczytać okładki {cover_path}: {e}")
                    img = None
            text = ""

        # --- podmień w widgetcie -----------------------------------
        self.focus_cover_label.config(image=img or "", text=text)
        self.focus_cover_label.image = img              # bez tego GC skasuje obraz
        self._current_focus_cover_id = desired_id       # zapamiętaj, co wisi

    # --- ZMODYFIKOWANA METODA ---
    def _get_display_name_for_track(self, track_entry_or_path) -> str:
        """
        Zwraca nazwę utworu do wyświetlenia, próbując odczytać tagi Tytuł/Artysta.
        Akceptuje jako argument słownik utworu lub bezpośrednią ścieżkę.
        Dodaje serduszko, jeśli utwór jest ulubiony (na podstawie ścieżki).
        """
        track_path = None
        # --- NOWE ZMIANY: Pobierz ścieżkę z argumentu ---
        if isinstance(track_entry_or_path, dict):
            track_path = track_entry_or_path.get('path')
        elif isinstance(track_entry_or_path, str): # Na wypadek, gdyby gdzieś jeszcze przekazywano samą ścieżkę
            track_path = track_entry_or_path
        else:
            logging.warning(f"Nieprawidłowy typ argumentu w _get_display_name_for_track: {type(track_entry_or_path)}")
            return "Błąd typu utworu"

        if not track_path or not os.path.exists(track_path):
            return "Nieznany lub usunięty utwór"
        # --- KONIEC NOWYCH ZMIAN ---

        title_str = None
        artist_str = None
        final_display_name = ""

        try:
            audio = MutagenFile(track_path, easy=True)
            if audio:
                if 'title' in audio and audio['title']:
                    title_str = audio['title'][0]
                elif 'TIT2' in audio:
                    title_str = str(audio['TIT2'])
                
                if 'artist' in audio and audio['artist']:
                    artist_str = audio['artist'][0]
                elif 'TPE1' in audio:
                    artist_str = str(audio['TPE1'])
                elif 'albumartist' in audio and audio['albumartist'] and not artist_str:
                    artist_str = audio['albumartist'][0]
                
                if title_str and not isinstance(title_str, str): title_str = str(title_str)
                if artist_str and not isinstance(artist_str, str): artist_str = str(artist_str)

                if title_str: title_str = title_str.strip()
                if artist_str: artist_str = artist_str.strip()
        except Exception as e:
            logging.warning(f"Nie można odczytać tagów mutagen dla '{track_path}': {e}")

        if title_str and artist_str:
            final_display_name = f"{title_str} - {artist_str}"
        elif title_str:
            final_display_name = title_str
        elif artist_str:
            base_name_no_ext = os.path.splitext(os.path.basename(track_path))[0]
            final_display_name = f"{artist_str} - {base_name_no_ext}"
        else:
            base_name = os.path.basename(track_path)
            final_display_name = os.path.splitext(base_name)[0]

        # Ulubione są nadal sprawdzane po ścieżce `path`
        if track_path in self.favorite_tracks:
            final_display_name = f"♥ {final_display_name}"

        return final_display_name.strip()

    # --- NOWA METODA ---
# W klasie MusicPlayerPage

    def apply_theme_colors(self):
        """
        Stosuje kolory z aktywnego motywu launchera do widgetów odtwarzacza muzyki.
        Ta metoda powinna być wywoływana przez GameLauncher po zmianie motywu.
        """
        if not self.launcher or not hasattr(self.launcher, 'settings') or not hasattr(self.launcher, 'get_all_available_themes'):
            logging.warning("apply_theme_colors: Brak dostępu do ustawień motywu launchera.")
            return

        logging.info("MusicPlayerPage: Stosowanie kolorów motywu...")

        active_theme_name_main = self.launcher.settings.get('theme', 'Dark')
        all_themes_main = self.launcher.get_all_available_themes()
        active_theme_def_main = all_themes_main.get(active_theme_name_main, THEMES.get('Dark', {})) 

        # --- Definicje domyślnych wartości (powinny być przed ich użyciem) ---
        default_bg = active_theme_def_main.get('background','#1e1e1e') 
        default_fg = active_theme_def_main.get('foreground','white')
        default_entry_bg = active_theme_def_main.get('entry_background','#2e2e2e')
        default_button_bg_for_borders = active_theme_def_main.get('button_background', default_entry_bg) # Dla koloru ramki
        default_player_bar_bg = active_theme_def_main.get('player_bottom_bar_background', default_entry_bg) 
        default_scrollbar_slider = active_theme_def_main.get('scrollbar_slider','#555555')
        default_scrollbar_trough = default_bg 
        default_link_fg = active_theme_def_main.get('link_foreground','#aabbff')
        default_tile_background = active_theme_def_main.get('tree_background', default_entry_bg) 
        # --- ZMIANA: Definiujemy default_tile_border_color tutaj ---
        default_tile_border_color_fallback = active_theme_def_main.get('tree_heading', default_button_bg_for_borders) 
        # --- KONIEC ZMIANY ---
        default_selected_list_item_bg_color = active_theme_def_main.get('link_foreground', default_link_fg)

        # --- Pobieranie kolorów z aktywnego motywu launchera (z fallbackami) ---
        main_bg = active_theme_def_main.get('background', default_bg)
        main_fg = active_theme_def_main.get('foreground', default_fg)
        entry_bg = active_theme_def_main.get('entry_background', default_entry_bg)
        button_fg = active_theme_def_main.get('button_foreground', main_fg)
        bottom_bar_color = active_theme_def_main.get('player_bottom_bar_background', default_player_bar_bg)
        scrollbar_slider_color = active_theme_def_main.get('scrollbar_slider', default_scrollbar_slider)
        link_fg = active_theme_def_main.get('link_foreground', default_link_fg)
        selected_list_item_bg = active_theme_def_main.get('link_foreground', default_selected_list_item_bg_color)
        selected_list_item_fg = main_bg 
        
        tile_bg_color = active_theme_def_main.get('tree_background', default_tile_background)
        # --- ZMIANA: Używamy zdefiniowanego fallbacku ---
        tile_normal_border_color = active_theme_def_main.get('tree_heading', default_tile_border_color_fallback) 
        # --- KONIEC ZMIANY ---
        active_tile_highlight_color = active_theme_def_main.get('link_foreground', default_link_fg)


        style = ttk.Style()

        # 0. Główna ramka strony
        if hasattr(self, 'parent_frame') and self.parent_frame.winfo_exists():
            # parent_frame dziedziczy styl TFrame z launchera, który już jest ustawiony
            # przez GameLauncher.apply_theme() z użyciem `main_bg`.
            # Można to zostawić, lub jeśli chcesz mieć pewność:
            # style.configure("MusicPageParent.TFrame", background=main_bg)
            # self.parent_frame.configure(style="MusicPageParent.TFrame")
            pass

        # 1. Górny panel (top_panel_frame i jego dzieci typu Frame)
        # Powinny używać standardowego stylu "TFrame", który dziedziczy z głównego motywu.
        # Przyciski i Combobox w nim również powinny dziedziczyć style z głównego launchera.

        # 2. Listbox playlisty (tk widget)
        if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
            self.playlist_listbox.configure(
                bg=entry_bg, 
                fg=main_fg,   
                selectbackground=selected_list_item_bg,
                selectforeground=selected_list_item_fg,
                highlightbackground=main_bg, # Kolor ramki focusu (gdy nieaktywny)
                highlightcolor=link_fg      # Kolor ramki focusu (gdy aktywny)
            )

        # 3. Style dla dolnego paska i jego elementów
        style.configure("BottomBar.TFrame", background=bottom_bar_color)
        style.configure("BottomBar.Controls.TFrame", background=bottom_bar_color)
        style.configure("BottomBar.Controls.TLabel", background=bottom_bar_color, foreground=main_fg)
        style.configure("BottomBar.NowPlaying.TLabel", background=bottom_bar_color, foreground=main_fg, font=("Segoe UI", 10, "bold"))
        style.configure("BottomBar.TrackTime.TLabel", background=bottom_bar_color, foreground=main_fg) 

        style.configure("Music.Toolbutton.TButton", background=bottom_bar_color, foreground=button_fg, padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.Toolbutton.TButton", foreground=[('active', link_fg), ('hover', link_fg)], background=[('active', bottom_bar_color), ('hover', bottom_bar_color)])
        style.configure("Music.PlayPause.TButton", background=bottom_bar_color, foreground=button_fg, padding=6, font=("Segoe UI", 12, "bold"), relief="flat", borderwidth=0)
        style.map("Music.PlayPause.TButton", foreground=[('active', link_fg), ('hover', link_fg)], background=[('active', bottom_bar_color), ('hover', bottom_bar_color)])
        
        fav_on_color = "MediumPurple1" 
        fav_hover_color = "MediumPurple2"
        fav_active_color = "MediumPurple3"
        fav_off_color = main_fg 
        
        style.configure("Music.FavOn.TButton", background=bottom_bar_color, foreground=fav_on_color, padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.FavOn.TButton", foreground=[('active', fav_active_color), ('hover', fav_hover_color)], background=[('active', bottom_bar_color), ('hover', bottom_bar_color)])
        style.configure("Music.FavOff.TButton", background=bottom_bar_color, foreground=fav_off_color, padding=3, relief="flat", borderwidth=0, font=("Segoe UI", 10))
        style.map("Music.FavOff.TButton", foreground=[('active', fav_on_color), ('hover', fav_on_color)], background=[('active', bottom_bar_color), ('hover', bottom_bar_color)])

        style.configure("MusicProgress.Horizontal.TScale", troughcolor=bottom_bar_color, background=scrollbar_slider_color, lightcolor=bottom_bar_color, darkcolor=bottom_bar_color, bordercolor=bottom_bar_color, sliderrelief='flat')
        style.map("MusicProgress.Horizontal.TScale", background=[('disabled', "#404040")])
        style.configure("MusicVolume.Horizontal.TScale", troughcolor=bottom_bar_color, background=scrollbar_slider_color, lightcolor=bottom_bar_color, darkcolor=bottom_bar_color, bordercolor=bottom_bar_color, sliderrelief='flat')

        # --- Style dla Kafelków Muzycznych ---
        # Styl dla ramki normalnego kafelka (zakładamy, że będziemy go nazywać "Game.TFrame" 
        # dla spójności z launcherem gier, ale musi być zdefiniowany lub dziedziczony)
        # Jeśli Game.TFrame jest już dobrze zdefiniowane w GameLauncher i dziedziczy tło, to poniższe może nie być konieczne.
        # Jeśli nie, zdefiniujmy go tutaj specyficznie dla odtwarzacza, jeśli potrzeba.
        # Załóżmy, że chcemy, aby normalne kafelki muzyczne miały takie samo tło jak Listbox (entry_bg)
        # i ramkę w kolorze np. tree_heading_bg
        # --- Style dla Kafelków Muzycznych ---
        style.configure("NormalMusicTile.TFrame", 
                        background=tile_bg_color, 
                        relief="solid", 
                        borderwidth=1,
                        # --- ZMIANA: Użyj tile_normal_border_color ---
                        bordercolor=tile_normal_border_color)
                        # --- KONIEC ZMIANY ---

        # Styl dla ramki AKTYWNEGO (odtwarzanego) kafelka muzycznego
        style.configure("MusicTileSelected.TFrame",
                        background=entry_bg, # Tło takie samo jak normalnego, lub lekko inne
                        relief="solid",
                        borderwidth=2,  # Grubsza ramka
                        bordercolor=active_tile_highlight_color) # Kolor ramki podświetlenia

        # Styl dla tekstu (nazwy utworu) na NORMALNYM kafelku
        style.configure("MusicTile.TLabel",
                        background=entry_bg, # Tło etykiety zgodne z tłem kafelka
                        foreground=main_fg, # Standardowy kolor tekstu
                        font=("Segoe UI", 9))

        # Styl dla tekstu (nazwy utworu) na AKTYWNYM kafelku
        style.configure("ActiveMusicTile.TLabel",
                        background=entry_bg, # Tło etykiety zgodne z tłem kafelka
                        foreground=active_tile_highlight_color, # Tekst w kolorze podświetlenia
                        font=("Segoe UI", 9, "bold")) # Pogrubiony
        # --- KONIEC STYLÓW DLA KAFELKÓW ---

        logging.info("MusicPlayerPage: Kolory motywu zostały zastosowane do stylów.")
        
        # Odśwież aktualnie widoczny widok (listę lub kafelki), aby nowe style się zaaplikowały
        if hasattr(self, '_apply_music_content_view'):
             self._apply_music_content_view()

    def _get_artist_album_from_tags(self, track_path: str) -> tuple[str | None, str | None, str | None]:
        """Pomocnicza funkcja do odczytu Artysty, Albumu i Tytułu z tagów pliku."""
        artist, album, title = None, None, None
        try:
            audio = MutagenFile(track_path, easy=True)
            if audio:
                if 'artist' in audio and audio['artist']: artist = str(audio['artist'][0]).strip()
                elif 'TPE1' in audio : artist = str(audio['TPE1']).strip()

                if 'album' in audio and audio['album']: album = str(audio['album'][0]).strip()
                elif 'TALB' in audio : album = str(audio['TALB']).strip()

                if 'title' in audio and audio['title']: title = str(audio['title'][0]).strip()
                elif 'TIT2' in audio : title = str(audio['TIT2']).strip()
        except Exception as e:
            logging.warning(f"Nie można odczytać tagów Artysta/Album/Tytuł dla '{track_path}': {e}")
        return artist, album, title

    def _fetch_and_set_lastfm_cover(self, track_entry: dict, 
                                   force_update_focus_cover: bool = False,
                                   callback_on_complete=None): # NOWY ARGUMENT
        """
        Pobiera okładkę z Last.fm dla danego utworu i aktualizuje wpis oraz UI.
        Wywołuje callback po zakończeniu.
        """
        track_path = track_entry.get('path')
        cover_actually_found_and_set = False # Flaga, czy udało się pobrać i zapisać URL/plik
        
        try:
            # --- Początek istniejącego kodu metody (API key, pobieranie tagów) ---
            if not track_path:
                return # Zakończ, jeśli brak ścieżki

            api_key = self.launcher.local_settings.get("lastfm_api_key")
            if not api_key:
                logging.warning("Brak klucza API Last.fm.")
                return
            # --- Reszta logiki pobierania cover_url (jak wcześniej) ---
            network = pylast.LastFMNetwork(api_key=api_key)
            artist_tag, album_tag, title_tag = self._get_artist_album_from_tags(track_path)

            if not artist_tag or not (album_tag or title_tag):
                logging.info(f"Brak wystarczających tagów dla '{track_path}'.")
                return

            cover_url = None
            preferred_sizes = [pylast.SIZE_MEGA, pylast.SIZE_EXTRA_LARGE, pylast.SIZE_LARGE, pylast.SIZE_MEDIUM]

            if album_tag and artist_tag:
                try:
                    album_obj = network.get_album(artist_tag, album_tag)
                    if album_obj:
                        for size_const in preferred_sizes:
                            try:
                                temp_url = album_obj.get_cover_image(size=size_const)
                                if temp_url: cover_url = temp_url; break
                            except IndexError: continue
                            except pylast.WSError: raise 
                    if not cover_url: logging.warning(f"Last.fm (Album): Nie znaleziono okładki dla {artist_tag} - {album_tag}.")
                except pylast.WSError as e: logging.warning(f"Błąd API Last.fm (album.getInfo) dla {artist_tag} - {album_tag}: {e}")
            
            if not cover_url and title_tag and artist_tag:
                try:
                    track_obj = network.get_track(artist_tag, title_tag)
                    if track_obj and hasattr(track_obj, 'get_album') and track_obj.get_album():
                        album_from_track = track_obj.get_album()
                        if album_from_track:
                            for size_const in preferred_sizes:
                                try:
                                    temp_url = album_from_track.get_cover_image(size=size_const)
                                    if temp_url: cover_url = temp_url; break
                                except IndexError: continue
                                except pylast.WSError: raise
                    if not cover_url: logging.warning(f"Last.fm (Track->Album): Nie znaleziono okładki dla {artist_tag} - {title_tag}.")
                except pylast.WSError as e: logging.warning(f"Błąd API Last.fm (track.getInfo) dla {artist_tag} - {title_tag}: {e}")
            # --- Koniec logiki pobierania cover_url ---

            if cover_url:
                response = requests.get(cover_url, stream=True, timeout=20) # Zwiększony timeout
                response.raise_for_status()
                
                safe_artist = re.sub(r'[\\/*?:"<>|]', "_", artist_tag or "UnknownArtist")
                safe_album_title = re.sub(r'[\\/*?:"<>|]', "_", album_tag or title_tag or "UnknownAlbumTrack") # Zmiana UnknownAlbum na UnknownAlbumTrack
                
                content_type = response.headers.get('content-type', '').lower()
                ext = '.jpg'
                if 'png' in content_type: ext = '.png'

                cover_filename = f"{safe_artist}_{safe_album_title}_lastfm{ext}"[:150] # Ograniczenie długości nazwy pliku
                covers_dir = os.path.join(IMAGES_FOLDER, "music_covers", "lastfm")
                os.makedirs(covers_dir, exist_ok=True)
                local_cover_path = os.path.join(covers_dir, cover_filename)

                with open(local_cover_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                logging.info(f"Zapisano okładkę Last.fm dla '{track_path}' -> '{local_cover_path}'")
                cover_actually_found_and_set = True # Ustaw flagę sukcesu dla tego utworu

                # --- ZMIENIONA I UPROSZCZONA LOGIKA AKTUALIZACJI I UI ---
                def update_data_and_ui_after_fetch():
                    data_changed_in_named_playlists = False
                    active_named_list = self.named_playlists.get(self.active_playlist_name)
                    if active_named_list:
                        for i, entry in enumerate(active_named_list):
                            if entry.get('path') == track_path:
                                if entry.get('lastfm_cover_path') != local_cover_path:
                                    entry['lastfm_cover_path'] = local_cover_path
                                    data_changed_in_named_playlists = True
                                if force_update_focus_cover or not entry.get('focus_cover_path'):
                                    if entry.get('focus_cover_path') != local_cover_path:
                                        entry['focus_cover_path'] = local_cover_path
                                        data_changed_in_named_playlists = True
                                # Nie modyfikujemy `self.named_playlists[self.active_playlist_name][i]` bezpośrednio,
                                # bo `entry` jest referencją do słownika w liście, więc zmiany na `entry` są widoczne.
                                break 
                    
                    if data_changed_in_named_playlists:
                        self._save_player_settings() # Zapisz, bo `named_playlists` mogły się zmienić

                        # Przeładuj self.playlist, aby mieć pewność, że zawiera najnowsze dane okładek
                        current_playing_path = None
                        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                            current_playing_path = self.playlist[self.current_track_index].get('path')
                        
                        self._load_active_playlist() # Odbuduje self.playlist z named_playlists

                        # Przywróć indeks, jeśli to możliwe
                        if current_playing_path:
                            self.current_track_index = -1
                            for idx, reloaded_entry in enumerate(self.playlist):
                                if reloaded_entry.get('path') == current_playing_path:
                                    self.current_track_index = idx
                                    break
                    
                    # Zawsze odśwież widok, który jest aktywny
                    # _apply_music_content_view wywoła odpowiednią metodę (_update_playlist_display lub _update_music_tiles_display)
                    self._apply_music_content_view()

                    # Specjalne odświeżenie dla focus view, jeśli dotyczy to aktualnego utworu
                    if not self.is_playlist_view_active.get() and \
                       self.current_track_index != -1 and \
                       self.current_track_index < len(self.playlist) and \
                       self.playlist[self.current_track_index].get('path') == track_path:
                        self._update_focus_cover_label() # To już jest w _update_now_playing_label, które woła _apply_music_content_view

                self.launcher.root.after(0, update_data_and_ui_after_fetch)
                # --- KONIEC ZMIENIONEJ LOGIKI ---
            else:
                logging.info(f"Nie znaleziono URL okładki w Last.fm dla '{track_path}' (Artysta: {artist_tag}, Album/Tytuł: {album_tag or title_tag}).")

        except pylast.WSError as e:
            logging.error(f"Błąd API Last.fm dla '{track_path}': {e}.")
        except requests.RequestException as e:
            logging.error(f"Błąd pobierania obrazu okładki z URL dla '{track_path}': {e}")
        except Exception as e:
            logging.exception(f"Nieoczekiwany błąd podczas pobierania okładki Last.fm dla '{track_path}': {e}")
        
        # --- NOWE: Wywołaj callback po zakończeniu ---
        finally:
            if callback_on_complete:
                # Przekaż do callback, czy udało się znaleźć i zapisać okładkę (niekoniecznie czy się wyświetliła)
                self.launcher.root.after(0, lambda: callback_on_complete(cover_actually_found_and_set))
        # --- KONIEC NOWEGO ---


    def _start_lastfm_cover_fetch_thread(self, track_entry: dict, 
                                         force_update_focus_cover: bool = False, 
                                         callback_on_complete=None): # NOWY ARGUMENT
        """Uruchamia pobieranie okładki Last.fm w osobnym wątku."""
        threading.Thread(
            target=self._fetch_and_set_lastfm_cover,
            args=(track_entry, force_update_focus_cover, callback_on_complete), # PRZEKAŻ CALLBACK
            daemon=True
        ).start()

    def _fetch_covers_for_active_playlist(self):
        """
        Pobiera okładki z Last.fm dla wszystkich utworów w aktywnej playliście.
        Uruchamiamy cały pętlę fetchującą w tle, by UI pozostał responsywny.
        """
        if not self.active_playlist_name or self.active_playlist_name not in self.named_playlists:
            messagebox.showwarning("Brak playlisty", "Nie wybrano aktywnej playlisty.", parent=self.parent_frame)
            return

        api_key = self.launcher.local_settings.get("lastfm_api_key")
        if not api_key:
            messagebox.showwarning("Brak Klucza API", "Podaj klucz API Last.fm w Ustawieniach.", parent=self.parent_frame)
            return

        tracks = list(self.named_playlists[self.active_playlist_name])
        if not tracks:
            messagebox.showinfo("Playlista pusta", "Aktywna playlista nie zawiera utworów.", parent=self.parent_frame)
            return

        total = len(tracks)
        # pokaż progress i skonfiguruj go
        self.launcher.show_progress_window(f"Okładki dla: {self.active_playlist_name} (0/{total})")
        self.launcher.progress_bar['maximum'] = total
        self.launcher.progress_bar['value'] = 0
        self.launcher.progress_bar['mode'] = 'determinate'
        # jeśli show_progress_window robi grab_set, możemy go od razu zwolnić:
        try:
            self.launcher.progress_window.grab_release()
        except Exception:
            pass

        # stany do podsumowania
        self._covers_fetched_count = 0
        self._covers_not_found_count = 0
        self._threads_completed_count = 0
        self._last_progress_update_time = time.time()

        def on_single_fetch_complete(found: bool):
            self._threads_completed_count += 1
            if found:
                self._covers_fetched_count += 1
            else:
                self._covers_not_found_count += 1

            now = time.time()
            if (self._threads_completed_count % 5 == 0
                or now - self._last_progress_update_time > 0.5
                or self._threads_completed_count == total):
                # aktualizuj pasek postępu
                self.launcher.progress_bar['value'] = self._threads_completed_count
                txt = f"Pobrano ({self._threads_completed_count}/{total})\nOk: {self._covers_fetched_count}, Brak: {self._covers_not_found_count}"
                self.launcher.progress_label.config(text=txt)
                self.launcher.progress_window.update_idletasks()
                self._last_progress_update_time = now

            if self._threads_completed_count == total:
                # koniec – zamknij okno i pokaż podsumowanie
                self.launcher.progress_window.destroy()
                msg = (f"Pobieranie okładek zakończone dla '{self.active_playlist_name}'.\n\n"
                    f"Pomyślnie: {self._covers_fetched_count}\n"
                    f"Nie znaleziono: {self._covers_not_found_count}")
                messagebox.showinfo("Zakończono", msg, parent=self.parent_frame)
                # odśwież focus-view, jeśli jest aktywny
                if not self.is_playlist_view_active.get():
                    self._update_focus_cover_label()

        def worker():
            for entry in tracks:
                self._start_lastfm_cover_fetch_thread(entry.copy(),
                                                    force_update_focus_cover=False,
                                                    callback_on_complete=on_single_fetch_complete)
                # odczekaj między żądaniami, ale nie blokuj UI
                time.sleep(0.25)

        threading.Thread(target=worker, daemon=True).start()


    def _add_music_files(self, *, import_to_internal: bool = False):
        if not pygame.mixer.get_init(): # ... (reszta bez zmian) ...
             messagebox.showerror("Błąd Mixera", "Moduł audio nie jest zainicjalizowany.", parent=self.parent_frame)
             return

        initial_dir = self.local_settings.get("last_music_folder", os.path.expanduser("~"))
        supported_filetypes = [ # ... (bez zmian) ...
            ("Pliki Audio", "*.mp3 *.wav *.ogg *.flac *.m4a"),
            ("Wszystkie pliki", "*.*")
        ]
        filepaths = filedialog.askopenfilenames(
            title=f"Wybierz pliki muzyczne {'do importu wewnętrznego' if import_to_internal else ''}",
            initialdir=initial_dir,
            filetypes=supported_filetypes,
            parent=self.parent_frame
        )

        if filepaths:
            # --- NOWE ZMIANY: Wybór docelowej playlisty ---
            target_playlist_name_files = "Muzyka Wewnętrzna" if import_to_internal else "Główna Kolejka"

            if target_playlist_name_files not in self.named_playlists:
                logging.error(f"Docelowa playlista '{target_playlist_name_files}' nie istnieje!")
                messagebox.showerror("Błąd Wewnętrzny", f"Playlista '{target_playlist_name_files}' nie została znaleziona.", parent=self.parent_frame)
                return

            active_playlist_tracks_files = self.named_playlists.get(target_playlist_name_files, [])
            # --- KONIEC NOWYCH ZMIAN ---

            added_count_files = 0
            skipped_due_to_error_count_files = 0
            self.local_settings["last_music_folder"] = os.path.dirname(filepaths[0])
            
            total_files_to_process_f = len(filepaths)
            operation_label_f = (
                'Importowanie do "Muzyka Wewnętrzna"'
                if import_to_internal
                else 'Dodawanie do "Główna Kolejka"'
            )
            operation_title_f = f"{operation_label_f}: {total_files_to_process_f} plików"
            self.launcher.show_progress_window(operation_title_f)
            if not (hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists()): # ... (bez zmian) ...
                logging.error("Nie udało się utworzyć okna postępu w GameLauncher.")
                return
            
            self.launcher.progress_bar['maximum'] = total_files_to_process_f
            self.launcher.progress_bar['value'] = 0
            self.launcher.progress_bar['mode'] = 'determinate'
            self.launcher.progress_label.config(text="Przygotowywanie...")

            def process_files_thread_local():
                nonlocal added_count_files, skipped_due_to_error_count_files # Użyj nonlocal

                for idx_f, src_path_f in enumerate(filepaths):
                    progress_text_ui_f = f"Plik {idx_f+1}/{total_files_to_process_f}: {os.path.basename(src_path_f)}"
                    if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists(): # ... (bez zmian) ...
                        self.launcher.root.after(0, lambda prog_txt=progress_text_ui_f, val=idx_f : (
                            setattr(self.launcher.progress_bar, 'value', val),
                            self.launcher.progress_label.config(text=prog_txt)
                        ))
                    else: 
                        logging.info("Okno postępu zamknięte, przerywanie importu plików.")
                        break

                    path_to_add_to_playlist_f = None
                    is_internal_flag_f = False

                    if import_to_internal:
                        path_to_add_to_playlist_f = self._copy_into_internal_library(src_path_f)
                        if path_to_add_to_playlist_f:
                            is_internal_flag_f = True
                        else:
                            skipped_due_to_error_count_files +=1
                            continue
                    else:
                        path_to_add_to_playlist_f = os.path.abspath(src_path_f)
                        is_internal_flag_f = False
                    
                    if path_to_add_to_playlist_f:
                        if not any(entry.get('path') == path_to_add_to_playlist_f for entry in active_playlist_tracks_files):
                            active_playlist_tracks_files.append({
                                "path": path_to_add_to_playlist_f,
                                "focus_cover_path": None,
                                "lastfm_cover_path": None,
                                "is_internal": is_internal_flag_f # WAŻNE: Ustawienie flagi
                            })
                            added_count_files += 1
                
                if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                    self.launcher.root.after(100, self.launcher.progress_window.destroy)
                
                # --- NOWA ZMIANA: Przekazanie target_playlist_name do finalizacji ---
                self.launcher.root.after(150, self._finalize_add_operation, added_count_files, skipped_due_to_error_count_files, import_to_internal, target_playlist_name_files, "plików")

            threading.Thread(target=process_files_thread_local, daemon=True).start()
        else:
            logging.debug("Anulowano wybór plików muzycznych.")

    # --- NOWA WSPÓLNA METODA FINALIZUJĄCA ---
    def _finalize_add_operation(self, added_count, skipped_count, was_internal_import, target_playlist_name_final, operation_type_str):
        """
        Wspólna metoda do finalizacji operacji dodawania/importu folderu lub plików.
        Aktualizuje UI i pokazuje podsumowanie.
        `operation_type_str` to np. "folder" lub "plików".
        """
        if added_count > 0:
            action_verb = "Zaimportowano" if was_internal_import else "Dodano"
            logging.info(f"{action_verb} {added_count} {operation_type_str} do playlisty '{target_playlist_name_final}'.")
            
            # Zapisz `named_playlists`, które było modyfikowane w wątku
            # (zakładając, że active_playlist_tracks było referencją lub odpowiednio przekazane)
            # Jeśli `active_playlist_tracks` w wątku było kopią, musisz je tu zaktualizować w `self.named_playlists`.
            # Dla bezpieczeństwa można dodać:
            # self.named_playlists[target_playlist_name_final] = ... (zaktualizowana lista z wątku, jeśli była kopią)

            self._save_player_settings() # Zapisz ZAWSZE po modyfikacji named_playlists

            # Jeśli aktywna playlista jest TĄ, którą właśnie modyfikowaliśmy, odśwież jej widok
            if self.active_playlist_name == target_playlist_name_final:
                self._load_active_playlist()    
                self._update_playlist_display() 
                if self.music_library_view_mode.get() == "tiles":
                    self._update_music_tiles_display()

                # Logika dla ustawienia current_track_index, jeśli nic nie grało
                if not self.is_playing and not self.is_paused and self.playlist and self.current_track_index == -1:
                    self.current_track_index = 0
                    self._update_now_playing_label()
                    # Zaznacz w Listboxie, jeśli widok listy jest aktywny i są elementy
                    if self.music_library_view_mode.get() == "list" and hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists() and self.currently_displayed_paths:
                        entry_to_select_f = self.playlist[self.current_track_index]
                        if entry_to_select_f in self.currently_displayed_paths:
                            try:
                                display_idx_to_select_f = self.currently_displayed_paths.index(entry_to_select_f)
                                self.playlist_listbox.selection_clear(0, tk.END)
                                self.playlist_listbox.selection_set(display_idx_to_select_f)
                                self.playlist_listbox.activate(display_idx_to_select_f)
                            except (tk.TclError, ValueError): pass
            else: # Jeśli modyfikowano inną playlistę niż aktywna
                logging.info(f"Modyfikowano playlistę '{target_playlist_name_final}', która nie jest aktywna. Aktywna: '{self.active_playlist_name}'. Nie odświeżono widoku aktywnej playlisty.")
        
        msg_parts = []
        if added_count > 0: msg_parts.append(f"Dodano pomyślnie: {added_count} {operation_type_str}.")
        if skipped_count > 0: msg_parts.append(f"Pominięto z powodu błędów: {skipped_count} {operation_type_str}.")
        if not msg_parts: msg_parts.append(f"Nie znaleziono nowych {operation_type_str} lub wszystkie już są na playliście '{target_playlist_name_final}'.")
        
        messagebox.showinfo("Zakończono", "\n".join(msg_parts), parent=self.parent_frame)
    # --- KONIEC NOWEJ WSPÓLNEJ METODY ---

    def _finalize_files_import(self, added_count, skipped_count, was_internal_import):
        """Metoda pomocnicza wywoływana po zakończeniu wątku importu plików."""
        if added_count > 0:
            action_verb = "Zaimportowano" if was_internal_import else "Dodano"
            logging.info(f"{action_verb} {added_count} plików muzycznych do playlisty '{self.active_playlist_name}'.")
            
            self._load_active_playlist()    
            self._update_playlist_display() 
            if self.music_library_view_mode.get() == "tiles":
                self._update_music_tiles_display()

            if not self.is_playing and not self.is_paused and self.playlist and self.current_track_index == -1:
                self.current_track_index = 0
                self._update_now_playing_label()
                # Zaznaczanie (kod jak wcześniej)
            self._save_player_settings() 
        
        msg_parts = []
        if added_count > 0: msg_parts.append(f"Dodano pomyślnie: {added_count} plików.")
        if skipped_count > 0: msg_parts.append(f"Pominięto z powodu błędów: {skipped_count} plików.")
        if not msg_parts: msg_parts.append("Nie wybrano nowych plików muzycznych lub wszystkie już są na playliście.")
        
        messagebox.showinfo("Zakończono", "\n".join(msg_parts), parent=self.parent_frame)

    def _copy_into_internal_library(self, src_path: str) -> str | None:
        """
        Kopiuje plik źródłowy do folderu INTERNAL_MUSIC_DIR, dbając o unikalną nazwę.
        Zwraca pełną, bezwzględną ścieżkę docelową skopiowanego pliku lub None w przypadku błędu.
        """
        if not os.path.exists(src_path):
            logging.error(f"_copy_into_internal_library: Plik źródłowy nie istnieje: {src_path}")
            return None
        
        if not os.path.isdir(INTERNAL_MUSIC_DIR):
            try:
                os.makedirs(INTERNAL_MUSIC_DIR, exist_ok=True)
                logging.info(f"Utworzono folder wewnętrznej biblioteki: {INTERNAL_MUSIC_DIR}")
            except OSError as e:
                logging.error(f"Nie można utworzyć folderu wewnętrznej biblioteki '{INTERNAL_MUSIC_DIR}': {e}")
                messagebox.showerror("Błąd Folderu", f"Nie można utworzyć folderu biblioteki wewnętrznej:\n{INTERNAL_MUSIC_DIR}\n\nBłąd: {e}", parent=self.parent_frame)
                return None

        base_name = os.path.basename(src_path)
        dest_path_candidate = os.path.join(INTERNAL_MUSIC_DIR, base_name)
        
        # Sprawdź, czy plik o tej samej zawartości już istnieje (opcjonalne, ale dobre dla unikania duplikatów)
        # Możemy to zrobić przez porównanie rozmiaru i hasha, ale to skomplikuje.
        # Na razie, jeśli plik o tej samej ścieżce docelowej (nazwie) już istnieje,
        # spróbujemy znaleźć unikalną nazwę.

        root, ext = os.path.splitext(dest_path_candidate)
        counter = 1
        final_dest_path = dest_path_candidate
        
        # Pętla do znalezienia unikalnej nazwy pliku
        while os.path.exists(final_dest_path):
            # Prosta heurystyka: jeśli nazwy i rozmiary są takie same, uznaj za duplikat i nie kopiuj
            if os.path.basename(src_path) == os.path.basename(final_dest_path) and \
               os.path.getsize(src_path) == os.path.getsize(final_dest_path):
                logging.info(f"Plik '{base_name}' (lub identyczny) już istnieje w bibliotece wewnętrznej jako '{os.path.basename(final_dest_path)}'. Pomijanie kopiowania.")
                return final_dest_path # Zwróć istniejącą ścieżkę

            final_dest_path = f"{root}_({counter}){ext}"
            counter += 1
            if counter > 100: # Zabezpieczenie przed nieskończoną pętlą
                logging.error(f"Nie można było znaleźć unikalnej nazwy dla pliku '{base_name}' po 100 próbach.")
                messagebox.showerror("Błąd Nazwy Pliku", f"Nie można było wygenerować unikalnej nazwy dla importowanego pliku:\n{base_name}", parent=self.parent_frame)
                return None
        
        try:
            shutil.copy2(src_path, final_dest_path) # copy2 zachowuje metadane
            logging.info(f"Skopiowano plik '{src_path}' do wewnętrznej biblioteki jako '{final_dest_path}'")
            return os.path.abspath(final_dest_path) # Zwróć bezwzględną ścieżkę
        except Exception as e:
            logging.error(f"Nie udało się skopiować pliku '{src_path}' do '{final_dest_path}': {e}")
            messagebox.showerror("Błąd Kopiowania", f"Nie udało się skopiować pliku:\n{src_path}\n\nBłąd: {e}", parent=self.parent_frame)
            return None
    #─────────────────────────────────────────────────────────────

    def _get_tracks_for_active_playlist(self, *, external_only=False):
        """
        Zwraca listę utworów słownikowych z aktywnej playlisty.
        external_only=True  → filtruj pliki będące w INTERNAL_MUSIC_DIR.
        """
        tracks = self.named_playlists.get(self.active_playlist_name, [])
        if external_only:
            return [e for e in tracks if not e.get("is_internal")]
        return tracks

# W klasie MusicPlayerPage

    def _clear_current_queue(self):
        """
        Czyści AKTYWNĄ nazwaną playlistę, resetuje stan odtwarzacza i aktualizuje UI.
        Jeśli czyszczona jest playlista "Muzyka Wewnętrzna", pyta o fizyczne usunięcie plików muzycznych.
        Usuwa powiązane okładki Focus/LastFM, jeśli utwór nie występuje już na żadnej innej playliście
        LUB jeśli plik muzyczny jest fizycznie usuwany.
        """
        logging.info(f"Rozpoczęto czyszczenie aktywnej playlisty: '{self.active_playlist_name}'.")
        was_playing_or_paused = self.is_playing or self.is_paused

        if not self.active_playlist_name or self.active_playlist_name not in self.named_playlists:
            logging.warning("Próba wyczyszczenia nieistniejącej lub nieaktywnej playlisty.")
            messagebox.showwarning("Błąd", "Brak aktywnej playlisty do wyczyszczenia.", parent=self.parent_frame)
            return

        # Potwierdzenie od użytkownika, zwłaszcza jeśli to playlista wewnętrzna
        confirm_msg = f"Czy na pewno chcesz wyczyścić wszystkie utwory z playlisty '{self.active_playlist_name}'?"
        if self.active_playlist_name == "Muzyka Wewnętrzna":
            confirm_msg += "\n\nZostaniesz również zapytany o fizyczne usunięcie plików muzycznych z tej playlisty z dysku."
        
        if not messagebox.askyesno("Potwierdź Wyczyszczenie", confirm_msg, parent=self.parent_frame):
            return

        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            logging.info("Zatrzymano muzykę przed czyszczeniem playlisty.")

        tracks_to_process_for_cleanup = list(self.named_playlists.get(self.active_playlist_name, [])) # Pracuj na kopii
        
        # --- Logika fizycznego usuwania plików muzycznych DLA WEWNĘTRZNEJ PLAYLISTY ---
        physical_music_files_to_delete_paths = set()
        if self.active_playlist_name == "Muzyka Wewnętrzna" and tracks_to_process_for_cleanup:
            if messagebox.askyesno("Usuń Pliki Fizycznie",
                                   f"Czy chcesz również fizycznie usunąć WSZYSTKIE ({len(tracks_to_process_for_cleanup)}) pliki muzyczne\n"
                                   f"z playlisty '{self.active_playlist_name}' znajdujące się w wewnętrznej bibliotece?\n\n"
                                   "Tej operacji NIE MOŻNA cofnąć!",
                                   parent=self.parent_frame, icon='warning'):
                
                # Pokaż pasek postępu dla usuwania plików
                delete_op_title = f"Usuwanie plików z '{self.active_playlist_name}'"
                self.launcher.show_progress_window(delete_op_title)
                if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                    self.launcher.progress_bar['maximum'] = len(tracks_to_process_for_cleanup)
                    self.launcher.progress_bar['value'] = 0
                    self.launcher.progress_bar['mode'] = 'determinate'
                
                deleted_music_files_count = 0
                for i, track_entry_to_check in enumerate(tracks_to_process_for_cleanup):
                    if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                        self.launcher.progress_label.config(text=f"Usuwanie pliku {i+1}/{len(tracks_to_process_for_cleanup)}...")
                        self.launcher.progress_bar['value'] = i
                        self.launcher.progress_window.update_idletasks()

                    if track_entry_to_check.get('is_internal') is True:
                        path_to_delete = track_entry_to_check.get('path')
                        if path_to_delete and os.path.exists(path_to_delete) and \
                           os.path.abspath(path_to_delete).startswith(os.path.abspath(INTERNAL_MUSIC_DIR)):
                            try:
                                os.remove(path_to_delete)
                                physical_music_files_to_delete_paths.add(path_to_delete) # Dodaj do zbioru usuniętych
                                deleted_music_files_count +=1
                                logging.info(f"Fizycznie usunięto (Wyczyść Kolejkę): {path_to_delete}")
                            except OSError as e_del_music:
                                logging.error(f"Błąd fizycznego usuwania pliku '{path_to_delete}' (Wyczyść Kolejkę): {e_del_music}")
                
                if hasattr(self.launcher, 'progress_window') and self.launcher.progress_window.winfo_exists():
                    self.launcher.progress_window.destroy()
                if deleted_music_files_count > 0:
                     messagebox.showinfo("Pliki Usunięte", f"Fizycznie usunięto {deleted_music_files_count} plików muzycznych.", parent=self.parent_frame)
        # --- Koniec logiki usuwania plików muzycznych ---


        # --- Usuwanie okładek ---
        abs_images_music_covers_dir = os.path.abspath(os.path.join(IMAGES_FOLDER, "music_covers"))
        for track_entry_cleaned in tracks_to_process_for_cleanup: # Iteruj po utworach, które były na czyszczonej playliście
            original_path_cleaned = track_entry_cleaned.get('path')
            if not original_path_cleaned: continue

            # Sprawdź, czy ten utwór (ta sama ścieżka) istnieje jeszcze na JAKIEJKOLWIEK *INNEJ* playliście
            is_on_any_other_playlist_after_clear = False
            for pl_name, other_entries in self.named_playlists.items():
                if pl_name != self.active_playlist_name: # Sprawdzamy tylko *inne* playlisty
                    if any(entry.get('path') == original_path_cleaned for entry in other_entries):
                        is_on_any_other_playlist_after_clear = True
                        break
            
            # Usuń okładki jeśli:
            # 1. Ścieżka pliku muzycznego została fizycznie usunięta LUB
            # 2. Utwór nie występuje już na ŻADNEJ INNEJ playliście (czyli czyszczona była ostatnią)
            if (original_path_cleaned in physical_music_files_to_delete_paths) or \
               (not is_on_any_other_playlist_after_clear):
                
                logging.debug(f"Czyszczenie okładek dla '{original_path_cleaned}' (plik usunięty: {original_path_cleaned in physical_music_files_to_delete_paths}, nie na innych: {not is_on_any_other_playlist_after_clear})")
                
                focus_cover_to_clear = track_entry_cleaned.get('focus_cover_path')
                if focus_cover_to_clear and os.path.exists(focus_cover_to_clear) and \
                   os.path.abspath(focus_cover_to_clear).startswith(abs_images_music_covers_dir):
                    try:
                        os.remove(focus_cover_to_clear)
                        logging.info(f"Usunięto okładkę Focus (Wyczyść Kolejkę): {focus_cover_to_clear}")
                    except OSError as e_fc_clear:
                        logging.error(f"Błąd usuwania okładki Focus '{focus_cover_to_clear}' (Wyczyść Kolejkę): {e_fc_clear}")

                lastfm_cover_to_clear = track_entry_cleaned.get('lastfm_cover_path')
                if lastfm_cover_to_clear and os.path.exists(lastfm_cover_to_clear) and \
                   os.path.abspath(lastfm_cover_to_clear).startswith(abs_images_music_covers_dir):
                    try:
                        os.remove(lastfm_cover_to_clear)
                        logging.info(f"Usunięto okładkę LastFM (Wyczyść Kolejkę): {lastfm_cover_to_clear}")
                    except OSError as e_lfm_clear:
                        logging.error(f"Błąd usuwania okładki LastFM '{lastfm_cover_to_clear}' (Wyczyść Kolejkę): {e_lfm_clear}")
        
        # Faktyczne wyczyszczenie nazwanej playlisty
        self.named_playlists[self.active_playlist_name] = []
        logging.info(f"Wyczyszczono wszystkie wpisy z nazwanej playlisty: '{self.active_playlist_name}'")

        # Wyczyść bieżącą kolejkę (self.playlist), oryginalną kolejność i wyświetlane ścieżki
        self.playlist.clear()
        self.original_playlist_order.clear()
        self.currently_displayed_paths.clear() 

        if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
            self.playlist_listbox.delete(0, tk.END)
        
        self.current_track_index = -1
        self.is_playing = False
        self.is_paused = False

        self._update_now_playing_label(track_name_override="Nic nie gra", duration_sec=0, current_pos_sec=0)
        if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
            self.play_pause_button.config(text="▶") # Symbol Play
        if hasattr(self, 'progress_scale') and self.progress_scale.winfo_exists():
            self.progress_scale_var.set(0.0)
            self.progress_scale.config(state=tk.DISABLED, to=100)
        
        self._update_fav_button_text() # Zaktualizuj serduszko (powinno być puste)

        if was_playing_or_paused:
            if hasattr(self.launcher, '_update_discord_status'):
                current_browsing_activity = self.launcher.current_section if hasattr(self.launcher, 'current_section') and self.launcher.current_section else "W menu głównym"
                self.launcher._update_discord_status(status_type="browsing", activity_details=current_browsing_activity)

        logging.info("Bieżąca kolejka odtwarzania i zawartość aktywnej nazwanej playlisty zostały wyczyszczone.")
        self._save_player_settings()
        if hasattr(self.launcher, 'track_overlay') and self.launcher.track_overlay and self.launcher.track_overlay.winfo_exists():
            self.launcher.track_overlay.update_display("Nic nie gra...", 0, 0, False)

    def _change_volume_by_step(self, step_percent: int):
        """Zmienia głośność o podany krok procentowy."""
        if not pygame.mixer.get_init(): return
        if not hasattr(self, 'volume_scale'): return

        current_volume_percent = self.volume_scale.get()
        new_volume_percent = current_volume_percent + step_percent
        new_volume_percent = max(0, min(100, new_volume_percent)) # Ogranicz do 0-100

        self.volume_scale.set(new_volume_percent) # To wywoła self._set_volume
        # self._set_volume(str(new_volume_percent)) # Lub bezpośrednio, jeśli set() nie triggeruje command

    # --- NOWA METODA PRYWATNA ---
    def _play_track(self, track_index_in_playlist: int): # Argument to teraz indeks w self.playlist
        """Ładuje i odtwarza utwór (słownik) o podanym indeksie z self.playlist."""
        if not pygame.mixer.get_init():
            logging.warning("Próba odtworzenia utworu, ale mixer nie jest zainicjalizowany.")
            return
        
        # --- ZMIANA: Sprawdzanie indeksu i pobieranie słownika utworu ---
        if not self.playlist or not (0 <= track_index_in_playlist < len(self.playlist)):
            logging.warning(f"Nieprawidłowy indeks utworu: {track_index_in_playlist} lub pusta playlista (długość: {len(self.playlist)}).")
            self._stop_music()
            return

        current_track_entry = self.playlist[track_index_in_playlist]
        track_path = current_track_entry.get('path')

        if not track_path or not os.path.exists(track_path):
            logging.error(f"Ścieżka utworu jest nieprawidłowa lub plik nie istnieje: '{track_path}'. Usuwanie z playlisty.")
            # Usuń ten wadliwy wpis z named_playlists i odśwież
            self._remove_track_entry_from_all_playlists(current_track_entry) # Nowa metoda pomocnicza
            # Spróbuj odtworzyć następny, jeśli jest
            if self.playlist: # Jeśli po usunięciu coś zostało
                next_idx_candidate = track_index_in_playlist # Spróbuj ten sam indeks (który teraz ma inny utwór) lub następny
                if next_idx_candidate >= len(self.playlist):
                     next_idx_candidate = 0 # Lub _get_next_track_index()?
                if self.playlist : self._play_track(next_idx_candidate if next_idx_candidate < len(self.playlist) else 0)
                else: self._stop_music()
            else:
                self._stop_music()
            return
        # --- KONIEC ZMIANY ---

        try:
            logging.info(f"Ładowanie utworu: {track_path}")
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.play()
            self._start_time = time.monotonic() # Czas monotoniczny dla dokładniejszego śledzenia
            self._pause_acc = 0.0
            
            # --- ZMIANA: Ustaw `current_track_index` na przekazany `track_index_in_playlist` ---
            self.current_track_index = track_index_in_playlist
            # --- KONIEC ZMIANY ---
            self.is_playing = True
            self.is_paused = False
            
            if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
                self.play_pause_button.config(text="❚❚ Pause") # Lub ikona

            self._current_track_duration_sec = self._get_track_length(track_path)
            logging.debug(f"Ustawiona długość utworu dla '{os.path.basename(track_path)}': {self._current_track_duration_sec:.2f}s")

            if hasattr(self, 'progress_scale') and self.progress_scale.winfo_exists():
                length_for_scale = max(self._current_track_duration_sec, 1.0)
                self.progress_scale.config(to=length_for_scale, state=tk.NORMAL)
                self.progress_scale_var.set(0.0)

            self._update_now_playing_label(duration_sec=self._current_track_duration_sec, current_pos_sec=0)
            self._update_fav_button_text() # Zaktualizuj status serduszka

            if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
                self.playlist_listbox.selection_clear(0, tk.END)
                # --- ZMIANA: Zaznaczanie na podstawie słownika utworu ---
                if current_track_entry in self.currently_displayed_paths:
                    try:
                        display_idx = self.currently_displayed_paths.index(current_track_entry)
                        self.playlist_listbox.selection_set(display_idx)
                        self.playlist_listbox.activate(display_idx)
                        self.playlist_listbox.see(display_idx)
                    except (tk.TclError, ValueError) as e_listbox:
                        logging.error(f"Błąd podczas ustawiania zaznaczenia dla '{track_path}': {e_listbox}")
                # --- KONIEC ZMIANY ---

            self.parent_frame.after(200, self._update_track_progress)
            if hasattr(self.launcher, '_update_discord_status'):
                self.launcher._update_discord_status()
            
            # Zapisz ostatnio odtwarzany indeks (ale tylko dla aktywnej playlisty w kontekście jej nazwy)
            self._save_player_settings()
            # <<< DODAJEMY NA KOŃCU >>>
            # jeśli jesteśmy w trybie kafelków, odśwież całą siatkę
            if self.music_library_view_mode.get() == "tiles":
                self._update_music_tiles_display()

        except pygame.error as e:
            logging.error(f"Błąd pygame podczas ładowania/odtwarzania '{track_path}': {e}")
            messagebox.showerror("Błąd Odtwarzania", f"Nie można odtworzyć pliku:\n{os.path.basename(track_path)}\n\nBłąd: {e}", parent=self.parent_frame)
            # Spróbuj usunąć wadliwy i przejść dalej
            self._remove_track_entry_from_all_playlists(current_track_entry)
            self._next_track() # Przejdź do następnego (który już uwzględni zmiany w playliście)
        except tk.TclError as e_tk:
             logging.error(f"Błąd TclError w _play_track (widget nie istnieje): {e_tk}")

    def _play_selected_from_playlist(self, event=None):
        """Odtwarza utwór (słownik) zaznaczony na playliście."""
        if not hasattr(self, 'playlist_listbox') or not self.playlist_listbox.winfo_exists(): return
        
        selection_indices = self.playlist_listbox.curselection()
        if not selection_indices:
            if self.currently_displayed_paths: # Jeśli nic nie zaznaczono, a są wyświetlane utwory, zagraj pierwszy
                # --- ZMIANA: `entry_to_play` to słownik ---
                entry_to_play = self.currently_displayed_paths[0]
                if entry_to_play in self.playlist: # Sprawdź, czy nadal jest w głównej playliście
                    try:
                        actual_index_in_main_list = self.playlist.index(entry_to_play)
                        self._play_track(actual_index_in_main_list)
                    except ValueError:
                        logging.warning(f"Utwór '{entry_to_play.get('path')}' z widoku nie znaleziony w self.playlist.")
                # --- KONIEC ZMIANY ---
            return

        selected_index_in_view = selection_indices[0]

        # --- ZMIANA: `selected_track_entry` to słownik ---
        if 0 <= selected_index_in_view < len(self.currently_displayed_paths):
            selected_track_entry = self.currently_displayed_paths[selected_index_in_view]
            if selected_track_entry in self.playlist:
                try:
                    actual_index_in_main_list = self.playlist.index(selected_track_entry)
                    self._play_track(actual_index_in_main_list)
                except ValueError:
                    logging.warning(f"Wybrany utwór '{selected_track_entry.get('path')}' nie znaleziony w self.playlist.")
                    self._update_playlist_display() # Na wszelki wypadek
            else:
                logging.warning(f"Wybrany utwór '{selected_track_entry.get('path')}' nie jest już częścią głównej playlisty.")
                self._update_playlist_display()
        # --- KONIEC ZMIANY ---
        else:
            logging.warning("Nieprawidłowy indeks zaznaczenia w _play_selected_from_playlist.")

    def _toggle_play_pause(self):
        """Przełącza między odtwarzaniem a pauzą z debouncingiem."""
        if not pygame.mixer.get_init(): return

        # Anuluj poprzedni timer debouncingu, jeśli istnieje
        if self._play_pause_debounce_timer:
            self.parent_frame.after_cancel(self._play_pause_debounce_timer)

        # Zaplanuj faktyczne przełączenie po opóźnieniu
        self._play_pause_debounce_timer = self.parent_frame.after(self._debounce_delay_ms, self._execute_play_pause)

    # --- NOWA METODA PRYWATNA do faktycznego wykonania akcji ---
    def _execute_play_pause(self):
        """Faktycznie wykonuje logikę play/pause."""
        self._play_pause_debounce_timer = None
        if not pygame.mixer.get_init(): return

        if self.is_playing: # Jeśli coś gra (może być spauzowane)
            if self.is_paused: # Jeśli jest spauzowane -> wznów
                pygame.mixer.music.unpause()
                # --- ZMIANA: Użyj getattr dla _pause_start, aby uniknąć błędu, jeśli nie było pauzy ---
                self._pause_acc += time.monotonic() - getattr(self, '_pause_start', time.monotonic())
                # --- KONIEC ZMIANY ---
                self.is_paused = False
                if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
                    self.play_pause_button.config(text="❚❚") # Symbol Pause
                logging.info("Wznowiono odtwarzanie muzyki.")
                self.parent_frame.after(50, self._update_track_progress)
            else: # Jeśli gra i nie jest spauzowane -> spauzuj
                pygame.mixer.music.pause()
                self._pause_start = time.monotonic()
                self.is_paused = True
                if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
                    self.play_pause_button.config(text="▶") # Symbol Play
                logging.info("Spauzowano muzykę.")
        else: # Jeśli nic nie grało -> zacznij grać
            if self.playlist:
                target_index_to_play = 0 # Domyślnie pierwszy utwór
                # Jeśli jest jakiś zaznaczony utwór, spróbuj go odtworzyć
                if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
                    selection = self.playlist_listbox.curselection()
                    if selection:
                        selected_view_idx = selection[0]
                        # --- ZMIANA: Pobierz słownik i jego indeks w self.playlist ---
                        selected_entry_in_view = self._get_actual_entry_from_view_index(selected_view_idx)
                        if selected_entry_in_view and selected_entry_in_view in self.playlist:
                            try:
                                target_index_to_play = self.playlist.index(selected_entry_in_view)
                            except ValueError: # Nie powinno się zdarzyć, jeśli logika jest spójna
                                logging.warning("Zaznaczony utwór z widoku nie znaleziony w self.playlist.")
                        # --- KONIEC ZMIANY ---
                    # Jeśli nic nie zaznaczono, a był zapamiętany current_track_index (np. po stopie)
                    elif self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                        target_index_to_play = self.current_track_index
                
                if 0 <= target_index_to_play < len(self.playlist):
                    self._play_track(target_index_to_play)
                else: # Na wypadek, gdyby playlista była pusta lub target_index był zły
                    messagebox.showinfo("Brak muzyki", "Playlista jest pusta lub wystąpił błąd indeksu.", parent=self.parent_frame)
            else:
                 messagebox.showinfo("Brak muzyki", "Dodaj utwory do playlisty...", parent=self.parent_frame)
        
        if hasattr(self.launcher, '_update_discord_status'):
            self.launcher._update_discord_status()

    # Metody _seek_relative, _seek_to_position, _get_track_length, _on_progress_scale_drag,
    # _begin_seek, _end_seek zazwyczaj operują na już załadowanym utworze i jego ścieżce,
    # więc nie powinny wymagać głębokich zmian, o ile _play_track poprawnie ustawia
    # `self._current_track_duration_sec` i obsługuje odtwarzanie z `track_path`.

    # Upewnij się, że w _seek_to_position() i _seek_relative() używasz
    # `track_path = self.playlist[self.current_track_index].get('path')`
    # do pobrania ścieżki przed `pygame.mixer.music.load(track_path)`.

    def _stop_music(self):
        """Zatrzymuje odtwarzanie muzyki i resetuje stan."""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        
        self.is_playing = False
        if hasattr(self.launcher, 'track_overlay') and self.launcher.track_overlay and self.launcher.track_overlay.winfo_exists():
            self.launcher.track_overlay.update_display("Nic nie gra...", 0, 0, False)
        self.is_paused = False
        # self.current_track_index = -1 # Nie resetuj tutaj, może chcemy zachować zaznaczenie

        if hasattr(self, 'play_pause_button') and self.play_pause_button.winfo_exists():
            self.play_pause_button.config(text="▶") # Symbol Play

        # Zresetuj etykiety i suwak (current_track_index może nadal być poprawny)
        self._update_now_playing_label(track_name_override="Nic nie gra", duration_sec=0, current_pos_sec=0)
        if hasattr(self, 'progress_scale') and self.progress_scale.winfo_exists():
            self.progress_scale_var.set(0.0)
            self.progress_scale.config(state=tk.DISABLED, to=100)
        
        # --- ZMIANA: Odznacz wszystko w Listboxie, jeśli stop ---
        if hasattr(self, 'playlist_listbox') and self.playlist_listbox.winfo_exists():
            self.playlist_listbox.selection_clear(0, tk.END)
        # Ustawienie current_track_index na -1 jest opcjonalne. Jeśli chcemy, aby "Play" zaczynał od
        # ostatnio zatrzymanego (lub pierwszego, jeśli -1), to można to zostawić.
        # Dla "czystego" stopu, reset current_track_index może być lepszy.
        # self.current_track_index = -1 # Zdecyduj, czy chcesz to zachowanie

        self._update_fav_button_text() # Zaktualizuj stan serduszka (powinien być "♡", jeśli nic nie gra)
                # --- ZMIANA: Bezpośrednia aktualizacja overlay'a po stopie ---
        if hasattr(self.launcher, 'track_overlay') and self.launcher.track_overlay and self.launcher.track_overlay.winfo_exists():
            self.launcher.track_overlay.update_display("Nic nie gra...", 0, 0, False) # is_active = False
        # --- KONIEC ZMIANY ---
        logging.info("Zatrzymano muzykę.")
        if hasattr(self.launcher, '_update_discord_status'):
            current_browsing_activity = self.launcher.current_section if hasattr(self.launcher, 'current_section') and self.launcher.current_section else "W menu głównym"
            self.launcher._update_discord_status(status_type="browsing", activity_details=current_browsing_activity)
        # Nie zapisujemy tu _save_player_settings(), bo sam stop nie zmienia trwałych ustawień.

    def _get_next_track_index(self) -> int: # Indeks w self.playlist
        """Zwraca INDEKS W self.playlist następnego utworu (słownika), uwzględniając tryby."""
        if not self.playlist: return -1 # Jeśli self.playlist jest pusta

        # Domyślnie: jeśli current_track_index jest nieustawiony, zacznij od początku `self.playlist`
        # Jest to ważne, gdy np. `self.playlist` nie jest tożsama z `self.currently_displayed_paths`
        # (np. po wyszukiwaniu, gdy klikamy "Next" - powinniśmy operować na pełnej `self.playlist`).
        effective_current_index_in_playlist = self.current_track_index
        if effective_current_index_in_playlist == -1 and self.playlist:
             effective_current_index_in_playlist = -1 # Traktuj jakbyśmy byli "przed" pierwszym

        num_tracks_in_playlist = len(self.playlist)
        next_playlist_index = -1

        if self.shuffle_mode and self.repeat_mode != "one":
            if num_tracks_in_playlist == 0: return -1
            if num_tracks_in_playlist == 1:
                next_playlist_index = 0
            else:
                available_indices = list(range(num_tracks_in_playlist))
                if effective_current_index_in_playlist in available_indices:
                    available_indices.remove(effective_current_index_in_playlist)
                if not available_indices: # Powinno się zdarzyć tylko jeśli num_tracks_in_playlist == 1
                     next_playlist_index = effective_current_index_in_playlist if effective_current_index_in_playlist != -1 else 0
                else:
                    next_playlist_index = random.choice(available_indices)
        else: # Kolejność standardowa lub powtarzanie jednego
            if self.repeat_mode == "one" and effective_current_index_in_playlist != -1:
                next_playlist_index = effective_current_index_in_playlist
            elif effective_current_index_in_playlist < num_tracks_in_playlist - 1:
                next_playlist_index = effective_current_index_in_playlist + 1
            elif self.repeat_mode == "all" and num_tracks_in_playlist > 0:
                next_playlist_index = 0
            else: # Koniec playlisty i brak powtarzania
                return -1
        
        return next_playlist_index

    # Metoda _get_prev_track_index analogicznie będzie zwracać indeks w self.playlist

    # Metody _next_track i _prev_track teraz wywołują _play_track z indeksem z self.playlist
    # (ich uproszczona logika z poprzedniej odpowiedzi była już prawie gotowa)

    def _next_track(self):
        if not self.playlist: self._stop_music(); logging.debug("NextTrack: Playlista pusta."); return
        
        candidate_index = -1
        if self.repeat_mode == "one" and self.current_track_index != -1:
            # Przy kliknięciu "Next" chcemy wyjść z pętli jednego utworu,
            # więc tymczasowo traktujemy jakby repeat_mode był "none"
            original_repeat_mode = self.repeat_mode
            self.repeat_mode = "none" 
            candidate_index = self._get_next_track_index() # Znajdź następny w self.playlist
            self.repeat_mode = original_repeat_mode
        else:
            candidate_index = self._get_next_track_index() # Znajdź następny w self.playlist

        if candidate_index != -1:
            self._play_track(candidate_index)
        else:
            self._stop_music(); logging.debug("NextTrack: Brak następnego, zatrzymano.")
    # ─────────────────────────────────────────────────────────────────────
    #  NOWA FUNKCJA:  poprzedni indeks zgodny z aktualnym widokiem listy
    # ─────────────────────────────────────────────────────────────────────
    def _get_prev_track_index(self) -> int:
        """
        Zwraca indeks (w self.playlist) poprzedniego utworu, biorąc pod uwagę:
        • aktualnie wyświetlaną listę (self.currently_displayed_paths),
        • tryby shuffle / repeat,
        • powtarzanie jednego utworu („one”) lub całej listy („all”).
        W przypadku braku poprzedniego utworu – zwraca ‑1.
        """
        #   1. brak czegokolwiek do odtwarzania → -1
        if not self.playlist or not self.currently_displayed_paths:
            return -1

        #   2. pełna ścieżka aktualnie granego utworu
        cur_path = None
        if 0 <= self.current_track_index < len(self.playlist):
            cur_path = self.playlist[self.current_track_index]

        #   3. indeks tego utworu na LIŚCIE WIDOCZNEJ
        try:
            cur_disp_idx = self.currently_displayed_paths.index(cur_path)
        except (ValueError, TypeError):
            cur_disp_idx = -1      # nic jeszcze nie grało albo utwór spoza widoku

        n_disp = len(self.currently_displayed_paths)
        prev_disp_idx = -1         # indeks na liście wyświetlanej

        if self.shuffle_mode and self.repeat_mode != "one":
            # losowy utwór ≠ bieżący
            choices = [i for i in range(n_disp) if i != cur_disp_idx]
            prev_disp_idx = random.choice(choices) if choices else cur_disp_idx
        else:
            # liniowo wstecz
            if self.repeat_mode == "one" and cur_disp_idx != -1:
                prev_disp_idx = cur_disp_idx
            elif cur_disp_idx > 0:
                prev_disp_idx = cur_disp_idx - 1
            elif self.repeat_mode == "all":
                prev_disp_idx = n_disp - 1
            else:
                return -1   # początek listy i brak zapętlenia

        #   4. mapa z powrotem: ścieżka → indeks w self.playlist
        if 0 <= prev_disp_idx < n_disp:
            path = self.currently_displayed_paths[prev_disp_idx]
            try:
                return self.playlist.index(path)
            except ValueError:
                # niespójność (nie powinno się zdarzyć)
                return -1
        return -1
    # ─────────────────────────────────────────────────────────────────────


    def _prev_track(self):
        if not self.playlist: self._stop_music(); logging.debug("PrevTrack: Playlista pusta."); return

        candidate_index = -1
        if self.repeat_mode == "one" and self.current_track_index != -1:
            # Podobnie, wyjdź z pętli jednego
            original_repeat_mode = self.repeat_mode
            self.repeat_mode = "none" 
            candidate_index = self._get_prev_track_index() # Znajdź poprzedni w self.playlist
            self.repeat_mode = original_repeat_mode
        else:
            candidate_index = self._get_prev_track_index() # Znajdź poprzedni w self.playlist
            
        if candidate_index != -1:
            self._play_track(candidate_index)
        else: # Brak poprzedniego
            # Można odtworzyć bieżący od początku, jeśli jest na początku i gra
            if self.is_playing and self.current_track_index == 0:
                self._play_track(0) # Odtwórz od nowa pierwszy
            else:
                self._stop_music(); logging.debug("PrevTrack: Brak poprzedniego, zatrzymano.")


    # --- NOWA METODA POMOCNICZA DO USUWANIA BŁĘDNYCH WPISÓW ---
    def _remove_track_entry_from_all_playlists(self, track_entry_to_remove: dict):
        """Usuwa dany wpis (słownik) utworu ze wszystkich miejsc."""
        if not track_entry_to_remove or not isinstance(track_entry_to_remove, dict):
            return

        path_to_remove = track_entry_to_remove.get('path')
        if not path_to_remove: return

        logging.info(f"Usuwanie błędnego/nieistniejącego utworu: {path_to_remove}")

        # Usuń z named_playlists
        for pl_name, entries in self.named_playlists.items():
            self.named_playlists[pl_name] = [entry for entry in entries if entry.get('path') != path_to_remove]
        
        # Usuń z ulubionych (jeśli tam był)
        if path_to_remove in self.favorite_tracks:
            self.favorite_tracks.remove(path_to_remove)
        
        # Odśwież self.playlist, original_playlist_order i current_track_index
        current_playing_path_before_removal = None
        if self.is_playing and self.current_track_index != -1 and self.current_track_index < len(self.playlist):
             current_playing_path_before_removal = self.playlist[self.current_track_index].get('path')

        self._load_active_playlist() # To odbuduje self.playlist i self.original_playlist_order

        # Spróbuj przywrócić indeks odtwarzania
        if current_playing_path_before_removal:
            self.current_track_index = -1 # Zresetuj
            for i, entry in enumerate(self.playlist):
                if entry.get('path') == current_playing_path_before_removal:
                    self.current_track_index = i
                    break
            # Jeśli nie znaleziono (np. był to jedyny usunięty utwór), current_track_index pozostanie -1

        self._update_playlist_display() # Odśwież widok
        self._save_player_settings()   # Zapisz zmiany


    def _set_volume(self, value_str): # Zmieniono nazwę argumentu dla jasności
        if pygame.mixer.get_init():
            value = float(value_str) # Konwertuj string na float
            volume_float = value / 100
            pygame.mixer.music.set_volume(volume_float)
            # --- NOWE: Aktualizuj etykietę procentów ---
            if hasattr(self, 'volume_percent_label'):
                self.volume_percent_label.config(text=f"{int(value)}%")
            # --- KONIEC NOWEGO ---
            # Nie zapisujemy tutaj za każdym razem, _save_player_settings() zrobi to przy zamykaniu
            # self.local_settings["music_player_volume"] = volume_float

# W klasie MusicPlayerPage

    def _update_track_progress(self):
        """Aktualizuje wyświetlany czas utworu i suwak postępu oraz sprawdza, czy utwór się nie skończył."""
        if not pygame.mixer.get_init(): return
        
        if self.is_playing and not self.is_paused:
            try:
                current_pos_sec = time.monotonic() - self._start_time - self._pause_acc
                if current_pos_sec < 0: # Sanity check
                    current_pos_sec = 0.0

                track_duration = getattr(self, '_current_track_duration_sec', 0.0)

                # Sprawdzenie końca utworu
                has_ended = False
                if not pygame.mixer.music.get_busy(): # Główny warunek końca
                    has_ended = True
                
                if not has_ended and track_duration > 0.1: 
                    if current_pos_sec >= track_duration - 0.15: # 0.15s marginesu
                        if not pygame.mixer.music.get_busy(): # Sprawdź ponownie
                             has_ended = True

                if has_ended:
                    current_playing_filename_display = "Nieznany"
                    if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
                        # Użyj _get_display_name_for_track dla poprawnego formatowania (i usuń serduszko)
                        current_playing_filename_display = self._get_display_name_for_track(self.playlist[self.current_track_index]).replace("♥ ","")
                    logging.info(f"Koniec utworu: '{current_playing_filename_display}'")

                    # --- NOWA, POPRAWIONA LOGIKA DECYZJI PO ZAKOŃCZENIU UTWORU ---
                    if self.repeat_mode == "one":
                        logging.debug("Koniec utworu: Repeat One. Odtwarzam ten sam utwór.")
                        self._play_track(self.current_track_index) # Odtwórz ten sam
                    elif self.repeat_mode == "all":
                        logging.debug("Koniec utworu: Repeat All. Próba przejścia do następnego/początku listy.")
                        next_idx_candidate = self._get_next_track_index_for_auto_advance()
                        if next_idx_candidate != -1:
                            self._play_track(next_idx_candidate)
                        else:
                            logging.warning("Koniec utworu: Repeat All, ale _get_next_track_index_for_auto_advance zwrócił -1. Zatrzymuję.")
                            self._stop_music()
                    elif self.autoplay: # repeat_mode jest "none", ale autoplay jest "True"
                        logging.debug("Koniec utworu: Repeat None, Autoplay True. Próba przejścia do następnego.")
                        next_idx_candidate = self._get_next_track_index_for_auto_advance()
                        if next_idx_candidate != -1:
                            self._play_track(next_idx_candidate)
                        else:
                            logging.debug("Koniec utworu: Autoplay True, ale brak następnego utworu (koniec playlisty). Zatrzymuję.")
                            self._stop_music()
                    else: # repeat_mode jest "none" ORAZ autoplay jest "False"
                        logging.debug("Koniec utworu: Repeat None, Autoplay False. Zatrzymuję muzykę.")
                        self._stop_music()
                    # --- KONIEC NOWEJ, POPRAWIONEJ LOGIKI ---
                    return # Ważne: zakończ to wywołanie

                # Jeśli utwór się NIE zakończył, aktualizuj UI
                if not getattr(self, '_seeking', False):
                    self._update_now_playing_label(duration_sec=track_duration, current_pos_sec=current_pos_sec)
                    if hasattr(self, 'progress_scale') and self.progress_scale.winfo_exists():
                        max_scale_val = track_duration if track_duration > 0 else 1.0
                        current_scale_val = current_pos_sec if track_duration > 0 else 0.0
                        if self.progress_scale.cget('to') != max_scale_val:
                            try: # Dodatkowe zabezpieczenie przy konfiguracji
                                self.progress_scale.config(to=max_scale_val)
                            except tk.TclError as e_scale_config:
                                logging.warning(f"Błąd TclError podczas konfiguracji 'to' dla progress_scale: {e_scale_config}")
                        self.progress_scale_var.set(min(current_scale_val, max_scale_val))

            except pygame.error as e:
                logging.error(f"Błąd pygame podczas aktualizacji postępu utworu: {e}")
                self._stop_music()
                return
            except IndexError:
                logging.warning("IndexError w _update_track_progress, playlista mogła ulec zmianie.")
                self._stop_music()
                return
            except tk.TclError as e_tk:
                logging.warning(f"Błąd TclError w _update_track_progress (widget mógł zniknąć): {e_tk}")
                return

            if self.is_playing and not self.is_paused and hasattr(self.parent_frame, 'after'):
                self.parent_frame.after(250, self._update_track_progress)

        elif not self.is_playing: # Jeśli odtwarzanie zostało zatrzymane
            # --- ZMIANA: Użyj track_name_override ---
            self._update_now_playing_label(track_name_override="Nic nie gra", duration_sec=0, current_pos_sec=0)
            # --- KONIEC ZMIANY ---
            if hasattr(self, 'progress_scale') and self.progress_scale.winfo_exists():
                try: # Dodatkowe zabezpieczenie
                    self.progress_scale_var.set(0.0)
                    self.progress_scale.config(state=tk.DISABLED, to=100)
                except tk.TclError as e_scale_config_disabled:
                    logging.warning(f"Błąd TclError podczas konfigurowania progress_scale na disabled: {e_scale_config_disabled}")

    # --- NOWA METODA POMOCNICZA ---
    def _get_next_track_index_for_auto_advance(self) -> int:
        """
        Zwraca indeks następnego utworu do automatycznego odtworzenia.
        Używana przez _update_track_progress. Uwzględnia repeat:all.
        Jeśli repeat jest 'none' i autoplay jest włączone, a lista się skończyła, zwraca -1.
        """
        if not self.playlist or not self.currently_displayed_paths:
            return -1

        current_playing_path_in_main_list = None
        if self.current_track_index != -1 and self.current_track_index < len(self.playlist):
            current_playing_path_in_main_list = self.playlist[self.current_track_index]

        current_display_index = -1
        if current_playing_path_in_main_list and current_playing_path_in_main_list in self.currently_displayed_paths:
            try:
                current_display_index = self.currently_displayed_paths.index(current_playing_path_in_main_list)
            except ValueError:
                current_display_index = -1

        num_displayed_tracks = len(self.currently_displayed_paths)
        next_display_index = -1

        if self.shuffle_mode: # Jeśli shuffle, wybierz losowy inny
            if num_displayed_tracks == 0: return -1
            if num_displayed_tracks == 1:
                 # Jeśli tylko jeden utwór i jest repeat:all, to go weź, inaczej -1
                 return 0 if self.repeat_mode == "all" else -1 
            
            available_display_indices = list(range(num_displayed_tracks))
            if current_display_index in available_display_indices:
                available_display_indices.remove(current_display_index)
            
            if not available_display_indices: # Powinno się zdarzyć tylko jeśli num_displayed_tracks == 1
                return current_display_index if self.repeat_mode == "all" else -1
            else:
                next_display_index = random.choice(available_display_indices)
        else: # Kolejność standardowa
            if current_display_index < num_displayed_tracks - 1:
                next_display_index = current_display_index + 1
            elif self.repeat_mode == "all" and num_displayed_tracks > 0: # Ostatni, ale repeat:all
                next_display_index = 0
            else: # Koniec listy i brak repeat:all
                return -1

        # Przekonwertuj display_index z powrotem na indeks w self.playlist
        if 0 <= next_display_index < num_displayed_tracks:
            next_track_path_to_play = self.currently_displayed_paths[next_display_index]
            try:
                return self.playlist.index(next_track_path_to_play)
            except ValueError:
                return -1
        return -1
    # --- KONIEC NOWEJ METODY POMOCNICZEJ ---
    def import_internal_music(self):
        folder = filedialog.askdirectory(title="Wybierz folder z muzyką")
        if not folder:
            return

        # --- nowy Toplevel z Progressbarem ---
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Importowanie muzyki…")
        bar = ttk.Progressbar(progress_win, length=400, mode='determinate')
        bar.pack(padx=15, pady=15)
        files = os.listdir(folder)
        bar['maximum'] = len(files)

        # funkcja kopiuje pliki w tle i aktualizuje pasek
        def do_copy():
            for idx, file in enumerate(files, start=1):
                src = os.path.join(folder, file)
                dest = os.path.join(INTERNAL_MUSIC_DIR, file)
                shutil.copy2(src, dest)
                # aktualizacja paska w wątku GUI via after
                progress_win.after(0, lambda v=idx: bar.config(value=v))
            # po zakończeniu zamknij okno
            progress_win.after(0, progress_win.destroy)

        threading.Thread(target=do_copy, daemon=True).start()

        # --- koniec nowego bloku ---
 
         # odśwież listę w launcherze
        self.refresh_music_list()
    # --- NOWA METODA ---
    def _on_progress_scale_drag(self, value_str):
        """Obsługuje zmianę pozycji suwaka postępu przez użytkownika."""
        if not pygame.mixer.get_init() or not self.is_playing:
            return # Nie rób nic, jeśli muzyka nie gra lub mixer nie działa

        try:
            new_position_sec = float(value_str)
            # Sprawdź, czy pozycja się faktycznie zmieniła (aby uniknąć pętli przy programowym ustawianiu)
            # To jest trudne, bo command jest wywoływany przy programowym set()
            # Dodamy flagę, aby to kontrolować
            if hasattr(self, '_is_seeking_by_user') and self._is_seeking_by_user:
                if pygame.mixer.music.get_busy(): # Tylko jeśli muzyka gra
                    # Pygame.mixer.music.set_pos() nie działa dla MP3.
                    # Pygame.mixer.music.play(start=new_position_sec) restartuje utwór.
                    # Dla MP3 jedynym sposobem jest ponowne załadowanie i play z pozycją startową.
                    logging.info(f"Użytkownik przewija do: {new_position_sec:.2f}s")
                    # Zapisz aktualny stan pauzy
                    was_paused = self.is_paused
                    pygame.mixer.music.stop() # Zatrzymaj, aby móc użyć play(start=...)
                    pygame.mixer.music.play(start=new_position_sec)
                    if was_paused: # Jeśli było spauzowane, spauzuj ponownie
                        pygame.mixer.music.pause()
                    else: # Jeśli grało, upewnij się, że is_paused jest False
                         self.is_paused = False
                         self.play_pause_button.config(text="❚❚ Pause") # Upewnij się, że przycisk jest poprawny

                    # Zaktualizuj czas od razu (może być małe opóźnienie zanim get_pos() zadziała)
                    self._update_now_playing_label(duration_sec=getattr(self, '_current_track_duration_sec', 0), current_pos_sec=new_position_sec)
        except ValueError:
            logging.warning("Nieprawidłowa wartość z suwaka postępu.")
        except pygame.error as e:
            logging.error(f"Błąd pygame podczas przewijania utworu: {e}")
        finally:
            if hasattr(self, '_is_seeking_by_user'):
                self._is_seeking_by_user = False
from .shared_imports import (
    tk,
    ttk,
    messagebox,
    filedialog,
    logging,
    pygame,
    os,
    time,
    random,
    threading,
    Image,
    ImageTk,
    ImageDraw,
    ImageFont,
    requests,
    pylast,
    MutagenFile,
    shutil,
    re,
)
from .constants import IMAGES_FOLDER, INTERNAL_MUSIC_DIR, THEMES
from .utils import save_config
from .tooltip import ToolTip


