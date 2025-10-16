# plugins/screenshots/plugin.py
from core.plugin_interface import BasePlugin
from .view import ScreenshotsView

class ScreenshotsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "screenshots"

    def get_name(self) -> str:
        return "Screenshoty"

    def create_view(self, parent):
        return ScreenshotsView(parent, self.app_context)
    
    # Ten plugin nie przechowuje własnych danych, więc get_default_storage jest puste.
    
    def on_view_enter(self, view_instance):
        """Odśwież galerię po wejściu."""
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()