# Game Launcher 3.0 🚀

Game Launcher to nowoczesna aplikacja desktopowa napisana w Pythonie, która pozwala zarządzać biblioteką gier, śledzić statystyki, planować roadmapę z kalendarzem, czytać newsy z RSS oraz organizować przypomnienia. Wersja 3.0 wprowadza kompletnie przeprojektowaną roadmapę z widokiem kalendarza i archiwum!

## 🎯 Co nowego w v3.0?
### 📅 ROADMAPA - Kompletna Przebudowa!
- **Trzy widoki**: 📋 Lista, 📅 Kalendarz, 📦 Archiwum
- **Widok kalendarza** - miesięczny kalendarz z polskimi nazwami dni i miesiąca
  - Pełna nawigacja ◀ / ▶ między miesiącami
  - Gry wyświetlane w zakresie dat start-target
  - Kolorowe oznaczenia według priorytetu (🔴 Wysoki, 🟡 Średni, ⚪ Niski)
  - Do 3 gier na dzień + licznik dodatkowych
- **Archiwum z kolorami miesięcy** - 12 unikalnych kolorów dla każdego miesiąca
  - Filtry: Wszystkie / Ukończone / W archiwum
  - Pełna legenda kolorów miesięcy (Sty-Gru)
  - Możliwość przywrócenia gier do aktywnych
- **Edycja wpisów** - pełna edycja aktywnych zadań roadmapy
- **Inteligentne powiadomienia**:
  - 🎉 Po ukończeniu gry
  - 🎯 Gdy osiągnięto cel (po sesji gry)
- **Integracja z osiągnięciami**:
  - 🗺️ Planista (30 pkt) - Ukończ 3 pozycje
  - 🗓️ Mistrz Planowania (60 pkt) - Ukończ 10 pozycji
- **Automatyczna migracja danych** - bezpieczne dodanie nowych pól

Zobacz [`CHANGELOG.md`](CHANGELOG.md) dla szczegółowego opisu wszystkich zmian v3.0!

## ✨ Najważniejsze zmiany
- Modularna struktura katalogów (`app/core`, `app/services`, `app/plugins`, `app/ui`, `app/utils`)
- Nowy kontekst aplikacji (`AppContext`) zapewniający wstrzykiwanie zależności
- Wydzielone usługi biznesowe (GameService, ReminderService, MusicService, ThemeService…)
- EventBus do komunikacji pomiędzy modułami
- Nowy, estetyczny interfejs oparty o CustomTkinter z motywami kolorystycznymi
- Pluginy odpowiadające za poszczególne sekcje aplikacji
- Domyślne dane startowe (`app/data/database.json`) oraz automatyczna migracja konfiguracji

Szczegóły architektury opisane są w sekcji 🏗️ Architektura powyżej.

## 🎉 Co było nowego w v2.2?
- **⚙️ Nowe ustawienia wielosekcyjne** - zakładki: Ogólne, Personalizacja, Dane, Chmura
- **👤 Profil zintegrowany z ustawieniami** - avatar, nazwa użytkownika i bio w zakładce Personalizacja
- **🎨 Edytor własnych motywów** - twórz i edytuj motywy bezpośrednio w aplikacji z color pickerami
- **🎨 Export/import motywów** - udostępniaj własne motywy kolorystyczne jako pliki JSON
- **🛡️ Zabezpieczenia motywów** - ochrona przed usunięciem motywów systemowych (midnight, emerald, sunset)
- **💾 Zaawansowane zarządzanie backupami** - wybór lokalizacji, export i import kopii zapasowych
- **☁️ Przygotowanie pod synchronizację** - sekcja chmury z placeholderami dla Google Drive i GitHub
- **🔄 System migracji danych** - automatyczna aktualizacja struktury danych przy upgrade

## 🎉 Co było nowego w v2.1?
- **🏆 Rozbudowany system osiągnięć** z automatycznym śledzeniem postępów i paskami postępu
- **🎵 Odtwarzacz muzyki z seekiem** - przewijaj utwory jak chcesz!
- **🎵 Mini kontrolka muzyki** - steruj muzyką z każdego miejsca w aplikacji (w sidebar)!
- **🎵 Synchronizacja odtwarzacza** - widok pamięta stan (utwór, czas, pozycja)!
- **📸 Manager zrzutów ekranu** - galeria ze screenshotami, auto-scan i przypisywanie do gier!

## 🚀 Uruchomienie
```bash
python main.py
```
Pierwsze uruchomienie utworzy plik `config.json` na podstawie domyślnej bazy (`app/data/database.json`).

## 📖 Szybki Przewodnik

### 🗺️ Roadmapa 3.0
**Trzy widoki planowania gier:**
- **📋 Lista** - Aktywne gry z priorytetami (🔴🟡⚪) i licznikiem dni
- **📅 Kalendarz** - Miesięczny widok z polskimi nazwami i nawigacją
- **📦 Archiwum** - Ukończone gry z kolorami miesięcy (12 unikalnych kolorów)

**Podstawowe operacje:**
1. Dodaj grę: `➕ Dodaj do Roadmapy` → wybierz grę → ustaw priorytet/daty
2. Edytuj wpis: `✏️ Edytuj` w widoku listy
3. Ukończ grę: `✅ Ukończ` → przenosi do archiwum z powiadomieniem 🎉
4. Przywróć z archiwum: `↺ Przywróć` w widoku archiwum

### 📚 Biblioteka Gier
1. Dodaj grę: `➕ Dodaj Grę` → nazwa, ścieżka .exe, gatunki, ocena
2. Uruchom grę: `▶️ Uruchom` na karcie gry
3. Gry z oceną ≥8.0 mają **złotą ramkę** 💎

### 🎵 Odtwarzacz Muzyki
1. Wybierz playlistę (folder z muzyką)
2. **Seek bar** - przeciągnij suwak do wybranego momentu
3. **Mini kontrolka** w sidebar - steruj z każdego widoku!

### 🏆 Osiągnięcia
Automatycznie odblokowują się przy:
- Ukończeniu 3 gier z roadmapy → 🗺️ Planista (30 pkt)
- Ukończeniu 10 gier z roadmapy → 🗓️ Mistrz Planowania (60 pkt)

### 🎨 Kolory i Priorytety
**Priorytety roadmapy:**
- 🔴 **Wysoki**: Czerwony (#e74c3c)
- 🟡 **Średni**: Pomarańczowy (#f39c12)
- ⚪ **Niski**: Szary (#95a5a6)

**Kolory miesięcy (archiwum):**
Sty 🩷  Lut 🍑  Mar 💛  Kwi 💚  Maj 💙  Cze 💜  Lip 🟣  Sie 🌸  Wrz 🪻  Paź 🧡  Lis 🩵  Gru ⚪

## 📦 Funkcjonalności
- **📚 Biblioteka gier** – dodawanie, uruchamianie, kafelkowy podgląd gier
- **📊 Statystyki** – wykresy czasu gry i podział gatunków (Matplotlib)
- **🏆 Osiągnięcia** – system osiągnięć z automatycznym śledzeniem postępów i paskami postępu
- **🗺️ Roadmapa 3.0** – planowanie gier z trzema widokami:
  - 📋 Lista z priorytetami i licznikiem dni
  - 📅 Kalendarz miesięczny z polskimi nazwami
  - 📦 Archiwum z kolorami miesięcy i filtrami
- **🔧 Mody** – zarządzanie modami dla gier
- **📸 Screenshoty** – galeria zrzutów ekranu z auto-scanem i przypisywaniem do gier
- **📰 Aktualności** – kanały RSS (Feedparser)
- **⏰ Przypomnienia** – powtarzalne alerty i zarządzanie zadaniami
- **🎵 Odtwarzacz muzyki** – obsługa playlist z folderów (pygame) + seek bar do przewijania utworów
- **⚙️ Ustawienia** – wielosekcyjny panel ustawień z zakładkami:
  - **Ogólne**: powiadomienia systemowe, kanały RSS
  - **Personalizacja**: profil użytkownika (avatar, nazwa, bio), motywy, export/import motywów
  - **Dane**: zarządzanie kopiami zapasowymi, wybór lokalizacji, export/import backupów
  - **Chmura**: konfiguracja synchronizacji (Google Drive, GitHub) - w przygotowaniu

## ⚙️ Konfiguracja
- **Discord Rich Presence**: wprowadź `discord_client_id` w ustawieniach
- **Kanały RSS**: dodawaj w panelu ustawień lub bezpośrednio w `config.json`
- **Powiadomienia systemowe**: sterowane z poziomu UI

## 🧩 Architektura pluginów
Każda sekcja interfejsu to osobny plugin – łatwo dodasz kolejne widoki.
```python
from .base import BasePlugin

class LibraryPlugin(BasePlugin):
    name = "Library"

    def register(self, context: AppContext) -> None:
        ...
```
Widok pluginu dziedziczy z `customtkinter.CTkFrame`.

## 📚 Dokumentacja
- [`CHANGELOG.md`](CHANGELOG.md) - Historia wszystkich zmian
- [`docs/STATISTICS_API.md`](docs/STATISTICS_API.md) - API modułu statystyk

## 🏗️ Architektura

Game Launcher używa nowoczesnej, modularnej architektury z wzorcami projektowymi:

```
app/
├── core/                    # Rdzeń aplikacji
│   ├── app_context.py      # Kontekst i dependency injection
│   ├── event_bus.py        # Publish/subscribe dla luźnego powiązania
│   └── data_manager.py     # Centralne zarządzanie danymi JSON
├── services/               # Logika biznesowa
│   ├── game_service.py     # Zarządzanie biblioteką gier
│   ├── session_tracker.py  # Śledzenie aktywnych sesji
│   ├── reminder_service.py # Obsługa przypomnień
│   ├── music_service.py    # Odtwarzacz muzyki (pygame)
│   ├── theme_service.py    # System motywów
│   ├── discord_service.py  # Discord Rich Presence
│   ├── cloud_service.py    # Synchronizacja z chmurą
│   └── notification_service.py # Powiadomienia systemowe
├── plugins/                # Widoki i funkcjonalności
│   ├── base.py            # Interfejs bazowy pluginu
│   ├── library.py         # Widok biblioteki gier
│   ├── statistics.py      # Wykresy i statystyki
│   ├── news.py            # Aktualności (RSS)
│   ├── reminders.py       # Przypomnienia
│   ├── music_player.py    # Odtwarzacz muzyki
│   └── settings.py        # Panel ustawień
├── ui/                    # Komponenty interfejsu
│   └── main_window.py     # Główne okno z nawigacją
├── utils/                 # Narzędzia pomocnicze
│   └── image_utils.py     # Obróbka obrazów
└── data/                  # Dane początkowe
    └── database.json      # Przykładowe dane startowe
```

### Wzorce Projektowe
- **Dependency Injection** (AppContext) - Centralne wstrzykiwanie zależności
- **Event Bus Pattern** - Luźne powiązanie między komponentami poprzez publish/subscribe
- **Plugin Architecture** - Każda funkcjonalność to osobny plugin
- **Service Layer** - Oddzielenie logiki biznesowej od UI

## 🔄 Migracja z Wersji 1.0

Stary monolityczny plik `game_launcher.py` (40,000+ linii) został zastąpiony prostym wrapperem. Aplikacja automatycznie:
1. Odczytuje stary `config.json` jeśli istnieje
2. Uzupełnia brakujące pola domyślnymi wartościami
3. Tworzy backup przy błędach

## 🚀 Plan Rozwoju

**Następne funkcje w priorytecie:**
- 📸 Manager zrzutów ekranu (auto-scan, galeria)
- 🎮 Obsługa emulatorów (retro gry)
- 🎮 Obsługa kontrolera (gamepad)
- 🖥️ Minimalizacja do tray
- 👁️ Overlay podczas gry
- ☁️ Synchronizacja z chmurą (Google Drive, GitHub)
- 💬 Chat (HTTP/Socket.IO)

## 🤝 Kontrybucje
Pull requesty są mile widziane! Przed dodaniem nowych funkcji zapoznaj się z architekturą projektu opisaną powyżej oraz z zasadami EventBus API:
- Używaj `event_bus.subscribe()` do rejestracji listenerów
- Zawsze czyść subskrypcje w metodzie `destroy()`
- Emituj zdarzenia przez `event_bus.emit()`

---
**Autorzy**: Game Launcher Team  
**Wersja**: 3.0.0  
**Data wydania**: 2024-10-25
