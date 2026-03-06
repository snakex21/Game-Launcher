"""
Game Launcher - Moduł
Eksportuje klasy z game_launcher.py dla wygodnego importu.
"""

__version__ = "1.6.0"

# Nie importuj cyklicznie - użytkownik importuje bezpośrednio z game_launcher
__all__ = [
    "GameLauncher",
]
