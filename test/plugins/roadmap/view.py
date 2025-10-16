# plugins/roadmap/view.py
import customtkinter as ctk

class RoadmapView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        
        # Mapa przechowująca 'Nazwa Gry': 'ID Gry' dla menu wyboru
        self.game_selector_map = {}
        
        self._setup_ui()
        self.refresh_view()

    def _setup_ui(self):
        """Tworzy statyczne elementy interfejsu."""
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=10, pady=10)
        
        add_label = ctk.CTkLabel(add_frame, text="Dodaj grę do roadmapy:")
        add_label.pack(side="left", padx=10)

        self.game_selector = ctk.CTkOptionMenu(add_frame, values=["Ładowanie..."])
        self.game_selector.pack(side="left", padx=10)
        
        self.add_button = ctk.CTkButton(add_frame, text="Dodaj", width=100, command=self._add_selected_game_to_roadmap)
        self.add_button.pack(side="left", padx=10)

        self.columns_container = ctk.CTkFrame(self, fg_color="transparent")
        self.columns_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.columns_container.grid_columnconfigure((0, 1, 2), weight=1)
        self.columns_container.grid_rowconfigure(0, weight=1)

    def refresh_view(self):
        """Czyści i ponownie tworzy całą zawartość widoku."""
        # --- NOWY SPOSÓB POBIERANIA DANYCH ---
        library_data = self.app_context.data_manager.get_plugin_data('library')
        all_games = library_data.get('games', [])
        
        roadmap_data = self.app_context.data_manager.get_plugin_data('roadmap')
        roadmap_entries = roadmap_data.get('entries', [])
        
        roadmap_game_ids = [entry['game_id'] for entry in roadmap_entries]
        
        # --- Aktualizacja listy gier w dropdownie ---
        available_games = {game['name']: game['id'] for game in all_games if game['id'] not in roadmap_game_ids}
        self.game_selector_map = available_games
        
        if available_games:
            self.game_selector.configure(values=list(available_games.keys()))
            self.game_selector.set(list(available_games.keys())[0])
            self.game_selector.configure(state="normal")
            self.add_button.configure(state="normal")
        else:
            self.game_selector.configure(values=["Brak gier do dodania"])
            self.game_selector.set("Brak gier do dodania")
            self.game_selector.configure(state="disabled")
            self.add_button.configure(state="disabled")

        # Czyszczenie starych kolumn
        for widget in self.columns_container.winfo_children():
            widget.destroy()

        # Tworzenie kolumn i ich zawartości
        statuses = ["Planowane", "W trakcie", "Ukończone"]
        game_id_to_name = {game['id']: game['name'] for game in all_games}

        for i, status in enumerate(statuses):
            column_frame = ctk.CTkFrame(self.columns_container)
            column_frame.grid(row=0, column=i, sticky="nsew", padx=5)
            
            title = ctk.CTkLabel(column_frame, text=status, font=("Roboto", 16, "bold"))
            title.pack(fill="x", pady=10)

            entries_for_status = [entry for entry in roadmap_entries if entry['status'] == status]
            
            for entry in entries_for_status:
                game_name = game_id_to_name.get(entry['game_id'], "Nieznana gra")
                self._create_roadmap_card(column_frame, entry, game_name, statuses)

    def _create_roadmap_card(self, parent, entry_data, game_name, all_statuses):
        """Tworzy pojedynczą kartę gry w kolumnie."""
        card = ctk.CTkFrame(parent, border_width=1)
        card.pack(fill="x", padx=10, pady=5)
        
        label = ctk.CTkLabel(card, text=game_name)
        label.pack(side="left", padx=10, pady=10)
        
        status_menu = ctk.CTkOptionMenu(card, values=all_statuses,
            command=lambda new_status, g_id=entry_data['game_id']: self._change_status(g_id, new_status))
        status_menu.set(entry_data['status'])
        status_menu.pack(side="right", padx=10, pady=10)

    def _add_selected_game_to_roadmap(self):
        selected_game_name = self.game_selector.get()
        if selected_game_name in self.game_selector_map:
            game_id_to_add = self.game_selector_map[selected_game_name]
            
            # --- NOWY SPOSÓB ZAPISU ---
            roadmap_data = self.app_context.data_manager.get_plugin_data('roadmap')
            entries = roadmap_data.get('entries', [])
            entries.append({"game_id": game_id_to_add, "status": "Planowane"})
            roadmap_data['entries'] = entries
            self.app_context.data_manager.save_plugin_data('roadmap', roadmap_data)
            
            self.refresh_view()

    def _change_status(self, game_id, new_status):
        # --- NOWY SPOSÓB AKTUALIZACJI ---
        roadmap_data = self.app_context.data_manager.get_plugin_data('roadmap')
        entries = roadmap_data.get('entries', [])
        for entry in entries:
            if entry['game_id'] == game_id:
                entry['status'] = new_status
                break
        roadmap_data['entries'] = entries
        self.app_context.data_manager.save_plugin_data('roadmap', roadmap_data)
        
        self.refresh_view()