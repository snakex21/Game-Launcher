"""
Integracja Last.fm
Scrobblowanie muzyki i pobieranie statystyk.
"""

import logging
import time
from typing import Optional, Dict, Any, List
import pylast

from config.constants import LASTFM_API_KEY, LASTFM_API_SECRET

logger = logging.getLogger(__name__)


class LastFMIntegration:
    """
    Klasa zarządzająca integracją z Last.fm.
    Scrobbluje odtwarzaną muzykę i pobiera statystyki.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje integrację Last.fm.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.network: Optional[pylast.LastFMNetwork] = None
        self.authenticated: bool = False
        self.username: Optional[str] = None
        self.session_key: Optional[str] = None
        
        logger.debug("LastFMIntegration zainicjalizowany")
    
    def authenticate(self, username: str, password_hash: str) -> bool:
        """
        Uwierzytelnia użytkownika w Last.fm.
        
        Args:
            username: Nazwa użytkownika Last.fm
            password_hash: Hash hasła (MD5)
            
        Returns:
            True jeśli uwierzytelniono pomyślnie
        """
        try:
            self.network = pylast.LastFMNetwork(
                api_key=LASTFM_API_KEY,
                api_secret=LASTFM_API_SECRET,
                username=username,
                password_hash=password_hash
            )
            
            # Sprawdź połączenie
            user = self.network.get_user(username)
            user.get_playcount()  # Test request
            
            self.authenticated = True
            self.username = username
            
            logger.info(f"Uwierzytelniono w Last.fm jako: {username}")
            return True
            
        except pylast.WSError as e:
            logger.error(f"Błąd Last.fm API: {e}")
            self.authenticated = False
            return False
            
        except Exception as e:
            logger.error(f"Błąd uwierzytelniania Last.fm: {e}")
            self.authenticated = False
            return False
    
    def scrobble(self, artist: str, track: str, 
                album: Optional[str] = None,
                timestamp: Optional[int] = None) -> bool:
        """
        Scrobbluje utwór do Last.fm.
        
        Args:
            artist: Wykonawca
            track: Tytuł utworu
            album: Album (opcjonalnie)
            timestamp: Unix timestamp (None = teraz)
            
        Returns:
            True jeśli scrobblowano pomyślnie
        """
        try:
            if not self.authenticated or not self.network:
                logger.warning("Nie uwierzytelniono w Last.fm")
                return False
            
            if timestamp is None:
                timestamp = int(time.time())
            
            self.network.scrobble(
                artist=artist,
                title=track,
                timestamp=timestamp,
                album=album
            )
            
            logger.info(f"Scrobblowano: {artist} - {track}")
            return True
            
        except pylast.WSError as e:
            logger.error(f"Błąd scrobblowania: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd scrobblowania: {e}")
            return False
    
    def update_now_playing(self, artist: str, track: str,
                          album: Optional[str] = None,
                          duration: Optional[int] = None) -> bool:
        """
        Aktualizuje "Now Playing" na Last.fm.
        
        Args:
            artist: Wykonawca
            track: Tytuł utworu
            album: Album (opcjonalnie)
            duration: Długość w sekundach (opcjonalnie)
            
        Returns:
            True jeśli zaktualizowano pomyślnie
        """
        try:
            if not self.authenticated or not self.network:
                logger.warning("Nie uwierzytelniono w Last.fm")
                return False
            
            self.network.update_now_playing(
                artist=artist,
                title=track,
                album=album,
                duration=duration
            )
            
            logger.debug(f"Now Playing: {artist} - {track}")
            return True
            
        except pylast.WSError as e:
            logger.error(f"Błąd aktualizacji Now Playing: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd Now Playing: {e}")
            return False
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Pobiera informacje o użytkowniku.
        
        Returns:
            Słownik z informacjami o użytkowniku lub None
        """
        try:
            if not self.authenticated or not self.network or not self.username:
                return None
            
            user = self.network.get_user(self.username)
            
            return {
                'username': user.get_name(),
                'playcount': user.get_playcount(),
                'registered': user.get_registered(),
                'url': user.get_url(),
                'country': user.get_country() if hasattr(user, 'get_country') else None
            }
            
        except Exception as e:
            logger.error(f"Błąd pobierania informacji użytkownika: {e}")
            return None
    
    def get_top_artists(self, period: str = "overall", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobiera top wykonawców użytkownika.
        
        Args:
            period: Okres (overall, 7day, 1month, 3month, 6month, 12month)
            limit: Maksymalna liczba wyników
            
        Returns:
            Lista top wykonawców
        """
        try:
            if not self.authenticated or not self.network or not self.username:
                return []
            
            user = self.network.get_user(self.username)
            top_artists = user.get_top_artists(period=period, limit=limit)
            
            result = []
            for item in top_artists:
                artist = item.item
                result.append({
                    'name': artist.get_name(),
                    'playcount': item.weight,
                    'url': artist.get_url()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd pobierania top wykonawców: {e}")
            return []
    
    def get_top_tracks(self, period: str = "overall", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobiera top utwory użytkownika.
        
        Args:
            period: Okres (overall, 7day, 1month, 3month, 6month, 12month)
            limit: Maksymalna liczba wyników
            
        Returns:
            Lista top utworów
        """
        try:
            if not self.authenticated or not self.network or not self.username:
                return []
            
            user = self.network.get_user(self.username)
            top_tracks = user.get_top_tracks(period=period, limit=limit)
            
            result = []
            for item in top_tracks:
                track = item.item
                result.append({
                    'artist': track.get_artist().get_name(),
                    'title': track.get_title(),
                    'playcount': item.weight,
                    'url': track.get_url()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd pobierania top utworów: {e}")
            return []
    
    def get_recent_tracks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobiera ostatnio odtwarzane utwory.
        
        Args:
            limit: Maksymalna liczba wyników
            
        Returns:
            Lista ostatnich utworów
        """
        try:
            if not self.authenticated or not self.network or not self.username:
                return []
            
            user = self.network.get_user(self.username)
            recent_tracks = user.get_recent_tracks(limit=limit)
            
            result = []
            for track in recent_tracks:
                result.append({
                    'artist': track.track.artist.get_name(),
                    'title': track.track.title,
                    'album': track.album if hasattr(track, 'album') else None,
                    'timestamp': track.timestamp if hasattr(track, 'timestamp') else None,
                    'now_playing': track.now_playing if hasattr(track, 'now_playing') else False
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd pobierania ostatnich utworów: {e}")
            return []
    
    def get_track_info(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera informacje o utworze.
        
        Args:
            artist: Wykonawca
            track: Tytuł utworu
            
        Returns:
            Słownik z informacjami o utworze lub None
        """
        try:
            if not self.network:
                return None
            
            track_obj = self.network.get_track(artist, track)
            
            return {
                'artist': artist,
                'title': track,
                'playcount': track_obj.get_playcount(),
                'listeners': track_obj.get_listener_count(),
                'url': track_obj.get_url(),
                'duration': track_obj.get_duration() if hasattr(track_obj, 'get_duration') else None
            }
            
        except pylast.WSError as e:
            logger.error(f"Błąd pobierania info o utworze: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd pobierania info: {e}")
            return None
    
    def love_track(self, artist: str, track: str) -> bool:
        """
        Oznacza utwór jako ulubiony (love).
        
        Args:
            artist: Wykonawca
            track: Tytuł utworu
            
        Returns:
            True jeśli oznaczono pomyślnie
        """
        try:
            if not self.authenticated or not self.network:
                logger.warning("Nie uwierzytelniono w Last.fm")
                return False
            
            track_obj = self.network.get_track(artist, track)
            track_obj.love()
            
            logger.info(f"Polubiono: {artist} - {track}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd oznaczania utworu jako ulubiony: {e}")
            return False
    
    def unlove_track(self, artist: str, track: str) -> bool:
        """
        Usuwa oznaczenie utworu jako ulubiony.
        
        Args:
            artist: Wykonawca
            track: Tytuł utworu
            
        Returns:
            True jeśli usunięto oznaczenie
        """
        try:
            if not self.authenticated or not self.network:
                logger.warning("Nie uwierzytelniono w Last.fm")
                return False
            
            track_obj = self.network.get_track(artist, track)
            track_obj.unlove()
            
            logger.info(f"Odpolubiono: {artist} - {track}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd usuwania oznaczenia ulubionego: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Sprawdza czy użytkownik jest uwierzytelniony.
        
        Returns:
            True jeśli uwierzytelniony
        """
        return self.authenticated
    
    def logout(self):
        """Wylogowuje użytkownika."""
        self.network = None
        self.authenticated = False
        self.username = None
        self.session_key = None
        logger.info("Wylogowano z Last.fm")
    
    def cleanup(self):
        """Czyści zasoby Last.fm."""
        try:
            self.logout()
            logger.info("Last.fm integration oczyszczona")
        except Exception as e:
            logger.error(f"Błąd czyszczenia Last.fm: {e}")
