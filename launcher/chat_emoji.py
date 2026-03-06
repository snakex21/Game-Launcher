import logging
import tkinter as tk
from tkinter import ttk

from launcher.utils import THEMES


def _open_emoji_picker(self):
    """Otwiera szersze, wyśrodkowane okno Toplevel z wyborem emoji i przewijaniem."""
    if (
        hasattr(self, "_emoji_picker_window")
        and self._emoji_picker_window is not None
        and self._emoji_picker_window.winfo_exists()
    ):
        self._emoji_picker_window.lift()
        self._emoji_picker_window.focus_force()
        parent_for_centering = (
            self.chat_page_frame
            if hasattr(self, "chat_page_frame") and self.chat_page_frame.winfo_exists()
            else self.root
        )
        self._emoji_picker_window.update_idletasks()  # Wymuś aktualizację rozmiaru
        win_w = self._emoji_picker_window.winfo_width()
        win_h = self._emoji_picker_window.winfo_height()
        parent_x = parent_for_centering.winfo_rootx()
        parent_y = parent_for_centering.winfo_rooty()
        parent_w = parent_for_centering.winfo_width()
        parent_h = parent_for_centering.winfo_height()
        x = parent_x + (parent_w // 2) - (win_w // 2)
        y = parent_y + (parent_h // 2) - (win_h // 2)
        self._emoji_picker_window.geometry(f"+{x}+{y}")
        return

    parent_window_for_picker = (
        self.chat_page_frame
        if hasattr(self, "chat_page_frame") and self.chat_page_frame.winfo_exists()
        else self.root
    )
    self._emoji_picker_window = tk.Toplevel(parent_window_for_picker)
    self._emoji_picker_window.title("Wybierz Emoji")
    self._emoji_picker_window.configure(bg=self.settings.get("background", "#1e1e1e"))
    self._emoji_picker_window.transient(parent_window_for_picker)

    emoji_button_width_approx = (
        35  # Przybliżona szerokość przycisku emoji (w tym mały padding)
    )
    emoji_button_height_approx = 35  # Przybliżona wysokość przycisku emoji

    cols = 6  # Zwiększamy liczbę kolumn, np. do 6
    max_rows_visible = 4  # Ile rzędów emoji ma być widocznych bez przewijania

    # Paddingi wewnątrz ramki scrollable_emoji_buttons_frame
    inner_padding_x = 2
    inner_padding_y = 2

    # Szerokość i wysokość przycisków z uwzględnieniem wewnętrznego paddingu grid
    button_grid_total_width = cols * (emoji_button_width_approx + 2 * inner_padding_x)

    # Szerokość scrollbara (przybliżona)
    scrollbar_width_approx = 20

    # Szerokość okna
    picker_width = (
        button_grid_total_width + 2 * 5 + scrollbar_width_approx
    )  # 2*5 to padding głównej ramki emoji_canvas

    # Wysokość okna
    visible_buttons_height = max_rows_visible * (
        emoji_button_height_approx + 2 * inner_padding_y
    )
    picker_height = visible_buttons_height + 2 * 5  # 2*5 to padding głównej ramki emoji_canvas

    # Ustaw minsize, żeby scrollbar miał sens
    self._emoji_picker_window.minsize(
        picker_width, 100
    )  # Minimalna sensowna wysokość
    # self._emoji_picker_window.geometry(f"{picker_width}x{picker_height}") # Ustaw geometrię
    # Geometry ustawimy po wycentrowaniu

    main_emoji_frame = ttk.Frame(self._emoji_picker_window, style="TFrame")
    main_emoji_frame.pack(fill=tk.BOTH, expand=True)
    main_emoji_frame.rowconfigure(0, weight=1)
    main_emoji_frame.columnconfigure(0, weight=1)

    emoji_canvas = tk.Canvas(
        main_emoji_frame,
        bg=self.settings.get("background", "#1e1e1e"),
        highlightthickness=0,
    )
    emoji_canvas.grid(row=0, column=0, sticky="nsew")

    emoji_scrollbar = ttk.Scrollbar(
        main_emoji_frame, orient="vertical", command=emoji_canvas.yview
    )
    emoji_scrollbar.grid(row=0, column=1, sticky="ns")
    emoji_canvas.configure(yscrollcommand=emoji_scrollbar.set)

    self.scrollable_emoji_buttons_frame = ttk.Frame(
        emoji_canvas, style="TFrame", padding=5
    )
    scrollable_emoji_frame_id = emoji_canvas.create_window(
        (0, 0), window=self.scrollable_emoji_buttons_frame, anchor="nw"
    )

    def _configure_emoji_canvas(event):
        if (
            emoji_canvas.winfo_exists()
            and self.scrollable_emoji_buttons_frame.winfo_exists()
        ):
            canvas_width = event.width
            emoji_canvas.itemconfig(scrollable_emoji_frame_id, width=canvas_width)
            # Ważne: update_idletasks przed bbox, aby rozmiar wewnętrznej ramki był poprawny
            self.scrollable_emoji_buttons_frame.update_idletasks()
            emoji_canvas.configure(scrollregion=emoji_canvas.bbox("all"))

    emoji_canvas.bind("<Configure>", _configure_emoji_canvas)
    self.scrollable_emoji_buttons_frame.bind(
        "<Configure>",
        lambda e: (_configure_emoji_canvas(e) if emoji_canvas.winfo_exists() else None),
    )

    def _on_emoji_mousewheel(event):
        # ... (logika _on_emoji_mousewheel bez zmian) ...
        if emoji_canvas.winfo_exists():
            widget_under_cursor = (
                self._emoji_picker_window.winfo_containing(event.x_root, event.y_root)
                if hasattr(self, "_emoji_picker_window")
                and self._emoji_picker_window.winfo_exists()
                else None
            )
            is_emoji_area = False
            curr = widget_under_cursor
            while curr is not None:
                if curr == emoji_canvas:
                    is_emoji_area = True
                    break
                if curr == self._emoji_picker_window:
                    break
                try:
                    curr = curr.master
                except tk.TclError:
                    break
            if is_emoji_area:
                scroll_val = 0
                if event.num == 5 or event.delta < 0:
                    scroll_val = 1
                elif event.num == 4 or event.delta > 0:
                    scroll_val = -1
                if scroll_val != 0:
                    view_start, view_end = emoji_canvas.yview()
                    if (scroll_val < 0 and view_start > 0.0001) or (
                        scroll_val > 0 and view_end < 0.9999
                    ):
                        emoji_canvas.yview_scroll(scroll_val, "units")
                        return "break"

    emoji_canvas.bind_all("<MouseWheel>", _on_emoji_mousewheel, add="+")


    emoji_list = [
        "😊",
        "👍",
        "❤️",
        "😂",
        "😢",
        "🤔",
        "🎉",
        "👋",
        "🙏",
        "🥳",
        "🤩",
        "😭",
        "🔥",
        "💯",
        "✅",
        "🌟",
        "💡",
        "🎈",
        "🎁",
        "🎄",
        "🎃",
        "👻",
        "💀",
        "👽",
        "🤖",
        "👾",
        "💩",
        "😀",
        "😃",
        "😄",
        "😁",
        "😆",
        "😅",
        "🤣",
        "🙂",
        "🙃",
        "😉",
        "😌",
        "😍",
        "🥰",
        "😘",
        "😗",
        "😙",
        "😚",
        "😋",
        "😛",
        "😝",
        "😜",
        "🤪",
        "🤨",
        "🧐",
        "🤓",
        "😎",
        "🥸",
        "🤩",
        "🥳",
        "😏",
        "😒",
        "😞",
        "😔",
        "😟",
        "😕",
        "🙁",
        "☹️",
        "😣",
        "😖",
        "😫",
        "😩",
        "🥺",
        "😢",
        "😭",
        "😤",
        "😠",
        "😡",
        "🤬",
        "🤯",
        "😳",
        "🥵",
        "🥶",
        "😱",
        "😨",
        "😰",
        "😥",
        "😓",
        "🤗",
        "🤔",
        "🤭",
        "🤫",
        "🤥",
        "😶",
        "🫠",
        "😮",
        "😯",
        "😲",
        "😴",
        "🤤",
        "😪",
        "😵",
        "😵‍💫",
        "🤐",
        "🥴",
        "🤢",
        "🤮",
        "🤧",
        "😷",
        "🤒",
        "🤕",
        "🤑",
        "🤠",
        "😈",
        "👿",
        "👹",
        "👺",
        "🤡",
        " Poole ",
        " Oggy ",
        " Ja ",
        " Jack ",
        " Markab ",
        " Joey ",
        " DeeDee ",
        " Kot ",
        " Psy ",
        "🍕",
        "🍔",
        "🍟",
        "🌭",
        "🍿",
        "🧂",
        "🥓",
        "🥚",
        "🍳",
        "🧇",
        "🥞",
        "🧈",
        "🍞",
        "🥐",
        "🥨",
        "🥯",
    ]

    current_theme = self.settings.get("theme", "Dark")
    all_themes_dict = self.get_all_available_themes()
    theme_def_val = all_themes_dict.get(current_theme, THEMES.get("Dark", {}))
    emoji_font_color = theme_def_val.get("button_foreground", "white")
    s = ttk.Style()
    s.configure(
        "Emoji.Toolbutton.TButton",
        font=("Segoe UI Emoji", 14),
        foreground=emoji_font_color,
    )

    for i, emoji_char in enumerate(emoji_list):
        row, col = divmod(i, cols)
        btn = ttk.Button(
            self.scrollable_emoji_buttons_frame,
            text=emoji_char,
            command=lambda e=emoji_char: self._insert_emoji(e),
            width=3,
            style="Emoji.Toolbutton.TButton",
        )
        btn.grid(row=row, column=col, padx=inner_padding_x, pady=inner_padding_y)

    self._emoji_picker_window.bind(
        "<FocusOut>", lambda e: self._close_emoji_picker_if_focus_lost(e)
    )
    emoji_canvas.focus_set()

    self.scrollable_emoji_buttons_frame.update_idletasks()
    if emoji_canvas.winfo_exists():
        emoji_canvas.config(scrollregion=emoji_canvas.bbox("all"))

    # Centrowanie okna na rodzicu
    self._emoji_picker_window.update_idletasks()  # Wymuś aktualizację rozmiaru okna emoji
    win_w = self._emoji_picker_window.winfo_width()
    win_h = self._emoji_picker_window.winfo_height()

    # Jeśli wysokość przekracza założoną picker_height, ogranicz ją
    if win_h > picker_height:
        win_h = picker_height
        self._emoji_picker_window.geometry(f"{win_w}x{win_h}")  # Ustaw nową geometrię
        self._emoji_picker_window.update_idletasks()  # Ponownie, aby zmiany były uwzględnione

    parent_x = parent_window_for_picker.winfo_rootx()
    parent_y = parent_window_for_picker.winfo_rooty()
    parent_w = parent_window_for_picker.winfo_width()
    parent_h = parent_window_for_picker.winfo_height()

    x_pos = parent_x + (parent_w // 2) - (win_w // 2)
    y_pos = parent_y + (parent_h // 2) - (win_h // 2)
    self._emoji_picker_window.geometry(f"+{x_pos}+{y_pos}")


def _close_emoji_picker_if_focus_lost(self, event):
    """Zamyka okno wyboru emoji, jeśli straciło fokus na inny widget POZA tym oknem."""
    if (
        hasattr(self, "_emoji_picker_window")
        and self._emoji_picker_window.winfo_exists()
    ):
        focused_widget = self.root.focus_get()
        if focused_widget:
            # Sprawdź, czy nowo sfokusowany widget nie jest częścią okna emoji
            is_child = False
            curr = focused_widget
            while curr is not None:
                if curr == self._emoji_picker_window:
                    is_child = True
                    break
                try:
                    curr = curr.master
                except AttributeError:  # np. curr jest self.root
                    break

            if not is_child:
                self._emoji_picker_window.destroy()
                self._emoji_picker_window = None  # Wyczyść referencję
        else:  # Nic nie ma fokusu (np. kliknięto poza aplikacją)
            self._emoji_picker_window.destroy()
            self._emoji_picker_window = None


def _insert_emoji(self, emoji_char):
    """Wstawia wybrany znak emoji do pola wprowadzania wiadomości."""
    if hasattr(self, "chat_input_entry") and self.chat_input_entry.winfo_exists():
        try:
            current_cursor_pos = self.chat_input_entry.index(tk.INSERT)
            self.chat_input_var.set(
                self.chat_input_var.get()[:current_cursor_pos]
                + emoji_char
                + self.chat_input_var.get()[current_cursor_pos:]
            )
            # Ustaw kursor za wstawionym emoji
            self.chat_input_entry.icursor(current_cursor_pos + len(emoji_char))
            self.chat_input_entry.focus_set()  # Przywróć fokus do pola wpisywania
        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas wstawiania emoji: {e}")
        except Exception as e:
            logging.exception(f"Nieoczekiwany błąd podczas wstawiania emoji: {e}")


__all__ = [
    "_open_emoji_picker",
    "_close_emoji_picker_if_focus_lost",
    "_insert_emoji",
]
