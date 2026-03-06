import time
import tkinter as tk


def _update_overlay_regularly(self):
    """Pobiera dane z odtwarzacza i aktualizuje overlay, jeśli jest widoczny."""
    if self.overlay_update_timer:
        self.root.after_cancel(self.overlay_update_timer)
        self.overlay_update_timer = None

    should_show_overlay = False
    if hasattr(self, "show_track_overlay_var"):
        try:
            should_show_overlay = self.show_track_overlay_var.get()
        except tk.TclError:
            should_show_overlay = self.local_settings.get("show_track_overlay", False)

    if (
        hasattr(self, "track_overlay")
        and self.track_overlay
        and self.track_overlay.winfo_exists()
        and self.track_overlay.winfo_viewable()
        and hasattr(self, "music_player_page_instance")
        and self.music_player_page_instance
    ):
        player = self.music_player_page_instance
        track_name_disp = "Nic nie gra..."
        current_t_sec = 0.0
        total_t_sec = 0.0
        is_actually_playing_or_paused = player.is_playing

        if (
            player.is_playing
            and player.current_track_index != -1
            and player.current_track_index < len(player.playlist)
        ):
            current_entry = player.playlist[player.current_track_index]
            track_name_disp = (
                player._get_display_name_for_track(current_entry)
                .replace("♥ ", "")
                .strip()
            )
            total_t_sec = getattr(player, "_current_track_duration_sec", 0.0)

            if not player.is_paused:
                if hasattr(player, "_start_time") and hasattr(player, "_pause_acc"):
                    current_t_sec = time.monotonic() - player._start_time - player._pause_acc
                    current_t_sec = max(0, current_t_sec)
                    if total_t_sec > 0:
                        current_t_sec = min(current_t_sec, total_t_sec)
            else:
                if (
                    hasattr(player, "_pause_start")
                    and hasattr(player, "_start_time")
                    and hasattr(player, "_pause_acc")
                ):
                    current_t_sec = (
                        player._pause_start - player._start_time - player._pause_acc
                    )
                    current_t_sec = max(0, current_t_sec)
                    if total_t_sec > 0:
                        current_t_sec = min(current_t_sec, total_t_sec)

        self.track_overlay.update_display(
            track_name_disp,
            current_t_sec,
            total_t_sec,
            is_actually_playing_or_paused,
        )

    if should_show_overlay:
        self.overlay_update_timer = self.root.after(250, self._update_overlay_regularly)


__all__ = [
    "_update_overlay_regularly",
]
