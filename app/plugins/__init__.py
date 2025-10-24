"""Plugin registry."""
from .base import BasePlugin
from .home import HomePlugin
from .library import LibraryPlugin
from .statistics import StatisticsPlugin
from .news import NewsPlugin
from .reminders import ReminderPlugin
from .settings import SettingsPlugin
from .music_player import MusicPlayerPlugin
from .roadmap import RoadmapPlugin
from .mods import ModsPlugin
from .achievements import AchievementsPlugin
from .profile import ProfilePlugin
from .screenshots import ScreenshotsPlugin

__all__ = [
    "BasePlugin",
    "HomePlugin",
    "LibraryPlugin",
    "StatisticsPlugin",
    "NewsPlugin",
    "ReminderPlugin",
    "SettingsPlugin",
    "MusicPlayerPlugin",
    "RoadmapPlugin",
    "ModsPlugin",
    "AchievementsPlugin",
    "ProfilePlugin",
    "ScreenshotsPlugin",
]
