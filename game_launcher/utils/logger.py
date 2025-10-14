"""
Logger - Prosty system logowania dla aplikacji
AI-Friendly: Centralne miejsce do logowania eventów i błędów
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name="GameLauncher", level=logging.INFO):
    """
    Konfiguruje i zwraca logger dla aplikacji.
    
    Args:
        name (str): Nazwa loggera
        level: Poziom logowania (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger: Skonfigurowany logger
    
    AI Note: Ten logger zapisuje do pliku i wyświetla w konsoli
    """
    # Tworzenie folderu logs jeśli nie istnieje
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Nazwa pliku z datą
    log_file = log_dir / f"launcher_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Tworzenie loggera
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Usunięcie poprzednich handlerów (jeśli istnieją)
    logger.handlers.clear()
    
    # Format logów
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler do pliku
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler do konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name="GameLauncher"):
    """
    Pobiera istniejący logger lub tworzy nowy.
    
    Args:
        name (str): Nazwa loggera
    
    Returns:
        logging.Logger: Logger
    
    AI Note: Użyj tej funkcji w innych modułach: logger = get_logger()
    """
    return logging.getLogger(name)