from __future__ import annotations

from .shared_imports import *


def get_contrast_color(hex_color):
    """Zwraca 'black' lub 'white' w zależności od jasności koloru HEX."""
    try:
        # Usuń '#' i przekonwertuj na RGB
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            logging.warning(f"Nieprawidłowy format HEX w get_contrast_color: {hex_color}")
            return "black" # Domyślnie czarny przy błędzie formatu

        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

        # Prosta formuła luminancji (można użyć bardziej złożonych)
        # Wartości od 0 (czarny) do 255 (biały)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)

        # Próg decyzyjny (można dostosować eksperymentalnie, 140-150 często działa dobrze)
        threshold = 145
        # print(f"Color: {hex_color}, Lum: {luminance}, Contrast: {'black' if luminance > threshold else 'white'}") # Debug
        return "black" if luminance > threshold else "white"

    except ValueError:
        logging.warning(f"Nieprawidłowy format HEX w get_contrast_color (ValueError): {hex_color}")
        return "black" # Domyślnie czarny przy błędzie konwersji
    except Exception as e:
        logging.error(f"Błąd w get_contrast_color dla {hex_color}: {e}")
        return "black" # Domyślnie czarny przy innym błędzie


def _load_theme_from_file(filepath: str) -> dict | None:
    """Ładuje definicję motywu z pliku JSON, w tym nazwę i definicję.
    Zwraca słownik {'name': ..., 'definition': ...} lub None, jeśli błąd/nieprawidłowa struktura."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Walidacja podstawowa struktury pliku motywu
            if isinstance(data, dict) and "name" in data and "definition" in data and isinstance(data["definition"], dict):
                return data
            else:
                logging.warning(f"Plik motywu '{filepath}' ma nieprawidłową strukturę (wymaga 'name' i 'definition'). Pomijanie.")
                return None
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Błąd odczytu pliku motywu '{filepath}': {e}. Pomijanie.")
        return None


def load_local_settings():
    if os.path.exists(LOCAL_SETTINGS_FILE):
        try:
            with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Błąd odczytu pliku {LOCAL_SETTINGS_FILE}: {e}. Używam domyślnych.")
            data = {}
    else:
        data = {}

    # --- NOWE ZMIANY (Wielu Serwerów Czatu - Wczytywanie i Migracja) ---
    # Sprawdź, czy istnieje stary format konfiguracji czatu
    old_chat_server_url = data.pop("chat_server_url", None) # Pobierz i usuń stary klucz
    old_chat_email = data.pop("chat_email", None)
    old_chat_password = data.pop("chat_password", None)
    old_chat_remember_me = data.pop("chat_remember_me", False)
    old_chat_auto_login = data.pop("chat_auto_login", False)
    
    # Jeśli nie ma nowej struktury "chat_servers", utwórz ją
    if "chat_servers" not in data or not isinstance(data["chat_servers"], list):
        data["chat_servers"] = []

    # Migracja ze starego formatu, jeśli istniał i nowa lista jest pusta
    if old_chat_server_url and not data["chat_servers"]:
        migrated_server_id = str(uuid.uuid4())
        migrated_server_entry = {
            "id": migrated_server_id,
            "name": "Domyślny Serwer (migr.)", # Nazwa dla migracji
            "url": old_chat_server_url,
            "is_default": True,
            "last_used": time.time(),
            "credentials": {},
            "remember_credentials": old_chat_remember_me,
            "auto_login_to_server": old_chat_auto_login and old_chat_remember_me # Auto-login tylko jeśli dane były pamiętane
        }
        if old_chat_remember_me and old_chat_email:
            migrated_server_entry["credentials"]["email"] = old_chat_email
            migrated_server_entry["credentials"]["password"] = old_chat_password # Hasło było już "zaszyfrowane" lub w plain text
        
        data["chat_servers"].append(migrated_server_entry)
        data["active_chat_server_id"] = migrated_server_id
        logging.info(f"Migrowano ustawienia pojedynczego serwera czatu do nowej struktury: {old_chat_server_url}")
    
    # Ustaw domyślne wartości dla nowej struktury, jeśli nadal ich nie ma
    if not data["chat_servers"]: # Jeśli po migracji nadal pusto (np. pierwszy start)
        default_server_id = str(uuid.uuid4())
        data["chat_servers"] = [{
            "id": default_server_id,
            "name": "Serwer Lokalny (Domyślny)",
            "url": "http://127.0.0.1:5000",
            "is_default": True,
            "last_used": None,
            "credentials": {},
            "remember_credentials": False,
            "auto_login_to_server": False
        }]
        data["active_chat_server_id"] = default_server_id
    
    # Upewnij się, że active_chat_server_id jest ustawiony, jeśli lista nie jest pusta
    if data["chat_servers"] and "active_chat_server_id" not in data:
        # Ustaw pierwszy serwer z listy jako aktywny lub domyślny, jeśli jest
        default_server = next((s for s in data["chat_servers"] if s.get("is_default")), None)
        data["active_chat_server_id"] = default_server["id"] if default_server else data["chat_servers"][0]["id"]

    data.setdefault("chat_auto_connect_to_default", True) # Globalne auto-łączenie z domyślnym
    # --- KONIEC NOWYCH ZMIAN ---
    data.setdefault("remote_control_enabled", False)
    data.setdefault("remote_control_port", 5000)
    data.setdefault("window_state", "normal")
    data.setdefault("window_geometry", "1024x768+100+100")
    data.setdefault("library_view_mode", "tiles")
    data.setdefault("tiles_per_row", 3)
    data.setdefault("discord_rpc_enabled", False) # Upewnij się, że jest tu
    data.setdefault("discord_status_text", "Korzysta z Game Launcher") # Upewnij się, że jest tu
    data.setdefault("ui_font", "Segoe UI") # Zakładając Segoe UI jako domyślną
    data.setdefault("window_maximized", False) # Z on_closing
    data.setdefault("last_run_date", "") # Dla dni z rzędu
    data.setdefault("consecutive_days", 0) # Dla dni z rzędu
    # --- WAŻNE: Użyj setdefault także dla czasu launchera ---
    data.setdefault("total_launcher_usage_seconds", 0)
    # --- KONIEC WAŻNEGO ---
    # --- NOWE ZMIANY (CHAT) ---
    # Domyślne wartości dla checkboxów logowania czatu
    data.setdefault("chat_remember_me", False) 
    data.setdefault("chat_auto_login", False)
    # --- KONIEC NOWYCH ZMIAN (CHAT) ---
    # --- NOWE: Ustawienie rozmiaru awatara ---
    data.setdefault("avatar_display_size", 48) # Domyślny rozmiar 48x48
    # --- NOWE: Ustawienia odtwarzacza muzyki ---
    data.setdefault("music_player_volume", 0.5)
    data.setdefault("last_music_folder", os.path.expanduser("~"))
    data.setdefault("music_hotkeys", DEFAULT_MUSIC_HOTKEYS.copy())
    data.setdefault("music_hotkeys_enabled", True) # Domyślnie skróty są włączone
    # --- NOWE ZMIANY ---
# --- NOWE ZMIANY ---
    # Usuwamy stare globalne wpisy dla playlisty
    # data.setdefault("music_playlist", []) # USUNIĘTE
    # data.setdefault("music_current_track_index", -1) # USUNIĘTE

    # Dodajemy nowe wpisy dla nazwanych playlist
    data.setdefault("named_music_playlists", {}) # Słownik na nazwane playlisty
    data.setdefault("active_music_playlist_name", None) # Nazwa aktywnej playlisty
    data.setdefault("current_track_in_active_playlist_index", -1) # Indeks w aktywnej playliście
# --- KONIEC NOWYCH ZMIAN ---
    # --- NOWE ZMIANY (CHAT) ---
    data.setdefault("chat_last_email", "")
    data.setdefault("chat_last_user_id", None) # Będzie int lub None
    # --- KONIEC NOWYCH ZMIAN (CHAT) ---
    data.setdefault("music_repeat_mode", "none") # "none", "one", "all"
    data.setdefault("music_shuffle_mode", False)
    # --- NOWE: Lista ulubionych utworów ---
    data.setdefault("music_favorite_tracks", []) # Lista ścieżek do ulubionych plików
    # --- KONIEC NOWEGO ---
    # --- KONIEC NOWYCH ZMIAN ---
    # --- NOWE ZMIANY: słownik czasu per‑dzień ---
    data.setdefault("launcher_daily_usage_seconds", {})
    # --- KONIEC NOWYCH ZMIAN ---
    data.setdefault("show_track_overlay", False) # Domyślnie wyłączone
    data.setdefault("overlay_x_pos", None)      # Domyślnie brak zapisanej pozycji
    data.setdefault("overlay_y_pos", None)
    return data


def save_local_settings(data):
    with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            try: # Dodano obsługę błędu odczytu JSON
                data = json.load(file)
            except json.JSONDecodeError as e:
                 logging.error(f"Błąd odczytu pliku {CONFIG_FILE}: {e}. Tworzenie nowego.")
                 # Zwróć kompletną domyślną strukturę w razie błędu
                 data = {"version": PROGRAM_VERSION, "games": {}, "settings": {}, "groups": {}, "user": {}, "emulators": {}, "saved_filters": {}}
                 return data # Zakończ wczytywanie w tym przypadku
    else:
        # --- ZMIANA: Dodano 'emulators' do struktury domyślnej ---
        data = {"version": PROGRAM_VERSION, "games": {}, "settings": {}, "groups": {}, "user": {}, "emulators": {}, "saved_filters": {}}
        # --- KONIEC ZMIANY ---

    # Upewnij się, że pole "version" jest obecne
    data.setdefault("version", "0.0.0") # Domyślna wersja, jeśli brakuje

    # Aktualizuj wersję tylko jeśli PROGRAM_VERSION jest nowszy niż zapisany
    if version.parse(PROGRAM_VERSION) > version.parse(data.get("version", "0.0.0")):
        data["version"] = PROGRAM_VERSION

    settings = data.setdefault("settings", {})
    # --- Poprawiona obsługa RSS ---
    if "rss_feeds" not in settings or not isinstance(settings["rss_feeds"], list):
        settings["rss_feeds"] = [
            {"url": "https://feeds.ign.com/ign/games-all", "active": True, "name": "IGN Games"}
        ]
    else:
        # Sprawdź, czy rss_feeds jest listą stringów i konwersja do listy słowników
        if all(isinstance(feed, str) for feed in settings["rss_feeds"]):
            settings["rss_feeds"] = [{"url": feed, "active": True, "name": feed} for feed in settings["rss_feeds"]]
        # Upewnij się, że każdy element jest słownikiem z wymaganymi kluczami
        settings["rss_feeds"] = [
            feed if isinstance(feed, dict) and "url" in feed else {"url": str(feed), "active": True, "name": str(feed)}
            for feed in settings["rss_feeds"]
        ]
    # --- Koniec poprawionej obsługi RSS ---
    # --- ZMIANA: Dodaj domyślne ładowanie/tworzenie 'custom_themes' ---
    # --- KONIEC ZMIANY ---
    settings.setdefault("news_post_limit", 10)  # Domyślny limit postów
    settings.setdefault("scan_ignore_folders", ["_CommonRedist", "DirectX", "DotNet", "Redist", "Tools", "Benchmark", "support", "data", "__overlay"]) # Dodano domyślne ignorowane foldery
    settings.setdefault("scan_recursively", True) # Domyślne skanowanie rekursywne
    # --- NOWE ZMIANY ---
    settings.setdefault("autoscan_screenshot_folders", []) # Lista folderów do skanowania screenshotów
    settings.setdefault("autoscan_on_startup", False) # Czy skanować przy starcie (domyślnie nie)
    # --- NOWE ZMIANY (IGNORE FOLDERS) ---
    # Upewnij się, że domyślne ignorowane foldery są tutaj
    settings.setdefault("screenshot_scan_ignore_folders", ["thumb_cache", "cache", "temp", "thumbnails"])
    # --- KONIEC NOWYCH ZMIAN (IGNORE FOLDERS) ---
    settings.setdefault("screenshot_filename_patterns", [ # Domyślne wzorce nazw plików screenshotów (proste)
        "{game_name}*.png",
        "{game_name}*.jpg",
        "{game_name}*.jpeg",
        # Można dodać bardziej złożone wzorce regex w przyszłości
    ])
    # --- KONIEC NOWYCH ZMIAN ---
    # --- Upewnij się, że każda gra ma listę profili ---
    for game_name, game_data in data.get("games", {}).items():
        # Upewnij się, że game_data jest słownikiem
        if not isinstance(game_data, dict):
            logging.warning(f"Nieprawidłowy format danych dla gry '{game_name}'. Pomijanie sprawdzania profili.")
            continue

        if "launch_profiles" not in game_data or not isinstance(game_data.get("launch_profiles"), list) or not game_data.get("launch_profiles"):
            default_profile = {"name": "Default", "exe_path": None, "arguments": ""}
            game_data["launch_profiles"] = [default_profile]
        else:
            # Sprawdź, czy istnieje profil "Default" i czy jest pierwszy
            default_found_at_zero = False
            default_found_elsewhere = False
            default_index = -1

            for i, p in enumerate(game_data["launch_profiles"]):
                 # Sprawdź, czy profil p jest słownikiem przed dostępem do .get()
                 if isinstance(p, dict) and p.get("name", "").lower() == "default":
                     if i == 0:
                         default_found_at_zero = True
                     else:
                         default_found_elsewhere = True
                         default_index = i
                     break # Znaleziono default, nie trzeba dalej szukać

            if default_found_elsewhere:
                 # Przenieś znaleziony default na początek
                 default_profile_obj = game_data["launch_profiles"].pop(default_index)
                 game_data["launch_profiles"].insert(0, default_profile_obj)
            elif not default_found_at_zero:
                 # Jeśli default nie istnieje nigdzie, dodaj go na początek
                 default_profile = {"name": "Default", "exe_path": None, "arguments": ""}
                 game_data["launch_profiles"].insert(0, default_profile)
    # --- KONIEC sprawdzania profili ---
        # --- NOWE ZMIANY ---
        # Upewnij się, że istnieje lista na ręczne screenshoty
        game_data.setdefault("screenshots", [])
        # Upewnij się, że istnieje lista na automatycznie znalezione screenshoty
        game_data.setdefault("autoscan_screenshots", [])
        # Upewnij się, że istnieje lista checklisty
        game_data.setdefault("checklist", [])
        # --- KONIEC NOWYCH ZMIAN ---
    # --- ZMIANA: Dodano domyślne ładowanie/tworzenie 'emulators' ---
    data.setdefault("emulators", {})
    # --- KONIEC ZMIANY ---
    # --- NOWE: Dodaj domyślne ładowanie/tworzenie 'saved_filters' ---
    data.setdefault("saved_filters", {})
    # --- KONIEC NOWEGO ---
    # --- NOWE: Dodaj sekcję osiągnięć użytkownika ---
    user_data = data.setdefault("user", {}) # Upewnij się, że 'user' istnieje
    user_data.setdefault("achievements", {}) # Dodaj pusty słownik na postępy
    # Format: "user": {"username": "...", "achievements": {"first_launch": {"unlocked": true, "timestamp": 123456789.0}, ...}}
    # --- KONIEC NOWEGO ---

    return data


def save_config(data):
    data_copy = data.copy()
    data_copy.get("settings", {}).pop("github_token", None)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(data_copy, file, indent=4, ensure_ascii=False)


def create_default_cover(game_name, size=(200, 300)):
    # Tworzenie prostego obrazka z nazwą gry
    image = Image.new('RGB', size, color='#1e1e1e')
    draw = ImageDraw.Draw(image)
    try:
        # Maksymalny rozmiar czcionki
        max_font_size = 48
        font_size = max_font_size
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        font_size = 10  # Domyślny rozmiar dla wbudowanej czcionki

    # Dostosowanie rozmiaru czcionki, aby tekst zmieścił się na okładce
    while True:
        try:
            bbox = draw.textbbox((0, 0), game_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # Dla starszych wersji Pillow
            text_width, text_height = draw.textsize(game_name, font=font)

        if text_width <= size[0] - 20 or font_size <= 10:
            break
        font_size -= 2
        font = ImageFont.truetype("arial.ttf", font_size)

    # Dzielimy nazwę gry na kilka linii, jeśli jest za długa
    words = game_name.split()
    lines = []
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w, h = draw.textsize(test_line, font=font)
        if w <= size[0] - 20:
            line = test_line
        else:
            lines.append(line)
            line = word
    lines.append(line)

    total_text_height = len(lines) * text_height
    text_y = (size[1] - total_text_height) // 2

    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w, h = draw.textsize(line, font=font)
        text_x = (size[0] - w) // 2
        draw.text((text_x, text_y), line, fill='white', font=font)
        text_y += text_height

    image_path = os.path.join(IMAGES_FOLDER, f"{game_name}.png")
    image.save(image_path)
    return image_path


def load_photoimage_from_path(image_path, size):
    """Ładuje obraz z podanej ścieżki, skaluje i tworzy PhotoImage. Wynik jest cache'owany."""
    try:
        # Mimo że to miniatura, otwórzmy ją na nowo, bo PhotoImage wymaga obiektu Image
        with Image.open(image_path) as img:
             # Miniaturka powinna już być w dobrym rozmiarze, ale przeskalujmy dla pewności
             # lub jeśli chcemy dynamicznie zmieniać rozmiar kafelków
             img = img.resize(size, resampling)
             return ImageTk.PhotoImage(img)
    except (UnidentifiedImageError, FileNotFoundError, OSError, ValueError) as e:
        logging.error(f"Błąd ładowania PhotoImage z '{image_path}': {e}")
        # Można zwrócić domyślny obrazek błędu jako PhotoImage
        try:
            # Spróbuj załadować predefiniowany obraz błędu, jeśli istnieje
            # error_img = Image.open("error_cover.png")
            # return ImageTk.PhotoImage(error_img.resize(size, resampling))
             # Lub stwórz prosty obraz błędu programowo
             error_img = Image.new('RGB', size, color='red')
             draw = ImageDraw.Draw(error_img)
             draw.text((10, 10), "Błąd\nObrazu", fill="white")
             return ImageTk.PhotoImage(error_img)
        except Exception as inner_e:
            logging.error(f"Nie można nawet utworzyć domyślnego obrazu błędu: {inner_e}")
            return None # Ostateczność
from .shared_imports import (
    logging,
    json,
    os,
    uuid,
    time,
    version,
    Image,
    ImageDraw,
    ImageFont,
    ImageTk,
    UnidentifiedImageError,
    functools,
)
from .constants import (
    DEFAULT_MUSIC_HOTKEYS,
    LOCAL_SETTINGS_FILE,
    CONFIG_FILE,
    PROGRAM_VERSION,
    THEMES,
    CUSTOM_THEMES_DIR,
    resampling,
    IMAGES_FOLDER,
)

