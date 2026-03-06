import logging
import os
import threading
import queue
from tkinter import simpledialog  # Potrzebne do interakcji z użytkownikiem

# Importy specyficzne dla usług chmurowych (np. google-auth, PyGithub)
# Będą dodane, gdy funkcjonalność zostanie zaimplementowana
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
# from github import Github, GithubException

SCOPES_GOOGLE_DRIVE = ["https://www.googleapis.com/auth/drive.file"]
GITHUB_REPO_NAME = "GameLauncherBackups"  # Domyślna nazwa repozytorium


class CloudManager:
    """Zarządza operacjami synchronizacji zapisów gier z usługami chmurowymi."""

    def __init__(self, launcher_instance):
        self.launcher = launcher_instance
        self.progress_queue = queue.Queue()  # Kolejka do komunikacji z UI
        self.progress_window = None  # Referencja do okna postępu

    def _show_progress_window(self, title):
        """Tworzy i pokazuje okno postępu (implementacja w UI)."""
        # Ta metoda powinna być wywołana w głównym wątku Tkinter
        # self.launcher.show_progress_window(title) # Przykładowe wywołanie
        logging.info(f"Rozpoczęto operację w chmurze: {title}")  # Tymczasowy log

    def _update_progress(self, percent):
        """Aktualizuje pasek postępu w oknie (implementacja w UI)."""
        # Ta metoda powinna być wywołana w głównym wątku Tkinter
        # self.launcher.update_progress(percent) # Przykładowe wywołanie
        logging.debug(f"Postęp operacji w chmurze: {percent}%")  # Tymczasowy log

    def _close_progress_window(self):
        """Zamyka okno postępu (implementacja w UI)."""
        # Ta metoda powinna być wywołana w głównym wątku Tkinter
        # self.launcher.stop_scan_progress() # Przykładowe wywołanie (może być inna metoda)
        logging.info("Zakończono operację w chmurze.")  # Tymczasowy log

    def _show_error(self, message):
        """Wyświetla komunikat błędu (implementacja w UI)."""
        # Ta metoda powinna być wywołana w głównym wątku Tkinter
        # messagebox.showerror("Błąd Chmury", message, parent=self.launcher.root)
        logging.error(f"Błąd operacji w chmurze: {message}")

    def _show_info(self, message):
        """Wyświetla komunikat informacyjny (implementacja w UI)."""
        # Ta metoda powinna być wywołana w głównym wątku Tkinter
        # messagebox.showinfo("Informacja Chmury", message, parent=self.launcher.root)
        logging.info(f"Informacja operacji w chmurze: {message}")

    # --- Google Drive ---

    def setup_google_drive(self):
        """Konfiguruje dostęp do Google Drive."""
        self._show_error(
            "Funkcja konfiguracji Google Drive nie jest jeszcze zaimplementowana."
        )
        # TODO: Implementacja logiki OAuth2 dla Google Drive
        # 1. Sprawdź, czy istnieje plik token.json
        # 2. Jeśli nie, uruchom przepływ autoryzacji (InstalledAppFlow)
        # 3. Zapisz dane uwierzytelniające w local_settings.json (bezpieczniej?) lub token.json
        # 4. Zaktualizuj stan w self.launcher.settings['cloud_services']['google_drive']['enabled']
        # 5. Zapisz konfigurację self.launcher.config

    def upload_to_google_drive(self):
        """Wysyła zapisy gier na Google Drive."""
        self._show_error(
            "Funkcja wysyłania na Google Drive nie jest jeszcze zaimplementowana."
        )
        # TODO: Implementacja logiki wysyłania
        # 1. Uzyskaj dane uwierzytelniające
        # 2. Zbuduj obiekt usługi Drive API
        # 3. Znajdź lub utwórz folder aplikacji na Drive
        # 4. Dla każdej gry z ustawioną ścieżką zapisu:
        #    a. Spakuj folder zapisu do archiwum (np. zip)
        #    b. Wyślij plik archiwum na Drive (MediaFileUpload)
        #    c. Aktualizuj postęp przez self._update_progress()

    def download_from_google_drive(self):
        """Pobiera zapisy gier z Google Drive."""
        self._show_error(
            "Funkcja pobierania z Google Drive nie jest jeszcze zaimplementowana."
        )
        # TODO: Implementacja logiki pobierania
        # 1. Uzyskaj dane uwierzytelniające
        # 2. Zbuduj obiekt usługi Drive API
        # 3. Znajdź folder aplikacji na Drive
        # 4. Pobierz listę plików (archiwów zip) z folderu
        # 5. Wyświetl użytkownikowi listę dostępnych gier/zapisów do pobrania (może być nowe okno UI)
        # 6. Dla wybranego pliku:
        #    a. Pobierz plik (MediaIoBaseDownload)
        #    b. Rozpakuj archiwum do odpowiedniego folderu lokalnego (GAMES_FOLDER/game_name)
        #    c. Aktualizuj postęp przez self._update_progress()

    # --- GitHub ---

    def setup_github(self):
        """Konfiguruje dostęp do GitHub."""
        token = simpledialog.askstring(
            "Token GitHub",
            "Wklej swój Personal Access Token (PAT) z uprawnieniami 'repo':",
            show="*",
        )
        if token:
            self.launcher.local_settings["github_token"] = token
            config_manager.save_local_settings(self.launcher.local_settings)
            # Sprawdź poprawność tokenu (opcjonalnie)
            try:
                g = Github(token)
                user = g.get_user()
                logging.info(f"Pomyślnie zalogowano do GitHub jako {user.login}")
                self.launcher.settings["cloud_services"]["github"]["enabled"] = True
                config_manager.save_config(self.launcher.config)
                self._show_info("Pomyślnie skonfigurowano dostęp do GitHub.")
            except Exception as e:  # Złap GithubException i inne
                logging.error(f"Błąd podczas weryfikacji tokenu GitHub: {e}")
                self._show_error(
                    f"Nieprawidłowy token lub błąd połączenia z GitHub: {e}"
                )
                self.launcher.settings["cloud_services"]["github"]["enabled"] = False
                config_manager.save_config(self.launcher.config)
        else:
            self.launcher.settings["cloud_services"]["github"]["enabled"] = False
            config_manager.save_config(self.launcher.config)

    def _get_github_repo(self, g):
        """Pobiera lub tworzy repozytorium na GitHub."""
        user = g.get_user()
        try:
            repo = user.get_repo(GITHUB_REPO_NAME)
            logging.info(f"Znaleziono repozytorium GitHub: {repo.full_name}")
            return repo
        except Exception:  # Złap GithubException.UnknownObjectException
            logging.info(
                f"Repozytorium '{GITHUB_REPO_NAME}' nie znalezione. Próba utworzenia..."
            )
            try:
                repo = user.create_repo(
                    GITHUB_REPO_NAME, private=True
                )  # Utwórz jako prywatne
                logging.info(f"Utworzono repozytorium GitHub: {repo.full_name}")
                # Dodaj plik .gitignore?
                try:
                    repo.create_file(".gitignore", "Initial commit", "*.log\n*.tmp\n")
                except Exception as e:
                    logging.warning(
                        f"Nie udało się dodać pliku .gitignore do repozytorium: {e}"
                    )
                return repo
            except Exception as e:  # Złap GithubException.GithubException
                logging.error(
                    f"Nie można utworzyć repozytorium '{GITHUB_REPO_NAME}': {e}"
                )
                self._show_error(
                    f"Nie można utworzyć repozytorium '{GITHUB_REPO_NAME}': {e}"
                )
                return None

    def upload_to_github(self):
        """Wysyła zapisy gier do repozytorium GitHub."""
        token = self.launcher.local_settings.get("github_token")
        if not token:
            self._show_error(
                "Brak tokenu dostępu do GitHub. Skonfiguruj go w ustawieniach."
            )
            return

        try:
            g = Github(token)
            repo = self._get_github_repo(g)
            if not repo:
                return

            self._show_progress_window("Wysyłanie na GitHub")
            total_games = len(self.launcher.games)
            processed_games = 0

            for game_name, game_data in self.launcher.games.items():
                save_path = game_data.get("save_path")
                if save_path and os.path.isdir(save_path):
                    logging.info(
                        f"Próba wysłania zapisów gry '{game_name}' na GitHub z '{save_path}'"
                    )
                    repo_folder_path = game_name  # Użyj nazwy gry jako ścieżki w repo
                    self._upload_folder_to_github_recursive(
                        repo, save_path, repo_folder_path
                    )
                else:
                    logging.warning(
                        f"Pominięto grę '{game_name}' - brak prawidłowej ścieżki zapisu: {save_path}"
                    )

                processed_games += 1
                progress = int((processed_games / total_games) * 100)
                self.launcher.root.after(
                    0, self._update_progress, progress
                )  # Aktualizuj UI w głównym wątku

            self.launcher.root.after(0, self._close_progress_window)
            self.launcher.root.after(
                0, self._show_info, "Zakończono wysyłanie zapisów na GitHub."
            )

        except Exception as e:  # Złap GithubException i inne
            logging.error(f"Błąd podczas wysyłania na GitHub: {e}")
            self.launcher.root.after(0, self._close_progress_window)
            self.launcher.root.after(
                0, self._show_error, f"Błąd podczas wysyłania na GitHub: {e}"
            )

    def _upload_folder_to_github_recursive(self, repo, local_folder, repo_folder_path):
        """Rekursywnie wysyła zawartość folderu do repozytorium GitHub."""
        commit_message = f"Update saves for {os.path.basename(repo_folder_path)} - {datetime.datetime.now()}"
        files_to_upload = {}  # Słownik: {repo_path: local_path}

        for root, _, files in os.walk(local_folder):
            for filename in files:
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, local_folder)
                repo_path = os.path.join(repo_folder_path, relative_path).replace(
                    "\\", "/"
                )  # Ścieżka w repo

                try:
                    # Sprawdź, czy plik istnieje i czy się zmienił (porównanie SHA może być kosztowne)
                    # Prostsze podejście: zawsze wysyłaj, GitHub obsłuży resztę
                    with open(local_path, "rb") as file_content:
                        content = file_content.read()

                    # Sprawdź, czy plik już istnieje w repozytorium
                    try:
                        existing_file = repo.get_contents(repo_path)
                        # Jeśli plik istnieje, zaktualizuj go tylko jeśli zawartość jest inna
                        # Porównanie SHA jest bardziej efektywne, ale wymaga pobrania zawartości
                        # if existing_file.sha != new_sha: # Trzeba by obliczyć SHA
                        repo.update_file(
                            repo_path, commit_message, content, existing_file.sha
                        )
                        logging.debug(f"Zaktualizowano plik w GitHub: {repo_path}")
                    except (
                        Exception
                    ):  # Złap GithubException.UnknownObjectException - plik nie istnieje
                        repo.create_file(repo_path, commit_message, content)
                        logging.debug(f"Utworzono plik w GitHub: {repo_path}")

                except Exception as e:
                    logging.error(
                        f"Nie udało się wysłać pliku '{local_path}' do '{repo_path}': {e}"
                    )
        # TODO: Obsługa usuwania plików, które istnieją w repo, a nie ma ich lokalnie?

    def download_from_github(self):
        """Pobiera zapisy gier z repozytorium GitHub."""
        token = self.launcher.local_settings.get("github_token")
        if not token:
            self._show_error(
                "Brak tokenu dostępu do GitHub. Skonfiguruj go w ustawieniach."
            )
            return

        try:
            g = Github(token)
            repo = self._get_github_repo(g)  # Użyj istniejącej metody
            if not repo:
                self._show_error(
                    f"Nie znaleziono repozytorium '{GITHUB_REPO_NAME}'. Czy zostało utworzone?"
                )
                return

            self._show_progress_window("Pobieranie z GitHub")

            contents = repo.get_contents("")  # Pobierz zawartość roota repozytorium
            available_games = [item.path for item in contents if item.type == "dir"]

            if not available_games:
                self.launcher.root.after(0, self._close_progress_window)
                self.launcher.root.after(
                    0,
                    self._show_info,
                    "Repozytorium GitHub jest puste lub nie zawiera folderów gier.",
                )
                return

            # TODO: Wyświetlić użytkownikowi listę gier do pobrania (np. w nowym oknie)
            # Na razie pobieramy wszystko
            total_games = len(available_games)
            processed_games = 0

            for game_folder_name in available_games:
                local_game_save_path = os.path.join(GAMES_FOLDER, game_folder_name)
                logging.info(
                    f"Pobieranie zapisów dla gry '{game_folder_name}' z GitHub do '{local_game_save_path}'"
                )
                os.makedirs(local_game_save_path, exist_ok=True)
                self._download_folder_from_github_recursive(
                    repo, game_folder_name, local_game_save_path
                )

                processed_games += 1
                progress = int((processed_games / total_games) * 100)
                self.launcher.root.after(0, self._update_progress, progress)

            self.launcher.root.after(0, self._close_progress_window)
            self.launcher.root.after(
                0, self._show_info, "Zakończono pobieranie zapisów z GitHub."
            )

        except Exception as e:  # Złap GithubException i inne
            logging.error(f"Błąd podczas pobierania z GitHub: {e}")
            self.launcher.root.after(0, self._close_progress_window)
            self.launcher.root.after(
                0, self._show_error, f"Błąd podczas pobierania z GitHub: {e}"
            )

    def _download_folder_from_github_recursive(
        self, repo, repo_folder_path, local_folder
    ):
        """Rekursywnie pobiera zawartość folderu z repozytorium GitHub."""
        try:
            contents = repo.get_contents(repo_folder_path)
        except Exception as e:  # Złap GithubException.UnknownObjectException
            logging.error(
                f"Nie można pobrać zawartości folderu '{repo_folder_path}' z GitHub: {e}"
            )
            return

        for item in contents:
            local_path = os.path.join(local_folder, item.name)
            if item.type == "dir":
                os.makedirs(local_path, exist_ok=True)
                self._download_folder_from_github_recursive(repo, item.path, local_path)
            else:
                try:
                    logging.debug(f"Pobieranie pliku: {item.path} -> {local_path}")
                    file_content = repo.get_contents(item.path).decoded_content
                    with open(local_path, "wb") as file:
                        file.write(file_content)
                except Exception as e:  # Złap GithubException i inne
                    logging.error(
                        f"Nie udało się pobrać pliku '{item.path}' z GitHub: {e}"
                    )

    # --- Wspólne metody wątkowe ---

    def run_threaded_operation(self, operation_func, *args):
        """Uruchamia daną operację chmurową w osobnym wątku."""
        # Sprawdź, czy inna operacja już nie trwa? (można dodać flagę)
        thread = threading.Thread(target=operation_func, args=args, daemon=True)
        thread.start()
        # Opcjonalnie: monitoruj kolejkę postępu w głównym wątku
        # self.launcher.root.after(100, self.check_progress_queue)

    # Metoda check_progress_queue powinna być w GameLauncher,
    # aby aktualizować UI w głównym wątku. CloudManager tylko wrzuca do kolejki.
