# plugins/home/view.py
import customtkinter as ctk
import threading
from datetime import datetime

class HomeView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.pack_propagate(False)

    def refresh_view(self):
        for widget in self.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self, text="Ładowanie dashboardu...", font=("Roboto", 16)).pack(expand=True)
        threading.Thread(target=self._process_data_thread, daemon=True).start()

    def _process_data_thread(self):
        # --- Zbieranie danych z innych pluginów ---
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        library_data = self.app_context.data_manager.get_plugin_data("library")
        reminders_data = self.app_context.data_manager.get_plugin_data("reminders")

        username = settings_data.get("username", "Graczu")
        
        games = library_data.get("games", [])
        sessions = library_data.get("sessions", [])
        
        # --- Przetwarzanie danych ---
        # Ostatnio grane
        sessions.sort(key=lambda s: s.get("start_time"), reverse=True)
        recent_game_ids = []
        for s in sessions:
            if s['game_id'] not in recent_game_ids:
                recent_game_ids.append(s['game_id'])
            if len(recent_game_ids) >= 4:
                break
        
        id_to_game_map = {g['id']: g for g in games}
        recent_games = [id_to_game_map[gid] for gid in recent_game_ids if gid in id_to_game_map]

        # Szybkie statystyki
        total_playtime_seconds = sum(g.get('total_playtime_seconds', 0) for g in games)
        completed_games_count = sum(1 for g in games if g.get('completion_percent', 0) == 100)

        # Nadchodzące przypomnienia
        upcoming_reminder = None
        now = datetime.now()
        reminders = sorted(reminders_data.get("reminders_list", []), key=lambda r: r.get("datetime"))
        for r in reminders:
            if datetime.fromisoformat(r['datetime']) > now:
                upcoming_reminder = r
                break

        processed_data = {
            "username": username,
            "recent_games": recent_games,
            "total_playtime": total_playtime_seconds,
            "completed_games": completed_games_count,
            "upcoming_reminder": upcoming_reminder
        }
        self.after(0, self._update_ui, processed_data)

    def _update_ui(self, data):
        for widget in self.winfo_children():
            widget.destroy()
        
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Powitanie
        ctk.CTkLabel(self, text=f"Witaj, {data['username']}!", font=("Roboto", 32, "bold"), anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 20))

        # --- Lewa kolumna: Ostatnio grane i Przypomnienia ---
        left_column = ctk.CTkFrame(self, fg_color="transparent")
        left_column.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_column.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(left_column, text="Ostatnio Grane", font=("Roboto", 18, "bold"), anchor="w").pack(fill="x")
        recent_frame = ctk.CTkFrame(left_column)
        recent_frame.pack(fill="both", expand=True, pady=(5, 10))
        for game in data['recent_games']:
            ctk.CTkButton(recent_frame, text=game['name'], anchor="w").pack(fill="x", padx=10, pady=5)
        
        if data['upcoming_reminder']:
            reminder = data['upcoming_reminder']
            dt = datetime.fromisoformat(reminder.get("datetime"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            ctk.CTkLabel(left_column, text="Następne Przypomnienie", font=("Roboto", 18, "bold"), anchor="w").pack(fill="x", pady=(10,0))
            reminder_frame = ctk.CTkFrame(left_column)
            reminder_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(reminder_frame, text=f"[{date_str}] {reminder['message']}").pack(padx=10, pady=10)

        # --- Prawa kolumna: Statystyki ---
        right_column = ctk.CTkFrame(self, fg_color="transparent")
        right_column.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(right_column, text="Szybkie Statystyki", font=("Roboto", 18, "bold"), anchor="w").pack(fill="x")
        stats_frame = ctk.CTkFrame(right_column)
        stats_frame.pack(fill="both", expand=True, pady=5)
        
        total_hours = data['total_playtime'] // 3600
        ctk.CTkLabel(stats_frame, text="Całkowity czas gry:", font=("Roboto", 14)).pack(anchor="w", padx=15, pady=(15, 0))
        ctk.CTkLabel(stats_frame, text=f"{total_hours} godzin", font=("Roboto", 24, "bold")).pack(anchor="w", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(stats_frame, text="Ukończone gry:", font=("Roboto", 14)).pack(anchor="w", padx=15, pady=(10, 0))
        ctk.CTkLabel(stats_frame, text=str(data['completed_games']), font=("Roboto", 24, "bold")).pack(anchor="w", padx=15, pady=(0, 15))