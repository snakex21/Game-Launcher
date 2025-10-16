# plugins/emulators/plugin.py
from core.plugin_interface import BasePlugin
from .view import EmulatorsView

class EmulatorsPlugin(BasePlugin):
    @property
    def plugin_name(self) -> str:
        return "emulators"

    def get_name(self) -> str:
        return "Emulatory"

    def create_view(self, parent):
        return EmulatorsView(parent, self.app_context)
    
    def get_default_storage(self) -> dict:
        return {"emulators_list": []}

    def on_view_enter(self, view_instance):
        if hasattr(view_instance, 'refresh_view'):
            view_instance.refresh_view()