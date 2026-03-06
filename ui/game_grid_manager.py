import tkinter as tk
from tkinter import ttk
import math
import logging
from utils import image_utils, constants


class GameGridManager:
    """Zarządza tworzeniem, aktualizacją i paginacją siatki gier."""

    def __init__(self, launcher_instance, parent_frame):
        self.launcher = launcher_instance
        self.parent_frame = parent_frame  # Ramka, w której siatka ma być umieszczona (np. self.content w GameLauncher)
        self.canvas = None
        self.scrollbar = None
        self.grid_frame = None  # Ramka wewnątrz canvas, zawierająca kafelki
        self.pagination_frame = None  # Ramka na przyciski paginacji
        self.current_page = 1
        self.items_per_page = constants.DEFAULT_ITEMS_PER_PAGE
        self._total_pages = 1
        self._current_tiles = (
            {}
        )  # Słownik przechowujący widgety kafelków {game_name: tile_frame}
        self._lazy_load_scheduled = False
        self._last_visible_range = (-1, -1)  # Do optymalizacji lazy load

        self._setup_grid_ui()

    def _setup_grid_ui(self):
        """Konfiguruje Canvas, Scrollbar i wewnętrzną ramkę dla siatki gier."""
        # Canvas do przewijania
        self.canvas = tk.Canvas(
            self.parent_frame,
            bg=constants.THEMES["Dark"]["background"],
            highlightthickness=0,
        )
        self.canvas.grid(
            row=0, column=0, sticky="nsew"
        )  # Siatka gier w pierwszym wierszu

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(
            self.parent_frame, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Ramka wewnątrz Canvas, która będzie zawierać kafelki
        self.grid_frame = ttk.Frame(self.canvas, style="Game.TFrame")
        self.canvas_frame_id = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw"
        )

        # Bindowanie zdarzeń do Canvas i Ramki
        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind(
            "<Configure>", self._on_canvas_configure
        )  # Do aktualizacji szerokości ramki
        # Bindowanie kółka myszy (różne dla różnych systemów)
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)  # Linux góra
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)  # Linux dół

        # Ramka na kontrolki paginacji
        self.pagination_frame = ttk.Frame(self.parent_frame)
        self.pagination_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=5
        )  # Paginacja w drugim wierszu
        self.pagination_frame.columnconfigure(1, weight=1)  # Etykieta strony na środku

        # Przyciski paginacji (początkowo puste, wypełniane w update_pagination_controls)
        self.prev_button = ttk.Button(
            self.pagination_frame,
            text="<< Poprzednia",
            command=self.prev_page,
            state=tk.DISABLED,
        )
        self.prev_button.grid(row=0, column=0, padx=10)
        self.page_label = ttk.Label(self.pagination_frame, text="Strona 1 / 1")
        self.page_label.grid(row=0, column=1)
        self.next_button = ttk.Button(
            self.pagination_frame,
            text="Następna >>",
            command=self.next_page,
            state=tk.DISABLED,
        )
        self.next_button.grid(row=0, column=2, padx=10)

    def _on_frame_configure(self, event=None):
        """Aktualizuje region przewijania Canvas, gdy zmieni się rozmiar ramki."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._trigger_lazy_load()  # Załaduj widoczne kafelki po zmianie rozmiaru

    def _on_canvas_configure(self, event=None):
        """Dostosowuje szerokość wewnętrznej ramki do szerokości Canvas."""
        canvas_width = self.canvas.winfo_width()
        self.canvas.itemconfig(self.canvas_frame_id, width=canvas_width)
        self._trigger_lazy_load()  # Załaduj widoczne kafelki po zmianie rozmiaru

    def _on_mouse_wheel(self, event):
        """Obsługuje przewijanie kółkiem myszy."""
        if event.num == 4 or event.delta > 0:  # Linux góra lub Windows/macOS góra
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:  # Linux dół lub Windows/macOS dół
            self.canvas.yview_scroll(1, "units")
        self._trigger_lazy_load()  # Załaduj widoczne kafelki po przewinięciu

    def _trigger_lazy_load(self, event=None):
        """Opóźnia wywołanie _load_visible_tiles, aby uniknąć wielokrotnych wywołań."""
        if not self._lazy_load_scheduled:
            self._lazy_load_scheduled = True
            self.parent_frame.after(
                100, self._load_visible_tiles_callback
            )  # Opóźnienie 100ms

    def _load_visible_tiles_callback(self):
        """Callback do wykonania lazy load po opóźnieniu."""
        self._lazy_load_scheduled = False
        self._load_visible_tiles()

    def _load_visible_tiles(self):
        """Ładuje tylko te kafelki, które są aktualnie widoczne w Canvas."""
        try:
            canvas_height = self.canvas.winfo_height()
            # yview() zwraca (górna_widoczna_część, dolna_widoczna_część) jako ułamki (0.0 do 1.0)
            scroll_info = self.canvas.yview()
            if not scroll_info:
                return  # Czasami może być puste na starcie

            scroll_top_frac = scroll_info[0]
            scroll_bottom_frac = scroll_info[1]

            # Oblicz widoczny zakres Y w pikselach
            scroll_region = self.canvas.bbox("all")
            if not scroll_region:
                return  # Jeśli ramka jest pusta
            total_height = scroll_region[3] - scroll_region[1]

            visible_top_y = scroll_top_frac * total_height
            visible_bottom_y = scroll_bottom_frac * total_height

            # Sprawdź, czy widoczny zakres się zmienił znacząco
            current_visible_range = (int(visible_top_y), int(visible_bottom_y))
            if current_visible_range == self._last_visible_range:
                # logging.debug("Lazy load: Widoczny zakres bez zmian.")
                return
            self._last_visible_range = current_visible_range
            # logging.debug(f"Lazy load: Widoczny zakres Y: {visible_top_y:.0f} - {visible_bottom_y:.0f}")

            for game_name, tile_info in self._current_tiles.items():
                tile_frame = tile_info["frame"]
                if not tile_frame.winfo_exists():
                    continue  # Pomiń zniszczone kafelki

                tile_y = tile_frame.winfo_y()
                tile_height = tile_frame.winfo_height()
                tile_bottom_y = tile_y + tile_height

                # Sprawdź, czy kafelek jest (przynajmniej częściowo) widoczny
                is_visible = (tile_y < visible_bottom_y) and (
                    tile_bottom_y > visible_top_y
                )

                if is_visible and not tile_info["loaded"]:
                    # logging.debug(f"Lazy load: Ładowanie kafelka {game_name} (Y: {tile_y})")
                    self._populate_game_tile(
                        tile_frame,
                        game_name,
                        self.launcher.games[game_name],
                        tile_info["width"],
                        tile_info["height"],
                    )
                    tile_info["loaded"] = True
                # Opcjonalnie: można dodać logikę do "unload" (zastąpienia obrazka placeholderem),
                # jeśli kafelek przestaje być widoczny, aby oszczędzać pamięć.
                # elif not is_visible and tile_info['loaded']:
                #     logging.debug(f"Lazy load: Odładowanie kafelka {game_name}")
                #     self._unload_game_tile(tile_frame) # Trzeba by zaimplementować
                #     tile_info['loaded'] = False

        except tk.TclError as e:
            # Ignoruj błędy związane z odpytywaniem widgetów podczas ich niszczenia
            if "invalid command name" not in str(e):
                logging.warning(f"Błąd TclError podczas lazy load: {e}")
        except Exception as e:
            logging.exception(f"Nieoczekiwany błąd podczas lazy load: {e}")

    def update_game_grid(self, filtered_games):
        """Czyści i ponownie wypełnia siatkę gier na podstawie przefiltrowanej listy."""
        # Wyczyść poprzednie kafelki
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self._current_tiles.clear()
        self.launcher._launch_buttons.clear()  # Wyczyść referencje przycisków w launcherze

        # Oblicz liczbę kolumn na podstawie szerokości canvas
        canvas_width = max(
            self.canvas.winfo_width(), 600
        )  # Minimalna szerokość dla co najmniej 2-3 kolumn
        tile_width = constants.DEFAULT_TILE_WIDTH
        tile_height = constants.DEFAULT_TILE_HEIGHT
        padding = 10
        num_columns = max(1, (canvas_width - padding) // (tile_width + padding))

        # Paginacja
        total_items = len(filtered_games)
        self._total_pages = math.ceil(total_items / self.items_per_page)
        self.current_page = max(
            1, min(self.current_page, self._total_pages)
        )  # Upewnij się, że strona jest poprawna

        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        games_to_display = filtered_games[start_index:end_index]

        logging.info(
            f"Aktualizacja siatki: Strona {self.current_page}/{self._total_pages}, Gry: {len(games_to_display)}/{total_items}, Kolumny: {num_columns}"
        )

        # Tworzenie kafelków dla bieżącej strony
        for i, (game_name, game_data) in enumerate(games_to_display):
            row = i // num_columns
            col = i % num_columns
            padx_config = (padding, padding) if col == num_columns - 1 else (padding, 0)
            pady_config = (
                (padding, padding)
                if row == (len(games_to_display) + num_columns - 1) // num_columns - 1
                else (padding, 0)
            )

            tile_frame = self._create_tile_placeholder(
                self.grid_frame,
                game_name,
                row,
                col,
                padx_config,
                pady_config,
                tile_width,
                tile_height,
            )
            self._current_tiles[game_name] = {
                "frame": tile_frame,
                "loaded": False,
                "row": row,
                "col": col,
                "width": tile_width,
                "height": tile_height,
            }

        # Aktualizuj kontrolki paginacji
        self.update_pagination_controls(total_items)

        # Wymuś aktualizację geometrii i załaduj widoczne kafelki
        self.parent_frame.update_idletasks()
        self._on_frame_configure()  # Zaktualizuj scrollregion
        self._trigger_lazy_load()  # Rozpocznij ładowanie widocznych

    def _create_tile_placeholder(
        self,
        parent,
        game_name,
        row,
        col,
        padx_config,
        pady_config,
        tile_width,
        tile_height,
    ):
        """Tworzy pustą ramkę (placeholder) dla kafelka gry."""
        tile_frame = ttk.Frame(
            parent,
            width=tile_width,
            height=tile_height,
            style="Game.TFrame",
            borderwidth=1,
            relief="solid",
        )
        tile_frame.grid(
            row=row, column=col, padx=padx_config, pady=pady_config, sticky="nsew"
        )
        tile_frame.grid_propagate(False)  # Zapobiegaj zmianie rozmiaru przez zawartość

        # Można dodać etykietę "Ładowanie..." lub prosty szary prostokąt
        loading_label = ttk.Label(tile_frame, text="Ładowanie...", anchor="center")
        loading_label.place(relx=0.5, rely=0.5, anchor="center")

        return tile_frame

    def _populate_game_tile(
        self, tile_frame, game_name, game_data, tile_width, tile_height
    ):
        """Wypełnia placeholder kafelka rzeczywistą zawartością (obrazek, przyciski)."""
        for widget in tile_frame.winfo_children():
            widget.destroy()

        # --- Obrazek okładki ---
        cover_path = game_data.get("cover")
        thumbnail_path = image_utils.get_or_create_thumbnail(
            cover_path, game_name, (tile_width, tile_height)
        )
        photo = image_utils.load_photoimage_from_path(
            thumbnail_path, (tile_width, tile_height)
        )

        image_button = ttk.Button(
            tile_frame,
            image=photo,
            style="Game.TButton",
            command=lambda gn=game_name: self.launcher.launch_game(gn),
        )
        image_button.image = photo  # Zachowaj referencję!
        image_button.pack(fill=tk.BOTH, expand=True)
        self.launcher._launch_buttons[game_name] = (
            image_button  # Zapisz referencję do przycisku uruchamiającego
        )

        # --- Pasek z nazwą i przyciskami ---
        info_bar = ttk.Frame(tile_frame, style="Game.TFrame")
        info_bar.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)  # Na dole kafelka

        # Nazwa gry (skrócona, jeśli za długa)
        max_name_width = tile_width - 60  # Zostaw miejsce na przyciski
        game_name_label = ttk.Label(
            info_bar,
            text=game_name,
            anchor="w",
            style="Game.TLabel",
            width=int(max_name_width / 7),
        )  # Przybliżona szerokość w znakach
        game_name_label.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        # Tooltip dla pełnej nazwy
        # ToolTip(game_name_label, text=game_name) # Wymaga implementacji ToolTip

        # Przycisk Edycji
        edit_icon_img = self._create_icon("edit")  # Potrzebna implementacja ikony
        edit_btn = ttk.Button(
            info_bar,
            image=edit_icon_img,
            style="Tool.TButton",
            width=2,
            command=lambda gn=game_name: self.launcher.edit_game(gn),
        )
        edit_btn.image = edit_icon_img
        edit_btn.pack(side=tk.RIGHT, padx=(0, 1))
        # ToolTip(edit_btn, text="Edytuj")

        # Przycisk Zarządzania Zapisami
        save_icon_img = self._create_icon("save")  # Potrzebna implementacja ikony
        save_btn = ttk.Button(
            info_bar,
            image=save_icon_img,
            style="Tool.TButton",
            width=2,
            command=lambda gn=game_name: self.launcher.manage_saves(gn),
        )
        save_btn.image = save_icon_img
        save_btn.pack(side=tk.RIGHT, padx=(0, 1))
        # ToolTip(save_btn, text="Zarządzaj Zapisami")

        # Przycisk Usunięcia
        delete_icon_img = self._create_icon("delete")  # Potrzebna implementacja ikony
        delete_btn = ttk.Button(
            info_bar,
            image=delete_icon_img,
            style="Tool.TButton",
            width=2,
            command=lambda gn=game_name: self.launcher.delete_game(gn),
        )
        delete_btn.image = delete_icon_img
        delete_btn.pack(side=tk.RIGHT, padx=(0, 1))
        # ToolTip(delete_btn, text="Usuń")

        # Dodaj obsługę menu kontekstowego
        tile_frame.bind(
            "<Button-3>",
            lambda event, gn=game_name: self.launcher.show_context_menu(event, gn),
        )
        image_button.bind(
            "<Button-3>",
            lambda event, gn=game_name: self.launcher.show_context_menu(event, gn),
        )
        info_bar.bind(
            "<Button-3>",
            lambda event, gn=game_name: self.launcher.show_context_menu(event, gn),
        )
        game_name_label.bind(
            "<Button-3>",
            lambda event, gn=game_name: self.launcher.show_context_menu(event, gn),
        )

    def _create_icon(self, icon_type):
        """Tworzy prostą ikonę (placeholder). Wymaga lepszej implementacji."""
        # TODO: Załadować rzeczywiste ikony z plików lub użyć biblioteki ikon
        size = (16, 16)
        img = Image.new("RGBA", size, (0, 0, 0, 0))  # Przezroczyste tło
        draw = ImageDraw.Draw(img)
        if icon_type == "edit":
            draw.polygon(
                [(2, 10), (2, 14), (6, 14), (14, 6), (10, 2), (6, 2)],
                fill="white",
                outline="black",
            )
        elif icon_type == "save":
            draw.rectangle([2, 2, 14, 14], outline="white")
            draw.rectangle([4, 2, 12, 8], fill="white")
        elif icon_type == "delete":
            draw.line([(4, 4), (12, 12)], fill="red", width=2)
            draw.line([(4, 12), (12, 4)], fill="red", width=2)
        else:  # Domyślna ikona
            draw.rectangle([4, 4, 12, 12], fill="gray")
        return ImageTk.PhotoImage(img)

    def update_pagination_controls(self, total_items):
        """Aktualizuje etykietę strony i stan przycisków paginacji."""
        if self._total_pages <= 1:
            self.pagination_frame.grid_remove()  # Ukryj paginację, jeśli jest tylko jedna strona
        else:
            self.pagination_frame.grid()  # Pokaż paginację
            self.page_label.config(
                text=f"Strona {self.current_page} / {self._total_pages}"
            )
            self.prev_button.config(
                state=tk.NORMAL if self.current_page > 1 else tk.DISABLED
            )
            self.next_button.config(
                state=(
                    tk.NORMAL if self.current_page < self._total_pages else tk.DISABLED
                )
            )

    def prev_page(self):
        """Przechodzi do poprzedniej strony."""
        if self.current_page > 1:
            self.current_page -= 1
            self.launcher.update_game_grid()  # Wywołaj aktualizację w głównym launcherze

    def next_page(self):
        """Przechodzi do następnej strony."""
        if self.current_page < self._total_pages:
            self.current_page += 1
            self.launcher.update_game_grid()  # Wywołaj aktualizację w głównym launcherze

    def reset_pagination(self):
        """Resetuje paginację do pierwszej strony."""
        self.current_page = 1
