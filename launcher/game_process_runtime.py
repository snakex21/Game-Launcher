import datetime
import logging
import os
import shlex
import subprocess
import time
import tkinter as tk
from tkinter import messagebox

import psutil

from launcher.utils import save_config
from ui.components import ToolTip


def launch_game(self, game_name, profile=None):
    """Uruchamia wybraną grę (PC lub emulowaną)."""
    game = self.games.get(game_name)
    if not game:
        messagebox.showerror("Błąd", "Nie znaleziono gry.")
        return

    game_type = game.get("game_type", "pc")

    command = []
    args_to_add = []
    profile_name_for_log = "Default"
    log_msg = ""

    try:
        if game_type == "pc":
            exe_to_run = game.get("exe_path")
            profile_name_for_log = "Default (PC)"

            if profile and isinstance(profile, dict):
                profile_name_for_log = profile.get("name", "Unknown Profile")
                profile_exe = profile.get("exe_path")
                profile_args_str = profile.get("arguments", "")
                if profile_exe:
                    exe_to_run = profile_exe
                    profile_name_for_log += " (profile exe)"
                elif not exe_to_run:
                    messagebox.showerror("Błąd", "...")
                    return
                if profile_args_str:
                    try:
                        args_to_add = shlex.split(profile_args_str)
                    except ValueError:
                        messagebox.showerror("Błąd Argumentów", "...")
                        return
            elif not exe_to_run:
                messagebox.showerror("Błąd", "...")
                return

            if not exe_to_run or not os.path.exists(exe_to_run):
                messagebox.showerror("Błąd", "...")
                return

            command = [exe_to_run] + args_to_add
            log_msg = f"Uruchamianie gry PC: {game_name} (Profil: {profile_name_for_log}) z poleceniem: {command}"

        elif game_type == "emulator":
            emulator_name = game.get("emulator_name")
            rom_path = game.get("rom_path")
            emulator_args_str = game.get("emulator_args", "")
            profile_name_for_log = f"Emulator: {emulator_name}"

            if not emulator_name or not rom_path:
                messagebox.showerror("Błąd Konfiguracji", "...")
                return
            emulator_config = self.config.get("emulators", {}).get(emulator_name)
            if not emulator_config or not emulator_config.get("path"):
                messagebox.showerror("Błąd Emulatora", "...")
                return
            emulator_exe_path = emulator_config["path"]
            if not os.path.exists(emulator_exe_path):
                messagebox.showerror("Błąd Ścieżki", "...")
                return
            if not os.path.exists(rom_path):
                messagebox.showerror("Błąd Ścieżki", "...")
                return
            if emulator_args_str:
                try:
                    args_to_add = shlex.split(emulator_args_str)
                except ValueError:
                    messagebox.showerror("Błąd Argumentów", "...")
                    return

            command = [emulator_exe_path] + args_to_add + [rom_path]
            log_msg = f"Uruchamianie gry emulowanej: {game_name} (Emulator: {emulator_name}) z poleceniem: {command}"

        else:
            messagebox.showerror(
                "Błąd", f"Nieznany typ gry '{game_type}' dla '{game_name}'."
            )
            return

        now_hour = datetime.datetime.now().hour
        ach_id_night = "night_owl"
        user_achievements = self.user.setdefault("achievements", {})
        if 2 <= now_hour < 4:
            if ach_id_night not in user_achievements or not user_achievements[
                ach_id_night
            ].get("_triggered_at_night"):
                logging.info(
                    "Wykryto uruchomienie gry w nocy (2-4). Oznaczanie do sprawdzenia."
                )
                ach_progress_data = user_achievements.setdefault(
                    ach_id_night,
                    {"unlocked": False, "timestamp": None, "current_progress": 0},
                )
                ach_progress_data["_triggered_at_night"] = True

        logging.info(log_msg)
        try:
            process = subprocess.Popen(command)
            self.processes[game_name] = process
        except OSError as e:
            if e.winerror == 740:
                logging.error(
                    f"Błąd uruchamiania '{game_name}': Wymagane uprawnienia administratora (WinError 740)."
                )
                messagebox.showerror(
                    "Błąd Uprawnień",
                    f"Nie można uruchomić gry '{game_name}'.\n\n"
                    f"Ta gra wymaga uprawnień administratora, a launcher został uruchomiony bez nich.\n\n"
                    f"Możliwe rozwiązania:\n"
                    f"1. Uruchom launcher ponownie, klikając prawym przyciskiem myszy i wybierając 'Uruchom jako administrator' (mniej bezpieczne).\n"
                    f"2. Sprawdź właściwości pliku .exe gry (zakładka Zgodność) i odznacz 'Uruchom ten program jako administrator', jeśli to możliwe.",
                    parent=self.root,
                )
                return
            else:
                logging.exception(
                    f"Nie udało się uruchomić gry '{game_name}' (inny OSError: {e})"
                )
                messagebox.showerror(
                    "Błąd Uruchamiania",
                    f"Nie udało się uruchomić gry '{game_name}':\n{e}",
                )
                return
        except Exception as e:
            logging.exception(f"Nie udało się uruchomić gry '{game_name}'")
            messagebox.showerror(
                "Błąd Uruchamiania",
                f"Nie udało się uruchomić gry '{game_name}':\n{e}",
            )
            return

        game["last_played"] = time.time()
        game["play_count"] = game.get("play_count", 0) + 1
        start_time = time.time()
        self.game_start_times[game_name] = start_time

        if game_name in self._launch_buttons:
            button = self._launch_buttons[game_name]
            if button.winfo_exists():
                stop_icon_tk = self._button_icons.get("stop_btn")
                close_command = lambda: self.close_game(game_name)
                tooltip_text = "Zamknij"
                if stop_icon_tk:
                    button.config(
                        image=stop_icon_tk,
                        style="Red.TButton",
                        command=close_command,
                    )
                    if hasattr(button, "tooltip") and button.tooltip:
                        button.tooltip.update_text(tooltip_text)
                else:
                    button.config(
                        image="",
                        text="Zamknij",
                        style="Red.TButton",
                        command=close_command,
                    )
                    if hasattr(button, "tooltip") and button.tooltip:
                        button.tooltip.update_text(tooltip_text)
                    else:
                        button.tooltip = ToolTip(button, tooltip_text)

                profile_menu_key = f"{game_name}_profile_menu"
                if profile_menu_key in self._launch_buttons:
                    menu_button = self._launch_buttons[profile_menu_key]
                    if menu_button.winfo_exists():
                        menu_button.pack_forget()

        self._update_discord_status(
            status_type="in_game",
            game_name=game_name,
            profile_name=profile_name_for_log,
            start_time=start_time,
        )

        save_config(self.config)

    except Exception as e:
        logging.exception(f"Nie udało się uruchomić gry '{game_name}'")
        messagebox.showerror(
            "Błąd Uruchamiania", f"Nie udało się uruchomić gry '{game_name}':\n{e}"
        )


def is_game_running(self, game_name):
    """Sprawdza, czy proces gry (PC lub emulowanej) jest uruchomiony."""
    game_data = self.games.get(game_name)
    if not game_data:
        return False

    game_type = game_data.get("game_type", "pc")

    if game_type == "pc":
        exe_paths_to_check = set()
        if game_data.get("exe_path"):
            exe_paths_to_check.add(os.path.abspath(game_data["exe_path"]))
        for profile in game_data.get("launch_profiles", []):
            if profile.get("exe_path"):
                exe_paths_to_check.add(os.path.abspath(profile["exe_path"]))

        if not exe_paths_to_check:
            return False

        exe_names_to_check = {os.path.basename(p).lower() for p in exe_paths_to_check}

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                proc_name_lower = proc.info["name"].lower()
                proc_exe_abs = (
                    os.path.abspath(proc.info["exe"]) if proc.info["exe"] else None
                )

                if proc_name_lower in exe_names_to_check:
                    return True
                if proc_exe_abs and proc_exe_abs in exe_paths_to_check:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, OSError):
                continue
        return False

    elif game_type == "emulator":
        emulator_name = game_data.get("emulator_name")
        if not emulator_name:
            return False

        emulator_config = self.config.get("emulators", {}).get(emulator_name)
        if not emulator_config or not emulator_config.get("path"):
            return False

        emulator_exe_path = emulator_config["path"]
        if not emulator_exe_path:
            return False

        emulator_exe_path_abs = os.path.abspath(emulator_exe_path)
        emulator_exe_name_lower = os.path.basename(emulator_exe_path_abs).lower()

        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                proc_name_lower = proc.info["name"].lower()
                proc_exe_abs = (
                    os.path.abspath(proc.info["exe"]) if proc.info["exe"] else None
                )

                if proc_name_lower == emulator_exe_name_lower or (
                    proc_exe_abs and proc_exe_abs == emulator_exe_path_abs
                ):
                    rom_path = game_data.get("rom_path")
                    if rom_path and proc.info["cmdline"]:
                        norm_rom_path = os.path.normcase(os.path.abspath(rom_path))
                        if any(
                            norm_rom_path in os.path.normcase(arg)
                            for arg in proc.info["cmdline"]
                        ):
                            logging.debug(
                                f"Znaleziono proces emulatora ({proc.pid}) z pasującą ścieżką ROM dla '{game_name}'."
                            )
                            return True
                        else:
                            logging.debug(
                                f"Znaleziono proces emulatora ({proc.pid}), ale linia komend nie pasuje do ROMu '{game_name}'."
                            )
                            continue
                    else:
                        logging.warning(
                            f"Znaleziono proces emulatora dla '{game_name}', ale nie można zweryfikować ROMu w linii komend."
                        )
                        return True

            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, OSError):
                continue
        return False

    else:
        logging.error(
            f"Nieznany typ gry '{game_type}' w is_game_running dla '{game_name}'."
        )
        return False


def close_game(self, game_name):
    """Zamyka proces gry (PC lub emulowanej)."""
    game_data = self.games.get(game_name)
    if not game_data:
        logging.error(f"Próba zamknięcia nieistniejącej gry: {game_name}")
        return

    game_type = game_data.get("game_type", "pc")
    process_found_and_killed = False

    if game_type == "pc":
        exe_paths_to_check = set()
        if game_data.get("exe_path"):
            exe_paths_to_check.add(os.path.abspath(game_data["exe_path"]))
        for profile in game_data.get("launch_profiles", []):
            if profile.get("exe_path"):
                exe_paths_to_check.add(os.path.abspath(profile["exe_path"]))

        if not exe_paths_to_check:
            messagebox.showwarning(
                "Błąd",
                f"Brak zdefiniowanej ścieżki .exe do zamknięcia dla gry PC '{game_name}'.",
            )
            return

        exe_names_to_check = {os.path.basename(p).lower() for p in exe_paths_to_check}
        logging.info(
            f"Próba zamknięcia gry PC '{game_name}'. Sprawdzanie nazw: {exe_names_to_check}, ścieżek: {exe_paths_to_check}"
        )

        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                proc_name_lower = proc.info["name"].lower()
                proc_exe_abs = (
                    os.path.abspath(proc.info["exe"]) if proc.info["exe"] else None
                )

                if proc_name_lower in exe_names_to_check or (
                    proc_exe_abs and proc_exe_abs in exe_paths_to_check
                ):
                    logging.info(
                        f"Znaleziono pasujący proces PC (PID: {proc.info['pid']}). Próba zamknięcia."
                    )
                    parent = psutil.Process(proc.info["pid"])
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    try:
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                    messagebox.showinfo(
                        "Informacja", f"Gra '{game_name}' została zamknięta."
                    )
                    process_found_and_killed = True
                    break
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                OSError,
            ):
                continue

    elif game_type == "emulator":
        emulator_name = game_data.get("emulator_name")
        rom_path = game_data.get("rom_path")
        if not emulator_name:
            messagebox.showwarning(
                "Błąd",
                f"Brak nazwy emulatora dla gry '{game_name}'. Nie można zamknąć.",
                parent=self.root,
            )
            return

        emulator_config = self.config.get("emulators", {}).get(emulator_name)
        if not emulator_config or not emulator_config.get("path"):
            messagebox.showwarning(
                "Błąd",
                f"Brak konfiguracji ścieżki dla emulatora '{emulator_name}'.",
                parent=self.root,
            )
            return

        emulator_exe_path = emulator_config["path"]
        if not emulator_exe_path:
            messagebox.showwarning(
                "Błąd",
                f"Pusta ścieżka w konfiguracji emulatora '{emulator_name}'.",
                parent=self.root,
            )
            return

        emulator_exe_path_abs = os.path.abspath(emulator_exe_path)
        emulator_exe_name_lower = os.path.basename(emulator_exe_path_abs).lower()
        norm_rom_path = os.path.normcase(os.path.abspath(rom_path)) if rom_path else None

        logging.info(
            f"Próba zamknięcia gry emulowanej '{game_name}'. Szukanie procesu emulatora: '{emulator_exe_name_lower}' ze ścieżką ROM: '{norm_rom_path}'"
        )

        candidate_pids = []

        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                proc_name_lower = proc.info["name"].lower()
                proc_exe_abs = (
                    os.path.abspath(proc.info["exe"]) if proc.info["exe"] else None
                )

                if proc_name_lower == emulator_exe_name_lower or (
                    proc_exe_abs and proc_exe_abs == emulator_exe_path_abs
                ):
                    if norm_rom_path and proc.info["cmdline"]:
                        if any(
                            norm_rom_path in os.path.normcase(arg)
                            for arg in proc.info["cmdline"]
                        ):
                            candidate_pids.append(proc.info["pid"])
                            logging.debug(
                                f"Znaleziono kandydata do zamknięcia (PID: {proc.info['pid']}) - pasuje emulator i ROM."
                            )
                    elif not norm_rom_path:
                        candidate_pids.append(proc.info["pid"])
                        logging.warning(
                            f"Znaleziono kandydata do zamknięcia (PID: {proc.info['pid']}), ale brak ROMu do weryfikacji cmdline."
                        )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                OSError,
            ):
                continue

        if candidate_pids:
            for pid in candidate_pids:
                try:
                    logging.info(
                        f"Próba zamknięcia procesu emulatora (PID: {pid}) dla gry '{game_name}'."
                    )
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    try:
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                    process_found_and_killed = True
                except psutil.NoSuchProcess:
                    logging.warning(
                        f"Proces emulatora (PID: {pid}) już nie istniał podczas próby zamknięcia."
                    )
                except Exception as kill_err:
                    logging.error(
                        f"Błąd podczas zabijania procesu emulatora (PID: {pid}): {kill_err}"
                    )
            if process_found_and_killed:
                messagebox.showinfo(
                    "Informacja",
                    f"Emulator '{emulator_name}' dla gry '{game_name}' został zamknięty.",
                )
    else:
        messagebox.showerror(
            "Błąd",
            f"Nieznany typ gry '{game_type}' dla '{game_name}'. Nie można zamknąć.",
        )
        return

    if not process_found_and_killed:
        messagebox.showwarning(
            "Błąd", f"Nie znaleziono działającego procesu dla gry '{game_name}'."
        )

    self.root.after(50, self.update_game_grid)


def _update_button_on_game_close(self, game_name):
    """Aktualizuje przycisk gry do stanu 'Uruchom' (z ikoną i tooltipem) po jej zamknięciu."""
    if game_name in self._launch_buttons:
        button = self._launch_buttons[game_name]
        if button.winfo_exists():
            game_data = self.games.get(game_name, {})
            profiles = game_data.get("launch_profiles", [])
            default_profile = (
                profiles[0] if profiles else {"name": "Uruchom", "arguments": ""}
            )

            if len(profiles) == 1 and default_profile.get("name", "").lower() == "default":
                tooltip_text = "Uruchom"
            else:
                tooltip_text = f"Uruchom: {default_profile.get('name', 'Profil')}"

            play_icon_tk = self._button_icons.get("play_btn")
            default_launch_command = lambda p=default_profile: self.launch_game(
                game_name, profile=p
            )

            if play_icon_tk:
                button.config(
                    image=play_icon_tk,
                    style="Green.TButton",
                    command=default_launch_command,
                )
                if hasattr(button, "tooltip") and button.tooltip:
                    button.tooltip.update_text(tooltip_text)
            else:
                button.config(
                    image="",
                    text="Uruchom",
                    style="Green.TButton",
                    command=default_launch_command,
                )
                if hasattr(button, "tooltip") and button.tooltip:
                    button.tooltip.update_text(tooltip_text)
                else:
                    button.tooltip = ToolTip(button, tooltip_text)

            profile_menu_key = f"{game_name}_profile_menu"
            if profile_menu_key in self._launch_buttons:
                menu_button = self._launch_buttons[profile_menu_key]
                if menu_button.winfo_exists():
                    menu_button.pack(side=tk.LEFT, fill=tk.Y)

            logging.debug(
                f"Zaktualizowano przycisk (ikona/tekst) dla zamkniętej gry: {game_name}"
            )


__all__ = [
    "launch_game",
    "is_game_running",
    "close_game",
    "_update_button_on_game_close",
]
