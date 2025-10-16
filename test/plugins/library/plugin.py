# plugins/library/plugin.py
from core.plugin_interface import BasePlugin
from .view import LibraryView

class LibraryPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "library" # Techniczna nazwa

    def get_name(self) -> str:
        return "Biblioteka" # Wyświetlana nazwa

    def create_view(self, parent):
        return LibraryView(parent, self.app_context)

    def get_default_storage(self) -> dict:
        # Deklarujemy, czego potrzebuje nasz plugin
        return {
            "games": [],
            "sessions": [],
            # --- NOWOŚĆ: Przechowujemy stan widoku ---
            "view_mode": "simple" # Dostępne tryby: 'simple', 'rich'
        }