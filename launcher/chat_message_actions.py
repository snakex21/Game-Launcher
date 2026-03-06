import logging
import tkinter as tk
from tkinter import messagebox, ttk

from launcher.utils import THEMES


def _on_message_read_update(
    self, data
):  # Upewnij się, że nazwa jest poprawna i bindowana
    """
    Odebrano informację od serwera, że wiadomość (którą my wysłaliśmy)
    została przeczytana przez odbiorcę.
    Data: {'message_id': ..., 'read_by_user_id': ..., 'is_read': True}
    """
    message_id_that_was_read = data.get("message_id")
    is_read_status = data.get("is_read", False)
    # read_by_user_id to ID partnera, który przeczytał naszą wiadomość
    partner_who_read_id = data.get("read_by_user_id")

    logging.debug(
        f"Chat: Odebrano 'message_read_update' dla wiadomości ID {message_id_that_was_read}, is_read={is_read_status} by user {partner_who_read_id}"
    )

    if message_id_that_was_read and is_read_status:
        message_updated_locally = False
        # Iteruj po WSZYSTKICH parach w self.chat_messages, bo nie wiemy, do której rozmowy należy ta wiadomość,
        # dopóki nie znajdziemy message_id. Partnerem dla tej wiadomości będzie `partner_who_read_id`.
        for partner_key_in_history, messages_list_local in self.chat_messages.items():
            # Sprawdź, czy ta lista wiadomości jest z partnerem, który właśnie przeczytał wiadomość
            if (
                partner_key_in_history == partner_who_read_id
            ):  # partner_key_in_history to ID partnera (odbiorcy tej wiadomości)
                for i, msg_data_item in enumerate(messages_list_local):
                    if msg_data_item.get("id") == message_id_that_was_read:
                        # Sprawdź, czy to my byliśmy nadawcą tej wiadomości
                        if (
                            msg_data_item.get("sender_id")
                            == self.chat_logged_in_user["user_id"]
                        ):
                            if not msg_data_item.get(
                                "is_read_by_receiver", False
                            ):  # Tylko jeśli jeszcze nie był oznaczony
                                self.chat_messages[partner_key_in_history][i][
                                    "is_read_by_receiver"
                                ] = True
                                message_updated_locally = True
                                logging.info(
                                    f"Chat: Lokalnie zaktualizowano status 'przeczytane' dla wiadomości ID {message_id_that_was_read}."
                                )
                            break
                if message_updated_locally:
                    break

        # Jeśli zaktualizowano stan lokalny i dotyczy to aktywnego czatu, odśwież widok
        if (
            message_updated_locally
            and self.active_chat_partner_id == partner_who_read_id
        ):
            logging.debug(
                f"Chat: Odświeżanie aktywnego czatu z {self.active_chat_partner_id} po aktualizacji statusu przeczytania."
            )
            # Flaga _force_history_reload_for_partner może nie być tutaj konieczna,
            # ponieważ _display_active_chat_history samo w sobie czyta z zaktualizowanego self.chat_messages
            self._display_active_chat_history(self.active_chat_partner_id)


def _show_chat_message_context_menu(self, event, message_id, message_bubble_container):
    """
    Wyświetla menu kontekstowe dla klikniętej wiadomości czatu.
    `message_bubble_container` to widget tk.Frame reprezentujący dymek.
    """
    if message_id is None:
        return

    context_menu = tk.Menu(
        self.chat_page_frame, tearoff=0, background="#2e2e2e", foreground="white"
    )

    # Pobierz dane wiadomości, aby sprawdzić, czy to nasza wiadomość
    message_data = None
    current_user_id = self.chat_logged_in_user["user_id"]
    for partner_id, messages_list in self.chat_messages.items():
        for msg in messages_list:
            if msg.get("id") == message_id:
                message_data = msg
                break
        if message_data:
            break

    if not message_data:
        logging.warning(
            f"Błąd: Nie znaleziono danych dla wiadomości ID {message_id} w menu kontekstowym."
        )
        return

    # Opcja "Edytuj wiadomość" (tylko dla naszych wiadomości)
    if message_data.get("sender_id") == current_user_id:
        context_menu.add_command(
            label="Edytuj wiadomość",
            command=lambda msg_data_to_edit=message_data: self._edit_chat_message_dialog(
                msg_data_to_edit
            ),
        )
    context_menu.add_command(
        label="Odpowiedz",
        command=lambda msg_data_to_reply=message_data: self._set_reply_mode(
            msg_data_to_reply
        ),
    )
    context_menu.add_separator()  # Separator po opcjach edycji/usuwania/odpowiadania

    context_menu.add_command(
        label="Usuń wiadomość",
        command=lambda msg_id_to_del=message_id: self._confirm_and_delete_chat_message(
            msg_id_to_del
        ),
    )
    context_menu.add_separator()
    context_menu.add_command(
        label="Kopiuj tekst",
        command=lambda content=message_data.get(
            "content", ""
        ): self.root.clipboard_clear()
        or self.root.clipboard_append(content),
    )

    context_menu.post(event.x_root, event.y_root)


def _edit_chat_message_dialog(self, message_data_to_edit: dict):
    """
    Otwiera okno dialogowe do edycji treści wiadomości.
    """
    message_id = message_data_to_edit.get("id")
    original_content = message_data_to_edit.get("content", "")
    sender_username = message_data_to_edit.get("sender_username", "Ty")

    edit_dialog = tk.Toplevel(self.chat_page_frame)
    edit_dialog.title(f"Edytuj Wiadomość (ID: {message_id})")
    edit_dialog.configure(bg="#1e1e1e")
    edit_dialog.grab_set()
    edit_dialog.transient(
        self.chat_page_frame
    )  # Okno dialogowe zależne od strony czatu

    # Centrowanie okna edycji
    self.root.update_idletasks()  # Wymuś aktualizację wymiarów
    parent_x = self.chat_page_frame.winfo_rootx()
    parent_y = self.chat_page_frame.winfo_rooty()
    parent_w = self.chat_page_frame.winfo_width()
    parent_h = self.chat_page_frame.winfo_height()

    dialog_w = 400
    dialog_h = 200
    pos_x = parent_x + (parent_w // 2) - (dialog_w // 2)
    pos_y = parent_y + (parent_h // 2) - (dialog_h // 2)
    edit_dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
    edit_dialog.resizable(False, False)

    ttk.Label(
        edit_dialog,
        text=f"Edytujesz wiadomość od {sender_username}:",
        font=("Segoe UI", 9, "bold"),
    ).pack(pady=(10, 5))

    # Pole tekstowe do edycji
    edit_text_frame = ttk.Frame(edit_dialog)
    edit_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    edit_text_frame.columnconfigure(0, weight=1)
    edit_text_frame.rowconfigure(0, weight=1)

    edit_text_widget = tk.Text(edit_text_frame, height=5, wrap=tk.WORD, relief=tk.FLAT)
    edit_text_widget.insert("1.0", original_content)
    edit_text_widget.grid(row=0, column=0, sticky="nsew")
    edit_text_widget.config(
        background=ttk.Style().lookup("TEntry", "fieldbackground"),
        foreground=ttk.Style().lookup("TEntry", "foreground"),
    )

    edit_text_scroll = ttk.Scrollbar(
        edit_text_frame, orient="vertical", command=edit_text_widget.yview
    )
    edit_text_scroll.grid(row=0, column=1, sticky="ns")
    edit_text_widget.config(yscrollcommand=edit_text_scroll.set)

    edit_text_widget.focus_set()  # Ustaw fokus na polu edycji
    edit_text_widget.mark_set(tk.INSERT, "1.0")  # Ustaw kursor na początku
    edit_text_widget.see(tk.INSERT)  # Upewnij się, że kursor jest widoczny

    def save_edited_message():
        new_content = edit_text_widget.get("1.0", tk.END).strip()
        if not new_content:
            messagebox.showwarning(
                "Błąd", "Treść wiadomości nie może być pusta.", parent=edit_dialog
            )
            return

        if self.sio and self.sio.connected and self.chat_logged_in_user:
            logging.info(
                f"Chat: Wysyłanie żądania edycji wiadomości ID {message_id} z nową treścią: '{new_content[:50]}...'"
            )
            self.sio.emit(
                "edit_message",
                {
                    "message_id": message_id,
                    "new_content": new_content,
                    "editor_user_id": self.chat_logged_in_user["user_id"],
                },
            )
            edit_dialog.destroy()
        else:
            messagebox.showerror(
                "Błąd Połączenia",
                "Brak połączenia z serwerem czatu. Nie można edytować wiadomości.",
                parent=edit_dialog,
            )

    button_frame = ttk.Frame(edit_dialog)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text="Zapisz Edycję", command=save_edited_message).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(button_frame, text="Anuluj", command=edit_dialog.destroy).pack(
        side=tk.LEFT, padx=5
    )


def _confirm_and_delete_chat_message(self, message_id_to_delete):
    """Pyta o potwierdzenie i wysyła żądanie usunięcia wiadomości."""
    if message_id_to_delete is None:
        return

    # Tutaj można dodać logikę pobierania treści wiadomości po ID dla lepszego potwierdzenia,
    # ale na razie proste potwierdzenie.
    if messagebox.askyesno(
        "Potwierdź Usunięcie",
        "Czy na pewno chcesz usunąć tę wiadomość?\nTej operacji nie można cofnąć.",
        parent=self.chat_page_frame,  # Ustaw rodzica dla okna dialogowego
        icon="warning",
    ):
        if self.sio and self.sio.connected and self.chat_logged_in_user:
            logging.info(
                f"Chat: Wysyłanie żądania usunięcia wiadomości o ID: {message_id_to_delete}"
            )
            self.sio.emit(
                "delete_message",
                {
                    "message_id": message_id_to_delete,
                    "deleter_user_id": self.chat_logged_in_user[
                        "user_id"
                    ],  # Przesyłamy ID usuwającego dla weryfikacji na serwerze
                },
            )
        else:
            messagebox.showerror(
                "Błąd Połączenia",
                "Nie można usunąć wiadomości. Brak połączenia z serwerem lub nie jesteś zalogowany.",
                parent=self.chat_page_frame,
            )


def _on_message_deleted_event(self, data):
    """
    Wywoływana, gdy serwer potwierdzi usunięcie wiadomości lub zgłosi błąd.
    Data powinna zawierać: {'success': True/False, 'message_id': ID_usuniętej,
                            'room_id': (opcjonalnie, ID pokoju), 'error': (opcjonalnie)}
    """
    message_id_deleted = data.get("message_id")
    success = data.get("success", False)
    error_msg_server = data.get("error")
    deleted_in_room_id = data.get("room_id")  # ID pokoju, jeśli to wiadomość grupowa

    if success:
        logging.info(
            f"Chat: Serwer potwierdził usunięcie wiadomości ID: {message_id_deleted} (Pokój: {deleted_in_room_id if deleted_in_room_id else 'N/A'})"
        )

        # Określ, której historii czatu dotyczy usunięcie
        target_history_key = None
        if deleted_in_room_id:  # Jeśli wiadomość była z pokoju
            target_history_key = deleted_in_room_id
        elif (
            self.active_chat_type == "user" and self.active_chat_partner_id
        ):  # Jeśli to czat prywatny, użyj active_chat_partner_id
            target_history_key = self.active_chat_partner_id
        # W przypadku wiadomości prywatnej usuniętej przez partnera, musimy znaleźć, kto był partnerem tej wiadomości.
        # To jest bardziej skomplikowane, jeśli nie jesteśmy w aktywnym czacie.
        # Na razie zakładamy, że `message_deleted_successfully` przyjdzie tylko do aktywnego czatu PRYWATNEGO
        # lub do WSZYSTKICH w pokoju grupowym.

        if target_history_key is not None and target_history_key in self.chat_messages:
            self.chat_messages[target_history_key] = [
                msg
                for msg in self.chat_messages[target_history_key]
                if msg.get("id") != message_id_deleted
            ]
            logging.debug(
                f"Usunięto wiadomość ID {message_id_deleted} z lokalnej historii dla klucza {target_history_key}."
            )

            # Odśwież widok, jeśli dotyczy to AKTYWNIE otwartego czatu (prywatnego LUB grupowego)
            if self.active_chat_partner_id == target_history_key and (
                (self.active_chat_type == "room" and deleted_in_room_id == target_history_key)
                or (self.active_chat_type == "user" and not deleted_in_room_id)
            ):  # Sprawdź, czy typ się zgadza
                logging.info(
                    f"Odświeżanie aktywnego czatu ({self.active_chat_type} ID: {target_history_key}) po usunięciu wiadomości."
                )
                self._display_active_chat_history(self.active_chat_partner_id)
            else:
                logging.debug(
                    f"Usunięta wiadomość ID {message_id_deleted} nie dotyczy aktywnie otwartego czatu. Aktywny: {self.active_chat_type} {self.active_chat_partner_id}, Wiadomość z pokoju: {deleted_in_room_id}"
                )

        else:
            logging.warning(
                f"Nie można zlokalizować historii czatu dla usuniętej wiadomości (target_key: {target_history_key})."
            )

    else:
        logging.error(
            f"Chat: Serwer odmówił usunięcia wiadomości ID: {message_id_deleted}. Powód: {error_msg_server}"
        )
        parent_for_msgbox = (
            self.chat_page_frame
            if hasattr(self, "chat_page_frame") and self.chat_page_frame.winfo_exists()
            else self.root
        )
        messagebox.showerror(
            "Błąd Usuwania",
            f"Nie udało się usunąć wiadomości:\n{error_msg_server or 'Nieznany błąd serwera.'}",
            parent=parent_for_msgbox,
        )


def _display_join_room_prompt(self, room_name: str, room_id: int):
    """Wyświetla w oknie czatu informację o braku dostępu i przycisk dołączenia."""
    self._display_chat_message("", "clear")  # Wyczyść okno wiadomości

    prompt_text = (
        f"Nie jesteś członkiem pokoju '{room_name}'.\n\n"
        "Aby zobaczyć wiadomości i uczestniczyć w rozmowie, musisz najpierw dołączyć do pokoju."
    )
    self._display_chat_message(prompt_text, "system")

    # Możemy tutaj dodać przycisk "Dołącz do Pokoju" bezpośrednio w oknie Text,
    # ale to jest bardziej skomplikowane. Na razie zostawmy to jako informację.
    # Użytkownik będzie musiał użyć menu kontekstowego (które dodamy później).
    # Alternatywnie, moglibyśmy dodać przycisk pod polem wiadomości.

    # TODO: W przyszłości, zamiast tylko tekstu, można by dodać tutaj interaktywny element "Dołącz"
    # lub pokazać pole do wpisania hasła, jeśli pokój jest chroniony.
    # Na razie, po prostu informujemy.

    # Upewnij się, że etykieta partnera pokazuje nazwę pokoju
    if hasattr(self, "chat_active_partner_label"):
        self.chat_active_partner_label.config(text=f"Pokój: {room_name} (Brak dostępu)")

    # Wyłącz pole do wpisywania wiadomości, jeśli nie jesteśmy członkiem
    if hasattr(self, "chat_input_entry"):
        self.chat_input_entry.config(state=tk.DISABLED)
        self.chat_input_var.set("")
        if hasattr(self, "_current_reply_message_data"):
            self._current_reply_message_data = None
        if hasattr(self, "_pending_chat_attachment"):
            self._pending_chat_attachment = None
        self._update_reply_preview_ui()
        self._update_pending_attachment_ui()

    self._update_send_button_state()  # To powinno wyłączyć przycisk wysyłania


def _on_message_edited_event(self, updated_message_data: dict):
    """
    Aktualizuje lokalną historię wiadomości po edycji i odświeża widok.
    """
    edited_message_id = updated_message_data.get("id")
    if not edited_message_id:
        logging.error("Chat: Otrzymano event edycji wiadomości bez ID.")
        return

    # Zaktualizuj lokalną kopię historii
    message_updated_in_local_history = False
    for partner_id, messages_list in self.chat_messages.items():
        for i, msg_data_local in enumerate(messages_list):
            if msg_data_local.get("id") == edited_message_id:
                # Zamień stary słownik wiadomości na nowy, zaktualizowany
                self.chat_messages[partner_id][i] = updated_message_data
                message_updated_in_local_history = True
                logging.info(
                    f"Chat: Lokalnie zaktualizowano wiadomość ID {edited_message_id}."
                )
                break
        if message_updated_in_local_history:
            break

    # Jeśli zaktualizowano stan lokalny i dotyczy to aktywnego czatu, odśwież widok
    if message_updated_in_local_history and self.active_chat_partner_id == partner_id:
        logging.debug(
            f"Chat: Wiadomość ID {edited_message_id} była w aktywnym czacie, odświeżanie."
        )
        # Wymuś ponowne wyświetlenie historii aktywnego czatu
        setattr(
            self, "_force_history_reload_for_partner", True
        )  # Flaga wymuszająca przeładowanie
        self._display_active_chat_history(self.active_chat_partner_id)


def _set_reply_mode(self, message_data_to_quote: dict):
    """
    Ustawia tryb odpowiadania na wiadomość, wyświetlając jej podgląd
    nad polem wprowadzania.
    """
    if not message_data_to_quote or not message_data_to_quote.get("id"):
        logging.warning(
            "Chat: Próba ustawienia trybu odpowiadania bez danych wiadomości."
        )
        return

    self._current_reply_message_data = message_data_to_quote
    logging.info(
        f"Chat: Ustawiono tryb odpowiadania na wiadomość ID {message_data_to_quote.get('id')}."
    )
    self._update_reply_preview_ui()  # Odśwież UI, aby pokazać podgląd


def _update_reply_preview_ui(self):
    """
    Aktualizuje UI podglądu cytowanej wiadomości.
    Jeśli _current_reply_message_data jest ustawione, pokazuje ramkę i jej zawartość.
    W przeciwnym razie ukrywa ramkę.
    """
    if not (
        hasattr(self, "chat_reply_preview_frame")
        and self.chat_reply_preview_frame.winfo_exists()
    ):
        return

    if self._current_reply_message_data:
        sender_name = self._current_reply_message_data.get("sender_username", "Nieznany")
        content_preview = self._current_reply_message_data.get("content", "")
        attachment_name = self._current_reply_message_data.get(
            "attachment_original_filename"
        )

        # Utwórz skróconą treść do wyświetlenia
        display_text = f"Odpowiadasz do {sender_name}: "
        if content_preview:
            display_text += content_preview[:50]
            if len(content_preview) > 50:
                display_text += "..."
        elif attachment_name:
            display_text += f"[Załącznik: {attachment_name}]"
        else:
            display_text += "[Wiadomość bez treści]"

        self.reply_preview_label.config(text=display_text)
        # Tutaj umieść pady i padx dla ramki:
        self.chat_reply_preview_frame.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 5)
        )

        # Dostosuj tło ramki podglądu
        theme_def = self.get_all_available_themes().get(
            self.settings.get("theme", "Dark"), THEMES["Dark"]
        )
        reply_preview_bg = theme_def.get("entry_background", "#282828")
        reply_preview_fg = theme_def.get("foreground", "white")
        reply_preview_border_color = theme_def.get("tree_heading", "#3e3e3e")  # Kolor ramki

        self.chat_reply_preview_frame.config(
            background=reply_preview_bg,
            highlightbackground=reply_preview_border_color,  # Kolor ramki gdy nie ma focusu
            highlightcolor=reply_preview_border_color,  # Kolor ramki gdy ma focus
            highlightthickness=1,  # Grubość ramki highlight
        )
        # Etykieta wewnątrz ramki podglądu odpowiedzi (to jest ttk.Label)
        self.reply_preview_label.config(
            background=reply_preview_bg, foreground=reply_preview_fg
        )

        # Wyczyść zawartość pola Entry
        self.chat_input_var.set("")  # Wyczyść pole po włączeniu trybu odpowiadania
        self.chat_input_entry.focus_set()  # Ustaw fokus

    else:
        self.chat_reply_preview_frame.grid_remove()  # Ukryj ramkę

    # Zaktualizuj pady górnego pola input, aby nie było podwójnego pady.
    if hasattr(self, "chat_input_entry") and self.chat_input_entry.winfo_exists():
        if self._current_reply_message_data or self._pending_chat_attachment:
            self.chat_input_entry.grid_configure(
                pady=(0, 5)
            )  # Mniejsze pady, jeśli coś jest nad nim
        else:
            self.chat_input_entry.grid_configure(pady=5)  # Normalne pady


def _cancel_reply_mode(self):
    """Anuluje tryb odpowiadania na wiadomość."""
    self._current_reply_message_data = None
    logging.info("Chat: Anulowano tryb odpowiadania.")
    self._update_reply_preview_ui()  # Odśwież UI, aby ukryć podgląd


__all__ = [
    "_on_message_read_update",
    "_show_chat_message_context_menu",
    "_edit_chat_message_dialog",
    "_confirm_and_delete_chat_message",
    "_on_message_deleted_event",
    "_display_join_room_prompt",
    "_on_message_edited_event",
    "_set_reply_mode",
    "_update_reply_preview_ui",
    "_cancel_reply_mode",
]
