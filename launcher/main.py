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

import game_launcher


def main():
    """Główna funkcja uruchamiająca aplikację."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    game_launcher.main()


if __name__ == "__main__":
    main()
