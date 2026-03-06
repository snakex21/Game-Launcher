import logging


def show_statistics_page(self):
    """Pokazuje stronę statystyk, tworząc ją przy pierwszym użyciu."""
    if not self.stats_page_frame.winfo_children():
        logging.info("Tworzenie zawartości strony Statystyk po raz pierwszy.")
        self.create_statistics_page()

    self.stats_page_frame.grid()
    self.stats_page_frame.tkraise()
    self.current_frame = self.stats_page_frame
    self.current_section = "Przegląda Statystyki"
    self._update_discord_status(status_type="browsing", activity_details=self.current_section)
    self._update_launcher_usage_display()


__all__ = [
    "show_statistics_page",
]
