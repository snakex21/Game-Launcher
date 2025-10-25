# Naprawa migającej ikony na pasku zadań Windows

## Wprowadzone zmiany

### 1. Utworzenie katalogu assets
- Utworzono katalog `app/assets/` do przechowywania zasobów statycznych aplikacji

### 2. Wygenerowanie pliku ikony
- Utworzono `app/assets/game_launcher.ico` z wieloma rozdzielczościami (16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
- Ikona przedstawia stylizowany gamepad w kolorystyce zgodnej z motywem aplikacji
- Format: ICO z kanałem alfa (RGBA)

### 3. Modyfikacja MainWindow (`app/ui/main_window.py`)

#### Dodane importy:
```python
import platform
import sys
from pathlib import Path
```

#### Nowa metoda `_set_window_icon()`:
- Ustawia ikonę okna przy inicjalizacji
- Wykorzystuje `wm_iconbitmap()` na Windows (najbardziej stabilna metoda)
- Wykorzystuje `iconphoto()` na innych platformach
- Rozwiązuje ścieżkę względną do absolutnej
- Obsługuje zarówno normalny tryb Python jak i PyInstaller (frozen)
- Loguje komunikaty o sukcesie/błędach

#### Wywołanie w `__init__`:
```python
self._set_window_icon()  # Dodane po ustawieniu geometrii, przed motywem
```

### 4. Dokumentacja
- `docs/ICON_CONFIGURATION.md` - szczegółowy opis rozwiązania
- `app/assets/README.md` - dokumentacja zawartości katalogu assets
- `test_icon.py` - skrypt testowy do weryfikacji konfiguracji

## Rozwiązane problemy

✓ Ikona nie znika podczas najechania kursorem na pasku zadań Windows  
✓ Ikona jest widoczna w Alt+Tab  
✓ Ścieżka jest poprawnie rozwiązywana niezależnie od miejsca uruchamiania  
✓ Kompatybilność z innymi platformami (macOS/Linux) zachowana  
✓ Obsługa trybu PyInstaller (frozen executable)  

## Testowanie

### Test podstawowy:
```bash
python3 test_icon.py
```

### Uruchomienie z różnych katalogów:
```bash
cd /tmp
python3 /path/to/project/test_icon.py
```

### Uruchomienie aplikacji:
```bash
python3 main.py
```

## Uwagi techniczne

1. **Rozwiązywanie ścieżki**: Używa `Path(__file__).resolve().parent.parent` do znalezienia bazowego katalogu `app/`
2. **PyInstaller**: Obsługuje `sys._MEIPASS` dla skompilowanych aplikacji
3. **Wieloplatformowość**: Kod automatycznie wykrywa platformę i stosuje odpowiednią metodę
4. **Obsługa błędów**: Wszystkie błędy są logowane, ale nie przerywają działania aplikacji

## Pliki zmienione

- ✏️ `app/ui/main_window.py` - dodano metodę `_set_window_icon()` i jej wywołanie
- ➕ `app/assets/game_launcher.ico` - nowy plik ikony
- ➕ `app/assets/README.md` - dokumentacja assets
- ➕ `docs/ICON_CONFIGURATION.md` - dokumentacja rozwiązania
- ➕ `test_icon.py` - skrypt testowy

## Zgodność

- ✓ Windows 10/11 (główny cel poprawki)
- ✓ Linux (testowane)
- ✓ macOS (powinno działać, wymaga testów na sprzęcie)
- ✓ Python 3.8+
- ✓ CustomTkinter
- ✓ PIL/Pillow

## Referencje

- Ticket: "Naprawa migającej ikony na pasku zadań Windows"
- Branch: `fix/windows-taskbar-icon-flicker-use-ico-resolve-path`
