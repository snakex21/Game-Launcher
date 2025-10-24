# Reforma Odtwarzacza Muzyki - Dokumentacja

## Przegląd zmian

Odtwarzacz muzyki został w pełni przebudowany, aby zapewnić lepszą funkcjonalność i doświadczenie użytkownika.

## Nowe funkcje

### 1. Zarządzanie Playlistami

#### Wielkie Playlisty
- Możliwość tworzenia i zarządzania wieloma playlistami
- Zapisywanie playlist w formatach JSON i M3U
- Automatyczne wczytywanie playlist przy starcie aplikacji
- Przełączanie między playlistami za pomocą menu rozwijanego

#### Lokalizacja Playlist
- Playlisty przechowywane w: `app/data/playlists/`
- Format JSON: pełne metadane playlisty
- Format M3U: kompatybilność z innymi odtwarzaczami

#### Operacje na Playlistach
- **Wczytaj folder**: Importuj wszystkie utwory z wybranego folderu
- **Zapisz**: Zapisz aktualną playlistę pod wybraną nazwą
- **Dodaj utwory**: Dodaj pojedyncze pliki do playlisty
- **Usuń utwór**: Usuń wybrany utwór z playlisty
- **Wyczyść**: Wyczyść całą playlistę

### 2. Foldery Muzyczne

#### Konfiguracja Folderów
- Foldery muzyczne zapisywane w `config.json` pod `settings.music.music_folders`
- Automatyczne skanowanie wewnętrznego katalogu launchera: `app/data/music/`
- Możliwość dodawania wielu folderów źródłowych

#### Funkcje
```python
# Dodaj folder muzyczny
music_service.add_music_folder("/ścieżka/do/muzyki")

# Usuń folder muzyczny
music_service.remove_music_folder("/ścieżka/do/muzyki")

# Skanuj wszystkie foldery
tracks = music_service.scan_music_folders()
```

### 3. Tryby Odtwarzania

#### Tryb Losowy (Shuffle)
- Ikona: 🔀
- Losowe odtwarzanie utworów z playlisty
- Historia ostatnich 10 utworów aby uniknąć powtórzeń
- Przełącznik w głównym oknie odtwarzacza
- Wskaźnik w mini-odtwarzaczu

#### Tryby Zapętlenia (Loop)
Trzy tryby zapętlenia:

1. **Brak zapętlenia** (🔁 szary)
   - Odtwarzanie zatrzymuje się na końcu playlisty
   
2. **Zapętlenie utworu** (🔂 niebieski)
   - Aktualny utwór powtarza się w nieskończoność
   
3. **Zapętlenie playlisty** (🔁 niebieski)
   - Playlista odtwarza się od początku po zakończeniu

#### Cykliczne przełączanie
- Kliknij przycisk loop aby przełączać między trybami
- Stan zachowywany w konfiguracji

### 4. Ulepszone UI

#### Główny Odtwarzacz
- **Panel playlist** (lewa strona):
  - Lista wszystkich utworów z możliwością kliknięcia
  - Wizualne zaznaczenie aktualnie odtwarzanego utworu
  - Przyciski zarządzania playlistą
  - Selektor playlist

- **Panel odtwarzacza** (prawa strona):
  - Duże przyciski kontrolne
  - Przyciski shuffle i loop z kolorowym stanem
  - Pasek postępu z czasem
  - Regulacja głośności z procentowym wskaźnikiem

#### Przyciski Kontrolne
- 🔀 **Shuffle**: Tryb losowy
- ⏮ **Poprzedni**: Poprzedni utwór
- ▶/⏸ **Play/Pause**: Połączony przycisk odtwarzania/pauzy
- ⏭ **Następny**: Następny utwór
- 🔁/🔂 **Loop**: Cykliczne zapętlenie

#### Tooltipsy
Wszystkie przyciski mają polskie tooltipsy pokazujące aktualny stan:
- "Tryb losowy: włączony/wyłączony"
- "Zapętlenie: wyłączone/utwór/playlista"
- "Odtwórz/Wstrzymaj"
- "Poprzedni/Następny utwór"

### 5. Mini-Odtwarzacz

#### Nowe Zachowanie
- **Pojawia się tylko podczas odtwarzania**: Mini-player jest widoczny tylko gdy muzyka faktycznie gra
- **Nie zmniejsza przestrzeni nawigacji**: Pojawia się dynamicznie na dole sidebara
- **Synchronizacja stanu**: Pełna synchronizacja z głównym odtwarzaczem

#### Wskaźniki
- **Shuffle**: 🔀 (szary/niebieski)
- **Loop**: 🔁/🔂 (szary/niebieski)
- Nazwa utworu i czas odtwarzania
- Przyciski kontrolne (poprzedni/play-pause/następny)

### 6. Obsługa Błędów

#### Komunikaty w języku polskim
Wszystkie błędy wyświetlane są po polsku:
- "Nie udało się zainicjalizować pygame.mixer. Sprawdź czy są zainstalowane odpowiednie kodeki audio."
- "Playlista jest pusta. Wczytaj playlistę lub dodaj utwory."
- "Błąd odtwarzania: [szczegóły]. Sprawdź czy plik istnieje i jest w obsługiwanym formacie."
- "Katalog nie istnieje: [ścieżka]"
- "Nie udało się zapisać playlisty: [szczegóły]"

#### Event Bus
Błędy emitowane przez event bus jako `music_error`:
```python
event_bus.emit("music_error", error="Komunikat błędu")
```

### 7. Persystencja

#### Config.json
Konfiguracja muzyki zapisywana w `settings.music`:
```json
{
  "settings": {
    "music": {
      "shuffle": false,
      "loop_mode": "no_loop",
      "music_folders": [
        "/ścieżka/do/muzyki",
        "/home/engine/project/app/data/music"
      ]
    }
  }
}
```

#### Playlisty
Zapisywane automatycznie w `app/data/playlists/`:
- Format JSON dla metadanych
- Format M3U dla kompatybilności
- Automatyczne wczytywanie przy starcie

## API MusicService

### Nowe metody

#### Zarządzanie Playlistami
```python
# Zapisz playlistę
music.save_playlist("Moja Playlista", format="json")  # lub "m3u"

# Wczytaj playlistę po nazwie
music.load_playlist_by_name("Moja Playlista")

# Usuń playlistę
music.delete_playlist("Moja Playlista")
```

#### Foldery Muzyczne
```python
# Dodaj folder
music.add_music_folder("/ścieżka/do/muzyki")

# Usuń folder
music.remove_music_folder("/ścieżka/do/muzyki")

# Skanuj foldery
tracks = music.scan_music_folders()
```

#### Tryby Odtwarzania
```python
from app.services.music_service import LoopMode

# Ustaw shuffle
music.set_shuffle(True)  # lub False

# Ustaw tryb zapętlenia
music.set_loop_mode(LoopMode.LOOP_TRACK)

# Cykliczne przełączanie loop
next_mode = music.cycle_loop_mode()
```

#### Zarządzanie Utworem
```python
# Sprawdź czy utwór się zakończył (obsługuje autoplay)
music.check_track_ended()
```

### Nowe właściwości
```python
music.shuffle_mode       # bool
music.loop_mode          # LoopMode enum
music.playlist_name      # str
music.playlists          # dict[str, list[str]]
music.shuffle_history    # list[int]
music.music_folders      # list[str]
```

### Nowe eventy

#### Event Bus
```python
# Playlisty
"playlist_loaded"   # tracks: int, name: str
"playlist_saved"    # name: str
"playlist_deleted"  # name: str

# Tryby odtwarzania
"shuffle_changed"     # enabled: bool
"loop_mode_changed"   # mode: str

# Błędy
"music_error"  # error: str
```

## Kompatybilność

### Zachowana funkcjonalność
- ✅ Regulacja głośności
- ✅ Przewijanie utworów
- ✅ Kompatybilność z pygame
- ✅ Obsługa formatów: MP3, WAV, OGG, FLAC
- ✅ Cache długości utworów
- ✅ Legacy metoda `load_playlist(directory)`

### Nowe wymagania
Brak dodatkowych wymagań - wszystkie nowe funkcje używają istniejących zależności.

## Migracja z poprzedniej wersji

### Automatyczna migracja
Przy pierwszym uruchomieniu:
1. Istniejące playlisty są zachowane
2. Wewnętrzny katalog muzyki jest automatycznie dodawany
3. Domyślne ustawienia są tworzone w config.json

### Ręczna migracja playlist
Jeśli masz playlisty w starym formacie:
1. Wczytaj folder z muzyką
2. Użyj "Zapisz" aby stworzyć nową playlistę
3. Playlista zostanie zapisana w nowym formacie

## Testy

### Testy manualne na Windows
Rekomendowane scenariusze testowe:

1. **Podstawowe odtwarzanie**
   - Wczytaj folder z muzyką
   - Odtwórz utwór
   - Sprawdź czy mini-player się pojawia
   - Wstrzymaj - mini-player powinien pozostać
   - Zatrzymaj - mini-player powinien zniknąć

2. **Tryby odtwarzania**
   - Włącz shuffle - sprawdź losowe odtwarzanie
   - Przełącz loop modes - sprawdź zachowanie na końcu playlisty/utworu
   - Sprawdź czy wskaźniki się aktualizują

3. **Zarządzanie playlistami**
   - Dodaj pojedyncze utwory
   - Zapisz playlistę
   - Wczytaj zapisaną playlistę
   - Usuń utwór z playlisty

4. **Obsługa błędów**
   - Spróbuj wczytać nieistniejący folder
   - Spróbuj odtworzyć uszkodzony plik
   - Sprawdź czy komunikaty są po polsku

## Znane ograniczenia

1. **Mutagen**: Jeśli biblioteka mutagen nie jest zainstalowana, długość utworów będzie domyślnie ustawiona na 3 minuty
2. **Pygame**: Wymaga prawidłowej instalacji pygame z obsługą audio
3. **M3U**: Playlisty M3U używają bezwzględnych ścieżek - nie są przenośne między systemami

## Przyszłe usprawnienia

Potencjalne rozszerzenia:
- Import/eksport playlist z innych źródeł
- Wyszukiwanie utworów w playliście
- Sortowanie playlist
- Obsługa okładek albumów
- Equalizery audio
- Crossfade między utworami
- Obsługa tagów ID3
- Historia odtwarzania
