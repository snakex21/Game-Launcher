"""Prosta warstwa komunikacji z API RAWG.

RAWG udostępnia informacje o grach – opisy, gatunki, oceny oraz okładki.
Moduł udostępnia niewielkie API potrzebne do pobierania danych w
launcherze: wyszukiwanie gier, pobieranie szczegółów oraz listy gatunków
i platform.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests

from utils.logger import get_logger


class RAWGApi:
    """Klient API RAWG.

    Args:
        api_key: Klucz API (wymagany przez RAWG od 2021 roku).
        base_url: Alternatywny adres API – ułatwia testowanie.
    """

    def __init__(self, api_key: Optional[str], base_url: str = "https://api.rawg.io/api") -> None:
        self.logger = get_logger()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    # ------------------------------------------------------------------
    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if params is None:
            params = {}
        if self.api_key:
            params.setdefault("key", self.api_key)

        url = f"{self.base_url}/{endpoint.lstrip('/') }"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.logger.error(f"RAWG API request failed: {exc}")
            return None

    # ------------------------------------------------------------------
    def search_games(self, query: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """Wyszukuje gry po nazwie."""

        if not query:
            return []

        data = self._request("games", {"search": query, "page_size": page_size})
        if not data or "results" not in data:
            return []
        return data["results"]

    # ------------------------------------------------------------------
    def get_game_details(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Zwraca szczegółowe informacje o grze."""

        return self._request(f"games/{game_id}")

    # ------------------------------------------------------------------
    @lru_cache(maxsize=1)
    def get_genres(self) -> List[Dict[str, Any]]:
        """Zwraca listę gatunków gier."""

        data = self._request("genres")
        if not data or "results" not in data:
            return []
        return data["results"]

    # ------------------------------------------------------------------
    @lru_cache(maxsize=1)
    def get_platforms(self) -> List[Dict[str, Any]]:
        """Zwraca listę platform wspieranych przez RAWG."""

        data = self._request("platforms")
        if not data or "results" not in data:
            return []
        return data["results"]

