import logging
import os
import shutil
import subprocess
import sys
import tempfile
from tkinter import messagebox

import requests
from packaging import version

from launcher.utils import PROGRAM_VERSION


def check_for_updates(self):
    try:
        current_version = PROGRAM_VERSION
        logging.info(f"Obecna wersja: {current_version}")

        github_api_url = "https://api.github.com/repos/snakex21/Game-Launcher/releases"
        response = requests.get(github_api_url, timeout=10)
        response.raise_for_status()
        releases = response.json()
        logging.info(f"Pobrano {len(releases)} wydań")

        newer_versions = []
        for release in releases:
            release_version = release["tag_name"].lstrip("v")
            logging.info(f"Analizuję wydanie: {release_version}")
            try:
                if version.parse(release_version) > version.parse(current_version):
                    if not release.get("assets"):
                        logging.warning(f"Wydanie {release_version} nie ma assetów")
                        continue
                    newer_versions.append(
                        {
                            "version": release_version,
                            "download_url": release["assets"][0]["browser_download_url"],
                            "release": release,
                        }
                    )
            except version.InvalidVersion:
                logging.warning(f"Nieprawidłowy format wersji: {release_version}")

        if not newer_versions:
            logging.info("Brak dostępnych aktualizacji")
            return {"available": False}

        newer_versions.sort(key=lambda x: version.parse(x["version"]))
        next_update = newer_versions[0]
        logging.info(f"Znaleziono aktualizację: {next_update['version']}")
        return {
            "available": True,
            "latest_version": next_update["version"],
            "download_url": next_update["download_url"],
        }
    except requests.RequestException as e:
        logging.error(f"Błąd sieciowy: {e}")
        return {"available": False}
    except Exception as e:
        logging.error(f"Nieoczekiwany błąd: {e}")
        return {"available": False}


def perform_update_check(self):
    """Wykonuje sprawdzanie aktualizacji i promuje je w GUI."""
    update_info = self.check_for_updates()
    if update_info.get("available"):
        self.root.after(0, lambda: self.prompt_update(update_info))


def prompt_update(self, update_info):
    if update_info.get("available"):
        latest_version = update_info["latest_version"]
        if messagebox.askyesno(
            "Aktualizacja Dostępna",
            f"Dostępna jest nowa wersja ({latest_version}). Czy chcesz ją pobrać i zainstalować?",
        ):
            self.download_and_update(update_info["download_url"])
    else:
        logging.info("Nie ma dostępnych aktualizacji.")


def download_and_update(self, download_url):
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        current_exe = sys.executable
        temp_dir = tempfile.gettempdir()
        new_exe_path = os.path.join(temp_dir, "GameLauncher_Update.exe")

        with open(new_exe_path, "wb") as file:
            shutil.copyfileobj(response.raw, file)

        updater_script = os.path.join(temp_dir, "updater.bat")
        with open(updater_script, "w", encoding="cp1250") as script:
            script.write(
                f"""@echo off
    timeout /t 3 /nobreak > NUL
    echo Aktualizuję...
    copy /Y "{new_exe_path}" "{current_exe}"
    start "" "{current_exe}"
    del "{new_exe_path}"
    del "%~f0"
    """
            )

        subprocess.Popen(["cmd", "/c", updater_script], shell=True)
        self.root.quit()

    except Exception as e:
        logging.error(f"Błąd podczas pobierania aktualizacji: {e}")
        messagebox.showerror("Błąd", f"Nie udało się pobrać aktualizacji: {e}")


def manual_check_updates(self):
    """Ręczne sprawdzanie aktualizacji przez użytkownika."""
    update_info = self.check_for_updates()
    self.prompt_update(update_info)


__all__ = [
    "perform_update_check",
    "check_for_updates",
    "prompt_update",
    "download_and_update",
    "manual_check_updates",
]
