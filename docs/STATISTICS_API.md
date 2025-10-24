# API Modułu Statystyk

## Struktura klas

### `StatisticsPlugin(BasePlugin)`

Plugin rejestrujący moduł statystyk w aplikacji.

```python
class StatisticsPlugin(BasePlugin):
    name = "Statistics"
    
    def register(self, context: AppContext) -> None:
        # Rejestracja pluginu w kontekście aplikacji
```

### `StatisticsView(ctk.CTkFrame)`

Główny widok statystyk z nawigacją i wizualizacjami.

#### Inicjalizacja

```python
def __init__(self, parent, context: AppContext) -> None:
    # parent: Ramka rodzica (main_content)
    # context: Kontekst aplikacji z serwisami i danymi
```

#### Atrybuty publiczne

- `context: AppContext` - Kontekst aplikacji
- `theme: Theme` - Aktywny motyw
- `selected_game_id: str | None` - ID aktualnie wybranej gry
- `cached_charts: dict` - Cache wygenerowanych wykresów
- `processing: bool` - Flaga przetwarzania

#### Atrybuty prywatne

- `games_list: CTkScrollableFrame` - Lista gier do wyboru
- `stats_container: CTkScrollableFrame` - Kontener na statystyki

## Metody publiczne

### Zarządzanie widokiem

#### `destroy() -> None`

Czyści subskrypcje eventów i niszczy widok.

```python
def destroy(self) -> None:
    self.context.event_bus.unsubscribe("games_changed", self._on_data_changed)
    self.context.event_bus.unsubscribe("theme_changed", self._on_theme_changed)
    super().destroy()
```

## Metody prywatne

### Obsługa danych

#### `_load_data() -> None`

Ładuje listę gier i odświeża widok.

- Sortuje gry według czasu gry (malejąco)
- Tworzy przyciski dla każdej gry
- Dodaje przycisk "Wszystkie gry"

#### `_show_game_stats(game_id: str | None) -> None`

Wyświetla statystyki dla wybranej gry lub wszystkich gier.

**Parametry:**
- `game_id`: ID gry lub `None` dla widoku ogólnego

#### `_on_data_changed(**kwargs) -> None`

Callback dla eventu `games_changed`.

- Czyści cache wykresów
- Przeładowuje dane

#### `_on_theme_changed(**kwargs) -> None`

Callback dla eventu `theme_changed`.

- Aktualizuje motyw
- Czyści cache wykresów (wymaga regeneracji z nowymi kolorami)
- Przeładowuje widok

### Formatowanie i obliczenia

#### `_format_time_conversions(total_minutes: int) -> list[tuple[str, str]]`

Konwertuje minuty na różne jednostki czasu.

**Parametry:**
- `total_minutes`: Łączny czas w minutach

**Zwraca:**
```python
[
    ("⏱️ Łączny czas", "120 minut"),
    ("🕐 W godzinach", "2h 0m"),
    ("📅 W dniach", "0.08 dni"),
    ("📆 W miesiącach", "0.00 miesięcy"),
    ("📊 W latach", "0.00 lat"),
]
```

#### `_calculate_advanced_stats(games: list) -> dict[str, Any]`

Oblicza zaawansowane statystyki dla wszystkich gier.

**Parametry:**
- `games`: Lista obiektów `Game`

**Zwraca:**
```python
{
    'longest_session': {
        'game': Game,
        'duration': 180,  # minuty
        'started_at': '2024-01-01T10:00:00'
    },
    'daily_average': 45.5,  # minuty/dzień
    'most_played_genre': ('RPG', 1200),  # (gatunek, minuty)
    'genre_times': Counter({'RPG': 1200, 'Action': 800}),
}
```

**Logika:**
- **longest_session**: Znajduje sesję o największej wartości `duration`
- **daily_average**: Sumuje sesje z ostatnich 30 dni i dzieli przez 30
- **most_played_genre**: Agreguje czas gry per gatunek, wybiera najpopularniejszy
- **genre_times**: Counter wszystkich czasów per gatunek

### Widoki

#### `_show_all_games_stats() -> None`

Wyświetla statystyki dla wszystkich gier.

**Komponenty:**
1. Tytuł sekcji
2. Konwersje czasu (minut → różne jednostki)
3. Liczba gier
4. Statystyki zaawansowane:
   - Średnia dzienna (30 dni)
   - Najczęściej grany gatunek
   - Najdłuższa sesja
5. Top 10 najdłużej granych gier
6. Kalendarz aktywności (heatmapa)

#### `_show_single_game_stats(game_id: str) -> None`

Wyświetla statystyki dla pojedynczej gry.

**Parametry:**
- `game_id`: ID gry

**Komponenty:**
1. Tytuł z nazwą gry
2. Konwersje czasu
3. Ukończenie (procent)
4. Ocena (rating)
5. Gatunki
6. Wykres progresu ukończenia (jeśli są sesje)
7. Historia sesji (ostatnie 10)

### Kalendarz aktywności

#### `_show_activity_calendar(games: list) -> None`

Wyświetla kalendarz aktywności w formie heatmapy.

**Parametry:**
- `games`: Lista gier

**Proces:**
1. Zbiera wszystkie sesje
2. Agreguje czas per dzień
3. Generuje heatmapę dla ostatnich 90 dni
4. Wyświetla wykres lub komunikat "Brak danych"

#### `_create_activity_heatmap(daily_activity: dict, games_per_day: dict, start_date, end_date) -> Figure`

Tworzy wykres heatmapy aktywności.

**Parametry:**
- `daily_activity`: `{date: minutes}` - czas gry per dzień
- `games_per_day`: `{date: set(game_names)}` - gry grane danego dnia
- `start_date`: Data początkowa
- `end_date`: Data końcowa

**Zwraca:**
- `matplotlib.figure.Figure` - Gotowy wykres

**Implementacja:**
```python
# Przygotuj macierz 7 (dni tygodnia) x N (tygodnie)
heatmap_data = np.zeros((7, weeks))

# Wypełnij danymi
for i, value in enumerate(values):
    week = i // 7
    day = i % 7
    heatmap_data[day, week] = value

# Rysuj
ax.imshow(heatmap_data, cmap='YlGnBu', ...)
```

**Kolory motywu:**
- Tło: `theme.surface`
- Tekst: `theme.text`
- Osie: `theme.text_muted`

#### `_update_calendar_ui(loading_label, canvas) -> None`

Aktualizuje UI po wygenerowaniu kalendarza.

**Parametry:**
- `loading_label`: Etykieta ładowania do usunięcia
- `canvas`: Canvas z wykresem do wyświetlenia

### Wykres progresu

#### `_show_completion_progress(game) -> None`

Wyświetla sekcję z wykresem progresu ukończenia.

**Parametry:**
- `game`: Obiekt `Game`

**Proces:**
1. Tworzy sekcję w kontenerze statystyk
2. Sprawdza cache
3. Jeśli brak w cache, generuje wykres w tle
4. Wyświetla "⏳ Generowanie wykresu..." podczas przetwarzania

#### `_create_completion_chart(game) -> Figure`

Tworzy wykres liniowy progresu.

**Parametry:**
- `game`: Obiekt `Game`

**Zwraca:**
- `matplotlib.figure.Figure` - Wykres lub komunikat o braku danych

**Implementacja:**
```python
# Sortuj sesje chronologicznie
sessions_data = []
cumulative_time = 0

for session in sorted(game.sessions, key=lambda x: x['started_at']):
    cumulative_time += session['duration']
    sessions_data.append((started_at, cumulative_time))

# Rysuj wykres
dates = [s[0] for s in sessions_data]
times_hours = [s[1] / 60 for s in sessions_data]  # Konwersja na godziny

ax.plot(dates, times_hours, color=theme.accent, linewidth=2, marker='o')
ax.fill_between(dates, times_hours, alpha=0.3, color=theme.accent)

# Dodaj linię ukończenia
if game.completion > 0:
    ax.axhline(y=game.play_time/60, linestyle='--', ...)
```

#### `_update_chart_ui(loading_label, canvas) -> None`

Aktualizuje UI po wygenerowaniu wykresu progresu.

**Parametry:**
- `loading_label`: Etykieta ładowania do usunięcia
- `canvas`: Canvas z wykresem do wyświetlenia

## System cache'owania

### Struktura cache

```python
self.cached_charts = {
    'progress_{game_id}': FigureCanvasTkAgg,
    'calendar_{start_date}_{end_date}': FigureCanvasTkAgg,
}
```

### Zarządzanie cache

**Czyszczenie:**
- Przy zmianie danych (`games_changed`)
- Przy zmianie motywu (`theme_changed`)

**Klucze:**
- Wykres progresu: `f"progress_{game.id}"`
- Kalendarz: `f"calendar_{start_date}_{end_date}"`

## Asynchroniczne generowanie wykresów

### Wzorzec

```python
def generate_chart():
    try:
        fig = self._create_XXX_chart(...)
        canvas = FigureCanvasTkAgg(fig, parent)
        self.cached_charts[chart_key] = canvas
        self.after(0, lambda: self._update_XXX_ui(loading_label, canvas))
    except Exception as e:
        logger.exception("Błąd...")
        self.after(0, lambda: loading_label.configure(text=f"❌ Błąd: {e}"))

thread = threading.Thread(target=generate_chart, daemon=True)
thread.start()
```

### Dlaczego `self.after(0, ...)`?

Matplotlib i Tkinter canvas muszą być aktualizowane w głównym wątku GUI. `self.after(0, callback)` planuje wykonanie callback w głównym wątku przy najbliższej okazji.

## Integracja z motywami

### Kolory dostępne w `theme`

```python
theme.background      # Tło aplikacji
theme.surface         # Tło paneli
theme.surface_alt     # Alternatywne tło (hover)
theme.base_color      # Kolor bazowy przycisków
theme.accent          # Kolor akcentu (highlight)
theme.text            # Główny kolor tekstu
theme.text_muted      # Wyciszony tekst
```

### Zastosowanie w wykresach

```python
fig.patch.set_facecolor(theme.surface)        # Tło wykresu
ax.set_facecolor(theme.surface)               # Tło obszaru rysowania
ax.tick_params(colors=theme.text)             # Kolory ticków
ax.set_xlabel('Label', color=theme.text)      # Etykiety osi
ax.grid(True, color=theme.text_muted)         # Siatka
ax.plot(x, y, color=theme.accent)             # Linie wykresu

for spine in ax.spines.values():
    spine.set_color(theme.text_muted)         # Ramki wykresu
```

## Eventy

### Subskrybowane eventy

- `games_changed`: Zmiana w danych gier (dodanie, edycja, usunięcie)
- `theme_changed`: Zmiana motywu aplikacji

### Emisja eventów

Moduł nie emituje żadnych eventów samodzielnie.

## Format danych sesji

```python
{
    "started_at": "2024-01-15T14:30:00",  # ISO 8601 datetime string
    "duration": 120                        # Czas trwania w minutach
}
```

### Wymagania

- `started_at` musi być parsowalne przez `datetime.fromisoformat()`
- `duration` musi być liczbą całkowitą >= 0
- Brak sesji jest obsługiwany (wyświetlany komunikat)

## Przykłady użycia

### Dodanie nowej metryki

```python
def _calculate_advanced_stats(self, games: list) -> dict[str, Any]:
    # ... istniejący kod ...
    
    # Nowa metryka: liczba gier ukończonych
    completed_games = len([g for g in games if g.completion == 100])
    
    return {
        # ... istniejące metryki ...
        'completed_games': completed_games,
    }

# W _show_all_games_stats():
completed = advanced_stats.get('completed_games', 0)
stat_row = ctk.CTkFrame(advanced_section, fg_color=self.theme.surface, corner_radius=8)
stat_row.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(stat_row, text="✅ Ukończone gry", ...).pack(side="left", ...)
ctk.CTkLabel(stat_row, text=f"{completed}", ...).pack(side="right", ...)
```

### Dodanie nowego wykresu

```python
def _show_rating_distribution(self) -> None:
    """Wyświetla rozkład ocen gier."""
    chart_section = ctk.CTkFrame(self.stats_container, ...)
    chart_section.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(chart_section, text="⭐ Rozkład ocen", ...).pack(...)
    
    chart_key = "rating_distribution"
    if chart_key in self.cached_charts:
        canvas = self.cached_charts[chart_key]
        canvas.get_tk_widget().pack(...)
    else:
        loading_label = ctk.CTkLabel(chart_section, text="⏳ Generowanie...", ...)
        loading_label.pack(...)
        
        def generate():
            fig = self._create_rating_chart()
            canvas = FigureCanvasTkAgg(fig, chart_section)
            self.cached_charts[chart_key] = canvas
            self.after(0, lambda: self._update_chart_ui(loading_label, canvas))
        
        threading.Thread(target=generate, daemon=True).start()

def _create_rating_chart(self):
    """Tworzy wykres słupkowy rozkładu ocen."""
    fig = Figure(figsize=(8, 4), dpi=100)
    fig.patch.set_facecolor(self.theme.surface)
    ax = fig.add_subplot(111)
    
    games = self.context.games.games
    ratings = [g.rating for g in games if g.rating > 0]
    
    if not ratings:
        ax.text(0.5, 0.5, 'Brak ocenionych gier', 
               ha='center', va='center', color=self.theme.text_muted,
               transform=ax.transAxes)
    else:
        bins = range(0, 11)  # 0-10
        ax.hist(ratings, bins=bins, color=self.theme.accent, edgecolor=self.theme.text)
        ax.set_xlabel('Ocena', color=self.theme.text)
        ax.set_ylabel('Liczba gier', color=self.theme.text)
        ax.set_facecolor(self.theme.surface)
        ax.tick_params(colors=self.theme.text)
        
        for spine in ax.spines.values():
            spine.set_color(self.theme.text_muted)
    
    fig.tight_layout()
    return fig
```

## Testowanie

### Unit testy (zalecane)

```python
import unittest
from datetime import datetime, timedelta
from app.plugins.statistics import StatisticsView

class TestStatisticsView(unittest.TestCase):
    def test_format_time_conversions(self):
        view = StatisticsView(None, mock_context)
        result = view._format_time_conversions(120)
        self.assertEqual(result[0], ("⏱️ Łączny czas", "120 minut"))
        self.assertEqual(result[1], ("🕐 W godzinach", "2h 0m"))
    
    def test_calculate_advanced_stats_empty(self):
        view = StatisticsView(None, mock_context)
        result = view._calculate_advanced_stats([])
        self.assertEqual(result, {})
    
    # ... więcej testów
```

### Testy manualne

1. **Widok ogólny:**
   - Sprawdź konwersje czasu
   - Zweryfikuj Top 10
   - Sprawdź statystyki zaawansowane
   - Obejrzyj kalendarz aktywności

2. **Widok pojedynczej gry:**
   - Sprawdź konwersje czasu
   - Zweryfikuj wykres progresu
   - Sprawdź historię sesji

3. **Zmiana motywu:**
   - Przełącz motyw w ustawieniach
   - Sprawdź czy wykresy używają nowych kolorów

4. **Wydajność:**
   - Dodaj wiele gier z wieloma sesjami
   - Sprawdź czy generowanie wykresów nie blokuje UI
   - Obserwuj wskaźniki "⏳ Generowanie..."

## Troubleshooting

### Wykresy nie wyświetlają się

**Przyczyna:** Brak biblioteki matplotlib lub numpy

**Rozwiązanie:**
```bash
pip install matplotlib>=3.8.0 numpy>=1.26.0
```

### Błąd "datetime.fromisoformat() failed"

**Przyczyna:** Sesje mają nieprawidłowy format daty

**Rozwiązanie:** Sprawdź format `started_at` w danych sesji:
```python
# Prawidłowy format:
"started_at": "2024-01-15T14:30:00"

# Nieprawidłowe formaty:
"started_at": "2024-01-15 14:30:00"  # Spacja zamiast 'T'
"started_at": "15/01/2024 14:30"     # Niewłaściwy format
```

### Wykresy nie używają kolorów motywu

**Przyczyna:** Cache nie został wyczyszczony po zmianie motywu

**Rozwiązanie:** Sprawdź czy `_on_theme_changed` czyści cache:
```python
def _on_theme_changed(self, **kwargs):
    self.theme = self.context.theme.get_active_theme()
    self.cached_charts.clear()  # ← To musi być
    self._load_data()
```

### UI zawiesza się podczas generowania wykresów

**Przyczyna:** Generowanie odbywa się w głównym wątku

**Rozwiązanie:** Upewnij się, że generowanie jest asynchroniczne:
```python
# ✗ Złe - blokuje UI
fig = self._create_chart(...)
canvas = FigureCanvasTkAgg(fig, parent)

# ✓ Dobre - nie blokuje UI
def generate():
    fig = self._create_chart(...)
    canvas = FigureCanvasTkAgg(fig, parent)
    self.after(0, lambda: self._show_canvas(canvas))

threading.Thread(target=generate, daemon=True).start()
```

## Najlepsze praktyki

1. **Zawsze używaj cache'owania** dla wykresów
2. **Generuj wykresy asynchronicznie** (threading)
3. **Aktualizuj UI tylko w głównym wątku** (`self.after(0, ...)`)
4. **Używaj kolorów motywu** dla spójności
5. **Obsługuj przypadki brzegowe** (brak danych, pojedyncza sesja)
6. **Loguj błędy** dla debugowania
7. **Dodawaj docstringi** do nowych metod
8. **Testuj z różnymi zestawami danych**
