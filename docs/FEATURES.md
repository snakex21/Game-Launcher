# Game Launcher (Python/Tkinter) – inwentarz funkcji przed portem

Stan: gałąź `polish/v1.5.0` (wersja w kodzie `1.5.0`), listopad 2026.
Cel dokumentu: punkt odniesienia dla przepisania launchera (prawdopodobnie Go + WebView2).
Port powinien **czytać istniejące dane użytkownika bez konwersji** – sekcja „Formaty danych” opisuje je na podstawie kodu (z odnośnikami `plik:linia`). Rzeczy niepotwierdzone oznaczono „(niepewne)”.

Spis treści:
1. Wydajność – punkt odniesienia (Python)
2. Ekrany i okna
3. Integracje
4. Skróty klawiszowe
5. Znane błędy i ograniczenia
6. Formaty danych

---

## 1. Wydajność – punkt odniesienia (Python)

Pomiar: Windows 10 Pro, Python 3.13.7, przykładowa biblioteka 12 gier (ścieżki do nieistniejących exe), 5 zimnych startów w osobnych procesach, mediana. „Pierwsza klatka” = od startu interpretera do `root.update()` po konstruktorze `GameLauncher`. RAM = RSS procesu.

| Wariant | Import | Konstruktor | Ładowanie ikon | Pierwsza klatka | RAM przy 1. klatce | RAM po 6 s |
|---|---|---|---|---|---|---|
| Oryginał (`main`, d55d15f) | 371 ms | 1067 ms | 425 ms | **1497 ms** | 54 MB | **101 MB** |
| `polish/v1.5.0` (źródła) | 331 ms | 602 ms | 33 ms | **977 ms** | 54 MB | **102 MB** |
| `polish/v1.5.0` exe (PyInstaller onedir) | – | – | – | okno widoczne po **~0,6 s** od uruchomienia exe (3 starty: 604 / 543 / 774 ms) | – | **~101 MB** po 10 s |

Uwagi:
- Pierwszy start po zimnym dysku (bez cache systemu plików) trwał 4,7 s (oryginał).
- Po 6 s RAM rośnie do ~100 MB, bo w tle ładują się strony biblioteki, roadmapy, muzyki (pygame) i statystyk (matplotlib).
- Exe onedir zajmuje ~288 MB (największe: `googleapiclient` 89 MB, `babel` 31 MB, `jedi` 22 MB, `numpy.libs` 20 MB, `matplotlib` 13 MB).
- Jedna z 3 próbek RAM exe dała 4,3 MB (proces był w trakcie zamykania/ukrycia do zasobnika – pomiar odrzucony).
- Skrypty pomiarowe: `scratchpad\game_launcher\bench\bench.py`, `bench_once.py`, `bench_exe.py`; surowe wyniki: `bench\final.txt`.

---

## 2. Ekrany i okna

<!-- Część 1a inwentarza funkcji: ekrany i dialogi biblioteki. Gałąź polish/v1.5.0. Ścieżki względem katalogu głównego repo. -->

### Pasek boczny (sidebar)

Źródło: `launcher/sidebar_ui.py:5-97` (funkcja `create_sidebar`, wołana też przy `refresh_ui`, `launcher/app_navigation.py:37`).

- Nagłówek „Game Launcher” (`sidebar_ui.py:9-13`), tekst przez `translator.gettext`.
- Przyciski nawigacji (każdy `fill="x"`) w tej kolejności:
  1. **Home** → `show_home` (`:15-18`)
  2. **Library** → `show_library` (`:20-25`); przy pierwszym wejściu buduje nagłówek i siatkę (`launcher/app_navigation.py:138-144`)
  3. **Roadmap** → `show_roadmap` (`:27-32`)
  4. **Mod Manager** → `show_mod_manager` (`:34-39`)
  5. **Osiągnięcia** → `show_achievements_page` (`:41-46`)
  6. **News** → `show_news` (`:48-51`)
  7. **Statystyki** → `show_statistics_page` (`:53-56`), napis wpisany na sztywno, bez tłumaczenia
  8. **Muzyka** → `show_music_page` (`:58-59`), bez tłumaczenia
  9. **Czat** → `show_chat_page` (`:61-62`), bez tłumaczenia
  10. **Serwery Czatu** → `show_server_selection_page` (`:64-67`), bez tłumaczenia
  11. **Settings** → `show_settings` (`:69-74`)
  12. **Exit** → `on_closing` (`:76-79`)
- Checkbutton **Fullscreen Mode** (`:81-90`) → `toggle_fullscreen` (`launcher/library_view.py:49-53`): ustawia `root.attributes("-fullscreen")`, a gdy otwarta jest biblioteka w trybie kafelków, przelicza siatkę po 100 ms. Stan nie jest zapisywany w ustawieniach (zachowuje się tylko przy przebudowie sidebara).
- Przycisk **Minimize to Tray** (`:92-97`) → `minimize_to_tray` (`game_launcher.py:2058`): `root.withdraw()` i utworzenie ikony w zasobniku (`launcher/tray_runtime.py:29-65`). Minimalizacja okna (`on_minimize`, `tray_runtime.py:23-26`) robi to samo.
- **Menu ikony w zasobniku** (pystray, `tray_runtime.py:35-62`): Strona Główna, Biblioteka, Muzyka ▸ (Odtwórz / Pauza, Poprzedni, Następny, ─, Pokaż Odtwarzacz), ─, Roadmapa, Menedżer Modów, Osiągnięcia, Newsy, Statystyki, ─, Ustawienia, ─, Wyjdź z Programu. Każda pozycja „pokaż” woła `show_window()` (zatrzymuje ikonę, `deiconify`, `lift`, `focus_force`; `tray_runtime.py:13-20`), a potem otwiera daną stronę (`game_launcher.py:2047-2089`). Ikona pochodzi z `icon.png`, a gdy go brak, rysowana jest niebieska ikona „GL” (`game_launcher.py:2062-2066`).
- Uwagi: przycisku Przypomnień nie ma ani w sidebarze, ani w zasobniku (zob. „Przypomnienia”). Część napisów jest przetłumaczona, część wpisana na sztywno po polsku.

### Strona główna (Home)

Źródło: `launcher/home_page_runtime.py:10-109` oraz metody w `game_launcher.py`.

- **Nagłówek** (`home_page_runtime.py:15-85`):
  - Awatar o rozmiarze z `local_settings["avatar_display_size"]` (domyślnie 48). Bez pliku awatara rysowany jest szary kwadrat z pierwszą literą nazwy użytkownika (`:40-64`).
  - Losowe powitanie z 5 wariantów z nazwą użytkownika (`:66-75`).
  - „Czas sesji: HH:MM:SS” oraz „Łączny czas: …”. Oba odświeżane timerami `_update_current_session_time_display` i `_update_launcher_usage_display` (`launcher/usage_runtime.py:8`, `:59`).
- **Ciało** w układzie 2×2 (`:87-106`):
  - LabelFrame **„Ostatnio grane”**: przyciski z nazwami gier posortowanymi po `last_played` malejąco. Kliknięcie od razu uruchamia grę (`game_launcher.py:1306-1320`). Liczba przycisków zależy od wysokości ramki, bez paska przewijania (`_update_home_lists`, `game_launcher.py:1291-1304`, podpięte pod `<Configure>`).
  - LabelFrame **„Losowe gry”**: losowa próbka gier jako przyciski „uruchom”. Przy pustej bibliotece pokazuje „Brak gier.” (`game_launcher.py:1322-1336`).
  - Prawa kolumna:
    - **„Czas spędzony w grach”** (`launcher/playtime_stats_runtime.py:6-74`): OptionMenu jednostki (godziny / dni / miesiące / lata) oraz wiersze „Łącznie”, „Gry PC”, „Emulatory (razem)”, a pod nimi „↳ <emulator>” dla każdego emulatora.
    - **„Statystyki Ogólne”**: top 10 „Najdłużej Grane Gry” (`game_launcher.py:1044-1065`).
- Uwagi: kliknięcie nazwy na Home od razu uruchamia grę, bez otwierania szczegółów. Treść odświeża się tylko przez `create_home_page()`, które wołają np. `edit_game` i `update_after_game`.

### Biblioteka – nagłówek i sterowanie

Źródło: `launcher/library_header.py:5-204`, `launcher/library_groups_runtime.py`, `launcher/library_tags.py`, `launcher/library_genres.py`, `launcher/library_view.py`.

Wiersz 0 nagłówka (`library_header.py:17-47`):
- Etykieta „Biblioteka”.
- **Pole wyszukiwania** (`search_entry`) z debounce 400 ms (`launcher/library_lazy_load.py:6-12`). Filtruje po podciągu nazwy gry, bez rozróżniania wielkości liter (`library_grid_runtime.py:300`).
- **„Dodaj Grę”** → `add_game` (zob. „Formularz dodawania/edycji gry”).
- **OptionMenu grupa/filtr** (`update_filter_group_menu`, `library_groups_runtime.py:62-97`). Pozycje: „Wszystkie Gry”, nieaktywny separator „--- Grupy Statyczne ---”, nazwy grup (posortowane), nieaktywny separator „--- Filtry Zaawansowane ---”, zapisane filtry. Wybór woła `reset_and_update_grid`.
- **„Dodaj Grupę Statyczną”** → `add_group` (`library_groups_runtime.py:39-59`): `askstring` z nazwą. Odrzuca „Wszystkie Gry”, nazwy zaczynające się od „---”, duplikaty grup i nazwy zajęte przez filtr. Po dodaniu przełącza widok na nową grupę.
- **„Usuń Grupę Statyczną”** → `delete_group` (`:7-36`): usuwa aktualnie wybraną grupę po potwierdzeniu. Dla „Wszystkie Gry” i dla filtrów pokazuje ostrzeżenia.
- **„Zarządzaj filtrami”** → `open_advanced_filter_manager` (`game_launcher.py:1942-1954`). Okno jest pojedyncze: drugie kliknięcie podnosi istniejące.

Wiersz 1 (`library_header.py:51-204`):
- **Gatunek:** OptionMenu „Wszystkie Gatunki” + `get_all_genres()`, czyli gatunki ze wszystkich gier plus `settings["custom_genres"]`, posortowane (`game_launcher.py:923-928`).
- **Tag:** OptionMenu „Wszystkie Tagi” + unikalne tagi ze wszystkich gier, sortowane bez rozróżniania wielkości liter (`library_tags.py:5-38`). Lista odświeża się po dodaniu, edycji i usunięciu gry.
- **Typ:** „Wszystkie Typy” / „Gry PC” (`game_type=="pc"`) / „Gry Emulowane” (`=="emulator"`).
- **Sortuj:** „Nazwa” (A→Z), „Data Dodania”, „Czas Gry”, „Ocena”; trzy ostatnie malejąco (`library_grid_runtime.py:310-317`).
- **„Zarządzaj Gatunkami”** → `ManageGenresWindow`.
- Przycisk przełączania widoku `view_mode_button` z tekstem „Widok: Lista” / „Widok: Kafelki” → `toggle_library_view` (`library_view.py:7-16`). Tryb zapisuje się w `local_settings["library_view_mode"]` (`tiles` lub `list`).

Filtry łączą się logiką AND: grupa lub filtr zaawansowany, potem typ, wyszukiwanie, gatunek i tag (`library_grid_runtime.py:279-308`).

- Uwagi:
  - **Przycisk przełączania widoku nigdy nie jest wyświetlany.** W `library_header.py:194-201` tworzony jest `view_mode_button`, ale `.grid()` wywołano ponownie na `manage_genres_btn`. Widok listy jest więc osiągalny tylko przez zapisane ustawienie.
  - `update_genre_menu` (`library_genres.py:4-15`), wołane po zmianie w „Zarządzaj Gatunkami”, tworzy nowy OptionMenu w złym rodzicu (`self.header`, row=1, col=1, czyli nakłada się na ramkę filtrów). Ustawia też `command=self.update_game_grid`, a ta metoda nie przyjmuje argumentu, więc wybór gatunku po takim odświeżeniu kończy się TypeError.

### Biblioteka – widok kafelków (grid)

Źródło: `launcher/library_grid_runtime.py:12-135` i `:243-418`, `launcher/library_lazy_load.py`, `launcher/library_tile_actions.py:23-237`.

- Canvas (tło #1e1e1e) z pionowym scrollbarem. Kółko myszy jest podpięte globalnie (`bind_all`) i doładowuje kafelki.
- **Paginacja** (`:114-135`, `:478-518`): „<< Poprzednia”, „Strona X / Y”, „Następna >>”. Rozmiar strony to `items_per_page`. Każda zmiana filtra lub sortowania wraca na stronę 1 (`reset_and_update_grid`, `game_launcher.py:908-911`).
- Liczba kolumn pochodzi z `local_settings["tiles_per_row"]` (domyślnie 4). Szerokość kafelka wynika z szerokości canvasu, minimum 200 px. Wysokość kafelka jest stała: 670 (`:112`, `:335-357`).
- **Lazy loading**: najpierw tworzone są puste ramki placeholderów (`library_lazy_load.py:119-141`), a treść ładuje się tylko dla widocznych kafelków z buforem jednej wysokości kafelka (`:64-116`).
- **Pusty stan** (`library_grid_runtime.py:371-396`): przy pustej bibliotece komunikat „Biblioteka jest pusta… Dodaj pierwszą grę…”, przy braku wyników „Brak gier pasujących… Wyczyść pole wyszukiwania albo wybierz „Wszystkie Gry””.
- **Zawartość kafelka** (`library_tile_actions.py:23-237`):
  - Okładka zajmuje 60% wysokości. Gdy brak pliku, generowany jest szary placeholder „Brak Okładki”. **LPM na okładce** otwiera okno szczegółów gry.
  - Opis: `Nazwa [PC]` albo `Nazwa [<emulator>]`, a pod nią „⚠ Brak pliku gry” (pomarańczowy tekst, gdy exe/ROM nie istnieje, także po zmianie litery dysku; `:12-20`), „Czas: …”, „Ukoń.: N%”, „Ver: …” i skrócone „Tagi: …”.
  - Przycisk **Uruchom/Zamknij** z ikoną play/stop i tooltipem. Gdy gra działa, przycisk jest czerwony i zamyka grę. Przy więcej niż jednym profilu obok jest Menubutton „▼” z listą profili, każdy uruchamia grę z danym profilem (`:192-214`). Na czas działania gry Menubutton jest ukrywany (`game_process_runtime.py`, `launch_game`).
  - Przycisk **Zapisy** (ikona dyskietki, tooltip „Zarządzaj Zapisami”) → SaveManager.
  - Ten sam przycisk zmienia stan dynamicznie po uruchomieniu i zamknięciu gry (`launch_game` oraz `_update_button_on_game_close`, `game_process_runtime.py:425-482`).
- **Menu kontekstowe kafelka** (PPM na ramce, okładce lub opisie; `_show_tile_context_menu`, `library_tile_actions.py:240-378`), z ikonami:
  1. „Uruchom”, albo kaskada „Uruchom z profilem…” z listą profili, gdy profil nie jest pojedynczym „Default”
  2. ─
  3. „Edytuj dane”
  4. „Otwórz folder z zapisami” (nieaktywne, gdy `save_path` nie jest katalogiem)
  5. „Zarządzaj zapisami”
  6. „Pokaż Checklistę” (otwiera szczegóły na zakładce „Checklista”)
  7. „Pokaż Screenshoty” (szczegóły, zakładka „Screenshoty”)
  8. „Mody” (przechodzi do Menedżera Modów i zaznacza grę; `:396-399`). Warunek `hasattr(self,"extended_mod_manager")` jest zawsze prawdziwy, bo atrybut ustawiany jest na `None` w `init_constructor_runtime.py:299`.
  9. ─
  10. „Resetuj statystyki”
  11. „Dodaj do grupy…” ▸ wszystkie grupy; grupy, w których gra już jest, są nieaktywne, a cała kaskada jest nieaktywna, gdy gra jest we wszystkich grupach. Pozycja pojawia się tylko, gdy istnieją grupy.
  12. „Usuń z grupy…” ▸ grupy, w których jest gra (tylko gdy jest w jakiejś)
  13. ─
  14. „Usuń grę”
- Legacy: `create_game_tile` (`library_grid_runtime.py:138-240`) to starszy wariant kafelka z przyciskami Uruchom/Zamknij, Zapis, Edytuj, Usuń, Resetuj Statystyki, Dodaj do Grupy, Usuń z Grupy. Nie jest używany przez `update_game_grid`.
- Klasa `ui/game_grid_manager.py:8` (`GameGridManager`) z własną siatką i paginacją nie jest nigdzie importowana (martwy kod).
- `ui/components.py:8-52`: `ToolTip`, żółty dymek pod widgetem pokazywany na `<Enter>`, z metodą `update_text`.
- Uwagi:
  - `_remove_from_group_from_menu` (`library_tile_actions.py:387`) używa nieistniejącego `self.group_var`. Gra zostaje usunięta z grupy i zapisana, ale potem leci AttributeError i widok się nie odświeża. Ten sam błąd jest w `remove_from_group` (`game_launcher.py:1475`) i w legacy `create_game_tile` (`library_grid_runtime.py:234`).
  - `_add_to_group_from_menu` nie odświeża widoku, gdy wybrana jest grupa statyczna.

### Biblioteka – widok listy

Źródło: `launcher/library_grid_runtime.py:24-102` i `:421-461`, `launcher/library_list_sort.py`, `launcher/library_list_context.py`.

- Treeview z kolumnami: Nazwa Gry, Czas Gry, Ocena, Gatunki, Wersja, Tagi, Data Dodania (format `YYYY-MM-DD HH:MM`). Zaznaczenie pojedyncze. W tym widoku nie ma paginacji.
- **Sortowanie kliknięciem nagłówka** (`library_list_sort.py:5-119`): ponowne kliknięcie odwraca kierunek, a w nagłówku pojawia się „▲” lub „▼”. Sortowanie działa po wszystkich 7 kolumnach. Domyślnie po Nazwie rosnąco.
- **Dwuklik** otwiera okno szczegółów gry (`game_launcher.py:2982-2990`).
- **Menu kontekstowe wiersza** (`library_list_context.py:9-161`) ma te same pozycje co menu kafelka, ale w innej kolejności: Uruchom / Uruchom z profilem…, ─, Edytuj dane, Otwórz folder z zapisami, Zarządzaj zapisami, Pokaż Checklistę, Pokaż Screenshoty, Mody, Dodaj do grupy… ▸, Usuń z grupy… ▸, Resetuj statystyki, ─, Usuń grę.
- Uwagi:
  - Przy aktywnym **filtrze zaawansowanym** widok listy pokazuje wszystkie gry, bo reguły nie są stosowane. Kod ma tu komentarz „logika filtrowania TODO” (`library_list_sort.py:21-26`).
  - Sortowanie z nagłówka (`Sortuj:`) w nagłówku biblioteki nie działa w liście, bo lista zawsze sortuje po `_list_sort_column`.
  - Każde `update_game_grid` w trybie listy woła `_sort_list_view_by_column`, a ta odwraca kierunek, gdy kolumna się nie zmieniła (`:8-12`). W efekcie każde odświeżenie (np. wpisanie znaku w wyszukiwarce) przełącza kierunek sortowania.

### Grupy statyczne

- Grupy są przechowywane jako `config` → `self.groups` w postaci `{nazwa: [nazwy gier]}`.
- Operacje:
  - dodawanie i usuwanie grupy z nagłówka biblioteki (zob. wyżej),
  - dodawanie i usuwanie gry przez kaskady menu kontekstowego (`library_list_context.py:166-177`, `library_tile_actions.py:381-393`),
  - legacy `add_to_group` (`game_launcher.py:1446-1472`), gdzie nazwę grupy wpisuje się w `askstring` z listą dostępnych grup w treści.
- Usunięcie gry usuwa ją także ze wszystkich grup (`game_crud_runtime.py:170-172`).

### Gatunki i tagi

- Gatunki gry to lista `genres`, wybierana wielokrotnie w formularzu. Gatunki niestandardowe trzymane są w `settings["custom_genres"]`.
- Tagi to lista `tags`, wpisywana w formularzu jako tekst rozdzielany przecinkami. Służą do filtrowania (nagłówek) i są wyświetlane na kafelku i w liście.

### Okno „Zarządzaj Gatunkami Niestandardowymi”

Źródło: `ui/manage_genres_window.py:7-169`.

- Listbox „Gatunki Niestandardowe:” pokazuje posortowane `settings["custom_genres"]`.
- Przyciski:
  - **Dodaj Gatunek**: `askstring`. Ostrzega, gdy gatunek już występuje w grach lub jest duplikatem. Po dodaniu zapisuje i woła `update_genre_menu`.
  - **Usuń Zaznaczony**: `askyesno`, potem usunięcie i odświeżenie.
  - **Zamknij**.
- Uwagi: po zmianie odpala się błędne `update_genre_menu` (zob. nagłówek biblioteki).

### Filtry zaawansowane – menedżer, edytor filtra, edytor reguły

Źródło: `ui/filters.py:13-620`, ewaluacja w `launcher/advanced_filter_eval.py:6-159`.

- **AdvancedFilterManager** („Zarządzaj Filtrami Zaawansowanymi”, `filters.py:13-146`): listbox „Zapisane Filtry:” oraz przyciski:
  - **Dodaj Filtr**,
  - **Edytuj Zaznaczony** (zmiana nazwy usuwa stary wpis),
  - **Usuń Zaznaczony** (`askyesno`),
  - **Zamknij**.

  Filtry zapisują się w `config["saved_filters"][nazwa] = {name, rules}`, po czym odświeża się OptionMenu grup/filtrów.
- **FilterEditorWindow** („Nowy Filtr Zaawansowany” / „Edytuj Filtr Zaawansowany”, `:149-354`):
  - pole „Nazwa Filtra:” (domyślnie „Nowy Filtr”),
  - przyciski **Dodaj Regułę**, **Edytuj Regułę**, **Usuń Regułę** (z potwierdzeniem),
  - Treeview reguł z kolumnami Filtrowane Pole / Warunek / Wartość/Cel,
  - przyciski **Zapisz Filtr** i **Anuluj**.

  Walidacja: nazwa niepusta, nie „Wszystkie Gry” ani „---…”, unikalna względem grup i filtrów, co najmniej 1 reguła. Reguły łączone są logiką **AND**.
- **RuleEditor** („Dodaj/Edytuj Regułę Filtra”, `:357-619`) zawiera Combobox pola, Combobox warunku i widget wartości zależny od typu: Entry, DateEntry (`yyyy-mm-dd`) albo Combobox wyboru. Dla „jest ustawione” / „nie jest ustawione” widget wartości jest ukryty. Przyciski: **Zapisz Regułę**, **Anuluj**.
  - **Pola** (`:373-392`):

    | Etykieta | Pole w danych | Typ |
    |---|---|---|
    | Nazwa Gry | `name` | text |
    | Gatunek | `genres` | list |
    | Tag | `tags` | list |
    | Ocena | `rating` | number |
    | Czas Gry (godz.) | `play_time` | number; ewaluacja przelicza sekundy na godziny |
    | Data Dodania | `date_added` | date (timestamp → `YYYY-MM-DD`) |
    | Data Ost. Gry | `last_played` | date |
    | Typ Gry | `game_type` | choice: pc, emulator |
    | Emulator | `emulator_name` | choice: klucze `config["emulators"]` |
    | Ukończenie (%) | `completion` | number |

  - **Operatory w edytorze** (`:393-420`):

    | Typ | Operatory |
    |---|---|
    | text | zawiera, nie zawiera, równa się, zaczyna się od, kończy się na |
    | list | zawiera, nie zawiera |
    | number | ==, !=, >, <, >=, <=, jest ustawione, nie jest ustawione |
    | date | jest równe, jest przed, jest po, jest ustawione, nie jest ustawione |
    | choice | jest, nie jest |

    Ewaluator obsługuje dodatkowo „jest ustawione” / „nie jest ustawione” dla text, list i choice (`advanced_filter_eval.py:11-52`).
  - Porównania tekstowe nie rozróżniają wielkości liter. Daty porównywane są jako napisy `YYYY-MM-DD`.
- Uwagi:
  - **Filtry zaawansowane są zepsute.** `_check_game_against_rules` odwołuje się do `self.FIELDS` launchera (`advanced_filter_eval.py:65`), a `FIELDS` istnieje tylko w `RuleEditor`. Każdy wybór filtra w bibliotece kończy się AttributeError.
  - Dla pól typu list operator „zawiera”/„nie zawiera” jest mapowany na nieistniejące klucze „zawiera (lista)” (`:108-114`), więc reguły na Gatunek i Tag zawsze dają False.
  - W `filters.py:622-1080` jest też `ThemeEditorWindow` (edytor motywów), ale należy on do Ustawień.

### Okno szczegółów gry (GameDetailsWindow)

Źródło: `ui/game_details.py:17-1781`. Otwierane przez LPM na okładce kafelka, dwuklik w liście albo pozycje „Pokaż Checklistę” / „Pokaż Screenshoty” z menu. Jest jedno okno na grę (rozpoznawane po tytule), modalne (`grab_set`), 800×650.

- **Lewa kolumna**: okładka 300×450. **PPM na okładce** otwiera menu (`:1741-1761`):
  - „Ustaw Własną Okładkę…”
  - „Użyj Okładki z RAWG” (tylko gdy jest `cover_rawg`)
  - „Pobierz Ponownie z RAWG”
  - ─ „Usuń Okładkę” (tylko gdy jest okładka)
- **Nagłówek**: tytuł gry, „Data wydania”, „Deweloper”, „Wydawca” (dane z RAWG) oraz link-przycisk **Strona WWW** (aktywny, gdy jest URL; `open_website`, `:1330`).
- **Zakładki** (Notebook):
  1. **„Opis / Notatki”** (`:116-145`): pole tekstowe tylko do odczytu, w którym sekcja „--- OPIS ---” (RAWG `description`) poprzedza „--- NOTATKI UŻYTKOWNIKA ---” (`:653-668`). Przycisk **Edytuj Notatki** / **Zapisz Notatki** przełącza edycję i zapisuje `notes` (`:1431-1461`).
  2. **„Info / Wymagania”** (`:148-200`): „Platformy”, „Gatunki (API)”, „Tagi (API)” oraz tekst wymagań minimalnych i zalecanych PC (`requirements_pc`; `:1399-1429`).
  3. **„Screenshoty”** (`:201-260`, `:765-1130`):
     - przycisk **Dodaj Screenshoty…** (wielokrotny wybór plików obrazów, kopiowanie do `IMAGES_FOLDER/screenshots/<gra>`),
     - przycisk **Skanuj Foldery Teraz (dla tej gry)** (wymaga skonfigurowanych `autoscan_screenshot_folders`),
     - siatka miniatur 120×80 z tooltipem „dodany ręcznie” / „znaleziony automatycznie”. LPM otwiera obraz w systemowej przeglądarce (`os.startfile`).

     PPM na miniaturze otwiera menu: „Otwórz”, „Usuń z listy ręcznej”, „Usuń z listy automatycznej” (z potwierdzeniem; usuwa tylko wpis z listy). Nieistniejące ścieżki są czyszczone automatycznie (`:954`).
  4. **„Checklista”** (`:262-321`, `:1150-1310`): Treeview z kolumnami ✓ (☑/☐) i Zadanie. **Dwuklik** przełącza `done`. Przyciski:
     - **Dodaj Zadanie** (`askstring`),
     - **Edytuj Zaznaczone** (`askstring`),
     - **Usuń Zaznaczone** (`askyesno`).

     Dane trafiają do `checklist: [{task, done}]`.
  5. **„Akcje / Zarządzanie”** (przewijane, `:323-455`):
     - ramka „Zarządzanie Grą”: **Edytuj Dane Gry…**, **Zarządzaj Zapisami…**, **Przejdź do Menedżera Modów**, **Resetuj Statystyki…**,
     - ramka „Zarządzanie Okładką”: **Ustaw Własną Okładkę…**, **Pobierz/Użyj Okładki z RAWG** (wymusza pobranie), **Usuń Okładkę (przywróć domyślną)** (usuwa plik, jeśli leży w `IMAGES_FOLDER`).
- **Statystyki launchera** pod zakładkami (`:1350-1397`): Czas gry, Ukończenie, Ocena (moja), Wersja (moja), Ostatnio grane, Data dodania, Gatunki (moje), Tagi (moje).
- **Dolny pasek** (`:470-489`):
  - **Pobierz Dane z RAWG**: wątek; w trakcie przycisk jest zablokowany, po zakończeniu wraca tekst „Pobierz Dane”.
  - **Uruchom**, albo „Uruchom (<profil>)” z „▼” i listą profili (`:1463-1524`).
  - **Zamknij**.
- Nieużywane w UI: `toggle_cover_source` (`:1763`), `create_action_buttons` (`:686`), `fetch_online_description_stub`.
- Uwagi:
  - `start_scan_for_this_game` jest zdefiniowane dwa razy (`:494` i `:571`); obowiązuje druga wersja.
  - Przycisk „Uruchom” w szczegółach nie przełącza się na „Zamknij”.
  - Po zapisie notatek z widocznym opisem mogą zostać zapisane razem z tekstem opisu (`:1440-1451`).

### Formularz dodawania/edycji gry (GameForm)

Źródło: `ui/game_form.py:9-891`; logika w `launcher/game_crud_runtime.py:13-103`. Tytuł okna to „Dodaj Grę” albo „Edytuj Grę”.

- **Pola** w kolejności:
  - **Typ gry** (Combobox: pc / emulator). Przełącza widoczność pól PC i emulatora (`:355-369`).
  - **Nazwa gry**. Wymagana i unikalna przy dodawaniu.
  - PC: **Ścieżka .exe (PC)** + „Wybierz…” (filtr `*.exe`). Wymagana, plik musi istnieć.
  - Emulator:
    - **Wybierz Emulator** (Combobox z `config["emulators"]`, wymagany),
    - **Ścieżka ROM/ISO** + „Wybierz…” (wymagana, musi istnieć),
    - **Argumenty Emulatora**.
  - **Ścieżka zapisów** + „Wybierz…” (wybór katalogu).
  - **Okładka** + „Wybierz…” (pliki obrazów). Puste pole czyści okładkę.
  - **Gatunki**: Listbox wielokrotnego wyboru z `get_all_genres()` + przycisk **Zarządzaj Gatunkami**.
  - **Ocena (1-10)**: liczba typu float albo puste. Zakres nie jest sprawdzany.
  - **Wersja gry**.
  - **Tagi (oddzielone przecinkami)**.
  - **Notatki** (Text).
- **Ramka „Profile Uruchomieniowe (PC)”** (`:230-285`, ukryta dla emulatora): Treeview z kolumnami Nazwa Profilu / Argumenty / Ścieżka EXE (jeśli inna). Przyciski:
  - **Dodaj Profil** i **Edytuj Zaznaczony**: podokno z polami Nazwa profilu, Ścieżka .exe (opcjonalna) + Wybierz…, Argumenty linii komend, oraz przyciskami Zapisz / Anuluj (`:714-828`).
  - **Usuń Zaznaczony**: nie pozwala usunąć jedynego profilu „Default”; potwierdzenie przez `askyesno`.
- **Przyciski dolne**:
  - **Parsuj .NFO** (`:461-507`): wymaga exe. Dopisuje „NFO Date: …” do wersji, „NFO Genre: …” do tagów i „NFO Publisher: …” do notatek.
  - **Parsuj Nazwę Fold.** (`:509-543`): dopisuje „Year: …” do wersji i dane do notatek.
  - **Zapisz**, **Anuluj**.
- **Po dodaniu** (`game_crud_runtime.py:13-57`): ustawiane są `date_added`, `play_time=0`, `completion=0`, `last_played`, `play_sessions` oraz `launch_profiles=[Default]`. Potem pytanie „Czy chcesz zaimportować zapisy gry?” → wybór folderu → kopia do `GAMES_FOLDER/<gra>`. Na końcu sprawdzane są osiągnięcia i odświeżana jest siatka, filtr tagów i combobox roadmapy.
- **Po edycji** (`:60-103`): zachowywane są `play_time`, `completion`, `last_played`, `play_sessions`, `date_added`. Odświeżane są siatka, kafelek, Home i otwarte okno szczegółów.
- Uwagi:
  - **Utrata danych przy edycji.** `save()` buduje słownik wyłącznie z pól formularza (`game_form.py:562-565`), a `edit_game` nadpisuje nim cały rekord (`game_crud_runtime.py:81-83`). Giną checklista, screenshoty, opis, dane RAWG, `cover_rawg`/`cover_custom`, `play_count` itd.
  - Przy dodawaniu profile zdefiniowane w formularzu są nadpisywane domyślnym `[Default]` (`game_crud_runtime.py:27-33`).
  - W trybie edycji zmiana nazwy jest po cichu ignorowana, bo klucz pochodzi z oryginału (`game_form.py:547-548`).
  - W formularzu nie ma pola „Ukończenie”.
  - `check_and_unlock_achievements()` jest wołane dwa razy (`game_crud_runtime.py:52-53`).

### Usuwanie gry, reset statystyk

- **Usuń grę** (`game_crud_runtime.py:145-186`): `askyesno`, a następnie:
  - usuwa plik okładki, jeśli leży w `IMAGES_FOLDER`,
  - **usuwa cały katalog kopii zapisów `GAMES_FOLDER/<gra>`** (`rmtree`) bez dodatkowego ostrzeżenia,
  - usuwa grę z grup i z bazy,
  - odświeża bibliotekę, tagi, roadmapę i Home.
- **Resetuj statystyki** (`game_launcher.py:1387-1398`): `askyesno`, potem zeruje `play_time`, `completion` i `play_sessions`.

### Uruchamianie i zamykanie gry (akcje widoczne dla użytkownika)

Źródło: `launcher/game_process_runtime.py`, `launcher/session_monitor_runtime.py`, `game_launcher.py`.

- **Uruchom** (`game_process_runtime.py:16-140`): budowa polecenia przez `build_launch_command`, z profilem albo bez. Wariant PC to exe + argumenty, wariant emulatora to emulator + ROM + argumenty.
  - Błędy konfiguracji (`LaunchError`, `launcher/launch_command.py`) pokazują się w `showerror`.
  - Proces startuje przez `subprocess.Popen(cwd=…)`. Dla WinError 740 jest osobny komunikat o uprawnieniach administratora.
  - Ustawiane są `last_played` i `play_count`, przycisk na kafelku zmienia się na czerwony „Zamknij”.
  - Status Discord przechodzi na „in_game”.
  - Między 2:00 a 4:00 ustawiany jest znacznik dla osiągnięcia „night_owl”.
- **Zamknij** (`:238-422`): dla PC szuka procesu po ścieżce exe, dla emulatora po exe emulatora i ROM w cmdline. Zabija dzieci, potem rodzica, i pokazuje „Gra … została zamknięta”. Gdy procesu nie znaleziono, pokazuje ostrzeżenie.
- **Monitor sesji** (wątek co 5 s, `session_monitor_runtime.py:7-60`) wykrywa także grę uruchomioną poza launcherem. Po zakończeniu gry:
  - dolicza `play_time` i sesję, a dla gier „Planowana” dolicza `time_spent` w roadmapie,
  - przywraca przycisk „Uruchom”,
  - gdy `auto_backup_on_exit` (domyślnie włączone), robi auto-zapis (`_autosave`, `launcher/autosave_runtime.py:11`),
  - jeśli checklista ma otwarte zadania, pyta „Czy chcesz teraz przejrzeć/zaktualizować checklistę…?” (`game_launcher.py:1092-1110`),
  - pyta `askinteger` „Ile procent gry ukończyłeś?” (0–100; `game_launcher.py:1184-1199`).
- Uwagi:
  - Odpowiedź „Tak” na pytanie o checklistę tylko zapisuje log i niczego nie otwiera (`game_launcher.py:1106-1110`).
  - `track_play_time` i `update_after_game` (`game_launcher.py:1348-1378`) to nieużywany kod legacy.

### Menedżer zapisów (SaveManager)

Źródło: `ui/save_manager.py:13-448`. Okno „Zarządzanie zapisami – <gra>”. Kopie leżą w `GAMES_FOLDER/<gra>/saves/<nazwa>` i `…/_autosave`.

- Treeview z kolumnami % Ukoń. / Data Zapisu / Godzina / Nazwa Folderu (Techniczna). Wiersz „Automatyczny Zapis” (`_autosave_`) jest na górze, wyróżniony kursywą i jasnoniebieskim kolorem (`:124-200`).
- Przyciski (`:85-121`):
  - **Utwórz Zapis**: `askinteger` z procentem ukończenia, potem kopia `save_path` do `Save_<N>%_<YYYYmmdd_HHMMSS>` z oknem postępu. Nieaktywny, gdy `save_path` jest nieprawidłowe.
  - **Wczytaj Zapis**: `askyesno`, potem kopia wybranego zapisu (ręcznego lub auto) do `save_path` z paskiem postępu. Nieaktywny j.w.
  - **Edytuj Zapis**: zmiana procentu (`askinteger`) i zmiana nazwy folderu z zachowaniem znacznika czasu. Nie działa dla auto-zapisu.
  - **Usuń Zapis**: `askyesno`, usunięcie w tle z postępem.
  - **Otwórz Folder Zapisów Gry**: otwiera `save_path` w Eksploratorze.
  - **Zamknij**.
- Operacje w tle obsługuje `launcher/file_ops_runtime.py:10-189` (`_copy_or_delete_with_progress`: `copytree` lub `rmtree` w wątku, okno postępu, `showinfo`/`showerror`).

### Menedżer modów (ExtendedModManager)

Źródło: `ui/mod_manager.py:12-755`. Jest to strona w głównym oknie (sidebar „Mod Manager”), tworzona leniwie (`game_launcher.py:2383`). Dane trafiają do `mods_data[gra]["profiles"][profil] = {mods:{}, load_order:[]}`.

- **Lewy panel**:
  - „Wybierz grę:” (OptionMenu z grami),
  - „Profil:” (OptionMenu, domyślnie „default”),
  - przyciski **Utwórz Profil** (`askstring`) i **Usuń Profil** (`askyesno`; `:314-359`).
- **Tabela modów** z kolumnami Nazwa / Aktywny / Priorytet.
- **Przyciski** (`:110-128`):
  - **Zainstaluj Mod** (`:487-638`): okno „Wybierz lokalizację moda” z ostatnimi lokalizacjami (do 5 na grę) i „Wybierz inną lokalizację…”. Dalej `askstring` z nazwą moda i `askyesno` „Aktywować od razu?”. Pliki moda kopiowane są do folderu gry (`dirname(exe_path)`), a nadpisywane pliki trafiają wcześniej do `_backup_<mod>_<ts>`.
  - **Zainstaluj z ZIP** (`:361-485`): wybór pliku `.zip`, `askstring` z nazwą, okno wyboru lokalizacji instalacji (ostatnie lub „Wybierz inną lokalizację…”), rozpakowanie (`extractall`), `askyesno` o aktywacji.
  - **Dezaktywuj Mod** (`:203-257`): przywraca pliki z backupu i ustawia `active=False`.
  - **Odinstaluj Mod** (`:640-706`): `askyesno`, przywrócenie oraz usunięcie backupu, usunięcie z `load_order`.
  - **Zwiększ Priorytet** / **Zmniejsz Priorytet**: ±1, a `load_order` sortowany jest po priorytecie malejąco (`:708-748`).
- **Odśwież**: przeładowanie tabeli.
- Wejście z menu kontekstowego biblioteki zaznacza grę przez `select_game_in_manager` (`:136`).
- Uwagi:
  - **Brak wykrywania konfliktów** między modami.
  - **Brak akcji „Aktywuj”** dla nieaktywnego moda.
  - Pliki moda są kopiowane do gry niezależnie od odpowiedzi „Aktywować od razu?” (flaga jest tylko zapisywana).
  - Priorytet nie wpływa na pliki na dysku.
  - Mod z ZIP nie ma backupu, więc „Dezaktywuj” zgłosi błąd „Nie znaleziono backupu”.
  - Pierwsza gra w menu to placeholder „Wybierz grę”.

### Duplikaty gier

Źródło: `launcher/duplicates_ui.py:15-405`. Uruchamiane wyłącznie z Ustawień → „Narzędzia Biblioteki” → **„Znajdź Potencjalne Duplikaty”** (`launcher/settings_page_content.py:678-684`).

- **Algorytm**: nazwa jest zamieniana na małe litery i pozostają tylko znaki `a-z` (`:15-19`). Grupy z co najmniej 2 grami to kandydaci. Analiza idzie w wątku z nieokreślonym paskiem postępu.
- Gdy nic nie znaleziono: „Nie znaleziono potencjalnych duplikatów.”
- **Okno „Potencjalne Duplikaty Gier”**:
  - drzewo z nagłówkami grup (szare tło) i grami jako dziećmi, kolumny Nazwa Gry / Czas Gry / Data Dodania / Ścieżka Pliku,
  - wielokrotne zaznaczanie i sortowanie po kliknięciu nagłówka (`:285-331`),
  - licznik „Zaznaczono: N gier”,
  - przyciski **Otwórz Lokalizację** (folder exe/ROM), **Usuń Zaznaczone Gry** (`askyesno`; usuwa okładkę, katalog kopii zapisów, wpisy w grupach i grę; `:195-249`) oraz **Zamknij**.
- Uwagi: w `except` (`:70-78`) lambda używa niezdefiniowanego `e`, więc błąd skanowania zakończy się NameError zamiast komunikatu.

### Roadmapa, kalendarz i archiwum

Źródło: `launcher/roadmap_archive_runtime.py:10-484` (strona otwierana z sidebara „Roadmap”, `game_launcher.py:2355`).

- Nagłówek „Roadmapa Gier” i Notebook z zakładkami:
  - **„Obecne”** (`:54-76`, `:256-326`):
    - lewy panel z ramką „Dodaj grę do Roadmapy”: Nazwa Gry (Combobox z gier biblioteki), Data Rozpoczęcia (DateEntry), Planowana Data Zakończenia (DateEntry) i przycisk **Dodaj do Roadmapy**. Walidacja: wymagana gra, brak duplikatu, koniec nie wcześniej niż start (`:329-368`).
    - Treeview z kolumnami Nazwa Gry / Data Rozpoczęcia / Data Zakończenia / Status / Czas Spędzony.
    - przyciski **Oznacz jako Ukończoną** (przenosi do archiwum z `completion_date`=dziś i sprawdza osiągnięcia) oraz **Usuń z Roadmapy** (`askyesno`).
    - prawy panel: Calendar (`locale pl_PL`), w którym każdy dzień od startu do końca planu jest zaznaczony na niebiesko (`:233-253`).
    - Statusy: „Planowana”, „Ukończona”, „Nie ukończona na czas”. `time_spent` rośnie, gdy gra „Planowana” jest uruchamiana (`session_monitor_runtime.py:34-42`).
  - **„Archiwum”** (`:79-215`): Treeview z kolumnami Nazwa Gry / Data Rozpoczęcia / Data Ukończenia / Czas Spędzony. Wiersze są kolorowane według miesiąca ukończenia (`MONTH_COLORS`). Obok kalendarz ze zdarzeniami w dniach ukończenia w tych samych kolorach i legenda miesięcy. W archiwum nie ma żadnych przycisków.
- Uwagi:
  - `monitor_roadmap` (`:428-441`), który zmienia status na „Nie ukończona na czas”, **nigdzie nie jest uruchamiany**, więc status ten nigdy się nie pojawi. Gdyby był uruchomiony, modyfikowałby widgety Tk z wątku.
  - Z archiwum nie da się nic usunąć ani przywrócić.

### Przypomnienia

Źródło: `launcher/reminders_runtime.py:11-119`, `game_launcher.py:1991-2003`.

- **Strona „Przypomnienia”**: Listbox z wpisami „YYYY-MM-DD HH:MM:SS – wiadomość” oraz przyciski:
  - **Dodaj Przypomnienie**: okno z polem „Data i Godzina (YYYY-MM-DD HH:MM:SS)” (wpisywane ręcznie), polem „Wiadomość” i przyciskiem **Zapisz**. Wymaga daty w przyszłości.
  - **Usuń Przypomnienie**: bez potwierdzenia.
- **Wątek `monitor_reminders`** (uruchamiany przy starcie, `init_constructor_runtime.py:526`) co 60 s wysyła powiadomienie systemowe (plyer) „Przypomnienie” i oznacza wpis jako `notified`.
- Uwagi: **strona jest nieosiągalna z UI**. `show_reminders` nie jest podpięte do żadnego przycisku ani menu, więc przypomnienia można tylko odebrać, nie dodać.

### Newsy (RSS)

Źródło: `launcher/news_runtime.py:12-240`, zarządzanie źródłami w `launcher/settings_runtime.py:35-100`.

- **Strona „Newsy Gier”**: `HTMLLabel` (tkhtmlview). Bez pakietów `feedparser` lub `tkhtmlview` pokazuje instrukcję „pip install -r requirements.txt” (`:16-32`).
- **Ładowanie** w wątku przy pierwszym wejściu (`:159-182`):
  - pobierane są aktywne `settings["rss_feeds"]` przez `requests` z UA przeglądarki i timeoutem 10 s, potem parsowane przez `feedparser`,
  - wpisy ze wszystkich źródeł są łączone i sortowane po dacie malejąco, a widok ucinany do `settings["news_post_limit"]` (domyślnie 10),
  - każdy wpis pokazuje tytuł, datę, `summary` (HTML) i link „Czytaj więcej”.
- **Domyślne źródło**: IGN Games `https://feeds.ign.com/ign/games-all` (`launcher/config_store.py:281-288`). Stary format, czyli lista stringów, migrowany jest do `{url, active, name}`.
- **Zarządzanie źródłami** (w Ustawieniach):
  - checkbox aktywności dla każdego kanału + **Usuń** (`remove_specific_rss_feed`, z potwierdzeniem),
  - dodawanie (`add_rss_feed`: `askstring` z URL, potem nazwa opcjonalna),
  - limit postów (`update_post_limit`).

  Po zmianie newsy przeładowują się, jeśli strona jest otwarta.
- Uwagi:
  - Brak przycisku „Odśwież” na stronie newsów: newsy ładują się raz na sesję (`_news_loaded`).
  - Legacy `remove_rss_feed` (`:214-228`) usuwa string z listy słowników, co dałoby ValueError (prawdopodobnie nieużywane).

### Dialogi z `ui/dialogs.py`

- **AddProfileDialog** (`:12-118`): pola Nazwa profilu, Plik .exe + Wybierz…, Argumenty; przyciski Zapisz / Anuluj. Używany przez ScanVerificationWindow do „+ Dodaj Profil .EXE”.
- **ScanVerificationWindow** – „Weryfikacja Znalezionych Gier” (`:120-630`):
  - Treeview z kolumnami Importuj? / Sugerowana Nazwa Gry / Sugerowany Główny Plik EXE / Folder Gry / Dodatkowe Profile. Dwuklik przełącza import (zielony lub szary wiersz).
  - Przyciski: **Zmień Nazwę**, **Zmień Główny .EXE**, **+ Dodaj Profil .EXE**, **- Usuń Profil**, **Importuj Zaznaczone** (tworzy gry PC z `date_added`, `play_time=0` i profilami), **Anuluj**.
  - Uwagi: funkcja skanowania folderów z grami (`start_scan_thread`, `launcher/scan_pipeline.py:152`) **nie ma żadnego przycisku w UI**, więc to okno jest praktycznie nieosiągalne.
- **AchievementForm** (`:632-1029`, wołany z `launcher/achievements_defs.py:209`, opis w części o osiągnięciach):
  - pola: ID Osiągnięcia, Nazwa Wyświetlana, Opis, Ikona (ścieżka) + Wybierz…, Typ Warunku, Wartość/Cel (Entry albo Combobox gatunku/tagu/grupy plus „Liczba gier:”), checkbox „Ukryte (do odblokowania)”, przyciski Zapisz / Anuluj,
  - typy warunków (`launcher/init_constructor_runtime.py:358-379`): Liczba uruchomionych gier, Rozmiar biblioteki, Łączny czas gry (godziny), Gry ukończone w 100%, Czas gry w jednej grze (godz.), Liczba gier z gatunku, Liczba gier z tagiem, Liczba gier w grupie, Gry 100% z gatunku, Gry 100% z tagiem, Gry 100% w grupie, Ukończone gry z Roadmapy, Liczba ocenionych gier, Liczba stworzonych grup, Liczba gier z tagami, Liczba zainstalowanych modów, Liczba gier dodanych do Roadmapy, Liczba zmian motywu, Gra uruchomiona w nocy (2-4), Dni używania z rzędu.
- **ChatServerEditorDialog** (`:1031-1217`, wołany z `launcher/server_selection.py:209`): pola Nazwa Serwera i Adres URL Serwera (musi zaczynać się od http:// lub https://, nazwa i URL muszą być unikalne), checkbox „Ustaw jako domyślny serwer” (zdejmuje flagę z pozostałych serwerów), przyciski Zapisz / Anuluj.

### Kreator pierwszego uruchomienia

Źródło: `launcher/initial_setup_runtime.py:8-105`, wywoływany, gdy brak skonfigurowanego użytkownika.

- **Modalny dialog „Witaj w Game Launcher!”** (400×200, w kolorach aktywnego motywu) z tekstem „Nie wykryto konfiguracji użytkownika. Co chcesz zrobić?” i trzema przyciskami:
  - **Wczytaj Backup**: `load_local_backup` z wyborem folderu „GameLauncher_Backup_…” (`launcher/backup_restore.py:230`). Bez nazwy użytkownika w backupie aplikacja się zamyka.
  - **Nowy Użytkownik**: `askstring` „Podaj swoją nazwę użytkownika” (`launcher/window_ops.py:57-63`), potem `refresh_ui`.
  - **Wyjdź**: zamknięcie aplikacji. Tak samo działa zamknięcie okna dialogu.
- Uwagi: anulowanie pytania o nazwę ustawia „Gracz” (`window_ops.py:61-62`), więc gałąź „anulowano → zamknij” (`initial_setup_runtime.py:95-99`) nigdy się nie wykona.

### Statystyki (strona „Statystyki”)

**Wejście:** przycisk „Statystyki” w sidebarze (`launcher/sidebar_ui.py:53`) → `show_statistics_page` (`launcher/stats_navigation.py:4`). Strona budowana leniwie przy pierwszym wejściu (`launcher/stats_page.py:8`). Wejście ustawia status Discord „Przegląda Statystyki” i uruchamia licznik czasu launchera.

**Pasek kontrolek (wiersz 0)** – `launcher/stats_page.py:16-129`:
- **Okres** (combobox readonly, `stats_page.py:30`) – opcje z `launcher/init_constructor_runtime.py:333-340`:
  - Ostatnie 7 dni (domyślnie), Ostatnie 30 dni, Ten miesiąc, Ten rok, Cały czas (od najstarszego `date_added` w bibliotece), Zakres niestandardowy... (obliczenia: `launcher/stats_controls.py:28-81`).
- **Widok** (combobox readonly, `stats_page.py:50`, zmiana → `_on_view_change`, `game_launcher.py:2207`) – 8 widoków (`init_constructor_runtime.py:341-350`):
  1. Czas gry dziennie – słupki, godziny/dzień (`launcher/stats_data.py:135`).
  2. Gry uruchamiane dziennie – słupki, liczba unikalnych gier/dzień; **kliknięcie słupka** pokazuje w panelu „Szczegóły” listę gier z tego dnia (`launcher/stats_runtime.py:110-118, 161-220`).
  3. Czas gry (wszystkie gry) – top 20 gier wg czasu w okresie (`stats_data.py:155`).
  4. Czas gry (wybrana gra) – dzienny czas jednej gry; pokazuje dodatkowy combobox **„Gra:”** z listą gier (`stats_page.py:65-78`, `game_launcher.py:2220`).
  5. Czas gry wg Gatunku (Kołowy) – wykres kołowy, top 8 gatunków + „Inne”, legenda „Gatunki” z godzinami (`stats_data.py:183`, `launcher/stats_chart.py:48-83`).
  6. Najczęściej Uruchamiane Gry – top 20 wg liczby sesji rozpoczętych w okresie (`stats_data.py:204`).
  7. Średni Czas Sesji (per Gra) – top 20, minuty (`stats_data.py:230`).
  8. Czas w launcherze dziennie – z `local_settings.launcher_daily_usage_seconds` + bieżąca sesja (`stats_data.py:114-125, 220`).
- **Od / Do** (2× `tkcalendar.DateEntry`, format yyyy-mm-dd, domyślnie ostatni tydzień) – tylko dla zakresu niestandardowego (`stats_page.py:80-94`); walidacja start ≤ koniec (`stats_controls.py:59-76`).
- **„Pokaż Czas / Grę (Okres)”** – widoczny tylko w widoku „Czas gry dziennie”; otwiera po prawej panel „Szczegóły” (Treeview: Nazwa Gry | Czas w okresie), posortowany malejąco (`stats_page.py:99`, `stats_runtime.py:120-158`).
- **„Kolor słupków”** – color picker, zmienia kolor słupków (tylko w pamięci, `stats_bar_color`) i odświeża (`stats_page.py:105-113`).
- **„Odśwież”** – generuje wykres w wątku tła (kolejka + polling 100 ms) (`stats_runtime.py:9-68`).
- Etykieta „Łączny czas: Xd Yh Zm” – łączny czas w launcherze, odświeżana co 1 s (`launcher/usage_runtime.py:8-43`). Reset licznika (`usage_runtime.py:46`) jest wywoływany z innego ekranu (pytanie tak/nie).

**Obszar wykresu:** matplotlib osadzony w Tk (`stats_runtime.py:71-92`), kolory z aktywnego motywu, etykiety wartości nad słupkami (format czasu `format_play_time` / liczby / „Xm”, „< 1m”), oś X obrócona o 45°, siatka Y przerywana (`stats_chart.py:84-145`). Brak danych → napis „Brak danych...” (`stats_chart.py:13-37`). Panel „Szczegóły” (Treeview 2-kolumnowy) ukryty domyślnie (`stats_page.py:142-160`).

**Źródło danych:** sesje `games[*].play_sessions[{start,end}]` rozbijane na dni z podziałem sesji przechodzących przez północ (`stats_data.py:53-112`); gatunki/tagi z `genres`/`tags` gry (tagi są liczone, ale żaden widok ich nie używa – `stats_data.py:36, 98`).

**Widżet „Czas spędzony w grach” (strona główna)** – `launcher/playtime_stats_runtime.py:6-75`, wywołanie z `launcher/home_page_runtime.py:102`: OptionMenu jednostek (godziny/dni/miesiące/lata), wiersze „Łącznie”, „Gry PC”, „Emulatory (razem)” + podwiersz per emulator.

**Uwagi:** combobox „Okres” nie ma podpiętego `<<ComboboxSelected>>` (jedyne wywołanie `_on_period_change` to inicjalizacja, `stats_page.py:163`), więc pola Od/Do dla „Zakres niestandardowy...” nigdy się nie pokazują i zakres użyje dat domyślnych (ostatni tydzień); zmiana okresu/widoku nie odświeża wykresu automatycznie – trzeba kliknąć „Odśwież”; `_on_view_change` umieszcza ramkę dynamicznych kontrolek w tej samej kolumnie (4) co zakres dat; kolor słupków nie jest zapisywany w ustawieniach.

---

### Osiągnięcia (strona „Osiągnięcia” + edytor definicji)

**Wejście:** sidebar „Osiągnięcia” (`launcher/sidebar_ui.py:43`) → `show_achievements_page` (`launcher/achievements_runtime.py:18`); pierwsze wejście buduje stronę, kolejne przeładowują definicje z pliku i przeliczają postęp (`achievements_runtime.py:9-15, 23-31`).

**Część górna – „Twoje Osiągnięcia”** (`launcher/achievements_page.py:42-284`):
- Nagłówek + licznik „Odblokowano: X / Y” (`:45-74`).
- Przewijana lista (Canvas + scroll kółkiem) posortowana po nazwie; każda pozycja: ikona 48×48 (szara dla zablokowanych, „(brak ikony)” przy błędzie), nazwa (biała/szara), opis, oraz:
  - odblokowane: „Odblokowano: RRRR-MM-DD GG:MM” (zielony) (`:242-250`),
  - zablokowane: pasek postępu + tekst „aktualny / cel” (`:251-284`).

**Część dolna – „Zarządzaj Definicjami”** (`achievements_page.py:286-357`):
- Treeview: ID | Nazwa | Opis | Warunek (warunek = przetłumaczony typ reguły + cel) (`launcher/achievements_defs.py:60-89`).
- Przyciski: **„Dodaj Nowe”**, **„Edytuj Zaznaczone”** (oba → dialog `AchievementForm`), **„Usuń Zaznaczone”** (potwierdzenie tak/nie, usuwa definicję i postęp użytkownika), **„Odśwież Definicje”** (`:334-355`).

**Edytor (`AchievementForm`, `ui/dialogs.py:632-~900`):** pola ID Osiągnięcia, Nazwa Wyświetlana, Opis, Ikona (ścieżka + „Wybierz...”), Typ Warunku (combobox), Wartość/Cel – Entry lub, dla reguł z gatunkiem/tagiem/grupą, combobox wyboru gatunku/tagu/grupy + pole „Liczba gier” (`ui/dialogs.py:815-890`), checkbox „Ukryte (do odblokowania)”, przyciski Zapisz/Anuluj. Walidacja unikalności ID (`achievements_defs.py:215-228`). Definicje zapisywane do `CONFIG_DIR/achievements_def.json` (migracja ze starej lokalizacji `APP_DIR/achievements_def.json`, `achievements_defs.py:11-32`); postęp w `user.achievements[id] = {unlocked, timestamp, current_progress}`.

**Typy warunków (reguł)** – `launcher/init_constructor_runtime.py:357-378`, ewaluacja `launcher/achievements_runtime.py:40-324`:
games_launched_count (gry z play_count>0), library_size, total_playtime_hours, games_completed_100, playtime_single_game_hours, genre_played_count / genre_completed_100 (param `genre`), tag_played_count / tag_completed_100 (param `tag`), group_played_count / group_completed_100 (param `group`), roadmap_completed_count (rozmiar archiwum), games_rated_count, groups_created, games_with_tags, mods_installed (suma modów w profilach), roadmap_items_added, themes_changed (`user.theme_change_count`), game_launched_at_night (flaga `_triggered_at_night`, okno 2–4), consecutive_days_used (`local_settings.consecutive_days`).
W repo nie ma wbudowanego pliku z gotowymi definicjami – wszystkie pochodzą z pliku JSON użytkownika (brak definicji → „(Brak zdefiniowanych osiągnięć)”).

**Odblokowanie:** ustawia `unlocked`, `timestamp`, zapisuje config i pokazuje powiadomienie systemowe (plyer) „Osiągnięcie Odblokowane!” (`achievements_runtime.py:297-318`).

**Uwagi:** flaga „Ukryte” z edytora nie jest nigdzie uwzględniana na liście (strona pokazuje wszystkie); cache ikon kluczowany samą ścieżką (`achievements_page.py:200-208`), więc ta sama ikona dla odblokowanego i zablokowanego osiągnięcia dostaje ten sam (kolorowy lub szary) wariant; komunikaty usuwania mają `parent=settings_page_frame` mimo wywołania ze strony Osiągnięć (`achievements_defs.py:94`); po usunięciu definicji lista/strona nie jest jawnie odświeżana (odświeża tylko `check_and_unlock` przy zmianie postępu); gałąź `genre_played_count` zdublowana (`achievements_runtime.py:122` i `:154`, druga martwa dla tego typu); `bind_all("<MouseWheel>")` dokładany przy każdym przebudowaniu strony (`achievements_page.py:139`).

---

### Odtwarzacz muzyki (strona „Muzyka”)

**Wejście:** sidebar „Muzyka” (`launcher/sidebar_ui.py:58`) → `show_music_page` (`launcher/music_navigation.py:4`), jedna instancja `MusicPlayerPage` tworzona leniwie (`ui/music_player.py:49`). Silnik: `pygame.mixer` (błąd init → messagebox), tagi: `mutagen`, okładki online: `pylast` + `requests` (`ui/music_player.py:25-47, 67-78`). Obsługiwane rozszerzenia: .mp3 .wav .ogg .flac .m4a (`:3518`, `:403`).

**Model danych (local_settings):** `named_music_playlists` {nazwa: [ {path, focus_cover_path, lastfm_cover_path, is_internal} ]}, `active_music_playlist_name`, `current_track_in_active_playlist_index`, `music_player_volume`, `last_music_folder`, `music_repeat_mode` (none/one/all), `music_shuffle_mode`, `music_autoplay_enabled`, `music_favorite_tracks` (lista ścieżek) (`ui/music_player.py:80-132, 316-348`). Dwie stałe, nieusuwalne playlisty: **„Główna Kolejka”** i **„Muzyka Wewnętrzna”** (folder `INTERNAL_MUSIC_DIR`) (`:82-93`). „Kolejka” = po prostu aktywna playlista – nie ma osobnej kolejki „odtwórz następne”.

**Górny pasek** (`ui/music_player.py:677-821`):
- Menubutton **„➕ Dodaj/Importuj”**: „Dodaj Folder...”, „Dodaj Pliki...”, „Importuj Folder (do wewn.)”, „Importuj Pliki (do wewn.)” – import kopiuje pliki do biblioteki wewnętrznej (nazwa z sufiksem `_(n)` przy kolizji, `:4871-4950`); folder dodawany nierekurencyjnie (`os.listdir`, `:3519-3523`); praca w wątku z oknem postępu, podsumowanie dodanych/pominiętych (`:3478-3667`, `:4611-4870`).
- **„🌍 Okładki”** – pobiera okładki z Last.fm dla wszystkich utworów aktywnej playlisty (wymaga `lastfm_api_key` z Ustawień; okno postępu „Pobrano (x/n) Ok/Brak”, podsumowanie) (`:4513-4610`).
- **„🗑️ Wyczyść”** – czyści aktywną playlistę (potwierdzenie; dla „Muzyka Wewnętrzna” dodatkowe pytanie o fizyczne usunięcie plików; usuwa osierocone okładki Focus/Last.fm) (`:4966-5208`).
- Checkbox **„♥ Ulubione”** – filtr: tylko ulubione (`:725-739`).
- Pole wyszukiwania (debounce 350 ms, po „Tytuł - Wykonawca” z tagów lub nazwie pliku) + **„✖”** czyszczenie (`:740-760`, `:1278-1300`).
- Przycisk **„Lista”/„Kafelki”** – przełącza widok treści (`:763`, `:1628-1689`).
- OptionMenu sortowania: Domyślnie, Tytuł A-Z, Tytuł Z-A, Ścieżka A-Z, Ścieżka Z-A – sortowanie trwale zmienia kolejność zapisanej playlisty (`:771-788`, `:1453-1563`).
- Combobox wyboru aktywnej playlisty (przełączenie zatrzymuje odtwarzanie) (`:791-802`, `:2406-2453`); **„+”** nowa playlista (askstring, walidacja pustej/zdublowanej nazwy) (`:803`, `:2372-2404`); **„-”** usuń aktywną playlistę (potwierdzenie, blokada dla stałych) (`:813`, `:3020-3047`).

**Widok Lista** (`:822-867`): Listbox (multi-select), dwuklik = odtwórz, PPM = menu kontekstowe, przyciski **▲ / ▼** przesuwania pojedynczego utworu (aktywne tylko przy 1 zaznaczeniu) (`:2189-2370`).

**Widok Kafelki** (`:868-904`, `:1712-1962`): siatka kafelków 160×220 (okładka Focus lub Last.fm albo placeholder „🎵”), aktualny utwór wyróżniony; LPM = odtwórz, PPM = to samo menu kontekstowe co lista.

**Widok „Teraz odtwarzane” (Focus)** (`:905-928`, `:2034-2080`, `:3876-3928`): duża okładka Focus + duży „Tytuł - Wykonawca”; przełączany przyciskiem **☰ / 🖼️** na dolnym pasku („Pokaż/Ukryj Kolejkę”, `:1252-1260`, `:1610-1626`).

**Menu kontekstowe utworu** (`:2455-2607`):
- Na pustym miejscu: „➕ Nowa Playlista...”, „🔁 Odśwież Playlistę 'Muzyka Wewnętrzna'” (tylko na tej playliście – synchronizuje wpisy z zawartością folderu, `:350-588`), „❌ Usuń Playlistę '…'” (nie dla stałych).
- Na utworze: „♥ Dodaj do Ulubionych” / „💔 Usuń z Ulubionych”, „↪ Kopiuj do...” (podmenu z innymi playlistami; „(już zawiera)” wyszarzone), „❌ Usuń z Playlisty” (dla pliku wewnętrznego nieobecnego na innych playlistach – pytanie o fizyczne usunięcie, „NIE MOŻNA cofnąć”, `:3071-3325`), „🖼️ Przypisz okładkę Focus...” (wybór pliku png/jpg/jpeg/bmp/gif/webp, `:2737-2820`), „🗑️ Usuń okładkę Focus” (gdy ustawiona, `:2609`), „🌍 Pobierz okładkę (Last.fm)” (`:4281-4511`), ewentualnie „🔁 Odśwież Playlistę 'Muzyka Wewnętrzna'”.

**Dolny pasek** (`:1105-1260`):
- Lewo: miniatura okładki, przycisk ulubionego **♥/♡** dla bieżącego utworu, „Nic nie gra”/nazwa, czas „0:00 / 0:00”.
- Środek: **🔀 Wł./Wył.** (shuffle – tasuje kopię playlisty, bieżący utwór na początek, `:3699-3795`), **⏮** poprzedni, **▶ / ❚❚** play/pauza (debounce 200 ms, `:5400-5504`), **⏭** następny, **🔁 Brak / 🔁¹ Jeden / 🔁 Lista** (repeat none→one→all, `:3669-3696`), **„Autoplay: Wł./Wył.”** (auto-przejście do następnego, `:1589-1607`), suwak postępu (przeciąganie = seek przez `play(start=…)`, `:3326-3400`, `:6019-6060`).
- Prawo: 🔊 suwak głośności 0–100 + „NN%” (`:1226-1250`, `:5772-5782`), przycisk ☰.
- Pętla postępu co 250 ms; koniec utworu → logika repeat/autoplay (`:5784-5987`). Zmiana utworu/pauzy aktualizuje status Discord (`:5322`, `:5494`).

**Sterowanie zewnętrzne:** globalne skróty klawiszowe (play/pause, next, prev, stop, głośność ±10%) – `launcher/hotkey_runtime.py:10-97`; menu w trayu: „Odtwórz / Pauza”, „Poprzedni”, „Następny”, „Pokaż Odtwarzacz” (`launcher/tray_runtime.py:35-42`). Klucz API Last.fm wpisywany w Ustawieniach (`launcher/settings_page_content.py:411`). Stan odtwarzacza przywracany po restore kopii zapasowej (`launcher/backup_restore.py:404-437`).

**Brak w kodzie (nie istnieje):** zmiana nazwy playlisty, import/eksport playlist (M3U itp.), korektor/equalizer, teksty piosenek, scrobbling Last.fm (Last.fm służy tylko do okładek), skróty klawiszowe w obrębie strony, przeciąganie i upuszczanie.

**Uwagi:** tworzenie nowej playlisty kończy się wyjątkiem – `_update_now_playing_label(track_name="Nic nie gra")` (`ui/music_player.py:2395`) używa nieistniejącego argumentu (sygnatura ma `track_name_override`, `:3831-3838`), więc kolejne kroki (`_apply_music_content_view`, stan przycisku „-”) się nie wykonują; zdublowane definicje metod – `_update_autoplay_button_text` (`:228` i `:1589`), `_toggle_autoplay` (`:1601` i `:3332`), `_delete_active_playlist_dialog` (`:2881` i `:3020`) – obowiązuje późniejsza; przełącznik ☰ (`_apply_current_view_mode`, `:2034-2052`) zawsze pokazuje Listbox i nie ukrywa ramki kafelków, więc w trybie Kafelki widoki mogą się nakładać; widok Focus czyta tylko `focus_cover_path` i ignoruje okładkę Last.fm (kafelki i miniatura używają obu, `:1830-1832` vs `:3892`); detekcja „.m3u” w `_load_active_playlist` to martwy placeholder (`:603-606`); `bind_all("<MouseWheel>")` na canvasie kafelków (`:902`).

---

### Nakładka „Teraz odtwarzane” (overlay)

**Okno:** `TrackOverlayWindow` (`ui/overlay.py:6`) – Toplevel 300×70, bez ramki, zawsze na wierzchu, tło przezroczyste (kolor klucza „lime green”, fallback #212121) (`ui/overlay.py:20-51`). Domyślna pozycja: prawy dolny róg (szer. ekranu − 320, wys. − 130).
- Zawartość: nazwa utworu (max 60 znaków, „Nic nie gra...”), cienki pasek postępu, czas „MM:SS / MM:SS” („??:?? / ??:??” gdy długość nieznana – pasek nieokreślony) (`ui/overlay.py:63-181`).
- **Przeciąganie myszą** (LPM) – po puszczeniu pozycja zapisywana w `local_settings.overlay_x_pos/overlay_y_pos` (`ui/overlay.py:105-136`).
- Brak przycisków/menu kontekstowego w samym overlayu.

**Sterowanie (Ustawienia):** checkbox „Pokaż nakładkę 'Teraz Odtwarzane' na ekranie (globalnie)” (`launcher/settings_page_content.py:192`) → `_toggle_track_overlay_setting` (`launcher/overlay_controls.py:17`); pola „Pozycja X/Y nakładki” + „Zastosuj Pozycję” (`overlay_controls.py:80`) i „Resetuj Pozycję” (`overlay_controls.py:112`, komunikat „Pozycja nakładki została zresetowana.”). Inicjalizacja przy starcie wg `show_track_overlay` (`overlay_controls.py:9`).

**Aktualizacja:** co 250 ms gdy włączone (`launcher/overlay_runtime.py:5-72`) – czas liczony z `time.monotonic()` i pól odtwarzacza `_start_time/_pause_acc/_pause_start`; `_stop_music` ustawia „Nic nie gra...” (`ui/music_player.py:5513-5547`).

**Uwagi:** wyświetla dane tylko gdy instancja odtwarzacza istnieje (strona Muzyka otwarta przynajmniej raz); brak walidacji pozycji poza ekranem.

---

### Serwery czatu (strona „Serwery Czatu”)

**Wejście:** sidebar „Serwery Czatu” (`launcher/sidebar_ui.py:65`) → `show_server_selection_page` (`launcher/server_selection.py:23`); także przyciski „🌐 Wybierz/Zarządzaj Serwerami Czatu” (ekran logowania) i „🌐 Zmień Serwer” (ekran czatu, rozłącza) (`launcher/chat_auth.py:441-453`).

**Zawartość** (`server_selection.py:47-145`): nagłówek „Zarządzanie Serwerami Czatu”; Treeview: Nazwa Serwera | Adres URL | Domyślny? (Tak/Nie), domyślny na górze, aktywny pogrubiony/zielony (`:147-178`).
- **„➕ Dodaj Serwer”** / **„✏️ Edytuj Zaznaczony”** → `ChatServerEditorDialog` (`ui/dialogs.py:1031`): Nazwa Serwera, Adres URL Serwera (musi zaczynać się od http:// lub https://), checkbox „Ustaw jako domyślny serwer”, Zapisz/Anuluj. Tylko jeden domyślny; gdy żaden – pierwszy staje się domyślny (`server_selection.py:180-264`).
- **„❌ Usuń Zaznaczony”** – potwierdzenie; nie można usunąć ostatniego serwera; usunięcie aktywnego → wylogowanie i przełączenie na domyślny (`:266-339`).
- **„🔗 Połącz z Zaznaczonym”** – jeśli już połączony z tym URL → info i przejście do czatu; inny serwer → wylogowanie; ustawia aktywny serwer, `last_used`, przechodzi do strony Czat (`:393-475`).
- Checkbox **„Automatycznie łącz z domyślnym serwerem przy starcie launchera”** (`:136-142`, zapis `chat_auto_connect_to_default`).

**Dane serwera (local_settings.chat_servers):** `{id, name, url, is_default, last_used, credentials:{email,password}, remember_credentials, auto_login_to_server}` (`:342-390`).

**Dialog „Ustawienia Serwera Czatu”** (`launcher/chat_server_settings.py:8-115`): jedno pole „Adres URL Serwera Czatu” (stary model `local_settings.chat_server_url`), Zapisz/Anuluj; zapis rozłącza aktywną sesję.

**Uwagi:** dialog `_open_chat_server_settings_dialog` nie ma wywołania w UI (tylko wrapper `game_launcher.py:293`) – pozostałość po modelu jednego serwera; hasła czatu przechowywane jawnym tekstem w `local_settings` (per serwer oraz dodatkowo globalnie `chat_email/chat_password`, `launcher/chat_auth.py:45-50`).

---

### Czat (strona „Czat”)

**Wejście:** sidebar „Czat” (`launcher/sidebar_ui.py:61`) → `show_chat_page` (`launcher/chat_navigation.py:4`): buduje UI przy pierwszym wejściu (`launcher/chat_layout.py:12`), wypełnia zapamiętane dane, próbuje auto-logowania, przywraca ostatnią rozmowę lub panel główny.

#### Panel logowania / rejestracji (`chat_layout.py:27-130`, `launcher/chat_auth.py`)
- Pola: Adres E-mail, Hasło (maskowane); **„Zaloguj”** → `POST /login {email,password}` → `{user_id, username}` → połączenie Socket.IO (`chat_auth.py:10-85`); tłumaczone błędy: zły format e-maila, e-mail niezarejestrowany, złe hasło, konto zbanowane.
- Checkboxy **„Zapamiętaj dane logowania”** (per serwer; odznaczenie czyści dane i wyłącza auto-login) i **„Automatyczne logowanie”** (wymusza „zapamiętaj”) (`chat_auth.py:87-137`); auto-login przy wejściu (`:139-168`).
- „--- Brak konta? ---”: Nazwa Użytkownika + **„Zarejestruj”** → `POST /register {username,email,password}` (`:170-232`).
- **„🌐 Wybierz/Zarządzaj Serwerami Czatu”**.

#### Panel główny czatu (3-kolumnowy PanedWindow, `chat_layout.py:140-621`)
**Lewa kolumna – lista rozmów:**
- „Status: Połączono/Rozłączono” (zielony/czerwony), „Zalogowano jako: …” + **„Edytuj”** (zmiana nazwy), **„➕ Utwórz Pokój”**, pole wyszukiwania użytkowników/pokoi (`:154-199`, filtr `launcher/chat_ui.py:92-245`).
- Treeview (Nazwa | Nowe): „💬 Panel Główny Czatu”, sekcja „👤 Użytkownicy” (online na zielono z dopiskiem „(online)”, offline szare, licznik nieprzeczytanych), sekcja „🏢 Pokoje Grupowe” (członek/nie-członek, ikona hasła) (`chat_ui.py:110-214`, tagi `chat_layout.py:213-240`).
- **Menu kontekstowe (PPM)** – `launcher/chat_context_actions.py:341-420`:
  - użytkownik: „Rozpocznij czat prywatny”, „🚫 Zablokuj {nick}” / „🔓 Odblokuj {nick}”;
  - pokój: „🚪 Opuść pokój '…'” (członek) lub „Dołącz do pokoju '…'”, separator, „Otwórz czat pokoju '…'”.

**Panel główny („Panel Główny Czatu”)** – lista aktualnie online użytkowników (`launcher/chat_dashboard.py:48-101`).

**Środkowa kolumna – rozmowa:**
- Etykieta partnera/pokoju, wskaźnik pisania (`chat_ui.py:68`), pole szukania w wiadomościach + „✖” (filtr lokalny, `launcher/chat_interactions.py:172-217`).
- Okno wiadomości (tk.Text z „dymkami”, `launcher/chat_render.py:274-623`): własne po prawej (niebieskie), cudze po lewej; separatory dat „Dzisiaj/Wczoraj/RRRR-MM-DD” (`chat_dashboard.py:152`); klikalne linki (`chat_render.py:12-52`); cytat odpowiedzi – klik przewija i podświetla oryginał (`chat_render.py:357-400, 626-717`); znacznik „(edytowano)”; znacznik przeczytania „👁️” na własnych wiadomościach (`chat_render.py:618-622`); załączniki: obraz → miniatura ładowana w tle + „Pobierz oryginał: …”, inne → „📄 nazwa” – klik otwiera `/download_file/<plik>` w przeglądarce (`chat_render.py:505-590`).
- Historia stronicowana: pierwsza strona przy otwarciu, kolejne automatycznie po przewinięciu do góry (≤2%) (`chat_layout.py:353-362`, `launcher/chat_history.py:198-394`); automatyczne oznaczanie jako przeczytane (`chat_interactions.py:59-170`).
- **Menu kontekstowe wiadomości** (`launcher/chat_message_actions.py:68-128`): „Edytuj wiadomość” (tylko własne; dialog z polem tekstowym, „Zapisz Edycję”/„Anuluj”, `:131-227`), „Odpowiedz” (tryb odpowiedzi z podglądem nad polem i „✖” anuluj, `:410-518`), „Usuń wiadomość” (potwierdzenie, `:229-261`), „Kopiuj tekst”.
- Pole wpisywania (Enter = wyślij; wysyła typing_start/stop), podgląd załącznika „📄 nazwa” + „✖” usuń, przyciski **„Wyślij”**, **„📎 Dołącz Plik”** (maks. 10 MB, upload `POST /upload_file`, potem wiadomość), **„😊”** emoji, **„Wyloguj z Czatu”**, **„🌐 Zmień Serwer”** (`chat_layout.py:454-580`, `launcher/chat_messaging.py:242-525`).
- Pokój, do którego nie należysz: komunikat systemowy „Nie jesteś członkiem pokoju …”, pole wpisywania wyłączone (`chat_message_actions.py:337-372`).
- Zablokowany rozmówca: pole wyłączone, komunikat „Zablokowałeś tego użytkownika. Odblokuj, aby wysyłać wiadomości.” (`chat_auth.py:329-440`).

**Prawa kolumna – „Członkowie Pokoju:”** (tylko dla pokoju, `chat_layout.py:592-617`, `launcher/chat_data.py:6-151`). PPM na członku (`chat_context_actions.py:9-97`): „{nick} (To Ty)” (nieaktywne) lub „Wyślij prywatną wiadomość do {nick}”; dla twórcy pokoju dodatkowo „Usuń {nick} z pokoju” (potwierdzenie).

#### Pokoje (`launcher/chat_rooms.py`)
- **Utwórz:** dialog „Utwórz Nowy Pokój” – Nazwa (3–100 znaków), Hasło (opcjonalne) + checkbox „Pokaż”, Utwórz/Anuluj → `POST /rooms {name, creator_id, password?}` (`:10-160`).
- **Dołącz:** pokój z hasłem → askstring (maskowany), bez hasła → potwierdzenie → `POST /rooms/<id>/members {user_id, password}` (`:209-335`).
- **Opuść:** dwuetapowe potwierdzenie – tak/nie (dla twórcy ostrzeżenie, że pokój zostanie trwale usunięty) + wpisanie pełnej nazwy pokoju → `DELETE /rooms/<id>/members/<uid>` (`chat_context_actions.py:99-198`; alternatywna ścieżka `chat_rooms.py:339-422`).
- Wyrzucenie członka przez twórcę: `DELETE /rooms/<id>/members/<uid>` (`chat_context_actions.py:200-273`).

#### Profil użytkownika (`launcher/chat_user_profile.py`)
- „Edytuj Nazwę Użytkownika”: nowa nazwa 3–80 znaków, różna od obecnej → `PUT /user/<id> {new_username}` (`:10-164`).
- Usuwanie konta: `_confirm_delete_chat_account` – potwierdzenie + hasło (askstring maskowany) → `DELETE /user/<id> {password}` (`:166-280`). Przycisk jest na stronie Ustawień (`launcher/settings_page_content.py:320`), nie w layoucie czatu.
- Brak widoku profilu innego użytkownika (avatar/opis) – tylko nazwa/status online.

#### Blokowanie (`launcher/chat_blocking.py`)
- Zablokuj: potwierdzenie → lokalny zbiór `blocked_user_ids` zapisywany w `local_settings.chat_blocked_user_ids` + `POST /users/<id>/block {blocker_id}`; Odblokuj: `DELETE /users/<id>/block` (`:15-105`).

#### Emoji (`launcher/chat_emoji.py`)
- Okno „Wybierz Emoji” przy przycisku, siatka 6 kolumn ze stałą listą ~139 emoji (bez kategorii, wyszukiwania i ostatnio używanych), przewijane; klik wstawia w miejscu kursora; zamyka się po utracie fokusu (`:8-405`).

#### Powiadomienia
- Nowa wiadomość w nieaktywnej rozmowie: licznik „Nowe” w drzewie + powiadomienie systemowe plyer „Nowa wiadomość od …” (`chat_history.py:578-647`).

#### Zdarzenia Socket.IO po stronie klienta (`launcher/chat_socket.py:7-597`)
Emitowane: `authenticate {user_id}` (po connect), `send_message {sender_id, content, receiver_id | room_id, replied_to_message_id?, attachment…}`, `typing_start/typing_stop {sender_id, receiver_id}`, `edit_message {message_id, new_content, editor_user_id}`, `delete_message {message_id, …}`, `mark_messages_as_read {message_ids, reader_id}`, `join_specific_room`, `leave_specific_room {room_id}`.
Obsługiwane: connect, disconnect, authenticated, authentication_failed, online_users_list, user_online, user_offline, account_status_changed, new_room_created, member_left_room, member_removed_from_room, room_deleted_by_creator, private_message_sent/received, group_message_sent/received, message_error, message_edited_successfully, message_edit_failed, message_deleted_successfully, message_delete_failed, message_read_update, typing_update.
HTTP: `/login`, `/register`, `/users`, `/rooms` (GET/POST), `/rooms/<id>/members` (POST/DELETE), `/rooms/<id>/messages` i `/messages/<u1>/<u2>` (paginacja `limit`, `before`, odp. `has_more`, `next_before`), `/upload_file`, `/download_file/<plik>`, `/users/<id>/block`, `/user/<id>` (PUT/DELETE).

**Uwagi:** klient emituje `join_specific_room` (`chat_rooms.py:307`), a serwer nie ma takiego handlera – po dołączeniu do pokoju wiadomości grupowe w czasie rzeczywistym dotrą dopiero po ponownym `authenticate`; serwer emituje `account_deleted` (`chat_server.py:1008`), którego klient nie obsługuje; „Usuń wiadomość” pokazywane też dla cudzych wiadomości (serwer i tak odrzuca – `chat_server.py:2358`); legacy ścieżka `_select_and_upload_chat_file`/`_handle_file_upload_response` emituje nieistniejące na serwerze zdarzenie `private_message` (`chat_messaging.py:203`) i nie ma wywołania w UI; brak reakcji emoji na wiadomości (nie istnieją ani w kliencie, ani w serwerze); emoji picker nie ma kategorii.

---

### Serwer czatu `chat_server.py` (kontrakt zgodności dla klienta)

Flask + Flask-SocketIO + SQLAlchemy (`chat_server.py:40-180`); `cors_allowed_origins="*"`, ping_interval 60 s / ping_timeout 120 s; uploady w `data/chat/uploads` obok exe, limit 10 MB, dozwolone rozszerzenia: txt, pdf, png, jpg, jpeg, gif, webp, zip, rar, 7z, doc(x), xls(x), ppt(x), mp3, wav, ogg, mp4, webm (`:45-79`). Start: `socketio.run(host, port)` (`:2820`).

**Modele:** User (username, email, password_hash, created_at, is_banned, is_admin), EmailBlacklist, BlockedRelationship, Message (sender_id, receiver_id | room_id, content, timestamp, edited_at, replied_to_message_id, attachment_server_filename / original_filename / mimetype, is_read_by_receiver), ChatRoom (name unikalne, creator_id, password_hash), RoomMembership (`:1056-1270`).

**REST:** `GET /`, `POST /register` (walidacja e-maila, czarna lista, unikalność nicka/e-maila), `POST /login` (błędy: Invalid email format / Email not registered / banned / Incorrect password), `GET /users`, `PUT /user/<id>` (zmiana nicka), `DELETE /user/<id>` (wymaga hasła), `POST|DELETE /users/<id>/block` (body `blocker_id`), `POST|GET /rooms` (POST emituje `new_room_created`), `POST /rooms/<id>/members` (dołączenie z hasłem), `DELETE /rooms/<id>/members/<uid>` (opuszczenie / wyrzucenie; wyjście twórcy usuwa pokój → `room_deleted_by_creator`; inaczej `member_left_room` / `member_removed_from_room`), `GET /rooms/<id>/messages`, `GET /messages/<u1>/<u2>` (limit ≤100, `before` ISO), `POST /upload_file`, `GET /download_file/<nazwa>` (`:1274-2058`).
**Panel admina:** `/admin/login`, `/admin/logout`, `/admin/status`, `/admin/panel` (HTML), `/admin/users` (GET), `/admin/users/<id>/ban|unban` (emituje `account_status_changed`), `DELETE /admin/users/<id>` (emituje `account_deleted`), `/admin/blacklist` (GET, add, DELETE) (`:213-1050`); hasło admina tylko ze zmiennej `FLASK_ADMIN_PASS` (bez niej logowanie zablokowane, `:186-197`).

**Socket.IO:** `connect`, `disconnect` (→ `user_offline`), `authenticate {user_id}` (dołącza do pokoju prywatnego = id użytkownika i pokoi grupowych, emituje `user_online`, `online_users_list`, `authenticated` / `authentication_failed`), `leave_specific_room`, `typing_start` / `typing_stop` (→ `typing_update {sender_id, is_typing}`), `edit_message` (tylko nadawca; → `message_edited_successfully` / `message_edit_failed`), `delete_message` (tylko nadawca; → `message_deleted_successfully` / `message_delete_failed`), `mark_messages_as_read` (→ `message_read_update`), `send_message` (→ `private_message_sent` + `private_message_received` do odbiorcy / `group_message_sent` + `group_message_received`; blokady i błędy → `message_error`) (`:2060-2800`).

**Uwagi (ważne dla portu klienta):** uwierzytelnienie Socket.IO i wielu endpointów REST opiera się wyłącznie na przesłanym `user_id`/`blocker_id`/`creator_id` (brak tokenu/sesji), a `PUT /user/<id>` nie wymaga hasła – nowy klient musi zachować ten kontrakt albo serwer wymaga przeróbki; endpointy `/users/<id>/block` POST/DELETE są zarejestrowane dwukrotnie – drugie, „stub” (`:1703-1741`), są martwe, bo pierwsza rejestracja (`:1279`, `:1323`) wygrywa; brak handlera `join_specific_room` (patrz Czat).

### Ekran „Ustawienia” (Settings)

**Pliki:** `launcher/settings_page_content.py` (budowa UI, 911 linii), `launcher/settings_runtime.py` (`show_settings`, RSS), `launcher/settings_avatar.py`, `launcher/rawg_settings.py`, `launcher/emulator_settings_runtime.py`, `launcher/services/theme_runtime.py`, `launcher/services/theme_store.py`, `ui/filters.py` (`ThemeEditorWindow`, l. 622+), `launcher/hotkey_capture.py`, `launcher/hotkey_input.py`, `launcher/backup_restore.py`, `launcher/cloud_github_runtime.py`, `launcher/overlay_controls.py`, `launcher/discord_runtime.py`, `launcher/remote_server_runtime.py`, `launcher/server_selection.py`, `ui/dialogs.py` (`ChatServerEditorDialog`, l. 1031+), metody w `game_launcher.py`.

**Ogólne zachowanie strony**
- Leniwa inicjalizacja: `show_settings()` (`settings_runtime.py:8`) buduje treść tylko za pierwszym razem (`_settings_initialized`), a przy każdym wejściu odświeża: listy folderów skanowania, RSS, ignorowane foldery, screenshoty, emulatory, motywy, nazwę/awatar użytkownika; ustawia status Discord „Zmienia Ustawienia”.
- Układ: nagłówek „Ustawienia Aplikacji” + przewijany `Canvas` (tło `#1e1e1e`) z kolejnymi sekcjami `LabelFrame` w jednej kolumnie. Kółko myszy przez `bind_all("<MouseWheel>", add="+")` – przewija tylko gdy kursor jest nad obszarem ustawień.
- Zapisy są natychmiastowe (brak globalnego przycisku „Zapisz”): każde pole ma własny handler. Dwa magazyny:
  - `config.json` → `self.settings` (= `config["settings"]`), `self.user` (= `config["user"]`), `config["emulators"]`; zapis `save_config()` (`launcher/utils.py:268`).
  - `local_settings.json` → `self.local_settings`; zapis `save_local_settings()` (`launcher/config_store.py:242`).

Kolejność sekcji na stronie (od góry): Wygląd → Użytkownik → System → Klucze API i Synchronizacja → Skanowanie Screenshotów → Emulatory → Newsy (RSS) → Narzędzia Biblioteki → Aktualizacje Aplikacji → Integracja z Discord → Zdalne Sterowanie → Skróty Klawiszowe Odtwarzacza Muzyki → Narzędzia Deweloperskie.

---

### Sekcja „Wygląd”

| Etykieta | Widget | Klucz konfiguracji | Domyślnie | Efekt / handler |
|---|---|---|---|---|
| Aktywny Motyw: | `ttk.OptionMenu` (lista wbudowanych + niestandardowych, sortowana) | `config.settings.theme` | `"Dark"` | `change_theme()` (`theme_runtime.py:46`): zapis, `apply_theme()`, inkrementacja `user.theme_change_count`, sprawdzenie osiągnięć. Gdy zapisany motyw nie istnieje → reset do `Dark`. |
| Kafelki w rzędzie w Bibliotece: | `ttk.Spinbox` readonly, 2–8 | `local_settings.tiles_per_row` | UI: 4; `config_store`: 3; example: 5 | `_save_tiles_per_row_setting()` (`game_launcher.py:2484`): walidacja 2–8, zapis, przebudowa siatki jeśli widok kafelkowy aktywny. |
| Czcionka interfejsu: | `ttk.Combobox` readonly (lista: Segoe UI, Arial, Verdana, Tahoma, Calibri, System + wszystkie `font.families()` bez `@`) | `local_settings.ui_font` | `"Segoe UI"` (lub `System`) | `_save_and_apply_font_setting()` → `apply_font_settings()` (`theme_runtime.py:764/774`): rozmiar 9 normal, 10 bold (nagłówki), 8 small; style TLabel, TButton, TEntry, TCombobox, TSpinbox, TCheckbutton, TRadiobutton, TMenubutton, TNotebook.Tab, Treeview.Heading, TLabelframe.Label, Tile.TButton. |
| Zarządzanie Motywami Niestandardowymi | `tk.Listbox` (5 wierszy) + przyciski **Dodaj / Edytuj / Usuń / Eksportuj / Importuj** | pliki `custom_themes/<nazwa>.json` | – | patrz 1c.1a |
| Pokaż nakładkę 'Teraz Odtwarzane' na ekranie (globalnie) | `ttk.Checkbutton` | `local_settings.show_track_overlay` | `False` | `_toggle_track_overlay_setting()` (`overlay_controls.py:17`): pokazuje/ukrywa `TrackOverlayWindow` (`ui/overlay.py`), uruchamia/zatrzymuje timer odświeżania. |
| Pozycja X nakładki: / Pozycja Y nakładki: | 2× `ttk.Entry` (IntVar, szer. 6) | `local_settings.overlay_x_pos`, `overlay_y_pos` | `None` (pole pokazuje 0) | Zapis dopiero przyciskiem. |
| Zastosuj Pozycję | `ttk.Button` | j.w. | – | `_apply_overlay_position_from_settings()` (`overlay_controls.py:80`): zapis + przesunięcie okna nakładki; błąd gdy nie liczba. |
| Resetuj Pozycję | `ttk.Button` | j.w. | – | `_reset_overlay_position()` (`overlay_controls.py:112`): X = ekran_w − szer_nakładki − 20, Y = ekran_h − wys − 60 (domyślnie 300×70). |

Nakładkę można też przeciągać myszą (`ui/overlay.py:105-113`); pozycja zapisywana callbackiem `save_local_settings`.

#### Motywy (theme_runtime + theme_store)

- **Wbudowane** (`launcher/utils.py:118`, `THEMES`): `Dark`, `Light`, `Blue`, `Forest Green`, `Deep Purple`, `Solarized Dark`, `Gruvbox Dark`.
- **Klucze definicji motywu** (12): `background`, `foreground`, `button_background`, `button_foreground`, `entry_background`, `tree_background`, `tree_heading`, `scrollbar_trough`, `scrollbar_slider`, `link_foreground`, `chart_bar_color`, `chart_axis_color`.
- **Format pliku motywu** (`theme_store.save_custom_theme`): `custom_themes/<nazwa po sanitize>.json` = `{"name": "...", "definition": {...}}` (indent 2, UTF-8). Nazwa pliku: znaki `\/*?:"<>|` → `_`.
- **Ładowanie** (`load_available_themes`): skan katalogu `custom_themes/` (tworzony, gdy brak), cache po `mtime`; motyw o nazwie kolidującej z wbudowanym jest pomijany (wbudowany ma priorytet).
- **`apply_theme`** (`theme_runtime.py:67`): konfiguruje style ttk (TFrame, TLabel, TButton, Game.TButton, TEntry, TCombobox map, TSpinbox, Treeview + selected `#0078d7`, Treeview.Heading, TScrollbar, Link.TButton), tło root, canvas biblioteki, canvas ustawień; wywołuje `apply_theme_colors()` odtwarzacza muzyki.
- **Dodaj / Edytuj** → `ThemeEditorWindow` (`ui/filters.py:622`, okno 550×840, modalne):
  - pole „Nazwa Motywu:” (domyślnie „Mój Motyw”),
  - dla każdego z 12 kluczy: etykieta PL (np. „Tło Główne”, „Tekst Główny”, „Tło Przycisku”, „Kolor Słupków Wykresu”…), `Entry` HEX + przycisk-próbnik koloru (colorchooser),
  - „Losuj Wszystkie”, ramka „Podgląd na Żywo” (etykieta, przycisk, entry, link…), „Zapisz Motyw” / „Anuluj”,
  - walidacja: nazwa niepusta, nie wbudowana, kolory `^#[0-9a-fA-F]{6}$`.
  - Edycja ze zmianą nazwy usuwa stary plik (pyta o nadpisanie istniejącego), po zapisie ponownie stosuje motyw, jeśli był aktywny.
- **Usuń**: potwierdzenie, usunięcie pliku; jeśli był aktywny → przełączenie na `Dark`.
- **Eksportuj**: okno 300×150 z wyborem „Kopiuj do Schowka” lub „Zapisz do Pliku...” (domyślna nazwa `<nazwa_z_podkreśleniami>_theme.json`), format `{"name","definition"}`.
- **Importuj**: okno 450×350, pole tekstowe JSON lub „Importuj z Pliku...”; `_process_theme_import` wymaga kluczy `name` i `definition`; brakujące/błędne kolory zastępowane wartościami z `Dark` (z ostrzeżeniem dla każdego klucza), pytanie o nazwę, pytanie o nadpisanie.

#### Tło (obraz)

- Klucz `config.settings.background_image` (ścieżka). Stosowane przy starcie (`init_constructor_runtime.py:388`) i po przywróceniu backupu: `apply_background_image()` (`game_launcher.py:1548`) kładzie `tk.Label` z obrazem pod wszystkimi widgetami (bez skalowania).
- `select_background_image()` (`game_launcher.py:1540`) istnieje, ale **nie ma żadnego widgetu w ustawieniach**, który by ją wywoływał.

---

### Sekcja „Użytkownik”

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| (podgląd awatara + „Nazwa: …”) | `ttk.Label` z obrazem | `config.user.avatar`, `config.user.username` | `"Gracz"` | `_load_and_display_settings_avatar()` (`settings_avatar.py:9`): miniatura; gdy brak pliku → generowany kwadrat `#444444` z pierwszą literą nazwy (Arial Bold). |
| Zmień Nazwę Użytkownika | `ttk.Button` → `simpledialog` | `config.user.username` | – | `change_username()` (`game_launcher.py:1637`): zapis, przebudowa strony głównej. |
| Ścieżka Awatara: | `ttk.Entry` readonly + „Wybierz...” | `config.user.avatar` | `""` | `select_avatar()` (`game_launcher.py:1965`): plik PNG/JPG kopiowany do `images/avatar.png`. |
| Usuń Awatar | `ttk.Button` | j.w. | – | `delete_avatar()` (`game_launcher.py:2024`): **usuwa plik z dysku**, czyści klucz. |
| Rozmiar Awatara: | `ttk.Spinbox` readonly, wartości 32/48/64/96/128 | `local_settings.avatar_display_size` | `48` | `_save_and_refresh_avatar_size()` (`game_launcher.py:2728`): zapis, odświeżenie podglądu i strony głównej. |
| Usuń Konto Czatu | `ttk.Button` (styl `Red.TButton`) | – (serwer czatu) | – | `_confirm_delete_chat_account()` (`chat_user_profile.py:166`): wymaga zalogowania, 2-stopniowe potwierdzenie + hasło, żądanie do serwera czatu. |

---

### Sekcja „System”

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| Uruchamiaj z systemem Windows | `ttk.Checkbutton` | `config.settings.autostart` | `False` | `toggle_autostart()` (`game_launcher.py:1603`): wpis w `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, nazwa `GameLauncher`, wartość `sys.executable + " " + abspath(__file__)`; odznaczenie usuwa wpis. |
| Automatycznie twórz backup zapisów przy zamknięciu gry (nadpisuje poprzedni) | `ttk.Checkbutton` | `config.settings.auto_backup_on_exit` | `True` | `_save_auto_backup_setting()` (`game_launcher.py:2849`). Używane w `session_monitor_runtime.py:50`: po zakończeniu gry → `_create_or_overwrite_autosave(game)`. |
| Resetuj licznik Launchera | `ttk.Button` | `local_settings.total_launcher_usage_seconds` | – | `reset_launcher_usage_time()` (`usage_runtime.py:46`): potwierdzenie, zerowanie łącznego czasu w launcherze. |

Brak przełączników dla: minimalizacji do zasobnika (zawsze aktywna – `<Unmap>` → `on_minimize` → `withdraw()` + ikona pystray, `tray_runtime.py:23`), powiadomień systemowych (plyer – przypomnienia i osiągnięcia, zawsze włączone), potwierdzenia wyjścia (zawsze `askokcancel`).

---

### Sekcja „Klucze API i Synchronizacja”

**Klucze API** (wszystkie w `local_settings`, pole `show="*"`, checkbox „Pokaż” → `toggle_show_key()` w `rawg_settings.py:6`, przycisk „?” z instrukcją):

| Etykieta | Klucz | Zmienna środowiskowa (nadpisuje plik) | Przycisk zapisu / handler |
|---|---|---|---|
| GitHub Token: | `github_token` | `GL_GITHUB_TOKEN` | „Zapisz GitHub Token” → `save_github_token()` (`game_launcher.py`) – pusty = ostrzeżenie (nie usuwa). Pomoc: `show_github_token_help` (wymagany scope `repo`). |
| RAWG.io API Key: | `rawg_api_key` | `GL_RAWG_API_KEY` | „Zapisz RAWG Key” → `save_rawg_api_key()` (`rawg_settings.py:13`) – pusty = usunięcie klucza. |
| Last.fm API Key: | `lastfm_api_key` | `GL_LASTFM_API_KEY` | „Zapisz Last.fm Key” → `_save_lastfm_api_key()` (`game_launcher.py:2887`) – pusty = usunięcie. Używany do okładek albumów. |

**Usługi Chmurowe do Synchronizacji:**

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| Google Drive | `ttk.Checkbutton` | `config.settings.cloud_service_google_drive` | `False` | `update_cloud_services()` (`game_launcher.py:1596`) |
| GitHub | `ttk.Checkbutton` | `config.settings.cloud_service_github` | `False` | j.w. |
| Prześlij | `ttk.Button` | – | – | `upload_to_cloud()` (`game_launcher.py:1698`): wątek + okno postępu (kolejka `progress_queue`). |
| Pobierz | `ttk.Button` | – | – | `download_from_cloud()` (`game_launcher.py:1793`). |

- **GitHub** (`cloud_github_runtime.py`): repozytorium `game_launcher_saves` na koncie właściciela tokena (tworzone automatycznie przez `user.create_repo(...)` gdy brak). Wysyła/pobiera: `config.json`, `achievements_def.json`, opcjonalnie `local_settings.json` (tylko gdy `config.settings.sync_local_settings_to_cloud == True` – brak przełącznika w UI, domyślnie `False`), foldery `games_saves/` i `images/`.
- **Google Drive** (`setup_google_drive`, `game_launcher.py`): OAuth z `credentials.json` w CWD, token w `token_google_drive.pickle`, scope `drive.file`. Pobieranie: szuka pliku `config.json` w Drive i nadpisuje lokalny `CONFIG_FILE`.

**Lokalny Backup:**

| Przycisk | Handler | Działanie |
|---|---|---|
| Zgraj Backup | `backup_to_local_folder()` (`backup_restore.py:57`) | Wybór folderu → tworzy `GameLauncher_Backup_YYYYMMDD_HHMMSS/` i kopiuje (wątek + pasek postępu): `config.json`, `local_settings.json`, `achievements_def.json` (pliki), `games_saves/`, `images/`, `internal_music/`, `custom_themes/` (foldery). Brakujące źródła są pomijane. Przy błędzie krytycznym niekompletny folder jest usuwany. Format: zwykła kopia katalogów (bez ZIP). |
| Wczytaj Backup | `load_local_backup()` (`backup_restore.py:230`) | Wybór folderu backupu → ostrzeżenie o nadpisaniu → te same 7 elementów kopiowane do `APP_DIR` (foldery najpierw usuwane `rmtree`). Potem przeładowanie: `load_config`, `load_local_settings`, definicje osiągnięć, motyw, czcionka, tło, sidebar, strona główna, siatka, stan odtwarzacza (playlisty, ulubione, indeks). |

`_perform_backup_restore_thread` (`backup_restore.py:517`) – starsza, wieloetapowa ścieżka przywracania; wrapper w `game_launcher.py:2482`, bez wywołań z UI.

---

### Sekcja „Skanowanie Screenshotów”

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| (lista folderów) | `tk.Listbox` (4 wiersze) + „Dodaj” / „Usuń” | `config.settings.autoscan_screenshot_folders` | `[]` | `add_autoscan_folder` / `remove_autoscan_folder` (`screenshot_scan_runtime.py:49/70`) |
| Skanuj screenshoty automatycznie przy uruchomieniu launchera | `ttk.Checkbutton` | `config.settings.autoscan_on_startup` | `False` | `_save_autoscan_startup_setting()`; używane w `init_constructor_runtime.py:532`. |
| Skanuj Screenshoty Teraz (Wszystkie Gry) | `ttk.Button` | – | – | `start_scan_screenshots_thread()` (`screenshot_scan_runtime.py:99`) |
| Nazwy folderów do ignorowania podczas skanowania screenshotów (jedna na linię): | `tk.Text` (4 wiersze) + „Zapisz Ignorowane Foldery Screenshotów” | `config.settings.screenshot_scan_ignore_folders` | `["thumb_cache","cache","temp","thumbnails"]` | `save_screenshot_ignored_folders()` (`screenshot_scan_runtime.py:29`): lowercase, deduplikacja, sortowanie. |

Ukryty (bez UI) klucz: `config.settings.screenshot_filename_patterns` (domyślnie `["{game_name}*.png","{game_name}*.jpg","{game_name}*.jpeg"]`).

---

### Sekcja „Emulatory”

- `ttk.Treeview` (kolumny „Nazwa Emulatora”, „Ścieżka do .exe”, 4 wiersze) + przyciski „Dodaj Emulator”, „Edytuj Zaznaczony”, „Usuń Zaznaczony” (`emulator_settings_runtime.py`).
- Klucz: `config.emulators` (top-level, **nie** w `settings`) = `{ "<nazwa>": {"path": "<exe>"} }`.
- Dialog „Dodaj/Edytuj Emulator”: „Nazwa Emulatora:” (Entry), „Ścieżka do .exe:” (Entry + „Wybierz...” – filtr `*.exe`), „Zapisz”/„Anuluj”. Walidacja: oba pola wymagane, plik musi istnieć, nazwa unikalna. Zmiana nazwy przy edycji usuwa stary wpis.
- Usunięcie z potwierdzeniem. Po zmianie odświeżane są otwarte Toplevel-e mające metodę `update_emulator_list()`.

---

### Sekcja „Newsy (RSS)”

| Element | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| Zarządzanie Kanałami RSS: | dynamiczna lista: `Checkbutton` (nazwa kanału) + „Usuń” na wiersz | `config.settings.rss_feeds` = `[{url, active, name}]` | `[{"url":"https://feeds.ign.com/ign/games-all","active":true,"name":"IGN Games"}]` | checkbox → `update_rss_feeds()` (`news_runtime.py:141`); „Usuń” → `remove_specific_rss_feed()` (`news_runtime.py:118`). |
| Dodaj Kanał RSS | `ttk.Button` → 2× `askstring` (URL, nazwa opcjonalna) | j.w. | – | `add_rss_feed_from_settings()` (`settings_runtime.py:64`): odrzuca duplikat URL, odświeża newsy jeśli strona newsów otwarta. |
| Liczba wyświetlanych newsów: | `ttk.Spinbox` 1–100 | `config.settings.news_post_limit` | `10` | `update_post_limit()` (`news_runtime.py:231`) + przeładowanie newsów. Uwaga: wywoływane tylko strzałkami spinboxa (`command`), wpisanie ręczne nie zapisuje. |

Migracja: stara lista stringów `rss_feeds` → lista obiektów (`config_store.py:290`).

---

### Sekcje „Narzędzia Biblioteki”, „Aktualizacje Aplikacji”, „Narzędzia Deweloperskie”

| Sekcja | Element | Handler | Działanie |
|---|---|---|---|
| Narzędzia Biblioteki | Znajdź Potencjalne Duplikaty | `start_duplicate_scan_thread()` (`duplicates_ui.py:22`) | Skan duplikatów gier (normalizacja nazw), okno wyników z Treeview. |
| Aktualizacje Aplikacji | Sprawdź Aktualizacje Teraz | `manual_check_updates()` (`updater_runtime.py:117`) | Pobiera `https://api.github.com/repos/snakex21/Game-Launcher/releases`. |
| Aktualizacje Aplikacji | „Aktualna wersja: 1.5.0” | `PROGRAM_VERSION` (`utils.py:5`) | etykieta |
| Narzędzia Deweloperskie | Pokaż Konsolę Deweloperską | `_show_developer_console()` (`app_navigation.py:80`) | Okno 500×700 z czasami punktów kontrolnych startu (`start_up_time_points`, ms). |

---

### Sekcja „Integracja z Discord”

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| Włącz Discord Rich Presence (pokaż status w Discord) | `ttk.Checkbutton` | `local_settings.discord_rpc_enabled` | `False` | `_toggle_discord_rpc()` (`discord_runtime.py:125`): start/stop pypresence RPC; przy starcie aplikacji łączy się, jeśli włączone (`init_constructor_runtime.py:509`). |
| Tekst statusu (gdy w menu): | `ttk.Entry`, zapis na `<FocusOut>` | `local_settings.discord_status_text` | `"Korzysta z Game Launcher"` | `_save_discord_settings()` (`discord_runtime.py:290`). |

Statusy RPC: `idle`, `browsing` (np. „Zmienia Ustawienia”), w grze (nazwa gry, profil, czas startu); duży obraz `gl_logo`.

---

### Sekcja „Zdalne Sterowanie (Telefon/Przeglądarka)”

| Etykieta | Widget | Klucz | Domyślnie | Efekt |
|---|---|---|---|---|
| Włącz zdalne sterowanie (uruchamianie gier przez przeglądarkę) | `ttk.Checkbutton` | `local_settings.remote_control_enabled` | `False` | `_toggle_remote_server()` (`remote_server_runtime.py:163`): start/stop serwera Flask (`launcher/remote_app.py`: `/`, `/api/games`, `/api/status`, `/api/launch/<gra>` POST, `/api/close/<gra>` POST, `/cover/<gra>`). Autostart przy uruchomieniu, jeśli włączone. |
| Adres z tokenem (…kto go zna, może uruchamiać gry): | `ttk.Label` (zielony gdy działa, szary „Serwer wyłączony”) | – | – | `_update_server_status_ui` |
| Port serwera: | `ttk.Entry` (IntVar) + „Zapisz Port” | `local_settings.remote_control_port` | `5050` | `_save_remote_port()` (`:180`): zakres 1025–65534, port 5000 zabroniony (czat), restart serwera, jeśli działa. Migracja: port 5000 → 5050 (`config_store.py:204`). |
| Nowy token | `ttk.Button` | `local_settings.remote_control_token` (env `GL_REMOTE_TOKEN`) | generowany przy pierwszym starcie (`generate_token()`) | `_regenerate_remote_token()` (`:241`): nowy token, restart serwera, stare linki przestają działać. |
| Dostępny w sieci lokalnej (…). Domyślnie tylko ten komputer (127.0.0.1). | `ttk.Checkbutton` | `local_settings.remote_control_bind_lan` | `False` | `_toggle_remote_lan()` (`:231`): zmiana hosta nasłuchu, restart serwera. |

---

### Sekcja „Skróty Klawiszowe Odtwarzacza Muzyki”

| Etykieta | Widget | Klucz | Domyślnie |
|---|---|---|---|
| Włącz globalne skróty klawiszowe dla odtwarzacza muzyki | `ttk.Checkbutton` | `local_settings.music_hotkeys_enabled` | `True` |
| Odtwórz / Pauza: | `Entry` readonly + „Ustaw” | `local_settings.music_hotkeys.play_pause` | `<alt>+<space>` |
| Następny utwór: | j.w. | `music_hotkeys.next_track` | `<alt>+<right>` |
| Poprzedni utwór: | j.w. | `music_hotkeys.prev_track` | `<alt>+<left>` |
| Zatrzymaj: | j.w. | `music_hotkeys.stop_music` | `<alt>+s` |
| Głośniej: | j.w. | `music_hotkeys.volume_up` | `<alt>+<up>` |
| Ciszej: | j.w. | `music_hotkeys.volume_down` | `<alt>+<down>` |
| Przywróć Domyślne Skróty | `ttk.Button` | `music_hotkeys` ← `DEFAULT_MUSIC_HOTKEYS` | – |

- Przełącznik (`_toggle_music_hotkeys_enabled`, `game_launcher.py:2761`): zapis, rejestracja/zatrzymanie `pynput.keyboard.GlobalHotKeys`, wyłączenie (`disabled`) pól i przycisków.
- „Ustaw” → `_set_music_hotkey_dialog()` (`hotkey_capture.py:8`): modalne okno 350×130 „Naciśnij nową kombinację klawiszy dla: '…'”, podgląd na żywo, „Anuluj”/zamknięcie okna = `_cancel_hotkey_capture`. Na czas przechwytywania zatrzymuje globalne skróty i uruchamia `keyboard.Listener(suppress=True)` (blokuje klawiaturę w całym systemie do zwolnienia klawisza).
- Budowa ciągu (`hotkey_input.py:55`): modyfikatory `<ctrl>`, `<alt>`, `<shift>`, `<cmd>` (sortowane alfabetycznie) + klawisz główny (pojedynczy znak alfanumeryczny bez nawiasów, pozostałe jako `<nazwa>`), łączone `+`. Finalizacja po zwolnieniu klawisza niebędącego modyfikatorem; sam modyfikator = błąd i przywrócenie poprzedniego skrótu. Zapis do `local_settings.music_hotkeys` i ponowna rejestracja.
- „Przywróć Domyślne Skróty” (`_reset_music_hotkeys`, `game_launcher.py:2795`): potwierdzenie, zapis, re-rejestracja.

---

### Ustawienia serwerów czatu (poza stroną Ustawień)

Zarządzanie serwerami czatu jest na osobnej stronie **„Zarządzanie Serwerami Czatu”** (`server_selection.py:47`, wejście z ekranu logowania czatu / czatu głównego):

| Element | Widget | Klucz | Efekt |
|---|---|---|---|
| Lista serwerów | `ttk.Treeview` (Nazwa Serwera, Adres URL, Domyślny?) – domyślny na górze, aktywny wyróżniony | `local_settings.chat_servers` | – |
| ➕ Dodaj Serwer / ✏️ Edytuj Zaznaczony | `ChatServerEditorDialog` (`ui/dialogs.py:1031`): „Nazwa Serwera:”, „Adres URL Serwera:”, checkbox „Ustaw jako domyślny serwer” | element listy | Walidacja: nazwa niepusta i unikalna (bez wielkości liter), URL `http(s)://`. Ustawienie domyślnego odznacza pozostałe. Zmiana URL czyści zapamiętane dane logowania. |
| ❌ Usuń Zaznaczony | `ttk.Button` | j.w. | Przy usunięciu aktywnego/domyślnego wybiera następny. |
| 🔗 Połącz z Zaznaczonym | `ttk.Button` (`Green.TButton`) | `local_settings.active_chat_server_id`, `last_used` | Przełącza aktywny serwer i łączy. |
| Automatycznie łącz z domyślnym serwerem przy starcie launchera | `ttk.Checkbutton` | `local_settings.chat_auto_connect_to_default` (domyślnie `True`) | `_save_auto_connect_setting()` |

Struktura wpisu serwera: `{id (uuid), name, url, is_default, last_used, credentials: {email, password}, remember_credentials, auto_login_to_server}`. Na ekranie logowania czatu (`chat_layout.py:61/77`) checkboxy „Zapamiętaj dane logowania” i „Automatyczne logowanie” zapisują `remember_credentials` / `auto_login_to_server` aktywnego serwera; hasło trafia jawnym tekstem do `credentials.password` w `local_settings.json`.

`launcher/chat_server_settings.py` (`_open_chat_server_settings_dialog`, `_save_chat_server_url`) – stary dialog jednego URL-a (`local_settings.chat_server_url`); nie jest nigdzie wywoływany.

---

### Inne ustawienia (bez UI w Ustawieniach)

- **Język**: `change_language()` (`game_launcher.py:913`) zapisuje `config.settings.language` i woła `translator.set_language` + `refresh_ui()`; brak kontrolki w Ustawieniach.
- **Foldery skanowania gier / ignorowane foldery skanowania**: `show_settings()` woła `load_scan_folders_list()` i `load_ignored_folders()`, ale widgety `scan_folders_listbox` / `ignored_folders_text` nie są tworzone na tej stronie (klucze `config.settings.scan_folders`, `scan_ignore_folders`, `scan_recursively`).
- **Okno**: `local_settings.window_geometry` (`"1024x768+100+100"`), `window_state` (`normal`/`zoomed`), `window_maximized` – zapisywane przy zamknięciu (`closing_runtime.py`).
- **Widok biblioteki**: `local_settings.library_view_mode` (`tiles`/lista).
- **Odtwarzacz muzyki** (ustawiane w odtwarzaczu): `music_player_volume`, `last_music_folder`, `named_music_playlists`, `active_music_playlist_name`, `current_track_in_active_playlist_index`, `music_repeat_mode`, `music_shuffle_mode`, `music_favorite_tracks`, `music_autoplay_enabled`.
- **Tryb Big Picture** (automatycznie po wykryciu pada): nadpisuje w pamięci `tiles_per_row` (3 przy wejściu, 5 przy wyjściu) i czcionki TLabel/Tile.TButton (`game_launcher.py:966-989`).

---

### Przechowywanie konfiguracji i migracje (`launcher/config_store.py`, `launcher/utils.py`, `launcher/paths.py`)

**Lokalizacje** (względem `APP_DIR` = folder exe lub katalog repo; punkt wejścia robi `chdir(APP_DIR)`):

| Plik / folder | Ścieżka | Zawartość |
|---|---|---|
| `CONFIG_FILE` | `data/config/config.json` | gry, ustawienia, grupy, użytkownik, emulatory, filtry, roadmapa |
| `LOCAL_SETTINGS_FILE` | `data/config/local_settings.json` | ustawienia lokalne i sekrety (ignorowany przez git) |
| `ACHIEVEMENTS_DEFINITIONS_FILE` | `data/config/achievements_def.json` | definicje osiągnięć |
| `GAMES_FOLDER` | `data/games_saves/` | kopie zapisów gier |
| `CHAT_DB_FILE` | `data/chat/chat.db` | baza czatu |
| `IMAGES_FOLDER` | `images/` (względna) | okładki, awatar |
| `INTERNAL_MUSIC_DIR` | `internal_music/` (względna) | wewnętrzna biblioteka muzyki |
| `CUSTOM_THEMES_DIR` | `custom_themes/` (względna) | motywy użytkownika |
| `SCRIPTHOOK_CONFIG_FILE` | `external/ScriptHookConfig.ini` | – |

**Migracje:**
- Pliki z korzenia aplikacji → `data/config/` (`_migrate_legacy_file`: `config.json`, `local_settings.json`) i `games_saves/` → `data/games_saves/` (`_migrate_legacy_directory`, `os.replace` lub copytree+rmtree), tylko gdy cel nie istnieje.
- Czat: stare klucze `chat_server_url`, `chat_email`, `chat_password`, `chat_remember_me`, `chat_auto_login` → jeden wpis w `chat_servers` („Domyslny Serwer (migr.)”). Gdy brak serwerów → „Serwer Lokalny (Domyslny)” `http://127.0.0.1:5000`.
- `remote_control_port == 5000` → `5050`.
- `rss_feeds` (stringi) → obiekty.
- Gry: zapewnienie profilu uruchomieniowego `Default` na pozycji 0 w `launch_profiles`; domyślne `screenshots`, `autoscan_screenshots`, `checklist`.
- `version` podbijana do `PROGRAM_VERSION`, gdy starsza.
- Przenośność ścieżek (`paths.py`): `save_config` zapisuje ścieżki gier bez litery dysku / względnie do launchera i zapamiętuje `settings.launcher_drive`; `load_config` → `resolve_config_paths` przemapowuje po zmianie litery dysku.
- Sekrety: zmienne `GL_GITHUB_TOKEN`, `GL_RAWG_API_KEY`, `GL_LASTFM_API_KEY`, `GL_REMOTE_TOKEN` nadpisują wartości z pliku i **nie są zapisywane** z powrotem (`_strip_env_overrides`). `redact_settings()` maskuje sekrety/hasła w logach.
- Błędny JSON: `config.json` → nowy domyślny config (log błędu); `local_settings.json` → `{}` + wartości domyślne.

**Domyślne wartości `local_settings` nadawane przez `load_local_settings()`** (`config_store.py:201-237`):
`chat_auto_connect_to_default=True`, `remote_control_enabled=False`, `remote_control_port=5050`, `remote_control_bind_lan=False`, `window_state="normal"`, `window_geometry="1024x768+100+100"`, `library_view_mode="tiles"`, `tiles_per_row=3`, `discord_rpc_enabled=False`, `discord_status_text="Korzysta z Game Launcher"`, `ui_font="Segoe UI"`, `window_maximized=False`, `last_run_date=""`, `consecutive_days=0`, `total_launcher_usage_seconds=0`, `chat_remember_me=False`, `chat_auto_login=False`, `avatar_display_size=48`, `music_player_volume=0.5`, `last_music_folder=~`, `music_hotkeys=DEFAULT_MUSIC_HOTKEYS`, `music_hotkeys_enabled=True`, `named_music_playlists={}`, `active_music_playlist_name=None`, `current_track_in_active_playlist_index=-1`, `chat_last_email=""`, `chat_last_user_id=None`, `music_repeat_mode="none"`, `music_shuffle_mode=False`, `music_favorite_tracks=[]`, `launcher_daily_usage_seconds={}`, `show_track_overlay=False`, `overlay_x_pos=None`, `overlay_y_pos=None`, plus `chat_servers`, `active_chat_server_id`. Inne klucze zapisywane w kodzie: `github_token`, `rawg_api_key`, `lastfm_api_key`, `remote_control_token`, `chat_blocked_user_ids`, `music_autoplay_enabled`.

**Domyślne wartości `config.json`** (`_default_config` + `load_config`): top-level `version`, `games`, `settings`, `groups`, `user` (`achievements`), `emulators`, `saved_filters`; w `settings`: `rss_feeds`, `news_post_limit=10`, `scan_ignore_folders=["_CommonRedist","DirectX","DotNet","Redist","Tools","Benchmark","support","data","__overlay"]`, `scan_recursively=True`, `autoscan_screenshot_folders=[]`, `autoscan_on_startup=False`, `screenshot_scan_ignore_folders`, `screenshot_filename_patterns`. Inne klucze `settings` używane w kodzie: `theme`, `language`, `autostart`, `auto_backup_on_exit`, `background_image`, `cloud_service_google_drive`, `cloud_service_github`, `sync_local_settings_to_cloud`, `custom_genres`, `scan_folders`, `launcher_drive`. W `user`: `username`, `avatar`, `theme_change_count`, osiągnięcia. Inne top-level ustawiane przy starcie: `mods_data`, `archive`, `roadmap`.

**Pliki przykładowe w repo:**
- `config.example.json`: `games`, `settings` {`theme:"dark"`, `language:"pl"`, `font`, `autostart`, `background_image`, `scan_folders`, `scan_recursive`, `ignored_folders`, `cloud_service_google_drive`, `cloud_service_github`, `discord_rpc_enabled`, `rawg_api_key`, `rawg_auto_fetch`, `custom_genres`, `screenshot_folders`, `screenshot_scan_recursive`, `screenshot_scan_on_startup`, `emulators: []`}, `groups`, `user` {`username:"Player"`, `avatar`, `achievements`, `total_launcher_time`, `consecutive_days`, `last_login_date`, `theme_changes`}, `roadmap`.
- `local_settings.example.json` (komentarz: kopiować do `data/config/local_settings.json`): `github_token`, `rawg_api_key`, `lastfm_api_key`, `tiles_per_row: 5`, `library_view_mode: "tiles"`, `music_player_volume: 0.5`, `music_hotkeys_enabled`, `music_hotkeys` (= domyślne), `show_track_overlay`, `discord_rpc_enabled`, `chat_servers` [lokalny `http://127.0.0.1:5000`], `active_chat_server_id: "local"`, `remote_control_enabled`, `remote_control_port: 5050`, `remote_control_bind_lan`, `remote_control_token`.

---

**Uwagi** (rzeczy wyraźnie zepsute / niespójne):
- `_save_discord_settings()` (`discord_runtime.py:297`) odwołuje się do `self.discord_rpc_enabled`, które nigdzie nie jest zdefiniowane → `AttributeError` przy zmianie tekstu statusu (na FocusOut).
- „Prześlij” z zaznaczonym Google Drive woła `self.do_upload_to_google_drive()` (`game_launcher.py:1911`) – metoda nie istnieje → wyjątek w wątku.
- `_save_chat_server_url()` (`chat_server_settings.py:75`) używa niezdefiniowanego `active_server_data` (NameError); moduł martwy.
- GitHub sync tworzy repo `game_launcher_saves` przez `create_repo(name)` bez `private=True` → domyślnie **publiczne** (z `config.json`, zapisami i obrazami).
- Autostart zapisuje `sys.executable + " " + __file__` bez cudzysłowów; w buildzie PyInstallera ścieżka jest błędna (exe + ścieżka .py w paczce).
- `select_background_image()` używa nieistniejącego `self.background_image_var`, a w UI brak przycisku tła; `scan_folders_listbox`/`ignored_folders_text` i wybór języka też nie mają widgetów.
- Niespójne domyślne `tiles_per_row` (UI 4 / config_store 3 / example 5 / Big Picture 3↔5, nadpisywane bez pytania).
- `config.example.json` używa innych nazw kluczy niż kod (`theme:"dark"` vs `"Dark"`, `scan_recursive` vs `scan_recursively`, `screenshot_folders`/`screenshot_scan_on_startup` vs `autoscan_screenshot_folders`/`autoscan_on_startup`, `emulators` w `settings` jako lista vs top-level dict, `theme_changes` vs `theme_change_count`, `discord_rpc_enabled` w config zamiast local_settings).
- Edytor motywów sprawdza duplikat nazwy w przestarzałym `settings.custom_themes`, a nie w plikach → „Dodaj” po cichu nadpisuje istniejący plik motywu.
- Po przywróceniu backupu `apply_theme(THEMES.get(theme))` obsługuje tylko motywy wbudowane (niestandardowy → fallback Dark).
- Hasła czatu zapisywane jawnym tekstem w `local_settings.json`.

## 3. Integracje

Ścieżki względem katalogu repo `Game_Launcher_git` (gałąź `polish/v1.5.0`). Wszystkie metody `launcher/*_runtime.py` przyjmują `self` = instancja `GameLauncher` (cienkie wrappery w `game_launcher.py`). Tekstowe źródła sekretów: `launcher/config_store.py:71-80` – każdy sekret może pochodzić ze zmiennej środowiskowej (nadpisuje plik, nie jest zapisywany z powrotem do pliku `:101-110`) albo z `data/config/local_settings.json`:

| klucz w local_settings | zmienna środowiskowa |
|---|---|
| `github_token` | `GL_GITHUB_TOKEN` |
| `rawg_api_key` | `GL_RAWG_API_KEY` |
| `lastfm_api_key` | `GL_LASTFM_API_KEY` |
| `remote_control_token` | `GL_REMOTE_TOKEN` |

Porty domyślne: czat 5000, pilot WWW 5050 (`config_store.py:83-84`). Wersja programu `PROGRAM_VERSION = "1.5.0"` (`launcher/utils.py:5`). W kodzie nie znaleziono zahardkodowanych kluczy API/tokenów (hasło admina czatu pochodzi z env, patrz niżej).

---

### 3.1 RAWG.io (metadane gier + okładki)

Pliki: `launcher/rawg_fetch_runtime.py`, `launcher/rawg_cover.py`, `launcher/rawg_settings.py`, UI: `ui/game_details.py`, `launcher/settings_page_content.py:389-436`.

- **Klucz API**: `self.local_settings["rawg_api_key"]` (`rawg_fetch_runtime.py:12`) lub env `GL_RAWG_API_KEY`. Zapis z pola w Ustawieniach → `save_rawg_api_key` (`rawg_settings.py:14-27`): niepusty → zapis, pusty → usunięcie klucza. Pomoc „?” – instrukcja z rawg.io (`rawg_settings.py:30-41`). Brak klucza → `messagebox` „Brak klucza API” (`rawg_fetch_runtime.py:13-19`).
- **Wywołanie**: `start_fetch_details_thread(game_name, details_window, force)` (`rawg_fetch_runtime.py:11-34`) – blokuje przycisk „Pobieranie...”, uruchamia wątek daemon z `fetch_rawg_game_details`; wynik wraca przez `root.after(0, callback, result)` do `details_window._on_details_fetched`.
- **Żądania HTTP** (`rawg_fetch_runtime.py:37-146`), nagłówek `User-Agent: GameLauncher/<PROGRAM_VERSION>`, timeout 15 s:
  1. `GET https://api.rawg.io/api/games?key=<KEY>&search=<nazwa gry>&page_size=1` → bierze `results[0].id` i `results[0].slug`. Pusty `results` → błąd „Nie znaleziono gry w bazie RAWG.”.
  2. `GET https://api.rawg.io/api/games/<id>?key=<KEY>`.
- **Wyciągane pola** (`:79-113`):
  - `description` ← `description_raw`
  - `release_date` ← `released`
  - `website` ← `website`
  - `developers` ← `developers[].name`
  - `publishers` ← `publishers[].name`
  - `genres_api` ← `genres[].name`
  - `tags_api` ← `tags[].name`
  - `platforms` ← `platforms[].platform.name`
  - `requirements_pc` ← `{minimum, recommended}` z wpisu `platforms[]` o `platform.slug == "pc"` (jeśli ma `requirements`)
  - `background_image` → pobierany jako okładka (`downloaded_cover_path`).
  - `rawg_id`, `rawg_slug` zapisywane od razu do `self.games[game_name]` (`:68-69`, z wątku roboczego).
- **Pobranie okładki** (`rawg_cover.py:11-70`): `GET <background_image>` (stream, timeout 20 s); rozszerzenie z `Content-Type` (jpeg/png/webp/gif/bmp), fallback z końcówki URL, domyślnie `.jpg`. Zapis do `images/<nazwa_gry_bez_znaków \/*?:"<>|>_rawg_cover<ext>` (ścieżka względna, `IMAGES_FOLDER = "images"`, `utils.py:27`). Zwraca ścieżkę względną.
- **Zapis wyników** (`ui/game_details.py:1546-1638`):
  - `cover_rawg` = ścieżka pobranej okładki (zawsze, jeśli plik istnieje).
  - `cover_image` = okładka RAWG tylko gdy: `force` (przycisk „Pobierz/Użyj Okładki z RAWG” / „Pobierz Ponownie z RAWG”), albo gra ma flagę `_auto_cover` (placeholder), albo brak/nieistniejąca obecna okładka. Wtedy usuwa `_auto_cover`.
  - Pola `rawg_id, rawg_slug, description, release_date, website, developers, publishers, genres_api, tags_api, platforms, requirements_pc` nadpisywane, jeśli różne; `save_config` tylko przy zmianie.
  - Menu kontekstowe okładki (`game_details.py:1741-1760`): „Użyj Okładki z RAWG” (używa zapisanej `cover_rawg` bez sieci, `fetch_cover_from_rawg(force=False)` `:1714-1739`), „Pobierz Ponownie z RAWG” (force=True).
- **Uwagi**: tylko pierwszy wynik wyszukiwania (brak wyboru przy niejednoznacznych nazwach); zapis do `self.games` z wątku tła (`rawg_fetch_runtime.py:68-69`); niespójny tekst przycisku po zakończeniu („Pobierz dane” vs „Pobierz Dane”, `rawg_fetch_runtime.py:28` / `game_details.py:1544`).

---

### 3.2 Last.fm (tylko okładki muzyczne)

Plik: `ui/music_player.py` (lib `pylast`, ładowany leniwie w `_ensure_music_dependencies` `:25-36`).

- **Brak scrobblingu i „now playing”** – jedyne użycie Last.fm to pobieranie okładek albumów. Brak `api_secret`/sesji, używany jest tylko `api_key`.
- **Klucz**: `self.launcher.local_settings["lastfm_api_key"]` (`music_player.py:4301`, `:4529`) lub env `GL_LASTFM_API_KEY`; zapis z Ustawień `game_launcher.py:2888-2904` (pole `settings_page_content.py:411-441`).
- **Algorytm** `_fetch_and_set_lastfm_cover` (`music_player.py:4281-4494`), w wątku (`_start_lastfm_cover_fetch_thread` `:4496-4511`):
  1. Tagi z pliku przez `mutagen` (`MutagenFile(path, easy=True)`): `artist`/`TPE1`, `album`/`TALB`, `title`/`TIT2` (`:4253-4279`). Wymagane: artysta oraz album lub tytuł.
  2. `pylast.LastFMNetwork(api_key=...)`; jeśli jest album → `network.get_album(artist, album).get_cover_image(size)` (album.getInfo) próbując rozmiarów MEGA → EXTRA_LARGE → LARGE → MEDIUM.
  3. Fallback: `network.get_track(artist, title).get_album().get_cover_image(...)` (track.getInfo).
  4. `GET <cover_url>` (stream, timeout 20 s); rozszerzenie `.png` gdy Content-Type zawiera png, inaczej `.jpg`.
  5. Zapis: `images/music_covers/lastfm/<artist>_<album lub tytuł>_lastfm<ext>` (nazwa obcięta do 150 znaków, `:4395-4400`).
  6. W wątku GUI: wpis utworu w aktywnej playliście dostaje `lastfm_cover_path`; `focus_cover_path` ustawiane, jeśli `force_update_focus_cover` lub było puste (`:4411-4433`); zapis ustawień odtwarzacza i przeładowanie playlisty.
- **Wejścia z UI**: menu kontekstowe utworu „🌍 Pobierz okładkę (Last.fm)” (`:2594-2595`); przycisk „Pobierz okładki z Last.fm dla wszystkich utworów w aktywnej playliście” (`:720-725`) → `_fetch_covers_for_active_playlist` (`:4513-4609`): osobny wątek na każdy utwór, odstęp 0,25 s, okno postępu, podsumowanie „Pomyślnie / Nie znaleziono”.
- Przy usuwaniu utworu z playlist okładka LastFM jest kasowana, jeśli leży w zarządzanym folderze i nie jest używana gdzie indziej (`:3196-3251`, `:5140-5155`).
- **Uwagi**: brak scrobblingu – w portowaniu do Go wystarczą 2 metody REST Last.fm (`album.getInfo`, `track.getInfo`) z `api_key`.

---

### 3.3 Discord Rich Presence

Plik: `launcher/discord_runtime.py` (lib `pypresence`).

- **Client ID** (publiczny): `1300136792636522517` (`launcher/init_constructor_runtime.py:297`).
- **Włączanie**: `local_settings["discord_rpc_enabled"]` (domyślnie False, `config_store.py:212`); checkbox → `_toggle_discord_rpc` (`discord_runtime.py:125-142`). Start przy uruchomieniu (`init_constructor_runtime.py:509-510`, `root.after(100)`), tylko gdy użytkownik ma ustawioną nazwę (`_post_init_heavy_jobs` uruchamiane warunkowo, `:490-491`).
- **Połączenie** `_start_discord_rpc` (`:11-56`): `Presence(client_id).connect()`, następnie status „browsing”. Przy nieoczekiwanym wyjątku (nie `PyPresenceException`/`ConnectionRefusedError`) RPC jest wyłączane w ustawieniach + messagebox „Błąd Krytyczny RPC”.
- **Monitor** `_monitor_discord_connection` (`:59-86`): wątek daemon, co **30 s** sprawdza: włączone, brak `rpc` i brak trwającego łączenia → `root.after(0, _start_discord_rpc)`. To jedyna cykliczność; aktualizacje statusu są wyłącznie zdarzeniowe (brak timera odświeżania).
- **Logika statusu** `_update_discord_status(status_type, game_name, profile_name, start_time, activity_details)` (`:145-272`), priorytety:
  1. **W grze** (`status_type="in_game"` i `game_name`): `state="Gra w: <gra>"`, `details="Profil: <profil>"` (gdy profil ≠ "default") lub `"Uruchomiono z GL"`; jeśli gra muzyka – dopisek `" | 🎧 <utwór[:40]>"`, `small_image="music_note_icon"`, `small_text="Słucha muzyki"`; `large_image="gaming_status"`; `start=int(start_time)`.
  2. **Muzyka gra (bez gry)**: `state="Słucha Muzyki 🎧"`, `details=<utwór[:128]>`, `large_image="music_icon"`, `start = teraz − (monotonic − _start_time − _pause_acc)`.
  3. **browsing** z `activity_details`: `state = discord_status_text_var` (domyślnie „Korzysta z Game Launcher”, `config_store.py:213`), `details = activity_details`, `large_image="gl_logo"`.
  4. inaczej (idle): jak 3, `details = self.current_section` lub „W menu głównym”.
  - Wszystkie teksty obcinane do 128 znaków; **brak przycisków (`buttons`)**, brak `large_text`.
- **Wartości `current_section`/activity_details** wysyłane przy nawigacji: „Na Stronie Głównej” (`app_navigation.py:14`), „Zarządza Modami” (`:26`), „Przegląda Bibliotekę” (`:145`), „Przegląda Statystyki” (`stats_navigation.py:13`), „Przegląda Muzykę” (`music_navigation.py:17`), „Czat” (`chat_navigation.py:40`), „Przegląda Osiągnięcia” (`achievements_runtime.py:33`), „Sprawdza Przypomnienia” (`game_launcher.py:2005`), „Sprawdza Roadmapę” (`game_launcher.py:2366`).
- **Wyzwalacze**: uruchomienie gry → `in_game` (`game_process_runtime.py:127-132`); koniec sesji → `idle` (`session_monitor_runtime.py:48`); zmiany w odtwarzaczu muzyki (`music_player.py:3337-3345, 5188-5195, 5322, 5494, 5549-5556`).
- **Błędy**: `PyPresenceException` z „pipe” → `_stop_discord_rpc` (monitor połączy ponownie); inne → `_handle_rpc_connection_error` (`:89-122`) wyłącza RPC w ustawieniach.
- Zapis własnego tekstu statusu `_save_discord_settings` (`:290-299`).
- **Uwagi**: `_save_discord_settings` odwołuje się do `self.discord_rpc_enabled` (`:297`), które nigdzie nie jest przypisywane (istnieje tylko `discord_rpc_enabled_var`) → `AttributeError` przy zmianie tekstu statusu, gdy RPC aktywne. `_update_discord_status(idle)` wywoływane z wątku monitora sesji (odczyt `tk.BooleanVar` spoza wątku GUI).

---

### 3.4 Synchronizacja w chmurze – GitHub

Aktywna implementacja: `launcher/cloud_github_runtime.py` + orkiestracja w `game_launcher.py:1683-1935`. Lib: **PyGithub** (`from github import Github, GithubException`, import leniwy `cloud_github_runtime.py:18-21`) – **zakomentowana w `requirements.txt`** i nieobecna w hiddenimports specu.

- **Auth**: Personal Access Token z `local_settings["github_token"]` / env `GL_GITHUB_TOKEN`. Brak tokenu → `setup_github` (`game_launcher.py:1683-1696`) pyta `simpledialog` (show="*") i zapisuje. Pole tokenu w Ustawieniach `settings_page_content.py:374-430`.
- **Repozytorium** (nie gist): `game_launcher_saves` na koncie właściciela tokenu (`user.get_repo`); przy uploadzie tworzone, jeśli brak (`user.create_repo(repo_name)` – **publiczne**, bo bez `private=True`) (`cloud_github_runtime.py:76-83`). Przy download brak repo → komunikat (`:203-210`).
- **Wybór usług**: checkboksy „Google Drive”/„GitHub” → `settings["cloud_service_google_drive"]`, `settings["cloud_service_github"]` (`game_launcher.py:1596-1601`, UI `settings_page_content.py:448-477`); przyciski „Prześlij” (`upload_to_cloud`) i „Pobierz” (`download_from_cloud`).
- **Upload** (`upload_to_cloud` `game_launcher.py:1698-1727` → wątek `upload_to_cloud_thread` `:1908-1915` → `do_upload_to_github` `cloud_github_runtime.py:68-126`), komunikacja przez `self.progress_queue` (int = %, `"ERROR: ..."`, `"DONE"`), odpytywana co 100 ms w `check_progress_queue` (`game_launcher.py:1917-1935`):
  - `config.json` → `config.json` w repo (tekst UTF-8),
  - `achievements_def.json` → `achievements_def.json`,
  - `local_settings.json` – tylko gdy `settings["sync_local_settings_to_cloud"]` (domyślnie False, brak przełącznika w UI),
  - folder `data/games_saves/**` → `games_saves/<rel>` (binarnie),
  - folder `images/**` → `images/<rel>`.
  - Każdy plik: `get_contents` → `update_file(sha)`; przy 404 → `create_file` (1 commit na plik, wiadomość „Update/Create <nazwa>”).
- **Download** (`download_from_github` `:185-284`, w wątku GUI): pobiera te same pliki/foldery (rekurencyjnie po `get_contents` typu `dir`), nadpisuje lokalne, potem przeładowuje `config` (games/groups/user/mods_data/archive/roadmap), definicje osiągnięć, ewentualnie local_settings + `repair_save_paths()`, `refresh_ui()`, `show_home()`.
- **Konflikty**: brak – ostatni zapis wygrywa (upload nadpisuje zdalne, download nadpisuje lokalne); brak usuwania plików nieistniejących po drugiej stronie, brak porównania znaczników czasu.
- **Martwy kod**: `cloud/cloud_manager.py` – klasa `CloudManager` (repo `GameLauncherBackups`, prywatne, sync per-gra wg `save_path`) **nie jest nigdzie importowana**; dodatkowo odwołuje się do niezaimportowanych `Github`, `config_manager`, `datetime` (`cloud_manager.py:112,115,175,219`) – niedziałająca.
- **Uwagi (błędy)**:
  - `upload_folder_to_github` (`:146`) i `_download_single_file_from_github` (`:172`) łapią `GithubException`, które w tych funkcjach nie jest zdefiniowane → przy pierwszym wyjątku (np. 404 dla nowego pliku) `NameError`; w praktyce **tworzenie nowych plików w folderach i obsługa brakujących plików przy pobieraniu nie działa**.
  - Brak PyGithub → `ImportError` w wątku przed `try` (`:69`) → nic nie trafia do kolejki, okno postępu wisi.
  - `"DONE"` jest wrzucane dwa razy (`cloud_github_runtime.py:126` i `game_launcher.py:1915`).
  - Download wykonuje się synchronicznie w wątku Tk (UI zamrożone).

---

### 3.5 Google Drive

- `cloud/cloud_manager.py:59-99` – czyste stuby („nie jest jeszcze zaimplementowana”), klasa nieużywana.
- W `game_launcher.py` istnieje półimplementacja: `setup_google_drive` (`:1655-1681`; OAuth `InstalledAppFlow` z `credentials.json` w CWD, token w `token_google_drive.pickle`, scope `drive.file`), `upload_to_google_drive` (`:1808-1822`; wysyła tylko `config.json`), `download_from_google_drive` (`:1828-1865`; szuka pliku po nazwie, nadpisuje `config.json`).
- **Uwagi**: biblioteki Google zakomentowane w requirements; `upload_to_cloud_thread` woła **nieistniejącą** metodę `self.do_upload_to_google_drive()` (`game_launcher.py:1911`) → `AttributeError` w wątku. **Funkcja w praktyce nie działa – traktować jako stub.**

---

### 3.6 Aktualizator (GitHub Releases)

Plik: `launcher/updater_runtime.py` (libs `requests`, `packaging.version`).

- **Kiedy**: automatycznie w wątku przy starcie (`init_constructor_runtime.py:520`, `perform_update_check`), ręcznie przyciskiem w Ustawieniach (`settings_page_content.py:695`, `manual_check_updates` `:117-120`).
- **Sprawdzenie** `check_for_updates` (`:15-62`): `GET https://api.github.com/repos/snakex21/Game-Launcher/releases` (timeout 10 s, bez auth). Dla każdego wydania `tag_name.lstrip("v")`; porównanie `version.parse(tag) > version.parse(PROGRAM_VERSION)`; wydania bez `assets` pomijane; nieprawidłowe wersje logowane.
- **Wybór**: lista nowszych sortowana rosnąco i brany **najniższy** nowszy (`newer_versions[0]`, `:49-50`) – aktualizacja „krok po kroku”, nie do najnowszej. Asset: zawsze **`assets[0].browser_download_url`** (bez filtrowania po nazwie/typie).
- **Zastosowanie** `download_and_update` (`:84-114`): `askyesno` → pobranie (stream, **bez timeoutu**, w wątku GUI) do `%TEMP%\GameLauncher_Update.exe`; zapis `%TEMP%\updater.bat` (cp1250):
  ```
  timeout /t 3 /nobreak > NUL
  copy /Y "<nowy exe>" "<sys.executable>"
  start "" "<sys.executable>"
  del "<nowy exe>"
  del "%~f0"
  ```
  uruchomienie `cmd /c updater.bat` i `root.quit()`. Brak ZIP, brak weryfikacji sumy/podpisu.
- **Uwagi**: w trybie deweloperskim `sys.executable` = `python.exe` → skrypt nadpisałby interpreter Pythona; ręczne sprawdzanie bez dostępnej aktualizacji nie pokazuje użytkownikowi żadnego komunikatu (tylko log, `:80-81`); błędy sieci zwracają `{"available": False}` bez informacji.

---

### 3.7 Czat – klient (Socket.IO + REST) i serwer

**Klient** – `launcher/chat_socket.py` (lib `python-socketio`), REST przez `requests` w `launcher/chat_*.py`.

- **URL serwera**: domyślnie `http://127.0.0.1:5000` (`init_constructor_runtime.py:63`); lista serwerów `local_settings["chat_servers"]` = `[{id, name, url, is_default, last_used, credentials{email,password}, remember_credentials, auto_login_to_server}]` (`config_store.py:146-165`, wybór `launcher/server_selection.py`, edycja `launcher/chat_server_settings.py:95`).
- **Logowanie REST**: `POST {url}/login` JSON `{email, password}` → `{user_id, username}` (`chat_auth.py:22-34`); `POST {url}/register` (`chat_auth.py:184`). „Zapamiętaj” zapisuje `chat_email`/`chat_password` **jawnym tekstem** do local_settings (`chat_auth.py:45-52`; przy następnym wczytaniu klucze te są migrowane/usuwane `config_store.py:147-148`).
- **Połączenie Socket.IO** (`chat_socket.py:7-27, 581-595`): `socketio.Client(reconnection=True, reconnection_attempts=0 (∞), reconnection_delay=2, reconnection_delay_max=10)`, `eio.ping_interval=60`, `ping_timeout=120`; `sio.connect(chat_server_url)` w wątku daemon; domyślny namespace, bez nagłówków auth.
- **Uwierzytelnienie Socket.IO**: po `connect` emit `authenticate {user_id}` (`:397-414`) – **tylko ID użytkownika, bez hasła/tokenu**; serwer odpowiada `authenticated` (dane sesji) lub `authentication_failed`.
- **Zdarzenia odbierane** (handlery `chat_socket.py`): `connect`, `disconnect`, `authenticated`, `authentication_failed`, `member_removed_from_room` (:30), `user_online` (:78), `user_offline` (:95), `account_status_changed` (:108), `online_users_list` (:153), `new_room_created` (:184), `member_left_room` (:215), `room_deleted_by_creator` (:264), `message_deleted_successfully` (:320), `message_delete_failed` (:330), `message_read_update` (:339), `private_message_sent` (:471), `private_message_received` (:487), `group_message_sent` (:503), `group_message_received` (:517), `message_error` (:532), `message_edited_successfully` (:542), `message_edit_failed` (:551), `typing_update` (:567).
- **Zdarzenia emitowane**:
  - `authenticate {user_id}` (`chat_socket.py:411`)
  - `send_message` – zawsze ta nazwa (`chat_messaging.py:531-559`); payload z `sender_id`, `receiver_id` (prywatne) lub `room_id` (grupa), `content`, `attachment_server_filename`, opcjonalnie odpowiedź (`replied_to_message_id`)
  - `private_message` (`chat_messaging.py:203` – ścieżka z załącznikiem)
  - `typing_start` / `typing_stop {sender_id, receiver_id}` (`chat_messaging.py:282, 307`)
  - `mark_messages_as_read {message_ids, reader_id}` (`chat_interactions.py:142`)
  - `edit_message {message_id, new_content, editor_user_id}` (`chat_message_actions.py:203`)
  - `delete_message {message_id, deleter_user_id}` (`chat_message_actions.py:246`)
  - `join_specific_room` / `leave_specific_room {room_id}` (`chat_rooms.py:307, 174`)
- **REST używane przez klienta**: `GET /users`, `GET /rooms` (`chat_data.py:160,169`); historia `GET /messages/<u1>/<u2>`, `GET /rooms/<id>/messages` z paginacją (`chat_history.py:234,342`); `POST /upload_file` multipart (timeout 60 s, `chat_messaging.py:146,467`); `GET /download_file/<fn>` (`chat_render.py:527-579`); `POST /rooms`, `POST /rooms/<id>/members` (hasło pokoju), `DELETE /rooms/<id>/members/<uid>` (`chat_rooms.py:96,262,364`, `chat_context_actions.py:156,219`); `POST/DELETE /users/<id>/block` (`chat_blocking.py:37,78`); `PUT /user/<id>`, `DELETE /user/<id>` (z hasłem) (`chat_user_profile.py:83,217`).
- Powiadomienia systemowe o nowych wiadomościach – patrz 2.14.

**Serwer** – `chat_server.py` (2820 linii; Flask + Flask-SocketIO + Flask-SQLAlchemy/SQLite + werkzeug hash + email-validator):
- Start: `GL_CHAT_HOST` (domyślnie 127.0.0.1), `GL_CHAT_PORT` (domyślnie 5000) (`chat_server.py:2817-2820`); `cors_allowed_origins="*"` (`:172`).
- DB: `sqlite:///` + `CHAT_DB_PATH` (`:136`, `data/chat/chat.db`); uploady w `data/chat/uploads` z migracją starych folderów (`:47-48, 75-90`), `MAX_CONTENT_LENGTH` (`:76`).
- `SECRET_KEY`: env `GL_CHAT_SECRET_KEY` lub losowy zapisany w `data/chat/secret_key` (`:141-162`).
- Admin: login z `FLASK_ADMIN_USER` (domyślnie "admin"), hasło z env `FLASK_ADMIN_PASS`; bez niego losowe (panel zablokowany) (`:184-194`). Endpointy `/admin/login|logout|blacklist|panel|status|users|users/<id>/ban|unban|DELETE` (`:213-959`).
- Endpointy publiczne: `/`, `/register`, `/login`, `/users`, `/user/<id>` PUT/DELETE, `/users/<id>/block` POST/DELETE, `/rooms` GET/POST, `/rooms/<id>/members` POST, `/rooms/<id>/members/<uid>` DELETE, `/rooms/<id>/messages`, `/messages/<u1>/<u2>`, `/upload_file`, `/download_file/<name>` (`:1274-2000`).
- Socket.IO: `connect`, `disconnect` (emit `user_offline`), `authenticate` (join room = user.id, emit `user_online` innym, `online_users_list` + `authenticated`), `leave_specific_room`, `typing_start/stop`, `edit_message`, `delete_message`, `mark_messages_as_read`, `send_message` (`:2060-2783`).
- **Uwagi**: uwierzytelnianie socketu wyłącznie po `user_id` (`chat_server.py:2107-2157`) – każdy klient może podszyć się pod dowolnego użytkownika; REST nie używa tokenów/sesji; route `/users/<id>/block` POST i DELETE zdefiniowane dwukrotnie (właściwe `:1279`, `:1323` oraz stuby `block_user_stub` `:1703`, `unblock_user_stub` `:1723`); handlery Socket.IO wołają `self.root.after` z wątku socketio.

---

### 3.8 Pilot WWW (zdalne sterowanie)

Pliki: `launcher/remote_app.py` (Flask, bez Tk), `launcher/remote_server_runtime.py` (serwer WSGI `werkzeug.serving.make_server`).

- **Ustawienia** (local_settings): `remote_control_enabled` (domyślnie False, `config_store.py:202`), `remote_control_port` (domyślnie 5050), `remote_control_bind_lan` (False → `127.0.0.1`, True → `0.0.0.0`, `remote_app.py:33-34`), `remote_control_token`.
- **Token**: `secrets.token_urlsafe(24)` (`remote_app.py:29-30`), generowany przy pierwszym starcie i zapisywany (`remote_server_runtime.py:19-25`); „Regeneruj token” `_regenerate_remote_token` (`:241-252`) restartuje serwer. Porównanie `hmac.compare_digest` (`remote_app.py:37-40`).
- **Autoryzacja** (`before_request`, `remote_app.py:68-76`) – token z nagłówka `X-Remote-Token`, parametru `?token=` lub ciasteczka `gl_remote_token`. Brak/zły → `/api/*`: 401 JSON `{"error": ...}`, reszta: 401 HTML „Brak dostępu”. Gdy `is_running()` False → 503. Nagłówki odpowiedzi: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` (`:78-83`).
- **Endpointy**:
  - `GET /` – jeśli `?token=` → ustawia ciasteczko (`HttpOnly`, `SameSite=Strict`, 30 dni) i redirect na `/`; w innym razie zwraca wbudowaną stronę SPA z wstrzykniętym tokenem (`:85-94`).
  - `GET /api/games` – `[{name, playtime (sformatowany), cover_url: "/cover/<urlenc name>"}]` posortowane alfabetycznie (`:96-102`; dane `remote_server_runtime.py:62-69`).
  - `GET /api/status` – `{"running_game": <pierwsza gra z tracking_games lub null>}` (`:104-106`).
  - `POST /api/launch/<name>` – 404 jeśli gry brak; inaczej `root.after(0, launch_game(name))` (`:108-113`).
  - `POST /api/close/<name>` – analogicznie `close_game(name)` (`:115-120`).
  - `GET /cover/<name>` – `send_file` okładki, tylko jeśli ścieżka leży w `images/` (ochrona przed path traversal, `remote_server_runtime.py:28-38`); inaczej 404.
- **Frontend** (`remote_app.py:141-241`): lista z filtrem, przyciski „▶ Uruchom”/„■ Zamknij” (Zamknij widoczne tylko dla aktualnie działającej gry), odświeżanie statusu co 5 s, po akcji po 1,5 s.
- **Wątki**: `make_server(host, port, app, threaded=True)` + `serve_forever()` w wątku daemon (`remote_server_runtime.py:84-124`); stop: `shutdown()` + `server_close()` w osobnym wątku (`:127-144`). Zajęty port (WinError 10048/errno 98) → komunikat. Port 1025–65534, port 5000 zabroniony (zarezerwowany dla czatu) (`:180-228`). Adres w UI: `http://<IP>:<port>/?token=<token>`, IP LAN ustalane przez UDP „connect” do 8.8.8.8 (`game_launcher.py:2253-2268`).
- Autostart przy starcie aplikacji, jeśli `remote_control_enabled` (`init_constructor_runtime.py:513-514`).
- **Uwagi**: `close_game` wywołany zdalnie pokazuje `messagebox` na PC (blokujący).

---

### 3.9 Uruchamianie gier i emulatory

Pliki: `launcher/launch_command.py` (czyste, testowalne), `launcher/game_process_runtime.py:16-140`, `launcher/emulator_settings_runtime.py`.

- **Konfiguracja emulatorów**: `config["emulators"] = { "<nazwa>": {"path": "<exe>"} }` – tylko nazwa i ścieżka (`emulator_settings_runtime.py:109`); brak argumentów/platform per emulator. Dodawanie/edycja/usuwanie w Ustawieniach (walidacja: plik musi istnieć, nazwa unikalna, `:77-115, 140-172`).
- **Brak placeholderów** (`{rom}` itp.) – polecenie składane pozycyjnie.
- **Gra PC** (`launch_command.py:73-115`): exe = `profile.exe_path` jeśli profil ma własny, inaczej `game.exe_path`; argumenty z `profile.arguments` rozbijane `shlex.split(posix=False)` z usunięciem zewnętrznych cudzysłowów (`:34-42`). Polecenie `[exe] + args`, `cwd = katalog exe`.
- **Gra emulowana** (`:117-160`): wymagane `emulator_name`, `rom_path`; polecenie `[emulator_exe] + shlex(game.emulator_args) + [rom]`, `cwd = katalog emulatora`.
- **Zmiana litery dysku** `find_existing_path` (`:45-60`): jeśli ścieżka nie istnieje, próbuje tę samą ścieżkę na dysku, z którego działa launcher (`paths.drive_of`/`remap_drive`, `paths.py:71-133`).
- Błędy konfiguracji → `LaunchError(title, message)` po polsku → messagebox.
- **Start procesu** (`game_process_runtime.py:56`): `subprocess.Popen(command, cwd=...)`; `WinError 740` → komunikat o uprawnieniach administratora. Po starcie: `last_played`, `play_count += 1`, `game_start_times[name]`, przycisk zmienia się na „Zamknij”, Discord `in_game`, `save_config`. Uruchomienie między 2:00 a 4:00 ustawia flagę `_triggered_at_night` dla osiągnięcia `night_owl` (`:36-51`).
- **Zamykanie** `close_game` (`:238-422`): PC – pierwszy proces o pasującej nazwie exe lub pełnej ścieżce → `kill()` dzieci (rekurencyjnie) i rodzica; emulator – wszystkie procesy emulatora, których cmdline zawiera ścieżkę ROM (lub wszystkie, gdy brak ROM).
- **Uwagi**: dopasowanie po samej nazwie exe może zabić inny program o tej samej nazwie.

---

### 3.10 Skanowanie folderów w poszukiwaniu gier

Plik: `launcher/scan_pipeline.py`; ustawienia `scan_ignore_folders` (domyślne `_CommonRedist, DirectX, DotNet, Redist, Tools, Benchmark, support, data, __overlay`), `scan_recursively` (True), `scan_folders` (`config_store.py:305-319`).

- **Zgadywanie nazwy** `guess_game_name_from_folder` (`:57-72`): usuwa kolejno regexami (ignorecase) `[...]`, `(...)`, `v\d+(\.\d+)*`, słowa `Repack|Update|Fix|Edition|GOTY|Gold|Definitive|Remastered`, 4-cyfrowe liczby, znaki `-_.`; normalizuje spacje; pusty wynik → oryginalna nazwa.
- **Szukanie exe** `find_likely_executable` (`:75-149`): przeszukuje folder gry + podfoldery `bin, Binaries, Win32, Win64, x64, x86` (bez rekursji); pomija `ignore_files` = `setup.exe, uninstall.exe, unins000.exe, unins001.exe, launcher.exe, crashreporter.exe, configtool.exe, activation.exe` (`game_launcher.py:2548-2557`). Punktacja: 10 – nazwa exe = nazwa folderu; 9 – = zgadnięta nazwa; 7 – zgadnięta nazwa zawiera się w nazwie exe; 6 – nazwa exe zawiera się w nazwie folderu; 5 – zawiera `game|shipping|retail` (`game_launcher.py:2558-2562`); sortowanie malejąco po (punkty, rozmiar pliku, bonus płytkości).
- **Przebieg** `scan_folders_for_games` (`:178-311`, wątek): zbiór kandydatów = folder bazowy (jeśli zawiera exe) + wszystkie podfoldery (`os.walk` z odcinaniem ignorowanych) lub tylko bezpośrednie podfoldery; pomija nazwy już w bibliotece i duplikaty; wynik `[{guessed_name, folder_path, suggested_exe_path, import: True, profiles:[{name:"Default", exe_path:None, arguments:""}]}]` → okno weryfikacji `ScanVerificationWindow` (`ui/dialogs.py:120`).
- Dodatkowo: `parse_folder_name_metadata` (rok 1980–2099, wydawca z `[...]` z czarną listą grup scenowych, `:337-363`) i `parse_nfo_file` (`.nfo`/`.txt` < 5 MB, kodowania cp437/utf-8/latin-1/cp1250/cp1252, regexy Title/Publisher/Developer/Release Date/Genre/Version + fallbacki, `:366-489`) – **używane** przez przyciski „Parsuj .NFO” / „Parsuj Nazwę Fold.” w formularzu gry (`ui/game_form.py:292-296, 461-530`).
- **Potwierdzenie braku wejścia z UI**: `start_scan_thread`, `add_scan_folder`, `remove_scan_folder`, `save_scan_settings`, `load_scan_folders_list` mają tylko wrappery w `game_launcher.py:2517-2565`; nigdzie w `launcher/`, `ui/` nie ma przycisku/menu, które je wywołuje; widgety `scan_folders_listbox`, `scan_recursively_var`, `ignored_folders_text` nigdy nie są tworzone (grep: tylko odczyty). **Skanowanie folderów gier jest nieosiągalne z UI.**
- **Uwagi**: `find_likely_executable.ignore_dirs` (`game_launcher.py:2534-2547`) zdefiniowane, ale nieużywane; ślepe `self.root.after` z `i` przechwyconym przez domknięcie (`:255-260`).

---

### 3.11 Skanowanie screenshotów

Plik: `launcher/screenshot_scan_runtime.py`.

- **Foldery**: wyłącznie konfigurowane przez użytkownika – `settings["autoscan_screenshot_folders"]` (domyślnie `[]`, dodawanie/usuwanie `:49-87`, UI `settings_page_content.py:518-590`). **Brak automatycznych ścieżek Steam/NVIDIA/Xbox.**
- Ignorowane podfoldery `settings["screenshot_scan_ignore_folders"]` (domyślnie `thumb_cache, cache, temp, thumbnails`, `config_store.py:322-324`).
- **Uruchamianie**: przycisk w Ustawieniach (`settings_page_content.py:590`), przyciski w szczegółach gry (tylko dla tej gry, `ui/game_details.py:500, 589`), przy starcie gdy `settings["autoscan_on_startup"]` (po 3 s, `init_constructor_runtime.py:532-533`).
- **Dopasowanie** (`:197-265`): `os.walk` każdego folderu; pliki `.png .jpg .jpeg .bmp .webp .gif`; plik przypisany do **pierwszej** gry, dla której `nazwa_pliku.lower().startswith(nazwa_gry.lower())`. Nowe ścieżki absolutne dopisywane do `game["autoscan_screenshots"]`, jeśli nie ma ich też w ręcznej liście `game["screenshots"]`. `save_config` przy zmianach; okno postępu + messagebox z liczbą nowych.
- **Uwagi**: `settings["screenshot_filename_patterns"]` (`config_store.py:325-328`) zdefiniowane, ale nieużywane; dopasowanie prefiksowe (np. „Doom” złapie „Doom Eternal_…”); autoskan przy starcie wyświetla messagebox po zakończeniu.

---

### 3.12 Gamepad

Plik: `launcher/gamepad_runtime.py` (lib `inputs`), wątek startowany w `init_constructor_runtime.py:506`.

- Pętla `get_gamepad()` (blokująca). Pierwsze zdarzenie → `_enter_big_picture_mode` (3 kafelki w rzędzie, szerokość 300, większe czcionki, `game_launcher.py:966-978`); `UnpluggedError` → `_exit_big_picture_mode` (5 kafelków, 200) i sleep 1 s.
- Mapowanie (próg osi 10000):
  - `ABS_HAT0X`/`ABS_X` → `<Left>`/`<Right>` (`event_generate`);
  - `ABS_HAT0Y`/`ABS_Y` → `canvas.yview_scroll(±1, "units")`;
  - `BTN_SOUTH` (A/✕) → `<Return>`;
  - `BTN_EAST` (B/○) → `show_home`;
  - `BTN_NORTH`/`BTN_WEST` → `yview_scroll(+1, "pages")`.
- **Uwagi**: gałąź „Page Up” (`:43-49`) jest nieosiągalna (te same przyciski co wyżej) – X i Y robią to samo; `event_generate`/`yview_scroll`/`update_idletasks` wołane z wątku tła (niebezpieczne w Tk); oś bez martwej strefy/repeat-rate → przy wychyleniu gałki generuje zdarzenie na każdy odczyt.

---

### 3.13 Zasobnik systemowy (tray)

Plik: `launcher/tray_runtime.py` (lib `pystray` + PIL).

- Tworzony przy minimalizacji (`<Unmap>` → `on_minimize`, gdy stan `iconic` → `withdraw` + ikona, `init_constructor_runtime.py:328`, `tray_runtime.py:23-26`) oraz przyciskiem w sidebarze `minimize_to_tray` (`sidebar_ui.py:95`, `game_launcher.py:2058-2060`). `pystray.Icon("GameLauncher", image, "Game Launcher", menu)` w wątku daemon.
- Ikona: `Image.open("icon.png")`; w repo jest tylko `icon.ico`, więc w praktyce fallback `create_default_icon` – niebieski kwadrat 64×64 z napisem „GL” (`game_launcher.py:2062-2066`).
- **Menu** (`tray_runtime.py:35-62`): Strona Główna · Biblioteka · Muzyka ▸ (Odtwórz / Pauza, Poprzedni, Następny, ─, Pokaż Odtwarzacz) · ─ · Roadmapa · Menedżer Modów · Osiągnięcia · Newsy · Statystyki · ─ · Ustawienia · ─ · Wyjdź z Programu (`exit_program` → `on_closing`).
- Każda pozycja „pokaż” → `show_window` (zatrzymuje ikonę, `deiconify/lift/focus_force`) + nawigacja.
- **Uwagi**: callbacki pystray wykonują operacje Tk bezpośrednio z wątku zasobnika (np. `show_roadmap_from_tray` `game_launcher.py:2068-2086`).

---

### 3.14 Powiadomienia systemowe (plyer)

`from plyer import notification` → `notification.notify(...)`:
1. **Odblokowanie osiągnięcia** – tytuł „Osiągnięcie Odblokowane!”, treść „nazwa\nopis”, `app_name="Game Launcher"`, timeout 10 (`achievements_runtime.py:308-316`).
2. **Przypomnienia** – wątek `monitor_reminders` co **60 s** sprawdza `self.reminders` z `time <= now` i bez `notified` → tytuł „Przypomnienie”, timeout 10; ustawia `notified=True` i zapisuje config (`reminders_runtime.py:105-119`, start `init_constructor_runtime.py:526`).
3. **Nowa wiadomość czatu** – gdy wiadomość nie dotyczy aktualnie otwartej i widocznej rozmowy; `app_name="Game Launcher Chat"`, ikona `icon.ico`, timeout 5 (`chat_history.py:610-638`).

---

### 3.15 Monitorowanie sesji i czasu gry (psutil)

Pliki: `launcher/session_monitor_runtime.py`, `launcher/game_process_runtime.py:143-235`.

- **Wątek** `monitor_game_sessions` (start `init_constructor_runtime.py:523`), pętla co **5 s** po **wszystkich grach** w bibliotece (niezależnie od tego, czy uruchomiono je z launchera).
- **Wykrywanie** `is_game_running` (`game_process_runtime.py:143-235`):
  - PC: zbiór ścieżek `exe_path` + `launch_profiles[].exe_path` (abspath) i ich nazw plików; `psutil.process_iter(["name","exe"])` → działa, jeśli **nazwa procesu** (lower) pasuje do którejkolwiek nazwy exe **lub** pełna ścieżka `exe` pasuje. Procesy potomne nie są śledzone (np. launcher → właściwa gra o innej nazwie nie zostanie wykryta).
  - Emulator: proces o nazwie/ścieżce emulatora z `config["emulators"][name]["path"]`; jeśli gra ma `rom_path` i cmdline dostępny → wymagane, by któryś argument zawierał ścieżkę ROM (normcase); bez cmdline → uznaje za działającą.
- **Liczenie czasu** (`session_monitor_runtime.py:17-59`): przejście „nie działa → działa” zapisuje `tracking_games[name] = time.time()` i `last_played`; przejście „działa → nie działa”: `elapsed = end − start`, `play_time += elapsed` (sekundy, float), dopisanie `play_sessions.append({"start", "end"})` (epoch), dla wpisu roadmapy tej gry ze statusem „Planowana” `time_spent += elapsed`; `save_config`; Discord → idle; przycisk → „Uruchom”; jeśli `settings["auto_backup_on_exit"]` (domyślnie True) → autosave (2.17); po 150 ms `prompt_checklist_update`, po 250 ms `prompt_completion` (askinteger 0–100 → `completion`, a następnie `check_and_unlock_achievements`, `game_launcher.py:1184-1202`).
- Czas trwania bieżącej sesji w UI: `_update_current_session_time_display` (`init_constructor_runtime.py:541`).
- **Uwagi**: koszt O(gry × procesy) co 5 s (pełny `process_iter` na każdą grę); czas sesji obejmuje maksymalnie ±5 s niedokładności; martwy kod `track_play_time`/`update_after_game` (`game_launcher.py:1348-1379`) – nigdzie nie wywoływany; `game_start_times` ustawiane w `launch_game`, ale nieużywane do liczenia czasu; zamknięcie launchera w trakcie gry gubi bieżącą sesję (stan tylko w pamięci).

---

### 3.16 Osiągnięcia

Pliki: `launcher/achievements_runtime.py`, `launcher/achievements_defs.py`; definicje w `data/config/achievements_def.json` (lista obiektów `{id, name, description, rule_type, target_value, genre?, tag?, group?}`), postęp w `config.user.achievements[id] = {unlocked, timestamp, current_progress, _triggered_at_night?}`.

- **Kiedy ewaluowane** (`check_and_unlock_achievements`): po pytaniu o % ukończenia po sesji (`game_launcher.py:1199`), dodaniu/edycji gry (`game_crud_runtime.py:52-53, 85`), zmianach roadmapy (`roadmap_archive_runtime.py:392`), zmianie motywu (`services/theme_runtime.py:64`), imporcie gier ze skanu (`ui/dialogs.py:603`), instalacji modów (`ui/mod_manager.py:480, 633`), zmianie definicji (`achievements_defs.py:127`), przeładowaniu definicji (`achievements_runtime.py:14`). Brak cyklicznej ewaluacji.
- **Typy warunków** (`achievements_runtime.py:87-273`, etykiety `init_constructor_runtime.py:358-379`):
  - `games_launched_count` – gry z `play_count > 0`
  - `library_size` – liczba gier
  - `total_playtime_hours` – suma `play_time`/3600 (float, epsilon 0.001)
  - `games_completed_100` – gry z `completion >= 100`
  - `playtime_single_game_hours` – maks. czas jednej gry (h)
  - `genre_played_count` / `genre_completed_100` (param `genre`, pole `games[].genres`)
  - `tag_played_count` / `tag_completed_100` (param `tag`)
  - `group_played_count` / `group_completed_100` (param `group`, `self.groups[group]` = lista nazw gier)
  - `roadmap_completed_count` – `len(archive)`
  - `roadmap_items_added` – `len(roadmap)`
  - `games_rated_count` – gry z `rating != None`
  - `groups_created` – `len(groups)`
  - `games_with_tags` – gry z niepustym `tags`
  - `themes_changed` – `user.theme_change_count`
  - `mods_installed` – suma `len(mods)` po profilach w `mods_data`
  - `consecutive_days_used` – `local_settings.consecutive_days` (liczone przy starcie, `init_constructor_runtime.py:268-288`)
  - `game_launched_at_night` – flaga `_triggered_at_night` (uruchomienie 2:00–4:00)
- Odblokowanie: `current >= target` → `unlocked=True`, `timestamp`, `current_progress=target`, powiadomienie plyer (2.14), `save_config`, odświeżenie strony osiągnięć jeśli otwarta (`:297-324`). Nieznany `rule_type` → nigdy nie odblokuje.
- **Uwagi**: gałąź `genre_played_count` jest zdublowana (`:122` i `:154`, druga osiągalna tylko dla `genre_completed_100`); `game_launched_at_night` jest ewaluowane dopiero przy następnym wywołaniu po starcie gry (samo `launch_game` nie wywołuje sprawdzenia).

---

### 3.17 Autozapis i kopie zapasowe

**Autozapis po sesji** – `launcher/autosave_runtime.py`:
- Wywołanie z monitora sesji, gdy `settings["auto_backup_on_exit"]` (checkbox `settings_page_content.py:341`, zapis `game_launcher.py:2851`).
- Wymaga `game["save_path"]` (istniejący folder). Kopiuje rekurencyjnie (`shutil.copy2`) do `data/games_saves/<gra>/_autosave/` w wątku z oknem postępu (aktualizacja co 0,1 s) (`:11-119`).
- **Uwagi**: „nadpisanie” nie czyści starej zawartości `_autosave` (pliki usunięte w źródle zostają); okno postępu wyskakuje po każdej sesji.

**Backup lokalny** – `launcher/backup_restore.py`:
- `backup_to_local_folder` (`:57-227`): wybór folderu → `GameLauncher_Backup_YYYYMMDD_HHMMSS/` z: `config.json`, `local_settings.json` (**zawiera sekrety**), `achievements_def.json`, `games_saves/`, `images/`, `internal_music/`, `custom_themes/` (kopie plików/folderów, nie ZIP); przy krytycznym błędzie usuwa niekompletny backup.
- `load_local_backup` (`:230-476`): potwierdzenie, przywrócenie tych samych elementów (foldery: rmtree + copytree), przeładowanie config/local_settings/definicji, `refresh_ui`. Wywoływane także z kreatora pierwszego uruchomienia (`initial_setup_runtime.py:72`). Przyciski „Zgraj Backup”/„Wczytaj Backup” (`settings_page_content.py:490-493`).
- `_perform_backup_restore_thread` (`:517-883`) – alternatywna implementacja przywracania, **nieużywana** (tylko wrapper `game_launcher.py:2481`).

---

### 3.18 Pozostałe integracje zewnętrzne

- **Newsy RSS** (`launcher/news_runtime.py`, libs `requests`, `feedparser`, `tkhtmlview`): `settings["rss_feeds"] = [{url, active, name}]` (domyślnie IGN `https://feeds.ign.com/ign/games-all`, `config_store.py:281-302`), `news_post_limit` (10). `GET` z UA przeglądarki, timeout 10 s, `feedparser.parse`; wpisy z błędem parsowania (`bozo`) odrzucane; sortowanie po `published_parsed`/`updated_parsed`, top N renderowane jako HTML w `HTMLScrolledText` (`:50-115`). Uwaga: `title`/`summary` wstawiane do HTML bez escapowania.
- **Globalne skróty klawiszowe** (`launcher/hotkey_runtime.py`, lib `pynput.keyboard.GlobalHotKeys`): `local_settings["music_hotkeys_enabled"]` (domyślnie True), `music_hotkeys` – domyślnie `play_pause <alt>+<space>`, `next_track <alt>+<right>`, `prev_track <alt>+<left>`, `stop_music <alt>+s`, `volume_up <alt>+<up>`, `volume_down <alt>+<down>` (`utils.py:108-115`); rejestracja 500 ms po starcie (`init_constructor_runtime.py:517`). Uwaga: `stop_music` tylko zmienia overlay („Nic nie gra...”), nie zatrzymuje odtwarzania (`hotkey_runtime.py:85-87`).
- **Autostart Windows** (`game_launcher.py:1603-1635`, `winreg`): wpis `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\GameLauncher = sys.executable + " " + abspath(__file__)`. Uwaga: w wersji exe (PyInstaller) dopisuje ścieżkę do nieistniejącego `.py`; bez cudzysłowów dla ścieżek ze spacjami.
- **Steam**: brak integracji (jedyne wystąpienie „STEAM” to czarna lista wydawców w parserze NFO, `scan_pipeline.py:471`).
- **ScriptHook / `external/`**: `external/ScriptHookConfig.ini` + stała `SCRIPTHOOK_CONFIG_FILE` (`utils.py:33`) – **nigdzie nieużywane** w kodzie.
- **Pobieranie obrazków w czacie** (`chat_render.py:186`, `requests` stream, timeout 20 s) – podgląd załączników z serwera czatu.

---

### 3.19 Zależności z `requirements.txt` i ich użycie

| Pakiet | Gdzie używany | Do czego |
|---|---|---|
| Pillow | wszędzie (`launcher/utils.py:11`, `tray_runtime.py`, UI) | obrazy, okładki, ikona tray |
| tkcalendar | `roadmap_archive_runtime.py`, `stats_page.py`, `ui/filters.py` | wybór dat |
| pygame | `ui/music_player.py` (mixer), `languages.py` | odtwarzanie muzyki |
| mutagen | `ui/music_player.py` | tagi audio, długość utworów |
| pylast | `ui/music_player.py` | okładki Last.fm (2.2) |
| Flask | `chat_server.py`, `launcher/remote_app.py` | serwer czatu, pilot WWW |
| Flask-SocketIO | `chat_server.py` | Socket.IO serwera |
| Flask-SQLAlchemy | `chat_server.py` | SQLite czatu |
| python-socketio | `launcher/chat_socket.py` | klient czatu |
| Werkzeug | `chat_server.py` (hash haseł), `remote_server_runtime.py` (`make_server`) | |
| psutil | `game_process_runtime.py` | wykrywanie/zamykanie procesów gier |
| pystray | `tray_runtime.py` | zasobnik |
| plyer | `achievements_runtime.py`, `reminders_runtime.py`, `chat_history.py` | powiadomienia |
| inputs | `gamepad_runtime.py` | gamepad |
| pynput | `hotkey_runtime.py`, `hotkey_capture.py`, `hotkey_input.py` | globalne skróty |
| requests | RAWG, Last.fm (pobranie obrazu), updater, newsy, REST czatu | HTTP |
| pypresence | `discord_runtime.py` | Discord RPC |
| feedparser, tkhtmlview | `news_runtime.py` | RSS + render HTML |
| email-validator | `chat_server.py` | walidacja e-maili rejestracji |
| packaging | `updater_runtime.py`, `config_store.py`, `utils/config_manager.py` | porównanie wersji |
| matplotlib | `stats_chart.py`, `stats_runtime.py` | wykresy statystyk |
| numpy | brak bezpośredniego importu | tylko zależność matplotlib |
| *(zakomentowane)* PyGithub | `cloud_github_runtime.py` | sync GitHub – **wymagany, a nie instalowany** |
| *(zakomentowane)* google-auth*, google-api-python-client | `game_launcher.py:1655-1865` | Google Drive (niedziałające) |

`requirements-dev.txt`: `pytest`, `pyinstaller`. Moduły stdlib z integracją systemową: `winreg` (autostart), `socket` (wykrywanie IP LAN), `subprocess` (start gier, updater .bat).

## 4. Skróty klawiszowe

### 4.1 Globalne skróty systemowe (pynput)

Rejestracja: `_register_music_hotkeys()` (`launcher/hotkey_runtime.py:27`) tworzy `pynput.keyboard.GlobalHotKeys(callbacks_map)` (`hotkey_runtime.py:66`) z `local_settings.music_hotkeys` (fallback `DEFAULT_MUSIC_HOTKEYS`, `launcher/utils.py:108`). Uruchamiane 500 ms po starcie (`launcher/init_constructor_runtime.py:517`), tylko gdy `local_settings.music_hotkeys_enabled == True` (domyślnie tak). Konfigurowalne w Ustawieniach (sekcja „Skróty Klawiszowe Odtwarzacza Muzyki”), format ciągu pynput (`<alt>+<space>`). Dispatcher: `_music_action_callback()` (`hotkey_runtime.py:10`).

| Akcja (klucz) | Domyślny skrót | Definicja domyślna | Obsługa | Efekt |
|---|---|---|---|---|
| Odtwórz / Pauza (`play_pause`) | `Alt+Space` (`<alt>+<space>`) | `launcher/utils.py:109` | `hotkey_runtime.py:13` → `_music_control_play_pause` (`game_launcher.py:1740`) | `MusicPlayerPage._toggle_play_pause()`, odświeżenie nakładki |
| Następny utwór (`next_track`) | `Alt+→` (`<alt>+<right>`) | `launcher/utils.py:110` | `hotkey_runtime.py:15` → `_music_control_next_track` | `_next_track()` |
| Poprzedni utwór (`prev_track`) | `Alt+←` (`<alt>+<left>`) | `launcher/utils.py:111` | `hotkey_runtime.py:17` → `_music_control_prev_track` | `_prev_track()` |
| Zatrzymaj (`stop_music`) | `Alt+S` (`<alt>+s`) | `launcher/utils.py:112` | `hotkey_runtime.py:19` → `_music_control_stop` (`hotkey_runtime.py:85`) | tylko ustawia nakładkę na „Nic nie gra...” (patrz Uwagi) |
| Głośniej (`volume_up`) | `Alt+↑` (`<alt>+<up>`) | `launcher/utils.py:113` | `hotkey_runtime.py:21` → `_music_control_volume_up` (`:90`) | `_change_volume_by_step(+10)` |
| Ciszej (`volume_down`) | `Alt+↓` (`<alt>+<down>`) | `launcher/utils.py:114` | `hotkey_runtime.py:23` → `_music_control_volume_down` (`:95`) | `_change_volume_by_step(-10)` |

Dodatkowo:
- **Przechwytywanie nowego skrótu**: `keyboard.Listener(suppress=True)` (`launcher/hotkey_capture.py:107`) – na czas dialogu „Ustawianie Skrótu” globalne skróty są zatrzymane, a klawiatura zablokowana dla innych aplikacji do momentu zwolnienia klawisza głównego (`hotkey_input.py:132`). Anuluj / zamknięcie okna → `_cancel_hotkey_capture` (`hotkey_capture.py:140`).
- **Nakładka „Teraz Odtwarzane”** (`ui/overlay.py`) nie ma własnych skrótów klawiszowych – tylko przeciąganie myszą (3.3).
- **Menu zasobnika** (`launcher/tray_runtime.py:36-61`, pystray) – pozycje bez akceleratorów: Odtwórz/Pauza, Poprzedni, Następny, Pokaż Odtwarzacz, Strona Główna, Biblioteka, Roadmapa, Newsy, Statystyki, Ustawienia, Wyjdź z Programu.
- W kodzie nie ma `accelerator=` w menu Tk ani innych mechanizmów globalnych skrótów (`RegisterHotKey`, `keyboard.add_hotkey`).

### 4.2 Skróty klawiaturowe Tk

| Widget / kontekst | Klawisz | Efekt | Plik:linia |
|---|---|---|---|
| Całe okno (`bind_all`) – nawigacja fokusem | `Up` / `Left` | `focus_prev_widget` – poprzedni widget (w Big Picture: generuje `<Left>`) | `game_launcher.py:948`, `:950` |
| Całe okno (`bind_all`) | `Down` / `Right` | `focus_next_widget` – następny widget (w Big Picture: generuje `<Right>`) | `game_launcher.py:949`, `:951` |
| Całe okno (`bind_all`) | `Return` | `activate_focused_widget` – `invoke()` dla `ttk.Button`, `<Return>` dla `ttk.Entry` | `game_launcher.py:952` |
| Czat – pole wpisywania wiadomości | `Return` | `_send_chat_message` – wysyła wiadomość | `launcher/chat_layout.py:458` |
| Czat – pole wpisywania wiadomości | `<Key>` (każdy klawisz) | `_on_chat_input_key_press` – wysyła `typing_start` (wskaźnik pisania, tylko czat prywatny) | `launcher/chat_layout.py:457` |
| Odtwarzacz muzyki – pole wyszukiwania | `Return` | `"break"` – blokuje propagację (wyszukiwanie działa na bieżąco) | `ui/music_player.py:763` |
| Ustawienia – pole „Tekst statusu” Discord | `<FocusOut>` | `_save_discord_settings` | `launcher/settings_page_content.py:728` |
| Ustawienia – Combobox czcionki | `<<ComboboxSelected>>` | `_save_and_apply_font_setting` | `launcher/settings_page_content.py:143` |
| Okno wyboru emoji (czat) | `<FocusOut>` | zamyka picker po utracie fokusu | `launcher/chat_emoji.py:324` |
| Okno główne | `<Unmap>` (minimalizacja) | `on_minimize` – ukrycie okna i ikona w zasobniku | `launcher/init_constructor_runtime.py:328` |

Brak bindowań na `Escape`, `F1–F12`, `Delete`, `BackSpace`, `Control-…`, `space`, `Tab`, `Prior/Next`, `Home/End` w całym kodzie (poza 3.1).

### 4.3 Mysz (kółko, dwuklik, PPM, przeciąganie)

| Widget / kontekst | Zdarzenie | Efekt | Plik:linia |
|---|---|---|---|
| Ustawienia – canvas | `MouseWheel` (`bind_all`, add) | przewijanie, gdy kursor nad ustawieniami | `launcher/settings_page_content.py:72` |
| Biblioteka – canvas kafelków | `MouseWheel` (`bind_all`, add) | `_on_mouse_wheel_and_lazy_load` – przewijanie + leniwe ładowanie kafelków | `launcher/library_grid_runtime.py:110` |
| Biblioteka – pasek przewijania | `B1-Motion` | `_trigger_lazy_load` | `launcher/library_grid_runtime.py:109` |
| Biblioteka – widok listy (Treeview) | `Double-1` | `_on_list_view_double_click` → okno szczegółów gry | `launcher/library_grid_runtime.py:99` |
| Biblioteka – widok listy | `Button-3` | menu kontekstowe gry | `launcher/library_grid_runtime.py:100` |
| Biblioteka – okładka kafelka | `Button-1` | `show_game_details` | `launcher/library_tile_actions.py:73` |
| Biblioteka – kafelek/okładka/nazwa/pasek info | `Button-3` | `_show_tile_context_menu` (Uruchom, grupy, itd.) | `launcher/library_tile_actions.py:74`, `:78`, `:132`, `:136` |
| Osiągnięcia – canvas | `MouseWheel` (`bind_all`, add) | przewijanie listy osiągnięć | `launcher/achievements_page.py:139` |
| Czat – picker emoji | `MouseWheel` (`bind_all`, add) | przewijanie emoji | `launcher/chat_emoji.py:157` |
| Czat – lista użytkowników | `Button-3` | `_on_chat_list_right_click` – menu kontekstowe | `launcher/chat_layout.py:244` |
| Czat – lista członków pokoju | `Button-3` | `_on_room_member_list_right_click` | `launcher/chat_layout.py:617` |
| Czat – link w treści (tag `chat_link_tag`) | `Enter` / `Leave` | kursor `hand2` / domyślny | `launcher/chat_render.py:76`, `:81` |
| Czat – miniatura obrazu | `Button-1` | otwiera pełny obraz w przeglądarce | `launcher/chat_render.py:264` |
| Czat – dymek wiadomości, etykiety, załącznik, „edytowano”, linki | `Button-3` | `_show_chat_message_context_menu` (odpowiedz/edytuj/usuń itp.) | `launcher/chat_render.py:338`, `:434`, `:453`, `:481`, `:508`, `:551`, `:583` |
| Czat – cytat odpowiedzi | `Button-1` | `_jump_to_message` – przewija do cytowanej wiadomości | `launcher/chat_render.py:398` |
| Czat – URL w tekście | `Button-1` | `webbrowser.open` | `launcher/chat_render.py:428` |
| Czat – link do pliku | `Button-1` | otwiera `<serwer>/download_file/<plik>` | `launcher/chat_render.py:545`, `:577` |
| Szczegóły gry – okładka | `Button-3` | `show_cover_context_menu` | `ui/game_details.py:68` |
| Szczegóły gry – screenshoty | `MouseWheel` (`bind_all`, add) | `_on_screenshot_mousewheel` | `ui/game_details.py:260` |
| Szczegóły gry – miniatura screenshota | `Button-1` / `Button-3` | podgląd / menu kontekstowe screenshota | `ui/game_details.py:902`, `:918` |
| Szczegóły gry – checklista (Treeview) | `Double-1` | `_toggle_task_status_event` – przełącza status zadania | `ui/game_details.py:301` |
| Szczegóły gry – panel akcji | `MouseWheel` (`bind_all`, add) | przewijanie akcji | `ui/game_details.py:399` |
| Okno weryfikacji skanu (`ScanVerificationWindow`) | `Double-1` | `toggle_import_selected` – zaznacza/odznacza grę do importu | `ui/dialogs.py:226` |
| Menedżer zapisów (`SaveManager`) – Treeview | `Double-1` | `load_save` – wczytuje zaznaczony zapis | `ui/save_manager.py:73` |
| Odtwarzacz – playlista (Listbox) | `Double-1` | `_play_selected_from_playlist` | `ui/music_player.py:868` |
| Odtwarzacz – playlista | `Button-3` | `_show_playlist_context_menu` | `ui/music_player.py:869` |
| Odtwarzacz – kafelki utworów | `MouseWheel` (`bind_all`, add) | `_on_music_tiles_mousewheel` | `ui/music_player.py:932` |
| Odtwarzacz – kafelek utworu | `Button-1` | odtwórz utwór | `ui/music_player.py:1937-1940` |
| Odtwarzacz – kafelek utworu | `Button-3` | menu kontekstowe utworu | `ui/music_player.py:1945-1948` |
| Odtwarzacz – suwak postępu | `ButtonPress-1` / `ButtonRelease-1` | `_begin_seek` / `_end_seek` – przewijanie utworu | `ui/music_player.py:1224`, `:1225` |
| Nakładka „Teraz Odtwarzane” | `ButtonPress-1`, `B1-Motion`, `ButtonRelease-1` | przeciąganie okna; zapis pozycji | `ui/overlay.py:105-113` |
| Tooltip (`ui/components.py`) | `ButtonPress` | ukrywa tooltip | `ui/components.py:17` |
| `GameGridManager` (kod martwy – klasa nie jest instancjonowana) | `MouseWheel`, `Button-4`, `Button-5`, `Button-3` | przewijanie / menu kontekstowe | `ui/game_grid_manager.py:60-62`, `:374-386` |

### 4.4 Gamepad (biblioteka `inputs`)

Wątek `controller_listener` (`launcher/gamepad_runtime.py:7`, start w `launcher/init_constructor_runtime.py:506`) w pętli czyta `inputs.get_gamepad()`. Pierwsze zdarzenie z pada → `_enter_big_picture_mode` (`game_launcher.py:966`: 3 kafelki w rzędzie, szerokość kafelka 300, większe czcionki). `UnpluggedError` → `_exit_big_picture_mode` (`game_launcher.py:980`: 5 kafelków, szer. 200) i ponowna próba co 1 s. Próg analogu: `10000`.

| Przycisk / oś (kod `inputs`) | Xbox / PlayStation | Efekt | Plik:linia |
|---|---|---|---|
| `ABS_HAT0X` / `ABS_X` = −1 lub < −10000 | D-pad / lewa gałka w lewo | `root.event_generate("<Left>")` | `launcher/gamepad_runtime.py:23-25` |
| `ABS_HAT0X` / `ABS_X` = +1 lub > 10000 | D-pad / lewa gałka w prawo | `root.event_generate("<Right>")` | `launcher/gamepad_runtime.py:26-27` |
| `ABS_HAT0Y` / `ABS_Y` = −1 lub < −10000 | D-pad góra / gałka (oś Y ujemna) | `canvas.yview_scroll(-1, "units")` (przewiń w górę) | `launcher/gamepad_runtime.py:29-32` |
| `ABS_HAT0Y` / `ABS_Y` = +1 lub > 10000 | D-pad dół / gałka (oś Y dodatnia) | `canvas.yview_scroll(1, "units")` (przewiń w dół) | `launcher/gamepad_runtime.py:33-35` |
| `BTN_SOUTH` (wciśnięcie) | A / ✕ | `root.event_generate("<Return>")` (aktywacja) | `launcher/gamepad_runtime.py:37-38` |
| `BTN_EAST` (wciśnięcie) | B / ○ | `show_home()` (powrót na stronę główną) | `launcher/gamepad_runtime.py:40-41` |
| `BTN_NORTH` / `BTN_WEST` (wciśnięcie) | Y / △ i X / □ | `canvas.yview_scroll(1, "pages")` (strona w dół) | `launcher/gamepad_runtime.py:43-45` |
| (gałąź martwa) `BTN_WEST` / `BTN_NORTH` | X / □ – wg docstringu „Page Up” | `yview_scroll(-1, "pages")` – nigdy nie wykonywane | `launcher/gamepad_runtime.py:47-49` |

Brak obsługi: Start/Select/Back, bumperów, triggerów, prawej gałki, wibracji; brak mapowania konfigurowalnego.

**Uwagi:**
- `setup_key_bindings()` (`game_launcher.py:947`) – jedyne miejsce rejestrujące `Up/Down/Left/Right/Return` – **nigdy nie jest wywoływane**, więc nawigacja strzałkami i `Enter` w oknie głównym nie działa, a zdarzenia `<Left>/<Right>/<Return>` generowane przez pada trafiają w próżnię. Gdyby ją włączyć, w trybie Big Picture `focus_next_widget` generuje `<Right>`, które ponownie wywołuje `focus_next_widget` → nieskończona rekurencja.
- Gamepad: X i Y robią to samo (strona w dół) – druga gałąź `elif` (`gamepad_runtime.py:47`) jest nieosiągalna, więc brak „Page Up”. Wątek pada woła `event_generate`, `yview_scroll` i `update_idletasks` bezpośrednio z wątku pobocznego (Tk nie jest thread-safe). Analog generuje zdarzenie przy każdej próbce powyżej progu (brak debounce/repeat-delay).
- Globalny skrót „Zatrzymaj” (`_music_control_stop`, `hotkey_runtime.py:85`) nie zatrzymuje odtwarzania – tylko zmienia tekst nakładki.
- Callbacki pynput działają w wątku pynput i wołają `root.after` / metody Tk z tego wątku.
- Dwie akcje z tym samym skrótem nadpisują się w `callbacks_map` (brak walidacji konfliktów); przechwytywanie skrótu z `suppress=True` blokuje klawiaturę całego systemu, dopóki dialog jest otwarty.
- Kilka ekranów rejestruje `bind_all("<MouseWheel>", add="+")` przy każdym utworzeniu (np. każde otwarcie okna szczegółów gry, `ui/game_details.py:260`, `:399`) – handlery się kumulują.

## 5. Znane błędy i ograniczenia

Stan sprawdzony na gałęzi `polish/v1.5.0` (HEAD `15111b7`); `game_launcher.spec` został potem zacommitowany (5ed5cd1). Ścieżki podane względem katalogu repozytorium. Folderu `data/` nie otwierano. Pozycje oznaczone „(do weryfikacji)” wynikają z analizy statycznej i nie zostały sprawdzone w działającej aplikacji.

### 5.1. Funkcje niedokończone lub atrapy

**4.1.1. Skanowanie folderów z grami nie ma wejścia w UI**
Cały pipeline w `launcher/scan_pipeline.py` (`add_scan_folder` :21, `remove_scan_folder` :35, `save_scan_settings` :51, `start_scan_thread` :152, `scan_folders_for_games` :178, `update_scan_progress` :320) ma wrappery w `game_launcher.py:2514-2583`, ale nic ich nie wywołuje. Nie ma przycisku ani polecenia (`command=`), które by je uruchamiało. `load_scan_folders_list` jest wywoływane (`launcher/app_navigation.py:52`, `launcher/settings_runtime.py:18`), ale wypełnia `self.scan_folders_listbox`, którego żaden kod nie tworzy, więc kończy się na `hasattr` i nic nie robi (`launcher/scan_pipeline.py:14`). Działają tylko funkcje pomocnicze: `parse_nfo_file` i `parse_folder_name_metadata` w formularzu gry (`ui/game_form.py:475`, `:521`). README nadal reklamuje „Smart Scanning / Inteligentne Skanowanie” (`README.md:19`, `:279`).
Uwaga: przycisk „Skanuj Foldery Teraz (dla tej gry)” (`ui/game_details.py:223`) skanuje **screenshoty**, a nie gry, więc etykieta wprowadza w błąd.

**4.1.2. Google Drive nie działa: są dwie implementacje i obie są zepsute**
- `cloud/cloud_manager.py`: klasa `CloudManager` (:19) to atrapa. `setup_google_drive` (:59), `upload_to_google_drive` (:71) i `download_from_google_drive` (:85) tylko logują „nie jest jeszcze zaimplementowana” i zawierają TODO. Nikt nie importuje tej klasy ani modułu (cały `cloud/` to martwy kod).
- `game_launcher.py` ma własną, częściową implementację, którą podpięto do UI (checkbox „Google Drive” w `launcher/settings_page_content.py:459-464`, przyciski „Prześlij/Pobierz” :476-480):
  - `upload_to_cloud_thread` wywołuje `self.do_upload_to_google_drive()` (`game_launcher.py:1911`), a ta metoda **nie istnieje nigdzie**. W wątku leci `AttributeError`, do kolejki nie trafia ani `DONE`, ani `ERROR`, więc okno postępu wisi bez końca (`check_progress_queue` odpytuje co 100 ms, `game_launcher.py:1917-1935`).
  - `setup_google_drive` (`game_launcher.py:1655`) i `download_from_google_drive` (:1828) importują `google_auth_oauthlib` i `googleapiclient`, ale te pakiety są zakomentowane w `requirements.txt:46-49`, więc kończy się to `ModuleNotFoundError`.
  - Jeśli brakuje `credentials.json`, `setup_google_drive` wraca bez ustawienia `self.google_drive_creds`, a zaraz potem `build(..., credentials=self.google_drive_creds)` rzuca `AttributeError` (`game_launcher.py:1813-1814`, `:1833-1835`).
  - Token jest zapisywany przez `pickle` do `token_google_drive.pickle` w katalogu aplikacji (`game_launcher.py:1662-1679`). Przy wczytaniu podmienionego pliku pickle wykonuje dowolny kod.
  - `upload_to_google_drive` w `game_launcher.py:1808` jest martwe (nic go nie wywołuje).
- README jest wewnętrznie sprzeczne: `README.md:29`/`:289` („Sync saves to GitHub or Google Drive”) kontra `README.md:229`/`:489` („not implemented”).

**4.1.3. GitHub sync wymaga pakietu, którego nie ma w zależnościach**
`launcher/cloud_github_runtime.py:18-21` importuje `github` (PyGithub) leniwie, a `PyGithub` jest zakomentowany w `requirements.txt:45`. Po czystej instalacji z `requirements.txt` funkcja oznaczona w `docs/ROADMAP.md` jako „Zrobione” kończy się `ModuleNotFoundError`. CI tego nie wykrywa, bo import jest leniwy.

**4.1.4. Tłumaczenia wyłączone (DummyTranslator), a `languages.py` to gra Pong**
- `launcher/init_constructor_runtime.py:330-331`: `self.translator = DummyTranslator()` z logiem „tłumaczenia tymczasowo wyłączone”.
- `launcher/utils.py:220-243`: `DummyTranslator` ma na sztywno słownik EN→PL z 11 kluczami, a `set_language()` to `pass`.
- `game_launcher.py:913` `change_language()` nie jest wywoływane nigdzie i nie ma do niego UI. Klucz `settings["language"]` ustawia tylko martwy `utils/config_manager.py:114`.
- `languages.py` **nie zawiera tłumaczeń**. To samodzielna gra „Pong - AI” w pygame (`languages.py:1-12`, `pygame.display.set_mode` na poziomie modułu, więc import otworzyłby okno). Nikt go nie importuje. `docs/ROADMAP.md:28` błędnie sugeruje, że to baza do wielojęzyczności.
- Klucze `gettext` mieszają język źródłowy: sidebar używa kluczy angielskich (`launcher/sidebar_ui.py:11-94`), a tray i roadmapa polskich (`launcher/tray_runtime.py:45-61`, `launcher/roadmap_archive_runtime.py:31-43`, `launcher/discord_runtime.py:28`).

**4.1.5. Filtr zaawansowany ignorowany przy sortowaniu widoku listy**
`launcher/library_list_sort.py:29-34`: gdy wybrany jest zapisany filtr zaawansowany, kod loguje „(logika filtrowania TODO)” i bierze **wszystkie** gry (`games_to_sort = list(self.games.keys())`). Kliknięcie nagłówka kolumny w widoku listy gubi więc filtr, mimo że ewaluator istnieje (`launcher/advanced_filter_eval.py:6` `_check_game_against_rules`). Potwierdza to `docs/ROADMAP.md:36`.

**4.1.6. Inne niepodpięte funkcje (martwe metody z logiką)**
- `monitor_roadmap` (`launcher/roadmap_archive_runtime.py:428`, wrapper `game_launcher.py:2351`) nigdy nie jest uruchamiane. Automatyczna zmiana statusu „Planowana” na „Nie ukończona na czas” nie działa.
- `setup_key_bindings` (`game_launcher.py:947`) nigdy nie jest wywoływane. Strzałki i Enter generowane przez pad (`launcher/gamepad_runtime.py:25-38`, `event_generate("<Left>")` itd.) nie mają globalnej obsługi nawigacji fokusa (do weryfikacji, jak to wygląda w praktyce).
- `track_play_time` (`game_launcher.py:1348`) to martwa, starsza wersja śledzenia czasu (zastąpiona przez `session_monitor_runtime`).
- `upload_to_github` i `run_threaded_operation` w `cloud/cloud_manager.py:165`, `:351` są martwe.

### 5.2. Autostart z Windows: błędna wartość w rejestrze

`game_launcher.py:1603-1635` `toggle_autostart`, wpis `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\GameLauncher`:

```python
sys.executable + " " + os.path.abspath(__file__),      # game_launcher.py:1617
```

- Brak cudzysłowów. Ścieżki ze spacjami (np. `C:\Program Files\Python313\python.exe` albo folder launchera ze spacją) zostaną źle rozbite przez Windows.
- Przy uruchomieniu ze źródeł zapisuje `python.exe` zamiast `pythonw.exe`, więc przy starcie systemu pojawia się okno konsoli.
- W wersji PyInstaller `sys.executable` to exe, ale `__file__` wskazuje na nieistniejący `.py` wewnątrz paczki. Do exe trafia zbędny argument (działa raczej przypadkiem, do weryfikacji).
- Gałąź „włącz” nie ma obsługi błędów (`OSError` z `winreg` leci do handlera Tk). Stan checkboxa jest czytany z `settings["autostart"]` (`launcher/settings_page_content.py:332`), a nie z rejestru, więc może się z nim rozjechać (np. po przeniesieniu launchera na pendrive ze zmianą litery dysku wpis wskazuje starą ścieżkę).

### 5.3. Obsługa wyjątków

**4.3.1. Gołe `except:`**
`grep -nE "except\s*:"` na śledzonych `*.py` daje **2** trafienia, a nie około 31 (najwyraźniej poprawione wcześniej w gałęzi polish):

| # | Miejsce | Kontekst |
|---|---|---|
| 1 | `ui/components.py:25` | `ToolTip.show_tooltip`: fallback na `bbox("insert")` |
| 2 | `ui/music_player.py:1882` | `try: pass / except: pass`, kod bez żadnego efektu |

**4.3.2. Szerokie `except Exception`**
W kodzie jest **198** klauzul `except Exception` lub `except Exception as e:`. Wyjątki są cicho połykane (`except Exception:` + `pass`) w:
- `launcher/discord_runtime.py:119` (zamykanie RPC)
- `launcher/settings_page_content.py:131`
- `launcher/stats_runtime.py:106`
- `ui/music_player.py:1420`
- `ui/music_player.py:4558`

Pozostałe zwykle tylko logują. Wiele z nich kończy się `return` bez informacji dla użytkownika.

**4.3.3. Pętle wątków bez `try`**
- `launcher/session_monitor_runtime.py:9-61` `monitor_game_sessions`: `while True` bez `try/except`. Dowolny wyjątek (np. `KeyError` po usunięciu gry, `RuntimeError` przy zmianie słownika) po cichu zabija wątek, a śledzenie czasu gry przestaje działać do restartu.
- `launcher/reminders_runtime.py:105-119` `monitor_reminders`: to samo; dodatkowo `plyer.notification.notify` może rzucić wyjątek.

### 5.4. Wątki i bezpieczeństwo Tk

Tkinter nie jest thread-safe. Poniższe miejsca dotykają widżetów lub zmiennych Tk spoza głównego wątku:

| Miejsce | Wątek | Problem |
|---|---|---|
| `launcher/tray_runtime.py:13-20` `show_window` (wołane z `game_launcher.py:2047-2091` `show_*_from_tray`) | wątek pystray (`tray_runtime.py:65`) | `deiconify/lift/focus_force/update_idletasks` i budowanie całych stron (`show_home`, `show_library`…) bezpośrednio z wątku traya; `tray_icon.stop()` wołane z własnego callbacka |
| `game_launcher.py:2055` `exit_program` → `on_closing` | wątek pystray | zamykanie aplikacji i `root.destroy` spoza wątku Tk |
| `launcher/gamepad_runtime.py:25,27,32,35,38,45,49,51` | `controller_listener` (`init_constructor_runtime.py:506`) | `event_generate`, `canvas.yview_scroll`, `root.update_idletasks` bezpośrednio z wątku |
| `launcher/discord_runtime.py:65,71` | `_monitor_discord_connection` | `root.winfo_exists()` i `BooleanVar.get()` z wątku |
| `launcher/session_monitor_runtime.py:48` → `discord_runtime.py:153,238,242,270` | monitor sesji | `_update_discord_status` czyta `StringVar/BooleanVar` i przy błędzie woła `_handle_rpc_connection_error`, które pokazuje `messagebox` (`discord_runtime.py:98`) z wątku tła |
| `launcher/chat_render.py:186` `_load_and_display_chat_image_thumbnail` (cel wątku `chat_render.py:524`) | wątek pobierania | `target_label_widget.winfo_exists()` z wątku (reszta przez `root.after`) |
| `launcher/remote_server_runtime.py:78-79` | wątek Flask/werkzeug | `self.root.after(...)` wołane z wątku serwera; w praktyce działa, ale formalnie nie jest bezpieczne |
| `launcher/remote_server_runtime.py:62-72` | wątek Flask | `list_games` i `running_game` czytają `self.games` i `self.tracking_games` bez blokady, gdy wątek monitora je modyfikuje |

Wyścigi na danych i pliku konfiguracji:
- `save_config(self.config)` jest wołane z wątków tła: `launcher/session_monitor_runtime.py:44`, `launcher/reminders_runtime.py:118`, `launcher/roadmap_archive_runtime.py:438` (martwy `monitor_roadmap`). Główny wątek zapisuje równolegle. Nie ma blokady ani zapisu atomowego (`launcher/utils.py:265-273` otwiera `config.json` w trybie `"w"`), więc możliwy jest uszkodzony JSON albo `RuntimeError: dictionary changed size during iteration` przy `deepcopy` (do weryfikacji).
- `launcher/remote_server_runtime.py:109-124`: blok `finally` starego wątku serwera ustawia `_server_running=False` i `_flask_app=None`. Po „Regeneruj token” lub „Zmień port” (stop, a po 500 ms start, `:206`, `:238`, `:247`) spóźnione zakończenie starego wątku może wyłączyć flagę nowego serwera, który wtedy odpowiada 503 (do weryfikacji).
- Podwójny `DONE` w kolejce postępu chmury: `do_upload_to_github` sam wrzuca `"DONE"` (`launcher/cloud_github_runtime.py:126`), a `upload_to_cloud_thread` dodaje drugi (`game_launcher.py:1915`). Po błędzie (`ERROR:` + `DONE`) lub sukcesie (dwa `DONE`) w `self.progress_queue` zostaje nieodebrany `DONE`, który przy następnym przesyłaniu natychmiast zamyka okno postępu z komunikatem „sukces”.

### 5.5. Blokujące operacje sieciowe w wątku UI

- `launcher/updater_runtime.py:84-115` `download_and_update`: pobiera exe w wątku Tk przez `requests.get(download_url, stream=True)` **bez timeoutu**, więc UI zamarza. Ręczne sprawdzanie (`manual_check_updates` :117, przycisk `settings_page_content.py:695`) też blokuje do 10 s.
- `launcher/chat_auth.py:23` (`_chat_login`), `:184` (`_chat_register`), `launcher/chat_data.py:160,169` (`_fetch_chat_users`, wołane m.in. z `chat_rooms.py:159,309`, `chat_user_profile.py:156`, `chat_context_actions.py:303`): synchroniczne `requests` z timeoutem 10 s w wątku Tk.
- `launcher/cloud_github_runtime.py:185-285` `download_from_github`: całe pobieranie z GitHub (wiele plików) w wątku Tk, z wołaniem `update_idletasks` dla postępu.
- `launcher/game_process_runtime.py:143` `is_game_running`: `psutil.process_iter` jest wołane **dla każdej gry** co 5 s (`session_monitor_runtime.py:17`), czyli O(gry × procesy). Działa w wątku tła, ale przy dużej bibliotece mocno obciąża CPU.

### 5.6. Aktualizator: ryzykowna logika

`launcher/updater_runtime.py`:
- Repozytorium GitHub jest zahardkodowane (:20). Pobierany jest `assets[0]` bez sprawdzenia typu, sumy kontrolnej ani podpisu (:37).
- `copy /Y nowy.exe "{sys.executable}"` (:96-104): przy uruchomieniu ze źródeł `sys.executable` to **python.exe**, więc aktualizacja nadpisałaby interpreter. Przy buildzie onedir (`game_launcher.spec`) podmieniany jest tylko exe, bez `_internal/`.
- Wybierana jest **najstarsza** nowsza wersja (`sort` rosnąco, `[0]`, :48-49), więc aktualizacja idzie skokami po jednej wersji (może to być celowe).

### 5.7. Martwy i zdublowany kod

**4.7.1. Pakiet `utils/` (duplikat `launcher/utils.py`)**
- `utils/constants.py` powiela stałe z `launcher/utils.py` (`PROGRAM_VERSION`, ścieżki, `THEMES`, `MONTH_*`) plus stałe skanera (`COMMON_EXECUTABLES`, `NFO_PATTERNS`…). Importuje go tylko martwy `ui/game_grid_manager.py:5`.
- `utils/image_utils.py`: importuje go tylko `ui/game_grid_manager.py:5`, więc jest martwy.
- `utils/config_manager.py`: **jedyny żywy element**. `ui/manage_genres_window.py:4,114,145` używa `config_manager.save_config`, funkcjonalnie równoważnego `launcher/utils.save_config`. Reszta (`initialize_folders` :18, `load_config` :59 z własnymi domyślnymi, `load/save_local_settings`) jest nieużywana.
- `ui/game_grid_manager.py` (`GameGridManager` :8): nikt go nie importuje (jest tam też TODO :393).

**4.7.2. Puste lub atrapowe pakiety**
- `launcher/components/__init__.py`: tylko komentarz i `__all__ = []`. Katalog nie ma innych plików.
- `launcher/services/__init__.py`: `__all__ = []` (pakiet zawiera `theme_runtime.py` i `theme_store.py`, importowane bezpośrednio).
- `launcher/__init__.py:6,9-11`: `__version__ = "1.6.0"` (niezgodne z `PROGRAM_VERSION = "1.5.0"` w `launcher/utils.py:5`). `__all__ = ["GameLauncher"]` wskazuje nazwę, której pakiet nie definiuje, więc `from launcher import *` rzuci `AttributeError`.
- `ui/__init__.py`: leniwe eksporty przez `__getattr__`, nieużywane (wszyscy importują `from ui.xxx import ...`).
- `launcher/main.py`: alternatywny punkt wejścia, nigdzie nie używany. Robi `logging.basicConfig` przed `game_launcher.main()`, co może kolidować z `_setup_file_logging` (do weryfikacji).
- `cloud/cloud_manager.py`: cały moduł martwy (patrz 4.1.2).
- `languages.py`: gra Pong, martwy (patrz 4.1.4).

**4.7.3. Nieużywane wrappery i funkcje** (analiza AST: nazwa występuje tylko w definicji i w wywołaniu `gl_modul.nazwa`; dynamiczne `getattr` mogło umknąć, do weryfikacji)
- `game_launcher.py`: `_get_pynput_key_string` :237, `_select_chat_partner_silently` :277, `_open_chat_server_settings_dialog` :292, `_leave_room_action` :389, `_fetch_room_members_and_store` :393, `_select_and_upload_chat_file` :460, `_update_chat_partner_details` :566, `_display_chat_messages_from_history` :582, `_on_message_read_update` :616, `_apply_chat_message_tags_and_alignment` :657, `change_language` :913, `setup_key_bindings` :947, `create_recently_played` :1204, `create_random_games` :1245, `on_mouse_wheel` :1272, `track_play_time` :1348, `select_background_image` :1540, `toggle_show_token` :1566, `upload_to_google_drive` :1808, `show_reminders` :1991, `create_game_tile` :2017, `add_rss_feed` :2113, `remove_rss_feed` :2116, `monitor_roadmap` :2351, `_perform_backup_restore_thread` :2481, metody skanera :2517-2574, `save_ignored_folders` :2955.
- `ui/game_details.py`: `create_stats_labels` :610, `fetch_online_description_stub` :670, `create_action_buttons` :686, `toggle_cover_source` :1763.
- `ui/music_player.py`: `_seek_relative` :3433, `_finalize_folder_import` :3628, `_finalize_files_import` :4833, `import_internal_music` :5989.
- Atrybut funkcji `find_likely_executable.ignore_dirs` (`game_launcher.py:2534`) jest zdefiniowany, ale nieużywany (używane są tylko `ignore_files` i `preferred_keywords`, `launcher/scan_pipeline.py:95,136,210`).
- `SCRIPTHOOK_CONFIG_FILE` (`launcher/utils.py:33`, `utils/constants.py:53`) nie jest nigdzie używane. `external/ScriptHookConfig.ini` jest śledzony w git, mimo że `.gitignore` ignoruje `external/`.

**4.7.4. Zdublowane definicje metod w klasie** (późniejsza nadpisuje wcześniejszą)
W `game_launcher.py` **nie ma** duplikatów. Są w:
- `ui/game_details.py`: `GameDetailsWindow.start_scan_for_this_game` :494 i :571 (druga wersja dodaje sprawdzenie folderów).
- `ui/music_player.py`: `MusicPlayerPage._update_autoplay_button_text` :228 i :1589 (różne teksty: „Auto-play: Wł.” vs „Autoplay: Wł.”), `_toggle_autoplay` :1601 i :3332, `_delete_active_playlist_dialog` :2881 i :3020.

**4.7.5. Wzorce dynamiczne utrudniające analizę i port**
- `game_launcher.py:34-134`: `_LazyModule` i `globals().update({...})` wstrzykują około 70 aliasów `gl_*` do przestrzeni nazw modułu. `GameLauncher` (3109 linii) to w większości wrappery `def x(self): return gl_mod.x(self)`, a moduły `launcher/*.py` to funkcje przyjmujące `self` (pseudo-mixiny). Narzędzia statyczne (pyflakes, IDE) nie widzą tych nazw.
- Atrybuty na funkcjach jako konfiguracja (`game_launcher.py:2534-2562`) i `setattr(self, ...)` na instancji launchera (`launcher/backup_restore.py:780-797`, `launcher/chat_message_actions.py:404`, `launcher/chat_render.py:105`, `launcher/chat_socket.py:391`).

### 5.8. Brakujące pliki i zasoby

- `icons/attach_16.png` (`launcher/chat_layout.py:525`): brak w repo. Jest fallback (przycisk bez ikony).
- `icon.png` (`launcher/tray_runtime.py:31`): brak w repo (jest tylko `icon.ico`), a ścieżka jest względna do CWD. Fallback: `create_default_icon()`, więc tray zawsze ma ikonę zastępczą.
- `game_launcher.spec`: **nieśledzony** (`git status`: `??`), choć `CHANGELOG.md` deklaruje jego dodanie, a `README.md:134`/`:394` każe budować `pyinstaller --noconfirm game_launcher.spec`. Z czystego klonu build się nie uda.
- `icons/save_16.png` jest w repo, ale nieużywany (używany jest `save_disk_16.png`).
- `.gitignore` ignoruje `launcher/pages/` (pozostałość, katalog nie istnieje).

### 5.9. Zahardkodowane ścieżki i sekrety

- W kodzie (poza testami) nie znaleziono zahardkodowanych ścieżek `J:\`, `E:\` ani `C:\Users\...`. Wzmianki w `game_launcher.py:2409-2422` to docstring i komentarze funkcji przemapowującej. Testy celowo używają `D:\`, `E:\`, `F:\`.
- Względne ścieżki zależne od `os.chdir(APP_DIR)` (`game_launcher.py:3088`): `credentials.json` i `token_google_drive.pickle` (`game_launcher.py:1662-1678`), `icon.png` (`tray_runtime.py:31`), `IMAGES_FOLDER="images"` (`launcher/utils.py:24-26`). Działa tylko dlatego, że `main()` zmienia katalog roboczy.
- Sekrety: brak kluczy API i tokenów w repo. Jedyna zahardkodowana wartość to publiczny Discord Application ID (`launcher/init_constructor_runtime.py:297`, nie jest sekretem). Token w `tests/test_remote_app.py:12` jest testowy.
- `chat_server.py:170-177`: `cors_allowed_origins="*"`, `logger=True` i `engineio_logger=True` (bardzo gadatliwe logi), komentarz „W PRZYSZŁOŚCI PRZENIEŚ…” (:183).
- `launcher/updater_runtime.py:20`: zahardkodowany URL repozytorium wydań.

### 5.10. Niespójny język UI (PL/EN)

UI jest w większości po polsku, ale z wyjątkami:
- „❚❚ Pause” (`ui/music_player.py:5286`, `:6044`)
- „RAWG.io API Key:”, „Last.fm API Key:”, „Zapisz Last.fm Key”, „Zapisz RAWG Key”, „GitHub Token:” (`launcher/settings_page_content.py:392`, `:410`, `:440`)
- „Checklista”, „Autoplay/Auto-play” (dwie pisownie, patrz 4.7.4)
- placeholder „Item 1/Item 2” w podglądzie filtra (`ui/filters.py:822`)

Etykiety w sidebarze to angielskie klucze tłumaczone przez `DummyTranslator`; brak klucza skutkuje angielskim tekstem.

### 5.11. Rozbieżności dokumentacja a kod

| Twierdzenie | Źródło | Stan faktyczny |
|---|---|---|
| „Smart Scanning: automatic game detection from folders” | `README.md:19`, `:279` | brak UI (4.1.1) |
| „Cloud Backup: GitHub or Google Drive” | `README.md:29`, `:289` | GDrive zepsuty (4.1.2); README sam przeczy temu w `:229`, `:489` |
| „Chmura: GitHub” jako Zrobione | `docs/ROADMAP.md:22` | wymaga ręcznej instalacji PyGithub (4.1.3) |
| GDrive „tylko TODO w `cloud/cloud_manager.py`” | `docs/ROADMAP.md:27` | UI używa innej, zepsutej implementacji w `game_launcher.py`; `cloud_manager` jest martwy |
| „jest `languages.py`” jako baza wielojęzyczności | `docs/ROADMAP.md:28` | `languages.py` to gra Pong |
| `game_launcher.spec` dodany | `CHANGELOG.md` („Inne”), `README.md:134` | plik nieśledzony |
| „Testy pytest (62)” | `CHANGELOG.md` | 48 funkcji `test_*` + 3 `parametrize`, więc 62 przypadki są prawdopodobne (do weryfikacji uruchomieniem) |
| Wersja 1.5.0 | `CHANGELOG.md:3` | `launcher/__init__.py:6` mówi 1.6.0 |
| „Launch games remotely from anywhere on your network” | `README.md:79` | domyślnie nasłuch na `127.0.0.1` (`launcher/remote_app.py:33-34`), LAN po włączeniu opcji |
| Big Picture / gamepad | `README.md:75` | nawigacja strzałkami bez `setup_key_bindings` (4.1.6), wywołania Tk z wątku (4.4) |

### 5.12. Testy i CI

- `tests/` obejmuje tylko 4 moduły: `launcher/config_store.py` (12 testów), `launcher/launch_command.py` + fragment `game_process_runtime` (10), `launcher/paths.py` (15), `launcher/remote_app.py` (11). Brak testów UI, chatu, chmury, statystyk, osiągnięć, odtwarzacza, skanera, backupu i aktualizatora. Około 110 modułów nie ma testów.
- `.github/workflows/ci.yml`: `windows-latest`, Python 3.12/3.13. Kroki: `pip install -r requirements.txt pytest` (bez `requirements-dev.txt`), `python -m compileall -q .`, smoke import `game_launcher, chat_server`, `pytest -v` oraz grep pilnujący, żeby nie śledzić `config.json`, `local_settings.json`, `.db`, `.mp3`, `__pycache__`, `games_saves/`.
- CI **nie** uruchamia lintera (pyflakes/ruff), nie buduje PyInstallerem i nie sprawdza leniwych importów (PyGithub, google-*), dlatego błędy 4.1.2, 4.1.3 i brakujący `do_upload_to_google_drive` przechodzą.

### 5.13. Inne zauważone problemy

- `launcher/gamepad_runtime.py:43-49`: dwie gałęzie `elif` mają ten sam warunek (`BTN_NORTH`/`BTN_WEST`), więc druga („Page Up”, `yview_scroll(-1,"pages")`) jest nieosiągalna. Docstring obiecuje X = Page Up.
- `ui/music_player.py:1876-1883`: blok `try: pass / except: pass` i nieużywany `text_bbox`, pozostałość po refaktorze.
- `launcher/chat_messaging.py:93`, `:451`: plik jest otwierany bez `with`, a zamknięcie zależy od wątku uploadu. Gdy wątek nie wystartuje (wyjątek między `open` a `start`), uchwyt wycieka (do weryfikacji).
- `chat_server.py` ma 2820 linii w jednym pliku (Flask-SocketIO + SQLAlchemy), a `ui/music_player.py` około 6000 linii z duplikatami metod. Zastosowano tylko częściowy podział na moduły.
- `launcher/library_list_sort.py:45-52` i inne miejsca porównują z polskimi stringami UI („Wszystkie Typy”, „Gry PC”, „Wszystkie Gatunki”) jako wartościami logiki, więc tłumaczenie UI zepsułoby filtrowanie.
- `launcher/session_monitor_runtime.py:20`: `last_played` ustawiane przy wykryciu procesu, także dla gier uruchomionych spoza launchera. Dopasowanie po nazwie procesu może dawać fałszywe trafienia (do weryfikacji w `game_process_runtime.py:143`).

### 5.14. Pełna lista komentarzy TODO/FIXME/XXX/HACK

(FIXME/XXX/HACK: 0 trafień.)

| Plik:linia | Treść |
|---|---|
| `cloud/cloud_manager.py:64` | `# TODO: Implementacja logiki OAuth2 dla Google Drive` |
| `cloud/cloud_manager.py:76` | `# TODO: Implementacja logiki wysyłania` |
| `cloud/cloud_manager.py:90` | `# TODO: Implementacja logiki pobierania` |
| `cloud/cloud_manager.py:256` | `# TODO: Obsługa usuwania plików, które istnieją w repo, a nie ma ich lokalnie?` |
| `cloud/cloud_manager.py:290` | `# TODO: Wyświetlić użytkownikowi listę gier do pobrania (np. w nowym oknie)` |
| `launcher/chat_message_actions.py:352` | `# TODO: W przyszłości, zamiast tylko tekstu, można by dodać tutaj interaktywny element "Dołącz"` |
| `launcher/library_list_sort.py:32` | log: `Sortowanie listy dla filtra zaawansowanego '…' (logika filtrowania TODO).` |
| `launcher/server_selection.py:93` | `# TODO: Bindowanie <Double-1> do "Połącz" i <Button-3> do menu kontekstowego` |
| `ui/game_grid_manager.py:393` | `# TODO: Załadować rzeczywiste ikony z plików lub użyć biblioteki ikon` |
| `ui/music_player.py:1647` | `` # TODO: W przyszłości zapisz `new_mode` do `self.local_settings` jeśli chcesz, aby wybór był trwały `` (tryb widoku odtwarzacza nie jest zapamiętywany) |
| `ui/music_player.py:1701` | `# TODO: W przyszłości, po dodaniu kafelków, wywołaj odświeżenie ich układu` |
| `docs/ROADMAP.md:27`, `:36` | odwołania do powyższych TODO (Google Drive, sortowanie listy) |

### Dodatkowo zaobserwowane podczas testu exe (polish/v1.5.0)

- Strona Główna: „Czas spędzony w grach” pokazuje 0,00 h, mimo że gry mają `play_time` (lista „Najdłużej grane gry” obok pokazuje poprawne godziny) – dwa różne źródła danych (do weryfikacji).
- Pierwsze uruchomienie → „Nowy Użytkownik”: `AttributeError: list_view_frame` i podwójne `_post_init_heavy_jobs` – **naprawione** w 15111b7.
- Okno dialogowe startowe („Witaj w Game Launcher!”) i okna podrzędne mają domyślną ikonę Tk zamiast `icon.ico`.
- `get_contrast_color` loguje ostrzeżenie dla nazwanych kolorów Tk (np. `lightgoldenrod` w `MONTH_COLORS`), bo PIL ich nie zna.
- Aplikacja nie deklaruje DPI awareness – przy skalowaniu 150% okno jest rozmyte (skalowane przez Windows).
- Paczka PyInstaller ~288 MB (googleapiclient, babel, jedi wciągane bez potrzeby).

---

## 6. Formaty danych

Opis na podstawie kodu z gałęzi `polish/v1.5.0` (`PROGRAM_VERSION = "1.5.0"`, `launcher/utils.py:5`). Celem jest, żeby port w Go czytał istniejące dane użytkownika bez żadnej konwersji. Odwołania mają postać `plik:linia`. Rzeczy, których nie da się jednoznacznie ustalić z kodu, mają dopisek „(niepewne)”.

Zasady ogólne dla wszystkich plików JSON launchera:
- zapis: `json.dump(..., indent=4, ensure_ascii=False)`, kodowanie UTF-8 bez BOM, **zapis nieatomowy** (otwarcie z `"w"`, bez pliku tymczasowego): `launcher/utils.py:268-276`, `launcher/config_store.py:242-247`. Port powinien czytać tolerancyjnie (nieznane klucze zachowywać przy zapisie, brakujące uzupełniać domyślnymi), bo Python w wielu miejscach dopisuje klucze `setdefault`-em dopiero przy użyciu.
- znaczniki czasu „epoch” to `time.time()`, czyli **float** sekund (z częścią ułamkową), czas lokalny przy konwersji na datę (`datetime.fromtimestamp`).
- daty tekstowe: `"%Y-%m-%d"`.

### 6.1. Układ folderów (względem folderu aplikacji)

`APP_DIR` to folder z `game_launcher.py` (katalog nadrzędny `launcher/`) albo, w buildzie PyInstallera, folder z exe (`launcher/paths.py:39-46`). Punkt wejścia robi `os.chdir(APP_DIR)` (`game_launcher.py:3088`), dlatego część stałych jest celowo względna i odnosi się do CWD = APP_DIR (`launcher/utils.py:24-29`).

| Ścieżka (względem APP_DIR) | Stała / źródło | Zawartość |
|---|---|---|
| `data/` | `DATA_DIR` `launcher/utils.py:17` | dane użytkownika (nie trafiają do gita) |
| `data/config/config.json` | `CONFIG_FILE` `:22` | główna konfiguracja (sekcja 2) |
| `data/config/local_settings.json` | `LOCAL_SETTINGS_FILE` `:30` | ustawienia lokalne i sekrety (sekcja 4) |
| `data/config/achievements_def.json` | `ACHIEVEMENTS_DEFINITIONS_FILE` `:31` | definicje osiągnięć (sekcja 5) |
| `data/chat/chat.db` | `CHAT_DB_FILE` `:32`; serwer: `chat_server.py:121-136` | baza SQLite serwera czatu (sekcja 6) |
| `data/chat/uploads/` | `chat_server.py:47,75` | załączniki czatu |
| `data/chat/secret_key` | `chat_server.py:140-162` | klucz sesji Flask serwera czatu (sekret) |
| `data/games_saves/<gra>/` | `GAMES_FOLDER` `launcher/utils.py:23` | kopie zapisów gier (sekcja 7) |
| `data/logs/game_launcher.log` (+ `.1`…`.3`) | `game_launcher.py:3041-3060` | `RotatingFileHandler`, 1 000 000 B, 3 kopie, UTF-8, format `%(asctime)s - %(levelname)s - %(message)s` |
| `images/` | `IMAGES_FOLDER = "images"` `launcher/utils.py:27` | okładki, awatar, zrzuty ekranu, okładki muzyki |
| `images/<nazwa gry>.png` | `create_default_cover` `launcher/utils.py:333` | wygenerowana okładka zastępcza (nazwa gry **bez** sanityzacji) |
| `images/<safe>_cover<ext>` | `ui/game_details.py:517-521` | własna okładka skopiowana z okna szczegółów; `safe` = nazwa z `[\\/*?:"<>|]` zamienionymi na `_` |
| `images/<safe>_rawg_cover<ext>` | `launcher/rawg_cover.py:43-44` | okładka pobrana z RAWG |
| `images/avatar.png` | `game_launcher.py:1969-1973` | awatar użytkownika (zawsze ta nazwa, niezależnie od formatu źródła) |
| `images/screenshots/<safe>/<plik>` | `ui/game_details.py:778-790` | zrzuty ekranu dodane ręcznie |
| `images/music_covers/`, `images/music_covers/lastfm/` | `ui/music_player.py:3202,4398,5087` | okładki utworów / z Last.fm |
| `images/thumbnails/<nazwa>_thumb<ext>` | `THUMBNAIL_FOLDER` `utils/constants.py:49`, `utils/image_utils.py:210-213` | miniatury; używane tylko przez stary pakiet `utils/` (`ui/game_grid_manager.py`). W głównym kodzie `launcher/` brak użycia (niepewne, czy ten kod jest jeszcze wywoływany) |
| `internal_music/` | `INTERNAL_MUSIC_DIR` `launcher/utils.py:28` | wewnętrzna biblioteka muzyki (tworzony przy starcie `launcher/init_constructor_runtime.py:188`) |
| `custom_themes/` | `CUSTOM_THEMES_DIR` `launcher/utils.py:29` | pliki motywów JSON (tworzony `init_constructor_runtime.py:189`) |
| `mods_storage/` | `MODS_STORAGE_FOLDER` `utils/constants.py:54` | stała zdefiniowana, ale nigdzie nieużywana w `launcher/` ani `ui/` |
| `external/ScriptHookConfig.ini` | `SCRIPTHOOK_CONFIG_FILE` `launcher/utils.py:33` | stała zdefiniowana, poza definicją **nieużywana** |
| `icons/` | `resource_path("icons", ...)` `launcher/paths.py:54-64` | ikony tylko do odczytu; najpierw `APP_DIR/icons`, potem `sys._MEIPASS/icons` |
| `icon.ico` | `resource_path("icon.ico")` | ikona aplikacji |
| `credentials.json`, `token_google_drive.pickle` | `game_launcher.py:1662-1678` (względne do CWD = APP_DIR) | OAuth Google Drive: klient i token (pickle Pythona, **sekret**; nieczytelny wprost w Go) |

Migracje ze starych lokalizacji (jednorazowe, wykonywane przy wczytaniu; działają tylko gdy cel **nie istnieje**, a źródło istnieje):

| Stara lokalizacja | Nowa | Mechanizm | Linia |
|---|---|---|---|
| `APP_DIR/config.json` | `data/config/config.json` | `os.replace` | `launcher/config_store.py:21-39,263` |
| `APP_DIR/games_saves/` | `data/games_saves/` | `os.replace`; gdy się nie uda, to `copytree` + `rmtree` | `launcher/config_store.py:42-68,264` |
| `APP_DIR/local_settings.json` | `data/config/local_settings.json` | `os.replace` | `launcher/config_store.py:132` |
| `APP_DIR/achievements_def.json` | `data/config/achievements_def.json` | `os.replace`; błąd jest tylko logowany | `launcher/achievements_defs.py:11-32` |
| `APP_DIR/chat.db` | `data/chat/chat.db` | `os.replace` | `chat_server.py:123-133` |
| `APP_DIR/chat_uploads/*`, `APP_DIR/uploads/*` | `data/chat/uploads/` | per plik `os.replace`; przy kolizji `<base>_legacy_<8hex>.<ext>` | `chat_server.py:81-118` |

Migracje treści w `local_settings.json` (stare klucze czatu) i `config.json` (`rss_feeds`, `launch_profiles`) opisują sekcje 2 i 4.

### 6.2. `data/config/config.json`

Wczytywanie: `launcher/config_store.py:262-382` (`load_config`). Zapis: `launcher/utils.py:268-276` (`save_config`), który robi głęboką kopię, koduje ścieżki przenośnie (sekcja 3), usuwa `settings.github_token` i zapisuje. Gdy JSON jest uszkodzony, `load_config` zwraca konfigurację domyślną (`:270-272`), a następny zapis **nadpisuje** uszkodzony plik.

Konfiguracja domyślna (`config_store.py:250-259`): `{"version": "1.5.0", "games": {}, "settings": {}, "groups": {}, "user": {}, "emulators": {}, "saved_filters": {}}`.

#### 6.2.1 Klucze najwyższego poziomu

| Klucz | Typ | Opis / kto zapisuje | Linia |
|---|---|---|---|
| `version` | string (semver) | brak → `"0.0.0"`; jeśli starsza niż `PROGRAM_VERSION`, jest podbijana do bieżącej. Nigdy nie jest obniżana | `config_store.py:276-278` |
| `games` | obiekt `{nazwa_gry: Game}` | kluczem jest **wyświetlana nazwa gry** (unikalna); sekcja 2.2 | |
| `settings` | obiekt | sekcja 2.3 | |
| `groups` | obiekt `{nazwa_grupy: [nazwa_gry, ...]}` | grupy statyczne; tworzenie `launcher/library_groups_runtime.py:54`, dopisywanie `game_launcher.py:1459-1460`, `launcher/library_list_context.py:168-169`; usunięcie gry czyści ją ze wszystkich grup (`launcher/game_crud_runtime.py:170-172`) | |
| `user` | obiekt | sekcja 2.4 | |
| `emulators` | obiekt `{nazwa: {"path": str}}` | jedyne pole to `path` (exe emulatora), zapis `launcher/emulator_settings_runtime.py:109`. `paths.py:157` toleruje też starą postać **listy** obiektów z `path` | |
| `saved_filters` | obiekt `{nazwa: {"name": str, "rules": [Rule]}}` | filtry zaawansowane, sekcja 2.7 | `ui/filters.py:77-80,112-115` |
| `roadmap` | lista `RoadmapItem` | sekcja 2.5; tworzony `setdefault` przy starcie | `launcher/init_constructor_runtime.py:262` |
| `archive` | lista `RoadmapItem` (ukończone) | sekcja 2.5 | `init_constructor_runtime.py:263` |
| `mods_data` | obiekt | sekcja 2.6 | `init_constructor_runtime.py:264` |
| `last_mod_locations` | obiekt `{nazwa_gry: [ścieżka, ...]}` | do 5 ostatnich folderów/zipów modów, najnowszy na początku | `ui/mod_manager.py:131-132,433-439,539-545` |
| `reminders` | lista `{"time": float epoch, "message": str, "notified"?: bool}` | `notified=true` ustawiane po wyświetleniu powiadomienia; data wpisywana jako `"%Y-%m-%d %H:%M:%S"` i zamieniana `time.mktime` (czas lokalny) | `launcher/reminders_runtime.py:45-48,109-117` |

Plik `config.example.json` w repo zawiera też klucze, których kod **nie czyta** (np. `settings.scan_recursive`, `settings.ignored_folders`, `settings.rawg_api_key`, `settings.emulators`, `user.total_launcher_time`, `user.last_login_date`, `user.theme_changes`). Są nieistotne, ale port powinien je przepuszczać bez zmian.

#### 6.2.2 `games[<nazwa>]` – rekord gry

Rekord nie ma stałego schematu: różne ścieżki tworzenia zapisują różne zestawy pól. Wszystkie odczyty używają `.get(klucz, domyślna)`.

Miejsca tworzenia i zapisu:
- formularz `GameForm.save` (`ui/game_form.py:545-696`), potem `add_game` dopisuje statystyki (`launcher/game_crud_runtime.py:22-33`);
- import ze skanu folderów (`ui/dialogs.py:560-587`);
- edycja `edit_game` (`launcher/game_crud_runtime.py:74-83`). **Uwaga:** rekord jest **zastępowany** wynikiem formularza plus zachowanymi `play_time`, `completion`, `last_played`, `play_sessions` i `date_added`. Pozostałe pola (np. `play_count`, `screenshots`, `checklist`, dane RAWG, `cover_rawg`) **giną** przy edycji. To zachowanie oryginału, prawdopodobnie błąd (niepewne, czy port ma je odtwarzać).

| Pole | Typ | Jednostka / znaczenie | Kto zapisuje |
|---|---|---|---|
| `name` | string | kopia klucza słownika (formularz zapisuje ją zawsze) | `ui/game_form.py:564`, `ui/dialogs.py:571` |
| `game_type` | `"pc"` \| `"emulator"` | brak → traktowane jako `"pc"` (`launch_command.py:71`, `advanced_filter_eval.py:95`) | `game_form.py:565` |
| `exe_path` | string \| null | exe gry PC; dla emulatora `null`. **Ścieżka przenośna** (sekcja 3) | `game_form.py:585,632` |
| `launch_profiles` | lista `{"name": str, "exe_path": str\|null, "arguments": str}` | profil 0 to zawsze `"Default"` z `exe_path: null` (null = użyj `exe_path` gry). `arguments` dzielone `shlex.split(posix=False)` (`launch_command.py:34-41,74-111`). Dla emulatora `[]` z formularza, ale `load_config` i tak wstawia `Default` | `config_store.py:337-365`, `game_form.py:586-588,633-635`, `game_crud_runtime.py:27-33` |
| `emulator_name` | string \| null | klucz w `config.emulators` | `game_form.py:590,628` |
| `rom_path` | string \| null | ścieżka ROM/ISO, **przenośna** | `game_form.py:591,629` |
| `emulator_args` | string \| null | argumenty emulatora. Polecenie: `[emu_exe] + shlex(args) + [rom]` (`launch_command.py:118-156`) | `game_form.py:592,630` |
| `save_path` | string | folder zapisów gry (źródło dla backupu zapisów), **przenośna**; `""` = brak. `repair_save_paths` może podmienić nazwę użytkownika w ścieżce (`game_launcher.py:2433-2446`) | `game_form.py:638` |
| `cover_image` | string | aktywna okładka. Zwykle **względna** `images\\<plik>` (separator `\` z `os.path.join` na Windows), ale formularz zapisuje dokładnie to, co wpisano, więc może to być ścieżka bezwzględna (`game_form.py:641-665`). Ścieżki względne rozwiązuje się względem APP_DIR (`remote_server_runtime.py:33`). **Nie** należy do `GAME_PATH_KEYS`, więc nie podlega remapowaniu litery dysku. Pusty string lub brak pliku → generowana jest okładka `images/<nazwa>.png` i zapisywana w config (`game_launcher.py:2333-2346`) | wiele miejsc |
| `cover_custom` | string | ścieżka własnej okładki (`images\\<safe>_cover<ext>`) | `ui/game_details.py:552` |
| `cover_rawg` | string | ścieżka okładki z RAWG (`images\\<safe>_rawg_cover<ext>`) | `ui/game_details.py:1562` |
| `_auto_cover` | bool | `true`, gdy `cover_image` to wygenerowany placeholder (pole zapisywane do pliku) | `game_launcher.py:2342`, `ui/game_details.py:1774` |
| `genres` | lista string | gatunki użytkownika | `game_form.py:668` |
| `tags` | lista string | tagi (z pola tekstowego rozdzielanego przecinkami) | `game_form.py:681-683` |
| `rating` | number (float) \| null | ocena; `null` = brak (liczona jako „nieoceniona” w osiągnięciach) | `game_form.py:672` |
| `version` | string | wersja gry (dowolny tekst, np. `"Year: 1999"` z parsowania nazwy folderu) | `game_form.py:679` |
| `notes` | string | notatki | `game_form.py:684`, `game_details.py:1457` |
| `folder_path` | string | folder gry, tylko przy imporcie ze skanu (informacyjnie, **nie** podlega remapowaniu) | `ui/dialogs.py:573` |
| `date_added` | float epoch | data dodania | `game_crud_runtime.py:22`, `dialogs.py:581` |
| `play_time` | float | **sekundy** łącznego czasu gry (suma `end-start` sesji) | `launcher/session_monitor_runtime.py:27-29` |
| `play_count` | int | liczba uruchomień z launchera | `launcher/game_process_runtime.py:91` |
| `last_played` | float epoch \| null | ustawiane przy starcie gry z launchera oraz przy wykryciu działającego procesu | `game_process_runtime.py:90`, `session_monitor_runtime.py:20` |
| `play_sessions` | lista `{"start": float epoch, "end": float epoch}` | dopisywane po zakończeniu sesji wykrytej przez monitor (co 5 s); źródło statystyk dziennych i miesięcznych (`launcher/stats_data.py:60-75`, `launcher/playtime_stats_runtime.py:99-101`) | `session_monitor_runtime.py:30-32` |
| `completion` | int 0–100 | procent ukończenia (pytanie po zamknięciu gry, `askinteger` 0..100); w nowych rekordach `0` | `game_launcher.py:1183-1196,1369-1374` |
| `screenshots` | lista string | zrzuty dodane ręcznie, ścieżki względne `images\\screenshots\\<safe>\\<plik>` | `ui/game_details.py:778-797`, domyślnie `[]` `config_store.py:367` |
| `autoscan_screenshots` | lista string | zrzuty znalezione automatycznie, ścieżki **bezwzględne** (`os.path.abspath`), nieremapowane | `launcher/screenshot_scan_runtime.py:249-256`, domyślnie `[]` `config_store.py:368` |
| `checklist` | lista `{"task": str, "done": bool}` | lista zadań gry | `ui/game_details.py:1201-1233`, domyślnie `[]` `config_store.py:369` |
| `vr_mode` | bool | tylko odczyt (dopisek „(VR)” na kafelku); żaden kod go nie zapisuje | `launcher/library_grid_runtime.py:169-170` |
| `rawg_id` | int | ID gry w RAWG | `launcher/rawg_fetch_runtime.py:68` |
| `rawg_slug` | string | slug RAWG | `rawg_fetch_runtime.py:69` |
| `description` | string \| null | `description_raw` z RAWG | `rawg_fetch_runtime.py:80`, kopiowane `ui/game_details.py:1608-1626` |
| `release_date` | string \| null | `released` z RAWG (`YYYY-MM-DD`) | `rawg_fetch_runtime.py:81` |
| `website` | string \| null | | `:82` |
| `developers`, `publishers` | lista string | | `:83-88` |
| `genres_api`, `tags_api` | lista string | gatunki i tagi z RAWG, oddzielne od `genres`/`tags` użytkownika | `:89-94` |
| `platforms` | lista string | | `:95-99` |
| `requirements_pc` | `{"minimum": str\|null, "recommended": str\|null}` | tylko gdy RAWG je zwróci | `:110-113` |

Usunięcie gry (`launcher/game_crud_runtime.py:150-174`) kasuje także okładkę z `cover_image` (tylko jeśli leży bezpośrednio w `images/`) oraz cały folder `data/games_saves/<nazwa>`.

#### 6.2.3 `settings`

Wartości domyślne dopisywane przez `load_config` (`config_store.py:280-328`). Pozostałe pola pojawiają się dopiero po pierwszym zapisie z UI.

| Klucz | Typ | Domyślnie | Opis / linia |
|---|---|---|---|
| `theme` | string | odczyt z domyślną `"Dark"` | nazwa motywu wbudowanego (`THEMES` w `launcher/utils.py:118+`) albo własnego; zapis `launcher/services/theme_runtime.py:59,193,430` |
| `custom_themes` | obiekt `{nazwa: definicja}` | — | stary sposób przechowywania motywów w config, używany jako fallback, gdy brak pliku w `custom_themes/` (`theme_runtime.py:473`, `ui/filters.py:982`) |
| `background_image` | string | — | bezwzględna ścieżka obrazu tła, nieremapowana (`game_launcher.py:1540-1546`) |
| `language` | string | — | kod języka (`game_launcher.py:914`) |
| `autostart` | bool | — | lustro wpisu `HKCU\...\Run\GameLauncher` (`game_launcher.py:1607-1635`) |
| `custom_genres` | lista string | `[]` | gatunki dodane przez użytkownika (`ui/manage_genres_window.py:99-113`) |
| `cloud_service_google_drive`, `cloud_service_github` | bool | — | `game_launcher.py:1596-1601` |
| `sync_local_settings_to_cloud` | bool | odczyt z domyślną `false` | czy synchronizować `local_settings.json` z GitHub (`launcher/cloud_github_runtime.py:98,224`); brak UI, który by go zapisywał (niepewne) |
| `auto_backup_on_exit` | bool | odczyt z domyślną `true` | autozapis zapisów gry po jej zamknięciu (`game_launcher.py:2851`, `session_monitor_runtime.py:50`) |
| `rss_feeds` | lista `{"url": str, "active": bool, "name": str}` | `[{"url": "https://feeds.ign.com/ign/games-all", "active": true, "name": "IGN Games"}]` | migracja: lista stringów → obiekty z `name=url` (`config_store.py:281-302`); zapis `launcher/news_runtime.py:127,146,204` |
| `news_post_limit` | int | `10` | `config_store.py:304`, `news_runtime.py:236` |
| `scan_folders` | lista string | `[]` | foldery skanowane w poszukiwaniu gier (`launcher/scan_pipeline.py:28,44,154`) |
| `scan_recursively` | bool | `true` | `config_store.py:319`, `scan_pipeline.py:53` |
| `scan_ignore_folders` | lista string | `["_CommonRedist","DirectX","DotNet","Redist","Tools","Benchmark","support","data","__overlay"]` | porównywane bez rozróżniania wielkości liter (`scan_pipeline.py:183`, zapis `game_launcher.py:2970`) |
| `autoscan_screenshot_folders` | lista string | `[]` | `config_store.py:320`, `screenshot_scan_runtime.py:56` |
| `autoscan_on_startup` | bool | `false` | `config_store.py:321`, `screenshot_scan_runtime.py:92` |
| `screenshot_scan_ignore_folders` | lista string | `["thumb_cache","cache","temp","thumbnails"]` | `config_store.py:322-324`, `screenshot_scan_runtime.py:36` |
| `screenshot_filename_patterns` | lista string | `["{game_name}*.png","{game_name}*.jpg","{game_name}*.jpeg"]` | tylko domyślna; skaner faktycznie dopasowuje `nazwa_pliku.lower().startswith(nazwa_gry.lower())` (`screenshot_scan_runtime.py:243-247`), a wzorce nie są czytane (niepewne) |
| `launcher_drive` | string `"E:"` | ustawiane przy każdym wczytaniu i zapisie | litera dysku launchera, sekcja 3 (`paths.py:171-173,184-196`) |
| `github_token` | — | — | **nigdy** nie jest zapisywany w config (usuwany w `save_config`, `utils.py:271`); żyje w `local_settings` |

Czcionki **nie** ma w `settings`. Czcionka UI to `local_settings.ui_font`.

#### 6.2.4 `user`

| Klucz | Typ | Opis | Linia |
|---|---|---|---|
| `username` | string | nazwa gracza; domyślnie `"Gracz"` w kreatorze pierwszego uruchomienia | `launcher/window_ops.py:60-62`, `game_launcher.py:1642` |
| `avatar` | string | ścieżka do awatara, zwykle `images\\avatar.png` (względna); `""` = brak | `game_launcher.py:1972-1973,2029` |
| `theme_change_count` | int | licznik zmian motywu (dla osiągnięć) | `init_constructor_runtime.py:268`, `theme_runtime.py:60` |
| `achievements` | obiekt `{id_osiągnięcia: AchState}` | stan osiągnięć | `config_store.py:373-374` |

`AchState` = `{"unlocked": bool, "timestamp": float epoch | null, "current_progress": number}` (`launcher/achievements_runtime.py:73-75,275-303`). Po odblokowaniu `current_progress` = `target_value` z definicji. Opcjonalnie `"_triggered_at_night": true`, gdy gra została uruchomiona między 2:00 a 4:00. Flaga jest ustawiana tylko pod stałym ID `night_owl` (`launcher/game_process_runtime.py:37-50`) i usuwana po odblokowaniu (`achievements_runtime.py:303`).

#### 6.2.5 `roadmap` i `archive`

`RoadmapItem` (`launcher/roadmap_archive_runtime.py:353-359`):

| Pole | Typ | Opis |
|---|---|---|
| `game_name` | string | nazwa gry (klucz w `games`, porównanie bez rozróżniania wielkości liter przy dodawaniu, `:340`) |
| `start_date`, `end_date` | string `YYYY-MM-DD` | plan |
| `time_spent` | float sekundy | czas gry naliczany, gdy `status == "Planowana"` (`session_monitor_runtime.py:35-41`) |
| `status` | string | `"Planowana"` → `"Ukończona"` (ręcznie, `:383`) albo `"Nie ukończona na czas"` (automatycznie, gdy `end_date < dziś`, `:434-435`) |
| `completion_date` | string `YYYY-MM-DD` | tylko w `archive`; ustawiane przy oznaczeniu ukończenia (`:384`) |

Ukończenie przenosi kopię pozycji z `roadmap` do `archive` (`:381-390`).

#### 6.2.6 `mods_data`

```
mods_data = { "<nazwa_gry>": { "profiles": { "<profil>": { "mods": { "<nazwa_moda>": Mod }, "load_order": ["<nazwa_moda>", ...] } } } }
```
Profil `"default"` jest tworzony automatycznie i nie można go usunąć (`ui/mod_manager.py:263-268,343`). `Mod` ma dwie postacie:
- instalacja z ZIP (`ui/mod_manager.py:467-472`): `{"active": bool, "priority": int, "location": str (folder, do którego rozpakowano), "zip_file": str (nazwa pliku zip)}`;
- instalacja z folderu, kopiowana do folderu gry (`ui/mod_manager.py:620-626`): `{"active": bool, "priority": int, "files_changed": [ścieżki względne do folderu gry], "backup_folder": str (bezwzględna: `<folder_gry>/_backup_<mod>_<int epoch>`), "location": str (folder źródłowy moda)}`.

`priority` zmieniane o ±1 (`:719,735`). Folder gry = `dirname(games[g].exe_path)`. Ścieżki w `mods_data` **nie** są remapowane przy zmianie litery dysku.

#### 6.2.7 `saved_filters` – reguły filtra zaawansowanego

`Rule = {"field": str, "operator": str, "value": any}` (`ui/filters.py:618`). Wszystkie reguły łączy AND (`launcher/advanced_filter_eval.py:6-159`).

Pola (`ui/filters.py:373-392`), typy i operatory (polskie napisy są wartościami zapisanymi w JSON):

| `field` | typ | uwagi |
|---|---|---|
| `name` | text | |
| `genres`, `tags` | list | |
| `rating`, `completion` | number | `value` jako float |
| `play_time` | number | `value` w **godzinach** (float); pole porównywane jako `play_time/3600` zaokrąglone do 2 miejsc |
| `date_added`, `last_played` | date | `value` jako `"YYYY-MM-DD"`; epoch gry zamieniany na datę lokalną i porównywany **leksykograficznie** jako string |
| `game_type` | choice | brak → `"pc"` |
| `emulator_name` | choice | |

| Typ | Operatory |
|---|---|
| text | `zawiera`, `nie zawiera`, `równa się`, `zaczyna się od`, `kończy się na`, `jest ustawione`, `nie jest ustawione` (porównania bez rozróżniania wielkości liter) |
| list | `zawiera`, `nie zawiera`, `jest ustawione`, `nie jest ustawione` |
| number | `==`, `!=`, `>`, `<`, `>=`, `<=`, `jest ustawione`, `nie jest ustawione` |
| date | `jest równe`, `jest przed`, `jest po`, `jest ustawione`, `nie jest ustawione` |
| choice | `jest`, `nie jest`, `jest ustawione`, `nie jest ustawione` |

Błąd w oryginale: dla typu `list` operatory `zawiera`/`nie zawiera` są mapowane na nieistniejące klucze `"zawiera (lista)"`/`"nie zawiera (lista)"` (`advanced_filter_eval.py:108-112`). Taka reguła zawsze daje `false`, więc gra jest odfiltrowywana. Port powinien zachować format danych, a zachowanie poprawić. Nieznane pole: typ zgadywany z wartości (`:70-81`). Nieznany operator: gra jest odrzucana.

### 6.3. Kodowanie ścieżek (`launcher/paths.py`)

Dotyczy wyłącznie tych pól (`paths.py:138-162`):
- `GAME_PATH_KEYS = ("exe_path", "rom_path", "save_path")` w każdym `games[*]`;
- `PROFILE_PATH_KEYS = ("exe_path",)` w każdym `games[*].launch_profiles[*]`;
- `EMULATOR_PATH_KEYS = ("path",)` w każdym `emulators[*]` (dict lub lista).

Puste wartości (`""`, `null`) są pomijane. Inne ścieżki (`cover_image`, `screenshots`, `autoscan_screenshots`, `folder_path`, `background_image`, `user.avatar`, `mods_data`, `last_mod_locations`, `settings.scan_folders`) **nie** są przekształcane. Zapisują się tak, jak powstały: względne `images\...` albo bezwzględne z literą dysku.

Zapis, `to_portable(path)` (`paths.py:86-108`, wywoływane przez `make_config_portable` `:165-174`). Operacje są w semantyce Windows (`ntpath`), porównanie bez rozróżniania wielkości liter:
1. ścieżka bez litery dysku: jeśli zaczyna się od pojedynczego `\` lub `/` (zakorzeniona bez dysku), jest normalizowana (`normpath`); w przeciwnym razie (względna, UNC) zostaje bez zmian;
2. ścieżka na **tym samym dysku co APP_DIR** i **wewnątrz APP_DIR** → ścieżka względna do APP_DIR (`ntpath.relpath`, np. `Gry\Gothic\Gothic.exe`);
3. ścieżka na tym samym dysku, poza APP_DIR → bez litery dysku (`\Gry\Gothic\Gothic.exe`);
4. inny dysk lub UNC → `normpath`, bez innych zmian.

Dodatkowo `settings.launcher_drive = "<LITERA>:"` (wielka litera) przy każdym zapisie, jeśli APP_DIR ma literę dysku.

Odczyt, `resolve_config_paths` (`paths.py:177-197`), wywoływany na końcu `load_config` (`config_store.py:376`):
1. `old_drive = settings.launcher_drive` (upper). Jeśli zarówno stara, jak i nowa litera są niepuste i się różnią, każda ścieżka zaczynająca się od `old_drive` dostaje nową literę (`remap_drive`, `:127-133`);
2. potem `resolve_path` (`:111-124`):
   - `\x\y` (zakorzeniona bez dysku) → `<dysk APP_DIR>\x\y`;
   - z literą dysku lub UNC (`\\`, `//`) → `normpath`;
   - zaczyna się od `%` lub `~` → bez zmian (nierozwinięta);
   - pozostałe (względne) → `normpath(join(APP_DIR, path))`;
3. `settings.launcher_drive` = bieżąca litera.

W pamięci programu ścieżki są zawsze bezwzględne. W pliku mogą wystąpić wszystkie cztery formy, więc port musi obsłużyć każdą z nich. Separator w zapisanych ścieżkach to `\`. Względne `cover_image` itp. rozwiązuje się po prostu względem APP_DIR.

### 6.4. `data/config/local_settings.json`

Plik ignorowany przez git, przypisany do maszyny. Wczytywanie: `launcher/config_store.py:131-239`. Zapis: `:242-247` (wartości sekretów pochodzące ze zmiennych środowiskowych są przed zapisem przywracane do wartości z pliku albo usuwane, `:101-110`). Uszkodzony JSON → `{}` plus wartości domyślne (`:138-142`).

Migracja starego, pojedynczego serwera czatu (`:146-199`): klucze `chat_server_url`, `chat_email`, `chat_password`, `chat_remember_me`, `chat_auto_login` są **usuwane** (`pop`) przy wczytaniu. Jeśli był `chat_server_url`, a `chat_servers` jest puste, powstaje wpis `{"name": "Domyslny Serwer (migr.)", "url": <stary>, "credentials": {email, password} (tylko jeśli remember_me), "remember_credentials": <remember_me>, "auto_login_to_server": <auto_login && remember_me>, "is_default": true, "last_used": time.time()}`. Gdy `chat_servers` jest puste, tworzony jest serwer `"Serwer Lokalny (Domyslny)"`, `http://127.0.0.1:5000`. Później `chat_remember_me` i `chat_auto_login` są i tak przywracane `setdefault(False)` (`:219-220`), a `chat_server_url`, `chat_email` i `chat_password` może ponownie zapisać kod UI (`launcher/chat_server_settings.py:92-93`, `launcher/chat_auth.py:46-50`).

| Klucz | Typ | Domyślnie | Opis / linia | Sekret |
|---|---|---|---|---|
| `github_token` | string | brak | GitHub PAT (zakres `repo`), `game_launcher.py:1575` | **TAK** (env `GL_GITHUB_TOKEN`) |
| `rawg_api_key` | string | brak | `launcher/rawg_settings.py:18`, `rawg_fetch_runtime.py:12` | **TAK** (env `GL_RAWG_API_KEY`) |
| `lastfm_api_key` | string | brak | `game_launcher.py:2891` | **TAK** (env `GL_LASTFM_API_KEY`) |
| `remote_control_token` | string | generowany przy pierwszym użyciu `secrets.token_urlsafe(24)` | token pilota WWW (`launcher/remote_server_runtime.py:19-25`, `launcher/remote_app.py:29-30`) | **TAK** (env `GL_REMOTE_TOKEN`) |
| `chat_servers` | lista `ChatServer` | 1 serwer lokalny | `{"id": str (uuid4), "name": str, "url": str, "is_default": bool, "last_used": float epoch \| null, "credentials": {"email"?: str, "password"?: str}, "remember_credentials": bool, "auto_login_to_server": bool}` (`ui/dialogs.py:568-577`, `launcher/chat_auth.py:97-133`) | **`credentials.password` jest zapisane jawnym tekstem** |
| `active_chat_server_id` | string | id domyślnego lub pierwszego | `launcher/server_selection.py:323,453` | |
| `chat_auto_connect_to_default` | bool | `true` | `server_selection.py:478` | |
| `chat_remember_me`, `chat_auto_login` | bool | `false` | stare klucze, nadal zapisywane (`chat_auth.py:260-261`) | |
| `chat_email`, `chat_password` | string | brak | stare klucze, zapisywane przy „zapamiętaj mnie” (`chat_auth.py:46-50`), usuwane przy następnym wczytaniu | **`chat_password` to sekret jawnym tekstem** |
| `chat_server_url` | string | brak | stary klucz, zapisywany przez `chat_server_settings.py:93` | |
| `chat_last_email` | string | `""` | `launcher/chat_navigation.py:18` | |
| `chat_last_user_id` | int \| null | `null` | | |
| `chat_blocked_user_ids` | lista int | brak | ID użytkowników zablokowanych lokalnie (`launcher/chat_blocking.py:28,69`) | |
| `remote_control_enabled` | bool | `false` | | |
| `remote_control_port` | int | `5050` | wartość `5000` jest przy wczytaniu zamieniana na `5050`, żeby nie kolidować z czatem (`config_store.py:203-206`) | |
| `remote_control_bind_lan` | bool | `false` | `false` = 127.0.0.1 | |
| `window_state` | string | `"normal"` | `"normal"` \| `"zoomed"` (`closing_runtime.py:33`) | |
| `window_geometry` | string | `"1024x768+100+100"` | geometria Tk `WxH+X+Y` | |
| `window_maximized` | bool | `false` | | |
| `library_view_mode` | string | `"tiles"` | `"tiles"` \| `"list"` | |
| `tiles_per_row` | int | `3` | | |
| `ui_font` | string | `"Segoe UI"` | rodzina czcionki UI (`theme_runtime.py:767-768`) | |
| `avatar_display_size` | int | `48` | px | |
| `discord_rpc_enabled` | bool | `false` | Discord RPC, client_id `1300136792636522517` (`init_constructor_runtime.py:297`) | |
| `discord_status_text` | string | `"Korzysta z Game Launcher"` | | |
| `last_run_date` | string `YYYY-MM-DD` | `""` | do liczenia serii dni (`init_constructor_runtime.py:269-288`) | |
| `consecutive_days` | int | `0` | seria kolejnych dni użycia (osiągnięcie `consecutive_days_used`) | |
| `total_launcher_usage_seconds` | number | `0` | łączny czas działania launchera, s (`closing_runtime.py:20`, reset `usage_runtime.py:53`) | |
| `launcher_daily_usage_seconds` | obiekt `{"YYYY-MM-DD": sekundy}` | `{}` | czas sesji launchera podzielony na dni lokalne (`closing_runtime.py:47-60`) | |
| `music_player_volume` | float 0..1 | `0.5` | | |
| `last_music_folder` | string | katalog domowy (`~`) | | |
| `music_hotkeys` | obiekt | `{"play_pause":"<alt>+<space>","next_track":"<alt>+<right>","prev_track":"<alt>+<left>","stop_music":"<alt>+s","volume_up":"<alt>+<up>","volume_down":"<alt>+<down>"}` | składnia skrótów pynput (`launcher/utils.py:108-115`, zapis `launcher/hotkey_input.py:222`) | |
| `music_hotkeys_enabled` | bool | `true` | | |
| `named_music_playlists` | obiekt | `{}` | playlisty, opis w sekcji 9 | |
| `active_music_playlist_name` | string \| null | `null` | | |
| `current_track_in_active_playlist_index` | int | `-1` | | |
| `music_repeat_mode` | string | `"none"` | (wartości: sekcja 9) | |
| `music_shuffle_mode` | bool | `false` | | |
| `music_favorite_tracks` | lista | `[]` | | |
| `music_autoplay_enabled` | bool | odczyt z domyślną `true` | `ui/music_player.py:131` | |
| `music_player_default_view` | string | — | tylko odczyt (`ui/music_player.py:1648`, zapis zakomentowany) | |
| `show_track_overlay` | bool | `false` | | |
| `overlay_x_pos`, `overlay_y_pos` | int \| null | `null` | pozycja nakładki z utworem (`overlay_controls.py:86-87,131-132`) | |
| `themes` | obiekt | — | tylko odczyt fallback w `ui/music_player.py:2162` (`themes[<motyw>].entry_background`); nic go nie zapisuje (niepewne, martwy kod) | |

Nadpisania ze zmiennych środowiskowych (`config_store.py:74-98`): jeśli zmienna jest ustawiona i po `strip()` niepusta, wartość z pliku jest zastępowana w pamięci, ale nie trafia do pliku.

| Klucz | Zmienna |
|---|---|
| `github_token` | `GL_GITHUB_TOKEN` |
| `rawg_api_key` | `GL_RAWG_API_KEY` |
| `lastfm_api_key` | `GL_LASTFM_API_KEY` |
| `remote_control_token` | `GL_REMOTE_TOKEN` |

Serwer czatu ma własne zmienne: `GL_CHAT_SECRET_KEY`, `GL_CHAT_HOST`, `GL_CHAT_PORT`, `FLASK_ADMIN_USER`, `FLASK_ADMIN_PASS` (sekcja 6).

Przy logowaniu (`redact_settings`, `config_store.py:113-128`) maskowane są klucze z `SECRET_KEYS` oraz każdy klucz zawierający `password`, `token` lub `credentials`, a także `chat_servers[*].credentials`. Port powinien traktować to samo jako sekrety.

### 6.5. `data/config/achievements_def.json`

Plik to lista JSON (nie obiekt). Wczytywanie: `launcher/achievements_defs.py:35-57`; brak pliku lub błąd → `[]`. Zapis z edytora w Ustawieniach: `json.dump(..., indent=2, ensure_ascii=False)` (`achievements_defs.py:140-148`).

Element (`ui/dialogs.py:1016-1026`):

| Pole | Typ | Opis |
|---|---|---|
| `id` | string `^[a-zA-Z0-9_]+$` | klucz w `user.achievements` |
| `name` | string | |
| `description` | string | |
| `icon` | string | ścieżka do obrazka (`""` = domyślna); otwierana bezpośrednio przez `Image.open` (`achievements_page.py:196-202`) |
| `rule_type` | string | patrz niżej |
| `target_value` | int lub float (float dla reguł `*_hours`) | > 0 |
| `hidden` | bool | ukryte do odblokowania |
| `genre` / `tag` / `group` | string | parametr dodatkowy dla reguł `genre_*`, `tag_*`, `group_*` |

Typy reguł obsługiwane w `launcher/achievements_runtime.py:86-273`. Wartości wejściowe liczone są w `:48-66`:

| `rule_type` | Bieżąca wartość |
|---|---|
| `games_launched_count` | liczba gier z `play_count > 0` |
| `library_size` | `len(games)` |
| `total_playtime_hours` | suma `play_time`/3600 (2 miejsca po przecinku) |
| `games_completed_100` | gry z `completion >= 100` |
| `playtime_single_game_hours` | max `play_time`/3600 |
| `genre_played_count` / `genre_completed_100` | gry z `genre` w `genres` (i `play_count>0` / `completion>=100`) |
| `tag_played_count` / `tag_completed_100` | j.w. dla `tag` w `tags` |
| `group_played_count` / `group_completed_100` | j.w. dla gier z `groups[group]`; nieistniejąca grupa → pominięcie |
| `roadmap_completed_count` | `len(archive)` |
| `roadmap_items_added` | `len(roadmap)` |
| `games_rated_count` | gry z `rating != null` |
| `groups_created` | `len(groups)` |
| `games_with_tags` | gry z niepustym `tags` |
| `themes_changed` | `user.theme_change_count` |
| `consecutive_days_used` | `local_settings.consecutive_days` |
| `mods_installed` | liczba wszystkich modów we wszystkich profilach `mods_data` |
| `game_launched_at_night` | 1, jeśli stan ma `_triggered_at_night` (ustawiane tylko dla ID `night_owl`); cel zawsze 1 |

Odblokowanie: `current >= target` (dla float z tolerancją 0.001). Zapis `unlocked=true`, `timestamp=time.time()`, `current_progress=target_value`. Nieznany `rule_type` nigdy nie zostaje odblokowany. Mapa tłumaczeń w edytorze (`achievements_defs.py:70-75`) zawiera tylko 4 typy, ale `AchievementForm` obsługuje pełną listę, o ile `ACHIEVEMENT_RULE_TYPES_TRANSLATED` ją zawiera (niepewne, gdzie definiowany jest pełny słownik).

### 6.6. chat.db i serwer czatu

Źródło: `chat_server.py` (2820 linii, samodzielny skrypt Flask + Flask-SocketIO + Flask-SQLAlchemy). Nie importuje żadnych modułów pomocniczych z repo — tylko biblioteki zewnętrzne (`flask`, `flask_socketio`, `flask_sqlalchemy`, `werkzeug`, `email_validator`) (`chat_server.py:3-27`). Wersje z `requirements.txt:13-17`: Flask>=3.0.0, Flask-SocketIO>=5.3.0, Flask-SQLAlchemy>=3.1.0, Werkzeug>=3.0.0.

#### Lokalizacje plików, konfiguracja, migracje

`BASE_DIR` = katalog skryptu, a w buildzie PyInstallera katalog `sys.executable` — **nie** CWD (`:43-45`).

| Element | Ścieżka / wartość | Linia |
|---|---|---|
| Katalog danych czatu | `BASE_DIR/data/chat` (tworzony `makedirs(exist_ok=True)`) | `:121`, `:135` |
| Baza SQLite | `BASE_DIR/data/chat/chat.db`, URI `sqlite:///<abs path>` | `:122`, `:136` |
| Uploady | `BASE_DIR/data/chat/uploads` (tworzony przy starcie) | `:47`, `:75`, `:83`, `:2811-2813` |
| Klucz sesji Flask | `GL_CHAT_SECRET_KEY` (env, po `strip()`), inaczej plik `BASE_DIR/data/chat/secret_key` (UTF-8, `strip()`), inaczej nowy `secrets.token_hex(32)` (64 znaki hex) zapisywany do tego pliku; błąd zapisu → klucz tylko na sesję | `:140-162` |
| Admin – login | env `FLASK_ADMIN_USER`, domyślnie `admin` | `:184-186` |
| Admin – hasło | env `FLASK_ADMIN_PASS`; brak → losowe `token_urlsafe(32)` (panel praktycznie zablokowany); trzymany tylko jako hash w pamięci | `:187-194` |
| Host / port | env `GL_CHAT_HOST` (dom. `127.0.0.1`), `GL_CHAT_PORT` (dom. `5000`); `socketio.run(..., debug=False, use_reloader=False)` | `:2817-2820` |
| Socket.IO | `cors_allowed_origins="*"`, `ping_interval=60`, `ping_timeout=120` | `:170-178` |
| Limit żądania | `MAX_CONTENT_LENGTH = 10 MiB` (dotyczy całego body, nie tylko pliku → 413) | `:72`, `:76-78` |

Migracje „legacy” (wykonywane przy imporcie modułu):

| Co | Stara ścieżka | Nowa ścieżka | Zachowanie | Linia |
|---|---|---|---|---|
| Uploady | `BASE_DIR/chat_uploads/*`, `BASE_DIR/uploads/*` (tylko pliki, bez rekursji) | `BASE_DIR/data/chat/uploads/<nazwa>` | `os.replace`; kolizja nazwy → `<base>_legacy_<8 hex z uuid4>.<ext>`; pusty stary katalog jest usuwany (`rmdir`). Uwaga: zmiana nazwy przy kolizji **nie** aktualizuje `message.attachment_server_filename` | `:48`, `:81-118` |
| Baza | `BASE_DIR/chat.db` | `BASE_DIR/data/chat/chat.db` | tylko gdy nowej brak, a stara istnieje; `os.replace` | `:123-133` |

Tworzenie schematu: wyłącznie `db.create_all()` w `if __name__ == "__main__"` (`:2814`) — tworzy brakujące tabele, **nie** zmienia istniejących. Brak jakichkolwiek `ALTER TABLE` / Alembic / migracji kolumn w pliku. Brak `PRAGMA foreign_keys=ON` → `ondelete` w FK **nie jest egzekwowane przez SQLite**; kaskady działają tylko na poziomie ORM (opisane niżej).

#### Schemat bazy (SQLAlchemy)

Nazwy tabel nadawane automatycznie przez Flask-SQLAlchemy (CamelCase → snake_case; brak jawnych `__tablename__`). Wszystkie `id` = `INTEGER PRIMARY KEY` (autoincrement rowid SQLite).

Konwencje typów w SQLite (SQLAlchemy dialekt sqlite):
- `db.String(n)` → `VARCHAR(n)` (długość nieegzekwowana przez SQLite), `db.Text` → `TEXT`.
- `db.Boolean` → `BOOLEAN` przechowywane jako INTEGER 0/1 (SQLAlchemy może dodać `CHECK (col IN (0,1))` — (niepewne), zależy od wersji; SA 2.x domyślnie nie dodaje).
- `db.DateTime` → TEXT w formacie `YYYY-MM-DD HH:MM:SS.ffffff` (zawsze 6 cyfr mikrosekund). Wartości z `datetime.datetime.now` → **czas lokalny, naive (bez strefy), NIE UTC**.
- `default=` to defaulty po stronie Pythona (brak `server_default`) — w DDL nie ma `DEFAULT`; port w Go musi sam wstawiać wartości.
- Brak kolumn JSON-w-tekście.

**`email_blacklist`** (`EmailBlacklist`, `:1056-1067`)

| Kolumna | Typ | Null | Unique | Default | Uwagi |
|---|---|---|---|---|---|
| id | INTEGER | PK | | | |
| email | VARCHAR(120) | NOT NULL | UNIQUE | | znormalizowany przez `email_validator` |
| reason | VARCHAR(255) | NULL | | | |
| added_at | DATETIME | NULL | | `datetime.now` | lokalny |

**`user`** (`User`, `:1070-1100`) — nazwa tabeli `user` (słowo kluczowe w niektórych SQL; w SQLite cytować `"user"`).

| Kolumna | Typ | Null | Unique | Default | Uwagi |
|---|---|---|---|---|---|
| id | INTEGER | PK | | | |
| username | VARCHAR(80) | NOT NULL | UNIQUE | | 3–80 znaków wymuszane tylko przy zmianie nazwy (`:1798`), nie przy rejestracji |
| email | VARCHAR(120) | NOT NULL | UNIQUE | | znormalizowany `validate_email(...).email` |
| password_hash | VARCHAR(128) | NOT NULL | | | hash Werkzeug, patrz niżej (scrypt ma >128 znaków — SQLite to przyjmuje) |
| created_at | DATETIME | NULL | | `datetime.now` | |
| is_banned | BOOLEAN | NOT NULL | | `False` | |
| is_admin | BOOLEAN | NOT NULL | | `False` | żaden endpoint go nie ustawia (tylko ręcznie w DB) |

**`blocked_relationship`** (`BlockedRelationship`, `:1103-1126`)

| Kolumna | Typ | Null | FK | Default |
|---|---|---|---|---|
| id | INTEGER | PK | | |
| blocker_id | INTEGER | NOT NULL | `user.id` ON DELETE CASCADE | |
| blocked_id | INTEGER | NOT NULL | `user.id` ON DELETE CASCADE | |
| timestamp | DATETIME | NULL | | `datetime.now` |

Ograniczenie: `UNIQUE(blocker_id, blocked_id)` nazwa `_blocker_blocked_uc` (`:1114-1116`). Relacje ORM: `blocker` (backref `User.blocking_relationships`), `blocked_user` (backref `User.blocked_by_relationships`).

**`message`** (`Message`, `:1129-1209`)

| Kolumna | Typ | Null | FK | Default | Uwagi |
|---|---|---|---|---|---|
| id | INTEGER | PK | | | |
| sender_id | INTEGER | NULL | `user.id` ON DELETE SET NULL | | |
| receiver_id | INTEGER | NULL | `user.id` ON DELETE SET NULL | | ustawione dla DM, NULL dla grupy |
| room_id | INTEGER | NULL | `chat_room.id` (bez ondelete) | | ustawione dla grupy, NULL dla DM |
| content | TEXT | NULL | | | maks. 5000 znaków (walidacja w handlerach) |
| timestamp | DATETIME | NULL | | `datetime.now` | klucz paginacji |
| edited_at | DATETIME | NULL | | | ustawiane przy edycji (`:2281`) |
| replied_to_message_id | INTEGER | NULL | `message.id` (self-FK, bez ondelete) | | |
| attachment_server_filename | VARCHAR(255) | NULL | | | `<uuid4hex>.<ext>` |
| attachment_original_filename | VARCHAR(255) | NULL | | | po `secure_filename` |
| attachment_mimetype | VARCHAR(100) | NULL | | | z nagłówka multipart klienta |
| is_read_by_receiver | BOOLEAN | NOT NULL | | `False` | sensowne tylko dla DM |

Relacje ORM: `sender`/`receiver` (backrefy `User.sent_messages`/`received_messages`), `room` (backref `ChatRoom.messages`, bez cascade → przy ORM-owym usunięciu pokoju SQLAlchemy ustawia `message.room_id = NULL`, wiadomości zostają osierocone (niepewne, domyślne zachowanie SA)), `replied_to_message` (self, backref `replies`).

**`chat_room`** (`ChatRoom`, `:1212-1243`)

| Kolumna | Typ | Null | Unique | FK | Default |
|---|---|---|---|---|---|
| id | INTEGER | PK | | | |
| name | VARCHAR(100) | NOT NULL | UNIQUE | | (3–100 znaków przy tworzeniu) |
| creator_id | INTEGER | NULL | | `user.id` ON DELETE SET NULL | |
| created_at | DATETIME | NULL | | | `datetime.now` |
| password_hash | VARCHAR(128) | NULL | | | NULL = pokój bez hasła; hash Werkzeug |

**`room_membership`** (`RoomMembership`, `:1246-1271`)

| Kolumna | Typ | Null | FK |
|---|---|---|---|
| id | INTEGER | PK | |
| user_id | INTEGER | NOT NULL | `user.id` ON DELETE CASCADE |
| room_id | INTEGER | NOT NULL | `chat_room.id` ON DELETE CASCADE |

Ograniczenie: `UNIQUE(user_id, room_id)` nazwa `_user_room_uc` (`:1259`). Backrefy `User.room_memberships` i `ChatRoom.memberships` z `cascade="all, delete-orphan"` (kaskada ORM). Brak osobnych tabel asocjacyjnych (`db.Table`) — członkostwo to pełny model. Brak jawnych indeksów poza PK i UNIQUE.

**Hasła** (`:1083-1087`, `:1239-1243`, `:193`): `werkzeug.security.generate_password_hash` z domyślną metodą. Werkzeug ≥3.0 → `scrypt:32768:8:1$<salt 16 znaków alnum>$<hex 128 znaków>` (scrypt N=32768, r=8, p=1, dkLen=64, salt używany jako bajty UTF-8 stringa). Starsze rekordy mogą mieć `pbkdf2:sha256:<iter>$<salt>$<hex>` (np. 260000/600000 iteracji, dkLen=32) — (niepewne, zależy od wersji Werkzeuga, którą zakładano bazę). Port w Go musi weryfikować oba formaty (porównanie hex w stałym czasie).

#### Uwierzytelnianie (stan faktyczny)

- **Użytkownicy czatu: brak tokenów/JWT/flask-login.** `/login` zwraca tylko `user_id`; wszystkie dalsze endpointy i eventy ufają `user_id`/`sender_id`/`creator_id` itp. podanym przez klienta. Jedyna weryfikacja hasła: `/login`, `DELETE /user/<id>`, hasło pokoju.
- Socket.IO `connect` nie sprawdza niczego (`:2060-2065`); „logowanie” socketu = event `authenticate` z `user_id` (bez hasła), nie sprawdza `is_banned`.
- **Admin:** podpisane ciasteczko sesji Flask (`session`, cookie `session`, itsdangerous z `SECRET_KEY`), klucz `is_admin_logged_in=True` (`:197-210`, `:234`). Brak → `401 {"error":"Administrator access required. Please log in."}`.
- Nagłówek `X-Initiator-User-ID` — używany tylko w `DELETE /rooms/<id>/members/<uid>` (`:1547`).
- Błędy zawsze jako `{"error": "..."}`; sukcesy zwykle `{"message": "..."}`.

#### Endpointy HTTP

Obiekty w odpowiedziach:
- **UserDict** (`:1092-1100`): `id, username, email, created_at (isoformat), is_banned, is_admin`.
- **RoomDict** (`:1225-1237`): `id, name, creator_id, creator_username ("Nieznany" gdy brak), created_at, has_password (bool), member_ids [int]`.
- **MessageDict** (`:1170-1209`): `id, sender_id, receiver_id, room_id, content, timestamp, sender_username ("Nieznany Nadawca" gdy brak), attachment_server_filename, attachment_original_filename, attachment_mimetype, is_read_by_receiver, replied_to_message_id, edited_at (iso lub null)` + opcjonalnie `replied_to_message_preview {id, sender_id, sender_username ("Nieznany"), content (pierwsze 50 znaków + "..." gdy >50), attachment_original_filename}`.
- Daty: Python `isoformat()` → `YYYY-MM-DDTHH:MM:SS.ffffff`, bez strefy; gdy mikrosekundy = 0, **bez** części `.ffffff`.

| Metoda | Ścieżka | Auth | Wejście | Odpowiedź (kody) | Linia |
|---|---|---|---|---|---|
| GET | `/` | – | – | tekst `Chat Server is running!` 200 | `:1274` |
| POST | `/register` | – | JSON `username, email, password` | 201 `{message, user_id}`; 400 brak pól / zły email; 403 email na blackliście; 409 username lub email zajęty | `:1838-1875` |
| POST | `/login` | – | JSON `email, password` | 200 `{message, user_id, username}`; 400; 404 email niezarejestrowany; 403 zbanowany (sprawdzane **przed** hasłem); 401 złe hasło | `:1878-1912` |
| GET | `/users` | – | – | 200 `[UserDict]` (zawiera e-maile wszystkich!) | `:1915-1919` |
| PUT | `/user/<int:user_id>` | – (ufa ID) | JSON `new_username` (3–80) | 200 `{message, new_username}` lub `{message:"Username is already the same"}`; 400; 404; 409; 500 | `:1789-1835` |
| DELETE | `/user/<int:user_id>` | hasło użytkownika | JSON `password` | 400/404/401; **zawsze 500 po poprawnym haśle** — odwołanie do niezdefiniowanej `email_to_blacklist` (NameError → rollback), konto nie jest usuwane. Intencja: usunąć usera i dodać email do blacklisty | `:1366-1421` |
| POST | `/users/<int:id>/block` | – (ufa ID) | JSON `blocker_id` | 201 `{message}`; 200 `{message:"User already blocked"}`; 400 brak JSON/ID / blokada siebie; 404; 500 | `:1279-1320` |
| DELETE | `/users/<int:id>/block` | – | JSON `unblocker_id` | 200 `{message}`; 400; 404; 500 | `:1323-1363` |
| (POST/DELETE) | `/users/<int:id>/block` – stuby | – | – | zduplikowane reguły `block_user_stub`/`unblock_user_stub` rejestrowane później; Werkzeug dopasowuje pierwszą regułę → stuby martwe (niepewne, ale zgodne z kolejnością rejestracji) | `:1703-1741` |
| POST | `/rooms` | – | JSON `name` (3–100), `creator_id`, opc. `password` | 201 `{message, room: RoomDict}` + broadcast `new_room_created`; twórca automatycznie członkiem; 400; 404 twórca; 409 nazwa zajęta; 500 | `:1424-1479` |
| GET | `/rooms` | – | – | 200 `[RoomDict]` (wszystkie pokoje) | `:1482-1485` |
| POST | `/rooms/<int:room_id>/members` | hasło pokoju gdy ustawione | JSON `user_id`, opc. `password` | 201 `{message}`; 200 już członek; 400; 404 pokój/user; 401 brak/złe hasło; 500 | `:1488-1534` |
| DELETE | `/rooms/<int:room_id>/members/<int:uid>` | nagłówek `X-Initiator-User-ID` lub JSON `admin_id` | opc. JSON `admin_id` | self-leave: initiator==uid lub admin_id==uid. Twórca wychodzi → **usunięcie całego pokoju** (członkostwa kaskadą ORM), event `room_deleted_by_creator`, 200. Inaczej usunięcie członkostwa, event `member_left_room` lub `member_removed_from_room` (gdy admin_id==creator_id), 200. Błędy: 404 pokój / nie-członek; 400 brak admin_id i nie self; 403 nie-twórca usuwa innych; 500 | `:1537-1700` |
| GET | `/rooms/<int:room_id>/messages` | członkostwo (ufa `user_id`) | query `user_id` (wymag.), `limit` (dom. 50, max 100), `before` (ISO) | 200 `{messages:[MessageDict] rosnąco, has_more, next_before}` (`next_before` = timestamp najstarszej zwróconej); 400; 403 nie-członek; 404 | `:1744-1786` |
| GET | `/messages/<int:u1>/<int:u2>` | – | query `limit` (50/max 100), `before` (ISO) | 200 jak wyżej, DM w obie strony; zły `before` → 500 (brak obsługi wyjątku) | `:1922-1954` |
| POST | `/upload_file` | – | multipart, pole `file` | 201 `{message, attachment_server_filename, attachment_original_filename, attachment_mimetype}`; 400 brak pliku / niedozwolony typ; 413 >10 MiB; 500 | `:1961-1996` |
| GET | `/download_file/<server_filename>` | – | – | plik `send_from_directory` z `as_attachment=True`, `download_name=secure_filename(original)` (z pierwszej wiadomości o tej nazwie, fallback nazwa serwerowa, fallback `downloaded_file`); 404/500 JSON | `:2000-2054` |
| POST | `/admin/login` | – | JSON `username, password` | 200 `{message}` + cookie sesji; 400; 401 | `:213-239` |
| POST | `/admin/logout` | admin | – | 200 | `:242-247` |
| GET | `/admin/` | – | – | HTML panelu (`ADMIN_PANEL_HTML`, `:313-746`), zawsze | `:809-819` |
| GET | `/admin/panel` | admin | – | HTML panelu | `:749-753` |
| GET | `/admin/status` | admin | – | 200 `{message:"Admin is logged in."}` | `:822-825` |
| GET | `/admin/users` | admin | – | 200 `[UserDict + is_online]` po `id` | `:828-844` |
| POST | `/admin/users/<int:id>/ban` | admin | – | 200 `{message, user}` (lub „already banned”); 404; 400 gdy `is_admin`; emit `account_status_changed` + rozłączenie wszystkich SID usera | `:847-913` |
| POST | `/admin/users/<int:id>/unban` | admin | – | 200 `{message, user}` / „not currently banned”; 404; emit `account_status_changed` | `:916-956` |
| DELETE | `/admin/users/<int:id>` | admin | – | 200; 404; 400 dla admina. Usuwa `blocked_relationship` i `room_membership` usera, w `message` ustawia `sender_id`/`receiver_id`=NULL, usuwa usera; emit `account_deleted` do jego SID + rozłączenie; broadcast `user_offline {user_id, username}`. Pokoje, których był twórcą, zostają z wiszącym `creator_id` (niepewne) | `:959-1048` |
| GET | `/admin/blacklist` | admin | – | 200 `[{id, email, reason, added_at}]` malejąco po `added_at` | `:250-269` |
| POST | `/admin/blacklist/add` | admin | JSON `email`, opc. `reason` | 201; 400; 409 duplikat; 500 | `:756-804` |
| DELETE | `/admin/blacklist/<email>` | admin | – | 200; 400 zły format; 404; 500 | `:272-310` |

#### Socket.IO — eventy

Pokoje Socket.IO (`:2113`, `:2138`): po `authenticate` socket dołącza do pokoju **`user.id` (int)** i do pokoju **`room_id` (int)** każdego swojego członkostwa. Każdy socket ma też domyślny pokój = własny `sid`. Uwaga na typy: `room_deleted_by_creator`, `member_left_room`, `member_removed_from_room` są emitowane do `str(id)` (`:1622`, `:1669`, `:1689`), a dołączenie jest do int → w python-socketio to różne klucze, więc te eventy najpewniej **nie docierają** (niepewne). Nowy członek dodany przez REST nie jest dołączany do pokoju Socket.IO aż do ponownego `authenticate`. Stan online: słownik w pamięci `connected_sids_to_user_id` (SID→user_id) (`:30`).

Klient → serwer:

| Event | Payload | Efekt / odpowiedzi | Linia |
|---|---|---|---|
| `connect` | – | tylko log, brak auth | `:2060` |
| `disconnect` | – | usuwa SID z mapy; broadcast `user_offline {user_id}` (skip własny SID) — także gdy user ma inne aktywne SID-y | `:2068-2077` |
| `authenticate` | `{user_id}` | ok: rejestruje SID, join pokoi; broadcast `user_online {user_id}` (skip sid); do sid `online_users_list {online_users:[user_id,...]}` (może zawierać duplikaty); do nadawcy `authenticated {user_id, username, authenticated:true}`. Błąd: `authentication_failed {message:"Invalid user_id"}` | `:2107-2158` |
| `leave_specific_room` | `{room_id}` | `leave_room(room_id)` dla SID; brak odpowiedzi | `:2080-2104` |
| `typing_start` | `{sender_id, receiver_id}` | do pokoju `receiver_id`: `typing_update {sender_id, is_typing:true}` (tylko DM) | `:2161-2182` |
| `typing_stop` | `{sender_id, receiver_id}` | `typing_update {sender_id, is_typing:false}` | `:2530-2551` |
| `send_message` | `{sender_id, receiver_id?, room_id?, content?, attachment_server_filename?, attachment_original_filename?, attachment_mimetype?, replied_to_message_id?}` | `room_id` ma pierwszeństwo (grupa, wymaga członkostwa); inaczej `receiver_id` (DM; odrzucane, gdy odbiorca zablokował nadawcę lub nadawca odbiorcę). Wymaga treści lub załącznika, treść ≤5000. Nie sprawdza `is_banned`. DM: `private_message_sent` (MessageDict) do sid nadawcy + `private_message_received` do pokoju `receiver.id`. Grupa: `group_message_sent` do sid + `group_message_received` do pokoju `room.id` (skip sid). Błędy: `message_error {message}` do sid | `:2554-2804` |
| `edit_message` | `{message_id, new_content, editor_user_id}` | tylko nadawca; niepusta, ≤5000; ustawia `content`, `edited_at=now()`. `message_edited_successfully` (MessageDict) do sid i do pokoju drugiego uczestnika DM (dla grupy **nie** rozsyłane do pokoju). Błąd: `message_edit_failed {message_id, error}` | `:2185-2324` |
| `delete_message` | `{message_id, deleter_user_id}` | tylko nadawca; usuwa plik załącznika z dysku i rekord. `message_deleted_successfully {success:true, message_id, room_id}` do sid, oraz do pokoju grupy (skip sid) albo do pokoju odbiorcy DM. Błąd: `message_delete_failed {message_id, error}` | `:2327-2450` |
| `mark_messages_as_read` | `{reader_id, message_ids:[...]}` lub `{reader_id, conversation_partner_id}` | ustawia `is_read_by_receiver=1` dla wiadomości, gdzie `receiver_id=reader_id`; do pokoju `msg.sender_id` dla każdej: `message_read_update {message_id, read_by_user_id, is_read:true}` (emit przed commitem); brak odpowiedzi do czytającego | `:2453-2527` |

Serwer → klient (zebrane):

| Event | Payload | Cel | Linia |
|---|---|---|---|
| `authenticated` | `{user_id, username, authenticated}` | sid | `:2151` |
| `authentication_failed` | `{message}` | sid | `:2157` |
| `online_users_list` | `{online_users:[int]}` | sid | `:2126` |
| `user_online` | `{user_id}` | broadcast bez sid | `:2121` |
| `user_offline` | `{user_id}` (+`username` przy usunięciu przez admina) | broadcast | `:2076`, `:1027` |
| `new_room_created` | RoomDict | broadcast | `:1465` |
| `room_deleted_by_creator` | `{room_id, room_name, creator_id, creator_username}` | `str(member_id)` | `:1614` |
| `member_left_room` | `{room_id, user_id, username}` | `str(room_id)` | `:1662` |
| `member_removed_from_room` | `{room_id, removed_user_id, removed_username, admin_id, admin_username}` | `str(room_id)` | `:1680` |
| `private_message_sent` / `private_message_received` | MessageDict | sid / pokój odbiorcy | `:2772`, `:2777` |
| `group_message_sent` / `group_message_received` | MessageDict | sid / pokój grupy (skip sid) | `:2783`, `:2788` |
| `message_error` | `{message}` | sid | wiele |
| `message_edited_successfully` | MessageDict | sid + drugi uczestnik | `:2291`, `:2306` |
| `message_edit_failed` | `{message_id, error}` | sid | wiele |
| `message_deleted_successfully` | `{success, message_id, room_id}` | sid + grupa/odbiorca | `:2412-2436` |
| `message_delete_failed` | `{message_id, error}` | sid | wiele |
| `message_read_update` | `{message_id, read_by_user_id, is_read}` | pokój nadawcy | `:2506` |
| `typing_update` | `{sender_id, is_typing}` | pokój odbiorcy | `:2177`, `:2546` |
| `account_status_changed` | `{banned: bool, reason: str}` | sid(y) usera | `:880`, `:938` |
| `account_deleted` | `{user_id, username}` | sid(y) usera | `:1008` |

#### Upload plików

| Reguła | Wartość | Linia |
|---|---|---|
| Dozwolone rozszerzenia (ostatnie po kropce, lowercase) | txt, pdf, png, jpg, jpeg, gif, zip, rar, 7z, doc, docx, xls, xlsx, ppt, pptx, mp3, wav, ogg, mp4, webm, webp | `:49-71`, `:1957-1958` |
| Limit rozmiaru | 10 MiB na całe żądanie (`MAX_CONTENT_LENGTH`) → 413 | `:72`, `:76` |
| Nazwa na dysku | `uuid4().hex` + `.` + rozszerzenie z `secure_filename(oryginał)` (lowercase) | `:1970-1975` |
| Nazwa oryginalna w odpowiedzi/DB | `secure_filename(file.filename)` (Werkzeug: ASCII, spacje→`_`, usuwa znaki spoza `[A-Za-z0-9_.-]`; polskie znaki giną). Jeśli po sanityzacji brak kropki → `IndexError` → 500 (niepewne) | `:1970-1972` |
| MIME | `file.mimetype` z części multipart klienta (nie wykrywany) | `:1987` |
| Pobieranie | `GET /download_file/<attachment_server_filename>` | `:2000` |
| Powiązanie z wiadomością | upload jest osobny; klient przekazuje pola `attachment_*` w `send_message`, serwer ich nie weryfikuje (plik może nie istnieć) | `:2563-2565` |
| Sprzątanie | plik usuwany tylko przy `delete_message`; osierocone uploady (bez wiadomości) zostają | `:2372-2390` |

### 6.7. Zapisy gier (data/games_saves)

**Stałe ścieżek** (`launcher/utils.py:17-29`): `DATA_DIR = APP_DIR/data`, `GAMES_FOLDER = APP_DIR/data/games_saves` (bezwzględna). `IMAGES_FOLDER="images"`, `INTERNAL_MUSIC_DIR="internal_music"`, `CUSTOM_THEMES_DIR="custom_themes"` są **względne** (CWD = APP_DIR, ustawiane w punkcie wejścia, `utils.py:24-26`). Duplikat stałych w `utils/constants.py:47` (stary moduł).
Migracja: `load_config()` przenosi stary folder `APP_DIR/games_saves` → `data/games_saves` (`launcher/config_store.py:264`, `_migrate_legacy_directory` ~`:50-67`: copytree + rmtree).

**Układ katalogów**

| Ścieżka | Znaczenie | Źródło |
|---|---|---|
| `data/games_saves/<nazwa_gry>/` | folder kopii danej gry | `ui/save_manager.py:28`, `launcher/autosave_runtime.py:18` |
| `.../<nazwa_gry>/_autosave/` | jedyny auto-zapis (nadpisywany) | `autosave_runtime.py:26`, `save_manager.py:131` |
| `.../<nazwa_gry>/saves/Save_<P>%_<YYYYmmdd>_<HHMMSS>/` | zapisy ręczne | `save_manager.py:154,221-222` |
| `.../<nazwa_gry>/<pliki importu>` | import przy dodawaniu gry: `copytree(źródło, GAMES_FOLDER/<gra>, dirs_exist_ok=True)` – pliki lądują **bezpośrednio w korzeniu** folderu gry, nie w `saves/` | `launcher/game_crud_runtime.py:43-46` |

**Nazwa folderu gry**: brak sanityzacji – używany jest surowy klucz gry z `config.json` (`games{<nazwa>}`) przez `os.path.join(GAMES_FOLDER, game_name)` (`save_manager.py:28`, `autosave_runtime.py:18`, `game_crud_runtime.py:43,166`, `duplicates_ui.py:222`). Zmiana nazwy gry nie przenosi folderu (nie znaleziono kodu rename) (niepewne).

**Nazewnictwo**

| Typ | Format | Parsowanie |
|---|---|---|
| Ręczny | `f"Save_{percent}%_{time.strftime('%Y%m%d_%H%M%S')}"` (czas lokalny), `percent` = int podany przez użytkownika (może być dowolny int, także ujemny) | `save_manager.py:221`; procent z regex `r"Save_(\d+)%"` (`:163-167`), brak dopasowania → 0 |
| Edycja ręcznego | nowa nazwa `Save_{nowy%}_{ts}`; `ts` = dwie ostatnie części po `_` jeśli obie cyfrowe, inaczej bieżący czas; `os.rename` | `save_manager.py:357-385` |
| Auto | stała nazwa `_autosave`; data wyświetlana = mtime folderu | `save_manager.py:131-147` |

Lista w UI: autosave pierwszy, ręczne sortowane po `(mtime folderu, percent)` malejąco; data/godzina z **mtime** folderu, nie z nazwy (`save_manager.py:180-198`).

**Format**: zwykłe skopiowane drzewa katalogów (nie zip). Brak plików metadanych/JSON – wszystkie metadane wynikają z nazwy folderu i mtime.
- Ręczny zapis/wczytanie/usunięcie: `_copy_or_delete_with_progress` (`launcher/file_ops_runtime.py:~12-80`), kopiowanie copytree/plik-po-pliku w wątku; pusty folder źródłowy → tylko `makedirs(dest)`.
- Autozapis: `os.walk` + `shutil.copy2` plik po pliku do `_autosave` (`autosave_runtime.py:69-95`), **bez wcześniejszego czyszczenia** – stare pliki, których już nie ma w źródle, zostają (merge/overwrite). Gdy źródło puste → tylko tworzy pusty `_autosave` (`:36-41`).

**Retencja/rotacja**: brak limitów – ręczne zapisy kumulują się bez końca; autosave pojedynczy, nadpisywany.

**Przywracanie** (`save_manager.py:275-315`): kopiowanie wybranego folderu (`saves/<nazwa>` lub `_autosave`) **na** `game.save_path` (nadpisanie plików, bez wcześniejszego usunięcia istniejących – merge) (niepewne co do trybu w `_perform_file_operation_thread`; najpewniej copytree `dirs_exist_ok`). Usuwanie gry kasuje cały `games_saves/<gra>` (`game_crud_runtime.py:166-168`, `duplicates_ui.py:222-224`).

**Klucze konfiguracji**

| Klucz | Plik | Znaczenie | Źródło |
|---|---|---|---|
| `games.<gra>.save_path` | config.json | folder zapisów gry (źródło kopii / cel przywracania); przechowywany przenośnie (bez litery dysku na dysku launchera / względnie do APP_DIR) | `launcher/paths.py:137,163-201` (`GAME_PATH_KEYS`) |
| `settings.auto_backup_on_exit` | config.json | bool, domyślnie `True`; po zakończeniu sesji gry wywołuje autosave | `launcher/session_monitor_runtime.py:50-54`, `settings_page_content.py:341`, `game_launcher.py:2851` |
| `settings.launcher_drive` | config.json | litera dysku do remapowania ścieżek | `paths.py:170-201` |

`repair_save_paths` (`game_launcher.py:2432-2457`) po przywróceniu backupu/pobraniu z GitHub podmienia prefiks `X:/Users/<ktoś>` na bieżący katalog domowy i robi `makedirs(save_path)` (nie zapisuje configu).

### 6.8. Motywy własne (custom_themes)

**Lokalizacja**: `APP_DIR/custom_themes/` (względna `CUSTOM_THEMES_DIR`, `utils.py:29`). Tworzona automatycznie, jeśli brak (`launcher/services/theme_store.py:62-64`). Lista motywów własnych **nie** jest przechowywana w configu – wynika z listingu katalogu (`theme_store.py:53-114`, cache w pamięci po mtime).

**Nazwa pliku**: `sanitize_theme_filename(name) = re.sub(r'[\\/*?:"<>|]', "_", name).strip()` + `.json` (`theme_store.py:7-13`). Wczytywane są wszystkie pliki `*.json` (case-insensitive), nazwa pliku nie musi odpowiadać nazwie motywu (`:67-71`).

**Format pliku** (zapis: `json.dump(..., indent=2, ensure_ascii=False)`, UTF-8; `theme_store.py:23-29`):
```json
{ "name": "<nazwa motywu>", "definition": { "<klucz>": "#RRGGBB", ... } }
```
Eksport (schowek/plik `<nazwa_lower_z_podkreśleniami>_theme.json`) ma identyczny format (`theme_runtime.py:503-536`).

**Walidacja**
- Odczyt `_load_theme_from_file` (`utils.py:246-265`): obiekt z kluczami `name` i `definition` (dict); inaczej plik pomijany. Brak walidacji kolorów przy odczycie.
- Motyw własny o nazwie wbudowanej → pomijany, wbudowany ma priorytet (`theme_store.py:91-96`).
- Edytor (`ui/filters.py:971-1019`): nazwa niepusta, nie wbudowana; każdy kolor `#RRGGBB`; klucze = klucze motywu `Dark` (`filters.py:716,726`).
- Import (`theme_runtime.py:638-697`): wymaga `name` (niepusty str) i `definition` (dict); wynikowa definicja zawiera **tylko klucze z `THEMES["Dark"]`**; brakujący klucz lub nie-`^#[0-9a-fA-F]{6}$` → wartość z `Dark`.
- `apply_theme` używa `.get(klucz, domyślna)`, więc brakujące klucze nie psują działania (`theme_runtime.py:67-...`).

**Klucze definicji** (wszystkie motywy wbudowane mają dokładnie te 12 kluczy, `utils.py:118-217`):
`background, foreground, button_background, button_foreground, entry_background, tree_background, tree_heading, scrollbar_trough, scrollbar_slider, link_foreground, chart_bar_color, chart_axis_color`.
Uwaga: wbudowane używają też nazw kolorów (`"white"`, `"black"`), nie tylko HEX.

**Motywy wbudowane (`THEMES`)**: `Dark`, `Light`, `Blue`, `Forest Green`, `Deep Purple`, `Solarized Dark`, `Gruvbox Dark`.

**Odwołanie z ustawień**: `config.json → settings.theme` = nazwa motywu (pole `name`, nie nazwa pliku); domyślnie `"Dark"` (`theme_runtime.py:57-63`, `init_constructor_runtime.py:382-385`). Nieznana nazwa → fallback `Dark` (i zapis `Dark` do configu w `_update_main_theme_selector`, `theme_runtime.py:188-193`). Usunięcie aktywnego motywu ustawia `Dark` (`:427-431`). Zmiana motywu inkrementuje `user.theme_change_count` (`:60`).
Pozostałość: `settings.custom_themes` (dict nazwa→definicja) jest tylko czytany jako fallback przy eksporcie i w walidacji nazwy edytora (`theme_runtime.py:473`, `filters.py:981-983`); nic go nie zapisuje (legacy) (niepewne).

### 6.9. Muzyka (stan w local_settings)

Cały stan w `data/config/local_settings.json` (`LOCAL_SETTINGS_FILE`, `utils.py:30`), zapis `json.dump(indent=4, ensure_ascii=False)` (`config_store.py:~232-237`). Zapisywane przez `MusicPlayerPage._save_player_settings` (`ui/music_player.py:316-348`).

| Klucz | Typ / domyślna (`config_store.py:~205-226`) | Znaczenie |
|---|---|---|
| `named_music_playlists` | `{nazwa: [wpis,...]}`, `{}` | playlisty |
| `active_music_playlist_name` | str/`null` | aktywna playlista; nieistniejąca → `"Główna Kolejka"` (`music_player.py:95-104`) |
| `current_track_in_active_playlist_index` | int, `-1` | indeks w `self.playlist` (lista aktywnej playlisty; przy shuffle – kolejność przetasowana) (niepewne) |
| `music_repeat_mode` | `"none"` / `"one"` / `"all"`, `"none"` | cykl `none→one→all` (`:3670-3675`) |
| `music_shuffle_mode` | bool, `false` | |
| `music_autoplay_enabled` | bool, `true` (brak setdefault, default w `:131`) | |
| `music_favorite_tracks` | lista **ścieżek** (str), `[]` | set ścieżek w pamięci; kolejność nieistotna (`:132,3050-3066`) |
| `music_player_volume` | float 0..1, `0.5` | |
| `last_music_folder` | str, `~` | |
| `music_hotkeys` | dict, `DEFAULT_MUSIC_HOTKEYS` (`utils.py:108-115`: `play_pause,next_track,prev_track,stop_music,volume_up,volume_down`, format pynput np. `"<alt>+<space>"`) | |
| `music_hotkeys_enabled` | bool, `true` | |
| `show_track_overlay`, `overlay_x_pos`, `overlay_y_pos` | bool/`null` | nakładka utworu |
| `lastfm_api_key` | str (sekret, env `GL_LASTFM_API_KEY`) | `config_store.py:73-78` |
| `music_player_default_view` | – | tylko zakomentowany zapis (`music_player.py:1647-1649`) |

**Wpis playlisty** (dict; `music_player.py:452-458,3598-3604,4716-4722`):
```json
{ "path": "<bezwzględna ścieżka pliku>", "focus_cover_path": "<ścieżka obrazu>|null",
  "lastfm_cover_path": "<ścieżka>|null", "is_internal": true|false }
```
- Stary format: wpis jako sam string ścieżki – konwertowany do `{"path": s, "focus_cover_path": null}` przy wczytaniu i zapisie (`:323-336,606-621`). Wpisy bez `path` są pomijane. Go musi akceptować oba warianty.
- Wymagane tylko `path`; `focus_cover_path` uzupełniany na `null`; `lastfm_cover_path`/`is_internal` mogą nie istnieć.
- Ścieżki **bezwzględne** (`os.path.abspath`), brak przenośności liter dysków (w przeciwieństwie do config.json).
- `focus_cover_path`: dowolny plik wybrany przez użytkownika (`:2755-2775`) lub okładka Last.fm.
- Okładki Last.fm zapisywane w `images/music_covers/lastfm/<artist>_<album>_lastfm.<jpg|png>` (nazwa obcięta do 150 znaków, znaki `\/*?:"<>|`→`_`) (`:4385-4403`).

**Playlisty stałe** (nieusuwalne): `"Główna Kolejka"` i `"Muzyka Wewnętrzna"` – tworzone puste, jeśli brak (`:82-93`).

**internal_music**: `APP_DIR/internal_music/` (płaski katalog, bez podfolderów). Import do biblioteki wewnętrznej kopiuje plik (`shutil.copy2`) z unikalną nazwą `<nazwa>_(N).<ext>` (N=1..100); plik o tej samej nazwie i rozmiarze traktowany jako duplikat (`:4870-4936`). Zwracana ścieżka bezwzględna, wpis z `is_internal: true`. Odświeżenie playlisty „Muzyka Wewnętrzna” synchronizuje ją z zawartością folderu (rozszerzenia `.mp3 .wav .ogg .flac .m4a`), usuwa wpisy pod `internal_music`, których plików już nie ma (`:350-522`).

### 6.10. Kopia zapasowa (backup_restore)

**Tworzenie** – `backup_to_local_folder` (`launcher/backup_restore.py:57-227`):
- Użytkownik wybiera folder bazowy; tworzony **folder** (nie zip) `GameLauncher_Backup_<YYYYmmdd_HHMMSS>` (`datetime.now().strftime("%Y%m%d_%H%M%S")`, czas lokalny, `:69-71`).
- Brak manifestu/pliku metadanych.

| Element w backupie | Źródło | Typ |
|---|---|---|
| `config.json` | `data/config/config.json` | plik (`copy2`) |
| `local_settings.json` | `data/config/local_settings.json` | plik |
| `achievements_def.json` | `data/config/achievements_def.json` | plik |
| `games_saves/` | `data/games_saves` | katalog (`copytree`) |
| `images/` | `APP_DIR/images` (okładki gier + `music_covers`) | katalog |
| `internal_music/` | `APP_DIR/internal_music` | katalog |
| `custom_themes/` | `APP_DIR/custom_themes` | katalog |

(`:73-116`). Brakujące źródła są pomijane z ostrzeżeniem; błąd pojedynczego elementu tylko logowany. Folder usuwany tylko przy krytycznym wyjątku (`:215-217`).
**Sekrety**: `local_settings.json` kopiowany w całości – zawiera `github_token`, `rawg_api_key`, `lastfm_api_key`, `remote_control_token`, dane logowania czatu (`chat_servers[].credentials`), chyba że pochodzą ze zmiennych środowiskowych (`config_store.py:73-108`). Nie są kopiowane: `data/chat/` (chat.db), `external/`, logi.

**Przywracanie** – `load_local_backup` (`:230-476`): wybór folderu, potwierdzenie, następnie dla każdej pozycji z tabeli (te same nazwy): plik – `os.remove` + `copy2`; katalog – `rmtree` celu + `copytree` (pełne zastąpienie). Brak elementu w backupie → pominięty. Potem przeładowanie `config`/`local_settings`, motywu (uwaga: `THEMES.get(theme)` – motyw własny daje `None` → fallback Dark, `:388`), odtwarzacza.
**Przepisywanie ścieżek**: w aktywnym przepływie brak – ścieżki gier w config.json są przenośne i rozwiązywane w `load_config` → `resolve_config_paths` (`config_store.py:376`, `paths.py:177-201`); ścieżki muzyki w local_settings pozostają bezwzględne bez zmian.

**Legacy (martwy kod)**: `_perform_backup_restore_thread` (`:517-873`, wrapper `game_launcher.py:2481`) oczekuje innego układu: `music_library_backup/`, `games_saves_backup/`, `images_backup/`; dla wpisów `is_internal` traktuje `path` jako nazwę pliku w `music_library_backup`, kopiuje do `internal_music` i przepisuje `path` na nową ścieżkę bezwzględną (`:586-662`), potem `repair_save_paths`. Używa niezdefiniowanego `self.restore_steps` – nieużywany (niepewne, czy jakieś wywołanie istnieje poza grepem).

### 6.11. Chmura (GitHub, Google Drive)

Implementacja aktywna: `launcher/cloud_github_runtime.py` (PyGithub, import leniwy `from github import Github, GithubException`, `:18-21`). `cloud/cloud_manager.py` to nieużywany szkic (`CloudManager` nigdzie nie instancjonowany; repo `GameLauncherBackups`, prywatne, `cloud_manager.py:16,136-146`) – ignorować.

**Klucze**

| Klucz | Plik | Znaczenie |
|---|---|---|
| `github_token` | local_settings.json (lub env `GL_GITHUB_TOKEN`) | PAT (classic, scope `repo`); `save_config` usuwa go z `settings` w config.json (`utils.py:271`); zapis `game_launcher.py:1572-1579,1683-1696` |
| `settings.cloud_service_github` | config.json | bool – włącza GitHub w `upload_to_cloud`/`download_from_cloud` (`game_launcher.py:1596-1601,1698-1806`) |
| `settings.cloud_service_google_drive` | config.json | bool – Google Drive |
| `settings.sync_local_settings_to_cloud` | config.json | bool, domyślnie `False` – czy wysyłać/pobierać `local_settings.json` (`:98-108,224-231`) |

**Repozytorium**: stała nazwa `game_launcher_saves` na koncie właściciela tokena (`user.get_repo`; brak → `user.create_repo(repo_name)` – domyślnie **publiczne**, `:78-83`).

**Układ w repo** (ścieżki z `/`):
```
config.json
achievements_def.json
local_settings.json          (opcjonalnie)
games_saves/<gra>/...        (odwzorowanie data/games_saves)
images/...                   (odwzorowanie APP_DIR/images)
```
(`:85-113`, `upload_folder_to_github` `:129-155` – ścieżka repo = `repo_folder/relpath` z `\`→`/`). `internal_music` i `custom_themes` nie są synchronizowane.

**API (Contents API przez PyGithub)**: `get_user`, `get_repo`, `create_repo`, `get_contents(path)`, `update_file(path, "Update <nazwa>", content, sha)`, przy 404 `create_file(path, "Create <nazwa>", content)`; jeden commit na plik. Pliki konfiguracyjne czytane jako tekst UTF-8, foldery binarnie. Pobieranie: `get_contents` rekurencyjnie (BFS po `type=="dir"`), zapis `decoded_content` (`:287-304`); pliki tekstowe `decoded_content.decode("utf-8")` (`:158-170`).

**Konflikty**: brak – upload zawsze nadpisuje (last-write-wins, sha pobierane tuż przed update); download nadpisuje lokalne pliki, nie usuwa lokalnych plików nieobecnych w repo i nie usuwa z repo plików skasowanych lokalnie. Po pobraniu: przeładowanie config/achievements/local_settings, `repair_save_paths`.

**Znane błędy (istotne przy porcie)**: `GithubException` nie jest zdefiniowany w zasięgu `upload_folder_to_github` (`:146`) ani `_download_single_file_from_github` (`:172`) – pierwszy upload nowego pliku z folderu (404) kończy się `NameError`. Limit Contents API ~100 MB/plik (1 MB dla `get_contents` bez blob API) (niepewne – zależne od PyGithub).

**Google Drive** (`game_launcher.py:1655-1681,1808-1858`): OAuth `InstalledAppFlow`, scope `drive.file`, `credentials.json` i token `token_google_drive.pickle` (pickle) w CWD=APP_DIR. Upload: tylko `config.json` (`files().create`, zawsze nowy plik – duplikaty). Download: pierwszy plik o nazwie `config.json` → nadpisuje `data/config/config.json`. `upload_to_cloud_thread` woła `self.do_upload_to_google_drive()`, która **nie istnieje** (`:1911`) – upload GDrive w praktyce nie działa.
