#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Launcher - Główny punkt wejścia aplikacji
Kompleksowy launcher do zarządzania grami, muzyką i wieloma innymi funkcjami.

Autor: [Twoje Imię]
Wersja: 2.0 (Zrefaktoryzowana - Modułowa)
Data: 2025
"""

import sys
import os
import logging
import tkinter as tk
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki importu
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_launcher.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def check_dependencies():
    """
    Sprawdza czy wszystkie wymagane biblioteki są zainstalowane.
    Zwraca True jeśli wszystko OK, False jeśli brakuje zależności.
    """
    required_modules = [
        'PIL', 'pygame', 'requests', 'psutil', 'plyer', 
        'pystray', 'tkcalendar', 'matplotlib', 'pylast',
        'pypresence', 'pynput', 'flask', 'socketio', 
        'feedparser', 'mutagen', 'packaging', 'inputs',
        'tkhtmlview', 'github'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        logger.error(f"Brakujące moduły: {', '.join(missing)}")
        logger.error("Zainstaluj brakujące moduły używając: pip install [nazwa_modułu]")
        return False
    
    return True


def setup_icon(root):
    """Ustawia ikonę okna aplikacji"""
    try:
        icon_path = PROJECT_ROOT / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
            logger.info(f"Załadowano ikonę z: {icon_path}")
        else:
            logger.warning(f"Plik ikony '{icon_path}' nie został znaleziony.")
    except tk.TclError as e:
        logger.error(f"Nie można ustawić ikony okna: {e}")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas ustawiania ikony: {e}")


def main():
    """
    Główna funkcja uruchamiająca aplikację Game Launcher.
    """
    logger.info("=" * 60)
    logger.info("Uruchamianie Game Launcher v2.0")
    logger.info("=" * 60)
    
    # Sprawdź zależności
    if not check_dependencies():
        logger.critical("Nie wszystkie wymagane biblioteki są zainstalowane!")
        input("Naciśnij Enter aby zakończyć...")
        sys.exit(1)
    
    try:
        # Import głównej klasy launchera (będzie w module core.launcher)
        from core.launcher import GameLauncher
        
        # Inicjalizacja głównego okna Tkinter
        root = tk.Tk()
        root.title("Game Launcher v2.0")
        
        # Ustawienie ikony
        setup_icon(root)
        
        # Utworzenie instancji launchera
        logger.info("Inicjalizacja GameLauncher...")
        app = GameLauncher(root)
        
        # Uruchomienie głównej pętli zdarzeń
        logger.info("Uruchamianie głównej pętli aplikacji...")
        root.mainloop()
        
    except ImportError as e:
        logger.critical(f"Błąd importu modułu: {e}")
        logger.critical("Upewnij się, że wszystkie moduły projektu są obecne!")
        input("Naciśnij Enter aby zakończyć...")
        sys.exit(1)
        
    except Exception as e:
        logger.critical(f"Krytyczny błąd podczas uruchamiania aplikacji: {e}", exc_info=True)
        input("Naciśnij Enter aby zakończyć...")
        sys.exit(1)
    
    finally:
        logger.info("Zamykanie Game Launcher...")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
