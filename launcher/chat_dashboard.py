import datetime
import logging
import tkinter as tk

def _reset_to_chat_dashboard(self):
        """Bezpiecznie przełącza widok czatu na panel główny (dashboard)."""
        self.active_chat_partner_id = self.chat_dashboard_placeholder_id
        self.active_chat_type = "dashboard"
        if hasattr(self, "chat_users_tree") and self.chat_users_tree.winfo_exists():
            try:
                self.chat_users_tree.selection_set(self.chat_dashboard_placeholder_id)
                self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
            except tk.TclError:
                logging.warning(
                    "TclError podczas resetowania do dashboardu (chat_users_tree)."
                )

        if hasattr(self, "chat_active_partner_label"):
            self.chat_active_partner_label.config(text="Panel Główny Czatu")

        self._show_chat_dashboard()  # Wyświetla zawartość dashboardu

        if self._room_members_panel_visible:  # Ukryj panel członków
            try:
                self.chat_paned_window.forget(self.chat_room_members_panel)
            except tk.TclError:
                logging.warning(
                    "TclError podczas ukrywania panelu członków przy resecie do dashboardu."
                )
            self._room_members_panel_visible = False

        self._cancel_reply_mode()  # Anuluj tryb odpowiedzi, jeśli był aktywny
        self._update_send_button_state()

def _update_chat_partner_details(self, partner_id_to_update: int):
        """
        Placeholder: W przyszłości może aktualizować szczegóły partnera,
        jeśli nie są w pełni załadowane. Na razie nie robi nic.
        """
        # logging.debug(f"Chat: _update_chat_partner_details wywołane dla ID: {partner_id_to_update}")
        pass

def _refresh_chat_dashboard_if_visible(self):
        """Jeśli wyświetlony jest placeholder panelu głównego, odrysuj listę online."""
        if self.active_chat_partner_id == self.chat_dashboard_placeholder_id:
            self._show_chat_dashboard()

def _show_chat_dashboard(self):
        """Wyświetla zawartość panelu głównego czatu (Dashboard)."""
        self._display_chat_message("", "clear")
        if hasattr(self, "chat_active_partner_label"):
            self.chat_active_partner_label.config(text="Panel Główny Czatu")
        if hasattr(self, "chat_typing_indicator_label"):
            self.chat_typing_indicator_label.config(text="")

        self._show_or_hide_room_members_panel(
            show=False
        )  # Dashboard nie ma członków do wyświetlenia

        self._rendered_chat_partner_id = (
            self.chat_dashboard_placeholder_id
        )  # Ustaw, że dashboard jest renderowany

        self._display_chat_message("--- Panel Główny Czatu ---", "system")
        self._display_chat_message(
            "Witaj w Czat! Wybierz użytkownika lub pokój z listy, aby rozpocząć rozmowę.",
            "system",
        )
        self._display_chat_message("", "normal")
        self._display_chat_message("--- Aktywni użytkownicy ---", "system")

        active_users_displayed = False
        if not self.chat_logged_in_user:
            logging.warning(
                "Chat Dashboard: Próba wyświetlenia aktywnych użytkowników bez zalogowanego użytkownika."
            )
            self._display_chat_message(
                "Zaloguj się, aby zobaczyć aktywnych użytkowników.", "system"
            )
            return

        logging.debug(
            f"Chat Dashboard: Rendering active users. self.online_users: {self.online_users}, self.chat_users keys: {list(self.chat_users.keys())}"
        )

        for user_id in sorted(list(self.online_users)):
            if user_id == self.chat_logged_in_user["user_id"]:
                continue

            user_info = self.chat_users.get(user_id)
            if user_info:
                username = user_info.get("username", f"ID_{user_id}")
                self._display_chat_message(f"• {username} (online)", "other_message")
                active_users_displayed = True
            else:
                logging.warning(
                    f"Chat Dashboard: Brak user_info dla online user_id: {user_id}. Pomijanie."
                )

        if not active_users_displayed:
            self._display_chat_message("Brak innych użytkowników online.", "system")

def _display_chat_messages_from_history(self, partner_id):
        """
        Wyświetla wiadomości z self.chat_messages dla aktywnego partnera czatu.
        Wywoływana PO pobraniu historii z serwera.
        """
        # Sprawdź, czy użytkownik nadal jest aktywnym partnerem czatu
        if partner_id != self.active_chat_partner_id:
            logging.debug(
                f"Chat: Partner czatu zmieniony na {self.active_chat_partner_id}, nie wyświetlam historii dla {partner_id}."
            )
            return  # Nie wyświetlaj, jeśli użytkownik w międzyczasie zmienił czat

        self._display_chat_message("", "clear")  # Wyczyść okno ponownie

        messages_for_current_chat = self.chat_messages.get(partner_id, [])

        if messages_for_current_chat:
            self._display_chat_message(
                f"--- Początek czatu z {self.chat_users.get(partner_id, {}).get('username')} ---",
                "system",
            )
            for msg_data in messages_for_current_chat:
                sender_id = msg_data.get("sender_id")
                content = msg_data.get("content")
                timestamp = datetime.datetime.fromisoformat(
                    msg_data.get("timestamp")
                ).strftime("%H:%M")

                if sender_id == self.chat_logged_in_user["user_id"]:
                    self._display_chat_message(
                        f"[{timestamp}] Ja: {content}", "my_message"
                    )
                else:
                    sender_username = self.chat_users.get(sender_id, {}).get(
                        "username", f"ID_{sender_id}"
                    )
                    self._display_chat_message(
                        f"[{timestamp}] {sender_username}: {content}", "other_message"
                    )
            self._display_chat_message(
                f"--- Koniec czatu z {self.chat_users.get(partner_id, {}).get('username')} ---",
                "system",
            )
        else:
            self._display_chat_message(
                f"--- Brak historii czatu z {self.chat_users.get(partner_id, {}).get('username')} ---",
                "system",
            )

def _format_chat_date(self, chat_date: datetime.date) -> str:
        """Formatuje datę wiadomości na 'Dzisiaj', 'Wczoraj' lub pełną datę."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        if chat_date == today:
            return "--- Dzisiaj ---"
        elif chat_date == yesterday:
            return "--- Wczoraj ---"
        else:
            return f"--- {chat_date.strftime('%Y-%m-%d')} ---"

__all__ = [
    "_reset_to_chat_dashboard",
    "_update_chat_partner_details",
    "_refresh_chat_dashboard_if_visible",
    "_show_chat_dashboard",
    "_display_chat_messages_from_history",
    "_format_chat_date",
]
