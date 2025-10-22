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

## 🚀 Uruchomienie
```bash
python main.py
```
Pierwsze uruchomienie utworzy plik `config.json` na podstawie domyślnej bazy (`app/data/database.json`).

## 📦 Funkcjonalności
- **Biblioteka gier** – dodawanie, uruchamianie, kafelkowy podgląd gier
- **Statystyki** – wykresy czasu gry i podział gatunków (Matplotlib)
- **Aktualności** – kanały RSS (Feedparser)
- **Przypomnienia** – powtarzalne alerty i zarządzanie zadaniami
- **Odtwarzacz muzyki** – obsługa playlist z folderów (pygame)
- **Ustawienia** – wybór motywu, koloru akcentu, kanałów RSS, powiadomień

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
**Wersja**: 2.0.0
