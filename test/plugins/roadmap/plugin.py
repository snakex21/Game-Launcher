# plugins/roadmap/plugin.py
from core.plugin_interface import BasePlugin
from .view import RoadmapView

class RoadmapPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "roadmap"

    def get_name(self) -> str:
        return "Roadmapa"

    def create_view(self, parent):
        return RoadmapView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        return {"entries": []}
    
    # --- NOWA, ZDEFINIOWANA METODA ---
    def on_view_enter(self, view_instance):
        """Gdy użytkownik wchodzi na widok Roadmapy, odśwież go."""
        print("Użytkownik wszedł na widok Roadmapy. Odświeżanie danych...")
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()