import logging
import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from launcher.utils import GAMES_FOLDER, IMAGES_FOLDER, save_config
from ui.game_details import GameDetailsWindow
from ui.game_form import GameForm


def add_game(self):
    add_window = GameForm(self, "Dodaj Grę")
    self.root.wait_window(add_window.top)
    if add_window.result:
        game_name, game_data = add_window.result
        if game_name in self.games:
            messagebox.showwarning("Błąd", "Gra o tej nazwie już istnieje.")
            return

        game_data["date_added"] = time.time()
        game_data["play_time"] = 0
        game_data["completion"] = 0
        game_data["last_played"] = None
        game_data["play_sessions"] = []
        game_data["launch_profiles"] = [
            {
                "name": "Default",
                "exe_path": None,
                "arguments": "",
            }
        ]
        self.games[game_name] = game_data

        import_saves = messagebox.askyesno(
            "Importowanie zapisów",
            f"Czy chcesz zaimportować zapisy gry '{game_name}'?",
        )
        if import_saves:
            source = filedialog.askdirectory(title="Wybierz folder z zapisami gry")
            if source:
                destination = os.path.join(GAMES_FOLDER, game_name)
                os.makedirs(destination, exist_ok=True)
                try:
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                    messagebox.showinfo("Sukces", "Zapisy zostały zaimportowane.")
                except Exception as e:
                    messagebox.showerror("Błąd", f"Nie udało się zaimportować zapisów: {e}")

        save_config(self.config)
        self.check_and_unlock_achievements()
        self.check_and_unlock_achievements()
        self.reset_and_update_grid()
        self.update_tag_filter_options()
        if hasattr(self, "roadmap_game_name"):
            self.roadmap_game_name["values"] = list(self.games.keys())


def edit_game(self, game_name):
    if game_name not in self.games:
        messagebox.showerror("Błąd", f"Gra '{game_name}' nie została znaleziona.")
        return

    game_data_original = self.games[game_name].copy()
    game_data_original["name"] = game_name

    edit_window = GameForm(self, "Edytuj Grę", game_name, game_data_original)
    self.root.wait_window(edit_window.top)

    if edit_window.result:
        returned_name, new_game_data = edit_window.result

        stats_to_preserve = {
            "play_time": game_data_original.get("play_time", 0),
            "completion": game_data_original.get("completion", 0),
            "last_played": game_data_original.get("last_played", None),
            "play_sessions": game_data_original.get("play_sessions", []),
            "date_added": game_data_original.get("date_added", time.time()),
        }
        final_game_data = {**new_game_data, **stats_to_preserve}

        self.games[returned_name] = final_game_data
        save_config(self.config)
        self.check_and_unlock_achievements()
        logging.debug(
            f"Dane gry '{returned_name}' zaktualizowane. Wymuszanie odświeżenia UI."
        )

        self.reset_and_update_grid()
        self.root.after(100, lambda gn=returned_name: self._force_refresh_tile(gn))
        self.update_tag_filter_options()
        self.create_home_page()

        details_title = f"Szczegóły Gry - {game_name}"
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.title() == details_title:
                if isinstance(widget, GameDetailsWindow):
                    logging.debug(
                        f"Odświeżanie otwartego okna szczegółów dla: {game_name}"
                    )
                    widget.refresh_details_data()
                    break


def _force_refresh_tile(self, game_name):
    """Wymusza ponowne załadowanie zawartości konkretnego kafelka."""
    logging.debug(f"Próba wymuszonego odświeżenia kafelka dla: {game_name}")
    if self.library_view_mode.get() != "tiles":
        logging.debug("Widok inny niż kafelki, pomijam wymuszone odświeżenie.")
        return

    tile_frame_widget = None
    if hasattr(self, "games_frame") and self.games_frame.winfo_exists():
        for widget in self.games_frame.winfo_children():
            if hasattr(widget, "game_info") and widget.game_info["name"] == game_name:
                tile_frame_widget = widget
                break

    if tile_frame_widget and tile_frame_widget.winfo_exists():
        logging.info(f"Znaleziono kafelek dla '{game_name}'. Wywołuję _populate_game_tile.")
        game_data = self.games.get(game_name)
        if game_data:
            current_width = getattr(self, "current_tile_width", 200)
            current_height = self.tile_height
            self._populate_game_tile(
                tile_frame_widget,
                game_name,
                game_data,
                current_width,
                current_height,
            )
            tile_frame_widget.update_idletasks()
            self.canvas.update_idletasks()
        else:
            logging.warning(
                f"Nie znaleziono danych dla gry '{game_name}' podczas wymuszonego odświeżania."
            )
    else:
        logging.warning(
            f"Nie znaleziono widocznego kafelka dla '{game_name}' do wymuszonego odświeżenia."
        )


def delete_game(self, game_name):
    confirm = messagebox.askyesno(
        "Usuń Grę", f"Czy na pewno chcesz usunąć grę '{game_name}'?"
    )
    if confirm:
        if game_name in self.games:
            cover_image = self.games[game_name].get("cover_image")
            if cover_image and os.path.exists(cover_image):
                if os.path.dirname(os.path.abspath(cover_image)) == os.path.abspath(
                    IMAGES_FOLDER
                ):
                    try:
                        os.remove(cover_image)
                        logging.info(f"Usunięto zarządzaną okładkę: {cover_image}")
                    except OSError as e:
                        logging.error(
                            f"Nie udało się usunąć okładki {cover_image}: {e}"
                        )
                else:
                    logging.info(f"Okładka {cover_image} nie jest zarządzana, nie usuwam.")

            backup_path = os.path.join(GAMES_FOLDER, game_name)
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)

            for group in self.groups.values():
                if game_name in group:
                    group.remove(game_name)

            del self.games[game_name]
            save_config(self.config)

            self.reset_and_update_grid()
            self.update_tag_filter_options()
            if hasattr(self, "roadmap_game_name"):
                self.roadmap_game_name["values"] = list(self.games.keys())

            if hasattr(self, "home_frame"):
                self.root.after(0, self._update_home_lists)
                self.root.after(0, self.update_time_stats)
        else:
            messagebox.showwarning("Błąd", "Gra nie istnieje w bazie danych.")


__all__ = ["add_game", "edit_game", "_force_refresh_tile", "delete_game"]
