# core/data_manager.py
import json
import os

class DataManager:
    def __init__(self, app_context, db_path='data/database.json'):
        self.app_context = app_context
        self.db_path = db_path
        self.data = {}
        self.is_new_db = not os.path.exists(db_path)
        
        self.load_database()

    def load_database(self):
        """Wczytuje dane lub tworzy pustą strukturę."""
        if self.is_new_db:
            self.data = {"plugins": {}}
            print("Tworzenie nowej struktury bazy danych.")
        else:
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                print("Baza danych została pomyślnie wczytana.")
            except (json.JSONDecodeError, FileNotFoundError):
                self.data = {"plugins": {}}
                print("Błąd wczytywania, tworzenie nowej bazy.")

    def save_database(self):
        """Zapisuje cały stan danych do pliku JSON."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Błąd podczas zapisywania bazy danych: {e}")

    def register_plugin_storage(self, plugin_name, default_data):
        """Upewnia się, że plugin ma swoją 'szufladę' w bazie danych."""
        if "plugins" not in self.data:
            self.data["plugins"] = {}
            
        if plugin_name not in self.data["plugins"]:
            print(f"Inicjalizowanie przestrzeni danych dla pluginu: {plugin_name}")
            self.data["plugins"][plugin_name] = default_data
            self.save_database()

    def get_plugin_data(self, plugin_name):
        """Pobiera dane dla konkretnego pluginu."""
        return self.data.get("plugins", {}).get(plugin_name, {})

    def save_plugin_data(self, plugin_name, new_data):
        """Zapisuje dane dla konkretnego pluginu i zapisuje całą bazę."""
        self.data["plugins"][plugin_name] = new_data
        self.save_database()
        print(f"Zapisano dane dla pluginu: {plugin_name}")