# Edytor Własnych Motywów - Dokumentacja

## Podsumowanie

Dodano pełnoprawny edytor własnych motywów kolorystycznych bezpośrednio w interfejsie ustawień. Użytkownicy mogą teraz tworzyć, edytować i zarządzać własnymi motywami bez konieczności ręcznej edycji plików JSON.

## Funkcjonalności

### 🎨 Edytor Motywów

Lokalizacja: **Ustawienia → Personalizacja → Edytor Własnych Motywów**

#### Tworzenie Nowego Motywu

1. **Pole nazwy motywu**: Wprowadź unikalną nazwę dla swojego motywu
2. **Przyciski pomocnicze**:
   - **📋 Załaduj aktualny**: Wczytuje aktualnie aktywny motyw jako punkt wyjścia
   - **✨ Nowy motyw**: Czyści edytor i ustawia domyślne wartości

3. **Edycja kolorów**: 7 pól kolorystycznych z:
   - Polem tekstowym dla kodu hex
   - Podglądem koloru na żywo
   - Przyciskiem 🎨 do otwarcia color pickera

4. **Kolory do edycji**:
   - **Kolor bazowy** (base_color)
   - **Tło** (background)
   - **Powierzchnia** (surface)
   - **Powierzchnia alt.** (surface_alt)
   - **Tekst** (text)
   - **Tekst wyciszony** (text_muted)
   - **Akcent** (accent)

5. **Akcje**:
   - **💾 Zapisz motyw**: Zapisuje motyw do konfiguracji
   - **👁️ Podgląd**: Tymczasowo aplikuje motyw bez zapisywania

### 📚 Lista Własnych Motywów

Sekcja poniżej edytora wyświetla wszystkie utworzone motywy.

Dla każdego motywu:
- **Miniaturki kolorów**: 3 kwadraciki pokazujące główne kolory (base, surface, accent)
- **Nazwa motywu**: Czytelna nazwa
- **Przyciski akcji**:
  - **✓ Użyj**: Aktywuje motyw
  - **✏️ Edytuj**: Wczytuje motyw do edytora
  - **🗑️ Usuń**: Usuwa motyw (z potwierdzeniem)

## Zabezpieczenia

### 🛡️ Ochrona Motywów Systemowych

1. **Nie można nadpisać motywów systemowych**:
   - midnight
   - emerald
   - sunset

2. **Nie można usunąć motywów systemowych**:
   - Przycisk usuwania działa tylko dla własnych motywów
   - Walidacja w `ThemeService.delete_custom_theme()`

3. **Walidacja nazw**:
   - Sprawdzanie kolizji z motywami systemowymi
   - Komunikat błędu przy próbie nadpisania

### ✅ Walidacja Danych

1. **Wymagane pola**: Wszystkie 7 kolorów + nazwa motywu
2. **Walidacja kolorów hex**:
   - Muszą zaczynać się od `#`
   - Długość: 4 lub 7 znaków (np. `#fff` lub `#ffffff`)
3. **Komunikaty błędów**: Powiadomienia o nieprawidłowych danych

## Struktura Danych

### config.json

```json
{
  "settings": {
    "theme": "midnight",
    "custom_themes": {
      "moj_motyw": {
        "name": "moj_motyw",
        "base_color": "#0b1120",
        "background": "#0f172a",
        "surface": "#1e293b",
        "surface_alt": "#273449",
        "text": "#e2e8f0",
        "text_muted": "#94a3b8",
        "accent": "#6366f1"
      },
      "ciemny_fiolet": {
        "name": "ciemny_fiolet",
        "base_color": "#1a0f1f",
        "background": "#2d1b3d",
        "surface": "#3d2450",
        "surface_alt": "#4d2e63",
        "text": "#e8dff0",
        "text_muted": "#b39cc7",
        "accent": "#a855f7"
      }
    }
  }
}
```

## API ThemeService

### Nowe Metody

#### `save_custom_theme(theme_name: str, theme_data: dict) -> bool`
Zapisuje własny motyw do konfiguracji.

**Parametry:**
- `theme_name`: Nazwa motywu (klucz w dict)
- `theme_data`: Słownik z danymi motywu (zawiera wszystkie wymagane pola)

**Zwraca:**
- `True`: Sukces
- `False`: Błąd (np. kolizja z motywem systemowym, nieprawidłowe dane)

**Walidacja:**
- Sprawdza kolizję z motywami systemowymi
- Weryfikuje obecność wszystkich wymaganych pól
- Waliduje formaty kolorów hex

#### `delete_custom_theme(theme_name: str) -> bool`
Usuwa własny motyw.

**Parametry:**
- `theme_name`: Nazwa motywu do usunięcia

**Zwraca:**
- `True`: Sukces
- `False`: Błąd (motyw systemowy lub nie istnieje)

**Dodatkowe akcje:**
- Jeśli usuwany motyw jest aktywny, przełącza na "midnight"
- Emituje event `custom_themes_changed`

#### `is_system_theme(theme_name: str) -> bool`
Sprawdza czy motyw jest systemowy.

**Parametry:**
- `theme_name`: Nazwa motywu

**Zwraca:**
- `True`: Jest motywem systemowym
- `False`: Jest własnym motywem

#### `get_custom_themes() -> dict[str, dict[str, Any]]`
Zwraca wszystkie własne motywy.

**Zwraca:**
- Słownik z własnymi motywami (klucz: nazwa, wartość: dane motywu)

### Zmodyfikowane Metody

#### `available_themes() -> list[Theme]`
**Zmiana:** Teraz zwraca motywy systemowe + wszystkie własne motywy.

#### `get_active_theme() -> Theme`
**Zmiana:** Szuka motywu najpierw wśród systemowych, potem wśród własnych.

## Workflow Użytkownika

### Tworzenie Nowego Motywu

1. Przejdź do: **Ustawienia → Personalizacja**
2. Przewiń do sekcji **Edytor Własnych Motywów**
3. Kliknij **✨ Nowy motyw** (opcjonalnie lub **📋 Załaduj aktualny**)
4. Wprowadź nazwę motywu
5. Dostosuj kolory:
   - Wpisz ręcznie kod hex, lub
   - Kliknij 🎨 aby użyć color pickera
6. (Opcjonalnie) Kliknij **👁️ Podgląd** aby zobaczyć motyw w akcji
7. Kliknij **💾 Zapisz motyw**
8. Motyw pojawi się na liście **Twoje Motywy**

### Edycja Istniejącego Motywu

1. Znajdź motyw na liście **Twoje Motywy**
2. Kliknij **✏️ Edytuj**
3. Edytor załaduje wszystkie kolory motywu
4. Wprowadź zmiany
5. Kliknij **💾 Zapisz motyw** (nadpisze istniejący motyw)

### Usuwanie Motywu

1. Znajdź motyw na liście **Twoje Motywy**
2. Kliknij **🗑️**
3. Potwierdź usunięcie w dialogu
4. Motyw zostanie usunięty
5. Jeśli był aktywny, aplikacja przełączy się na "midnight"

### Stosowanie Motywu

**Sposób 1:** Z listy własnych motywów
- Kliknij **✓ Użyj** przy wybranym motywie

**Sposób 2:** Z dropdown motywów
- Wybierz motyw z listy rozwijanej na górze sekcji motywów

## Events

### `custom_themes_changed`
Emitowany gdy:
- Zapisano nowy motyw
- Usunięto motyw

Subskrybenci mogą odświeżyć swoje listy motywów.

### `theme_changed`
Emitowany gdy aktywny motyw się zmienia (zachowane z poprzedniej wersji).

## Migracja z Poprzedniej Wersji

### Kompatybilność Wsteczna

Stara struktura z pojedynczym `custom_theme` jest nadal obsługiwana:

```json
{
  "settings": {
    "custom_theme": {
      "name": "stary_motyw",
      ...
    }
  }
}
```

ThemeService automatycznie:
1. Wczyta stary `custom_theme` do listy dostępnych motywów
2. Sprawdzi czy nie koliduje z nowymi własnymi motywami
3. Pozwoli na kontynuację używania starego motywu

## Przykłady Motywów

### Motyw Nocny Fiolet

```json
{
  "name": "nocny_fiolet",
  "base_color": "#1a0f1f",
  "background": "#2d1b3d",
  "surface": "#3d2450",
  "surface_alt": "#4d2e63",
  "text": "#e8dff0",
  "text_muted": "#b39cc7",
  "accent": "#a855f7"
}
```

### Motyw Ocean

```json
{
  "name": "ocean",
  "base_color": "#0c1a27",
  "background": "#0f2942",
  "surface": "#143a5c",
  "surface_alt": "#1a4b75",
  "text": "#d4e9f7",
  "text_muted": "#8fb8d6",
  "accent": "#06b6d4"
}
```

### Motyw Leśny

```json
{
  "name": "lesny",
  "base_color": "#0d1810",
  "background": "#162d1b",
  "surface": "#1f4228",
  "surface_alt": "#285735",
  "text": "#dff0e3",
  "text_muted": "#a0c9ab",
  "accent": "#22c55e"
}
```

## Wskazówki

### Tworzenie Spójnego Motywu

1. **Kolor bazowy**: Najciemniejszy, używany w nielicznych miejscach
2. **Tło**: Główne tło aplikacji (trochę jaśniejsze niż base)
3. **Powierzchnia**: Karty, panele (jeszcze jaśniejsza)
4. **Powierzchnia alt**: Hover states, alternatywne panele
5. **Tekst**: Główny kolor tekstu (wysoki kontrast z tłem)
6. **Tekst wyciszony**: Drugorzędne informacje (niższy kontrast)
7. **Akcent**: Przyciski, podkreślenia (wyraźny, kontrastowy)

### Kolorystyka

- **Ciemne motywy**: base < background < surface < surface_alt
- **Kontrast tekstu**: Minimum 4.5:1 dla dostępności
- **Akcent**: Powinien "wyskakiwać" z tła
- **Spójność**: Użyj odcieni tego samego koloru bazowego

## Techniczne Szczegóły

### Pliki Zmodyfikowane

1. **app/services/theme_service.py** (+100 linii)
   - Nowe metody zarządzania własnymi motywami
   - Walidacja i zabezpieczenia

2. **app/plugins/settings.py** (+440 linii)
   - Edytor motywów w UI
   - Lista własnych motywów
   - Metody obsługi zdarzeń

### Zależności

- **customtkinter**: Komponenty UI
- **tkinter.colorchooser**: Color picker dialog
- **tkinter.messagebox**: Dialog potwierdzenia usunięcia

## FAQ

**Q: Czy mogę edytować motywy systemowe (midnight, emerald, sunset)?**  
A: Nie. Motywy systemowe są chronione. Możesz je załadować do edytora, zmienić nazwę i zapisać jako nowy własny motyw.

**Q: Co się stanie jeśli użyję nazwy, która już istnieje?**  
A: Jeśli to nazwa własnego motywu - nadpiszesz go. Jeśli to motyw systemowy - zobaczysz błąd.

**Q: Czy mogę eksportować własne motywy?**  
A: Tak! Użyj przycisku "📤 Eksportuj motyw" w sekcji powyżej. Eksportuje aktualnie aktywny motyw do pliku JSON.

**Q: Ile motywów mogę stworzyć?**  
A: Teoretycznie nieograniczoną liczbę. Wszystkie są przechowywane w `config.json`.

**Q: Co się stanie po usunięciu aktywnego motywu?**  
A: Aplikacja automatycznie przełączy się na motyw "midnight".

---

**Wersja:** 2.2.0  
**Data:** 2024-10-24  
**Autor:** AI Development Team
