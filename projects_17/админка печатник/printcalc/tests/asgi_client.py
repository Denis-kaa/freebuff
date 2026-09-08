"""Минимальный синхронный ASGI-клиент для интеграционных тестов printcalc_web.

Причина существования: среда имеет starlette 0.27 + httpx 0.28, где
fastapi.testclient.TestClient падает (TestClient передаёт kwarg `app=`,
удалённый из httpx 0.28). Вместо модификации системных пакетов — прямой
вызов ASGI-приложения: стабильно для любых версий starlette/httpx и не
требует сети. Интерфейс повторяет привычный httpx-стиль
(.get/.post/.patch/.put, json=, params=), чтобы обратный переход на
TestClient после обновления starlette был однострочным.
"""

from __future__ import annotations

import asyncio
import json as jsonlib
from typing import Any
from urllib.parse import urlencode


class ASGIResponse:
    """Минимальный ответ: статус, заголовки, тело."""

    def __init__(self, status: int, headers: list[tuple[bytes, bytes]], body: bytes) -> None:
        self.status_code = status
        self.headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in headers}
        self._body = body

    @property
    def text(self) -> str:
        return self._body.decode("utf-8")

    def json(self) -> Any:
        return jsonlib.loads(self._body)


class ASGITestClient:
    """Синхронный клиент поверх ASGI-приложения (без сокетов и lifespan)."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def request(
        self,
        method: str,
        path: str,
        json: Any = None,  # noqa: A002 — имя повторяет httpx-API намеренно
        params: dict[str, Any] | None = None,
    ) -> ASGIResponse:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        query = urlencode(clean_params).encode("ascii")
        body = b""
        headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
        if json is not None:
            body = jsonlib.dumps(json, ensure_ascii=False).encode("utf-8")
            headers.append((b"content-type", b"application/json"))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query,
            "root_path": "",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "headers": headers,
        }

        status = 0
        resp_headers: list[tuple[bytes, bytes]] = []
        chunks: list[bytes] = []

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            nonlocal status, resp_headers
            if message["type"] == "http.response.start":
                status = message["status"]
                resp_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        asyncio.run(self._app(scope, receive, send))
        return ASGIResponse(status, resp_headers, b"".join(chunks))

    def get(self, path: str, **kwargs: Any) -> ASGIResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> ASGIResponse:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> ASGIResponse:
        return self.request("PATCH", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> ASGIResponse:
        return self.request("PUT", path, **kwargs)
