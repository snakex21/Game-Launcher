# 🎮 Game Launcher

[English](#english) | [Polski](#polski)

---

<a name="english"></a>
## 🇬🇧 English

### Overview
A comprehensive game launcher designed for managing cracked, old, and DRM-free games. Perfect for organizing your personal game collection with advanced features like playtime tracking, achievements, integrated music player, and social chat.

### ✨ Key Features

#### 🎯 Game Management
- **Library Organization**: Grid and list views with search, filters, and custom groups
- **Multiple Profiles**: Different mod configurations per game
- **Emulator Support**: Configure and launch games through emulators (DOSBox, RetroArch, etc.)
- **Smart Scanning**: Automatic game detection from folders
- **Playtime Tracking**: Detailed statistics and session history
- **Completion Tracking**: Track your progress percentage per game
- **Custom Covers**: Manual upload or automatic fetch from RAWG API
- **Tags & Genres**: Organize with custom tags and genre categories

#### 💾 Save Management
- **Manual & Auto Saves**: Create backups manually or automatically
- **Version Control**: Multiple save states with timestamps
- **Easy Restore**: One-click save restoration
- **Cloud Backup**: Sync saves to GitHub or Google Drive

#### 🎨 Mod Manager
- **Multiple Profiles**: Switch between different mod setups
- **Load Order**: Manage mod priority
- **Easy Installation**: Install from folder or ZIP
- **Safe Uninstall**: Automatic backup before mod changes

#### 📊 Statistics & Analytics
- **Playtime Charts**: Visual graphs of your gaming habits
- **Period Analysis**: Daily, weekly, monthly, yearly stats
- **Most Played**: Rankings and detailed breakdowns
- **Session Tracking**: Monitor individual gaming sessions

#### 🎵 Music Player
- **Full-Featured Player**: Play music while gaming
- **Playlists**: Create and manage multiple playlists
- **Global Hotkeys**: Control music from any game
- **Track Overlay**: Always-on-top display of current track
- **Album Covers**: Automatic cover art from Last.fm
- **Multiple Sources**: Internal library + external folders

#### 💬 Social Features
- **Real-time Chat**: Socket.IO based messaging
- **Private & Group Chat**: 1-on-1 conversations and chat rooms
- **File Sharing**: Send images and files
- **Rich Features**: Emojis, replies, message editing, read receipts
- **Multiple Servers**: Connect to different chat servers
- **User Management**: Blocking, profiles, online status

#### 🏆 Achievements System
- **Custom Achievements**: Define your own goals
- **Progress Tracking**: Monitor achievement progress
- **Multiple Types**: Playtime, completion, library size, and more
- **Notifications**: Get notified when unlocking achievements

#### 🗓️ Roadmap & Planning
- **Game Backlog**: Plan which games to play
- **Calendar View**: Visualize your gaming schedule
- **Archive**: Track completed games with dates
- **Time Estimates**: Plan your gaming time

#### 🎨 Customization
- **Themes**: Multiple built-in themes + custom theme creator
- **Fonts**: Choose your preferred font
- **Background Images**: Personalize with custom backgrounds
- **Big Picture Mode**: Gamepad-optimized interface

#### 🌐 Remote Control
- **Web Interface**: Control launcher from phone/tablet
- **Launch Games Remotely**: Start games from anywhere on your network
- **Mobile-Friendly**: Responsive web UI

### 📋 Requirements

- **OS**: Windows 10/11
- **Python**: 3.12 or 3.13 (tested on 3.13.7; CI runs 3.12 and 3.13)
- **Dependencies**: see `requirements.txt` (dev tools: `requirements-dev.txt`)

### 🚀 Installation (from source)

```bat
git clone https://github.com/snakex21/Game-Launcher.git
cd Game-Launcher
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python game_launcher.py
```

On the first start the launcher creates `data\config\config.json` and `data\config\local_settings.json` **next to the program** (not in the current working directory), asks for a username and shows an empty library. You can also start from the templates:

```bat
mkdir data\config
copy config.example.json data\config\config.json
copy local_settings.example.json data\config\local_settings.json
```

### 🔐 Configuration and secrets

- No keys or tokens live in the repository. `data\` (config, `local_settings.json`, `chat.db`, saves), `images\`, `internal_music\` and all `*.mp3` files are ignored by git.
- API keys are entered in **Settings → API keys** and stored only in `data\config\local_settings.json`. Alternatively set environment variables (they win over the file and are never written to it):

| Variable | Used for |
|---|---|
| `GL_GITHUB_TOKEN` | GitHub cloud sync |
| `GL_RAWG_API_KEY` | covers/metadata from RAWG |
| `GL_LASTFM_API_KEY` | album covers in the music player |
| `GL_REMOTE_TOKEN` | fixed token for the web remote |
| `GL_CHAT_SECRET_KEY`, `FLASK_ADMIN_USER`, `FLASK_ADMIN_PASS` | chat server (`chat_server.py`); without `FLASK_ADMIN_PASS` the admin panel is disabled |
| `GL_CHAT_PORT`, `GL_CHAT_HOST` | chat server port/host (default `127.0.0.1:5000`) |

- Logs: `data\logs\game_launcher.log` (secrets are redacted).

### 💽 Portable use (USB drive, changing drive letters)

- Game, ROM, save and emulator paths **on the same drive as the launcher** are stored without the drive letter (`\Games\Gothic\Gothic.exe`); games inside the launcher folder are stored relative to it. When the drive gets a different letter (E: → F:), the paths are resolved for the new letter automatically.
- Old configs with absolute paths are remapped as soon as the launcher has recorded its drive once (`settings.launcher_drive`).
- When an `.exe`/ROM is missing, the launcher also tries the same path on the launcher's drive; tiles of games whose file cannot be found are marked **"⚠ Brak pliku gry"**.
- Games are started with the working directory set to the game's folder (emulated games: the emulator's folder).

### 📦 Building the .exe (PyInstaller)

```bat
pip install -r requirements-dev.txt
pyinstaller --noconfirm game_launcher.spec
```

The result is `dist\GameLauncher\GameLauncher.exe` (one-folder build: faster start, data folder created next to the exe). Copy the whole `dist\GameLauncher` folder. The build contains only icons, `icon.ico` and the `*.example.json` templates – never your `data\` or music.

### 🧪 Tests

```bat
pip install -r requirements-dev.txt
python -m pytest
```

Tests cover path resolution/portability, config loading (defaults, env secrets, port migration), launch command building and web-remote authentication. GitHub Actions runs them on `windows-latest` (`.github/workflows/ci.yml`).

### 📦 Dependencies

Main libraries used:
- `tkinter` - GUI framework
- `Pillow` - Image processing
- `pygame` - Music player
- `socketio` - Real-time chat
- `matplotlib` - Statistics charts
- `psutil` - Process monitoring
- `requests` - API calls
- `mutagen` - Music metadata

### 🎮 Usage

#### First Launch
1. Set your username
2. Choose to scan folders or add games manually
3. Configure your preferences in Settings

#### Adding Games
- **Manual**: Library → Add Game → Fill in details
- **Emulated Games**: Configure emulator first, then add ROM

#### Chat Setup
1. Start the server: `python chat_server.py` (port 5000, see `GL_CHAT_PORT`)
2. Go to Chat page and add the server (default: `http://127.0.0.1:5000`)
3. Register or login
4. Start chatting!

#### Music Player
1. Go to Music page
2. Add music folder or files
3. Create playlists
4. Configure global hotkeys in Settings

### ⚙️ Configuration

#### Data Layout

Application data is separated from source code:

- `data/config/config.json` - main app config
- `data/config/local_settings.json` - local/private settings
- `data/config/achievements_def.json` - achievement definitions
- `data/games_saves/` - game save data
- `data/chat/chat.db` - chat SQLite database
- `data/chat/uploads/` - uploaded chat files
- `custom_themes/` - custom themes
- `external/ScriptHookConfig.ini` - external integration config

#### Compatibility and Migration

The app keeps backward compatibility with old locations:

- `config.json`, `local_settings.json`, `achievements_def.json`
- `games_saves/`
- `chat.db`
- `chat_uploads/` and `uploads/`

On startup, data is migrated to the new structure when needed.

### 🔧 Advanced Features

#### Web remote
Enable in Settings → Remote control. The page shows the full address **with a token**
(e.g. `http://127.0.0.1:5050/?token=...`). Without the token every request gets HTTP 401;
games are started/closed only with POST requests.
- Default port **5050** (the chat server uses 5000), listening only on `127.0.0.1`.
- To use a phone on the same Wi-Fi, tick "Available on the local network" (binds `0.0.0.0`).
- "New token" invalidates old links.

#### Discord Rich Presence
Enable in Settings → Discord Integration
Shows what game you're playing on Discord

#### Global Hotkeys
Configure in Settings → Music Hotkeys
Control music player from any application

#### Cloud Sync
- **GitHub**: Settings → Cloud → Configure GitHub token
- **Google Drive**: not implemented yet (see `docs/ROADMAP.md`)

### ⚠️ Known limitations

- Google Drive sync is not implemented (only GitHub works).
- Interface translations are disabled (Polish UI only).
- Folder scanning for games exists in code (`launcher/scan_pipeline.py`) but has no menu entry yet.
- Moving games to another drive letter that is *not* the launcher's drive still requires editing the game paths.
- See `docs/ROADMAP.md` for planned features.

### 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

### 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

This means:
- ✅ You can use, modify, and distribute this software freely
- ✅ You can use it for commercial purposes
- ⚠️ **Any modifications or derivative works MUST also be open source under GPL-3.0**
- ⚠️ You must include the original license and copyright notice
- ⚠️ You must state any changes made to the code

**This ensures the project and all its derivatives remain open source forever.**

See the [LICENSE](LICENSE) file for full details or visit https://www.gnu.org/licenses/gpl-3.0.html

### ⚠️ Disclaimer

This launcher is designed for managing personal game collections. Users are responsible for ensuring they have legal rights to any games they add to the launcher.

---

<a name="polski"></a>
## 🇵🇱 Polski

### Opis
Kompleksowy launcher do zarządzania crackedowymi, starymi i grami bez DRM. Idealny do organizacji osobistej kolekcji gier z zaawansowanymi funkcjami jak śledzenie czasu gry, osiągnięcia, zintegrowany odtwarzacz muzyki i czat społecznościowy.

### ✨ Główne Funkcje

#### 🎯 Zarządzanie Grami
- **Organizacja Biblioteki**: Widok siatki i listy z wyszukiwaniem, filtrami i własnymi grupami
- **Wiele Profili**: Różne konfiguracje modów na grę
- **Wsparcie Emulatorów**: Konfiguruj i uruchamiaj gry przez emulatory (DOSBox, RetroArch, itp.)
- **Inteligentne Skanowanie**: Automatyczne wykrywanie gier z folderów
- **Śledzenie Czasu Gry**: Szczegółowe statystyki i historia sesji
- **Śledzenie Ukończenia**: Śledź procent postępu w każdej grze
- **Własne Okładki**: Ręczne dodawanie lub automatyczne pobieranie z RAWG API
- **Tagi i Gatunki**: Organizuj za pomocą własnych tagów i kategorii gatunków

#### 💾 Zarządzanie Zapisami
- **Zapisy Ręczne i Auto**: Twórz kopie zapasowe ręcznie lub automatycznie
- **Kontrola Wersji**: Wiele stanów zapisu z datami
- **Łatwe Przywracanie**: Przywracanie zapisu jednym kliknięciem
- **Backup w Chmurze**: Synchronizuj zapisy do GitHub lub Google Drive

#### 🎨 Menedżer Modów
- **Wiele Profili**: Przełączaj się między różnymi setupami modów
- **Kolejność Ładowania**: Zarządzaj priorytetem modów
- **Łatwa Instalacja**: Instaluj z folderu lub ZIP
- **Bezpieczna Deinstalacja**: Automatyczny backup przed zmianami modów

#### 📊 Statystyki i Analityka
- **Wykresy Czasu Gry**: Wizualne grafy twoich nawyków gamingowych
- **Analiza Okresów**: Statystyki dzienne, tygodniowe, miesięczne, roczne
- **Najczęściej Grane**: Rankingi i szczegółowe zestawienia
- **Śledzenie Sesji**: Monitoruj pojedyncze sesje grania

#### 🎵 Odtwarzacz Muzyki
- **Pełnofunkcyjny Odtwarzacz**: Słuchaj muzyki podczas grania
- **Playlisty**: Twórz i zarządzaj wieloma playlistami
- **Globalne Skróty**: Steruj muzyką z dowolnej gry
- **Nakładka Utworu**: Wyświetlanie zawsze na wierzchu aktualnego utworu
- **Okładki Albumów**: Automatyczne okładki z Last.fm
- **Wiele Źródeł**: Wewnętrzna biblioteka + zewnętrzne foldery

#### 💬 Funkcje Społecznościowe
- **Czat w Czasie Rzeczywistym**: Komunikacja oparta na Socket.IO
- **Czat Prywatny i Grupowy**: Rozmowy 1-na-1 i pokoje czatowe
- **Udostępnianie Plików**: Wysyłaj obrazy i pliki
- **Bogate Funkcje**: Emoji, odpowiedzi, edycja wiadomości, potwierdzenia odczytu
- **Wiele Serwerów**: Łącz się z różnymi serwerami czatu
- **Zarządzanie Użytkownikami**: Blokowanie, profile, status online

#### 🏆 System Osiągnięć
- **Własne Osiągnięcia**: Definiuj własne cele
- **Śledzenie Postępu**: Monitoruj postęp osiągnięć
- **Wiele Typów**: Czas gry, ukończenie, rozmiar biblioteki i więcej
- **Powiadomienia**: Otrzymuj powiadomienia przy odblokowywaniu osiągnięć

#### 🗓️ Roadmapa i Planowanie
- **Backlog Gier**: Planuj które gry zagrać
- **Widok Kalendarza**: Wizualizuj swój harmonogram grania
- **Archiwum**: Śledź ukończone gry z datami
- **Szacowanie Czasu**: Planuj swój czas na granie

#### 🎨 Personalizacja
- **Motywy**: Wiele wbudowanych motywów + kreator własnych motywów
- **Czcionki**: Wybierz preferowaną czcionkę
- **Obrazy Tła**: Personalizuj własnymi tłami
- **Tryb Big Picture**: Interfejs zoptymalizowany pod gamepad

#### 🌐 Zdalne Sterowanie
- **Interfejs Webowy**: Steruj launcherem z telefonu/tabletu
- **Zdalne Uruchamianie Gier**: Uruchamiaj gry z dowolnego miejsca w sieci
- **Przyjazny Mobilnie**: Responsywny interfejs webowy

### 📋 Wymagania

- **System**: Windows 10/11
- **Python**: 3.12 lub 3.13 (testowane na 3.13.7; CI sprawdza 3.12 i 3.13)
- **Zależności**: zobacz `requirements.txt` (narzędzia deweloperskie: `requirements-dev.txt`)

### 🚀 Instalacja (ze źródeł)

```bat
git clone https://github.com/snakex21/Game-Launcher.git
cd Game-Launcher
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python game_launcher.py
```

Przy pierwszym starcie launcher tworzy `data\config\config.json` i `data\config\local_settings.json` **obok programu** (nie w bieżącym katalogu), pyta o nazwę użytkownika i pokazuje pustą bibliotekę. Można też zacząć od szablonów:

```bat
mkdir data\config
copy config.example.json data\config\config.json
copy local_settings.example.json data\config\local_settings.json
```

### 🔐 Konfiguracja i sekrety

- W repozytorium nie ma żadnych kluczy ani tokenów. `data\` (config, `local_settings.json`, `chat.db`, zapisy), `images\`, `internal_music\` i wszystkie pliki `*.mp3` są ignorowane przez git.
- Klucze API wpisuje się w **Ustawienia → Klucze API** – trafiają tylko do `data\config\local_settings.json`. Zamiast tego można ustawić zmienne środowiskowe (mają pierwszeństwo przed plikiem i nigdy nie są do niego zapisywane):

| Zmienna | Do czego |
|---|---|
| `GL_GITHUB_TOKEN` | synchronizacja z chmurą GitHub |
| `GL_RAWG_API_KEY` | okładki i metadane z RAWG |
| `GL_LASTFM_API_KEY` | okładki albumów w odtwarzaczu |
| `GL_REMOTE_TOKEN` | stały token pilota WWW |
| `GL_CHAT_SECRET_KEY`, `FLASK_ADMIN_USER`, `FLASK_ADMIN_PASS` | serwer czatu (`chat_server.py`); bez `FLASK_ADMIN_PASS` panel admina jest wyłączony |
| `GL_CHAT_PORT`, `GL_CHAT_HOST` | port/host serwera czatu (domyślnie `127.0.0.1:5000`) |

- Logi: `data\logs\game_launcher.log` (sekrety są w nim zamaskowane).

### 💽 Praca z pendrive'a (zmiana litery dysku)

- Ścieżki gier, ROM-ów, zapisów i emulatorów **na tym samym dysku co launcher** są zapisywane bez litery dysku (`\Gry\Gothic\Gothic.exe`), a gry w folderze launchera – względnie do niego. Gdy dysk dostanie inną literę (E: → F:), ścieżki są automatycznie rozwiązywane dla nowej litery.
- Stare configi ze ścieżkami bezwzględnymi są przemapowywane, gdy launcher raz zapamięta swój dysk (`settings.launcher_drive`).
- Gdy brakuje `.exe`/ROM-u, launcher próbuje też tej samej ścieżki na swoim dysku; kafelki gier, których pliku nie da się znaleźć, mają oznaczenie **„⚠ Brak pliku gry”**.
- Gry startują z katalogiem roboczym ustawionym na folder gry (gry emulowane: folder emulatora).

### 📦 Budowanie .exe (PyInstaller)

```bat
pip install -r requirements-dev.txt
pyinstaller --noconfirm game_launcher.spec
```

Wynik: `dist\GameLauncher\GameLauncher.exe` (build „onedir”: szybszy start, folder `data` powstaje obok exe). Kopiuj cały folder `dist\GameLauncher`. Do paczki trafiają tylko ikony, `icon.ico` i szablony `*.example.json` – nigdy Twój `data\` ani muzyka.

### 🧪 Testy

```bat
pip install -r requirements-dev.txt
python -m pytest
```

Testy obejmują rozwiązywanie i przenośność ścieżek, wczytywanie konfiguracji (domyślne wartości, sekrety ze zmiennych, migracja portu), budowanie polecenia uruchomienia gry oraz autoryzację pilota WWW. GitHub Actions uruchamia je na `windows-latest` (`.github/workflows/ci.yml`).

### 📦 Zależności

Główne używane biblioteki:
- `tkinter` - Framework GUI
- `Pillow` - Przetwarzanie obrazów
- `pygame` - Odtwarzacz muzyki
- `socketio` - Czat w czasie rzeczywistym
- `matplotlib` - Wykresy statystyk
- `psutil` - Monitorowanie procesów
- `requests` - Wywołania API
- `mutagen` - Metadane muzyki

### 🎮 Użytkowanie

#### Pierwsze Uruchomienie
1. Ustaw swoją nazwę użytkownika
2. Wybierz skanowanie folderów lub dodaj gry ręcznie
3. Skonfiguruj preferencje w Ustawieniach

#### Dodawanie Gier
- **Ręcznie**: Biblioteka → Dodaj Grę → Wypełnij szczegóły
- **Gry Emulowane**: Najpierw skonfiguruj emulator, potem dodaj ROM

#### Konfiguracja Czatu
1. Uruchom serwer: `python chat_server.py` (port 5000, zob. `GL_CHAT_PORT`)
2. Przejdź do strony Czat i dodaj serwer (domyślnie: `http://127.0.0.1:5000`)
3. Zarejestruj się lub zaloguj
4. Zacznij czatować!

#### Odtwarzacz Muzyki
1. Przejdź do strony Muzyka
2. Dodaj folder z muzyką lub pliki
3. Twórz playlisty
4. Skonfiguruj globalne skróty w Ustawieniach

### ⚙️ Konfiguracja

#### Struktura Danych

Dane aplikacji są oddzielone od kodu źródłowego:

- `data/config/config.json` - główna konfiguracja aplikacji
- `data/config/local_settings.json` - ustawienia lokalne/prywatne
- `data/config/achievements_def.json` - definicje osiągnięć
- `data/games_saves/` - dane zapisów gier
- `data/chat/chat.db` - baza danych czatu SQLite
- `data/chat/uploads/` - przesłane pliki czatu
- `custom_themes/` - własne motywy
- `external/ScriptHookConfig.ini` - konfiguracja integracji zewnętrznych

#### Kompatybilność i Migracja

Aplikacja zachowuje kompatybilność wsteczną ze starymi lokalizacjami:

- `config.json`, `local_settings.json`, `achievements_def.json`
- `games_saves/`
- `chat.db`
- `chat_uploads/` i `uploads/`

Przy starcie dane są migrowane do nowej struktury gdy jest to potrzebne.

### 🔧 Zaawansowane Funkcje

#### Pilot WWW
Włącz w Ustawienia → Zdalne sterowanie. Launcher pokazuje pełny adres **z tokenem**
(np. `http://127.0.0.1:5050/?token=...`). Bez tokenu każde żądanie dostaje HTTP 401,
a gry uruchamia/zamyka się wyłącznie żądaniami POST.
- Domyślny port **5050** (serwer czatu używa 5000), nasłuch tylko na `127.0.0.1`.
- Telefon w tej samej sieci Wi-Fi: zaznacz „Dostępny w sieci lokalnej” (nasłuch na `0.0.0.0`).
- „Nowy token” unieważnia stare linki.

#### Discord Rich Presence
Włącz w Ustawienia → Integracja Discord
Pokazuje w jaką grę grasz na Discordzie

#### Globalne Skróty Klawiszowe
Konfiguruj w Ustawienia → Skróty Muzyki
Steruj odtwarzaczem muzyki z dowolnej aplikacji

#### Synchronizacja w Chmurze
- **GitHub**: Ustawienia → Chmura → Skonfiguruj token GitHub
- **Google Drive**: jeszcze niezaimplementowane (zob. `docs/ROADMAP.md`)

### ⚠️ Znane ograniczenia

- Synchronizacja z Google Drive nie jest zaimplementowana (działa tylko GitHub).
- Tłumaczenia interfejsu są wyłączone (UI tylko po polsku).
- Skanowanie folderów w poszukiwaniu gier istnieje w kodzie (`launcher/scan_pipeline.py`), ale nie ma jeszcze pozycji w menu.
- Przeniesienie gier na dysk o innej literze, który *nie* jest dyskiem launchera, nadal wymaga edycji ścieżek gier.
- Planowane funkcje: `docs/ROADMAP.md`.

### 🤝 Współpraca

Wkład jest mile widziany! Możesz:
- Zgłaszać błędy
- Sugerować funkcje
- Wysyłać pull requesty

### 📄 Licencja

Ten projekt jest objęty licencją **GNU General Public License v3.0 (GPL-3.0)**.

Oznacza to:
- ✅ Możesz używać, modyfikować i dystrybuować to oprogramowanie swobodnie
- ✅ Możesz używać go do celów komercyjnych
- ⚠️ **Wszelkie modyfikacje lub prace pochodne MUSZĄ również być open source na licencji GPL-3.0**
- ⚠️ Musisz dołączyć oryginalną licencję i informację o prawach autorskich
- ⚠️ Musisz zaznaczyć wszelkie zmiany wprowadzone w kodzie

**To gwarantuje, że projekt i wszystkie jego pochodne pozostaną open source na zawsze.**

Zobacz plik [LICENSE](LICENSE) po szczegóły lub odwiedź https://www.gnu.org/licenses/gpl-3.0.html

### ⚠️ Zastrzeżenie

Ten launcher jest zaprojektowany do zarządzania osobistymi kolekcjami gier. Użytkownicy są odpowiedzialni za upewnienie się, że posiadają legalne prawa do gier, które dodają do launchera.

---

**Made with ❤️ for retro and indie game enthusiasts**

---

## Wersja Go + WebView2 / Go + WebView2 version

Port launchera do Go (jeden exe, te same dane) jest w folderze [`go/`](go/README.md). / A Go port (single exe, same data files) lives in [`go/`](go/README.md).
