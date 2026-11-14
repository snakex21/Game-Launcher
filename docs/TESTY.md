# Testy ręczne przed wydaniem (Game Launcher 2.x)

Automatycznie (`cd go && go test -race ./...`, CI `go-ci.yml`) sprawdzane są m.in.: dane z 1.5.0 (config/local_settings bajt w bajt, zapisy, czat), uruchamianie gier i sesje (fałszywe procesy), menedżer modów na fałszywych grach (wszystkie 16 definicji, awaria w każdym kroku, aktualizacja gry, pliki tylko-do-odczytu, polskie znaki), złośliwe archiwa, aktualizator (fałszywy serwer wydań), czat (serwer + klient), pilot WWW, autostart (na kluczu testowym w HKCU), parsowanie skrótów, ramki Discord IPC oraz **okno zasobnika**: dodanie ikony, rejestracja globalnego skrótu Ctrl+Alt+Shift+F12, wykrycie zajętego skrótu, dostarczenie WM_HOTKEY i polecenia menu do własnego okna (`internal/winsys/tray_windows_test.go`).

Poniższe rzeczy wymagają człowieka (prawdziwy pulpit, prawdziwy Discord, prawdziwe gry). Każdy punkt to kilka sekund–minut. Zaznacz `[x]`.

## Zasobnik i okno
- [ ] Minimalizacja do zasobnika (Ustawienia → System) chowa okno; lewy klik na ikonie przywraca je na wierzch.
- [ ] Prawy klik na ikonie: menu otwiera się przy kursorze, każda pozycja działa, menu znika po kliknięciu obok.
- [ ] Start z autostartu (`-minimized`) – launcher startuje schowany w zasobniku.
- [ ] Powiadomienie systemowe (przypomnienie z datą za 1 min) pojawia się i kliknięcie otwiera launcher.

## Globalne skróty
- [ ] Włącz globalne skróty w Ustawieniach; w innej aplikacji (np. Notatnik) skonfigurowane skróty sterują muzyką.
- [ ] Skrót pokazania launchera działa, gdy okno jest schowane w zasobniku.
- [ ] Skrót zajęty przez inny program jest zgłoszony w Ustawieniach (np. ustaw ten sam, co w Discordzie/ShareX).
- [ ] W grze pełnoekranowej skróty muzyki działają (sprawdź w jednej grze DX11 i jednej starej DX9).

## Discord Rich Presence
- [ ] Przy uruchomionym Discordzie (aplikacja desktopowa) i włączonej opcji: w profilu widać „Gra: <nazwa>” z czasem od startu.
- [ ] Po zamknięciu gry status wraca do „W launcherze” / znika.
- [ ] Discord wyłączony w trakcie – launcher nie zgłasza błędów, po ponownym włączeniu Discorda status wraca.

## Menedżer modów na prawdziwych grach (zrób kopię zapisów gry przed testem)
- [ ] „Dowolna gra”: mały mod (np. tekstury) → Wdróż → gra startuje z modem → „Przywróć vanilla” → Steam/GOG „Zweryfikuj pliki” nie znajduje różnic.
- [ ] Skyrim SE / Fallout 4: mod z `.esp` → `plugins.txt` w `%LOCALAPPDATA%` zawiera `*Mod.esp`, gra ładuje plugin; po purge `plugins.txt` wraca do poprzedniej treści.
- [ ] Cyberpunk 2077: mod `.archive` + CET (`init.lua`) → zgoda na kod → gra działa; `archive\pc\mod\modlist.txt` ma kolejność z profilu.
- [ ] Valheim/BepInEx: BepInExPack + plugin z Thunderstore (pobrane ręcznie) → `BepInEx\plugins\<Autor-Nazwa>` → konsola BepInEx przy starcie.
- [ ] Stardew Valley: archiwum z dwoma modami SMAPI → dwa foldery w `Mods\`, SMAPI je ładuje.
- [ ] Wiedźmin 3 / RimWorld / Doom (GZDoom + IWAD) – po jednym modzie; Doom uruchamiany przyciskiem „Uruchom z modami”.
- [ ] Dwa mody z tym samym plikiem: zmiana kolejności i „Niech wygrywa ten mod” zmieniają plik w grze.
- [ ] Przełączenie profilu przy działającej grze jest odrzucone komunikatem; po zamknięciu gry działa.
- [ ] Aktualizacja gry przez Steam w trakcie, gdy mody są wdrożone: „Sprawdź pliki” pokazuje zmiany, „Wdróż” je naprawia, a „Przywróć vanilla” zostawia nową wersję plików gry.
- [ ] Zabicie launchera (Menedżer zadań) w trakcie wdrażania dużego moda → przy następnym otwarciu strony Mody pojawia się informacja „przerwana operacja – dokończona/wycofana”, gra jest spójna.
- [ ] Magazyn na pendrivie, gra na dysku C: wdrożenie kopiami działa; po odłączeniu pendrive’a gra nadal działa z wdrożonymi modami.

## Dane z wersji 1.5.0
- [ ] Exe w folderze z danymi 1.5.0 (kopia!): biblioteka, czasy gry, grupy, filtry, roadmapa, osiągnięcia i playlisty są takie jak w 1.5.0.
- [ ] Klucze API (RAWG, Last.fm, GitHub) działają po pierwszym starcie (zaszyfrowane DPAPI).
- [ ] Strona Mody pokazuje stare wpisy `mods_data` (tylko do odczytu).

## Aktualizator
- [ ] Po wydaniu kolejnej wersji: Ustawienia → Aktualizacje → „Sprawdź” znajduje ją, pobiera exe, sprawdza SHA-256 i uruchamia nową wersję; stara zostaje jako kopia do wycofania.
