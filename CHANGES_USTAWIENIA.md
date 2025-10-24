# Modernizacja Ustawień i Migracja Funkcji Profilu

## Podsumowanie zmian

Zrealizowano kompleksową modernizację sekcji ustawień oraz przeniesienie funkcjonalności profilu użytkownika do nowego, rozbudowanego interfejsu ustawień.

## Szczegółowe zmiany

### 1. Usunięcie zakładki "Profil" z nawigacji

- Usunięto wpis "Profil" z głównego menu bocznego aplikacji
- Usunięto `ProfilePlugin` z listy aktywnych pluginów
- Usunięto dedykowany widok `ProfileView` z nawigacji głównej

### 2. Nowy interfejs ustawień z zakładkami

Ustawienia zostały całkowicie przeprojektowane i podzielone na 4 główne sekcje w formie zakładek:

#### **Zakładka "Ogólne"**
- 🔔 **Powiadomienia**: Przełącznik powiadomień systemowych
- 📰 **Kanały RSS**: Zarządzanie źródłami newsów RSS z możliwością edycji listy kanałów

#### **Zakładka "Personalizacja"**
- 👤 **Profil Użytkownika**:
  - Wyświetlanie i zmiana avatara (z podglądem 100x100px)
  - Edycja nazwy użytkownika
  - Pole tekstowe Bio/opis profilu
  - Przycisk zapisywania zmian profilu

- 🎨 **Motyw i Wygląd**:
  - Wybór motywu z listy dostępnych
  - Wybór koloru akcentu (color picker)
  - **📤 Eksport motywu**: Zapisanie aktualnego motywu do pliku JSON
  - **📥 Import motywu**: Wczytanie własnego motywu z pliku JSON

#### **Zakładka "Dane"**
- 💾 **Kopie Zapasowe**:
  - Wyświetlanie aktualnej lokalizacji kopii zapasowych
  - **📁 Zmień lokalizację**: Dialog wyboru folderu dla backupów (CTk)
  - **➕ Utwórz backup**: Manualne tworzenie kopii zapasowej
  - **📤 Eksportuj backup**: Export kopii do wskazanej lokalizacji
  - **📥 Importuj backup**: Import i przywracanie kopii z zewnętrznego pliku
  - Lista dostępnych kopii zapasowych z datą, rozmiarem i przyciskiem przywracania

#### **Zakładka "Chmura"**
- ☁️ **Synchronizacja Chmury** (placeholders dla przyszłej implementacji):
  - **Google Drive**: Przełącznik włączania synchronizacji i przycisk autoryzacji
  - **GitHub**: Przełącznik synchronizacji, pole na token i zapis tokena
  - **Akcje**: Przyciski wyślij/pobierz/synchronizuj
  - Informacja o statusie rozwoju funkcji chmury

### 3. Rozbudowa BackupService

- **Dynamiczna lokalizacja backupów**: `BackupService` odczytuje lokalizację z ustawień (`settings.backup_location`)
- **Wsparcie dialogów CTk**: Wszystkie operacje na plikach używają natywnych dialogów `filedialog`
- **Export i import**: Możliwość eksportu backupów do dowolnej lokalizacji i importu z zewnętrznych źródeł

### 4. Rozbudowa ThemeService

- **Export motywu**: Metoda `set_custom_theme()` pozwala zapisać własny motyw
- **Import motywu**: Walidacja i wczytywanie motywów z plików JSON
- **Dostępność własnych motywów**: Importowane motywy są dodawane do listy dostępnych motywów

### 5. System migracji danych w DataManager

Dodano metodę `_run_migrations()` zapewniającą kompatybilność wsteczną:

- **Migracja v1**: Zachowanie istniejących danych profilu użytkownika (username, avatar, bio)
- **Migracja v2**: Dodanie nowych kluczy ustawień:
  - `backup_location` (domyślnie: "backups")
  - `gdrive_enabled` (domyślnie: false)
  - `github_enabled` (domyślnie: false)

System wersjonowania zapewnia, że dane użytkownika są automatycznie aktualizowane przy pierwszym uruchomieniu po zmianie.

### 6. Natychmiastowa aktualizacja UI przy zmianie avatara

- Event `profile_updated` jest emitowany przy zmianie avatara lub nazwy użytkownika
- Sidebar i HomeView automatycznie odświeżają avatar i nazwę użytkownika
- Wszystkie komponenty subskrybujące event `profile_updated` są natychmiast aktualizowane

### 7. Integracja z NotificationService

- Wszystkie operacje w ustawieniach pokazują powiadomienia systemowe:
  - Zapisanie profilu
  - Zapisanie kanałów RSS
  - Eksport/import motywu
  - Operacje na backupach
  - Operacje chmury (placeholders)

## Szczegóły techniczne

### Struktura danych w config.json

```json
{
  "_version": 2,
  "user": {
    "username": "Nazwa użytkownika",
    "avatar": "/ścieżka/do/avatar.png",
    "bio": "Opis profilu użytkownika",
    "achievements": {}
  },
  "settings": {
    "theme": "midnight",
    "accent": "#6366f1",
    "custom_theme": {...},
    "backup_location": "backups",
    "gdrive_enabled": false,
    "github_enabled": false,
    "github_token": "",
    "show_notifications": true,
    "rss_feeds": [...]
  }
}
```

### Format pliku motywu (JSON)

```json
{
  "name": "custom_theme",
  "base_color": "#0b1120",
  "background": "#0f172a",
  "surface": "#1e293b",
  "surface_alt": "#273449",
  "text": "#e2e8f0",
  "text_muted": "#94a3b8",
  "accent": "#6366f1"
}
```

## Korzyści

1. **Lepsza organizacja**: Wszystkie ustawienia w jednym miejscu, pogrupowane logicznie
2. **Więcej możliwości personalizacji**: Export/import motywów, wybór lokalizacji backupów
3. **Kompatybilność wsteczna**: Automatyczne migracje zapewniają zachowanie danych użytkownika
4. **Przygotowanie na przyszłość**: Sekcja chmury gotowa na implementację pełnej synchronizacji
5. **Lepsze UX**: Intuicyjne zakładki, natychmiastowa aktualizacja UI, powiadomienia o akcjach
6. **Elastyczność**: Możliwość zarządzania backupami z dowolnymi lokalizacjami

## Wsteczna kompatybilność

Aplikacja automatycznie wykrywa i migruje dane ze starszych wersji. Użytkownicy nie muszą podejmować żadnych działań - wszystkie dane profilu i ustawienia są zachowane podczas pierwszego uruchomienia po aktualizacji.

## Przyszłe rozszerzenia

Sekcja "Chmura" zawiera kompletną strukturę UI gotową do podłączenia rzeczywistych implementacji synchronizacji z:
- Google Drive API
- GitHub API
- Innymi usługami chmurowymi

---

**Data aktualizacji**: 2024-10-24  
**Wersja**: 2.2.0  
**Autor**: AI Development Team
