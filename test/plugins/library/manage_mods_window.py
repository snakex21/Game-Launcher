# plugins/library/manage_mods_window.py
import customtkinter as ctk
from tkinter import filedialog
from .mod_handler import ModHandler

class ManageModsWindow(ctk.CTkToplevel):
    def __init__(self, parent, app_context, game_data):
        super().__init__(parent)
        self.app_context = app_context
        self.game_data = game_data
        self.mod_handler = ModHandler()

        self.title(f"Mody dla: {self.game_data.get('name')}")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self.refresh_mod_list()

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(top_frame, text="Dodaj mod (z folderu)...", command=self.add_mod).pack(side="left")
        ctk.CTkButton(top_frame, text="Odśwież listę", command=self.refresh_mod_list).pack(side="left", padx=10)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Zainstalowane mody")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh_mod_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        mods = self.mod_handler.discover_mods(self.game_data.get("path"))
        
        if not mods:
            ctk.CTkLabel(self.scrollable_frame, text="Nie znaleziono modów w folderze `_mods`.").pack(pady=20)
            return

        for mod in mods:
            mod_frame = ctk.CTkFrame(self.scrollable_frame)
            mod_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(mod_frame, text=mod.get("name")).pack(side="left", padx=10)
            
            ctk.CTkButton(mod_frame, text="Usuń", width=80, fg_color="red", hover_color="darkred", command=lambda m=mod: self.remove_mod(m)).pack(side="right", padx=10)

            switch_var = ctk.StringVar(value="on" if mod.get("is_active") else "off")
            switch = ctk.CTkSwitch(mod_frame, text="Aktywny", variable=switch_var, onvalue="on", offvalue="off",
                                   command=lambda m=mod, sv=switch_var: self.toggle_mod_status(m, sv))
            switch.pack(side="right", padx=10)

    def toggle_mod_status(self, mod, switch_var):
        is_active_now = switch_var.get() == "on"
        self.mod_handler.set_mod_status(mod.get("path"), activate=is_active_now)
        # Nie ma potrzeby odświeżania całej listy, bo switch sam się aktualizuje, a nazwa pliku zmienia się w tle

    def add_mod(self):
        source_path = filedialog.askdirectory(title="Wybierz folder z modem do dodania")
        if not source_path:
            return
        
        success, message = self.mod_handler.add_mod(self.game_data.get("path"), source_path)
        # Można by tu dodać okienko z informacją dla użytkownika
        print(message)
        if success:
            self.refresh_mod_list()

    def remove_mod(self, mod):
        if self.mod_handler.remove_mod(mod.get("path")):
            self.refresh_mod_list()