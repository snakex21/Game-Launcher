import datetime
import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from launcher.utils import RESAMPLING


def create_achievements_page(self):
    """Tworzy interfejs strony Osiągnięć (z postępem i zarządzaniem definicjami)."""
    logging.debug("Rozpoczynanie tworzenia strony osiągnięć...")

    if hasattr(self, "achievements_frame") and self.achievements_frame.winfo_exists():
        logging.debug("Czyszczenie istniejącej ramki achievements_frame...")
        for widget in self.achievements_frame.winfo_children():
            try:
                widget.destroy()
            except tk.TclError as e:
                logging.warning(
                    f"Błąd TclError podczas niszczenia widgetu w achievements_frame: {e}"
                )
            except Exception as e:
                logging.exception(
                    f"Nieoczekiwany błąd podczas niszczenia widgetu: {e}"
                )
    else:
        logging.debug("Tworzenie nowej ramki achievements_frame.")
        self.achievements_frame = ttk.Frame(self.root, style="TFrame")
        self.achievements_frame.grid(row=0, column=1, sticky="nsew")

    self.achievements_frame.columnconfigure(0, weight=1)
    self.achievements_frame.rowconfigure(0, weight=1)
    self.achievements_frame.rowconfigure(1, weight=0)

    progress_frame = ttk.Frame(self.achievements_frame)
    progress_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    progress_frame.columnconfigure(0, weight=1)
    progress_frame.rowconfigure(1, weight=1)

    header_frame = ttk.Frame(progress_frame)
    header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
    header_frame.columnconfigure(0, weight=1)
    ttk.Label(header_frame, text="Twoje Osiągnięcia", font=("Helvetica", 16, "bold")).grid(
        row=0, column=0, sticky="w"
    )

    if not hasattr(self, "achievement_definitions"):
        self._load_achievement_definitions()

    defined_ids = set()
    if hasattr(self, "achievement_definitions") and self.achievement_definitions:
        defined_ids = {
            ach_def.get("id") for ach_def in self.achievement_definitions if ach_def.get("id")
        }

    user_progress = self.user.get("achievements", {})

    unlocked_count = 0
    if defined_ids and user_progress:
        unlocked_count = len(
            [
                ach_id
                for ach_id, progress_data in user_progress.items()
                if progress_data.get("unlocked") and ach_id in defined_ids
            ]
        )

    total_count = len(defined_ids)

    ttk.Label(header_frame, text=f"Odblokowano: {unlocked_count} / {total_count}").grid(
        row=0, column=1, sticky="e", padx=10
    )

    ach_canvas = tk.Canvas(progress_frame, bg="#1e1e1e", highlightthickness=0)
    ach_scrollbar = ttk.Scrollbar(progress_frame, orient="vertical", command=ach_canvas.yview)
    self.scrollable_ach_frame = ttk.Frame(ach_canvas, style="TFrame")
    scrollable_ach_frame_window_id = ach_canvas.create_window(
        (0, 0), window=self.scrollable_ach_frame, anchor="nw"
    )

    def _configure_ach_canvas(event):
        if ach_canvas.winfo_exists() and self.scrollable_ach_frame.winfo_exists():
            canvas_width = event.width
            ach_canvas.itemconfig(scrollable_ach_frame_window_id, width=canvas_width)
            ach_canvas.configure(scrollregion=ach_canvas.bbox("all"))

    ach_canvas.bind("<Configure>", _configure_ach_canvas)
    self.scrollable_ach_frame.bind(
        "<Configure>",
        lambda e: (
            ach_canvas.configure(scrollregion=ach_canvas.bbox("all"))
            if ach_canvas.winfo_exists()
            else None
        ),
    )

    def _on_ach_mousewheel(event):
        widget_under_cursor = None
        try:
            widget_under_cursor = self.root.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError) as e:
            logging.debug(f"Ignorowany błąd w winfo_containing (achievements): {e}")
            widget_under_cursor = None

        is_ach_area = False
        curr = widget_under_cursor
        while curr is not None:
            if curr == ach_canvas or (
                hasattr(self, "scrollable_ach_frame") and curr == self.scrollable_ach_frame
            ):
                is_ach_area = True
                break
            if curr == self.root:
                break
            try:
                curr = curr.master
            except tk.TclError:
                break

        if is_ach_area and ach_canvas.winfo_exists():
            scroll_val = -1 * int(event.delta / 120)
            try:
                view_start, view_end = ach_canvas.yview()
                if 0.0 <= view_start <= 1.0 and 0.0 <= view_end <= 1.0:
                    if (scroll_val < 0 and view_start > 0.0) or (
                        scroll_val > 0 and view_end < 1.0
                    ):
                        ach_canvas.yview_scroll(scroll_val, "units")
                        return "break"
                else:
                    logging.warning("Niespójny stan yview dla ach_canvas")
            except tk.TclError as e:
                logging.warning(
                    f"Błąd TclError podczas sprawdzania/przewijania yview dla ach_canvas: {e}"
                )

    ach_canvas.bind_all("<MouseWheel>", _on_ach_mousewheel, add="+")

    ach_canvas.configure(yscrollcommand=ach_scrollbar.set)
    ach_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    ach_scrollbar.grid(row=1, column=1, sticky="ns", pady=5)
    self.scrollable_ach_frame.columnconfigure(1, weight=1)

    logging.debug("Wypełnianie nowo utworzonej scrollable_ach_frame...")
    user_achievements = self.user.get("achievements", {})
    self._ach_icons = {}

    if not hasattr(self, "achievement_definitions") or not self.achievement_definitions:
        logging.warning("Brak definicji osiągnięć do wyświetlenia.")
        ttk.Label(self.scrollable_ach_frame, text="(Brak zdefiniowanych osiągnięć)").grid(
            pady=20
        )
        sorted_definitions = []
    else:
        sorted_definitions = sorted(
            self.achievement_definitions,
            key=lambda x: x.get("name", x.get("id", "")),
        )

    if not sorted_definitions:
        logging.debug("Lista posortowanych definicji jest pusta.")
        if not self.scrollable_ach_frame.winfo_children():
            ttk.Label(self.scrollable_ach_frame, text="(Brak zdefiniowanych osiągnięć)").grid(
                pady=20
            )

    for idx, ach_def in enumerate(sorted_definitions):
        ach_id = ach_def.get("id")
        if not ach_id:
            continue

        ach_progress_data = user_achievements.get(
            ach_id, {"unlocked": False, "timestamp": None, "current_progress": 0}
        )
        is_unlocked = ach_progress_data.get("unlocked")
        timestamp = ach_progress_data.get("timestamp") if is_unlocked else None
        current_progress = ach_progress_data.get("current_progress", 0)
        target_value = ach_def.get("target_value", 1)

        if idx > 0:
            ttk.Separator(self.scrollable_ach_frame, orient="horizontal").grid(
                row=idx * 2 - 1,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=10,
                pady=5,
            )

        item_frame = ttk.Frame(self.scrollable_ach_frame, padding=5, style="Game.TFrame")
        item_frame.grid(row=idx * 2, column=0, columnspan=2, sticky="ew", pady=(0, 5), padx=5)
        item_frame.columnconfigure(1, weight=1)

        icon_path = ach_def.get("icon")
        icon_label = ttk.Label(item_frame, width=8)
        icon_label.grid(row=0, column=0, rowspan=3, padx=(0, 10), sticky="ns")
        if icon_path:
            if icon_path not in self._ach_icons:
                try:
                    img = Image.open(icon_path)
                    icon_size = (48, 48)
                    img.thumbnail(icon_size, RESAMPLING)
                    if not is_unlocked:
                        img = img.convert("L").convert("RGBA")
                    photo = ImageTk.PhotoImage(img)
                    self._ach_icons[icon_path] = photo
                except Exception as e:
                    logging.error(f"Nie można załadować ikony '{icon_path}': {e}")
                    self._ach_icons[icon_path] = None
            if self._ach_icons[icon_path]:
                icon_label.config(image=self._ach_icons[icon_path])
                icon_label.image = self._ach_icons[icon_path]
            else:
                icon_label.config(text="(brak\nikony)", font=("Segoe UI", 7), anchor="center")
        else:
            icon_label.config(text="")

        name_text = ach_def.get("name", ach_id)
        name_color = "white" if is_unlocked else "gray"
        name_label = ttk.Label(
            item_frame,
            text=name_text,
            font=("Helvetica", 11, "bold"),
            foreground=name_color,
        )
        name_label.grid(row=0, column=1, sticky="w")

        desc_text = ach_def.get("description", "")
        desc_color = "white" if is_unlocked else "gray"
        desc_label = ttk.Label(
            item_frame,
            text=desc_text,
            wraplength=600,
            justify=tk.LEFT,
            font=("Segoe UI", 9),
            foreground=desc_color,
        )
        desc_label.grid(row=1, column=1, sticky="w")

        if is_unlocked and timestamp:
            unlock_date = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
            unlock_label = ttk.Label(
                item_frame,
                text=f"Odblokowano: {unlock_date}",
                font=("Segoe UI", 8, "italic"),
                foreground="lightgreen",
            )
            unlock_label.grid(row=2, column=1, sticky="w", pady=(2, 0))
        elif not is_unlocked:
            progress_value = min(current_progress, target_value) if target_value > 0 else 0
            max_progress = target_value if target_value > 0 else 1

            progress_widget_frame = ttk.Frame(item_frame)
            progress_widget_frame.grid(row=2, column=1, sticky="ew", pady=(2, 0))
            progress_widget_frame.columnconfigure(0, weight=1)

            pbar = ttk.Progressbar(
                progress_widget_frame,
                orient="horizontal",
                length=200,
                mode="determinate",
                maximum=max_progress,
                value=progress_value,
                style="custom.Horizontal.TProgressbar",
            )
            pbar.grid(row=0, column=0, sticky="ew", pady=(2, 2))

            progress_text = ""
            if isinstance(target_value, int) and isinstance(current_progress, int):
                progress_text = f"{current_progress} / {target_value}"
            elif isinstance(target_value, float) or isinstance(current_progress, float):
                progress_text = f"{current_progress:.1f} / {target_value:.1f}"
            else:
                progress_text = f"{current_progress} / {target_value}"

            progress_label = ttk.Label(
                progress_widget_frame,
                text=progress_text,
                font=("Segoe UI", 8),
                foreground="gray",
            )
            progress_label.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=(2, 2))

    manage_def_frame = ttk.LabelFrame(
        self.achievements_frame, text=" Zarządzaj Definicjami ", padding=(10, 5)
    )
    manage_def_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(10, 5))
    manage_def_frame.columnconfigure(0, weight=1)
    manage_def_frame.rowconfigure(0, weight=0)

    ach_def_list_frame = ttk.Frame(manage_def_frame)
    ach_def_list_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
    ach_def_list_frame.columnconfigure(0, weight=1)
    ach_def_list_frame.rowconfigure(0, weight=0)

    ach_cols = ("ID", "Nazwa", "Opis", "Warunek")
    self.achievements_def_tree = ttk.Treeview(
        ach_def_list_frame,
        columns=ach_cols,
        show="headings",
        height=5,
        selectmode="browse",
    )
    self.achievements_def_tree.heading("ID", text="ID")
    self.achievements_def_tree.column("ID", width=120, anchor=tk.W, stretch=False)
    self.achievements_def_tree.heading("Nazwa", text="Nazwa")
    self.achievements_def_tree.column("Nazwa", width=180, anchor=tk.W)
    self.achievements_def_tree.heading("Opis", text="Opis")
    self.achievements_def_tree.column("Opis", width=250, anchor=tk.W)
    self.achievements_def_tree.heading("Warunek", text="Warunek")
    self.achievements_def_tree.column("Warunek", width=150, anchor=tk.W)
    ach_def_scrollbar_y = ttk.Scrollbar(
        ach_def_list_frame,
        orient="vertical",
        command=self.achievements_def_tree.yview,
    )
    ach_def_scrollbar_x = ttk.Scrollbar(
        ach_def_list_frame,
        orient="horizontal",
        command=self.achievements_def_tree.xview,
    )
    self.achievements_def_tree.configure(
        yscrollcommand=ach_def_scrollbar_y.set,
        xscrollcommand=ach_def_scrollbar_x.set,
    )
    self.achievements_def_tree.grid(row=0, column=0, sticky="ew")
    ach_def_scrollbar_y.grid(row=0, column=1, sticky="ns")
    ach_def_scrollbar_x.grid(row=1, column=0, columnspan=2, sticky="ew")

    ach_def_buttons_frame = ttk.Frame(manage_def_frame)
    ach_def_buttons_frame.grid(row=2, column=0, pady=(5, 10))
    ttk.Button(
        ach_def_buttons_frame,
        text="Dodaj Nowe",
        command=lambda: self._add_edit_achievement_def(parent_window=self.achievements_frame),
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        ach_def_buttons_frame,
        text="Edytuj Zaznaczone",
        command=lambda: self._add_edit_achievement_def(
            edit_mode=True, parent_window=self.achievements_frame
        ),
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        ach_def_buttons_frame,
        text="Usuń Zaznaczone",
        command=self._delete_achievement_def,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        ach_def_buttons_frame,
        text="Odśwież Definicje",
        command=self._reload_definitions_and_refresh_ui,
    ).pack(side=tk.RIGHT, padx=5)

    self._load_achievement_def_list()

    logging.debug("Zakończono tworzenie strony osiągnięć.")
    self.root.after(
        50,
        lambda: (
            ach_canvas.configure(scrollregion=ach_canvas.bbox("all"))
            if ach_canvas.winfo_exists()
            else None
        ),
    )


__all__ = ["create_achievements_page"]
