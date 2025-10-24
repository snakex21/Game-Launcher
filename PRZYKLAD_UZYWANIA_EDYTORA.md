# Przykłady Użycia Edytora Motywów

## Scenariusz 1: Tworzenie Nowego Motywu od Zera

**Cel:** Stworzyć motyw "Nocny Granat" z odcieniami granatu i niebieskiego.

### Kroki:

1. **Otwórz edytor**:
   - Przejdź do: Ustawienia → Personalizacja
   - Przewiń do sekcji "🎨 Edytor Własnych Motywów"

2. **Rozpocznij nowy motyw**:
   - Kliknij **✨ Nowy motyw**
   - W polu "Nazwa motywu" wpisz: `nocny_granat`

3. **Ustaw kolory**:
   - **Kolor bazowy**: `#0a0e1f` (bardzo ciemny granat)
   - **Tło**: `#0f1629` (ciemny granat)
   - **Powierzchnia**: `#1a2237` (granat)
   - **Powierzchnia alt.**: `#243045` (jaśniejszy granat)
   - **Tekst**: `#e6eef7` (jasny niebieski)
   - **Tekst wyciszony**: `#8b9eb8` (wyciszony niebieski)
   - **Akcent**: `#3b82f6` (jasny niebieski)

4. **Podgląd** (opcjonalnie):
   - Kliknij **👁️ Podgląd** aby zobaczyć efekt
   - Jeśli nie podoba się - zmień kolory i podejrzyj ponownie

5. **Zapisz**:
   - Kliknij **💾 Zapisz motyw**
   - Zobaczysz powiadomienie: "Zapisano motyw 'nocny_granat'"
   - Motyw pojawi się na liście "Twoje Motywy"

6. **Użyj motywu**:
   - Na liście "Twoje Motywy" znajdź "nocny_granat"
   - Kliknij **✓ Użyj**
   - Aplikacja przełączy się na nowy motyw

---

## Scenariusz 2: Modyfikacja Istniejącego Motywu

**Cel:** Zmodyfikować motyw systemowy "midnight" aby był cieplejszy (więcej brązu).

### Kroki:

1. **Załaduj bazę**:
   - Wybierz "midnight" z dropdown motywów u góry
   - W edytorze kliknij **📋 Załaduj aktualny**
   - Wszystkie pola wypełnią się kolorami z "midnight"

2. **Zmień nazwę**:
   - Pole nazwy pokazuje "midnight"
   - Zmień na: `midnight_warm`
   - ⚠️ Ważne: Gdybyś zostawił "midnight", dostałbyś błąd (motyw systemowy jest chroniony)

3. **Dostosuj kolory**:
   - **Kolor bazowy**: Zmień z `#0b1120` na `#1a1410` (brązowy odcień)
   - **Tło**: Zmień z `#0f172a` na `#251b14` (cieplejszy)
   - **Powierzchnia**: Zmień z `#1e293b` na `#332619` (brązowy)
   - Pozostałe kolory dostosuj podobnie

4. **Zapisz jako nowy**:
   - Kliknij **💾 Zapisz motyw**
   - Teraz masz motyw "midnight_warm" na liście własnych motywów
   - Oryginalny "midnight" pozostaje niezmieniony

---

## Scenariusz 3: Edycja Własnego Motywu

**Cel:** Poprawić kolor akcentu w już istniejącym motywie.

### Kroki:

1. **Znajdź motyw**:
   - Przewiń do sekcji "📚 Twoje Motywy"
   - Znajdź motyw do edycji (np. "nocny_granat")

2. **Załaduj do edytora**:
   - Kliknij **✏️ Edytuj** przy wybranym motywie
   - Edytor wypełni się danymi tego motywu
   - Zakładka automatycznie przewinie do edytora

3. **Zmień kolor akcentu**:
   - Znajdź pole "Akcent"
   - Kliknij **🎨** obok tego pola
   - W color pickerze wybierz nowy kolor (np. cyjan zamiast niebieskiego)
   - Kliknij OK

4. **Zapisz zmiany**:
   - Kliknij **💾 Zapisz motyw**
   - Nazwa jest ta sama, więc motyw zostanie **nadpisany**
   - Zobaczysz powiadomienie o zapisie

5. **Zastosuj**:
   - Jeśli motyw był już aktywny, zmiany zadziałają automatycznie
   - Jeśli nie - kliknij **✓ Użyj** na liście

---

## Scenariusz 4: Usunięcie Nieudanego Motywu

**Cel:** Usunąć motyw, który się nie sprawdził.

### Kroki:

1. **Znajdź motyw**:
   - Na liście "Twoje Motywy" znajdź motyw do usunięcia

2. **Usuń**:
   - Kliknij czerwony przycisk **🗑️**
   - Pojawi się dialog potwierdzenia:
     ```
     Czy na pewno chcesz usunąć motyw 'xxx'?
     Tej operacji nie można cofnąć.
     ```
   - Kliknij **Yes** (Tak)

3. **Automatyczne przełączenie**:
   - Jeśli usuwany motyw był aktywny, aplikacja automatycznie przełączy się na "midnight"
   - Zobaczysz powiadomienie o usunięciu

4. **Potwierdzenie**:
   - Motyw zniknie z listy "Twoje Motywy"
   - Nie będzie już dostępny w dropdown motywów

---

## Scenariusz 5: Próba Nadpisania Motywu Systemowego (Błąd)

**Cel:** Zrozumienie zabezpieczeń przed nadpisaniem motywów systemowych.

### Co się stanie:

1. **Próba zapisu jako "midnight"**:
   - Wprowadź nazwę: `midnight`
   - Ustaw jakieś kolory
   - Kliknij **💾 Zapisz motyw**

2. **Wynik**:
   - ❌ Zobaczysz powiadomienie błędu:
     ```
     Nie można nadpisać motywu systemowego 'midnight'
     ```
   - Motyw NIE zostanie zapisany
   - Systemowy "midnight" pozostaje niezmieniony

3. **Rozwiązanie**:
   - Zmień nazwę na coś innego (np. `midnight_custom`)
   - Zapisz ponownie

### Podobnie z próbą usunięcia:

1. **Próba usunięcia "emerald"**:
   - Motyw "emerald" nie ma przycisku 🗑️ (jest systemowy)
   - Gdyby ktoś próbował usunąć programowo - dostałby błąd

---

## Scenariusz 6: Tworzenie Motywu Przez Kopiowanie

**Cel:** Stworzyć motyw podobny do "sunset" ale z innymi odcieniami.

### Kroki:

1. **Wybierz bazę**:
   - Wybierz "sunset" z dropdown motywów
   - Kliknij **📋 Załaduj aktualny**

2. **Zmień nazwę**:
   - Zmień z "sunset" na `sunset_purple`

3. **Dostosuj kolory**:
   - Zamień różowe odcienie na fioletowe
   - Przykład:
     - Kolor bazowy: `#1f0a16` → `#180a1f` (fioletowy odcień)
     - Accent: `#fb7185` → `#a855f7` (fiolet)

4. **Zapisz i użyj**:
   - **💾 Zapisz motyw**
   - **✓ Użyj** z listy

---

## Scenariusz 7: Eksport Motywu do Udostępnienia

**Cel:** Udostępnić własny motyw znajomemu.

### Kroki:

1. **Aktywuj motyw**:
   - Kliknij **✓ Użyj** przy motywie, który chcesz wyeksportować

2. **Eksportuj**:
   - Przewiń do sekcji "Motyw i Wygląd" (nad edytorem)
   - Kliknij **📤 Eksportuj motyw**
   - Wybierz lokalizację zapisu (np. Pulpit)
   - Wpisz nazwę pliku: `nocny_granat.json`

3. **Udostępnij plik**:
   - Wyślij plik JSON znajomemu przez email/chat
   - Znajomy może go zaimportować używając **📥 Importuj motyw**

---

## Scenariusz 8: Import Motywu od Kogoś Innego

**Cel:** Zainstalować motyw otrzymany od znajomego.

### Kroki:

1. **Przygotuj plik**:
   - Pobierz plik motywu (np. `ocean_theme.json`)
   - Zapisz w znanej lokalizacji

2. **Importuj**:
   - W sekcji "Motyw i Wygląd" kliknij **📥 Importuj motyw**
   - Wybierz plik `ocean_theme.json`
   - Kliknij Open

3. **Walidacja**:
   - Jeśli motyw jest poprawny:
     - Zostanie dodany do listy własnych motywów
     - Zobaczysz powiadomienie: "Zaimportowano motyw ocean_theme"
     - Pojawi się w dropdown motywów
   - Jeśli plik jest nieprawidłowy:
     - Zobaczysz błąd: "Nie udało się zaimportować motywu"

4. **Użyj**:
   - Znajdź motyw na liście "Twoje Motywy"
   - Kliknij **✓ Użyj**

---

## Częste Pytania

### P: Czy mogę mieć wiele motywów o podobnych nazwach?
**O:** Tak, ale nazwy muszą być unikalne. `theme_v1` i `theme_v2` to różne motywy.

### P: Co się stanie jeśli wyłączę aplikację podczas edycji?
**O:** Nic. Edytor nie zapisuje automatycznie - musisz kliknąć **💾 Zapisz motyw**.

### P: Czy mogę tworzyć motywy jasne (light themes)?
**O:** Tak! Ustaw jasne kolory dla tła i ciemne dla tekstu.

### P: Ile motywów mogę stworzyć?
**O:** Praktycznie nieograniczoną liczbę (limit to rozmiar pliku `config.json`).

### P: Czy mogę przywrócić usunięty motyw?
**O:** Nie, chyba że masz backup konfiguracji. Dlatego przed usunięciem pojawia się potwierdzenie.

### P: Co zrobić jeśli źle ustawiłem kolory i interfejs jest nieczytelny?
**O:** Wybierz motyw systemowy (midnight, emerald, sunset) z dropdown motywów u góry.

---

**Powodzenia w tworzeniu własnych motywów!** 🎨
