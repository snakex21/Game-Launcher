# Rozszerzenie modułu statystyk - Analizy wielopoziomowe

## Przegląd zmian

Moduł statystyk (`app/plugins/statistics.py`) został znacznie rozbudowany o zaawansowane analizy i wizualizacje danych sesji gier.

## Nowe funkcje

### 1. Widok szczegółowy gry

#### Konwersje czasu
Każda gra oraz widok ogólny wyświetla łączny czas gry przekonwertowany na:
- ⏱️ Minuty (wartość bazowa)
- 🕐 Godziny i minuty (Xh Ym)
- 📅 Dni (z dokładnością do 2 miejsc po przecinku)
- 📆 Miesiące (zakładając 30 dni/miesiąc)
- 📊 Lata (zakładając 365 dni/rok)

#### Wykres progresu ukończenia
Dla każdej gry z dostępnymi sesjami wyświetlany jest wykres liniowy pokazujący:
- Skumulowany czas gry w godzinach na osi Y
- Daty sesji na osi X
- Wypełnienie pod wykresem dla lepszej czytelności
- Linia przerywana oznaczająca obecny poziom ukończenia (jeśli > 0%)
- Automatyczne formatowanie dat

### 2. Kalendarz aktywności (Heatmapa)

#### Widok ogólny
W sekcji "Wszystkie gry" wyświetlany jest kalendarz aktywności przedstawiający:
- **Okres**: Ostatnie 90 dni
- **Format**: Heatmapa w układzie dni tygodnia (wiersze) × tygodnie (kolumny)
- **Kolory**: Gradient YlGnBu (żółty-zielony-niebieski) wskazujący intensywność gry
- **Legendy**: 
  - Oś Y: Dni tygodnia (Pn, Wt, Śr, Cz, Pt, So, Nd)
  - Oś X: Numery tygodni
  - Colorbar: Minuty gry

#### Dane źródłowe
Heatmapa agreguje wszystkie sesje ze wszystkich gier:
- Sumuje czas gry per dzień
- Śledzi, które gry były grane danego dnia
- Obsługuje puste dni (wartość 0)

### 3. Statystyki zaawansowane

Nowa sekcja "📈 Statystyki zaawansowane" w widoku ogólnym zawiera:

#### 📊 Średnia dzienna (30 dni)
- Oblicza średni dzienny czas gry z ostatnich 30 dni
- Format: Xh Ym
- Przydatne do śledzenia regularności grania

#### 🎯 Najczęściej grany gatunek
- Agreguje łączny czas gry per gatunek
- Wyświetla gatunek z najdłuższym czasem i liczbę godzin
- Format: "Nazwa_gatunku (Xh)"

#### ⏰ Najdłuższa sesja
- Znajduje pojedynczą sesję o najdłuższym czasie trwania
- Wyświetla nazwę gry i czas trwania
- Format: "Nazwa_gry: Xh Ym"

### 4. Wsparcie dla motywów

Wszystkie wykresy matplotlib są zintegrowane z systemem motywów:
- **Tło wykresów**: `theme.surface`
- **Tekst i etykiety**: `theme.text`
- **Linie i znaczniki**: `theme.accent`
- **Siatka i osie**: `theme.text_muted`
- **Ramki**: `theme.text_muted`

Wykresy automatycznie odświeżają się przy zmianie motywu.

### 5. Cache i przetwarzanie asynchroniczne

#### System cache'owania
- Wygenerowane wykresy są przechowywane w `self.cached_charts`
- Klucze cache zawierają istotne parametry (np. ID gry, zakres dat)
- Cache jest czyszczony przy zmianie danych lub motywu

#### Generowanie w tle
Wszystkie wykresy są generowane w osobnych wątkach:
```python
def generate_chart():
    fig = self._create_completion_chart(game)
    canvas = FigureCanvasTkAgg(fig, parent)
    self.cached_charts[chart_key] = canvas
    self.after(0, lambda: self._update_chart_ui(loading_label, canvas))

thread = threading.Thread(target=generate_chart, daemon=True)
thread.start()
```

#### Wskaźniki ładowania
Podczas generowania wykresów wyświetlany jest komunikat:
- "⏳ Generowanie wykresu..."
- "⏳ Generowanie kalendarza..."

W przypadku błędu: "❌ Błąd: [opis]"

## Struktura danych sesji

Moduł opiera się na strukturze sesji w formacie:
```python
{
  "started_at": "2024-01-01T10:00:00",  # ISO 8601 datetime
  "duration": 60  # minuty
}
```

Sesje są przechowywane w liście `game.sessions` dla każdej gry.

## Wykorzystywane biblioteki

- **matplotlib**: Generowanie wykresów
  - `matplotlib.figure.Figure`: Tworzenie figur
  - `matplotlib.backends.backend_tkagg.FigureCanvasTkAgg`: Integracja z Tkinter
  - `matplotlib.dates`: Formatowanie osi dat
- **numpy**: Operacje na tablicach (heatmapa)
- **threading**: Asynchroniczne generowanie wykresów
- **collections.Counter**: Agregacja gatunków
- **datetime**: Parsowanie i manipulacja datami

## Kompatybilność

### Wieloplatformowość
- Matplotlib jest w pełni wieloplatformowe (Windows, Linux, macOS)
- Używany backend `TkAgg` działa na wszystkich platformach
- Brak wywołań specyficznych dla systemu

### Obsługa dużych zbiorów danych
- Asynchroniczne generowanie wykresów zapobiega blokowaniu UI
- Cache redukuje ponowne obliczenia
- Heatmapa ograniczona do 90 dni (optymalizacja pamięci)
- Top 10 zamiast pełnej listy gier

## Etykiety i język

Wszystkie etykiety są w języku polskim zgodnie z konwencją projektu:
- Nagłówki sekcji: "📊 Statystyki zaawansowane"
- Metryki: "Średnia dzienna (30 dni)"
- Wykresy: "Progres ukończenia w czasie"
- Dni tygodnia: Pn, Wt, Śr, Cz, Pt, So, Nd

## Rozszerzalność

Moduł został zaprojektowany z myślą o łatwym dodawaniu nowych analiz:

### Dodawanie nowej metryki
1. Rozszerz `_calculate_advanced_stats()` o nowe obliczenie
2. Dodaj wiersz w sekcji zaawansowanej w `_show_all_games_stats()`
3. Użyj spójnego formatowania z istniejącymi metrykami

### Dodawanie nowego wykresu
1. Utwórz metodę `_create_XXX_chart()`
2. Zastosuj kolory motywu (`self.theme`)
3. Użyj asynchronicznego wzorca generowania
4. Dodaj klucz cache dla wykresu

### Przykład nowej metryki
```python
# W _calculate_advanced_stats():
total_games_started = len([g for g in games if g.play_time > 0])

# W _show_all_games_stats():
stat_row = ctk.CTkFrame(advanced_section, ...)
ctk.CTkLabel(stat_row, text="🎮 Rozpoczęte gry", ...)
ctk.CTkLabel(stat_row, text=f"{total_games_started}", ...)
```

## Testowanie

### Przypadki testowe
1. **Brak danych**: Moduł wyświetla komunikaty "Brak danych o sesjach"
2. **Pojedyncza sesja**: Wykresy działają z minimalną ilością danych
3. **Duża liczba sesji**: Asynchroniczne generowanie zapobiega zawieszeniu
4. **Zmiana motywu**: Wykresy odświeżają się z nowymi kolorami
5. **Brak gatunków**: Sekcja "Najczęściej grany gatunek" jest ukryta

### Uruchomienie
```bash
python main.py
# Przejdź do sekcji "Statystyki" w bocznym menu
```

## Znane ograniczenia

1. **Heatmapa**: Ograniczona do 90 dni (możliwa rozbudowa o selektor okresu)
2. **Historia sesji**: Wyświetlane tylko ostatnie 10 sesji per gra
3. **Format dat**: Zakłada ISO 8601, starsze formaty mogą nie działać
4. **Obliczenia**: Miesiąc = 30 dni, rok = 365 dni (uproszczenie)

## Przyszłe ulepszenia

Potencjalne rozszerzenia:
- [ ] Interaktywna heatmapa z tooltipami (gry grane danego dnia)
- [ ] Eksport statystyk do CSV/JSON
- [ ] Porównanie wielu gier na jednym wykresie
- [ ] Statystyki per gatunek (wykresy kołowe)
- [ ] Prognozy czasu do ukończenia gry
- [ ] Filtry czasowe dla wszystkich widoków
- [ ] Statystyki per miesiąc/rok
- [ ] Rankingi osiągnięć gracza

## Migracja z stary_launcher.py

Funkcjonalności obecne w `stary_launcher.py`, które zostały przeniesione:
- ✅ Konwersje czasu (minuty → różne jednostki)
- ✅ Top 10 najdłużej granych
- ✅ Historia sesji
- ➕ **NOWE**: Kalendarz aktywności
- ➕ **NOWE**: Średnia dzienna
- ➕ **NOWE**: Najczęściej grany gatunek
- ➕ **NOWE**: Najdłuższa sesja
- ➕ **NOWE**: Wykres progresu ukończenia
- ➕ **NOWE**: Asynchroniczne generowanie

## Podsumowanie

Rozbudowa modułu statystyk wprowadza kompleksowy system analizy danych sesji gier, oferując:
- **Wielopoziomowe widoki**: Od ogólnych agregacji po szczegóły pojedynczych gier
- **Wizualizacje**: Wykresy liniowe, heatmapy, agregaty
- **Wydajność**: Cache i asynchroniczne generowanie
- **UX**: Spójność z motywem, polskie etykiety, responsywność
- **Rozszerzalność**: Łatwe dodawanie nowych metryk i wykresów
