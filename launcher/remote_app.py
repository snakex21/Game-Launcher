"""Aplikacja Flask pilota WWW (bez Tk - testowalna).

Bezpieczeństwo:
* każde żądanie wymaga tokenu: nagłówek ``X-Remote-Token``, parametr
  ``?token=`` (tylko przy pierwszym wejściu - potem ciasteczko) albo
  ciasteczko ``gl_remote_token`` (HttpOnly, SameSite=Strict);
* uruchamianie/zamykanie gier tylko przez POST (GET nie zmienia stanu);
* serwer domyślnie nasłuchuje tylko na 127.0.0.1 (patrz ``remote_bind_host``).
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import urllib.parse
from typing import Callable, Iterable, Optional

from flask import Flask, Response, abort, jsonify, redirect, request, send_file

TOKEN_HEADER = "X-Remote-Token"
TOKEN_COOKIE = "gl_remote_token"
LOCALHOST = "127.0.0.1"
ALL_INTERFACES = "0.0.0.0"


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def remote_bind_host(allow_lan: bool) -> str:
    return ALL_INTERFACES if allow_lan else LOCALHOST


def token_matches(expected: str, provided: Optional[str]) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))


def create_remote_app(
    *,
    token: str,
    list_games: Callable[[], Iterable[dict]],
    running_game: Callable[[], Optional[str]],
    launch: Callable[[str], None],
    close: Callable[[str], None],
    has_game: Callable[[str], bool],
    cover_path: Callable[[str], Optional[str]] = lambda name: None,
    is_running: Callable[[], bool] = lambda: True,
) -> Flask:
    """Tworzy aplikację pilota. Funkcje zwrotne łączą ją z launcherem."""
    if not token:
        raise ValueError("Pilot WWW wymaga niepustego tokenu.")

    app = Flask(__name__)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    def _provided_token() -> Optional[str]:
        return (
            request.headers.get(TOKEN_HEADER)
            or request.args.get("token")
            or request.cookies.get(TOKEN_COOKIE)
        )

    @app.before_request
    def _check_auth():
        if not is_running():
            return "Serwer zdalnego sterowania jest zatrzymany.", 503
        if not token_matches(token, _provided_token()):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Brak autoryzacji - nieprawidłowy token."}), 401
            return Response(_UNAUTHORIZED_HTML, status=401, mimetype="text/html")
        return None

    @app.after_request
    def _security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/")
    def index():
        if "token" in request.args:
            # Token z adresu zamieniamy na ciasteczko i usuwamy go z paska adresu.
            response = redirect("/")
            response.set_cookie(
                TOKEN_COOKIE, token, httponly=True, samesite="Strict", max_age=30 * 24 * 3600
            )
            return response
        return Response(_INDEX_HTML.replace("__TOKEN_JSON__", json.dumps(token)), mimetype="text/html")

    @app.route("/api/games")
    def api_games():
        games = []
        for game in list_games():
            encoded = urllib.parse.quote(game["name"], safe="")
            games.append({**game, "cover_url": f"/cover/{encoded}"})
        return jsonify(games)

    @app.route("/api/status")
    def api_status():
        return jsonify({"running_game": running_game()})

    @app.route("/api/launch/<path:game_name>", methods=["POST"])
    def api_launch(game_name):
        if not has_game(game_name):
            return jsonify({"error": f"Nie znaleziono gry „{game_name}” w bibliotece."}), 404
        launch(game_name)
        return jsonify({"ok": True, "action": "launch", "game": game_name})

    @app.route("/api/close/<path:game_name>", methods=["POST"])
    def api_close(game_name):
        if not has_game(game_name):
            return jsonify({"error": f"Nie znaleziono gry „{game_name}” w bibliotece."}), 404
        close(game_name)
        return jsonify({"ok": True, "action": "close", "game": game_name})

    @app.route("/cover/<path:game_name>")
    def cover(game_name):
        path = cover_path(game_name)
        if not path or not os.path.isfile(path):
            abort(404)
        return send_file(path)

    return app


_UNAUTHORIZED_HTML = """<!DOCTYPE html>
<html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Game Launcher Remote</title>
<style>body{font-family:system-ui,sans-serif;background:#1e1e1e;color:#ddd;padding:24px;max-width:560px;margin:auto}</style>
</head><body><h1>Brak dostępu</h1>
<p>Otwórz pełny adres z tokenem, który widać w launcherze:
<b>Ustawienia → Zdalne sterowanie</b>.</p></body></html>
"""

_INDEX_HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Game Launcher Remote</title>
<style>
:root { --bg:#1e1e1e; --text:#ddd; --muted:#888; --border:#333; --input:#2e2e2e; --green:#aaffaa; --red:#ffaaaa; --cover:60px; }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); margin:0; padding:10px; }
.container { max-width:800px; margin:10px auto; }
h1 { text-align:center; color:#ccc; margin-bottom:15px; font-size:1.5em; }
#status-bar { text-align:center; padding:8px; margin-bottom:15px; background:#2a2a2a; border-radius:4px; font-size:.9em; min-height:1.2em; }
#search-input { width:calc(100% - 22px); padding:10px; background:var(--input); color:var(--text); border:1px solid var(--border); border-radius:4px; font-size:1em; }
ul#game-list { list-style:none; padding:0; }
li.game-item { margin:5px 0; border-bottom:1px solid var(--border); padding:8px 5px; display:flex; align-items:center; gap:10px; }
li.game-item.hidden { display:none; }
li.empty { color:var(--muted); text-align:center; padding:24px 0; }
.game-cover img { width:var(--cover); height:auto; max-height:calc(var(--cover)*1.5); object-fit:cover; background:#333; }
.game-info { flex-grow:1; }
.game-name { font-size:1.1em; display:block; margin-bottom:3px; }
.game-playtime { font-size:.8em; color:var(--muted); display:block; }
.game-actions button { font-weight:bold; border:0; padding:6px 10px; margin-left:5px; border-radius:3px; font-size:.9em; cursor:pointer; }
.launch-btn { color:var(--green); background:#3a4a3a; }
.close-btn { color:var(--red); background:#4a3a3a; display:none; }
</style>
</head>
<body>
<div class="container">
  <h1>Game Launcher</h1>
  <div id="status-bar">Ładowanie statusu…</div>
  <input type="text" id="search-input" placeholder="Filtruj gry…">
  <ul id="game-list"><li class="empty">Ładowanie listy gier…</li></ul>
</div>
<script>
const TOKEN = __TOKEN_JSON__;
const statusBar = document.getElementById('status-bar');
const list = document.getElementById('game-list');
const search = document.getElementById('search-input');
let running = null, items = [];

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'X-Remote-Token': TOKEN } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
  return data;
}
function showStatus(text, color) { statusBar.textContent = text; statusBar.style.color = color; }

async function updateStatus() {
  try {
    running = (await api('/api/status')).running_game;
    if (running) showStatus('Uruchomiona gra: ' + running, 'var(--green)');
    else showStatus('Brak uruchomionej gry', 'var(--muted)');
  } catch (e) { running = null; showStatus('Błąd pobierania statusu: ' + e.message, 'var(--red)'); }
  items.forEach(li => { li.querySelector('.close-btn').style.display = li.dataset.name === running ? 'inline-block' : 'none'; });
}

async function act(action, name) {
  try {
    await api('/api/' + action + '/' + encodeURIComponent(name), { method: 'POST' });
    showStatus((action === 'launch' ? 'Uruchamianie: ' : 'Zamykanie: ') + name, 'var(--text)');
    setTimeout(updateStatus, 1500);
  } catch (e) { showStatus('Błąd: ' + e.message, 'var(--red)'); }
}

async function loadGames() {
  try {
    const games = await api('/api/games');
    list.innerHTML = ''; items = [];
    if (games.length === 0) { list.innerHTML = '<li class="empty">Biblioteka jest pusta. Dodaj gry w launcherze.</li>'; return; }
    games.forEach(game => {
      const li = document.createElement('li'); li.className = 'game-item'; li.dataset.name = game.name;
      const cover = document.createElement('div'); cover.className = 'game-cover';
      const img = document.createElement('img'); img.src = game.cover_url; img.alt = 'Okładka ' + game.name;
      img.onerror = function () { this.style.visibility = 'hidden'; };
      cover.appendChild(img);
      const info = document.createElement('div'); info.className = 'game-info';
      const nm = document.createElement('span'); nm.className = 'game-name'; nm.textContent = game.name;
      const pt = document.createElement('span'); pt.className = 'game-playtime'; pt.textContent = 'Czas gry: ' + game.playtime;
      info.append(nm, pt);
      const actions = document.createElement('div'); actions.className = 'game-actions';
      const launch = document.createElement('button'); launch.className = 'launch-btn'; launch.textContent = '▶ Uruchom';
      launch.onclick = () => act('launch', game.name);
      const close = document.createElement('button'); close.className = 'close-btn'; close.textContent = '■ Zamknij';
      close.onclick = () => act('close', game.name);
      actions.append(launch, close);
      li.append(cover, info, actions); list.appendChild(li); items.push(li);
    });
    updateStatus();
  } catch (e) { list.innerHTML = ''; const li = document.createElement('li'); li.className = 'empty'; li.textContent = 'Błąd ładowania listy gier: ' + e.message; list.appendChild(li); }
}

search.addEventListener('input', () => {
  const q = search.value.toLowerCase();
  items.forEach(li => li.classList.toggle('hidden', !li.dataset.name.toLowerCase().includes(q)));
});
loadGames();
setInterval(updateStatus, 5000);
</script>
</body>
</html>
"""

__all__ = [
    "TOKEN_HEADER",
    "TOKEN_COOKIE",
    "generate_token",
    "remote_bind_host",
    "token_matches",
    "create_remote_app",
]
