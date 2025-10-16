# plugins/reminders/plugin.py
from core.plugin_interface import BasePlugin
from .view import RemindersView

class RemindersPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "reminders"

    def get_name(self) -> str:
        return "Przypomnienia"

    def create_view(self, parent):
        return RemindersView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        return {"reminders_list": []}

    def on_view_enter(self, view_instance):
        """Odśwież widok po wejściu."""
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()