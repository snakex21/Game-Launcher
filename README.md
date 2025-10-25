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

Szczegóły architektury opisane są w pliku [`README_REFACTOR.md`](README_REFACTOR.md).

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
- [`README_REFACTOR.md`](README_REFACTOR.md) - Architektura i standardy
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) - Przewodnik migracji
- [`PLAN_ROZWOJU.md`](PLAN_ROZWOJU.md) - Plan dalszego rozwoju
- [`ROADMAP_CALENDAR_ARCHIVE.md`](ROADMAP_CALENDAR_ARCHIVE.md) - Dokumentacja Roadmapy 3.0

## 🤝 Kontrybucje
Pull requesty są mile widziane! Przed dodaniem nowych funkcji zapoznaj się z [`README_REFACTOR.md`](README_REFACTOR.md), gdzie opisano standardy i wzorce wykorzystane w projekcie.

---
**Autorzy**: Game Launcher Team  
**Wersja**: 3.0.0  
**Data wydania**: 2024-10-25
