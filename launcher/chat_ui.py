import logging

def _on_chat_display_resize(self, event=None):
        """
        Dostosowuje marginesy w tk.Text, aby wiadomości miały 'dymki'
        dla różnych rozmiarów okna, ALE TERAZ TYLKO Z BIAŁYMI ODSTĘPAMI.
        """
        if (
            not hasattr(self, "chat_message_display")
            or not self.chat_message_display.winfo_exists()
        ):
            return

        display_width = self.chat_message_display.winfo_width()
        if display_width < 100:  # Minimalna sensowna szerokość
            return

        # Używamy szerokiego marginesu po stronie, GDZIE NIE MA TEKSTU,
        # aby zasymulować "krótki" dymek.
        # Minimalny stały margines dla estetyki (tekst nie przykleja się do krawędzi okna)
        fixed_text_margin = 10

        # Maksymalny proporcjonalny margines, który tworzy "dymek"
        # Będzie to % szerokości okna wiadomości.
        proportional_gap = int(display_width * 0.35)  # Np. 35% szerokości
        min_proportional_gap = (
            100  # Minimalne oddalenie wiadomości od przeciwległej krawędzi
        )

        # Margines z lewej dla moich wiadomości (push to right)
        # Będzie to lmargin1 i lmargin2. Prawy margines jest stały i mały (fixed_text_margin)
        my_left_indent = max(min_proportional_gap, proportional_gap)

        # Margines z prawej dla wiadomości od innych (push to left)
        # Będzie to rmargin. Lewy margines jest stały i mały (fixed_text_margin)
        other_right_indent = max(min_proportional_gap, proportional_gap)

        # Zastosuj obliczone marginesy do tagów
        # Tag "my_message_tag": tekst wyrównany do prawej, lewy margines odpycha tekst od lewej strony okna
        # po obliczeniu my_left_indent i other_right_indent
        # Twoje wiadomości: bubble przy prawej krawędzi, szerokość = widget_width - (fixed + proportional)
        self.chat_message_display.tag_config(
            "my_message_tag",
            lmargin1=fixed_text_margin,  # mały odstęp od lewej
            lmargin2=fixed_text_margin,
            rmargin=my_left_indent,  # duży odstęp od prawej
        )

        # Wiadomości innych: bubble przy lewej, szerokość = widget_width - (proportional + fixed)
        self.chat_message_display.tag_config(
            "other_message_tag",
            lmargin1=other_right_indent,  # duży odstęp od lewej
            lmargin2=other_right_indent,
            rmargin=fixed_text_margin,  # mały odstęp od prawej
        )

        if hasattr(self, "_chat_bubble_containers"):
            for cont in list(self._chat_bubble_containers):
                if cont.winfo_exists():
                    cont.configure(width=display_width)
                    # po zmianie szerokości policz wysokość, żeby nie znikł
                    cont.update_idletasks()
                    cont.configure(height=cont.winfo_reqheight())
                else:
                    # usuwamy z listy, jeśli kontener został zniszczony
                    self._chat_bubble_containers.remove(cont)

def _update_typing_indicator(self):
        """Aktualizuje tekst wskaźnika pisania na podstawie self.typing_status."""
        if (
            not hasattr(self, "chat_typing_indicator_label")
            or not self.chat_typing_indicator_label.winfo_exists()
        ):
            return

        # Sprawdź, czy aktywny partner czatu pisze
        partner_id = self.active_chat_partner_id
        is_partner_typing = self.typing_status.get(partner_id, False)

        if is_partner_typing:
            partner_username = self.chat_users.get(partner_id, {}).get(
                "username", "Nieznany"
            )
            self.chat_typing_indicator_label.config(
                text=f"{partner_username} pisze...", foreground="gray"
            )
        else:
            self.chat_typing_indicator_label.config(
                text="", foreground="gray"
            )

def _filter_chat_users(self):
        search_term = self.chat_user_search_var.get().lower().strip()

        if (
            not hasattr(self, "chat_users_tree")
            or not self.chat_users_tree.winfo_exists()
        ):
            logging.error(
                "Chat: _filter_chat_users - Treeview nie istnieje lub nie jest widoczny."
            )
            return

        self.chat_users_tree.delete(*self.chat_users_tree.get_children())

        self.chat_users_tree.insert(
            "",
            0,
            iid=self.chat_dashboard_placeholder_id,
            values=("💬 Panel Główny Czatu", ""),
            tags=("system_header_tag", "dashboard_placeholder"),
        )

        users_header_iid = "section_users_header"
        self.chat_users_tree.insert(
            "",
            "end",
            iid=users_header_iid,
            values=("👤 Użytkownicy", ""),
            tags=("system_header_tag",),
        )

        users_matching_filter_found = False
        if self.chat_logged_in_user:
            logging.debug(
                f"Chat Filter: Filtering users. self.online_users: {self.online_users}. All known chat users: {list(self.chat_users.keys())}. Self ID: {self.chat_logged_in_user['user_id']}"
            )
            for user_id, user_info in sorted(
                self.chat_users.items(),
                key=lambda item: item[1].get("username", "").lower(),
            ):
                if user_id == self.chat_logged_in_user["user_id"]:
                    continue

                username = user_info.get("username", f"ID_{user_id}")
                username_lower = username.lower()

                if search_term in username_lower:
                    tags = ["user_chat_item"]
                    display_name_with_status = username

                    if user_id in self.online_users:
                        tags.append("user_online_tag")
                        display_name_with_status = f"{username} (online)"
                    else:
                        tags.append("user_offline_tag")
                        display_name_with_status = f"{username} (offline)"

                    unread_count = self.unread_messages_count.get(user_id, 0)
                    if unread_count > 0:
                        tags.append("new_message_tag")
                        unread_count_str = str(unread_count)
                    else:
                        unread_count_str = ""

                    self.chat_users_tree.insert(
                        users_header_iid,
                        "end",
                        iid=f"{self.CHAT_PREFIX_USER}{user_id}",
                        values=(display_name_with_status, unread_count_str),
                        tags=tuple(tags),
                    )
                    users_matching_filter_found = True

            if not users_matching_filter_found and search_term:
                self.chat_users_tree.insert(
                    users_header_iid,
                    "end",
                    iid="no_users_results",
                    values=("Brak użytkowników", ""),
                    tags=("system_header_tag",),
                )
        elif search_term:
            self.chat_users_tree.insert(
                users_header_iid,
                "end",
                iid="no_users_results_not_logged_in",
                values=("Zaloguj się, aby wyszukać", ""),
                tags=("system_header_tag",),
            )

        # Sekcja Pokoje Grupowe (pozostaje bez większych zmian w tej iteracji)
        rooms_header_iid = "section_rooms_header"
        self.chat_users_tree.insert(
            "",
            "end",
            iid=rooms_header_iid,
            values=("🏢 Pokoje Grupowe", ""),
            tags=("system_header_tag",),
        )

        rooms_matching_filter_found = False
        for room_id, room_info in sorted(
            self.chat_rooms.items(), key=lambda item: item[1]["name"].lower()
        ):
            room_name = room_info.get("name", f"Pokój ID_{room_id}")
            room_name_lower = room_name.lower()
            if search_term in room_name_lower:
                tags = ["room_chat_item"]
                unread_count_room_str = ""  # Placeholder

                self.chat_users_tree.insert(
                    rooms_header_iid,
                    "end",
                    iid=f"{self.CHAT_PREFIX_ROOM}{room_id}",
                    values=(room_name, unread_count_room_str),
                    tags=tuple(tags),
                )
                rooms_matching_filter_found = True
        if not rooms_matching_filter_found and search_term:
            self.chat_users_tree.insert(
                rooms_header_iid,
                "end",
                values=("Brak pokoi grupowych", ""),
                tags=("system_header_tag",),
            )

        # ... (reszta kodu przywracania zaznaczenia) ...

        item_to_select_id = None
        # Sprawdź, czy self.active_chat_type jest ustawione
        if self.active_chat_partner_id and self.active_chat_type:
            if self.active_chat_type == "user":
                item_to_select_id = (
                    f"{self.CHAT_PREFIX_USER}{self.active_chat_partner_id}"
                )
            elif self.active_chat_type == "room":
                item_to_select_id = (
                    f"{self.CHAT_PREFIX_ROOM}{self.active_chat_partner_id}"
                )
            elif self.active_chat_type == "dashboard":
                item_to_select_id = self.chat_dashboard_placeholder_id

        if item_to_select_id and self.chat_users_tree.exists(item_to_select_id):
            self.chat_users_tree.selection_set(item_to_select_id)
            self.chat_users_tree.see(item_to_select_id)
            self.chat_users_tree.focus(item_to_select_id)
        elif self.chat_users_tree.exists(
            self.chat_dashboard_placeholder_id
        ):  # Domyślny wybór na dashboard, jeśli nie ma nic innego
            self.chat_users_tree.selection_set(self.chat_dashboard_placeholder_id)
            self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
            # Zresetuj active_chat_partner_id i type, jeśli nie można było ustawić focusu
            self.active_chat_partner_id = self.chat_dashboard_placeholder_id
            self.active_chat_type = "dashboard"

def _reset_chat_search_field(self):
        """Resetuje pole wyszukiwania użytkowników czatu."""
        self.chat_user_search_var.set("")

__all__ = [
    "_on_chat_display_resize",
    "_update_typing_indicator",
    "_filter_chat_users",
    "_reset_chat_search_field",
]
