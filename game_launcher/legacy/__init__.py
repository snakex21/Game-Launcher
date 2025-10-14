"""Convenience imports for legacy launcher components."""
from __future__ import annotations

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .achievement_form import AchievementForm
from .add_profile import AddProfileDialog
from .advanced_filters import AdvancedFilterManager
from .chat_server_editor import ChatServerEditorDialog
from .translator import DummyTranslator
from .mod_manager import ExtendedModManager
from .filter_editor import FilterEditorWindow
from .game_details import GameDetailsWindow
from .game_form import GameForm
from .launcher import GameLauncher
from .manage_genres import ManageGenresWindow
from .music_player_page import MusicPlayerPage
from .rule_editor import RuleEditor
from .save_manager import SaveManager
from .scan_verification import ScanVerificationWindow
from .theme_editor import ThemeEditorWindow
from .tool_tip import ToolTip
from .track_overlay import TrackOverlayWindow

__all__ = [
    'AchievementForm',
    'AddProfileDialog',
    'AdvancedFilterManager',
    'CONFIG_FILE',
    'CUSTOM_THEMES_DIR',
    'ChatServerEditorDialog',
    'DEFAULT_MUSIC_HOTKEYS',
    'DummyTranslator',
    'ExtendedModManager',
    'FilterEditorWindow',
    'GAMES_FOLDER',
    'GameDetailsWindow',
    'GameForm',
    'GameLauncher',
    'IMAGES_FOLDER',
    'INTERNAL_MUSIC_DIR',
    'LOCAL_SETTINGS_FILE',
    'MONTH_COLORS',
    'MONTH_NAMES_PL',
    'ManageGenresWindow',
    'MusicPlayerPage',
    'PROGRAM_VERSION',
    'RESAMPLING',
    'RuleEditor',
    'SaveManager',
    'ScanVerificationWindow',
    'THEMES',
    'ThemeEditorWindow',
    'ToolTip',
    'TrackOverlayWindow',
    '_load_theme_from_file',
    'create_default_cover',
    'ensure_legacy_directories',
    'get_contrast_color',
    'load_config',
    'load_local_settings',
    'load_photoimage_from_path',
    'save_config',
    'save_local_settings',
]

ensure_legacy_directories()
