# Game Launcher 2.0 - Zrefaktoryzowana Architektura

## 📝 Przegląd

Całkowicie przepisana i zoptymalizowana wersja Game Launcher z wykorzystaniem nowoczesnej, modularnej architektury. Aplikacja została podzielona na mniejsze, łatwiejsze w zarządzaniu komponenty z zastosowaniem wzorców projektowych i najlepszych praktyk.

## ✨ Główne Zmiany

### 🎨 CustomTkinter
- **Nowoczesny interfejs**: Całkowicie przeprojektowany UI z użyciem CustomTkinter
- **Lepsze style**: Elegancki, płynny interfejs z profesjonalnymi animacjami
- **Responsywny design**: Dynamiczne skalowanie i dopasowanie do rozmiaru okna

### 🏗️ Architektura Modularna

```
app/
├── core/                    # Rdzeń aplikacji
│   ├── app_context.py      # Kontekst i dependency injection
│   ├── event_bus.py        # Publish/subscribe dla luźnego powiązania
│   └── data_manager.py     # Centralne zarządzanie danymi JSON
│
├── services/               # Logika biznesowa
│   ├── game_service.py     # Zarządzanie biblioteką gier
│   ├── session_tracker.py  # Śledzenie aktywnych sesji
│   ├── reminder_service.py # Obsługa przypomnień
│   ├── music_service.py    # Odtwarzacz muzyki (pygame)
│   ├── theme_service.py    # System motywów
│   ├── discord_service.py  # Discord Rich Presence
│   ├── cloud_service.py    # Synchronizacja z chmurą
│   └── notification_service.py # Powiadomienia systemowe
│
├── plugins/                # Widoki i funkcjonalności
│   ├── base.py            # Interfejs bazowy pluginu
│   ├── library.py         # Widok biblioteki gier
│   ├── statistics.py      # Wykresy i statystyki
│   ├── news.py            # Aktualności (RSS)
│   ├── reminders.py       # Przypomnienia
│   ├── music_player.py    # Odtwarzacz muzyki
│   └── settings.py        # Panel ustawień
│
├── ui/                    # Komponenty interfejsu
│   └── main_window.py     # Główne okno z nawigacją
│
├── utils/                 # Narzędzia pomocnicze
│   └── image_utils.py     # Obróbka obrazów
│
└── data/                  # Dane początkowe
    └── database.json      # Przykładowe dane startowe
```

## 🚀 Uruchamianie

### Wymagania
```bash
Python 3.10+
```

### Instalacja
```bash
# Aktywuj wirtualne środowisko (jeśli istnieje)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Uruchom aplikację
python main.py
```

## 🎯 Wzorce Projektowe

### 1. **Dependency Injection** (AppContext)
Wszystkie serwisy są rejestrowane centralnie i wstrzykiwane tam, gdzie są potrzebne:

```python
context = AppContext("config.json")
context.register_service("games", GameService(...))
context.games.add(game_data)
```

### 2. **Event Bus Pattern**
Luźne powiązanie między komponentami poprzez publish/subscribe:

```python
event_bus.subscribe("games_changed", callback)
event_bus.emit("games_changed", game_id=123)
```

### 3. **Plugin Architecture**
Każda funkcjonalność to osobny plugin, który można łatwo dodać lub usunąć:

```python
class LibraryPlugin(BasePlugin):
    def register(self, context: AppContext) -> None:
        # Inicjalizacja pluginu
```

### 4. **Service Layer**
Oddzielenie logiki biznesowej od UI:

```python
class GameService:
    def add(self, game_data) -> Game:
        # Logika biznesowa
        
class LibraryView(CTkFrame):
    # Tylko UI, używa GameService
```

## 📊 Optymalizacje

### Wydajność
- ✅ Lazy loading widoków
- ✅ Efektywne zarządzanie pamięcią
- ✅ Minimalizacja renderowania UI
- ✅ Asynchroniczne operacje I/O

### Kod
- ✅ Type hints wszędzie
- ✅ Dokumentacja docstrings
- ✅ Konsystentne formatowanie
- ✅ Logowanie strukturalne
- ✅ Właściwa obsługa błędów

### Struktura Danych
- ✅ Wykorzystanie dataclass dla modeli
- ✅ Immutable Theme obiekty
- ✅ Centralne zarządzanie konfiguracją
- ✅ Automatyczne backupy

## 🎨 System Motywów

Trzy predefiniowane motywy:
- **Midnight**: Ciemny niebieski (domyślny)
- **Emerald**: Ciemny zielony
- **Sunset**: Ciemny różowy

Każdy motyw posiada:
```python
@dataclass(frozen=True)
class Theme:
    name: str
    base_color: str
    background: str
    surface: str
    surface_alt: str
    text: str
    text_muted: str
    accent: str
```

## 🔌 Pluginy

### Aktualnie Dostępne

1. **Library** - Zarządzanie biblioteką gier
   - Dodawanie/edycja/usuwanie gier
   - Uruchamianie gier
   - Karty z informacjami

2. **Statistics** - Wykresy i statystyki
   - Wykres czasu gry
   - Podział gatunków (pie chart)
   - Agregacje danych

3. **News** - Aktualności ze świata gier
   - Pobieranie z kanałów RSS
   - Konfigurowalne źródła
   - Otwieranie linków w przeglądarce

4. **Reminders** - System przypomnień
   - Dodawanie/edycja/usuwanie
   - Powtarzalne przypomnienia
   - Status ukończenia

5. **Music Player** - Odtwarzacz muzyki
   - Obsługa MP3, WAV, OGG, FLAC
   - Playlisty z folderów
   - Kontrola głośności

6. **Settings** - Panel ustawień
   - Zmiana motywu
   - Kolor akcentu
   - Kanały RSS
   - Powiadomienia

### W Planach
- Roadmapa
- Menedżer Modów
- Zrzuty ekranu
- Osiągnięcia
- Chat

## 📝 Migracja z Wersji 1.0

Stary monolityczny plik `game_launcher.py` został przepisany. Aby zachować dane:

1. Wykonaj backup starego `config.json`
2. Uruchom nową wersję - automatycznie zaimportuje dane
3. Stary plik został zastąpiony prostym wrapperem uruchamiającym nową wersję

## 🐛 Debugging

Wszystkie logi są zapisywane do `game_launcher.log`:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

## 🤝 Rozwój

### Dodawanie Nowego Pluginu

1. Stwórz plik w `app/plugins/`:
```python
from .base import BasePlugin

class MyPlugin(BasePlugin):
    name = "MyPlugin"
    
    def register(self, context: AppContext) -> None:
        # Inicjalizacja
```

2. Stwórz widok:
```python
class MyView(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
```

3. Zarejestruj w `main.py`:
```python
context.add_plugin(MyPlugin())
```

4. Dodaj routing w `main_window.py`:
```python
elif view_id == "my_view":
    from app.plugins.my_plugin import MyView
    self.current_view = MyView(self.main_content, self.context)
```

## 📦 Zależności

Główne biblioteki:
- `customtkinter` - Nowoczesny UI
- `pygame` - Odtwarzacz muzyki
- `matplotlib` - Wykresy statystyk
- `feedparser` - Parser RSS
- `plyer` - Powiadomienia systemowe
- `psutil` - Informacje o procesach
- `pypresence` - Discord Rich Presence
- `Pillow` - Obróbka obrazów

## 📄 Licencja

Ten projekt jest open-source i dostępny na tych samych warunkach co oryginalna wersja.

## 💡 Wsparcie

Masz pytania lub sugestie? Zgłoś issue lub otwórz pull request!

---

**Wersja**: 2.0.0  
**Autor**: Game Launcher Team  
**Data**: 2024
