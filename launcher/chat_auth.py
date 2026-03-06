import json
import logging
import tkinter as tk
from tkinter import messagebox, ttk

import requests

from launcher.config_store import save_local_settings

def _chat_login(self):
        email = self.chat_email_var.get().strip()
        password = self.chat_password_var.get()

        if not email or not password:
            messagebox.showerror(
                "Błąd Logowania",
                "E-mail i hasło są wymagane.",
                parent=self.chat_page_frame,
            )
            return

        try:
            response = requests.post(
                f"{self.chat_server_url}/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            response.raise_for_status()  # To rzuci wyjątek dla statusów 4xx/5xx

            data = response.json()
            self.chat_logged_in_user = {
                "user_id": data["user_id"],
                "username": data["username"],
            }
            messagebox.showinfo(
                "Sukces",
                f"Zalogowano jako: {self.chat_logged_in_user['username']}",
                parent=self.chat_page_frame,
            )
            logging.info(
                f"Chat: Użytkownik {self.chat_logged_in_user['username']} zalogowany."
            )

            # Zapisz dane logowania TYLKO, jeśli "Zapamiętaj dane logowania" jest zaznaczone
            if self.chat_remember_me_var.get():
                self.local_settings["chat_email"] = email
                self.local_settings["chat_password"] = password
            else:  # Jeśli nie zaznaczono "Zapamiętaj", upewnij się, że nie ma ich w local_settings
                self.local_settings.pop("chat_email", None)
                self.local_settings.pop("chat_password", None)

            save_local_settings(self.local_settings)  # Zapisz stan local_settings

            self._connect_to_chat_server()  # Spróbuj połączyć się z SocketIO
            self._update_chat_ui_state()

        except requests.exceptions.HTTPError as e:
            error_msg = "Nieznany błąd logowania."
            if e.response and e.response.status_code:
                try:
                    server_error_data = e.response.json()
                    error_msg = server_error_data.get("error", "Nieznany błąd serwera.")
                    # Mapowanie kodów błędów na bardziej przyjazne komunikaty, jeśli potrzebne
                    if error_msg == "Invalid email format":
                        error_msg = "Nieprawidłowy format adresu e-mail."
                    elif error_msg == "Email not registered":
                        error_msg = "Podany adres e-mail nie jest zarejestrowany."
                    elif error_msg == "Incorrect password":
                        error_msg = "Nieprawidłowe hasło."
                except json.JSONDecodeError:
                    error_msg = f"Serwer zwrócił błąd HTTP {e.response.status_code}, ale bez JSONa."
            else:
                error_msg = f"Błąd połączenia z serwerem: {e}"

            messagebox.showerror(
                "Błąd Logowania", error_msg, parent=self.chat_page_frame
            )
            logging.error(f"Chat: Błąd logowania: {error_msg}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Błąd Sieci",
                f"Nie można połączyć się z serwerem czatu:\n{e}",
                parent=self.chat_page_frame,
            )
            logging.error(f"Chat: Błąd sieci podczas logowania: {e}")

def _on_remember_me_toggle(self):
        active_server_data = self._get_active_server_data()
        if not active_server_data:
            return

        remember_me = self.chat_remember_me_var.get()
        active_server_data["remember_credentials"] = remember_me

        if remember_me:  # Jeśli zaznaczono, zapisz aktualne dane z pól do tego serwera
            active_server_data.setdefault("credentials", {})
            active_server_data["credentials"]["email"] = self.chat_email_var.get()
            active_server_data["credentials"][
                "password"
            ] = self.chat_password_var.get()  # Nadal plain/zaszyfrowane
        else:  # Jeśli odznaczono, wyczyść dane dla tego serwera i odznacz auto-login
            active_server_data.get("credentials", {}).clear()
            active_server_data["auto_login_to_server"] = False
            self.chat_auto_login_var.set(False)

        self.local_settings["chat_servers"] = self.chat_servers_list
        save_local_settings(self.local_settings)
        logging.info(
            f"Chat: 'Zapamiętaj dane' dla serwera '{active_server_data.get('name')}' ustawiono na: {remember_me}"
        )

def _on_auto_login_toggle(self):
        active_server_data = self._get_active_server_data()
        if not active_server_data:
            return

        auto_login = self.chat_auto_login_var.get()
        active_server_data["auto_login_to_server"] = auto_login

        if (
            auto_login
        ):  # Jeśli włączono auto-login, upewnij się, że "zapamiętaj" jest też włączone
            active_server_data["remember_credentials"] = True
            self.chat_remember_me_var.set(True)
            # Upewnij się, że dane są zapisane, jeśli jeszcze nie były
            if not active_server_data.get("credentials", {}).get("email"):
                active_server_data.setdefault("credentials", {})
                active_server_data["credentials"]["email"] = self.chat_email_var.get()
                active_server_data["credentials"][
                    "password"
                ] = self.chat_password_var.get()

        self.local_settings["chat_servers"] = self.chat_servers_list
        save_local_settings(self.local_settings)
        logging.info(
            f"Chat: 'Auto-logowanie' dla serwera '{active_server_data.get('name')}' ustawiono na: {auto_login}"
        )

def _try_auto_chat_login(self):
        if self.chat_logged_in_user:
            return

        active_server_data = self._get_active_server_data()
        if not (
            active_server_data
            and active_server_data.get("auto_login_to_server", False)
            and active_server_data.get("remember_credentials", False)
        ):
            logging.debug(
                "Chat: Automatyczne logowanie wyłączone dla aktywnego serwera lub brak danych."
            )
            return

        creds = active_server_data.get("credentials", {})
        saved_email = creds.get("email")
        saved_password = creds.get("password")

        if saved_email and saved_password:
            logging.info(
                f"Chat: Próba automatycznego logowania do serwera '{active_server_data.get('name')}'..."
            )
            self.chat_email_var.set(saved_email)
            self.chat_password_var.set(saved_password)
            self.root.after_idle(self._chat_login)
        else:
            logging.debug(
                f"Chat: Brak zapisanego e-maila/hasła do automatycznego logowania dla serwera '{active_server_data.get('name')}'."
            )

def _chat_register(self):
        username = self.chat_username_var.get().strip()
        email = self.chat_email_var.get().strip()
        password = self.chat_password_var.get()

        if not username or not email or not password:
            messagebox.showerror(
                "Błąd Rejestracji",
                "Nazwa użytkownika, e-mail i hasło są wymagane.",
                parent=self.chat_page_frame,
            )
            return

        try:
            response = requests.post(
                f"{self.chat_server_url}/register",
                json={"username": username, "email": email, "password": password},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            messagebox.showinfo(
                "Sukces",
                f"Użytkownik {username} zarejestrowany. Możesz się teraz zalogować.",
                parent=self.chat_page_frame,
            )
            logging.info(f"Chat: Użytkownik {username} zarejestrowany.")

            # Po rejestracji, opcjonalnie automatycznie zaloguj lub zachęć do logowania
            # self.chat_email_var.set(email)
            # self.chat_password_var.set(password)
            # self._chat_login() # Automatyczne logowanie po rejestracji

        except requests.exceptions.HTTPError as e:
            error_msg = "Nieznany błąd rejestracji."
            if e.response and e.response.status_code:
                try:
                    server_error_data = e.response.json()
                    error_msg = server_error_data.get("error", "Nieznany błąd serwera.")
                    # Mapowanie kodów błędów na bardziej przyjazne komunikaty
                    if error_msg == "Invalid email format":
                        error_msg = "Nieprawidłowy format adresu e-mail."
                    elif error_msg == "Username already taken":
                        error_msg = "Nazwa użytkownika jest już zajęta."
                    elif error_msg == "Email already registered":
                        error_msg = "Podany adres e-mail jest już zarejestrowany."
                except json.JSONDecodeError:
                    error_msg = f"Serwer zwrócił błąd HTTP {e.response.status_code}, ale bez JSONa."
            else:
                error_msg = f"Błąd połączenia z serwerem: {e}"

            messagebox.showerror(
                "Błąd Rejestracji", error_msg, parent=self.chat_page_frame
            )
            logging.error(f"Chat: Błąd rejestracji: {error_msg}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Błąd Sieci",
                f"Nie można połączyć się z serwerem czatu:\n{e}",
                parent=self.chat_page_frame,
            )
            logging.error(f"Chat: Błąd sieci podczas rejestracji: {e}")

def _chat_logout(self):
        if self.sio and self.sio.connected:
            self.sio.disconnect()
            logging.info("Chat: Klient SocketIO rozłączony.")

        self.chat_logged_in_user = None
        self.chat_connected_to_server = False
        self.chat_authenticated = False
        # self.chat_users = {} # Możemy zostawić, żeby nie pobierać od nowa, jeśli user szybko się połączy
        # self.active_chat_partner_id = None # Zostawmy, żeby po ponownym zalogowaniu spróbował przywrócić
        # self.chat_messages = {} # Możemy zostawić

        # Usuwaj dane logowania z local_settings tylko, jeśli "Zapamiętaj mnie" jest ODZNACZONE.
        # Jeśli jest zaznaczone, zachowaj je.
        if not self.chat_remember_me_var.get():  # Sprawdź aktualny stan checkboxa
            self.local_settings.pop("chat_email", None)
            self.local_settings.pop("chat_password", None)
            logging.info(
                "Chat: Usunięto dane logowania z local_settings (Zapamiętaj mnie było odznaczone)."
            )
        else:
            logging.info(
                "Chat: Zachowano dane logowania w local_settings (Zapamiętaj mnie było zaznaczone)."
            )

        # Zawsze zapisuj stan checkboxów
        self.local_settings["chat_remember_me"] = self.chat_remember_me_var.get()
        self.local_settings["chat_auto_login"] = self.chat_auto_login_var.get()
        save_local_settings(self.local_settings)

        # messagebox.showinfo("Wylogowano", "Wylogowano z czatu.", parent=self.chat_page_frame) # Komunikat jest opcjonalny
        logging.info("Chat: Wylogowano użytkownika (stan UI zostanie zaktualizowany).")
        self._update_chat_ui_state()

def _update_chat_ui_state(self):
        """
        Aktualizuje, który panel (logowania czy czatu) jest widoczny,
        oraz status połączenia i początkowy widok czatu.
        """
        if (
            self.chat_logged_in_user
            and self.chat_connected_to_server
            and self.chat_authenticated
        ):
            self.chat_auth_panel.grid_remove()
            self.chat_main_panel.grid(row=0, column=0, sticky="nsew")

            if (
                hasattr(self, "chat_current_user_label")
                and self.chat_current_user_label.winfo_exists()
            ):
                username = self.chat_logged_in_user.get("username", "Nieznany")
                self.chat_current_user_label.config(text=f"Zalogowano jako: {username}")

            self.chat_connection_status_label.config(
                text="Status: Połączono", foreground="lightgreen"
            )

            # Po pomyślnym uwierzytelnieniu, pobierz dane użytkowników i pokoi.
            # Dopiero po tym można odświeżyć dashboard i listę kontaktów.
            self._fetch_chat_users()
            # Po `_fetch_chat_users` -> `_filter_chat_users`
            # A jeśli `active_chat_partner_id` jest `chat_dashboard_placeholder_id`, to odświeży dashboard.
            # To jest sekwencja, która powinna zadziałać.
            # `_fetch_chat_users` samo wywołuje `_filter_chat_users` po pobraniu danych.

            # Upewnij się, że dashboard jest wyświetlony, jeśli to pierwszy raz,
            # lub jeśli nie ma zapamiętanego ostatniego czatu.
            # `show_chat_page` ustawia `self.active_chat_partner_id` na dashboard.
            if self.active_chat_partner_id == self.chat_dashboard_placeholder_id:
                self.root.after(
                    50, self._show_chat_dashboard
                )  # Małe opóźnienie na pobranie użytkowników

            self._update_send_button_state()  # Upewnij się, że przycisk "Wyślij" jest aktywny

        else:  # Nie jesteśmy w pełni zalogowani/połączeni
            self.chat_main_panel.grid_remove()
            self.chat_auth_panel.grid(row=0, column=0, sticky="nsew")
            self.chat_connection_status_label.config(
                text="Status: Rozłączono", foreground="red"
            )
            if (
                hasattr(self, "chat_current_user_label")
                and self.chat_current_user_label.winfo_exists()
            ):
                self.chat_current_user_label.config(text="Zalogowano jako: Nieznany")
            # Wyczyść dane czatu na wypadek, gdyby były
            self.chat_users = {}
            self.chat_rooms = {}
            self.online_users.clear()
            if hasattr(self, "chat_users_tree"):
                self.chat_users_tree.delete(*self.chat_users_tree.get_children())
            self._update_send_button_state()

def _update_chat_ui_for_blocked_status(self):
        """Aktualizuje UI czatu (pole wprowadzania, komunikat) w zależności od statusu blokady aktywnego partnera."""
        if not (
            hasattr(self, "chat_input_entry") and self.chat_input_entry.winfo_exists()
        ):
            return

        # Inicjalizuj label blokady, jeśli nie istnieje
        if not hasattr(self, "chat_block_status_label"):
            self.chat_block_status_label = ttk.Label(
                self.chat_messages_panel,
                text="",
                font=("Segoe UI", 9, "italic"),
                foreground="orange",
                anchor="w",
            )
            # Celowo nie umieszczamy go w gridzie od razu

        is_currently_blocked = False
        if self.active_chat_type == "user" and self.active_chat_partner_id is not None:
            if self._is_user_blocked(self.active_chat_partner_id):
                is_currently_blocked = True

        if is_currently_blocked:
            self.chat_input_entry.config(state=tk.DISABLED)
            self.chat_input_var.set("")
            self.chat_block_status_label.config(
                text="Zablokowałeś tego użytkownika. Odblokuj, aby wysyłać wiadomości."
            )
            # Umieść label blokady nad polem input, a pod panelem wiadomości
            self.chat_block_status_label.grid(
                row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(2, 0)
            )
            # Reszta elementów przesuwa się w dół
            self.chat_input_entry.grid_configure(row=5)
            # Ramka podglądu cytowanej wiadomości (jeśli istnieje)
            if (
                hasattr(self, "chat_reply_preview_frame")
                and self.chat_reply_preview_frame.winfo_exists()
            ):
                self.chat_reply_preview_frame.grid_configure(row=6)
            # Ramka podglądu oczekującego załącznika (jeśli istnieje)
            if (
                hasattr(self, "chat_pending_attachment_frame")
                and self.chat_pending_attachment_frame.winfo_exists()
            ):
                self.chat_pending_attachment_frame.grid_configure(row=7)
            # Ramka przycisków akcji
            if (
                hasattr(self, "chat_action_buttons_frame")
                and self.chat_action_buttons_frame.winfo_exists()
            ):
                self.chat_action_buttons_frame.grid_configure(row=8)
            # Przycisk wylogowania
            # (zakładamy, że masz referencję do niego, np. self.chat_logout_button)
            if (
                hasattr(self, "chat_logout_button")
                and self.chat_logout_button.winfo_exists()
            ):  # Znajdź i przesuń przycisk wylogowania
                self.chat_logout_button.grid_configure(row=9)

        else:  # Użytkownik nie jest zablokowany lub to nie czat prywatny
            self.chat_block_status_label.grid_remove()  # Ukryj label blokady

            # Przywróć standardowe pozycje widgetów
            # Okno wiadomości powinno być zawsze na row=3, gdy nie ma statusu blokady
            # self.chat_message_display.grid_configure(row=3) # Nie ruszamy tego, bo jest zarządzane wyżej
            # self.messages_scrollbar.grid_configure(row=3)

            self.chat_input_entry.grid_configure(row=4)
            if (
                hasattr(self, "chat_reply_preview_frame")
                and self.chat_reply_preview_frame.winfo_exists()
            ):
                self.chat_reply_preview_frame.grid_configure(row=5)
            if (
                hasattr(self, "chat_pending_attachment_frame")
                and self.chat_pending_attachment_frame.winfo_exists()
            ):
                self.chat_pending_attachment_frame.grid_configure(
                    row=6
                )  # Miejsce na attachment
            if (
                hasattr(self, "chat_action_buttons_frame")
                and self.chat_action_buttons_frame.winfo_exists()
            ):
                self.chat_action_buttons_frame.grid_configure(row=7)
            if (
                hasattr(self, "chat_logout_button")
                and self.chat_logout_button.winfo_exists()
            ):
                self.chat_logout_button.grid_configure(row=8)

            # Upewnij się, że chat_input_entry jest aktywne, jeśli inne warunki na to pozwalają
            send_possible = (
                self.chat_logged_in_user
                and self.chat_connected_to_server
                and self.chat_authenticated
                and (self.active_chat_type == "user" or self.active_chat_type == "room")
                and self.active_chat_partner_id != self.chat_dashboard_placeholder_id
            )
            self.chat_input_entry.config(
                state=tk.NORMAL if send_possible else tk.DISABLED
            )

        # To zapewni, że ramka załącznika jest poprawnie ukryta, jeśli nie ma załącznika
        self._update_pending_attachment_ui()
        self._update_reply_preview_ui()  # I podgląd odpowiedzi też

        # Zawsze aktualizuj stan przycisku Wyślij
        self._update_send_button_state()

def _go_to_server_selection_from_chat_auth(self):
        """Przechodzi do strony wyboru serwera z panelu logowania czatu."""
        # Tutaj nie ma potrzeby rozłączania, bo i tak nie jesteśmy połączeni
        self.show_server_selection_page()

def _go_to_server_selection_from_chat_main(self):
        """Przechodzi do strony wyboru serwera z głównego panelu czatu, rozłączając obecne połączenie."""
        if self.sio and self.sio.connected:
            self._chat_logout()  # Rozłącz i zresetuj stan czatu
            # Daj chwilę na przetworzenie rozłączenia przed przejściem
            self.root.after(150, self.show_server_selection_page)
        else:
            self.show_server_selection_page()

__all__ = [
    "_chat_login",
    "_try_auto_chat_login",
    "_on_remember_me_toggle",
    "_on_auto_login_toggle",
    "_chat_register",
    "_chat_logout",
    "_update_chat_ui_state",
    "_update_chat_ui_for_blocked_status",
    "_go_to_server_selection_from_chat_auth",
    "_go_to_server_selection_from_chat_main",
]
