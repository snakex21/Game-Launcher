import logging
import threading
from tkinter import messagebox

import socketio

def _connect_to_chat_server(self):
        if self.sio and self.sio.connected:
            logging.info("Chat: Klient SocketIO już połączony.")
            return

        if not self.chat_logged_in_user:  # Poprawiona nazwa atrybutu

            logging.warning(
                "Chat: Brak zalogowanego użytkownika, nie można połączyć z SocketIO."
            )
            return

        logging.info(f"Chat: Próba połączenia z SocketIO na {self.chat_server_url}...")
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # 0 = nieskończoność
            reconnection_delay=2,  # pierwsza próba po 2s
            reconnection_delay_max=10,
        )
        self.sio.eio.ping_interval = 60
        self.sio.eio.ping_timeout = 120

        @self.sio.event
        def member_removed_from_room(data):
            room_id_event = data.get("room_id")
            removed_user_id_event = data.get("removed_user_id")
            removed_username_event = data.get("removed_username", "Nieznany")
            admin_username_event = data.get("admin_username", "Admin")

            logging.info(
                f"Chat Event: Użytkownik '{removed_username_event}' (ID: {removed_user_id_event}) "
                f"został usunięty z pokoju {room_id_event} przez '{admin_username_event}'."
            )

            # Jeśli to my zostaliśmy usunięci z aktywnie otwartego pokoju
            if (
                self.chat_logged_in_user
                and removed_user_id_event == self.chat_logged_in_user["user_id"]
                and self.active_chat_type == "room"
                and self.active_chat_partner_id == room_id_event
            ):

                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Usunięto z Pokoju",
                        f"Zostałeś usunięty z pokoju '{self.chat_rooms.get(room_id_event, {}).get('name', f'ID {room_id_event}')}' "
                        f"przez administratora '{admin_username_event}'.",
                        parent=self.chat_page_frame,
                    ),
                )
                self._reset_to_chat_dashboard()

            # Niezależnie od tego, kto został usunięty, odśwież listę członków, jeśli ten pokój jest aktywny
            elif (
                self.active_chat_type == "room"
                and self.active_chat_partner_id == room_id_event
            ):
                self.root.after(50, self._load_and_display_room_members, room_id_event)
                self.root.after(
                    100,
                    lambda: self._display_chat_message(
                        f"--- Użytkownik '{removed_username_event}' został usunięty z pokoju przez {admin_username_event}. ---",
                        "system",
                    ),
                )

            # Zawsze odśwież główne drzewo kontaktów i dane pokoi (aby zaktualizować listę członków w self.chat_rooms)
            self.root.after(150, self._fetch_chat_users)

        @self.sio.event
        def user_online(data):
            user_id = data.get("user_id")
            if user_id:
                logging.info(
                    f"Chat: RECEIVED 'user_online' for User ID: {user_id}. Current self.online_users: {self.online_users}"
                )
                if user_id not in self.online_users:
                    self.online_users.add(user_id)
                    logging.info(
                        f"Chat: ADDED {user_id} to self.online_users. New state: {self.online_users}"
                    )
                    self.root.after(0, self._refresh_chat_dashboard_if_visible)
                    self.root.after(
                        0, self._filter_chat_users
                    )  # Wymuś odświeżenie Treeview

        @self.sio.event
        def user_offline(data):
            user_id = data.get("user_id")
            if user_id and user_id in self.online_users:
                self.online_users.remove(user_id)
                logging.info(
                    f"Chat: REMOVED {user_id} from self.online_users. New state: {self.online_users}"
                )
                self.root.after(0, self._refresh_chat_dashboard_if_visible)
                self.root.after(
                    0, self._filter_chat_users
                )  # Wymuś odświeżenie Treeview

        @self.sio.event
        def account_status_changed(data):
            is_now_banned = data.get("banned", False)
            reason = data.get("reason", "")

            if is_now_banned:
                logging.warning(
                    f"Chat Event: Twoje konto zostało zbanowane. Powód: {reason}"
                )
                self.root.after(
                    0,
                    lambda r=reason: messagebox.showwarning(
                        "Konto Zablokowane",
                        f"Twoje konto czatu zostało zablokowane przez administratora.\nPowód: {r}\n\nZostaniesz wylogowany z czatu.",
                        parent=(
                            self.chat_page_frame
                            if hasattr(self, "chat_page_frame")
                            else self.root
                        ),
                    ),
                )
                # Wymuś wylogowanie i rozłączenie SocketIO po stronie klienta
                self.root.after(
                    100, self._chat_logout
                )  # _chat_logout już powinno obsłużyć disconnect
            else:  # Zostałeś odbanowany
                logging.info(
                    f"Chat Event: Twoje konto zostało odblokowane. Powód: {reason}"
                )
                self.root.after(
                    0,
                    lambda r=reason: messagebox.showinfo(
                        "Konto Odblokowane",
                        f"Twoje konto czatu zostało odblokowane.\n{r}",
                        parent=(
                            self.chat_page_frame
                            if hasattr(self, "chat_page_frame")
                            else self.root
                        ),
                    ),
                )
                # Klient nie musi nic specjalnego robić, przy następnym logowaniu będzie mógł wejść.
                # Jeśli był wylogowany, _chat_logout już ustawił odpowiedni stan UI.


        @self.sio.event
        def online_users_list(data):
            online_ids_received = data.get("online_users", [])
            logging.info(
                f"Chat: RECEIVED 'online_users_list': {online_ids_received}. Current self.online_users (before processing): {self.online_users}"
            )

            # Tworzymy nowy zbiór na podstawie otrzymanej listy, aby uniknąć problemów z modyfikacją podczas iteracji
            new_online_set = set(online_ids_received)

            # Dodaj swoje własne ID do listy online (jeśli jest uwierzytelniony)
            if self.chat_logged_in_user and self.chat_authenticated:
                new_online_set.add(self.chat_logged_in_user["user_id"])
                logging.debug(
                    f"Chat: Added self ({self.chat_logged_in_user['user_id']}) to new_online_set."
                )

            # Zaktualizuj self.online_users, tylko jeśli nowy zbiór jest inny od obecnego
            if self.online_users != new_online_set:
                self.online_users = new_online_set  # Całkowicie nadpisz zbiór
                logging.info(
                    f"Chat: self.online_users FINAL STATE after 'online_users_list': {self.online_users}"
                )
                # Po masowej aktualizacji, odśwież dashboard i listę kontaktów
                self.root.after(0, self._refresh_chat_dashboard_if_visible)
                self.root.after(0, self._filter_chat_users)
            else:
                logging.debug(
                    "Chat Event: 'online_users_list' - self.online_users unchanged."
                )

        @self.sio.event
        def new_room_created(data):
            new_room_data = data.get("room")
            if new_room_data:
                room_id = new_room_data.get("id")
                room_name = new_room_data.get("name", "Nowy Pokój")
                logging.info(
                    f"Chat Event: Nowy pokój utworzony na serwerze: '{room_name}' (ID: {room_id})"
                )

                # Dodaj nowy pokój do lokalnego słownika self.chat_rooms
                self.chat_rooms[room_id] = new_room_data

                # Odśwież listę użytkowników/pokoi w Treeview
                # _filter_chat_users zostanie wywołane przez _fetch_chat_users,
                # ale możemy też odświeżyć bezpośrednio _filter_chat_users, jeśli _fetch_chat_users jest zbyt ciężkie.
                # Na razie _fetch_chat_users (które pobiera też pokoje) wydaje się ok.
                self.root.after(0, self._fetch_chat_users)

                # Opcjonalnie: Pokaż powiadomienie o nowym pokoju, jeśli nie jest to nasz pokój
                if (
                    self.chat_logged_in_user
                    and new_room_data.get("creator_id")
                    != self.chat_logged_in_user["user_id"]
                ):
                    # Można dodać subtelniejsze powiadomienie
                    # messagebox.showinfo("Nowy Pokój", f"Nowy pokój czatu został utworzony: '{room_name}'", parent=self.chat_page_frame)
                    pass


        # --- NOWY EVENT HANDLER (Samodzielne opuszczanie pokoju) ---
        @self.sio.event
        def member_left_room(data):
            """
            Obsługuje event informujący, że członek (być może my) opuścił pokój.
            Data: {'room_id': ..., 'user_id': ..., 'username': ...}
            """
            room_id_event = data.get("room_id")
            left_user_id = data.get("user_id")
            left_username = data.get("username", "Nieznany")

            logging.info(
                f"Chat Event: Użytkownik '{left_username}' (ID: {left_user_id}) opuścił pokój {room_id_event}."
            )

            # Jeśli to my opuściliśmy aktywnie otwarty pokój
            if (
                self.chat_logged_in_user
                and left_user_id == self.chat_logged_in_user["user_id"]
                and self.active_chat_type == "room"
                and self.active_chat_partner_id == room_id_event
            ):

                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Opuściłeś Pokój",
                        f"Opuściłeś pokój '{self.chat_rooms.get(room_id_event, {}).get('name', f'ID {room_id_event}')}'.",
                        parent=self.chat_page_frame,
                    ),
                )
                self._reset_to_chat_dashboard()  # Przełącz na dashboard

            # Niezależnie, odśwież listę członków, jeśli ten pokój jest aktywny (u innych)
            elif (
                self.active_chat_type == "room"
                and self.active_chat_partner_id == room_id_event
            ):
                self.root.after(50, self._load_and_display_room_members, room_id_event)
                self.root.after(
                    100,
                    lambda: self._display_chat_message(
                        f"--- Użytkownik '{left_username}' opuścił pokój. ---", "system"
                    ),
                )

            # Zawsze odśwież dane pokoi (aby zaktualizować member_ids w self.chat_rooms)
            self.root.after(150, self._fetch_chat_users)


        @self.sio.event
        def room_deleted_by_creator(data):
            """
            Obsługuje event informujący, że pokój został usunięty przez twórcę.
            Data: {'room_id': ..., 'room_name': ..., 'creator_id': ..., 'creator_username': ...}
            """
            deleted_room_id = data.get("room_id")
            deleted_room_name = data.get("room_name", "Nieznany pokój")
            creator_username_who_deleted = data.get("creator_username", "Twórca")

            logging.info(
                f"Chat Event: Pokój '{deleted_room_name}' (ID: {deleted_room_id}) "
                f"został usunięty przez twórcę '{creator_username_who_deleted}'."
            )

            # Usuń pokój z lokalnego słownika
            if deleted_room_id in self.chat_rooms:
                del self.chat_rooms[deleted_room_id]
                logging.debug(
                    f"Usunięto pokój ID {deleted_room_id} z lokalnego self.chat_rooms."
                )

            # Jeśli usunięty pokój był aktywnym czatem, przełącz na dashboard
            if (
                self.active_chat_type == "room"
                and self.active_chat_partner_id == deleted_room_id
            ):
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Pokój Usunięty",
                        f"Pokój '{deleted_room_name}', w którym byłeś, został usunięty przez twórcę ({creator_username_who_deleted}).",
                        parent=self.chat_page_frame,
                    ),
                )
                self._reset_to_chat_dashboard()  # Przełącza widok i ukrywa panel członków
            else:
                # Jeśli nie był to aktywny czat, ale użytkownik mógł być jego członkiem,
                # po prostu wyświetl informację (jeśli okno czatu jest widoczne)
                if self.current_frame == self.chat_page_frame:
                    self.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Pokój Usunięty",
                            f"Pokój '{deleted_room_name}', którego byłeś członkiem, "
                            f"został usunięty przez twórcę ({creator_username_who_deleted}).",
                            parent=self.chat_page_frame,
                        ),
                    )

            # Zawsze odśwież listę kontaktów (pokoi/użytkowników) w Treeview
            self.root.after(
                100, self._fetch_chat_users
            )  # To pociągnie _filter_chat_users


        @self.sio.event
        def message_deleted_successfully(
            data,
        ):  # Nazwa eventu taka sama jak na serwerze
            """Odebrano potwierdzenie usunięcia wiadomości."""
            logging.debug(
                f"Chat: Odebrano event 'message_deleted_successfully': {data}"
            )
            self.root.after(0, self._on_message_deleted_event, data)

        @self.sio.event
        def message_delete_failed(data):  # Nazwa eventu taka sama jak na serwerze
            """Odebrano informację o nieudanym usunięciu."""
            logging.debug(f"Chat: Odebrano event 'message_delete_failed': {data}")
            self.root.after(
                0, self._on_message_deleted_event, data
            )  # Możemy użyć tej samej funkcji obsługi


        @self.sio.event
        def message_read_update(data):
            """
            Odebrano informację od serwera, że wiadomość (którą my wysłaliśmy)
            została przeczytana przez odbiorcę.
            Data: {'message_id': ..., 'read_by_user_id': ..., 'is_read': True}
            """
            message_id = data.get("message_id")
            is_read = data.get("is_read", False)

            logging.debug(
                f"Chat: Odebrano 'message_read_update' dla wiadomości ID {message_id}, is_read={is_read}"
            )

            if message_id and is_read:
                # Zaktualizuj status tej wiadomości w naszej lokalnej historii (self.chat_messages)
                # To jest ważne, aby przy ponownym renderowaniu historii (np. po przełączeniu czatu)
                # status "przeczytane" był poprawnie wyświetlany.
                message_updated_in_local_history = False
                for partner, messages_list in self.chat_messages.items():
                    for i, msg_data_local in enumerate(messages_list):
                        if msg_data_local.get("id") == message_id:
                            # Upewnijmy się, że to wiadomość WYSŁANA przez nas
                            if (
                                msg_data_local.get("sender_id")
                                == self.chat_logged_in_user["user_id"]
                            ):
                                if msg_data_local.get("is_read_by_receiver") != True:
                                    self.chat_messages[partner][i][
                                        "is_read_by_receiver"
                                    ] = True
                                    message_updated_in_local_history = True
                                    logging.info(
                                        f"Chat: Zaktualizowano lokalny status 'is_read_by_receiver' dla wiadomości ID {message_id}"
                                    )
                                break  # Znaleziono wiadomość
                    if message_updated_in_local_history:
                        break

                # Jeśli aktualnie wyświetlamy czat, w którym jest ta wiadomość, odśwież widok,
                # aby pokazać wskaźnik "przeczytane".
                # Sprawdzamy self.active_chat_partner_id - jeśli jest to odbiorca tej wiadomości, odśwież.
                if (
                    message_updated_in_local_history
                ):  # Tylko jeśli faktycznie zaktualizowaliśmy lokalny stan
                    # Partner to odbiorca wiadomości, którą MY wysłaliśmy
                    partner_of_this_message = data.get("read_by_user_id")
                    if self.active_chat_partner_id == partner_of_this_message:
                        logging.debug(
                            f"Chat: Wiadomość ID {message_id} była w aktywnym czacie, odświeżanie."
                        )
                        # Wymuś ponowne wyświetlenie historii aktywnego czatu
                        # Użyj _force_history_reload_for_partner, aby _on_chat_user_select wiedziało, że ma przeładować
                        setattr(self, "_force_history_reload_for_partner", True)
                        self._display_active_chat_history(self.active_chat_partner_id)


        # Definicja event handlerów
        # Definicja event handlerów
        @self.sio.event
        def connect():
            self.chat_connected_to_server = True
            logging.info("Chat: Połączono z serwerem SocketIO.")
            self.root.after(
                0,
                lambda: self.chat_connection_status_label.config(
                    text="Status: Połączono", foreground="lightgreen"
                ),
            )
            # Wyślij uwierzytelnienie dopiero PO aktualizacji UI połączenia
            # i po małym opóźnieniu, aby UI zdążyło się ustabilizować.
            self.root.after(
                100,
                lambda: self.sio.emit(
                    "authenticate", {"user_id": self.chat_logged_in_user["user_id"]}
                ),
            )

        @self.sio.event
        def disconnect():
            self.chat_connected_to_server = False
            self.chat_authenticated = False
            logging.warning("Chat: Rozłączono z serwerem SocketIO.")
            self.root.after(
                0,
                lambda: self.chat_connection_status_label.config(
                    text="Status: Rozłączono", foreground="red"
                ),
            )
            self.root.after(
                0,
                lambda: self._display_chat_message(
                    "--- Rozłączono z serwerem czatu ---", "system"
                ),
            )
            self.root.after(0, self._update_chat_ui_state)

        @self.sio.event
        def authenticated(data):
            self.chat_authenticated = True
            logging.info(
                f"Chat: Uwierzytelniono na serwerze SocketIO jako {data.get('username')}."
            )
            self.root.after(
                0,
                lambda: self._display_chat_message(
                    f"--- Uwierzytelniono jako {data.get('username')} ---", "system"
                ),
            )
            self.root.after(
                0, self._update_chat_ui_state
            )  # To wywoła _fetch_chat_users i _filter_chat_users

            # Poinformuj serwer, że chcesz dostać aktualną listę online (jeśli tego nie robi server.py automatycznie po uwierzytelnieniu)
            # W obecnej wersji `chat_server.py` to jest już robione w `handle_authentication`
            # `emit('online_users_list', {'online_users': online_users_ids_at_connect})`
            # więc ta linia może być zbędna, ale nie zaszkodzi.
            # self.sio.emit('request_online_users_list') # Zakładając, że serwer ma taki event handler

        @self.sio.event
        def authentication_failed(data):
            logging.error(
                f"Chat: Uwierzytelnianie SocketIO nieudane: {data.get('message')}"
            )
            self.root.after(
                0,
                lambda: self._display_chat_message(
                    f"--- Błąd uwierzytelniania: {data.get('message')} ---", "system"
                ),
            )
            self.sio.disconnect()  # Rozłącz, jeśli uwierzytelnianie się nie powiodło

        @self.sio.event
        def private_message_sent(data):
            # Wiadomość, którą wysłaliśmy, została potwierdzona przez serwer
            logging.info(
                f"Chat: Wysłano wiadomość prywatną do {data.get('receiver_id')}."
            )
            message_type_context = (
                "private" if data.get("receiver_id") is not None else "unknown"
            )
            self.root.after(
                0,
                lambda d=data, mt=message_type_context: self._add_message_to_history(
                    d, is_sent_by_me=True, message_context=mt
                ),
            )

        @self.sio.event
        def private_message_received(data):
            # Otrzymano nową wiadomość prywatną
            logging.info(
                f"Chat: Otrzymano wiadomość prywatną od {data.get('sender_username')}."
            )
            message_type_context = (
                "private" if data.get("receiver_id") is not None else "unknown"
            )
            self.root.after(
                0,
                lambda d=data, mt=message_type_context: self._add_message_to_history(
                    d, is_sent_by_me=False, message_context=mt
                ),
            )

        @self.sio.event
        def group_message_sent(data):
            """Odebrano potwierdzenie, że nasza wiadomość grupowa została wysłana."""
            logging.info(
                f"Chat: Wysłano wiadomość grupową do pokoju ID {data.get('room_id')}."
            )
            # `message_context` będzie 'group', bo to event dla wiadomości grupowych
            self.root.after(
                0,
                lambda d=data: self._add_message_to_history(
                    d, is_sent_by_me=True, message_context="group"
                ),
            )

        @self.sio.event
        def group_message_received(data):
            """Odebrano nową wiadomość grupową od innego użytkownika."""
            logging.info(
                f"Chat: Otrzymano wiadomość grupową od {data.get('sender_username')} w pokoju ID {data.get('room_id')}."
            )
            # `message_context` będzie 'group'
            self.root.after(
                0,
                lambda d=data: self._add_message_to_history(
                    d, is_sent_by_me=False, message_context="group"
                ),
            )


        @self.sio.event
        def message_error(data):
            logging.error(f"Chat: Błąd wiadomości: {data.get('message')}")
            self.root.after(
                0,
                lambda: self._display_chat_message(
                    f"--- Błąd wiadomości: {data.get('message')} ---", "error"
                ),
            )

        @self.sio.event
        def message_edited_successfully(data):
            """
            Odebrano zaktualizowane dane wiadomości po edycji.
            Data zawiera pełny słownik wiadomości.
            """
            logging.debug(f"Chat: Odebrano 'message_edited_successfully': {data}")
            self.root.after(0, self._on_message_edited_event, data)

        @self.sio.event
        def message_edit_failed(data):
            """Odebrano informację o nieudanej edycji wiadomości."""
            logging.warning(f"Chat: Odebrano 'message_edit_failed': {data}")
            message_id = data.get("message_id", "Nieznane")
            error_msg = data.get("error", "Nieznany błąd.")
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Błąd Edycji Wiadomości",
                    f"Nie udało się edytować wiadomości ID {message_id}:\n{error_msg}",
                    parent=self.chat_page_frame,
                ),
            )


        @self.sio.event
        def typing_update(data):
            sender_id = data.get("sender_id")
            is_typing = data.get("is_typing")

            # Zaktualizuj status pisania dla tego użytkownika
            self.typing_status[sender_id] = is_typing

            # Odśwież wskaźnik pisania TYLKO jeśli ten użytkownik jest aktywnym partnerem
            if sender_id == self.active_chat_partner_id:
                self.root.after(0, self._update_typing_indicator)

            # W przyszłości: wizualna sygnalizacja pisania na liście użytkowników


        # Uruchom połączenie w osobnym wątku, aby nie blokować GUI
        try:
            threading.Thread(
                target=self.sio.connect, args=(self.chat_server_url,), daemon=True
            ).start()
        except Exception as e:
            logging.error(f"Chat: Błąd uruchomienia wątku połączenia SocketIO: {e}")
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Błąd Połączenia Czatu",
                    f"Nie można uruchomić połączenia SocketIO:\n{e}",
                    parent=self.chat_page_frame,
                ),
            )

__all__ = ["_connect_to_chat_server"]
