# Changelog

## [2.0.0] - 2024-10-22

### 🎉 Nowa wersja - całkowita refaktoryzacja!

### ✨ Dodano
- **Modularna architektura** - podzielono monolityczny plik na logiczne moduły
- **AppContext** - centralne zarządzanie zależnościami (Dependency Injection)
- **EventBus** - komunikacja pub/sub między modułami
- **DataManager** - zarządzanie konfiguracją JSON z automatycznymi backupami
- **System motywów** - 3 gotowe motywy (Midnight, Emerald, Sunset) + wybór koloru akcentu
- **Plugin Architecture** - każda funkcjonalność jako osobny plugin
- **Testy jednostkowe** - `test_basic.py` z 6 testami podstawowymi

### 🎨 UI
- **CustomTkinter** zamiast standardowego Tkinter
- Nowoczesny, płynny interfejs z profesjonalnym wyglądem
- Sidebar z nawigacją między widokami
- Responsywny design z dynamicznym skalowaniem
- Highlight aktywnego widoku w nawigacji

### 🏗️ Architektura
- `app/core/` - AppContext, EventBus, DataManager
- `app/services/` - GameService, ReminderService, MusicService, ThemeService, itp.
- `app/plugins/` - Library, Statistics, News, Reminders, MusicPlayer, Settings
- `app/ui/` - MainWindow z pełną obsługą motywów
- `app/utils/` - narzędzia pomocnicze (image_utils)
- `app/data/` - domyślne dane startowe

### 🛠️ Serwisy
- **GameService** - zarządzanie biblioteką gier (dodawanie, edycja, uruchamianie)
- **SessionTracker** - śledzenie aktywnych sesji gier
- **ReminderService** - przypomnienia z powtarzaniem
- **MusicService** - odtwarzacz muzyki (pygame)
- **ThemeService** - system motywów kolorystycznych
- **DiscordService** - Discord Rich Presence
- **CloudService** - szkielet synchronizacji z chmurą
- **NotificationService** - powiadomienia systemowe

### 📚 Dokumentacja
- `README.md` - zaktualizowany główny przewodnik
- `README_REFACTOR.md` - szczegółowy opis architektury
- `MIGRATION_GUIDE.md` - przewodnik migracji z v1.0
- `STRUKTURA.md` - drzewo katalogów i przepływ danych
- `CHANGELOG.md` - historia zmian

### 🔧 Optymalizacje
- Lazy loading widoków
- Type hints wszędzie
- Efektywne zarządzanie pamięcią
- Strukturalne logowanie do pliku i konsoli
- Właściwa obsługa błędów z backupami

### 📦 Pluginy
1. **Library** - biblioteka gier z kafelkami
2. **Statistics** - wykresy słupkowe i kołowe (matplotlib)
3. **News** - aktualności z kanałów RSS
4. **Reminders** - system przypomnień
5. **MusicPlayer** - odtwarzacz z playlistami
6. **Settings** - panel konfiguracji

### 🔄 Zmieniono
- Stary `game_launcher.py` (40k linii) → wrapper do `main.py`
- Tkinter → CustomTkinter
- Bezpośredni dostęp do config → przez DataManager
- Globalne funkcje → usługi w AppContext
- Monolityczna struktura → modularna

### 🐛 Naprawiono
- Lepsza obsługa pustych plików JSON
- Automatyczne backupy przy błędach parsowania
- Proper cleanup przy zamykaniu widoków (unsubscribe z EventBus)
- Kompatybilność ze starymi konfiguracjami

### ⚠️ Do zrobienia w przyszłych wersjach
- Roadmapa gier
- Menedżer modów
- Manager zrzutów ekranu
- System osiągnięć
- Chat (HTTP/Socket.IO)
- Overlay dla gier
- Pełna integracja z Google Drive/GitHub
- Obsługa kontrolera
- Auto-start i minimalizacja do tray

### 📝 Uwagi techniczne
- Python 3.10+ wymagany
- 26 plików modułów (vs 1 plik 40k linii w v1.0)
- CustomTkinter, pygame, matplotlib, feedparser jako główne zależności
- JSON jako baza danych z automatycznym tworzeniem struktury

---

## [1.0.0] - 2024 (legacy)

Oryginalny monolityczny plik `game_launcher.py` z wszystkimi funkcjami w jednym miejscu.

### Funkcje v1.0
- Biblioteka gier
- Uruchamianie gier
- Statystyki czasu gry
- Menedżer modów
- Roadmapa
- Aktualności RSS
- Przypomnienia
- Discord Rich Presence
- Synchronizacja z chmurą
- Obsługa kontrolera
- Chat
- Overlay
- Odtwarzacz muzyki
- System osiągnięć

**Struktura**: Jeden plik 40,381 linii
