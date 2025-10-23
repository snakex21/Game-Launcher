# 📝 Changelog - Game Launcher

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
