# core/app_context.py
import threading
from .event_manager import EventManager
from .data_manager import DataManager
from .game_handler import GameHandler
from .session_tracker import SessionTracker
from .reminder_service import ReminderService
from .system_handler import SystemHandler
from .discord_service import DiscordService
from .music_service import MusicService
from .theme_service import ThemeService
from .backup_service import BackupService
from .cloud_service import CloudService

class AppContext:
    def __init__(self):
        self.shutdown_event = threading.Event()
        
        # --- KROK 1: Inicjalizuj absolutne podstawy ---
        self.event_manager = EventManager()
        self.data_manager = DataManager(app_context=self)
        
        # --- KROK 2: Inicjalizuj serwisy, które zależą od podstaw ---
        self.game_handler = GameHandler(app_context=self)
        self.session_tracker = SessionTracker(app_context=self)
        self.reminder_service = ReminderService(app_context=self)
        self.system_handler = SystemHandler(app_context=self)
        self.discord_service = DiscordService(app_context=self)
        self.music_service = MusicService(app_context=self)
        self.theme_service = ThemeService(app_context=self)
        self.backup_service = BackupService(app_context=self)
        self.cloud_service = CloudService(app_context=self)
        
        # --- KROK 3: Uruchom logikę startową serwisów, gdy wszystko jest gotowe ---
        self._initialize_services()

    def _initialize_services(self):
        """Wywołuje metody startowe serwisów, które tego potrzebują."""
        self.cloud_service.initialize_provider() # Nowa, bezpieczna metoda