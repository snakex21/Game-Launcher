"""Core implementation of the Game Launcher application.

This module contains the main :class:`GameLauncher` class responsible for
combining the various feature managers (games, music, stats, calendar, mods,
profiles, achievements, etc.) and exposing a cohesive Tkinter based UI.

The goal of this refactor is to move the heavy logic from the legacy
``game_launcher.py`` script into a clean, testable class that can be reused by
``main.py`` and future entry points.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from config import Settings
from config.constants import (
    APP_NAME,
    APP_VERSION,
    AUTO_SAVE_INTERVAL,
    COLOR_BG_DARK,
    COLOR_FG_LIGHT,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from features.achievements import AchievementsManager
from features.calendar_manager import CalendarManager
from features.game_manager import GameManager
from features.mod_manager import ModManager
from features.music_player import MusicPlayer
from features.profile_manager import ProfileManager
from features.stats_manager import StatsManager
from ui.overlay import TrackOverlayWindow

logger = logging.getLogger(__name__)


class GameLauncher:
    """Main application class coordinating every launcher subsystem."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")

        self.settings = Settings()

        # Internal state placeholders populated during initialisation
        self.games_data: List[Dict[str, Any]] = []
        self.filtered_games: List[Dict[str, Any]] = []
        self.current_game_id: Optional[str] = None
        self.profiles_data: Dict[str, List[Dict[str, Any]]] = {}
        self.calendar_events: List[Dict[str, Any]] = []
        self.achievements_data: Dict[str, List[Dict[str, Any]]] = {}

        # GUI specific attributes
        self.main_notebook: Optional[ttk.Notebook] = None
        self.games_tree: Optional[ttk.Treeview] = None
        self.calendar_tree: Optional[ttk.Treeview] = None
        self.music_playlist_box: Optional[tk.Listbox] = None
        self.stats_text: Optional[tk.Text] = None
        self.status_var = tk.StringVar(value="Gotowy")
        self.music_current_track_var = tk.StringVar(value="Brak odtwarzanego utworu")
        self.overlay_enabled_var = tk.BooleanVar(value=self.settings.get("overlay.enabled", True))

        # Tkinter after() jobs
        self.auto_save_job: Optional[str] = None
        self.music_poll_job: Optional[str] = None

        # Overlay window reference
        self.track_overlay_window: Optional[TrackOverlayWindow] = None

        logger.debug("Rozpoczynam inicjalizację GameLauncher")

        self._init_managers()
        self._load_data()
        self._create_ui()
        self._start_components()
        self._configure_window()

        logger.info("GameLauncher zainicjalizowany")

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _init_managers(self) -> None:
        """Create instances of all feature managers."""

        logger.debug("Inicjalizacja menedżerów funkcji")

        self.game_manager = GameManager(self)
        self.profile_manager = ProfileManager(self)
        self.music_player = MusicPlayer(self)
        self.stats_manager = StatsManager(self)
        self.calendar_manager = CalendarManager(self)
        self.mod_manager = ModManager(self)
        self.achievements_manager = AchievementsManager(self)

    def _load_data(self) -> None:
        """Synchronise internal state with data stored in managers."""

        logger.debug("Ładowanie danych z menedżerów")

        self.games_data = self.game_manager.games
        self.filtered_games = list(self.games_data)
        self.profiles_data = self.profile_manager.profiles
        self.calendar_events = self.calendar_manager.events
        self.achievements_data = self.achievements_manager.achievements

    def _create_ui(self) -> None:
        """Build the Tkinter user interface."""

        logger.debug("Tworzenie interfejsu użytkownika")

        self.root.configure(bg=COLOR_BG_DARK)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            logger.warning("Motyw 'clam' niedostępny – używam domyślnego")
        style.configure("TFrame", background=COLOR_BG_DARK)
        style.configure("TLabel", background=COLOR_BG_DARK, foreground=COLOR_FG_LIGHT)

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        self.main_notebook = ttk.Notebook(container)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        self._build_games_tab()
        self._build_music_tab()
        self._build_stats_tab()
        self._build_calendar_tab()
        self._build_settings_tab()

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._update_status("Aplikacja gotowa")

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------
    def _build_games_tab(self) -> None:
        games_frame = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(games_frame, text="Biblioteka gier")

        toolbar = ttk.Frame(games_frame)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(toolbar, text="Dodaj grę", command=self._add_game_dialog).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Usuń", command=self._remove_selected_game).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(toolbar, text="Uruchom", command=self._launch_selected_game).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(toolbar, text="Szukaj:").pack(side=tk.LEFT, padx=(12, 4))
        self.games_search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.games_search_var, width=30)
        search_entry.pack(side=tk.LEFT)
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_games_tree())

        columns = ("name", "path", "last_played", "playtime", "launches")
        self.games_tree = ttk.Treeview(
            games_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15,
        )
        self.games_tree.heading("name", text="Nazwa")
        self.games_tree.heading("path", text="Ścieżka")
        self.games_tree.heading("last_played", text="Ostatnio grano")
        self.games_tree.heading("playtime", text="Czas gry (h)")
        self.games_tree.heading("launches", text="Uruchomienia")

        self.games_tree.column("name", width=220, stretch=True)
        self.games_tree.column("path", width=320, stretch=True)
        self.games_tree.column("last_played", width=140, stretch=False)
        self.games_tree.column("playtime", width=120, stretch=False)
        self.games_tree.column("launches", width=120, stretch=False)

        scrollbar = ttk.Scrollbar(games_frame, orient=tk.VERTICAL, command=self.games_tree.yview)
        self.games_tree.configure(yscrollcommand=scrollbar.set)
        self.games_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.games_tree.bind("<Double-1>", lambda _event: self._launch_selected_game())
        self.games_tree.bind("<<TreeviewSelect>>", self._on_game_selected)

        self._refresh_games_tree()

    def _build_music_tab(self) -> None:
        music_frame = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(music_frame, text="Muzyka")

        controls = ttk.Frame(music_frame)
        controls.pack(fill=tk.X)

        ttk.Button(controls, text="Wczytaj katalog", command=self._load_music_folder).pack(side=tk.LEFT)
        ttk.Button(controls, text="Play", command=self.play_music).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Pause", command=self.pause_music).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Stop", command=self.stop_music).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Prev", command=self.previous_track).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Next", command=self.next_track).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(controls, text="Głośność").pack(side=tk.LEFT, padx=(12, 4))
        self.volume_slider = ttk.Scale(
            controls,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            command=self._on_volume_change,
        )
        self.volume_slider.set(self.music_player.volume)
        self.volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        playlist_frame = ttk.Frame(music_frame)
        playlist_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.music_playlist_box = tk.Listbox(playlist_frame, height=14)
        self.music_playlist_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.music_playlist_box.bind("<Double-1>", lambda _event: self._play_selected_track())

        playlist_scroll = ttk.Scrollbar(playlist_frame, orient=tk.VERTICAL, command=self.music_playlist_box.yview)
        playlist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.music_playlist_box.configure(yscrollcommand=playlist_scroll.set)

        track_info = ttk.Label(music_frame, textvariable=self.music_current_track_var, anchor="w")
        track_info.pack(fill=tk.X, pady=(8, 0))

        self._update_music_playlist()

    def _build_stats_tab(self) -> None:
        stats_frame = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(stats_frame, text="Statystyki")

        buttons = ttk.Frame(stats_frame)
        buttons.pack(fill=tk.X)

        ttk.Button(buttons, text="Odśwież statystyki", command=self.update_stats).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Generuj raport", command=self._show_stats_report).pack(side=tk.LEFT, padx=(6, 0))

        self.stats_text = tk.Text(stats_frame, height=20, wrap="word")
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.stats_text.configure(state="disabled", background="#1c1c1c", foreground="#f0f0f0")

        self.update_stats()

    def _build_calendar_tab(self) -> None:
        calendar_frame = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(calendar_frame, text="Kalendarz")

        controls = ttk.Frame(calendar_frame)
        controls.pack(fill=tk.X)

        ttk.Button(controls, text="Dodaj wydarzenie", command=self._add_event_dialog).pack(side=tk.LEFT)
        ttk.Button(controls, text="Usuń", command=self._remove_selected_event).pack(side=tk.LEFT, padx=(6, 0))

        columns = ("title", "date", "game", "type")
        self.calendar_tree = ttk.Treeview(
            calendar_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=14,
        )
        self.calendar_tree.heading("title", text="Tytuł")
        self.calendar_tree.heading("date", text="Data")
        self.calendar_tree.heading("game", text="Gra")
        self.calendar_tree.heading("type", text="Typ")

        self.calendar_tree.column("title", width=220, stretch=True)
        self.calendar_tree.column("date", width=140, stretch=False)
        self.calendar_tree.column("game", width=200, stretch=True)
        self.calendar_tree.column("type", width=120, stretch=False)

        scroll = ttk.Scrollbar(calendar_frame, orient=tk.VERTICAL, command=self.calendar_tree.yview)
        self.calendar_tree.configure(yscrollcommand=scroll.set)
        self.calendar_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_calendar_tree()

    def _build_settings_tab(self) -> None:
        settings_frame = ttk.Frame(self.main_notebook, padding=10)
        self.main_notebook.add(settings_frame, text="Ustawienia")

        general_box = ttk.LabelFrame(settings_frame, text="Ogólne")
        general_box.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(
            general_box,
            text=f"Plik ustawień: {Path(self.settings.settings_file).resolve()}",
        ).pack(anchor="w", pady=2)

        ttk.Button(
            general_box,
            text="Zresetuj ustawienia",
            command=self._reset_settings,
        ).pack(anchor="w", pady=2)

        overlay_box = ttk.LabelFrame(settings_frame, text="Overlay odtwarzacza")
        overlay_box.pack(fill=tk.X)

        overlay_toggle = ttk.Checkbutton(
            overlay_box,
            text="Włącz overlay odtwarzacza",
            variable=self.overlay_enabled_var,
            command=self._toggle_overlay,
        )
        overlay_toggle.pack(anchor="w", pady=2)

    # ------------------------------------------------------------------
    # Component management
    # ------------------------------------------------------------------
    def _start_components(self) -> None:
        logger.debug("Uruchamianie komponentów tła")

        if self.overlay_enabled_var.get():
            overlay_x = self.settings.get("overlay.x")
            overlay_y = self.settings.get("overlay.y")
            self.track_overlay_window = TrackOverlayWindow(
                self.root,
                initial_x=overlay_x,
                initial_y=overlay_y,
                launcher_instance=self,
            )

        if self.settings.get("auto.save_enabled", True):
            interval = int(self.settings.get("auto.save_interval", AUTO_SAVE_INTERVAL) * 1000)
            self.auto_save_job = self.root.after(interval, self._auto_save_callback)

        # Poll music player to detect when tracks end
        self.music_poll_job = self.root.after(1000, self._poll_music_player)

    def _configure_window(self) -> None:
        width = self.settings.get("window.width", WINDOW_DEFAULT_WIDTH)
        height = self.settings.get("window.height", WINDOW_DEFAULT_HEIGHT)

        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.geometry(f"{width}x{height}")

        pos_x = self.settings.get("window.x")
        pos_y = self.settings.get("window.y")
        if pos_x is not None and pos_y is not None:
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        if self.settings.get("window.maximized", False):
            try:
                self.root.state("zoomed")
            except tk.TclError:
                logger.debug("Tryb zmaksymalizowany niedostępny na tej platformie")

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------
    def _update_status(self, message: str) -> None:
        logger.info(message)
        self.status_var.set(message)

    def _format_datetime(self, value: Optional[str]) -> str:
        if not value:
            return "—"
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    def _refresh_games_tree(self) -> None:
        if not self.games_tree:
            return

        search = self.games_search_var.get().strip().lower()
        self.games_tree.delete(*self.games_tree.get_children())

        for game in self.game_manager.games:
            if search and search not in game.get("name", "").lower():
                continue

            playtime_hours = game.get("total_playtime", 0) / 3600
            values = (
                game.get("name", "Nieznana"),
                game.get("exe_path", ""),
                self._format_datetime(game.get("last_played")),
                f"{playtime_hours:.1f}",
                game.get("launch_count", 0),
            )
            self.games_tree.insert("", tk.END, iid=game["id"], values=values)

    def _on_game_selected(self, _event: tk.Event) -> None:
        if not self.games_tree:
            return
        selected = self.games_tree.selection()
        if selected:
            self.current_game_id = selected[0]

    def _launch_selected_game(self) -> None:
        if not self.current_game_id:
            messagebox.showinfo("Uruchamianie", "Wybierz najpierw grę")
            return
        if self.launch_game(self.current_game_id):
            game = self.game_manager.get_game_by_id(self.current_game_id)
            if game:
                self._update_status(f"Uruchomiono grę: {game['name']}")

    def _remove_selected_game(self) -> None:
        if not self.current_game_id:
            messagebox.showinfo("Biblioteka", "Wybierz grę do usunięcia")
            return
        game = self.game_manager.get_game_by_id(self.current_game_id)
        if not game:
            return
        if not messagebox.askyesno("Potwierdzenie", f"Usunąć grę '{game['name']}'?"):
            return
        if self.remove_game(self.current_game_id):
            self._update_status(f"Usunięto grę: {game['name']}")

    def _add_game_dialog(self) -> None:
        exe_path = filedialog.askopenfilename(title="Wybierz plik EXE gry")
        if not exe_path:
            return
        default_name = Path(exe_path).stem
        game_name = simpledialog.askstring("Nowa gra", "Podaj nazwę gry:", initialvalue=default_name, parent=self.root)
        if not game_name:
            return

        game_data = {
            "name": game_name,
            "exe_path": exe_path,
            "working_dir": str(Path(exe_path).parent),
        }
        game_id = self.add_game(game_data)
        if game_id:
            self._update_status(f"Dodano grę: {game_name}")
            self.current_game_id = game_id

    def _load_music_folder(self) -> None:
        folder = filedialog.askdirectory(title="Wybierz katalog z muzyką")
        if not folder:
            return
        loaded = self.music_player.load_folder(folder)
        self._update_music_playlist()
        self._update_status(f"Załadowano {loaded} utworów")

    def _play_selected_track(self) -> None:
        if not self.music_playlist_box:
            return
        selection = self.music_playlist_box.curselection()
        if not selection:
            self.play_music()
        else:
            self.play_music(selection[0])

    def _on_volume_change(self, value: str) -> None:
        try:
            volume = float(value)
        except ValueError:
            return
        self.music_player.set_volume(volume)

    def _update_music_playlist(self) -> None:
        if not self.music_playlist_box:
            return
        self.music_playlist_box.delete(0, tk.END)
        for track in self.music_player.playlist:
            self.music_playlist_box.insert(tk.END, track.name)

    def _refresh_calendar_tree(self) -> None:
        if not self.calendar_tree:
            return
        self.calendar_tree.delete(*self.calendar_tree.get_children())
        for event in self.calendar_manager.events:
            values = (
                event.get("title", "Wydarzenie"),
                event.get("date", ""),
                self._get_game_name(event.get("game_id")),
                event.get("type", ""),
            )
            self.calendar_tree.insert("", tk.END, iid=event["id"], values=values)

    def _add_event_dialog(self) -> None:
        title = simpledialog.askstring("Nowe wydarzenie", "Tytuł:", parent=self.root)
        if not title:
            return
        date = simpledialog.askstring(
            "Nowe wydarzenie",
            "Data (YYYY-MM-DD):",
            initialvalue=datetime.now().date().isoformat(),
            parent=self.root,
        )
        event_data = {
            "title": title,
            "date": date or datetime.now().date().isoformat(),
        }
        event_id = self.calendar_manager.add_event(event_data)
        if event_id:
            self._refresh_calendar_tree()
            self._update_status(f"Dodano wydarzenie: {title}")

    def _remove_selected_event(self) -> None:
        if not self.calendar_tree:
            return
        selection = self.calendar_tree.selection()
        if not selection:
            messagebox.showinfo("Kalendarz", "Wybierz wydarzenie do usunięcia")
            return
        event_id = selection[0]
        if self.calendar_manager.remove_event(event_id):
            self._refresh_calendar_tree()
            self._update_status("Usunięto wydarzenie")

    def _show_stats_report(self) -> None:
        report = self.stats_manager.generate_summary_report()
        messagebox.showinfo("Raport statystyk", report)

    def _reset_settings(self) -> None:
        if not messagebox.askyesno("Reset ustawień", "Przywrócić ustawienia domyślne?"):
            return
        if self.settings.reset():
            self.overlay_enabled_var.set(self.settings.get("overlay.enabled", True))
            self._update_status("Przywrócono ustawienia domyślne")

    def _toggle_overlay(self) -> None:
        enabled = self.overlay_enabled_var.get()
        self.settings.set("overlay.enabled", enabled)
        if enabled and not self.track_overlay_window:
            self.track_overlay_window = TrackOverlayWindow(self.root, launcher_instance=self)
        elif not enabled and self.track_overlay_window:
            self.track_overlay_window.destroy()
            self.track_overlay_window = None

    def _get_game_name(self, game_id: Optional[str]) -> str:
        if not game_id:
            return "—"
        game = self.game_manager.get_game_by_id(game_id)
        return game.get("name", "—") if game else "—"

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------
    def _auto_save_callback(self) -> None:
        self._save_all_data()
        interval = int(self.settings.get("auto.save_interval", AUTO_SAVE_INTERVAL) * 1000)
        self.auto_save_job = self.root.after(interval, self._auto_save_callback)

    def _poll_music_player(self) -> None:
        try:
            self.music_player.check_if_ended()
        finally:
            self.music_poll_job = self.root.after(1000, self._poll_music_player)

    # ------------------------------------------------------------------
    # Shutdown handling
    # ------------------------------------------------------------------
    def _on_closing(self) -> None:
        logger.info("Zamykanie aplikacji")
        self._save_window_state()
        self._save_all_data()
        self._stop_components()
        self.root.destroy()

    def _save_window_state(self) -> None:
        try:
            geometry = self.root.winfo_geometry()
            size, _, position = geometry.partition("+")
            width, _, height = size.partition("x")
            pos_x, _, pos_y = position.partition("+")

            self.settings.set("window.width", int(width), auto_save=False)
            self.settings.set("window.height", int(height), auto_save=False)
            if pos_x and pos_y:
                self.settings.set("window.x", int(pos_x), auto_save=False)
                self.settings.set("window.y", int(pos_y), auto_save=False)
            self.settings.save()
        except Exception as exc:
            logger.error("Nie udało się zapisać stanu okna", exc_info=exc)

    def _save_all_data(self) -> None:
        logger.debug("Zapisywanie danych aplikacji")
        self.game_manager.save_games()
        self.calendar_manager.save_events()
        self.achievements_manager.save_achievements()
        self.mod_manager.save_mods()
        self.settings.save()

    def _stop_components(self) -> None:
        if self.auto_save_job is not None:
            self.root.after_cancel(self.auto_save_job)
            self.auto_save_job = None
        if self.music_poll_job is not None:
            self.root.after_cancel(self.music_poll_job)
            self.music_poll_job = None
        if self.track_overlay_window:
            self.track_overlay_window.destroy()
            self.track_overlay_window = None
        try:
            self.music_player.stop()
        except Exception:
            logger.exception("Błąd zatrzymywania odtwarzacza muzyki")

    # ------------------------------------------------------------------
    # Public API delegating to feature managers
    # ------------------------------------------------------------------
    def add_game(self, game_data: Dict[str, Any]) -> Optional[str]:
        game_id = self.game_manager.add_game(game_data)
        if game_id:
            self._refresh_games_tree()
        return game_id

    def remove_game(self, game_id: str) -> bool:
        result = self.game_manager.remove_game(game_id)
        if result:
            self._refresh_games_tree()
        return result

    def launch_game(self, game_id: str, profile_id: Optional[str] = None) -> bool:
        return self.game_manager.launch_game(game_id, profile_id)

    def play_music(self, index: Optional[int] = None) -> bool:
        success = self.music_player.play(index)
        if success:
            info = self.music_player.current_track_info
            if info:
                artist = info.get("artist", "Nieznany")
                title = info.get("title", "")
                self.music_current_track_var.set(f"{artist} - {title}")
        return success

    def pause_music(self) -> None:
        if self.music_player.is_paused:
            self.music_player.unpause()
        else:
            self.music_player.pause()

    def stop_music(self) -> None:
        self.music_player.stop()
        self.music_current_track_var.set("Brak odtwarzanego utworu")

    def next_track(self) -> bool:
        result = self.music_player.next_track()
        if result:
            self._update_music_playlist()
        return result

    def previous_track(self) -> bool:
        return self.music_player.previous_track()

    def update_stats(self) -> None:
        if not self.stats_text:
            return
        stats = self.stats_manager.generate_summary_report()
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, stats)
        self.stats_text.configure(state="disabled")

    def generate_charts(self) -> None:
        logger.info("Generowanie wykresów statystyk – funkcja w przygotowaniu")

    def update_discord_presence(self, state: str, details: Optional[str] = None) -> None:
        logger.info("Discord RPC -> %s %s", state, details or "")

    def handle_gamepad_input(self, event: Any) -> None:
        logger.debug("Odebrano zdarzenie gamepada: %s", event)

    def __repr__(self) -> str:
        return f"GameLauncher(games={len(self.game_manager.games)}, profiles={len(self.profile_manager.profiles)})"
