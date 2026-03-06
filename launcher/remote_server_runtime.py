import logging
import os
import threading
import urllib.parse
import tkinter as tk
from tkinter import messagebox

from flask import Flask, abort, jsonify, redirect, render_template_string, send_file, url_for

from launcher.config_store import save_local_settings
from launcher.utils import IMAGES_FOLDER


def _start_flask_server(self):
    """Tworzy i uruchamia serwer Flask w osobnym wątku."""
    if self._server_running or self._flask_thread is not None:
        logging.warning("Próba uruchomienia serwera Flask, gdy już działa.")
        return

    port_to_use = self.remote_server_port
    ip_address = self._get_local_ip()
    if not ip_address:
        messagebox.showerror(
            "Błąd Sieci",
            "Nie można było ustalić lokalnego adresu IP.",
            parent=self.root,
        )
        self._update_server_status_ui(False)
        return

    self._server_running = True
    self._flask_app = Flask(__name__)
    flask_log = logging.getLogger("werkzeug")
    flask_log.setLevel(logging.ERROR)

    @self._flask_app.route("/")
    def index():
        if not self._server_running:
            return "Serwer został zatrzymany.", 503

        html_content = """
            <!DOCTYPE html>
            <html lang="pl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>Game Launcher Remote</title>
                <style>
                    :root {
                        --bg-color: #1e1e1e;
                        --text-color: #dddddd;
                        --text-muted-color: #888888;
                        --border-color: #333333;
                        --input-bg-color: #2e2e2e;
                        --link-color: #aabbff;
                        --link-visited-color: #99aaff;
                        --accent-green: #aaffaa;
                        --accent-red: #ffaaaa;
                        --cover-size: 60px;
                    }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        background-color: var(--bg-color);
                        color: var(--text-color);
                        margin: 0;
                        padding: 10px;
                    }
                    .container { max-width: 800px; margin: 10px auto; }
                    h1 { text-align: center; color: #cccccc; margin-bottom: 15px; font-size: 1.5em; }
                    #status-bar {
                        text-align: center; padding: 8px; margin-bottom: 15px;
                        background-color: #2a2a2a; border-radius: 4px; font-size: 0.9em; min-height: 1.2em;
                    }
                    #search-container { margin-bottom: 15px; }
                    #search-input {
                        width: calc(100% - 22px);
                        padding: 10px;
                        background-color: var(--input-bg-color);
                        color: var(--text-color);
                        border: 1px solid var(--border-color);
                        border-radius: 4px;
                        font-size: 1em;
                    }
                    #game-list-container { margin-top: 15px; }
                    ul#game-list { list-style: none; padding: 0; }
                    li.game-item {
                        margin: 5px 0; border-bottom: 1px solid var(--border-color); padding: 8px 5px;
                        display: flex;
                        align-items: center; gap: 10px;
                    }
                    li.game-item.hidden { display: none; }
                    .game-cover img {
                        width: var(--cover-size); height: auto; max-height: calc(var(--cover-size) * 1.5);
                        object-fit: cover; vertical-align: middle; background-color: #333;
                    }
                    .game-info { flex-grow: 1; }
                    .game-name { font-size: 1.1em; display: block; margin-bottom: 3px; }
                    .game-playtime { font-size: 0.8em; color: var(--text-muted-color); display: block;}
                    .game-actions a {
                        font-weight: bold; text-decoration: none; padding: 5px 8px; margin-left: 5px;
                        border-radius: 3px; font-size: 0.9em; white-space: nowrap;
                    }
                    .launch-link { color: var(--accent-green); background-color: #3a4a3a; }
                    .close-link { color: var(--accent-red); background-color: #4a3a3a; }
                    a:visited { color: var(--link-visited-color); }
                    a { transition: opacity 0.2s ease; }
                    a:hover { opacity: 0.7; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Game Launcher</h1>
                    <div id="status-bar">Ładowanie statusu...</div>

                    <div id="search-container">
                        <input type="text" id="search-input" placeholder="Filtruj gry...">
                    </div>

                    <div id="game-list-container">
                        <ul id="game-list">
                            <li>Ładowanie listy gier...</li>
                        </ul>
                    </div>
                </div>

                <script>
                    const statusBar = document.getElementById('status-bar');
                    const gameListUl = document.getElementById('game-list');
                    const searchInput = document.getElementById('search-input');
                    let currentRunningGame = null;
                    let allGameItems = [];

                    async function updateStatus() {
                        try {
                            const response = await fetch('/api/status');
                            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
                            const data = await response.json();
                            currentRunningGame = data.running_game;
                            if (currentRunningGame) {
                                statusBar.textContent = `Uruchomiona Gra: ${currentRunningGame}`;
                                statusBar.style.color = 'var(--accent-green)';
                            } else {
                                statusBar.textContent = 'Brak uruchomionej gry';
                                statusBar.style.color = 'var(--text-muted-color)';
                            }
                            updateCloseButtonsVisibility();
                        } catch (error) {
                            console.error('Błąd pobierania statusu:', error);
                            statusBar.textContent = 'Błąd pobierania statusu';
                            statusBar.style.color = 'var(--accent-red)';
                            currentRunningGame = null;
                            updateCloseButtonsVisibility();
                        }
                    }

                    async function loadGames() {
                        try {
                            const response = await fetch('/api/games');
                            if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
                            const games = await response.json();

                            gameListUl.innerHTML = '';
                            allGameItems = [];

                            if (games.length === 0) {
                                gameListUl.innerHTML = '<li>Brak gier w bibliotece.</li>';
                                return;
                            }

                            games.forEach(game => {
                                const li = document.createElement('li');
                                li.classList.add('game-item');
                                li.dataset.gameName = game.name;

                                const coverDiv = document.createElement('div');
                                coverDiv.classList.add('game-cover');
                                const img = document.createElement('img');
                                img.src = game.cover_url;
                                img.alt = `Okładka ${game.name}`;
                                img.onerror = function() { this.style.display='none'; }
                                coverDiv.appendChild(img);

                                const infoDiv = document.createElement('div');
                                infoDiv.classList.add('game-info');
                                const nameSpan = document.createElement('span');
                                nameSpan.classList.add('game-name');
                                nameSpan.textContent = game.name;
                                const timeSpan = document.createElement('span');
                                timeSpan.classList.add('game-playtime');
                                timeSpan.textContent = `Czas gry: ${game.playtime}`;
                                infoDiv.appendChild(nameSpan);
                                infoDiv.appendChild(timeSpan);

                                const actionsDiv = document.createElement('div');
                                actionsDiv.classList.add('game-actions');
                                const launchLink = document.createElement('a');
                                launchLink.href = `/launch/${encodeURIComponent(game.name)}`;
                                launchLink.textContent = '▶ Uruchom';
                                launchLink.classList.add('launch-link');
                                const closeLink = document.createElement('a');
                                closeLink.href = `/close/${encodeURIComponent(game.name)}`;
                                closeLink.textContent = '■ Zamknij';
                                closeLink.classList.add('close-link');
                                closeLink.style.display = 'none';

                                actionsDiv.appendChild(launchLink);
                                actionsDiv.appendChild(closeLink);

                                li.appendChild(coverDiv);
                                li.appendChild(infoDiv);
                                li.appendChild(actionsDiv);
                                gameListUl.appendChild(li);
                                allGameItems.push(li);
                            });

                            updateStatus();
                        } catch (error) {
                            console.error('Błąd pobierania listy gier:', error);
                            gameListUl.innerHTML = '<li>Błąd ładowania listy gier.</li>';
                        }
                    }

                    function updateCloseButtonsVisibility() {
                        allGameItems.forEach(item => {
                            const closeButton = item.querySelector('.close-link');
                            if (closeButton) {
                                if (item.dataset.gameName === currentRunningGame) {
                                    closeButton.style.display = 'inline-block';
                                } else {
                                    closeButton.style.display = 'none';
                                }
                            }
                        });
                     }

                    function filterGames() {
                        const searchTerm = searchInput.value.toLowerCase();
                        allGameItems.forEach(item => {
                            const gameName = item.dataset.gameName.toLowerCase();
                            if (gameName.includes(searchTerm)) {
                                item.classList.remove('hidden');
                            } else {
                                item.classList.add('hidden');
                            }
                        });
                    }

                    loadGames();
                    setInterval(updateStatus, 5000);
                    searchInput.addEventListener('input', filterGames);
                </script>
            </body>
            </html>
            """
        return render_template_string(html_content)

    @self._flask_app.route("/api/games")
    def api_games():
        if not self._server_running:
            return jsonify({"error": "Server stopped"}), 503
        try:
            game_list = []
            sorted_game_names = sorted(list(self.games.keys()), key=str.lower)
            for game_name in sorted_game_names:
                game_data = self.games.get(game_name, {})
                encoded_name = urllib.parse.quote(game_name.encode("utf-8"))
                game_list.append(
                    {
                        "name": game_name,
                        "playtime": self.format_play_time(game_data.get("play_time", 0)),
                        "cover_url": f"/cover/{encoded_name}",
                    }
                )
            return jsonify(game_list)
        except Exception:
            logging.exception("Błąd w endpoint /api/games")
            return jsonify({"error": "Internal server error"}), 500

    @self._flask_app.route("/api/status")
    def api_status():
        if not self._server_running:
            return jsonify({"error": "Server stopped"}), 503
        try:
            running_game = None
            if self.tracking_games:
                running_game = next(iter(self.tracking_games))
            return jsonify({"running_game": running_game})
        except Exception:
            logging.exception("Błąd w endpoint /api/status")
            return jsonify({"error": "Internal server error"}), 500

    @self._flask_app.route("/cover/<encoded_game_name>")
    def serve_cover(encoded_game_name):
        if not self._server_running:
            return "...", 503
        try:
            game_name = urllib.parse.unquote(encoded_game_name)
            game_data = self.games.get(game_name)
            if not game_data:
                abort(404)
            cover_rel_path = game_data.get("cover_image")
            if not cover_rel_path:
                abort(404)
            images_folder_abs = os.path.abspath(IMAGES_FOLDER)
            cover_abs_path = os.path.abspath(os.path.join(os.getcwd(), cover_rel_path))
            if os.path.commonpath([images_folder_abs, cover_abs_path]) == images_folder_abs and os.path.exists(
                cover_abs_path
            ):
                return send_file(cover_abs_path)
            else:
                abort(404)
        except Exception:
            abort(500)

    @self._flask_app.route("/launch/<game_name>")
    def launch(game_name):
        if not self._server_running:
            return "...", 503
        decoded_game_name = urllib.parse.unquote(game_name)
        if decoded_game_name in self.games:
            self.root.after(0, lambda gn=decoded_game_name: self.launch_game(gn))
            return redirect(url_for("index"))
        else:
            return "...", 404

    @self._flask_app.route("/close/<game_name>")
    def close(game_name):
        if not self._server_running:
            return "...", 503
        decoded_game_name = urllib.parse.unquote(game_name)
        if decoded_game_name in self.games:
            self.root.after(0, lambda gn=decoded_game_name: self.close_game(gn))
            return redirect(url_for("index"))
        else:
            return "...", 404

    self._flask_thread = threading.Thread(
        target=self._flask_server_target, args=(port_to_use,), daemon=True
    )
    self._flask_thread.start()

    self.root.after(100, lambda: self._update_server_status_ui(True, ip_address))


def _flask_server_target(self, port):
    """Funkcja docelowa dla wątku serwera Flask."""
    try:
        logging.info(f"Uruchamianie serwera Flask na porcie {port}...")
        self._flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
        logging.info("Serwer Flask zakończył działanie.")
    except OSError as e:
        if e.errno == 98 or e.errno == 10048:
            logging.error(f"Port {port} jest już zajęty!")
            self.root.after(
                0,
                lambda p=port: messagebox.showerror(
                    "Błąd Serwera",
                    f"Port {p} jest już używany przez inną aplikację.",
                    parent=self.root,
                ),
            )
        else:
            logging.exception("Błąd podczas uruchamiania serwera Flask.")
            self.root.after(
                0,
                lambda err=e: messagebox.showerror(
                    "Błąd Serwera",
                    f"Nie można uruchomić serwera Flask:\n{err}",
                    parent=self.root,
                ),
            )
        self.root.after(0, self._update_server_status_ui, False)
    except Exception:
        logging.exception("Nieoczekiwany błąd w wątku serwera Flask.")
        self.root.after(0, self._update_server_status_ui, False)
    finally:
        self._server_running = False
        self._flask_thread = None
        self._flask_app = None


def _stop_flask_server(self):
    """Zatrzymuje serwer Flask (na razie przez ustawienie flagi)."""
    if not self._server_running:
        logging.info("Serwer Flask nie jest uruchomiony.")
        return

    logging.info("Zatrzymywanie serwera Flask (ustawianie flagi)...")
    self._server_running = False
    self._flask_thread = None
    self._flask_app = None
    self._update_server_status_ui(False)


def _update_server_status_ui(self, is_running, ip_address=None):
    """Aktualizuje etykietę URL i stan Checkbuttona w UI."""
    if hasattr(self, "remote_url_label") and self.remote_url_label.winfo_exists():
        if is_running and ip_address:
            url = f"http://{ip_address}:{self.remote_server_port}"
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

        current_port = self.local_settings.get("remote_control_port", 5000)

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


__all__ = [
    "_start_flask_server",
    "_flask_server_target",
    "_stop_flask_server",
    "_update_server_status_ui",
    "_toggle_remote_server",
    "_save_remote_port",
]
