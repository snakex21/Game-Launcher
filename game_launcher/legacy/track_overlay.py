"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class TrackOverlayWindow(tk.Toplevel):
    def __init__(self, parent, initial_x=None, initial_y=None, launcher_instance=None): # Dodajemy launcher_instance
        super().__init__(parent)
        self.parent = parent
        # --- NOWE: Referencja do launchera dla zapisu pozycji ---
        self.launcher = launcher_instance 
        # --- KONIEC NOWEGO ---

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        
        self.transparent_color = 'lime green'
        try:
            self.attributes("-transparentcolor", self.transparent_color)
            self.configure(bg=self.transparent_color)
        except tk.TclError:
            fallback_bg = "#212121" # Ciemniejsze tło, jeśli przezroczystość nie działa
            self.configure(bg=fallback_bg)
            self.transparent_color = fallback_bg

        self.width = 300
        self.height = 70

        # Domyślne wartości pozycji, jeśli nie ma zapisanych
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        default_x = screen_w - self.width - 20
        default_y = screen_h - self.height - 60 

        # --- ZMIANA: Upewnij się, że x_pos i y_pos są liczbami ---
        temp_x = initial_x # Używamy przekazanych argumentów
        temp_y = initial_y

        if temp_x is None: # Jeśli z local_settings przyszło None (lub nie było initial_x)
            temp_x = default_x
        if temp_y is None:
            temp_y = default_y
            
        self.x_pos = int(temp_x) # Teraz konwersja na int jest bezpieczniejsza
        self.y_pos = int(temp_y)
        # --- KONIEC ZMIANY ---
        
        self.geometry(f"{self.width}x{self.height}+{int(self.x_pos)}+{int(self.y_pos)}") # Upewnij się, że pozycje są int

        # --- Wewnętrzna ramka, do której przypniemy bindowania przesuwania ---
        self.drag_frame = ttk.Frame(self, style="Overlay.TFrame") # Użyjmy dedykowanego stylu
        self.drag_frame.pack(fill=tk.BOTH, expand=True)
        # Styl dla ramki (tło takie samo jak "przezroczysty" kolor okna)
        s = ttk.Style()
        s.configure("Overlay.TFrame", background=self.transparent_color)

        # --- NOWE ZMIANY: Użycie grid() zamiast pack() ---
        # Konfiguracja siatki dla drag_frame
        self.drag_frame.columnconfigure(0, weight=1) # Wszystkie elementy w jednej kolumnie, rozciągliwe na szerokość
        
        # Wiersz 0: Nazwa utworu - może zająć dostępną przestrzeń, ale nie za dużo
        self.drag_frame.rowconfigure(0, weight=0) # Nie pozwól tej etykiecie zbytnio rosnąć
        # Wiersz 1: Pasek postępu - stała wysokość
        self.drag_frame.rowconfigure(1, weight=0)
        # Wiersz 2: Czas - stała wysokość, na samym dole
        self.drag_frame.rowconfigure(2, weight=0)


        self.track_name_label = ttk.Label(self.drag_frame, text="Nic nie gra...", 
                                          font=("Segoe UI", 9, "bold"), 
                                          wraplength=self.width - 15, # Zostaw trochę więcej marginesu
                                          justify="left", # Wyrównaj do lewej
                                          anchor="nw",    # Zakotwicz w lewym górnym rogu komórki
                                          style="Overlay.TLabel")
        # Użyj justify="left" i anchor="nw"
        self.track_name_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(3,0)) # Mniejszy pady

        self.progress_bar = ttk.Progressbar(self.drag_frame, orient="horizontal", length=self.width - 10, mode="determinate")
        s.configure("Overlay.Horizontal.TProgressbar", troughcolor='#404040', background='#C0C0C0', thickness=4, borderwidth=0) # Cieńszy pasek
        self.progress_bar.config(style="Overlay.Horizontal.TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(1,1))

        self.time_label = ttk.Label(self.drag_frame, text="0:00 / 0:00", 
                                    font=("Segoe UI", 8), 
                                    anchor="e", # Wyrównaj do prawej
                                    style="Overlay.TLabel")
        self.time_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(0,3)) # Mniejszy pady
        # --- KONIEC NOWYCH ZMIAN ---

        # Styl dla etykiet (już powinien być)
        s.configure("Overlay.TLabel", background=self.transparent_color, foreground="#E0E0E0")


        # --- Logika przesuwania okna ---
        self._offset_x = 0
        self._offset_y = 0
        # Bindowanie do ramki wewnętrznej, aby cała powierzchnia była chwytalna
        self.drag_frame.bind("<ButtonPress-1>", self._on_overlay_press)
        self.drag_frame.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.drag_frame.bind("<B1-Motion>", self._on_overlay_motion)
        # Bindowanie również do etykiet i paska, aby one też były "chwytalne"
        self.track_name_label.bind("<ButtonPress-1>", self._on_overlay_press)
        self.track_name_label.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.track_name_label.bind("<B1-Motion>", self._on_overlay_motion)
        self.time_label.bind("<ButtonPress-1>", self._on_overlay_press)
        self.time_label.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.time_label.bind("<B1-Motion>", self._on_overlay_motion)
        # Pasek postępu nie powinien być bezpośrednio chwytalny, aby nie kolidować z ewentualną interakcją
        
        self.withdraw()

    def _on_overlay_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_overlay_release(self, event):
        # Zapisz nową pozycję
        self.x_pos = self.winfo_x()
        self.y_pos = self.winfo_y()
        if self.launcher and hasattr(self.launcher, 'local_settings'):
            self.launcher.local_settings["overlay_x_pos"] = self.x_pos
            self.launcher.local_settings["overlay_y_pos"] = self.y_pos
            save_local_settings(self.launcher.local_settings) # Zapisz do pliku
            logging.debug(f"Overlay: Zapisano nową pozycję: x={self.x_pos}, y={self.y_pos}")

    def _on_overlay_motion(self, event):
        new_x = self.winfo_x() + (event.x - self._offset_x)
        new_y = self.winfo_y() + (event.y - self._offset_y)
        self.geometry(f"+{int(new_x)}+{int(new_y)}") # Upewnij się, że są int

    def update_display(self, track_name: str | None, current_time_sec: float, total_time_sec: float, is_active: bool):
        if not self.winfo_exists(): return

        current_time_sec = max(0, current_time_sec)
        total_time_sec = max(0, total_time_sec)

        if track_name:
            self.track_name_label.config(text=track_name[:60])
        else:
            self.track_name_label.config(text="Nic nie gra...")

        # --- ZMIANY W OBSŁUDZE PROGRESSBARA ---
        if is_active and total_time_sec > 0: # Utwór gra lub jest spauzowany, znamy długość
            if self.progress_bar['mode'] == 'indeterminate':
                self.progress_bar.stop() # Zatrzymaj animację indeterminate, jeśli była
            self.progress_bar.config(mode='determinate') # Upewnij się, że jest determinate
            self.progress_bar['maximum'] = total_time_sec
            self.progress_bar['value'] = min(current_time_sec, total_time_sec)
            
            current_m, current_s = divmod(int(current_time_sec), 60)
            total_m, total_s = divmod(int(total_time_sec), 60)
            self.time_label.config(text=f"{current_m:02d}:{current_s:02d} / {total_m:02d}:{total_s:02d}")

        elif is_active and total_time_sec == 0: # Utwór gra/pauza, ale długość nieznana (np. strumień)
            if self.progress_bar['mode'] != 'indeterminate':
                self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(15) # Uruchom animację (15ms interwał)
            self.time_label.config(text="??:?? / ??:??") # lub "Strumień..."

        else: # Nie jest aktywny (zatrzymany lub nic nie wybrano)
            if self.progress_bar['mode'] == 'indeterminate':
                self.progress_bar.stop() # Zatrzymaj animację, jeśli była
            self.progress_bar.config(mode='determinate') # Wróć do determinate
            self.progress_bar['maximum'] = 1 
            self.progress_bar['value'] = 0
            self.time_label.config(text="00:00 / 00:00")
        # --- KONIEC ZMIAN ---
        
    def show_overlay(self):
        if not self.winfo_exists(): # Jeśli okno zostało zniszczone, stwórz je na nowo (prostsze niż sprawdzanie)
            # Ta logika wymagałaby przekazania self.parent (root GameLaunchera)
            # i potencjalnie ponownego stworzenia instancji w GameLauncher.
            # Na razie zakładamy, że jeśli jest, to je pokazujemy.
            logging.warning("Próba pokazania overlay'a, który nie istnieje.")
            return 
        self.geometry(f"{self.width}x{self.height}+{self.x_pos}+{self.y_pos}") # Przywróć pozycję
        self.deiconify()
        self.lift() # Upewnij się, że jest na wierzchu

    def hide_overlay(self):
        if self.winfo_exists():
            self.withdraw()
