import datetime
import logging
import time
import tkinter as tk
from tkinter import messagebox, ttk

from launcher.utils import MONTH_COLORS, MONTH_NAMES_PL, get_contrast_color, save_config


def create_roadmap_page(self, show_frame=True):
    """Tworzy strukturę UI strony Roadmapy, ładowanie danych jest odroczone."""
    if not hasattr(self, "roadmap_frame"):
        self.roadmap_frame = ttk.Frame(self.root)
        if show_frame:
            self.roadmap_frame.grid(row=0, column=1, sticky="nsew")
        self.roadmap_frame.columnconfigure(0, weight=1)
        self.roadmap_frame.rowconfigure(1, weight=1)
    else:
        if show_frame:
            self.roadmap_frame.grid(row=0, column=1, sticky="nsew")
            self.roadmap_frame.tkraise()
        elif self.roadmap_frame.winfo_ismapped():
            self.roadmap_frame.grid_remove()
        return

    for widget in self.roadmap_frame.winfo_children():
        widget.destroy()

    header = ttk.Label(
        self.roadmap_frame,
        text=self.translator.gettext("Roadmapa Gier"),
        font=("Helvetica", 20, "bold"),
    )
    header.grid(row=0, column=0, pady=10, sticky="n")

    notebook = ttk.Notebook(self.roadmap_frame)
    notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    current_frame = ttk.Frame(notebook)
    notebook.add(current_frame, text=self.translator.gettext("Obecne"))

    archive_frame = ttk.Frame(notebook)
    notebook.add(archive_frame, text=self.translator.gettext("Archiwum"))

    self.create_current_games_ui(current_frame)
    self.create_archive_ui(archive_frame)

    self.root.after(150, self._populate_roadmap_and_archive_data)

    if not show_frame and self.roadmap_frame.winfo_ismapped():
        self.roadmap_frame.grid_remove()


def create_current_games_ui(self, parent_frame):
    from tkcalendar import Calendar

    paned_window = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill="both", expand=True)

    left_frame = ttk.Frame(paned_window)
    paned_window.add(left_frame, weight=1)

    right_frame = ttk.Frame(paned_window)
    paned_window.add(right_frame, weight=1)

    self.create_add_game_section(left_frame)
    self.create_roadmap_tree(left_frame)
    self.create_roadmap_buttons(left_frame)

    self.roadmap_calendar = Calendar(
        right_frame,
        selectmode="day",
        date_pattern="yyyy-MM-dd",
        locale="pl_PL",
    )
    self.roadmap_calendar.pack(fill="both", expand=True)


def create_archive_ui(self, parent_frame):
    from tkcalendar import Calendar

    archive_header = ttk.Label(
        parent_frame, text="Archiwum Gier", font=("Helvetica", 16, "bold")
    )
    archive_header.pack(pady=10)

    paned_window = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill="both", expand=True)

    left_frame = ttk.Frame(paned_window)
    paned_window.add(left_frame, weight=1)

    right_frame = ttk.Frame(paned_window)
    paned_window.add(right_frame, weight=1)

    self.archive_tree = ttk.Treeview(
        left_frame,
        columns=(
            "Nazwa Gry",
            "Data Rozpoczęcia",
            "Data Ukończenia",
            "Czas Spędzony",
        ),
        show="headings",
    )
    self.archive_tree.heading("Nazwa Gry", text="Nazwa Gry")
    self.archive_tree.heading("Data Rozpoczęcia", text="Data Rozpoczęcia")
    self.archive_tree.heading("Data Ukończenia", text="Data Ukończenia")
    self.archive_tree.heading("Czas Spędzony", text="Czas Spędzony")
    self.archive_tree.pack(fill="both", expand=True)

    scrollbar = ttk.Scrollbar(
        left_frame, orient="vertical", command=self.archive_tree.yview
    )
    scrollbar.pack(side="right", fill="y")
    self.archive_tree.configure(yscrollcommand=scrollbar.set)

    self.archive_calendar = Calendar(
        right_frame,
        selectmode="day",
        date_pattern="yyyy-MM-dd",
        locale="pl_PL",
    )
    self.archive_calendar.pack(fill="both", expand=True)

    self.create_archive_legend(parent_frame)


def load_archive(self):
    """Ładuje archiwalne gry do Treeview archiwum z dynamicznym kolorem czcionki."""
    self.archive_tree.delete(*self.archive_tree.get_children())
    for game in self.archive:
        game_name = game.get("game_name", "")
        start_date = game.get("start_date", "")
        completion_date = game.get("completion_date", "")
        time_spent = self.format_play_time(game.get("time_spent", 0))

        try:
            completion_month = datetime.datetime.strptime(
                completion_date, "%Y-%m-%d"
            ).month
        except Exception:
            completion_month = None

        if completion_month:
            tag = f"month_{completion_month}"
            self.archive_tree.insert(
                "",
                "end",
                values=(game_name, start_date, completion_date, time_spent),
                tags=(tag,),
            )
        else:
            self.archive_tree.insert(
                "",
                "end",
                values=(game_name, start_date, completion_date, time_spent),
            )

    for month, color in MONTH_COLORS.items():
        tag = f"month_{month}"
        fg_color = get_contrast_color(color)
        self.archive_tree.tag_configure(tag, background=color, foreground=fg_color)


def update_archive_calendar(self):
    """Aktualizuje kalendarz w Archiwum z dynamicznym kolorem czcionki."""
    self.archive_calendar.calevent_remove("all")
    for game in self.archive:
        try:
            completion_date = datetime.datetime.strptime(
                game["completion_date"], "%Y-%m-%d"
            ).date()
            completion_month = completion_date.month
            tag = f"month_{completion_month}"
            self.archive_calendar.calevent_create(
                completion_date, game["game_name"], tags=[tag]
            )
        except Exception as e:
            logging.error(
                f"Nie udało się oznaczyć daty ukończenia dla gry {game['game_name']}: {e}"
            )

    for month, color in MONTH_COLORS.items():
        tag = f"month_{month}"
        fg_color = get_contrast_color(color)
        try:
            self.archive_calendar.tag_config(tag, background=color, foreground=fg_color)
        except Exception as e_cal:
            logging.warning(
                f"Nie można ustawić dynamicznych kolorów dla tagu kalendarza '{tag}': {e_cal}"
            )
            self.archive_calendar.tag_config(tag, background=color)


def create_archive_legend(self, parent_frame):
    """Dodaje legendę do sekcji Archiwum z dynamicznym kolorem czcionki."""
    legend_frame = ttk.Frame(parent_frame)
    legend_frame.pack(pady=5)

    ttk.Label(legend_frame, text="Legenda:").pack(side="left", padx=(0, 5))

    for month in range(1, 13):
        bg_color = MONTH_COLORS.get(month, "white")
        month_name = MONTH_NAMES_PL.get(month, "")
        fg_color = get_contrast_color(bg_color)
        label = ttk.Label(
            legend_frame,
            text=month_name,
            background=bg_color,
            foreground=fg_color,
            padding=(4, 2),
            anchor="center",
        )
        label.pack(side="left", padx=3)


def load_roadmap(self):
    """Ładuje gry z Roadmapy do Treeview."""
    self.roadmap_tree.delete(*self.roadmap_tree.get_children())
    for game in self.roadmap:
        game_name = game.get("game_name", "")
        start_date = game.get("start_date", "")
        end_date = game.get("end_date", "")
        status = game.get("status", "Planowana")
        time_spent = self.format_play_time(game.get("time_spent", 0))
        self.roadmap_tree.insert(
            "", "end", values=(game_name, start_date, end_date, status, time_spent)
        )
        self.mark_calendar_dates(game)


def mark_calendar_dates(self, game):
    """Oznacza daty w kalendarzu związane z Roadmapą."""
    try:
        start_date = datetime.datetime.strptime(game["start_date"], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(game["end_date"], "%Y-%m-%d").date()
        delta = end_date - start_date
        for i in range(delta.days + 1):
            day = start_date + datetime.timedelta(days=i)
            self.roadmap_calendar.calevent_create(day, game["game_name"], "planned_game")
        self.roadmap_calendar.tag_config(
            "planned_game", background="blue", foreground="white"
        )
    except Exception as e:
        logging.error(f"Nie udało się oznaczyć dat dla gry {game['game_name']}: {e}")


def update_calendar(self):
    """Aktualizuje kalendarz z wydarzeniami z Roadmapy."""
    self.roadmap_calendar.calevent_remove("all")
    for game in self.roadmap:
        self.mark_calendar_dates(game)


def create_add_game_section(self, parent_frame):
    """Tworzy sekcję dodawania gry do Roadmapy."""
    from tkcalendar import DateEntry

    add_frame = ttk.LabelFrame(parent_frame, text="Dodaj grę do Roadmapy")
    add_frame.pack(pady=10, padx=10, fill="x")

    ttk.Label(add_frame, text="Nazwa Gry:").grid(
        row=0, column=0, padx=5, pady=5, sticky="e"
    )
    self.roadmap_game_name = ttk.Combobox(
        add_frame, values=list(self.games.keys()), state="readonly"
    )
    self.roadmap_game_name.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    self.roadmap_game_name.set("Wybierz grę")

    ttk.Label(add_frame, text="Data Rozpoczęcia:").grid(
        row=1, column=0, padx=5, pady=5, sticky="e"
    )
    self.roadmap_start_cal = DateEntry(add_frame, date_pattern="yyyy-MM-dd")
    self.roadmap_start_cal.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    ttk.Label(add_frame, text="Planowana Data Zakończenia:").grid(
        row=2, column=0, padx=5, pady=5, sticky="e"
    )
    self.roadmap_end_cal = DateEntry(add_frame, date_pattern="yyyy-MM-dd")
    self.roadmap_end_cal.grid(row=2, column=1, padx=5, pady=5, sticky="w")

    add_btn = ttk.Button(add_frame, text="Dodaj do Roadmapy", command=self.add_to_roadmap)
    add_btn.grid(row=3, column=0, columnspan=2, pady=10)


def create_roadmap_tree(self, parent_frame):
    """Tworzy Treeview dla Roadmapy."""
    self.roadmap_tree = ttk.Treeview(
        parent_frame,
        columns=(
            "Nazwa Gry",
            "Data Rozpoczęcia",
            "Data Zakończenia",
            "Status",
            "Czas Spędzony",
        ),
        show="headings",
    )
    self.roadmap_tree.heading("Nazwa Gry", text="Nazwa Gry")
    self.roadmap_tree.heading("Data Rozpoczęcia", text="Data Rozpoczęcia")
    self.roadmap_tree.heading("Data Zakończenia", text="Data Zakończenia")
    self.roadmap_tree.heading("Status", text="Status")
    self.roadmap_tree.heading("Czas Spędzony", text="Czas Spędzony")
    self.roadmap_tree.pack(fill="both", expand=True)

    scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=self.roadmap_tree.yview)
    scrollbar.pack(side="right", fill="y")
    self.roadmap_tree.configure(yscrollcommand=scrollbar.set)


def create_roadmap_buttons(self, parent_frame):
    """Tworzy przyciski zarządzania Roadmapą."""
    btn_frame = ttk.Frame(parent_frame)
    btn_frame.pack(pady=5)

    complete_btn = ttk.Button(
        btn_frame, text="Oznacz jako Ukończoną", command=self.mark_as_completed
    )
    complete_btn.pack(side="left", padx=5)

    delete_btn = ttk.Button(
        btn_frame, text="Usuń z Roadmapy", command=self.delete_from_roadmap
    )
    delete_btn.pack(side="left", padx=5)


def add_to_roadmap(self):
    """Dodaje nową grę do Roadmapy."""
    game_name = self.roadmap_game_name.get()
    start_date_str = self.roadmap_start_cal.get_date().strftime("%Y-%m-%d")
    end_date_str = self.roadmap_end_cal.get_date().strftime("%Y-%m-%d")

    if game_name == "Wybierz grę" or not start_date_str or not end_date_str:
        messagebox.showwarning("Błąd", "Wszystkie pola są wymagane.")
        return

    for game in self.roadmap:
        if game["game_name"].lower() == game_name.lower():
            messagebox.showwarning("Błąd", "Ta gra już znajduje się w Roadmapie.")
            return

    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        if end_date < start_date:
            raise ValueError("Data zakończenia musi być późniejsza niż data rozpoczęcia.")
    except ValueError as ve:
        messagebox.showerror("Błąd", f"Nieprawidłowy format daty lub logika dat:\n{ve}")
        return

    new_game = {
        "game_name": game_name,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "time_spent": 0,
        "status": "Planowana",
    }
    self.roadmap.append(new_game)
    save_config(self.config)

    self.load_roadmap()
    self.update_calendar()

    self.roadmap_game_name.set("Wybierz grę")
    self.roadmap_start_cal.set_date(datetime.date.today())
    self.roadmap_end_cal.set_date(datetime.date.today())


def mark_as_completed(self):
    """Oznacza wybraną grę jako ukończoną i przenosi ją do archiwum."""
    selected_item = self.roadmap_tree.selection()
    if not selected_item:
        messagebox.showwarning("Błąd", "Nie wybrano żadnej gry.")
        return

    values = self.roadmap_tree.item(selected_item, "values")
    game_name = values[0]

    for game in self.roadmap:
        if game["game_name"] == game_name:
            game["status"] = "Ukończona"
            game["completion_date"] = datetime.date.today().strftime("%Y-%m-%d")
            self.archive.append(game.copy())
            self.roadmap.remove(game)
            break

    self.config["roadmap"] = self.roadmap
    self.config["archive"] = self.archive
    save_config(self.config)
    self.check_and_unlock_achievements()

    self.load_roadmap()
    self.update_calendar()
    self.load_archive()
    self.update_archive_calendar()

    messagebox.showinfo(
        "Sukces",
        f"Gra '{game_name}' została oznaczona jako ukończona i przeniesiona do archiwum.",
    )


def delete_from_roadmap(self):
    """Deletes the selected game from the roadmap."""
    selected_item = self.roadmap_tree.selection()
    if not selected_item:
        messagebox.showwarning("Błąd", "Nie wybrano żadnej gry.")
        return

    values = self.roadmap_tree.item(selected_item, "values")
    game_name = values[0]

    if messagebox.askyesno(
        "Potwierdzenie", f"Czy na pewno chcesz usunąć grę '{game_name}' z Roadmapy?"
    ):
        self.roadmap = [g for g in self.roadmap if g["game_name"] != game_name]
        self.config["roadmap"] = self.roadmap
        save_config(self.config)

        self.load_roadmap()
        self.update_calendar()

        messagebox.showinfo("Sukces", f"Gra '{game_name}' została usunięta z Roadmapy.")


def monitor_roadmap(self):
    """Monitoruje roadmapę i aktualizuje statusy gier."""
    while True:
        current_date = time.strftime("%Y-%m-%d")
        updated = False
        for game in self.roadmap:
            if game["status"] == "Planowana" and game["end_date"] < current_date:
                game["status"] = "Nie ukończona na czas"
                updated = True
        if updated:
            save_config(self.config)
            self.load_roadmap()
            self.update_calendar()
        time.sleep(86400)


def _populate_roadmap_and_archive_data(self):
    """Wypełnia danymi Treeview i Kalendarze w zakładkach Roadmapy i Archiwum."""
    logging.debug("Rozpoczynanie ładowania danych Roadmapy i Archiwum...")
    try:
        if hasattr(self, "roadmap_tree") and self.roadmap_tree.winfo_exists():
            self.load_roadmap()
        if hasattr(self, "roadmap_calendar") and self.roadmap_calendar.winfo_exists():
            self.update_calendar()

        if hasattr(self, "archive_tree") and self.archive_tree.winfo_exists():
            self.load_archive()
        if hasattr(self, "archive_calendar") and self.archive_calendar.winfo_exists():
            self.update_archive_calendar()

        logging.debug("Zakończono ładowanie danych Roadmapy i Archiwum.")

    except tk.TclError as e:
        logging.warning(f"Błąd TclError podczas ładowania danych roadmapy/archiwum: {e}")
    except Exception:
        logging.exception("Nieoczekiwany błąd podczas ładowania danych roadmapy/archiwum")


__all__ = [
    "create_roadmap_page",
    "create_current_games_ui",
    "create_archive_ui",
    "load_archive",
    "update_archive_calendar",
    "create_archive_legend",
    "load_roadmap",
    "mark_calendar_dates",
    "update_calendar",
    "create_add_game_section",
    "create_roadmap_tree",
    "create_roadmap_buttons",
    "add_to_roadmap",
    "mark_as_completed",
    "delete_from_roadmap",
    "monitor_roadmap",
    "_populate_roadmap_and_archive_data",
]
