"""
Achievements View - System osiągnięć użytkownika
AI-Friendly: Custom achievements dla gier
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime
from utils.logger import get_logger


class AchievementsView(tk.Frame):
    """
    Widok osiągnięć - customowe achievementy.
    
    AI Note:
    - Dodawanie własnych osiągnięć do gier
    - Odblokowanie osiągnięć
    - Progress tracking
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok osiągnięć.
        
        Args:
            parent: Widget rodzica
            config_manager (ConfigManager): Manager konfiguracji
            database (Database): Obiekt bazy danych
        """
        super().__init__(parent)
        self.config = config_manager
        self.db = database
        self.logger = get_logger()
        
        # Dane
        self.games = []
        self.achievements = []
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Ładowanie danych
        self.refresh_achievements()
        
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
                'locked': '#7f8c8d',
                'unlocked': '#27ae60'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'card_bg': '#bdc3c7',
                'text': '#2c3e50',
                'accent': '#3498db',
                'locked': '#95a5a6',
                'unlocked': '#27ae60'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Header + Stats + Grid of achievements
        """
        # Konfiguracja grid
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Stats bar
        self._create_stats_bar()
        
        # Scrollable achievements grid
        self._create_achievements_grid()
    
    def _create_header(self):
        """Tworzy header z tytułem."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Tytuł
        title = tk.Label(
            header,
            text="Osiągnięcia",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Przycisk dodawania
        add_btn = tk.Button(
            header,
            text="➕ Dodaj Osiągnięcie",
            font=('Arial', 11),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=20,
            pady=8,
            command=self._add_achievement_dialog
        )
        add_btn.pack(side='right', padx=10)
    
    def _create_stats_bar(self):
        """Tworzy pasek ze statystykami osiągnięć."""
        stats_frame = tk.Frame(self, bg=self.colors['card_bg'], relief='raised', borderwidth=1)
        stats_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        
        # Wewnętrzny padding
        inner = tk.Frame(stats_frame, bg=self.colors['card_bg'])
        inner.pack(fill='x', padx=20, pady=15)
        
        # Labels ze statystykami
        self.total_label = tk.Label(
            inner,
            text="Wszystkie: 0",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text']
        )
        self.total_label.pack(side='left', padx=20)
        
        self.unlocked_label = tk.Label(
            inner,
            text="Odblokowane: 0",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['unlocked']
        )
        self.unlocked_label.pack(side='left', padx=20)
        
        self.locked_label = tk.Label(
            inner,
            text="Zablokowane: 0",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['locked']
        )
        self.locked_label.pack(side='left', padx=20)
        
        # Progress bar
        self.progress_label = tk.Label(
            inner,
            text="Progress: 0%",
            font=('Arial', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        self.progress_label.pack(side='right', padx=20)
    
    def _create_achievements_grid(self):
        """Tworzy scrollable grid dla osiągnięć."""
        # Container z scrollbarem
        container = tk.Frame(self, bg=self.colors['bg'])
        container.grid(row=2, column=0, sticky='nsew', padx=10, pady=10)
        
        # Canvas
        self.canvas = tk.Canvas(container, bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame wewnątrz canvas
        self.achievements_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        self.canvas_window = self.canvas.create_window((0, 0), window=self.achievements_frame, anchor='nw')
        
        # Update scroll region
        self.achievements_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scroll
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def refresh_achievements(self):
        """Odświeża listę osiągnięć z bazy."""
        # Pobierz gry
        self.games = self.db.get_all_games()
        
        # Pobierz osiągnięcia
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT a.*, g.name as game_name
            FROM achievements a
            LEFT JOIN games g ON a.game_id = g.id
            ORDER BY a.unlocked DESC, a.id DESC
        """)
        rows = cursor.fetchall()
        self.achievements = [dict(row) for row in rows]
        
        # Aktualizuj UI
        self._update_stats()
        self._display_achievements()
        
        self.logger.info(f"Achievements refreshed: {len(self.achievements)} total")
    
    def _update_stats(self):
        """Aktualizuje statystyki osiągnięć."""
        total = len(self.achievements)
        unlocked = sum(1 for a in self.achievements if a['unlocked'])
        locked = total - unlocked
        progress = int((unlocked / total * 100) if total > 0 else 0)
        
        self.total_label.config(text=f"Wszystkie: {total}")
        self.unlocked_label.config(text=f"Odblokowane: {unlocked}")
        self.locked_label.config(text=f"Zablokowane: {locked}")
        self.progress_label.config(text=f"Progress: {progress}%")
    
    def _display_achievements(self):
        """Wyświetla osiągnięcia w grid."""
        # Wyczyść poprzednie
        for widget in self.achievements_frame.winfo_children():
            widget.destroy()
        
        if not self.achievements:
            # Placeholder
            no_ach_label = tk.Label(
                self.achievements_frame,
                text="Brak osiągnięć. Dodaj pierwsze!",
                font=('Arial', 14),
                bg=self.colors['bg'],
                fg=self.colors['text']
            )
            no_ach_label.pack(pady=50)
            return
        
        # Grid - 2 kolumny
        columns = 2
        
        for idx, achievement in enumerate(self.achievements):
            row = idx // columns
            col = idx % columns
            
            card = self._create_achievement_card(achievement)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='ew')
        
        # Konfiguruj kolumny żeby się rozciągały
        for col in range(columns):
            self.achievements_frame.grid_columnconfigure(col, weight=1)
    
    def _create_achievement_card(self, achievement):
        """
        Tworzy kartę osiągnięcia.
        
        Args:
            achievement (dict): Dane osiągnięcia
        
        Returns:
            tk.Frame: Karta
        
        AI Note: Ikona (emoji) + nazwa + opis + status
        """
        is_unlocked = achievement['unlocked']
        bg_color = self.colors['card_bg']
        
        card = tk.Frame(
            self.achievements_frame,
            bg=bg_color,
            relief='raised',
            borderwidth=1
        )
        
        # Padding wewnętrzny
        inner = tk.Frame(card, bg=bg_color)
        inner.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Header (ikona + nazwa)
        header_frame = tk.Frame(inner, bg=bg_color)
        header_frame.pack(fill='x')
        
        # Ikona (emoji - trofeum)
        icon = "🏆" if is_unlocked else "🔒"
        icon_label = tk.Label(
            header_frame,
            text=icon,
            font=('Arial', 24),
            bg=bg_color
        )
        icon_label.pack(side='left', padx=(0, 10))
        
        # Nazwa
        name_label = tk.Label(
            header_frame,
            text=achievement['name'],
            font=('Arial', 12, 'bold'),
            bg=bg_color,
            fg=self.colors['unlocked'] if is_unlocked else self.colors['locked'],
            anchor='w'
        )
        name_label.pack(side='left', fill='x', expand=True)
        
        # Opis
        desc_label = tk.Label(
            inner,
            text=achievement['description'] or "Brak opisu",
            font=('Arial', 10),
            bg=bg_color,
            fg=self.colors['text'],
            anchor='w',
            justify='left',
            wraplength=350
        )
        desc_label.pack(fill='x', pady=(5, 0))
        
        # Footer (gra + data odblokowania lub przycisk)
        footer_frame = tk.Frame(inner, bg=bg_color)
        footer_frame.pack(fill='x', pady=(10, 0))
        
        # Nazwa gry
        game_name = achievement.get('game_name', 'Globalne')
        game_label = tk.Label(
            footer_frame,
            text=f"🎮 {game_name}",
            font=('Arial', 9),
            bg=bg_color,
            fg=self.colors['text']
        )
        game_label.pack(side='left')
        
        if is_unlocked:
            # Data odblokowania
            unlock_date = achievement.get('unlock_date', '')
            if unlock_date:
                date_str = datetime.fromisoformat(unlock_date).strftime('%Y-%m-%d')
                date_label = tk.Label(
                    footer_frame,
                    text=f"✅ {date_str}",
                    font=('Arial', 9),
                    bg=bg_color,
                    fg=self.colors['unlocked']
                )
                date_label.pack(side='right')
        else:
            # Przycisk odblokowania
            unlock_btn = tk.Button(
                footer_frame,
                text="Odblokuj",
                font=('Arial', 9),
                bg=self.colors['accent'],
                fg='white',
                cursor='hand2',
                relief='flat',
                command=lambda: self._unlock_achievement(achievement['id'])
            )
            unlock_btn.pack(side='right')
        
        return card
    
    def _add_achievement_dialog(self):
        """Dialog dodawania osiągnięcia."""
        dialog = tk.Toplevel(self)
        dialog.title("Dodaj Osiągnięcie")
        dialog.geometry("450x400")
        dialog.configure(bg=self.colors['bg'])
        
        # Nazwa
        tk.Label(
            dialog,
            text="Nazwa osiągnięcia:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=5)
        
        name_entry = tk.Entry(dialog, width=40)
        name_entry.pack(pady=5)
        
        # Opis
        tk.Label(
            dialog,
            text="Opis:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=5)
        
        desc_text = tk.Text(dialog, width=40, height=4)
        desc_text.pack(pady=5)
        
        # Gra (opcjonalnie)
        tk.Label(
            dialog,
            text="Gra (opcjonalnie):",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=5)
        
        game_var = tk.StringVar(value="Globalne")
        game_names = ["Globalne"] + [g['name'] for g in self.games]
        
        game_combo = ttk.Combobox(
            dialog,
            textvariable=game_var,
            values=game_names,
            state='readonly',
            width=37
        )
        game_combo.pack(pady=5)
        
        # Przycisk dodaj
        def add_achievement():
            name = name_entry.get().strip()
            desc = desc_text.get('1.0', 'end-1c').strip()
            game_name = game_var.get()
            
            if not name:
                messagebox.showwarning("Błąd", "Nazwa jest wymagana!")
                return
            
            # Znajdź game_id
            game_id = None
            if game_name != "Globalne":
                game = next((g for g in self.games if g['name'] == game_name), None)
                if game:
                    game_id = game['id']
            
            # Dodaj do bazy
            try:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "INSERT INTO achievements (game_id, name, description) VALUES (?, ?, ?)",
                    (game_id, name, desc)
                )
                self.db.conn.commit()
                
                messagebox.showinfo("Sukces", f"Dodano osiągnięcie: {name}")
                dialog.destroy()
                self.refresh_achievements()
                
            except Exception as e:
                self.logger.error(f"Failed to add achievement: {e}")
                messagebox.showerror("Błąd", str(e))
        
        tk.Button(
            dialog,
            text="Dodaj Osiągnięcie",
            bg=self.colors['accent'],
            fg='white',
            command=add_achievement
        ).pack(pady=20)
    
    def _unlock_achievement(self, achievement_id):
        """
        Odblokowuje osiągnięcie.
        
        Args:
            achievement_id (int): ID osiągnięcia
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE achievements SET unlocked = 1, unlock_date = ? WHERE id = ?",
                (datetime.now().isoformat(), achievement_id)
            )
            self.db.conn.commit()
            
            self.refresh_achievements()
            self.logger.info(f"Unlocked achievement {achievement_id}")
            
            messagebox.showinfo("Gratulacje!", "Osiągnięcie odblokowane! 🏆")
            
        except Exception as e:
            self.logger.error(f"Failed to unlock achievement: {e}")
            messagebox.showerror("Błąd", str(e))
    
    def _on_frame_configure(self, event):
        """Update scroll region."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Resize achievements frame to canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Scroll with mouse wheel."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')