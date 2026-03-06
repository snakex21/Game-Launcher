import datetime
import json
import logging
import os
import threading
import tkinter as tk

import requests
from plyer import notification

def _display_active_chat_history(self, partner_id):
        """
        Wyczyść okno i wyrenderuj pełną historię czatu z partnerem.
        Potwierdzenia „przeczytane” wyślemy tylko przy pierwszym wywołaniu
        (czyli gdy użytkownik faktycznie otworzy czat).
        """
        self._rendered_message_widgets.clear()  # Wyczyść mapowanie widgetów przed każdym pełnym renderowaniem
        # --- obsługa None lub Dashboard ---
        if partner_id is None:
            self._display_chat_message("", "clear")
            self._display_chat_message(
                "Wybierz partnera czatu lub panel główny.", "system"
            )
            self.chat_active_partner_label.config(text="Panel Czatu")
            if hasattr(self, "chat_typing_indicator_label"):
                self.chat_typing_indicator_label.config(text="")
            self._rendered_chat_partner_id = None
            return

        if partner_id == self.chat_dashboard_placeholder_id:
            self.chat_active_partner_label.config(text="Panel Główny Czatu")
            if hasattr(self, "chat_typing_indicator_label"):
                self.chat_typing_indicator_label.config(text="")
            self._show_chat_dashboard()
            self._rendered_chat_partner_id = partner_id

            if hasattr(self, "chat_message_search_var"):
                self.chat_message_search_var.set("")
            return

        # --- Czyścimy i przygotowujemy dane ---
        first_display = self._rendered_chat_partner_id != partner_id
        self._display_chat_message("", "clear")
        self._last_chat_date_displayed_for_active = {}

        all_msgs = self.chat_messages.get(partner_id, [])
        # filtr na podstawie wyszukiwarki
        search_term = (
            getattr(self, "chat_message_search_var", tk.StringVar())
            .get()
            .lower()
            .strip()
        )
        if search_term:
            to_show = [
                m
                for m in all_msgs
                if search_term in (m.get("content") or "").lower()
                or search_term in (m.get("attachment_original_filename") or "").lower()
            ]
        else:
            to_show = all_msgs

        partner_uname = self.chat_users.get(partner_id, {}).get(
            "username", f"ID_{partner_id}"
        )
        if not to_show:
            if search_term:
                self._display_chat_message(
                    f"--- Brak wiadomości pasujących do '{search_term}' w czacie z {partner_uname} ---",
                    "system",
                )
            else:
                self._display_chat_message(
                    f"--- Brak historii czatu z {partner_uname} ---", "system"
                )
            self._rendered_chat_partner_id = partner_id
            return

        # sortujemy
        sorted_msgs = sorted(
            to_show, key=lambda m: datetime.datetime.fromisoformat(m["timestamp"])
        )

        # znajdujemy ostatnią swoją wiadomość, którą odbiorca przeczytał
        my_id = self.chat_logged_in_user["user_id"]
        last_read_id = None
        for m in sorted_msgs:
            if m.get("sender_id") == my_id and m.get("is_read_by_receiver"):
                last_read_id = m["id"]

        # nagłówek
        if not search_term:
            self._display_chat_message(
                f"--- Początek czatu z {partner_uname} ---", "system"
            )
        else:
            self._display_chat_message(
                f"--- Wyniki wyszukiwania '{search_term}' w czacie z {partner_uname} ---",
                "system",
            )

        # zbieramy ID wiadomości, które trzeba oznaczyć jako przeczytane
        message_ids_to_mark = []

        # pętla wyświetlająca każdą wiadomość
        for m in sorted_msgs:
            dt = datetime.datetime.fromisoformat(m["timestamp"])
            # wrzuc datówkę
            if self._last_chat_date_displayed_for_active.get(partner_id) != dt.date():
                self._display_chat_message("", "normal")
                self._display_chat_message(self._format_chat_date(dt.date()), "system")
                self._display_chat_message("", "normal")
                self._last_chat_date_displayed_for_active[partner_id] = dt.date()

            sid = m["sender_id"]
            ts = dt.strftime("%H:%M")
            # tekst i typ
            # Ważne: Jeśli `m['sender_id']` jest NULL (bo konto usunięto), to `self.chat_users.get(sid)` zwróci None.
            # Upewnij się, że wyświetlanie nadawcy jest bezpieczne.
            sender_obj = self.chat_users.get(sid)
            sender_name = (
                sender_obj.get("username") if sender_obj else "Usunięty Użytkownik"
            )  # Nowy bezpieczny tekst

            if sid == self.chat_logged_in_user["user_id"]:
                text = f"[{ts}] Ja: {m.get('content','')}"
                msg_type = "my_message"
            else:
                # Jeśli to wiadomość grupowa, wyświetl imię nadawcy
                if self.active_chat_type == "room":
                    text = f"[{ts}] {sender_name}: {m.get('content','')}"
                else:  # Prywatna wiadomość (już działało)
                    text = f"[{ts}] {sender_name}: {m.get('content','')}"
                msg_type = "other_message"

            # załącznik
            attach = None
            if m.get("attachment_server_filename"):
                attach = {
                    "server_filename": m["attachment_server_filename"],
                    "original_filename": m.get("attachment_original_filename"),
                    "attachment_mimetype": m.get("attachment_mimetype"),
                }

            # 4) Display the bubble
            self._display_chat_message(
                text,
                msg_type,
                attachment_data=attach,
                message_id=m["id"],
                is_read_by_receiver=(
                    msg_type == "my_message" and m["id"] == last_read_id
                ),
                sender_id_for_read_status_check=sid,
                replied_to_message_preview=m.get("replied_to_message_preview"),
                message_data=m,  # Przekazujemy pełne dane wiadomości
            )

        # stopka
        if not search_term:
            self._display_chat_message(
                f"--- Koniec czatu z {partner_uname} ---", "system"
            )

        if first_display:
            self.root.after(100, self._check_and_mark_read)

        # Przewiń na dół TYLKO jeśli nie mamy celu do przeskoczenia
        if self._jump_target_message_id is None:
            if (
                hasattr(self, "chat_message_display")
                and self.chat_message_display.winfo_exists()
            ):
                self.chat_message_display.see(tk.END)

        self._rendered_chat_partner_id = partner_id
        if hasattr(self, "_update_typing_indicator"):
            self._update_typing_indicator()

        # Po zakończeniu renderowania, przewiń do wiadomości docelowej, jeśli istnieje flaga
        if self._jump_target_message_id is not None:
            target_widget_to_jump_to = self._rendered_message_widgets.get(
                self._jump_target_message_id
            )
            if target_widget_to_jump_to and target_widget_to_jump_to.winfo_exists():
                # Przewiń do wiadomości
                self.chat_message_display.see(
                    self.chat_message_display.index(target_widget_to_jump_to)
                )
                # Podświetl na chwilę
                self._highlight_message_widget(target_widget_to_jump_to)
            self._jump_target_message_id = None

def _load_and_display_chat_history(
        self, current_user_id, partner_or_room_id, *, chat_type: str
    ):  # Zmieniono user1_id na current_user_id
        """
        Ładuje pierwszą stronę historii czatu (ostatnie N wiadomości)
        i wyświetla je w oknie.
        """
        self.chat_history_before = None
        self.chat_history_has_more = False
        self.chat_history_loading = False
        self._jump_target_message_id = None

        self._display_chat_message("", "clear")
        self._display_chat_message("--- Ładowanie historii czatu... ---", "system")

        def fetch_initial_page():
            try:
                url_path = ""
                params = {"limit": self.chat_page_size, "user_id": current_user_id}

                if chat_type == "user":
                    url_path = f"/messages/{current_user_id}/{partner_or_room_id}"
                elif chat_type == "room":
                    url_path = f"/rooms/{partner_or_room_id}/messages"
                else:
                    self.root.after(
                        0,
                        lambda: self._display_chat_message(
                            "--- Błąd: Nieznany typ chatu ---", "error"
                        ),
                    )
                    return

                logging.debug(
                    f"Chat: Pobieranie historii z {self.chat_server_url}{url_path} z parametrami: {params}"
                )
                resp = requests.get(
                    f"{self.chat_server_url}{url_path}", params=params, timeout=10
                )
                resp.raise_for_status()  # To rzuci wyjątek dla 4xx/5xx
                data = resp.json()

                self.chat_messages[partner_or_room_id] = data["messages"]
                self.chat_history_has_more = data.get("has_more", False)
                self.chat_history_before = data.get("next_before")

                self.root.after(
                    0,
                    lambda partner_id_cb=partner_or_room_id: self._display_active_chat_history(
                        partner_id_cb
                    ),
                )

            except requests.exceptions.HTTPError as http_err_local:
                error_content = "Nieznany błąd serwera HTTP."
                response_obj_for_lambda = http_err_local.response
                status_code_for_lambda = (
                    response_obj_for_lambda.status_code
                    if response_obj_for_lambda
                    else None
                )

                try:
                    error_content = (
                        response_obj_for_lambda.json().get("error", error_content)
                        if response_obj_for_lambda
                        else str(http_err_local)
                    )
                except json.JSONDecodeError:
                    error_content = str(http_err_local)

                logging.error(
                    f"Chat: Błąd HTTP ({status_code_for_lambda}) podczas pobierania historii: {error_content}"
                )

                if status_code_for_lambda == 403:
                    # Użytkownik nie jest członkiem pokoju
                    room_name_for_message = self.chat_rooms.get(
                        partner_or_room_id, {}
                    ).get("name", f"Pokój ID {partner_or_room_id}")
                    self.root.after(
                        0,
                        lambda rn=room_name_for_message, rid=partner_or_room_id: self._display_join_room_prompt(
                            rn, rid
                        ),
                    )
                else:  # Inne błędy HTTP
                    self.root.after(
                        0,
                        lambda err=error_content, code=status_code_for_lambda: self._display_chat_message(
                            f"--- Błąd ładowania historii ({code}): {err} ---", "error"
                        ),
                    )
            except Exception as general_e_local:  # Zmieniono nazwę zmiennej błędu
                logging.exception(
                    f"Chat: Nieoczekiwany błąd w fetch_initial_page dla historii: {general_e_local}"
                )
                self.root.after(
                    0,
                    lambda err_str_gen=str(general_e_local): self._display_chat_message(
                        f"--- Nieoczekiwany błąd: {err_str_gen} ---", "error"
                    ),
                )

        threading.Thread(target=fetch_initial_page, daemon=True).start()


def _fetch_more_chat_history(self):
        self.chat_history_loading = True
        limit = self.chat_page_size
        before = self.chat_history_before

        current_user_id_local = self.chat_logged_in_user["user_id"]
        partner_or_room_id_local = self.active_chat_partner_id
        chat_type_local = self.active_chat_type

        def thread_fn():
            try:
                url_path_more = ""
                params_more = {
                    "limit": limit,
                    "before": before,
                    "user_id": current_user_id_local,
                }

                if chat_type_local == "user":
                    url_path_more = (
                        f"/messages/{current_user_id_local}/{partner_or_room_id_local}"
                    )
                elif chat_type_local == "room":
                    url_path_more = f"/rooms/{partner_or_room_id_local}/messages"
                else:
                    self.root.after(
                        0,
                        lambda: self._display_chat_message(
                            "--- Błąd: Nieznany typ chatu (więcej) ---", "error"
                        ),
                    )
                    self.chat_history_loading = False
                    return

                logging.debug(
                    f"Chat: Pobieranie WIĘCEJ historii z {self.chat_server_url}{url_path_more} z parametrami: {params_more}"
                )
                resp = requests.get(
                    f"{self.chat_server_url}{url_path_more}",
                    params=params_more,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                old_messages = data["messages"]
                self.chat_history_has_more = data["has_more"]
                self.chat_history_before = data["next_before"]

                if old_messages:
                    self.chat_messages[partner_or_room_id_local] = (
                        old_messages + self.chat_messages[partner_or_room_id_local]
                    )
                    self._jump_target_message_id = old_messages[-1]["id"]
                    self.root.after(
                        0,
                        lambda: self._display_active_chat_history(
                            partner_or_room_id_local
                        ),
                    )
            except requests.exceptions.HTTPError as http_err_more:
                error_content_more = "Nieznany błąd serwera HTTP (więcej)."
                try:
                    error_content_more = (
                        http_err_more.response.json().get("error", error_content_more)
                        if http_err_more.response
                        else str(http_err_more)
                    )
                except json.JSONDecodeError:
                    error_content_more = str(http_err_more)
                logging.error(
                    f"Chat: Błąd HTTP ({http_err_more.response.status_code if http_err_more.response else 'N/A'}) podczas pobierania więcej historii: {error_content_more}"
                )
                self.root.after(
                    0,
                    lambda err=error_content_more, code=(
                        http_err_more.response.status_code
                        if http_err_more.response
                        else "N/A"
                    ): self._display_chat_message(
                        f"--- Błąd ładowania więcej historii ({code}): {err} ---",
                        "error",
                    ),
                )
            except Exception as e:
                logging.exception(f"Chat: Błąd w _fetch_more_chat_history: {e}")
            finally:
                self.chat_history_loading = False

        threading.Thread(target=thread_fn, daemon=True).start()


def _add_message_to_history(self, message_data: dict, is_sent_by_me: bool, message_context: str):
        """
        Dodaje wiadomość do historii self.chat_messages i, jeśli dotyczy
        aktywnego czatu, wyświetla ją natychmiast oraz wysyła potwierdzenie odczytu.
        `message_context` może być "private" lub "group".
        """
        sender_id = message_data.get("sender_id")
        msg_id = message_data.get("id")
        timestamp_str = message_data.get("timestamp")
        timestamp_dt = datetime.datetime.fromisoformat(timestamp_str)
        current_user_id = self.chat_logged_in_user["user_id"]

        # Załącznik
        attachment_server_filename = message_data.get("attachment_server_filename")
        attachment_original_filename = message_data.get("attachment_original_filename")
        attachment_mimetype = message_data.get("attachment_mimetype")

        # Cytowana wiadomość
        replied_to_preview = message_data.get("replied_to_message_preview")

        # Pełne dane wiadomości dla _display_chat_message
        full_message_data_for_display = message_data.copy()

        history_key = None  # ID partnera lub pokoju, do którego przypisujemy wiadomość w historii
        display_this_message_in_active_chat = False  # Czy wiadomość ma być od razu wyświetlona

        if message_context == "private":
            receiver_id = message_data.get("receiver_id")
            history_key = receiver_id if is_sent_by_me else sender_id
            if (
                history_key == self.active_chat_partner_id
                and self.active_chat_type == "user"
            ):
                display_this_message_in_active_chat = True
        elif message_context == "group":
            room_id = message_data.get("room_id")
            history_key = room_id
            if (
                history_key == self.active_chat_partner_id
                and self.active_chat_type == "room"
            ):
                display_this_message_in_active_chat = True
        else:  # Nieznany kontekst, nie rób nic (lub zaloguj błąd)
            logging.error(
                f"Chat: Nieznany kontekst wiadomości w _add_message_to_history: {message_context}"
            )
            return

        if history_key is None:
            logging.error(
                "Chat: Nie można ustalić klucza historii (partnera/pokoju) dla wiadomości."
            )
            return

        # Dodaj do pamięci podręcznej historii wiadomości
        self.chat_messages.setdefault(history_key, []).append(message_data)
        logging.debug(
            f"Chat: Dodano wiadomość ID {msg_id} do historii dla klucza '{history_key}'. Aktualny rozmiar: {len(self.chat_messages[history_key])}"
        )

        if display_this_message_in_active_chat:
            yview_info = (
                self.chat_message_display.yview()
                if hasattr(self, "chat_message_display")
                else (0, 1.0)
            )
            was_at_bottom = yview_info[1] >= 0.98

            active_partner_name = ""
            if self.active_chat_type == "user":
                active_partner_name = self.chat_users.get(history_key, {}).get(
                    "username", f"ID_{history_key}"
                )
            elif self.active_chat_type == "room":
                active_partner_name = self.chat_rooms.get(history_key, {}).get(
                    "name", f"Pokój ID_{history_key}"
                )

            # --- Usunięcie starych stopek (footerów) ---
            footer_base_text = (
                "--- Koniec czatu z "  # Nie dołączaj tutaj nazwy, bo może się zmienić
            )
            self.chat_message_display.config(state=tk.NORMAL)
            current_pos = "1.0"
            while True:
                idx = self.chat_message_display.search(
                    footer_base_text, current_pos, tk.END, nocase=True
                )
                if not idx:
                    break
                self.chat_message_display.delete(
                    f"{idx} linestart", f"{idx} lineend +1c"
                )
            self.chat_message_display.config(state=tk.DISABLED)

            # Sprawdzenie i dodanie nagłówka daty
            if (
                not hasattr(self, "_last_chat_date_displayed_for_active")
                or self._last_chat_date_displayed_for_active.get(history_key)
                != timestamp_dt.date()
            ):
                self._display_chat_message("", "normal")
                self._display_chat_message(
                    self._format_chat_date(timestamp_dt.date()), "system"
                )
                self._display_chat_message("", "normal")
                if not hasattr(self, "_last_chat_date_displayed_for_active"):
                    self._last_chat_date_displayed_for_active = {}
                self._last_chat_date_displayed_for_active[history_key] = (
                    timestamp_dt.date()
                )

            # Przygotowanie tekstu wiadomości
            time_str = timestamp_dt.strftime("%H:%M")
            display_text_bubble = ""
            msg_type_bubble = "other_message"  # Domyślnie

            sender_display_name = message_data.get("sender_username", f"ID_{sender_id}")

            if is_sent_by_me:
                display_text_bubble = (
                    f"[{time_str}] Ja: {message_data.get('content', '')}"
                )
                msg_type_bubble = "my_message"
            else:  # Wiadomość przychodząca
                if message_context == "private":
                    display_text_bubble = f"[{time_str}] {sender_display_name}: {message_data.get('content', '')}"
                elif message_context == "group":
                    # Dla wiadomości grupowych ZAWSZE pokazuj nazwę nadawcy
                    display_text_bubble = f"[{time_str}] {sender_display_name}: {message_data.get('content', '')}"
                msg_type_bubble = "other_message"

            # Przygotowanie danych załącznika
            attach_data_bubble = None
            if attachment_server_filename:
                attach_data_bubble = {
                    "server_filename": attachment_server_filename,
                    "original_filename": attachment_original_filename,
                    "attachment_mimetype": attachment_mimetype,
                }

            # Wyświetlenie dymka
            self._display_chat_message(
                display_text_bubble,
                msg_type_bubble,
                attachment_data=attach_data_bubble,
                message_id=msg_id,
                is_read_by_receiver=(
                    is_sent_by_me and message_data.get("is_read_by_receiver", False)
                ),
                sender_id_for_read_status_check=sender_id,
                replied_to_message_preview=replied_to_preview,
                message_data=full_message_data_for_display,
            )

            # Dodanie stopki
            self._display_chat_message(
                f"--- Koniec czatu z {active_partner_name} ---", "system"
            )

            if was_at_bottom:
                self.chat_message_display.see(tk.END)

            if (
                not is_sent_by_me and message_context == "private"
            ):  # Oznacz jako przeczytane tylko dla wiadomości prywatnych
                self.root.after(
                    200, self._check_and_mark_read
                )  # Z opóźnieniem, aby UI zdążyło się zrenderować
        else:  # Wiadomość nie dotyczy aktywnego czatu (tylko prywatne i grupowe od innych)
            if not is_sent_by_me:  # Tylko dla przychodzących
                # Użyj `history_key` do aktualizacji licznika (może to być `sender_id` dla prywatnych lub `room_id` dla grup)
                self.unread_messages_count[history_key] = (
                    self.unread_messages_count.get(history_key, 0) + 1
                )
                self._notify_new_chat_message(
                    history_key,
                    message_data.get("sender_username", ""),
                    message_data.get("content", ""),
                    message_context=message_context,
                )  # Przekaż message_context

def _notify_new_chat_message(
        self, source_id, sender_username, message_content, message_context: str
    ):  # Dodano message_context
        """
        Wyświetla systemowe powiadomienie o nowej wiadomości i oznacza użytkownika/pokój na liście.
        `source_id` to `sender_id` dla prywatnych lub `room_id` dla grupowych.
        """
        if (
            sender_username == self.chat_logged_in_user["username"]
            and source_id == self.chat_logged_in_user["user_id"]
        ):  # Ignoruj powiadomienia od siebie
            return

        notification_title = ""
        target_name_for_title = ""
        if message_context == "private":
            target_name_for_title = sender_username
            notification_title = f"Nowa wiadomość od {target_name_for_title}"
        elif message_context == "group":
            room_info = self.chat_rooms.get(source_id)  # source_id to room_id
            target_name_for_title = (
                room_info.get("name", f"Pokój ID_{source_id}")
                if room_info
                else f"Pokój ID_{source_id}"
            )
            notification_title = (
                f"Nowa wiadomość w '{target_name_for_title}' od {sender_username}"
            )
        else:
            notification_title = f"Nowa wiadomość od {sender_username}"  # Fallback

        # Opcjonalne sprawdzenie, czy nie pokazywać, jeśli okno jest aktywne i to ten czat
        if (
            self.root.winfo_exists()
            and self.root.winfo_ismapped()
            and self.current_frame == self.chat_page_frame
            and self.active_chat_partner_id == source_id
            and self.active_chat_type == message_context
        ):  # Sprawdź też typ
            logging.debug(
                f"Chat: Wiadomość odebrana dla aktywnego czatu ({message_context} {source_id}), pomijam powiadomienie systemowe."
            )
            # Jeśli to aktywny czat, _add_message_to_history już wyświetliło wiadomość
            # i zaktualizowało unread_count dla tej rozmowy/pokoju w Treeview.
            return

        # Powiadomienie systemowe
        try:
            notification.notify(
                title=notification_title,  # Użyj zaktualizowanego tytułu
                message=message_content,
                app_name="Game Launcher Chat",
                app_icon=(
                    os.path.abspath("icon.ico") if os.path.exists("icon.ico") else None
                ),
                timeout=5,
            )
        except Exception as e:
            logging.warning(
                f"Chat: Nie udało się wyświetlić powiadomienia systemowego: {e}"
            )

        # Wizualne zaznaczenie na liście użytkowników/pokoi - użyj source_id jako klucza
        self._filter_chat_users()

__all__ = [
    "_display_active_chat_history",
    "_load_and_display_chat_history",
    "_fetch_more_chat_history",
    "_add_message_to_history",
    "_notify_new_chat_message",
]
