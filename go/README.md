# Game Launcher – Go + WebView2

[Polski](#polski) · [English](#english)

---

## Polski

Port Game Launchera z Pythona/Tkinter do Go + WebView2. Jeden plik
`GameLauncher.exe` (~13 MB), interfejs HTML/CSS/JS osadzony w exe, ciemny motyw,
obsługa klawiatury i pada. **Czyta dane wersji Pythona bez konwersji**, więc exe
można położyć obok `game_launcher.py` w tym samym folderze.

Kod Go jest w folderze `go/` repozytorium (Python zostaje w katalogu głównym).

### Uruchamianie

1. Skopiuj `GameLauncher.exe` do folderu launchera (tego, w którym jest `data\`,
   `images\`, `internal_music\`). Bez danych launcher startuje z pustą biblioteką.
2. Wymagany jest Microsoft Edge WebView2 Runtime (w Windows 10/11 zwykle jest).
3. Opcje: `-app-dir <folder>` (inny folder danych), `-debug` (narzędzia deweloperskie WebView2).

### Dane i zgodność

| Plik / folder | Co robi wersja Go |
|---|---|
| `data\config\config.json` | odczyt i zapis w formacie v1.5.0: kolejność kluczy, nieznane pola i zapis liczb zachowane (zapis 1:1 jak `json.dump(indent=4, ensure_ascii=False)`, także CRLF jeśli plik go miał). Przed pierwszym zapisem w sesji powstaje `config.json.bak`; uszkodzony plik jest odkładany jako `.broken-<data>` i nigdy nie jest nadpisywany. |
| `data\config\local_settings.json` | jw.; sekrety (RAWG, Last.fm, GitHub, hasła czatu) nigdy nie trafiają do UI ani logów. Zmienne `GL_RAWG_API_KEY`, `GL_LASTFM_API_KEY`, `GL_GITHUB_TOKEN`, `GL_REMOTE_TOKEN` mają pierwszeństwo i nie są zapisywane do pliku. |
| `data\games_saves\<gra>\saves\Save_N%_RRRRMMDD_GGMMSS`, `_autosave` | ten sam układ kopii zapisów. |
| `data\chat\chat.db` | tylko odczyt (`mode=ro&immutable=1`), bez plików journal/WAL. |
| `images\`, `internal_music\`, `data\config\achievements_def.json` | używane bez zmian. |
| `data\go_cache\thumbs` | nowe: miniatury okładek (JPEG). |
| `data\webview2` | nowe: profil WebView2 (patrz Przenośność). |
| `data\logs\go_launcher.log` | nowe: log. |

Test migracji na kopii danych użytkownika: `GL_TEST_USERDATA=<kopia folderu> go test ./internal/ojson ./internal/store ./internal/saves ./internal/chatdb`
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
archiwum czatu (tylko odczyt), ustawienia.

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

### Czego jeszcze nie ma (w porównaniu z Pythonem)

* Czat: klient Socket.IO i serwer (`chat_server.py`) – jest tylko podgląd archiwum `chat.db`.
* Kopia w chmurze GitHub, aktualizator (GitHub Releases + SHA256), Discord RPC, ikona w
  zasobniku, globalne skróty klawiszowe (poza oknem), powiadomienia systemowe, autostart.
* Menedżer modów, newsy RSS, wyszukiwanie duplikatów, edytor motywów, edytor definicji
  osiągnięć, kopia/odtwarzanie całego launchera, skanowanie screenshotów, Last.fm (okładki muzyki).
* Google Drive – świadomie **pominięty** (w Pythonie nie działał; patrz FEATURES.md).

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
  `chat.db` is opened read-only. Save backups keep the Python layout.
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
* Not ported yet: chat client/server (archive viewer only), GitHub cloud backup, updater,
  Discord RPC, tray, global hotkeys, system notifications, autostart, mod manager, RSS news,
  duplicates, theme editor, achievement definition editor, full backup/restore, screenshot
  scanning, Last.fm covers. Google Drive is intentionally dropped.
