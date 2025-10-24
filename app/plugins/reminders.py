"""Widok przypomnień."""
from __future__ import annotations

import logging
from datetime import datetime

import customtkinter as ctk

from .base import BasePlugin
from app.services.reminder_service import Reminder

logger = logging.getLogger(__name__)


class ReminderPlugin(BasePlugin):
    name = "Reminders"

    def register(self, context) -> None:  # type: ignore[no-untyped-def]
        logger.info("Zarejestrowano plugin Reminders")


class RemindersView(ctk.CTkFrame):
    def __init__(self, parent, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.context = context

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))

        title = ctk.CTkLabel(
            header,
            text="⏰ Przypomnienia",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left")

        add_btn = ctk.CTkButton(header, text="+ Dodaj", command=self._add_reminder)
        add_btn.pack(side="right")

        self.scrollable = ctk.CTkScrollableFrame(self)
        self.scrollable.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self._load_reminders()

    def _load_reminders(self) -> None:
        for child in self.scrollable.winfo_children():
            child.destroy()

        reminders = self.context.reminders.list()
        if not reminders:
            empty = ctk.CTkLabel(
                self.scrollable,
                text="Brak przypomnień",
                font=ctk.CTkFont(size=16),
                text_color="gray"
            )
            empty.pack(pady=60)
            return

        for reminder in reminders:
            card = ctk.CTkFrame(self.scrollable, corner_radius=10)
            card.pack(fill="x", padx=10, pady=5)

            title = ctk.CTkLabel(
                card,
                text=reminder.title,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            title.pack(fill="x", padx=15, pady=(12, 4))

            info = f"🕒 {reminder.remind_at} | Powtarzanie: {reminder.repeat}"
            ctk.CTkLabel(
                card,
                text=info,
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).pack(fill="x", padx=15)

            ctk.CTkLabel(
                card,
                text=reminder.message,
                font=ctk.CTkFont(size=12),
                wraplength=700,
                justify="left"
            ).pack(fill="x", padx=15, pady=10)

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(fill="x", padx=15, pady=(0, 12))

            toggle = ctk.CTkButton(
                btn_frame,
                text="✔ Zakończ" if not reminder.completed else "↺ Przywróć",
                command=lambda r=reminder: self._toggle(r),
                width=110,
            )
            toggle.pack(side="left", padx=5)

            delete = ctk.CTkButton(
                btn_frame,
                text="🗑 Usuń",
                command=lambda r=reminder: self._delete(r),
                width=80,
                fg_color="gray40",
                hover_color="gray30"
            )
            delete.pack(side="left", padx=5)

    def _add_reminder(self) -> None:
        dialog = AddReminderDialog(self, self.context)
        dialog.grab_set()

    def _toggle(self, reminder: Reminder) -> None:
        self.context.reminders.update(reminder.id, {"completed": not reminder.completed})
        self._load_reminders()

    def _delete(self, reminder: Reminder) -> None:
        self.context.reminders.remove(reminder.id)
        self._load_reminders()


class AddReminderDialog(ctk.CTkToplevel):
    def __init__(self, parent, context) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.context = context
        self.title("Nowe przypomnienie")
        self.geometry("500x520")
        self.resizable(True, True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Dodaj przypomnienie", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, pady=20)

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=20, sticky="ew")
        form.columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Tytuł:").grid(row=0, column=0, sticky="w", pady=(15, 5))
        self.entry_title = ctk.CTkEntry(form)
        self.entry_title.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Wiadomość:").grid(row=2, column=0, sticky="w", pady=(15, 5))
        self.entry_message = ctk.CTkTextbox(form, height=100)
        self.entry_message.grid(row=3, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Data i czas (YYYY-MM-DDTHH:MM):").grid(row=4, column=0, sticky="w", pady=(15, 5))
        self.entry_datetime = ctk.CTkEntry(form)
        self.entry_datetime.insert(0, datetime.now().strftime("%Y-%m-%dT%H:%M"))
        self.entry_datetime.grid(row=5, column=0, sticky="ew")

        ctk.CTkLabel(form, text="Powtarzanie:").grid(row=6, column=0, sticky="w", pady=(15, 5))
        self.option_repeat = ctk.CTkOptionMenu(form, values=["none", "daily", "weekly", "monthly"])
        self.option_repeat.grid(row=7, column=0, sticky="w")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, pady=20)

        ctk.CTkButton(buttons, text="Zapisz", command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(buttons, text="Anuluj", command=self.destroy, fg_color="gray40", hover_color="gray30").pack(side="left", padx=10)

    def _save(self) -> None:
        import uuid
        reminder = Reminder(
            id=str(uuid.uuid4()),
            title=self.entry_title.get().strip(),
            message=self.entry_message.get("1.0", "end").strip(),
            remind_at=self.entry_datetime.get().strip(),
            repeat=self.option_repeat.get(),
        )
        self.context.reminders.add(reminder)
        self.master._load_reminders()  # type: ignore[attr-defined]
        self.destroy()
