# 📋 Plan Rozwoju Game Launcher 2.0

## ✅ Już zaimplementowane

- ✅ Biblioteka gier (dodawanie, edycja, uruchamianie)
- ✅ Statystyki (wykresy, czas gry)
- ✅ Roadmapa (planowanie gier)
- ✅ Mody (zarządzanie modami)
- ✅ Osiągnięcia (z automatycznym śledzeniem i paskami postępu)
- ✅ Newsy (RSS)
- ✅ Przypomnienia (alerty)
- ✅ Odtwarzacz muzyki (z seekiem i mini kontrolką)
- ✅ Profil użytkownika (avatar, bio, backup)
- ✅ Ustawienia (motywy, kolory)

---

## 🚀 Do zrobienia (priorytet)

### 1. 📸 Manager Zrzutów Ekranu
**Priorytet: Wysoki**

Ze starego launchera:
- Auto-scan folderów ze screenshotami
- Wzorce nazw plików (np. "screenshot_*.png")
- Ignorowanie folderów (cache, temp, thumbnails)
- Ręczne dodawanie screenshotów
- Przypisywanie do gier
- Galeria zdjęć

**Plan implementacji:**
- [ ] Serwis `ScreenshotService` z metodami scan/add/delete
- [ ] Plugin `ScreenshotsPlugin` z widokiem galerii
- [ ] Konfiguracja folderów w ustawieniach
- [ ] Integracja z kartami gier (przycisk "Zobacz screenshoty")

---

### 2. 🎮 Obsługa Emulatorów
**Priorytet: Średni**

Ze starego launchera:
- Definicje emulatorów (nazwa, ścieżka do exe, argumenty)
- Gry emulowane (przypisane do emulatora)
- Uruchamianie: `emulator.exe rom_path`

**Plan implementacji:**
- [ ] Model `Emulator` (nazwa, exe_path, arguments, system)
- [ ] Rozszerzenie `Game` o pole `emulator_id`
- [ ] Serwis `EmulatorService`
- [ ] UI do zarządzania emulatorami w ustawieniach
- [ ] Wybór emulatora przy dodawaniu gry

---

### 3. 🎮 Obsługa Kontrolera (Gamepad)
**Priorytet: Średni**

Ze starego launchera:
- Biblioteka `inputs` do czytania gamepad
- Listener w tle (`controller_listener`)
- Mapowanie przycisków do akcji

**Plan implementacji:**
- [ ] Serwis `ControllerService` z listenerem
- [ ] Konfiguracja mapowania w ustawieniach
- [ ] Akcje: nawigacja w menu, play/pause muzyki, uruchom grę
- [ ] Wskaźnik stanu kontrolera w UI

---

### 4. 🖥️ Minimalizacja do Tray
**Priorytet: Niski**

Ze starego launchera:
- Biblioteka `pystray`
- Ikona w zasobniku systemowym
- Menu kontekstowe (Pokaż, Ukryj, Zamknij)
- Minimalizacja przy zamknięciu okna

**Plan implementacji:**
- [ ] Serwis `TrayService` z `pystray`
- [ ] Ustawienie "Minimalizuj do tray przy zamknięciu"
- [ ] Menu tray: Pokaż/Ukryj, Odtwarzacz, Wyjście
- [ ] Powiadomienia z tray

---

### 5. 👁️ Overlay Podczas Gry
**Priorytet: Średni-Niski**

Ze starego launchera:
- `TrackOverlayWindow` - okno overlay z informacją o muzyce
- Zawsze na wierzchu, podczas gry
- Pokazuje: nazwa utworu, czas, przyciski kontroli

**Plan implementacji:**
- [ ] Oddzielne okno `MusicOverlay` (zawsze na wierzchu)
- [ ] Ustawienie włącz/wyłącz overlay
- [ ] Pozycja i rozmiar do zapisania
- [ ] Przezroczystość, możliwość przeciągania
- [ ] Hotkey do pokazania/ukrycia

---

### 6. ☁️ Synchronizacja z Chmurą
**Priorytet: Niski**

Funkcje:
- Google Drive API
- GitHub Gist jako backup
- Auto-sync co X minut
- Wybór co synchronizować (gry, osiągnięcia, ustawienia)

**Plan implementacji:**
- [ ] Rozszerzenie `CloudService` o Google Drive
- [ ] Rozszerzenie `CloudService` o GitHub Gist
- [ ] UI do konfiguracji OAuth
- [ ] Auto-sync w tle
- [ ] Rozwiązywanie konfliktów

---

### 7. 💬 Chat (HTTP/Socket.IO)
**Priorytet: Niski**

Ze starego launchera:
- Klient HTTP/Socket.IO
- Czat 1-on-1
- Pokoje czatowe
- Lista użytkowników online

**Plan implementacji:**
- [ ] Serwis `ChatService` z Socket.IO
- [ ] Plugin `ChatPlugin` z UI
- [ ] Konfiguracja serwera w ustawieniach
- [ ] Powiadomienia o wiadomościach
- [ ] Historia czatu

---

## 📝 Kolejne kroki

### Najbliższe zadania:
1. **📸 Screenshots** - najłatwiejsze i najbardziej przydatne
2. **🎮 Emulatory** - rozszerzy funkcjonalność biblioteki
3. **🎮 Controller** - fajny dodatek dla graczy

### Po nich:
4. **🖥️ Tray** - wygoda użytkowania
5. **👁️ Overlay** - dla fanów muzyki podczas gry
6. **☁️ Cloud** - zaawansowane
7. **💬 Chat** - wymaga serwera

---

## 🎯 Priorytety użytkownika

**Użytkownik poprosił o:**
> "pododawaj podobne mechaniki osiągnięć jak w starym launcherze"
> "kontynułujmy dodawanie rzeczy do launchera"
> "dodaj brakujące funkcje są one zapisane tutaj NOWE_FUNKCJE.md"

**Strategia:**
- Zaczynamy od **screenshots** - najprostsze i najbardziej visual
- Potem **emulatory** - rozszerzy bibliotekę o retro gry
- Na końcu rzeczy wymagające więcej pracy (chat, overlay, cloud)

---

**Status:** 📸 Zaczynamy od Managera Zrzutów Ekranu!
