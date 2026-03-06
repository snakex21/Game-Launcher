import logging
import os
from tkinter import messagebox

from launcher.config_store import (
    load_config as config_load_config,
    load_local_settings as config_load_local_settings,
)
from launcher.utils import (
    ACHIEVEMENTS_DEFINITIONS_FILE,
    CONFIG_FILE,
    GAMES_FOLDER,
    IMAGES_FOLDER,
    LOCAL_SETTINGS_FILE,
)


def _get_github_types():
    from github import Github, GithubException

    return Github, GithubException


def _upload_single_file_to_github(self, repo, local_path, repo_path):
    """Pomocnicza funkcja do wysyłania pojedynczego pliku na GitHub."""
    _, GithubException = _get_github_types()

    if not os.path.exists(local_path):
        logging.warning(f"Plik lokalny '{local_path}' nie istnieje, pomijam wysyłanie.")
        return True

    try:
        with open(local_path, "r", encoding="utf-8") as file:
            content = file.read()
    except Exception as e:
        error_msg = f"Nie można odczytać pliku lokalnego {local_path}: {e}"
        logging.error(error_msg)
        self.progress_queue.put(f"ERROR: {error_msg}")
        return False

    try:
        contents = repo.get_contents(repo_path)
        repo.update_file(
            contents.path,
            f"Update {os.path.basename(repo_path)}",
            content,
            contents.sha,
        )
        logging.info(f"Zaktualizowano plik '{repo_path}' na GitHub.")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(repo_path, f"Create {os.path.basename(repo_path)}", content)
            logging.info(f"Utworzono plik '{repo_path}' na GitHub.")
        else:
            error_msg = f"Nie udało się przesłać pliku {repo_path}: {e}"
            logging.error(error_msg)
            self.progress_queue.put(f"ERROR: {error_msg}")
            return False
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd przy wysyłaniu {repo_path}: {e}"
        logging.exception(error_msg)
        self.progress_queue.put(f"ERROR: {error_msg}")
        return False

    return True


def do_upload_to_github(self):
    Github, GithubException = _get_github_types()

    token = self.local_settings.get("github_token")
    if not token:
        self.progress_queue.put("ERROR: Brak tokenu GitHub")
        return
    g = Github(token)
    try:
        user = g.get_user()
        repo_name = "game_launcher_saves"
        try:
            repo = user.get_repo(repo_name)
        except GithubException:
            logging.info(f"Repozytorium '{repo_name}' nie istnieje. Tworzenie nowego.")
            repo = user.create_repo(repo_name)

        if not self._upload_single_file_to_github(
            repo,
            CONFIG_FILE,
            os.path.basename(CONFIG_FILE),
        ):
            return
        if not self._upload_single_file_to_github(
            repo,
            ACHIEVEMENTS_DEFINITIONS_FILE,
            os.path.basename(ACHIEVEMENTS_DEFINITIONS_FILE),
        ):
            return

        if self.settings.get("sync_local_settings_to_cloud", False):
            if not self._upload_single_file_to_github(
                repo,
                LOCAL_SETTINGS_FILE,
                os.path.basename(LOCAL_SETTINGS_FILE),
            ):
                return
        else:
            logging.info(
                "Pomijam wysyłanie local_settings.json do chmury (zgodnie z ustawieniami)."
            )

        logging.info("Rozpoczynanie wysyłania folderu games_saves...")
        self.upload_folder_to_github(repo, GAMES_FOLDER, os.path.basename(GAMES_FOLDER))
        logging.info("Rozpoczynanie wysyłania folderu images...")
        self.upload_folder_to_github(repo, IMAGES_FOLDER, IMAGES_FOLDER)

    except GithubException as e:
        error_msg = f"Błąd GitHub API podczas operacji: {e}"
        logging.error(error_msg)
        self.progress_queue.put(f"ERROR: {error_msg}")
        return
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas wysyłania do GitHub: {e}"
        logging.exception(error_msg)
        self.progress_queue.put(f"ERROR: {error_msg}")
        return

    self.progress_queue.put("DONE")


def upload_folder_to_github(self, repo, local_folder, repo_folder):
    files = []
    for root, dirs, filenames in os.walk(local_folder):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    total_files = len(files)
    for idx, local_file_path in enumerate(files):
        with open(local_file_path, "rb") as file:
            content = file.read()
        repo_file_path = os.path.join(
            repo_folder, os.path.relpath(local_file_path, local_folder)
        ).replace("\\", "/")
        try:
            contents = repo.get_contents(repo_file_path)
            repo.update_file(
                contents.path, f"Update {repo_file_path}", content, contents.sha
            )
        except GithubException as e:
            if e.status == 404:
                repo.create_file(repo_file_path, f"Create {repo_file_path}", content)
            else:
                self.progress_queue.put(
                    f"ERROR: Nie udało się przesłać pliku {repo_file_path}: {e}"
                )
                return
        percent = int(((idx + 1) / total_files) * 100)
        self.progress_queue.put(percent)


def _download_single_file_from_github(self, repo, repo_path, local_path):
    """Pomocnicza funkcja do pobierania pojedynczego pliku z GitHub."""
    try:
        contents = repo.get_contents(repo_path)
        content = contents.decoded_content.decode("utf-8")
        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as file:
            file.write(content)
        logging.info(
            f"Pobrano i zapisano plik '{repo_path}' z GitHub do '{local_path}'."
        )
        return True
    except GithubException as e:
        if e.status == 404:
            logging.warning(f"Nie znaleziono pliku '{repo_path}' w repozytorium GitHub.")
        else:
            logging.error(f"Błąd GitHub podczas pobierania '{repo_path}': {e}")
        return False
    except Exception as e:
        logging.exception(
            f"Nieoczekiwany błąd podczas pobierania/zapisu '{repo_path}': {e}"
        )
        return False


def download_from_github(self):
    Github, GithubException = _get_github_types()

    self.show_progress_window("Pobieranie z GitHub")
    self.progress_bar["value"] = 0
    self.progress_label.config(text="0%")

    token = self.local_settings.get("github_token")
    if not token:
        self.setup_github()
        token = self.local_settings.get("github_token")
    if not token:
        messagebox.showwarning("Błąd", "Brak tokenu GitHub.")
        self.progress_window.destroy()
        return
    g = Github(token)

    try:
        user = g.get_user()
        repo_name = "game_launcher_saves"
        try:
            repo = user.get_repo(repo_name)
        except GithubException:
            messagebox.showwarning("Błąd", f"Repozytorium '{repo_name}' nie istnieje.")
            self.progress_window.destroy()
            return

        logging.info("Pobieranie plików konfiguracyjnych...")
        config_ok = self._download_single_file_from_github(
            repo,
            os.path.basename(CONFIG_FILE),
            CONFIG_FILE,
        )
        ach_def_ok = self._download_single_file_from_github(
            repo,
            os.path.basename(ACHIEVEMENTS_DEFINITIONS_FILE),
            ACHIEVEMENTS_DEFINITIONS_FILE,
        )
        local_settings_ok = False
        if self.settings.get("sync_local_settings_to_cloud", False):
            local_settings_ok = self._download_single_file_from_github(
                repo,
                os.path.basename(LOCAL_SETTINGS_FILE),
                LOCAL_SETTINGS_FILE,
            )
        else:
            logging.info("Pomijam pobieranie local_settings.json z chmury.")

        logging.info("Pobieranie folderu games_saves...")
        self.download_folder_from_github(
            repo,
            os.path.basename(GAMES_FOLDER),
            GAMES_FOLDER,
            progress_callback=self.update_progress,
        )
        logging.info("Pobieranie folderu images...")
        self.download_folder_from_github(
            repo,
            IMAGES_FOLDER,
            IMAGES_FOLDER,
            progress_callback=self.update_progress,
        )

        logging.info("Ponowne wczytywanie konfiguracji i odświeżanie UI...")
        if config_ok:
            self.config = config_load_config()
            self.settings = self.config.setdefault("settings", {})
            self.games = self.config.setdefault("games", {})
            self.groups = self.config.setdefault("groups", {})
            self.user = self.config.setdefault("user", {})
            self.mods_data = self.config.setdefault("mods_data", {})
            self.archive = self.config.setdefault("archive", [])
            self.roadmap = self.config.setdefault("roadmap", [])

        if ach_def_ok:
            self._load_achievement_definitions()

        if local_settings_ok:
            self.local_settings = config_load_local_settings()
            self.apply_font_settings()

        self.repair_save_paths()
        self.refresh_ui()
        self.show_home()

        self.progress_window.destroy()
        messagebox.showinfo("Sukces", "Pliki zostały pobrane z GitHub.")

    except GithubException as e:
        error_msg = f"Błąd GitHub API podczas pobierania: {e}"
        logging.error(error_msg)
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror("Błąd Pobierania", error_msg)
    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas pobierania z GitHub: {e}"
        logging.exception(error_msg)
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        messagebox.showerror("Błąd Pobierania", error_msg)


def download_folder_from_github(self, repo, repo_folder, local_folder, progress_callback=None):
    contents = repo.get_contents(repo_folder)
    files = []
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            files.append(file_content)
    total_files = len(files)
    for idx, file_content in enumerate(files):
        file_path = os.path.join(local_folder, os.path.relpath(file_content.path, repo_folder))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as file:
            file.write(file_content.decoded_content)
        if progress_callback:
            percent = int(((idx + 1) / total_files) * 100)
            self.root.after(0, progress_callback, percent)


__all__ = [
    "_upload_single_file_to_github",
    "do_upload_to_github",
    "upload_folder_to_github",
    "_download_single_file_from_github",
    "download_from_github",
    "download_folder_from_github",
]
