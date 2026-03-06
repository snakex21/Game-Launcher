import logging
import threading
import time

from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

from launcher.utils import save_config


def create_news_page(self):
    from tkhtmlview import HTMLLabel

    for widget in self.news_frame.winfo_children():
        widget.destroy()

    header = ttk.Frame(self.news_frame)
    header.grid(row=0, column=0, sticky="ew")
    ttk.Label(header, text="Newsy Gier", font=("Helvetica", 20, "bold")).pack(pady=10)

    self.news_content = HTMLLabel(
        self.news_frame,
        html="<h1 style='font-size:24px; text-align:center; color:white;'>Ładowanie newsów...</h1>",
        background=self.settings.get("background", "#1e1e1e"),
        foreground=self.settings.get("foreground", "white"),
    )
    self.news_content.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    self.news_frame.columnconfigure(0, weight=1)
    self.news_frame.rowconfigure(1, weight=1)


def load_news(self, content_widget):
    import feedparser
    import requests

    active_feeds = [
        feed for feed in self.settings.get("rss_feeds", []) if feed.get("active", False)
    ]
    rss_feeds = [feed["url"] for feed in active_feeds]
    post_limit = self.settings.get("news_post_limit", 10)

    logging.info(f"Rozpoczynanie ładowania newsów z {len(rss_feeds)} RSS Feeds.")
    print(f"Loading news from {len(rss_feeds)} feeds.")

    all_entries = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for feed_url in rss_feeds:
        logging.info(f"Pobieranie newsów z: {feed_url}")
        try:
            response = requests.get(feed_url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.bozo:
                logging.error(f"Błąd podczas parsowania RSS feed: {feed_url}")
                continue
            for entry in feed.entries:
                entry_date = None
                if "published_parsed" in entry and entry.published_parsed:
                    entry_date = time.mktime(entry.published_parsed)
                elif "updated_parsed" in entry and entry.updated_parsed:
                    entry_date = time.mktime(entry.updated_parsed)
                else:
                    entry_date = time.time()
                entry["entry_date"] = entry_date
                all_entries.append(entry)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Błąd podczas pobierania RSS feed: {feed_url} - {req_err}")
            continue

    all_entries.sort(key=lambda x: x.get("entry_date", time.time()), reverse=True)
    selected_entries = all_entries[:post_limit]

    news_html = """
        <h1 style='font-size:24px; text-align:center; color:white;'>Newsy Gier</h1>
        """

    for entry in selected_entries:
        title = entry.get("title", "Brak tytułu")
        summary = entry.get("summary", "Brak opisu")
        link = entry.get("link", "#")
        date_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(entry.get("entry_date", time.time()))
        )

        news_html += f"""
            <div style='margin-bottom: 20px;'>
                <h2 style='font-size:18px; color:#ffcc00;'>{title}</h2>
                <div style='font-size:12px; color:#888888;'>{date_str}</div>
                <p style='font-size:14px; color:white;'>{summary}</p>
                <a href="{link}" style='color:#1e90ff; text-decoration:none;'>Czytaj więcej</a>
                <hr style='border:0; height:1px; background:#333; margin:10px 0;'>
            </div>
            """

    logging.info("Newsy zostały poprawnie załadowane i przetworzone.")
    self.root.after(0, lambda: content_widget.set_html(news_html))


def remove_specific_rss_feed(self, feed_to_remove):
    """Usuwa konkretny kanał RSS i odświeża UI ustawień."""
    confirm = messagebox.askyesno(
        "Usuń RSS Feed",
        f"Czy na pewno chcesz usunąć RSS Feed:\n{feed_to_remove.get('name', feed_to_remove['url'])}?",
    )
    if confirm:
        rss_list = self.settings.get("rss_feeds", [])
        original_length = len(rss_list)
        self.settings["rss_feeds"] = [
            feed for feed in rss_list if feed["url"] != feed_to_remove["url"]
        ]

        if len(self.settings["rss_feeds"]) < original_length:
            save_config(self.config)
            messagebox.showinfo("Sukces", "RSS Feed został usunięty.")
            self.populate_rss_management_frame()
            if self.current_frame == self.news_frame:
                self.load_news_threaded()
        else:
            messagebox.showerror("Błąd", "Nie udało się znaleźć i usunąć kanału RSS.")


def update_rss_feeds(self):
    """Aktualizuje status aktywności kanałów RSS."""
    rss_list = self.settings.get("rss_feeds", [])
    if len(self.rss_vars) == len(rss_list):
        for idx, feed in enumerate(rss_list):
            feed["active"] = self.rss_vars[idx].get()
        save_config(self.config)
        logging.info("Zaktualizowano statusy aktywności RSS.")
        if self.current_frame == self.news_frame:
            self.load_news_threaded()
    else:
        logging.error("Niezgodność liczby zmiennych RSS i listy kanałów!")
        messagebox.showerror(
            "Błąd wewnętrzny",
            "Niezgodność danych RSS. Spróbuj ponownie otworzyć ustawienia.",
        )


def show_news(self):
    self.news_frame.grid()
    self.news_frame.tkraise()
    self.current_frame = self.news_frame

    if not self._news_initialized:
        logging.info("Tworzenie zawartości strony Newsów po raz pierwszy (lazy init).")
        self.create_news_page()
        self._news_initialized = True

    if not getattr(self, "_news_loaded", False):
        logging.info("Uruchamianie ładowania newsów w tle.")
        if hasattr(self, "news_content") and self.news_content.winfo_exists():
            threading.Thread(target=self.load_news, args=(self.news_content,), daemon=True).start()
            self._news_loaded = True
        else:
            logging.error("Nie można załadować newsów - widget news_content nie istnieje.")
    else:
        logging.debug("Newsy były już ładowane.")

    self.current_section = "Czyta Newsy"
    self._update_discord_status(status_type="browsing", activity_details=self.current_section)


def load_news_threaded(self):
    if hasattr(self, "news_content") and self.news_content:
        threading.Thread(target=self.load_news, args=(self.news_content,), daemon=True).start()
    else:
        logging.error("Nie znaleziono widgetu news_content.")


def add_rss_feed(self):
    new_feed_url = simpledialog.askstring("Dodaj RSS Feed", "Podaj URL RSS Feed:")
    if new_feed_url:
        new_feed_name = simpledialog.askstring(
            "Nazwa RSS Feed", "Podaj nazwę RSS Feed (opcjonalnie):"
        )
        if not new_feed_name:
            new_feed_name = new_feed_url
        if any(feed["url"] == new_feed_url for feed in self.settings["rss_feeds"]):
            messagebox.showwarning("Błąd", "Ten RSS Feed już istnieje.")
            return
        self.settings["rss_feeds"].append(
            {"url": new_feed_url, "active": True, "name": new_feed_name}
        )
        save_config(self.config)
        messagebox.showinfo("Sukces", "RSS Feed został dodany.")
        self.show_settings()

        if self.current_frame == self.news_frame:
            self.load_news_threaded()


def remove_rss_feed(self):
    selected = self.rss_listbox.curselection()
    if selected:
        index = selected[0]
        feed = self.rss_listbox.get(index)
        confirm = messagebox.askyesno(
            "Usuń RSS Feed", f"Czy na pewno chcesz usunąć RSS Feed:\n{feed}?"
        )
        if confirm:
            self.settings["rss_feeds"].remove(feed)
            self.rss_listbox.delete(index)
            save_config(self.config)
            messagebox.showinfo("Sukces", "RSS Feed został usunięty.")
    else:
        messagebox.showwarning("Błąd", "Nie wybrano żadnego RSS Feed.")


def update_post_limit(self):
    try:
        limit = self.post_limit_var.get()
        if limit < 1:
            raise ValueError
        self.settings["news_post_limit"] = limit
        save_config(self.config)
        self.load_news_threaded()
    except Exception:
        messagebox.showwarning("Błąd", "Proszę podać prawidłową liczbę.")


__all__ = [
    "create_news_page",
    "load_news",
    "remove_specific_rss_feed",
    "update_rss_feeds",
    "show_news",
    "load_news_threaded",
    "add_rss_feed",
    "remove_rss_feed",
    "update_post_limit",
]
