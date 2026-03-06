from tkinter import ttk


def update_genre_menu(self):
    self.genre_options = ["Wszystkie Gatunki"] + self.get_all_genres()
    self.filter_menu.destroy()
    self.filter_menu = ttk.OptionMenu(
        self.header,
        self.filter_var,
        "Wszystkie Gatunki",
        *self.genre_options,
        command=self.update_game_grid,
    )
    self.filter_menu.grid(row=1, column=1, padx=10, pady=5, sticky="w")
    self.filter_var.set("Wszystkie Gatunki")
    self.update_game_grid()


__all__ = [
    "update_genre_menu",
]
