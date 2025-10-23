# 📝 Changelog - Game Launcher

## [2.1.2] - 2024-01-XX

### 🐛 Naprawione Błędy

#### 🎵 Odtwarzacz Muzyki - Synchronizacja stanu
- **Problem:** Widok odtwarzacza "zapominał" stan po wyjściu i powrocie
  - Pokazywał "Nie wybrano playlisty" mimo że muzyka grała
  - Suwak był na 0:00, brak informacji o aktualnym utworze
- **Rozwiązanie:** Dodano synchronizację stanu przy wejściu na stronę
  - Nowa metoda `_sync_with_music_state()` aktualizuje UI według stanu `MusicService`
  - Pokazuje aktualny utwór, czas, pozycję suwaka
  - Automatycznie uruchamia timer jeśli muzyka gra
  - Dodano `destroy()` aby zapobiec memory leaks

**Przykład:** Muzyka gra "Utwór X" na 1:20 → wychodzę → wracam → ✅ widok pokazuje "Utwór X" 1:20 / 3:45

---

## [2.1.1] - 2024-01-XX

### ✨ Nowe Funkcje

#### 📸 Manager Zrzutów Ekranu
- **Galeria screenshotów** - przeglądaj zrzuty ekranu dla każdej gry
- **Auto-scan** - automatyczne wyszukiwanie screenshotów w folderach
- **Ręczne dodawanie** - wybierz pliki z dysku
- **Wzorce plików** - automatyczne rozpoznawanie typowych nazw screenshotów
- **Ignorowanie folderów** - pomija cache, temp, thumbnails
- **Podgląd miniatur** - obrazki 300x200px
- **Przypisywanie do gier** - każda gra ma własną galerię

Funkcje:
- `ScreenshotService` - skanowanie, dodawanie, usuwanie
- `ScreenshotsPlugin` - widok galerii z listą gier
- Konfiguracja folderów do skanowania
- Automatyczne przypisywanie na podstawie nazwy gry

### 🐛 Naprawione Błędy

#### 🎵 Odtwarzacz Muzyki - Seek i odtwarzanie w tle
- **Naprawiono seek bar** - suwak nie wraca już na 0:00 po przewinięciu
  - Dodano `seek_offset` do śledzenia pozycji po seekowaniu
  - `get_pos()` teraz poprawnie oblicza aktualną pozycję: `seek_offset + pygame_time`
  - Seek ładuje utwór od nowa z parametrem `start=position`
- **Muzyka gra w tle!** - dodano mini kontrolkę muzyki w sidebar
  - Kontrolka zawsze widoczna niezależnie od aktualnego widoku
  - Pokazuje nazwę utworu, czas (MM:SS / MM:SS) i przyciski ⏮▶/⏸⏭
  - Timer aktualizacji (500ms) działa globalnie w MainWindow
  - Automatyczne przejście do następnego utworu po zakończeniu

### 🔧 Ulepszenia

#### MusicService
- Dodano cache długości utworów (`track_length_cache`) dla lepszej wydajności
- Poprawiono `get_length()` aby cache'ować wyniki z mutagen
- Reset `seek_offset` przy odtwarzaniu nowego utworu

#### MainWindow
- Mini kontrolka muzyki w sidebar (row 11)
- Metody `_music_play()`, `_music_next()`, `_music_previous()` do globalnej kontroli
- Metoda `_update_music_status()` aktualizuje stan co 500ms

---

## [2.1.0] - 2024-01-XX

### ✨ Nowe Funkcje

#### 🏆 Rozbudowany System Osiągnięć
- **Mechanika warunkowa**: Każde osiągnięcie ma teraz `condition_type`, `target_value` i `current_progress`
- **Paski postępu**: Wizualne paski pokazują postęp w nieukończonych osiągnięciach (np. "3/10 gier")
- **Automatyczne sprawdzanie**: Osiągnięcia odblokowują się automatycznie gdy spełnisz warunki
- **Ikony**: Każde osiągnięcie ma dedykowaną ikonę emoji
- **Nowe osiągnięcia**:
  - 🎮 **Gracz Debiutant** (15 pkt) - Uruchom 5 różnych gier
  - 🏛️ **Mega Kolekcjoner** (50 pkt) - Dodaj 50 gier do biblioteki

Typy warunków:
- `library_size` - liczba gier w bibliotece
- `mods_count` - liczba zainstalowanych modów
- `games_launched_count` - liczba uruchomionych różnych gier
- `play_time_hours` - łączny czas gry w godzinach
- `roadmap_completed` - liczba ukończonych zadań roadmapy
- `manual` - ręczne odblokowywanie

#### 🎵 Odtwarzacz Muzyki z Seek Barem
- **Pasek postępu**: Wizualizacja aktualnej pozycji w utworze
- **Wyświetlanie czasu**: Aktualny czas / całkowity czas w formacie MM:SS
- **Przewijanie utworu**: Kliknij i przeciągnij suwak do wybranego momentu
- **Automatyczna aktualizacja**: Pozycja aktualizuje się co 0.5 sekundy
- **Auto-next**: Automatyczne przejście do następnego utworu po zakończeniu
- **Wsparcie dla wielu formatów**: MP3, WAV, OGG, FLAC

Funkcje seekowania:
- `get_pos()` - zwraca aktualną pozycję w sekundach
- `get_length()` - zwraca długość utworu (używa mutagen jeśli dostępny)
- `seek(position)` - przewija do podanej pozycji

### 🔧 Ulepszenia

#### Event System
Dodano nowe eventy do integracji z osiągnięciami:
- `game_added` - emitowany gdy dodajesz grę do biblioteki
- `game_launched` - emitowany gdy uruchamiasz grę
- `roadmap_completed` - emitowany gdy oznaczasz zadanie jako ukończone
- `mod_added` - emitowany gdy instalujesz mod

#### Achievement Service
- Metoda `check_and_update_progress()` - automatycznie sprawdza i aktualizuje wszystkie osiągnięcia
- Automatyczne odblokowanie przy osiągnięciu celu
- Zapisywanie postępu w `current_progress`

#### Music Service
- Metoda `get_pos()` - pobiera aktualną pozycję odtwarzania
- Metoda `get_length()` - pobiera długość utworu
- Metoda `seek(position)` - przewija do pozycji w sekundach

### 🐛 Naprawione Błędy

- **CustomTkinter border_color**: Naprawiono błąd `ValueError: transparency is not allowed` w osiągnięciach
  - Zmieniono `border_color="transparent"` na `border_color=self.theme.base_color`
  - Dla nieaktywnych ramek używamy `border_width=0` zamiast przezroczystego koloru

### 📚 Dokumentacja

- Zaktualizowano `NOWE_FUNKCJE.md` z opisem nowych mechanik osiągnięć
- Dodano sekcję o odtwarzaczu muzyki z seekiem
- Zaktualizowano tabele porównań funkcji
- Dodano porady dotyczące używania nowych funkcji

### 🔄 Zmiany Wewnętrzne

- Osiągnięcia mają teraz 7 domyślnych pozycji (było 5)
- `DEFAULT_ACHIEVEMENTS` zawiera pełną strukturę z ikonami i warunkami
- Achievement Plugin subskrybuje eventy: `game_added`, `game_launched`, `roadmap_completed`, `mod_added`
- Music Player używa timerów do aktualizacji UI co 500ms
- Dodano obsługę `is_seeking` aby uniknąć konfliktów podczas ręcznego przewijania

---

## [2.0.0] - 2024-01-10

### 🎉 Pierwsza wersja refaktoryzowanego launchera

- Przejście z monolitycznego `stary_launcher.py` (40k linii) na modularną strukturę
- System pluginów pod `app/plugins/`
- Centralne zarządzanie stanem przez `AppContext`
- Event Bus dla komunikacji między komponentami
- CustomTkinter UI zamiast Tkinter
- System motywów (dark/light)
- JSON database z automatycznymi backupami

### Główne funkcje:
- 📚 Biblioteka gier
- 📊 Statystyki
- 🗺️ Roadmapa gier
- 🔧 Manager modów
- 🏆 System osiągnięć (podstawowy)
- 📰 Newsy RSS
- ⏰ Przypomnienia
- 🎵 Odtwarzacz muzyki (podstawowy)
- 👤 Profil użytkownika
- ⚙️ Ustawienia

---

**Legenda:**
- ✨ Nowe funkcje
- 🔧 Ulepszenia
- 🐛 Naprawione błędy
- 📚 Dokumentacja
- 🔄 Zmiany wewnętrzne
- ⚠️ Breaking changes
- 🗑️ Usunięte funkcje
