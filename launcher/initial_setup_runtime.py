import logging
import tkinter as tk
from tkinter import ttk

from launcher.utils import THEMES


def prompt_initial_setup_choice(self):
    logging.info("Brak skonfigurowanego użytkownika. Wyświetlanie dialogu początkowego.")

    dialog = tk.Toplevel(self.root)
    dialog.title("Witaj w Game Launcher!")
    active_theme_name = self.settings.get("theme", "Dark")
    all_themes = self.get_all_available_themes()
    theme_def = all_themes.get(active_theme_name, THEMES.get("Dark", {}))
    dialog.configure(bg=theme_def.get("background", "#1e1e1e"))

    self.root.update_idletasks()
    root_x = self.root.winfo_x()
    root_y = self.root.winfo_y()
    root_w = self.root.winfo_width()
    root_h = self.root.winfo_height()
    dialog_w = 400
    dialog_h = 200
    pos_x = root_x + (root_w // 2) - (dialog_w // 2)
    pos_y = root_y + (root_h // 2) - (dialog_h // 2)
    dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")

    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.transient(self.root)

    choice_made = tk.StringVar()

    def handle_choice(chosen_action):
        choice_made.set(chosen_action)
        dialog.destroy()

    ttk.Label(
        dialog, text="Nie wykryto konfiguracji użytkownika.", font=("Helvetica", 11)
    ).pack(pady=(15, 5))
    ttk.Label(dialog, text="Co chcesz zrobić?", font=("Helvetica", 11, "bold")).pack(
        pady=(5, 15)
    )

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=10, fill=tk.X, padx=20)
    btn_frame.columnconfigure((0, 1, 2), weight=1)

    ttk.Button(
        btn_frame,
        text="Wczytaj Backup",
        command=lambda: handle_choice("load_backup"),
    ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    ttk.Button(btn_frame, text="Nowy Użytkownik", command=lambda: handle_choice("new_user")).grid(
        row=0, column=1, padx=5, pady=5, sticky="ew"
    )
    ttk.Button(btn_frame, text="Wyjdź", command=lambda: handle_choice("exit")).grid(
        row=0, column=2, padx=5, pady=5, sticky="ew"
    )

    dialog.protocol("WM_DELETE_WINDOW", lambda: handle_choice("exit"))
    self.root.wait_window(dialog)

    user_choice = choice_made.get()
    if user_choice == "load_backup":
        logging.info("Użytkownik wybrał wczytanie backupu.")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        self.load_local_backup()

        if self.user.get("username"):
            self.root.after(250, self._post_init_heavy_jobs)
            logging.info("Backup wczytany. Kontynuacja normalnego startu.")
        else:
            logging.warning(
                "Wczytywanie backupu nie powiodło się lub backup nie zawierał danych użytkownika. Zamykam aplikację."
            )
            self.root.quit()

    elif user_choice == "new_user":
        logging.info("Użytkownik wybrał utworzenie nowego użytkownika.")
        self.ask_for_username()
        if self.user.get("username"):
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.refresh_ui()
            self.root.after(200, self.update_game_grid)
            self.root.after(250, self._post_init_heavy_jobs)
            logging.info("Nowy użytkownik stworzony. Kontynuacja normalnego startu.")
        else:
            logging.info(
                "Tworzenie nowego użytkownika anulowane lub brak nazwy. Zamykam aplikację."
            )
            self.root.quit()

    elif user_choice == "exit" or not user_choice:
        logging.info(
            "Użytkownik wybrał wyjście z dialogu początkowego. Zamykam aplikację."
        )
        self.root.quit()


__all__ = ["prompt_initial_setup_choice"]
