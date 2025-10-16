# plugins/reminders/view.py
import customtkinter as ctk
from datetime import datetime
import uuid

class RemindersView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self._setup_ui()

    def refresh_view(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        reminders_data = self.app_context.data_manager.get_plugin_data("reminders")
        reminders = sorted(reminders_data.get("reminders_list", []), key=lambda r: r.get("datetime"))

        if not reminders:
            ctk.CTkLabel(self.scrollable_frame, text="Brak zaplanowanych przypomnień.").pack(pady=20)
        
        for reminder in reminders:
            frame = ctk.CTkFrame(self.scrollable_frame)
            frame.pack(fill="x", pady=5)
            
            dt = datetime.fromisoformat(reminder.get("datetime"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            
            label_text = f"[{date_str}] - {reminder.get('message')}"
            ctk.CTkLabel(frame, text=label_text).pack(side="left", padx=10, pady=5)
            ctk.CTkButton(frame, text="Usuń", width=80, fg_color="red", hover_color="darkred",
                          command=lambda r_id=reminder.get("id"): self.delete_reminder(r_id)).pack(side="right", padx=10)

    def _setup_ui(self):
        # Sekcja dodawania
        add_frame = ctk.CTkFrame(self); add_frame.pack(fill="x", padx=10, pady=10)
        add_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(add_frame, text="Wiadomość:").grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5,0))
        self.msg_entry = ctk.CTkEntry(add_frame, placeholder_text="Np. Zagraj w nową grę"); self.msg_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)
        
        ctk.CTkLabel(add_frame, text="Data:").grid(row=2, column=0, sticky="w", padx=5, pady=(5,0))
        self.date_entry = ctk.CTkEntry(add_frame, placeholder_text="RRRR-MM-DD"); self.date_entry.grid(row=3, column=0, sticky="ew", padx=5, pady=(0,5))
        
        ctk.CTkLabel(add_frame, text="Godzina:").grid(row=2, column=1, sticky="w", padx=5, pady=(5,0))
        self.time_entry = ctk.CTkEntry(add_frame, placeholder_text="GG:MM"); self.time_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=(0,5))
        
        self.add_button = ctk.CTkButton(add_frame, text="Dodaj przypomnienie", command=self.add_reminder); self.add_button.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,5))

        # Sekcja listy
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Nadchodzące przypomnienia")
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def add_reminder(self):
        message = self.msg_entry.get(); date_str = self.date_entry.get(); time_str = self.time_entry.get()
        if not all([message, date_str, time_str]): return

        try:
            dt_str = f"{date_str}T{time_str}:00"
            dt_obj = datetime.fromisoformat(dt_str) # Sprawdzenie poprawności formatu
        except ValueError:
            print("Błędny format daty lub godziny. Użyj RRRR-MM-DD i GG:MM.")
            # TODO: Pokaż błąd w UI
            return

        new_reminder = {"id": str(uuid.uuid4()), "datetime": dt_obj.isoformat(), "message": message}
        
        data = self.app_context.data_manager.get_plugin_data("reminders")
        data.setdefault("reminders_list", []).append(new_reminder)
        self.app_context.data_manager.save_plugin_data("reminders", data)
        self.refresh_view()
        self.msg_entry.delete(0, 'end'); self.date_entry.delete(0, 'end'); self.time_entry.delete(0, 'end')

    def delete_reminder(self, reminder_id):
        data = self.app_context.data_manager.get_plugin_data("reminders")
        reminders = data.get("reminders_list", [])
        data["reminders_list"] = [r for r in reminders if r.get("id") != reminder_id]
        self.app_context.data_manager.save_plugin_data("reminders", data)
        self.refresh_view()