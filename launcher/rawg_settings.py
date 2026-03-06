from tkinter import messagebox

from launcher.config_store import save_local_settings


def toggle_show_key(self, entry_widget, show_var):
    """Przełącza widoczność hasła/klucza w danym polu Entry."""
    if show_var.get():
        entry_widget.config(show="")
    else:
        entry_widget.config(show="*")


def save_rawg_api_key(self):
    """Zapisuje klucz API RAWG do ustawień lokalnych."""
    key = self.rawg_api_key_entry.get().strip()
    if key:
        self.local_settings["rawg_api_key"] = key
        save_local_settings(self.local_settings)
        messagebox.showinfo("Sukces", "Klucz API RAWG został zapisany.")
    else:
        if "rawg_api_key" in self.local_settings:
            del self.local_settings["rawg_api_key"]
            save_local_settings(self.local_settings)
            messagebox.showinfo("Usunięto", "Klucz API RAWG został usunięty.")
        else:
            messagebox.showwarning("Brak klucza", "Pole klucza API RAWG jest puste.")


def show_rawg_key_help(self):
    """Wyświetla pomoc dotyczącą klucza RAWG API."""
    message = (
        "Jak uzyskać klucz RAWG API:\n\n"
        "1. Zarejestruj się lub zaloguj na stronie: https://rawg.io/\n"
        "2. Przejdź do strony swojego profilu (kliknij na awatar).\n"
        "3. W sekcji 'API key' znajdziesz swój klucz.\n"
        "4. Skopiuj klucz i wklej go w polu powyżej.\n\n"
        "Klucz API jest wymagany do pobierania szczegółowych informacji o grach."
    )
    parent_window = self.settings_page_frame if hasattr(self, "settings_page_frame") else self.root
    messagebox.showinfo("Pomoc - Klucz RAWG API", message, parent=parent_window)


__all__ = ["toggle_show_key", "save_rawg_api_key", "show_rawg_key_help"]
