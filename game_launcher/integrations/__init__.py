"""
Integrations - Moduły integracji z zewnętrznymi API
AI-Friendly: Discord, Last.fm, RAWG, GitHub
"""

# Import integracji
from .discord_rpc import DiscordRPC
from .github_backup import GitHubBackup
from .lastfm import LastFMIntegration
from .rawg_api import RAWGApi

__all__ = [
    "DiscordRPC",
    "GitHubBackup",
    "LastFMIntegration",
    "RAWGApi",
]