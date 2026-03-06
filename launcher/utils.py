"""
Narzędzia i stałe dla Game Launchera.
"""

PROGRAM_VERSION = "1.6.0"

import functools
import logging
import json
import os
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageColor, UnidentifiedImageError


# Ścieżki plików i folderów
DATA_DIR = os.path.join("data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
CHAT_DATA_DIR = os.path.join(DATA_DIR, "chat")
EXTERNAL_DIR = os.path.join("external")

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
GAMES_FOLDER = os.path.join(DATA_DIR, "games_saves")
IMAGES_FOLDER = "images"
INTERNAL_MUSIC_DIR = "internal_music"
CUSTOM_THEMES_DIR = "custom_themes"
LOCAL_SETTINGS_FILE = os.path.join(CONFIG_DIR, "local_settings.json")
ACHIEVEMENTS_DEFINITIONS_FILE = os.path.join(CONFIG_DIR, "achievements_def.json")
CHAT_DB_FILE = os.path.join(CHAT_DATA_DIR, "chat.db")
SCRIPTHOOK_CONFIG_FILE = os.path.join(EXTERNAL_DIR, "ScriptHookConfig.ini")

# MONTH_COLORS - kolory dla miesięcy (używane w statystykach)
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

# MONTH_NAMES_PL - polskie nazwy miesięcy
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


def get_contrast_color(hex_color):
    """Zwraca 'black' lub 'white' w zależności od jasności koloru (HEX lub nazwa)."""
    try:
        if not isinstance(hex_color, str) or not hex_color.strip():
            return "black"

        color = hex_color.strip()
        if color.startswith("#"):
            color = color[1:]

        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)

        if len(color) == 6:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        else:
            r, g, b = ImageColor.getrgb(hex_color)

        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        threshold = 145
        return "black" if luminance > threshold else "white"

    except ValueError:
        logging.warning(
            f"Nieprawidłowy format HEX w get_contrast_color (ValueError): {hex_color}"
        )
        return "black"
    except Exception as e:
        logging.error(f"Błąd w get_contrast_color dla {hex_color}: {e}")
        return "black"


try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING = Image.LANCZOS


DEFAULT_MUSIC_HOTKEYS = {
    "play_pause": "<alt>+<space>",
    "next_track": "<alt>+<right>",
    "prev_track": "<alt>+<left>",
    "stop_music": "<alt>+s",
    "volume_up": "<alt>+<up>",
    "volume_down": "<alt>+<down>",
}


THEMES = {
    "Dark": {
        "background": "#1e1e1e",
        "foreground": "white",
        "button_background": "#2e2e2e",
        "button_foreground": "white",
        "entry_background": "#2e2e2e",
        "tree_background": "#2e2e2e",
        "tree_heading": "#3e3e3e",
        "scrollbar_trough": "#1e1e1e",
        "scrollbar_slider": "#555555",
        "link_foreground": "#66b3ff",
        "chart_bar_color": "#0078D7",
        "chart_axis_color": "#aaaaaa",
    },
    "Light": {
        "background": "white",
        "foreground": "black",
        "button_background": "#e0e0e0",
        "button_foreground": "black",
        "entry_background": "#f0f0f0",
        "tree_background": "#fdfdfd",
        "tree_heading": "#f0f0f0",
        "scrollbar_trough": "#f0f0f0",
        "scrollbar_slider": "#cccccc",
        "link_foreground": "#0066cc",
        "chart_bar_color": "#4477AA",
        "chart_axis_color": "#555555",
    },
    "Blue": {
        "background": "#1e1e2e",
        "foreground": "white",
        "button_background": "#2e2e3e",
        "button_foreground": "white",
        "entry_background": "#2e2e3e",
        "tree_background": "#2e2e3e",
        "tree_heading": "#3e3e4e",
        "scrollbar_trough": "#1e1e2e",
        "scrollbar_slider": "#555577",
        "link_foreground": "#88ccff",
        "chart_bar_color": "#5599FF",
        "chart_axis_color": "#bbbbdd",
    },
    "Forest Green": {
        "background": "#1a2a1a",
        "foreground": "#e0ffe0",
        "button_background": "#2a4a2a",
        "button_foreground": "#e0ffe0",
        "entry_background": "#2a3a2a",
        "tree_background": "#2a3a2a",
        "tree_heading": "#3a5a3a",
        "scrollbar_trough": "#1a2a1a",
        "scrollbar_slider": "#446644",
        "link_foreground": "#99ff99",
        "chart_bar_color": "#55AA55",
        "chart_axis_color": "#99cc99",
    },
    "Deep Purple": {
        "background": "#2d1a2d",
        "foreground": "#ffe0ff",
        "button_background": "#4d2a4d",
        "button_foreground": "#ffe0ff",
        "entry_background": "#3d2a3d",
        "tree_background": "#3d2a3d",
        "tree_heading": "#5d3a5d",
        "scrollbar_trough": "#2d1a2d",
        "scrollbar_slider": "#664466",
        "link_foreground": "#ffb3ff",
        "chart_bar_color": "#9966CC",
        "chart_axis_color": "#cc99ff",
    },
    "Solarized Dark": {
        "background": "#002b36",
        "foreground": "#839496",
        "button_background": "#073642",
        "button_foreground": "#93a1a1",
        "entry_background": "#073642",
        "tree_background": "#073642",
        "tree_heading": "#0a404f",
        "scrollbar_trough": "#002b36",
        "scrollbar_slider": "#586e75",
        "link_foreground": "#268bd2",
        "chart_bar_color": "#2aa198",
        "chart_axis_color": "#586e75",
    },
    "Gruvbox Dark": {
        "background": "#282828",
        "foreground": "#ebdbb2",
        "button_background": "#3c3836",
        "button_foreground": "#ebdbb2",
        "entry_background": "#504945",
        "tree_background": "#3c3836",
        "tree_heading": "#504945",
        "scrollbar_trough": "#282828",
        "scrollbar_slider": "#665c54",
        "link_foreground": "#83a598",
        "chart_bar_color": "#fabd2f",
        "chart_axis_color": "#a89984",
    },
}


class DummyTranslator:
    """Prosta klasa zastępująca Translator, zwracająca polski tekst."""

    def __init__(self):
        self.translations = {
            "Game Launcher": "Game Launcher",
            "Home": "Strona Główna",
            "Library": "Biblioteka",
            "Roadmap": "Roadmapa",
            "Mod Manager": "Menedżer Modów",
            "Achievements": "Osiągnięcia",
            "News": "Newsy",
            "Settings": "Ustawienia",
            "Exit": "Wyjście",
            "Fullscreen Mode": "Tryb Pełnoekranowy",
            "Minimize to Tray": "Zminimalizuj do zasobnika",
        }
        logging.info("DummyTranslator initialized with Polish string map.")

    def gettext(self, text):
        return self.translations.get(text, text)

    def set_language(self, language_code):
        pass


def _load_theme_from_file(filepath: str) -> dict | None:
    """Laduje definicje motywu z pliku JSON."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if (
                isinstance(data, dict)
                and "name" in data
                and "definition" in data
                and isinstance(data["definition"], dict)
            ):
                return data
            else:
                logging.warning(
                    f"Plik motywu '{filepath}' ma nieprawidlowa strukture."
                )
                return None
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Blad odczytu pliku motywu '{filepath}': {e}.")
        return None


def save_config(data):
    data_copy = data.copy()
    data_copy.get("settings", {}).pop("github_token", None)
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(data_copy, file, indent=4, ensure_ascii=False)


def create_default_cover(game_name, size=(200, 300)):
    image = Image.new("RGB", size, color="#1e1e1e")
    draw = ImageDraw.Draw(image)
    try:
        max_font_size = 48
        font_size = max_font_size
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        font_size = 10

    while True:
        try:
            bbox = draw.textbbox((0, 0), game_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(game_name, font=font)

        if text_width <= size[0] - 20 or font_size <= 10:
            break
        font_size -= 2
        font = ImageFont.truetype("arial.ttf", font_size)

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
        draw.text((text_x, text_y), line, fill="white", font=font)
        text_y += text_height

    image_path = os.path.join(IMAGES_FOLDER, f"{game_name}.png")
    image.save(image_path)
    return image_path


@functools.lru_cache(maxsize=256)
def load_photoimage_from_path(image_path, size):
    try:
        with Image.open(image_path) as img:
            img = img.resize(size, RESAMPLING)
            return ImageTk.PhotoImage(img)
    except (UnidentifiedImageError, FileNotFoundError, OSError, ValueError) as e:
        logging.error(f"Blad ladowania PhotoImage z '{image_path}': {e}")
        try:
            error_img = Image.new("RGB", size, color="red")
            draw = ImageDraw.Draw(error_img)
            draw.text((10, 10), "Blad\nObrazu", fill="white")
            return ImageTk.PhotoImage(error_img)
        except Exception as inner_e:
            logging.error(
                f"Nie mozna nawet utworzyc domyslnego obrazu bledu: {inner_e}"
            )
            return None
