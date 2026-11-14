# Changelog

## v1.5.0 (w przygotowaniu)

### Bezpieczeństwo
- Brak sekretów w repozytorium: `.gitignore` obejmuje `local_settings.json`, `config.json`, `chat.db`, zapisy gier i pliki audio; usunięto zacommitowane `__pycache__`.
- Sekrety (GitHub, RAWG, Last.fm, token pilota) można podać przez zmienne `GL_*`; nie są wtedy zapisywane na dysk.
- Ustawienia lokalne nie są już logowane w całości (tokeny i hasła trafiały do logu).
- Serwer czatu: losowy `SECRET_KEY` zapisywany w `data/chat`, brak domyślnego hasła admina.
- Pilot WWW: token, akcje tylko przez POST, domyślnie nasłuch na `127.0.0.1`, osobny port 5050 (czat zostaje na 5000).

### Poprawki
- Gry uruchamiają się z katalogiem roboczym = folder gry (emulator: folder emulatora).
- 18 zastępczych komunikatów „...” zastąpionych prawdziwymi komunikatami po polsku.
- Dane (`data/`) są szukane obok programu, a nie w bieżącym katalogu – uruchomienie ze skrótu z innym „Rozpocznij w” nie tworzy już pustej biblioteki. Obsługa PyInstallera (`frozen`).
- Przenośne ścieżki gier: na dysku launchera zapisywane bez litery dysku i automatycznie przemapowywane po zmianie litery (pendrive).
- Dodano brakujące zależności `feedparser` i `tkhtmlview`.
- Przywrócono `icon.ico`; wersja w kodzie ujednolicona do 1.5.0.

### Wydajność
- Ikony 16 px zmniejszone z 1024×1024 (15,7 MB → 9 KB); ładowanie ikon 447 ms → ~35 ms, pierwsza klatka okna ~1,6 s → ~0,9 s.

### Interfejs
- Okno błędu i log `data/logs/game_launcher.log` dla nieobsłużonych wyjątków.
- Komunikat pustej biblioteki / braku wyników wyszukiwania.
- Oznaczenie gier, których plik nie istnieje.
- Czytelna informacja, gdy brakuje pakietów zakładki Newsy.

### Inne
- Testy pytest (62) i GitHub Actions (windows-latest, Python 3.12/3.13).
- `game_launcher.spec` (PyInstaller onedir), `docs/ROADMAP.md`, README z instrukcją konfiguracji i budowania.
