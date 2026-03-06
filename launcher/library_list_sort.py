import datetime
import logging


def _sort_list_view_by_column(self, column_name):
    """Sortuje dane w widoku listy po kliknięciu nagłówka kolumny."""
    if self.library_view_mode.get() != "list":
        return

    reverse_sort = False
    if column_name == self._list_sort_column:
        reverse_sort = not self._list_sort_reverse
    else:
        self._list_sort_column = column_name
        reverse_sort = False
    self._list_sort_reverse = reverse_sort

    selected_filter_or_group = self.filter_or_group_var.get()
    is_static_group = selected_filter_or_group in self.groups
    is_advanced_filter = selected_filter_or_group in self.config.get("saved_filters", {})

    search_query = self.search_var.get().lower()
    selected_genre = self.filter_var.get()
    selected_tag = self.tag_filter_var.get().strip()
    selected_game_type_filter = self.game_type_filter_var.get()

    games_to_sort = []
    if is_static_group:
        games_to_sort = list(self.groups.get(selected_filter_or_group, []))
    elif is_advanced_filter:
        logging.debug(
            f"Sortowanie listy dla filtra zaawansowanego '{selected_filter_or_group}' (logika filtrowania TODO)."
        )
        games_to_sort = list(self.games.keys())
    else:
        games_to_sort = list(self.games.keys())

    filtered_names = []
    for game_name in games_to_sort:
        game_data = self.games.get(game_name)
        if not game_data:
            continue

        game_type = game_data.get("game_type", "pc")
        type_match = False
        if selected_game_type_filter == "Wszystkie Typy":
            type_match = True
        elif selected_game_type_filter == "Gry PC" and game_type == "pc":
            type_match = True
        elif selected_game_type_filter == "Gry Emulowane" and game_type == "emulator":
            type_match = True
        if not type_match:
            continue

        if search_query and search_query not in game_name.lower():
            continue
        if selected_genre != "Wszystkie Gatunki" and selected_genre not in game_data.get("genres", []):
            continue
        if selected_tag and selected_tag != "Wszystkie Tagi":
            if not any(selected_tag.lower() == tag.lower() for tag in game_data.get("tags", [])):
                continue

        filtered_names.append(game_name)

    key_func = None
    if column_name == "Nazwa":
        key_func = lambda name: name.lower()
    elif column_name == "Czas Gry":
        key_func = lambda name: self.games.get(name, {}).get("play_time", 0)
    elif column_name == "Ocena":
        key_func = lambda name: self.games.get(name, {}).get("rating") or -1
    elif column_name == "Data Dodania":
        key_func = lambda name: self.games.get(name, {}).get("date_added", 0)
    elif column_name == "Wersja":
        key_func = lambda name: self.games.get(name, {}).get("version", "").lower()
    elif column_name == "Gatunki":
        key_func = lambda name: ", ".join(self.games.get(name, {}).get("genres", [])).lower()
    elif column_name == "Tagi":
        key_func = lambda name: ", ".join(self.games.get(name, {}).get("tags", [])).lower()

    if key_func:
        sorted_games = sorted(filtered_names, key=key_func, reverse=reverse_sort)

        self.list_view_tree.delete(*self.list_view_tree.get_children())
        for game_name in sorted_games:
            game_data = self.games.get(game_name)
            if game_data:
                play_time_str = self.format_play_time(game_data.get("play_time", 0))
                rating_str = str(game_data.get("rating", ""))
                genres_str = ", ".join(game_data.get("genres", []))
                version_str = game_data.get("version", "")
                tags_str = ", ".join(game_data.get("tags", []))
                try:
                    added_timestamp = game_data.get("date_added")
                    added_date_str = (
                        datetime.datetime.fromtimestamp(added_timestamp).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        if added_timestamp
                        else ""
                    )
                except Exception:
                    added_date_str = ""
                values = (
                    game_name,
                    play_time_str,
                    rating_str,
                    genres_str,
                    version_str,
                    tags_str,
                    added_date_str,
                )
                self.list_view_tree.insert("", "end", iid=game_name, values=values)

        for col in self.list_view_tree["columns"]:
            text = col
            if col == column_name:
                text += " ▲" if not reverse_sort else " ▼"
            self.list_view_tree.heading(col, text=text)


__all__ = ["_sort_list_view_by_column"]
