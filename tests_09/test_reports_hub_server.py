#!/usr/bin/env python3
"""Tests for Reports Hub server (спека §12, тест 7: test_token_gate).

Токен-гейт: без токена в env → 401 на всё; с токеном → 200; cookie после
первого входа; /download/zip отдаёт архив; path traversal заблокирован.
"""

from __future__ import annotations

import io
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.server import COOKIE_NAME, make_zip, serve


class _Site:
    """Минимальный сайт в tmp: index + вложенная страница."""

    def __init__(self, root: Path) -> None:
        (root / "projects" / "demo").mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text("<html><body>index</body></html>", encoding="utf-8")
        (root / "projects" / "demo" / "index.html").write_text(
            "<html><body>demo</body></html>", encoding="utf-8"
        )


def _start_server(tmp_path: Path, token: str | None) -> tuple[str, object]:
    site_root = tmp_path / "site"
    _Site(site_root)
    httpd = serve(site_root, "127.0.0.1", 0, token)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}", httpd


def _get(url: str) -> tuple[int, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


class TestTokenGate:
    def test_no_token_in_env_all_401(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, None)
        try:
            status, body, _ = _get(f"{base}/index.html")
            assert status == 401
            assert "token" in body.decode("utf-8").lower()
            # Любой другой путь — тоже 401 (гейт до маршрутизации).
            status2, _, _ = _get(f"{base}/projects/demo/index.html")
            assert status2 == 401
        finally:
            httpd.shutdown()

    def test_token_in_env_no_query_401(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "secret")
        try:
            status, _, _ = _get(f"{base}/index.html")
            assert status == 401
        finally:
            httpd.shutdown()

    def test_wrong_token_401_right_token_200(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "secret")
        try:
            status, _, _ = _get(f"{base}/index.html?token=wrong")
            assert status == 401
            status, body, _ = _get(f"{base}/index.html?token=secret")
            assert status == 200
            assert b"index" in body
            status, body, _ = _get(f"{base}/projects/demo/index.html?token=secret")
            assert status == 200
            assert b"demo" in body
        finally:
            httpd.shutdown()

    def test_cookie_after_first_login(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "secret")
        try:
            _, _, headers = _get(f"{base}/index.html?token=secret")
            set_cookie = headers.get("Set-Cookie", "")
            assert COOKIE_NAME in set_cookie
            cookie = set_cookie.split(";")[0]
            request = urllib.request.Request(f"{base}/projects/demo/index.html")
            request.add_header("Cookie", cookie)
            with urllib.request.urlopen(request, timeout=5) as response:
                assert response.status == 200
        finally:
            httpd.shutdown()

    def test_zip_endpoint(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "t")
        try:
            status, body, headers = _get(f"{base}/download/zip?token=t")
            assert status == 200
            assert headers.get("Content-Type") == "application/zip"
            archive = zipfile.ZipFile(io.BytesIO(body))
            names = archive.namelist()
            assert "index.html" in names
            assert "projects/demo/index.html" in names
        finally:
            httpd.shutdown()

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "t")
        try:
            outside = tmp_path / "secret.txt"
            outside.write_text("top secret", encoding="utf-8")
            status, _, _ = _get(f"{base}/../secret.txt?token=t")
            assert status in (401, 404)  # гейт или резолвер — не 200
            # Явно с токеном через кодированный путь — тоже не 200.
            request = urllib.request.Request(f"{base}/%2e%2e/secret.txt?token=t")
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    assert response.status == 404
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
        finally:
            httpd.shutdown()

    def test_404_unknown_file(self, tmp_path: Path) -> None:
        base, httpd = _start_server(tmp_path, "t")
        try:
            status, _, _ = _get(f"{base}/no-such-page.html?token=t")
            assert status == 404
        finally:
            httpd.shutdown()


class TestMakeZip:
    def test_zip_contains_site_files(self, tmp_path: Path) -> None:
        site_root = tmp_path / "site"
        _Site(site_root)
        body = make_zip(site_root)
        archive = zipfile.ZipFile(io.BytesIO(body))
        assert set(archive.namelist()) == {"index.html", "projects/demo/index.html"}
