import logging
import tkinter as tk

def _restore_last_chat_partner(self, partner_id_to_restore):
        """
        Próbuje przywrócić ostatnio otwarty czat, jeśli jesteśmy zalogowani.
        """
        if self.chat_logged_in_user and self.chat_authenticated:
            if self.active_chat_partner_id == self.chat_dashboard_placeholder_id:
                logging.debug(
                    f"Chat: Próba przywrócenia ostatniego partnera: {partner_id_to_restore}"
                )

                item_to_select_iid = None
                if partner_id_to_restore in self.chat_users:
                    item_to_select_iid = f"{self.CHAT_PREFIX_USER}{partner_id_to_restore}"
                elif partner_id_to_restore in self.chat_rooms:
                    item_to_select_iid = f"{self.CHAT_PREFIX_ROOM}{partner_id_to_restore}"

                if item_to_select_iid and self.chat_users_tree.exists(item_to_select_iid):
                    self.chat_users_tree.selection_set(item_to_select_iid)
                    self.chat_users_tree.see(item_to_select_iid)
                    self.chat_users_tree.focus(item_to_select_iid)
                    self.chat_users_tree.event_generate("<<TreeviewSelect>>")
                else:
                    logging.warning(
                        f"Nie można przywrócić ostatniego partnera '{partner_id_to_restore}', brak w Treeview lub danych."
                    )
                    self.chat_users_tree.selection_set(self.chat_dashboard_placeholder_id)
                    self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
                    self._show_chat_dashboard()
            else:
                logging.debug(
                    f"Dashboard nie jest aktywny, nie przywracam partnera ({self.active_chat_partner_id})."
                )
        else:
            logging.info(
                "Nie jesteśmy zalogowani, pomijanie przywracania ostatniego partnera."
            )

def _select_chat_partner_silently(self, partner_id: int):
        """
        Wewnętrzne: wybiera partnera czatu **bez czyszczenia okna**
        i bez dodatkowych mignięć.
        """
        if self.active_chat_partner_id != self.chat_dashboard_placeholder_id:
            return

        self.active_chat_partner_id = partner_id
        self.chat_users_tree.selection_set(str(partner_id))
        self.chat_users_tree.see(str(partner_id))
        self.chat_active_partner_label.config(
            text=f"Czat z: {self.chat_users.get(partner_id, {}).get('username', '...?')}"
        )
        self._load_and_display_chat_history(
            self.chat_logged_in_user["user_id"], partner_id
        )

def _check_and_mark_read(self):
        """
        Jeżeli masz otwarty chat z partnerem, jesteś na dole scrolla i
        jesteś **na karcie czatu**, to wyślij potwierdzenia odczytu.
        """
        # Tylko dla prywatnych czatów, nie grup
        if self.active_chat_type != "user":
            return
        active_partner_id = self.active_chat_partner_id
        # 1) Tylko gdy to nie dashboard i to faktyczny partner
        if (
            not active_partner_id
            or active_partner_id == self.chat_dashboard_placeholder_id
        ):
            return

        # 2) Tylko gdy jesteśmy **na stronie czatu**
        if getattr(self, "current_frame", None) != self.chat_page_frame:
            logging.debug("ChatReadCheck: Nie na stronie czatu, pomijam oznaczanie.")
            return

        # 3) Opcjonalnie: Tylko gdy okno aplikacji ma fokus (bardziej zaawansowane, na razie pomińmy)
        # if not self.root.focus_displayof():
        #     logging.debug("ChatReadCheck: Okno launchera nie ma fokusu, pomijam.")
        #     return

        # 4) Tylko gdy scroll jest na dole (lub blisko)
        if (
            hasattr(self, "chat_message_display")
            and self.chat_message_display.winfo_exists()
        ):
            # Sprawdź, czy scrollbar faktycznie jest potrzebny (czy zawartość jest większa niż widok)
            # To zapobiegnie oznaczaniu jako przeczytane, jeśli wszystkie wiadomości mieszczą się na ekranie
            # bez scrollowania, a użytkownik jeszcze nie doszedł na sam dół (chociaż w tym przypadku
            # warunek yview()[1] < 0.99 może nie być spełniony od razu)
            # Można by to rozbudować o sprawdzanie, czy ostatnia wiadomość jest w ogóle widoczna.
            # Na razie zostawiamy prostsze yview().

            # yview_info = self.chat_message_display.yview()
            # logging.debug(f"ChatReadCheck: yview info: {yview_info}")
            # if yview_info[1] < 0.99 and yview_info[1] < yview_info[0] + (yview_info[1]-yview_info[0]) + 0.01 : # Trochę tolerancji
            # (yview_info[1] - yview_info[0]) to widoczna część, yview_info[1] to dolna krawędź widocznej części.

            # Spróbujmy prościej: Jeśli dolna krawędź widocznego obszaru jest blisko końca całkowitej zawartości
            if (
                self.chat_message_display.yview()[1] < 0.95
            ):  # Użyjmy np. 0.95 zamiast 0.99 dla większej tolerancji
                logging.debug(
                    "ChatReadCheck: Scroll nie jest na dole, pomijam oznaczanie."
                )
                return
        else:  # Jeśli widget nie istnieje, nie rób nic
            return

        # W tym momencie faktycznie użytkownik powinien widzieć najnowsze wiadomości
        messages_from_partner_to_mark = []
        my_user_id = self.chat_logged_in_user["user_id"]

        # Przeglądamy wiadomości dla AKTYWNEGO partnera
        for msg_data in self.chat_messages.get(active_partner_id, []):
            # Interesują nas wiadomości WYSŁANE przez partnera DO NAS
            # i które JESZCZE nie zostały oznaczone jako przeczytane przez nas na serwerze
            if (
                msg_data.get("sender_id") == active_partner_id
                and msg_data.get("receiver_id") == my_user_id
                and not msg_data.get("is_read_by_receiver", False)
            ):  # `is_read_by_receiver` w tym kontekście znaczy "przeczytane przeze mnie"
                messages_from_partner_to_mark.append(msg_data.get("id"))

        if not messages_from_partner_to_mark:
            # logging.debug(f"ChatReadCheck: Brak nowych wiadomości od partnera {active_partner_id} do oznaczenia.")
            return

        if not self.sio or not self.sio.connected:
            logging.warning(
                "ChatReadCheck: Brak połączenia z SIO, nie można wysłać potwierdzeń."
            )
            return

        try:
            logging.info(
                f"ChatReadCheck: Wysyłanie mark_messages_as_read dla ID: {messages_from_partner_to_mark} (czytelnik: {my_user_id})"
            )
            self.sio.emit(
                "mark_messages_as_read",
                {"message_ids": messages_from_partner_to_mark, "reader_id": my_user_id},
            )

            # Optymistyczna aktualizacja lokalnego stanu - oznaczamy je jako "przeczytane przez odbiorcę (czyli nas)"
            # To jest ważne, aby przy następnym wywołaniu _check_and_mark_read nie wysyłać ich ponownie,
            # zanim serwer zdąży odpowiedzieć i zaktualizować nasz widok przez `message_read_update`
            # (które de facto nie jest używane do aktualizacji wskaźnika "oko" dla wiadomości OD PARTNERA,
            # bo "oko" jest tylko dla naszych wysłanych wiadomości).
            for msg_id_marked in messages_from_partner_to_mark:
                for i, msg_in_hist in enumerate(
                    self.chat_messages.get(active_partner_id, [])
                ):
                    if msg_in_hist.get("id") == msg_id_marked:
                        self.chat_messages[active_partner_id][i][
                            "is_read_by_receiver"
                        ] = True  # Oznaczamy, że my jako odbiorca przeczytaliśmy
                        break

            # Odświeżenie UI nie jest tu bezpośrednio potrzebne, bo nie dodajemy "oka" do wiadomości partnera.
            # Jednak jeśli usuwamy np. licznik nieprzeczytanych wiadomości z listy użytkowników, to tutaj
            # byłoby miejsce na odświeżenie tego licznika dla `active_partner_id`.
            # Na razie zakładamy, że licznik jest kasowany w `_on_chat_user_select`.

        except Exception as e:
            logging.error(
                f"ChatReadCheck: Błąd podczas wysyłania mark_messages_as_read: {e}"
            )

def _on_chat_message_search_change(self, *args):
        """Wywoływane przy zmianie tekstu w polu wyszukiwania wiadomości."""
        # Użyjemy prostego debounce, aby nie odświeżać przy każdej literze
        if hasattr(self, "_chat_msg_search_timer"):
            self.root.after_cancel(self._chat_msg_search_timer)

        # Jeśli pole wyszukiwania jest puste, a _last_chat_message_search_term też było puste,
        # nie rób nic, aby uniknąć niepotrzebnego odświeżania przy czyszczeniu pustego pola.
        current_search_term = self.chat_message_search_var.get().lower().strip()
        if not current_search_term and not getattr(
            self, "_last_chat_message_search_term", ""
        ):
            return

        self._last_chat_message_search_term = (
            current_search_term  # Zapamiętaj ostatni termin
        )

        self._chat_msg_search_timer = self.root.after(
            400, self._apply_chat_message_filter
        )

def _clear_chat_message_search(self):
        """Czyści pole wyszukiwania wiadomości i odświeża widok."""
        self.chat_message_search_var.set("")

def _apply_chat_message_filter(self):
        """
        Filtruje i ponownie wyświetla historię czatu na podstawie
        terminu w self.chat_message_search_var.
        """
        if (
            self.active_chat_partner_id is None
            or self.active_chat_partner_id == self.chat_dashboard_placeholder_id
        ):
            # Nie filtruj, jeśli nie ma aktywnego czatu z użytkownikiem lub jest dashboard
            self._display_active_chat_history(
                self.active_chat_partner_id
            )  # Wyświetl standardowo (np. dashboard)
            return

        logging.debug(
            f"Aplikowanie filtru wiadomości dla: {self.chat_message_search_var.get()}"
        )
        # Po prostu wywołaj _display_active_chat_history, która teraz będzie zawierać logikę filtrowania
        self._display_active_chat_history(self.active_chat_partner_id)

def _on_chat_user_select(self, event=None):
        selected_item_id_tuple = self.chat_users_tree.selection()

        if not selected_item_id_tuple:
            current_focus = self.chat_users_tree.focus()
            if current_focus:
                selected_item_id_tuple = (current_focus,)
            else:
                if (
                    self.active_chat_partner_id != self.chat_dashboard_placeholder_id
                    or self.active_chat_type != "dashboard"
                ):
                    self.active_chat_partner_id = self.chat_dashboard_placeholder_id
                    self.active_chat_type = "dashboard"
                    if (
                        hasattr(self, "chat_users_tree")
                        and self.chat_users_tree.winfo_exists()
                    ):
                        try:
                            self.chat_users_tree.selection_set(
                                self.chat_dashboard_placeholder_id
                            )
                            self.chat_users_tree.focus(
                                self.chat_dashboard_placeholder_id
                            )
                        except tk.TclError:
                            pass
                    self._display_active_chat_history(
                        None
                    )  # Celowo None, aby wyczyścić i pokazać dashboard
                    if hasattr(self, "chat_active_partner_label"):
                        self.chat_active_partner_label.config(text="Panel Główny Czatu")
                    self._show_chat_dashboard()
                    # Ukryj panel członków, jeśli dashboard jest aktywny
                    if self._room_members_panel_visible:
                        try:
                            self.chat_paned_window.forget(self.chat_room_members_panel)
                        except tk.TclError:
                            logging.warning(
                                "TclError przy forget(self.chat_room_members_panel) w _on_chat_user_select dla dashboardu"
                            )
                        self._room_members_panel_visible = False
                return

        selected_iid_str = selected_item_id_tuple[0]

        if selected_iid_str == self.chat_dashboard_placeholder_id:
            if (
                self.active_chat_partner_id == self.chat_dashboard_placeholder_id
                and self.active_chat_type == "dashboard"
            ):
                logging.debug("Chat: Dashboard already selected and active.")
                return

            self.active_chat_partner_id = self.chat_dashboard_placeholder_id
            self.active_chat_type = "dashboard"
            self._display_chat_message("", "clear")
            if hasattr(self, "chat_active_partner_label"):
                self.chat_active_partner_label.config(text="Panel Główny Czatu")
            self._show_chat_dashboard()
            self._cancel_reply_mode()
            self._last_open_chat_partner_id = self.chat_dashboard_placeholder_id
            if hasattr(self, "chat_typing_indicator_label"):
                self.chat_typing_indicator_label.config(text="")
            self._update_send_button_state()
            logging.debug(
                f"Chat: Switched to Dashboard view. Active partner: {self.active_chat_partner_id}, type: {self.active_chat_type}"
            )

            # Ukryj panel członków dla dashboardu
            if self._room_members_panel_visible:
                try:
                    self.chat_paned_window.forget(self.chat_room_members_panel)
                except tk.TclError:
                    logging.warning(
                        "TclError przy forget(self.chat_room_members_panel) w _on_chat_user_select dla dashboardu (2)"
                    )
                self._room_members_panel_visible = False
            self._show_or_hide_room_members_panel(show=False)
            return

        non_selectable_iids = [
            "section_users_header",
            "section_rooms_header",
            "no_users_results",
            "no_rooms_results",
            "no_users_results_not_logged_in",
        ]
        if selected_iid_str in non_selectable_iids:
            logging.debug(
                f"Chat: Clicked on a non-selectable header or placeholder: {selected_iid_str}. Ignoring."
            )
            if (
                hasattr(self, "chat_users_tree")
                and self.chat_users_tree.winfo_exists()
                and self.chat_users_tree.exists(self.chat_dashboard_placeholder_id)
            ):
                self.chat_users_tree.selection_set(self.chat_dashboard_placeholder_id)
                self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
            return

        try:
            chat_partner_id_pure = None
            chat_type_detected = None

            if selected_iid_str.startswith(self.CHAT_PREFIX_USER):
                chat_partner_id_pure = int(
                    selected_iid_str[len(self.CHAT_PREFIX_USER) :]
                )
                chat_type_detected = "user"
                self._show_or_hide_room_members_panel(show=False)
            elif selected_iid_str.startswith(self.CHAT_PREFIX_ROOM):
                chat_partner_id_pure = int(
                    selected_iid_str[len(self.CHAT_PREFIX_ROOM) :]
                )
                chat_type_detected = "room"
                self._show_or_hide_room_members_panel(show=True)
                if chat_partner_id_pure is not None:
                    self._load_and_display_room_members(chat_partner_id_pure)
            else:
                # Jeśli doszliśmy tutaj, to IID jest nieznany, co jest błędem.
                logging.error(
                    f"Chat: UNEXPECTED - Unrecognized selection IID '{selected_iid_str}' that was not a header or dashboard."
                )
                raise ValueError("Unrecognized chat item IID (post-checks).")

            # ... (reszta Twojej logiki z poprzedniej wersji, czyli od `if chat_partner_id_pure == self.chat_logged_in_user['user_id']...` w dół,
            #      pozostaje bez zmian, bo wydawała się już poprawna) ...

            if (
                chat_partner_id_pure == self.chat_logged_in_user["user_id"]
                and chat_type_detected == "user"
            ):
                self.root.after(
                    0,
                    lambda: self._display_chat_message(
                        "Nie możesz rozmawiać sam ze sobą!", "error"
                    ),
                )
                if self.active_chat_partner_id:
                    current_selection_iid = None
                    if self.active_chat_type == "user":
                        current_selection_iid = (
                            f"{self.CHAT_PREFIX_USER}{self.active_chat_partner_id}"
                        )
                    elif self.active_chat_type == "room":
                        current_selection_iid = (
                            f"{self.CHAT_PREFIX_ROOM}{self.active_chat_partner_id}"
                        )
                    else:
                        current_selection_iid = self.chat_dashboard_placeholder_id
                    if self.chat_users_tree.exists(current_selection_iid):
                        self.chat_users_tree.selection_set(current_selection_iid)
                return

            should_reload_history = (
                chat_partner_id_pure != self.active_chat_partner_id
                or chat_type_detected != self.active_chat_type
                or getattr(self, "_force_history_reload_for_partner", False)
            )

            if hasattr(self, "_force_history_reload_for_partner"):
                self._force_history_reload_for_partner = False

            self.active_chat_partner_id = chat_partner_id_pure
            self.active_chat_type = chat_type_detected
            self._last_active_chat_type_selected = chat_type_detected

            partner_display_name = ""
            if self.active_chat_type == "user":
                partner_display_name = self.chat_users.get(
                    self.active_chat_partner_id, {}
                ).get("username", f"Użytkownik ID_{self.active_chat_partner_id}")
                # self._update_chat_partner_details(self.active_chat_partner_id) # _update_chat_partner_details jest teraz puste
            elif self.active_chat_type == "room":
                partner_display_name = self.chat_rooms.get(
                    self.active_chat_partner_id, {}
                ).get("name", f"Pokój ID_{self.active_chat_partner_id}")
                # self._fetch_room_members_and_store(self.active_chat_partner_id) # to teraz będzie w _load_and_display_room_members

            if hasattr(self, "chat_active_partner_label"):
                self.chat_active_partner_label.config(
                    text=f"Czat z: {partner_display_name}"
                )

            if should_reload_history:
                self._load_and_display_chat_history(
                    self.chat_logged_in_user["user_id"],
                    self.active_chat_partner_id,
                    chat_type=self.active_chat_type,
                )
            else:
                # Jeśli nie przeładowujemy historii, a zmieniono na grupę, nadal musimy załadować członków.
                # To już jest robione wyżej. Jeśli to ten sam pokój, `_load_and_display_room_members` może zdecydować, czy odświeżyć.
                self.root.after(50, self._check_and_mark_read)

            self._clear_new_message_notification(
                self.active_chat_partner_id, chat_type=self.active_chat_type
            )
            self._last_open_chat_partner_id = self.active_chat_partner_id
            if hasattr(self, "chat_typing_indicator_label"):
                self._update_typing_indicator()
            self._cancel_reply_mode()
            self._update_send_button_state()

        except ValueError as e:  # Błąd konwersji ID lub nieznany IID
            logging.warning(
                f"Chat: Błąd podczas przetwarzania wyboru '{selected_iid_str}': {e}"
            )
            self.active_chat_partner_id = self.chat_dashboard_placeholder_id
            self.active_chat_type = "dashboard"
            if hasattr(self, "chat_users_tree") and self.chat_users_tree.winfo_exists():
                try:
                    self.chat_users_tree.selection_set(
                        self.chat_dashboard_placeholder_id
                    )
                    self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
                except tk.TclError:
                    pass
            if hasattr(self, "chat_active_partner_label"):
                self.chat_active_partner_label.config(text="Panel Główny Czatu")
            self._display_chat_message(
                f"--- Błąd: Problem z wyborem ({selected_iid_str}). ---", "error"
            )
            # Upewnij się, że panel członków jest ukryty w razie błędu
            if self._room_members_panel_visible:
                try:
                    self.chat_paned_window.forget(self.chat_room_members_panel)
                except tk.TclError:
                    logging.warning(
                        "TclError przy forget(self.chat_room_members_panel) w obsłudze błędu _on_chat_user_select"
                    )
                self._room_members_panel_visible = False
            self._show_or_hide_room_members_panel(show=False)

def _update_send_button_state(self):
        """
        Aktualizuje stan pól wprowadzania i przycisku wysyłania
        w zależności od statusu połączenia i wybranego partnera.
        """
        send_possible = (
            self.chat_logged_in_user
            and self.chat_connected_to_server
            and self.chat_authenticated
            and (
                self.active_chat_type == "user" or self.active_chat_type == "room"
            )  # Enable if user OR room is active
            and self.active_chat_partner_id != self.chat_dashboard_placeholder_id
        )

        # Dodatkowa blokada dla czatu prywatnego z użytkownikiem na liście blokowanych.
        if send_possible and self.active_chat_type == "user" and self.active_chat_partner_id:
            try:
                if self._is_user_blocked(self.active_chat_partner_id):
                    send_possible = False
            except Exception:
                # Nie przerywamy aktualizacji UI przy ewentualnym błędzie pomocniczej walidacji.
                pass

        desired_state = tk.NORMAL if send_possible else tk.DISABLED

        if hasattr(self, "chat_input_entry") and self.chat_input_entry.winfo_exists():
            try:
                self.chat_input_entry.config(state=desired_state)
            except tk.TclError:
                pass

        send_button = getattr(self, "chat_send_button", None)
        if send_button is None or not getattr(send_button, "winfo_exists", lambda: False)():
            action_frame = getattr(self, "chat_action_buttons_frame", None)
            if action_frame is not None and action_frame.winfo_exists():
                for child in action_frame.winfo_children():
                    try:
                        if child.cget("text") == "Wyślij":
                            send_button = child
                            break
                    except Exception:
                        continue

        if send_button is not None and getattr(send_button, "winfo_exists", lambda: False)():
            try:
                send_button.config(state=desired_state)
            except tk.TclError:
                pass

        attach_button = getattr(self, "chat_attach_button", None)
        if attach_button is not None and getattr(attach_button, "winfo_exists", lambda: False)():
            try:
                attach_button.config(state=desired_state)
            except tk.TclError:
                pass

        if hasattr(self, "emoji_button") and self.emoji_button.winfo_exists():
            try:
                self.emoji_button.config(state=desired_state)
            except tk.TclError:
                pass

__all__ = [
    "_restore_last_chat_partner",
    "_select_chat_partner_silently",
    "_check_and_mark_read",
    "_on_chat_message_search_change",
    "_clear_chat_message_search",
    "_apply_chat_message_filter",
    "_on_chat_user_select",
    "_update_send_button_state",
]
