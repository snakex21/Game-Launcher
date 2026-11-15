# Game Launcher – Go + WebView2

[Polski](#polski) · [English](#english)

---

## Polski

Game Launcher 2.0 – wersja w Go + WebView2 (główny opis: README.md w katalogu głównym repozytorium). Jeden plik
`GameLauncher.exe` (~13 MB), interfejs HTML/CSS/JS osadzony w exe, ciemny motyw,
obsługa klawiatury i pada. **Czyta dane wersji Pythona bez konwersji**, więc exe
można położyć obok `game_launcher.py` w tym samym folderze.

Kod Go jest w folderze `go/` repozytorium (kod Pythona usunięty z `main`, dostępny pod tagiem `python-final`).

### Uruchamianie

1. Skopiuj `GameLauncher.exe` do folderu launchera (tego, w którym jest `data\`,
   `images\`, `internal_music\`). Bez danych launcher startuje z pustą biblioteką.
2. Wymagany jest Microsoft Edge WebView2 Runtime (w Windows 10/11 zwykle jest).
3. Opcje: `-app-dir <folder>` (inny folder danych), `-debug` (narzędzia deweloperskie WebView2).

### Dane i zgodność

| Plik / folder | Co robi wersja Go |
|---|---|
| `data\config\config.json` | odczyt i zapis w formacie v1.5.0: kolejność kluczy, nieznane pola i zapis liczb zachowane (zapis 1:1 jak `json.dump(indent=4, ensure_ascii=False)`, także CRLF jeśli plik go miał). Przed pierwszym zapisem w sesji powstaje `config.json.bak`; uszkodzony plik jest odkładany jako `.broken-<data>` i nigdy nie jest nadpisywany. |
| `data\config\local_settings.json` | jw.; sekrety (RAWG, Last.fm, GitHub, hasła czatu) są szyfrowane DPAPI i nigdy nie trafiają do UI ani logów. Zmienne `GL_RAWG_API_KEY`, `GL_LASTFM_API_KEY`, `GL_GITHUB_TOKEN`, `GL_REMOTE_TOKEN` mają pierwszeństwo i nie są zapisywane do pliku. |
| `data\games_saves\<gra>\saves\Save_N%_RRRRMMDD_GGMMSS`, `_autosave` | ten sam układ kopii zapisów. |
| `data\chat\chat.db` | baza serwera czatu; tworzona dopiero przy włączeniu serwera czatu, uszkodzona nigdy nie jest nadpisywana (patrz „Zmiany formatu danych”). |
| `images\`, `internal_music\`, `data\config\achievements_def.json` | używane bez zmian. |
| `data\go_cache\thumbs` | nowe: miniatury okładek (JPEG). |
| `data\webview2` | nowe: profil WebView2 (patrz Przenośność). |
| `data\logs\go_launcher.log` | nowe: log. |

Test migracji na kopii danych użytkownika: `GL_TEST_USERDATA=<kopia folderu> go test ./internal/ojson ./internal/store ./internal/saves`
(nigdy na oryginale – testy kopiują pliki do katalogu tymczasowego).

### Przenośność (pendrive)

* Folder aplikacji = folder exe (nie zależy od bieżącego katalogu).
* Ścieżki gier na dysku launchera są zapisywane bez litery dysku (`\Gry\Gothic\Gothic.exe`),
  a gry w folderze launchera – względnie (`Gry\DSJ4\DSJ4.exe`). Po zmianie litery (E: → F:)
  wczytują się z nową literą; stare ścieżki bezwzględne z poprzednią literą launchera
  (`settings.launcher_drive`) są przemapowywane. Test: `internal/paths`, `internal/store`
  (`TestRoundTripAfterDriveLetterChange`, `TestDriveLetterChangeThroughStore`).
* Brakujący plik gry jest oznaczany w bibliotece; „Ustawienia → Przenieś ścieżki” zamienia
  prefiks (np. `E:\Gry` → `F:\Gry`) we wszystkich grach i emulatorach.
* **Profil WebView2 leży w `data\webview2`**, nie w `%APPDATA%`. `webview_go` ma ten folder
  zakodowany na sztywno; `third_party/webview_go` to lokalna kopia z łatką, która czyta
  `WEBVIEW_GO_USER_DATA_FOLDER` (exe ustawia ją przed utworzeniem okna).

### Funkcje

Biblioteka (kafelki i lista, wyszukiwanie, grupy, filtry zaawansowane, gatunek, tag, typ,
sortowanie), dodawanie/edycja gier (edycja **nie gubi** checklisty, screenshotów, danych RAWG
ani statystyk; zmiana nazwy przenosi grupy, roadmapę i kopie zapisów), profile uruchamiania,
skanowanie folderów z oknem weryfikacji, uruchamianie z katalogiem roboczym = folder gry,
emulatory (`emulator [argumenty] ROM` w folderze emulatora), wykrywanie i zamykanie gier,
czas gry i sesje (także gier uruchomionych poza launcherem), automatyczna kopia zapisów po
wyjściu z gry, menedżer kopii zapisów (z kopią bezpieczeństwa przed wczytaniem), RAWG (opis,
wymagania, okładka), okładki własne, statystyki z dowolnym zakresem dat, roadmapa z
automatycznym statusem „Nie ukończona na czas”, archiwum, przypomnienia, osiągnięcia (te same
reguły co w Pythonie), muzyka (playlisty, losowo, powtarzanie, głośność, Stop), pilot WWW,
czat, ustawienia – pełna lista niżej.

Pilot WWW: osobny port (domyślnie 5050, nigdy 5000 = czat), token (nagłówek, `?token=` przy
pierwszym wejściu → ciasteczko HttpOnly SameSite=Strict), akcje tylko POST, POST z obcego
Origin odrzucany, domyślnie tylko 127.0.0.1 (LAN po włączeniu opcji).

Sterowanie: strzałki / Home / End / PgUp / PgDn – siatka, Enter – szczegóły, Ctrl+Enter lub
P – uruchom, Ctrl+F lub / – szukaj, Esc – zamknij, Ctrl+1…8 – zakładki, Alt+Spacja /
Alt+←/→ / Alt+S / Alt+↑/↓ – muzyka. Pad: D-pad/gałka – ruch, A – otwórz, B – wstecz,
X – uruchom/zamknij grę, Y – szukaj, LB/RB – zakładki.

### Budowanie i testy

Wymagania: Go 1.26 (toolchain 1.26.11 pobierany automatycznie), MinGW-w64 `gcc` (CGO dla webview_go).

```bat
cd go
build.bat 0.1.0                         :: -> build\GameLauncher.exe (-s -w -trimpath -H windowsgui)
go test -race ./...
go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 ./...
```

CI: `.github/workflows/go-ci.yml` (windows-latest: gofmt, node --check UI, vet, test -race,
govulncheck, build, artefakt exe).

### Pomiary (Windows 10, kopia danych użytkownika: 17 gier, okładki 1–3 MB)

Mierzone z zewnątrz tym samym skryptem, 5 uruchomień, mediana.

| | Python v1.5.0 (źródła) | Go + WebView2 |
|---|---|---|
| Okno widoczne od startu procesu | 520 ms | **61 ms** |
| Biblioteka wyrenderowana (z okładkami ładowanymi leniwie) | ~980 ms (pierwsza klatka, pomiar z FEATURES.md) | **573 ms** |
| RAM po 6 s – proces aplikacji (working set) | 106 MB | **29 MB** |
| RAM po 6 s – całe drzewo procesów (WS / private) | 106 / 562 MB | 378 / 337 MB (7 procesów: exe + WebView2) |
| Rozmiar | źródła + Python; onedir PyInstaller ~288 MB | **jeden exe 13 MB** (+ WebView2 Runtime z systemu) |

Uwagi: WebView2 (Edge) uruchamia własne procesy (przeglądarka, GPU, sieć, renderer), stąd
większa suma working set całego drzewa (współdzielone strony są tam liczone wielokrotnie).
Pierwszy start generuje miniatury okładek (~1 s jednorazowo); kolejne starty korzystają z cache.

### Lista zgodności z wersją Python

| Obszar | Stan |
|---|---|
| Biblioteka: kafelki/lista (przełącznik widoczny), wyszukiwanie, grupy, gatunki, tagi, typ, sortowanie | ✅ |
| Filtry zaawansowane (zapisane filtry z Pythona działają, także reguły na listach) | ✅ |
| Dodawanie/edycja gry bez utraty pól, zmiana nazwy, profile, emulatory | ✅ |
| Skanowanie folderów z oknem weryfikacji | ✅ |
| Uruchamianie (cwd = folder gry), emulatory, zamykanie, czas gry i sesje, autozapis | ✅ |
| Menedżer kopii zapisów, RAWG, okładki, screenshoty (ręczne + skanowanie wzorców) | ✅ |
| Statystyki (dowolny zakres dat), roadmapa z monitorem terminów, przypomnienia (+ powiadomienie systemowe) | ✅ |
| Osiągnięcia (te same reguły) + edytor definicji | ✅ |
| Muzyka: playlisty, losowo/powtarzanie, Stop, okładki Last.fm | ✅ |
| Czat: serwer + klient (WebSocket, bcrypt, tokeny sesji, limity, pokoje z hasłem, `join_specific_room`, DM, blokowanie, emoji, pliki) | ✅ |
| Pilot WWW (token, POST, localhost) | ✅ |
| Kopia w chmurze GitHub (zawsze prywatne repo, wysyłanie różnicowe) | ✅ |
| Aktualizator (semver, wzorzec pliku, SHA-256, podmiana z wycofaniem) | ✅ |
| Zasobnik, globalne skróty, powiadomienia, autostart (ścieżka w cudzysłowie), Discord RPC | ✅ |
| Newsy RSS/Atom, duplikaty, edytor motywów, pełna kopia .zip, ikona i wersja w exe | ✅ |
| Nawigacja strzałkami i padem (X ≠ Y) | ✅ |
| Menedżer modów (nowy: magazyn, profile, konflikty, wdrożenie z dziennikiem i powrotem do vanilla, 15 gier + „Dowolna gra”) | ✅ `internal/modmgr`, opis: `docs/MOD_MANAGER.md`; stare `mods_data` tylko do odczytu |
| Google Drive | ✖ świadomie pominięty (w Pythonie nie działał) |
| Wielojęzyczność | ✖ UI tylko po polsku (jak w Pythonie po wyłączeniu tłumaczeń) |

### Zmiany formatu danych (względem wersji Python)

* `local_settings.json`: klucze API, token GitHub, token pilota i hasła serwerów czatu są
  szyfrowane **DPAPI** (`"dpapi:<base64>"`), przy pierwszym uruchomieniu wersji Go. Wersja
  Python nie odczyta już tych wartości; na innym komputerze/koncie Windows trzeba je wpisać ponownie.
* Nowe klucze `local_settings.json`: `global_hotkeys_enabled`, `launcher_hotkey`,
  `chat_host_server`, `chat_host_port`, `chat_host_lan`, `github_backup_repo`, `github_last_backup`.
* `data/chat/chat.db`: nowa baza czatu (tworzona dopiero przy włączeniu serwera czatu). Nazwy
  tabel jak w modelach SQLAlchemy + tabela `session` i kolumna `message.is_deleted`; stara, poprawna
  baza Pythona jest podnoszona (konta ze starymi hasłami logują się i dostają hash bcrypt).
  Uszkodzona baza nie jest nadpisywana.
* Autostart: wpis w rejestrze jest źródłem prawdy, `settings.autostart` jest tylko kopią.

Czat działa po zwykłym WebSockecie (bez Socket.IO): klient Pythona nie połączy się z nowym
serwerem. Serwer można uruchomić w launcherze (Czat → Własny serwer czatu) albo osobno: `glchat.exe -addr 0.0.0.0:5000`.

---

## English

A port of Game Launcher from Python/Tkinter to Go + WebView2: a single
`GameLauncher.exe` (~13 MB) with the HTML/CSS/JS UI embedded, dark theme, keyboard and
gamepad navigation, Polish UI. It **reads the Python version's data unchanged**, so the exe
can sit next to `game_launcher.py` in the same folder. The Go code lives in `go/`.

* Run: put `GameLauncher.exe` into the launcher folder (with `data\`, `images\`, …).
  Needs the Microsoft Edge WebView2 Runtime. Flags: `-app-dir <folder>`, `-debug`.
* Data: `config.json` / `local_settings.json` are rewritten byte-compatibly with Python's
  `json.dump(indent=4, ensure_ascii=False)` (key order, unknown keys, number text and line
  endings preserved; `.bak` before the first save, broken files are set aside). Secrets never
  reach the UI or logs; `GL_*` environment variables override them and are never written.
  The chat database is created only when the chat server is enabled. Save backups keep the Python layout.
* Portability: the app folder is the exe folder; game paths on the launcher drive are stored
  without the drive letter and re-resolved after a drive letter change (tested); the WebView2
  profile is kept in `data\webview2` via a patched `webview_go` (`WEBVIEW_GO_USER_DATA_FOLDER`).
* Build: `go\build.bat` (CGO + MinGW-w64, `-s -w -trimpath -H windowsgui`); tests:
  `go test -race ./...`; `govulncheck` is clean with toolchain go1.26.11; CI in
  `.github/workflows/go-ci.yml`.
* Measurements (same machine, same data copy, median of 5): window shown in 61 ms (Python
  520 ms), library rendered in 573 ms, app process 29 MB working set (Python 106 MB); the whole
  tree including WebView2 is 378 MB WS / 337 MB private; single 13 MB exe vs ~288 MB
  PyInstaller onedir.
* Phase 2 added: chat server + client (plain WebSocket, bcrypt, session tokens, rate limits,
  rooms incl. `join_specific_room`, DMs, blocking, emoji, uploads with size/type limits), GitHub
  backup (always private repos, diff-based), updater (semver, asset pattern, mandatory SHA-256,
  self-replace with rollback), tray, global hotkeys (opt-in), notifications, autostart with a
  quoted path, Discord RPC, RSS news, duplicate finder, theme editor, achievement definition
  editor, full zip backup/restore, screenshot scanning, Last.fm covers, exe icon + version info.
* Data format changes: secrets in `local_settings.json` are DPAPI-encrypted (`dpapi:<base64>`);
  new chat database schema (compatible table names, plus `session`); see the Polish section.
* Mod manager (2.0.0): store outside the game, profiles, per-file conflicts, journaled deployment with backups and purge to vanilla, crash recovery, load order files; 15 game definitions + a generic one (`internal/modmgr`, `docs/MOD_MANAGER.md`). Google Drive is dropped.
