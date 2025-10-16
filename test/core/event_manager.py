# core/event_manager.py
import weakref # Importujemy moduł do "magicznego atramentu"

class EventManager:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type, callback):
        """Subskrybuje na zdarzenie, używając słabej referencji."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        # Zamiast przechowywać callback bezpośrednio, przechowujemy słabą referencję do niego.
        # To pozwala, aby obiekt (np. GameCard) został usunięty z pamięci.
        self._listeners[event_type].append(weakref.WeakMethod(callback))
        print(f"Zarejestrowano nowego słuchacza dla zdarzenia: {event_type}")

    def emit(self, event_type, *args, **kwargs):
        """Emituje zdarzenie, ignorując "martwych" subskrybentów."""
        if event_type in self._listeners:
            # Tworzymy nową listę tylko z żywymi słuchaczami, aby oczyścić "duchy"
            alive_listeners = []
            
            for weak_callback in self._listeners[event_type]:
                # "Wyciągamy" prawdziwą funkcję ze słabej referencji
                callback = weak_callback()
                
                if callback:  # Jeśli callback wciąż istnieje (obiekt nie został zniszczony)
                    alive_listeners.append(weak_callback)
                    try:
                        callback(*args, **kwargs)
                    except Exception as e:
                        print(f"Błąd podczas wywoływania callback dla zdarzenia {event_type}: {e}")
            
            # Zastępujemy starą listę nową, oczyszczoną listą
            self._listeners[event_type] = alive_listeners