# core/discord_service.py
import time
import threading

try:
    from pypresence import Presence
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# --- GŁÓWNA ZMIANA: Hardkodujemy ID tutaj ---
# Wklej tutaj swój Client ID, który skopiowałeś z portalu Discorda.
CLIENT_ID = 'YOUR_CLIENT_ID_HERE' 

class DiscordService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.rpc = None
        self.is_connected = False

    def start(self):
        if not DISCORD_AVAILABLE:
            print("Biblioteka pypresence nie jest zainstalowana. Integracja z Discordem wyłączona.")
            return
        
        self.app_context.event_manager.subscribe("game_started", self._on_game_started)
        self.app_context.event_manager.subscribe("game_ended", self._on_game_ended)
        print("Serwis Discorda nasłuchuje na zdarzenia gier.")

    def shutdown(self):
        self._disconnect()

    def _connect_and_update(self, game_name):
        try:
            # Sprawdź, czy Client ID zostało ustawione
            if not CLIENT_ID or CLIENT_ID == '1300136792636522517':
                print("Brak Client ID Discorda w kodzie (core/discord_service.py).")
                return

            self.rpc = Presence(CLIENT_ID)
            self.rpc.connect()
            self.rpc.update(
                details=f"Gra w: {game_name}",
                start=int(time.time()),
                large_image="app_icon",
                large_text="Game-Launcher"
            )
            self.is_connected = True
            print(f"Ustawiono status Discord: Gra w {game_name}")
        except Exception as e:
            print(f"Błąd połączenia z Discordem: {e}")
            self.rpc = None

    def _disconnect(self):
        if self.rpc and self.is_connected:
            try:
                self.rpc.close()
                print("Rozłączono od Discorda.")
            except Exception as e:
                print(f"Błąd podczas rozłączania od Discorda: {e}")
            finally:
                self.rpc = None
                self.is_connected = False

    def _on_game_started(self, game_id):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        if not settings_data.get("discord_rpc_enabled", False):
            return

        library_data = self.app_context.data_manager.get_plugin_data("library")
        game = next((g for g in library_data.get("games", []) if g['id'] == game_id), None)
        
        if game:
            thread = threading.Thread(target=self._connect_and_update, args=(game['name'],))
            thread.daemon = True
            thread.start()

    def _on_game_ended(self, game_id):
        self._disconnect()