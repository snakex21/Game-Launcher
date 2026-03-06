import logging
import time

from plyer import notification

from launcher.utils import save_config


def _reload_definitions_and_refresh_ui(self):
    """Wczytuje ponownie definicje z pliku i odświeża UI."""
    self._load_achievement_definitions()
    if hasattr(self, "achievements_def_tree") and self.achievements_def_tree.winfo_exists():
        self._load_achievement_def_list()
    self.check_and_unlock_achievements()
    logging.info("Odświeżono definicje osiągnięć i interfejs.")


def show_achievements_page(self):
    self.achievements_frame.grid()
    self.achievements_frame.tkraise()
    self.current_frame = self.achievements_frame

    if not self._achievements_initialized:
        logging.info("Tworzenie zawartości strony Osiągnięć po raz pierwszy (lazy init).")
        self.create_achievements_page()
        self._achievements_initialized = True
    else:
        if hasattr(self, "_reload_definitions_and_refresh_ui"):
            self._reload_definitions_and_refresh_ui()
        else:
            self.create_achievements_page()

    self.current_section = "Przegląda Osiągnięcia"
    self._update_discord_status(
        status_type="browsing", activity_details=self.current_section
    )
    logging.info("Wyświetlono stronę osiągnięć.")


def check_and_unlock_achievements(self):
    """Sprawdza warunki odblokowania osiągnięć, aktualizuje postęp i odblokowuje (Rozbudowana)."""
    if not self.achievement_definitions:
        return

    user_achievements = self.user.setdefault("achievements", {})
    something_changed = False

    library_size = len(self.games)
    total_playtime_seconds = sum(g.get("play_time", 0) for g in self.games.values())
    total_playtime_hours = round(total_playtime_seconds / 3600, 2)
    games_launched_count = sum(1 for g in self.games.values() if g.get("play_count", 0) > 0)
    games_completed_100 = sum(1 for g in self.games.values() if g.get("completion", 0) >= 100)
    max_single_game_playtime_hours = max(
        (g.get("play_time", 0) / 3600 for g in self.games.values()), default=0
    )
    roadmap_completed = len(self.archive)
    rated_count = sum(1 for g in self.games.values() if g.get("rating") is not None)
    groups_created_count = len(self.groups)
    games_with_tags_count = sum(1 for g in self.games.values() if g.get("tags"))
    themes_changed_count = self.user.get("theme_change_count", 0)
    mods_installed_count = sum(
        len(p.get("mods", {}))
        for g_data in self.mods_data.values()
        for p in g_data.get("profiles", {}).values()
    )
    consecutive_days = self.local_settings.get("consecutive_days", 0)

    for achievement_def in self.achievement_definitions:
        ach_id = achievement_def.get("id")
        if not ach_id:
            continue

        ach_progress_data = user_achievements.setdefault(
            ach_id, {"unlocked": False, "timestamp": None, "current_progress": 0}
        )

        if ach_progress_data.get("unlocked"):
            continue

        rule_type = achievement_def.get("rule_type")
        target_value = achievement_def.get("target_value")
        current_value = 0
        update_progress = False
        unlocked_now = False

        try:
            if rule_type == "games_launched_count":
                current_value = games_launched_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "library_size":
                current_value = library_size
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "total_playtime_hours":
                current_value = total_playtime_hours
                update_progress = True
                try:
                    target_value = float(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą")
            elif rule_type == "games_completed_100":
                current_value = games_completed_100
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "playtime_single_game_hours":
                current_value = round(max_single_game_playtime_hours, 2)
                update_progress = True
                try:
                    target_value = float(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą")
            elif rule_type == "genre_played_count":
                required_genre = achievement_def.get("genre")
                if required_genre:
                    current_value = sum(
                        1
                        for g_name, g_data in self.games.items()
                        if g_data.get("play_count", 0) > 0 and required_genre in g_data.get("genres", [])
                    )
                    update_progress = True
                    try:
                        target_value = int(target_value)
                    except ValueError:
                        raise ValueError("Wartość docelowa musi być liczbą całkowitą")
                else:
                    logging.warning(
                        f"Brak parametru 'genre' w definicji osiągnięcia {ach_id}"
                    )
                    continue
            elif rule_type == "roadmap_completed_count":
                current_value = roadmap_completed
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "games_rated_count":
                current_value = rated_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type in ["genre_played_count", "genre_completed_100"]:
                required_genre = achievement_def.get("genre")
                if required_genre:
                    if rule_type == "genre_played_count":
                        current_value = sum(
                            1
                            for g_data in self.games.values()
                            if g_data.get("play_count", 0) > 0 and required_genre in g_data.get("genres", [])
                        )
                    else:
                        current_value = sum(
                            1
                            for g_data in self.games.values()
                            if g_data.get("completion", 0) >= 100 and required_genre in g_data.get("genres", [])
                        )
                    update_progress = True
                    try:
                        target_value = int(target_value)
                    except ValueError:
                        raise ValueError("Wartość docelowa musi być liczbą całkowitą")
                else:
                    logging.warning(f"Brak parametru 'genre' dla {ach_id}")
                    continue

            elif rule_type in ["tag_played_count", "tag_completed_100"]:
                required_tag = achievement_def.get("tag")
                if required_tag:
                    if rule_type == "tag_played_count":
                        current_value = sum(
                            1
                            for g_data in self.games.values()
                            if g_data.get("play_count", 0) > 0 and required_tag in g_data.get("tags", [])
                        )
                    else:
                        current_value = sum(
                            1
                            for g_data in self.games.values()
                            if g_data.get("completion", 0) >= 100 and required_tag in g_data.get("tags", [])
                        )
                    update_progress = True
                    try:
                        target_value = int(target_value)
                    except ValueError:
                        raise ValueError("Wartość docelowa musi być liczbą całkowitą")
                else:
                    logging.warning(f"Brak parametru 'tag' dla {ach_id}")
                    continue

            elif rule_type in ["group_played_count", "group_completed_100"]:
                required_group = achievement_def.get("group")
                if required_group and required_group in self.groups:
                    group_games = self.groups[required_group]
                    if rule_type == "group_played_count":
                        current_value = sum(
                            1
                            for g_name in group_games
                            if self.games.get(g_name, {}).get("play_count", 0) > 0
                        )
                    else:
                        current_value = sum(
                            1
                            for g_name in group_games
                            if self.games.get(g_name, {}).get("completion", 0) >= 100
                        )
                    update_progress = True
                    try:
                        target_value = int(target_value)
                    except ValueError:
                        raise ValueError("Wartość docelowa musi być liczbą całkowitą")
                else:
                    logging.warning(
                        f"Brak parametru 'group' lub grupa nie istnieje dla {ach_id}"
                    )
                    continue

            elif rule_type == "groups_created":
                current_value = groups_created_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "games_with_tags":
                current_value = games_with_tags_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "roadmap_items_added":
                current_value = len(self.roadmap)
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "themes_changed":
                current_value = themes_changed_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "game_launched_at_night":
                current_value = 1 if ach_progress_data.get("_triggered_at_night") else 0
                target_value = 1
            elif rule_type == "consecutive_days_used":
                current_value = consecutive_days
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")
            elif rule_type == "mods_installed":
                current_value = mods_installed_count
                update_progress = True
                try:
                    target_value = int(target_value)
                except ValueError:
                    raise ValueError("Wartość docelowa musi być liczbą całkowitą")

            if update_progress and ach_progress_data.get("current_progress") != current_value:
                ach_progress_data["current_progress"] = current_value
                something_changed = True
                logging.debug(
                    f"Zaktualizowano postęp dla '{ach_id}': {current_value} / {target_value}"
                )

            epsilon = 0.001
            if isinstance(target_value, float):
                if current_value >= target_value - epsilon:
                    unlocked_now = True
            elif isinstance(target_value, int):
                if current_value >= target_value:
                    unlocked_now = True

        except ValueError as ve:
            logging.error(f"Błąd wartości docelowej dla '{ach_id}': {ve}")
            continue
        except Exception as e:
            logging.error(f"Błąd sprawdzania '{ach_id}': {e}")
            continue

        if unlocked_now and not ach_progress_data.get("unlocked"):
            logging.info(f"Odblokowano osiągnięcie: {ach_id}!")
            timestamp = time.time()
            ach_progress_data["unlocked"] = True
            ach_progress_data["timestamp"] = timestamp
            ach_progress_data["current_progress"] = target_value
            ach_progress_data.pop("_triggered_at_night", None)
            something_changed = True
            ach_name = achievement_def.get("name", ach_id)
            ach_desc = achievement_def.get("description", "")
            try:
                self.root.after(
                    100,
                    lambda name=ach_name, desc=ach_desc: notification.notify(
                        title="Osiągnięcie Odblokowane!",
                        message=f"{name}\n{desc}",
                        app_name="Game Launcher",
                        timeout=10,
                    ),
                )
            except Exception as e_notify:
                logging.error(f"Błąd powiadomienia: {e_notify}")

    if something_changed:
        save_config(self.config)
        if hasattr(self, "achievements_frame") and self.current_frame == self.achievements_frame:
            if hasattr(self, "create_achievements_page"):
                self.root.after(50, self.create_achievements_page)


__all__ = [
    "check_and_unlock_achievements",
    "_reload_definitions_and_refresh_ui",
    "show_achievements_page",
]
