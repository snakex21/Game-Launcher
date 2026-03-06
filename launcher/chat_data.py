import logging
import tkinter as tk

import requests

def _load_and_display_room_members(self, room_id: int):
        """
        Wypełnia listbox self.room_members_listbox członkami danego pokoju.
        Teraz przechowuje pełne dane w self._last_loaded_room_members_details.
        """
        if (
            not hasattr(self, "room_members_listbox")
            or not self.room_members_listbox.winfo_exists()
        ):
            logging.error(
                "_load_and_display_room_members: Listbox członków pokoju nie istnieje."
            )
            return

        self.room_members_listbox.delete(0, tk.END)
        self._last_loaded_room_members_details = []  # Wyczyść poprzednie dane

        room_data = self.chat_rooms.get(room_id)
        if not room_data:
            logging.warning(f"Brak danych dla pokoju ID {room_id} w self.chat_rooms.")
            self.room_members_listbox.insert(tk.END, "(Błąd: Brak danych pokoju)")
            return

        member_ids = room_data.get("member_ids", [])
        if not member_ids:
            self.room_members_listbox.insert(tk.END, "(Brak członków)")
            return

        current_user_id = (
            self.chat_logged_in_user["user_id"] if self.chat_logged_in_user else None
        )
        room_creator_id = room_data.get("creator_id")  # Pobierz ID twórcy pokoju

        for user_id_member in member_ids:
            user_info = self.chat_users.get(user_id_member)
            username = (
                user_info.get("username", f"ID_{user_id_member}")
                if user_info
                else f"ID_{user_id_member}"
            )

            is_online = user_id_member in self.online_users
            is_self = user_id_member == current_user_id
            is_creator = user_id_member == room_creator_id  # Sprawdź, czy to twórca

            prefix = ""
            if is_self:
                prefix = "⭐ "  # Gwiazdka dla siebie (najwyższy priorytet wizualny)
            elif is_creator:
                prefix = "👑 "  # Korona dla twórcy pokoju (jeśli nie jest to self)
            elif is_online:
                prefix = "🟢 "
            else:
                prefix = "⚪ "

            display_entry_text = f"{prefix}{username}"

            # Kolejność sortowania: Ty, Twórca (jeśli nie Ty), Online, Offline, Alfabetycznie
            sort_key_1_self = 0 if is_self else 1
            sort_key_2_creator = 0 if is_creator else 1
            sort_key_3_online = 0 if is_online else 1

            self._last_loaded_room_members_details.append(
                {
                    "id": user_id_member,
                    "username": username,
                    "display_text": display_entry_text,
                    "_sort_keys": (
                        sort_key_1_self,
                        sort_key_2_creator,
                        sort_key_3_online,
                        username.lower(),
                    ),
                }
            )

        self._last_loaded_room_members_details.sort(key=lambda x: x["_sort_keys"])

        for member_detail in self._last_loaded_room_members_details:
            self.room_members_listbox.insert(tk.END, member_detail["display_text"])

        logging.info(
            f"Załadowano i posortowano {len(self._last_loaded_room_members_details)} członków dla pokoju ID {room_id}."
        )

def _show_or_hide_room_members_panel(self, show: bool):
        """Pokazuje lub ukrywa panel członków pokoju w PanedWindow."""
        if (
            not hasattr(self, "chat_paned_window")
            or not self.chat_paned_window.winfo_exists()
            or not hasattr(self, "chat_room_members_panel")
            or not self.chat_room_members_panel.winfo_exists()
        ):
            logging.warning(
                "_show_or_hide_room_members_panel: Wymagane widgety (PanedWindow/MembersPanel) nie istnieją."
            )
            return

        panel_already_visible = (
            self._room_members_panel_visible
        )  # lub sprawdź z self.chat_paned_window.panes()
        # Bezpieczniej jest użyć flagi, którą sami ustawiamy

        if show and not panel_already_visible:
            try:
                # Sprawdź, czy pane jest już dodane (na wszelki wypadek, jeśli _room_members_panel_visible jest False, a panel jest)
                # Ta część jest trochę bardziej skomplikowana, jeśli chcemy być super ostrożni.
                # Najprościej jest założyć, że _room_members_panel_visible jest poprawne.
                panes_in_window = self.chat_paned_window.panes()
                is_really_there = False
                for pane_widget_path in panes_in_window:
                    if (
                        self.chat_room_members_panel.winfo_pathname(
                            self.chat_room_members_panel.winfo_id()
                        )
                        == pane_widget_path
                    ):
                        is_really_there = True
                        break

                if not is_really_there:
                    self.chat_paned_window.add(
                        self.chat_room_members_panel, weight=1
                    )  # Ustaw wagę
                    logging.debug(
                        "Pokazano panel członków pokoju (dodano do PanedWindow)."
                    )
                else:
                    logging.debug(
                        "Panel członków pokoju jest już w PanedWindow, nie dodawano ponownie."
                    )
                self._room_members_panel_visible = True
            except tk.TclError as e_add:
                logging.error(f"TclError podczas dodawania panelu członków: {e_add}")
        elif not show and panel_already_visible:
            try:
                self.chat_paned_window.forget(self.chat_room_members_panel)
                logging.debug("Ukryto panel członków pokoju (usunięto z PanedWindow).")
                self._room_members_panel_visible = False
            except tk.TclError as e_forget:
                logging.warning(
                    f"TclError podczas ukrywania panelu członków (może już nie istniał w PanedWindow): {e_forget}"
                )
                self._room_members_panel_visible = (
                    False  # Na wszelki wypadek zresetuj flagę
                )

def _fetch_chat_users(self):
        """
        Pobiera listę wszystkich zarejestrowanych użytkowników czatu (dla prywatnych konwersacji)
        oraz listę dostępnych pokoi czatu (dla grup).
        """
        try:
            # 1. Pobierz użytkowników
            response_users = requests.get(f"{self.chat_server_url}/users", timeout=10)
            response_users.raise_for_status()
            users_data = response_users.json()
            self.chat_users = {user["id"]: user for user in users_data}
            logging.info(
                f"Chat: Pobrano {len(self.chat_users)} użytkowników: {self.chat_users}"
            )  # Dodatkowy log

            # 2. Pobierz pokoje czatu
            response_rooms = requests.get(f"{self.chat_server_url}/rooms", timeout=10)
            response_rooms.raise_for_status()
            rooms_data = response_rooms.json()
            self.chat_rooms = {room["id"]: room for room in rooms_data}
            logging.info(
                f"Chat: Pobrano {len(self.chat_rooms)} pokoi czatu: {self.chat_rooms}"
            )  # Dodatkowy log

            # 3. Zaktualizuj Treeview
            self.root.after(0, self._filter_chat_users)

        except requests.exceptions.RequestException as e:
            logging.error(f"Chat: Błąd pobierania listy użytkowników/pokoi: {e}")
            self.root.after(
                0,
                lambda: self._display_chat_message(
                    f"--- Błąd pobierania użytkowników/pokoi: {e} ---", "error"
                ),
            )
        except Exception as e_ex:  # Złap inne potencjalne błędy parsowania
            logging.exception(f"Chat: Nieoczekiwany błąd w _fetch_chat_users: {e_ex}")

def _clear_new_message_notification(
        self, partner_or_room_id, chat_type: str | None = None
    ):  # <-- Dodano chat_type
        """Usuwa wizualne powiadomienie o nowej wiadomości dla danego użytkownika/pokoju i resetuje licznik."""

        # Resetuj licznik nieprzeczytanych wiadomości dla tego partnera/pokoju
        # W przyszłości, jeśli `chat_type` będzie 'room', możemy użyć innego słownika
        # dla liczników nieprzeczytanych wiadomości grupowych. Na razie używamy tego samego.
        if partner_or_room_id is not None:  # Upewnij się, że ID nie jest None
            self.unread_messages_count.pop(
                partner_or_room_id, None
            )  # Użyj pop do usunięcia klucza, jeśli istnieje

        # Wizualne zaznaczenie na liście użytkowników/pokoi
        if hasattr(self, "chat_users_tree") and self.chat_users_tree.winfo_exists():
            item_iid_to_clear = None
            if chat_type == "user" and partner_or_room_id is not None:
                item_iid_to_clear = f"{self.CHAT_PREFIX_USER}{partner_or_room_id}"
            elif chat_type == "room" and partner_or_room_id is not None:
                item_iid_to_clear = f"{self.CHAT_PREFIX_ROOM}{partner_or_room_id}"

            if item_iid_to_clear and self.chat_users_tree.exists(item_iid_to_clear):
                current_tags = list(
                    self.chat_users_tree.item(item_iid_to_clear, "tags")
                )
                if "new_message_tag" in current_tags:
                    current_tags.remove("new_message_tag")
                    # Zaktualizuj również licznik w kolumnie (ustaw na pusty string)
                    current_values = list(
                        self.chat_users_tree.item(item_iid_to_clear, "values")
                    )
                    if len(current_values) == 2:  # Powinno być ("Nazwa", "Nowe")
                        current_values[1] = ""  # Wyczyść licznik "Nowe"
                        self.chat_users_tree.item(
                            item_iid_to_clear,
                            values=tuple(current_values),
                            tags=tuple(current_tags),
                        )
                    else:
                        self.chat_users_tree.item(
                            item_iid_to_clear, tags=tuple(current_tags)
                        )  # Fallback

                    logging.debug(
                        f"Chat: Usunięto tag 'new_message' dla IID: {item_iid_to_clear}"
                    )

__all__ = [
    "_load_and_display_room_members",
    "_show_or_hide_room_members_panel",
    "_fetch_chat_users",
    "_clear_new_message_notification",
]
