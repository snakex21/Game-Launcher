"""
Narzędzia do operacji na plikach
Zawiera funkcje pomocnicze do bezpiecznej pracy z plikami i katalogami.
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def ensure_directory(path: Union[str, Path]) -> bool:
    """
    Upewnia się, że katalog istnieje. Tworzy go jeśli nie istnieje.
    
    Args:
        path: Ścieżka do katalogu
        
    Returns:
        True jeśli katalog istnieje lub został utworzony
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Błąd tworzenia katalogu {path}: {e}")
        return False


def safe_json_load(filepath: Union[str, Path], default: Any = None) -> Any:
    """
    Bezpiecznie ładuje dane z pliku JSON.
    
    Args:
        filepath: Ścieżka do pliku JSON
        default: Wartość zwracana w przypadku błędu
        
    Returns:
        Załadowane dane lub default w przypadku błędu
    """
    try:
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"Plik {filepath} nie istnieje")
            return default
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"Załadowano JSON z: {filepath}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Błąd parsowania JSON {filepath}: {e}")
        return default
        
    except Exception as e:
        logger.error(f"Błąd ładowania pliku {filepath}: {e}")
        return default


def safe_json_save(filepath: Union[str, Path], data: Any, indent: int = 4) -> bool:
    """
    Bezpiecznie zapisuje dane do pliku JSON.
    
    Args:
        filepath: Ścieżka do pliku JSON
        data: Dane do zapisania
        indent: Wcięcie w pliku JSON
        
    Returns:
        True jeśli zapisano pomyślnie
    """
    try:
        filepath = Path(filepath)
        ensure_directory(filepath.parent)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        logger.debug(f"Zapisano JSON do: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd zapisywania pliku {filepath}: {e}")
        return False


def get_file_size(filepath: Union[str, Path]) -> Optional[int]:
    """
    Zwraca rozmiar pliku w bajtach.
    
    Args:
        filepath: Ścieżka do pliku
        
    Returns:
        Rozmiar pliku w bajtach lub None
    """
    try:
        return Path(filepath).stat().st_size
    except Exception as e:
        logger.error(f"Błąd pobierania rozmiaru pliku {filepath}: {e}")
        return None


def get_file_modified_time(filepath: Union[str, Path]) -> Optional[datetime]:
    """
    Zwraca czas ostatniej modyfikacji pliku.
    
    Args:
        filepath: Ścieżka do pliku
        
    Returns:
        Datetime ostatniej modyfikacji lub None
    """
    try:
        timestamp = Path(filepath).stat().st_mtime
        return datetime.fromtimestamp(timestamp)
    except Exception as e:
        logger.error(f"Błąd pobierania czasu modyfikacji {filepath}: {e}")
        return None


def copy_file_safe(src: Union[str, Path], dst: Union[str, Path], 
                   overwrite: bool = False) -> bool:
    """
    Bezpiecznie kopiuje plik.
    
    Args:
        src: Ścieżka źródłowa
        dst: Ścieżka docelowa
        overwrite: Czy nadpisać istniejący plik
        
    Returns:
        True jeśli skopiowano pomyślnie
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            logger.error(f"Plik źródłowy nie istnieje: {src}")
            return False
        
        if dst_path.exists() and not overwrite:
            logger.warning(f"Plik docelowy już istnieje: {dst}")
            return False
        
        ensure_directory(dst_path.parent)
        shutil.copy2(src_path, dst_path)
        
        logger.debug(f"Skopiowano: {src} -> {dst}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd kopiowania pliku: {e}")
        return False


def move_file_safe(src: Union[str, Path], dst: Union[str, Path],
                   overwrite: bool = False) -> bool:
    """
    Bezpiecznie przenosi plik.
    
    Args:
        src: Ścieżka źródłowa
        dst: Ścieżka docelowa
        overwrite: Czy nadpisać istniejący plik
        
    Returns:
        True jeśli przeniesiono pomyślnie
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            logger.error(f"Plik źródłowy nie istnieje: {src}")
            return False
        
        if dst_path.exists() and not overwrite:
            logger.warning(f"Plik docelowy już istnieje: {dst}")
            return False
        
        ensure_directory(dst_path.parent)
        shutil.move(str(src_path), str(dst_path))
        
        logger.debug(f"Przeniesiono: {src} -> {dst}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd przenoszenia pliku: {e}")
        return False


def delete_file_safe(filepath: Union[str, Path]) -> bool:
    """
    Bezpiecznie usuwa plik.
    
    Args:
        filepath: Ścieżka do pliku
        
    Returns:
        True jeśli usunięto pomyślnie
    """
    try:
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"Plik nie istnieje: {filepath}")
            return True  # Nie istnieje = cel osiągnięty
        
        filepath.unlink()
        logger.debug(f"Usunięto plik: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd usuwania pliku {filepath}: {e}")
        return False


def find_files(directory: Union[str, Path], 
               pattern: str = "*",
               recursive: bool = True,
               extensions: Optional[List[str]] = None) -> List[Path]:
    """
    Znajduje pliki w katalogu pasujące do wzorca.
    
    Args:
        directory: Katalog do przeszukania
        pattern: Wzorzec nazwy pliku (np. "*.txt")
        recursive: Czy szukać rekurencyjnie
        extensions: Lista rozszerzeń do filtrowania (np. ['.txt', '.json'])
        
    Returns:
        Lista znalezionych plików
    """
    try:
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Katalog nie istnieje: {directory}")
            return []
        
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        # Filtruj tylko pliki (nie katalogi)
        files = [f for f in files if f.is_file()]
        
        # Filtruj po rozszerzeniach jeśli podane
        if extensions:
            extensions_lower = [ext.lower() for ext in extensions]
            files = [f for f in files if f.suffix.lower() in extensions_lower]
        
        logger.debug(f"Znaleziono {len(files)} plików w {directory}")
        return files
        
    except Exception as e:
        logger.error(f"Błąd przeszukiwania katalogu {directory}: {e}")
        return []


def get_available_filename(filepath: Union[str, Path]) -> Path:
    """
    Zwraca dostępną nazwę pliku (dodaje numer jeśli plik istnieje).
    
    Args:
        filepath: Pożądana ścieżka do pliku
        
    Returns:
        Dostępna ścieżka do pliku
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        return filepath
    
    # Plik istnieje, dodaj numer
    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        
        if not new_path.exists():
            return new_path
        
        counter += 1
        
        # Zabezpieczenie przed nieskończoną pętlą
        if counter > 9999:
            logger.error(f"Nie można znaleźć dostępnej nazwy dla: {filepath}")
            return filepath


def format_file_size(size_bytes: int) -> str:
    """
    Formatuje rozmiar pliku do czytelnej postaci.
    
    Args:
        size_bytes: Rozmiar w bajtach
        
    Returns:
        Sformatowany string (np. "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def get_directory_size(directory: Union[str, Path]) -> int:
    """
    Oblicza całkowity rozmiar katalogu (włącznie z podkatalogami).
    
    Args:
        directory: Ścieżka do katalogu
        
    Returns:
        Rozmiar w bajtach
    """
    try:
        total_size = 0
        directory = Path(directory)
        
        for item in directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
        
        return total_size
        
    except Exception as e:
        logger.error(f"Błąd obliczania rozmiaru katalogu {directory}: {e}")
        return 0


def clean_old_files(directory: Union[str, Path], 
                    days_old: int = 30,
                    pattern: str = "*") -> int:
    """
    Usuwa stare pliki z katalogu.
    
    Args:
        directory: Katalog do wyczyszczenia
        days_old: Usuń pliki starsze niż X dni
        pattern: Wzorzec nazw plików
        
    Returns:
        Liczba usuniętych plików
    """
    try:
        directory = Path(directory)
        now = datetime.now()
        deleted = 0
        
        for filepath in directory.glob(pattern):
            if not filepath.is_file():
                continue
            
            modified_time = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_days = (now - modified_time).days
            
            if age_days > days_old:
                if delete_file_safe(filepath):
                    deleted += 1
        
        logger.info(f"Usunięto {deleted} starych plików z {directory}")
        return deleted
        
    except Exception as e:
        logger.error(f"Błąd czyszczenia katalogu {directory}: {e}")
        return 0
