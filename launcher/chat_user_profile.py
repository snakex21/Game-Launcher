import json
import logging
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import requests


def _edit_chat_username_dialog(self):
    """
    Otwiera okno dialogowe do edycji nazwy użytkownika czatu.
    """
    if not self.chat_logged_in_user:
        messagebox.showwarning(
            "Edycja Nazwy",
            "Musisz być zalogowany do czatu, aby edytować swoją nazwę użytkownika.",
            parent=self.chat_page_frame,
        )
        return

    edit_dialog = tk.Toplevel(self.chat_page_frame)
    edit_dialog.title("Edytuj Nazwę Użytkownika")
    edit_dialog.configure(bg="#1e1e1e")
    edit_dialog.grab_set()
    edit_dialog.transient(self.chat_page_frame)
    edit_dialog.resizable(False, False)

    # Centrowanie okna
    self.root.update_idletasks()
    parent_x = self.chat_page_frame.winfo_rootx()
    parent_y = self.chat_page_frame.winfo_rooty()
    parent_w = self.chat_page_frame.winfo_width()
    parent_h = self.chat_page_frame.winfo_height()

    dialog_w = 350
    dialog_h = 150
    pos_x = parent_x + (parent_w // 2) - (dialog_w // 2)
    pos_y = parent_y + (parent_h // 2) - (dialog_h // 2)
    edit_dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")

    ttk.Label(
        edit_dialog,
        text=f"Obecna nazwa: {self.chat_logged_in_user['username']}",
        font=("Segoe UI", 9, "bold"),
    ).pack(pady=(10, 5))
    ttk.Label(edit_dialog, text="Nowa nazwa użytkownika:").pack(pady=(0, 5))

    new_username_var = tk.StringVar(value=self.chat_logged_in_user["username"])
    new_username_entry = ttk.Entry(edit_dialog, textvariable=new_username_var, width=40)
    new_username_entry.pack(padx=10, pady=5)
    new_username_entry.focus_set()

    def save_new_username():
        new_name = new_username_var.get().strip()
        if not new_name:
            messagebox.showwarning(
                "Błąd", "Nazwa użytkownika nie może być pusta.", parent=edit_dialog
            )
            return

        # Lokalna walidacja długości (powtórzona z serwera dla szybszej odpowiedzi)
        if not (3 <= len(new_name) <= 80):
            messagebox.showwarning(
                "Błąd",
                "Nazwa użytkownika musi mieć od 3 do 80 znaków.",
                parent=edit_dialog,
            )
            return

        if new_name == self.chat_logged_in_user["username"]:
            messagebox.showinfo(
                "Informacja",
                "Nowa nazwa jest taka sama jak obecna.",
                parent=edit_dialog,
            )
            edit_dialog.destroy()
            return

        # Wysłanie żądania do serwera w osobnym wątku
        def send_update_request():
            try:
                response = requests.put(
                    f"{self.chat_server_url}/user/{self.chat_logged_in_user['user_id']}",
                    json={"new_username": new_name},
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                self.root.after(
                    0,
                    lambda: self._handle_username_update_success(data, edit_dialog),
                )

            except requests.exceptions.HTTPError as e:
                error_msg = "Nieznany błąd serwera."
                if e.response and e.response.status_code:
                    try:
                        server_error_data = e.response.json()
                        error_msg = server_error_data.get("error", error_msg)
                        if error_msg == "Username already taken by another user":
                            error_msg = f"Nazwa użytkownika '{new_name}' jest już zajęta."
                        elif error_msg == "Username must be between 3 and 80 characters":
                            error_msg = "Nazwa użytkownika musi mieć od 3 do 80 znaków."
                    except json.JSONDecodeError:
                        pass
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Aktualizacji", error_msg, parent=edit_dialog
                    ),
                )
                logging.error(f"Chat: Błąd aktualizacji nazwy użytkownika: {error_msg}")
            except requests.exceptions.RequestException as e:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Sieci",
                        f"Nie można połączyć się z serwerem czatu:\n{e}",
                        parent=edit_dialog,
                    ),
                )
                logging.error(f"Chat: Błąd sieci podczas aktualizacji nazwy użytkownika: {e}")

        threading.Thread(target=send_update_request, daemon=True).start()

    button_frame = ttk.Frame(edit_dialog)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text="Zapisz", command=save_new_username).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(button_frame, text="Anuluj", command=edit_dialog.destroy).pack(
        side=tk.LEFT, padx=5
    )


def _handle_username_update_success(self, data: dict, dialog_window: tk.Toplevel):
    """Obsługuje sukces aktualizacji nazwy użytkownika w głównym wątku GUI."""
    if dialog_window.winfo_exists():
        dialog_window.destroy()

    new_username = data.get("new_username")
    if new_username:
        self.chat_logged_in_user["username"] = new_username  # Zaktualizuj lokalne dane
        messagebox.showinfo(
            "Sukces",
            f"Twoja nazwa użytkownika została zmieniona na '{new_username}'.",
            parent=self.chat_page_frame,
        )

        # Odśwież etykietę w UI
        self.chat_current_user_label.config(text=f"Zalogowano jako: {new_username}")

        # Odśwież listę użytkowników w Treeview, aby pokazać nową nazwę (jeśli to inni użytkownicy)
        self._fetch_chat_users()  # To pobierze zaktualizowaną listę z serwera
        logging.info(f"Chat: Nazwa użytkownika zaktualizowana w UI na '{new_username}'.")
    else:
        messagebox.showerror(
            "Błąd",
            "Serwer zwrócił sukces, ale brak nowej nazwy użytkownika.",
            parent=self.chat_page_frame,
        )


def _confirm_delete_chat_account(self):
    """
    Inicjuje proces usuwania konta czatu, wyświetlając prośbę o potwierdzenie
    i podanie hasła.
    """
    if not self.chat_logged_in_user:
        messagebox.showwarning(
            "Usuń Konto",
            "Musisz być zalogowany do czatu, aby usunąć konto.",
            parent=self.settings_page_frame,
        )
        return

    current_username = self.chat_logged_in_user.get("username", "Twoje konto")

    confirm_first_step = messagebox.askyesno(
        "Potwierdź Usunięcie Konta",
        f"Czy na pewno chcesz trwale usunąć konto użytkownika '{current_username}'?\n\n"
        "Tej operacji nie można cofnąć! Wszystkie Twoje dane związane z czatem "
        "(np. lista kontaktów, unikalny identyfikator użytkownika) zostaną usunięte z serwera.\n\n"
        "Wiadomości, które wysłałeś/odebrałeś, mogą pozostać w historii czatu innych użytkowników, "
        "ale będą powiązane z usuniętym kontem.\n\n"
        "Kontynuować?",
        icon="warning",
        parent=self.settings_page_frame,
    )

    if not confirm_first_step:
        return

    password_confirmation = simpledialog.askstring(
        "Potwierdź Hasło",
        "Aby potwierdzić usunięcie konta, podaj swoje hasło:",
        show="*",
        parent=self.settings_page_frame,
    )

    if not password_confirmation:
        messagebox.showwarning(
            "Usuwanie Anulowane",
            "Usuwanie konta zostało anulowane (brak podania hasła).",
            parent=self.settings_page_frame,
        )
        return

    logging.info(
        f"Chat: Wysyłanie żądania usunięcia konta dla użytkownika ID: {self.chat_logged_in_user['user_id']}."
    )

    def send_delete_request():
        try:
            response = requests.delete(
                f"{self.chat_server_url}/user/{self.chat_logged_in_user['user_id']}",
                json={"password": password_confirmation},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            self.root.after(0, lambda: self._handle_account_deletion_response(data, None))

        except requests.exceptions.HTTPError as e:
            error_msg = "Nieznany błąd serwera."
            if e.response and e.response.status_code:
                try:
                    server_error_data = e.response.json()
                    error_msg = server_error_data.get("error", error_msg)
                    if error_msg == "Incorrect password":
                        error_msg = "Podane hasło jest nieprawidłowe."
                except json.JSONDecodeError:
                    pass
            self.root.after(0, lambda: self._handle_account_deletion_response(None, error_msg))
            logging.error(f"Chat: Błąd usuwania konta: {error_msg}")
        except requests.exceptions.RequestException as e:
            self.root.after(
                0,
                lambda: self._handle_account_deletion_response(None, f"Błąd sieci: {e}"),
            )
            logging.error(f"Chat: Błąd sieci podczas usuwania konta: {e}")

    threading.Thread(target=send_delete_request, daemon=True).start()


def _handle_account_deletion_response(self, data: dict | None, error_message: str | None):
    """
    Obsługuje odpowiedź serwera po próbie usunięcia konta.
    Wywoływana w głównym wątku GUI.
    """
    if error_message:
        messagebox.showerror(
            "Błąd Usuwania Konta", error_message, parent=self.settings_page_frame
        )
        return

    if data and data.get("message") == "User account deleted successfully":
        messagebox.showinfo(
            "Sukces",
            "Twoje konto czatu zostało pomyślnie usunięte.",
            parent=self.settings_page_frame,
        )
        logging.info("Chat: Konto użytkownika pomyślnie usunięte, wylogowywanie.")
        self._chat_logout()
    else:
        messagebox.showerror(
            "Błąd Usuwania Konta",
            "Nieoczekiwana odpowiedź serwera podczas usuwania konta.",
            parent=self.settings_page_frame,
        )


__all__ = [
    "_edit_chat_username_dialog",
    "_handle_username_update_success",
    "_confirm_delete_chat_account",
    "_handle_account_deletion_response",
]
