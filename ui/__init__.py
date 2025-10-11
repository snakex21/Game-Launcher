"""
Moduł interfejsu użytkownika (UI)
Zawiera komponenty interfejsu: okna, dialogi, widgety.
"""

from .overlay import TrackOverlayWindow
from .dialogs import *

__all__ = [
    'TrackOverlayWindow',
    'AddGameDialog',
    'EditGameDialog',
    'SettingsDialog',
    'AboutDialog',
    'ConfirmDialog'
]
