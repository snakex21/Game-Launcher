"""Integracja z Last.fm umożliwiająca scrobblowanie utworów.

Plik był pusty – brakowało więc elementu wymienionego w dokumentacji
projektu.  Implementacja poniżej bazuje na bibliotece :mod:`pylast` i
zapewnia podstawowe operacje potrzebne w launcherze: nawiązanie
połączenia, aktualizację statusu „Now Playing”, scrobblowanie oraz
pobieranie ostatnio słuchanych utworów.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pylast

from utils.logger import get_logger


class LastFMIntegration:
    """Warstwa integracji z Last.fm.

    Args:
        api_key: Klucz API otrzymany z Last.fm.
        api_secret: Sekret API.
        username: Nazwa użytkownika Last.fm.
        password_hash: Hasz hasła (tworzony funkcją
            :func:`pylast.md5` z czystego hasła).
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        username: Optional[str] = None,
        password_hash: Optional[str] = None,
    ) -> None:
        self.logger = get_logger()
        self.api_key = api_key
        self.api_secret = api_secret
        self.username = username
        self.password_hash = password_hash
        self.network: Optional[pylast.LastFMNetwork] = None

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Tworzy połączenie z Last.fm."""

        if not self.api_key or not self.api_secret:
            self.logger.error("Last.fm API credentials are missing")
            return False

        try:
            self.network = pylast.LastFMNetwork(
                api_key=self.api_key,
                api_secret=self.api_secret,
                username=self.username,
                password_hash=self.password_hash,
            )
            self.logger.info("Connected to Last.fm API")
            return True
        except pylast.WSError as exc:
            self.logger.error(f"Failed to connect to Last.fm: {exc}")
        except Exception as exc:  # pragma: no cover - nieprzewidziane błędy
            self.logger.error(f"Unexpected Last.fm error: {exc}")
        self.network = None
        return False

    # ------------------------------------------------------------------
    def update_now_playing(
        self,
        artist: str,
        track: str,
        album: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> bool:
        """Aktualizuje status „Now Playing” użytkownika."""

        if not self.network:
            self.logger.warning("Last.fm network not connected")
            return False

        try:
            self.network.update_now_playing(
                artist=artist,
                title=track,
                album=album,
                duration=duration,
            )
            self.logger.info(f"Updated Last.fm now playing: {artist} – {track}")
            return True
        except pylast.WSError as exc:
            self.logger.error(f"Failed to update now playing: {exc}")
            return False

    # ------------------------------------------------------------------
    def scrobble(self, artist: str, track: str, timestamp: Optional[datetime] = None) -> bool:
        """Wysyła scrobbla do Last.fm."""

        if not self.network:
            self.logger.warning("Last.fm network not connected")
            return False

        ts = int((timestamp or datetime.utcnow()).timestamp())

        try:
            self.network.scrobble(artist=artist, title=track, timestamp=ts)
            self.logger.info(f"Scrobbled track: {artist} – {track}")
            return True
        except pylast.WSError as exc:
            self.logger.error(f"Failed to scrobble track: {exc}")
            return False

    # ------------------------------------------------------------------
    def get_recent_tracks(self, limit: int = 10) -> List[pylast.PlayedTrack]:
        """Zwraca listę ostatnio odtworzonych utworów."""

        if not self.network or not self.username:
            self.logger.warning("Cannot fetch Last.fm history without username")
            return []

        try:
            user = self.network.get_user(self.username)
            recent = user.get_recent_tracks(limit=limit)
            return list(recent)
        except pylast.WSError as exc:
            self.logger.error(f"Failed to fetch recent tracks: {exc}")
            return []

