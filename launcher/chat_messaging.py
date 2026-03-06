import logging
import mimetypes
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests

def _select_and_upload_chat_file(self):
        """
        Otwiera dialog wyboru pliku, a następnie próbuje przesłać wybrany plik
        na serwer czatu. Po pomyślnym przesłaniu, wysyła wiadomość czatu
        z informacją o załączniku.
        """
        if (
            not self.chat_logged_in_user
            or not self.sio
            or not self.sio.connected
            or not self.chat_authenticated
        ):
            messagebox.showwarning(
                "Czat",
                "Musisz być zalogowany i połączony z serwerem, aby wysyłać pliki.",
                parent=self.chat_page_frame,
            )
            return
        if (
            self.active_chat_partner_id is None
            or self.active_chat_partner_id == self.chat_dashboard_placeholder_id
        ):
            messagebox.showwarning(
                "Czat",
                "Wybierz partnera czatu, do którego chcesz wysłać plik.",
                parent=self.chat_page_frame,
            )
            return

        # Otwórz dialog wyboru pliku
        filepath = filedialog.askopenfilename(
            title="Wybierz plik do wysłania",
            parent=self.chat_page_frame,  # Ustaw rodzica dla modalności
        )

        if not filepath:
            logging.debug("Chat: Anulowano wybór pliku do wysłania.")
            return

        # Sprawdź rozmiar pliku przed wysłaniem
        try:
            file_size_bytes = os.path.getsize(filepath)
            # MAX_FILE_SIZE_MB jest zdefiniowane w chat_server.py, ale możemy tu mieć własny limit
            # lub pobierać go z konfiguracji w przyszłości. Na razie hardkodujemy podobny.
            client_max_file_size_mb = 10
            if file_size_bytes > client_max_file_size_mb * 1024 * 1024:
                messagebox.showerror(
                    "Błąd Pliku",
                    f"Wybrany plik jest zbyt duży (maks. {client_max_file_size_mb} MB).",
                    parent=self.chat_page_frame,
                )
                return
        except OSError as e:
            logging.error(f"Chat: Nie można odczytać rozmiaru pliku '{filepath}': {e}")
            messagebox.showerror(
                "Błąd Pliku",
                f"Nie można odczytać pliku:\n{filepath}",
                parent=self.chat_page_frame,
            )
            return

        logging.info(f"Chat: Wybrano plik do wysłania: {filepath}")

        # Pokaż okno postępu (proste, indeterminate)
        # Możesz stworzyć bardziej zaawansowane okno postępu dla plików, jeśli chcesz
        upload_progress_window = tk.Toplevel(self.chat_page_frame)
        upload_progress_window.title("Przesyłanie Pliku...")
        upload_progress_window.geometry("300x100")
        upload_progress_window.resizable(False, False)
        upload_progress_window.grab_set()  # Zablokuj interakcję z oknem czatu

        ttk.Label(
            upload_progress_window, text=f"Przesyłanie: {os.path.basename(filepath)}"
        ).pack(pady=10)
        progress_bar_upload = ttk.Progressbar(
            upload_progress_window, mode="indeterminate", length=250
        )
        progress_bar_upload.pack(pady=5)
        progress_bar_upload.start(20)
        upload_progress_window.update()

        try:
            # Otwieramy plik TUTAJ, ale NIE używamy 'with'
            file_object = open(filepath, "rb")

            # Przygotuj dane do wysłania, przekazując otwarty obiekt pliku
            files_payload = {
                "file": (
                    os.path.basename(filepath),
                    file_object,  # <-- Przekazujemy otwarty obiekt pliku
                    mimetypes.guess_type(filepath)[0] or "application/octet-stream",
                )
            }

            # Wyślij plik w osobnym wątku, przekazując obiekt pliku do zamknięcia
            upload_thread = threading.Thread(
                target=self._upload_file_thread,
                args=(
                    files_payload,
                    upload_progress_window,
                    file_object,
                ),  # <-- Dodajemy file_object jako argument
                daemon=True,
            )
            upload_thread.start()

        except FileNotFoundError:  # Dodano obsługę FileNotFoundError
            logging.error(f"Chat: Nie znaleziono pliku do wysłania: {filepath}")
            messagebox.showerror(
                "Błąd Pliku",
                f"Nie znaleziono pliku:\n{filepath}",
                parent=self.chat_page_frame,
            )
            if upload_progress_window.winfo_exists():
                upload_progress_window.destroy()
        except Exception as e:
            logging.error(f"Chat: Błąd przygotowania pliku do wysłania: {e}")
            messagebox.showerror(
                "Błąd Wysyłania",
                f"Nie można przygotować pliku do wysłania:\n{e}",
                parent=self.chat_page_frame,
            )
            if upload_progress_window.winfo_exists():
                upload_progress_window.destroy()
            # Jeśli plik został otwarty, a wystąpił inny błąd, upewnij się, że jest zamknięty
            if "file_object" in locals() and file_object and not file_object.closed:
                file_object.close()

def _upload_file_thread(
        self, files_payload, progress_window_ref, file_to_close=None
    ):
        """
        Funkcja działająca w osobnym wątku, odpowiedzialna za wysłanie pliku
        i obsługę odpowiedzi. Zamyka przekazany obiekt pliku po zakończeniu.
        """
        try:
            response = requests.post(
                f"{self.chat_server_url}/upload_file", files=files_payload, timeout=60
            )
            response.raise_for_status()

            upload_data = response.json()
            if progress_window_ref.winfo_exists():
                progress_window_ref.destroy()
            self.root.after(0, self._handle_file_upload_response, upload_data, None)

        except requests.exceptions.RequestException as e:
            error_message = f"Błąd sieci podczas wysyłania pliku: {e}"
            logging.error(error_message)
            if progress_window_ref.winfo_exists():
                progress_window_ref.destroy()
            self.root.after(0, self._handle_file_upload_response, None, error_message)
        except Exception as e:
            error_message = f"Nieoczekiwany błąd podczas wysyłania pliku: {e}"
            logging.exception(error_message)
            if progress_window_ref.winfo_exists():
                progress_window_ref.destroy()
            self.root.after(0, self._handle_file_upload_response, None, error_message)
        finally:
            # Zawsze próbuj zamknąć przekazany obiekt pliku
            if file_to_close and not file_to_close.closed:
                try:
                    file_to_close.close()
                    logging.debug("Chat: Zamknięto obiekt pliku po wysłaniu/błędzie.")
                except Exception as e_close:
                    logging.error(
                        f"Chat: Błąd podczas zamykania obiektu pliku: {e_close}"
                    )

def _handle_file_upload_response(self, upload_data, error_message):
        """
        Obsługuje odpowiedź z serwera po próbie wysłania pliku.
        Wywoływana w głównym wątku przez self.root.after().
        """
        if error_message:
            messagebox.showerror(
                "Błąd Wysyłania Pliku", error_message, parent=self.chat_page_frame
            )
            return

        if upload_data and upload_data.get("attachment_server_filename"):
            logging.info(f"Chat: Plik pomyślnie przesłany: {upload_data}")

            # Wyślij wiadomość Socket.IO z informacją o załączniku
            # Treść tekstowa może być pusta, jeśli wysyłamy tylko plik
            message_content_with_file = self.chat_input_var.get().strip()
            # Opcjonalnie: dodaj informację o pliku do treści, jeśli jest pusta
            if not message_content_with_file:
                message_content_with_file = (
                    f"[Plik: {upload_data.get('attachment_original_filename', 'plik')}]"
                )

            try:
                self.sio.emit(
                    "private_message",
                    {
                        "sender_id": self.chat_logged_in_user["user_id"],
                        "receiver_id": self.active_chat_partner_id,
                        "content": message_content_with_file,  # Treść wiadomości
                        "attachment_server_filename": upload_data.get(
                            "attachment_server_filename"
                        ),
                        "attachment_original_filename": upload_data.get(
                            "attachment_original_filename"
                        ),
                        "attachment_mimetype": upload_data.get("attachment_mimetype"),
                    },
                )
                self.chat_input_var.set(
                    ""
                )  # Wyczyść pole wprowadzania po wysłaniu wiadomości (jeśli była tam treść)
                self._send_typing_stop_event()
            except Exception as e:
                messagebox.showerror(
                    "Błąd Wysyłania Wiadomości",
                    f"Plik został przesłany, ale nie udało się wysłać wiadomości czatu:\n{e}",
                    parent=self.chat_page_frame,
                )
                logging.error(
                    f"Chat: Błąd podczas emitowania wiadomości z załącznikiem: {e}"
                )
        else:
            # Powinno być obsłużone przez error_message, ale na wszelki wypadek
            messagebox.showerror(
                "Błąd Wysyłania Pliku",
                "Otrzymano nieprawidłową odpowiedź z serwera po wysłaniu pliku.",
                parent=self.chat_page_frame,
            )
            logging.error(
                f"Chat: Nieprawidłowa odpowiedź serwera po wysłaniu pliku: {upload_data}"
            )

def _on_chat_input_key_press(self, event=None):
        """Wywoływana przy każdym klawiszu — deleguje logikę po zaktualizowaniu StringVar."""
        if (
            not self.chat_logged_in_user
            or not self.sio
            or not self.sio.connected
            or not self.chat_authenticated
        ):
            return
        # Upewnij się, że aktywny czat jest użytkownikiem lub pokojem
        if not (self.active_chat_type == "user" or self.active_chat_type == "room"):
            return

        if (
            self.active_chat_partner_id is None
            or self.active_chat_partner_id == self.chat_dashboard_placeholder_id
        ):
            return

        self.root.after_idle(self._handle_typing_start_logic)

def _handle_typing_start_logic(self):
        """Właściwa logika uruchamiana po zaktualizowaniu pola tekstowego."""
        current_text = self.chat_input_var.get()
        # Sygnalizowanie pisania tylko w chatach prywatnych (bo do grup byłoby problematyczne)
        if self.active_chat_type != "user":
            self._typing_sent_flag = (
                False  # Upewnij się, że flaga jest zresetowana, by nie wysyłać stop
            )
            return

        if current_text == "":
            return

        if self._typing_timeout_timer:
            self.root.after_cancel(self._typing_timeout_timer)
            self._typing_timeout_timer = None

        if not self._typing_sent_flag:
            try:
                self.sio.emit(
                    "typing_start",
                    {
                        "sender_id": self.chat_logged_in_user["user_id"],
                        "receiver_id": self.active_chat_partner_id,
                    },
                )
                self._typing_sent_flag = True
                logging.debug("Chat: Emitting typing_start.")
            except Exception as e:
                logging.error(f"Chat: Błąd emitowania typing_start: {e}")
                self._typing_sent_flag = False

        self._typing_timeout_timer = self.root.after(
            1500, self._check_typing_status_timeout
        )

def _check_typing_status_timeout(self):
        """Wywoływane po 1.5s bez aktywności — wysyła typing_stop niezależnie od fokusów."""
        self._send_typing_stop_event()

def _send_typing_stop_event(self):
        """Wysyła event 'typing_stop' do serwera."""
        if self._typing_sent_flag and self.sio and self.sio.connected:
            try:
                self.sio.emit(
                    "typing_stop",
                    {
                        "sender_id": self.chat_logged_in_user["user_id"],
                        "receiver_id": self.active_chat_partner_id,
                    },
                )
                logging.debug("Chat: Emitting typing_stop.")
            except Exception as e:
                logging.error(f"Chat: Błąd emitowania typing_stop: {e}")
            finally:
                self._typing_sent_flag = False

def _select_chat_attachment_dialog(self):
        """Otwiera dialog wyboru pliku i ustawia go jako oczekujący załącznik."""
        if not self.chat_logged_in_user:  # Podstawowe sprawdzenie
            return

        filepath = filedialog.askopenfilename(
            title="Wybierz plik do dołączenia", parent=self.chat_page_frame
        )
        if not filepath:
            return

        # Wstępna walidacja rozmiaru (jak poprzednio w _select_and_upload_chat_file)
        try:
            file_size_bytes = os.path.getsize(filepath)
            client_max_file_size_mb = 10
            if file_size_bytes > client_max_file_size_mb * 1024 * 1024:
                messagebox.showerror(
                    "Błąd Pliku",
                    f"Wybrany plik jest zbyt duży (maks. {client_max_file_size_mb} MB).",
                    parent=self.chat_page_frame,
                )
                return
        except OSError as e:
            messagebox.showerror(
                "Błąd Pliku",
                f"Nie można odczytać pliku:\n{filepath}\n{e}",
                parent=self.chat_page_frame,
            )
            return

        original_filename = os.path.basename(filepath)
        self._pending_chat_attachment = {
            "filepath": filepath,
            "original_filename": original_filename,
        }
        logging.info(
            f"Chat: Wybrano plik do załączenia (oczekujący): {original_filename}"
        )
        self._update_pending_attachment_ui()

def _clear_pending_chat_attachment(self):
        """Usuwa oczekujący załącznik."""
        self._pending_chat_attachment = None
        self._update_pending_attachment_ui()
        logging.info("Chat: Usunięto oczekujący załącznik.")

def _update_pending_attachment_ui(self):
        """Aktualizuje UI podglądu oczekującego załącznika."""
        if not (
            hasattr(self, "chat_pending_attachment_frame")
            and self.chat_pending_attachment_frame.winfo_exists()
        ):
            return

        if self._pending_chat_attachment:
            original_filename = self._pending_chat_attachment.get(
                "original_filename", "plik"
            )
            # Prosta ikona na podstawie nazwy (można rozbudować o mimetype jeśli mamy)
            file_icon = "📄"
            if original_filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            ):
                file_icon = "🖼️"

            self.chat_pending_attachment_icon_label.config(text=file_icon)
            self.chat_pending_attachment_name_label.config(text=original_filename)

            # Pokaż ramkę
            self.chat_pending_attachment_frame.grid(
                row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(2, 2)
            )  # Wstawia do wiersza 5
        else:
            # Ukryj ramkę
            self.chat_pending_attachment_frame.grid_remove()

def _send_chat_message(self, event=None):
        # Walidacja stanu czatu
        if (
            not self.chat_logged_in_user
            or not self.sio
            or not self.sio.connected
            or not self.chat_authenticated
        ):
            messagebox.showwarning(
                "Czat",
                "Musisz być zalogowany i połączony, aby wysyłać wiadomości.",
                parent=self.chat_page_frame,
            )
            return
        if not (self.active_chat_type == "user" or self.active_chat_type == "room"):
            messagebox.showwarning(
                "Czat",
                "Wybierz partnera czatu lub pokój grupowy.",
                parent=self.chat_page_frame,
            )
            return

        message_content = self.chat_input_var.get().strip()
        replied_to_id = None
        if self._current_reply_message_data:
            replied_to_id = self._current_reply_message_data.get("id")

        # Jeżeli brak treści i brak załącznika -> nic nie wysyłaj
        if not message_content and not self._pending_chat_attachment:
            return

        # Przygotuj dane do wysłania
        payload = {
            "sender_id": self.chat_logged_in_user["user_id"],
            "content": message_content,
        }
        # Kierowanie wiadomości
        if self.active_chat_type == "user":
            payload["receiver_id"] = self.active_chat_partner_id
        elif self.active_chat_type == "room":
            payload["room_id"] = self.active_chat_partner_id

        if replied_to_id:
            payload["replied_to_message_id"] = replied_to_id

        # Obsługa załącznika (kopiujemy istniejący blok logiczny z `_emit_chat_message_with_attachment`)
        if self._pending_chat_attachment:
            filepath = self._pending_chat_attachment["filepath"]
            original_name = self._pending_chat_attachment["original_filename"]

            upload_win = tk.Toplevel(
                self.chat_page_frame
            )  # ... (standardowy kod progressbar) ...

            try:
                file_obj = open(filepath, "rb")
                files_payload = {
                    "file": (
                        original_name,
                        file_obj,
                        mimetypes.guess_type(filepath)[0] or "application/octet-stream",
                    )
                }

                def _upload_and_then_send_socket_message_thread(
                    files_payload_local,
                    progress_window_local,
                    file_to_close_local,
                    payload_local,  # Teraz przekazujemy cały payload zamiast tylko text_content_local i replied_to_id
                ):
                    try:
                        resp = requests.post(
                            f"{self.chat_server_url}/upload_file",
                            files=files_payload_local,
                            timeout=60,
                        )
                        resp.raise_for_status()
                        upload_data = resp.json()
                        if progress_window_local.winfo_exists():
                            progress_window_local.destroy()

                        # Dodaj dane załącznika do payloadu
                        payload_local["attachment_server_filename"] = upload_data.get(
                            "attachment_server_filename"
                        )
                        payload_local["attachment_original_filename"] = upload_data.get(
                            "attachment_original_filename"
                        )
                        payload_local["attachment_mimetype"] = upload_data.get(
                            "attachment_mimetype"
                        )

                        self.root.after(
                            0, self._emit_chat_message, payload_local
                        )  # Nowa/uproszczona metoda emitująca
                    except Exception as e:
                        err = str(e)
                        logging.error(f"Błąd wysyłania pliku: {err}")
                        if progress_window_local.winfo_exists():
                            progress_window_local.destroy()
                        self.root.after(
                            0,
                            lambda: messagebox.showerror(
                                "Błąd Wysyłania Pliku", err, parent=self.chat_page_frame
                            ),
                        )
                        self.root.after(0, self._clear_pending_chat_attachment)
                    finally:
                        if file_to_close_local and not file_to_close_local.closed:
                            file_to_close_local.close()

                threading.Thread(
                    target=_upload_and_then_send_socket_message_thread,
                    args=(files_payload, upload_win, file_obj, payload),
                    daemon=True,
                ).start()

            except Exception as e:
                logging.error(f"Przygotowanie pliku nie powiodło się: {e}")
                messagebox.showerror(
                    "Błąd Wysyłania", str(e), parent=self.chat_page_frame
                )
                if "upload_win" in locals() and upload_win.winfo_exists():
                    upload_win.destroy()
                if "file_obj" in locals() and not file_obj.closed:
                    file_obj.close()
                self._clear_pending_chat_attachment()

        # Wysyłka samej wiadomości tekstowej (bez załącznika)
        elif message_content:
            self._emit_chat_message(payload)

def _emit_chat_message(self, payload: dict):
        """
        Faktycznie emituje wiadomość Socket.IO na serwer.
        Teraz ZAWSZE emituje event 'send_message'.
        """
        event_name = "send_message"
        log_message = ""
        if (
            "room_id" in payload and payload["room_id"] is not None
        ):  # Sprawdź czy room_id nie jest None
            log_message = (
                f"Chat: Emitting '{event_name}' for GROUP to room {payload['room_id']}"
            )
        elif (
            "receiver_id" in payload and payload["receiver_id"] is not None
        ):  # Sprawdź czy receiver_id nie jest None
            log_message = f"Chat: Emitting '{event_name}' for PRIVATE to user {payload.get('receiver_id')}"
        else:
            logging.error(
                f"Chat: Próba wysłania wiadomości ({event_name}) bez room_id i bez receiver_id. Payload: {payload}"
            )
            messagebox.showerror(
                "Błąd Wysyłania",
                "Błąd wewnętrzny: Brak odbiorcy lub pokoju.",
                parent=self.chat_page_frame,
            )
            return

        logging.info(log_message)

        try:
            self.sio.emit(event_name, payload)  # Emituj event 'send_message'
            self.chat_input_var.set("")
            self._clear_pending_chat_attachment()
            self._send_typing_stop_event()
            self._cancel_reply_mode()
        except Exception as e:
            messagebox.showerror(
                "Błąd Wysyłania",
                f"Nie udało się wysłać wiadomości:\n{e}",
                parent=self.chat_page_frame,
            )
            logging.error(f"Chat: Błąd emitowania wiadomości ({event_name}): {e}")

__all__ = [
    "_select_and_upload_chat_file",
    "_upload_file_thread",
    "_handle_file_upload_response",
    "_on_chat_input_key_press",
    "_handle_typing_start_logic",
    "_check_typing_status_timeout",
    "_send_typing_stop_event",
    "_select_chat_attachment_dialog",
    "_clear_pending_chat_attachment",
    "_update_pending_attachment_ui",
    "_send_chat_message",
    "_emit_chat_message",
]
