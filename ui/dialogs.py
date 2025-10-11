"""
Okna dialogowe
Zawiera różne okna dialogowe używane w aplikacji.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, Any

from config.constants import FONT_FAMILY, FONT_SIZE_NORMAL

logger = logging.getLogger(__name__)


class BaseDialog(tk.Toplevel):
    """
    Bazowa klasa dla okien dialogowych.
    Zapewnia wspólną funkcjonalność dla wszystkich dialogów.
    """
    
    def __init__(self, parent, title: str, width: int = 400, height: int = 300):
        """
        Inicjalizuje okno dialogowe.
        
        Args:
            parent: Okno rodzica
            title: Tytuł okna
            width: Szerokość okna
            height: Wysokość okna
        """
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        # Konfiguracja okna
        self.title(title)
        self.transient(parent)  # Okno modalne względem rodzica
        self.grab_set()  # Blokuj interakcję z rodzicem
        
        # Rozmiar i pozycja
        self.geometry(f"{width}x{height}")
        self._center_window()
        
        # Protokół zamknięcia
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def _center_window(self):
        """Wyśrodkowuje okno na ekranie."""
        self.update_idletasks()
        
        # Pobierz wymiary
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Oblicz pozycję środka
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        
        self.geometry(f"+{x}+{y}")
    
    def on_ok(self):
        """Obsługa przycisku OK."""
        self.destroy()
    
    def on_cancel(self):
        """Obsługa przycisku Anuluj."""
        self.result = None
        self.destroy()


class ConfirmDialog(BaseDialog):
    """
    Okno dialogowe z pytaniem Tak/Nie.
    """
    
    def __init__(self, parent, title: str, message: str):
        """
        Inicjalizuje okno potwierdzenia.
        
        Args:
            parent: Okno rodzica
            title: Tytuł okna
            message: Treść pytania
        """
        super().__init__(parent, title, width=400, height=150)
        
        self.message = message
        self._create_ui()
    
    def _create_ui(self):
        """Tworzy interfejs dialogu."""
        # Wiadomość
        message_label = ttk.Label(
            self,
            text=self.message,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            wraplength=350,
            justify="center"
        )
        message_label.pack(pady=20, padx=20)
        
        # Przyciski
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Tak",
            command=self.on_yes,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Nie",
            command=self.on_no,
            width=10
        ).pack(side=tk.LEFT, padx=5)
    
    def on_yes(self):
        """Obsługa przycisku Tak."""
        self.result = True
        self.destroy()
    
    def on_no(self):
        """Obsługa przycisku Nie."""
        self.result = False
        self.destroy()


class InputDialog(BaseDialog):
    """
    Okno dialogowe z polem tekstowym.
    """
    
    def __init__(self, parent, title: str, prompt: str, default: str = ""):
        """
        Inicjalizuje okno input.
        
        Args:
            parent: Okno rodzica
            title: Tytuł okna
            prompt: Tekst prompt
            default: Domyślna wartość
        """
        super().__init__(parent, title, width=400, height=150)
        
        self.prompt = prompt
        self.default = default
        self._create_ui()
    
    def _create_ui(self):
        """Tworzy interfejs dialogu."""
        # Prompt
        prompt_label = ttk.Label(
            self,
            text=self.prompt,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL)
        )
        prompt_label.pack(pady=(20, 10), padx=20)
        
        # Pole tekstowe
        self.entry = ttk.Entry(self, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        self.entry.pack(pady=10, padx=20, fill=tk.X)
        self.entry.insert(0, self.default)
        self.entry.select_range(0, tk.END)
        self.entry.focus()
        
        # Enter zatwierdza
        self.entry.bind("<Return>", lambda e: self.on_ok())
        
        # Przyciski
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self.on_ok,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Anuluj",
            command=self.on_cancel,
            width=10
        ).pack(side=tk.LEFT, padx=5)
    
    def on_ok(self):
        """Obsługa przycisku OK."""
        self.result = self.entry.get().strip()
        self.destroy()


class AboutDialog(BaseDialog):
    """
    Okno dialogowe "O programie".
    """
    
    def __init__(self, parent, app_name: str, version: str, author: str, description: str):
        """
        Inicjalizuje okno About.
        
        Args:
            parent: Okno rodzica
            app_name: Nazwa aplikacji
            version: Wersja
            author: Autor
            description: Opis
        """
        super().__init__(parent, f"O programie {app_name}", width=450, height=300)
        
        self.app_name = app_name
        self.version = version
        self.author = author
        self.description = description
        self._create_ui()
    
    def _create_ui(self):
        """Tworzy interfejs dialogu."""
        # Ramka główna
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Nazwa aplikacji
        name_label = ttk.Label(
            main_frame,
            text=self.app_name,
            font=(FONT_FAMILY, 16, "bold")
        )
        name_label.pack(pady=(0, 5))
        
        # Wersja
        version_label = ttk.Label(
            main_frame,
            text=f"Wersja {self.version}",
            font=(FONT_FAMILY, 10)
        )
        version_label.pack(pady=(0, 10))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Opis
        desc_label = ttk.Label(
            main_frame,
            text=self.description,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            wraplength=400,
            justify="center"
        )
        desc_label.pack(pady=10)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Autor
        author_label = ttk.Label(
            main_frame,
            text=f"Autor: {self.author}",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL)
        )
        author_label.pack(pady=(10, 20))
        
        # Przycisk OK
        ttk.Button(
            main_frame,
            text="OK",
            command=self.on_ok,
            width=15
        ).pack()


class AddGameDialog(BaseDialog):
    """
    Okno dialogowe do dodawania gry.
    """
    
    def __init__(self, parent):
        """
        Inicjalizuje okno dodawania gry.
        
        Args:
            parent: Okno rodzica
        """
        super().__init__(parent, "Dodaj grę", width=500, height=400)
        self._create_ui()
    
    def _create_ui(self):
        """Tworzy interfejs dialogu."""
        # Ramka główna
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Nazwa gry
        ttk.Label(main_frame, text="Nazwa gry:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        self.name_entry.focus()
        
        # Ścieżka do pliku exe
        ttk.Label(main_frame, text="Plik .exe:").grid(row=1, column=0, sticky="w", pady=5)
        
        exe_frame = ttk.Frame(main_frame)
        exe_frame.grid(row=1, column=1, pady=5, padx=(10, 0), sticky="ew")
        
        self.exe_entry = ttk.Entry(exe_frame)
        self.exe_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            exe_frame,
            text="...",
            command=self._browse_exe,
            width=3
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Katalog roboczy
        ttk.Label(main_frame, text="Katalog roboczy:").grid(row=2, column=0, sticky="w", pady=5)
        
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=2, column=1, pady=5, padx=(10, 0), sticky="ew")
        
        self.dir_entry = ttk.Entry(dir_frame)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            dir_frame,
            text="...",
            command=self._browse_dir,
            width=3
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Argumenty
        ttk.Label(main_frame, text="Argumenty:").grid(row=3, column=0, sticky="w", pady=5)
        self.args_entry = ttk.Entry(main_frame, width=40)
        self.args_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
        
        # Konfiguracja kolumn
        main_frame.columnconfigure(1, weight=1)
        
        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Przyciski
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Dodaj",
            command=self.on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Anuluj",
            command=self.on_cancel,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _browse_exe(self):
        """Otwiera dialog wyboru pliku exe."""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            parent=self,
            title="Wybierz plik wykonywalny",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")]
        )
        if filename:
            self.exe_entry.delete(0, tk.END)
            self.exe_entry.insert(0, filename)
    
    def _browse_dir(self):
        """Otwiera dialog wyboru katalogu."""
        from tkinter import filedialog
        dirname = filedialog.askdirectory(
            parent=self,
            title="Wybierz katalog roboczy"
        )
        if dirname:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, dirname)
    
    def on_ok(self):
        """Obsługa przycisku Dodaj."""
        name = self.name_entry.get().strip()
        exe_path = self.exe_entry.get().strip()
        
        if not name:
            messagebox.showerror("Błąd", "Podaj nazwę gry", parent=self)
            return
        
        if not exe_path:
            messagebox.showerror("Błąd", "Podaj ścieżkę do pliku .exe", parent=self)
            return
        
        # Przygotuj wynik
        self.result = {
            'name': name,
            'exe_path': exe_path,
            'working_dir': self.dir_entry.get().strip(),
            'arguments': self.args_entry.get().strip()
        }
        
        self.destroy()


class EditGameDialog(AddGameDialog):
    """
    Okno dialogowe do edycji gry (rozszerza AddGameDialog).
    """
    
    def __init__(self, parent, game_data: Dict[str, Any]):
        """
        Inicjalizuje okno edycji gry.
        
        Args:
            parent: Okno rodzica
            game_data: Słownik z danymi gry
        """
        self.game_data = game_data
        super().__init__(parent)
        self.title("Edytuj grę")
        
        # Wypełnij pola danymi
        self.name_entry.insert(0, game_data.get('name', ''))
        self.exe_entry.insert(0, game_data.get('exe_path', ''))
        self.dir_entry.insert(0, game_data.get('working_dir', ''))
        self.args_entry.insert(0, game_data.get('arguments', ''))


class SettingsDialog(BaseDialog):
    """
    Okno dialogowe ustawień (placeholder - do rozbudowy).
    """
    
    def __init__(self, parent, settings):
        """
        Inicjalizuje okno ustawień.
        
        Args:
            parent: Okno rodzica
            settings: Instancja Settings
        """
        super().__init__(parent, "Ustawienia", width=600, height=500)
        self.settings = settings
        self._create_ui()
    
    def _create_ui(self):
        """Tworzy interfejs dialogu."""
        # TODO: Implementacja pełnego okna ustawień
        # Na razie placeholder
        
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        info_label = ttk.Label(
            main_frame,
            text="Okno ustawień\n\nTODO: Dodać zakładki z ustawieniami:\n"
                 "- Wygląd\n- Muzyka\n- Discord\n- Gamepad\n- Sieć\n- Zaawansowane",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            justify="center"
        )
        info_label.pack(expand=True)
        
        # Przycisk OK
        ttk.Button(
            main_frame,
            text="OK",
            command=self.on_ok,
            width=15
        ).pack(pady=10)
