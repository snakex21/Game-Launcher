# core/cloud_service.py
from .cloud_providers.google_drive_provider import GoogleDriveProvider
from .cloud_providers.github_provider import GitHubProvider

class CloudService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.providers = {
            "Google Drive": GoogleDriveProvider,
            "GitHub": GitHubProvider
        }
        self.active_provider = None
        # --- USUWAMY _init_provider() STĄD ---

    def initialize_provider(self):
        """
        Bezpieczna metoda inicjalizacji, wywoływana przez AppContext,
        gdy DataManager jest już dostępny.
        """
        settings = self.app_context.data_manager.get_plugin_data("settings")
        provider_name = settings.get("cloud_provider", "Google Drive")
        self.set_provider(provider_name, save_setting=False)

    def set_provider(self, provider_name, save_setting=True):
        if save_setting:
            settings = self.app_context.data_manager.get_plugin_data("settings")
            settings['cloud_provider'] = provider_name
            self.app_context.data_manager.save_plugin_data("settings", settings)
        
        if provider_name in self.providers:
            self.active_provider = self.providers[provider_name](self.app_context)
            print(f"Ustawiono aktywnego dostawcę chmury na: {provider_name}")
        else:
            self.active_provider = None

    def authenticate_async(self):
        if self.active_provider:
            self.active_provider.authenticate_async()
        else:
            self.app_context.event_manager.emit("cloud_status_update", status="Najpierw wybierz dostawcę.")

    def upload_database_async(self):
        if self.active_provider:
            self.active_provider.upload_async()

    def download_database_async(self):
        if self.active_provider:
            self.active_provider.download_async()