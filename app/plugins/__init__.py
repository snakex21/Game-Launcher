"""Plugin registry."""
from .base import BasePlugin
from .library import LibraryPlugin
from .statistics import StatisticsPlugin
from .news import NewsPlugin
from .reminders import ReminderPlugin
from .settings import SettingsPlugin
from .music_player import MusicPlayerPlugin

__all__ = [
    "BasePlugin",
    "LibraryPlugin",
    "StatisticsPlugin",
    "NewsPlugin",
    "ReminderPlugin",
    "SettingsPlugin",
    "MusicPlayerPlugin",
]
