# Game Launcher 2.0

Game Launcher to nowoczesna aplikacja desktopowa napisana w Pythonie, która pozwala zarządzać biblioteką gier, śledzić statystyki, planować roadmapę, czytać newsy z RSS oraz organizować przypomnienia. Wersja 2.0 została całkowicie zrefaktoryzowana – monolityczny plik `game_launcher.py` został zastąpiony modularną architekturą, a interfejs otrzymał nowe życie dzięki CustomTkinter.

## ✨ Najważniejsze zmiany
- Modularna struktura katalogów (`app/core`, `app/services`, `app/plugins`, `app/ui`, `app/utils`)
- Nowy kontekst aplikacji (`AppContext`) zapewniający wstrzykiwanie zależności
- Wydzielone usługi biznesowe (GameService, ReminderService, MusicService, ThemeService…)
- EventBus do komunikacji pomiędzy modułami
- Nowy, estetyczny interfejs oparty o CustomTkinter z motywami kolorystycznymi
- Pluginy odpowiadające za poszczególne sekcje aplikacji
- Domyślne dane startowe (`app/data/database.json`) oraz automatyczna migracja konfiguracji

Szczegóły architektury opisane są w pliku [`README_REFACTOR.md`](README_REFACTOR.md).

## 🎉 Co nowego w v2.2?
- **⚙️ Nowe ustawienia wielosekcyjne** - zakładki: Ogólne, Personalizacja, Dane, Chmura
- **👤 Profil zintegrowany z ustawieniami** - avatar, nazwa użytkownika i bio w zakładce Personalizacja
- **🎨 Export/import motywów** - twórz i udostępniaj własne motywy kolorystyczne
- **💾 Zaawansowane zarządzanie backupami** - wybór lokalizacji, export i import kopii zapasowych
- **☁️ Przygotowanie pod synchronizację** - sekcja chmury z placeholderami dla Google Drive i GitHub
- **🔄 System migracji danych** - automatyczna aktualizacja struktury danych przy upgrade
- Zobacz [`CHANGES_USTAWIENIA.md`](CHANGES_USTAWIENIA.md) dla szczegółowego opisu modernizacji ustawień

## 🎉 Co było nowego w v2.1?
- **🏆 Rozbudowany system osiągnięć** z automatycznym śledzeniem postępów i paskami postępu
- **🎵 Odtwarzacz muzyki z seekiem** - przewijaj utwory jak chcesz!
- **🎵 Mini kontrolka muzyki** - steruj muzyką z każdego miejsca w aplikacji (w sidebar)!
- **🎵 Synchronizacja odtwarzacza** - widok pamięta stan (utwór, czas, pozycja)!
- **📸 Manager zrzutów ekranu** - galeria ze screenshotami, auto-scan i przypisywanie do gier!
- Zobacz [`ZMIANY_PL.md`](ZMIANY_PL.md) dla pełnego opisu zmian po polsku
- Zobacz [`PLAN_ROZWOJU.md`](PLAN_ROZWOJU.md) dla planu dalszego rozwoju
- Sprawdź [`CHANGELOG.md`](CHANGELOG.md) dla szczegółowej historii zmian

## 🚀 Uruchomienie
```bash
python main.py
```
Pierwsze uruchomienie utworzy plik `config.json` na podstawie domyślnej bazy (`app/data/database.json`).

## 📦 Funkcjonalności
- **📚 Biblioteka gier** – dodawanie, uruchamianie, kafelkowy podgląd gier
- **📊 Statystyki** – wykresy czasu gry i podział gatunków (Matplotlib)
- **🏆 Osiągnięcia** – system osiągnięć z automatycznym śledzeniem postępów i paskami postępu
- **🗺️ Roadmapa** – planowanie gier do ukończenia z priorytetami
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

## 🤝 Kontrybucje
Pull requesty są mile widziane! Przed dodaniem nowych funkcji zapoznaj się z [`README_REFACTOR.md`](README_REFACTOR.md), gdzie opisano standardy i wzorce wykorzystane w projekcie.

---
**Autorzy**: Game Launcher Team  
**Wersja**: 2.2.0
