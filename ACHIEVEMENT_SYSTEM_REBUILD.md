# Przebudowa Systemu Osiągnięć i Edytora

## Podsumowanie Zmian

Ten dokument opisuje kompleksową przebudowę systemu osiągnięć w Game Launcher z rozszerzonym katalogiem, nowymi warunkami zakończenia, edytorem UI oraz mechanizmami import/export.

## 1. Rozszerzony Katalog Osiągnięć (DEFAULT_ACHIEVEMENTS)

### Dodano 27 wbudowanych osiągnięć w języku polskim:

#### Osiągnięcia związane z biblioteką:
- **Kolekcjoner** (10 gier) - 25 pkt 📚
- **Mega Kolekcjoner** (50 gier) - 50 pkt 🏛️
- **Archiwalny Strażnik** (100 gier) - 100 pkt 📖

#### Osiągnięcia związane z modami:
- **Mistrz Modyfikacji** (5 modów) - 20 pkt 🔧
- **Entuzjasta Modów** (20 modów) - 40 pkt 🛠️

#### Osiągnięcia związane z czasem gry:
- **Maratończyk** (100 godzin) - 40 pkt ⏱️
- **Ultra Maratończyk** (500 godzin) - 80 pkt ⏰
- **Władca Czasu** (1000 godzin) - 150 pkt ⌚

#### Osiągnięcia związane z roadmapą:
- **Planista** (3 pozycje) - 30 pkt 🗺️
- **Mistrz Planowania** (10 pozycji) - 60 pkt 🗓️

#### Osiągnięcia związane z uruchamianiem gier:
- **Gracz Debiutant** (5 różnych gier) - 15 pkt 🎮
- **Weteran Gamingu** (20 różnych gier) - 35 pkt 🎯
- **Ekspert Rozgrywki** (50 różnych gier) - 70 pkt 🏅

#### Osiągnięcia za wielokrotne uruchomienia jednej gry:
- **Oddany Gracz** (10 razy) - 20 pkt 🔄
- **Fanatyk Gry** (50 razy) - 45 pkt 🔁
- **Legenda Rozgrywki** (100 razy) - 80 pkt ♾️

#### Osiągnięcia czasowe:
- **Nocny Maraton** (gra 23:00-5:00) - 15 pkt 🦉
- **Poranny Ptaszek** (gra 5:00-8:00) - 15 pkt 🐦

#### Osiągnięcia związane z ukończeniem:
- **Perfekcjonista** (100% ukończenia) - 50 pkt 💯
- **Finalizator** (5 ukończonych gier) - 30 pkt 🏁
- **Mistrz Ukończeń** (20 ukończonych gier) - 70 pkt 🎖️

#### Inne osiągnięcia:
- **Krytyk Gier** (10 ocenionych gier) - 20 pkt ⭐
- **Artysta Screenshotów** (50 zrzutów) - 25 pkt 📸
- **Organizator** (5 grup gier) - 15 pkt 📁
- **Zaangażowany Gracz** (10 dni z rzędu) - 40 pkt 📅
- **Mistrz Sesji** (100 sesji) - 35 pkt 📊

## 2. Nowe Warunki Zakończenia (condition_type)

Dodano obsługę następujących typów warunków:

### Istniejące (ulepszone):
- `library_size` - Rozmiar biblioteki gier
- `mods_count` - Liczba zainstalowanych modów
- `roadmap_completed` - Liczba ukończonych pozycji roadmapy
- `games_launched_count` - Liczba uruchomionych różnych gier
- `play_time_hours` - Łączny czas gry w godzinach
- `manual` - Ręczne odblokowywanie

### Nowe:
- `single_game_launches` - Maksymalna liczba uruchomień pojedynczej gry
- `play_at_night` - Granie w nocy (23:00-5:00)
- `play_at_morning` - Granie rano (5:00-8:00)
- `completion_percent` - Maksymalny procent ukończenia gry
- `games_completed` - Liczba ukończonych gier (completion >= 100)
- `games_rated` - Liczba ocenionych gier
- `screenshots_count` - Łączna liczba zrzutów ekranu
- `groups_count` - Liczba utworzonych grup gier
- `consecutive_days` - Liczba kolejnych dni z graniem
- `session_count` - Łączna liczba sesji gier

## 3. Ulepszenia AchievementService

### Nowe metody:
- `_separate_builtin_from_custom()` - Rozdziela wbudowane i niestandardowe osiągnięcia
- `builtin_achievements()` - Zwraca tylko wbudowane osiągnięcia
- `custom_achievements()` - Zwraca tylko niestandardowe osiągnięcia
- `_calculate_consecutive_days()` - Oblicza serię kolejnych dni z graniem
- `check_time_based_achievements()` - Sprawdza osiągnięcia czasowe
- `export_custom_achievements(filepath)` - Eksportuje niestandardowe osiągnięcia do JSON
- `import_custom_achievements(filepath)` - Importuje niestandardowe osiągnięcia z JSON

### Ulepszona logika:
- `check_and_update_progress()` - Rozszerzona o wszystkie nowe typy warunków
- `unlock()` - Emituje dodatkowy event `achievement_unlocked` z pełnymi danymi osiągnięcia
- `_ensure_catalog()` - Automatycznie dodaje nowe wbudowane osiągnięcia do istniejącego katalogu

## 4. Rozbudowany Panel Edycji/Dodawania (AchievementsView)

### Nowe funkcje UI:
- **Przyciski Import/Export** - Umożliwiają importowanie i eksportowanie niestandardowych osiągnięć
- **Odznaki wbudowanych/niestandardowych** - Wbudowane mają ⭐, niestandardowe 🔧
- **Blokada edycji wbudowanych** - Wbudowane osiągnięcia nie mogą być edytowane ani usuwane
- **Pasek postępu** - Wyświetlany dla osiągnięć w trakcie realizacji
- **Animowane powiadomienie** - Pojawia się przy odblokowaniu osiągnięcia

### AddAchievementDialog - Ulepszona walidacja:
- Sprawdzanie pustej nazwy
- Walidacja punktów (liczba całkowita, dodatnia)
- Walidacja wartości docelowej (liczba dodatnia)
- Obsługa wszystkich 16 typów warunków
- Automatyczne przypisanie UUID jako klucza
- Oznaczenie jako `custom: True`

### EditAchievementDialog:
- Te same walidacje co w AddAchievementDialog
- Zachowuje oryginalny klucz osiągnięcia
- Działa tylko dla niestandardowych osiągnięć

### AchievementUnlockNotification:
- Wyświetlany w prawym dolnym rogu ekranu
- Animacja fade-in/fade-out
- Automatyczne zamknięcie po 4 sekundach
- Złota obwódka i akcent kolorystyczny
- Wyświetla ikonę, nazwę, punkty i opis

## 5. Organizacja Danych w DataManager

### Struktura w config.json:

```json
{
  "achievements_catalog": [
    {
      "key": "first_launch",
      "name": "Pierwsze uruchomienie",
      "description": "Uruchom aplikację po raz pierwszy.",
      "points": 10,
      "icon": "🚀",
      "condition_type": "manual",
      "target_value": 1,
      "builtin": true
    },
    {
      "key": "uuid-custom-123",
      "name": "Moje Osiągnięcie",
      "description": "...",
      "points": 15,
      "icon": "🎯",
      "condition_type": "play_time_hours",
      "target_value": 50,
      "custom": true
    }
  ],
  "user": {
    "achievements": {
      "first_launch": {
        "unlocked": true,
        "timestamp": "2024-01-01T12:00:00",
        "current_progress": 1
      },
      "uuid-custom-123": {
        "unlocked": false,
        "timestamp": null,
        "current_progress": 25
      }
    }
  }
}
```

### Rozdzielenie danych:
- **Wbudowane osiągnięcia**: `builtin: true` - nieusuwalne, nieedytowalne
- **Niestandardowe osiągnięcia**: `custom: true` - edytowalne, usuwalne
- **Postęp użytkownika**: Przechowywany oddzielnie w `user.achievements`
- **Klucze niestandardowe**: Używają UUID zamiast prostych nazw

## 6. Integracja z Innymi Usługami

### Event Bus - Nowe subskrypcje:
- `game_added` → `check_and_update_progress()`
- `game_launched` → `check_time_based_achievements()` + `check_and_update_progress()`
- `roadmap_completed` → `check_and_update_progress()`
- `mod_added` → `check_and_update_progress()`
- `game_session_end` → `check_and_update_progress()`
- `screenshot_added` → `check_and_update_progress()`

### Nowe eventy emitowane:
- `achievement_unlocked` - Z pełnymi danymi osiągnięcia (dla notyfikacji)
- `achievements_changed` - Po każdej zmianie w katalogu/postępie

## 7. Zgodność Językowa

Wszystkie teksty w języku polskim:
- Nazwy i opisy osiągnięć
- Etykiety UI (przyciski, nagłówki)
- Komunikaty walidacji
- Nazwy warunków zakończenia
- Powiadomienia o sukcesie/błędzie

## Użycie

### Dodawanie własnego osiągnięcia:
1. Kliknij "➕ Dodaj" w widoku osiągnięć
2. Wypełnij formularz (nazwa, opis, ikona, punkty, warunek, wartość)
3. Kliknij "💾 Dodaj"

### Edycja niestandardowego osiągnięcia:
1. Kliknij "✏️ Edytuj" na karcie osiągnięcia
2. Zmodyfikuj pola
3. Kliknij "💾 Zapisz"

### Eksport osiągnięć:
1. Kliknij "📤 Export"
2. Wybierz lokalizację i nazwę pliku
3. Tylko niestandardowe osiągnięcia zostaną wyeksportowane

### Import osiągnięć:
1. Kliknij "📥 Import"
2. Wybierz plik JSON z osiągnięciami
3. Duplikaty nie zostaną zaimportowane

## Testowanie

System automatycznie:
- Sprawdza postęp po każdej akcji użytkownika
- Odblokowuje osiągnięcia gdy cel zostanie osiągnięty
- Wyświetla animowane powiadomienie
- Aktualizuje postęp na kartach osiągnięć
- Zapisuje dane do config.json

## Zmiany w plikach

### app/services/achievement_service.py
- Rozszerzono DEFAULT_ACHIEVEMENTS do 27 pozycji
- Dodano 10 nowych condition_type
- Dodano metody import/export
- Dodano rozbudowaną logikę check_and_update_progress

### app/plugins/achievements.py
- Dodano AchievementUnlockNotification
- Dodano przyciski Import/Export
- Dodano walidację w dialogach
- Dodano odznaki builtin/custom
- Ulepszono wizualizację postępu

## Kompatybilność wsteczna

System jest w pełni kompatybilny wstecz:
- Stare osiągnięcia są automatycznie oznaczane jako builtin
- Brak danych to defaults (unlocked: false, progress: 0)
- Nowe wbudowane osiągnięcia są automatycznie dodawane
