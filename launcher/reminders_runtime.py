import logging
import time
import tkinter as tk
from tkinter import messagebox, ttk

from plyer import notification

from launcher.utils import save_config


def load_reminders(self):
    self.reminders = self.config.setdefault("reminders", [])
    self.reminders_listbox.delete(0, tk.END)
    for reminder in self.reminders:
        reminder_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reminder["time"]))
        self.reminders_listbox.insert(tk.END, f"{reminder_time} - {reminder['message']}")


def add_reminder(self):
    reminder_window = tk.Toplevel(self.root)
    reminder_window.title("Dodaj Przypomnienie")
    reminder_window.configure(bg="#1e1e1e")
    reminder_window.grab_set()
    reminder_window.resizable(False, False)

    ttk.Label(
        reminder_window,
        text="Data i Godzina (YYYY-MM-DD HH:MM:SS):",
        background="#1e1e1e",
        foreground="white",
    ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
    date_entry = ttk.Entry(reminder_window, width=20)
    date_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

    ttk.Label(
        reminder_window, text="Wiadomość:", background="#1e1e1e", foreground="white"
    ).grid(row=1, column=0, padx=10, pady=10, sticky="w")
    message_entry = ttk.Entry(reminder_window, width=40)
    message_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

    def save_reminder():
        date_str = date_entry.get().strip()
        message = message_entry.get().strip()
        try:
            reminder_time = time.mktime(time.strptime(date_str, "%Y-%m-%d %H:%M:%S"))
            if reminder_time < time.time():
                raise ValueError("Data i godzina muszą być w przyszłości.")
            self.reminders.append({"time": reminder_time, "message": message})
            save_config(self.config)
            self.reminders_listbox.insert(tk.END, f"{date_str} - {message}")
            reminder_window.destroy()
        except ValueError as ve:
            messagebox.showerror(
                "Błąd",
                f"Nieprawidłowy format daty/godziny lub czas w przeszłości.\n\nSzczegóły: {ve}",
            )

    save_btn = ttk.Button(reminder_window, text="Zapisz", command=save_reminder)
    save_btn.grid(row=2, column=0, columnspan=2, pady=10)


def create_reminders_page(self):
    for widget in self.reminders_frame.winfo_children():
        widget.destroy()

    header = ttk.Frame(self.reminders_frame)
    header.grid(row=0, column=0, sticky="ew")
    ttk.Label(header, text="Przypomnienia", font=("Helvetica", 14)).pack(pady=10)

    list_frame = ttk.Frame(self.reminders_frame)
    list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)

    self.reminders_listbox = tk.Listbox(list_frame)
    self.reminders_listbox.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.reminders_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    self.reminders_listbox.config(yscrollcommand=scrollbar.set)

    btn_frame = ttk.Frame(self.reminders_frame)
    btn_frame.grid(row=2, column=0, pady=10)

    add_btn = ttk.Button(btn_frame, text="Dodaj Przypomnienie", command=self.add_reminder)
    add_btn.pack(side="left", padx=5)

    delete_btn = ttk.Button(btn_frame, text="Usuń Przypomnienie", command=self.delete_reminder)
    delete_btn.pack(side="left", padx=5)

    self.load_reminders()


def delete_reminder(self):
    selected = self.reminders_listbox.curselection()
    if selected:
        index = selected[0]
        del self.reminders[index]
        self.reminders_listbox.delete(index)
        save_config(self.config)
    else:
        messagebox.showwarning("Błąd", "Nie wybrano żadnego przypomnienia.")


def monitor_reminders(self):
    while True:
        now = time.time()
        to_notify = [
            r for r in self.reminders if r["time"] <= now and not r.get("notified", False)
        ]
        for reminder in to_notify:
            notification.notify(
                title="Przypomnienie",
                message=reminder["message"],
                timeout=10,
            )
            reminder["notified"] = True
            save_config(self.config)
        time.sleep(60)


__all__ = [
    "load_reminders",
    "add_reminder",
    "create_reminders_page",
    "delete_reminder",
    "monitor_reminders",
]
