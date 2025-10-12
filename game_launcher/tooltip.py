from __future__ import annotations

from .shared_imports import *


class ToolTip:
    """Prosta klasa do tworzenia podpowiedzi (tooltip) dla widgetów Tkinter."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None # Zmieniona nazwa
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip) # Dodane, aby ukryć przy kliknięciu

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text: # Nie pokazuj, jeśli już jest lub brak tekstu
            return
        x, y, _, _ = self.widget.bbox("insert") # Może być problematyczne jeśli widget nie ma insert bbox
        try:
            # Bezpieczniejsze pobranie pozycji, jeśli bbox nie działa (np. dla ramek)
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5 # Trochę poniżej widgetu
        except: # Fallback do poprzedniej metody, jeśli winfo_width/height zawiedzie
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{int(x)}+{int(y)}") # Upewnij się, że x, y to int
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                      background="#ffffe0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None): # Usunięto argument event, aby można było wywołać bez niego
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

    def update_text(self, new_text):
        self.text = new_text
        # Ważne: Jeśli tooltip był widoczny, ukrywamy go.
        # Nowy tekst zostanie użyty, gdy <Enter> ponownie stworzy tooltip.
        if self.tooltip_window:
            self.hide_tooltip()
from .shared_imports import tk


