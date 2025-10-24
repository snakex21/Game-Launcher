# Dostrajanie Wydajności Systemu Osiągnięć

## Parametry Konfiguracyjne

System osiągnięć został zoptymalizowany z możliwością dostrojenia parametrów wydajności.

### 1. Cache Duration (Czas trwania cache)

**Plik**: `app/services/achievement_service.py`  
**Parametr**: `self._check_cache_duration`  
**Domyślnie**: `2.0` sekund

```python
class AchievementService:
    def __init__(self, data_manager, event_bus):
        # ...
        self._check_cache_duration = 2.0  # ← TUTAJ
```

**Kiedy zmienić**:
- **Zwiększ** (np. do 5.0) jeśli:
  - Użytkownicy często przełączają się między widokami
  - Dane gier zmieniają się rzadko
  - Chcesz maksymalnej responsywności
  
- **Zmniejsz** (np. do 1.0) jeśli:
  - Chcesz bardziej "na żywo" aktualizacje
  - Dane często się zmieniają
  - Zależy Ci na aktualności ponad wydajnością

### 2. Batch Size (Rozmiar partii kart)

**Plik**: `app/plugins/achievements.py`  
**Parametr**: `batch_size` w `_load_achievement_cards_batch`  
**Domyślnie**: `8` kart (4 wiersze)

```python
def _load_achievement_cards_batch(self, catalog, progress, start_idx):
    batch_size = 8  # ← TUTAJ
```

**Kiedy zmienić**:
- **Zwiększ** (np. do 12 lub 16) jeśli:
  - Masz szybki komputer
  - Użytkownicy mają niewiele (<30) osiągnięć
  - Chcesz szybszego całkowitego czasu ładowania
  
- **Zmniejsz** (np. do 4 lub 6) jeśli:
  - Masz wolniejsze urządzenia
  - Użytkownicy mają dużo (>50) osiągnięć
  - Zauważasz "przeskakiwanie" podczas ładowania

### 3. Batch Delay (Opóźnienie między partiami)

**Plik**: `app/plugins/achievements.py`  
**Parametr**: delay w `self.after(...)` w `_load_achievement_cards_batch`  
**Domyślnie**: `5` milisekund

```python
if end_idx < len(catalog):
    self.after(5, lambda: ...)  # ← TUTAJ
```

**Kiedy zmienić**:
- **Zwiększ** (np. do 10-20ms) jeśli:
  - UI nadal się zacina
  - Chcesz widoczniejszej animacji ładowania
  - Inne procesy potrzebują czasu CPU
  
- **Zmniejsz** (np. do 1-2ms) jeśli:
  - Chcesz szybszego ładowania
  - Masz mocny komputer
  - Animacja jest zbyt wolna

### 4. Initial Load Delay (Początkowe opóźnienie)

**Plik**: `app/plugins/achievements.py`  
**Parametr**: delay w `self.after(...)` w `_load_achievements_async`  
**Domyślnie**: `10` milisekund

```python
def _load_achievements_async(self):
    # ...
    self.after(10, self._load_achievements)  # ← TUTAJ
```

**Kiedy zmienić**:
- **Zwiększ** (np. do 50ms) jeśli:
  - Chcesz dłużej widoczny wskaźnik ładowania
  - UI potrzebuje czasu na rendering
  
- **Zmniejsz** (np. do 1ms) jeśli:
  - Chcesz natychmiastowego ładowania
  - Wskaźnik ładowania miga za szybko

## Przykładowe Konfiguracje

### Dla Szybkich Komputerów

```python
# achievement_service.py
self._check_cache_duration = 3.0  # Dłuższy cache

# achievements.py
batch_size = 12  # Większe partie
self.after(2, ...)  # Krótsze opóźnienia
```

**Efekt**: Maksymalna responsywność, szybkie ładowanie

### Dla Wolniejszych Komputerów

```python
# achievement_service.py
self._check_cache_duration = 5.0  # Bardzo długi cache

# achievements.py
batch_size = 4  # Mniejsze partie
self.after(15, ...)  # Dłuższe opóźnienia
```

**Efekt**: Płynne działanie, bez zacinania UI

### Dla Animowanego Efektu

```python
# achievement_service.py
self._check_cache_duration = 2.0  # Standardowo

# achievements.py
batch_size = 2  # Małe partie (1 wiersz)
self.after(50, ...)  # Widoczne opóźnienie
```

**Efekt**: Ładne "wsuwanie się" kart od góry

### Dla Maksymalnej Wydajności

```python
# achievement_service.py
self._check_cache_duration = 10.0  # Długi cache

# achievements.py
batch_size = 100  # Załaduj wszystko od razu
self.after(0, ...)  # Brak opóźnień
```

**Efekt**: Jak najszybsze ładowanie (ale może zacinać UI)

## Monitoring Wydajności

Aby sprawdzić wydajność:

```python
import time
import logging

# Włącz debug logging
logging.basicConfig(level=logging.DEBUG)

# Zmierz czas
start = time.time()
achievement_service.check_and_update_progress(force=True)
print(f"Czas: {(time.time() - start)*1000:.2f}ms")
```

Oczekiwane czasy (benchmark):
- **check_and_update_progress**: 5-20ms (pierwsze wywołanie)
- **check_and_update_progress**: <1ms (z cache)
- **Ładowanie pojedynczej karty**: <2ms
- **Całkowite ładowanie widoku**: 50-200ms (w zależności od liczby osiągnięć)

## Diagnostyka Problemów

### Problem: Widok ładuje się wolno

**Przyczyny**:
1. Zbyt duży batch_size
2. Wolny dysk (częste zapisy)
3. Dużo osiągnięć (>50)

**Rozwiązania**:
- Zmniejsz batch_size do 4-6
- Zwiększ cache_duration do 5.0
- Zwiększ batch delay do 10-20ms

### Problem: UI się zacina podczas ładowania

**Przyczyny**:
1. Zbyt duży batch_size
2. Zbyt małe opóźnienia
3. Wolny komputer

**Rozwiązania**:
- Zmniejsz batch_size
- Zwiększ batch delay
- Sprawdź czy inne procesy nie obciążają CPU

### Problem: Wskaźnik ładowania nie jest widoczny

**Przyczyny**:
1. Zbyt małe initial delay
2. Bardzo szybkie ładowanie

**Rozwiązania**:
- Zwiększ initial load delay do 50ms
- To jest OK - znaczy że system jest szybki!

### Problem: Cache nie działa

**Przyczyny**:
1. force=True w wywołaniach
2. Cache duration zbyt krótki
3. Restartowanie serwisu

**Rozwiązania**:
- Użyj force=False
- Zwiększ cache_duration
- Sprawdź czy serwis nie jest tworzony wielokrotnie
