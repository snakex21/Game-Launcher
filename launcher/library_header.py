import tkinter as tk
from tkinter import ttk


def create_header(self):
    """Tworzy górny panel (header) dla widoku biblioteki."""
    if hasattr(self, "header") and self.header.winfo_exists():
        for widget in self.header.winfo_children():
            widget.destroy()
    else:
        self.header = ttk.Frame(self.main_frame)
        self.header.grid(row=0, column=0, sticky="ew")

    self.search_var = tk.StringVar()
    self.search_var.trace_add("write", lambda *_: self._on_search_change())

    ttk.Label(self.header, text="Biblioteka", font=("Helvetica", 14)).grid(
        row=0, column=0, padx=10, pady=10, sticky="w"
    )

    self.search_entry = ttk.Entry(self.header, textvariable=self.search_var)
    self.search_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

    self.add_game_btn = ttk.Button(self.header, text="Dodaj Grę", command=self.add_game)
    self.add_game_btn.grid(row=0, column=2, padx=5, pady=10)

    self.filter_or_group_var = tk.StringVar(value="Wszystkie Gry")
    self.filter_group_menu_placeholder = ttk.Frame(self.header)
    self.filter_group_menu_placeholder.grid(row=0, column=3, padx=5, pady=10, sticky="ew")
    self.update_filter_group_menu()

    self.add_group_btn = ttk.Button(
        self.header, text="Dodaj Grupę Statyczną", command=self.add_group
    )
    self.add_group_btn.grid(row=0, column=4, padx=5, pady=10)

    self.delete_group_btn = ttk.Button(
        self.header, text="Usuń Grupę Statyczną", command=self.delete_group
    )
    self.delete_group_btn.grid(row=0, column=5, padx=5, pady=10)

    manage_filters_btn = ttk.Button(
        self.header,
        text="Zarządzaj filtrami",
        command=self.open_advanced_filter_manager,
    )
    manage_filters_btn.grid(row=0, column=6, padx=10, pady=10, sticky="ew")

    self.header.columnconfigure(1, weight=1)

    filter_sort_frame = ttk.Frame(self.header)
    filter_sort_frame.grid(row=1, column=0, columnspan=7, sticky="ew", padx=5, pady=(0, 5))

    current_col_in_filter_sort_frame = 0

    MIN_DROPDOWN_WIDTH = 130
    COMMON_INNER_PADX = 5

    filter_sort_frame.columnconfigure(current_col_in_filter_sort_frame, weight=0)
    ttk.Label(filter_sort_frame, text="Gatunek:").grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(0, COMMON_INNER_PADX),
        pady=5,
        sticky="w",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(
        current_col_in_filter_sort_frame, weight=1, minsize=MIN_DROPDOWN_WIDTH
    )
    self.filter_var = tk.StringVar(value="Wszystkie Gatunki")
    self.genre_options = ["Wszystkie Gatunki"] + self.get_all_genres()
    self.filter_menu = ttk.OptionMenu(
        filter_sort_frame,
        self.filter_var,
        self.filter_var.get(),
        *self.genre_options,
        command=lambda _: self.reset_and_update_grid(),
    )
    self.filter_menu.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(0, 0),
        pady=5,
        sticky="ew",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(current_col_in_filter_sort_frame, weight=0)
    ttk.Label(filter_sort_frame, text="Tag:").grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(COMMON_INNER_PADX, COMMON_INNER_PADX),
        pady=5,
        sticky="w",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(
        current_col_in_filter_sort_frame, weight=1, minsize=MIN_DROPDOWN_WIDTH
    )
    self.tag_filter_var = tk.StringVar(value="Wszystkie Tagi")
    self.tag_filter_menu = ttk.OptionMenu(
        filter_sort_frame,
        self.tag_filter_var,
        "Wszystkie Tagi",
        command=lambda _: self.reset_and_update_grid(),
    )
    self.tag_filter_menu.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(0, 0),
        pady=5,
        sticky="ew",
    )
    current_col_in_filter_sort_frame += 1
    self.update_tag_filter_options()

    filter_sort_frame.columnconfigure(current_col_in_filter_sort_frame, weight=0)
    ttk.Label(filter_sort_frame, text="Typ:").grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(COMMON_INNER_PADX, COMMON_INNER_PADX),
        pady=5,
        sticky="w",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(
        current_col_in_filter_sort_frame, weight=1, minsize=MIN_DROPDOWN_WIDTH
    )
    self.game_type_filter_var = tk.StringVar(value="Wszystkie Typy")
    game_type_options = ["Wszystkie Typy", "Gry PC", "Gry Emulowane"]
    self.game_type_filter_menu = ttk.OptionMenu(
        filter_sort_frame,
        self.game_type_filter_var,
        self.game_type_filter_var.get(),
        *game_type_options,
        command=lambda _: self.reset_and_update_grid(),
    )
    self.game_type_filter_menu.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(0, 0),
        pady=5,
        sticky="ew",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(current_col_in_filter_sort_frame, weight=0)
    ttk.Label(filter_sort_frame, text="Sortuj:").grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(COMMON_INNER_PADX, COMMON_INNER_PADX),
        pady=5,
        sticky="w",
    )
    current_col_in_filter_sort_frame += 1

    filter_sort_frame.columnconfigure(
        current_col_in_filter_sort_frame, weight=1, minsize=MIN_DROPDOWN_WIDTH
    )
    self.sort_var = tk.StringVar(value="Nazwa")
    sort_options = ["Nazwa", "Data Dodania", "Czas Gry", "Ocena"]
    self.sort_menu = ttk.OptionMenu(
        filter_sort_frame,
        self.sort_var,
        self.sort_var.get(),
        *sort_options,
        command=lambda _: self.reset_and_update_grid(),
    )
    self.sort_menu.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(0, 0),
        pady=5,
        sticky="ew",
    )
    current_col_in_filter_sort_frame += 1

    manage_genres_btn = ttk.Button(
        filter_sort_frame, text="Zarządzaj Gatunkami", command=self.manage_genres
    )
    manage_genres_btn.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(10, 5),
        pady=5,
        sticky="e",
    )
    current_col_in_filter_sort_frame += 1

    self.view_mode_button = ttk.Button(filter_sort_frame, command=self.toggle_library_view)
    manage_genres_btn.grid(
        row=0,
        column=current_col_in_filter_sort_frame,
        padx=(5, 0),
        pady=5,
        sticky="e",
    )
    current_col_in_filter_sort_frame += 1

    self.update_view_mode_button_text()


__all__ = [
    "create_header",
]
