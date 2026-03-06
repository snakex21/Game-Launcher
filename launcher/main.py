#!/usr/bin/env python3
"""
Game Launcher - Punkt wejścia
Uruchamia aplikację Game Launcher.
"""

import os
import sys
import tkinter as tk
import logging

# Dodaj katalog główny do path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_launcher import GameLauncher


def main():
    """Główna funkcja uruchamiająca aplikację."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    root = tk.Tk()
    
    # Ustawienie ikony
    try:
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            logging.warning(f"Plik ikony '{icon_path}' nie został znaleziony.")
    except Exception as e:
        logging.error(f"Nie można ustawić ikony okna: {e}")
    
    app = GameLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
