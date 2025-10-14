"""
Helpers - Funkcje pomocnicze używane w całej aplikacji
AI-Friendly: Małe, pojedyncze funkcje - łatwe do rozbudowy
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import psutil


def format_time(seconds):
    """
    Formatuje sekundy na czytelny format (np. "2h 30m").
    
    Args:
        seconds (int/float): Liczba sekund
    
    Returns:
        str: Sformatowany czas
    
    Examples:
        >>> format_time(7200)
        '2h 0m'
        >>> format_time(150)
        '2m 30s'
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def is_process_running(process_name):
    """
    Sprawdza czy proces o podanej nazwie jest uruchomiony.
    
    Args:
        process_name (str): Nazwa procesu (np. "game.exe")
    
    Returns:
        bool: True jeśli proces działa, False w przeciwnym razie
    
    AI Note: Używane do trackowania czy gra jest uruchomiona
    """
    process_name = process_name.lower()
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() == process_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def get_process_by_name(process_name):
    """
    Znajduje proces po nazwie i zwraca jego PID.
    
    Args:
        process_name (str): Nazwa procesu
    
    Returns:
        int or None: PID procesu lub None jeśli nie znaleziono
    """
    process_name = process_name.lower()
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'].lower() == process_name:
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def ensure_dir(path):
    """
    Upewnia się że folder istnieje, tworzy jeśli nie.
    
    Args:
        path (str or Path): Ścieżka do folderu
    
    Returns:
        Path: Obiekt Path do folderu
    
    AI Note: Bezpieczne tworzenie folderów bez błędów
    """
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def load_json(file_path, default=None):
    """
    Ładuje JSON z pliku z obsługą błędów.
    
    Args:
        file_path (str or Path): Ścieżka do pliku JSON
        default: Wartość domyślna jeśli plik nie istnieje lub błąd
    
    Returns:
        dict or default: Załadowane dane lub default
    
    AI Note: Bezpieczne ładowanie JSON - nie crashuje aplikacji
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        return default if default is not None else {}


def save_json(file_path, data, indent=2):
    """
    Zapisuje dane do pliku JSON.
    
    Args:
        file_path (str or Path): Ścieżka do pliku
        data (dict): Dane do zapisania
        indent (int): Wcięcie w JSON (domyślnie 2)
    
    Returns:
        bool: True jeśli sukces, False jeśli błąd
    
    AI Note: Bezpieczny zapis z automatycznym tworzeniem folderów
    """
    try:
        # Upewnij się że folder istnieje
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON to {file_path}: {e}")
        return False


def get_file_size_mb(file_path):
    """
    Zwraca rozmiar pliku w MB.
    
    Args:
        file_path (str or Path): Ścieżka do pliku
    
    Returns:
        float: Rozmiar w MB (zaokrąglony do 2 miejsc)
    """
    try:
        size_bytes = Path(file_path).stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except:
        return 0.0


def sanitize_filename(filename):
    """
    Czyści nazwę pliku z niedozwolonych znaków.
    
    Args:
        filename (str): Oryginalna nazwa pliku
    
    Returns:
        str: Bezpieczna nazwa pliku
    
    AI Note: Używaj przed zapisywaniem plików z nazwami od użytkownika
    """
    # Usuń znaki niedozwolone w Windows
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()