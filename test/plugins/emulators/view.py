# plugins/emulators/view.py
import customtkinter as ctk
from tkinter import filedialog
import uuid

class EmulatorsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self._setup_ui()

    def refresh_view(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        data = self.app_context.data_manager.get_plugin_data("emulators")
        emulators = data.get("emulators_list", [])

        if not emulators:
            ctk.CTkLabel(self.scrollable_frame, text="Brak dodanych emulatorów.").pack(pady=20)
        
        for emu in emulators:
            frame = ctk.CTkFrame(self.scrollable_frame)
            frame.pack(fill="x", pady=5)
            label = f"{emu.get('name')}\n{emu.get('path')}"
            ctk.CTkLabel(frame, text=label, justify="left").pack(side="left", padx=10, pady=5, fill="x", expand=True)
            ctk.CTkButton(frame, text="Usuń", width=80, fg_color="red", hover_color="darkred",
                          command=lambda e_id=emu.get("id"): self.delete_emulator(e_id)).pack(side="right", padx=10)

    def _setup_ui(self):
        add_frame = ctk.CTkFrame(self); add_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(add_frame, text="Nazwa Emulatora:").pack(anchor="w", padx=10, pady=(5,0))
        self.name_entry = ctk.CTkEntry(add_frame, placeholder_text="np. PCSX2"); self.name_entry.pack(fill="x", padx=10, pady=(0,5))
        
        ctk.CTkLabel(add_frame, text="Ścieżka do pliku .exe:").pack(anchor="w", padx=10, pady=(5,0))
        path_frame = ctk.CTkFrame(add_frame, fg_color="transparent"); path_frame.pack(fill="x", padx=10, pady=(0,5))
        self.path_entry = ctk.CTkEntry(path_frame); self.path_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(path_frame, text="Przeglądaj...", command=self.browse_exe).pack(side="left")

        ctk.CTkButton(add_frame, text="Dodaj Emulator", command=self.add_emulator).pack(pady=10)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Zapisane Emulatory")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def browse_exe(self):
        filepath = filedialog.askopenfilename(filetypes=[("Pliki wykonywalne", "*.exe")])
        if filepath: self.path_entry.delete(0, 'end'); self.path_entry.insert(0, filepath)

    def add_emulator(self):
        name = self.name_entry.get(); path = self.path_entry.get()
        if not all([name, path]): return

        new_emu = {"id": str(uuid.uuid4()), "name": name, "path": path}
        
        data = self.app_context.data_manager.get_plugin_data("emulators")
        data.setdefault("emulators_list", []).append(new_emu)
        self.app_context.data_manager.save_plugin_data("emulators", data)
        self.refresh_view()
        self.name_entry.delete(0, 'end'); self.path_entry.delete(0, 'end')

    def delete_emulator(self, emu_id):
        data = self.app_context.data_manager.get_plugin_data("emulators")
        emulators = data.get("emulators_list", [])
        data["emulators_list"] = [e for e in emulators if e.get("id") != emu_id]
        self.app_context.data_manager.save_plugin_data("emulators", data)
        self.refresh_view()