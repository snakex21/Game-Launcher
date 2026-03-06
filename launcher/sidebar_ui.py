import tkinter as tk
from tkinter import ttk


def create_sidebar(self):
    for widget in self.sidebar.winfo_children():
        widget.destroy()

    ttk.Label(
        self.sidebar,
        text=self.translator.gettext("Game Launcher"),
        font=("Helvetica", 16, "bold"),
    ).pack(pady=20)

    self.btn_home = ttk.Button(
        self.sidebar, text=self.translator.gettext("Home"), command=self.show_home
    )
    self.btn_home.pack(fill="x", padx=20, pady=5)

    self.btn_library = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Library"),
        command=self.show_library,
    )
    self.btn_library.pack(fill="x", padx=20, pady=5)

    self.btn_roadmap = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Roadmap"),
        command=self.show_roadmap,
    )
    self.btn_roadmap.pack(fill="x", padx=20, pady=5)

    self.btn_mods = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Mod Manager"),
        command=self.show_mod_manager,
    )
    self.btn_mods.pack(fill="x", padx=20, pady=5)

    self.btn_achievements = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Osiągnięcia"),
        command=self.show_achievements_page,
    )
    self.btn_achievements.pack(fill="x", padx=20, pady=5)

    self.btn_news = ttk.Button(
        self.sidebar, text=self.translator.gettext("News"), command=self.show_news
    )
    self.btn_news.pack(fill="x", padx=20, pady=5)

    self.btn_stats = ttk.Button(
        self.sidebar, text="Statystyki", command=self.show_statistics_page
    )
    self.btn_stats.pack(fill="x", padx=20, pady=5)

    self.btn_music = ttk.Button(self.sidebar, text="Muzyka", command=self.show_music_page)
    self.btn_music.pack(fill="x", padx=20, pady=5)

    self.btn_chat = ttk.Button(self.sidebar, text="Czat", command=self.show_chat_page)
    self.btn_chat.pack(fill="x", padx=20, pady=5)

    self.btn_chat_servers = ttk.Button(
        self.sidebar, text="Serwery Czatu", command=self.show_server_selection_page
    )
    self.btn_chat_servers.pack(fill="x", padx=20, pady=5)

    self.btn_settings = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Settings"),
        command=self.show_settings,
    )
    self.btn_settings.pack(fill="x", padx=20, pady=5)

    self.btn_exit = ttk.Button(
        self.sidebar, text=self.translator.gettext("Exit"), command=self.on_closing
    )
    self.btn_exit.pack(fill="x", padx=20, pady=5)

    self.fullscreen_var = tk.BooleanVar(
        value=(self.fullscreen_var.get() if hasattr(self, "fullscreen_var") else False)
    )
    fullscreen_btn = ttk.Checkbutton(
        self.sidebar,
        text=self.translator.gettext("Fullscreen Mode"),
        variable=self.fullscreen_var,
        command=self.toggle_fullscreen,
    )
    fullscreen_btn.pack(pady=5)

    minimize_btn = ttk.Button(
        self.sidebar,
        text=self.translator.gettext("Minimize to Tray"),
        command=self.minimize_to_tray,
    )
    minimize_btn.pack(pady=5)


__all__ = [
    "create_sidebar",
]
