# plugins/achievements/view.py
import customtkinter as ctk
import uuid

class AchievementsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.games_map = {}
        self.current_game_id = None
        self._setup_ui()

    def refresh_view(self):
        self._populate_game_selector()
        self._on_game_selected(self.game_selector.get())

    def _setup_ui(self):
        # Panel wyboru gry
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top_frame, text="Wybierz grę:").pack(side="left", padx=10)
        self.game_selector = ctk.CTkOptionMenu(top_frame, values=["..."], command=self._on_game_selected)
        self.game_selector.pack(side="left", fill="x", expand=True)

        # Lista osiągnięć
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Osiągnięcia dla wybranej gry")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10)

        # Formularz dodawania
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=10, pady=10)
        self.title_entry = ctk.CTkEntry(add_frame, placeholder_text="Tytuł osiągnięcia")
        self.title_entry.pack(fill="x", pady=5)
        self.desc_entry = ctk.CTkEntry(add_frame, placeholder_text="Opis (opcjonalnie)")
        self.desc_entry.pack(fill="x", pady=5)
        ctk.CTkButton(add_frame, text="Dodaj nowe osiągnięcie", command=self._add_achievement).pack(fill="x", pady=5)

    def _populate_game_selector(self):
        library_data = self.app_context.data_manager.get_plugin_data("library")
        games = library_data.get("games", [])
        self.games_map = {game['name']: game['id'] for game in games}
        game_names = sorted(list(self.games_map.keys()))
        if game_names:
            self.game_selector.configure(values=game_names)
            self.game_selector.set(game_names[0])
        else:
            self.game_selector.configure(values=["Brak gier w bibliotece"])
            self.game_selector.set("Brak gier w bibliotece")

    def _on_game_selected(self, game_name):
        self.current_game_id = self.games_map.get(game_name)
        self._display_achievements()

    def _display_achievements(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.current_game_id: return
        
        achievements_plugin_data = self.app_context.data_manager.get_plugin_data("achievements")
        all_achievements = achievements_plugin_data.get("achievements_data", {})
        game_achievements = all_achievements.get(self.current_game_id, [])

        if not game_achievements:
            ctk.CTkLabel(self.scrollable_frame, text="Brak zdefiniowanych osiągnięć dla tej gry.").pack(pady=20)
        
        for ach in game_achievements:
            ach_frame = ctk.CTkFrame(self.scrollable_frame)
            ach_frame.pack(fill="x", pady=5)
            
            checkbox_var = ctk.StringVar(value="on" if ach.get("completed") else "off")
            checkbox = ctk.CTkCheckBox(ach_frame, text=ach.get("title"), variable=checkbox_var, onvalue="on", offvalue="off",
                                     command=lambda a_id=ach.get("id"): self._toggle_achievement(a_id))
            checkbox.pack(side="left", padx=10, pady=5)
            
            ctk.CTkButton(ach_frame, text="Usuń", width=60, fg_color="red", hover_color="darkred",
                          command=lambda a_id=ach.get("id"): self._delete_achievement(a_id)).pack(side="right", padx=10)

    def _add_achievement(self):
        if not self.current_game_id: return
        title = self.title_entry.get()
        desc = self.desc_entry.get()
        if not title: return

        new_ach = {"id": str(uuid.uuid4()), "title": title, "description": desc, "completed": False}

        data = self.app_context.data_manager.get_plugin_data("achievements")
        all_achievements = data.setdefault("achievements_data", {})
        game_achievements = all_achievements.setdefault(self.current_game_id, [])
        game_achievements.append(new_ach)
        
        self.app_context.data_manager.save_plugin_data("achievements", data)
        self.app_context.event_manager.emit("achievements_updated", game_id=self.current_game_id)
        self.title_entry.delete(0, 'end'); self.desc_entry.delete(0, 'end')
        self._display_achievements()

    def _toggle_achievement(self, achievement_id):
        data = self.app_context.data_manager.get_plugin_data("achievements")
        game_achievements = data.get("achievements_data", {}).get(self.current_game_id, [])
        for ach in game_achievements:
            if ach['id'] == achievement_id:
                ach['completed'] = not ach['completed']
                break
        self.app_context.data_manager.save_plugin_data("achievements", data)
        self.app_context.event_manager.emit("achievements_updated", game_id=self.current_game_id)

    def _delete_achievement(self, achievement_id):
        data = self.app_context.data_manager.get_plugin_data("achievements")
        game_achievements = data.get("achievements_data", {}).get(self.current_game_id, [])
        data["achievements_data"][self.current_game_id] = [a for a in game_achievements if a['id'] != achievement_id]
        self.app_context.data_manager.save_plugin_data("achievements", data)
        self.app_context.event_manager.emit("achievements_updated", game_id=self.current_game_id)
        self._display_achievements()