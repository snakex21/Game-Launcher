# Bugfix: Brak widoczności elementów w trybie okienkowym

## Problem

W trybie okienkowym (gdy okno jest zmniejszone) nagłówki widoków takie jak "📰 Aktualności" nie są widoczne. W trybie pełnoekranowym wszystko działa poprawnie.

**Przyczyna**: 
- Brak ustawienia minimalnego rozmiaru okna (`minsize`)
- Zbyt duże paddingi górne w widokach (20px)
- Okno może być zmniejszone poniżej wysokości wymaganej do wyświetlenia wszystkich elementów

## Zmiany

### 1. Dodanie minimalnego rozmiaru okna

**Plik**: `app/ui/main_window.py`  
**Linia**: 24

```python
# Przed:
self.geometry("1400x800")

# Po:
self.geometry("1400x800")
self.minsize(1000, 600)  # Minimalne wymiary okna aby elementy były widoczne
```

**Efekt**: Okno nie może być zmniejszone poniżej 1000x600px, co zapewnia widoczność wszystkich elementów UI.

### 2. Zmniejszenie paddingu górnego w widokach

#### NewsView (`app/plugins/news.py`)

**Linia**: 36, 67

```python
# Przed:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
self.scrollable.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

# Po:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
self.scrollable.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
```

**Efekt**: Zmniejszono górny padding z 20px do 10px, co daje więcej miejsca na treść.

#### HomeView (`app/plugins/home.py`)

**Linia**: 50

```python
# Przed:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

# Po:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
```

#### StatisticsView (`app/plugins/statistics.py`)

**Linia**: 48

```python
# Przed:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

# Po:
header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 10))
```

## Wynik

### Przed poprawką:
- ❌ W trybie okienkowym (małe okno) nagłówki są niewidoczne
- ❌ Okno można zmniejszyć do bardzo małych rozmiarów
- ❌ Zawartość jest obcięta/ukryta poza widocznym obszarem
- ❌ Użytkownik musi przełączyć się na pełny ekran aby zobaczyć wszystko

### Po poprawce:
- ✅ Minimalne wymiary okna: 1000x600px
- ✅ Okno nie może być zmniejszone poniżej tego rozmiaru
- ✅ Wszystkie nagłówki i elementy są widoczne
- ✅ Lepsze wykorzystanie przestrzeni (zmniejszone paddingi)
- ✅ Responsywny design - działa w trybie okienkowym i pełnoekranowym

## Parametry

### Minimalne wymiary okna

**Szerokość**: 1000px
- Sidebar: 240px
- Content: ~740px
- Paddings: 20px

**Wysokość**: 600px
- Header: ~80px
- Filters/Stats: ~60px
- Content (scrollable): ~440px
- Paddings: 20px

### Dlaczego te wymiary?

- **1000px szerokość**: Zapewnia komfortowe wyświetlanie kart (2 kolumny) i formularzy
- **600px wysokość**: Minimum do wyświetlenia nagłówka + przynajmniej 2-3 wiersze treści
- Mniejsze wymiary powodowałyby obcinanie elementów lub potrzebę scrollowania w dziwnych miejscach

## Alternatywne rozwiązania (nieimplementowane)

Gdyby problem nadal występował, można by:

1. **Dynamiczne ukrywanie elementów** - zmniejszać rozmiar czcionek/ikonek w małych oknach
2. **Responsive breakpoints** - zmieniać layout na mobilny poniżej pewnej szerokości
3. **Scrollable parent** - użyć CTkScrollableFrame dla całego main_content
4. **Hamburger menu** - ukrywać sidebar w małych oknach
5. **Compact mode** - tryb kompaktowy z mniejszymi elementami

## Testowanie

### Jak przetestować:

1. Uruchom aplikację w trybie okienkowym
2. Spróbuj zmniejszyć okno - powinno zatrzymać się na 1000x600
3. Przejdź do widoku "Aktualności" - nagłówek "📰 Aktualności" powinien być widoczny
4. Sprawdź inne widoki (Home, Statystyki, Osiągnięcia) - wszystkie nagłówki widoczne
5. Zmień rozmiar okna - zawartość powinna być zawsze widoczna

### Oczekiwane rezultaty:

- Okno nie zmniejsza się poniżej 1000x600px
- Wszystkie nagłówki są widoczne
- Brak obcinania tekstu
- Scrollowanie działa prawidłowo dla treści
- UI wygląda dobrze zarówno w małym oknie jak i pełnym ekranie

## Uwagi

- **AchievementsView** już miało mniejsze paddingi (16, 6), więc nie wymagało zmian
- **LibraryView** i inne widoki mogą potrzebować podobnych zmian jeśli użytkownicy zgłoszą problemy
- Padding dolny został również zmniejszony w NewsView (z 20 do 10) dla lepszego wykorzystania przestrzeni
- Minimalne wymiary można dostosować w `main_window.py` jeśli potrzeba

## Kompatybilność

- ✅ Windows - minsize działa poprawnie
- ✅ macOS - minsize działa poprawnie  
- ✅ Linux - minsize działa poprawnie
- ✅ Nie wpływa na działanie w trybie pełnoekranowym
- ✅ Backwards compatible - nie zmienia API
