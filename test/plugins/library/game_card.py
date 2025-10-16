# plugins/library/game_card.py
import customtkinter as ctk
from PIL import Image
import os
from tkinter import messagebox
from .manage_mods_window import ManageModsWindow

def format_playtime(total_seconds):
    """Konwertuje sekundy na czytelny format."""
    if total_seconds is None or total_seconds == 0:
        return "Nigdy nie grano"
    if total_seconds < 60:
        return "Mniej niż minuta"
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

class GameCard(ctk.CTkFrame):
    def __init__(self, parent_view, game_data, app_context, view_mode="simple"):
        # Ważne: rodzicem jest scrollable_frame, który jest wewnątrz LibraryView
        super().__init__(parent_view.scrollable_frame)
        
        self.parent_view = parent_view  # Zapisujemy referencję do całego widoku biblioteki
        self.game_data = game_data
        self.app_context = app_context
        self.view_mode = view_mode
        self.mods_window_instance = None

        # Rejestracja na wszystkie potrzebne zdarzenia
        self.app_context.event_manager.subscribe("playtime_updated", self.on_playtime_updated)
        self.app_context.event_manager.subscribe("completion_updated", self.on_completion_updated)
        self.app_context.event_manager.subscribe("game_started", self.on_game_state_changed)
        self.app_context.event_manager.subscribe("game_ended", self.on_game_state_changed)
        self.app_context.event_manager.subscribe("achievements_updated", self.on_achievements_updated)
        
        if self.view_mode == "rich":
            self.configure(width=200, height=350)
            self._create_rich_view()
        else:
            self.configure(border_width=2)
            self._create_simple_view()
        
        # Ustawienie początkowego stanu przycisku po stworzeniu UI
        self.update_button_state()
        self._update_achievements_display()

    def _create_simple_view(self):
        self.grid_columnconfigure(0, weight=1)
        
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5))
        ctk.CTkLabel(info_frame, text=self.game_data.get("name", "Brak nazwy"), font=("Roboto", 16, "bold")).pack(side="top", anchor="w")
        
        playtime_seconds = self.game_data.get('total_playtime_seconds', 0)
        self.playtime_label = ctk.CTkLabel(info_frame, text=f"Czas gry: {format_playtime(playtime_seconds)}", font=("Roboto", 10), text_color="gray")
        self.playtime_label.pack(side="top", anchor="w")
        
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,5))
        completion = self.game_data.get('completion_percent', 0)
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=8)
        self.progress_bar.set(completion / 100)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label = ctk.CTkLabel(progress_frame, text=f" {completion}%", font=("Roboto", 10))
        self.progress_label.pack(side="left")

        # --- NOWA ETYKIETA OSIĄGNIĘĆ ---
        self.achievements_label = ctk.CTkLabel(progress_frame, text="🏆 0/0", font=("Roboto", 10))
        self.achievements_label.pack(side="left", padx=(10, 0))
        
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,10))
        self.buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.launch_button = ctk.CTkButton(self.buttons_frame, text="Uruchom", command=self.launch_game)
        self.launch_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(self.buttons_frame, text="Mody", command=self.open_mods_window, fg_color="gray50", hover_color="gray30").grid(row=0, column=1, sticky="ew", padx=(5, 0))
        ctk.CTkButton(self.buttons_frame, text="Usuń", command=self.delete_game, fg_color="#D32F2F", hover_color="#B71C1C").grid(row=0, column=2, sticky="ew", padx=(5, 0))

    def _create_rich_view(self):
        self.grid_rowconfigure(0, weight=1) # Obraz
        self.grid_rowconfigure(1, weight=0) # Tytuł
        self.grid_rowconfigure(2, weight=0) # Pasek postępu
        self.grid_rowconfigure(3, weight=0) # Przyciski
        self.grid_rowconfigure(4, weight=0) # Czas gry
        self.grid_columnconfigure(0, weight=1)
        self.pack_propagate(False)

        cover_path = self.game_data.get("cover_image_path")
        image_label = ctk.CTkLabel(self, text="", fg_color="gray20")
        image_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        if cover_path and os.path.exists(cover_path):
            try:
                img = ctk.CTkImage(light_image=Image.open(cover_path), size=(190, 220))
                image_label.configure(image=img)
            except Exception:
                image_label.configure(text=f"Błąd obrazu")

        ctk.CTkLabel(self, text=self.game_data.get("name", "Brak nazwy"), font=("Roboto", 14, "bold")).grid(row=1, column=0, sticky="ew", padx=10, pady=(5,0))
        
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=0)
        completion = self.game_data.get('completion_percent', 0)
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=6)
        self.progress_bar.set(completion / 100)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_label = ctk.CTkLabel(progress_frame, text=f" {completion}%", font=("Roboto", 10))
        self.progress_label.pack(side="left")

        # --- NOWA ETYKIETA OSIĄGNIĘĆ ---
        self.achievements_label = ctk.CTkLabel(progress_frame, text="🏆 0/0", font=("Roboto", 10))
        self.achievements_label.pack(side="left", padx=(10, 0))

        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.launch_button = ctk.CTkButton(self.buttons_frame, text="Uruchom", height=24, command=self.launch_game)
        self.launch_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(self.buttons_frame, text="Mody", height=24, command=self.open_mods_window, fg_color="gray50", hover_color="gray30").grid(row=0, column=1, sticky="ew", padx=(5, 0))
        ctk.CTkButton(self.buttons_frame, text="Usuń", height=24, command=self.delete_game, fg_color="#D32F2F", hover_color="#B71C1C").grid(row=0, column=2, sticky="ew", padx=(5, 0))

        playtime_seconds = self.game_data.get('total_playtime_seconds', 0)
        self.playtime_label = ctk.CTkLabel(self, text=format_playtime(playtime_seconds), font=("Roboto", 10), text_color="gray")
        self.playtime_label.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 5))

    def update_button_state(self):
        """Sprawdza stan gry i aktualizuje wygląd i funkcję przycisku."""
        game_id = self.game_data.get('id')
        is_running = self.app_context.game_handler.is_game_running(game_id)
        
        if is_running:
            self.launch_button.configure(text="Wyłącz", command=self.close_game, fg_color="#c0392b", hover_color="#a52a2a")
        else:
            default_color = ("#3B8ED0", "#1F6AA5")
            hover_color = ("#36719F", "#144870")
            self.launch_button.configure(text="Uruchom", command=self.launch_game, fg_color=default_color, hover_color=hover_color)

    def on_game_state_changed(self, game_id):
        """Reaguje na zdarzenia rozpoczęcia/zakończenia gry."""
        if self.game_data.get('id') == game_id:
            self.after(0, self.update_button_state)

    def launch_game(self):
        self.app_context.game_handler.launch_game(self.game_data)

    def close_game(self):
        self.app_context.game_handler.close_game(self.game_data.get('id'))

    def delete_game(self):
        game_name = self.game_data.get('name')
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno chcesz usunąć '{game_name}' z biblioteki?\nTa operacja jest nieodwracalna."):
            self.parent_view.handle_game_deletion(self.game_data.get('id'))

    def on_playtime_updated(self, game_id, new_playtime):
        if self.game_data.get('id') == game_id:
            self.after(0, self._update_playtime_label, new_playtime)
            
    def _update_playtime_label(self, new_playtime):
        self.game_data['total_playtime_seconds'] = new_playtime
        self.playtime_label.configure(text=f"Czas gry: {format_playtime(new_playtime)}" if self.view_mode == 'simple' else format_playtime(new_playtime))

    def on_completion_updated(self, game_id, new_completion):
        if self.game_data.get('id') == game_id:
            self.after(0, self._update_progress_display, new_completion)

    def _update_progress_display(self, new_completion):
        self.game_data['completion_percent'] = new_completion
        self.progress_bar.set(new_completion / 100)
        self.progress_label.configure(text=f" {new_completion}%")

    def open_mods_window(self):
        if self.mods_window_instance is None or not self.mods_window_instance.winfo_exists():
            self.mods_window_instance = ManageModsWindow(self, self.app_context, self.game_data)
        else:
            self.mods_window_instance.focus()

    # --- NOWE FUNKCJE DO OBSŁUGI OSIĄGNIĘĆ ---
    def on_achievements_updated(self, game_id):
        """Reaguje na zdarzenie zmiany w osiągnięciach."""
        if self.game_data.get('id') == game_id:
            self.after(0, self._update_achievements_display)

    def _update_achievements_display(self):
        """Pobiera dane i aktualizuje licznik osiągnięć."""
        game_id = self.game_data.get('id')
        ach_data = self.app_context.data_manager.get_plugin_data("achievements")
        game_achievements = ach_data.get("achievements_data", {}).get(game_id, [])
        
        total = len(game_achievements)
        completed = sum(1 for ach in game_achievements if ach.get("completed"))
        
        self.achievements_label.configure(text=f"🏆 {completed}/{total}")