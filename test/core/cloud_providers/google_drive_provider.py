# core/cloud_providers/google_drive_provider.py
from .base_provider import BaseProvider
import os, pickle, io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_PATH = 'credentials.json'
TOKEN_PATH = 'token.pickle'

# --- KLUCZOWA ZMIANA: Klasa teraz dziedziczy po BaseProvider ---
class GoogleDriveProvider(BaseProvider):
    def __init__(self, app_context):
        super().__init__(app_context)
        self.service = None

    # --- ZMIANA NAZWY: Metoda implementuje kontrakt z BaseProvider ---
    def authenticate(self):
        creds = None
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    if os.path.exists(TOKEN_PATH): os.remove(TOKEN_PATH)
                    return self.authenticate()
            else:
                if not os.path.exists(CREDENTIALS_PATH):
                    self.app_context.event_manager.emit("cloud_status_update", status="Błąd: Brak credentials.json!")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, 'wb') as token: pickle.dump(creds, token)
        try:
            self.service = build('drive', 'v3', credentials=creds)
            self.app_context.event_manager.emit("cloud_status_update", status="Połączono z Google Drive")
            return True
        except Exception as e:
            self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd połączenia: {e}")
            return False

    def _find_file(self, filename="database.json"):
        if not self.service: return None
        response = self.service.files().list(q=f"name='{filename}' and trashed=false", spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        return files[0]['id'] if files else None

    # --- ZMIANA NAZWY: Metoda implementuje kontrakt z BaseProvider ---
    def upload(self):
        if not self.service and not self.authenticate(): return
        self.app_context.event_manager.emit("cloud_status_update", status="Wysyłanie...")
        file_id = self._find_file()
        media = MediaFileUpload('data/database.json', mimetype='application/json', resumable=True)
        try:
            if file_id: self.service.files().update(fileId=file_id, media_body=media).execute()
            else: self.service.files().create(body={'name': 'database.json'}, media_body=media, fields='id').execute()
            self.app_context.event_manager.emit("cloud_status_update", status="Wysyłanie zakończone!")
        except Exception as e: self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd wysyłania: {e}")

    # --- ZMIANA NAZWY: Metoda implementuje kontrakt z BaseProvider ---
    def download(self):
        if not self.service and not self.authenticate(): return
        self.app_context.event_manager.emit("cloud_status_update", status="Pobieranie...")
        file_id = self._find_file()
        if file_id:
            try:
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO(); downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False: status, done = downloader.next_chunk()
                with open('data/database.json', 'wb') as f: f.write(fh.getvalue())
                self.app_context.event_manager.emit("cloud_status_update", status="Pobieranie zakończone!")
                self.app_context.event_manager.emit("data_sync_completed")
            except Exception as e: self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd pobierania: {e}")
        else: self.app_context.event_manager.emit("cloud_status_update", status="Plik nie istnieje w chmurze.")