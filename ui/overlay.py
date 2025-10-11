"""
Okno overlay odtwarzacza muzyki
Floating overlay pokazujące aktualnie odtwarzany utwór.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional

from config.constants import OVERLAY_WIDTH, OVERLAY_HEIGHT, FONT_FAMILY

logger = logging.getLogger(__name__)


class TrackOverlayWindow(tk.Toplevel):
    """
    Okno overlay wyświetlające informacje o aktualnie odtwarzanym utworze.
    Można je przeciągać myszką i pozycjonować w dowolnym miejscu ekranu.
    """
    
    def __init__(self, parent, initial_x: Optional[int] = None, 
                 initial_y: Optional[int] = None, launcher_instance=None):
        """
        Inicjalizuje okno overlay.
        
        Args:
            parent: Rodzic okna (główne okno aplikacji)
            initial_x: Początkowa pozycja X (None = auto)
            initial_y: Początkowa pozycja Y (None = auto)
            launcher_instance: Referencja do głównej instancji launchera
        """
        super().__init__(parent)
        self.parent = parent
        self.launcher = launcher_instance
        
        # Konfiguracja okna
        self.overrideredirect(True)  # Usuń ramkę okna
        self.wm_attributes("-topmost", True)  # Zawsze na wierzchu
        
        # Przezroczystość tła
        self.transparent_color = 'lime green'
        try:
            self.attributes("-transparentcolor", self.transparent_color)
            self.configure(bg=self.transparent_color)
        except tk.TclError:
            # Fallback jeśli przezroczystość nie działa
            fallback_bg = "#212121"
            self.configure(bg=fallback_bg)
            self.transparent_color = fallback_bg
        
        # Wymiary okna
        self.width = OVERLAY_WIDTH
        self.height = OVERLAY_HEIGHT
        
        # Pozycja okna
        self._setup_position(initial_x, initial_y)
        
        # Zmienne do przeciągania
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False
        
        # Utworzenie UI
        self._create_ui()
        
        # Bindowania dla przeciągania
        self._setup_drag_bindings()
        
        logger.debug("TrackOverlayWindow zainicjalizowane")
    
    def _setup_position(self, initial_x: Optional[int], initial_y: Optional[int]):
        """Ustawia pozycję okna."""
        # Domyślne wartości - prawy dolny róg
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        default_x = screen_w - self.width - 20
        default_y = screen_h - self.height - 60
        
        # Użyj przekazanych wartości lub domyślnych
        self.x_pos = int(initial_x) if initial_x is not None else default_x
        self.y_pos = int(initial_y) if initial_y is not None else default_y
        
        # Ustaw geometrię
        self.geometry(f"{self.width}x{self.height}+{self.x_pos}+{self.y_pos}")
    
    def _create_ui(self):
        """Tworzy interfejs użytkownika overlay."""
        # Główna ramka
        self.drag_frame = ttk.Frame(self, style="Overlay.TFrame")
        self.drag_frame.pack(fill=tk.BOTH, expand=True)
        
        # Styl dla ramki
        style = ttk.Style()
        style.configure("Overlay.TFrame", background=self.transparent_color)
        
        # Konfiguracja siatki
        self.drag_frame.columnconfigure(0, weight=1)
        self.drag_frame.rowconfigure(0, weight=0)
        self.drag_frame.rowconfigure(1, weight=0)
        self.drag_frame.rowconfigure(2, weight=0)
        
        # Etykieta z nazwą utworu
        self.track_name_label = ttk.Label(
            self.drag_frame,
            text="Nic nie gra...",
            font=(FONT_FAMILY, 9, "bold"),
            wraplength=self.width - 15,
            justify="left",
            anchor="nw",
            style="Overlay.TLabel"
        )
        self.track_name_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(3, 0))
        
        # Pasek postępu
        self.progress_bar = ttk.Progressbar(
            self.drag_frame,
            orient="horizontal",
            length=self.width - 10,
            mode="determinate"
        )
        style.configure(
            "Overlay.Horizontal.TProgressbar",
            troughcolor='#404040',
            background='#C0C0C0',
            thickness=4,
            borderwidth=0
        )
        self.progress_bar.config(style="Overlay.Horizontal.TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(1, 1))
        
        # Etykieta z czasem
        self.time_label = ttk.Label(
            self.drag_frame,
            text="0:00 / 0:00",
            font=(FONT_FAMILY, 8),
            justify="left",
            anchor="w",
            style="Overlay.TLabel"
        )
        self.time_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 3))
        
        # Styl dla etykiet
        style.configure(
            "Overlay.TLabel",
            background=self.transparent_color,
            foreground="white"
        )
    
    def _setup_drag_bindings(self):
        """Konfiguruje bindowania do przeciągania okna."""
        # Binduj tylko do drag_frame, nie do całego okna
        self.drag_frame.bind("<Button-1>", self._start_drag)
        self.drag_frame.bind("<B1-Motion>", self._on_drag)
        self.drag_frame.bind("<ButtonRelease-1>", self._stop_drag)
        
        # Również binduj do etykiet
        for widget in [self.track_name_label, self.time_label]:
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)
    
    def _start_drag(self, event):
        """Rozpoczyna przeciąganie okna."""
        self._is_dragging = True
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self.config(cursor="fleur")  # Kursor przeciągania
    
    def _on_drag(self, event):
        """Obsługuje przeciąganie okna."""
        if self._is_dragging:
            # Oblicz przesunięcie
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            
            # Nowa pozycja
            new_x = self.x_pos + dx
            new_y = self.y_pos + dy
            
            # Ustaw nową pozycję
            self.geometry(f"+{new_x}+{new_y}")
            
            # Aktualizuj pozycję startową
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self.x_pos = new_x
            self.y_pos = new_y
    
    def _stop_drag(self, event):
        """Kończy przeciąganie okna."""
        self._is_dragging = False
        self.config(cursor="")  # Przywróć domyślny kursor
        
        # Zapisz pozycję w launcherze
        if self.launcher:
            try:
                self.launcher.settings.set("overlay.x", self.x_pos, auto_save=False)
                self.launcher.settings.set("overlay.y", self.y_pos, auto_save=True)
                logger.debug(f"Zapisano pozycję overlay: ({self.x_pos}, {self.y_pos})")
            except Exception as e:
                logger.error(f"Błąd zapisywania pozycji overlay: {e}")
    
    def update_track_info(self, track_name: str, current_time: int = 0, 
                         total_time: int = 0):
        """
        Aktualizuje informacje o utworze w overlay.
        
        Args:
            track_name: Nazwa utworu
            current_time: Aktualny czas w sekundach
            total_time: Całkowity czas w sekundach
        """
        try:
            # Aktualizuj nazwę utworu
            self.track_name_label.config(text=track_name)
            
            # Aktualizuj pasek postępu
            if total_time > 0:
                progress_percent = (current_time / total_time) * 100
                self.progress_bar['value'] = progress_percent
            else:
                self.progress_bar['value'] = 0
            
            # Aktualizuj czas
            current_str = self._format_time(current_time)
            total_str = self._format_time(total_time)
            self.time_label.config(text=f"{current_str} / {total_str}")
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji overlay: {e}")
    
    def _format_time(self, seconds: int) -> str:
        """
        Formatuje czas w sekundach do postaci MM:SS.
        
        Args:
            seconds: Czas w sekundach
            
        Returns:
            Sformatowany string (np. "3:45")
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    def show_overlay(self):
        """Pokazuje overlay."""
        try:
            self.deiconify()
            self.lift()
            logger.debug("Overlay pokazane")
        except Exception as e:
            logger.error(f"Błąd pokazywania overlay: {e}")
    
    def hide_overlay(self):
        """Ukrywa overlay."""
        try:
            self.withdraw()
            logger.debug("Overlay ukryte")
        except Exception as e:
            logger.error(f"Błąd ukrywania overlay: {e}")
    
    def toggle_overlay(self):
        """Przełącza widoczność overlay."""
        try:
            if self.state() == 'withdrawn':
                self.show_overlay()
            else:
                self.hide_overlay()
        except Exception as e:
            logger.error(f"Błąd przełączania overlay: {e}")
    
    def destroy(self):
        """Niszczy okno overlay."""
        try:
            # Zapisz pozycję przed zamknięciem
            if self.launcher:
                self.launcher.settings.set("overlay.x", self.x_pos, auto_save=False)
                self.launcher.settings.set("overlay.y", self.y_pos, auto_save=True)
            
            super().destroy()
            logger.debug("Overlay zniszczone")
        except Exception as e:
            logger.error(f"Błąd niszczenia overlay: {e}")
