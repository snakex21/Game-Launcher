# plugins/library/view.py
import customtkinter as ctk
from .game_card import GameCard
from .add_game_window import AddGameWindow
from .post_session_window import PostSessionWindow

class LibraryView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.add_game_win_instance = None
        self.post_session_win_instance = None # Do śledzenia okna
        
        self.app_context.event_manager.subscribe("session_ended", self.on_session_ended)

        # --- Górny pasek z przyciskami i przełącznikiem ---
        top_bar_frame = ctk.CTkFrame(self)
        top_bar_frame.pack(fill="x", pady=(0, 10))

        # Przełącznik widoku
        self.view_mode_switch = ctk.CTkSwitch(top_bar_frame, text="Widok okładek", command=self.toggle_view_mode)
        self.view_mode_switch.pack(side="left", padx=15, pady=10)
        
        ctk.CTkButton(top_bar_frame, text="Dodaj nową grę", command=self.open_add_game_window).pack(side="right", padx=10, pady=10)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Twoja Biblioteka Gier")
        self.scrollable_frame.pack(fill="both", expand=True)

        self.refresh_view()

    def toggle_view_mode(self):
        """Zmienia tryb widoku i zapisuje go."""
        new_mode = "rich" if self.view_mode_switch.get() == 1 else "simple"
        library_data = self.app_context.data_manager.get_plugin_data('library')
        library_data['view_mode'] = new_mode
        self.app_context.data_manager.save_plugin_data('library', library_data)
        self.refresh_view()

    def refresh_view(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        library_data = self.app_context.data_manager.get_plugin_data('library')
        view_mode = library_data.get('view_mode', 'simple')

        # Ustawienie przełącznika
        if view_mode == 'rich':
            self.view_mode_switch.select()
        else:
            self.view_mode_switch.deselect()

        self.load_games(view_mode)

    def load_games(self, view_mode):
        library_data = self.app_context.data_manager.get_plugin_data('library')
        games = library_data.get('games', [])
        
        # Konfiguracja siatki w zależności od widoku
        if view_mode == 'rich':
            self.scrollable_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1) # 5 kolumn dla okładek
            max_cols = 5
        else: # simple
            self.scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1) # 4 kolumny
            max_cols = 4

        row, col = 0, 0
        for game in games:
            card = GameCard(self, game_data=game, app_context=self.app_context, view_mode=view_mode)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew" if view_mode == 'simple' else 'n')
            col += 1
            if col >= max_cols: col = 0; row += 1

    # --- Reszta funkcji (bez zmian) ---
    def open_add_game_window(self):
        if self.add_game_win_instance is None or not self.add_game_win_instance.winfo_exists():
            self.add_game_win_instance = AddGameWindow(self, self.app_context, on_success_callback=self.refresh_view)
        else: self.add_game_win_instance.focus()
            
    def on_session_ended(self, identifier, duration_seconds):
        library_data = self.app_context.data_manager.get_plugin_data('library')
        games_list = library_data.get('games', [])
        
        game_to_update = None
        for game in games_list:
            if game.get("id") == identifier:
                # Krok 1: Zaktualizuj czas gry (tak jak wcześniej)
                new_playtime = game.get('total_playtime_seconds', 0) + duration_seconds
                game['total_playtime_seconds'] = new_playtime
                self.app_context.event_manager.emit("playtime_updated", game_id=identifier, new_playtime=new_playtime)
                game_to_update = game
                break
        
        # Zapisz dane czasu gry OD RAZU
        if game_to_update:
            library_data['games'] = games_list
            self.app_context.data_manager.save_plugin_data('library', library_data)
        
            # Krok 2: Otwórz okno podsumowania (z już zaktualizowanymi danymi gry)
            self.after(0, self._open_post_session_window, game_to_update, duration_seconds)

    def _open_post_session_window(self, game_data, session_duration):
        """Tworzy i wyświetla okno podsumowania sesji."""
        if self.post_session_win_instance is None or not self.post_session_win_instance.winfo_exists():
            self.post_session_win_instance = PostSessionWindow(
                self, game_data, session_duration, on_save_callback=self._handle_session_save
            )
        else:
            self.post_session_win_instance.focus()

    def _handle_session_save(self, game_id, new_completion):
        """
        Ta funkcja jest wywoływana przez PostSessionWindow po zapisaniu.
        Aktualizuje DANE i emituje zdarzenia.
        """
        library_data = self.app_context.data_manager.get_plugin_data('library')
        games_list = library_data.get('games', [])
        
        # Znajdź grę i zaktualizuj jej dane
        for game in games_list:
            if game.get("id") == game_id:
                # Na tym etapie czas gry jeszcze nie został zaktualizowany
                # Musimy to zrobić teraz, ponieważ on_session_ended już tego nie robi
                # TODO: To jest trochę nieeleganckie. Potrzebujemy lepszego sposobu na znalezienie czasu sesji.
                # Na razie załóżmy, że czas gry jest aktualizowany osobno.
                # (Refaktoryzacja w przyszłości)

                game['completion_percent'] = new_completion
                
                # Emituj zdarzenie, aby zaktualizować UI
                self.app_context.event_manager.emit(
                    "completion_updated", 
                    game_id=game_id, 
                    new_completion=new_completion
                )
                break
        
        library_data['games'] = games_list
        self.app_context.data_manager.save_plugin_data('library', library_data)

    # --- NOWA FUNKCJA DO OBSŁUGI USUWANIA ---
    def handle_game_deletion(self, game_id_to_delete):
        """Usuwa grę z danych i odświeża widok."""
        print(f"Otrzymano prośbę o usunięcie gry o ID: {game_id_to_delete}")
        library_data = self.app_context.data_manager.get_plugin_data('library')
        games_list = library_data.get('games', [])

        updated_games_list = [game for game in games_list if game.get('id') != game_id_to_delete]

        if len(updated_games_list) < len(games_list):
            library_data['games'] = updated_games_list
            self.app_context.data_manager.save_plugin_data('library', library_data)
            self.refresh_view() # Odśwież UI, aby usunąć kafelek
        else:
            print("Nie znaleziono gry do usunięcia.")