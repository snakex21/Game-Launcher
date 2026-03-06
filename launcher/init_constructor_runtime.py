import datetime
import importlib
import logging
import os
import queue
import re
import threading
import time
import tkinter as tk
from typing import TYPE_CHECKING
from tkinter import ttk

from launcher.config_store import (
    load_config as config_load_config,
    load_local_settings as config_load_local_settings,
    save_local_settings as config_save_local_settings,
)
from launcher.utils import (
    CUSTOM_THEMES_DIR,
    GAMES_FOLDER,
    IMAGES_FOLDER,
    INTERNAL_MUSIC_DIR,
    THEMES,
    DummyTranslator,
)
if TYPE_CHECKING:
    from ui.mod_manager import ExtendedModManager


def initialize(self, root):
    self.launcher_start_time = time.time()
    self.root = root
    self.root.title("Game Launcher")
    self.root.configure(bg="#1e1e1e")
    self._resize_timer = None
    self.root.bind("<Configure>", self._on_root_resize)
    self._button_icons = {}
    self._menu_icons = {}
    self.start_up_time_points = {}
    self.record_startup_time("init_start")
    self._load_icons()
    self.local_settings = config_load_local_settings()
    self.current_section = "Strona Główna"

    self._library_initialized = False
    self._achievements_initialized = False
    self._news_initialized = False
    self._news_loaded = False
    self._reminders_initialized = False
    self._settings_initialized = False
    self._roadmap_initialized = False
    self._stats_initialized = False
    self._server_selection_initialized = False

    self.chat_servers_list = self.local_settings.get("chat_servers", [])
    self.active_chat_server_id = self.local_settings.get("active_chat_server_id")
    self.chat_auto_connect_to_default_var = tk.BooleanVar(
        value=self.local_settings.get("chat_auto_connect_to_default", True)
    )

    self.chat_server_url = "http://127.0.0.1:5000"
    self.current_server_credentials = {"email": "", "password": ""}
    self.current_server_remember_credentials = False
    self.current_server_auto_login = False

    active_server_data = self._get_active_server_data()
    if active_server_data:
        self.chat_server_url = active_server_data.get("url", self.chat_server_url)
        creds = active_server_data.get("credentials", {})
        self.current_server_credentials["email"] = creds.get("email", "")
        self.current_server_credentials["password"] = creds.get("password", "")
        self.current_server_remember_credentials = active_server_data.get(
            "remember_credentials", False
        )
        self.current_server_auto_login = active_server_data.get(
            "auto_login_to_server", False
        )

    if not hasattr(self, "chat_server_url_var"):
        self.chat_server_url_var = tk.StringVar(value=self.chat_server_url)
    else:
        self.chat_server_url_var.set(self.chat_server_url)

    self.sio = None
    self.chat_logged_in_user = None
    self.chat_connected_to_server = False
    self.chat_authenticated = False
    self.chat_users = {}
    self.active_chat_partner_id = None
    self._last_open_chat_partner_id = None
    self.chat_messages = {}
    self.CHAT_PREFIX_USER = "u_"
    self.CHAT_PREFIX_ROOM = "r_"
    self.chat_rooms = {}
    self.active_chat_type = None
    self._current_chat_participants = {}
    self.unread_messages_count = {}
    self.online_users = set()
    self._last_chat_message_search_term = ""
    self._pending_chat_attachment = None
    self.blocked_user_ids = set(self.local_settings.get("chat_blocked_user_ids", []))

    self.typing_status = {}
    self._typing_timeout_timer = None
    self._typing_sent_flag = False
    self.chat_email_var = tk.StringVar()
    self.chat_password_var = tk.StringVar()
    self.chat_username_var = tk.StringVar()
    self.chat_remember_me_var = tk.BooleanVar(
        value=self.current_server_remember_credentials
    )
    self.chat_auto_login_var = tk.BooleanVar(value=self.current_server_auto_login)
    self.chat_dashboard_placeholder_id = "chat_dashboard_view"
    self._rendered_chat_partner_id = None
    self.chat_page_size = 50
    self.chat_history_has_more = False
    self.chat_history_before = None
    self.chat_history_loading = False
    self.MESSAGE_HIGHLIGHT_COLOR = "#FFD700"
    self._rendered_message_widgets = {}
    self._jump_target_message_id = None

    self.library_view_mode = tk.StringVar(
        value=self.local_settings.get("library_view_mode", "tiles")
    )
    self.filter_or_group_var = tk.StringVar(value="Wszystkie Gry")
    self.search_var = tk.StringVar()
    self.filter_var = tk.StringVar(value="Wszystkie Gatunki")
    self.tag_filter_var = tk.StringVar(value="Wszystkie Tagi")
    self.game_type_filter_var = tk.StringVar(value="Wszystkie Typy")
    self.sort_var = tk.StringVar(value="Nazwa")

    logging.info(f"Załadowano ustawienia lokalne: {self.local_settings}")
    self.stats_bar_color = "#0078d7"

    saved_geometry_str = self.local_settings.get("window_geometry")
    saved_maximized = self.local_settings.get("window_maximized", False)
    initial_center_width = 1024
    initial_center_height = 768

    if saved_geometry_str and re.match(r"^\d+x\d+", saved_geometry_str):
        try:
            parts = saved_geometry_str.split("x")
            initial_center_width = int(parts[0])
            initial_center_height = int(parts[1].split("+")[0])
        except (ValueError, IndexError) as e:
            logging.warning(
                f"Nieprawidłowy format zapisanej geometrii do odczytu wymiarów: {saved_geometry_str}. Używam domyślnych 1024x768. Błąd: {e}"
            )

    self.root.minsize(800, 600)

    if saved_maximized:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.wm_attributes("-zoomed", True)
            except tk.TclError:
                logging.warning(
                    "Nie można ustawić stanu zmaksymalizowanego. Okno zostanie wyśrodkowane."
                )
                self._center_window(root, initial_center_width, initial_center_height)
    else:
        self._center_window(root, initial_center_width, initial_center_height)

    self.root.withdraw()
    self.root.after_idle(self._capture_initial_root_size)
    self._last_root_width = self.root.winfo_width()
    self._last_root_height = self.root.winfo_height()
    self.record_startup_time("init_gui_base")

    self.track_overlay = None
    self.overlay_update_timer = None
    self._current_reply_message_data = None
    self._search_timer_id = None
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Inicjalizacja GameLauncher...")
    self._launch_buttons = {}
    self.items_per_page = 24
    self.current_page = 1
    self._total_pages = 1
    self.current_tile_width = 200
    os.makedirs(GAMES_FOLDER, exist_ok=True)
    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    os.makedirs(INTERNAL_MUSIC_DIR, exist_ok=True)
    os.makedirs(CUSTOM_THEMES_DIR, exist_ok=True)

    style = ttk.Style(self.root)
    style.theme_use("clam")
    style.configure("TFrame", background="#1e1e1e")
    style.configure("TLabel", background="#1e1e1e", foreground="white")
    style.configure("TButton", background="#2e2e2e", foreground="white", padding=6)
    style.map("TButton", background=[("active", "#3e3e3e")])
    style.configure("Game.TFrame", background="#1e1e1e", borderwidth=1, relief="solid")
    style.configure(
        "Game.TButton",
        background="#1e1e1e",
        foreground="white",
        borderwidth=0,
        highlightthickness=0,
    )
    style.map(
        "Game.TButton",
        background=[("active", "#1e1e1e")],
        borderwidth=[("active", 0)],
        relief=[("active", "flat")],
    )
    style.configure(
        "TEntry",
        fieldbackground="#2e2e2e",
        background="#2e2e2e",
        foreground="white",
        insertbackground="white",
    )
    style.configure(
        "TScrollbar",
        background="#2e2e2e",
        troughcolor="#1e1e1e",
        arrowcolor="white",
    )
    style.configure("Green.TButton", background="green", foreground="white")
    style.configure("Red.TButton", background="red", foreground="white")
    style.configure("Tile.TButton", padding=(3, 1), font=("Segoe UI", 7))
    style.map(
        "Tile.TButton",
        background=[("active", "#4e4e4e"), ("!disabled", "#2e2e2e")],
        foreground=[("active", "white"), ("!disabled", "white")],
    )
    style.configure(
        "Link.TButton",
        foreground="lightblue",
        padding=0,
        relief="flat",
        borderwidth=0,
    )
    style.map("Link.TButton", underline=[("active", 1)])
    style.configure(
        "Treeview",
        background="#2e2e2e",
        foreground="white",
        fieldbackground="#2e2e2e",
        rowheight=25,
    )
    style.map("Treeview", background=[("selected", "#0078d7")])
    style.configure(
        "Treeview.Heading",
        background="#2e2e2e",
        foreground="white",
        font=("Segoe UI", 10, "bold"),
    )
    style.map("Treeview.Heading", background=[("active", "#3e3e3e")])
    style.configure("Toolbutton", padding=1)

    self.config = config_load_config()
    self.settings = self.config.setdefault("settings", {})
    self.games = self.config.setdefault("games", {})
    self.groups = self.config.setdefault("groups", {})
    self.user = self.config.setdefault("user", {})
    self.roadmap = self.config.setdefault("roadmap", [])
    self.archive = self.config.setdefault("archive", [])
    self.mods_data = self.config.setdefault("mods_data", {})
    self.reminders = self.config.setdefault("reminders", [])

    self.user.setdefault("achievements", {})
    self.user.setdefault("theme_change_count", 0)
    self.local_settings.setdefault("last_run_date", "")
    self.local_settings.setdefault("consecutive_days", 0)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    last_run_str = self.local_settings.get("last_run_date", "")
    consecutive_days = self.local_settings.get("consecutive_days", 0)

    if last_run_str != today_str:
        try:
            last_run_date = datetime.datetime.strptime(last_run_str, "%Y-%m-%d").date()
            yesterday_date = datetime.date.today() - datetime.timedelta(days=1)
            if last_run_date == yesterday_date:
                consecutive_days += 1
            else:
                consecutive_days = 1
        except ValueError:
            consecutive_days = 1
        self.local_settings["last_run_date"] = today_str
        self.local_settings["consecutive_days"] = consecutive_days
        config_save_local_settings(self.local_settings)

    self.achievement_definitions = []
    self._load_achievement_definitions()
    self.record_startup_time("init_config_loaded")

    initial_view = self.local_settings.get("library_view_mode", "tiles")
    self.library_view_mode = tk.StringVar(value=initial_view)

    self.DISCORD_CLIENT_ID = "1300136792636522517"
    self.rpc = None
    self.extended_mod_manager = None
    self.rpc_loop = None
    self.rpc_thread = None
    self.discord_status_text = self.local_settings.get(
        "discord_status_text", "Korzysta z Game Launcher"
    )
    self.discord_rpc_enabled_var = tk.BooleanVar(
        value=self.local_settings.get("discord_rpc_enabled", False)
    )
    self.discord_status_text_var = tk.StringVar(value=self.discord_status_text)
    self._is_connecting_rpc = False

    self._flask_app = None
    self._flask_thread = None
    self._server_running = False
    self.remote_server_port = self.local_settings.get("remote_control_port", 5000)

    self.global_hotkeys_listener = None
    self.active_hotkeys = {}
    self.key_combination_listener = None
    self.current_new_hotkey_action = None
    self.current_new_hotkey_stringvar = None

    self.progress_queue = queue.Queue()
    self.processes = {}
    self.archive = self.config.get("archive", [])
    self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    self.root.bind("<Unmap>", self.on_minimize)

    self.translator = DummyTranslator()
    logging.info("Używam DummyTranslator - tłumaczenia tymczasowo wyłączone.")

    self.STATS_PERIOD_OPTIONS_TRANSLATED = {
        "Last 7 Days": "Ostatnie 7 dni",
        "Last 30 Days": "Ostatnie 30 dni",
        "This Month": "Ten miesiąc",
        "This Year": "Ten rok",
        "All Time": "Cały czas",
        "Custom Range...": "Zakres niestandardowy...",
    }
    self.STATS_VIEW_OPTIONS_TRANSLATED = {
        "Playtime per Day": "Czas gry dziennie",
        "Games Played per Day": "Gry uruchamiane dziennie",
        "Playtime per Game": "Czas gry (wszystkie gry)",
        "Playtime per Game (Selected)": "Czas gry (wybrana gra)",
        "Playtime by Genre (Pie)": "Czas gry wg Gatunku (Kołowy)",
        "Most Launched Games": "Najczęściej Uruchamiane Gry",
        "Average Session Time": "Średni Czas Sesji (per Gra)",
        "Launcher Usage per Day": "Czas w launcherze dziennie",
    }
    self.TRANSLATED_TO_STATS_PERIOD = {
        v: k for k, v in self.STATS_PERIOD_OPTIONS_TRANSLATED.items()
    }
    self.TRANSLATED_TO_STATS_VIEW = {
        v: k for k, v in self.STATS_VIEW_OPTIONS_TRANSLATED.items()
    }

    self.ACHIEVEMENT_RULE_TYPES_TRANSLATED = {
        "games_launched_count": "Liczba uruchomionych gier",
        "library_size": "Rozmiar biblioteki",
        "total_playtime_hours": "Łączny czas gry (godziny)",
        "games_completed_100": "Gry ukończone w 100%",
        "playtime_single_game_hours": "Czas gry w jednej grze (godz.)",
        "genre_played_count": "Liczba gier z gatunku",
        "tag_played_count": "Liczba gier z tagiem",
        "group_played_count": "Liczba gier w grupie",
        "genre_completed_100": "Gry 100% z gatunku",
        "tag_completed_100": "Gry 100% z tagiem",
        "group_completed_100": "Gry 100% w grupie",
        "roadmap_completed_count": "Ukończone gry z Roadmapy",
        "games_rated_count": "Liczba ocenionych gier",
        "groups_created": "Liczba stworzonych grup",
        "games_with_tags": "Liczba gier z tagami",
        "mods_installed": "Liczba zainstalowanych modów",
        "roadmap_items_added": "Liczba gier dodanych do Roadmapy",
        "themes_changed": "Liczba zmian motywu",
        "game_launched_at_night": "Gra uruchomiona w nocy (2-4)",
        "consecutive_days_used": "Dni używania z rzędu",
    }
    self.record_startup_time("init_translations_and_constants")

    theme_name_from_settings = self.settings.get("theme", "Dark")
    theme_def_to_apply = self.get_all_available_themes().get(
        theme_name_from_settings, THEMES["Dark"]
    )
    self.apply_theme(theme_def_to_apply)
    self.apply_font_settings()
    bg_image_path = self.settings.get("background_image", "")
    if bg_image_path:
        self.apply_background_image(bg_image_path)
    self.record_startup_time("init_theme_applied")

    self.root.columnconfigure(1, weight=1)
    self.root.rowconfigure(0, weight=1)

    self.sidebar = ttk.Frame(self.root, width=200)
    self.sidebar.grid(row=0, column=0, sticky="ns")
    self.sidebar.grid_propagate(False)
    self.create_sidebar()
    self.record_startup_time("init_sidebar_created")

    self.home_frame = ttk.Frame(self.root)
    self.home_frame.grid(row=0, column=1, sticky="nsew")
    self.home_frame.columnconfigure(0, weight=1)
    self.home_frame.rowconfigure(1, weight=1)
    self.record_startup_time("init_homepage_created")

    self.main_frame = ttk.Frame(self.root)
    self.main_frame.grid(row=0, column=1, sticky="nsew")
    self.main_frame.grid_remove()
    self.main_frame.columnconfigure(0, weight=1)
    self.main_frame.rowconfigure(1, weight=1)
    self.header = ttk.Frame(self.main_frame)
    self.header.grid(row=0, column=0, sticky="ew")
    self.content = ttk.Frame(self.main_frame)
    self.content.grid(row=1, column=0, sticky="nsew")
    self.content.columnconfigure(0, weight=1)
    self.content.rowconfigure(0, weight=1)
    self.content.rowconfigure(1, weight=0)
    self.record_startup_time("init_library_created")

    self.mod_manager_frame = ttk.Frame(self.root)
    self.mod_manager_frame.grid(row=0, column=1, sticky="nsew")
    self.mod_manager_frame.grid_remove()
    self.mod_manager_frame.columnconfigure(0, weight=1)
    self.mod_manager_frame.rowconfigure(1, weight=1)

    self.news_frame = ttk.Frame(self.root)
    self.news_frame.grid(row=0, column=1, sticky="nsew")
    self.news_frame.grid_remove()
    self.news_frame.columnconfigure(0, weight=1)
    self.news_frame.rowconfigure(0, weight=1)
    self.record_startup_time("init_news_created")

    self.reminders_frame = ttk.Frame(self.root)
    self.reminders_frame.grid(row=0, column=1, sticky="nsew")
    self.reminders_frame.grid_remove()
    self.reminders_frame.columnconfigure(0, weight=1)
    self.reminders_frame.rowconfigure(1, weight=1)
    self.record_startup_time("init_reminders_created")

    self.settings_page_frame = ttk.Frame(self.root, style="TFrame")
    self.settings_page_frame.grid(row=0, column=1, sticky="nsew")
    self.settings_page_frame.grid_remove()
    self.settings_page_frame.columnconfigure(0, weight=1)
    self.settings_page_frame.rowconfigure(1, weight=1)
    self.record_startup_time("init_settings_created")

    self.achievements_frame = ttk.Frame(self.root, style="TFrame")
    self.achievements_frame.grid(row=0, column=1, sticky="nsew")
    self.achievements_frame.grid_remove()

    self.music_page_frame = ttk.Frame(self.root, style="TFrame")
    self.music_page_frame.grid(row=0, column=1, sticky="nsew")
    self.music_page_frame.grid_remove()
    self.music_player_page_instance = None

    self.chat_page_frame = ttk.Frame(self.root, style="TFrame")
    self.chat_page_frame.grid(row=0, column=1, sticky="nsew")
    self.chat_page_frame.grid_remove()

    self.server_selection_page_frame = ttk.Frame(self.root, style="TFrame")
    self.server_selection_page_frame.grid(row=0, column=1, sticky="nsew")
    self.server_selection_page_frame.grid_remove()

    self.stats_page_frame = ttk.Frame(self.root, style="TFrame")
    self.stats_page_frame.grid(row=0, column=1, sticky="nsew")
    self.stats_page_frame.grid_remove()
    self.root.after(
        500,
        lambda: (self.create_statistics_page(), self.stats_page_frame.grid_remove()),
    )

    if not self.user.get("username"):
        self.prompt_initial_setup_choice()
        if not self.user.get("username"):
            self.root.quit()
            return

    self.root.deiconify()
    self.root.lift()
    self.root.focus_force()
    self.root.update_idletasks()
    self.record_startup_time("init_first_ui_display")

    self.show_home()

    self.root.after(150, self.refresh_ui)

    if self.user.get("username"):
        self.root.after(300, self._post_init_heavy_jobs)

    self.tracking_games = {}
    self.game_start_times = {}
    self.processes = {}
    self.vr_filter_var = tk.StringVar(value="Wszystkie")

    self.record_startup_time("init_end_of_constructor")


def _post_init_heavy_jobs(self):
    """Uruchamia zadania, które nie są krytyczne dla pierwszego wyświetlenia UI, z opóźnieniem."""
    logging.info("Uruchamianie zadań po inicjalizacji interfejsu (delayed heavy jobs)...")
    self.record_startup_time("post_init_heavy_jobs_start")

    threading.Thread(target=self.controller_listener, daemon=True).start()
    self.record_startup_time("post_init_controller_listener")

    if self.local_settings.get("discord_rpc_enabled", False):
        self.root.after(100, self._start_discord_rpc)
        self.record_startup_time("post_init_discord_rpc")

    if self.local_settings.get("remote_control_enabled", False):
        self.root.after(200, self._start_flask_server)
        self.record_startup_time("post_init_flask_server")

    self.root.after(500, self._register_music_hotkeys)
    self.record_startup_time("post_init_music_hotkeys")

    threading.Thread(target=self.perform_update_check, daemon=True).start()
    self.record_startup_time("post_init_update_check")

    threading.Thread(target=self.monitor_game_sessions, daemon=True).start()
    self.record_startup_time("post_init_game_sessions_monitor")

    threading.Thread(target=self.monitor_reminders, daemon=True).start()
    self.record_startup_time("post_init_reminders_monitor")

    threading.Thread(target=self._monitor_discord_connection, daemon=True).start()
    self.record_startup_time("post_init_discord_monitor")

    if self.settings.get("autoscan_on_startup", False):
        self.root.after(3000, self.start_scan_screenshots_thread)
        self.record_startup_time("post_init_screenshot_scan")

    threading.Thread(target=_warm_up_optional_modules, daemon=True).start()
    self.root.after(1200, self.preload_library_view)
    self.root.after(2000, self.preload_roadmap_view)
    self.root.after(3000, self.preload_music_page)

    self.root.after(1000, self._update_current_session_time_display)
    self.root.after(500, self._initialize_track_overlay_from_settings)
    self.record_startup_time("post_init_end")


def _warm_up_optional_modules():
    module_paths = [
        "launcher.news_runtime",
        "launcher.stats_runtime",
        "launcher.cloud_github_runtime",
        "launcher.chat_render",
        "launcher.music_navigation",
        "ui.music_player",
    ]
    for module_path in module_paths:
        try:
            importlib.import_module(module_path)
        except Exception as error:
            logging.debug(f"Warmup modułu '{module_path}' nieudany: {error}")


__all__ = ["initialize", "_post_init_heavy_jobs"]
