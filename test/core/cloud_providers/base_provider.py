# core/cloud_providers/base_provider.py
import threading

class BaseProvider:
    def __init__(self, app_context):
        self.app_context = app_context

    # --- METODY SYNCHRONICZNE (które implementują dostawcy) ---
    def authenticate(self):
        raise NotImplementedError

    def upload(self):
        raise NotImplementedError

    def download(self):
        raise NotImplementedError

    # --- METODY ASYNCHRONICZNE (które są dziedziczone przez wszystkich) ---
    # Te metody "opakowują" powyższe funkcje w osobne wątki.
    
    def authenticate_async(self):
        """Uruchamia proces autoryzacji w tle."""
        threading.Thread(target=self.authenticate, daemon=True).start()
    
    def upload_async(self):
        """Uruchamia proces wysyłania w tle."""
        threading.Thread(target=self.upload, daemon=True).start()
        
    def download_async(self):
        """Uruchamia proces pobierania w tle."""
        threading.Thread(target=self.download, daemon=True).start()