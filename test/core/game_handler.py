# core/game_handler.py
import subprocess
import os

class GameHandler:
    def __init__(self, app_context):
        self.app_context = app_context
        self.running_processes = {}  # Słownik: { game_id: process_object }

    def is_game_running(self, game_id):
        return game_id in self.running_processes

    def launch_game(self, game_data):
        game_id = game_data.get("id")
        if self.is_game_running(game_id): return
        
        launch_type = game_data.get("launch_type", "PC")
        
        try:
            launch_args = []
            if launch_type == "Emulator":
                emu_id = game_data.get("emulator_id")
                if not emu_id: raise ValueError("Brak ID emulatora dla gry.")

                emu_data = self.app_context.data_manager.get_plugin_data("emulators")
                emulators = emu_data.get("emulators_list", [])
                emulator = next((e for e in emulators if e['id'] == emu_id), None)
                if not emulator: raise ValueError(f"Nie znaleziono emulatora o ID: {emu_id}")

                emu_path = emulator.get('path')
                rom_path = game_data.get('path')
                
                if not all([emu_path, rom_path, os.path.exists(emu_path), os.path.exists(rom_path)]):
                    raise FileNotFoundError("Ścieżka do emulatora lub ROM-u jest nieprawidłowa.")

                launch_args = [emu_path, rom_path]
                print(f"Uruchamianie ROM-u: {rom_path} za pomocą: {emu_path}")
            else: # Domyślnie PC
                executable_path = game_data.get("path")
                if not executable_path or not os.path.exists(executable_path):
                    raise FileNotFoundError(f"Ścieżka do gry jest nieprawidłowa: {executable_path}")
                
                launch_args = [executable_path]
                print(f"Uruchamianie gry: {executable_path}")

            process = subprocess.Popen(launch_args)
            self.running_processes[game_id] = process
            self.app_context.event_manager.emit("game_started", game_id=game_id)
            self.app_context.session_tracker.start_tracking(process, game_id)
            
        except Exception as e:
            print(f"Nie udało się uruchomić gry. Błąd: {e}")
            # TODO: Wyświetl błąd w UI

    def close_game(self, game_id):
        if not self.is_game_running(game_id):
            print(f"Gra o ID {game_id} nie jest uruchomiona.")
            return
        
        try:
            print(f"Próba zamknięcia gry o ID: {game_id}")
            process = self.running_processes[game_id]
            process.terminate() # Wyślij sygnał zakończenia
            # SessionTracker obsłuży resztę (zapis czasu, event session_ended)
        except Exception as e:
            print(f"Błąd podczas zamykania gry: {e}")

    def on_session_ended_for_game(self, game_id):
        """Wywoływane przez SessionTracker, gdy proces się zakończy."""
        if game_id in self.running_processes:
            del self.running_processes[game_id]
            # Poinformuj resztę aplikacji, że gra się zakończyła
            self.app_context.event_manager.emit("game_ended", game_id=game_id)
            print(f"Zakończono śledzenie procesu dla gry o ID: {game_id}")