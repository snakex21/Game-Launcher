"""
Moduł integracji z zewnętrznymi serwisami
Zawiera integracje z Discord, Last.fm, Steam, Gamepad itp.
"""

from .discord_rpc import DiscordRPC
from .lastfm import LastFMIntegration
from .gamepad import GamepadHandler
from .steam import SteamIntegration

__all__ = [
    'DiscordRPC',
    'LastFMIntegration',
    'GamepadHandler',
    'SteamIntegration'
]
