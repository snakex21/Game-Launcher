"""Integracja z GitHubem służąca do wykonywania kopii zapasowych.

Dotychczas plik był pusty, co uniemożliwiało skorzystanie z deklarowanej
w README funkcji synchronizacji konfiguracji w repozytorium GitHub.
Zaimplementowana klasa zapewnia niewielkie API pozwalające na
połączenie się z repozytorium, przesyłanie plików oraz ich pobieranie.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from github import Github, GithubException

from utils.logger import get_logger


class GitHubBackup:
    """Proste zarządzanie kopiami zapasowymi w repozytorium GitHub.

    Typowy scenariusz użycia::

        backup = GitHubBackup(token, "user/repo")
        if backup.connect():
            backup.upload_file("config.json", "backups/config.json")

    Połączenie utrzymywane jest przez obiekt :class:`PyGithub.Github`.
    Wszystkie metody zwracają wartość logiczną informującą o powodzeniu
    operacji i logują szczegóły w przypadku niepowodzenia.
    """

    def __init__(self, token: str, repository: str, branch: str = "main") -> None:
        self.logger = get_logger()
        self.token = token
        self.repository_name = repository
        self.branch = branch
        self.github: Optional[Github] = None
        self.repo = None

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Nawiązuje połączenie z repozytorium GitHub."""

        if not self.token or not self.repository_name:
            self.logger.error("GitHub token or repository name not provided")
            return False

        try:
            self.github = Github(self.token, per_page=100)
            self.repo = self.github.get_repo(self.repository_name)
            self.logger.info(
                f"Connected to GitHub repository {self.repository_name} (branch: {self.branch})"
            )
            return True
        except GithubException as exc:
            self.logger.error(f"Failed to connect to GitHub: {exc}")
            self.github = None
            self.repo = None
            return False

    # ------------------------------------------------------------------
    def upload_file(
        self,
        local_path: Path | str,
        remote_path: str,
        message: Optional[str] = None,
    ) -> bool:
        """Wysyła plik do repozytorium.

        Jeśli wskazana ścieżka w repozytorium istnieje, plik zostanie
        zaktualizowany; w przeciwnym razie powstanie nowy wpis.
        """

        if not self.repo:
            self.logger.error("GitHub repository not connected")
            return False

        file_path = Path(local_path)
        if not file_path.exists():
            self.logger.error(f"Local file not found: {file_path}")
            return False

        commit_message = message or f"Update {remote_path}"

        try:
            with file_path.open("rb") as fh:
                content = fh.read()

            try:
                existing = self.repo.get_contents(remote_path, ref=self.branch)
            except GithubException:
                existing = None

            if existing:
                self.repo.update_file(
                    remote_path,
                    commit_message,
                    content,
                    sha=existing.sha,
                    branch=self.branch,
                )
                self.logger.info(f"Updated file on GitHub: {remote_path}")
            else:
                self.repo.create_file(
                    remote_path,
                    commit_message,
                    content,
                    branch=self.branch,
                )
                self.logger.info(f"Uploaded new file to GitHub: {remote_path}")

            return True
        except GithubException as exc:
            self.logger.error(f"Failed to upload {remote_path}: {exc}")
        except Exception as exc:  # pragma: no cover - I/O błędy systemowe
            self.logger.error(f"Unexpected error uploading {remote_path}: {exc}")
        return False

    # ------------------------------------------------------------------
    def download_file(self, remote_path: str, local_path: Path | str) -> bool:
        """Pobiera plik z repozytorium na lokalny dysk."""

        if not self.repo:
            self.logger.error("GitHub repository not connected")
            return False

        try:
            content_file = self.repo.get_contents(remote_path, ref=self.branch)
            destination = Path(local_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content_file.decoded_content)
            self.logger.info(f"Downloaded {remote_path} to {destination}")
            return True
        except GithubException as exc:
            self.logger.error(f"Failed to download {remote_path}: {exc}")
            return False

    # ------------------------------------------------------------------
    def list_directory(self, remote_dir: str = "") -> List[str]:
        """Zwraca listę plików w katalogu repozytorium."""

        if not self.repo:
            self.logger.error("GitHub repository not connected")
            return []

        try:
            items = self.repo.get_contents(remote_dir or "/", ref=self.branch)
            return [item.path for item in items]
        except GithubException as exc:
            self.logger.error(f"Failed to list directory '{remote_dir}': {exc}")
            return []

