import datetime
import tkinter as tk
from tkinter import colorchooser, ttk

from tkcalendar import DateEntry


def create_statistics_page(self):
    """Tworzy interfejs użytkownika dla strony statystyk."""
    for widget in self.stats_page_frame.winfo_children():
        widget.destroy()

    self.stats_page_frame.columnconfigure(0, weight=1)
    self.stats_page_frame.rowconfigure(1, weight=1)

    controls_frame = ttk.Frame(self.stats_page_frame, padding=(10, 5))
    controls_frame.grid(row=0, column=0, sticky="ew")

    col_idx = 0
    ttk.Label(controls_frame, text="Okres:").grid(
        row=0, column=col_idx, padx=(0, 2), pady=5, sticky="w"
    )
    col_idx += 1
    initial_period_key = "Last 7 Days"
    initial_period_display = self.STATS_PERIOD_OPTIONS_TRANSLATED.get(
        initial_period_key, initial_period_key
    )
    self.stats_period_var = tk.StringVar(value=initial_period_display)
    period_options_display = list(self.STATS_PERIOD_OPTIONS_TRANSLATED.values())
    self.stats_period_combo = ttk.Combobox(
        controls_frame,
        textvariable=self.stats_period_var,
        values=period_options_display,
        state="readonly",
        width=18,
    )
    self.stats_period_combo.grid(row=0, column=col_idx, padx=(0, 10), pady=5, sticky="w")
    col_idx += 1

    ttk.Label(controls_frame, text="Widok:").grid(
        row=0, column=col_idx, padx=(0, 2), pady=5, sticky="w"
    )
    col_idx += 1
    initial_view_key = "Playtime per Day"
    initial_view_display = self.STATS_VIEW_OPTIONS_TRANSLATED.get(
        initial_view_key, initial_view_key
    )
    self.stats_view_var = tk.StringVar(value=initial_view_display)
    view_options_display = list(self.STATS_VIEW_OPTIONS_TRANSLATED.values())
    self.stats_view_combo = ttk.Combobox(
        controls_frame,
        textvariable=self.stats_view_var,
        values=view_options_display,
        state="readonly",
        width=25,
    )
    self.stats_view_combo.grid(row=0, column=col_idx, padx=(0, 10), pady=5, sticky="w")
    col_idx += 1
    self.stats_view_combo.bind("<<ComboboxSelected>>", self._on_view_change)

    self.dynamic_controls_frame = ttk.Frame(controls_frame)
    self.dynamic_controls_frame.grid(row=0, column=col_idx, padx=5, pady=5, sticky="w")
    col_idx += 1

    self.stats_game_select_frame = ttk.Frame(self.dynamic_controls_frame)
    ttk.Label(self.stats_game_select_frame, text="Gra:").pack(side=tk.LEFT, padx=(0, 2))
    self.stats_game_var = tk.StringVar()
    all_game_names = sorted(list(self.games.keys()), key=str.lower)
    self.stats_game_combo = ttk.Combobox(
        self.stats_game_select_frame,
        textvariable=self.stats_game_var,
        values=all_game_names,
        state="readonly",
        width=30,
    )
    if all_game_names:
        self.stats_game_var.set(all_game_names[0])
    self.stats_game_combo.pack(side=tk.LEFT)

    self.custom_range_frame = ttk.Frame(self.dynamic_controls_frame)
    ttk.Label(self.custom_range_frame, text="Od:").grid(row=0, column=0, padx=(0, 2))
    self.stats_start_date_entry = DateEntry(
        self.custom_range_frame, width=10, date_pattern="yyyy-mm-dd"
    )
    self.stats_start_date_entry.grid(row=0, column=1, padx=(0, 5))
    ttk.Label(self.custom_range_frame, text="Do:").grid(row=0, column=2, padx=(5, 2))
    self.stats_end_date_entry = DateEntry(
        self.custom_range_frame, width=10, date_pattern="yyyy-mm-dd"
    )
    self.stats_end_date_entry.grid(row=0, column=3)
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=6)
    self.stats_start_date_entry.set_date(one_week_ago)
    self.stats_end_date_entry.set_date(today)

    controls_frame.columnconfigure(col_idx, weight=1)
    col_idx += 1

    self.show_time_details_button = ttk.Button(
        controls_frame,
        text="Pokaż Czas / Grę (Okres)",
        command=self._show_total_playtime_details,
    )

    def _choose_bar_color():
        initial = getattr(self, "stats_bar_color", "#0078d7")
        color_code = colorchooser.askcolor(initialcolor=initial, parent=self.stats_page_frame)
        if color_code and color_code[1]:
            self.stats_bar_color = color_code[1]
            self._on_refresh_stats_threaded()

    color_btn = ttk.Button(controls_frame, text="Kolor słupków", command=_choose_bar_color)
    color_btn.grid(row=0, column=col_idx, padx=5, pady=5, sticky="e")
    col_idx += 1

    refresh_btn = ttk.Button(
        controls_frame, text="Odśwież", command=self._on_refresh_stats_threaded
    )
    refresh_btn.grid(row=0, column=col_idx, padx=(5, 0), pady=5, sticky="e")
    col_idx += 1

    self.launcher_usage_label = ttk.Label(
        controls_frame,
        text="Łączny czas w launcherze: Ładowanie...",
        font=("Segoe UI", 8, "italic"),
    )
    self.launcher_usage_label.grid(
        row=1, column=0, columnspan=col_idx, sticky="w", padx=5, pady=(5, 0)
    )

    chart_detail_frame = ttk.Frame(self.stats_page_frame)
    chart_detail_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    chart_detail_frame.rowconfigure(0, weight=1)
    chart_detail_frame.columnconfigure(0, weight=1)
    chart_detail_frame.columnconfigure(1, weight=0)
    self.chart_container = ttk.Frame(chart_detail_frame, relief="sunken", borderwidth=1)
    self.chart_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    self.chart_info_label = ttk.Label(
        self.chart_container, text="Wybierz okres i widok...", anchor="center"
    )
    self.chart_info_label.pack(expand=True)
    self.details_frame = ttk.Frame(chart_detail_frame)
    self.details_frame.rowconfigure(1, weight=1)
    self.details_frame.columnconfigure(0, weight=1)
    details_label = ttk.Label(self.details_frame, text="Szczegóły:", font=("Segoe UI", 9, "bold"))
    details_label.grid(row=0, column=0, columnspan=2, sticky="nw", pady=(0, 2))
    self.details_tree = ttk.Treeview(
        self.details_frame, columns=("Col1", "Col2"), show="headings", height=10
    )
    self.details_tree.heading("Col1", text="Nazwa Gry")
    self.details_tree.heading("Col2", text="Wartość")
    self.details_tree.column("Col1", anchor="w", width=150)
    self.details_tree.column("Col2", anchor="e", width=80, stretch=False)
    details_tree_scroll = ttk.Scrollbar(
        self.details_frame, orient="vertical", command=self.details_tree.yview
    )
    self.details_tree.configure(yscrollcommand=details_tree_scroll.set)
    self.details_tree.grid(row=1, column=0, sticky="nsew")
    details_tree_scroll.grid(row=1, column=1, sticky="ns")
    self.details_frame.grid_remove()
    self._current_chart_data = None
    self._last_figure_canvas = None
    self._on_period_change()
    self._on_view_change()


__all__ = [
    "create_statistics_page",
]
