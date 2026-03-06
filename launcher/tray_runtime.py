import threading

import pystray
from PIL import Image


def show_statistics_from_tray(self):
    """Pokazuje okno launchera i przechodzi do strony Statystyk."""
    self.show_window()
    self.root.after_idle(self.show_statistics_page)


def show_window(self):
    """Przywraca okno z zasobnika i uaktywnia je."""
    if hasattr(self, "tray_icon"):
        self.tray_icon.stop()
    self.root.deiconify()
    self.root.lift()
    self.root.focus_force()
    self.root.update_idletasks()


def on_minimize(self, event):
    if self.root.state() == "iconic":
        self.root.withdraw()
        self.create_system_tray_icon()


def create_system_tray_icon(self):
    try:
        image = Image.open("icon.png")
    except FileNotFoundError:
        image = self.create_default_icon()

    music_submenu_items = [
        pystray.MenuItem("Odtwórz / Pauza", self._music_control_play_pause),
        pystray.MenuItem("Poprzedni", self._music_control_prev_track),
        pystray.MenuItem("Następny", self._music_control_next_track),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Pokaż Odtwarzacz", self.show_music_page_from_tray),
    ]
    music_submenu = pystray.Menu(*music_submenu_items)

    menu = pystray.Menu(
        pystray.MenuItem(self.translator.gettext("Strona Główna"), self.show_home_from_tray),
        pystray.MenuItem(self.translator.gettext("Biblioteka"), self.show_library_from_tray),
        pystray.MenuItem("Muzyka", music_submenu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(self.translator.gettext("Roadmapa"), self.show_roadmap_from_tray),
        pystray.MenuItem(
            self.translator.gettext("Menedżer Modów"), self.show_mods_from_tray
        ),
        pystray.MenuItem(
            self.translator.gettext("Osiągnięcia"), self.show_achievements_from_tray
        ),
        pystray.MenuItem(self.translator.gettext("Newsy"), self.show_news_from_tray),
        pystray.MenuItem("Statystyki", self.show_statistics_from_tray),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(self.translator.gettext("Ustawienia"), self.show_settings_from_tray),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(self.translator.gettext("Wyjdź z Programu"), self.exit_program),
    )

    self.tray_icon = pystray.Icon("GameLauncher", image, "Game Launcher", menu)
    threading.Thread(target=self.tray_icon.run, daemon=True).start()


__all__ = [
    "show_statistics_from_tray",
    "show_window",
    "on_minimize",
    "create_system_tray_icon",
]
