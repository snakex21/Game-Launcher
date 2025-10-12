from .shared_imports import Image

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
    12: "lightsteelblue"
}

DEFAULT_MUSIC_HOTKEYS = {
    "play_pause": "<alt>+<space>",  # Poprawny format dla spacji
    "next_track": "<alt>+<right>",
    "prev_track": "<alt>+<left>",
    "stop_music": "<alt>+s",      # 's' jest OK bez nawiasów
    "volume_up": "<alt>+<up>",
    "volume_down": "<alt>+<down>"
}


MONTH_COLORS = {
    # ZIMA (Grudzień, Styczeń, Luty) - chłodne odcienie błękitu i szarości
    12: "#4682B4",  # Granatowy (SteelBlue)
    1:  "#708090",  # Szary stalowy (SlateGray)
    2:  "#B0E0E6",  # Błękit lodowy (PowderBlue)

    # WIOSNA (Marzec, Kwiecień, Maj) - świeże kolory i kwiatowe akcenty
    3:  "#98FB98",  # Jasnozielony (PaleGreen)
    4:  "#FAEBD7",  # Alabaster (AntiqueWhite)
    5:  "#FFC0CB",  # Różowy (Pink)

    # LATO (Czerwiec, Lipiec, Sierpień) - słoneczne i energiczne kolory
    6:  "#FFD700",  # Złoty (Gold)
    7:  "#FF4500",  # Pomarańczowo-czerwony (OrangeRed)
    8:  "#FF6347",  # Łososiowy (Tomato)

    # JESIEŃ (Wrzesień, Październik, Listopad) - ciepłe ziemiście odcienie
    9:  "#CD853F",  # Brązowy (Peru)
    10: "#d6b17a",  # Pomarańcz głęboki (DarkOrange)
    11: "#8B008B",  # Fiolet ciemny (DarkMagenta)
}
# --- KONIEC NOWEJ PALETY ---

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
    12: "Grudzień"
}

try:
    resampling = Image.Resampling.LANCZOS
except AttributeError:
    resampling = Image.LANCZOS  # Dla starszych wersji Pillow

PROGRAM_VERSION = "1.6.0"  # Aktualna wersja programu

# Plik do przechowywania danych
CONFIG_FILE = "config.json"
GAMES_FOLDER = "games_saves"
IMAGES_FOLDER = "images"  # Definicja IMAGES_FOLDER jest tutaj
INTERNAL_MUSIC_DIR = "internal_music"
# --- NOWE ZMIANY ---
CUSTOM_THEMES_DIR = "custom_themes"  # Nowy folder na niestandardowe motywy
# --- KONIEC NOWYCH ZMIAN ---
LOCAL_SETTINGS_FILE = "local_settings.json"
THEMES = {
    'Dark': {
        'background': '#1e1e1e',
        'foreground': 'white',
        'button_background': '#2e2e2e',
        'button_foreground': 'white',
        'entry_background': '#2e2e2e',
        'tree_background': '#2e2e2e',
        'tree_heading': '#3e3e3e',
        'scrollbar_trough': '#1e1e1e',
        'scrollbar_slider': '#555555',
        'link_foreground': '#66b3ff',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#0078D7',  # Niebieski
        'chart_axis_color': '#aaaaaa',  # Jasnoszary
        # --- KONIEC NOWYCH ---
    },
    'Light': {
        'background': 'white',
        'foreground': 'black',
        'button_background': '#e0e0e0',
        'button_foreground': 'black',
        'entry_background': '#f0f0f0',
        'tree_background': '#fdfdfd',
        'tree_heading': '#f0f0f0',
        'scrollbar_trough': '#f0f0f0',
        'scrollbar_slider': '#cccccc',
        'link_foreground': '#0066cc',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#4477AA',  # Ciemniejszy niebieski
        'chart_axis_color': '#555555',  # Ciemnoszary
        # --- KONIEC NOWYCH ---
    },
    'Blue': {
        'background': '#1e1e2e',
        'foreground': 'white',
        'button_background': '#2e2e3e',
        'button_foreground': 'white',
        'entry_background': '#2e2e3e',
        'tree_background': '#2e2e3e',
        'tree_heading': '#3e3e4e',
        'scrollbar_trough': '#1e1e2e',
        'scrollbar_slider': '#555577',
        'link_foreground': '#88ccff',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#5599FF',  # Jaśniejszy niebieski
        'chart_axis_color': '#bbbbdd',  # Jasny niebiesko-szary
        # --- KONIEC NOWYCH ---
    },
    'Forest Green': {
        'background': '#1a2a1a',
        'foreground': '#e0ffe0',
        'button_background': '#2a4a2a',
        'button_foreground': '#e0ffe0',
        'entry_background': '#2a3a2a',
        'tree_background': '#2a3a2a',
        'tree_heading': '#3a5a3a',
        'scrollbar_trough': '#1a2a1a',
        'scrollbar_slider': '#446644',
        'link_foreground': '#99ff99',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#55AA55',  # Zielony
        'chart_axis_color': '#99cc99',  # Jasnozielony/szary
        # --- KONIEC NOWYCH ---
    },
    'Deep Purple': {
        'background': '#2d1a2d',
        'foreground': '#ffe0ff',
        'button_background': '#4d2a4d',
        'button_foreground': '#ffe0ff',
        'entry_background': '#3d2a3d',
        'tree_background': '#3d2a3d',
        'tree_heading': '#5d3a5d',
        'scrollbar_trough': '#2d1a2d',
        'scrollbar_slider': '#664466',
        'link_foreground': '#ffb3ff',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#9966CC',  # Fioletowy
        'chart_axis_color': '#cc99ff',  # Jasnofioletowy
        # --- KONIEC NOWYCH ---
    },
    'Solarized Dark': {
        'background': '#002b36',
        'foreground': '#839496',
        'button_background': '#073642',
        'button_foreground': '#93a1a1',
        'entry_background': '#073642',
        'tree_background': '#073642',
        'tree_heading': '#0a404f',
        'scrollbar_trough': '#002b36',
        'scrollbar_slider': '#586e75',
        'link_foreground': '#268bd2',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#2aa198',  # Cyan
        'chart_axis_color': '#586e75',  # Szary
        # --- KONIEC NOWYCH ---
    },
    'Gruvbox Dark': {
        'background': '#282828',
        'foreground': '#ebdbb2',
        'button_background': '#3c3836',
        'button_foreground': '#ebdbb2',
        'entry_background': '#504945',
        'tree_background': '#3c3836',
        'tree_heading': '#504945',
        'scrollbar_trough': '#282828',
        'scrollbar_slider': '#665c54',
        'link_foreground': '#83a598',
        # --- NOWE KLUCZE WYKRESÓW ---
        'chart_bar_color': '#fabd2f',  # Żółty
        'chart_axis_color': '#a89984',  # Szaro-beżowy
        # --- KONIEC NOWYCH ---
    },
}

__all__ = [
    'MONTH_COLORS',
    'DEFAULT_MUSIC_HOTKEYS',
    'MONTH_NAMES_PL',
    'resampling',
    'PROGRAM_VERSION',
    'CONFIG_FILE',
    'GAMES_FOLDER',
    'IMAGES_FOLDER',
    'INTERNAL_MUSIC_DIR',
    'CUSTOM_THEMES_DIR',
    'LOCAL_SETTINGS_FILE',
    'THEMES',
]
