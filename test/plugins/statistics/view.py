# plugins/statistics/view.py
import customtkinter as ctk
import threading
from datetime import datetime, timedelta

# Importy potrzebne do osadzenia wykresu Matplotlib w Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def format_hours_minutes(total_seconds):
    """Konwertuje sekundy na czytelny format godzin i minut."""
    if total_seconds is None or total_seconds == 0: return "0 minut"
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    if hours > 0: return f"{hours} godzin {minutes} minut"
    return f"{minutes} minut"

class StatisticsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.pack_propagate(False)

    def refresh_view(self):
        """Czyści widok i rozpoczyna analizę danych w tle."""
        for widget in self.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self, text="Analizowanie danych...", font=("Roboto", 16)).pack(expand=True)
        
        thread = threading.Thread(target=self._process_data_thread)
        thread.daemon = True
        thread.start()

    def _process_data_thread(self):
        """Pobiera i przetwarza dane w tle, aby nie blokować UI."""
        library_data = self.app_context.data_manager.get_plugin_data("library")
        games = library_data.get("games", [])
        sessions = library_data.get("sessions", [])

        # --- Obliczenia ---
        # 1. Całkowity czas gry
        total_playtime = sum(game.get('total_playtime_seconds', 0) for game in games)

        # 2. Najczęściej grana gra
        most_played_game = max(games, key=lambda g: g.get('total_playtime_seconds', 0)) if games else None

        # 3. Aktywność w ostatnim tygodniu
        today = datetime.now()
        last_week_start = today - timedelta(days=6)
        weekly_playtime = { (last_week_start + timedelta(days=i)).strftime('%a'): 0 for i in range(7) } # Np. {'Mon': 0, 'Tue': 0, ...}

        for session in sessions:
            start_time = datetime.fromisoformat(session.get('start_time'))
            if start_time >= last_week_start:
                day_name = start_time.strftime('%a')
                if day_name in weekly_playtime:
                    weekly_playtime[day_name] += session.get('duration_seconds', 0)
        
        processed_data = {
            "total_playtime": total_playtime,
            "most_played_game": most_played_game,
            "weekly_playtime": weekly_playtime
        }
        
        if self.app_context.shutdown_event.is_set(): return
        self.after(0, self._update_ui, processed_data)

    def _update_ui(self, data):
        """Aktualizuje interfejs użytkownika z przetworzonymi danymi."""
        for widget in self.winfo_children():
            widget.destroy()

        # --- Górny panel z kluczowymi statystykami ---
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=10, pady=10)
        stats_frame.grid_columnconfigure((0, 1), weight=1)

        # Karta: Całkowity czas gry
        total_time_card = ctk.CTkFrame(stats_frame, border_width=1)
        total_time_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(total_time_card, text="Całkowity Czas Gry", font=("Roboto", 12, "bold")).pack(pady=(10,0))
        ctk.CTkLabel(total_time_card, text=format_hours_minutes(data['total_playtime']), font=("Roboto", 20)).pack(pady=(0,10), padx=10)

        # Karta: Ulubiona gra
        fav_game_card = ctk.CTkFrame(stats_frame, border_width=1)
        fav_game_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(fav_game_card, text="Najdłużej Grana Gra", font=("Roboto", 12, "bold")).pack(pady=(10,0))
        game_name = data['most_played_game'].get('name', 'Brak danych') if data['most_played_game'] else 'Brak danych'
        ctk.CTkLabel(fav_game_card, text=game_name, font=("Roboto", 20)).pack(pady=(0,10), padx=10)

        # --- Dolny panel z wykresem ---
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.create_weekly_chart(chart_frame, data['weekly_playtime'])

    def create_weekly_chart(self, parent_frame, weekly_data):
        """Tworzy i osadza wykres Matplotlib."""
        # Ustaw styl wykresu, aby pasował do motywu aplikacji
        theme = ctk.get_appearance_mode()
        bg_color = "#2b2b2b" if theme == "Dark" else "#ebebeb"
        text_color = "white" if theme == "Dark" else "black"
        
        fig, ax = plt.subplots(facecolor=bg_color)
        ax.set_facecolor(bg_color)

        days = list(weekly_data.keys())
        playtime_minutes = [v / 60 for v in weekly_data.values()] # Konwertuj na minuty

        ax.bar(days, playtime_minutes, color="#1f6aa5")

        ax.set_title('Aktywność w Ostatnich 7 Dniach', color=text_color)
        ax.set_ylabel('Czas gry (minuty)', color=text_color)
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        
        fig.tight_layout() # Dopasuj wykres do ramki

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)