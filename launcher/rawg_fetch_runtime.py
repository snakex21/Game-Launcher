import json
import logging
import threading
import tkinter as tk
import requests
from tkinter import messagebox

from launcher.utils import PROGRAM_VERSION


def start_fetch_details_thread(self, game_name, details_window, force=False):
    api_key = self.local_settings.get("rawg_api_key")
    if not api_key:
        messagebox.showerror(
            "Brak klucza API",
            "Nie znaleziono klucza API RAWG.io w ustawieniach.",
            parent=details_window,
        )
        return

    if hasattr(details_window, "fetch_api_button"):
        details_window.fetch_api_button.config(text="Pobieranie...", state=tk.DISABLED)

    def on_complete(result):
        if details_window.winfo_exists():
            details_window._on_details_fetched(result)
            if hasattr(details_window, "fetch_api_button"):
                details_window.fetch_api_button.config(text="Pobierz dane", state=tk.NORMAL)

    threading.Thread(
        target=self.fetch_rawg_game_details,
        args=(game_name, api_key, on_complete, force),
        daemon=True,
    ).start()


def fetch_rawg_game_details(self, game_name, api_key, callback, force=False):
    """Pobiera dane gry z RAWG API i wywołuje callback z wynikiem."""
    base_url = "https://api.rawg.io/api/games"
    params = {"key": api_key}
    headers = {"User-Agent": f"GameLauncher/{PROGRAM_VERSION}"}
    result_data = {"success": False, "error": None, "data": None}

    try:
        search_params = {**params, "search": game_name, "page_size": 1}
        logging.info(f"Wyszukiwanie gry w RAWG: {game_name}")
        search_response = requests.get(
            base_url, params=search_params, headers=headers, timeout=15
        )
        search_response.raise_for_status()
        search_results = search_response.json()

        if not search_results.get("results"):
            logging.warning(f"Nie znaleziono gry '{game_name}' w RAWG.")
            result_data["error"] = "Nie znaleziono gry w bazie RAWG."
            self.root.after(0, callback, result_data)
            return

        game_id = search_results["results"][0].get("id")
        rawg_slug = search_results["results"][0].get("slug")
        if not game_id:
            logging.error("Pierwszy wynik wyszukiwania RAWG nie ma ID.")
            result_data["error"] = "Błąd odpowiedzi API RAWG (brak ID)."
            self.root.after(0, callback, result_data)
            return

        logging.info(f"Znaleziono ID gry: {game_id} (slug: {rawg_slug})")
        self.games[game_name]["rawg_id"] = game_id
        self.games[game_name]["rawg_slug"] = rawg_slug

        details_url = f"{base_url}/{game_id}"
        logging.info(f"Pobieranie szczegółów z: {details_url}")
        details_response = requests.get(
            details_url, params=params, headers=headers, timeout=15
        )
        details_response.raise_for_status()
        details = details_response.json()

        extracted_data = {}
        extracted_data["description"] = details.get("description_raw")
        extracted_data["release_date"] = details.get("released")
        extracted_data["website"] = details.get("website")
        extracted_data["developers"] = [
            dev.get("name") for dev in details.get("developers", []) if dev.get("name")
        ]
        extracted_data["publishers"] = [
            pub.get("name") for pub in details.get("publishers", []) if pub.get("name")
        ]
        extracted_data["genres_api"] = [
            gen.get("name") for gen in details.get("genres", []) if gen.get("name")
        ]
        extracted_data["tags_api"] = [
            tag.get("name") for tag in details.get("tags", []) if tag.get("name")
        ]
        extracted_data["platforms"] = [
            p.get("platform", {}).get("name")
            for p in details.get("platforms", [])
            if p.get("platform", {}).get("name")
        ]

        pc_platform = next(
            (
                p
                for p in details.get("platforms", [])
                if p.get("platform", {}).get("slug") == "pc"
            ),
            None,
        )
        if pc_platform and pc_platform.get("requirements"):
            extracted_data["requirements_pc"] = {
                "minimum": pc_platform["requirements"].get("minimum"),
                "recommended": pc_platform["requirements"].get("recommended"),
            }

        background_image_url = details.get("background_image")
        downloaded_cover_path = None
        if background_image_url:
            downloaded_cover_path = self._download_and_save_rawg_cover(
                game_name, background_image_url
            )
            if downloaded_cover_path:
                extracted_data["downloaded_cover_path"] = downloaded_cover_path
            else:
                logging.warning(
                    f"Nie udało się pobrać okładki RAWG dla '{game_name}' z URL: {background_image_url}"
                )

        result_data["success"] = True
        result_data["data"] = extracted_data
        result_data["force_cover"] = force
        logging.info(f"Pomyślnie pobrano i sparsowano dane dla ID: {game_id}")

    except requests.exceptions.Timeout:
        logging.error("Przekroczono czas oczekiwania na odpowiedź z RAWG API.")
        result_data["error"] = "Przekroczono czas odpowiedzi serwera RAWG."
    except requests.exceptions.RequestException as e:
        logging.error(f"Błąd połączenia z RAWG API: {e}")
        result_data["error"] = f"Błąd połączenia z RAWG: {e}"
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logging.error(f"Błąd przetwarzania odpowiedzi JSON z RAWG: {e}")
        result_data["error"] = "Błąd przetwarzania danych z RAWG."
    except Exception as e:
        logging.exception("Nieoczekiwany błąd podczas pobierania danych z RAWG.")
        result_data["error"] = f"Nieoczekiwany błąd: {e}"

    self.root.after(0, callback, result_data)


__all__ = [
    "start_fetch_details_thread",
    "fetch_rawg_game_details",
]
