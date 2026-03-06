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
- **Python**: 3.8 or higher
- **Dependencies**: See `requirements.txt`

### 🚀 Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/game-launcher.git
cd game-launcher
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up configuration files (first time only)**
```bash
# Copy example config files
copy config.example.json data\config\config.json
copy local_settings.example.json data\config\local_settings.json
```

4. **Run the launcher**
```bash
python game_launcher.py
```

**Note**: The example config files (`*.example.json`) are safe templates. Your actual config files (`config.json`, `local_settings.json`) are ignored by git to protect your personal data and tokens.

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
- **Auto Scan**: Settings → Scan Folders → Add folder paths
- **Manual**: Library → Add Game → Fill in details
- **Emulated Games**: Configure emulator first, then add ROM

#### Chat Setup
1. Go to Chat page
2. Add server (default: localhost:5000)
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

#### Remote Server
Enable in Settings → Remote Server → Start Server
Access from browser: `http://your-ip:5000`

#### Discord Rich Presence
Enable in Settings → Discord Integration
Shows what game you're playing on Discord

#### Global Hotkeys
Configure in Settings → Music Hotkeys
Control music player from any application

#### Cloud Sync
- **GitHub**: Settings → Cloud → Configure GitHub token
- **Google Drive**: Settings → Cloud → Setup Google Drive

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
- **Python**: 3.8 lub wyższy
- **Zależności**: Zobacz `requirements.txt`

### 🚀 Instalacja

1. **Sklonuj repozytorium**
```bash
git clone https://github.com/yourusername/game-launcher.git
cd game-launcher
```

2. **Zainstaluj zależności**
```bash
pip install -r requirements.txt
```

3. **Skonfiguruj pliki konfiguracyjne (tylko przy pierwszym uruchomieniu)**
```bash
# Skopiuj przykładowe pliki konfiguracyjne
copy config.example.json data\config\config.json
copy local_settings.example.json data\config\local_settings.json
```

4. **Uruchom launcher**
```bash
python game_launcher.py
```

**Uwaga**: Przykładowe pliki konfiguracyjne (`*.example.json`) to bezpieczne szablony. Twoje rzeczywiste pliki konfiguracyjne (`config.json`, `local_settings.json`) są ignorowane przez git, aby chronić twoje dane osobowe i tokeny.

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
- **Auto Skan**: Ustawienia → Foldery do Skanowania → Dodaj ścieżki folderów
- **Ręcznie**: Biblioteka → Dodaj Grę → Wypełnij szczegóły
- **Gry Emulowane**: Najpierw skonfiguruj emulator, potem dodaj ROM

#### Konfiguracja Czatu
1. Przejdź do strony Czat
2. Dodaj serwer (domyślnie: localhost:5000)
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

#### Serwer Zdalny
Włącz w Ustawienia → Serwer Zdalny → Uruchom Serwer
Dostęp z przeglądarki: `http://twoje-ip:5000`

#### Discord Rich Presence
Włącz w Ustawienia → Integracja Discord
Pokazuje w jaką grę grasz na Discordzie

#### Globalne Skróty Klawiszowe
Konfiguruj w Ustawienia → Skróty Muzyki
Steruj odtwarzaczem muzyki z dowolnej aplikacji

#### Synchronizacja w Chmurze
- **GitHub**: Ustawienia → Chmura → Skonfiguruj token GitHub
- **Google Drive**: Ustawienia → Chmura → Skonfiguruj Google Drive

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
