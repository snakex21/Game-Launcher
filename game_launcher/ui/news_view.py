"""
News View - Wyświetlanie newsów z RSS
AI-Friendly: Lista newsów z możliwością otwierania linków
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from utils.logger import get_logger
from features.rss_reader import RSSReader


class NewsView(tk.Frame):
    """
    Widok newsów - wyświetla aktualności o grach.
    
    AI Note:
    - RSS feed z newsami
    - Klikalne linki
    - Auto-refresh co 30 minut
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok newsów.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych (nieużywana tutaj)
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # RSS Reader
        feed_urls = self.config.get('features', 'rss_feeds', default=[
            'https://www.ign.com/feed.xml'
        ])
        self.rss_reader = RSSReader(feed_urls=feed_urls)
        
        # Dane
        self.news = []
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Start RSS reader
        self.rss_reader.start_auto_refresh()
        
        # Ładowanie newsów
        self.refresh_news()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'card_bg': '#34495e',
                'text': '#ecf0f1',
                'accent': '#3498db',
                'hover': '#4a5f7f'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'card_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'hover': '#95a5a6'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Header + Scrollable news list
        """
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Scrollable news area
        self._create_news_area()
    
    def _create_header(self):
        """Tworzy header z tytułem i przyciskiem odświeżania."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Tytuł
        title = tk.Label(
            header,
            text="Newsy",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Przycisk odświeżania
        refresh_btn = tk.Button(
            header,
            text="🔄 Odśwież",
            font=('Arial', 11),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=15,
            pady=5,
            command=self.refresh_news
        )
        refresh_btn.pack(side='right', padx=10)
        
        # Status label
        self.status_label = tk.Label(
            header,
            text="",
            font=('Arial', 9),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        self.status_label.pack(side='right', padx=10)
    
    def _create_news_area(self):
        """Tworzy scrollable obszar dla newsów."""
        # Container z scrollbarem
        container = tk.Frame(self, bg=self.colors['bg'])
        container.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        
        # Canvas
        self.canvas = tk.Canvas(container, bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame wewnątrz canvas
        self.news_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.news_frame, anchor='nw')
        
        # Update scroll region
        self.news_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scroll
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def refresh_news(self):
        """
        Odświeża newsy z RSS.
        
        AI Note: Wywołaj ręcznie lub automatycznie
        """
        self.status_label.config(text="Ładowanie...")
        self.update_idletasks()
        
        # Pobierz newsy
        self.news = self.rss_reader.fetch_news(force=True)
        
        # Wyświetl
        self._display_news()
        
        # Update status
        if self.news:
            self.status_label.config(text=f"Załadowano {len(self.news)} newsów")
        else:
            self.status_label.config(text="Brak newsów")
        
        self.logger.info(f"News refreshed: {len(self.news)} items")
    
    def _display_news(self):
        """Wyświetla newsy jako karty."""
        # Wyczyść poprzednie
        for widget in self.news_frame.winfo_children():
            widget.destroy()
        
        if not self.news:
            # Placeholder
            no_news_label = tk.Label(
                self.news_frame,
                text="Brak newsów do wyświetlenia",
                font=('Arial', 14),
                bg=self.colors['bg'],
                fg=self.colors['text']
            )
            no_news_label.pack(pady=50)
            return
        
        # Tworzenie kart newsów
        for news_item in self.news:
            card = self._create_news_card(news_item)
            card.pack(fill='x', padx=10, pady=5)
    
    def _create_news_card(self, news_item):
        """
        Tworzy kartę dla pojedynczego newsa.
        
        Args:
            news_item (dict): Dane newsa
        
        Returns:
            tk.Frame: Karta newsa
        
        AI Note: Tytuł + opis + źródło + link
        """
        card = tk.Frame(
            self.news_frame,
            bg=self.colors['card_bg'],
            relief='raised',
            borderwidth=1
        )
        card.pack(fill='x', pady=5)
        
        # Padding wewnętrzny
        inner_frame = tk.Frame(card, bg=self.colors['card_bg'])
        inner_frame.pack(fill='x', padx=15, pady=10)
        
        # Tytuł (kliknalny)
        title_label = tk.Label(
            inner_frame,
            text=news_item['title'],
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent'],
            cursor='hand2',
            anchor='w',
            justify='left',
            wraplength=900
        )
        title_label.pack(fill='x')
        title_label.bind('<Button-1>', lambda e: self._open_link(news_item['link']))
        
        # Opis
        desc_label = tk.Label(
            inner_frame,
            text=news_item['description'],
            font=('Arial', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            anchor='w',
            justify='left',
            wraplength=900
        )
        desc_label.pack(fill='x', pady=(5, 0))
        
        # Footer (źródło + data)
        footer_frame = tk.Frame(inner_frame, bg=self.colors['card_bg'])
        footer_frame.pack(fill='x', pady=(10, 0))
        
        # Źródło
        source_label = tk.Label(
            footer_frame,
            text=f"📰 {news_item['source']}",
            font=('Arial', 9),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        source_label.pack(side='left')
        
        # Data
        date_str = news_item['published'].strftime('%Y-%m-%d %H:%M')
        date_label = tk.Label(
            footer_frame,
            text=f"🕒 {date_str}",
            font=('Arial', 9),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        date_label.pack(side='right')
        
        # Hover effect
        card.bind('<Enter>', lambda e: card.config(bg=self.colors['hover']))
        card.bind('<Leave>', lambda e: card.config(bg=self.colors['card_bg']))
        inner_frame.bind('<Enter>', lambda e: inner_frame.config(bg=self.colors['hover']))
        inner_frame.bind('<Leave>', lambda e: inner_frame.config(bg=self.colors['card_bg']))
        
        return card
    
    def _open_link(self, url):
        """
        Otwiera link w przeglądarce.
        
        Args:
            url (str): URL do otwarcia
        """
        try:
            webbrowser.open(url)
            self.logger.info(f"Opened link: {url}")
        except Exception as e:
            self.logger.error(f"Failed to open link {url}: {e}")
            messagebox.showerror("Błąd", f"Nie można otworzyć linku:\n{str(e)}")
    
    def _on_frame_configure(self, event):
        """Update scroll region."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Resize news frame to canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Scroll with mouse wheel."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def destroy(self):
        """
        Cleanup przy zamykaniu widoku.
        
        AI Note: Zatrzymuje RSS reader
        """
        self.rss_reader.stop_auto_refresh()
        super().destroy()