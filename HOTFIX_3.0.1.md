# 🔧 Hotfix 3.0.1 - EventBus API Fix

**Data**: 2024-10-25  
**Typ**: Critical Bug Fix  
**Dotyczy**: Game Launcher 3.0.0

## 🐛 Problem

Po wydaniu wersji 3.0.0, roadmapa nie ładowała się z powodu błędu w API EventBus:

```
AttributeError: 'EventBus' object has no attribute 'on'
```

### Przyczyna
Kod roadmapy używał nieistniejącej metody `event_bus.on()` zamiast prawidłowej `event_bus.subscribe()`.

### Lokalizacja
- Plik: `app/plugins/roadmap.py`
- Linia: 106 (`_setup_event_listeners`)

## ✅ Rozwiązanie

### Zmiana 1: Poprawna Rejestracja Eventu
```python
# ❌ Przed (nieprawidłowe)
self.context.event_bus.on("game_session_ended", self._on_game_session_ended)

# ✅ Po (prawidłowe)
self.context.event_bus.subscribe("game_session_ended", self._on_game_session_ended)
```

### Zmiana 2: Dodano Cleanup
```python
def destroy(self) -> None:
    """Czyszczenie subskrypcji eventów."""
    self.context.event_bus.unsubscribe("game_session_ended", self._on_game_session_ended)
    super().destroy()
```

## 📋 Prawidłowe API EventBus

### Dostępne Metody
| Metoda | Opis | Przykład |
|--------|------|----------|
| `subscribe(event, callback)` | Rejestruje listener | `bus.subscribe("game_added", handler)` |
| `unsubscribe(event, callback)` | Usuwa listener | `bus.unsubscribe("game_added", handler)` |
| `emit(event, **kwargs)` | Emituje event | `bus.emit("game_added", game_id="123")` |

### Pattern dla Widoków
```python
class MyView(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent)
        self.context = context
        # ✅ Użyj subscribe()
        self.context.event_bus.subscribe("event_name", self._handler)
        
    def _handler(self, **kwargs):
        # Obsługa eventu
        pass
        
    def destroy(self):
        # ✅ Zawsze czyść subskrypcje!
        self.context.event_bus.unsubscribe("event_name", self._handler)
        super().destroy()
```

## 🧪 Weryfikacja

### Test 1: Ładowanie Roadmapy
```
✅ Kliknij 🗺️ Roadmapa
✅ Widok ładuje się bez błędów
✅ Wszystkie 3 zakładki działają (📋 Lista, 📅 Kalendarz, 📦 Archiwum)
```

### Test 2: Event Listeners
```
✅ Zagraj w grę z roadmapy
✅ Osiągnij datę docelową
✅ Po zakończeniu sesji pojawi się powiadomienie
```

### Test 3: Memory Leaks
```
✅ Przełącz się na roadmapę
✅ Przełącz się na inny widok
✅ Powtórz kilka razy
✅ Brak memory leaków (event listeners są czyszczone)
```

## 📊 Impact

- **Krytyczność**: 🔴 Wysoka (roadmapa nie działała w ogóle)
- **Użytkownicy**: Wszyscy użytkownicy v3.0.0
- **Naprawa**: ✅ Natychmiastowa

## 📚 Dokumentacja

Zaktualizowane pliki:
- `CHANGELOG.md` - Dodano sekcję bugfixu
- `BUGFIX_roadmap_eventbus.md` - Szczegółowy opis problemu
- `HOTFIX_3.0.1.md` - Ten plik
- Pamięć (memory) - Zaktualizowano guidelines o EventBus API

## 🚀 Wdrożenie

### Dla Użytkowników
```bash
git pull
python main.py
```

### Dla Deweloperów
**ZAWSZE używaj:**
- ✅ `event_bus.subscribe()` do rejestracji
- ✅ `event_bus.unsubscribe()` w `destroy()`
- ❌ NIE używaj `event_bus.on()` - nie istnieje!

## 📝 Lessons Learned

1. **API Sprawdzanie**: Zawsze weryfikuj API przed użyciem
2. **Testy Integracyjne**: Ten błąd byłby złapany przez test integracyjny
3. **Cleanup Pattern**: Każdy view z event listeners potrzebuje `destroy()`
4. **Memory Management**: Brak cleanup prowadzi do memory leaków

## ✨ Status

✅ **Naprawiono**: Linia 106 w `app/plugins/roadmap.py`  
✅ **Dodano**: Metoda `destroy()` w `RoadmapView`  
✅ **Przetestowano**: Wszystkie funkcje roadmapy działają  
✅ **Dokumentacja**: Zaktualizowana  

---

**Game Launcher Team**  
*Quality matters!* 🎮
