"""
Game Launcher - Główny punkt wejścia aplikacji
AI-Friendly: Ten plik tylko inicjalizuje aplikację i uruchamia GUI
"""

import sys
import tkinter as tk
from pathlib import Path

# Dodaj ścieżkę projektu do sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager
from core.database import Database
from ui.main_window import MainWindow
from utils.logger import setup_logger


def main():
    """
    Główna funkcja startowa aplikacji.
    
    Inicjalizuje:
    - Logger
    - Manager konfiguracji
    - Bazę danych
    - Główne okno GUI
    """
    # Setup loggera
    logger = setup_logger()
    logger.info("=== Starting Game Launcher ===")
    
    try:
        # Inicjalizacja konfiguracji
        config_manager = ConfigManager()
        logger.info("Configuration loaded successfully")
        
        # Inicjalizacja bazy danych
        db = Database(config_manager.get_database_path())
        logger.info("Database initialized successfully")
        
        # Tworzenie głównego okna Tkinter
        root = tk.Tk()
        
        # Inicjalizacja głównego okna aplikacji
        app = MainWindow(root, config_manager, db)
        logger.info("Main window created successfully")
        
        # Start aplikacji
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Critical error during startup: {e}", exc_info=True)
        # Pokazanie error messagebox jeśli GUI się nie uruchomi
        try:
            tk.messagebox.showerror(
                "Startup Error",
                f"Failed to start Game Launcher:\n{str(e)}"
            )
        except:
            print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
    
    finally:
        logger.info("=== Game Launcher closed ===")


if __name__ == "__main__":
    main()