# plugins/achievements/plugin.py
from core.plugin_interface import BasePlugin
from .view import AchievementsView

class AchievementsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "achievements"

    def get_name(self) -> str:
        return "Osiągnięcia"

    def create_view(self, parent):
        return AchievementsView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        # Struktura: { game_id: [lista_osiagniec], ... }
        return {"achievements_data": {}}

    def on_view_enter(self, view_instance):
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()