# plugins/home/plugin.py
from core.plugin_interface import BasePlugin
from .view import HomeView

class HomePlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "home"

    def get_name(self) -> str:
        return "Strona Główna"

    def create_view(self, parent):
        return HomeView(parent, self.app_context)
    
    def on_view_enter(self, view_instance):
        """Odśwież dashboard po wejściu."""
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()