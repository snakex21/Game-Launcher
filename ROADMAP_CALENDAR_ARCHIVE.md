# Przebudowa Roadmapy z Widokiem Kalendarza i Archiwum

## Zrealizowane Funkcjonalności

### 1. Trzy Widoki Roadmapy

Roadmapa oferuje teraz trzy główne widoki dostępne poprzez przyciski w nagłówku:

#### 📋 Lista
- Wyświetla aktywne gry z roadmapy w postaci kart
- Pokazuje priorytet każdej gry (🔴 Wysoki, 🟡 Średni, ⚪ Niski)
- Wyświetla daty rozpoczęcia i cel z licznikiem dni pozostałych
- Wizualne ostrzeżenia dla przeterminowanych celów
- Możliwość edycji, oznaczenia jako ukończone lub usunięcia

#### 📅 Kalendarz
- Miesięczny widok kalendarza z polskimi nazwami dni tygodnia
- Nawigacja między miesiącami (◀ / ▶)
- Wyświetlanie gier w zakresie dat rozpoczęcia i zakończenia
- Kolorowe oznaczenia priorytetów na poszczególnych dniach
- Legenda priorytetów
- Inteligentne wyświetlanie: maksymalnie 3 gry na dzień + licznik dodatkowych

#### 📦 Archiwum
- Wyświetla ukończone gry z roadmapy
- Kolorowe karty według miesiąca ukończenia (12 kolorów miesięcy)
- Filtrowanie: Wszystkie / Ukończone / W archiwum
- Legenda kolorów miesięcy (Sty, Lut, Mar, etc.)
- Możliwość przywrócenia gry do aktywnych lub usunięcia

### 2. Kolorystyka i Oznaczenia

#### Priorytety:
- **Wysoki (🔴)**: #e74c3c (czerwony)
- **Średni (🟡)**: #f39c12 (pomarańczowy)
- **Niski (⚪)**: #95a5a6 (szary)

#### Kolory Miesięcy (Archiwum):
- Styczeń: #FFB3BA (różowy)
- Luty: #FFDFBA (brzoskwiniowy)
- Marzec: #FFFFBA (żółty)
- Kwiecień: #BAFFC9 (miętowy)
- Maj: #BAE1FF (błękitny)
- Czerwiec: #FFB3E6 (lawendowy)
- Lipiec: #C9C9FF (fioletowy)
- Sierpień: #FFD1DC (łososiowy)
- Wrzesień: #E0BBE4 (liliowy)
- Październik: #FFDAB9 (brzoskwiniowy)
- Listopad: #B5EAD7 (turkusowy)
- Grudzień: #C7CEEA (perłowy)

### 3. Rozbudowany Model Danych

Nowa struktura wpisu roadmapy:
```json
{
  "id": "uuid",
  "game_name": "Nazwa gry",
  "game_id": "id_gry_z_biblioteki",
  "priority": "high|medium|low",
  "color": "#e74c3c",
  "start_date": "YYYY-MM-DD",
  "target_date": "YYYY-MM-DD",
  "notes": "Notatki użytkownika",
  "completed": false,
  "completed_date": "YYYY-MM-DD",
  "status": "Planowana|Ukończona",
  "added_date": "YYYY-MM-DD HH:MM:SS"
}
```

### 4. Automatyczna Migracja Danych

Plugin automatycznie migruje istniejące wpisy roadmapy dodając:
- Pole `color` na podstawie priorytetu
- Pole `game_id` (null dla starych wpisów)
- Pole `status` na podstawie stanu `completed`

### 5. Edycja Wpisów

- Możliwość edycji każdego aktywnego wpisu roadmapy
- Formularz wypełniany aktualnymi danymi
- Walidacja formatu daty (YYYY-MM-DD)
- Wybór gry z biblioteki
- Ustawienie priorytetu
- Pole na notatki

### 6. Powiadomienia

#### Przy Ukończeniu Gry:
- Wyświetlane powiadomienie: "🎉 Gratulacje! Ukończyłeś '{nazwa_gry}' z roadmapy!"
- Czas wyświetlania: 4 sekundy

#### Po Zakończeniu Sesji Gry:
- Jeśli gra jest w roadmapie i osiągnięto datę docelową
- Powiadomienie: "🎯 Cel roadmapy osiągnięty! '{nazwa_gry}' - Czy czas oznaczyć jako ukończone?"
- Czas wyświetlania: 5 sekund

### 7. Integracja z Systemem Osiągnięć

Emitowane zdarzenia:
- `roadmap_completed` - po oznaczeniu gry jako ukończonej (z game_name)
- `roadmap_updated` - po każdej zmianie w roadmapie

System osiągnięć automatycznie śledzi:
- **Planista** 🗺️: Ukończ 3 pozycje w roadmapie (30 pkt)
- **Mistrz Planowania** 🗓️: Ukończ 10 pozycji w roadmapie (60 pkt)

### 8. Interfejs Użytkownika

#### Responsywność:
- Widoki dostosowują się do rozmiaru okna
- Karty wykorzystują całą dostępną szerokość
- Kalendarz równomiernie dzieli przestrzeń między dni

#### Zgodność z Motywem:
- Wszystkie kolory używają palety z ThemeService
- Ciemne/jasne motywy automatycznie obsługiwane
- Spójne zaokrąglenia rogów (corner_radius)
- Jednolita typografia (CTkFont)

#### Język Polski:
- Wszystkie etykiety w języku polskim
- Polskie nazwy dni tygodnia (Pn, Wt, Śr, Cz, Pt, Sb, Nd)
- Polskie nazwy miesięcy
- Polskie komunikaty

### 9. Funkcje Dodatkowe

#### Licznik Dni:
- Pokazuje ile dni pozostało do celu
- Ostrzeżenia kolorystyczne:
  - **Zielony**: >7 dni
  - **Pomarańczowy**: ≤7 dni lub dziś
  - **Czerwony**: termin minął

#### Szybkie Przypisywanie z Biblioteki:
- Lista rozwijana z wszystkimi grami z biblioteki
- Automatyczne pobieranie game_id
- Możliwość wyboru tylko istniejących gier

#### Zarządzanie:
- Dodawanie nowych wpisów
- Edycja istniejących
- Oznaczanie jako ukończone
- Przywracanie z archiwum
- Usuwanie

## Testowanie

### Scenariusze Testowe

#### 1. Dodawanie Gry do Roadmapy
1. Kliknij "➕ Dodaj do Roadmapy"
2. Wybierz grę z listy
3. Ustaw priorytet (domyślnie Średni)
4. Ustaw daty rozpoczęcia i zakończenia
5. Dodaj opcjonalne notatki
6. Kliknij "💾 Dodaj"
7. **Oczekiwany rezultat**: Gra pojawia się w widoku listy

#### 2. Edycja Wpisu
1. W widoku listy kliknij "✏️ Edytuj" na karcie gry
2. Zmień dane (np. datę docelową)
3. Kliknij "💾 Zapisz"
4. **Oczekiwany rezultat**: Zmiany są widoczne natychmiast

#### 3. Wyświetlanie Kalendarza
1. Kliknij "📅 Kalendarz"
2. Sprawdź czy gry są widoczne w odpowiednich dniach
3. Użyj ◀ / ▶ do nawigacji między miesiącami
4. **Oczekiwany rezultat**: Gry wyświetlają się w zakresie dat start-target

#### 4. Ukończenie Gry
1. W widoku listy kliknij "✅ Ukończ" na karcie gry
2. **Oczekiwany rezultat**: 
   - Pojawia się powiadomienie
   - Gra znika z listy aktywnych
   - Gra pojawia się w archiwum z kolorem miesiąca

#### 5. Przywracanie z Archiwum
1. Przejdź do "📦 Archiwum"
2. Kliknij "↺ Przywróć" na karcie gry
3. **Oczekiwany rezultat**: 
   - Gra wraca do widoku listy
   - Usuwany jest completed_date
   - Status zmienia się na "Planowana"

#### 6. Filtrowanie Archiwum
1. Przejdź do "📦 Archiwum"
2. Użyj przycisków filtra (Wszystkie / Ukończone)
3. **Oczekiwany rezultat**: Widoczne są tylko odpowiednie gry

#### 7. Powiadomienia
1. Ukończ grę i sprawdź czy pojawia się powiadomienie
2. Zagraj w grę z roadmapy po terminie docelowym
3. **Oczekiwany rezultat**: Odpowiednie powiadomienia są wyświetlane

#### 8. Osiągnięcia
1. Ukończ 3 gry z roadmapy
2. Sprawdź w osiągnięciach czy "Planista" został odblokowany
3. **Oczekiwany rezultat**: Osiągnięcie odblokowane + powiadomienie

#### 9. Responsywność
1. Zmień rozmiar okna aplikacji
2. Sprawdź wszystkie widoki (lista, kalendarz, archiwum)
3. **Oczekiwany rezultat**: UI dostosowuje się płynnie

#### 10. Migracja Danych
1. Jeśli masz stare wpisy roadmapy, uruchom aplikację
2. Sprawdź czy wpisy mają nowe pola (color, game_id, status)
3. **Oczekiwany rezultat**: Stare dane migują automatycznie

## Architektura

### Pliki Zmodyfikowane/Utworzone:
- `app/plugins/roadmap.py` - Kompletnie przepisany moduł

### Klasy:
- `RoadmapPlugin` - Plugin z migracją danych
- `RoadmapView` - Główny widok z trzema zakładkami
- `AddRoadmapDialog` - Dialog dodawania/edycji wpisu

### Zależności:
- `calendar` (standardowa biblioteka Python) - generowanie kalendarzy
- `datetime`, `date`, `timedelta` - obsługa dat
- `uuid` - generowanie unikalnych ID
- `customtkinter` - komponenty UI

### Integracje:
- `DataManager` - zarządzanie danymi roadmapy
- `EventBus` - emitowanie zdarzeń
- `ThemeService` - motywy kolorystyczne
- `NotificationService` - powiadomienia
- `AchievementService` - automatyczne odblokowywanie osiągnięć
- `GameService` - lista gier do wyboru

## Wydajność

- Cache dla ostatniego sprawdzenia osiągnięć (2 sekundy)
- Leniwe ładowanie widoków (tworzenie przy przełączaniu)
- Minimalne przeładowywanie danych
- Efektywne filtrowanie list w pamięci

## Zgodność

- Kompatybilne ze starymi wpisami roadmapy
- Automatyczna migracja przy starcie
- Zachowanie wstecznej kompatybilności struktury danych
- Bezpieczne dodawanie nowych pól (optional)

## Przyszłe Ulepszenia

Potencjalne rozszerzenia:
1. Import/Export roadmapy do pliku
2. Statystyki ukończeń (wykres słupkowy miesięczny)
3. Przypomnienia przed terminem (np. 3 dni przed)
4. Grupowanie gier według serii/franczyzy
5. Synchronizacja z zewnętrznymi trackerami (HowLongToBeat, Backloggd)
6. Śledzenie czasu spędzonego w roadmapie vs realny czas
7. Cele tygodniowe/miesięczne
8. Eksport do kalendarza (iCal)
9. Udostępnianie roadmapy innym użytkownikom
10. Drag & drop na kalendarzu do zmiany dat
