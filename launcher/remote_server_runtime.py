import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox

from werkzeug.serving import make_server

from launcher.config_store import (
    DEFAULT_CHAT_SERVER_PORT,
    DEFAULT_REMOTE_CONTROL_PORT,
    save_local_settings,
)
from launcher.remote_app import LOCALHOST, create_remote_app, generate_token, remote_bind_host
from launcher.paths import APP_DIR
from launcher.utils import IMAGES_FOLDER


def _ensure_remote_token(self):
    token = self.local_settings.get("remote_control_token")
    if not token:
        token = generate_token()
        self.local_settings["remote_control_token"] = token
        save_local_settings(self.local_settings)
    return token


def _remote_cover_path(self, game_name):
    game_data = self.games.get(game_name)
    if not game_data or not game_data.get("cover_image"):
        return None
    images_folder_abs = os.path.abspath(os.path.join(APP_DIR, IMAGES_FOLDER))
    cover_abs_path = os.path.abspath(os.path.join(APP_DIR, game_data["cover_image"]))
    try:
        inside = os.path.commonpath([images_folder_abs, cover_abs_path]) == images_folder_abs
    except ValueError:  # inne dyski
        inside = False
    return cover_abs_path if inside else None


def _start_flask_server(self):
    """Tworzy i uruchamia serwer pilota WWW w osobnym wątku."""
    if self._server_running or self._flask_thread is not None:
        logging.warning("Próba uruchomienia serwera pilota, gdy już działa.")
        return

    port_to_use = self.remote_server_port
    allow_lan = bool(self.local_settings.get("remote_control_bind_lan", False))
    host = remote_bind_host(allow_lan)
    ip_address = self._get_local_ip() if allow_lan else LOCALHOST
    if not ip_address:
        messagebox.showerror(
            "Błąd Sieci",
            "Nie można było ustalić lokalnego adresu IP.",
            parent=self.root,
        )
        self._update_server_status_ui(False)
        return

    token = _ensure_remote_token(self)

    def list_games():
        return [
            {
                "name": name,
                "playtime": self.format_play_time(self.games.get(name, {}).get("play_time", 0)),
            }
            for name in sorted(list(self.games.keys()), key=str.lower)
        ]

    def running_game():
        return next(iter(self.tracking_games), None) if self.tracking_games else None

    self._flask_app = create_remote_app(
        token=token,
        list_games=list_games,
        running_game=running_game,
        launch=lambda name: self.root.after(0, lambda gn=name: self.launch_game(gn)),
        close=lambda name: self.root.after(0, lambda gn=name: self.close_game(gn)),
        has_game=lambda name: name in self.games,
        cover_path=lambda name: _remote_cover_path(self, name),
        is_running=lambda: self._server_running,
    )
    try:
        self._remote_wsgi_server = make_server(host, port_to_use, self._flask_app, threaded=True)
    except OSError as e:
        self._flask_app = None
        logging.error(f"Nie można uruchomić pilota na {host}:{port_to_use}: {e}")
        if getattr(e, "winerror", None) == 10048 or e.errno in (98, 10048):
            text = (
                f"Port {port_to_use} jest już używany przez inną aplikację "
                "(np. serwer czatu używa domyślnie portu 5000).\n\nZmień port pilota w ustawieniach."
            )
        else:
            text = f"Nie można uruchomić serwera pilota na porcie {port_to_use}:\n{e}"
        messagebox.showerror("Błąd Serwera", text, parent=self.root)
        self._update_server_status_ui(False)
        return

    self._server_running = True
    self._flask_thread = threading.Thread(
        target=self._flask_server_target, args=(port_to_use,), daemon=True
    )
    self._flask_thread.start()
    self._remote_url = f"http://{ip_address}:{port_to_use}/?token={token}"
    self.root.after(100, lambda: self._update_server_status_ui(True, ip_address))


def _flask_server_target(self, port):
    """Pętla serwera pilota (wątek)."""
    server = getattr(self, "_remote_wsgi_server", None)
    if server is None:
        return
    try:
        logging.info(f"Pilot WWW nasłuchuje na {server.host}:{port}.")
        server.serve_forever()
        logging.info("Serwer pilota zakończył działanie.")
    except Exception:
        logging.exception("Nieoczekiwany błąd w wątku serwera pilota.")
        self.root.after(0, self._update_server_status_ui, False)
    finally:
        self._server_running = False
        self._flask_thread = None
        self._flask_app = None


def _stop_flask_server(self):
    """Zatrzymuje serwer pilota (zamyka gniazdo, zwalnia port)."""
    server = getattr(self, "_remote_wsgi_server", None)
    if not self._server_running and server is None:
        logging.info("Serwer pilota nie jest uruchomiony.")
        return

    logging.info("Zatrzymywanie serwera pilota...")
    self._server_running = False
    self._remote_wsgi_server = None
    if server is not None:
        # shutdown() czeka na zakończenie serve_forever - nie blokujemy wątku Tk.
        threading.Thread(
            target=lambda: (server.shutdown(), server.server_close()), daemon=True
        ).start()
    self._flask_thread = None
    self._flask_app = None
    self._update_server_status_ui(False)


def _update_server_status_ui(self, is_running, ip_address=None):
    """Aktualizuje etykietę URL i stan Checkbuttona w UI."""
    if hasattr(self, "remote_url_label") and self.remote_url_label.winfo_exists():
        if is_running and ip_address:
            url = getattr(self, "_remote_url", None) or f"http://{ip_address}:{self.remote_server_port}"
            self.remote_url_label.config(text=url, foreground="lightgreen")
        else:
            self.remote_url_label.config(text="Serwer wyłączony", foreground="gray")

    if hasattr(self, "remote_server_enabled_var"):
        if self.remote_server_enabled_var.get() != is_running:
            self.remote_server_enabled_var.set(is_running)
            self.local_settings["remote_control_enabled"] = is_running
            save_local_settings(self.local_settings)


def _toggle_remote_server(self):
    """Włącza lub wyłącza serwer zdalny na podstawie Checkbuttona."""
    should_be_enabled = self.remote_server_enabled_var.get()

    if self.local_settings.get("remote_control_enabled") != should_be_enabled:
        self.local_settings["remote_control_enabled"] = should_be_enabled
        save_local_settings(self.local_settings)
        logging.info(f"Zmieniono ustawienie zdalnego sterowania na: {should_be_enabled}")

    if should_be_enabled:
        logging.info("Użytkownik włączył zdalne sterowanie. Uruchamianie serwera...")
        self._start_flask_server()
    else:
        logging.info("Użytkownik wyłączył zdalne sterowanie. Zatrzymywanie serwera...")
        self._stop_flask_server()


def _save_remote_port(self):
    """Zapisuje nowy port i restartuje serwer, jeśli jest aktywny."""
    try:
        new_port = self.remote_port_var.get()
        if not (1024 < new_port < 65535):
            raise ValueError("Port musi być liczbą między 1025 a 65534.")

        current_port = self.local_settings.get("remote_control_port", DEFAULT_REMOTE_CONTROL_PORT)
        if new_port == DEFAULT_CHAT_SERVER_PORT:
            raise ValueError(
                f"Port {DEFAULT_CHAT_SERVER_PORT} jest zarezerwowany dla serwera czatu. Wybierz inny."
            )

        if new_port != current_port:
            self.local_settings["remote_control_port"] = new_port
            save_local_settings(self.local_settings)
            self.remote_server_port = new_port
            logging.info(f"Zmieniono port zdalnego sterowania na: {new_port}")

            if self._server_running:
                messagebox.showinfo(
                    "Restart Serwera",
                    "Port został zmieniony. Serwer zdalny zostanie teraz zrestartowany.",
                    parent=self.settings_page_frame,
                )
                self._stop_flask_server()
                self.root.after(500, self._start_flask_server)
            else:
                messagebox.showinfo(
                    "Zapisano Port",
                    f"Nowy port ({new_port}) został zapisany. Serwer zostanie uruchomiony na tym porcie przy następnym włączeniu.",
                    parent=self.settings_page_frame,
                )

    except tk.TclError:
        messagebox.showerror(
            "Błąd Wartości",
            "Port musi być liczbą całkowitą.",
            parent=self.settings_page_frame,
        )
    except ValueError as e:
        messagebox.showerror("Błąd Wartości", str(e), parent=self.settings_page_frame)
    except Exception as e:
        logging.exception("Nieoczekiwany błąd podczas zapisywania portu.")
        messagebox.showerror(
            "Błąd",
            f"Wystąpił nieoczekiwany błąd: {e}",
            parent=self.settings_page_frame,
        )


def _toggle_remote_lan(self):
    """Przełącza nasłuch pilota: tylko ten komputer albo cała sieć LAN."""
    allow_lan = bool(self.remote_lan_var.get())
    self.local_settings["remote_control_bind_lan"] = allow_lan
    save_local_settings(self.local_settings)
    if self._server_running:
        self._stop_flask_server()
        self.root.after(500, self._start_flask_server)


def _regenerate_remote_token(self):
    """Nowy token pilota - stare linki/ciasteczka przestają działać."""
    self.local_settings["remote_control_token"] = generate_token()
    save_local_settings(self.local_settings)
    if self._server_running:
        self._stop_flask_server()
        self.root.after(500, self._start_flask_server)
    messagebox.showinfo(
        "Nowy token",
        "Wygenerowano nowy token pilota. Otwórz na telefonie nowy adres z ustawień.",
        parent=self.settings_page_frame,
    )


__all__ = [
    "_toggle_remote_lan",
    "_regenerate_remote_token",
    "_start_flask_server",
    "_flask_server_target",
    "_stop_flask_server",
    "_update_server_status_ui",
    "_toggle_remote_server",
    "_save_remote_port",
]
