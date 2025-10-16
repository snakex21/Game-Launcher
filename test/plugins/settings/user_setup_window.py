# plugins/settings/user_setup_window.py
import customtkinter as ctk

class UserSetupWindow(ctk.CTkToplevel):
    def __init__(self, parent, app_context, on_save_callback):
        super().__init__(parent)
        self.app_context = app_context
        self.on_save_callback = on_save_callback

        self.title("Witaj w Game-Launcher!")
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close) # Zablokuj zamknięcie krzyżykiem

        ctk.CTkLabel(self, text="Wygląda na to, że jesteś tu pierwszy raz!", font=("Roboto", 16)).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Podaj swoją nazwę użytkownika:").pack()
        
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Twój nick...")
        self.name_entry.pack(pady=10, padx=20, fill="x")

        ctk.CTkButton(self, text="Zapisz i kontynuuj", command=self._save_and_close).pack(pady=10)

    def _save_and_close(self):
        username = self.name_entry.get()
        if not username:
            return # Nie pozwól na pustą nazwę

        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        settings_data["username"] = username
        self.app_context.data_manager.save_plugin_data("settings", settings_data)
        
        if self.on_save_callback:
            self.on_save_callback()
            
        self.destroy()

    def _on_close(self):
        # Ignoruj próby zamknięcia okna bez zapisu
        pass