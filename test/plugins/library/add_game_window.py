# plugins/library/add_game_window.py
import customtkinter as ctk
from tkinter import filedialog
import os

class AddGameWindow(ctk.CTkToplevel):
    def __init__(self, parent, app_context, on_success_callback):
        super().__init__(parent)
        self.app_context = app_context
        self.on_success_callback = on_success_callback
        self.emulators_map = {}

        self.title("Dodaj nową grę")
        self.geometry("600x550")
        self.transient(parent)
        self.grab_set()

        # --- NOWOŚĆ: Wybór typu gry ---
        ctk.CTkLabel(self, text="Typ gry:").pack(pady=(10, 0), padx=20, anchor="w")
        self.game_type_var = ctk.StringVar(value="PC")
        self.game_type_segmented = ctk.CTkSegmentedButton(self, values=["PC", "Emulator"], variable=self.game_type_var, command=self._on_type_change)
        self.game_type_segmented.pack(pady=5, padx=20, fill="x")

        # --- NOWOŚĆ: Kontener na pola emulatora (początkowo ukryty) ---
        self.emulator_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.emulator_frame, text="Wybierz Emulator:").pack(anchor="w", padx=20)
        self.emulator_selector = ctk.CTkOptionMenu(self.emulator_frame, values=["Ładowanie..."])
        self.emulator_selector.pack(pady=5, padx=20, fill="x")

        # --- Reszta formularza ---
        ctk.CTkLabel(self, text="Nazwa gry:").pack(pady=(10, 0), padx=20, anchor="w")
        self.name_entry = ctk.CTkEntry(self, placeholder_text="np. Wiedźmin 3: Dziki Gon")
        self.name_entry.pack(pady=5, padx=20, fill="x")

        self.path_label = ctk.CTkLabel(self, text="Ścieżka do pliku wykonywalnego (.exe):")
        self.path_label.pack(pady=(10, 0), padx=20, anchor="w")
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.pack(pady=5, padx=20, fill="x")
        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Wybierz plik...")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.browse_button = ctk.CTkButton(path_frame, text="Przeglądaj...", width=100, command=self.browse_executable)
        self.browse_button.pack(side="left")

        ctk.CTkLabel(self, text="Okładka gry (opcjonalnie):").pack(pady=(10, 0), padx=20, anchor="w")
        cover_frame = ctk.CTkFrame(self, fg_color="transparent")
        cover_frame.pack(pady=5, padx=20, fill="x")
        self.cover_entry = ctk.CTkEntry(cover_frame, placeholder_text="Wybierz plik obrazu...")
        self.cover_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(cover_frame, text="Przeglądaj...", width=100, command=self.browse_cover).pack(side="left")
        
        ctk.CTkLabel(self, text="Folder ze zrzutami ekranu (opcjonalnie):").pack(pady=(10, 0), padx=20, anchor="w")
        screenshot_frame = ctk.CTkFrame(self, fg_color="transparent")
        screenshot_frame.pack(pady=5, padx=20, fill="x")
        self.screenshot_entry = ctk.CTkEntry(screenshot_frame, placeholder_text="Wybierz folder...")
        self.screenshot_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(screenshot_frame, text="Przeglądaj...", width=100, command=self.browse_screenshot_dir).pack(side="left")

        # Przyciski
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=20, padx=20)
        ctk.CTkButton(button_frame, text="Zapisz", command=self.save_game).pack(side="right")
        ctk.CTkButton(button_frame, text="Anuluj", command=self.destroy, fg_color="gray").pack(side="right", padx=(0, 10))

    def _on_type_change(self, value):
        """Zmienia wygląd formularza w zależności od wybranego typu gry."""
        if value == "Emulator":
            self._populate_emulators()
            # Użyj .pack() z opcją 'before', aby umieścić ramkę w odpowiednim miejscu
            self.emulator_frame.pack(pady=5, padx=0, fill="x", before=self.name_entry.master.master)
            self.path_label.configure(text="Ścieżka do pliku gry (ROM):")
        else: # PC
            self.emulator_frame.pack_forget()
            self.path_label.configure(text="Ścieżka do pliku wykonywalnego (.exe):")
            
    def _populate_emulators(self):
        """Wypełnia listę rozwijaną dostępnymi emulatorami."""
        emu_data = self.app_context.data_manager.get_plugin_data("emulators")
        emulators = emu_data.get("emulators_list", [])
        self.emulators_map = {emu['name']: emu['id'] for emu in emulators}
        emu_names = list(self.emulators_map.keys())
        if emu_names:
            self.emulator_selector.configure(values=emu_names)
            self.emulator_selector.set(emu_names[0])
        else:
            self.emulator_selector.configure(values=["Brak emulatorów!"])
            self.emulator_selector.set("Brak emulatorów!")

    def browse_executable(self):
        """Otwiera okno wyboru pliku w zależności od typu gry."""
        if self.game_type_var.get() == "PC":
            filepath = filedialog.askopenfilename(title="Wybierz plik wykonywalny", filetypes=(("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")))
        else: # Emulator
            filepath = filedialog.askopenfilename(title="Wybierz plik gry (ROM)")
        
        if filepath:
            self.path_entry.delete(0, "end"); self.path_entry.insert(0, filepath)
            if not self.name_entry.get():
                game_name = os.path.splitext(os.path.basename(filepath))[0]
                self.name_entry.insert(0, game_name)

    def browse_cover(self):
        filepath = filedialog.askopenfilename(title="Wybierz okładkę", filetypes=(("Obrazy", "*.png *.jpg *.jpeg *.gif *.webp"), ("Wszystkie pliki", "*.*")))
        if filepath:
            self.cover_entry.delete(0, "end"); self.cover_entry.insert(0, filepath)

    def browse_screenshot_dir(self):
        dirpath = filedialog.askdirectory(title="Wybierz folder ze zrzutami ekranu")
        if dirpath:
            self.screenshot_entry.delete(0, "end"); self.screenshot_entry.insert(0, dirpath)

    def save_game(self):
        game_name = self.name_entry.get()
        game_path = self.path_entry.get()
        if not game_name or not game_path: return

        library_data = self.app_context.data_manager.get_plugin_data('library')
        games_list = library_data.get('games', [])
        
        all_ids = [int(g.get('id', 0)) for g in games_list]
        new_id = max(all_ids) + 1 if all_ids else 1
        
        game_type = self.game_type_var.get()

        new_game_data = {
            "id": str(new_id),
            "name": game_name,
            "path": game_path,
            "cover_image_path": self.cover_entry.get(),
            "screenshot_folder": self.screenshot_entry.get(),
            "rawg_id": None,
            "total_playtime_seconds": 0,
            "completion_percent": 0,
            "launch_type": game_type
        }

        if game_type == "Emulator":
            selected_emu_name = self.emulator_selector.get()
            if selected_emu_name in self.emulators_map:
                new_game_data["emulator_id"] = self.emulators_map[selected_emu_name]
            else:
                print("Błąd: Wybrany emulator nie został znaleziony.")
                return # Nie zapisuj, jeśli emulator jest nieprawidłowy
        
        games_list.append(new_game_data)
        library_data['games'] = games_list
        self.app_context.data_manager.save_plugin_data('library', library_data)
        
        self.on_success_callback()
        self.destroy()