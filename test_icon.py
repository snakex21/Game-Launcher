#!/usr/bin/env python3
"""Test skryptu do weryfikacji konfiguracji ikony."""
import platform
import sys
from pathlib import Path

def test_icon_path():
    """Testuj rozwiązywanie ścieżki do ikony."""
    print("=" * 60)
    print("Test konfiguracji ikony Game Launcher")
    print("=" * 60)
    
    # Symuluj logikę z MainWindow._set_window_icon()
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        print(f"Tryb: PyInstaller (frozen)")
    else:
        # Symuluj położenie app/ui/main_window.py
        base_path = Path(__file__).resolve().parent / "app"
        print(f"Tryb: Normalny Python")
    
    icon_path = base_path / "assets" / "game_launcher.ico"
    
    print(f"\nPlatforma: {platform.system()}")
    print(f"Python: {sys.version}")
    print(f"Ścieżka bazowa: {base_path}")
    print(f"Ścieżka ikony: {icon_path}")
    print(f"Ścieżka absolutna: {icon_path.resolve()}")
    
    if icon_path.exists():
        print(f"\n✓ Plik ikony znaleziony")
        import os
        size = os.path.getsize(icon_path)
        print(f"  Rozmiar: {size} bajtów")
        
        # Sprawdź czy to poprawny plik ICO
        try:
            from PIL import Image
            img = Image.open(icon_path)
            print(f"  Format: {img.format}")
            print(f"  Rozmiar obrazu: {img.size}")
            print(f"  Tryb: {img.mode}")
            print("\n✓ Plik ikony jest poprawny!")
        except Exception as e:
            print(f"\n✗ Błąd podczas otwierania ikony: {e}")
    else:
        print(f"\n✗ Plik ikony nie został znaleziony!")
        print(f"\nSzukano w: {icon_path.resolve()}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_icon_path()
