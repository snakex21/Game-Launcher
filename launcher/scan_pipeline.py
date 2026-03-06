import logging
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from ui.dialogs import ScanVerificationWindow
from launcher.utils import save_config


def load_scan_folders_list(self):
    """Ładuje listę folderów do skanowania do listboxa w ustawieniach."""
    if hasattr(self, "scan_folders_listbox") and self.scan_folders_listbox.winfo_exists():
        self.scan_folders_listbox.delete(0, tk.END)
        scan_folders = self.settings.get("scan_folders", [])
        for folder in scan_folders:
            self.scan_folders_listbox.insert(tk.END, folder)


def add_scan_folder(self):
    """Otwiera dialog wyboru folderu i dodaje go do listy skanowania."""
    folder_selected = filedialog.askdirectory(title="Wybierz folder do skanowania")
    if folder_selected:
        scan_folders = self.settings.get("scan_folders", [])
        if folder_selected not in scan_folders:
            scan_folders.append(folder_selected)
            self.settings["scan_folders"] = scan_folders
            save_config(self.config)
            self.load_scan_folders_list()
        else:
            messagebox.showwarning("Informacja", "Ten folder jest już na liście.")


def remove_scan_folder(self):
    """Usuwa zaznaczony folder z listy skanowania."""
    selected_indices = self.scan_folders_listbox.curselection()
    if selected_indices:
        index = selected_indices[0]
        folder_to_remove = self.scan_folders_listbox.get(index)
        scan_folders = self.settings.get("scan_folders", [])
        if folder_to_remove in scan_folders:
            scan_folders.remove(folder_to_remove)
            self.settings["scan_folders"] = scan_folders
            save_config(self.config)
            self.load_scan_folders_list()
    else:
        messagebox.showwarning("Błąd", "Nie wybrano folderu do usunięcia.")


def save_scan_settings(self):
    """Zapisuje ustawienie skanowania rekursywnego."""
    self.settings["scan_recursively"] = self.scan_recursively_var.get()
    save_config(self.config)


def guess_game_name_from_folder(self, folder_name):
    """Próbuje odgadnąć nazwę gry na podstawie nazwy folderu."""
    patterns_to_remove = [
        r"\[.*?\]",
        r"\(.*?\)",
        r"v\d+(\.\d+)*",
        r"\b(Repack|Update|Fix|Edition|GOTY|Gold|Definitive|Remastered)\b",
        r"\b\d{4}\b",
        r"[-_.]",
    ]
    cleaned_name = folder_name
    for pattern in patterns_to_remove:
        cleaned_name = re.sub(pattern, "", cleaned_name, flags=re.IGNORECASE)

    cleaned_name = " ".join(cleaned_name.split()).strip()
    return cleaned_name if cleaned_name else folder_name


def find_likely_executable(self, game_folder_path, guessed_name=""):
    """Próbuje znaleźć najbardziej prawdopodobny plik .exe gry."""
    potential_exes = []
    guessed_name_lower = guessed_name.lower()
    game_folder_name_lower = os.path.basename(game_folder_path).lower()

    search_order = [game_folder_path]
    bin_folders = [
        os.path.join(game_folder_path, d)
        for d in ["bin", "Binaries", "Win32", "Win64", "x64", "x86"]
        if os.path.isdir(os.path.join(game_folder_path, d))
    ]
    search_order.extend(bin_folders)

    for folder in search_order:
        try:
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if (
                    item.lower().endswith(".exe")
                    and item.lower() not in self.find_likely_executable.ignore_files
                    and os.path.isfile(item_path)
                ):
                    try:
                        size = os.path.getsize(item_path)
                        potential_exes.append(
                            {
                                "path": item_path,
                                "size": size,
                                "name": item.lower(),
                                "depth": 0 if folder == game_folder_path else 1,
                            }
                        )
                    except OSError:
                        continue
        except OSError:
            continue

    if not potential_exes:
        logging.debug(
            f"Nie znaleziono żadnych plików .exe (poza ignorowanymi) w '{game_folder_path}' i jego podfolderach bin."
        )
        return None

    def sort_key(exe_info):
        name = exe_info["name"]
        size = exe_info["size"]
        depth = exe_info["depth"]
        base_name = name[:-4]

        score = 10 if base_name == game_folder_name_lower else 0
        if not score and base_name == guessed_name_lower:
            score = 9

        if not score:
            if guessed_name_lower and guessed_name_lower in base_name:
                score = 7
            elif base_name in game_folder_name_lower:
                score = 6

        if not score and any(
            keyword in name for keyword in self.find_likely_executable.preferred_keywords
        ):
            score = 5

        depth_bonus = (2 - depth) * 0.1
        return (score, size, depth_bonus)

    potential_exes.sort(key=sort_key, reverse=True)
    logging.debug(f"Posortowani kandydaci dla '{game_folder_path}': {potential_exes}")
    best_candidate_path = potential_exes[0]["path"]
    logging.info(
        f"Wybrano najlepszy kandydat .exe dla '{guessed_name}': {best_candidate_path}"
    )
    return best_candidate_path


def start_scan_thread(self):
    """Uruchamia skanowanie folderów w osobnym wątku."""
    scan_folders = self.settings.get("scan_folders", [])
    if not scan_folders:
        messagebox.showinfo(
            "Informacja",
            "Nie zdefiniowano żadnych folderów do skanowania. Dodaj je w ustawieniach.",
        )
        return

    if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
        messagebox.showwarning(
            "Skanowanie w toku",
            "Inna operacja (np. synchronizacja, skanowanie) jest już w toku.",
        )
        return

    self.show_progress_window("Skanowanie folderów...")
    self.progress_bar["mode"] = "indeterminate"
    self.progress_bar.start()
    self.progress_label.config(text="Rozpoczynanie...")

    scan_thread = threading.Thread(target=self.scan_folders_for_games, daemon=True)
    scan_thread.start()


def scan_folders_for_games(self):
    """Skanuje zdefiniowane foldery w poszukiwaniu gier i prezentuje wyniki do weryfikacji."""
    scan_folders_config = self.settings.get("scan_folders", [])
    scan_recursively = self.settings.get("scan_recursively", True)
    ignored_folder_names = set(
        name.lower() for name in self.settings.get("scan_ignore_folders", [])
    )
    logging.info(
        f"Rozpoczynanie skanowania. Foldery: {scan_folders_config}, Rekursywnie: {scan_recursively}, Ignorowane: {ignored_folder_names}"
    )

    potential_new_games = []

    try:
        all_potential_folders = set()

        for base_folder in scan_folders_config:
            self.root.after(
                0,
                lambda bf=base_folder: self.progress_label.config(text=f"Analiza: {bf}"),
            )
            if not os.path.isdir(base_folder):
                logging.warning(
                    f"Folder skanowania '{base_folder}' nie istnieje lub nie jest folderem."
                )
                continue

            contains_exe = False
            try:
                for item in os.listdir(base_folder):
                    if (
                        item.lower().endswith(".exe")
                        and item.lower() not in self.find_likely_executable.ignore_files
                    ):
                        contains_exe = True
                        break
            except OSError as e:
                logging.warning(
                    f"Nie można odczytać zawartości folderu '{base_folder}': {e}"
                )

            if (
                contains_exe
                and os.path.basename(base_folder).lower() not in ignored_folder_names
            ):
                all_potential_folders.add(os.path.abspath(base_folder))

            if scan_recursively:
                for root, dirs, files in os.walk(base_folder, topdown=True):
                    dirs[:] = [d for d in dirs if d.lower() not in ignored_folder_names]
                    for d in dirs:
                        folder_path = os.path.abspath(os.path.join(root, d))
                        all_potential_folders.add(folder_path)
            else:
                try:
                    for item in os.listdir(base_folder):
                        item_path = os.path.abspath(os.path.join(base_folder, item))
                        if (
                            os.path.isdir(item_path)
                            and item.lower() not in ignored_folder_names
                        ):
                            all_potential_folders.add(item_path)
                except OSError as e:
                    logging.warning(
                        f"Nie można odczytać zawartości folderu '{base_folder}': {e}"
                    )

        sorted_potential_folders = sorted(list(all_potential_folders))
        logging.info(
            f"Znaleziono {len(sorted_potential_folders)} unikalnych potencjalnych folderów do sprawdzenia."
        )
        total_folders = len(sorted_potential_folders)

        for i, folder_path in enumerate(sorted_potential_folders):
            if os.path.basename(folder_path).lower() in ignored_folder_names:
                continue

            self.root.after(
                0,
                lambda p=folder_path: self.progress_label.config(
                    text=f"Sprawdzanie: {os.path.basename(p)} ({i+1}/{total_folders})"
                ),
            )

            guessed_name = self.guess_game_name_from_folder(os.path.basename(folder_path))

            if guessed_name.lower() in (name.lower() for name in self.games.keys()):
                continue
            if any(
                g["guessed_name"].lower() == guessed_name.lower()
                for g in potential_new_games
            ):
                continue

            executable_path = self.find_likely_executable(folder_path, guessed_name)

            if executable_path:
                potential_new_games.append(
                    {
                        "guessed_name": guessed_name,
                        "folder_path": folder_path,
                        "suggested_exe_path": executable_path,
                        "import": True,
                        "profiles": [
                            {"name": "Default", "exe_path": None, "arguments": ""}
                        ],
                    }
                )

        self.root.after(0, self.stop_scan_progress)

        if potential_new_games:
            self.root.after(
                100,
                lambda games=potential_new_games: self.show_scan_verification_window(games),
            )
        else:
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Skanowanie Zakończone",
                    "Nie znaleziono żadnych nowych gier do dodania.",
                ),
            )

    except Exception as e:
        logging.exception("Krytyczny błąd podczas skanowania folderów.")
        self.root.after(0, self.stop_scan_progress)
        self.root.after(
            0,
            lambda err=e: messagebox.showerror(
                "Błąd Skanowania", f"Wystąpił nieoczekiwany błąd: {err}"
            ),
        )


def show_scan_verification_window(self, potential_games):
    """Otwiera okno weryfikacji znalezionych gier."""
    verification_window = ScanVerificationWindow(self.root, self, potential_games)
    _ = verification_window


def update_scan_progress(self, percent, current_folder):
    if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
        if self.progress_bar["mode"] == "indeterminate":
            self.progress_bar.stop()
            self.progress_bar["mode"] = "determinate"
        self.progress_bar["value"] = percent
        self.progress_label.config(text=f"{percent}% - {current_folder}")
        self.progress_window.update_idletasks()


def stop_scan_progress(self):
    if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
        if self.progress_bar["mode"] == "indeterminate":
            self.progress_bar.stop()
        self.progress_window.destroy()


def parse_folder_name_metadata(self, folder_name):
    """Próbuje wyciągnąć rok i wydawcę z nazwy folderu."""
    metadata = {}
    year_match = re.search(r"(\b(19[8-9]\d|20\d\d)\b)", folder_name)
    if year_match:
        metadata["year"] = year_match.group(1)
        logging.info(
            f"Znaleziono rok w nazwie folderu '{folder_name}': {metadata['year']}"
        )

    publisher_match = re.search(r"\[([^\]]+)\]", folder_name)
    if publisher_match:
        potential_publisher = publisher_match.group(1)
        if potential_publisher.upper() not in [
            "CODEX",
            "PLAZA",
            "SKIDROW",
            "FLT",
            "RELOADED",
            "CPY",
        ]:
            metadata["publisher"] = potential_publisher
            logging.info(
                f"Znaleziono potencjalnego wydawcę w nazwie folderu '{folder_name}': {metadata['publisher']}"
            )

    return metadata


def parse_nfo_file(self, game_folder_path):
    """Próbuje znaleźć i sparsować plik .nfo w folderze gry (bardziej elastycznie)."""
    nfo_file = None
    for filename in os.listdir(game_folder_path):
        if filename.lower().endswith((".nfo", ".txt")):
            try:
                f_path = os.path.join(game_folder_path, filename)
                if os.path.getsize(f_path) < 5 * 1024 * 1024:
                    nfo_file = f_path
                    if filename.lower().endswith(".nfo"):
                        break
            except OSError:
                continue

    if not nfo_file:
        logging.info(f"Nie znaleziono odpowiedniego pliku .nfo/.txt w {game_folder_path}")
        return None

    logging.info(f"Znaleziono plik do parsowania: {nfo_file}")
    encodings_to_try = ["cp437", "utf-8", "latin-1", "cp1250", "cp1252"]
    nfo_content = None
    for enc in encodings_to_try:
        try:
            with open(nfo_file, "r", encoding=enc) as f:
                nfo_content = f.read()
            logging.info(
                f"Odczytano plik '{os.path.basename(nfo_file)}' używając kodowania: {enc}"
            )
            break
        except UnicodeDecodeError:
            logging.warning(
                f"Nieudany odczyt pliku '{os.path.basename(nfo_file)}' z kodowaniem {enc}"
            )
            continue
        except Exception as e:
            logging.error(
                f"Błąd odczytu pliku '{os.path.basename(nfo_file)}' ({enc}): {e}"
            )

    if not nfo_content:
        logging.error(
            f"Nie udało się odczytać zawartości żadnego pliku .nfo/.txt w {game_folder_path}"
        )
        return None

    metadata = {}
    lines = nfo_content.splitlines()

    patterns = {
        "title": r"^\s*(?:Title|Game Name)\s*:\s*(.+)",
        "publisher": r"^\s*Publisher\s*:\s*(.+)",
        "developer": r"^\s*Developer\s*:\s*(.+)",
        "release_date": r"^\s*(?:Release Date|Date)\s*:\s*(.+)",
        "genre": r"^\s*Genre\s*:\s*(.+)",
        "version": r"^\s*Version\s*:\s*(.+)",
    }
    found_keys = set()
    for key, pattern in patterns.items():
        for line in lines:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    metadata[key] = value
                    found_keys.add(key)
                    logging.info(
                        f"[Pattern Match] Znaleziono w pliku - {key}: {metadata[key]}"
                    )
                    break

    logging.info("Uruchamianie logiki rezerwowej dla brakujących pól NFO...")

    if "title" not in found_keys:
        for line in lines:
            cleaned_line = line.strip()
            if (
                cleaned_line
                and len(cleaned_line) > 3
                and not re.match(r"^[\s\W_]*[-=_*#<>/\\]{3,}[\s\W_]*$", cleaned_line)
            ):
                metadata["title"] = cleaned_line
                logging.info(
                    f"[Fallback] Użyto pierwszej linii jako tytułu: {metadata['title']}"
                )
                break

    if "release_date" not in found_keys:
        year_match = re.search(r"\b(19[8-9]\d|20\d\d)\b", nfo_content)
        if year_match:
            metadata["release_date"] = year_match.group(1)
            logging.info(
                f"[Fallback] Znaleziono rok w treści: {metadata['release_date']}"
            )

    if "publisher" not in found_keys:
        publisher_match = re.search(r"\[([^\]]+)\]", nfo_content)
        if publisher_match:
            potential_publisher = publisher_match.group(1).strip()
            if potential_publisher.upper() not in [
                "CODEX",
                "PLAZA",
                "SKIDROW",
                "FLT",
                "RELOADED",
                "CPY",
                "STEAM",
                "GOG",
            ]:
                metadata["publisher"] = potential_publisher
                logging.info(
                    "[Fallback] Znaleziono potencjalnego wydawcę w treści: "
                    f"{metadata['publisher']}"
                )

    if metadata:
        logging.info(
            f"Finalne sparsowane metadane z '{os.path.basename(nfo_file)}': {metadata}"
        )
        return metadata

    logging.warning(
        f"Nie udało się sparsować żadnych użytecznych danych z pliku: {nfo_file}"
    )
    return None


__all__ = [
    "load_scan_folders_list",
    "add_scan_folder",
    "remove_scan_folder",
    "save_scan_settings",
    "guess_game_name_from_folder",
    "find_likely_executable",
    "start_scan_thread",
    "scan_folders_for_games",
    "show_scan_verification_window",
    "update_scan_progress",
    "stop_scan_progress",
    "parse_folder_name_metadata",
    "parse_nfo_file",
]
