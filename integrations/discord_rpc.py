"""
Integracja Discord Rich Presence
Wyświetla aktualną aktywność w Discord.
"""

import logging
import time
from typing import Optional, Dict, Any
from pypresence import Presence, PyPresenceException

from config.constants import DISCORD_CLIENT_ID

logger = logging.getLogger(__name__)


class DiscordRPC:
    """
    Klasa zarządzająca Discord Rich Presence.
    Wyświetla informacje o aktualnie granej grze lub aktywności w launcherze.
    """
    
    def __init__(self, client_id: str = DISCORD_CLIENT_ID, launcher_instance=None):
        """
        Inicjalizuje Discord RPC.
        
        Args:
            client_id: Discord Application Client ID
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.client_id = client_id
        self.launcher = launcher_instance
        self.rpc: Optional[Presence] = None
        self.connected: bool = False
        self.start_time: int = int(time.time())
        self.current_state: Optional[str] = None
        
        logger.debug("DiscordRPC zainicjalizowany")
    
    def connect(self) -> bool:
        """
        Łączy się z Discord RPC.
        
        Returns:
            True jeśli połączono pomyślnie
        """
        try:
            if self.connected:
                logger.warning("Discord RPC już połączony")
                return True
            
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            
            # Ustaw domyślny stan
            self.update_presence(
                state="Przeglądanie biblioteki",
                details="W menu głównym"
            )
            
            logger.info("Połączono z Discord RPC")
            return True
            
        except PyPresenceException as e:
            logger.error(f"Błąd połączenia z Discord RPC: {e}")
            self.connected = False
            return False
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd Discord RPC: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Rozłącza Discord RPC."""
        try:
            if self.rpc and self.connected:
                self.rpc.close()
                self.connected = False
                logger.info("Rozłączono Discord RPC")
        except Exception as e:
            logger.error(f"Błąd rozłączania Discord RPC: {e}")
    
    def update_presence(self, 
                       state: Optional[str] = None,
                       details: Optional[str] = None,
                       large_image: Optional[str] = None,
                       large_text: Optional[str] = None,
                       small_image: Optional[str] = None,
                       small_text: Optional[str] = None,
                       start_timestamp: Optional[int] = None,
                       end_timestamp: Optional[int] = None,
                       buttons: Optional[list] = None) -> bool:
        """
        Aktualizuje Discord Rich Presence.
        
        Args:
            state: Dolna linia tekstu
            details: Górna linia tekstu
            large_image: Klucz dużego obrazka
            large_text: Tekst przy najeździe na duży obrazek
            small_image: Klucz małego obrazka
            small_text: Tekst przy najeździe na mały obrazek
            start_timestamp: Timestamp rozpoczęcia (dla elapsed time)
            end_timestamp: Timestamp zakończenia (dla remaining time)
            buttons: Lista przycisków [{"label": "...", "url": "..."}]
            
        Returns:
            True jeśli zaktualizowano pomyślnie
        """
        try:
            if not self.connected:
                logger.warning("Discord RPC nie jest połączony")
                return False
            
            # Przygotuj argumenty
            presence_kwargs = {}
            
            if state:
                presence_kwargs['state'] = state
                self.current_state = state
            
            if details:
                presence_kwargs['details'] = details
            
            if large_image:
                presence_kwargs['large_image'] = large_image
            
            if large_text:
                presence_kwargs['large_text'] = large_text
            
            if small_image:
                presence_kwargs['small_image'] = small_image
            
            if small_text:
                presence_kwargs['small_text'] = small_text
            
            # Timestamps
            if start_timestamp:
                presence_kwargs['start'] = start_timestamp
            elif start_timestamp is None and 'start' not in presence_kwargs:
                # Użyj czasu startu aplikacji jako domyślnego
                presence_kwargs['start'] = self.start_time
            
            if end_timestamp:
                presence_kwargs['end'] = end_timestamp
            
            # Przyciski (max 2)
            if buttons:
                presence_kwargs['buttons'] = buttons[:2]
            
            # Aktualizuj presence
            self.rpc.update(**presence_kwargs)
            
            logger.debug(f"Zaktualizowano Discord presence: {state}")
            return True
            
        except PyPresenceException as e:
            logger.error(f"Błąd aktualizacji Discord presence: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd aktualizacji presence: {e}")
            return False
    
    def set_game_playing(self, game_name: str, 
                        game_icon: Optional[str] = None,
                        show_time: bool = True) -> bool:
        """
        Ustawia status grania w grę.
        
        Args:
            game_name: Nazwa gry
            game_icon: Klucz ikony gry (jeśli dostępny w Discord App)
            show_time: Czy pokazywać elapsed time
            
        Returns:
            True jeśli ustawiono pomyślnie
        """
        return self.update_presence(
            state="Gra w:",
            details=game_name,
            large_image=game_icon if game_icon else "game_controller",
            large_text=game_name,
            start_timestamp=int(time.time()) if show_time else None
        )
    
    def set_browsing_library(self, game_count: Optional[int] = None) -> bool:
        """
        Ustawia status przeglądania biblioteki.
        
        Args:
            game_count: Liczba gier w bibliotece
            
        Returns:
            True jeśli ustawiono pomyślnie
        """
        details = "Przeglądanie biblioteki"
        if game_count:
            details = f"Biblioteka: {game_count} gier"
        
        return self.update_presence(
            state="W menu",
            details=details,
            large_image="launcher_icon",
            large_text="Game Launcher"
        )
    
    def set_listening_music(self, track_name: str, artist: str) -> bool:
        """
        Ustawia status słuchania muzyki.
        
        Args:
            track_name: Nazwa utworu
            artist: Wykonawca
            
        Returns:
            True jeśli ustawiono pomyślnie
        """
        return self.update_presence(
            state=f"Słucha: {artist}",
            details=track_name,
            large_image="music_note",
            large_text="Odtwarzacz muzyki",
            small_image="play_button",
            small_text="Odtwarzanie"
        )
    
    def set_idle(self) -> bool:
        """
        Ustawia status bezczynności.
        
        Returns:
            True jeśli ustawiono pomyślnie
        """
        return self.update_presence(
            state="Bezczynny",
            details="W launcherze",
            large_image="launcher_icon"
        )
    
    def clear_presence(self) -> bool:
        """
        Czyści Discord presence (ukrywa aktywność).
        
        Returns:
            True jeśli wyczyszczono pomyślnie
        """
        try:
            if self.connected and self.rpc:
                self.rpc.clear()
                logger.debug("Wyczyszczono Discord presence")
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd czyszczenia presence: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Sprawdza czy Discord RPC jest połączony.
        
        Returns:
            True jeśli połączony
        """
        return self.connected
    
    def reconnect(self) -> bool:
        """
        Próbuje ponownie połączyć z Discord RPC.
        
        Returns:
            True jeśli połączono pomyślnie
        """
        logger.info("Próba ponownego połączenia z Discord RPC...")
        self.disconnect()
        time.sleep(1)
        return self.connect()
    
    def get_current_state(self) -> Optional[str]:
        """
        Zwraca aktualny stan Discord presence.
        
        Returns:
            Aktualny state lub None
        """
        return self.current_state
    
    def cleanup(self):
        """Czyści zasoby Discord RPC."""
        try:
            self.disconnect()
            logger.info("Discord RPC oczyszczony")
        except Exception as e:
            logger.error(f"Błąd czyszczenia Discord RPC: {e}")
