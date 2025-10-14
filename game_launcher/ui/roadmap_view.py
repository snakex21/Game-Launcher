"""
Roadmap View - Kalendarz planowanych gier
AI-Friendly: Calendar widget do planowania
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
from datetime import datetime
from utils.logger import get_logger


class RoadmapView(tk.Frame):
    """
    Widok roadmapy - planowanie gier w kalendarzu.
    
    AI Note:
    - Kalendarz z zaznaczonymi grami
    - Dodawanie/usuwanie planów
    - Status: planned, in_progress, completed
    """
    
    def __init__(self, parent, config_manager, database):
        """
        Inicjalizuje widok roadmapy.
        
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
        self.roadmap_items = []
        
        # Konfiguracja stylu
        self._load_theme()
        
        # Tworzenie UI
        self._create_ui()
        
        # Ładowanie danych
        self.refresh_roadmap()
        
        # Grid w parent
        self.grid(row=0, column=0, sticky='nsew')
    
    def _load_theme(self):
        """Ładuje kolory z konfiguracji."""
        theme = self.config.get('app', 'theme', default='dark')
        
        if theme == 'dark':
            self.colors = {
                'bg': '#2c3e50',
                'text': '#ecf0f1',
                'accent': '#3498db',
                'card_bg': '#34495e'
            }
        else:
            self.colors = {
                'bg': '#ecf0f1',
                'text': '#2c3e50',
                'accent': '#3498db',
                'card_bg': '#bdc3c7'
            }
        
        self.configure(bg=self.colors['bg'])
    
    def _create_ui(self):
        """
        Tworzy interfejs użytkownika.
        
        AI Note: Header + Calendar + List
        """
        # Konfiguracja grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self._create_header()
        
        # Main container
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)
        
        # Kalendarz
        self._create_calendar(main_container)
        
        # Lista planów
        self._create_roadmap_list(main_container)
    
    def _create_header(self):
        """Tworzy header z tytułem."""
        header = tk.Frame(self, bg=self.colors['bg'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Tytuł
        title = tk.Label(
            header,
            text="Roadmapa Gier",
            font=('Arial', 18, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        title.pack(side='left', padx=10)
        
        # Przycisk dodawania
        add_btn = tk.Button(
            header,
            text="➕ Dodaj do Roadmapy",
            font=('Arial', 11),
            bg=self.colors['accent'],
            fg='white',
            cursor='hand2',
            relief='flat',
            padx=20,
            pady=8,
            command=self._add_to_roadmap_dialog
        )
        add_btn.pack(side='right', padx=10)
    
    def _create_calendar(self, parent):
        """
        Tworzy kalendarz.
        
        Args:
            parent: Widget rodzica
        """
        calendar_frame = tk.Frame(parent, bg=self.colors['bg'])
        calendar_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        
        # Kalendarz
        self.calendar = Calendar(
            calendar_frame,
            selectmode='day',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day
        )
        self.calendar.pack(fill='both', expand=True, pady=10)
        
        # Event przy wyborze daty
        self.calendar.bind('<<CalendarSelected>>', self._on_date_selected)
    
    def _create_roadmap_list(self, parent):
        """
        Tworzy listę planowanych gier.
        
        Args:
            parent: Widget rodzica
        """
        list_frame = tk.Frame(parent, bg=self.colors['bg'])
        list_frame.grid(row=0, column=1, sticky='nsew')
        
        # Tytuł
        tk.Label(
            list_frame,
            text="Zaplanowane Gry",
            font=('Arial', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        # Treeview
        columns = ('Game', 'Date', 'Status')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        self.tree.heading('Game', text='Gra')
        self.tree.heading('Date', text='Data')
        self.tree.heading('Status', text='Status')
        
        self.tree.column('Game', width=200)
        self.tree.column('Date', width=100)
        self.tree.column('Status', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Context menu
        self.tree.bind('<Button-3>', self._show_context_menu)
    
    def refresh_roadmap(self):
        """
        Odświeża roadmapę z bazy.
        
        AI Note: Wywołaj po dodaniu/usunięciu planu
        """
        # Pobierz gry
        self.games = self.db.get_all_games()
        
        # Pobierz roadmap items
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT r.*, g.name as game_name
            FROM roadmap r
            JOIN games g ON r.game_id = g.id
            ORDER BY r.planned_date
        """)
        rows = cursor.fetchall()
        self.roadmap_items = [dict(row) for row in rows]
        
        # Aktualizuj listę
        self._update_list()
        
        # Aktualizuj kalendarz (zaznacz daty)
        self._highlight_calendar_dates()
        
        self.logger.info(f"Roadmap refreshed: {len(self.roadmap_items)} items")
    
    def _update_list(self):
        """Aktualizuje listę roadmapy."""
        # Wyczyść
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Status mapping
        status_map = {
            'planned': '📅 Zaplanowane',
            'in_progress': '🎮 W trakcie',
            'completed': '✅ Ukończone'
        }
        
        # Dodaj items
        for item in self.roadmap_items:
            status_text = status_map.get(item['status'], item['status'])
            self.tree.insert(
                '', 'end',
                values=(
                    item['game_name'],
                    item['planned_date'],
                    status_text
                ),
                tags=(str(item['id']),)
            )
    
    def _highlight_calendar_dates(self):
        """
        Zaznacza w kalendarzu daty z grami.
        
        AI Note: Dodaje events do kalendarza
        """
        # TODO: tkcalendar ma ograniczone API dla custom highlighting
        # Można dodać calevent() ale wymaga rozbudowy
        pass
    
    def _on_date_selected(self, event):
        """
        Obsługuje wybór daty w kalendarzu.
        
        AI Note: Można pokazać gry na ten dzień
        """
        selected_date = self.calendar.get_date()
        self.logger.info(f"Date selected: {selected_date}")
        
        # Filtruj roadmap items dla tej daty
        # TODO: Implementacja filtrowania
    
    def _add_to_roadmap_dialog(self):
        """Dialog dodawania gry do roadmapy."""
        dialog = tk.Toplevel(self)
        dialog.title("Dodaj do Roadmapy")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg'])
        
        # Wybór gry
        tk.Label(
            dialog,
            text="Wybierz grę:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        game_var = tk.StringVar()
        game_names = [g['name'] for g in self.games]
        
        if not game_names:
            messagebox.showinfo("Info", "Najpierw dodaj gry do biblioteki!")
            dialog.destroy()
            return
        
        game_combo = ttk.Combobox(
            dialog,
            textvariable=game_var,
            values=game_names,
            state='readonly',
            width=35
        )
        game_combo.pack(pady=5)
        game_combo.current(0)
        
        # Data
        tk.Label(
            dialog,
            text="Planowana data:",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        date_entry = Calendar(
            dialog,
            selectmode='day',
            date_pattern='yyyy-mm-dd'
        )
        date_entry.pack(pady=5)
        
        # Notatki
        tk.Label(
            dialog,
            text="Notatki (opcjonalnie):",
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=10)
        
        notes_text = tk.Text(dialog, width=40, height=4)
        notes_text.pack(pady=5)
        
        # Przycisk dodaj
        def add_roadmap():
            game_name = game_var.get()
            planned_date = date_entry.get_date()
            notes = notes_text.get('1.0', 'end-1c').strip()
            
            # Znajdź game_id
            game = next((g for g in self.games if g['name'] == game_name), None)
            
            if not game:
                messagebox.showerror("Błąd", "Nie znaleziono gry")
                return
            
            # Dodaj do bazy
            try:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "INSERT INTO roadmap (game_id, planned_date, notes) VALUES (?, ?, ?)",
                    (game['id'], planned_date, notes)
                )
                self.db.conn.commit()
                
                messagebox.showinfo("Sukces", f"Dodano {game_name} do roadmapy!")
                dialog.destroy()
                self.refresh_roadmap()
                
            except Exception as e:
                self.logger.error(f"Failed to add roadmap item: {e}")
                messagebox.showerror("Błąd", str(e))
        
        tk.Button(
            dialog,
            text="Dodaj",
            bg=self.colors['accent'],
            fg='white',
            command=add_roadmap
        ).pack(pady=20)
    
    def _show_context_menu(self, event):
        """
        Pokazuje menu kontekstowe dla roadmap item.
        
        AI Note: Zmiana statusu, usuwanie
        """
        # Wybierz item
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        self.tree.selection_set(item)
        
        # Menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Zmień status na 'W trakcie'", command=lambda: self._change_status(item, 'in_progress'))
        menu.add_command(label="Zmień status na 'Ukończone'", command=lambda: self._change_status(item, 'completed'))
        menu.add_separator()
        menu.add_command(label="Usuń z roadmapy", command=lambda: self._remove_from_roadmap(item))
        
        menu.post(event.x_root, event.y_root)
    
    def _change_status(self, tree_item, new_status):
        """Zmienia status roadmap item."""
        try:
            # Pobierz ID z tagów
            tags = self.tree.item(tree_item, 'tags')
            roadmap_id = int(tags[0])
            
            # Update w bazie
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE roadmap SET status = ? WHERE id = ?",
                (new_status, roadmap_id)
            )
            self.db.conn.commit()
            
            self.refresh_roadmap()
            self.logger.info(f"Changed roadmap item {roadmap_id} status to {new_status}")
            
        except Exception as e:
            self.logger.error(f"Failed to change status: {e}")
            messagebox.showerror("Błąd", str(e))
    
    def _remove_from_roadmap(self, tree_item):
        """Usuwa item z roadmapy."""
        if not messagebox.askyesno("Potwierdzenie", "Usunąć z roadmapy?"):
            return
        
        try:
            tags = self.tree.item(tree_item, 'tags')
            roadmap_id = int(tags[0])
            
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM roadmap WHERE id = ?", (roadmap_id,))
            self.db.conn.commit()
            
            self.refresh_roadmap()
            self.logger.info(f"Removed roadmap item {roadmap_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove from roadmap: {e}")
            messagebox.showerror("Błąd", str(e))