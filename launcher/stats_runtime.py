import datetime
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox


def _on_refresh_stats_threaded(self):
    """Uruchamia przygotowanie danych i generowanie wykresu w tle."""
    if hasattr(self, "_last_figure_canvas"):
        if (
            self._last_figure_canvas
            and self._last_figure_canvas.get_tk_widget().winfo_exists()
        ):
            self._last_figure_canvas.get_tk_widget().destroy()
        if hasattr(self, "chart_info_label") and self.chart_info_label.winfo_exists():
            self.chart_info_label.pack(expand=True)
            self.chart_info_label.config(text="Generowanie wykresu...")
    self.root.update_idletasks()

    self.stats_queue = queue.Queue()
    stats_thread = threading.Thread(target=self._generate_stats_in_thread, daemon=True)
    stats_thread.start()
    self.root.after(100, self._check_stats_queue)


def _generate_stats_in_thread(self):
    """Funkcja wykonywana w osobnym wątku."""
    try:
        chart_data = self._prepare_chart_data()
        if chart_data:
            view_type = self.stats_view_var.get()
            figure = self._generate_matplotlib_figure(chart_data, view_type)
            self._current_chart_data = chart_data
            self.stats_queue.put({"success": True, "figure": figure})
        else:
            self.stats_queue.put(
                {"success": False, "error": "Błąd podczas przygotowywania danych."}
            )
    except Exception as e:
        logging.exception("Błąd w wątku generowania statystyk.")
        self.stats_queue.put({"success": False, "error": str(e)})


def _check_stats_queue(self):
    """Sprawdza kolejkę i aktualizuje wykres w głównym wątku."""
    try:
        result = self.stats_queue.get_nowait()
        if result["success"]:
            self._update_stats_chart(result["figure"])
        else:
            if hasattr(self, "chart_info_label") and self.chart_info_label.winfo_exists():
                self.chart_info_label.config(
                    text=f"Błąd:\n{result.get('error', 'Nieznany błąd')}"
                )
            else:
                messagebox.showerror(
                    "Błąd Statystyk",
                    f"Nie można wygenerować wykresu:\n{result.get('error', 'Nieznany błąd')}",
                    parent=self.stats_page_frame,
                )
    except queue.Empty:
        self.root.after(100, self._check_stats_queue)
    except Exception as e:
        logging.exception("Błąd podczas sprawdzania kolejki statystyk.")
        if hasattr(self, "chart_info_label") and self.chart_info_label.winfo_exists():
            self.chart_info_label.config(text=f"Błąd aktualizacji:\n{e}")


def _update_stats_chart(self, figure):
    """Osadza wygenerowaną figurę Matplotlib w Tkinter."""
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    if not hasattr(self, "chart_container") or not self.chart_container.winfo_exists():
        logging.warning("Próba aktualizacji wykresu, ale kontener nie istnieje.")
        return

    if hasattr(self, "chart_info_label") and self.chart_info_label.winfo_exists():
        self.chart_info_label.pack_forget()
    if (
        hasattr(self, "_last_figure_canvas")
        and self._last_figure_canvas
        and self._last_figure_canvas.get_tk_widget().winfo_exists()
    ):
        self._last_figure_canvas.get_tk_widget().destroy()

    canvas = FigureCanvasTkAgg(figure, master=self.chart_container)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack(fill=tk.BOTH, expand=True)
    self._last_figure_canvas = canvas

    view_type = self.TRANSLATED_TO_STATS_VIEW.get(self.stats_view_var.get())

    if view_type not in ["Games Played per Day", "Playtime per Day"]:
        if hasattr(self, "details_frame") and self.details_frame.winfo_ismapped():
            self.details_frame.grid_remove()
            if hasattr(self, "chart_container") and self.chart_container.winfo_exists():
                self.chart_container.master.columnconfigure(0, weight=1)
                self.chart_container.master.columnconfigure(1, weight=0)

    if hasattr(self, "_chart_click_cid") and self._chart_click_cid:
        try:
            canvas.mpl_disconnect(self._chart_click_cid)
        except Exception:
            pass
        self._chart_click_cid = None

    if (
        view_type == "Games Played per Day"
        and self._current_chart_data
        and self._current_chart_data.get("details")
    ):
        self._chart_click_cid = canvas.mpl_connect(
            "button_press_event", self._on_chart_click
        )


def _show_total_playtime_details(self):
    """Wyświetla listę gier i ich łączny czas gry w wybranym okresie."""
    if not hasattr(self, "_current_chart_data") or not self._current_chart_data:
        logging.warning("Brak danych wykresu do pokazania szczegółów czasu gry.")
        return
    if not hasattr(self, "details_tree") or not self.details_tree.winfo_exists():
        return

    all_games_playtime = self._current_chart_data.get("all_games_playtime")
    if not all_games_playtime:
        messagebox.showinfo(
            "Brak Danych",
            "Brak zarejestrowanego czasu gry w wybranym okresie.",
            parent=self.stats_page_frame,
        )
        if self.details_frame.winfo_ismapped():
            self.details_frame.grid_remove()
            self.chart_container.master.columnconfigure(0, weight=1)
            self.chart_container.master.columnconfigure(1, weight=0)
        return

    self.details_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    self._bind_details_resize()
    self.chart_container.master.columnconfigure(0, weight=2)
    self.chart_container.master.columnconfigure(1, weight=1)

    self.details_tree.heading("Col1", text="Nazwa Gry")
    self.details_tree.heading("Col2", text="Czas w okresie")

    self.details_tree.column("Col1", anchor="w", width=200)
    self.details_tree.column("Col2", anchor="e", width=150, stretch=False)

    self.details_tree.delete(*self.details_tree.get_children())
    sorted_games = sorted(all_games_playtime.items(), key=lambda item: item[1], reverse=True)

    for game_name, seconds in sorted_games:
        if seconds > 0.1:
            time_str = self.format_play_time(seconds)
            self.details_tree.insert("", "end", values=(game_name, time_str))


def _on_chart_click(self, event):
    """Obsługuje kliknięcie na wykresie (np. na słupku)."""
    if event.inaxes is None:
        return

    ax = event.inaxes
    clicked_bar = None
    for bar in ax.patches:
        contains, _ = bar.contains(event)
        if contains:
            clicked_bar = bar
            break

    if clicked_bar and self._current_chart_data:
        try:
            bar_index = ax.patches.index(clicked_bar)
            if 0 <= bar_index < len(self._current_chart_data["x_labels"]):
                date_str_short = self._current_chart_data["x_labels"][bar_index]
                clicked_date = None
                start_date, end_date = self._get_time_period_dates()
                if start_date and end_date:
                    temp_date = start_date
                    while temp_date <= end_date:
                        if temp_date.strftime("%m-%d") == date_str_short:
                            clicked_date = temp_date
                            break
                        temp_date += datetime.timedelta(days=1)

                if clicked_date and self._current_chart_data.get("details"):
                    games_set = self._current_chart_data["details"].get(clicked_date, set())
                    logging.info(
                        f"Kliknięto na słupek dla daty {clicked_date}. Gry: {games_set}"
                    )
                    self._show_daily_games_details(games_set)

        except ValueError:
            logging.warning("Nie można znaleźć indeksu klikniętego słupka.")
        except Exception as e:
            logging.exception(f"Błąd podczas obsługi kliknięcia na wykresie: {e}")


def _show_daily_games_details(self, games_set):
    """Wyświetla listę gier dla wybranego dnia w Treeview."""
    if not hasattr(self, "details_tree") or not self.details_tree.winfo_exists():
        return

    self.details_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    self.chart_container.master.columnconfigure(0, weight=2)
    self.chart_container.master.columnconfigure(1, weight=1)

    self.details_tree["columns"] = ("Col1",)
    self.details_tree.heading("Col1", text="Gry Uruchomione Tego Dnia")
    self.details_tree.column("Col1", anchor="w", width=250)

    self.details_tree.delete(*self.details_tree.get_children())
    if not games_set:
        self.details_tree.insert("", "end", values=("(Brak gier tego dnia)",))
    else:
        for game_name in sorted(list(games_set), key=str.lower):
            self.details_tree.insert("", "end", values=(game_name,))


__all__ = [
    "_on_refresh_stats_threaded",
    "_generate_stats_in_thread",
    "_check_stats_queue",
    "_update_stats_chart",
    "_show_total_playtime_details",
    "_on_chart_click",
    "_show_daily_games_details",
]
