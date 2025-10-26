# Konfiguracja ikony okna

## Opis problemu

Na systemie Windows, ikona aplikacji w pasku zadań mogła migotać lub znikać podczas najechania kursorem oraz w widoku Alt+Tab. Problem wynikał z braku prawidłowej konfiguracji ikony okna.

## Rozwiązanie

### 1. Plik ikony

Utworzono plik ikony `app/assets/game_launcher.ico` zawierający ikonę w formatach:
- 16x16 pikseli
- 32x32 pikseli
- 48x48 pikseli
- 64x64 pikseli
- 128x128 pikseli
- 256x256 pikseli

Ikona przedstawia stylizowany gamepad z przyciskami i D-pad'em w kolorystyce zgodnej z motywem aplikacji.

### 2. Implementacja w MainWindow

W pliku `app/ui/main_window.py` dodano metodę `_set_window_icon()`, która:

1. **Na Windows**: Używa `wm_iconbitmap()` z bezwzględną ścieżką do pliku ICO
2. **Na innych platformach**: Używa `iconphoto()` z konwersją przez PIL/Pillow

### 3. Rozwiązywanie ścieżki

Ścieżka do ikony jest rozwiązywana dynamicznie:

```python
if getattr(sys, 'frozen', False):
    # Aplikacja skompilowana przez PyInstaller
    base_path = Path(sys._MEIPASS)
else:
    # Normalny tryb Python
    base_path = Path(__file__).resolve().parent.parent
    
icon_path = base_path / "assets" / "game_launcher.ico"
```

To zapewnia, że ikona będzie poprawnie znaleziona:
- Niezależnie od katalogu, z którego uruchamiana jest aplikacja
- W trybie normalnym Python
- Po skompikowaniu aplikacji do EXE (PyInstaller)

### 4. Kompatybilność międzyplatformowa

Kod jest specyficzny dla platformy:
- Na **Windows** używa natywnej metody `wm_iconbitmap()` - najbardziej stabilna metoda
- Na **macOS/Linux** próbuje użyć `iconphoto()` z konwersją obrazu
- Błędy są logowane, ale nie przerywają działania aplikacji

## Testowanie

Aby zweryfikować konfigurację ikony:

```bash
python3 test_icon.py
```

Skrypt sprawdza:
- Czy plik ikony istnieje
- Czy ścieżka jest poprawnie rozwiązywana
- Czy format pliku jest poprawny
- Rozmiar pliku i dostępne rozdzielczości

## Weryfikacja na Windows

Na systemie Windows należy sprawdzić:
1. Czy ikona pojawia się w pasku zadań
2. Czy ikona nie znika podczas najechania kursorem
3. Czy ikona jest widoczna w widoku Alt+Tab
4. Czy ikona pozostaje stabilna podczas minimalizacji/maksymalizacji okna

## Uwagi dla PyInstaller

Podczas tworzenia pliku EXE należy upewnić się, że katalog `app/assets/` jest dołączony:

```python
# W pliku .spec dla PyInstaller
datas=[
    ('app/assets', 'app/assets'),
],
```

## Powiązane pliki

- `app/ui/main_window.py` - implementacja ustawiania ikony
- `app/assets/game_launcher.ico` - plik ikony
- `test_icon.py` - skrypt testowy
