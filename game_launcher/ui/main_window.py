"""
Main Window - Główne okno aplikacji z menu bocznym
AI-Friendly: Kontener dla wszystkich widoków
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from utils.logger import get_logger
from ui.library_view import LibraryView
# Import innych widoków dodamy później
from ui.stats_view import StatsView
from ui.roadmap_view import RoadmapView, RoadmapView
from ui.news_view import NewsView
from ui.achievements_view import AchievementsView
from ui.settings_view import SettingsView
from ui.home_view import HomeView
from ui.music_view import MusicView
from ui.chat_view import ChatView


class MainWindow:
    """
    Główne okno aplikacji z menu bocznym i obszarem zawartości.
    
    AI Note: 
    - Lewe menu z przyciskami nawigacji
    - Prawy panel - dynamiczna zawartość (widoki)
    - Przełączanie widoków przez show_view()
    """
    
    def __init__(self, root, config_manager, database):
        """
        Inicjalizuje główne okno.
        
        Args:
            root (tk.Tk): Główne okno Tkinter
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        self.root = root
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Aktualny widok
        self.current_view = None
        self.current_view_name = None
        
        # Konfiguracja okna
        self._setup_window()
        
        # Tworzenie layoutu
        self._create_layout()
        
        # Pokazanie domyślnego widoku
        self.show_view('library')
        
        self.logger.info("Main window initialized")
    
    def _setup_window(self):
        """
        Konfiguruje główne okno aplikacji.
        
        AI Note: Rozmiar, tytuł, ikona
        """
        self.root.title("Game Launcher")
        
        # Rozmiar okna z configu
        window_size = self.config.get('ui', 'window_size', default='1200x800')
        self.root.geometry(window_size)
        
        # Minimalna wielkość
        self.root.minsize(800, 600)
        
        # Event przy zamykaniu
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Theme/style
        self._apply_theme()
    
    def _apply_theme(self):
        """
        Aplikuje motyw ciemny/jasny.
        
        AI Note: Kolory można łatwo zmieniać
        """
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            # Ciemny motyw
            self.colors = {
                'bg': '#2c3e50',          # Tło główne
                'sidebar_bg': '#1a252f',  # Tło menu bocznego
                'button_bg': '#34495e',   # Tło przycisku
                'button_hover': '#4a5f7f',# Hover przycisku
                'button_active': '#3498db', # Aktywny przycisk
                'text': '#ecf0f1',        # Tekst
                'accent': '#3498db'       # Kolor akcentu
            }
        else:
            # Jasny motyw
            self.colors = {
                'bg': '#ecf0f1',
                'sidebar_bg': '#bdc3c7',
                'button_bg': '#95a5a6',
                'button_hover': '#7f8c8d',
                'button_active': '#3498db',
                'text': '#2c3e50',
                'accent': '#3498db'
            }
        
        self.root.configure(bg=self.colors['bg'])
    
    def _create_layout(self):
        """
        Tworzy główny layout: menu boczne + obszar zawartości.
        
        AI Note: Grid layout - łatwy do modyfikacji
        """
        # Główny container
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)  # Kolumna zawartości rozciąga się
        
        # Menu boczne (lewa strona)
        self._create_sidebar()
        
        # Obszar zawartości (prawa strona)
        self._create_content_area()
    
    def _create_sidebar(self):
        """
        Tworzy menu boczne z przyciskami nawigacji.
        
        AI Note: Każdy przycisk wywołuje show_view() z nazwą widoku
        """
        # Frame menu bocznego
        self.sidebar = tk.Frame(
            self.root,
            bg=self.colors['sidebar_bg'],
            width=200
        )
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)  # Stała szerokość
        
        # Tytuł aplikacji
        title_label = tk.Label(
            self.sidebar,
            text="Game Launcher",
            font=('Arial', 16, 'bold'),
            bg=self.colors['sidebar_bg'],
            fg=self.colors['text'],
            pady=20
        )
        title_label.pack(fill='x')
        
        # Separator
        separator = tk.Frame(self.sidebar, height=2, bg=self.colors['accent'])
        separator.pack(fill='x', padx=10, pady=5)
        
        # Przyciski menu
        self.menu_buttons = {}
        
        menu_items = [
            ('Strona Główna', 'home'),
            ('Biblioteka', 'library'),
            ('Roadmapa', 'roadmap'),
            ('Osiągnięcia', 'achievements'),
            ('Newsy', 'news'),
            ('Statystyki', 'stats'),
            ('Muzyka', 'music'),
            ('Czat', 'chat'),
            ('Ustawienia', 'settings'),
            None,  # Separator
            ('Wyjście', 'exit')
        ]
        
        for item in menu_items:
            if item is None:
                # Separator
                sep = tk.Frame(self.sidebar, height=1, bg=self.colors['button_bg'])
                sep.pack(fill='x', padx=10, pady=10)
            else:
                label, view_name = item
                btn = self._create_menu_button(label, view_name)
                self.menu_buttons[view_name] = btn
    
    def _create_menu_button(self, text, view_name):
        """
        Tworzy przycisk menu.
        
        Args:
            text (str): Tekst przycisku
            view_name (str): Nazwa widoku do pokazania
        
        Returns:
            tk.Button: Stworzony przycisk
        
        AI Note: Przyciski z hover efektem
        """
        btn = tk.Button(
            self.sidebar,
            text=text,
            font=('Arial', 11),
            bg=self.colors['button_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['button_hover'],
            activeforeground=self.colors['text'],
            relief='flat',
            cursor='hand2',
            anchor='w',
            padx=20,
            pady=10,
            command=lambda: self._handle_menu_click(view_name)
        )
        btn.pack(fill='x', padx=10, pady=2)
        
        # Hover effect
        btn.bind('<Enter>', lambda e: btn.config(bg=self.colors['button_hover']))
        btn.bind('<Leave>', lambda e: btn.config(
            bg=self.colors['button_active'] if view_name == self.current_view_name 
            else self.colors['button_bg']
        ))
        
        return btn
    
    def _handle_menu_click(self, view_name):
        """
        Obsługuje kliknięcie w przycisk menu.
        
        Args:
            view_name (str): Nazwa widoku
        
        AI Note: Specjalne akcje dla exit, reszta to show_view()
        """
        if view_name == 'exit':
            self._on_closing()
        else:
            self.show_view(view_name)
    
    def _create_content_area(self):
        """
        Tworzy obszar zawartości (prawa strona).
        
        AI Note: Tu będą wyświetlane widoki
        """
        self.content_area = tk.Frame(
            self.root,
            bg=self.colors['bg']
        )
        self.content_area.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        
        # Konfiguracja grid dla dynamicznej zawartości
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
    
    def show_view(self, view_name):
        """
        Pokazuje wybrany widok w obszarze zawartości.
        
        Args:
            view_name (str): Nazwa widoku (library, stats, roadmap, etc.)
        
        AI Note: Tutaj dodawaj nowe widoki
        """
        # Usuń poprzedni widok
        if self.current_view:
            self.current_view.destroy()
            self.current_view = None
        
        # Aktualizuj kolory przycisków
        self._update_menu_buttons(view_name)
        
        # Utwórz nowy widok
        try:
            if view_name == 'library':
                self.current_view = LibraryView(self.content_area, self.config, self.db)
            
            elif view_name == 'stats':
                self.current_view = StatsView(self.content_area, self.config, self.db)

            elif view_name == 'roadmap':
                self.current_view = RoadmapView(self.content_area, self.config, self.db)
            
            elif view_name == 'news':
                self.current_view = NewsView(self.content_area, self.config, self.db)

            elif view_name == 'achievements':
                self.current_view = AchievementsView(self.content_area, self.config, self.db)

            elif view_name == 'settings':
                self.current_view = SettingsView(self.content_area, self.config, self.db)

            elif view_name == 'home':
                self.current_view = HomeView(self.content_area, self.config, self.db)

            elif view_name == 'music':
                self.current_view = MusicView(self.content_area, self.config, self.db)

            elif view_name == 'chat':
                self.current_view = ChatView(self.content_area, self.config, self.db)
            
            else:
                self.current_view = self._create_placeholder(f"Widok '{view_name}' nie istnieje")
            
            self.current_view_name = view_name
            self.logger.info(f"Switched to view: {view_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to load view {view_name}: {e}")
            self.current_view = self._create_placeholder(f"Błąd ładowania widoku:\n{str(e)}")
    
    def _create_placeholder(self, text):
        """
        Tworzy placeholder widok dla niezaimplementowanych sekcji.
        
        Args:
            text (str): Tekst do wyświetlenia
        
        Returns:
            tk.Frame: Frame z placeholderem
        
        AI Note: Użyj podczas developmentu
        """
        frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        frame.grid(row=0, column=0, sticky='nsew')
        
        label = tk.Label(
            frame,
            text=text,
            font=('Arial', 16),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        label.place(relx=0.5, rely=0.5, anchor='center')
        
        return frame
    
    def _update_menu_buttons(self, active_view):
        """
        Aktualizuje wygląd przycisków menu (podświetla aktywny).
        
        Args:
            active_view (str): Nazwa aktywnego widoku
        
        AI Note: Zmienia kolor aktywnego przycisku
        """
        for view_name, btn in self.menu_buttons.items():
            if view_name == active_view:
                btn.config(bg=self.colors['button_active'])
            else:
                btn.config(bg=self.colors['button_bg'])
    
    def _on_closing(self):
        """
        Obsługuje zamknięcie aplikacji.
        
        AI Note: Tutaj dodaj cleanup (zamknij połączenia, zapisz stan)
        """
        if messagebox.askokcancel("Wyjście", "Czy na pewno chcesz zamknąć launcher?"):
            self.logger.info("Closing application")
            
            # Zamknij bazę danych
            self.db.close()
            
            # Zapisz konfigurację
            self.config.save()
            
            # Zamknij okno
            self.root.destroy()