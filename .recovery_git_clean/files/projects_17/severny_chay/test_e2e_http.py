"""E2E-тесты: реальные HTTP-запросы (httpx) к реально запущенному uvicorn.

Сервер поднимается в отдельном потоке того же процесса, поэтому можно замокать
`main._client` до старта — сетевой стек (uvicorn -> fastapi -> handler) идёт
по-настоящему, но к Google AI обращений нет.
"""

import os
import socket
import threading
import time
from unittest import mock

# Ключ нужен лишь чтобы main.py прошёл проверку при импорте.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402

import main as m  # noqa: E402


# ---------------------------------------------------------------------------
# Фикстура: живой сервер в потоке
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_sessions():
    """Переключает хранилище сессий на изолированную in-memory БД между тестами."""
    m._db_path = ":memory:"
    m._db_conn = None  # при первом обращении создаст чистую in-memory БД
    yield
    m._db_conn = None


@pytest.fixture
def live_server(monkeypatch):
    """Поднимает настоящий uvicorn на свободном порту с замоканным Gemini.

    Возвращает строку base_url вида http://127.0.0.1:<port>.
    """
    client = mock.Mock()
    response = mock.Mock()
    response.text = "E2E-ответ"
    client.models.generate_content.return_value = response
    monkeypatch.setattr(m, "_client", client)

    port = _free_port()
    config = uvicorn.Config(m.app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # ждём готовности
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "uvicorn-сервер не стартовал за отведённое время"

    base = f"http://127.0.0.1:{port***REMOVED***"
    yield base

    server.should_exit = True
    thread.join(timeout=10)


def _free_port() -> int:
    """Возвращает свободный порт на loopback."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1***REMOVED***


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_e2e_index_serves_html(live_server):
    with httpx.Client() as c:
        r = c.get(live_server + "/")
        assert r.status_code == 200
        assert r.headers["content-type"***REMOVED***.startswith("text/html")
        assert "Северный чай" in r.text
        assert "Заказать" in r.text
        assert "/api/chat" in r.text


def test_e2e_chat_roundtrip(live_server):
    with httpx.Client() as c:
        r = c.post(live_server + "/api/chat", json={"message": "привет"***REMOVED***)
        assert r.status_code == 200
        data = r.json()
        assert data["reply"***REMOVED*** == "E2E-ответ"
        assert len(data["session_id"***REMOVED***) == 32


def test_e2e_chat_empty_message_400(live_server):
    with httpx.Client() as c:
        r = c.post(live_server + "/api/chat", json={"message": "   "***REMOVED***)
        assert r.status_code == 400


def test_e2e_chat_missing_body_422(live_server):
    with httpx.Client() as c:
        r = c.post(live_server + "/api/chat")
        assert r.status_code == 422  # FastAPI/pydantic валидация


def test_e2e_session_history_kept_over_real_http(live_server):
    with httpx.Client() as c:
        first = c.post(live_server + "/api/chat", json={"message": "один"***REMOVED***)
        sid = first.json()["session_id"***REMOVED***

        c.post(live_server + "/api/chat", json={"message": "два", "session_id": sid***REMOVED***)

    # оба реальных запроса дошли до модели; во втором — история (user,model,user)
    calls = m._client.models.generate_content.call_args_list
    assert len(calls) == 2
    contents = calls[1***REMOVED***.kwargs["contents"***REMOVED***
    assert len(contents) == 3
    assert contents[0***REMOVED***.parts[0***REMOVED***.text == "один"
    assert contents[1***REMOVED***.role == "model"
    assert contents[2***REMOVED***.parts[0***REMOVED***.text == "два"
