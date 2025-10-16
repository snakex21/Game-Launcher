# core/cloud_providers/github_provider.py
from .base_provider import BaseProvider
from github import Github, GithubException
from github.InputFileContent import InputFileContent

GIST_FILENAME = 'game_launcher_database.json'
GIST_DESCRIPTION = 'Game-Launcher Sync Data'

class GitHubProvider(BaseProvider):
    def __init__(self, app_context):
        super().__init__(app_context)
        self.github_instance = None

    def authenticate(self):
        settings = self.app_context.data_manager.get_plugin_data("settings")
        token = settings.get("github_pat")
        if not token:
            self.app_context.event_manager.emit("cloud_status_update", status="Błąd: Brak tokenu GitHub PAT.")
            return False
        try:
            self.github_instance = Github(token)
            user = self.github_instance.get_user()
            self.app_context.event_manager.emit("cloud_status_update", status=f"Połączono z GitHub ({user.login})")
            return True
        except GithubException as e:
            self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd GitHub: {e.data['message']}")
            return False

    def _find_gist(self):
        if not self.github_instance: return None
        for gist in self.github_instance.get_user().get_gists():
            if GIST_DESCRIPTION == gist.description:
                return gist
        return None

    def upload(self):
        if not self.github_instance and not self.authenticate(): return
        with open('data/database.json', 'r', encoding='utf-8') as f: content = f.read()
        try:
            self.app_context.event_manager.emit("cloud_status_update", status="Wysyłanie do GitHub...")
            gist = self._find_gist()
            files = {GIST_FILENAME: InputFileContent(content)}
            if gist: gist.edit(description=GIST_DESCRIPTION, files=files)
            else: self.github_instance.get_user().create_gist(public=False, files=files, description=GIST_DESCRIPTION)
            self.app_context.event_manager.emit("cloud_status_update", status="Wysyłanie zakończone!")
        except Exception as e: self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd wysyłania: {e}")

    def download(self):
        if not self.github_instance and not self.authenticate(): return
        try:
            self.app_context.event_manager.emit("cloud_status_update", status="Pobieranie z GitHub...")
            gist = self._find_gist()
            if not gist or GIST_FILENAME not in gist.files:
                self.app_context.event_manager.emit("cloud_status_update", status="Nie znaleziono Gista w chmurze.")
                return
            content = gist.files[GIST_FILENAME].content
            with open('data/database.json', 'w', encoding='utf-8') as f: f.write(content)
            self.app_context.event_manager.emit("cloud_status_update", status="Pobieranie zakończone!")
            self.app_context.event_manager.emit("data_sync_completed")
        except Exception as e: self.app_context.event_manager.emit("cloud_status_update", status=f"Błąd pobierania: {e}")