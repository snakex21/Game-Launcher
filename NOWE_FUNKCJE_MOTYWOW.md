# 🎨 Nowe Funkcje Motywów - Krótki Przewodnik

## Co się zmieniło?

Teraz możesz **tworzyć własne motywy kolorystyczne** bezpośrednio w aplikacji! Nie musisz już edytować plików JSON - wszystko odbywa się przez przyjazny interfejs.

## Gdzie to znaleźć?

**Ustawienia → Personalizacja → Przewiń w dół**

Znajdziesz dwie nowe sekcje:
1. **🎨 Edytor Własnych Motywów** - twórz i edytuj motywy
2. **📚 Twoje Motywy** - lista wszystkich Twoich motywów

## Szybki Start

### Tworzenie Motywu (3 kroki)

1. **Kliknij "✨ Nowy motyw"**
2. **Wpisz nazwę** (np. "moj_motyw")
3. **Ustaw kolory** używając:
   - Wpisywania kodu hex (np. `#ff0000`)
   - Lub klikając 🎨 i wybierając z palety
4. **Kliknij "💾 Zapisz motyw"**

✅ Gotowe! Twój motyw pojawi się na liście i będzie dostępny w dropdown motywów.

## Główne Funkcje

### 📋 Załaduj aktualny
Wczytuje aktualnie używany motyw do edytora - świetny punkt wyjścia!

### 👁️ Podgląd
Zobacz jak motyw wygląda bez zapisywania (tymczasowa aplikacja).

### ✏️ Edytuj
Kliknij przy motywie na liście - załaduje go do edytora.

### 🗑️ Usuń
Usuwa motyw z potwierdzeniem. **Uwaga:** Nie można cofnąć!

### ✓ Użyj
Aktywuje wybrany motyw natychmiast.

## 7 Kolorów do Personalizacji

1. **Kolor bazowy** - najciemniejszy, używany rzadko
2. **Tło** - główne tło aplikacji
3. **Powierzchnia** - karty i panele
4. **Powierzchnia alt.** - hover i alternatywy
5. **Tekst** - główny kolor tekstu
6. **Tekst wyciszony** - drugorzędne informacje
7. **Akcent** - przyciski i podkreślenia

## Zabezpieczenia

### 🛡️ Motywy Systemowe są Chronione

Nie możesz usunąć ani nadpisać:
- **midnight** (ciemny niebieski)
- **emerald** (zielony)
- **sunset** (różowy)

Jeśli chcesz je zmodyfikować:
1. Załaduj je do edytora
2. **Zmień nazwę** (np. "midnight_custom")
3. Zapisz jako nowy motyw

## Wskazówki

### ✨ Dobre Praktyki

- **Nazywaj jasno**: Użyj opisowych nazw (np. "ciemny_fiolet", "ocean_blue")
- **Testuj podgląd**: Przed zapisem kliknij "👁️ Podgląd"
- **Zachowuj kopie**: Wyeksportuj udane motywy (📤 Eksportuj motyw)
- **Eksperymentuj**: Zacznij od "📋 Załaduj aktualny" i zmieniaj po jednym kolorze

### 🎨 Inspiracje Kolorystyczne

**Ciemne Motywy:**
- Granat + Niebieski akcent
- Czarny + Cyjan akcent
- Ciemny fiolet + Różowy akcent

**Ciepłe Motywy:**
- Brąz + Złoty akcent
- Burgundowy + Różowy akcent
- Kawa + Beżowy akcent

**Chłodne Motywy:**
- Grafit + Niebieski akcent
- Granatowy + Błękitny akcent
- Czarny + Miętowy akcent

## Export i Import

### 📤 Eksport (Udostępnianie)
1. Aktywuj motyw, który chcesz wyeksportować
2. Kliknij "📤 Eksportuj motyw" (w sekcji "Motyw i Wygląd")
3. Zapisz plik JSON
4. Udostępnij znajomym!

### 📥 Import (Instalowanie)
1. Pobierz plik motywu (.json)
2. Kliknij "📥 Importuj motyw"
3. Wybierz plik
4. Motyw pojawi się na Twojej liście

## Rozwiązywanie Problemów

### ❌ "Nie można nadpisać motywu systemowego"
**Przyczyna:** Próbujesz użyć nazwy "midnight", "emerald" lub "sunset"  
**Rozwiązanie:** Zmień nazwę na inną

### ❌ "Nieprawidłowy kolor hex"
**Przyczyna:** Kolor nie jest w formacie `#xxx` lub `#xxxxxx`  
**Rozwiązanie:** Upewnij się, że kolory zaczynają się od `#` i mają 3 lub 6 cyfr hex

### 🤔 Interfejs jest nieczytelny po zastosowaniu motywu
**Rozwiązanie:** Wybierz "midnight" z dropdown motywów, aby wrócić do domyślnego

### 🤔 Nie widzę swojego motywu w dropdown
**Rozwiązanie:** Sprawdź czy kliknąłeś "💾 Zapisz motyw" - podgląd nie zapisuje!

## Często Zadawane Pytania

**P: Ile motywów mogę stworzyć?**  
O: Praktycznie nieograniczoną liczbę!

**P: Czy motywy są zapisywane lokalnie?**  
O: Tak, w pliku `config.json` w folderze aplikacji.

**P: Czy mogę przywrócić usunięty motyw?**  
O: Nie, chyba że masz backup. Zawsze jest dialog potwierdzenia przed usunięciem.

**P: Czy mogę tworzyć jasne motywy?**  
O: Tak! Ustaw jasne kolory dla tła i ciemne dla tekstu.

**P: Co to są "podglądy kolorów"?**  
O: Małe kolorowe kwadraty obok pól tekstowych - pokazują jak kolor wygląda.

## Przykład Krok po Kroku

### Stwórzmy Motyw "Midnight Purple"

1. **Ustawienia → Personalizacja → Edytor Własnych Motywów**

2. **Kliknij "📋 Załaduj aktualny"** (załaduje midnight)

3. **Zmień nazwę** na: `midnight_purple`

4. **Zmień kolory**:
   - Kolor bazowy: Zostaw `#0b1120`
   - Tło: Zostaw `#0f172a`
   - Powierzchnia: Zmień na `#2d1f3d` (fioletowy)
   - Powierzchnia alt: Zmień na `#3d2850` (jaśniejszy fiolet)
   - Tekst: Zostaw `#e2e8f0`
   - Tekst wyciszony: Zmień na `#b39cc7` (wyciszony fiolet)
   - Akcent: Zmień na `#a855f7` (jasny fiolet)

5. **Kliknij "👁️ Podgląd"** - zobacz jak wygląda

6. **Kliknij "💾 Zapisz motyw"**

7. **Kliknij "✓ Użyj"** na liście Twoje Motywy

🎉 Gotowe! Masz własny fioletowy motyw!

---

## Co Dalej?

- 🔍 Eksperymentuj z różnymi kombinacjami kolorów
- 📤 Udostępniaj swoje motywy znajomym
- 🎨 Twórz motywy dla różnych nastrojów (praca, wieczór, gaming)
- 💡 Zobacz [`PRZYKLAD_UZYWANIA_EDYTORA.md`](PRZYKLAD_UZYWANIA_EDYTORA.md) dla więcej scenariuszy

**Miłej zabawy z personalizacją!** 🚀
