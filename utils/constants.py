import os
from PIL import Image

# Stałe kolorów i nazw miesięcy
MONTH_COLORS = {
    1: "lightblue",
    2: "lightgreen",
    3: "pink",
    4: "yellow",
    5: "orange",
    6: "lightgrey",
    7: "lightcoral",
    8: "violet",
    9: "lightgoldenrod",
    10: "lightsalmon",
    11: "lightcyan",
    12: "lightsteelblue",
}

MONTH_NAMES_PL = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień",
}

# Wersja programu
PROGRAM_VERSION = "1.5.0"

# Ścieżki plików i folderów
DATA_DIR = os.path.join("data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
CHAT_DATA_DIR = os.path.join(DATA_DIR, "chat")
EXTERNAL_DIR = os.path.join("external")

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
GAMES_FOLDER = os.path.join(DATA_DIR, "games_saves")
IMAGES_FOLDER = "images"
THUMBNAIL_FOLDER = os.path.join(IMAGES_FOLDER, "thumbnails")
LOCAL_SETTINGS_FILE = os.path.join(CONFIG_DIR, "local_settings.json")
ACHIEVEMENTS_DEFINITIONS_FILE = os.path.join(CONFIG_DIR, "achievements_def.json")
CHAT_DB_FILE = os.path.join(CHAT_DATA_DIR, "chat.db")
SCRIPTHOOK_CONFIG_FILE = os.path.join(EXTERNAL_DIR, "ScriptHookConfig.ini")
MODS_STORAGE_FOLDER = "mods_storage"  # Dodano brakującą stałą

# Motywy
THEMES = {
    "Dark": {
        "background": "#1e1e1e",
        "foreground": "white",
        "button_background": "#2e2e2e",
        "button_foreground": "white",
    },
    "Light": {
        "background": "white",
        "foreground": "black",
        "button_background": "#f0f0f0",
        "button_foreground": "black",
    },
    "Blue": {
        "background": "#1e1e2e",
        "foreground": "white",
        "button_background": "#2e2e3e",
        "button_foreground": "white",
    },
}

# Ustawienie resampling dla Pillow (kompatybilność wsteczna)
try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING = Image.LANCZOS

# Domyślne kanały RSS
DEFAULT_RSS_FEEDS = [
    {"url": "https://feeds.ign.com/ign/games-all", "active": True, "name": "IGN Games"}
]

# Domyślny limit postów w newsach
DEFAULT_NEWS_POST_LIMIT = 10

# Domyślna szerokość kafelka gry
DEFAULT_TILE_WIDTH = 200
DEFAULT_TILE_HEIGHT = 300  # Dodano wysokość dla spójności

# Domyślna liczba elementów na stronę w siatce gier
DEFAULT_ITEMS_PER_PAGE = 24

# Nazwy plików wykonywalnych często spotykane w grach (do skanowania)
COMMON_EXECUTABLES = [
    "game.exe",
    "launcher.exe",
    "play.exe",
    "start.exe",
    "run.exe",
    "main.exe",
]

# Słowa kluczowe wskazujące na główny plik wykonywalny
EXECUTABLE_KEYWORDS = ["game", "play", "launch", "start", "main", "bin", "win64", "x64"]

# Wzorce do usuwania z nazw folderów przy zgadywaniu nazwy gry
FOLDER_NAME_CLEANUP_PATTERNS = [
    r"\[.*?\]",
    r"\(.*?\)",  # Usuń zawartość w nawiasach kwadratowych i okrągłych
    r"v\d+(\.\d+)*",  # Usuń wersje np. v1.2
    r"Build\.\d+",  # Usuń np. Build.12345
    r"Update\.\d+",  # Usuń np. Update.1
    r"CODEX",
    r"FLT",
    r"PLAZA",
    r"CPY",
    r"SKIDROW",
    r"RELOADED",  # Nazwy grup P2P
    r"GOG",
    r"Steam",
    r"Epic",  # Nazwy platform
    r"MULTi\d*",
    r"RUS",
    r"ENG",  # Oznaczenia językowe
    r"Repack",
    r"Portable",  # Typy wydań
    r"\.",  # Zamień kropki na spacje (często używane zamiast spacji)
]

# Wzorce do parsowania plików NFO
NFO_PATTERNS = {
    "title": [r"Title\s*:\s*(.*)", r"Game\s*:\s*(.*)"],
    "developer": [r"Developer\s*:\s*(.*)"],
    "publisher": [r"Publisher\s*:\s*(.*)"],
    "release_date": [r"Release Date\s*:\s*(.*)", r"Date\s*:\s*(.*)"],
    "genres": [r"Genre\s*:\s*(.*)"],
    "description": [r"Description\s*:\s*(.*)", r"Summary\s*:\s*(.*)"],
    # Można dodać więcej wzorców
}
