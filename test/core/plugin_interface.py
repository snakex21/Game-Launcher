# core/plugin_interface.py
import customtkinter as ctk

class BasePlugin:
    def __init__(self, app_context):
        self.app_context = app_context
    
    # --- NOWA, WYMAGANA METODA ---
    @property
    def plugin_name(self) -> str:
        """Unikalna, techniczna nazwa pluginu (np. 'library', 'settings')."""
        raise NotImplementedError("Plugin musi mieć unikalną nazwę techniczną!")

    def get_name(self) -> str:
        """Nazwa do wyświetlania w menu."""
        raise NotImplementedError("Plugin musi mieć nazwę!")

    def create_view(self, parent):
        raise NotImplementedError("Plugin musi tworzyć swój widok!")

    # --- NOWA, OPCJONALNA METODA ---
    def get_default_storage(self) -> dict:
        """Zwraca domyślną strukturę danych dla tego pluginu."""
        return {}

    def on_view_enter(self, view_instance):
        """
        Wywoływane, gdy widok tego pluginu staje się aktywny.
        Domyślnie nie robi nic, ale pluginy mogą to zaimplementować.
        """
        pass