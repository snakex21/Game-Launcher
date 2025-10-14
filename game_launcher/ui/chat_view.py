"""
Chat View - Panel czatu z kontrolkami serwera
AI-Friendly: Uruchom serwer i otwórz w przeglądarce
"""

import tkinter as tk
from tkinter import messagebox
import webbrowser
from utils.logger import get_logger
from features.chat_server import ChatServer


class ChatView(tk.Frame):
    """
    Widok czatu - kontrolki serwera.
    
    AI Note:
    - Start/Stop serwera
    - Link do otwarcia w przeglądarce
    - Status serwera
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok czatu.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Chat server
        chat_config = self.config.get('features', 'chat_server', default={})
        port = chat_config.get('port', 5000)
        
        self.chat_server = ChatServer(port=port)
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
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
                'success': '#27ae60',
                'danger': '#e74c3c'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'card_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'success': '#27ae60',
                'danger': '#e74c3c'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """Tworzy interfejs użytkownika."""
        # Header
        header = tk.Frame(self, bg=self.colors['bg'])
        header.pack(pady=20)
        
        title = tk.Label(
            header,
            text="💬 Serwer Czatu",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack()
        
        # Card z kontrolkami
        card = tk.Frame(self, bg=self.colors['card_bg'], relief='raised', borderwidth=2)
        card.pack(padx=50, pady=20, fill='both', expand=True)
        
        inner = tk.Frame(card, bg=self.colors['card_bg'])
        inner.pack(padx=50, pady=50)
        
        # Opis
        desc = tk.Label(
            inner,
            text="Uruchom serwer czatu aby czatować z innymi\ngraczami w lokalnej sieci",
            font=('Arial', 12),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            justify='center'
        )
        desc.pack(pady=20)
        
        # Status
        status_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        status_frame.pack(pady=20)
        
        tk.Label(
            status_frame,
            text="Status:",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        ).pack(side='left', padx=10)
        
        self.status_label = tk.Label(
            status_frame,
            text="⚫ Zatrzymany",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['danger']
        )
        self.status_label.pack(side='left')
        
        # Przyciski
        buttons_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        buttons_frame.pack(pady=30)
        
        self.start_btn = tk.Button(
            buttons_frame,
            text="▶️ Uruchom Serwer",
            font=('Arial', 14, 'bold'),
            bg=self.colors['success'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=30,
            pady=15,
            command=self._start_server
        )
        self.start_btn.pack(side='left', padx=10)
        
        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹️ Zatrzymaj Serwer",
            font=('Arial', 14, 'bold'),
            bg=self.colors['danger'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=30,
            pady=15,
            command=self._stop_server,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=10)
        
        # Link
        self.link_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        self.link_frame.pack(pady=20)
        
        # Instrukcje
        info_frame = tk.Frame(inner, bg=self.colors['card_bg'])
        info_frame.pack(pady=30)
        
        info_text = """
        📌 Instrukcje:
        
        1. Kliknij "Uruchom Serwer"
        2. Kliknij "Otwórz Czat w Przeglądarce"
        3. Udostępnij URL innym graczom w sieci
        4. Wszyscy mogą czatować w czasie rzeczywistym!
        """
        
        tk.Label(
            info_frame,
            text=info_text,
            font=('Arial', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            justify='left'
        ).pack()
    
    def _start_server(self):
        """Uruchamia serwer czatu."""
        if self.chat_server.start():
            self.status_label.config(text="🟢 Działa", fg=self.colors['success'])
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            # Pokaż link
            url = self.chat_server.get_server_url()
            
            link_label = tk.Label(
                self.link_frame,
                text=f"URL: {url}",
                font=('Arial', 11),
                bg=self.colors['card_bg'],
                fg=self.colors['accent'],
                cursor='hand2'
            )
            link_label.pack(pady=5)
            link_label.bind('<Button-1>', lambda e: webbrowser.open(url))
            
            open_btn = tk.Button(
                self.link_frame,
                text="🌐 Otwórz Czat w Przeglądarce",
                font=('Arial', 11),
                bg=self.colors['accent'],
                fg='white',
                cursor='hand2',
                relief='flat',
                padx=20,
                pady=10,
                command=lambda: webbrowser.open(url)
            )
            open_btn.pack(pady=10)
            
            messagebox.showinfo("Sukces", f"Serwer czatu uruchomiony!\n\nURL: {url}")
            self.logger.info("Chat server started from UI")
        else:
            messagebox.showerror("Błąd", "Nie udało się uruchomić serwera czatu")
    
    def _stop_server(self):
        """Zatrzymuje serwer czatu."""
        self.chat_server.stop()
        self.status_label.config(text="⚫ Zatrzymany", fg=self.colors['danger'])
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        # Usuń link
        for widget in self.link_frame.winfo_children():
            widget.destroy()
        
        messagebox.showinfo("Info", "Serwer czatu został zatrzymany")
        self.logger.info("Chat server stopped from UI")
    
    def destroy(self):
        """Cleanup przy zamykaniu widoku."""
        if self.chat_server.is_running:
            self.chat_server.stop()
        super().destroy()