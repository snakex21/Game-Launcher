# main.py
import customtkinter as ctk
from core.app_context import AppContext
from core.plugin_manager import load_plugins
from ui.main_window import MainWindow

if __name__ == "__main__":
    app_context = AppContext()
    app_context.reminder_service.start()
    
    # --- POPRAWKA JEST TUTAJ ---
    # Najpierw bierzemy całą "szufladę" danych pluginu 'settings',
    # a potem z niej wyciągamy wartość 'theme'.
    settings_data = app_context.data_manager.get_plugin_data('settings')
    initial_theme = settings_data.get("last_used_theme", "System")
    initial_theme = settings_data.get('theme', 'dark')
    ctk.set_appearance_mode(initial_theme)
    # --- KONIEC POPRAWKI ---
    app_context.discord_service.start()
    plugins = load_plugins(app_context)

    app = MainWindow(app_context=app_context, plugins=plugins)
    
    app.mainloop()