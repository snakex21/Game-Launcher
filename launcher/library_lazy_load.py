import logging
import tkinter as tk
from tkinter import ttk


def _on_search_change(self, *args):
    """Obsługuje zmianę w polu wyszukiwania z opóźnieniem (debouncing)."""
    if self._search_timer_id:
        self.root.after_cancel(self._search_timer_id)

    debounce_delay_ms = 400
    self._search_timer_id = self.root.after(debounce_delay_ms, self.update_game_grid)


def on_canvas_configure_and_lazy_load(self, event):
    """Obsługuje zmianę rozmiaru canvas i inicjuje lazy loading."""
    if hasattr(self, "canvas") and self.canvas.winfo_exists():
        self.canvas_width = event.width
        self.canvas.itemconfig(self.games_frame_id, width=event.width)
        self._trigger_lazy_load()


def _on_mouse_wheel_and_lazy_load(self, event):
    """Przewijanie za pomocą kółka myszy i inicjowanie lazy loadingu."""
    widget_under_cursor = None
    try:
        widget_under_cursor = self.root.winfo_containing(event.x_root, event.y_root)
    except (tk.TclError, KeyError) as e:
        logging.debug(f"Ignorowany błąd w winfo_containing (lazy_load): {e}")
        widget_under_cursor = None

    is_related_to_canvas = False
    curr = widget_under_cursor
    while curr is not None:
        if curr == self.canvas:
            is_related_to_canvas = True
            break
        if curr == self.root:
            break
        try:
            curr = curr.master
        except tk.TclError:
            break

    if is_related_to_canvas and hasattr(self, "canvas") and self.canvas.winfo_exists():
        scroll_amount = -1 * int(event.delta / 120)
        view_start, view_end = self.canvas.yview()
        if 0.0 <= view_start <= 1.0 and 0.0 <= view_end <= 1.0:
            if (scroll_amount < 0 and view_start > 0.0) or (
                scroll_amount > 0 and view_end < 1.0
            ):
                self.canvas.yview_scroll(scroll_amount, "units")
                self._trigger_lazy_load()
                return "break"
        else:
            logging.warning("Niespójny stan yview dla canvas (lazy_load)")


def _trigger_lazy_load(self, event=None):
    """Pomocnicza funkcja do inicjowania lazy loadingu."""
    self.root.after(10, self._load_visible_tiles)


def _load_visible_tiles(self):
    """Ładuje zawartość tylko dla widocznych kafelków-placeholderów."""
    if (
        not hasattr(self, "canvas")
        or not self.canvas.winfo_exists()
        or not hasattr(self, "games_frame")
    ):
        return

    try:
        _canvas_height = self.canvas.winfo_height()
        scroll_region = self.canvas.yview()
        visible_top = scroll_region[0] * self.games_frame.winfo_reqheight()
        visible_bottom = scroll_region[1] * self.games_frame.winfo_reqheight()

        buffer = self.tile_height

        current_width = getattr(self, "current_tile_width", 200)
        current_height = self.tile_height

        for tile_frame in self.games_frame.winfo_children():
            if hasattr(tile_frame, "game_info") and not tile_frame.game_info["loaded"]:
                frame_y = tile_frame.winfo_y()
                frame_height = tile_frame.winfo_height()
                if frame_height == 1:
                    frame_height = current_height

                is_visible = (
                    frame_y + frame_height > visible_top - buffer
                    and frame_y < visible_bottom + buffer
                )

                if is_visible:
                    game_name = tile_frame.game_info["name"]
                    game_data = self.games.get(game_name)
                    if game_data:
                        self._populate_game_tile(
                            tile_frame,
                            game_name,
                            game_data,
                            current_width,
                            current_height,
                        )
                        tile_frame.game_info["loaded"] = True
                    else:
                        logging.warning(
                            f"Nie znaleziono danych dla gry '{game_name}' podczas lazy loadingu."
                        )

    except tk.TclError as e:
        logging.warning(f"Błąd TclError podczas lazy loadingu: {e}")
    except Exception:
        logging.exception("Nieoczekiwany błąd podczas lazy loadingu")


def _create_tile_placeholder(
    self,
    parent,
    game_name,
    row,
    col,
    padx_config,
    pady_config,
    tile_width,
    tile_height,
):
    """Tworzy pustą ramkę (placeholder) dla kafelka gry."""
    game_frame = ttk.Frame(
        parent,
        width=tile_width,
        height=tile_height,
        style="Game.TFrame",
        borderwidth=1,
        relief="solid",
    )
    game_frame.grid(row=row, column=col, padx=padx_config, pady=pady_config, sticky="nsew")
    game_frame.grid_propagate(False)
    game_frame.game_info = {"name": game_name, "loaded": False}
    return game_frame


__all__ = [
    "_on_search_change",
    "on_canvas_configure_and_lazy_load",
    "_on_mouse_wheel_and_lazy_load",
    "_trigger_lazy_load",
    "_load_visible_tiles",
    "_create_tile_placeholder",
]
