# Przewodnik Użytkownika - Ustawienia Okna

## Optymalne rozmiary okna

Game Launcher 2.0 został zaprojektowany z myślą o elastyczności, ale niektóre funkcje działają najlepiej w określonych rozmiarach okna.

### Zalecane rozmiary

| Tryb | Szerokość | Wysokość | Opis |
|------|-----------|----------|------|
| **Minimalne** | 1000px | 600px | Wszystkie elementy widoczne, układ 2-kolumnowy |
| **Zalecane** | 1400px | 800px | Domyślne, komfortowe dla większości użytkowników |
| **Duże** | 1600px | 900px | Idealne dla monitorów Full HD |
| **Pełny ekran** | F11 | F11 | Maksymalne wykorzystanie ekranu |

### Minimalne wymagania

**Aplikacja nie pozwoli zmniejszyć okna poniżej 1000x600px.**

Jest to niezbędne minimum aby:
- Wszystkie nagłówki były widoczne
- Karty osiągnięć wyświetlały się w 2 kolumnach
- Formularze i dialogi mieściły się na ekranie
- Sidebar i menu były czytelne

## Co zrobić gdy elementy nie są widoczne?

### Problem: Nie widzę nagłówka "Aktualności" lub innych widoków

**Rozwiązanie**:
1. Sprawdź rozmiar okna - czy jest przynajmniej 1000x600px?
2. Spróbuj powiększyć okno
3. Jeśli problem występuje w trybie pełnoekranowym, zgłoś błąd

### Problem: Okno jest za małe na moim ekranie

**Rozwiązanie**:
1. Zmień rozdzielczość monitora (zalecane minimum: 1366x768)
2. Użyj scroll'a w widokach (większość widoków ma wbudowane scrollowanie)
3. Zmniejsz skalowanie UI w systemie (Windows: Ustawienia → System → Wyświetlacz)

### Problem: Okno jest za duże

**Rozwiązanie**:
1. Zmniejsz okno do wygodnego rozmiaru (minimum 1000x600)
2. Przenieś okno w inne miejsce ekranu
3. Aplikacja zapamięta rozmiar i pozycję okna

## Tryby wyświetlania

### Tryb okienkowy
- Możliwość zmiany rozmiaru
- Można przesuwać okno
- Działa obok innych aplikacji
- Minimalizacja do tray (jeśli włączona w ustawieniach)

### Tryb pełnoekranowy (F11)
- Maksymalne wykorzystanie ekranu
- Brak ramki okna
- Idealne do sesji gier
- ESC lub F11 aby wyjść

## Rozdzielczości ekranu

### Wspierane rozdzielczości

| Rozdzielczość | Status | Uwagi |
|---------------|--------|-------|
| **1920x1080** (Full HD) | ✅ Zalecane | Idealne doświadczenie |
| **1600x900** | ✅ Bardzo dobre | Komfortowe użytkowanie |
| **1366x768** | ✅ Dobre | Minimum dla laptopów |
| **1280x720** (HD) | ⚠️ Ograniczone | Może wymagać scrollowania |
| **<1280x720** | ❌ Niewspierane | Zbyt małe dla komfortnego użycia |

### Monitory Ultra-Wide

Na monitorach ultra-wide (21:9, 32:9):
- Aplikacja wykorzysta dodatkową szerokość
- Sidebar pozostanie po lewej
- Content zajmie resztę przestrzeni
- Można wyświetlić więcej kart osiągnięć obok siebie

### Monitory 4K i wyższe

Na monitorach 4K (3840x2160) i wyższych:
- Aplikacja skaluje się automatycznie
- Czcionki pozostają czytelne
- Karty i elementy są większe
- Wszystko działa normalnie

## Układy ekranu

### Jeden monitor
- Użyj F11 dla pełnego ekranu podczas grania
- W trybie okienkowym możesz mieć otwarte inne aplikacje

### Dwa monitory
- Możesz mieć Game Launcher na jednym monitorze
- Gra/inne aplikacje na drugim
- Przeciągaj okno między monitorami
- Rozmiar i pozycja są zapisywane

### Trzy lub więcej monitorów
- Działa tak samo jak z dwoma
- Możesz umieścić launcher na dowolnym monitorze

## Skalowanie DPI

### Windows

Jeśli elementy są:
- **Za małe**: Ustawienia → System → Wyświetlacz → Skalowanie (zwiększ do 125% lub 150%)
- **Za duże**: Zmniejsz skalowanie do 100%

### macOS

Jeśli elementy są:
- **Za małe**: Preferencje Systemowe → Monitory → Skalowanie (wybierz większy rozmiar)
- **Za duże**: Wybierz mniejszy rozmiar

### Linux

Zależy od środowiska graficznego:
- **GNOME**: Ustawienia → Wyświetlacze → Skala
- **KDE Plasma**: Ustawienia Systemowe → Wyświetlanie → Skalowanie
- **XFCE**: Ustawienia → Wygląd → Czcionki → DPI

## Rozwiązywanie problemów

### Okno nie mieści się na ekranie

1. Usuń plik konfiguracyjny pozycji okna (jeśli istnieje)
2. Uruchom ponownie aplikację
3. Okno pojawi się w domyślnej pozycji i rozmiarze

### Elementy nakładają się na siebie

1. Sprawdź rozdzielczość ekranu
2. Upewnij się że okno ma co najmniej 1000x600px
3. Sprawdź skalowanie DPI w systemie
4. Uruchom ponownie aplikację

### Czcionki są nieczytelne

1. Zwiększ rozmiar okna
2. Zmień skalowanie DPI w systemie
3. Sprawdź czy używasz aktualnej wersji aplikacji

### Scrollowanie nie działa

1. Upewnij się że kursor myszy jest nad obszarem z zawartością
2. Spróbuj użyć scroll bara po prawej stronie
3. Użyj klawiszy strzałek lub Page Up/Down

## Skróty klawiszowe (planowane)

| Skrót | Akcja |
|-------|-------|
| **F11** | Pełny ekran / Wyjście z pełnego ekranu |
| **Ctrl + +** | Powiększ UI (planowane) |
| **Ctrl + -** | Pomniejsz UI (planowane) |
| **Ctrl + 0** | Resetuj skalowanie UI (planowane) |
| **Alt + Enter** | Przełącz tryb okienkowy/pełny ekran (planowane) |

## Wskazówki Pro

### Dla małych ekranów (1366x768)
- Użyj trybu pełnoekranowego (F11)
- Zwiń sidebar gdy nie jest potrzebny (planowane)
- Skup się na jednym widoku na raz

### Dla dużych ekranów (1920x1080+)
- Użyj domyślnego rozmiaru lub większego
- Możesz mieć wiele aplikacji obok siebie
- Rozważ powiększenie okna dla lepszej widoczności

### Dla użytkowników laptopów
- Zwiększ rozmiar okna gdy pracujesz przy biurku
- Zmniejsz rozmiar gdy pracujesz w podróży
- Aplikacja zapamięta Twoje preferencje

## Najczęściej zadawane pytania

**Q: Czy mogę zmieniać rozmiar okna podczas działania aplikacji?**  
A: Tak, możesz zmieniać rozmiar w dowolnym momencie (minimum 1000x600).

**Q: Czy aplikacja zapamięta rozmiar mojego okna?**  
A: Tak, rozmiar i pozycja są zapisywane i przywracane przy następnym uruchomieniu.

**Q: Co się stanie jeśli zmniejszę okno poniżej 1000x600?**  
A: Nie możesz - okno zatrzyma się na minimalnym rozmiarze.

**Q: Czy mogę używać aplikacji na ekranie dotykowym?**  
A: Tak, aplikacja wspiera podstawowe gesty dotykowe (scroll, kliknięcie).

**Q: Czy mogę uruchomić aplikację na monitorze pionowym?**  
A: Tak, ale zalecamy orientację poziomą dla najlepszego doświadczenia.
