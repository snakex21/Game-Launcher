"""
Stałe globalne dla Game Launcher
Zawiera wszystkie stałe wartości używane w aplikacji.
"""

from pathlib import Path

# ============================================================================
# ŚCIEŻKI I PLIKI
# ============================================================================

# Katalog główny aplikacji
APP_DIR = Path(__file__).parent.parent
DATA_DIR = APP_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"

# Pliki konfiguracyjne
CONFIG_FILE = "games.json"
SETTINGS_FILE = "local_settings.json"
ACHIEVEMENTS_FILE = "achievements.json"
MOD_MANAGER_FILE = "mod_manager_config.json"
CALENDAR_EVENTS_FILE = "calendar_events.json"
CHAT_SERVERS_FILE = "chat_servers.json"

# Pliki logów
LOG_FILE = "game_launcher.log"

# ============================================================================
# DISCORD RICH PRESENCE
# ============================================================================

DISCORD_CLIENT_ID = "1234567890123456789"  # Zamień na właściwy Client ID

# Możliwe stany Discord RPC
DISCORD_STATE_BROWSING = "Przegląda bibliotekę"
DISCORD_STATE_PLAYING = "Gra w:"
DISCORD_STATE_IDLE = "Bezczynny"

# ============================================================================
# LAST.FM API
# ============================================================================

LASTFM_API_KEY = "your_lastfm_api_key_here"
LASTFM_API_SECRET = "your_lastfm_api_secret_here"
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

# ============================================================================
# GITHUB API (dla aktualizacji)
# ============================================================================

GITHUB_REPO = "username/game-launcher"  # Zamień na właściwy repo
GITHUB_API_URL = "https://api.github.com"

# ============================================================================
# SERWER CZATU (FLASK)
# ============================================================================

CHAT_SERVER_HOST = "0.0.0.0"
CHAT_SERVER_PORT = 5000
CHAT_SERVER_DEBUG = False

# ============================================================================
# UI - KOLORY
# ============================================================================

# Kolory motywu ciemnego
COLOR_BG_DARK = "#1e1e1e"
COLOR_BG_DARKER = "#161616"
COLOR_FG_LIGHT = "#ffffff"
COLOR_ACCENT = "#0078d4"
COLOR_ACCENT_HOVER = "#106ebe"
COLOR_SUCCESS = "#107c10"
COLOR_WARNING = "#ff8c00"
COLOR_ERROR = "#e81123"

# Kolory dla overlay
COLOR_OVERLAY_TRANSPARENT = "lime green"
COLOR_OVERLAY_BG_FALLBACK = "#212121"

# ============================================================================
# UI - CZCIONKI
# ============================================================================

FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 9
FONT_SIZE_SMALL = 8
FONT_SIZE_LARGE = 11
FONT_SIZE_TITLE = 14

# ============================================================================
# UI - WYMIARY
# ============================================================================

# Główne okno
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 800

# Overlay odtwarzacza muzyki
OVERLAY_WIDTH = 300
OVERLAY_HEIGHT = 70

# Rozmiary miniatur
THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_QUALITY = 85

# ============================================================================
# LIMITY I WARTOŚCI DOMYŚLNE
# ============================================================================

# Limity dla różnych funkcji
MAX_RECENT_GAMES = 10
MAX_SEARCH_RESULTS = 100
MAX_CALENDAR_EVENTS = 1000
MAX_ACHIEVEMENTS = 500

# Interwały odświeżania (w sekundach)
REFRESH_INTERVAL_STATS = 60
REFRESH_INTERVAL_NEWS = 3600
REFRESH_INTERVAL_MUSIC = 1

# Limity czasu (timeout) dla requestów HTTP
HTTP_TIMEOUT = 10  # sekundy

# ============================================================================
# GAMEPAD
# ============================================================================

# Nazwy przycisków gamepad (Xbox-style)
GAMEPAD_BTN_A = "BTN_SOUTH"
GAMEPAD_BTN_B = "BTN_EAST"
GAMEPAD_BTN_X = "BTN_WEST"
GAMEPAD_BTN_Y = "BTN_NORTH"
GAMEPAD_BTN_START = "BTN_START"
GAMEPAD_BTN_SELECT = "BTN_SELECT"
GAMEPAD_BTN_LB = "BTN_TL"
GAMEPAD_BTN_RB = "BTN_TR"

# Deadzone dla analogów
GAMEPAD_DEADZONE = 0.2

# ============================================================================
# FORMATY PLIKÓW
# ============================================================================

# Obsługiwane formaty obrazów
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

# Obsługiwane formaty audio
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.wma']

# Obsługiwane formaty wideo
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']

# ============================================================================
# WERSJA APLIKACJI
# ============================================================================

APP_NAME = "Game Launcher"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Twoje Imię"
APP_DESCRIPTION = "Kompleksowy launcher do zarządzania grami, muzyką i nie tylko"

# ============================================================================
# RÓŻNE
# ============================================================================

# Domyślny język
DEFAULT_LANGUAGE = "pl"

# Format daty i czasu
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

# Maksymalny rozmiar cache (w MB)
MAX_CACHE_SIZE_MB = 500

# Automatyczne zapisywanie (w sekundach)
AUTO_SAVE_INTERVAL = 300  # 5 minut
