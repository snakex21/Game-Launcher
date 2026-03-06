import logging


def show_music_page(self):
    """Pokazuje stronę odtwarzacza muzyki, tworząc ją przy pierwszym użyciu."""
    from ui.music_player import MusicPlayerPage

    self._hide_library_components()

    if self.music_player_page_instance is None:
        logging.info("Tworzenie instancji MusicPlayerPage po raz pierwszy.")
        self.music_player_page_instance = MusicPlayerPage(self.music_page_frame, self)

    self.music_page_frame.grid()
    self.music_page_frame.tkraise()
    self.current_frame = self.music_page_frame
    self.current_section = "Przegląda Muzykę"
    self._update_discord_status(
        status_type="browsing", activity_details=self.current_section
    )
    self._update_overlay_regularly()


__all__ = [
    "show_music_page",
]
