import json
import logging
import os
import re


def sanitize_theme_filename(theme_name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", theme_name).strip()


def get_theme_filepath(custom_themes_dir: str, theme_name: str) -> str:
    safe_filename = sanitize_theme_filename(theme_name)
    return os.path.join(custom_themes_dir, f"{safe_filename}.json")


def save_custom_theme(
    theme_name: str,
    theme_definition: dict,
    custom_themes_dir: str,
) -> str:
    os.makedirs(custom_themes_dir, exist_ok=True)
    theme_filepath = get_theme_filepath(custom_themes_dir, theme_name)
    with open(theme_filepath, "w", encoding="utf-8") as file:
        json.dump(
            {"name": theme_name, "definition": theme_definition},
            file,
            indent=2,
            ensure_ascii=False,
        )
    return theme_filepath


def delete_custom_theme(theme_name: str, custom_themes_dir: str) -> tuple[bool, str]:
    theme_filepath = get_theme_filepath(custom_themes_dir, theme_name)
    if not os.path.exists(theme_filepath):
        return False, theme_filepath

    os.remove(theme_filepath)
    return True, theme_filepath


def load_custom_theme_by_name(
    theme_name: str,
    custom_themes_dir: str,
    load_theme_from_file,
) -> dict | None:
    theme_filepath = get_theme_filepath(custom_themes_dir, theme_name)
    if not os.path.exists(theme_filepath):
        return None
    return load_theme_from_file(theme_filepath)


def load_available_themes(
    custom_themes_dir: str,
    builtin_themes: dict,
    load_theme_from_file,
    custom_themes_cache: dict | None = None,
) -> tuple[dict, dict]:
    all_themes = builtin_themes.copy()
    cache = custom_themes_cache if isinstance(custom_themes_cache, dict) else {}

    if not os.path.isdir(custom_themes_dir):
        os.makedirs(custom_themes_dir, exist_ok=True)
        return all_themes, cache

    files_seen: set[str] = set()
    for filename in os.listdir(custom_themes_dir):
        if not filename.lower().endswith(".json"):
            continue

        files_seen.add(filename)
        theme_filepath = os.path.join(custom_themes_dir, filename)
        try:
            current_mtime = os.path.getmtime(theme_filepath)
        except OSError as error:
            logging.warning(
                f"Nie można odczytać czasu modyfikacji pliku motywu '{filename}': {error}. Pomijanie."
            )
            continue

        cached_theme = cache.get(filename)
        if not cached_theme or current_mtime > cached_theme.get("_mtime", 0):
            theme_data_from_file = load_theme_from_file(theme_filepath)
            if not theme_data_from_file:
                cache.pop(filename, None)
                continue

            theme_name = theme_data_from_file["name"]
            theme_def = theme_data_from_file["definition"]

            if theme_name in builtin_themes:
                logging.warning(
                    f"Niestandardowy motyw z pliku '{filename}' o nazwie '{theme_name}' koliduje z wbudowanym motywem. Wbudowany ma priorytet."
                )
                cache.pop(filename, None)
                continue

            cached_theme = {
                "name": theme_name,
                "definition": theme_def,
                "_mtime": current_mtime,
            }
            cache[filename] = cached_theme
            logging.debug(
                f"Załadowano (lub odświeżono) niestandardowy motyw z pliku: {theme_name} ({filename})"
            )

        all_themes[cached_theme["name"]] = cached_theme["definition"]

    stale_files = [filename for filename in list(cache.keys()) if filename not in files_seen]
    for stale_file in stale_files:
        cache.pop(stale_file, None)

    return all_themes, cache


def list_custom_theme_names(
    custom_themes_dir: str,
    builtin_themes: dict,
    load_theme_from_file,
    custom_themes_cache: dict | None = None,
) -> tuple[list[str], dict]:
    all_themes, cache = load_available_themes(
        custom_themes_dir=custom_themes_dir,
        builtin_themes=builtin_themes,
        load_theme_from_file=load_theme_from_file,
        custom_themes_cache=custom_themes_cache,
    )
    custom_theme_names = [
        theme_name for theme_name in all_themes.keys() if theme_name not in builtin_themes
    ]
    return sorted(custom_theme_names, key=str.lower), cache
