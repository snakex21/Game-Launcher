"""
Discord RPC - Discord Rich Presence integration
AI-Friendly: Pokazuje co grasz na Discordzie
"""

import time
from pypresence import Presence, PyPresenceException
from utils.logger import get_logger


class DiscordRPC:
    """
    Integracja Discord Rich Presence.
    
    AI Note:
    - Pokazuje aktualnie graną grę na Discordzie
    - Automatyczna aktualizacja statusu
    - Bezpieczne łączenie/rozłączanie
    """
    
    def __init__(self, client_id):
        """
        Inicjalizuje Discord RPC.
        
        Args:
            client_id (str): Discord Application Client ID
        """
        self.logger = get_logger()
        self.client_id = client_id
        self.rpc = None
        self.is_connected = False
        self.current_game = None
    
    def connect(self):
        """
        Łączy z Discord RPC.
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Wywołaj przy starcie aplikacji
        """
        if not self.client_id:
            self.logger.warning("Discord client_id not provided")
            return False
        
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.is_connected = True
            self.logger.info("Connected to Discord RPC")
            return True
            
        except (PyPresenceException, Exception) as e:
            self.logger.error(f"Failed to connect to Discord RPC: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """
        Rozłącza od Discord RPC.
        
        AI Note: Wywołaj przy zamykaniu aplikacji
        """
        if self.rpc and self.is_connected:
            try:
                self.rpc.close()
                self.is_connected = False
                self.logger.info("Disconnected from Discord RPC")
            except Exception as e:
                self.logger.error(f"Error disconnecting from Discord: {e}")
    
    def update_presence(self, game_name, details=None, state=None, start_time=None):
        """
        Aktualizuje status Discord.
        
        Args:
            game_name (str): Nazwa gry
            details (str): Szczegóły (np. "In Menu")
            state (str): Stan (np. "Playing")
            start_time (int): Unix timestamp startu gry
        
        Returns:
            bool: True jeśli sukces
        
        AI Note: Wywołuj gdy zmienia się gra
        """
        if not self.is_connected:
            self.logger.warning("Not connected to Discord RPC")
            return False
        
        try:
            # Przygotuj dane
            presence_data = {
                'details': details or f"Playing {game_name}",
                'state': state or "In Game",
                'large_image': 'game_launcher_logo',  # Możesz ustawić w Discord Developer Portal
                'large_text': 'Game Launcher',
                'small_image': 'playing',
                'small_text': game_name
            }
            
            # Dodaj timestamp jeśli podany
            if start_time:
                presence_data['start'] = start_time
            
            self.rpc.update(**presence_data)
            self.current_game = game_name
            self.logger.info(f"Updated Discord presence: {game_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update Discord presence: {e}")
            return False
    
    def clear_presence(self):
        """
        Czyści status (usuwa aktywność).
        
        AI Note: Wywołaj gdy użytkownik przestaje grać
        """
        if not self.is_connected:
            return
        
        try:
            self.rpc.clear()
            self.current_game = None
            self.logger.info("Cleared Discord presence")
        except Exception as e:
            self.logger.error(f"Failed to clear Discord presence: {e}")
    
    def set_launcher_presence(self):
        """
        Ustawia status "przeglądanie launchera".
        
        AI Note: Użyj gdy użytkownik jest w launcher ale nie gra
        """
        if not self.is_connected:
            return
        
        try:
            self.rpc.update(
                details="Browsing Game Library",
                state="In Launcher",
                large_image='game_launcher_logo',
                large_text='Game Launcher'
            )
            self.current_game = None
            self.logger.info("Set launcher presence")
        except Exception as e:
            self.logger.error(f"Failed to set launcher presence: {e}")