# core/reminder_service.py
import threading
import time
from datetime import datetime
import uuid

class ReminderService:
    def __init__(self, app_context):
        self.app_context = app_context
        self._stop_event = threading.Event()

    def start(self):
        """Uruchamia wątek sprawdzający przypomnienia w tle."""
        thread = threading.Thread(target=self._check_loop)
        thread.daemon = True
        thread.start()
        print("Serwis przypomnień został uruchomiony.")

    def stop(self):
        self._stop_event.set()

    def _check_loop(self):
        """Nieskończona pętla, która co 30 sekund sprawdza przypomnienia."""
        while not self._stop_event.is_set():
            now = datetime.now()
            reminders_data = self.app_context.data_manager.get_plugin_data("reminders")
            reminders_list = reminders_data.get("reminders_list", [])
            
            triggered_reminders_ids = []
            for reminder in reminders_list:
                try:
                    reminder_time = datetime.fromisoformat(reminder.get("datetime"))
                    if now >= reminder_time:
                        print(f"WYZWOLONO PRZYPOMNIENIE: {reminder.get('message')}")
                        self.app_context.event_manager.emit(
                            "reminder_triggered",
                            message=reminder.get("message")
                        )
                        triggered_reminders_ids.append(reminder.get("id"))
                except (ValueError, TypeError):
                    continue # Ignoruj błędnie sformatowane daty

            if triggered_reminders_ids:
                # Usuń wyzwolone przypomnienia z bazy danych
                updated_list = [r for r in reminders_list if r.get("id") not in triggered_reminders_ids]
                reminders_data["reminders_list"] = updated_list
                self.app_context.data_manager.save_plugin_data("reminders", reminders_data)

            time.sleep(30) # Sprawdzaj co 30 sekund