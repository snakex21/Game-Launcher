import logging
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from launcher.utils import save_config


def show_settings(self):
    self.settings_page_frame.grid()
    self.settings_page_frame.tkraise()
    self.current_frame = self.settings_page_frame

    if not self._settings_initialized:
        logging.info("Tworzenie zawartości strony Ustawień po raz pierwszy (lazy init).")
        self._create_settings_page_content()
        self._settings_initialized = True

    self.load_scan_folders_list()
    self.populate_rss_management_frame()
    self.load_ignored_folders()
    self.load_screenshot_ignored_folders()
    self._load_emulators_list()
    self._load_custom_themes_list()

    if hasattr(self, "settings_username_label") and self.settings_username_label.winfo_exists():
        self.settings_username_label.config(text=f"Nazwa: {self.user.get('username', 'Gracz')}")
    if hasattr(self, "settings_avatar_label") and self.settings_avatar_label.winfo_exists():
        self._load_and_display_settings_avatar()
    if hasattr(self, "avatar_var"):
        self.avatar_var.set(self.user.get("avatar", ""))

    self.current_section = "Zmienia Ustawienia"
    self._update_discord_status(status_type="browsing", activity_details=self.current_section)


def populate_rss_management_frame(self):
    """Wypełnia ramkę zarządzania RSS w ustawieniach."""
    if not hasattr(self, "rss_management_frame") or not self.rss_management_frame.winfo_exists():
        return

    for widget in self.rss_management_frame.winfo_children():
        widget.destroy()

    self.rss_vars = []
    for feed in self.settings.get("rss_feeds", []):
        var = tk.BooleanVar(value=feed.get("active", True))
        self.rss_vars.append(var)

        frame = ttk.Frame(self.rss_management_frame)
        frame.pack(fill="x", pady=1, padx=5)
        cb = ttk.Checkbutton(
            frame,
            text=feed.get("name", feed["url"]),
            variable=var,
            command=self.update_rss_feeds,
        )
        cb.pack(side="left", expand=True, fill="x")
        del_btn = ttk.Button(
            frame,
            text="Usuń",
            command=lambda f=feed: self.remove_specific_rss_feed(f),
        )
        del_btn.pack(side="right")


def add_rss_feed_from_settings(self):
    """Dodaje nowy kanał RSS z poziomu strony ustawień."""
    new_feed_url = simpledialog.askstring("Dodaj RSS Feed", "Podaj URL RSS Feed:")
    if new_feed_url:
        new_feed_name = simpledialog.askstring(
            "Nazwa RSS Feed", "Podaj nazwę RSS Feed (opcjonalnie):"
        )
        if not new_feed_name:
            new_feed_name = new_feed_url

        rss_list = self.settings.setdefault("rss_feeds", [])
        if any(feed["url"] == new_feed_url for feed in rss_list):
            messagebox.showwarning("Błąd", "Ten RSS Feed już istnieje.")
            return

        rss_list.append({"url": new_feed_url, "active": True, "name": new_feed_name})
        save_config(self.config)
        messagebox.showinfo("Sukces", "RSS Feed został dodany.")
        self.populate_rss_management_frame()

        if self.current_frame == self.news_frame:
            self.load_news_threaded()


__all__ = ["show_settings", "populate_rss_management_frame", "add_rss_feed_from_settings"]
