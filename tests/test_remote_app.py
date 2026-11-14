"""Pilot WWW: autoryzacja tokenem, POST do akcji, bind na localhost."""
import pytest

from launcher.remote_app import (
    TOKEN_COOKIE,
    TOKEN_HEADER,
    create_remote_app,
    remote_bind_host,
    token_matches,
)

TOKEN = "test-token-123"


@pytest.fixture
def remote():
    calls = []
    games = {"Gothic II": 7200, "Mafia": 0}
    app = create_remote_app(
        token=TOKEN,
        list_games=lambda: [{"name": n, "playtime": str(t)} for n, t in games.items()],
        running_game=lambda: None,
        launch=lambda name: calls.append(("launch", name)),
        close=lambda name: calls.append(("close", name)),
        has_game=lambda name: name in games,
    )
    app.config["TESTING"] = True
    return app.test_client(), calls


def test_default_bind_is_localhost():
    assert remote_bind_host(False) == "127.0.0.1"
    assert remote_bind_host(True) == "0.0.0.0"


def test_empty_token_is_rejected():
    with pytest.raises(ValueError):
        create_remote_app(
            token="", list_games=list, running_game=lambda: None,
            launch=print, close=print, has_game=lambda n: True,
        )


def test_token_matches():
    assert token_matches("abc", "abc")
    assert not token_matches("abc", "abd")
    assert not token_matches("abc", None)
    assert not token_matches("", "")


@pytest.mark.parametrize("path", ["/", "/api/games", "/api/status", "/cover/Mafia"])
def test_requests_without_token_are_rejected(remote, path):
    client, _ = remote
    assert client.get(path).status_code == 401


def test_wrong_token_is_rejected(remote):
    client, calls = remote
    assert client.get("/api/games", headers={TOKEN_HEADER: "zly"}).status_code == 401
    assert client.post("/api/launch/Mafia", headers={TOKEN_HEADER: "zly"}).status_code == 401
    assert client.get("/?token=zly").status_code == 401
    assert calls == []


def test_games_with_header_token(remote):
    client, _ = remote
    response = client.get("/api/games", headers={TOKEN_HEADER: TOKEN})
    assert response.status_code == 200
    assert [g["name"] for g in response.get_json()] == ["Gothic II", "Mafia"]
    assert response.get_json()[0]["cover_url"] == "/cover/Gothic%20II"


def test_launch_requires_post(remote):
    client, calls = remote
    assert client.get("/api/launch/Mafia", headers={TOKEN_HEADER: TOKEN}).status_code == 405
    # stary, niezabezpieczony endpoint GET /launch/<gra> już nie istnieje
    assert client.get("/launch/Mafia", headers={TOKEN_HEADER: TOKEN}).status_code == 404
    assert calls == []


def test_launch_and_close(remote):
    client, calls = remote
    assert client.post("/api/launch/Gothic%20II", headers={TOKEN_HEADER: TOKEN}).status_code == 200
    assert client.post("/api/close/Mafia", headers={TOKEN_HEADER: TOKEN}).status_code == 200
    assert calls == [("launch", "Gothic II"), ("close", "Mafia")]


def test_unknown_game_404_with_message(remote):
    client, calls = remote
    response = client.post("/api/launch/Nieznana", headers={TOKEN_HEADER: TOKEN})
    assert response.status_code == 404
    assert "Nieznana" in response.get_json()["error"]
    assert calls == []


def test_query_token_sets_cookie_and_strips_url(remote):
    client, _ = remote
    response = client.get(f"/?token={TOKEN}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    set_cookie = response.headers["Set-Cookie"]
    assert TOKEN_COOKIE in set_cookie
    assert "HttpOnly" in set_cookie and "SameSite=Strict" in set_cookie
    page = client.get("/")  # klient testowy niesie ciasteczko
    assert page.status_code == 200
    assert b"Game Launcher" in page.data


def test_stopped_server_returns_503():
    app = create_remote_app(
        token=TOKEN, list_games=list, running_game=lambda: None,
        launch=print, close=print, has_game=lambda n: True, is_running=lambda: False,
    )
    response = app.test_client().get("/api/status", headers={TOKEN_HEADER: TOKEN})
    assert response.status_code == 503
