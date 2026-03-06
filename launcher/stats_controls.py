import datetime
import logging
import time
from tkinter import messagebox


def _on_period_change(self, event=None):
    selected_display_period = self.stats_period_var.get()
    period_key = self.TRANSLATED_TO_STATS_PERIOD.get(selected_display_period)

    if hasattr(self, "custom_range_frame") and self.custom_range_frame.winfo_exists():
        if hasattr(self.custom_range_frame, "pack_forget"):
            self.custom_range_frame.pack_forget()
        else:
            self.custom_range_frame.grid_remove()

    if period_key == "Custom Range...":
        self.dynamic_controls_frame.grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.custom_range_frame.pack(side="left")
    else:
        view_key = self.TRANSLATED_TO_STATS_VIEW.get(self.stats_view_var.get())
        if view_key != "Playtime per Game (Selected)":
            self.dynamic_controls_frame.grid_remove()

    self._on_view_change()


def _get_time_period_dates(self):
    """Zwraca (start_date, end_date) na podstawie wybranego okresu."""
    selected_display_period = self.stats_period_var.get()
    period_key = self.TRANSLATED_TO_STATS_PERIOD.get(selected_display_period)
    if not period_key:
        logging.warning(
            f"Nie można znaleźć klucza technicznego dla okresu: {selected_display_period}. Używam 'Last 7 Days'."
        )
        period_key = "Last 7 Days"

    today = datetime.date.today()
    start_date, end_date = None, None

    if period_key == "Last 7 Days":
        start_date = today - datetime.timedelta(days=6)
        end_date = today
    elif period_key == "Last 30 Days":
        start_date = today - datetime.timedelta(days=29)
        end_date = today
    elif period_key == "This Month":
        start_date = today.replace(day=1)
        end_date = today
    elif period_key == "This Year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period_key == "All Time":
        first_date_ts = min(
            [g.get("date_added", time.time()) for g in self.games.values()] or [time.time()]
        )
        start_date = datetime.date.fromtimestamp(first_date_ts)
        end_date = today
    elif period_key == "Custom Range...":
        try:
            start_date = self.stats_start_date_entry.get_date()
            end_date = self.stats_end_date_entry.get_date()
            if start_date > end_date:
                messagebox.showerror(
                    "Błąd Zakresu Dat",
                    "Data początkowa nie może być późniejsza niż końcowa.",
                    parent=self.stats_page_frame,
                )
                return None, None
        except Exception as e:
            messagebox.showerror(
                "Błąd Daty",
                f"Nieprawidłowy format daty w zakresie niestandardowym: {e}",
                parent=self.stats_page_frame,
            )
            return None, None
    else:
        start_date = today - datetime.timedelta(days=6)
        end_date = today

    return start_date, end_date


__all__ = [
    "_on_period_change",
    "_get_time_period_dates",
]
