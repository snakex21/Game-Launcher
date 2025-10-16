# plugins/screenshots/view.py
import customtkinter as ctk
import threading
import os
from PIL import Image

VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
THUMBNAIL_SIZE = (180, 180)

class ScreenshotsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        
        # Słownik do przechowywania 'Nazwa gry' -> 'Ścieżka do folderu'
        self.games_with_screenshots = {}
        self.thumbnail_cache = {} # Przechowuje gotowe obiekty CTkImage
        
        self._setup_ui()

    def refresh_view(self):
        """Główna funkcja odświeżająca, wywoływana przy wejściu na widok."""
        self._populate_game_selector()
        self.on_game_selected(self.game_selector.get())

    def _setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Wybierz grę:").pack(side="left", padx=10)
        
        self.game_selector = ctk.CTkOptionMenu(top_frame, values=["Ładowanie..."], command=self.on_game_selected)
        self.game_selector.pack(side="left", fill="x", expand=True)

        self.open_folder_button = ctk.CTkButton(top_frame, text="Otwórz folder", command=self._open_folder)
        self.open_folder_button.pack(side="left", padx=10)
        
        self.gallery_frame = ctk.CTkScrollableFrame(self, label_text="Galeria")
        self.gallery_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _populate_game_selector(self):
        """Wypełnia menu rozwijane grami, które mają zdefiniowany folder ze screenshotami."""
        library_data = self.app_context.data_manager.get_plugin_data("library")
        games = library_data.get("games", [])
        
        self.games_with_screenshots = {
            game['name']: game['screenshot_folder'] 
            for game in games if game.get('screenshot_folder')
        }
        
        game_names = list(self.games_with_screenshots.keys())
        if game_names:
            self.game_selector.configure(values=game_names)
            self.game_selector.set(game_names[0])
        else:
            self.game_selector.configure(values=["Brak gier z folderem screenshotów"])
            self.game_selector.set("Brak gier z folderem screenshotów")

    def on_game_selected(self, game_name: str):
        """Rozpoczyna skanowanie folderu dla wybranej gry."""
        folder_path = self.games_with_screenshots.get(game_name)
        if not folder_path or not os.path.isdir(folder_path):
            self._clear_gallery("Ten folder nie istnieje lub jest nieprawidłowy.")
            self.open_folder_button.configure(state="disabled")
            return

        self.open_folder_button.configure(state="normal")
        self._clear_gallery("Skanowanie folderu...")
        
        # Uruchom skanowanie i tworzenie miniaturek w tle
        threading.Thread(target=self._scan_folder_thread, args=(folder_path,), daemon=True).start()

    def _scan_folder_thread(self, folder_path):
        """Działa w tle, skanuje pliki i tworzy miniaturki."""
        found_images = []
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(VALID_EXTENSIONS):
                full_path = os.path.join(folder_path, filename)
                
                # Tworzenie miniaturki
                try:
                    if full_path in self.thumbnail_cache:
                        thumbnail_image = self.thumbnail_cache[full_path]
                    else:
                        with Image.open(full_path) as img:
                            img.thumbnail(THUMBNAIL_SIZE)
                            thumbnail_image = ctk.CTkImage(light_image=img, size=(img.width, img.height))
                            self.thumbnail_cache[full_path] = thumbnail_image
                    
                    found_images.append((full_path, thumbnail_image))
                except Exception as e:
                    print(f"Błąd podczas tworzenia miniaturki dla {filename}: {e}")

        # Przekaż wyniki do głównego wątku, aby zaktualizować UI
        if not self.app_context.shutdown_event.is_set():
            self.after(0, self._populate_gallery, found_images)

    def _populate_gallery(self, images):
        """Wypełnia siatkę miniaturkami. Działa w głównym wątku."""
        self._clear_gallery()

        if not images:
            self._clear_gallery("Nie znaleziono żadnych screenshotów.")
            return

        # Konfiguracja siatki
        cols = max(1, self.gallery_frame.winfo_width() // (THUMBNAIL_SIZE[0] + 20))
        self.gallery_frame.grid_columnconfigure(tuple(range(cols)), weight=1)

        for i, (full_path, thumbnail) in enumerate(images):
            row, col = divmod(i, cols)
            
            # Używamy przycisku jako klikalnej miniaturki
            btn = ctk.CTkButton(self.gallery_frame, image=thumbnail, text="", fg_color="transparent",
                                command=lambda p=full_path: os.startfile(p))
            btn.grid(row=row, column=col, padx=5, pady=5)

    def _clear_gallery(self, message=None):
        """Czyści galerię i opcjonalnie wyświetla wiadomość."""
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
        if message:
            ctk.CTkLabel(self.gallery_frame, text=message).pack(expand=True)

    def _open_folder(self):
        """Otwiera aktualnie wybrany folder w Eksploratorze Plików."""
        game_name = self.game_selector.get()
        folder_path = self.games_with_screenshots.get(game_name)
        if folder_path and os.path.isdir(folder_path):
            os.startfile(folder_path)