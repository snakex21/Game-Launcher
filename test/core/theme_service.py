# core/theme_service.py
import customtkinter as ctk
import json
import os
from copy import deepcopy

# Kompletny szablon, aby uniknąć błędów KeyError.
DEFAULT_THEME_STRUCTURE = {
    "CTk": {"fg_color": ["gray92", "gray14"]},
    "CTKFrame": {
        "corner_radius": 6, "border_width": 0, "fg_color": ["gray86", "gray17"],
        "top_fg_color": ["gray81", "gray20"], "border_color": ["gray65", "gray28"]
    },
    "CTkButton": {
        "corner_radius": 6, "border_width": 0, "fg_color": ["#3B8ED0", "#1F6AA5"],
        "hover_color": ["#36719F", "#144870"], "text_color": ["#DCE4EE", "#DCE4EE"]
    },
    "CTkLabel": {
        "corner_radius": 0, "fg_color": "transparent", "text_color": ["gray10", "gray90"]
    },
    "CTkEntry": {
        "corner_radius": 6, "border_width": 2, "fg_color": ["gray92", "gray14"],
        "text_color": ["gray10", "gray90"]
    },
    "CTkOptionMenu": {
        "fg_color": ["#3B8ED0", "#1F6AA5"],
        "button_color": ["#36719F", "#144870"],
        "button_hover_color": ["#36719F", "#144870"]
    },
    "CTkScrollableFrame": {
        "label_fg_color": ["gray81", "gray20"]
    }
}

class ThemeService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.themes_dir = "themes"
        os.makedirs(self.themes_dir, exist_ok=True)
        self.themes = {}
        self.load_all_themes()

    def load_all_themes(self):
        """Ładuje motywy wbudowane i niestandardowe."""
        self.themes = {
            'Dark': {"type": "built-in", "mode": "dark"},
            'Light': {"type": "built-in", "mode": "light"},
            'System': {"type": "built-in", "mode": "system"}
        }
        for filename in os.listdir(self.themes_dir):
            if filename.endswith(".json"):
                theme_name = os.path.splitext(filename)[0]
                filepath = os.path.join(self.themes_dir, filename)
                self.themes[theme_name] = {"type": "custom", "path": filepath}
                print(f"Znaleziono niestandardowy motyw: {theme_name}")

    def get_available_themes(self):
        return sorted(list(self.themes.keys()))

    def apply_theme(self, theme_name):
        """Inteligentnie stosuje wybrany motyw."""
        if theme_name not in self.themes:
            theme_name = "System"

        theme_info = self.themes[theme_name]
        
        try:
            if theme_info["type"] == "built-in":
                # Dla motywów wbudowanych, resetujemy do standardowego motywu CTk "blue"
                # a następnie ustawiamy tylko tryb (ciemny/jasny).
                ctk.set_default_color_theme("blue") 
                ctk.set_appearance_mode(theme_info["mode"])
            else: # custom
                # --- KLUCZOWA POPRAWKA NAPRAWIAJĄCA BŁĄD ---
                # 1. Wczytujemy plik JSON do słownika w Pythonie.
                theme_path = theme_info["path"]
                with open(theme_path, 'r') as f:
                    theme_data = json.load(f)
                
                # 2. Wyodrębniamy tryb wyglądu (np. "dark"), usuwając go jednocześnie ze słownika.
                appearance_mode = theme_data.pop("appearance_mode", "dark")
                ctk.set_appearance_mode(appearance_mode)

                # 3. Przekazujemy do CustomTkinter CZYSTY słownik z samymi kolorami.
                #    To jest najbardziej niezawodna metoda.
                ctk.set_default_color_theme(theme_data)
            
            settings_data = self.app_context.data_manager.get_plugin_data("settings")
            settings_data['last_used_theme'] = theme_name
            self.app_context.data_manager.save_plugin_data("settings", settings_data)
            
            self.app_context.event_manager.emit("theme_changed")
            print(f"Zastosowano motyw: {theme_name}")

        except Exception as e:
            print(f"Błąd krytyczny podczas stosowania motywu '{theme_name}': {e}. Wracam do motywu systemowego.")
            self.apply_theme("System")
            return

    def save_theme(self, theme_name, appearance_mode, user_colors):
        """Zapisuje KOMPLETNY plik motywu."""
        if not theme_name: return False, "Nazwa motywu nie może być pusta."
        
        final_theme = deepcopy(DEFAULT_THEME_STRUCTURE)
        
        final_theme['CTKFrame']['fg_color'] = user_colors['fg_color']
        final_theme['CTkButton']['fg_color'] = user_colors['button_color']
        final_theme['CTkButton']['hover_color'] = user_colors['button_hover_color']
        final_theme['CTkLabel']['text_color'] = user_colors['text_color']
        
        filepath = os.path.join(self.themes_dir, f"{theme_name}.json")
        try:
            # Do pliku zapisujemy nasz specjalny klucz "appearance_mode"
            final_theme_with_mode = {"appearance_mode": appearance_mode, **final_theme}
            with open(filepath, 'w') as f:
                json.dump(final_theme_with_mode, f, indent=4)
            self.load_all_themes()
            return True, f"Motyw '{theme_name}' został zapisany."
        except Exception as e:
            return False, f"Błąd zapisu motywu: {e}"