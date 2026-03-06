import json
import logging
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import requests


def _create_room_dialog(self):
    """Otwiera okno dialogowe do tworzenia nowego pokoju czatu (z opcjonalnym hasłem)."""
    if not self.chat_logged_in_user:
        messagebox.showwarning(
            "Czat",
            "Musisz być zalogowany, aby tworzyć pokoje czatu.",
            parent=self.chat_page_frame,
        )
        return

    room_dialog = tk.Toplevel(self.chat_page_frame)
    room_dialog.title("Utwórz Nowy Pokój")

    self.root.update_idletasks()  # Wymuś aktualizację głównego okna
    parent_x = self.root.winfo_rootx()
    parent_y = self.root.winfo_rooty()
    parent_width = self.root.winfo_width()
    parent_height = self.root.winfo_height()

    dialog_width = 510  # Możesz dostosować
    dialog_height = 200  # Możesz dostosować

    pos_x = parent_x + (parent_width // 2) - (dialog_width // 2)
    pos_y = parent_y + (parent_height // 2) - (dialog_height // 2)
    room_dialog.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")
    room_dialog.configure(bg=self.settings.get("background", "#1e1e1e"))
    room_dialog.grab_set()
    room_dialog.transient(self.chat_page_frame)
    room_dialog.resizable(False, False)

    ttk.Label(room_dialog, text="Nazwa Pokoju:").grid(
        row=0, column=0, padx=10, pady=5, sticky="w"
    )
    room_name_var = tk.StringVar()
    room_name_entry = ttk.Entry(room_dialog, textvariable=room_name_var, width=40)
    room_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    room_name_entry.focus_set()

    ttk.Label(room_dialog, text="Hasło (opcjonalnie):").grid(
        row=1, column=0, padx=10, pady=5, sticky="w"
    )
    room_password_var = tk.StringVar()
    room_password_entry = ttk.Entry(
        room_dialog, textvariable=room_password_var, show="*", width=40
    )
    room_password_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    # Checkbox "Pokaż hasło"
    show_password_var = tk.BooleanVar()
    show_password_checkbox = ttk.Checkbutton(
        room_dialog,
        text="Pokaż",
        variable=show_password_var,
        command=lambda: room_password_entry.config(
            show="" if show_password_var.get() else "*"
        ),
    )
    show_password_checkbox.grid(row=1, column=2, padx=5, pady=5, sticky="w")

    def create_room_action():
        name = room_name_var.get().strip()
        password = room_password_var.get()  # Pobieramy hasło jawnie (serwer zahashuje)

        if not name:
            messagebox.showwarning(
                "Błąd", "Nazwa pokoju nie może być pusta.", parent=room_dialog
            )
            return
        if not (3 <= len(name) <= 100):
            messagebox.showwarning(
                "Błąd",
                "Nazwa pokoju musi mieć od 3 do 100 znaków.",
                parent=room_dialog,
            )
            return

        # Wysłanie żądania do serwera w osobnym wątku
        def send_create_room_request():
            try:
                payload = {
                    "name": name,
                    "creator_id": self.chat_logged_in_user["user_id"],
                }
                if password:
                    payload["password"] = password  # Dodaj hasło do payloadu, jeśli podano

                response = requests.post(
                    f"{self.chat_server_url}/rooms", json=payload, timeout=10
                )
                response.raise_for_status()

                data = response.json()
                self.root.after(0, lambda: self._handle_create_room_success(data, room_dialog))

            except requests.exceptions.HTTPError as e:
                error_msg = "Nieznany błąd serwera."
                if e.response and e.response.status_code:
                    try:
                        server_error_data = e.response.json()
                        error_msg = server_error_data.get("error", error_msg)
                        if error_msg == "Room with this name already exists":
                            error_msg = f"Pokój o nazwie '{name}' już istnieje."
                    except json.JSONDecodeError:
                        pass
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Tworzenia Pokoju", error_msg, parent=room_dialog
                    ),
                )
                logging.error(f"Chat: Błąd tworzenia pokoju: {error_msg}")
            except requests.exceptions.RequestException as e:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Sieci",
                        f"Nie można połączyć się z serwerem czatu:\n{e}",
                        parent=room_dialog,
                    ),
                )
                logging.error(f"Chat: Błąd sieci podczas tworzenia pokoju: {e}")

        threading.Thread(target=send_create_room_request, daemon=True).start()

    button_frame = ttk.Frame(room_dialog)
    button_frame.grid(row=2, column=0, columnspan=3, pady=15)
    ttk.Button(button_frame, text="Utwórz", command=create_room_action).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(button_frame, text="Anuluj", command=room_dialog.destroy).pack(
        side=tk.LEFT, padx=5
    )


def _handle_create_room_success(self, data: dict, dialog_window: tk.Toplevel):
    """Obsługuje sukces utworzenia pokoju i odświeża UI."""
    if dialog_window.winfo_exists():
        dialog_window.destroy()

    messagebox.showinfo(
        "Sukces",
        f"Pokój '{data['room']['name']}' został pomyślnie utworzony.",
        parent=self.chat_page_frame,
    )
    logging.info(
        f"Chat: Pokój '{data['room']['name']}' utworzony i użytkownik dodany jako członek."
    )

    # Odśwież listę pokoi i użytkowników (to wywoła _filter_chat_users, która odświeża Treeview)
    self._fetch_chat_users()


def _handle_leave_room_success(self, success_message: str, room_id_left: int, user_id_left: int):
    messagebox.showinfo("Sukces", success_message, parent=self.chat_page_frame)
    logging.info(
        f"Chat: Użytkownik {user_id_left} pomyślnie opuścił pokój ID: {room_id_left} (odpowiedź HTTP)."
    )

    is_self_action = (
        self.chat_logged_in_user and user_id_left == self.chat_logged_in_user["user_id"]
    )

    if is_self_action:
        if self.sio and self.sio.connected:
            self.sio.emit("leave_specific_room", {"room_id": room_id_left})
            logging.debug(
                f"Chat: Wysłano 'leave_specific_room' (room: {room_id_left}) do serwera Socket.IO."
            )

        if self.active_chat_type == "room" and self.active_chat_partner_id == room_id_left:
            self.active_chat_partner_id = self.chat_dashboard_placeholder_id
            self.active_chat_type = "dashboard"
            self._current_chat_participants = {}
            logging.debug(
                f"Zmieniono aktywny czat na Dashboard po opuszczeniu pokoju {room_id_left}."
            )

    self.root.after(100, self._fetch_chat_users)

    if is_self_action and self.active_chat_type == "dashboard":
        logging.debug("Opuszczono aktywny pokój, odświeżanie widoku na dashboard...")

        self._display_chat_message("", "clear")
        if (
            hasattr(self, "chat_typing_indicator_label")
            and self.chat_typing_indicator_label.winfo_exists()
        ):
            self.chat_typing_indicator_label.config(text="")

        self.root.after(
            200,
            lambda: (
                self._show_chat_dashboard(),
                self._update_chat_ui_state(),
                self._show_or_hide_room_members_panel(show=False),
            ),
        )


def _join_room_dialog(self, room_id: int):
    """Wyświetla dialog dołączenia do pokoju, z opcją hasła, jeśli wymagane."""
    if not self.chat_logged_in_user:
        messagebox.showwarning(
            "Czat",
            "Musisz być zalogowany, aby dołączać do pokoi.",
            parent=self.chat_page_frame,
        )
        return

    room_data = self.chat_rooms.get(room_id)
    if not room_data:
        messagebox.showerror(
            "Błąd",
            "Nie znaleziono informacji o tym pokoju.",
            parent=self.chat_page_frame,
        )
        return

    room_name = room_data.get("name", f"Pokój ID {room_id}")
    requires_password = room_data.get("has_password", False)

    password_to_send = None
    if requires_password:
        password_to_send = simpledialog.askstring(
            "Dołącz do Chronionego Pokoju",
            f"Pokój '{room_name}' jest chroniony hasłem.\nPodaj hasło, aby dołączyć:",
            show="*",
            parent=self.chat_page_frame,
        )
        if password_to_send is None:
            return
        if not password_to_send:
            messagebox.showwarning(
                "Brak Hasła",
                "Hasło nie może być puste.",
                parent=self.chat_page_frame,
            )
            return
    else:
        if not messagebox.askyesno(
            "Dołącz do Pokoju",
            f"Czy na pewno chcesz dołączyć do pokoju '{room_name}'?",
            parent=self.chat_page_frame,
        ):
            return

    def send_join_request():
        try:
            payload = {"user_id": self.chat_logged_in_user["user_id"]}
            if password_to_send:
                payload["password"] = password_to_send

            response = requests.post(
                f"{self.chat_server_url}/rooms/{room_id}/members",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            join_data = response.json()
            self.root.after(
                0,
                lambda msg=join_data.get("message", f"Dołączono do pokoju '{room_name}'."), rid=room_id: self._handle_join_room_success(msg, rid),
            )

        except requests.exceptions.HTTPError as e:
            error_msg = "Błąd serwera."
            if e.response:
                try:
                    error_msg = e.response.json().get(
                        "error", f"Błąd serwera ({e.response.status_code})"
                    )
                except json.JSONDecodeError:
                    error_msg = f"Błąd serwera HTTP ({e.response.status_code})"
            messagebox.showerror(
                "Błąd Dołączania",
                f"Nie udało się dołączyć do pokoju '{room_name}':\n{error_msg}",
                parent=self.chat_page_frame,
            )
            logging.error(f"Chat: Błąd dołączania do pokoju {room_id}: {error_msg}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Błąd Sieci",
                f"Nie można połączyć się z serwerem czatu:\n{e}",
                parent=self.chat_page_frame,
            )
            logging.error(f"Chat: Błąd sieci podczas dołączania do pokoju {room_id}: {e}")

    threading.Thread(target=send_join_request, daemon=True).start()


def _handle_join_room_success(self, success_message: str, room_id_joined: int):
    """Obsługuje UI po pomyślnym dołączeniu do pokoju."""
    messagebox.showinfo("Sukces", success_message, parent=self.chat_page_frame)
    logging.info(f"Chat: Pomyślnie dołączono do pokoju ID: {room_id_joined}")

    if self.sio and self.sio.connected:
        self.sio.emit("join_specific_room", {"room_id": room_id_joined})

    self._fetch_chat_users()

    self.active_chat_partner_id = room_id_joined
    self.active_chat_type = "room"

    item_iid_to_select = f"{self.CHAT_PREFIX_ROOM}{room_id_joined}"
    if (
        hasattr(self, "chat_users_tree")
        and self.chat_users_tree.winfo_exists()
        and self.chat_users_tree.exists(item_iid_to_select)
    ):
        self.chat_users_tree.selection_set(item_iid_to_select)
        self.chat_users_tree.see(item_iid_to_select)
        self.chat_users_tree.focus(item_iid_to_select)

        self.root.after(
            100,
            lambda user_id=self.chat_logged_in_user["user_id"], r_id=room_id_joined: self._load_and_display_chat_history(
                user_id, r_id, chat_type="room"
            ),
        )
    else:
        self.root.after(
            100,
            lambda user_id=self.chat_logged_in_user["user_id"], r_id=room_id_joined: self._load_and_display_chat_history(
                user_id, r_id, chat_type="room"
            ),
        )


def _leave_room_action(self, room_id: int):
    """Obsługuje akcję opuszczenia pokoju przez użytkownika."""
    if not self.chat_logged_in_user:
        logging.warning("Chat: Próba opuszczenia pokoju bez zalogowanego użytkownika.")
        return

    room_data = self.chat_rooms.get(room_id)
    room_name_for_dialog = (
        room_data.get("name", f"Pokój ID {room_id}") if room_data else f"Pokój ID {room_id}"
    )

    if not messagebox.askyesno(
        "Opuść Pokój",
        f"Czy na pewno chcesz opuścić pokój '{room_name_for_dialog}'?",
        parent=self.chat_page_frame,
    ):
        return

    logging.info(
        f"Chat: Użytkownik {self.chat_logged_in_user['username']} (ID: {self.chat_logged_in_user['user_id']}) próbuje opuścić pokój ID: {room_id}"
    )

    def send_leave_request_thread():
        try:
            user_id_to_remove = self.chat_logged_in_user["user_id"]
            response = requests.delete(
                f"{self.chat_server_url}/rooms/{room_id}/members/{user_id_to_remove}",
                timeout=10,
            )
            response.raise_for_status()

            leave_data = response.json()
            self.root.after(
                0,
                lambda msg=leave_data.get("message", f"Opuszczono pokój '{room_name_for_dialog}'."), rid=room_id: self._handle_leave_room_success(msg, rid),
            )

        except requests.exceptions.HTTPError as e_http:
            error_message = "Błąd serwera podczas opuszczania pokoju."
            if e_http.response is not None:
                try:
                    error_detail = e_http.response.json().get(
                        "error", f"HTTP {e_http.response.status_code}"
                    )
                    error_message = f"Nie udało się opuścić pokoju '{room_name_for_dialog}':\n{error_detail}"
                except json.JSONDecodeError:
                    error_message = f"Nie udało się opuścić pokoju '{room_name_for_dialog}'. Błąd HTTP: {e_http.response.status_code}"
            else:
                error_message = f"Błąd połączenia podczas próby opuszczenia pokoju '{room_name_for_dialog}'."

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Błąd Opuszczania Pokoju",
                    error_message,
                    parent=self.chat_page_frame,
                ),
            )
            logging.error(
                f"Chat: Błąd opuszczania pokoju {room_id} dla użytkownika {self.chat_logged_in_user['user_id']}: {error_message}"
            )
        except requests.exceptions.RequestException as e_req:
            error_message = f"Błąd sieci podczas próby opuszczenia pokoju '{room_name_for_dialog}':\n{e_req}"
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Błąd Sieci", error_message, parent=self.chat_page_frame
                ),
            )
            logging.error(f"Chat: Błąd sieci podczas opuszczania pokoju {room_id}: {e_req}")
        except Exception as e_generic:
            error_message = f"Nieoczekiwany błąd podczas opuszczania pokoju '{room_name_for_dialog}':\n{e_generic}"
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Błąd Krytyczny", error_message, parent=self.chat_page_frame
                ),
            )
            logging.exception(
                f"Chat: Nieoczekiwany błąd opuszczania pokoju {room_id}: {e_generic}"
            )

    threading.Thread(target=send_leave_request_thread, daemon=True).start()


def _fetch_room_members_and_store(self, room_id: int):
    """
    [TYMCZASOWY STUB] W przyszłości ta metoda będzie pobierać i przechowywać
    listę członków danego pokoju. Na razie tylko loguje.
    """
    logging.debug(
        f"Chat: [STUB] _fetch_room_members_and_store wywołane dla pokoju ID: {room_id}"
    )
    if room_id in self.chat_rooms:
        self.chat_rooms[room_id].setdefault("members_details", [])


__all__ = [
    "_create_room_dialog",
    "_handle_create_room_success",
    "_handle_leave_room_success",
    "_join_room_dialog",
    "_handle_join_room_success",
    "_leave_room_action",
    "_fetch_room_members_and_store",
]
