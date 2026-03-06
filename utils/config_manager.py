import os
import json
import logging
from packaging import version
from .constants import (
    CONFIG_FILE,
    LOCAL_SETTINGS_FILE,
    PROGRAM_VERSION,
    DEFAULT_RSS_FEEDS,
    DEFAULT_NEWS_POST_LIMIT,
    GAMES_FOLDER,
    IMAGES_FOLDER,
    THUMBNAIL_FOLDER,
    MODS_STORAGE_FOLDER,
)


def initialize_folders():
    """Tworzy niezbędne foldery aplikacji, jeśli nie istnieją."""
    folders_to_create = [
        GAMES_FOLDER,
        IMAGES_FOLDER,
        THUMBNAIL_FOLDER,
        MODS_STORAGE_FOLDER,
    ]
    for folder in folders_to_create:
        try:
            os.makedirs(folder, exist_ok=True)
            logging.info(f"Folder '{folder}' sprawdzony/utworzony.")
        except OSError as e:
            logging.error(f"Nie można utworzyć folderu '{folder}': {e}")
            # Można rozważyć rzucenie wyjątku lub zakończenie programu,
            # jeśli foldery są krytyczne.


def load_local_settings():
    """Wczytuje lokalne ustawienia użytkownika (np. tokeny)."""
    if os.path.exists(LOCAL_SETTINGS_FILE):
        try:
            with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError) as e:
            logging.error(f"Błąd wczytywania pliku '{LOCAL_SETTINGS_FILE}': {e}")
    return {}


def save_local_settings(data):
    """Zapisuje lokalne ustawienia użytkownika."""
    try:
        local_settings_dir = os.path.dirname(LOCAL_SETTINGS_FILE)
        if local_settings_dir:
            os.makedirs(local_settings_dir, exist_ok=True)
        with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except OSError as e:
        logging.error(f"Błąd zapisu pliku '{LOCAL_SETTINGS_FILE}': {e}")


def load_config():
    """Wczytuje główny plik konfiguracyjny aplikacji."""
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError) as e:
            logging.error(
                f"Błąd wczytywania pliku '{CONFIG_FILE}': {e}. Tworzenie domyślnej konfiguracji."
            )
            data = {}  # Resetuj dane w przypadku błędu odczytu

    # Ustawienie domyślnych wartości, jeśli brakuje kluczy
    data.setdefault("version", "0.0.0")  # Ustaw domyślną wersję, jeśli nie ma
    data.setdefault("games", {})
    data.setdefault("settings", {})
    data.setdefault("groups", {})
    data.setdefault("user", {})
    data.setdefault("roadmap", [])
    data.setdefault("archive", [])  # Dodano brakujący klucz archiwum

    # Aktualizacja wersji programu w konfiguracji, jeśli jest nowsza
    try:
        if version.parse(PROGRAM_VERSION) > version.parse(data.get("version", "0.0.0")):
            data["version"] = PROGRAM_VERSION
            logging.info(f"Zaktualizowano wersję w konfiguracji do {PROGRAM_VERSION}")
    except version.InvalidVersion:
        logging.warning(
            f"Nieprawidłowy format wersji w pliku konfiguracyjnym: {data.get('version')}. Ustawiono na {PROGRAM_VERSION}."
        )
        data["version"] = PROGRAM_VERSION

    # Ustawienia domyślne dla RSS i limitu postów
    settings = data["settings"]
    if "rss_feeds" not in settings:
        settings["rss_feeds"] = DEFAULT_RSS_FEEDS
    else:
        # Konwersja starych formatów RSS (lista stringów) na nowy (lista słowników)
        if isinstance(settings["rss_feeds"], list) and all(
            isinstance(feed, str) for feed in settings["rss_feeds"]
        ):
            settings["rss_feeds"] = [
                {"url": feed, "active": True, "name": feed}
                for feed in settings["rss_feeds"]
            ]
            logging.info("Przekonwertowano format kanałów RSS w konfiguracji.")
        # Upewnij się, że każdy feed ma wymagane klucze
        for feed in settings["rss_feeds"]:
            feed.setdefault("active", True)
            feed.setdefault(
                "name", feed.get("url", "Nieznany kanał")
            )  # Ustaw nazwę, jeśli brakuje

    settings.setdefault("news_post_limit", DEFAULT_NEWS_POST_LIMIT)
    settings.setdefault("language", "pl")  # Domyślny język
    settings.setdefault("theme", "Dark")  # Domyślny motyw
    settings.setdefault("scan_folders", [])  # Domyślna lista folderów do skanowania
    settings.setdefault("scan_recursive", True)  # Domyślnie skanuj rekursywnie
    settings.setdefault("autostart", False)  # Domyślnie nie uruchamiaj z systemem
    settings.setdefault(
        "cloud_services",
        {"google_drive": {"enabled": False}, "github": {"enabled": False}},
    )  # Domyślne ustawienia chmury
    settings.setdefault(
        "show_completion_prompt", True
    )  # Domyślnie pytaj o ukończenie gry
    settings.setdefault(
        "custom_genres", []
    )  # Domyślnie pusta lista niestandardowych gatunków

    # Ustawienia użytkownika
    user = data["user"]
    user.setdefault("username", "")
    user.setdefault("avatar_path", "")

    return data


def save_config(data):
    """Zapisuje główny plik konfiguracyjny, usuwając wrażliwe dane (np. tokeny)."""
    # Tworzymy kopię, aby nie modyfikować oryginalnego obiektu w pamięci
    data_copy = json.loads(json.dumps(data))  # Głęboka kopia

    # Usuń potencjalnie wrażliwe dane przed zapisem do config.json
    # Tokeny powinny być w local_settings.json, ale na wszelki wypadek
    data_copy.get("settings", {}).pop("github_token", None)
    # Można dodać usuwanie innych wrażliwych danych, jeśli się pojawią

    try:
        config_dir = os.path.dirname(CONFIG_FILE)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(data_copy, file, indent=4, ensure_ascii=False)
    except OSError as e:
        logging.error(f"Błąd zapisu pliku '{CONFIG_FILE}': {e}")
    except TypeError as e:
        logging.error(
            f"Błąd serializacji danych do JSON podczas zapisu '{CONFIG_FILE}': {e}"
        )
