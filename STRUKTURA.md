# Struktura Projektu Game Launcher 2.0

## Drzewo katalogów

```
game-launcher/
├── app/
│   ├── __init__.py
│   ├── core/                    # 🔧 Rdzeń aplikacji
│   │   ├── __init__.py
│   │   ├── app_context.py       # Kontekst dependency injection
│   │   ├── event_bus.py         # Pub/sub dla komunikacji
│   │   └── data_manager.py      # Zarządzanie JSON
│   │
│   ├── services/                # 💼 Usługi biznesowe
│   │   ├── __init__.py
│   │   ├── game_service.py      # Biblioteka gier
│   │   ├── session_tracker.py   # Śledzenie sesji
│   │   ├── reminder_service.py  # Przypomnienia
│   │   ├── music_service.py     # Odtwarzacz
│   │   ├── theme_service.py     # Motywy
│   │   ├── discord_service.py   # Discord RPC
│   │   ├── cloud_service.py     # Synchronizacja
│   │   └── notification_service.py # Powiadomienia
│   │
│   ├── plugins/                 # 🔌 Pluginy widoków
│   │   ├── __init__.py
│   │   ├── base.py              # Klasa bazowa
│   │   ├── library.py           # Biblioteka gier
│   │   ├── statistics.py        # Statystyki
│   │   ├── news.py              # Newsy RSS
│   │   ├── reminders.py         # Przypomnienia
│   │   ├── music_player.py      # Odtwarzacz
│   │   └── settings.py          # Ustawienia
│   │
│   ├── ui/                      # 🖼️ Interfejs użytkownika
│   │   ├── __init__.py
│   │   └── main_window.py       # Główne okno
│   │
│   ├── utils/                   # 🛠️ Narzędzia
│   │   ├── __init__.py
│   │   └── image_utils.py       # Obróbka obrazów
│   │
│   └── data/                    # 📊 Dane domyślne
│       └── database.json        # Snapshot startowy
│
├── main.py                      # 🚀 Punkt wejścia
├── game_launcher.py             # Wrapper dla kompatybilności
├── config.json                  # Konfiguracja użytkownika
├── requirements.txt             # Zależności Python
├── test_basic.py                # Testy jednostkowe
│
├── README.md                    # Dokumentacja główna
├── README_REFACTOR.md           # Szczegóły architektury
├── MIGRATION_GUIDE.md           # Przewodnik migracji
└── STRUKTURA.md                 # Ten plik
```

## Przepływ danych

```
┌─────────────┐
│   main.py   │  Inicjalizuje AppContext
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│   AppContext     │  Rejestruje serwisy i pluginy
│  - EventBus      │
│  - DataManager   │
└──────┬───────────┘
       │
       ├─► GameService
       ├─► ReminderService
       ├─► MusicService
       ├─► ThemeService
       ├─► ...
       │
       ▼
┌──────────────────┐
│   MainWindow     │  Renderuje UI z sidebar
└──────┬───────────┘
       │
       ├─► LibraryView (plugin)
       ├─► StatisticsView (plugin)
       ├─► NewsView (plugin)
       └─► SettingsView (plugin)
```

## Komunikacja między modułami

### EventBus

```python
# Subskrypcja
context.event_bus.subscribe("games_changed", callback)

# Emitowanie
context.event_bus.emit("games_changed", game_id="123")
```

### Przykładowe eventy:
- `games_changed` – zmiana w bibliotece gier
- `theme_changed` – zmiana motywu
- `reminders_changed` – aktualizacja przypomnień
- `session_started` – rozpoczęcie gry
- `session_ended` – zakończenie gry
- `music_started` – odtwarzanie utworu
- `data_saved` – zapis konfiguracji

## Wzorce projektowe

1. **Dependency Injection** (`AppContext`)
   - Centralne zarządzanie zależnościami
   - Łatwe mockowanie w testach

2. **Event Bus** (`EventBus`)
   - Luźne powiązanie modułów
   - Reaktywna aktualizacja UI

3. **Plugin Architecture**
   - Każdy widok jako osobny plugin
   - Łatwe dodawanie nowych funkcji

4. **Service Layer**
   - Logika biznesowa oddzielona od UI
   - Możliwość użycia CLI/API

5. **Data Access Object**
   - `DataManager` jako centralne repozytorium
   - JSON jako baza danych

## Szczegóły techniczne

### Warstwy

1. **Core** – fundamenty aplikacji
2. **Services** – logika biznesowa
3. **Plugins** – rozszerzenia funkcjonalne
4. **UI** – komponenty widoku
5. **Utils** – narzędzia pomocnicze

### Zależności

- **CustomTkinter** – nowoczesny UI
- **pygame** – odtwarzacz muzyki
- **matplotlib** – wykresy statystyk
- **feedparser** – parser RSS
- **plyer** – powiadomienia
- **psutil** – informacje o procesach
- **pypresence** – Discord RPC
- **Pillow** – obróbka obrazów

### Dane

Struktura `config.json`:
```json
{
  "games": [...],
  "reminders": [...],
  "settings": {
    "theme": "midnight",
    "accent": "#6366f1",
    "rss_feeds": [...],
    ...
  },
  "user": {
    "username": "...",
    "avatar": "..."
  }
}
```

## Rozszerzanie

### Dodawanie nowego pluginu

1. Utwórz `app/plugins/my_plugin.py`
2. Zaimplementuj `BasePlugin`
3. Dodaj widok dziedziczący z `CTkFrame`
4. Zarejestruj w `main.py`
5. Dodaj routing w `main_window.py`

### Dodawanie nowego serwisu

1. Utwórz `app/services/my_service.py`
2. Wstrzykaj przez konstruktor `data_manager` i `event_bus`
3. Zarejestruj w `main.py` przez `context.register_service()`
4. Użyj w pluginach przez `context.my_service`

---
**Wersja**: 2.0.0  
**Data**: Październik 2024
