import datetime
import logging
import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from launcher.utils import load_photoimage_from_path


def create_game_grid(self):
    self.canvas = tk.Canvas(self.content, bg="#1e1e1e", highlightthickness=0)
    self.canvas.grid(row=0, column=0, sticky="nsew")

    self.scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=self.canvas.yview)
    self.scrollbar.grid(row=0, column=1, sticky="ns")

    self.canvas.configure(yscrollcommand=self.scrollbar.set)

    self.games_frame = ttk.Frame(self.canvas)
    self.games_frame_id = self.canvas.create_window((0, 0), window=self.games_frame, anchor="nw")

    self.list_view_frame = ttk.Frame(self.content)

    list_columns = (
        "Nazwa",
        "Czas Gry",
        "Ocena",
        "Gatunki",
        "Wersja",
        "Tagi",
        "Data Dodania",
    )
    self.list_view_tree = ttk.Treeview(
        self.list_view_frame,
        columns=list_columns,
        show="headings",
        selectmode="browse",
        height=15,
    )

    self.list_view_tree.heading(
        "Nazwa",
        text="Nazwa Gry",
        command=lambda: self._sort_list_view_by_column("Nazwa"),
    )
    self.list_view_tree.column("Nazwa", width=250, anchor=tk.W)

    self.list_view_tree.heading(
        "Czas Gry",
        text="Czas Gry",
        command=lambda: self._sort_list_view_by_column("Czas Gry"),
    )
    self.list_view_tree.column("Czas Gry", width=80, anchor=tk.CENTER)

    self.list_view_tree.heading(
        "Ocena",
        text="Ocena",
        command=lambda: self._sort_list_view_by_column("Ocena"),
    )
    self.list_view_tree.column("Ocena", width=60, anchor=tk.CENTER)

    self.list_view_tree.heading(
        "Gatunki",
        text="Gatunki",
        command=lambda: self._sort_list_view_by_column("Gatunki"),
    )
    self.list_view_tree.column("Gatunki", width=150, anchor=tk.W)

    self.list_view_tree.heading(
        "Wersja",
        text="Wersja",
        command=lambda: self._sort_list_view_by_column("Wersja"),
    )
    self.list_view_tree.column("Wersja", width=100, anchor=tk.W)

    self.list_view_tree.heading("Tagi", text="Tagi", command=lambda: self._sort_list_view_by_column("Tagi"))
    self.list_view_tree.column("Tagi", width=150, anchor=tk.W)

    self.list_view_tree.heading(
        "Data Dodania",
        text="Data Dodania",
        command=lambda: self._sort_list_view_by_column("Data Dodania"),
    )
    self.list_view_tree.column("Data Dodania", width=110, anchor=tk.CENTER)

    list_scrollbar = ttk.Scrollbar(self.list_view_frame, orient="vertical", command=self.list_view_tree.yview)
    self.list_view_tree.configure(yscrollcommand=list_scrollbar.set)

    self.list_view_tree.grid(row=0, column=0, sticky="nsew")
    list_scrollbar.grid(row=0, column=1, sticky="ns")

    self.list_view_frame.columnconfigure(0, weight=1)
    self.list_view_frame.rowconfigure(0, weight=1)

    self.list_view_frame.grid_remove()

    self.list_view_tree.bind("<Double-1>", self._on_list_view_double_click)
    self.list_view_tree.bind("<Button-3>", self._on_list_view_right_click)

    self._list_sort_column = "Nazwa"
    self._list_sort_reverse = False

    self.content.columnconfigure(0, weight=1)
    self.content.rowconfigure(0, weight=1)

    self.canvas.bind("<Configure>", self.on_canvas_configure_and_lazy_load)
    self.scrollbar.bind("<B1-Motion>", self._trigger_lazy_load)
    self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel_and_lazy_load, add="+")

    self.tile_height = 670
    self._loaded_tile_ids = set()
    self.pagination_frame = ttk.Frame(self.content)
    self.pagination_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 10))
    self.pagination_frame.columnconfigure(1, weight=1)

    self.prev_page_btn = ttk.Button(
        self.pagination_frame,
        text="<< Poprzednia",
        command=self.prev_page,
        state=tk.DISABLED,
    )
    self.prev_page_btn.grid(row=0, column=0, padx=10)

    self.page_label = ttk.Label(self.pagination_frame, text="Strona 1 / 1")
    self.page_label.grid(row=0, column=1, sticky="ew")

    self.next_page_btn = ttk.Button(
        self.pagination_frame,
        text="Następna >>",
        command=self.next_page,
        state=tk.DISABLED,
    )
    self.next_page_btn.grid(row=0, column=2, padx=10)


def create_game_tile(self, parent, game_name, game_data, tile_width=200, tile_height=300):
    target_size = (tile_width, tile_height)
    original_cover_path = game_data.get("cover_image")

    thumbnail_path = self.get_or_create_thumbnail(original_cover_path, game_name, target_size)

    if thumbnail_path != original_cover_path and "default_cover" in thumbnail_path:
        if not original_cover_path or not os.path.exists(original_cover_path):
            if thumbnail_path and os.path.exists(thumbnail_path):
                pass

    photo = load_photoimage_from_path(thumbnail_path, target_size)

    frame = ttk.Frame(parent, style="Game.TFrame")
    frame.pack(fill="both", expand=True)
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

    cover_label = ttk.Button(
        frame,
        image=photo,
        style="Game.TButton",
        command=lambda gn=game_name: self.launch_game(gn),
    )
    if photo:
        cover_label.image = photo
    else:
        cover_label.config(text="Brak\nOkładki")
    cover_label.grid(row=0, column=0, columnspan=2, sticky="nsew")

    completion = game_data.get("completion", 0)
    vr_mode = game_data.get("vr_mode", False)
    vr_text = " (VR)" if vr_mode else ""
    game_version = game_data.get("version", "")
    game_tags = ", ".join(game_data.get("tags", []))

    label_text = f"{game_name}{vr_text}\n"
    label_text += f"Czas gry: {self.format_play_time(game_data.get('play_time', 0))}\n"
    label_text += f"Ukończenie: {completion}%\n"
    if game_version:
        label_text += f"Wersja: {game_version}\n"
    if game_tags:
        max_tag_len = 25
        if len(game_tags) > max_tag_len:
            game_tags = game_tags[:max_tag_len] + "..."
        label_text += f"Tagi: {game_tags}"

    label_text = label_text.strip()

    name_label = ttk.Label(frame, text=label_text, anchor="w", wraplength=tile_width - 10)
    name_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
    btn_frame.columnconfigure(0, weight=1)
    btn_frame.columnconfigure(1, weight=1)

    if self.is_game_running(game_name):
        launch_btn = ttk.Button(
            btn_frame,
            text="Zamknij",
            style="Red.TButton",
            command=lambda gn=game_name: self.close_game(gn),
        )
    else:
        launch_btn = ttk.Button(
            btn_frame,
            text="Uruchom",
            style="Green.TButton",
            command=lambda gn=game_name: self.launch_game(gn),
        )
    launch_btn.grid(row=0, column=0, padx=5, sticky="ew")

    saves_btn = ttk.Button(btn_frame, text="Zapis", command=lambda gn=game_name: self.manage_saves(gn))
    saves_btn.grid(row=0, column=1, padx=5, sticky="ew")

    edit_btn = ttk.Button(btn_frame, text="Edytuj", command=lambda gn=game_name: self.edit_game(gn))
    edit_btn.grid(row=1, column=0, padx=5, sticky="ew")

    delete_btn = ttk.Button(btn_frame, text="Usuń", command=lambda gn=game_name: self.delete_game(gn))
    delete_btn.grid(row=1, column=1, padx=5, sticky="ew")

    reset_stats_btn = ttk.Button(
        btn_frame,
        text="Resetuj Statystyki",
        command=lambda gn=game_name: self.reset_stats(gn),
    )
    reset_stats_btn.grid(row=2, column=0, padx=5, sticky="ew")

    add_to_group_btn = ttk.Button(
        btn_frame,
        text="Dodaj do Grupy",
        command=lambda gn=game_name: self.add_to_group(gn),
    )
    add_to_group_btn.grid(row=2, column=1, padx=5, sticky="ew")

    if self.group_var.get() != "Wszystkie Gry":
        remove_from_group_btn = ttk.Button(
            btn_frame,
            text="Usuń z Grupy",
            command=lambda gn=game_name: self.remove_from_group(gn),
        )
        remove_from_group_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")


def update_game_grid(self):
    if hasattr(self, "_search_timer_id") and self._search_timer_id:
        try:
            self.root.after_cancel(self._search_timer_id)
        except tk.TclError:
            pass
        self._search_timer_id = None
    logging.debug("Rozpoczynanie update_game_grid...")
    self._launch_buttons.clear()

    search_query = self.search_var.get().lower()
    selected_filter_or_group = self.filter_or_group_var.get()
    selected_genre = self.filter_var.get()
    selected_tag = self.tag_filter_var.get().strip()
    selected_game_type_filter = self.game_type_filter_var.get()
    sort_by = self.sort_var.get()

    selected_filter_or_group = self.filter_or_group_var.get()
    is_static_group = selected_filter_or_group in self.groups
    is_advanced_filter = selected_filter_or_group in self.config.get("saved_filters", {})

    games_to_filter = list(self.games.keys())
    active_filter_rules = None

    if is_static_group:
        games_to_filter = list(self.groups.get(selected_filter_or_group, []))
        logging.debug(f"Filtrowanie według grupy statycznej: {selected_filter_or_group}")
    elif is_advanced_filter:
        active_filter_rules = self.config["saved_filters"][selected_filter_or_group].get(
            "rules", []
        )
        logging.debug(f"Stosowanie filtra zaawansowanego: {selected_filter_or_group}")

    filtered_games = []
    for game_name in games_to_filter:
        game_data = self.games.get(game_name)
        if not game_data:
            continue

        if active_filter_rules:
            if not self._check_game_against_rules(game_data, active_filter_rules):
                continue

        game_type = game_data.get("game_type", "pc")
        type_match = False
        if selected_game_type_filter == "Wszystkie Typy":
            type_match = True
        elif selected_game_type_filter == "Gry PC" and game_type == "pc":
            type_match = True
        elif selected_game_type_filter == "Gry Emulowane" and game_type == "emulator":
            type_match = True
        if not type_match:
            continue

        if search_query and search_query not in game_name.lower():
            continue
        if selected_genre != "Wszystkie Gatunki" and selected_genre not in game_data.get("genres", []):
            continue
        if selected_tag and selected_tag != "Wszystkie Tagi":
            if not any(selected_tag.lower() == tag.lower() for tag in game_data.get("tags", [])):
                continue

        filtered_games.append(game_name)

    if sort_by == "Nazwa":
        filtered_games.sort(key=str.lower)
    elif sort_by == "Data Dodania":
        filtered_games.sort(key=lambda x: self.games[x].get("date_added", 0), reverse=True)
    elif sort_by == "Czas Gry":
        filtered_games.sort(key=lambda x: self.games[x].get("play_time", 0), reverse=True)
    elif sort_by == "Ocena":
        filtered_games.sort(key=lambda x: self.games[x].get("rating", 0) or -1, reverse=True)

    view_mode = self.library_view_mode.get()
    logging.debug(f"Aktualizowanie widoku: {view_mode}")

    if view_mode == "tiles":
        self.list_view_frame.grid_remove()
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.pagination_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 10))

        total_items = len(filtered_games)
        self.update_pagination_controls(total_items)

        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        games_on_this_page = filtered_games[start_index:end_index]

        num_columns = self.local_settings.get("tiles_per_row", 4)
        tile_width = 200
        canvas_width = 1
        try:
            if hasattr(self, "canvas") and self.canvas.winfo_exists():
                self.canvas.update_idletasks()
                canvas_width = self.canvas.winfo_width()
            if canvas_width > 1 and num_columns > 0:
                default_padding_x = 10
                total_padding_width = (num_columns + 1) * default_padding_x
                available_width = canvas_width - total_padding_width
                if available_width > 0:
                    tile_width = available_width // num_columns
                tile_width = max(200, tile_width)
                self.current_tile_width = tile_width
            else:
                self.current_tile_width = 200

        except Exception as e:
            logging.exception(
                f"Błąd podczas obliczania szerokości kafelka na podstawie ustawień: {e}"
            )
            self.current_tile_width = 200
        logging.debug(
            f"Grid (z ustawień): tile_width={self.current_tile_width}, num_columns={num_columns}"
        )

        for widget in self.games_frame.winfo_children():
            if hasattr(widget, "game_info") and "name" in widget.game_info:
                self._clear_launch_button_ref(widget.game_info["name"])
            widget.destroy()
        self._loaded_tile_ids.clear()

        row, col = 0, 0
        default_padding_x = 10
        default_padding_y = 10
        if not games_on_this_page:
            logging.info("Brak gier do wyświetlenia na tej stronie (kafelki).")
            for i in range(num_columns):
                self.games_frame.columnconfigure(i, weight=1)
        else:
            for _idx, game_name in enumerate(games_on_this_page):
                padx_config = default_padding_x
                pady_config = default_padding_y
                self._create_tile_placeholder(
                    self.games_frame,
                    game_name,
                    row,
                    col,
                    padx_config,
                    pady_config,
                    self.current_tile_width,
                    self.tile_height,
                )
                col += 1
                if col >= num_columns:
                    col = 0
                    row += 1
            for i in range(num_columns):
                self.games_frame.columnconfigure(i, weight=1)

        self.root.after(10, self._update_canvas_scrollregion)
        self.root.after(50, self._trigger_lazy_load)

    elif view_mode == "list":
        self.canvas.grid_remove()
        self.scrollbar.grid_remove()
        self.pagination_frame.grid_remove()
        self.list_view_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.list_view_tree.delete(*self.list_view_tree.get_children())
        if not filtered_games:
            logging.info("Brak gier do wyświetlenia (lista).")
        else:
            if hasattr(self, "_list_sort_column"):
                self._sort_list_view_by_column(self._list_sort_column)
            else:
                for game_name in filtered_games:
                    game_data = self.games.get(game_name)
                    if game_data:
                        play_time_str = self.format_play_time(game_data.get("play_time", 0))
                        rating_str = str(game_data.get("rating", ""))
                        genres_str = ", ".join(game_data.get("genres", []))
                        version_str = game_data.get("version", "")
                        tags_str = ", ".join(game_data.get("tags", []))
                        try:
                            added_timestamp = game_data.get("date_added")
                            added_date_str = (
                                datetime.datetime.fromtimestamp(added_timestamp).strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                                if added_timestamp
                                else ""
                            )
                        except Exception:
                            added_date_str = ""
                        values = (
                            game_name,
                            play_time_str,
                            rating_str,
                            genres_str,
                            version_str,
                            tags_str,
                            added_date_str,
                        )
                        self.list_view_tree.insert("", "end", iid=game_name, values=values)

    logging.debug("Zakończono update_game_grid.")


def _update_canvas_scrollregion(self):
    """Aktualizuje scrollregion canvasa po zmianach w games_frame."""
    if hasattr(self, "canvas") and self.canvas.winfo_exists():
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.config(scrollregion=bbox)
        else:
            self.canvas.config(scrollregion=(0, 0, 1, 1))
            logging.warning("Bbox is None for canvas, setting minimal scrollregion.")


def update_pagination_controls(self, total_items):
    """Aktualizuje stan przycisków i etykiety paginacji."""
    if total_items == 0:
        self._total_pages = 1
        self.current_page = 1
    else:
        self._total_pages = (total_items + self.items_per_page - 1) // self.items_per_page

    if self.current_page > self._total_pages:
        self.current_page = self._total_pages

    self.page_label.config(text=f"Strona {self.current_page} / {self._total_pages}")

    if self.current_page <= 1:
        self.prev_page_btn.config(state=tk.DISABLED)
    else:
        self.prev_page_btn.config(state=tk.NORMAL)

    if self.current_page >= self._total_pages:
        self.next_page_btn.config(state=tk.DISABLED)
    else:
        self.next_page_btn.config(state=tk.NORMAL)


def prev_page(self):
    """Przechodzi do poprzedniej strony."""
    if self.current_page > 1:
        self.current_page -= 1
        self.update_game_grid()


def next_page(self):
    """Przechodzi do następnej strony."""
    if self.current_page < self._total_pages:
        self.current_page += 1
        self.update_game_grid()


def reset_pagination(self):
    """Resetuje paginację do pierwszej strony (np. po nowym wyszukiwaniu)."""
    self.current_page = 1


__all__ = [
    "create_game_grid",
    "create_game_tile",
    "update_game_grid",
    "_update_canvas_scrollregion",
    "update_pagination_controls",
    "prev_page",
    "next_page",
    "reset_pagination",
]
