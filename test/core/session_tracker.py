# core/session_tracker.py
import threading
import datetime

class SessionTracker:
    def __init__(self, app_context):
        self.app_context = app_context

    def start_tracking(self, process, identifier):
        thread = threading.Thread(target=self._track_session, args=(process, identifier))
        thread.daemon = True
        thread.start()

    def _track_session(self, process, identifier):
        start_time = datetime.datetime.now()
        process.wait() 
        end_time = datetime.datetime.now()
        duration_seconds = int((end_time - start_time).total_seconds())

        # --- 6. SPRAWDŹ FLAGĘ PRZED EMITOWANIEM ZDARZEŃ ---
        if self.app_context.shutdown_event.is_set(): return

        # Poinformuj GameHandler, że proces się zakończył
        self.app_context.game_handler.on_session_ended_for_game(identifier)
        
        # Wyemituj zdarzenie z danymi sesji (dla okna podsumowania)
        self.app_context.event_manager.emit(
            "session_ended", 
            identifier=identifier, 
            duration_seconds=duration_seconds
        )