"""Сервер Reports Hub (спека §10.2, H5).

stdlib `ThreadingHTTPServer` без внешних зависимостей. Token-гейт
(решение №16): все запросы требуют `?token=…` или cookie `rh_token`
(ставится после первого успешного входа). Токен — из env
`REPORTS_HUB_TOKEN`; нет токена в env → сервер стартует и отдаёт 401
с подсказкой в лог (не молча, не падает). Раздаёт `site/`, endpoint
`/download/zip` — архив всего сайта. HTML генерируются заранее; сервер
ничего не считает на лету (кроме zip).
"""

from __future__ import annotations

import argparse
import io
import os
import zipfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

COOKIE_NAME = "rh_token"
MIME_OVERRIDES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


@dataclass
class ServeConfig:
    """Конфиг сервера: корень сайта + токен (None → всё 401 с подсказкой)."""

    site_root: Path
    token: str | None


def make_zip(site_root: Path) -> bytes:
    """Собрать zip всего сайта в памяти (site/ маленький — 1.3с генерация)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(site_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(site_root).as_posix())
    return buffer.getvalue()


class ReportsHubHandler(BaseHTTPRequestHandler):
    """Обработчик с token-гейтом (config в атрибуте класса)."""

    config: ServeConfig  # type: ignore[annotation-unchecked]

    # -- auth ----------------------------------------------------------------

    def _has_valid_token(self) -> bool:
        if self.config.token is None:
            return False
        parsed = urlparse(self.path)
        query_token = parse_qs(parsed.query).get("token", [None])[0]
        if query_token == self.config.token:
            return True
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE_NAME and value == self.config.token:
                return True
        return False

    def _log_hint_once(self) -> None:
        if self.config.token is None:
            print(
                "serve: REPORTS_HUB_TOKEN не установлен — все запросы получают 401. "
                "Задайте токен и перезапустите сервер.",
                flush=True,
            )

    def _send(self, status: int, body: bytes, content_type: str, *, set_cookie: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if set_cookie:
            self.send_header("Set-Cookie", f"{COOKIE_NAME}={self.config.token}; Path=/; HttpOnly")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        self._send(status, html.encode("utf-8"), "text/html; charset=utf-8")

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    # -- GET -----------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        self._log_hint_once()
        if not self._has_valid_token():
            page = (
                "<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
                "<title>401</title></head><body>"
                "<h1>401 — требуется токен</h1>"
                "<p>Добавьте <code>?token=…</code> к адресу (токен задаётся в REPORTS_HUB_TOKEN).</p>"
                "</body></html>"
            )
            self._send_html(401, page)
            return
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        if route == "/download/zip":
            archive = make_zip(self.config.site_root)
            self._send(200, archive, "application/zip")
            return
        if route == "/" or route == "/index.html":
            self._redirect("/index.html?token=") if False else None
            self._serve_file("index.html", set_cookie=True)
            return
        rel_path = parsed.path.lstrip("/")
        self._serve_file(rel_path, set_cookie=True)

    # -- static --------------------------------------------------------------

    def _resolve(self, rel_path: str) -> Path | None:
        candidate = (self.config.site_root / rel_path).resolve()
        try:
            candidate.relative_to(self.config.site_root.resolve())
        except ValueError:
            return None  # path traversal
        return candidate if candidate.is_file() else None

    def _serve_file(self, rel_path: str, *, set_cookie: bool = False) -> None:
        path = self._resolve(rel_path)
        if path is None:
            self._send_html(404, "<h1>404 — страница не найдена</h1>")
            return
        body = path.read_bytes()
        content_type = MIME_OVERRIDES.get(path.suffix.lower(), "application/octet-stream")
        self._send(200, body, content_type, set_cookie=set_cookie)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Тихий лог (systemd забирает stdout — формат не критичен)."""
        pass


def serve(site_root: Path, host: str, port: int, token: str | None) -> ThreadingHTTPServer:
    """Запустить сервер (блокирующе; вызывающий делает serve_forever)."""
    config = ServeConfig(site_root=site_root, token=token)
    handler = type("BoundHandler", (ReportsHubHandler,), {"config": config})
    server = ThreadingHTTPServer((host, port), handler)
    if token is None:
        print(
            "serve: REPORTS_HUB_TOKEN не установлен — все запросы будут 401 "
            "(сервер работает, подсказка в логе).",
            flush=True,
        )
    print(f"serve: http://{host}:{port}/ (site: {site_root})", flush=True)
    return server


def main(argv: list[str] | None = None) -> int:
    """Точка входа `python -m services_08.reports_hub.server` (для тестов/юнита)."""
    parser = argparse.ArgumentParser(prog="reports_hub.server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8310)
    parser.add_argument("--site", default=None, help="каталог site/ (по умолчанию рядом с кодом)")
    args = parser.parse_args(argv)
    site_root = Path(args.site) if args.site else Path(__file__).resolve().parent / "site"
    token = os.environ.get("REPORTS_HUB_TOKEN")
    httpd = serve(site_root, args.host, args.port, token)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
