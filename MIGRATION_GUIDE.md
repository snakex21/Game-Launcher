# Przewodnik Migracji z Wersji 1.0 do 2.0

## Co się zmieniło?

### Stary plik game_launcher.py (40,000+ linii)
Został zastąpiony prostym wrapperem, który przekierowuje do `main.py`:
```python
from main import main

if __name__ == "__main__":
    main()
```

### Nowa struktura
Kod został podzielony na logiczne moduły w katalogu `app/`:
```
app/
├── core/           # Rdzeń (AppContext, EventBus, DataManager)
├── services/       # Logika biznesowa
├── plugins/        # Widoki/funkcje
├── ui/             # Komponenty UI
└── utils/          # Narzędzia pomocnicze
```

## Migracja danych

### Automatyczna migracja
Aplikacja automatycznie:
1. Odczytuje stary `config.json` jeśli istnieje
2. Uzupełnia brakujące pola domyślnymi wartościami
3. Tworzy backup przy błędach (`config_backup_YYYYMMDD_HHMMSS.json`)

### Ręczna migracja (opcjonalna)
Jeśli chcesz ręcznie przenieść dane:

1. **Backup starej konfiguracji**:
```bash
cp config.json config_v1_backup.json
```

2. **Uruchom nową wersję**:
```bash
python main.py
```

3. **Sprawdź dane** w nowym interfejsie

## Zmiany w strukturze danych

### Gry (games)
Struktura pozostaje kompatybilna:
```json
{
  "id": "string",
  "name": "string",
  "exe_path": "string",
  "genres": ["string"],
  "rating": 0.0,
  "play_time": 0,
  "completion": 0,
  "sessions": [],
  ...
}
```

### Przypomnienia (reminders)
Bez zmian w strukturze:
```json
{
  "id": "string",
  "title": "string",
  "message": "string",
  "remind_at": "ISO datetime",
  "repeat": "none|daily|weekly|monthly",
  "completed": false
}
```

### Ustawienia (settings)
Nowe pola:
- `theme`: "midnight" | "emerald" | "sunset" (zamiast "dark-blue")
- `accent`: kolor akcentu (hex)
- `custom_theme`: opcjonalny własny motyw

## API - dla developerów

### Stary sposób (v1.0)
```python
# Bezpośredni dostęp do config
config = load_config()
games = config["games"]
```

### Nowy sposób (v2.0)
```python
# Przez AppContext
context = AppContext("config.json")
games = context.games.games  # lista obiektów Game
```

### EventBus
```python
# Subskrybuj zdarzenia
context.event_bus.subscribe("games_changed", callback)

# Emituj zdarzenia
context.event_bus.emit("games_changed", game_id="123")
```

## Funkcje obecnie w budowie

Następujące funkcje z v1.0 są w planach na przyszłe wersje:
- Roadmapa gier
- Menedżer modów
- Zrzuty ekranu
- Osiągnięcia
- Chat (HTTP/Socket.IO)
- Overlay
- Synchronizacja z Google Drive/GitHub (szkielet istnieje w CloudService)
- Obsługa kontrolera
- Auto-start i minimalizacja do tray

## Rozwiązywanie problemów

### Aplikacja nie startuje
```bash
# Sprawdź logi
tail -f game_launcher.log
```

### Błąd importu
```bash
# Zainstaluj zależności
pip install -r requirements.txt
```

### Brak CustomTkinter
```bash
pip install customtkinter
```

### Stary plik config.json powoduje błędy
```bash
# Usuń i pozwól aplikacji utworzyć nowy
mv config.json config_old.json
python main.py
```

## Kontakt

Problemy? Otwórz issue na GitHub lub sprawdź:
- `README.md` - podstawowe info
- `README_REFACTOR.md` - szczegóły techniczne architektury
