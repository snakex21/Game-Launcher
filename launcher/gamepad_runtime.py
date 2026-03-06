import logging
import time

from inputs import UnpluggedError, get_gamepad


def controller_listener(self):
    """
    Obsługuje nawigację padem (Xbox / PlayStation).
    ↑↓ = scroll (kółko), ←→ = fokus poziomo,
    A/✕ = Enter, B/○ = Back, Y/△ = Page Down, X/□ = Page Up
    """
    threshold = 10000
    pad_connected = False
    while True:
        try:
            events = get_gamepad()
            if not pad_connected:
                pad_connected = True
                self.root.after(0, self._enter_big_picture_mode)

            for ev in events:
                if ev.code in ("ABS_HAT0X", "ABS_X"):
                    if ev.state == -1 or ev.state < -threshold:
                        self.root.event_generate("<Left>")
                    elif ev.state == 1 or ev.state > threshold:
                        self.root.event_generate("<Right>")

                elif ev.code in ("ABS_HAT0Y", "ABS_Y"):
                    if ev.state == -1 or ev.state < -threshold:
                        if getattr(self, "canvas", None):
                            self.canvas.yview_scroll(-1, "units")
                    elif ev.state == 1 or ev.state > threshold:
                        if getattr(self, "canvas", None):
                            self.canvas.yview_scroll(1, "units")

                elif ev.code == "BTN_SOUTH" and ev.state == 1:
                    self.root.event_generate("<Return>")

                elif ev.code == "BTN_EAST" and ev.state == 1:
                    self.root.after(0, self.show_home)

                elif ev.code in ("BTN_NORTH", "BTN_WEST") and ev.state == 1:
                    if getattr(self, "canvas", None):
                        self.canvas.yview_scroll(1, "pages")

                elif ev.code in ("BTN_WEST", "BTN_NORTH") and ev.state == 1:
                    if getattr(self, "canvas", None):
                        self.canvas.yview_scroll(-1, "pages")

            self.root.update_idletasks()

        except UnpluggedError:
            if pad_connected:
                pad_connected = False
                self.root.after(0, self._exit_big_picture_mode)
            time.sleep(1)

        except Exception as e:
            logging.error(f"Pad listener error: {e}")
            time.sleep(1)


__all__ = ["controller_listener"]
