# plugins/statistics/plugin.py
from core.plugin_interface import BasePlugin
from .view import StatisticsView

class StatisticsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "statistics"

    def get_name(self) -> str:
        return "Statystyki"

    def create_view(self, parent):
        return StatisticsView(parent, self.app_context)
    
    # Ten plugin nie przechowuje własnych danych, więc get_default_storage nie jest potrzebne
    # (domyślnie zwróci pusty słownik, co jest idealne)
    
    def on_view_enter(self, view_instance):
        """Gdy użytkownik wchodzi na widok Statystyk, odśwież go."""
        print("Użytkownik wszedł na widok Statystyk. Odświeżanie danych...")
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()