# Roadmapa / Roadmap

Lista pomysłów przeniesiona ze starego pliku `do dodania.txt` (folder legacy),
z aktualnym stanem sprawdzonym w kodzie v1.5.0.

## Zrobione

| Funkcja | Gdzie w kodzie |
|---|---|
| System osiągnięć i statystyk (w tym wykres kołowy czasu gry wg gatunku, „Najczęściej uruchamiane”) | `launcher/achievements_*`, `launcher/stats_*` |
| Personalizacja: motywy, tło, własne okładki | `launcher/services/theme_runtime.py`, `ui/game_form.py` |
| Obsługa kontrolera (gamepad) | `launcher/gamepad_runtime.py` |
| Tryb pełnoekranowy | `launcher/sidebar_ui.py`, `launcher/library_view.py` |
| Przypomnienia | `launcher/reminders_runtime.py` |
| Zaawansowane filtry i sortowanie biblioteki | `ui/filters.py`, `launcher/advanced_filter_eval.py` |
| Backup i przywracanie danych launchera | `launcher/backup_restore.py` |
| Automatyczne aktualizacje launchera (z kontrolą wersji) | `launcher/updater_runtime.py` |
| Menedżer modów | `ui/mod_manager.py` |
| Czat (własny serwer Flask-SocketIO) + Discord Rich Presence | `chat_server.py`, `launcher/chat_*`, `launcher/discord_runtime.py` |
| Filtr gier VR | `launcher/init_constructor_runtime.py` (`vr_filter_var`) |
| Kontrastowy kolor czcionki w legendzie roadmapy | `launcher/utils.py: get_contrast_color` |
| Chmura: GitHub (zapisy + config) | `launcher/cloud_github_runtime.py` |
| Profil użytkownika z awatarem i statystykami | `launcher/home_page_runtime.py` (częściowo: jeden profil) |

## Do zrobienia (planowane)

1. **Chmura Google Drive** – w `cloud/cloud_manager.py` OAuth, wysyłanie i pobieranie są tylko `TODO`. Do czasu implementacji ukryć opcję albo oznaczyć jako „wkrótce”.
2. **Wielojęzyczność** – jest `languages.py`, ale aplikacja używa `DummyTranslator` (tłumaczenia wyłączone).
3. **Import biblioteki ze Steam / GOG / Epic** – rejestr Windows + pliki `steamapps/*.acf`.
4. **Analiza wydajności w grze** – FPS (min/śr./max), CPU/GPU/RAM/VRAM, osobna karta z wykresem, opcjonalna nakładka (MSI Afterburner / RTSS).
5. **Wiele profili użytkownika** – osobne osiągnięcia, czas gry i ustawienia per użytkownik (wspólna biblioteka gier).
6. **Powiadomienia o aktualizacjach gier** (patche).
7. **Funkcje społecznościowe** – dzielenie się osiągnięciami, zaproszenia; interaktywne „Dołącz” w czacie (`launcher/chat_message_actions.py`).
8. **Dropbox / OneDrive** jako kolejne chmury (MEGA/GoFile odradzane – brak oficjalnego API).
9. **Roadmapa**: gra nie może znikać z listy przed „Oznacz jako ukończoną”, kolorowanie planowanego czasu w kalendarzu, nazwa gry widoczna w tabeli (zgłoszone w `do dodania.txt` – do weryfikacji, czy już naprawione).
10. **Filtr zaawansowany w sortowaniu widoku listy** – `launcher/library_list_sort.py` ma logikę oznaczoną jako TODO.
11. **Naprawa ścieżek w UI** – dialog „Gra nie znaleziona → wskaż plik / przemapuj E:\ → F:\ dla wszystkich gier” (v1.5.0 przemapowuje automatycznie tylko przy zmianie litery dysku launchera).

## Odrzucone / na daleką przyszłość

- Wbudowany sklep z grami.
- Tryb VR samego launchera.
- Integracja z MEGA / GoFile.
