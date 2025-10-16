# plugins/settings/plugin.py
from core.plugin_interface import BasePlugin
from .view import SettingsView

class SettingsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "settings"

    def get_name(self) -> str:
        return "Ustawienia"

    def create_view(self, parent):
        return SettingsView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        return {
            "last_used_theme": "Dark",
            "username": "",  # Pusty string oznacza, że profil nie został skonfigurowany
            "avatar_path": "",
            "discord_rpc_enabled": False,
            "cloud_provider": "Google Drive",
            "github_pat": ""
        }