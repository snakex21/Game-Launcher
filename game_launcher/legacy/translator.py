"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class DummyTranslator:
    """Prosta klasa zastępująca Translator, zwracająca polski tekst (jeśli zdefiniowany)."""
    def __init__(self):
        # Słownik mapujący klucze (oryginalne stringi w gettext) na polskie tłumaczenia
        self.translations = {
            # Sidebar
            "Game Launcher": "Game Launcher", # Lub "Launcher Gier"?
            "Home": "Strona Główna",
            "Library": "Biblioteka",
            "Roadmap": "Roadmapa",
            "Mod Manager": "Menedżer Modów",
            "Achievements": "Osiągnięcia", # Dodano
            "News": "Newsy",
            "Settings": "Ustawienia",
            "Exit": "Wyjście",
            "Fullscreen Mode": "Tryb Pełnoekranowy",
            "Minimize to Tray": "Zminimalizuj do zasobnika",

            # Możesz dodać więcej tłumaczeń dla innych części UI, jeśli były owinięte w gettext
            # Np. Nagłówki sekcji w Ustawieniach, tytuły okien dialogowych itp.
            # "Appearance": "Wygląd",
            # "User": "Użytkownik",
            # ... etc ...
        }
        logging.info("DummyTranslator initialized with Polish string map.")

    def gettext(self, text):
        # Zwróć polskie tłumaczenie, jeśli istnieje, inaczej zwróć oryginalny tekst
        return self.translations.get(text, text)

    def set_language(self, language_code):
        # Nadal nic nie robi
        pass
