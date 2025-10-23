# 🎮 Game Launcher 2.0 - Szybki Przewodnik

## 🚀 Uruchomienie
```bash
python main.py
```

## ✨ Co Nowego w Wyglądzie?

### 🎯 Naprawiono Nawigację
**Teraz aktywny widok jest wyraźnie widoczny!**
- ✅ Podświetlenie kolorem akcentu
- ✅ Pogrubiona czcionka
- ✅ Ikony przy każdej sekcji

### 📚 Biblioteka Gier - Mega Upgrade!

#### Karty Statystyk (na górze)
Widzisz na pierwszy rzut oka:
- 🎮 **Ile masz gier**
- ⏱️ **Ile godzin zagrałeś**
- 📈 **Średnie ukończenie**

#### Piękne Karty Gier
Każda karta to mini dashboard:
```
┌─────────────────────────────────┐
│ 🎯 Nazwa Gry           ⭐ 9.5   │
│                                  │
│ ⏱️ 21h 20m    📈 75%             │
│ ▓▓▓▓▓▓▓▓░░░░░░░                  │ ← Progress bar!
│                                  │
│ 🏷️ RPG  🏷️ Fantasy              │
│                                  │
│  ▶️ Uruchom    ✏️ Edytuj        │
└─────────────────────────────────┘
```

**Specjalne oznaczenia**:
- 💎 Złota ramka dla gier z oceną >= 8.0
- 📊 Progress bar pokazuje % ukończenia
- 🏷️ Badges z gatunkami

#### Formularz Dodawania Gry
**Znacznie lepszy!**
- 📱 Większe okno z przewijaniem
- 🎚️ **Slider do wyboru oceny** (nie musisz pisać!)
- 📝 Podpowiedzi (placeholders) w polach
- 🎨 Ładny gradient w headerze
- ✨ Przycisk "Zapisz" w kolorze motywu

## 🎨 Motywy

### Dostępne Motywy
1. **Midnight** 🌙 - Ciemny niebieski (domyślny)
2. **Emerald** 🟢 - Ciemny zielony
3. **Sunset** 🌅 - Ciemny różowy

### Zmiana Motywu
1. Kliknij **⚙️ Ustawienia** (ostatni przycisk w menu)
2. Wybierz motyw z listy
3. Wybierz własny **kolor akcentu** (opcjonalnie)
4. Cała aplikacja zmieni się natychmiast!

## 🎯 Nawigacja

```
┌─────────────────────┐
│  🎮 Game Launcher   │
│                     │
│  📚  Biblioteka  ←─ Aktywny (podświetlony)
│  📊  Statystyki     │
│  🗺️  Roadmapa      │
│  🔧  Mody           │
│  📰  Newsy          │
│  ⏰  Przypomnienia  │
│  🎵  Odtwarzacz     │
│  ⚙️  Ustawienia     │
└─────────────────────┘
```

## 📖 Jak Używać?

### Dodaj pierwszą grę
1. Otwórz **📚 Biblioteka**
2. Kliknij **➕ Dodaj Grę**
3. Wpisz nazwę (np. "Wiedźmin 3")
4. Wybierz plik .exe (przycisk **📁 Przeglądaj**)
5. Dodaj gatunki: `RPG, Fantasy, Akcja`
6. Ustaw ocenę sliderem 🎚️
7. Kliknij **💾 Zapisz**

### Uruchom grę
1. Znajdź kartę gry w bibliotece
2. Kliknij **▶️ Uruchom**
3. Aplikacja śledzi czas gry automatycznie!

### Przeglądaj statystyki
1. Kliknij **📊 Statystyki**
2. Zobacz wykresy:
   - 📊 Czas gry (wykres słupkowy)
   - 🥧 Podział gatunków (pie chart)

### Sprawdź newsy
1. Kliknij **📰 Newsy**
2. Przeglądaj aktualności z RSS
3. Kliknij "Czytaj więcej →" aby otworzyć link

### Ustaw przypomnienie
1. Kliknij **⏰ Przypomnienia**
2. Kliknij **+ Dodaj**
3. Wpisz tytuł i wiadomość
4. Ustaw datę i godzinę
5. Wybierz powtarzanie (none/daily/weekly/monthly)

## 🎵 Odtwarzacz Muzyki
1. Kliknij **🎵 Odtwarzacz**
2. Wybierz folder z muzyką
3. Steruj odtwarzaniem: ⏮ ▶️ ⏸ ⏭
4. Reguluj głośność sliderem

## 💡 Pro Tips

### Szybkie statystyki
Nie musisz wchodzić w Statystyki - widzisz je od razu w Bibliotece! (3 karty na górze)

### Znajdź najlepsze gry
Gry z oceną >= 8.0 mają **złotą ramkę** - łatwo je zauważyć!

### Śledź postępy
Progress bar pod każdą grą pokazuje jak bardzo ją ukończyłeś.

### Personalizacja
- Zmień motyw w Ustawieniach
- Ustaw własny kolor akcentu
- Włącz/wyłącz powiadomienia

## ⌨️ Skróty (Plany na przyszłość)
- `Ctrl+N` - Nowa gra
- `Ctrl+R` - Odśwież
- `Ctrl+,` - Ustawienia
- `F5` - Odśwież listę

## 🐛 Problemy?

### Aplikacja nie startuje
```bash
# Sprawdź czy masz zainstalowane zależności
pip install -r requirements.txt
```

### Gra nie uruchamia się
- Sprawdź czy ścieżka .exe jest poprawna
- Upewnij się że plik istnieje

### Nie widzę motywów
- Przejdź do Ustawień
- Lista motywów jest na samej górze

## 📊 Przykładowe Dane

Aplikacja startuje z 2 przykładowymi grami:
- **The Witcher 3** (⭐ 9.5) - 21h gry, 75% ukończenia
- **Hades** (⭐ 9.0) - 9h gry, 60% ukończenia

Możesz je edytować lub usunąć!

## 🎨 Kolory Motywów

| Motyw | Główny | Akcent | Vibe |
|-------|--------|--------|------|
| **Midnight** | Granatowy | Niebieski | Professional, spokojny |
| **Emerald** | Zielony | Jasna zieleń | Fresh, energetyczny |
| **Sunset** | Fioletowo-różowy | Różowy | Warm, artystyczny |

---

**Wesołej zabawy z Game Launcher 2.0!** 🎮✨

Masz pytania? Sprawdź:
- `README.md` - szczegóły techniczne
- `README_REFACTOR.md` - architektura
- `VISUAL_IMPROVEMENTS.md` - lista zmian wizualnych
