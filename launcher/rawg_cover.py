import logging
import os
import re
import shutil

import requests

from launcher.utils import IMAGES_FOLDER


def _download_and_save_rawg_cover(self, game_name, image_url):
    """Pobiera obrazek z URL i zapisuje go lokalnie jako okładkę RAWG."""
    if not image_url:
        return None

    logging.info(f"Próba pobrania okładki RAWG dla '{game_name}' z: {image_url}")
    safe_game_name = re.sub(r'[\\/*?:"<>|]', "_", game_name)

    try:
        response = requests.get(image_url, stream=True, timeout=20)
        response.raise_for_status()

        content_type = response.headers.get("content-type")
        extension = ".jpg"
        if content_type:
            if "jpeg" in content_type:
                extension = ".jpg"
            elif "png" in content_type:
                extension = ".png"
            elif "webp" in content_type:
                extension = ".webp"
            elif "gif" in content_type:
                extension = ".gif"
            elif "bmp" in content_type:
                extension = ".bmp"
        else:
            lower_url = image_url.lower()
            for ext in [".png", ".webp", ".jpg", ".jpeg", ".gif", ".bmp"]:
                if lower_url.endswith(ext):
                    extension = ext
                    break

        dest_filename = f"{safe_game_name}_rawg_cover{extension}"
        dest_path = os.path.join(IMAGES_FOLDER, dest_filename)
        dest_abs = os.path.abspath(dest_path)

        os.makedirs(IMAGES_FOLDER, exist_ok=True)

        with open(dest_abs, "wb") as f:
            shutil.copyfileobj(response.raw, f)

        logging.info(f"Pomyślnie pobrano i zapisano okładkę RAWG: {dest_abs}")
        return dest_path

    except requests.exceptions.Timeout:
        logging.error(f"Timeout podczas pobierania okładki RAWG dla '{game_name}'.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Błąd sieciowy podczas pobierania okładki RAWG dla '{game_name}': {e}")
        return None
    except IOError as e:
        logging.error(
            f"Błąd zapisu pliku okładki RAWG dla '{game_name}' w '{dest_abs}': {e}"
        )
        return None
    except Exception:
        logging.exception(
            f"Nieoczekiwany błąd podczas pobierania/zapisu okładki RAWG dla '{game_name}'."
        )
        return None


__all__ = ["_download_and_save_rawg_cover"]
