import logging
import time

from launcher.utils import save_config


def monitor_game_sessions(self):
    """Monitoruje wszystkie gry i śledzi czas gry niezależnie od sposobu uruchomienia."""
    while True:
        active_game_names = list(self.games.keys())
        for game_name in active_game_names:
            if game_name not in self.games:
                if game_name in self.tracking_games:
                    del self.tracking_games[game_name]
                continue

            if self.is_game_running(game_name):
                if game_name not in self.tracking_games:
                    self.tracking_games[game_name] = time.time()
                    self.games[game_name]["last_played"] = time.time()
                    logging.info(f"Rozpoczęto śledzenie gry: {game_name}")
            else:
                if game_name in self.tracking_games:
                    start_time = self.tracking_games.pop(game_name)
                    end_time = time.time()
                    elapsed = end_time - start_time
                    self.games[game_name]["play_time"] = (
                        self.games[game_name].get("play_time", 0) + elapsed
                    )
                    self.games[game_name].setdefault("play_sessions", []).append(
                        {"start": start_time, "end": end_time}
                    )

                    roadmap_updated = False
                    for game in self.roadmap:
                        if (
                            game["game_name"] == game_name
                            and game["status"] == "Planowana"
                        ):
                            game["time_spent"] = game.get("time_spent", 0) + elapsed
                            roadmap_updated = True
                            break

                    save_config(self.config)
                    logging.info(
                        f"Zakończono śledzenie gry: {game_name}, czas: {elapsed:.2f} sekund"
                    )
                    self._update_discord_status(status_type="idle")
                    self.root.after(0, self._update_button_on_game_close, game_name)
                    if self.settings.get("auto_backup_on_exit", True):
                        self.root.after(
                            10,
                            lambda gn=game_name: self._create_or_overwrite_autosave(gn),
                        )

                    self.root.after(
                        150, lambda gn=game_name: self.prompt_checklist_update(gn)
                    )
                    self.root.after(250, lambda gn=game_name: self.prompt_completion(gn))
        time.sleep(5)


__all__ = ["monitor_game_sessions"]
