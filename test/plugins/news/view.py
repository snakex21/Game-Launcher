# plugins/news/view.py
import customtkinter as ctk
import feedparser
import threading
import webbrowser
from .manage_feeds_window import ManageFeedsWindow

class NewsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.manage_feeds_win_instance = None
        
        # Mapa do przechowywania Nazwa kanału -> URL
        self.feed_name_to_url_map = {}
        # Przechowuje aktualnie wybrany kanał do odświeżania
        self.current_feed_url = "all" 

        self._setup_ui()
        self._update_feed_selector() # Wypełnij menu na starcie
        self.fetch_news()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        # --- NOWOŚĆ: Menu wyboru kanału ---
        self.feed_selector = ctk.CTkOptionMenu(top_frame, values=["Wszystkie kanały"], command=self.on_feed_selected)
        self.feed_selector.pack(side="left", padx=(0, 10))
        
        self.refresh_button = ctk.CTkButton(top_frame, text="Odśwież", width=100, command=self.fetch_news)
        self.refresh_button.pack(side="left")
        
        self.manage_button = ctk.CTkButton(top_frame, text="Zarządzaj...", width=120, command=self.open_manage_feeds_window)
        self.manage_button.pack(side="right", padx=10)
        
        self.add_button = ctk.CTkButton(top_frame, text="Dodaj", width=100, command=self.add_feed)
        self.add_button.pack(side="right", padx=10)

        self.url_entry = ctk.CTkEntry(top_frame, placeholder_text="Wklej adres URL kanału RSS...")
        self.url_entry.pack(side="right", fill="x", expand=True)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Najnowsze wiadomości")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def _update_feed_selector(self):
        """Aktualizuje zawartość menu wyboru kanałów."""
        news_data = self.app_context.data_manager.get_plugin_data("news")
        feeds = news_data.get("feeds", [])
        
        self.feed_name_to_url_map = {feed['name']: feed['url'] for feed in feeds}
        
        # Zawsze dodajemy opcję "Wszystkie kanały" na początku
        channel_names = ["Wszystkie kanały"] + list(self.feed_name_to_url_map.keys())
        self.feed_selector.configure(values=channel_names)

    def on_feed_selected(self, selected_name: str):
        """Wywoływane, gdy użytkownik wybierze kanał z menu."""
        if selected_name == "Wszystkie kanały":
            self.current_feed_url = "all"
        else:
            self.current_feed_url = self.feed_name_to_url_map.get(selected_name)
        
        self.fetch_news() # Odśwież widok z wybranym kanałem

    def _fetch_news_thread(self):
        """Działa w tle i pobiera wiadomości dla wybranego kanału."""
        news_data = self.app_context.data_manager.get_plugin_data("news")
        
        urls_to_fetch = []
        if self.current_feed_url == "all":
            urls_to_fetch = [feed["url"] for feed in news_data.get("feeds", [])]
        elif self.current_feed_url:
            urls_to_fetch = [self.current_feed_url]

        all_entries = []
        for url in urls_to_fetch:
            try:
                feed = feedparser.parse(url)
                all_entries.extend(feed.entries)
            except Exception as e:
                print(f"Błąd podczas pobierania kanału {url}: {e}")

        all_entries.sort(key=lambda x: x.get("published_parsed"), reverse=True)
        if self.app_context.shutdown_event.is_set(): return
        self.after(0, self._update_ui_with_news, all_entries[:50])

    def add_feed(self):
        new_url = self.url_entry.get()
        if not new_url: return

        news_data = self.app_context.data_manager.get_plugin_data("news")
        feeds = news_data.get("feeds", [])
        if any(feed['url'] == new_url for feed in feeds): return

        feed_name = new_url
        try:
            parsed_feed = feedparser.parse(new_url)
            if 'title' in parsed_feed.feed:
                feed_name = parsed_feed.feed.title
        except Exception: pass
        
        feeds.append({"name": feed_name, "url": new_url})
        news_data["feeds"] = feeds
        self.app_context.data_manager.save_plugin_data("news", news_data)
        self.url_entry.delete(0, 'end')
        
        # --- ULEPSZENIE: Automatycznie wybierz nowo dodany kanał ---
        self._update_feed_selector()
        self.feed_selector.set(feed_name)
        self.on_feed_selected(feed_name) # Wywołaj odświeżenie

    # --- Reszta funkcji (bez zmian) ---
    def fetch_news(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        loading_label = ctk.CTkLabel(self.scrollable_frame, text="Ładowanie wiadomości...", font=("Roboto", 16))
        loading_label.pack(pady=20)
        thread = threading.Thread(target=self._fetch_news_thread)
        thread.daemon = True
        thread.start()
        
    def _update_ui_with_news(self, entries):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        if not entries:
            no_news_label = ctk.CTkLabel(self.scrollable_frame, text="Nie znaleziono żadnych wiadomości.", font=("Roboto", 16))
            no_news_label.pack(pady=20)
            return
        for entry in entries:
            title = entry.get("title", "Brak tytułu")
            link = entry.get("link", "#")
            text_color = ("gray10", "#DCE4EE")
            news_item = ctk.CTkButton(self.scrollable_frame, text=title, fg_color="transparent", text_color=text_color, anchor="w", command=lambda l=link: webbrowser.open(l))
            news_item.pack(fill="x", padx=5, pady=2)

    def open_manage_feeds_window(self):
        if self.manage_feeds_win_instance is None or not self.manage_feeds_win_instance.winfo_exists():
            self.manage_feeds_win_instance = ManageFeedsWindow(self, self.app_context, on_close_callback=self._on_manage_window_close)
        else:
            self.manage_feeds_win_instance.focus()
            
    def _on_manage_window_close(self):
        """Wywoływane po zamknięciu okna zarządzania."""
        self._update_feed_selector()
        self.fetch_news()