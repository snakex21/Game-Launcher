# plugins/settings/theme_editor_window.py
import customtkinter as ctk
from tkinter import colorchooser

class ThemeEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent, app_context, on_save_callback):
        super().__init__(parent)
        self.app_context = app_context
        self.on_save_callback = on_save_callback
        
        # Słownik przechowuje kolory w formacie [light_mode_color, dark_mode_color]
        self.colors = {
            "fg_color": ["#dbdbdb", "#2b2b2b"],
            "button_color": ["#3B8ED0", "#1F6AA5"],
            "button_hover_color": ["#36719F", "#144870"],
            "text_color": ["#1A1A1A", "#DCE4EE"],
        }
        self.appearance_mode = "dark" # Domyślny tryb bazowy dla nowego motywu

        self.title("Edytor Motywów")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Lewa kolumna: Kontrolki
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(controls_frame, text="Ustawienia Motywu", font=("Roboto", 16, "bold")).pack(pady=(5, 15))
        
        self.create_color_picker(controls_frame, "Kolor Tła", "fg_color")
        self.create_color_picker(controls_frame, "Kolor Przycisku", "button_color")
        self.create_color_picker(controls_frame, "Kolor Przycisku (Hover)", "button_hover_color")
        self.create_color_picker(controls_frame, "Kolor Tekstu", "text_color")
        
        # Wybór trybu wyglądu (jasny/ciemny) dla motywu
        ctk.CTkLabel(controls_frame, text="Tryb bazowy motywu:").pack(pady=(20, 5))
        self.mode_selector = ctk.CTkSegmentedButton(controls_frame, values=["Dark", "Light"], command=self._set_appearance_mode)
        self.mode_selector.set("Dark")
        self.mode_selector.pack(pady=5)

        # Prawa kolumna: Podgląd
        self.preview_frame = ctk.CTkFrame(self, fg_color=self.colors['fg_color'][1]) # Start with dark mode color
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Podgląd na żywo", font=("Roboto", 16, "bold"), text_color=self.colors['text_color'][1])
        self.preview_label.pack(pady=10)
        
        self.preview_button = ctk.CTkButton(self.preview_frame, text="Przycisk", fg_color=self.colors['button_color'][1], hover_color=self.colors['button_hover_color'][1], text_color=self.colors['text_color'][1])
        self.preview_button.pack(pady=10)

        # Dolny panel: Zapis
        save_frame = ctk.CTkFrame(self)
        save_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        self.theme_name_entry = ctk.CTkEntry(save_frame, placeholder_text="Nazwa nowego motywu...")
        self.theme_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(save_frame, text="Zapisz Motyw", command=self._save_theme).pack(side="left")

    def create_color_picker(self, parent, label_text, color_key):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame, text=label_text).pack(side="left")
        
        # Używamy koloru dla trybu ciemnego jako domyślnego w swatchu
        color_swatch = ctk.CTkFrame(frame, width=30, height=30, fg_color=self.colors[color_key][1], border_width=1)
        color_swatch.pack(side="right")
        
        ctk.CTkButton(frame, text="Zmień...", command=lambda key=color_key, swatch=color_swatch, label=label_text: self._pick_color(key, swatch, label)).pack(side="right", padx=10)

    def _pick_color(self, color_key, swatch, label_text):
        color_data = colorchooser.askcolor(title=f"Wybierz: {label_text}")
        if color_data and color_data[1]:
            hex_color = color_data[1]
            
            # Zapisujemy ten sam kolor dla obu trybów, upraszczając edytor
            self.colors[color_key] = [hex_color, hex_color]
            swatch.configure(fg_color=hex_color)
            self._update_preview()

    def _update_preview(self):
        # Index 0 dla 'light', 1 dla 'dark'
        mode_index = 0 if self.appearance_mode == "light" else 1
        
        self.preview_frame.configure(fg_color=self.colors['fg_color'][mode_index])
        self.preview_label.configure(text_color=self.colors['text_color'][mode_index])
        self.preview_button.configure(fg_color=self.colors['button_color'][mode_index], 
                                      hover_color=self.colors['button_hover_color'][mode_index], 
                                      text_color=self.colors['text_color'][mode_index])

    def _set_appearance_mode(self, mode):
        self.appearance_mode = mode.lower()
        self._update_preview()

    def _save_theme(self):
        theme_name = self.theme_name_entry.get()
        if not theme_name: return

        # Przygotuj słownik tylko z kolorami do zapisu
        user_colors_to_save = {
            "fg_color": self.colors['fg_color'],
            "button_color": self.colors['button_color'],
            "button_hover_color": self.colors['button_hover_color'],
            "text_color": self.colors['text_color']
        }

        success, msg = self.app_context.theme_service.save_theme(theme_name, self.appearance_mode, user_colors_to_save)
        print(msg)
        if success:
            self.on_save_callback()
            self.destroy()