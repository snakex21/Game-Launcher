from core.plugin_interface import BasePlugin
from .view import MusicView

class MusicPlugin(BasePlugin):
    @property
    def plugin_name(self): return "music"
    def get_name(self): return "Muzyka"
    def create_view(self, parent): return MusicView(parent, self.app_context)
    def get_default_storage(self) -> dict:
            return {
                "music_folder": "",
                "loop_mode": "none",
                "shuffle_enabled": False
            }
    def on_view_enter(self, view_instance):
        if hasattr(view_instance, 'refresh_view'): view_instance.refresh_view()