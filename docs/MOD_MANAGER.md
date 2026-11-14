# Menedżer modów – stan implementacji (wersja 2.0.0)

Kod: `go/internal/modmgr` (opis pakietów niżej), interfejs: strona **Mody** (`go/internal/webui/web/app.js`), kanały mostu `mods.*` (`go/internal/app/mods.go`). Dane: `data\modmgr\` obok exe (magazyn, profile, manifesty, dziennik, kopie oryginałów). Pełny projekt (zaakceptowany przed implementacją) – w drugiej części tego pliku.

## Zrobione

| Obszar | Pakiet | Stan |
|---|---|---|
| Definicje gier (18 plików: 3 szablony + 15 gier), `extends`, szablony ścieżek względem nazwanych korzeni (bez liter dysku), definicje użytkownika w `data\modmgr\gamedefs\` | `gamedef` | ✅ |
| Import: `.zip`, `.7z`, folder, pojedynczy plik (`.esp`, `.pak`, `.wad`, `.pk3`, `.jar`…); rozpoznawanie po sygnaturze; odrzucanie `..`, ścieżek bezwzględnych/UNC, strumieni NTFS (`:`), nazw zarezerwowanych, linków; limity liczby plików / rozmiaru / współczynnika kompresji liczone w trakcie strumieniowania; kontrola wolnego miejsca | `archive` | ✅ (RAR – czytelny komunikat „rozpakuj i dodaj folder”) |
| Wykrywanie korzenia moda (opakowania, `Data/` na wierzchu, kilka typów w jednym archiwum), Thunderstore `manifest.json`, foldery SMAPI, ręczny wybór folderu i typu w podglądzie | `install` | ✅ (kreator FOMOD – nie; ostrzeżenie + wybór ręczny) |
| Magazyn poza folderem gry: atomowy import (`.tmp-*` → rename, sprzątanie po przerwaniu), sha256 i rozmiar każdego pliku, pliki tylko-do-odczytu, kopia archiwum w `downloads\`, wykrywanie duplikatu archiwum | `modstore` | ✅ |
| Profile (wiele na grę, kopiowanie, przełączanie = jedna transakcja „diff”), kolejność modów, reguły „ten plik wygrywa z tego moda” | `modmgr` | ✅ |
| Konflikty na poziomie pliku (bez wielkości liter), identyczne pliki oznaczone osobno, podsumowanie wygrane/przegrane per mod | `conflict` | ✅ |
| Wdrożenie: dowiązania twarde (ten sam wolumin) albo kopie; kopia oryginału przed nadpisaniem; dziennik WAL (CRC32) zapisany przed pierwszą zmianą; każda ścieżka to idempotentne przejście przed→po; odzyskiwanie przy starcie (dokończenie albo wycofanie, gdy brakuje pliku źródłowego); atomowy manifest; „Przywróć vanilla” bit w bit (także atrybut tylko-do-odczytu i daty) | `deploy` | ✅ |
| Aktualizacja gry: odcisk plików z `updates.watchFiles`, dryf (brak / zmieniony / przywrócony oryginał), nowy plik gry staje się nowym oryginałem, odinstalowanie po aktualizacji zostawia nowy plik gry | `deploy`, `modmgr` | ✅ |
| Pliki kolejności: `plugins.txt` (asterisk / active-only / textfile + `loadorder.txt` / timestamp), `Morrowind.ini` `[Game Files]` + daty pluginów, Cyberpunk `modlist.txt`, Wiedźmin 3 `mods.settings`, RimWorld `ModsConfig.xml` (z zachowaniem reszty XML), Doom – argumenty `-iwad/-file`; kodowanie Windows-1252 z odmową dla nazw, których gra nie odczyta | `loadorder` | ✅ (BG3 `modsettings.lsx`, OpenMW, REDmod deploy, Bannerlord – komunikat „ustaw kolejność w narzędziu gry”) |
| Wykrywanie: Steam (rejestr → `libraryfolders.vdf` → `appmanifest_*.acf`), dopasowanie folderu/exe z biblioteki do definicji, walidacja `requiredFiles` z możliwością wymuszenia | `detect` | ✅ (GOG/Epic/Xbox – wskazanie folderu ręcznie) |
| Bezpieczeństwo: zgoda przed włączeniem moda z kodem (DLL/ASI/skrypty), zgoda przed nadpisaniem `protectedPaths`, odmowa wdrożenia przy uruchomionej grze, blokada międzyprocesowa na instalację, nic z archiwum nie jest uruchamiane | wszystkie | ✅ |
| Integracja z launcherem: gra z biblioteki powiązana z menedżerem – niewdrożone zmiany wdrażane przed startem; „Uruchom z modami” (argumenty Dooma, `-modded` Cyberpunka); dane `mods_data` z 1.5.0 pokazywane tylko do odczytu | `app` | ✅ |

## Testy

`go test ./internal/modmgr/...` – m.in.: wdrożenie i purge dla **każdej** wbudowanej definicji na fałszywej instalacji w katalogu tymczasowym (porównanie migawek bit w bit, także Dokumenty/AppData), awaria w **każdym** kroku wdrożenia/purge/przełączenia profilu (stan zawsze „przed” albo „po”, drugie odzyskiwanie nic nie zmienia), odłączony magazyn w trakcie odzyskiwania, uszkodzony dziennik, aktualizacja gry w trakcie wdrożenia, pliki tylko-do-odczytu, ścieżki ze spacjami i polskimi znakami, złośliwe archiwa (traversal, ADS, nazwy zarezerwowane, linki, bomba ZIP), archiwum 7z, Steam VDF/ACF, fuzzing walidatora ścieżek. Testy nigdy nie dotykają prawdziwych gier ani folderów użytkownika (fałszywe korzenie z `testkit`).

## Nie zrobione (dalsze fazy projektu)

Kreator FOMOD, źródła modów (Nexus/`nxm://`, Thunderstore, Modrinth, CurseForge, GitHub), RAR, dowiązania symboliczne i cache na woluminie gry (przy magazynie na pendrivie i grze na innym dysku wdrażane są kopie), tryb `external-folder` (SMAPI `--mods-path`, Doorstop), instancje Minecrafta z loaderami, eksport/import profilu, odczyt nagłówków pluginów (mastery/ESL), BG3 `modsettings.lsx`, wykrywanie GOG/Epic/Xbox, ponowne wiązanie gry po zmianie litery **innego** dysku niż dysk launchera (ścieżki na dysku launchera są przenośne).

---

# Menedżer modów dla Game Launchera — dokument projektowy

Wersja: 1.0 (projekt, przed implementacją)
Data: 2026-11-14
Docelowa platforma: Windows 10/11, Go + WebView2 (gałąź `port/go` — **ten projekt jej nie modyfikuje**; definiuje tylko granicę integracji, zob. §1.11).

Pliki towarzyszące:

- `go/internal/modmgr/gamedef/defs/game-definition.schema.json` — JSON Schema (draft 2020-12) formatu definicji gry.
- `go/internal/modmgr/gamedef/defs/*.json` — przykładowe definicje (szablony: `generic-copy.json`, `template.bethesda.json`, `template.bepinex.json`; gry: Skyrim SE, Fallout 4, Fallout NV, Starfield, Morrowind, Valheim, Minecraft Java, Stardew Valley, RimWorld, Baldur's Gate 3, Cyberpunk 2077, Wiedźmin 3, Doom (source porty), Half-Life, GTA SA).
- Walidacja: test Go `gamedef.TestBuiltinDefinitionsLoad` (ścisłe dekodowanie każdej definicji po scaleniu `extends`).

---

## 0. Cele, nie-cele, słownik

**Cele**

1. Jeden moduł obsługujący wiele gier — od Dooma i Morrowinda po Cyberpunka i BG3 — bez pisania kodu dla każdej gry: większość wiedzy w **danych** (definicje JSON), kod Go tylko tam, gdzie format pliku kolejności ładowania lub manifestu tego wymaga (adaptery).
2. **Folder gry zawsze odwracalny do stanu vanilla.** Każda zmiana w folderze gry przechodzi przez dziennik (journal) i manifest wdrożenia; awaria prądu w połowie wdrożenia nie zostawia gry w stanie nieznanym.
3. **Przenośność**: magazyn modów, profile i profil WebView2 żyją na pendrivie; zmiana litery dysku nie psuje niczego.
4. Konflikty widoczne na poziomie pojedynczego pliku z możliwością ręcznego wyboru zwycięzcy.
5. Legalne źródła modów, zgodne z ToS i limitami API.

**Nie-cele**

- Obchodzenie DRM, patchowanie exe, downgradery, „crackowane” wersje — nie robimy tego i nie ułatwiamy.
- Uruchamianie zawartości modów podczas instalacji (skrypty C# FOMOD, instalatory .exe z archiwum).
- Własny sorter pluginów na miarę LOOT (w MVP: walidacja mastrów + opcjonalny import reguł/wyniku z LOOT, jeśli użytkownik go ma).
- Scalanie skryptów (Wiedźmin 3 Script Merger, Bashed Patch) — wykrywamy, nie scalamy.
- Logowanie do konta Microsoft dla Minecrafta — korzystamy z oficjalnego launchera lub Prism Launcher.

**Słownik**

| Termin | Znaczenie |
|---|---|
| Magazyn (store) | Rozpakowane, zainstalowane mody, poza folderem gry. |
| Pobrane (downloads) | Oryginalne archiwa (źródło prawdy do reinstalacji). |
| Instalacja gry (game install) | Konkretna kopia gry na dysku (gra + sklep + ścieżka). Jedna gra może mieć kilka instalacji. |
| Profil | Lista włączonych modów + kolejność + nadpisania konfliktów + kolejność pluginów, dla jednej instalacji gry. |
| Wdrożenie (deployment) | Umieszczenie plików modów z magazynu w folderze gry (link/kopia). |
| Purge | Usunięcie wdrożenia i przywrócenie oryginałów (stan vanilla). |
| Manifest | Trwały opis aktualnie wdrożonego stanu (co, gdzie, skąd, jakim sposobem, jaki hash). |
| Dziennik (journal) | Zapis zamiarów operacji (write-ahead log) umożliwiający dokończenie lub wycofanie przerwanego wdrożenia. |
| Typ moda (mod type) | Reguła z definicji gry: dokąd trafiają pliki danego rodzaju (np. `Data`, korzeń gry, `BepInEx/plugins`). |

---

## 1. Architektura rdzenia

### 1.1 Widok z lotu ptaka

```
WebView2 UI  ──(bridge JSON: komendy + zdarzenia)──►  modmgr.Service
                                                         │
     ┌───────────────┬───────────────┬──────────────┬────┴──────────┬───────────────┐
  gamedef         detect          sources         store/install     profile/conflict
 (JSON+schema)  (Steam/GOG/Epic/  (Nexus, TS,     (archive, FOMOD,   (kolejność,
                 Xbox/ręcznie)     Modrinth, CF,    heurystyki)        zwycięzcy)
                                   GitHub, plik)          │
                                                          ▼
                                                 deploy (planner → journal → executor)
                                                          │
                                                  loadorder writers (adaptery)
                                                          │
                                                   watch (aktualizacje gry, dryf)
```

Przepływ: **pobierz → zweryfikuj hash → zaimportuj do magazynu (bezpieczna ekstrakcja + instalator) → dodaj do profilu → zaplanuj wdrożenie (graf konfliktów) → wykonaj przez dziennik → zapisz manifest → zapisz pliki kolejności ładowania → uruchom grę**.

### 1.2 Układ pakietów Go

Moduł jako osobny pakiet w repo launchera (np. `internal/modmgr/...`), wpinany przez jeden punkt integracji. Proponowany układ:

```
internal/modmgr/
  service.go            // fasada: Service, komendy dla UI, zdarzenia
  portable/             // korzeń przenośny, rozwiązywanie ścieżek, ID woluminów
  gamedef/              // ładowanie JSON, walidacja schematu, scalanie "extends", szablony ścieżek
  detect/               // steam/ (VDF, ACF), gog/ (rejestr), epic/ (manifesty .item), xbox/, manual/
  archive/              // bezpieczna ekstrakcja: zip, 7z, rar; limity; normalizacja ścieżek
  install/              // wykrywanie korzenia, dopasowanie typów, plan instalacji
    fomod/              // parser ModuleConfig.xml, ewaluator warunków, model kroków dla UI
    pkgfmt/             // manifesty: thunderstore, mrpack, smapi, rimworld About.xml, redmod info.json, bg3 meta.lsx
  store/                // magazyn modów, metadane mod.json, indeks, hashe plików
  profile/              // profile, kolejność modów, nadpisania plików, eksport/import
  conflict/             // indeks ścieżka→dostawcy, wyliczanie zwycięzców, model UI
  deploy/
    planner.go          // stan docelowy vs manifest → lista operacji
    journal/            // WAL: zapis, fsync, odtwarzanie, rollback
    manifest/           // atomowy zapis stanu wdrożenia
    strategy/           // hardlink, symlink, copy, launchargs, externalfolder
    backup/             // kopie nadpisanych oryginałów
  loadorder/            // interfejs Writer + implementacje
    bethesda/  rimworld/  bg3/  witcher3/  cyberpunk/  doomargs/  bannerlord/
  frameworks/           // wykrywanie loaderów (BepInEx, SMAPI, SKSE...), wymagania modów
  sources/
    nexus/  thunderstore/  modrinth/  curseforge/  github/  manual/
    nxm/                // obsługa protokołu nxm://, rejestracja w HKCU (za zgodą)
    ratelimit/          // wspólne limity, cache, backoff
  watch/                // wykrywanie aktualizacji gry i dryfu plików
  adapters/             // hooki Go dla gier (bethesda, bepinex, smapi, minecraft, bg3, ...)
  testkit/              // fałszywe gry, złote pliki, wstrzykiwanie awarii
```

Zależności zewnętrzne (do weryfikacji licencji przed użyciem; wszystkie czysto w Go, bez cgo):

- `archive/zip` (stdlib) — ZIP.
- `github.com/bodgit/sevenzip` — odczyt 7z (licencja BSD-3).
- `github.com/nwaples/rardecode/v2` — odczyt RAR (BSD-2). Uwaga: niektóre wersje RAR5 z szyfrowaniem nagłówków nie są obsługiwane → czytelny błąd, nie crash.
- `github.com/santhosh-tekuri/jsonschema` — walidacja definicji gier (Apache-2.0).
- `golang.org/x/sys/windows` — `CreateHardLink`, `CreateSymbolicLink`, `MoveFileEx`, `GetVolumeInformation`, `GetFileInformationByHandle` (numer pliku/liczba linków), rejestr.
- Parser VDF/KeyValues — piszemy własny (format jest prosty; ~150 linii) — bez kopiowania cudzego kodu.

### 1.3 Kluczowe interfejsy (szkic)

```go
// Ścieżka względna wewnątrz "korzenia" (gra, magazyn, dokumenty...). Zawsze '/', znormalizowana,
// bez '..', bez dysku. Porównania case-insensitive tam, gdzie definicja gry tak mówi.
type RelPath string

type RootKind string // "game", "store", "documents", "localAppData", "instance", ...

// Lokalizacja niezależna od litery dysku.
type Location struct {
    Root RootKind
    Rel  RelPath
}

type GameDefinition struct { /* odwzorowanie schematu JSON */ }

type GameInstall struct {
    ID        string        // stabilny ULID
    GameID    string        // np. "skyrimse"
    Store     string        // steam|gog|epic|xbox|manual
    Root      VolumePath    // ścieżka gry: {VolumeSerial, PathWithoutLetter, LastSeenLetter}
    BuildID   string        // steam buildid / wersja Epic / odcisk exe
}

type Detector interface {
    Name() string
    Detect(ctx context.Context, defs []*GameDefinition) ([]GameInstall, error)
}

type ArchiveReader interface {
    Entries() ([]ArchiveEntry, error)          // tylko metadane, bez rozpakowywania
    Extract(ctx context.Context, sel func(ArchiveEntry) bool, dst SafeDir, lim Limits) error
}

type Installer interface {
    // Zwraca plan: które pliki archiwum trafiają do których typów modów i pod jakie ścieżki.
    Plan(ctx context.Context, arc ArchiveReader, def *GameDefinition, answers *FomodAnswers) (*InstallPlan, error)
}

type Store interface {
    Import(ctx context.Context, plan *InstallPlan, arc ArchiveReader, meta ModMeta) (ModID, error)
    Get(id ModID) (*Mod, error)
    Files(id ModID) ([]StoredFile, error)      // RelPath w obrębie typu + hash + rozmiar
    Remove(id ModID) error                     // tylko gdy żaden profil nie ma wdrożonego moda
    Verify(id ModID) ([]Problem, error)
}

type Strategy interface {
    Name() string                                    // hardlink|symlink|copy|launch-args|external-folder
    Supported(src, dst VolumeInfo) error             // np. hardlink wymaga tego samego woluminu NTFS
    Place(op PlaceOp) (Placed, error)                // tworzy plik/link w miejscu docelowym
    Remove(p Placed) error                           // usuwa TYLKO jeśli to nadal nasz plik
    Check(p Placed) (Drift, error)                   // czy plik w grze to nadal to, co wdrożyliśmy
}

type Deployer interface {
    Plan(ctx context.Context, inst *GameInstall, prof *Profile) (*DeployPlan, error)
    Apply(ctx context.Context, plan *DeployPlan, progress func(Progress)) error // przez journal
    Purge(ctx context.Context, inst *GameInstall) error
    Recover(ctx context.Context, inst *GameInstall) (RecoveryReport, error)      // przy starcie
}

type LoadOrderWriter interface {
    Kind() string                                          // "bethesda-plugins", "bg3-modsettings"...
    Read(ctx context.Context, env *GameEnv) (*LoadOrder, error)      // stan aktualny na dysku
    Write(ctx context.Context, env *GameEnv, lo *LoadOrder) error    // atomowo, z kopią
    Validate(env *GameEnv, lo *LoadOrder) []Problem                  // brak mastrów, limity ESL...
}

type Source interface {
    Name() string
    Resolve(ctx context.Context, ref SourceRef) (*RemoteFile, error) // URL, rozmiar, hash, nazwa
    CheckUpdates(ctx context.Context, mods []ModMeta) ([]Update, error)
}

type GameAdapter interface { // opcjonalny, dla rzeczy nie do opisania danymi
    ID() string
    ClassifyMod(m *Mod) (ModInfo, error)              // np. czytanie meta.lsx z .pak (BG3)
    PreDeploy(env *GameEnv, plan *DeployPlan) error   // np. prefiks "mod" w Wiedźminie 3
    PostDeploy(env *GameEnv) error
    LaunchArgs(env *GameEnv, prof *Profile) ([]string, error)
}
```

### 1.4 Magazyn modów (osobno od folderu gry)

Układ na dysku (wszystko względem **korzenia przenośnego** `<PR>`, zwykle `<litera USB>:\GameLauncher\`):

```
<PR>/modmgr/
  config.json                      // ustawienia modułu; brak ścieżek absolutnych z literą dysku
  gamedefs/                        // definicje użytkownika (nadpisują wbudowane, ten sam id)
  downloads/<gameId>/<plik archiwum>
  downloads/<gameId>/<plik>.meta.json   // źródło, URL strony, sha256, rozmiar, data, wersja
  store/<gameId>/<modId>/
      mod.json                     // nazwa, wersja, źródło, typy, flagi (executableContent), hash archiwum
      files/<modTypeId>/<ścieżka względna...>
      fomod-answers.json           // zapamiętane wybory instalatora (reinstalacja bez pytań)
  profiles/<installId>/<profileId>.json
  profiles/<installId>/<profileId>/overrides/   // pliki "przechwycone" (configi pisane przez mody/grę)
  state/<installId>/
      manifest.json                // aktualnie wdrożony stan
      journal/<txId>.wal           // dziennik bieżącej transakcji
      backups/<txId>/<ścieżka>     // oryginały nadpisane przez mody
      fingerprint.json             // odcisk wersji gry przy ostatnim wdrożeniu
  cache/                           // indeksy API (Thunderstore), miniatury; można skasować
  logs/
```

Zasady:

- **Identyfikator moda**: ULID (sortowalny w czasie). Ta sama wersja tego samego pliku (ten sam sha256 archiwum) importowana drugi raz → pytanie „zastąp / zainstaluj jako kopię”.
- **Pliki w magazynie są tylko do odczytu** (atrybut `FILE_ATTRIBUTE_READONLY`) — chroni przed przypadkowym zapisem przez hardlink (zob. §1.7 „Pułapka hardlinków”).
- Każdy plik ma w `mod.json` zapisany rozmiar i sha256 (liczone przy imporcie, strumieniowo). Służy do weryfikacji magazynu i wykrywania dryfu.
- **Wersje modów**: aktualizacja moda tworzy nowy `modId` powiązany polem `replaces`; stary zostaje do czasu potwierdzenia, że nowy działa (rollback = przełączenie w profilu).
- Magazyn jest per gra (`gameId`), nie per instalacja — dwie instalacje Skyrim SE (Steam i GOG) dzielą mody.
- Dla gier z `deployment.strategies = ["launch-args"]` (Doom) lub `external-folder` (SMAPI, OpenMW) magazyn jest bezpośrednio źródłem dla gry — brak plików w folderze gry.

### 1.5 Import archiwów i bezpieczna ekstrakcja

Obsługiwane: `.zip`, `.7z`, `.rar` (odczyt), a także „luźny plik” (np. `.jar`, `.pak`, `.wad`, `.pk3`, `.esp`) traktowany jak archiwum jednoelementowe. `.pk3`/`.pk7`/`.jar`/`.pak` to też zipy — ale **nie są rozpakowywane**, tylko przenoszone jako pliki (decyduje definicja gry przez `includeGlobs` / `flatten`).

Procedura importu:

1. **Weryfikacja przed ekstrakcją**: hash pobranego pliku zgodny z tym podanym przez źródło (zob. §5.5); typ rozpoznany po sygnaturze („magic bytes”), nie po rozszerzeniu.
2. **Lista wpisów bez rozpakowania** (`Entries()`), walidacja każdej ścieżki:
   - zamiana `\` → `/`, odrzucenie ścieżek absolutnych (`/x`, `C:x`, `C:/x`), UNC (`//server`), prefiksów `\\?\`;
   - odrzucenie składników `..` (po normalizacji) i pustych nazw; `.` usuwane;
   - odrzucenie `:` w nazwie (NTFS Alternate Data Streams, np. `plik.txt:zly`);
   - odrzucenie nazw zarezerwowanych Windows (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`, także z rozszerzeniem) oraz nazw kończących się kropką/spacją;
   - odrzucenie wpisów będących dowiązaniami symbolicznymi/hardlinkami (zip z atrybutami Unix, RAR „link”) — **nie tworzymy linków z archiwum**;
   - długość ścieżki docelowej: działamy z prefiksem `\\?\`, ale ostrzegamy powyżej 240 znaków (gry często nie obsługują długich ścieżek);
   - kolizje przy porównaniu case-insensitive (`Textures/a.dds` i `textures/A.dds`) → ostrzeżenie, wygrywa ostatni wpis, zapis w raporcie.
3. **Limity** (konfigurowalne, domyślne): maks. 200 000 plików; maks. łączny rozmiar po rozpakowaniu 64 GiB i nie więcej niż wolne miejsce minus 2 GiB; maks. współczynnik kompresji dla pojedynczego wpisu 1:200 (powyżej — tylko jeśli wpis < 50 MiB; chroni przed zip-bombami); zagnieżdżone archiwa nie są rozpakowywane rekurencyjnie automatycznie (chyba że mod to „archiwum w archiwum” bez innych plików — wtedy jeden poziom, z tymi samymi limitami).
4. **Ekstrakcja do katalogu tymczasowego w obrębie magazynu** (`store/<gameId>/.tmp-<ulid>/`) — ten sam wolumin, więc końcowe przeniesienie jest atomowym `rename`. Liczniki rozmiaru są sprawdzane **w trakcie** strumieniowania (deklarowany rozmiar w nagłówku archiwum może kłamać).
5. Każdy plik otwierany przez `SafeDir.Create(rel)`, który ponownie weryfikuje, że wynikowa ścieżka (po `filepath.Clean` i rozwiązaniu) leży w katalogu docelowym, i tworzy plik z `O_EXCL` (nie podąża za istniejącymi linkami).
6. Po sukcesie: hashowanie, zapis `mod.json`, atomowy `rename` katalogu `.tmp-*` → `<modId>`. Po porażce: usunięcie `.tmp-*`. Osierocone `.tmp-*` sprzątane przy starcie.

### 1.6 Heurystyki instalacji

#### Wykrywanie korzenia moda w archiwum

Typowe problemy: archiwum ma folder-opakowanie (`MojMod-1.2/Data/...`), pliki są „od Data” albo „od korzenia gry”, w archiwum jest kilka wariantów.

Algorytm (deterministyczny, testowalny):

1. Usuń z rozważań pliki z `installer.ignoreGlobs` (readme, zrzuty, `meta.ini` z MO2, `__MACOSX/`).
2. Jeśli istnieje `fomod/ModuleConfig.xml` (dowolna wielkość liter, także `fomod/` zagnieżdżony jeden poziom) i gra ma `installer.fomod = true` → instalator FOMOD (niżej).
3. Jeśli gra ma `installer.packageFormat` (thunderstore, mrpack, smapi-manifest, rimworld-about, redmod, bg3-pak) → parser formatu pakietu dostarcza strukturę (np. Thunderstore: `manifest.json` w korzeniu; SMAPI: każdy folder z `manifest.json` to osobny mod).
4. W przeciwnym razie dla każdego katalogu D w archiwum do głębokości `maxRootSearchDepth` policz wynik dla każdego typu moda T:
   - +3 za każde dziecko D pasujące do `T.rootMarkers` (np. `meshes`, `textures`, `*.esp`);
   - +5 jeśli spełnione `T.match` (np. `anyFiles: ["*.asi"]`);
   - −2 za każde dziecko niepasujące do żadnego markera (obniża „opakowania”);
   - −1 za każdy poziom głębokości (preferujemy płytsze).
5. Specjalny przypadek: jeśli D zawiera dokładnie jeden podkatalog o nazwie równej ostatniemu członowi ścieżki `T.target` (np. `Data` dla Bethesdy, `Mods` dla BG3/SMAPI, `BepInEx`) → korzeniem staje się ten podkatalog, a jego zawartość idzie do `target` („zdejmij Data/”).
6. Najlepszy wynik wygrywa, jeśli przewaga nad drugim ≥ 3 punkty; w przeciwnym razie (lub gdy wynik ≤ 0) **UI pokazuje drzewo archiwum** i pozwala wskazać korzeń i typ (jak w MO2) — wynik zapamiętany w `mod.json`, żeby aktualizacja moda nie pytała ponownie, jeśli struktura się nie zmieniła.
7. Archiwum może zawierać pliki kilku typów (np. Cyberpunk: `archive/` + `r6/` + `bin/`) — typ `root` z `rootMarkers` obejmującymi wszystkie te foldery wygrywa i całość idzie od korzenia gry.

Wynik to `InstallPlan`: lista `(źródło w archiwum) → (modTypeId, RelPath)`, plus wykryte cechy: `executableContent`, wymagane frameworki (`modRequiresIf`), manifesty i zależności.

#### Instalator FOMOD (tylko XML)

FOMOD to de facto standard dla modów Bethesdy, Cyberpunka, Wiedźmina i innych z Nexusa: `fomod/info.xml` (metadane) i `fomod/ModuleConfig.xml` (logika instalacji). Implementujemy **wyłącznie wariant XML**; instalatory skryptowe (C#, `script.cs`) nie są nigdy wykonywane — UI proponuje instalację ręczną (wybór folderów w drzewie archiwum).

Elementy, które obsługujemy (na podstawie publicznego schematu ModuleConfig.xsd):

- `moduleName`, `moduleImage`;
- `moduleDependencies` — warunki wstępne całej instalacji (`fileDependency` ze stanem `Active`/`Inactive`/`Missing`, `flagDependency`, `gameDependency` — wersja gry, `fommDependency` — wersja menedżera, traktowana jako spełniona; operatory `And`/`Or`, zagnieżdżanie);
- `requiredInstallFiles` — `file`/`folder` z `source`, `destination`, `priority`, `alwaysInstall`, `installIfUsable`;
- `installSteps` (kolejność `Explicit`/`Ascending`/`Descending`) → `installStep` z opcjonalnym `visible` (warunek) → `optionalFileGroups` → `group` z typem `SelectExactlyOne`, `SelectAtMostOne`, `SelectAtLeastOne`, `SelectAll`, `SelectAny` → `plugin` (`description`, `image`, `files`, `conditionFlags`, `typeDescriptor`: `type` albo `dependencyType` z `defaultType` i `patterns`; typy: `Required`, `Optional`, `Recommended`, `NotUsable`, `CouldBeUsable`);
- `conditionalFileInstalls` → `patterns` → `pattern` (`dependencies` + `files`) — wyliczane na końcu na podstawie flag i stanu plików.

Projekt:

- `fomod.Parse(xml) (*Module, error)` — parser odporny na typowe błędy autorów: BOM UTF-16/UTF-8, wielkość liter w ścieżkach, `\` w ścieżkach, puste `destination` (= ścieżka źródłowa względnie do korzenia), brak `order`.
- `fomod.Session` — maszyna stanów: aktualny krok, wybory, flagi; metoda `Next()`/`Back()` przelicza widoczność kroków. Stan jest serializowalny (`fomod-answers.json`) — reinstalacja/aktualizacja może odtworzyć wybory (z potwierdzeniem, jeśli zmieniła się struktura XML).
- `fileDependency` sprawdzamy względem **stanu profilu** (czy plugin jest w profilu i włączony), nie tylko obecności pliku w grze.
- Model dla UI: lista kroków → grupy → opcje (nazwa, opis, obrazek jako ścieżka w archiwum wyciągana do cache, typ, stan zaznaczenia, zablokowanie). UI nie zawiera logiki — wysyła tylko wybory.
- Rozwiązanie końcowe: lista `(source, destination, priority)`; konflikty wewnątrz instalatora rozstrzyga `priority`, potem kolejność w XML.
- Ścieżki `source`/`destination` przechodzą tę samą walidację co wpisy archiwum (żadnego `..`).

### 1.7 Strategie wdrożenia

| Strategia | Kiedy | Plusy | Minusy |
|---|---|---|---|
| **hardlink** | magazyn (lub jego cache) na tym samym woluminie NTFS co docelowy folder | brak dodatkowego miejsca, natychmiastowe, gra widzi zwykłe pliki, działa bez uprawnień admina | wymaga tego samego woluminu; współdzielone metadane (mtime); ryzyko zapisu „przez link” |
| **symlink** | inny wolumin, NTFS po stronie gry, uprawnienie do symlinków (Tryb dewelopera lub admin) | brak duplikacji | niektóre gry/antycheaty nie lubią linków; zależne od litery dysku magazynu |
| **copy** | zawsze (fallback), FAT32/exFAT, USB, gdy gra odrzuca linki | maksymalna zgodność | zajmuje miejsce, wolniejsze; wymaga kopii oryginałów |
| **launch-args** | Doom i podobne | zero plików w grze | tylko gry, które przyjmują pliki w argumentach |
| **external-folder** | SMAPI `--mods-path`, OpenMW `data=`, BepInEx przez Doorstop (opcja), RimWorld `-savedatafolder` (dla configu) | zero lub minimum plików w grze, profile przełączane natychmiast | zależne od wsparcia loadera |

Wybór strategii per instalacja: idziemy po `deployment.strategies` z definicji (lub `modType.deployStrategy`) i bierzemy pierwszą, dla której `Strategy.Supported(src, dst)` nie zwraca błędu. Użytkownik może wymusić strategię w ustawieniach instalacji.

**Cache na woluminie gry (staging)**: jeśli magazyn jest na USB, a gra na `C:`, hardlink jest niemożliwy. Gdy `preferStagingOnGameVolume = true` i jest miejsce, tworzymy `<wolumin gry>:\.gl-modcache\<installId>\` z kopią plików wdrażanych modów (deduplikacja po sha256), a do gry wdrażamy hardlinki z cache. Zalety: kolejne przełączenia profili są natychmiastowe; odłączenie pendrive’a nie psuje zainstalowanej gry. Cache jest odtwarzalny z magazynu i może być skasowany w dowolnej chwili (po purge).

**Pułapka hardlinków**: hardlink to ten sam plik — jeśli gra, narzędzie moda lub aktualizacja sklepu **zapisze do pliku w miejscu** (zamiast zastąpić go nowym), zmieni się też kopia w magazynie. Środki zaradcze:

1. pliki magazynu/cache mają atrybut tylko do odczytu (zapis w miejscu się nie uda; zastąpienie nowym plikiem — tak, co tylko rozłącza link);
2. manifest trzyma sha256; `watch` i purge porównują hash, a przy niezgodności magazyn jest „naprawiany” z archiwum w `downloads/` (dlatego oryginały archiwów domyślnie zostają);
3. pliki, o których wiadomo, że są modyfikowane w czasie gry (configi modów: `BepInEx/config/*.cfg`, SMAPI `config.json`, `*.ini`), definicja gry może oznaczyć jako **copy-only** — wtedy zmiany są po purge przechwytywane do `profiles/.../overrides/` (mechanizm podobny do folderu „Overwrite” w MO2).

**Gry z kolejnością po datach modyfikacji** (Morrowind, Oblivion, FO3, FNV, Skyrim LE dla starszych narzędzi): pluginy `.esp/.esm` wdrażamy jako **kopie** (nie hardlinki), żeby ustawianie mtime nie wpływało na magazyn współdzielony przez profile; reszta plików może być hardlinkiem.

### 1.8 Manifest, dziennik, purge i rollback (odporność na awarie)

#### Manifest wdrożenia (`state/<installId>/manifest.json`)

```json
{
  "formatVersion": 1,
  "installId": "01J...",
  "profileId": "01J...",
  "txId": "01J...",                       // transakcja, która wytworzyła ten stan
  "gameFingerprint": { "steamBuildId": "15012345", "exeSha256": "..." },
  "strategy": "hardlink",
  "entries": [
    {
      "target": { "root": "game", "rel": "Data/textures/x.dds" },
      "source": { "modId": "01J...", "modType": "data", "rel": "textures/x.dds" },
      "kind": "hardlink",
      "sha256": "…", "size": 123, "fileId": "volSerial:fileIndex",
      "backup": { "rel": "backups/01J.../Data/textures/x.dds", "sha256": "…" }   // tylko gdy nadpisano oryginał gry
    }
  ],
  "createdDirs": [ { "root": "game", "rel": "Data/textures" } ],
  "loadOrderFiles": [ { "root": "localAppData", "rel": "Skyrim Special Edition/plugins.txt", "backup": "…", "sha256": "…" } ]
}
```

- Ścieżki są **zawsze względne do nazwanego korzenia** — nigdy z literą dysku (przenośność).
- `fileId` (numer pliku NTFS z `GetFileInformationByHandle`) pozwala tanio sprawdzić, czy hardlink nadal wskazuje na nasz plik.
- Zapis atomowy: `manifest.json.tmp` → `FlushFileBuffers` → `MoveFileEx(MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)`; poprzednia wersja trzymana jako `manifest.prev.json`.

#### Dziennik (write-ahead log)

Każde wdrożenie/purge to **transakcja**: `txId` (ULID), plik `journal/<txId>.wal` w formacie JSON Lines, każda linia z sumą kontrolną CRC32 (wykrywa urwaną ostatnią linię).

Kolejność rekordów:

```
BEGIN {txId, kind: deploy|purge|redeploy, fromManifestTx, targetProfile, planHash}
PLAN  {n, ops: [...]}                     // pełny plan zapisany zanim cokolwiek dotkniemy
-- dla każdej operacji i:
INTENT {i, op: backup|place|remove|restore|mkdir|rmdir|writeLO, target, src, expectSha}
DONE   {i, observed: {sha256|fileId}}
-- na końcu:
COMMIT {newManifestSha}
```

Zasady:

1. `PLAN` jest zapisywany i `fsync`-owany przed pierwszą zmianą w grze.
2. Każda operacja jest **idempotentna** i **sprawdzalna** — przed jej wykonaniem patrzymy na stan faktyczny: np. `place` jest „już wykonane”, jeśli plik docelowy ma oczekiwany `fileId`/hash; `backup` jest wykonane, jeśli kopia istnieje z właściwym hashem.
3. Kolejność bezpieczna: **najpierw kopia oryginału (backup + fsync), potem usunięcie/nadpisanie**. Oryginał gry nigdy nie jest usuwany, zanim jego kopia nie jest trwała.
4. Nowy plik umieszczamy jako `cel.gl-new` (ten sam katalog) i dopiero potem `MoveFileEx` na miejsce — w każdym momencie w miejscu docelowym jest albo stary, albo nowy plik.
5. Zapis `DONE` jest buforowany i `fsync`-owany co N operacji (np. 256) lub co 250 ms — po awarii co najwyżej N operacji jest „ponownie sprawdzanych” (idempotencja to umożliwia).
6. `COMMIT` następuje po atomowym zapisie nowego manifestu. Po `COMMIT` plik WAL jest archiwizowany (ostatnie 5 trzymamy w `logs/` do diagnostyki), kopie zapasowe nieużywane przez nowy manifest — usuwane.

**Odzyskiwanie przy starcie** (`Deployer.Recover`):

- brak niezakończonego WAL → nic;
- WAL bez `PLAN` → nic nie zmieniono, usuń WAL;
- WAL z `PLAN`, bez `COMMIT` → domyślnie **dokończ do przodu** (roll-forward): przejdź plan od początku, każdą operację sprawdź i wykonaj tylko brakujące; jeśli roll-forward jest niemożliwy (np. brak pliku źródłowego — odłączony USB) → **roll-back**: wykonaj operacje odwrotne do tych z `DONE` w odwrotnej kolejności (usuń nasze pliki, przywróć kopie), wróć do manifestu `fromManifestTx`. Użytkownik dostaje raport i wybór, jeśli obie drogi są możliwe, a gra jest uruchomiona/ma otwarte pliki.

**Purge (powrót do vanilla)** = transakcja z planem: dla każdego wpisu manifestu `remove` (tylko jeśli plik nadal jest nasz: ten sam `fileId` lub hash; jeśli nie — patrz §1.10 dryf) → `restore` kopii → `rmdir` katalogów z `createdDirs`, jeśli puste → przywrócenie plików kolejności ładowania. Po purge folder gry jest bitowo zgodny ze stanem sprzed pierwszego wdrożenia (z wyjątkiem plików zmienionych w międzyczasie przez grę/sklep — raportowane).

**Redeploy / przełączenie profilu** to jedna transakcja „diff”: planner porównuje stan docelowy z manifestem i generuje minimalny zestaw operacji (pliki niezmienione nie są dotykane).

Dodatkowo:

- Przed transakcją: sprawdzenie, czy gra nie działa (lista procesów z exe z definicji) — jeśli działa, odmowa.
- Blokada na instalację (`state/<installId>/lock`, `LockFileEx`) — jedna transakcja naraz, także między instancjami launchera.
- **Ostatnia deska ratunku**: przycisk „Przywróć vanilla na podstawie manifestu” działający nawet bez magazynu (np. zgubiony pendrive) — usuwa pliki o hashach z manifestu i przywraca kopie, jeśli `state/` jest dostępne. Dlatego kopie zapasowe oryginałów trzymamy **na woluminie gry** w cache (`.gl-modcache/<installId>/backups`), a w `<PR>/state` tylko ich manifest — odłączenie USB nie odbiera możliwości przywrócenia gry. Kopia manifestu też ląduje w cache gry.

### 1.9 Profile, kolejność, konflikty i model UI

**Profil** (`profiles/<installId>/<profileId>.json`):

```json
{
  "id": "01J...", "name": "Survival 2026", "installId": "01J...",
  "mods": [ { "modId": "01J...", "enabled": true }, … ],          // kolejność = priorytet (później = wygrywa)
  "fileOverrides": { "data:textures/sky/clouds.dds": "01J...modB" }, // per-plik zwycięzca
  "pluginOrder": [ { "name": "Unofficial Skyrim Special Edition Patch.esp", "enabled": true }, … ],
  "launch": { "executable": "skse", "extraArgs": [] },
  "localSaves": false, "localIni": false
}
```

- Dwie osobne kolejności: **kolejność modów** (rozstrzyga konflikty plików, jak lewy panel MO2) i **kolejność pluginów/load order gry** (to, co trafia do `plugins.txt`, `modsettings.lsx` itp.). Dla gier, gdzie to jedno i to samo (Cyberpunk `modlist.txt`, Doom `-file`), UI pokazuje jedną listę.
- Opcjonalne „lokalne zapisy/INI” per profil (jak w MO2): zapisy przenoszone przez folder profilu tylko tam, gdzie gra ma do tego mechanizm (RimWorld `-savedatafolder`, SMAPI); dla Bethesdy — podmiana `[General] SLocalSavePath` w INI z kopią, za zgodą. W MVP: wyłączone.
- Eksport profilu: JSON z listą modów (źródło + id + wersja + hash), kolejnością i nadpisaniami → import u kolegi pobiera brakujące mody z tych samych źródeł (ważne dla gier sieciowych z BepInEx; format „kodu profilu” jak w r2modman, ale własny).

**Indeks konfliktów** (`conflict.Index`): mapa `klucz → []dostawca`, gdzie klucz = `targetRoot + ":" + lower(RelPath)` po rozwiązaniu typu moda do folderu docelowego (dwa mody z różnych typów, które trafiają w to samo miejsce, też się zderzają). Budowana przyrostowo (zmiana jednego moda → aktualizacja jego kluczy). Dla 500 modów × 50 000 plików to kilkadziesiąt MB w pamięci — akceptowalne; klucze internujemy.

Wyznaczanie zwycięzcy dla klucza: (1) jeśli jest `fileOverrides[klucz]` i ten mod jest włączony → on; (2) w przeciwnym razie ostatni włączony mod w kolejności profilu; (3) pliki oryginalne gry są „dostawcą 0” (przegrywają zawsze, ale są zapisywane w backupie).

Konflikty **wewnątrz archiwów** (`.bsa/.ba2`, `.archive`, `.pak`) nie są widoczne na poziomie plików — w MVP traktujemy archiwum jako jeden plik; w fazie 3 adapter może listować zawartość archiwów (tylko nagłówki), by pokazać „konflikty miękkie” (informacyjne).

**Konflikty identyczne** (ten sam sha256) oznaczamy jako „brak realnego konfliktu” — szare.

**Model UI** (dane wysyłane do WebView; UI renderuje):

```ts
ModRow {
  modId, name, version, enabled, priority,
  conflictSummary: { wins: number, loses: number, identical: number, overriddenByRule: number },
  badges: ["executable", "needs:SKSE64", "update-available", "missing-master"]
}
ConflictDetail(modId) → [
  { path: "Data/textures/sky/clouds.dds", winner: modId, providers: [{modId, name, sha256, size}],
    rule: "priority" | "override", identical: false }
]
```

- Lista modów: kolumna „Konflikty” z ikoną: błyskawica zielona (wygrywa wszystko), czerwona (przegrywa coś), mieszana; najechanie podświetla mody, z którymi koliduje (jak w MO2).
- Zakładka „Pliki” moda: drzewo plików z kolorami (wygrany/przegrany/identyczny/nadpisany regułą); prawy klik na plik → „Niech wygrywa ten mod” → wpis w `fileOverrides`; widoczny znaczek przy plikach z ręczną regułą i przycisk „wyczyść reguły”.
- Widok „Konflikty” dla całego profilu: tabela ścieżek z >1 dostawcą, filtrowanie po modzie, folderze, typie pliku.
- Każda zmiana kolejności/reguł oznacza profil jako „niezsynchronizowany z grą” — przycisk „Wdróż” (lub automatyczne wdrożenie przy uruchomieniu gry, opcja domyślnie włączona).

### 1.10 Gra aktualizuje własne pliki — wykrywanie i ponowne wdrożenie

Źródła sygnału:

1. **Steam**: `appmanifest_<appid>.acf` → `buildid`, `StateFlags` (4 = w pełni zainstalowana; inne bity = aktualizacja w toku), `LastUpdated`. Porównanie z `gameFingerprint` w manifeście.
2. **Epic**: manifest `.item` → `AppVersionString`.
3. **GOG / ręczne / Xbox**: odcisk z `updates.watchFiles` (rozmiar + mtime + sha256 exe).
4. **Dryf plików** (niezależny od sklepu): przy starcie launchera, przed uruchomieniem gry i opcjonalnie przez `ReadDirectoryChangesW` na folderach docelowych — dla wpisów manifestu sprawdzamy `fileId`/rozmiar/mtime (szybko), a przy niezgodności — sha256.

Klasyfikacja dryfu dla wpisu manifestu:

| Stan | Znaczenie | Reakcja |
|---|---|---|
| plik nasz (fileId/hash zgodny) | OK | — |
| plik zastąpiony nowym, hash ≠ nasz i ≠ backup | sklep zaktualizował/naprawił plik gry (lub inny program) | nowa wersja staje się **nowym oryginałem**: przenosimy ją do backup (zastępując stary backup), wdrażamy ponownie nasz plik |
| plik usunięty | „weryfikacja plików” w Steam lub ręczne usunięcie | wdrożenie ponowne |
| plik nasz, ale hash magazynu też się zmienił | zapis przez hardlink | naprawa magazynu z archiwum, ostrzeżenie |
| nowe pliki gry w miejscach, gdzie mamy backup | patch dodał plik, który mod nadpisywał | jak wyżej — nowy oryginał |

Przepływ po wykryciu aktualizacji gry (`updates.onUpdate`):

- `verify-and-redeploy` (domyślne): pełna weryfikacja dryfu → transakcja „redeploy” odświeżająca backupy i przywracająca mody; plus sprawdzenie frameworków z `gameVersionLocked` (SKSE/F4SE/SFSE/CET/RED4ext/ScriptHookV) — jeśli wersja exe nie pasuje do wersji frameworka (mapowanie wersji zapisane w adapterze/definicji lub odczytane z zasobów DLL), profil jest oznaczony „może nie działać” i domyślnie proponujemy uruchomienie vanilla.
- `purge-and-warn`: dla gier, gdzie mody po aktualizacji często psują start.
- `warn`: tylko informacja.

Ważne: **nie uruchamiamy wdrożenia, gdy `StateFlags` wskazuje aktualizację w toku** — czekamy, aż sklep skończy. Dodatkowo podpowiedź w UI: „Steam → Właściwości → Aktualizacje: tylko przy uruchamianiu” (nie zmieniamy ustawień Steam za użytkownika).

### 1.11 Przenośność (USB, zmiana litery dysku)

Założenia: launcher działa z pendrive’a, korzeń przenośny `<PR>` = folder obok `GameLauncher.exe`. Profil WebView2 ustawiany przez launcher (`userDataFolder` w opcjach środowiska WebView2) na `<PR>/webview/` — to po stronie launchera na gałęzi `port/go`; moduł modów tylko oczekuje, że dostanie `<PR>` w konstruktorze.

Rozwiązanie:

1. **Brak liter dysku w danych trwałych.** Każda ścieżka jest `Location{Root, Rel}`. Korzenie rozwiązywane w czasie działania:
   - `store`, `downloads`, `profiles`, `state` → względem `<PR>` (litera z bieżącej ścieżki exe);
   - `game` → `VolumePath{VolumeSerial, VolumeGUID, PathWithoutLetter, LastSeenLetter}` instalacji gry; przy starcie: jeśli `LastSeenLetter:\Path` istnieje i ma ten sam numer seryjny woluminu → OK; w przeciwnym razie szukamy woluminu o tym numerze seryjnym (`GetLogicalDrives` + `GetVolumeInformation`) i aktualizujemy literę; na końcu — ponowna detekcja przez Steam/GOG/Epic (gra mogła zostać przeniesiona);
   - `documents`, `localAppData`, `localLow`, `appData`, `savedGames` → `SHGetKnownFolderPath` na bieżącym komputerze (inny komputer = inne konto, nadal działa).
2. **Hardlinki** nie zależą od litery dysku magazynu (wskazują na dane pliku, nie na ścieżkę) — dlatego cache na woluminie gry (§1.7) jest preferowany. Wdrożenie przeżywa zmianę litery USB i nawet odłączenie USB.
3. **Symlinki** zawierają ścieżkę absolutną celu. Gdy cel jest na USB, a litera się zmieniła — linki są „zerwane”. Przy starcie `watch` wykrywa to (cel linku ≠ bieżąca lokalizacja magazynu) i wykonuje transakcję „relink” (tylko wpisy typu symlink). Symlinki **względne** są możliwe tylko w obrębie jednego woluminu, więc dla USB nie pomagają.
4. **Kopie** są niezależne od litery.
5. **Inny komputer**: instalacja gry ma `machineId` (z `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`, tylko lokalnie, nie wysyłamy nigdzie). Profile i magazyn wspólne; manifesty per instalacja per maszyna. Na nowym komputerze gra jest wykrywana od nowa, a profil można wdrożyć jednym kliknięciem.
6. **System plików pendrive’a**: FAT32 (limit 4 GiB na plik, brak linków), exFAT (brak linków, brak ACL). Moduł wykrywa FS (`GetVolumeInformation` → nazwa FS) i: ostrzega przy FAT32 (niektóre mody > 4 GiB), nie proponuje hardlinków/symlinków z USB, zaleca cache na woluminie gry. Hardlinki **w obrębie** USB (gra zainstalowana na USB NTFS) działają normalnie.
7. Rejestracja protokołu `nxm://` (§4.1) zawiera ścieżkę exe — przy zmianie litery dysku launcher proponuje ponowną rejestrację (za zgodą, tylko w `HKCU`).

---

## 2. Format definicji gry (JSON)

Pełny schemat: `go/internal/modmgr/gamedef/defs/game-definition.schema.json`. Poniżej semantyka pól i decyzje projektowe.

### 2.1 Zasady ogólne

- Definicje są **danymi** — wbudowane w exe (`embed`) + nadpisywalne przez `<PR>/modmgr/gamedefs/` (ten sam `id`) + aktualizowalne z repozytorium projektu (podpisane; faza późniejsza).
- `extends` + `abstract` — szablony (Bethesda, BepInEx, ogólny). Scalanie: obiekty głęboko, tablice zastępowane w całości (przewidywalne).
- `adapter` — nazwa adaptera Go z hookami, gdy dane nie wystarczają. Gra bez adaptera działa na samych danych.
- Ścieżki to szablony ze zmiennymi: `{game}`, `{documents}`, `{myGames}` (= `{documents}/My Games`), `{localAppData}`, `{appData}`, `{localLow}`, `{userProfile}`, `{savedGames}`, `{steamRoot}`, `{instance}`, `{profileDir}`, `{modsStaging}`, `{paths.<nazwa>}`, a w szablonach podfolderów `{mod.folderName}`, `{mod.namespace}`, `{mod.name}`, `{mod.id}`. Po rozwiązaniu ścieżka musi leżeć w jednym z dozwolonych korzeni — definicja nie może kazać pisać do `C:\Windows`.
- `storeOverrides` — różnice między wersjami sklepowymi (np. Skyrim SE z GOG używa folderu „Skyrim Special Edition GOG” w Dokumentach i AppData).

### 2.2 Wykrywanie (`detection`)

**Steam**

1. Ścieżka Steam: `HKCU\Software\Valve\Steam\SteamPath` (fallback `HKLM\SOFTWARE\WOW6432Node\Valve\Steam\InstallPath`).
2. `<Steam>/steamapps/libraryfolders.vdf` — format KeyValues (tekstowy): obiekt `libraryfolders` z kluczami `"0"`, `"1"`… zawierającymi `path` i `apps` (mapa appid → rozmiar). Parser VDF: tokeny w cudzysłowach, `{` `}`, komentarze `//`, sekwencje ucieczki `\\` i `\"`.
3. Dla każdej biblioteki: `steamapps/appmanifest_<appid>.acf` (również KeyValues) → `AppState.installdir`, `StateFlags`, `buildid`, `LastUpdated`. Gra: `<biblioteka>/steamapps/common/<installdir>`.
4. Walidacja `requiredFiles` / `anyOfFiles`.
5. Warsztat Steam: `<biblioteka>/steamapps/workshop/content/<appid>/<itemId>/` — tylko odczyt (RimWorld, Source). Nigdy nie modyfikujemy.
6. Uruchamianie: `steam://rungameid/<appid>` lub `steam.exe -applaunch <appid> <args>` (ten drugi przekazuje argumenty bez okna potwierdzenia — potrzebne dla REDmod `-modded`, BepInEx Doorstop).

**GOG**: `HKLM\SOFTWARE\WOW6432Node\GOG.com\Games\<gameId>` → wartości `path`, `exe`, `gameName`, `ver`. GOG Galaxy dodatkowo ma bazę SQLite — nie jest potrzebna. Uruchamianie bezpośrednie exe (bez DRM).

**Epic**: `C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\*.item` (JSON) → `InstallLocation`, `AppName`, `CatalogNamespace`, `AppVersionString`, `LaunchExecutable`. Ścieżkę `ProgramData` bierzemy z `FOLDERID_ProgramData`; lokalizację katalogu Manifests można potwierdzić w `HKLM\SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher\AppDataPath`. Uruchamianie: `com.epicgames.launcher://apps/<AppName>?action=launch&silent=true` (gry z DRM Epic) — argumenty dodatkowe trzeba przekazać przez ustawienia launchera Epic; dlatego dla Epic preferujemy gry bez wymaganego `-modded` lub informujemy użytkownika.

**Xbox / Microsoft Store**: gry w `C:\Program Files\WindowsApps` są chronione ACL i często zaszyfrowane — **nie wspieramy** wdrażania tam. Nowsze tytuły (Starfield, Skyrim SE z Game Pass, Fallout 4, Valheim) instalowane przez aplikację Xbox z włączonymi „zaawansowanymi opcjami zarządzania” lądują w `<dysk>:\XboxGames\<Gra>\Content\` z normalnymi uprawnieniami — tu działa (pole `xbox.moddable = "content-folder"`). Wykrywanie: pliki `<dysk>:\.GamingRoot` (wskazują folder bibliotek Xbox na danym dysku) + skanowanie `XboxGames\*\Content` pod `requiredFiles`; nazwa paczki (`packageFamilyNames`) dla dokładności. Ograniczenia do pokazania w UI: brak gwarancji dla Script Extenderów (często osobne wersje), inne ścieżki w Dokumentach (np. „Skyrim Special Edition MS”), uruchamianie przez `shell:AppsFolder\<AUMID>`.

**Rejestr**: dla klasyków z instalatorem retail/GOG (`detection.registry`, z wyborem widoku 32/64).

**Ręcznie**: użytkownik wskazuje folder lub exe (`rootFromExe` pozwala wskazać `bin/x64/Cyberpunk2077.exe`). Zawsze walidacja `requiredFiles`; dopuszczamy „wymuszenie” z ostrzeżeniem.

### 2.3 Foldery modów i reguły układu (`modTypes`)

Każdy typ: `id`, `target` (szablon), `priority` (kolejność dopasowania), `default`, `match` (kryteria), `rootMarkers` (dla heurystyki korzenia), `perModSubfolder` (mody w osobnych folderach: SMAPI, RimWorld, Wiedźmin 3, Thunderstore), `flatten` (tylko pasujące pliki do jednego folderu: `.pak`, `.jar`, `.archive`), `include/excludeGlobs`, `executableContent` (wymusza ostrzeżenie), `deployStrategy`.

Ogólna reguła: mod może zawierać pliki kilku typów; instalator przypisuje każdy plik do typu, a deploy wylicza ścieżkę docelową `resolve(target) / [perModSubfolder] / rel`.

`deployment.protectedPaths` — pliki gry, których nadpisanie wymaga dodatkowego potwierdzenia (exe, `gta3.img`, `valve/**`).

### 2.4 Pliki pluginów/kolejności (`loadOrder`)

`kind` wybiera implementację `LoadOrderWriter`; reszta pól to parametry. Wspólne zasady dla wszystkich writerów:

1. `Read` przed `Write` — jeśli plik zmienił się od naszego ostatniego zapisu (hash w manifeście ≠ hash na dysku) i `readExternalChanges = true`, UI pyta: „Gra/inne narzędzie zmieniło kolejność — zaimportować?”.
2. Zapis atomowy (tmp + `MoveFileEx`), kopia poprzedniej wersji w backupie transakcji, zachowanie kodowania i końców linii (`\r\n`) oryginału.
3. Plik kolejności jest częścią manifestu — purge przywraca oryginał.

Implementacje: `bethesda-plugins` (formaty `active-only`, `asterisk`, `textfile`, `timestamp`, `ini-gamefile`), `openmw-cfg`, `rimworld-modsconfig`, `bg3-modsettings`, `witcher3-mods-settings`, `cyberpunk-modlist`, `redmod-deploy`, `launch-args`, `dependency-sorted` (tylko walidacja), `bannerlord-launcher-data`, `deploy-priority` (brak pliku).

### 2.5 Wymagane frameworki/loadery (`frameworks`)

Każdy: `detect` (pliki świadczące o instalacji), `modRequiresIf` (kiedy mod go wymaga — np. pliki `SKSE/Plugins/*.dll`, zależność w manifeście), `install`:

- `as-mod` — framework to zwykły mod w magazynie (BepInExPack, SKSE, CET, RED4ext, ASI Loader). Zaleta: purge usuwa go razem z resztą.
- `external-installer` — oficjalny instalator uruchamia **użytkownik** (SMAPI, Forge/NeoForge). Moduł tylko wykrywa i prowadzi.
- `instance-loader` — dla Minecrafta: profil wersji loadera (Fabric/Quilt) pobierany z ich meta-API jako JSON.
- `manual` — instaluje sklep (np. REDmod jako DLC).

`gameVersionLocked` — framework przypięty do wersji exe (SKSE, F4SE, SFSE, CET, RED4ext, ScriptHook V): po aktualizacji gry → ostrzeżenie. `launchVia` — przez który executable uruchamiać.

Walidacja profilu przed uruchomieniem: każdy włączony mod z wymaganiem frameworka → framework wykryty? Jeśli nie: czerwony znaczek i link do źródła z `framework.source`.

### 2.6 Argumenty uruchomienia (`executables`, `launch`)

- `executables[]` — warianty uruchomienia (gra, loader, narzędzie), `args` ze zmiennymi, `default`.
- `launch.preferStoreLaunch` — uruchamianie przez klienta sklepu (Steam overlay/DRM).
- `launch.moddedArgs` — dodawane, gdy profil ma mody (REDmod `-modded`).
- `launch.steamLaunchOptionsHint` — tekst do skopiowania (np. SMAPI `"…\StardewModdingAPI.exe" %command%`) — **nie edytujemy** `localconfig.vdf` Steama.
- `loadOrder.argTemplate` — dla gier „launch-args” (Doom): `["-iwad","{iwad}","-file","{files:*.wad,*.pk3...}"]`. Argumenty zawsze przekazujemy jako tablicę (`exec.Command` z osobnymi argumentami, poprawne cytowanie Windows), nigdy przez powłokę.

---

## 3. Adaptery i definicje do wydania w pierwszej kolejności

Kolejność wg pokrycia: ogólny → BepInEx/Thunderstore → Minecraft → Bethesda → reszta. Dla każdej gry: układ folderów, mechanizm kolejności, loadery, pułapki.

### 3.1 Ogólny „kopiuj do folderu” (`generic-copy.json`)

- **Układ**: jeden typ `files` → `{paths.modsTarget}` (domyślnie korzeń gry; użytkownik może wskazać podfolder, np. `Mods`, `Data`, `addons`).
- **Kolejność**: `deploy-priority` — kolejność modów rozstrzyga tylko konflikty plików.
- **Loadery**: brak wiedzy; każdy DLL/ASI/EXE w archiwum → ostrzeżenie.
- **Pułapki**: brak walidacji zgodności; heurystyka korzenia słabsza (domyślnie głębokość 2, często pytamy użytkownika). Mimo to pełna wartość: magazyn, profile, konflikty, journal, purge.

### 3.2 BepInEx / Thunderstore (`template.bepinex.json`, `valheim.json`)

- **Układ**: `winhttp.dll` + `doorstop_config.ini` + `.doorstop_version` w korzeniu gry; `BepInEx/core` (sam loader), `BepInEx/plugins/<Namespace-Name>/` (pluginy), `BepInEx/patchers/<Namespace-Name>/` (preloader), `BepInEx/config/` (wspólne `.cfg`). Pakiet Thunderstore: `manifest.json` (`name`, `version_number`, `website_url`, `description`, `dependencies: ["Namespace-Name-1.2.3"]`), `icon.png`, `README.md`, opcjonalnie `CHANGELOG.md`, foldery `plugins/`, `patchers/`, `config/` albo luźne `.dll`. Pakiety `BepInExPack_<Gra>` zawierają loader w podfolderze — zdejmujemy go.
- **Kolejność**: brak pliku kolejności — BepInEx sortuje wg atrybutów zależności pluginów (`BepInDependency`). My: rozwiązywanie zależności Thunderstore (graf, instalacja brakujących, wykrywanie cykli i konfliktów wersji; zasada: najwyższa wymagana wersja).
- **Loadery**: BepInEx 5 (Mono) albo BepInEx 6/IL2CPP dla gier IL2CPP (rozpoznanie: `GameAssembly.dll` + `<Gra>_Data/il2cpp_data` → IL2CPP; `<Gra>_Data/Managed/Assembly-CSharp.dll` → Mono). Pakiet zawsze z Thunderstore danej społeczności (wersja dopasowana przez społeczność).
- **Tryb wdrożenia „external-folder” (opcjonalny, faza 2)**: Doorstop pozwala wskazać docelowy assembly argumentami uruchomienia (Doorstop 3: `--doorstop-enable true --doorstop-target <ścieżka>`; Doorstop 4: `--doorstop-enabled true --doorstop-target-assembly <ścieżka>` — nazwy różnią się między wersjami, wybór po `.doorstop_version`). Wtedy w grze leży tylko `winhttp.dll` + `doorstop_config.ini`, a cały `BepInEx/` z pluginami siedzi w folderze profilu — przełączenie profilu bez wdrażania. Wymaga uruchamiania przez `steam.exe -applaunch`, bo gry ze Steam API przy bezpośrednim starcie często restartują się przez Steam i gubią argumenty.
- **Pułapki**: konfiguracje `.cfg` są przepisywane przez grę → wdrażane jako kopie i przechwytywane do nakładki profilu; gry sieciowe wymagają identycznych modów u wszystkich (eksport profilu); Proton/Wine wymaga override `winhttp` (poza zakresem Windows MVP); część pakietów wkłada pliki w niestandardowe miejsca (np. `BepInEx/` w korzeniu pakietu) — obsługiwane przez typ `bepinex-pack`/`root`.

### 3.3 Minecraft Java (`minecraft-java.json`)

- **Model**: grą jest **instancja** w magazynie: `<PR>/modmgr/instances/<id>/` z `instance.json` (wersja MC, loader + wersja, wymagana Java) i folderami `mods/`, `resourcepacks/`, `shaderpacks/`, `config/`. Profil = instancja.
- **Kolejność**: brak — loader sortuje sam. Walidacja: zgodność wersji MC/loadera, zależności (z Modrinth `dependencies` lub z `fabric.mod.json`/`mods.toml` w jarze — tylko odczyt plików tekstowych z zip, bez ładowania klas).
- **Loadery**: Fabric/Quilt — profil wersji z ich meta-API (`meta.fabricmc.net`, `meta.quiltmc.org`) jako JSON; bez uruchamiania kodu. Forge/NeoForge — instalator to program Java z „procesorami”; uruchamia go użytkownik (lub korzystamy z zewnętrznego launchera).
- **Uruchamianie**: (a) oficjalny Minecraft Launcher — utworzenie wpisu w `launcher_profiles.json` z `gameDir` = folder instancji (to modyfikacja konfiguracji innej aplikacji → za zgodą, z kopią, odwracalne); (b) eksport instancji do Prism Launcher / import `.mrpack`. Nie implementujemy logowania Microsoft.
- **Format `.mrpack`** (Modrinth): zip z `modrinth.index.json` (`formatVersion`, `game: "minecraft"`, `versionId`, `name`, `files[]` z `path`, `hashes.sha1`, `hashes.sha512`, `env.client/server`, `downloads[]`, `fileSize`; `dependencies` z kluczami `minecraft`, `fabric-loader`, `quilt-loader`, `forge`, `neoforge`) + `overrides/` i `client-overrides/`. Import: walidacja `path` (żadnego `..`), pobranie plików wyłącznie z dozwolonych hostów (Modrinth CDN, GitHub, inne wymienione w specyfikacji formatu) i weryfikacja `sha512`.
- **Pułapki**: mody tylko-serwerowe (`env.client = unsupported`) pomijamy; `mods/` jest płaskie — konflikty to raczej duplikaty tego samego moda w różnych wersjach (wykrywane po `modid` z metadanych jara); strategia wdrożenia dla instancji w magazynie: bez wdrażania (instancja to folder gry); dla gier na USB bez problemów z literą dysku.

### 3.4 Bethesda (`template.bethesda.json`, `skyrimse.json`, `fallout4.json`, `falloutnv.json`, `starfield.json`, `morrowind.json`)

Wspólnie:

- **Układ**: `Data/` (Morrowind: `Data Files/`) z pluginami (`.esm/.esp/.esl`), archiwami (`.bsa`/`.ba2`) i luźnymi plikami (`meshes`, `textures`, `scripts`, `interface`, `sound`, `SKSE/…`); Script Extender w korzeniu gry (`*_loader.exe` + DLL); ENB/ReShade w korzeniu. FOMOD bardzo częsty.
- **Pluginy — reguły**:
  - ESM = master (ładowany przed ESP niezależnie od pozycji na liście w nowszych grach), ESP = zwykły plugin, ESL (Skyrim SE, FO4, Starfield) = „light” — rozszerzenie `.esl` lub flaga ESL w nagłówku `TES4` (ESP z flagą = ESPFE). Lekkie pluginy dzielą slot `FE` (do 4096 sztuk, każdy ograniczony do 4096 rekordów nowych FormID). Pełnych pluginów maks. ~254 (sloty `00`–`FD`).
  - Starfield ma dodatkowo pluginy „medium” (slot `FD`, flaga w nagłówku).
  - Nagłówek `TES4`/`TES3` czytamy sami (format rekordów jest udokumentowany przez społeczność UESP) — tylko flagi i listę `MAST` (mastery). Walidacja: brakujący master, master po zależnym, przekroczone limity, ESL z nowymi rekordami poza zakresem (ostrzeżenie).
- **Formaty plików kolejności**:
  - `ini-gamefile` (Morrowind): `Morrowind.ini` sekcja `[Game Files]`, linie `GameFile0=Morrowind.esm`…; kolejność **wg daty modyfikacji** plików → ustawiamy mtime (pluginy jako kopie, §1.7).
  - `active-only` + `timestamp` (Oblivion, Fallout 3, Fallout NV): `%LOCALAPPDATA%\<Gra>\plugins.txt` = lista aktywnych, kolejność z mtime.
  - `textfile` (Skyrim LE): `plugins.txt` (aktywne) + `loadorder.txt` (pełna kolejność, standard narzędzi społeczności) — gra czyta kolejność z `plugins.txt`, mtime też ustawiamy dla zgodności.
  - `asterisk` (Skyrim SE/AE, Fallout 4, Starfield): `plugins.txt` zawiera wszystkie pluginy w kolejności, aktywne poprzedzone `*`. Kodowanie: Windows-1252 dla starszych, UTF-8 dla Starfield (do weryfikacji testem na prawdziwym pliku). Pluginy bazowe (`implicitPlugins`) i z listy Creation Club (`Skyrim.ccc`, `Fallout4.ccc`, `Starfield.ccc`) ładują się zawsze i nie są zapisywane (gra je dopisuje) — pokazujemy je jako zablokowane na górze.
- **Sortowanie**: w MVP ręczne + „mastery przed zależnymi” + walidacja. Faza 3+: opcjonalna integracja z LOOT — jeśli użytkownik ma LOOT, możemy uruchomić go jako zewnętrzne narzędzie (za zgodą) albo odczytać masterlistę (YAML, licencja masterlisty do sprawdzenia) — decyzja później.
- **Loadery**: SKSE64 (Skyrim SE/AE; + Address Library), F4SE, SFSE, xNVSE, xOBSE, MWSE. Wszystkie przypięte do wersji exe.
- **Pułapki**:
  - Aktualizacja gry psuje Script Extender i pluginy DLL (szczególnie Skyrim AE 1.6.x vs SE 1.5.97, Fallout 4 „next-gen” 2024) → `gameVersionLocked` + odczyt wersji exe (zasób wersji pliku) + mapa zgodności.
  - Fallout 4 i Starfield wymagają ustawień INI (`bInvalidateOlderFiles=1`, `sResourceDataDirsFinal=`), aby czytać luźne pliki → proponujemy edycję `*Custom.ini` z kopią, za zgodą.
  - Starfield: luźne pliki z `Dokumenty/My Games/Starfield/Data` mają pierwszeństwo — tam wdrażamy luźne pliki; lista pluginów bazowych zmienia się z aktualizacjami (kreacje Bethesdy).
  - Wersje GOG/Epic/MS Skyrim SE mają inne nazwy folderów w Dokumentach i AppData (`storeOverrides`).
  - Usuwanie pluginów w trakcie rozgrywki psuje zapisy — ostrzeżenie przy wyłączaniu pluginu, gdy profil ma zapisy.
  - Oblivion Remastered (2025, UE5 + silnik Oblivion) — osobna definicja (pluginy w `OblivionRemastered/Content/Dev/ObvData/Data` i `Plugins.txt` w tym folderze; do weryfikacji), nie dziedziczy wprost po szablonie.
  - OpenMW: osobna definicja `openmw` — `openmw.cfg` (`Dokumenty/My Games/OpenMW/openmw.cfg`) z liniami `data="…"` (foldery danych, kolejność = priorytet) i `content=…` (pluginy). Dzięki temu strategia `external-folder`: wskazujemy foldery modów w magazynie bez kopiowania. Uwaga na zmianę litery USB — linie `data=` przepisujemy przy każdym starcie.

### 3.5 Stardew Valley (`stardewvalley.json`)

- **Układ**: `Mods/<FolderModa>/manifest.json` (`Name`, `Author`, `Version`, `UniqueID`, `EntryDll` albo `ContentPackFor`, `Dependencies`, `UpdateKeys` np. `Nexus:2400`). Jedno archiwum może zawierać kilka modów.
- **Kolejność**: SMAPI sortuje sam wg zależności — my walidujemy (brak zależności, zduplikowane `UniqueID`, wersje minimalne).
- **Loader**: SMAPI (wymagany zawsze). Instalator SMAPI uruchamia użytkownik.
- **Wdrożenie bez dotykania gry**: SMAPI przyjmuje argument `--mods-path <folder>` — profil to folder `<profil>/Mods` (hardlinki/kopie z magazynu w obrębie USB lub cache), uruchamiamy `StardewModdingAPI.exe --mods-path …`. Domyślna strategia `external-folder`; fallback — wdrożenie do `{game}/Mods`.
- **Pułapki**: `config.json` tworzony przez mody w ich folderze → przechwytywany do nakładki profilu; SMAPI ignoruje foldery zaczynające się kropką; uruchamianie przez Steam wymaga wpisania opcji uruchamiania (podajemy tekst do skopiowania); wersje Xbox/Game Pass nie wspierają SMAPI.

### 3.6 RimWorld (`rimworld.json`)

- **Układ**: `<gra>/Mods/<Folder>/About/About.xml` (`packageId`, `name`, `supportedVersions`, `modDependencies`, `loadBefore`, `loadAfter`, `incompatibleWith`), `Assemblies/`, `Defs/`, `Patches/`, `Textures/`, foldery wersji `1.5/`, `1.6/` i opcjonalnie `LoadFolders.xml`.
- **Kolejność**: `%USERPROFILE%\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios\Config\ModsConfig.xml` — `<ModsConfigData><version>…</version><activeMods><li>packageid</li>…</activeMods><knownExpansions>…</knownExpansions></ModsConfigData>`. Writer zachowuje nieznane elementy XML (zapisujemy przez model DOM, nie przez szablon). `packageId` porównujemy bez wielkości liter.
- **Sortowanie**: topologiczne wg `loadBefore/loadAfter/modDependencies`, Harmony pierwszy, potem Core i DLC; konflikty (cykle) do rozstrzygnięcia przez użytkownika.
- **Loadery**: Harmony (zwykły mod `brrainz.harmony`).
- **Pułapki**: mody z Warsztatu Steam — tylko odczyt, ale widoczne na liście kolejności (zarządzamy ich kolejnością, nie plikami); `-savedatafolder=<ścieżka>` pozwala profilowi mieć własny `Config/ModsConfig.xml` i zapisy — tryb opcjonalny; DLC ID muszą pozostać na liście, jeśli posiadane.

### 3.7 Baldur's Gate 3 (`baldursgate3.json`)

- **Układ**: mody `.pak` → `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\`; Script Extender → `<gra>/bin/DWrite.dll`; mody natywne → `<gra>/bin/NativeMods/` (wymagają Native Mod Loadera); rzadkie luźne pliki → `<gra>/Data/`.
- **Kolejność**: `…\PlayerProfiles\Public\modsettings.lsx` — XML Larian: `save` → `region id="ModuleSettings"` → `node id="root"` → `children` → `node id="Mods"` → lista `node id="ModuleShortDesc"` z atrybutami `Folder`, `MD5`, `Name`, `PublishHandle`, `UUID`, `Version64`. Od Patch 7 nie ma osobnego węzła `ModOrder` — kolejność listy `Mods` jest kolejnością ładowania (ostatni wygrywa). Pierwszy wpis to zawsze moduł bazowy `GustavDev`. Wersja nagłówka pliku zależy od patcha — **writer kopiuje nagłówek `version` z pliku, który zapisała gra**, i zmienia tylko listę modów.
- **Metadane moda**: `meta.lsx` wewnątrz `.pak` (format LSPK: czytamy nagłówek i tabelę plików, dekompresja LZ4/zstd pojedynczego wpisu) — UUID, Folder, Version64, zależności; alternatywnie `info.json` w archiwum z Nexusa.
- **Loadery**: BG3 Script Extender (opcjonalnie wymagany; wykrywany po `ScriptExtender/Config.json` w paku).
- **Pułapki**: `.pak` w folderze Mods, ale nie w `modsettings.lsx`, wciąż może nadpisywać pliki → wyłączony mod musi zniknąć z folderu (purge); wbudowany menedżer modów gry (mod.io) zapisuje ten sam plik → wykrywanie zmian zewnętrznych; MD5 często puste — identyfikujemy po UUID; zależności od modułów bazowych gry ignorujemy (lista wyjątków); przy starcie przez Steam launcher Larian jest pomijany argumentem `--skip-launcher`; renderer Vulkan vs DX11 — dwa executables.

### 3.8 Cyberpunk 2077 (`cyberpunk2077.json`)

- **Układ** (od korzenia gry):
  - `archive/pc/mod/*.archive` (+ `*.xl` dla ArchiveXL) — mody zasobów;
  - `mods/<nazwa>/info.json` + `archives/`, `customSounds/`, `scripts/`, `tweaks/` — REDmod;
  - `r6/scripts/**/*.reds` — redscript; `r6/tweaks/**/*.yaml` — TweakXL;
  - `bin/x64/plugins/cyber_engine_tweaks/mods/<nazwa>/init.lua` — mody CET;
  - `red4ext/plugins/<nazwa>/*.dll` — RED4ext;
  - `engine/config/platform/pc/*.ini` — poprawki konfiguracji.
- **Kolejność**: `.archive` ładują się alfabetycznie; od aktualizacji 2.0 gra respektuje `archive/pc/mod/modlist.txt` (jedna nazwa pliku na linię) — writer `cyberpunk-modlist` zapisuje kolejność z profilu. REDmod: kolejność przekazywana do `redMod.exe deploy` (parametry `-mod=` w kolejności), co kompiluje mody do `r6/cache/modded`. Uruchomienie z `-modded`.
- **Loadery**: CET (`bin/x64/version.dll` + `plugins/cyber_engine_tweaks.asi`), RED4ext (`bin/x64/winmm.dll`), redscript, ArchiveXL/TweakXL (wtyczki RED4ext), REDmod (DLC narzędziowe ze sklepu).
- **Uruchamianie narzędzia gry**: `redMod.exe` to oficjalne narzędzie CD Projekt (nie zawartość moda) — uruchamiamy je jako krok `postDeploy` **tylko za zgodą** (jednorazową lub stałą per instalacja), z przechwyceniem wyjścia do logu.
- **Pułapki**: każda aktualizacja gry psuje CET/RED4ext do czasu ich aktualizacji; `r6/cache/modded` jest generowane — nie należy do manifestu, ale purge go czyści (lista „plików pochodnych” w adapterze); archiwa z Nexusa zwykle są „od korzenia gry” — typ `root`; mody zawierające `bin/x64/*.dll` → ostrzeżenie o kodzie natywnym; Epic: argument `-modded` trzeba dodać w ustawieniach launchera Epic (pokazujemy instrukcję).

### 3.9 Wiedźmin 3 (`witcher3.json`)

- **Układ**: `<gra>/Mods/mod<Nazwa>/content/…` (`.bundle`, `.cache`, `scripts/*.ws`), `<gra>/dlc/dlc<Nazwa>/` dla modów-DLC, `<gra>/bin/config/r4game/user_config_matrix/pc/*.xml` dla menu (wymaga wpisów w `dx11filelist.txt`/`dx12filelist.txt`), `Dokumenty/The Witcher 3/input.settings` i `user.settings` dla kluczy.
- **Kolejność**: `Dokumenty/The Witcher 3/mods.settings` — sekcje `[modNazwa]` z `Enabled=1` i `Priority=N`; niższy numer = wyższy priorytet. Bez pliku: sortowanie po nazwie folderu (wcześniejszy alfabetycznie wygrywa — odwrotnie niż w większości gier; UI musi to tłumaczyć).
- **Loadery**: brak wymaganego; do skryptów — Script Merger (zewnętrzne, uruchamia użytkownik).
- **Pułapki**: dwa mody zmieniające ten sam `.ws` lub ten sam plik w `.bundle` wymagają scalenia (wykrywamy konflikty `.ws` jako „twarde” i oznaczamy na czerwono); edycje `input.settings` to wspólny plik — modyfikacja tylko za zgodą, z kopią, przez łatkę tekstową (dopisanie sekcji), nie nadpisanie całości; nazwa folderu moda musi zaczynać się od `mod`; wersja next-gen (4.x) i DX12 mają osobne `bin/x64_dx12`; mody REDkit są zgodne z tym samym układem.

### 3.10 Klasyki

**Doom — source porty** (`doom-sourceport.json`)

- **Układ**: brak wdrożenia — strategia `launch-args`; pliki `.wad`, `.pk3`, `.pk7`, `.pke`, `.deh`, `.bex` zostają w magazynie.
- **Kolejność**: argumenty: `-iwad DOOM2.WAD -file a.wad b.pk3 -deh x.deh`; kolejność `-file` = kolejność ładowania (późniejszy nadpisuje). IWAD wybierany per profil; IWAD-y znajdujemy w instalacjach Steam/GOG (DOOM + DOOM II z 2024 — pliki w `rerelease/`, Ultimate Doom, Doom II, Final Doom, Heretic, Hexen) i w folderze portu.
- **Loadery**: sam port: GZDoom (rozwój kontynuowany jako UZDoom), LZDoom, DSDA-Doom, Chocolate/Crispy Doom.
- **Pułapki**: kompatybilność poziomów (vanilla, limit-removing, Boom, MBF21, UDMF/ZScript) — pokazujemy port zalecany; Chocolate Doom dla PWAD-ów ze sprite’ami wymaga `-merge`; `.pk3` jest zipem — nie rozpakowujemy go; argumenty z tablicy, nie z powłoki (ścieżki ze spacjami).

**GoldSrc** (`halflife.json`)

- **Układ**: mody jako osobne katalogi obok `valve/` z `liblist.gam` (np. `cstrike`, `gearbox`, mody społeczności) uruchamiane `hl.exe -game <katalog>`; dodatki do istniejącej gry w `<katalog>_addon/` (wymaga opcji „zezwalaj na zawartość dodatków” w grze); `<katalog>_downloads/` — pliki z serwerów (nie ruszamy).
- **Kolejność**: brak; konflikty między dodatkami — priorytet wdrożenia.
- **Pułapki**: nigdy nie piszemy do `valve/` (protectedPaths); mody z własnymi DLL (`cl_dlls/client.dll`) + VAC → ostrzeżenie dla gry online.

**Source** (definicje w fazie 3: HL2, Portal, TF2 offline, Garry’s Mod tylko odczyt)

- **Układ**: `<gra>/<katalog>/custom/<nazwa>/` (luźne pliki lub `.vpk`) — silnik montuje wszystko z `custom/`; mody pełne (Source SDK) → `<Steam>/steamapps/sourcemods/<mod>/` z `gameinfo.txt`, uruchamiane przez Steam (pojawiają się w bibliotece po restarcie Steam).
- **Kolejność**: kolejność w `custom/` alfabetyczna (zachowanie silnika — do weryfikacji per gra); zwykle bez znaczenia.
- **Pułapki**: VAC — mody wpływające na rozgrywkę w grach sieciowych (TF2, CS2) mogą skutkować problemami; CS2 (Source 2) nie wspiera `custom/` w trybie online — definicja oznacza „tylko offline/serwery społeczności”.

**Mount & Blade** (definicje w fazie 3)

- **Warband**: `<gra>/Modules/<Moduł>/` (`module.ini`); wybór modułu w launcherze gry (zapisywany w rejestrze `HKCU\Software\MountAndBladeWarbandKeys\last_module_warband`) — zmiana tej wartości za zgodą jako „wybierz moduł”. Bez kolejności ładowania — mody to całe moduły; często wymagają kopii `Native`.
- **Bannerlord**: `<gra>/Modules/<Id>/SubModule.xml` (`Id`, `Version`, `DependedModules`, `ModuleCategory`); kolejność w `Dokumenty/Mount and Blade II Bannerlord/Configs/LauncherData.xml` lub argumentem `/singleplayer _MODULES_*Native*SandBoxCore*…*MójMod*_MODULES_` przy uruchomieniu `Bannerlord.exe`. Moduły z Warsztatu w `steamapps/workshop/content/261550`. Loader społeczności (BLSE + Harmony) — `as-mod`. Pułapka: DLL-e rozpakowane Eksploratorem Windows z pobranego archiwum dziedziczą „Mark of the Web” (`Zone.Identifier`) i .NET odmawia ich załadowania. Nasz ekstraktor nie kopiuje tego znacznika do magazynu (pliki tworzymy sami), więc problem dotyczy tylko modów zainstalowanych ręcznie poza menedżerem — wykrywamy taki znacznik w folderze gry i informujemy, nie usuwając go bez zgody.

**GTA SA / IV / V** (`gtasa.json`; IV i V w fazie 3 — tylko układ)

- **GTA SA**: ASI Loader (`vorbisFile.dll` z Silent’s ASI Loader lub `dinput8.dll` Ultimate ASI Loader), `*.asi` w korzeniu lub `scripts/`, CLEO (`cleo.asi` + `cleo/*.cs`), Mod Loader (`modloader.asi` + `modloader/<mod>/`) — preferowany, bo nie modyfikuje `gta3.img`. Pułapka: wiele modów wymaga exe 1.0 US; wersja ze Steam jest inna — wykrywamy po hashu i ostrzegamy, **nie dostarczamy downgradera**. Definitive Edition to inna gra.
- **GTA IV** (Complete Edition): Ultimate ASI Loader (`dinput8.dll`), ScriptHookIV / `plugins/*.asi`, FusionFix z folderem `update/` dla podmian plików bez edycji archiwów (`.img`/`.rpf`). Kolejność brak — priorytet wdrożenia.
- **GTA V** (Legacy/Enhanced): ScriptHookV + `dinput8.dll` + `*.asi` w korzeniu, `scripts/` dla .NET (ScriptHookVDotNet), folder `mods/` dla OpenIV (podmiany `.rpf` — edycja narzędziem zewnętrznym, nie przez nas). **Ostrzeżenie krytyczne**: GTA Online z modami grozi banem (BattlEye) — nie da się wykryć z zewnątrz, czy gracz wejdzie do trybu online, więc moduł wymusza osobny profil „vanilla/online” (purge przed uruchomieniem), pokazuje stały komunikat przy profilu z modami i umożliwia przełączanie profili jednym kliknięciem. ScriptHookV jest przypięty do wersji gry.

---

## 4. Źródła modów, API i warunki korzystania

Zasady wspólne (`sources/ratelimit`): jeden klient HTTP na źródło; `User-Agent` jednoznacznie identyfikujący aplikację (nazwa + wersja, bez danych użytkownika); szanowanie `Retry-After` i nagłówków limitów; wykładniczy backoff z jitterem; cache odpowiedzi (ETag/`If-Modified-Since`, gdzie dostępne); sprawdzanie aktualizacji najwyżej raz na N godzin i tylko na żądanie lub przy starcie (konfigurowalne); klucze API w Windows Credential Manager (`CredWrite`, `CRED_TYPE_GENERIC`), **nie** w plikach na USB — na USB co najwyżej w zaszyfrowanym pliku chronionym hasłem użytkownika (opcja), bo pendrive łatwo zgubić. Nigdy nie logujemy kluczy.

### 4.1 Nexus Mods

- **Klucz API**: osobisty klucz API z ustawień konta Nexus (zakładka API). Do dystrybucji aplikacji dla innych osób Nexus wymaga rejestracji aplikacji i logowania SSO (WebSocket `sso.nexusmods.com` z identyfikatorem aplikacji nadanym przez Nexus) — na start (użytek własny) wystarczy klucz wklejony przez użytkownika; przed publiczną dystrybucją: wniosek o rejestrację aplikacji.
- **API v1** (`https://api.nexusmods.com/v1/…`, nagłówki `apikey`, `Application-Name`, `Application-Version`): `users/validate.json` (czy klucz ważny, czy konto premium), `games/{domain}/mods/{id}.json`, `…/files.json`, `…/files/{fileId}/download_link.json`, `games/{domain}/mods/md5_search/{md5}.json` (rozpoznanie ręcznie pobranego archiwum), `games/{domain}/mods/updated.json?period=1w` (tanie sprawdzanie aktualizacji zbiorczo). Istnieje też API v2 (GraphQL) — do rozważenia dla wyszukiwania.
- **Limity**: wg strony pomocy Nexus — limit dzienny 20 000 zapytań (reset o 00:00 GMT) oraz godzinowy 500 zapytań; po przekroczeniu któregokolwiek zapytania (pobieranie, sprawdzanie aktualizacji) są odrzucane. Starsze wpisy na forum podają inne liczby — dokładną semantykę sprawdzamy na bieżąco z nagłówków odpowiedzi, a nie z wartości wpisanych w kod. Nagłówki `X-RL-Daily-Remaining`, `X-RL-Hourly-Remaining`; HTTP 429 przy przekroczeniu. Nasz budżet: sprawdzanie aktualizacji przez `updated.json` (1 zapytanie na grę) zamiast per mod; twardy wewnętrzny limit (np. ≤ 50% pozostałego limitu godzinowego) i licznik w UI.
- **Pobieranie — konto premium**: `download_link.json` bez dodatkowych parametrów zwraca listę URL-i CDN → możliwe pobieranie bezpośrednio z aplikacji.
- **Pobieranie — konto darmowe** (zgodnie z zasadami Nexusa): użytkownik klika na stronie moda przycisk **„Mod Manager Download”** → przeglądarka otwiera `nxm://{domain}/mods/{modId}/files/{fileId}?key=…&expires=…&user_id=…` → nasza aplikacja (zarejestrowany handler) wywołuje `download_link.json?key=…&expires=…` → pobiera plik. Bez kliknięcia użytkownika na stronie darmowe konto nie pobiera — **nie automatyzujemy tego kroku** (żadnego „klikania” w przeglądarce, scrapingu ani obchodzenia).
- **Handler `nxm://`**: rejestracja w `HKCU\Software\Classes\nxm` (`URL Protocol`, `shell\open\command` = `"<ścieżka exe>" --nxm "%1"`) **tylko za zgodą**, z informacją, że przejmie obsługę od Vortex/MO2 (wykrywamy obecny handler i pokazujemy, co zastępujemy; możliwość przywrócenia poprzedniego). Pojedyncza instancja: druga instancja exe przekazuje URL przez named pipe do działającej i kończy się. Walidacja URL: schemat, domena gry z naszej listy, liczby całkowite, parametry tylko znane; URL nigdy nie trafia do powłoki.
- **Weryfikacja**: Nexus podaje MD5 pliku (np. w `md5_search` i informacjach o pliku) → po pobraniu sprawdzamy MD5 + zapisujemy własny sha256.
- **ToS**: bez scrapingu stron, bez masowego pobierania, bez omijania premium; szanowanie preferencji autorów (np. pliki ukryte/archiwalne).

### 4.2 Thunderstore

- **API** (publiczne, bez klucza do odczytu): indeks pakietów społeczności `https://thunderstore.io/c/{community}/api/v1/package/` (duży JSON — pobierany warunkowo, cache na dysku, odświeżanie np. co 1 h lub na żądanie; parsowanie strumieniowe), endpointy eksperymentalne `api/experimental/package/{namespace}/{name}/` (szczegóły pojedynczego pakietu), pobieranie `https://thunderstore.io/package/download/{namespace}/{name}/{version}/`. Dokumentacja: `thunderstore.io/api/docs/` — przed implementacją zweryfikować aktualne endpointy (API ewoluuje, część oznaczona jako eksperymentalna).
- **Zależności**: `dependencies` w formacie `Namespace-Name-Version`; rozwiązywanie grafu, pakiety oznaczone `is_deprecated` — ostrzeżenie; `has_nsfw_content` — filtr domyślnie włączony.
- **Protokół** `ror2mm://` używany przez stronę dla menedżerów — obsługa opcjonalna (faza 2), z takimi samymi zasadami rejestracji jak `nxm`.
- **Weryfikacja**: brak sumy kontrolnej w indeksie v1 (do sprawdzenia w aktualnym API) → zapisujemy sha256 przy pierwszym pobraniu i porównujemy przy ponownych; walidacja `manifest.json` (nazwa, wersja zgodna z URL).
- **ToS**: szanować limity (brak opublikowanego limitu → własny limit, np. 2 zapytania/s), nie odpytywać pełnego indeksu częściej niż potrzeba.

### 4.3 Modrinth

- **API v2** `https://api.modrinth.com/v2/…` (odczyt bez klucza): `search` (facety: kategorie/loader, wersje gry, typ projektu), `project/{id|slug}`, `project/{id}/version?loaders=["fabric"]&game_versions=["1.21.1"]`, `version_file/{hash}?algorithm=sha1` i `version_files` (POST, zbiorczo — rozpoznawanie i aktualizacje wielu plików jednym zapytaniem), `version_files/update` (zbiorcze sprawdzenie aktualizacji).
- **Wymagania**: jednoznaczny `User-Agent` (wymóg dokumentacji; ogólne UA mogą być blokowane) — np. `GameLauncher-ModManager/1.0`; limit 300 zapytań/min na IP, nagłówki `X-Ratelimit-Limit/Remaining/Reset`, 429 przy przekroczeniu. Token osobisty tylko do operacji wymagających konta (niepotrzebny w MVP).
- **Weryfikacja**: każdy plik wersji ma `hashes.sha1` i `hashes.sha512` → obowiązkowa weryfikacja `sha512`.
- **Modpacki**: `.mrpack` (§3.3).

### 4.4 CurseForge

- **API** `https://api.curseforge.com/v1/…` wymaga klucza (`x-api-key`) wydawanego przez konsolę CurseForge dla deweloperów po zaakceptowaniu warunków; warunki zabraniają ujawniania klucza. Wniosek: **nie wbudowujemy klucza w aplikację**; użytkownik może wkleić własny klucz (użytek osobisty) albo — przy publicznej dystrybucji — rejestrujemy aplikację u CurseForge i trzymamy klucz po stronie serwera pośredniczącego (poza zakresem). Bez klucza: obsługa ręcznie pobranych plików + import manifestów modpacków (`manifest.json` CurseForge: `minecraft.version`, `modLoaders`, `files[{projectID, fileID, required}]`, `overrides`).
- **Dystrybucja przez osoby trzecie**: mody z `allowModDistribution = false` mają puste `downloadUrl` — wtedy UI otwiera stronę moda w przeglądarce i prosi o ręczne pobranie (potem import i dopasowanie po odcisku), nigdy nie obchodzimy tego.
- **Rozpoznawanie plików**: CurseForge używa „fingerprintu” (MurmurHash2 z pliku po usunięciu białych znaków) — endpoint `fingerprints` do dopasowania ręcznie pobranych plików (faza 3).
- **Weryfikacja**: pliki mają `hashes` (sha1/md5) → sprawdzamy.

### 4.5 GitHub Releases

- `https://api.github.com/repos/{owner}/{repo}/releases/latest` i `/releases` — bez tokenu limit 60 zapytań/h na IP; z tokenem osobistym (opcjonalnie, bez uprawnień) — 5000/h. ETag + `If-None-Match` (odpowiedzi 304 nie liczą się do limitu).
- Wybór zasobu (asset) wg wzorca z definicji (np. `SMAPI-*-installer.zip` — tylko do wskazania użytkownikowi, `BepInEx_win_x64_*.zip`, `RED4ext-*.zip`); pre-release pomijane domyślnie.
- **Weryfikacja**: jeśli wydanie publikuje sumy (`*.sha256`, `checksums.txt`) lub API podaje skrót zasobu — sprawdzamy; w przeciwnym razie zapisujemy sha256 przy pierwszym pobraniu (TOFU) i ostrzegamy o braku weryfikacji pochodzenia.

### 4.6 Ręczne archiwa

- Przeciągnij-upuść / „Dodaj z pliku”; plik kopiowany do `downloads/` (oryginał zostaje u użytkownika).
- Próba rozpoznania pochodzenia: MD5 → Nexus `md5_search` (jeśli klucz), sha1 → Modrinth `version_file`, nazwa pliku `Namespace-Name-1.2.3.zip` → Thunderstore. Rozpoznanie tylko uzupełnia metadane (aktualizacje), nie jest wymagane.

---

## 5. Bezpieczeństwo

### 5.1 Bezpieczna ekstrakcja

Zob. §1.5: walidacja ścieżek (traversal, absolutne, UNC, ADS, nazwy zarezerwowane), brak linków z archiwów, limity rozmiaru/liczby/kompresji liczone w trakcie strumieniowania, ekstrakcja do katalogu tymczasowego i atomowe przeniesienie, `O_EXCL`, osobny katalog na każdy import. Te same reguły dla ścieżek z FOMOD, `.mrpack`, manifestów i definicji gier.

### 5.2 Żadnego wykonywania zawartości modów podczas instalacji

- Instalator nie uruchamia niczego z archiwum: żadnych `.exe`, `.bat`, `.ps1`, skryptów C# FOMOD, `install.cmd`, instalatorów MSI. Takie pliki w archiwum → mod oznaczony, UI pokazuje „ten mod zawiera instalator; zainstaluj go ręcznie / sprawdź instrukcję autora”.
- Parsujemy tylko formaty danych (XML, JSON, INI, nagłówki pluginów, nagłówki `.pak`) — parsery z limitami rozmiaru i głębokości (XML: wyłączone encje zewnętrzne — `encoding/xml` w Go ich nie rozwija, ale ograniczamy rozmiar pliku i głębokość).
- Narzędzia uruchamiane przez moduł to wyłącznie: gra, loader zainstalowany przez użytkownika (SKSE itp. — uruchamiany na żądanie użytkownika jako „Graj”) i oficjalne narzędzia gry (`redMod.exe`) — po zgodzie.
- Obrazy z FOMOD/README wyświetlane w WebView jako dane (`data:` po sprawdzeniu typu obrazu), HTML/Markdown z modów renderowany bez skryptów (sanityzacja, CSP).

### 5.3 Ostrzeżenia dla modów z kodem (DLL/ASI/skrypty)

- Klasyfikacja przy imporcie: `*.dll`, `*.asi`, `*.exe`, `*.so`, `*.jar`, `*.lua`, `*.cs` (CLEO/C#), `*.reds`, `*.ws`, `*.py`, `*.ps1`, `*.bat`, `*.js` + typy z `executableContent: true` → flaga `executableContent`.
- Pierwsze włączenie takiego moda w profilu → okno: co to znaczy (kod uruchamiany z uprawnieniami gry, dostęp do plików użytkownika), źródło i autor, czy hash pliku zgadza się ze źródłem, czy plik ma podpis Authenticode (informacyjnie, `WinVerifyTrust`). Decyzja zapamiętana per mod i wersja.
- Mod z kodem z „nieznanego źródła” (ręczne archiwum bez dopasowania) → wyraźniejsze ostrzeżenie.
- Pliki zastępujące systemowe DLL-proxy (`dinput8.dll`, `version.dll`, `winmm.dll`, `dxgi.dll`, `d3d11.dll`, `winhttp.dll`, `dsound.dll`) → informacja, że to loader, i który mod go dostarcza (konflikty takich plików są szczególnie groźne — dwa loadery w tym samym pliku).
- Ostrzeżenia gier online/antycheat (VAC, BattlEye, EAC) z definicji (`when: on-online-launch`).

### 5.4 Kopie zapasowe

- Każdy nadpisywany plik gry → backup przed nadpisaniem (§1.8); każdy plik kolejności/INI → backup przed zapisem.
- Opcjonalna „migawka vanilla” przy pierwszym wdrożeniu: lista plików gry z rozmiarami, mtime i (opcjonalnie, w tle) sha256 — pozwala później wykryć, co zmieniło się poza nami i zbudować raport „czy gra jest czysta”.
- Profile i `state/` — eksport do jednego pliku `.zip` (bez magazynu) jako kopia konfiguracji.

### 5.5 Weryfikacja sum kontrolnych pobrań

- Nexus: MD5; Modrinth: sha512; CurseForge: sha1/MD5; GitHub: plik sum lub skrót zasobu (gdy dostępny); Thunderstore: TOFU sha256; ręczne: sha256 zapisany przy imporcie.
- Pobieranie do `*.part`, hashowanie w locie, porównanie, dopiero wtedy `rename`. Niezgodność → usunięcie, ponowienie raz, potem błąd z informacją.
- Wznawianie pobierania (HTTP Range) — jeśli serwer wspiera; hash liczony od początku po złożeniu.
- Tylko HTTPS; przekierowania tylko do HTTPS; dla `.mrpack` — lista dozwolonych hostów pobierania.

---

## 6. Strategia testów

### 6.1 Fałszywe foldery gier (`testkit`)

- Generator fałszywych instalacji z definicji: dla każdej definicji tworzy w `t.TempDir()` strukturę z `requiredFiles` (puste pliki lub minimalne prawidłowe: np. `Skyrim.esm` z poprawnym nagłówkiem TES4, `About.xml`, `modsettings.lsx` z prawdziwym nagłówkiem), plus fałszywe korzenie `documents`, `localAppData` — wstrzykiwane przez interfejs `KnownFolders`, nigdy prawdziwe foldery użytkownika.
- Fałszywe Steam: `libraryfolders.vdf` + `appmanifest_*.acf` w kilku bibliotekach (także z dziwnymi ścieżkami: spacje, Unicode, `\\` w VDF), fałszywy rejestr (interfejs `Registry` z implementacją w pamięci), fałszywe manifesty Epic.
- Fałszywe archiwa generowane w testach (zip budowany w Go; 7z/rar — małe pliki-fixture w repo, stworzone przez nas).
- Fałszywe serwery API (`httptest.Server`) dla Nexus/Modrinth/Thunderstore/GitHub: nagrane odpowiedzi w formacie przez nas zdefiniowanym, scenariusze 429, `Retry-After`, uszkodzony hash, przekierowanie na HTTP.

### 6.2 Złote testy wdrożenia i purge

- Scenariusz: (stan gry vanilla) → import modów A, B, C → profil → deploy → **zrzut drzewa** (ścieżka, rozmiar, sha256, typ: plik/hardlink/symlink, mtime dla gier „timestamp”) + zawartość plików kolejności → porównanie z plikiem złotym `testdata/golden/<gra>/<scenariusz>.deploy.txt`.
- Purge → zrzut drzewa musi być **identyczny** z zrzutem vanilla (test właściwości dla każdego scenariusza).
- Przełączenie profilu P1 → P2 → wynik równy bezpośredniemu wdrożeniu P2 na vanilla; P1 → P2 → P1 równe P1.
- Writery kolejności: złote pliki `plugins.txt` (każdy format), `ModsConfig.xml`, `modsettings.lsx`, `mods.settings`, `modlist.txt`, argumenty Dooma; test „read(write(x)) == x” i „zachowanie nieznanych elementów” (XML z dodatkowymi węzłami).
- Każda strategia (hardlink/symlink/copy) uruchamiana w tych samych scenariuszach; symlinki pomijane, gdy brak uprawnień (test oznaczony `t.Skip` z powodem).
- Aktualizacja `-update` flagą do regeneracji złotych plików, z przeglądem diffu w PR.

### 6.3 Wstrzykiwanie awarii dla dziennika

- Warstwa `fsx` (interfejs systemu plików używany przez deploy/journal) z implementacją „awaryjną”: po N-tej operacji (`Create`, `Rename`, `Link`, `Remove`, `Sync`, zapis WAL) zwraca błąd albo symuluje „utratę prądu” — zatrzymuje wykonywanie i **odrzuca niezsynchronizowane zapisy** (model: wszystko po ostatnim `Sync` danego pliku może zniknąć lub być urwane).
- Test wyczerpujący: dla scenariusza z K operacjami dla każdego N ∈ [0, K]: uruchom deploy, przerwij po N, uruchom `Recover`, sprawdź, że stan jest **dokładnie** równy stanowi „przed” albo „po” (nigdy pośredni), a ponowne `Recover` niczego nie zmienia (idempotencja). To samo dla purge i redeploy.
- Uszkodzone WAL: urwana ostatnia linia, zły CRC, pusty plik, brak `PLAN` → zachowanie zgodne z §1.8.
- Test procesowy (rzadszy, w CI nocnym): proces potomny wykonujący deploy zabijany `TerminateProcess` w losowych momentach; potem recover w nowym procesie.
- Brak źródła w trakcie recover (symulacja odłączonego USB) → roll-back, nie roll-forward.

### 6.4 Testy konfliktów

- Tabelaryczne: zestawy modów z nakładającymi się ścieżkami (różna wielkość liter, `\` vs `/`, różne typy modów trafiające w to samo miejsce, identyczne hashe) → oczekiwani zwycięzcy; zmiana kolejności; reguły `fileOverrides`, w tym reguła wskazująca wyłączony mod (ignorowana) i usunięty mod (sprzątanie reguły).
- Test właściwości (fuzz): losowe profile → zwycięzca każdej ścieżki w wyniku deploy == zwycięzca wg `conflict.Index`.
- Wydajność: 1000 modów × 100 000 plików — budowa indeksu < 2 s, aktualizacja po zmianie jednego moda < 100 ms (benchmark).

### 6.5 Pozostałe

- Fuzzing (`go test -fuzz`): walidator ścieżek archiwów, parser VDF, parser FOMOD, parser nagłówków TES4, parser `.mrpack`, parser URL `nxm://`.
- Bezpieczeństwo archiwów: zestaw złośliwych archiwów (traversal `../../x`, `C:\x`, ADS, `CON`, symlink w zip, zip-bomba, kłamliwy rozmiar w nagłówku) — każdy musi zostać odrzucony bez utworzenia pliku poza katalogiem tymczasowym.
- Walidacja wszystkich wbudowanych definicji względem schematu (+ scalanie `extends`) w CI — jak `tools/validate_defs.py`, docelowo test w Go.
- Testy przenośności: symulowana zmiana litery (interfejs `Volumes` w pamięci: ten sam numer seryjny pod inną literą) → poprawne rozwiązanie korzeni; symlinki → wykrycie zerwania i relink.
- Testy ręczne (lista kontrolna przed wydaniem) na prawdziwych grach z każdej rodziny, w tym „Steam: weryfikuj spójność plików” w trakcie wdrożenia.

---

## 7. Plan etapów i oszacowania

Skala: **S** ≤ 3 dni, **M** ≈ 1–2 tygodnie, **L** ≈ 3–5 tygodni (jedna osoba, z testami).

### Faza 0 — fundamenty (przed MVP)

| Zadanie | Rozmiar |
|---|---|
| Granica integracji z launcherem (`modmgr.Service`, kontrakt komend/zdarzeń dla WebView; uzgodnienie z gałęzią `port/go` po jej scaleniu) | S |
| `portable` (korzenie, numery seryjne woluminów, znane foldery) + interfejsy `fsx`, `Registry`, `KnownFolders` dla testów | M |
| `gamedef` (ładowanie, schemat, `extends`, szablony ścieżek) | M |

### Faza 1 — MVP: magazyn, ogólne wdrożenie, profile, konflikty, rollback

| Zadanie | Rozmiar |
|---|---|
| `archive`: zip/7z/rar, bezpieczna ekstrakcja, limity, testy złośliwych archiwów | M |
| `store`: import, `mod.json`, hashe, read-only, wersje | M |
| `install`: heurystyka korzenia + ręczny wybór w UI (bez FOMOD) | M |
| `deploy`: planner, strategie hardlink/copy (+symlink), manifest, journal, recover, purge | L |
| Testy wstrzykiwania awarii + złote testy | M |
| `profile` + `conflict` (indeks, zwycięzcy, `fileOverrides`) | M |
| `detect`: Steam (VDF/ACF) + ręcznie; GOG (rejestr) | M |
| `watch`: buildid/odcisk exe + dryf + redeploy | M |
| UI (po stronie launchera): lista modów, konflikty, drzewo plików, profile, przyciski Wdróż/Purge | L |
| Definicja `generic-copy` + import ręcznych archiwów | S |

Kryterium wyjścia: dowolna gra przez „kopiuj do folderu”; deploy/purge bitowo odwracalne; przeżywa zabicie procesu w każdym momencie; przenośność USB (zmiana litery) przetestowana.

### Faza 2 — BepInEx/Thunderstore i Modrinth

| Zadanie | Rozmiar |
|---|---|
| Format pakietu Thunderstore + rozwiązywanie zależności | M |
| Źródło Thunderstore (indeks, cache, pobieranie, protokół opcjonalnie) | M |
| Szablon BepInEx + 5–10 popularnych gier Unity (Valheim, Lethal Company, Risk of Rain 2, Content Warning, REPO itp. — lista wg biblioteki użytkownika) | M |
| Tryb Doorstop external-folder (opcjonalny) | S |
| Minecraft: instancje, Fabric/Quilt meta, Modrinth API (wyszukiwanie, aktualizacje zbiorcze), `.mrpack` import | L |
| Eksport/import profilu (kod/plik) | S |
| Epic (manifesty) + Xbox content-folder w `detect` | S |

### Faza 3 — Bethesda i pozostałe

| Zadanie | Rozmiar |
|---|---|
| FOMOD (parser, sesja, UI kreatora, zapamiętane odpowiedzi) | L |
| Bethesda: nagłówki pluginów, writery wszystkich formatów, walidacja mastrów/ESL/medium, INI z kopią, Script Extender + wersje | L |
| Nexus: klucz API, `nxm://`, pobieranie premium/darmowe, `updated.json`, md5_search, liczniki limitów | M |
| Stardew (SMAPI `--mods-path`, manifesty, przechwytywanie configów) | S |
| RimWorld (About.xml, ModsConfig.xml, sortowanie topologiczne, Warsztat tylko-odczyt) | M |
| BG3 (czytnik LSPK/meta.lsx, modsettings.lsx) | M |
| Cyberpunk 2077 (typy, modlist.txt, REDmod deploy za zgodą) | M |
| Wiedźmin 3 (mods.settings, konflikty `.ws`, filelisty menu) | M |
| Doom (launch-args, wykrywanie IWAD) | S |
| GoldSrc/Source, Mount & Blade (Warband/Bannerlord), GTA SA/IV/V — definicje „tylko układ” | M |
| OpenMW (`openmw.cfg`, external-folder) | S |
| CurseForge (klucz użytkownika, `allowModDistribution`, manifest modpacka) | M |
| GitHub Releases dla frameworków | S |

### Faza 4 — szlif

Konflikty wewnątrz archiwów (BSA/BA2/.archive/.pak — tylko listing), opcjonalna integracja LOOT, lokalne zapisy/INI per profil, podpisane aktualizacje definicji gier, Linux/Proton (jeśli launcher kiedyś tam trafi).

**Łącznie**: MVP ≈ 2–3 miesiące, faza 2 ≈ 1–1,5 miesiąca, faza 3 ≈ 3–4 miesiące (jedna osoba).

---

## 8. Ryzyka i otwarte pytania

1. **Zmienność formatów** (BG3 po patchach, Starfield i kreacje, Cyberpunk `modlist.txt`, Thunderstore API eksperymentalne) — writery czytają nagłówki z plików zapisanych przez grę, a definicje są aktualizowalne bez nowej wersji exe.
2. **Identyfikatory sklepów** w przykładowych definicjach (GOG gameId, Epic AppName, UUID GustavDev, listy pluginów bazowych) — **wymagają weryfikacji na prawdziwych instalacjach** przed wydaniem; testy integracyjne powinny je sprawdzać.
3. **Hardlinki a aktualizacje sklepów** — Steam zwykle zastępuje pliki (bezpieczne), ale nie mamy gwarancji dla każdego launchera; dlatego read-only + hashe + archiwa źródłowe.
4. **Symlinki** wymagają Trybu dewelopera lub uprawnień admina — nie prosimy o podniesienie uprawnień; strategia po prostu nie jest dostępna.
5. **Rejestracja aplikacji w Nexus / klucz CurseForge** przy ewentualnej publicznej dystrybucji — decyzja właściciela projektu.
6. **Integracja z `port/go`** — kontrakt mostu WebView (nazwy komend, format zdarzeń, wątek UI) do uzgodnienia po ustabilizowaniu portu; ten dokument zakłada tylko, że launcher przekazuje `<PR>` i rejestruje komendy modułu.

---

## 9. Źródła referencyjne (do weryfikacji przy implementacji)

Formaty i zachowania opisane na podstawie publicznej dokumentacji oraz obserwowalnych formatów plików narzędzi Vortex, Mod Organizer 2, r2modman i Limo (bez kopiowania ich kodu):

- Nexus Mods — limity API (strona pomocy): https://help.nexusmods.com/article/105-i-have-reached-a-daily-or-hourly-limit-api-requests-have-been-consumed-rate-limit-exceeded-what-does-this-mean
- Nexus Mods App — notatki o BG3 (modsettings.lsx po Patch 7, Script Extender, pułapki): https://nexus-mods.github.io/NexusMods.App/developers/games/0003-BaldursGate3
- bg3.wiki — instalacja modów: https://bg3.wiki/wiki/Modding:Installing_mods
- Modrinth API (dokumentacja oficjalna): https://docs.modrinth.com/ — wymóg User-Agent, limit 300/min, format `.mrpack`
- Thunderstore API: https://thunderstore.io/api/docs/
- CurseForge for Studios / Core API: https://docs.curseforge.com/
- GitHub REST API — releases i limity: https://docs.github.com/en/rest/releases
- FOMOD — schemat ModuleConfig.xsd (publiczny, używany przez Vortex/MO2)
- SMAPI — dokumentacja (`--mods-path`, manifest): https://stardewvalleywiki.com/Modding:Index
- BepInEx / UnityDoorstop — dokumentacja konfiguracji: https://docs.bepinex.dev/
- UESP — formaty plików Bethesdy (nagłówki TES3/TES4, plugins.txt)
- OpenMW — `openmw.cfg`: https://openmw.readthedocs.io/
- Cyberpunk 2077 modding wiki (układ folderów, REDmod): https://wiki.redmodding.org/
