# Changelog

## v2.0.0 (2026-11-15) – wersja Go

Launcher przepisany w Go + WebView2 (folder `go/`); wersja Python nie jest dalej rozwijana.

### Nowe
- Menedżer modów: magazyn poza grą, instalacja z `.zip`/`.7z`/folderu/pliku z podglądem, wdrażanie dowiązaniami lub kopiami z kopią oryginałów i dziennikiem transakcji, odzyskiwanie po awarii, „Przywróć vanilla”, konflikty per plik, profile, pliki kolejności ładowania, 15 gier + „Dowolna gra”, wykrywanie aktualizacji gry, gry ze Steam (`docs/MOD_MANAGER.md`).
- Jeden plik exe (~16 MB), start okna ~60 ms, profil WebView2 obok danych (pendrive).
- Czat po WebSockecie (serwer w launcherze i `glchat.exe`), kopia na GitHub tylko do prywatnego repozytorium, aktualizator z obowiązkowym SHA-256, sekrety szyfrowane DPAPI.

### Zgodność z 1.5.0
- `config.json`, `local_settings.json`, zapisy gier czytane bez konwersji; format zapisu zachowany. Zmiany: sekrety → DPAPI, nowy schemat `chat.db` (stara baza podnoszona), `mods_data` tylko do odczytu, Google Drive usunięty. Szczegóły w README.

### Poprawki względem portu
- Pakiet `go/internal/saves` był ignorowany przez `.gitignore` (czysty klon się nie budował).
- Zasób wersji exe podawał licencję MIT zamiast GPL-3.0.
- Zależności: x/crypto 0.59.0, klauspost/compress 1.20.2, brotli 1.2.7 (govulncheck bez znalezisk).

### Poprawki po niezależnym QA menedżera modów (16 błędów, każdy z testem regresyjnym)
- Wdrożenie nie włącza już pluginów wyłączonych przez użytkownika w `plugins.txt` (także po zmianie w zewnętrznym narzędziu); purge przywraca oryginalny `plugins.txt` mimo zewnętrznych edycji.
- Configi (`*.cfg`, `*.ini`, `*.json`…) i pliki kolejności są wdrażane jako zapisywalne kopie: zmiany gry są zachowywane, purge nadal wraca do vanilla.
- Zapis „w miejscu” przez dowiązanie twarde nie zostawia już pliku moda w grze po purge.
- Dwie instalacje tej samej gry nie mogą wdrażać do wspólnego pliku w Dokumentach/AppData; gra nie może leżeć w folderze launchera ani w folderze innej zarządzanej gry; brak wdrażania przez junction/symlink.
- Uszkodzone archiwum z nazwą `.zip`/`.7z` jest odrzucane (zamiast instalacji jako „luźny plik”); nazwy w kodowaniu OEM (CP852, Eksplorator Windows) są dekodowane; bomba ZIP zatrzymywana w trakcie rozpakowania; nazwy `COM¹`–`LPT³` odrzucane.
- Nieudane odinstalowanie (gra uruchomiona) nie zmienia profili; prośba o zgodę na nadpisanie chronionych plików dociera do interfejsu także przy automatycznym wdrożeniu; plugin z nazwą spoza Windows-1252 jest pomijany z ostrzeżeniem zamiast blokować wdrożenie; usunięcie gry nie zostawia pustych folderów.

## v1.5.0 (2026-11-14)

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
