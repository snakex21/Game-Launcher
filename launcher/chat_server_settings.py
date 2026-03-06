import logging
import tkinter as tk
from tkinter import messagebox, ttk

from launcher.config_store import save_local_settings


def _open_chat_server_settings_dialog(self):
    """Otwiera okno dialogowe do edycji URL serwera czatu."""
    dialog = tk.Toplevel(self.chat_page_frame)  # Rodzicem jest strona czatu
    dialog.title("Ustawienia Serwera Czatu")
    dialog.configure(bg=self.settings.get("background", "#1e1e1e"))
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.transient(self.chat_page_frame)

    # Wyśrodkuj dialog względem chat_page_frame
    self.chat_page_frame.update_idletasks()
    parent_x = self.chat_page_frame.winfo_rootx()
    parent_y = self.chat_page_frame.winfo_rooty()
    parent_w = self.chat_page_frame.winfo_width()
    parent_h = self.chat_page_frame.winfo_height()

    dialog_w = 450  # Szerokość okna dialogowego
    dialog_h = 150  # Wysokość okna dialogowego

    pos_x = parent_x + (parent_w // 2) - (dialog_w // 2)
    pos_y = parent_y + (parent_h // 2) - (dialog_h // 2)
    dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")

    # Zawartość dialogu
    content_frame = ttk.Frame(dialog, padding=15)
    content_frame.pack(fill=tk.BOTH, expand=True)
    content_frame.columnconfigure(1, weight=1)

    ttk.Label(content_frame, text="Adres URL Serwera Czatu:").grid(
        row=0, column=0, padx=5, pady=10, sticky="w"
    )

    # Użyj tymczasowej zmiennej dla Entry w dialogu, aby nie modyfikować self.chat_server_url_var
    # jeśli nie zostanie zapisane.
    temp_url_var = tk.StringVar(
        value=self.local_settings.get("chat_server_url", "http://127.0.0.1:5000")
    )
    url_entry = ttk.Entry(content_frame, textvariable=temp_url_var, width=45)
    url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
    url_entry.focus_set()
    url_entry.selection_range(0, tk.END)  # Zaznacz cały tekst

    button_frame = ttk.Frame(content_frame)
    button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="e")

    def on_save():
        # Przypisz wartość z tymczasowej zmiennej do głównej zmiennej
        self.chat_server_url_var.set(temp_url_var.get())
        self._save_chat_server_url()  # Wywołaj istniejącą metodę zapisu
        dialog.destroy()

    ttk.Button(button_frame, text="Zapisz", command=on_save).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Anuluj", command=dialog.destroy).pack(side=tk.LEFT)


def _save_chat_server_url(self):
    """Zapisuje nowy URL serwera czatu i aktualizuje go w instancji."""
    new_url = self.chat_server_url_var.get().strip()
    if not new_url:
        messagebox.showwarning(
            "Brak URL",
            "Adres URL serwera czatu nie może być pusty.",
            parent=(self.settings_page_frame if hasattr(self, "settings_page_frame") else self.root),
        )
        self.chat_server_url_var.set(self.chat_server_url)
        return

    if not active_server_data:
        messagebox.showerror(
            "Błąd",
            "Brak aktywnego serwera do zaktualizowania URL.",
            parent=self.root,
        )
        return

    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        messagebox.showerror(
            "Nieprawidłowy URL",
            "Adres URL serwera czatu musi zaczynać się od http:// lub https://",
            parent=(self.settings_page_frame if hasattr(self, "settings_page_frame") else self.root),
        )
        self.chat_server_url_var.set(self.chat_server_url)
        return

    if self.local_settings.get("chat_server_url") != new_url:
        self.local_settings["chat_server_url"] = new_url
        save_local_settings(self.local_settings)
        self.chat_server_url = new_url

        logging.info(f"Zmieniono adres URL serwera czatu na: {new_url}")
        messagebox.showinfo(
            "Zapisano URL",
            f"Nowy adres serwera czatu ({new_url}) został zapisany.\n"
            "Jeśli byłeś połączony z czatem, rozłącz się i połącz ponownie, aby użyć nowego adresu.",
            parent=(self.settings_page_frame if hasattr(self, "settings_page_frame") else self.root),
        )

        if self.sio and self.sio.connected:
            self._chat_logout()
    else:
        messagebox.showinfo(
            "Informacja",
            "Adres URL serwera czatu nie został zmieniony.",
            parent=(self.settings_page_frame if hasattr(self, "settings_page_frame") else self.root),
        )


__all__ = ["_open_chat_server_settings_dialog", "_save_chat_server_url"]
