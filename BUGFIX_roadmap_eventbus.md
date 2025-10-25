# Bugfix: EventBus API Issue in Roadmap

## Problem

Roadmap plugin używał nieistniejącej metody `on()` do rejestracji event listenerów, co powodowało błąd:

```
AttributeError: 'EventBus' object has no attribute 'on'
```

## Błąd

```python
File "app/plugins/roadmap.py", line 106, in _setup_event_listeners
    self.context.event_bus.on("game_session_ended", self._on_game_session_ended)
    ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'EventBus' object has no attribute 'on'
```

## Rozwiązanie

EventBus używa metody `subscribe()` zamiast `on()`:

### Przed:
```python
def _setup_event_listeners(self) -> None:
    self.context.event_bus.on("game_session_ended", self._on_game_session_ended)
```

### Po:
```python
def _setup_event_listeners(self) -> None:
    self.context.event_bus.subscribe("game_session_ended", self._on_game_session_ended)
```

## Dodatkowa Naprawa

Dodano metodę `destroy()` do prawidłowego czyszczenia subskrypcji:

```python
def destroy(self) -> None:
    """Czyszczenie subskrypcji eventów."""
    self.context.event_bus.unsubscribe("game_session_ended", self._on_game_session_ended)
    super().destroy()
```

## API EventBus

Prawidłowe metody EventBus (`app/core/event_bus.py`):
- `subscribe(event: str, callback: Callable)` - Rejestruje listener
- `unsubscribe(event: str, callback: Callable)` - Usuwa listener
- `emit(event: str, **payload)` - Emituje event

## Rezultat

✓ Roadmap view ładuje się poprawnie  
✓ Event listeners są prawidłowo zarejestrowane  
✓ Nie ma memory leaków (cleanup w destroy)  
✓ Powiadomienia o celach roadmapy działają  

## Powiązane Pliki

- `app/plugins/roadmap.py` - Naprawiony kod
- `app/core/event_bus.py` - API EventBus
- `app/plugins/home.py` - Przykład prawidłowego użycia (linie 31-36, 526-535)

---

**Status**: ✅ Naprawiono  
**Data**: 2024-10-25  
**Wersja**: 3.0.0
