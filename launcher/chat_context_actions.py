import logging
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

import requests


def _on_room_member_list_right_click(self, event):
    """Wyświetla menu kontekstowe dla klikniętego członka na liście członków pokoju."""
    if not hasattr(self, "room_members_listbox") or not self.room_members_listbox.winfo_exists():
        return

    clicked_index = self.room_members_listbox.nearest(event.y)
    item_bbox = self.room_members_listbox.bbox(clicked_index)
    if not item_bbox:
        logging.debug("Kliknięto prawym na pustym miejscu panelu członków pokoju.")
        return

    # Pobierz ID i nazwę użytkownika bezpośrednio z przechowywanych danych, jeśli to możliwe.
    # Zakładamy, że _load_and_display_room_members przechowuje listę słowników {'id': ..., 'username': ...}
    # w self._current_room_members_details (trzeba będzie to dodać).
    # Na razie, jeśli to nie jest dostępne, użyjemy starej metody parsowania.

    target_user_id = None
    username_from_list = ""

    # Bezpieczne pobranie aktualnie wybranego pokoju (potrzebne do sprawdzenia creator_id)
    active_room_id = None
    if self.active_chat_type == "room" and self.active_chat_partner_id is not None:
        active_room_id = self.active_chat_partner_id

    current_room_data = self.chat_rooms.get(active_room_id) if active_room_id else None

    if (
        hasattr(self, "_last_loaded_room_members_details")
        and current_room_data
        and clicked_index >= 0
        and clicked_index < len(self._last_loaded_room_members_details)
    ):
        member_detail = self._last_loaded_room_members_details[clicked_index]
        target_user_id = member_detail.get("id")
        username_from_list = member_detail.get("username", "BłądNazwy")
        logging.debug(
            f"Pobrano dane członka z _last_loaded_room_members_details: ID={target_user_id}, Nick={username_from_list}"
        )
    else:  # Fallback na parsowanie, jeśli _last_loaded_room_members_details nie działa
        selected_display_text = self.room_members_listbox.get(clicked_index)
        username_from_list = selected_display_text[2:].strip()
        for uid, udata in self.chat_users.items():
            if udata.get("username") == username_from_list:
                target_user_id = uid
                break
        logging.debug(
            f"Fallback: Parsowano dane członka: ID={target_user_id}, Nick={username_from_list}"
        )

    if target_user_id is None:
        logging.warning(
            f"Nie można znaleźć ID dla użytkownika '{username_from_list}' z listy członków (kliknięto index: {clicked_index})."
        )
        return

    if not self.chat_logged_in_user:
        return

    context_menu_members = tk.Menu(
        self.room_members_listbox,
        tearoff=0,
        background="#2e2e2e",
        foreground="white",
    )
    is_self_clicked = target_user_id == self.chat_logged_in_user["user_id"]

    if is_self_clicked:
        context_menu_members.add_command(label=f"{username_from_list} (To Ty)", state=tk.DISABLED)
    else:
        context_menu_members.add_command(
            label=f"Wyślij prywatną wiadomość do {username_from_list}",
            command=lambda uid=target_user_id, uname=username_from_list: self._start_private_chat_from_room_context(uid, uname),
        )

    # Opcje administratora pokoju
    if (
        current_room_data
        and current_room_data.get("creator_id") == self.chat_logged_in_user["user_id"]
    ):
        if not is_self_clicked:  # Admin nie może wyrzucić sam siebie przez to menu
            context_menu_members.add_separator()
            context_menu_members.add_command(
                label=f"Usuń {username_from_list} z pokoju",
                command=lambda rid=active_room_id, uid_rem=target_user_id, uname_rem=username_from_list: self._admin_remove_user_from_room_action(rid, uid_rem, uname_rem),
            )

    if context_menu_members.index("end") is not None:
        context_menu_members.post(event.x_root, event.y_root)


def _confirm_self_leave_room(self, room_id: int, room_name: str):
    """Pyta o potwierdzenie i opcjonalnie nazwę pokoju przed opuszczeniem."""
    if not self.chat_logged_in_user:
        return

    is_creator_leaving = False
    room_data = self.chat_rooms.get(room_id)
    if room_data and room_data.get("creator_id") == self.chat_logged_in_user["user_id"]:
        is_creator_leaving = True

    confirmation_message = f"Czy na pewno chcesz opuścić pokój '{room_name}'?"
    if is_creator_leaving:
        confirmation_message += (
            "\n\n⚠️ Jesteś twórcą tego pokoju. "
            "Opuszczenie go spowoduje jego trwałe usunięcie dla wszystkich członków!"
        )

    confirm_first_step = messagebox.askyesno(
        "Opuść Pokój",
        confirmation_message,
        icon=("warning" if is_creator_leaving else "question"),
        parent=self.chat_page_frame,
    )
    if not confirm_first_step:
        return

    entered_name = simpledialog.askstring(
        "Potwierdź Nazwę Pokoju",
        f"Aby potwierdzić, wpisz pełną nazwę pokoju:\n'{room_name}'",
        parent=self.chat_page_frame,
    )

    if entered_name is None:
        return
    if entered_name.strip() != room_name:
        messagebox.showerror(
            "Błędna Nazwa",
            "Wpisana nazwa nie zgadza się z nazwą pokoju. Operacja anulowana.",
            parent=self.chat_page_frame,
        )
        return

    self._execute_self_leave_room(room_id, room_name)


def _execute_self_leave_room(self, room_id: int, room_name_for_log: str):
    """Wysyła żądanie opuszczenia pokoju przez zalogowanego użytkownika."""
    user_id_leaving = self.chat_logged_in_user["user_id"]

    def leave_room_thread():
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Initiator-User-ID": str(user_id_leaving),
            }
            payload = {}

            response = requests.delete(
                f"{self.chat_server_url}/rooms/{room_id}/members/{user_id_leaving}",
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            self.root.after(
                0,
                lambda rn=room_name_for_log: messagebox.showinfo(
                    "Opuszczono Pokój",
                    f"Pomyślnie opuściłeś pokój '{rn}'.",
                    parent=self.chat_page_frame,
                ),
            )
        except requests.exceptions.HTTPError as e_http:
            err_data = (
                e_http.response.json()
                if e_http.response and e_http.response.content
                else {}
            )
            error_message = err_data.get(
                "error", f"Błąd serwera (HTTP {e_http.response.status_code})"
            )
            self.root.after(
                0,
                lambda msg=error_message: messagebox.showerror(
                    "Błąd Opuszczania Pokoju", msg, parent=self.chat_page_frame
                ),
            )
        except requests.exceptions.RequestException as e_req:
            self.root.after(
                0,
                lambda err=e_req: messagebox.showerror(
                    "Błąd Sieci",
                    f"Błąd połączenia: {err}",
                    parent=self.chat_page_frame,
                ),
            )

    threading.Thread(target=leave_room_thread, daemon=True).start()


def _admin_remove_user_from_room_action(self, room_id: int, user_id_to_remove: int, username_to_remove: str):
    """Wywołuje akcję usunięcia użytkownika z pokoju przez admina."""
    if not self.chat_logged_in_user:
        return

    confirm_msg = (
        f"Czy na pewno chcesz usunąć użytkownika '{username_to_remove}' (ID: {user_id_to_remove})\n"
        f"z pokoju (ID: {room_id})?"
    )
    if messagebox.askyesno(
        "Potwierdź Usunięcie Członka",
        confirm_msg,
        icon="warning",
        parent=self.chat_page_frame,
    ):

        def remove_member_thread():
            try:
                payload = {"admin_id": self.chat_logged_in_user["user_id"]}
                response = requests.delete(
                    f"{self.chat_server_url}/rooms/{room_id}/members/{user_id_to_remove}",
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()

                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Usunięto Członka",
                        f"Użytkownik '{username_to_remove}' został pomyślnie usunięty z pokoju.",
                        parent=self.chat_page_frame,
                    ),
                )
                logging.info(
                    f"Admin (ID: {self.chat_logged_in_user['user_id']}) usunął użytkownika {user_id_to_remove} z pokoju {room_id}."
                )

                if self.active_chat_type == "room" and self.active_chat_partner_id == room_id:
                    self.root.after(100, self._load_and_display_room_members, room_id)

            except requests.exceptions.HTTPError as e_http:
                err_data = (
                    e_http.response.json()
                    if e_http.response and e_http.response.content
                    else {}
                )
                error_message = err_data.get(
                    "error", f"Błąd serwera (HTTP {e_http.response.status_code})"
                )
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Usuwania Członka",
                        f"Nie udało się usunąć użytkownika '{username_to_remove}':\n{error_message}",
                        parent=self.chat_page_frame,
                    ),
                )
                logging.error(
                    f"Błąd HTTP podczas usuwania członka {user_id_to_remove} z pokoju {room_id}: {error_message}"
                )
            except requests.exceptions.RequestException as e_req:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Błąd Sieci",
                        f"Błąd połączenia podczas próby usunięcia członka:\n{e_req}",
                        parent=self.chat_page_frame,
                    ),
                )
                logging.error(f"Błąd sieciowy podczas usuwania członka: {e_req}")

        threading.Thread(target=remove_member_thread, daemon=True).start()


def _start_private_chat_from_room_context(self, target_user_id: int, target_username: str):
    """Przełącza na czat prywatny z wybranym użytkownikiem."""
    logging.info(
        f"Próba rozpoczęcia czatu prywatnego z {target_username} (ID: {target_user_id}) z kontekstu pokoju."
    )

    if not self.chat_logged_in_user:
        return

    if target_user_id == self.chat_logged_in_user["user_id"]:
        messagebox.showinfo(
            "Informacja",
            "Nie możesz rozpocząć czatu sam ze sobą.",
            parent=self.chat_page_frame,
        )
        return

    target_user_iid = f"{self.CHAT_PREFIX_USER}{target_user_id}"
    if not (
        target_user_id in self.chat_users
        and hasattr(self, "chat_users_tree")
        and self.chat_users_tree.exists(target_user_iid)
    ):
        messagebox.showerror(
            "Błąd",
            f"Nie można znaleźć użytkownika '{target_username}' na głównej liście kontaktów.",
            parent=self.chat_page_frame,
        )
        self._fetch_chat_users()
        return

    self.active_chat_type = "user"
    self.active_chat_partner_id = target_user_id
    if self._room_members_panel_visible:
        try:
            self.chat_paned_window.forget(self.chat_room_members_panel)
        except tk.TclError:
            logging.warning(
                "TclError przy forget(self.chat_room_members_panel) w _start_private_chat_from_room_context"
            )
        self._room_members_panel_visible = False

    try:
        self.chat_users_tree.selection_set(target_user_iid)
        self.chat_users_tree.focus(target_user_iid)
        self.chat_users_tree.see(target_user_iid)
        self.chat_users_tree.event_generate("<<TreeviewSelect>>")

        if hasattr(self, "chat_active_partner_label"):
            self.chat_active_partner_label.config(text=f"Czat z: {target_username}")

    except tk.TclError as e:
        logging.error(
            f"Błąd TclError podczas programowego wybierania użytkownika '{target_username}': {e}"
        )
        messagebox.showerror(
            "Błąd Nawigacji Czatu",
            "Nie udało się przełączyć na czat prywatny.",
            parent=self.chat_page_frame,
        )
    except Exception as e:
        logging.exception(
            f"Nieoczekiwany błąd w _start_private_chat_from_room_context dla '{target_username}': {e}"
        )


def _on_chat_list_right_click(self, event):
    item_iid = self.chat_users_tree.identify_row(event.y)
    if not item_iid:
        return

    current_selection = self.chat_users_tree.selection()
    if not current_selection or current_selection[0] != item_iid:
        self.chat_users_tree.selection_set(item_iid)
    self.chat_users_tree.focus(item_iid)

    context_menu = tk.Menu(
        self.chat_page_frame, tearoff=0, background="#2e2e2e", foreground="white"
    )

    item_type = None
    if item_iid.startswith(self.CHAT_PREFIX_USER):
        item_type = "user"
        user_id_pure = int(item_iid[len(self.CHAT_PREFIX_USER) :])
        user_data = self.chat_users.get(user_id_pure)
        username = (
            user_data.get("username", f"ID_{user_id_pure}")
            if user_data
            else f"ID_{user_id_pure}"
        )

        context_menu.add_command(
            label="Rozpocznij czat prywatny",
            command=lambda iid=item_iid: self._initiate_chat_from_context_menu(iid),
        )

        if self.chat_logged_in_user and user_id_pure != self.chat_logged_in_user["user_id"]:
            if self._is_user_blocked(user_id_pure):
                context_menu.add_command(
                    label=f"🔓 Odblokuj {username}",
                    command=lambda uid=user_id_pure, uname=username: self._unblock_chat_user(uid, uname),
                )
            else:
                context_menu.add_command(
                    label=f"🚫 Zablokuj {username}",
                    command=lambda uid=user_id_pure, uname=username: self._block_chat_user(uid, uname),
                )
    elif item_iid.startswith(self.CHAT_PREFIX_ROOM):
        item_type = "room"
        room_id_pure = int(item_iid[len(self.CHAT_PREFIX_ROOM) :])
        room_data = self.chat_rooms.get(room_id_pure)

        if room_data:
            room_name_for_menu = room_data.get("name", f"Pokój ID {room_id_pure}")

            is_current_user_member = False
            if self.chat_logged_in_user:
                user_id = self.chat_logged_in_user["user_id"]
                if user_id in room_data.get("member_ids", []):
                    is_current_user_member = True

            if is_current_user_member:
                context_menu.add_command(
                    label=f"🚪 Opuść pokój '{room_name_for_menu}'",
                    command=lambda rid=room_id_pure, rname=room_name_for_menu: self._confirm_self_leave_room(rid, rname),
                )
            else:
                context_menu.add_command(
                    label=f"Dołącz do pokoju '{room_name_for_menu}'",
                    command=lambda rid=room_id_pure: self._join_room_dialog(rid),
                )

            context_menu.add_separator()
            context_menu.add_command(
                label=f"Otwórz czat pokoju '{room_name_for_menu}'",
                command=lambda iid_to_select=item_iid: self._initiate_chat_from_context_menu(iid_to_select),
            )

        else:
            context_menu.add_command(label="Błąd: Brak danych pokoju", state=tk.DISABLED)
    else:
        return

    if context_menu.index("end") is not None:
        context_menu.post(event.x_root, event.y_root)


def _initiate_chat_from_context_menu(self, item_iid_to_select: str):
    """
    Wywoływana z menu kontekstowego, aby "wejść" do czatu z użytkownikiem lub pokojem.
    Po prostu generuje event <<TreeviewSelect>>, aby _on_chat_user_select się wykonało.
    """
    if hasattr(self, "chat_users_tree") and self.chat_users_tree.winfo_exists():
        if self.chat_users_tree.exists(item_iid_to_select):
            current_selection = self.chat_users_tree.selection()
            if not current_selection or current_selection[0] != item_iid_to_select:
                self.chat_users_tree.selection_set(item_iid_to_select)
            self.chat_users_tree.focus(item_iid_to_select)
            self.chat_users_tree.see(item_iid_to_select)
            self.chat_users_tree.event_generate("<<TreeviewSelect>>")
        else:
            logging.warning(
                f"_initiate_chat_from_context_menu: Item IID '{item_iid_to_select}' nie istnieje w Treeview."
            )


__all__ = [
    "_on_room_member_list_right_click",
    "_confirm_self_leave_room",
    "_execute_self_leave_room",
    "_admin_remove_user_from_room_action",
    "_start_private_chat_from_room_context",
    "_on_chat_list_right_click",
    "_initiate_chat_from_context_menu",
]
