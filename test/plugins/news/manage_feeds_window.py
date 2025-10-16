# plugins/news/manage_feeds_window.py
import customtkinter as ctk

class ManageFeedsWindow(ctk.CTkToplevel):
    def __init__(self, parent, app_context, on_close_callback):
        super().__init__(parent)
        self.app_context = app_context
        self.on_close_callback = on_close_callback

        self.title("Zarządzaj kanałami RSS")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()
        
        # Upewnij się, że funkcja zwrotna jest wywoływana po zamknięciu okna
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Zapisane kanały")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.populate_feeds()

    def populate_feeds(self):
        """Czyści i ponownie wypełnia listę kanałów."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        news_data = self.app_context.data_manager.get_plugin_data("news")
        feeds = news_data.get("feeds", [])

        for feed in feeds:
            feed_frame = ctk.CTkFrame(self.scrollable_frame)
            feed_frame.pack(fill="x", pady=5)

            label_text = f"{feed.get('name', 'Brak nazwy')}\n({feed.get('url')})"
            label = ctk.CTkLabel(feed_frame, text=label_text, justify="left")
            label.pack(side="left", fill="x", expand=True, padx=10, pady=5)

            remove_button = ctk.CTkButton(
                feed_frame, 
                text="Usuń", 
                width=80, 
                command=lambda f=feed: self.remove_feed(f)
            )
            remove_button.pack(side="right", padx=10, pady=5)

    def remove_feed(self, feed_to_remove):
        """Usuwa wybrany kanał z bazy danych."""
        news_data = self.app_context.data_manager.get_plugin_data("news")
        feeds = news_data.get("feeds", [])
        
        # Tworzy nową listę, pomijając kanał do usunięcia
        updated_feeds = [feed for feed in feeds if feed.get('url') != feed_to_remove.get('url')]
        
        news_data["feeds"] = updated_feeds
        self.app_context.data_manager.save_plugin_data("news", news_data)
        
        # Odśwież listę w tym oknie
        self.populate_feeds()
        
    def on_close(self):
        """Wywołuje callback i zamyka okno."""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()