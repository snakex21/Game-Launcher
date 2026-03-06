import logging
import threading
from tkinter import messagebox

import requests

from launcher.config_store import save_local_settings


def _is_user_blocked(self, user_id_to_check: int) -> bool:
    """Sprawdza, czy użytkownik o podanym ID jest na liście zablokowanych."""
    return user_id_to_check in self.blocked_user_ids


def _block_chat_user(self, user_id_to_block: int, username_to_block: str):
    if not self.chat_logged_in_user:
        return

    if messagebox.askyesno(
        "Zablokuj Użytkownika",
        f"Czy na pewno chcesz zablokować użytkownika '{username_to_block}'?\n"
        "Nie będziesz mógł wysyłać do niego wiadomości.",
        icon="warning",
        parent=self.chat_page_frame,
    ):

        self.blocked_user_ids.add(user_id_to_block)
        self.local_settings["chat_blocked_user_ids"] = list(self.blocked_user_ids)
        save_local_settings(self.local_settings)
        logging.info(
            f"Użytkownik {self.chat_logged_in_user['username']} zablokował {username_to_block} (ID: {user_id_to_block})."
        )

        def block_on_server_thread():
            try:
                payload = {"blocker_id": self.chat_logged_in_user["user_id"]}
                response = requests.post(
                    f"{self.chat_server_url}/users/{user_id_to_block}/block",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                )
                if response.status_code == 201 or response.status_code == 200:
                    logging.info(
                        f"Serwer potwierdził zablokowanie użytkownika ID: {user_id_to_block}"
                    )
                else:
                    error_data = response.json() if response.content else {}
                    logging.warning(
                        f"Serwer zwrócił błąd {response.status_code} przy blokowaniu {user_id_to_block}: {error_data.get('error', 'Nieznany błąd')}"
                    )
            except requests.RequestException as e_block_req:
                logging.error(
                    f"Błąd sieciowy przy próbie blokowania użytkownika: {e_block_req}"
                )

        threading.Thread(target=block_on_server_thread, daemon=True).start()

        self._update_chat_ui_for_blocked_status()
        self._filter_chat_users()


def _unblock_chat_user(self, user_id_to_unblock: int, username_to_unblock: str):
    if not self.chat_logged_in_user:
        return

    if user_id_to_unblock in self.blocked_user_ids:
        self.blocked_user_ids.remove(user_id_to_unblock)
        self.local_settings["chat_blocked_user_ids"] = list(self.blocked_user_ids)
        save_local_settings(self.local_settings)
        logging.info(
            f"Użytkownik {self.chat_logged_in_user['username']} odblokował {username_to_unblock} (ID: {user_id_to_unblock})."
        )

        def unblock_on_server_thread():
            try:
                payload = {"unblocker_id": self.chat_logged_in_user["user_id"]}
                response = requests.delete(
                    f"{self.chat_server_url}/users/{user_id_to_unblock}/block",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                )
                if response.status_code == 200 or response.status_code == 204:
                    logging.info(
                        f"Serwer potwierdził odblokowanie użytkownika ID: {user_id_to_unblock}"
                    )
                else:
                    error_data = response.json() if response.content else {}
                    logging.warning(
                        f"Serwer zwrócił błąd {response.status_code} przy odblokowywaniu {user_id_to_unblock}: {error_data.get('error', 'Nieznany błąd')}"
                    )
            except requests.RequestException as e_unblock_req:
                logging.error(
                    f"Błąd sieciowy przy próbie (stub) odblokowania użytkownika: {e_unblock_req}"
                )

        threading.Thread(target=unblock_on_server_thread, daemon=True).start()

        self._update_chat_ui_for_blocked_status()
        self._filter_chat_users()


__all__ = [
    "_is_user_blocked",
    "_block_chat_user",
    "_unblock_chat_user",
]
