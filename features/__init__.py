"""
Moduł funkcji (features)
Zawiera główne funkcjonalności aplikacji.
"""

from .music_player import MusicPlayer
from .game_manager import GameManager
from .stats_manager import StatsManager
from .calendar_manager import CalendarManager
from .achievements import AchievementsManager
from .profile_manager import ProfileManager
from .mod_manager import ModManager

__all__ = [
    'MusicPlayer',
    'GameManager',
    'StatsManager',
    'CalendarManager',
    'AchievementsManager',
    'ProfileManager',
    'ModManager'
]
