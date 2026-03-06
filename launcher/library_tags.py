import logging
import tkinter as tk


def get_all_tags(self):
    """Zbiera unikalne tagi ze wszystkich gier."""
    all_tags = set()
    for game_data in self.games.values():
        tags = game_data.get("tags", [])
        if isinstance(tags, list):
            all_tags.update(tag.strip() for tag in tags if tag.strip())
    return sorted(list(all_tags), key=str.lower)


def update_tag_filter_options(self):
    """Aktualizuje listę dostępnych tagów w OptionMenu."""
    if not hasattr(self, "tag_filter_menu") or not self.tag_filter_menu.winfo_exists():
        logging.warning(
            "update_tag_filter_options: OptionMenu tagów nie istnieje, pomijam aktualizację."
        )
        return

    menu = self.tag_filter_menu["menu"]
    menu.delete(0, "end")

    available_tags = ["Wszystkie Tagi"] + self.get_all_tags()

    current_filter = self.tag_filter_var.get()
    if current_filter not in available_tags:
        self.tag_filter_var.set("Wszystkie Tagi")

    for tag in available_tags:
        menu.add_command(
            label=tag,
            command=tk._setit(self.tag_filter_var, tag, self.reset_and_update_grid),
        )


__all__ = [
    "get_all_tags",
    "update_tag_filter_options",
]
