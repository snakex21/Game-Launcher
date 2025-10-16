# plugins/news/plugin.py
from core.plugin_interface import BasePlugin
from .view import NewsView

class NewsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "news"

    def get_name(self) -> str:
        return "Aktualności"

    def create_view(self, parent):
        return NewsView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        # Domyślne dane: lista kanałów RSS do śledzenia
        return {
            "feeds": [
                {"name": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed"}
            ]
        }