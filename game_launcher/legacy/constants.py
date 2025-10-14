"""Constants extracted from the legacy monolithic launcher."""
from __future__ import annotations

from PIL import Image

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

DEFAULT_MUSIC_HOTKEYS = {
    "play_pause": "<alt>+<space>",
    "next_track": "<alt>+<right>",
    "prev_track": "<alt>+<left>",
    "stop_music": "<alt>+s",
    "volume_up": "<alt>+<up>",
    "volume_down": "<alt>+<down>",
}

MONTH_COLORS = {
    12: "#4682B4",
    1: "#708090",
    2: "#B0E0E6",
    3: "#98FB98",
    4: "#FAEBD7",
    5: "#FFC0CB",
    6: "#FFD700",
    7: "#FF4500",
    8: "#FF6347",
    9: "#CD853F",
    10: "#d6b17a",
    11: "#8B008B",
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

PROGRAM_VERSION = "1.6.0"
CONFIG_FILE = "config.json"
GAMES_FOLDER = "games_saves"
IMAGES_FOLDER = "images"
INTERNAL_MUSIC_DIR = "internal_music"
CUSTOM_THEMES_DIR = "custom_themes"
LOCAL_SETTINGS_FILE = "local_settings.json"

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

try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9.1 fallback
    RESAMPLING = Image.LANCZOS

__all__ = [
    "MONTH_COLORS",
    "DEFAULT_MUSIC_HOTKEYS",
    "MONTH_NAMES_PL",
    "PROGRAM_VERSION",
    "CONFIG_FILE",
    "GAMES_FOLDER",
    "IMAGES_FOLDER",
    "INTERNAL_MUSIC_DIR",
    "CUSTOM_THEMES_DIR",
    "LOCAL_SETTINGS_FILE",
    "THEMES",
    "RESAMPLING",
]

def ensure_legacy_directories():
    """Ensure filesystem locations used by legacy features exist."""
    import os

    for path in (IMAGES_FOLDER, INTERNAL_MUSIC_DIR, CUSTOM_THEMES_DIR):
        os.makedirs(path, exist_ok=True)


__all__.append("ensure_legacy_directories")
