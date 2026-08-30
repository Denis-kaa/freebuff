#!/usr/bin/env python3
"""
test_mcp_fastapi.py — Tests for FastAPI MCP wrapper (Streamable HTTP).

Uses uvicorn in a thread + http.client (same pattern as test_mcp_server.py HTTP tests).
Avoids FastAPI TestClient compatibility issues with httpx.
"""

import asyncio
import http.client
import json
import os
}
import socket
import sys
import threading
import time
}
from unittest import mock

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

# Auth bypass для всего модуля тестов (TestAuthorization override их)
os.environ.setdefault("FREEBUFF_ENV", "test")
os.environ.setdefault("FREEBUFF_MCP_AUTH_DISABLED", "1")

fastapi = pytest.importorskip("fastapi")

from scripts_01.mcp_fastapi import app, McpAsyncSessionManager  # noqa: E402
from scripts_01 import mcp_fastapi as _mcp_fastapi  # noqa: E402
from scripts_01.mcp_server import PROTOCOL_VERSION, PARSE_ERROR, METHOD_NOT_FOUND  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _find_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _http(host: str, port: int, method: str, path: str = "/mcp",
          body: str | None = None, headers: dict | None = None) -> tuple[int, dict, str]:
    """Make HTTP request, return (status, headers_dict, body_str)."""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body_bytes = body.encode("utf-8") if body else None
    conn.request(method, path, body=body_bytes, headers=hdrs)
    resp = conn.getresponse()
    status = resp.status
    resp_headers = {k.lower(): v for k, v in resp.getheaders()}
    resp_body = resp.read().decode("utf-8")
    conn.close()
    return status, resp_headers, resp_body


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def _uvicorn_server():
    """Start uvicorn in a daemon thread, yield (host, port)."""
    import uvicorn

    # Reset global state for fresh startup
    import scripts_01.mcp_fastapi as mod
    mod._server = None
    mod._sessions = None

    host = "127.0.0.1"
    port = _find_port()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until server is ready
    for _ in range(50):
        try:
            conn = http.client.HTTPConnection(host, port, timeout=1)
            conn.request("GET", "/")
            conn.getresponse()
            conn.close()
            break
        except Exception:
            time.sleep(0.1)

    yield host, port

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture()
def addr(_uvicorn_server):
    """(host, port) tuple for the running server."""
    return _uvicorn_server


# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════


class TestHealth:
    def test_health_returns_ok(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "ok"
        assert data["server"] == "buffy-mcp"
        assert data["endpoint"] == "/mcp"
        assert data["protocol"] == PROTOCOL_VERSION


# ═══════════════════════════════════════════════════════════════
# POST /mcp
# ═══════════════════════════════════════════════════════════════


class TestPostInitialize:
    def test_initialize_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200

    def test_initialize_returns_session_id(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert "mcp-session-id" in headers
        assert len(headers["mcp-session-id"]) > 0

    def test_initialize_returns_protocol_version(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert headers.get("mcp-protocol-version") == PROTOCOL_VERSION

    def test_initialize_returns_server_info(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        status, headers, resp = _http(host, port, "POST", body=body)
        data = json.loads(resp)
        assert "result" in data
        assert data["result"]["protocolVersion"] == PROTOCOL_VERSION


class TestPostPing:
    def test_ping_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["result"] == {}


class TestPostNotification:
    def test_notification_returns_202(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 202


class TestPostToolsList:
    def test_tools_list_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        data = json.loads(resp)
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) > 0

    def test_tools_list_includes_knowledge_search(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        status, headers, resp = _http(host, port, "POST", body=body)
        names = [t["name"] for t in json.loads(resp)["result"]["tools"]]
        assert "knowledge_search" in names


class TestPostResourcesList:
    def test_resources_list(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "resources" in json.loads(resp)["result"]


class TestPostPromptsList:
    def test_prompts_list(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "prompts" in json.loads(resp)["result"]


class TestPostToolsCall:
    def test_session_status_tool(self, addr):
        host, port = addr
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "session_status", "arguments": {}},
        ])
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "content" in json.loads(resp)["result"]


class TestPostBatch:
    def test_batch_request(self, addr):
        host, port = addr
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        status, headers, resp = _http(host, port, "POST", body=json.dumps(batch))
        assert status == 200
        data = json.loads(resp)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    def test_batch_all_notifications(self, addr):
        host, port = addr
        batch = [{"jsonrpc": "2.0", "method": "notifications/initialized"}]
        status, headers, resp = _http(host, port, "POST", body=json.dumps(batch))
        assert status == 202


class TestPostErrors:
    def test_invalid_json_returns_400(self, addr):
        host, port = addr
        status, headers, resp = _http(host, port, "POST", body="{invalid")
        assert status == 400
        assert json.loads(resp)["error"]["code"] == PARSE_ERROR

    def test_unknown_method_returns_error(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["error"]["code"] == METHOD_NOT_FOUND

    def test_unknown_session_id_returns_404(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Mcp-Session-Id": "nonexistent"},
        )
        assert status == 404

    def test_shutdown_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "shutdown"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["result"] == {}


# ═══════════════════════════════════════════════════════════════
# DELETE /mcp
# ═══════════════════════════════════════════════════════════════


class TestDelete:
    def test_delete_session(self, addr):
        host, port = addr
        # Create session via initialize
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        _, init_h, _ = _http(host, port, "POST", body=body)
        session_id = init_h["mcp-session-id"]

        status, headers, resp = _http(
            host, port, "DELETE", headers={"Mcp-Session-Id": session_id}
        )
        assert status == 204

    def test_delete_unknown_session(self, addr):
        host, port = addr
        status, headers, resp = _http(
            host, port, "DELETE", headers={"Mcp-Session-Id": "nonexistent"}
        )
        assert status == 404

    def test_delete_without_session_id(self, addr):
        host, port = addr
        status, headers, resp = _http(host, port, "DELETE")
        assert status == 400


# ═══════════════════════════════════════════════════════════════
# GET /mcp
# ═══════════════════════════════════════════════════════════════


class TestGet:
    def test_get_without_session_id(self, addr):
        host, port = addr
        status, headers, resp = _http(host, port, "GET")
        assert status == 400

    def test_get_unknown_session(self, addr):
        host, port = addr
        status, headers, resp = _http(
            host, port, "GET", headers={"Mcp-Session-Id": "nonexistent"}
        )
        assert status == 404

    def test_get_sse_content_type(self, addr):
        host, port = addr
        # Create session first
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        _, init_h, _ = _http(host, port, "POST", body=body)
        session_id = init_h["mcp-session-id"]

        # GET SSE stream
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        request = (
            f"GET /mcp HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Mcp-Session-Id: {session_id}\r\n"
            f"Accept: text/event-stream\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        )
        sock.sendall(request.encode("utf-8"))

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            header_data += chunk

        sock.close()
        header_str = header_data.decode("utf-8")
        assert "200" in header_str.split("\r\n")[0]
        assert "text/event-stream" in header_str
        assert PROTOCOL_VERSION in header_str


# ═══════════════════════════════════════════════════════════════
# Origin Validation
# ═══════════════════════════════════════════════════════════════


class TestOriginValidation:
    def test_evil_origin_rejected(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://evil.com"},
        )
        assert status == 403

    def test_localhost_origin_allowed(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://localhost:3000"},
        )
        assert status == 200

    def test_no_origin_allowed(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200

    def test_evil_origin_bypass_attempt(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://localhost.evil.com"},
        )
        assert status == 403


# ═══════════════════════════════════════════════════════════════
# Async Session Manager
# ═══════════════════════════════════════════════════════════════


class TestAsyncSessionManager:
    def test_create_session(self):
        async def _test():
            sm = McpAsyncSessionManager()
            sid = await sm.create_session()
            assert isinstance(sid, str)
            assert len(sid) > 0
        asyncio.run(_test())

    def test_get_session(self):
        async def _test():
            sm = McpAsyncSessionManager()
            sid = await sm.create_session()
            session = await sm.get_session(sid)
            assert session is not None
            assert session.session_id == sid
        asyncio.run(_test())

    def test_delete_session(self):
        async def _test():
            sm = McpAsyncSessionManager()
            sid = await sm.create_session()
            assert await sm.delete_session(sid) is True
            assert await sm.get_session(sid) is None
        asyncio.run(_test())

    def test_delete_unknown(self):
        async def _test():
            sm = McpAsyncSessionManager()
            assert await sm.delete_session("nonexistent") is False
        asyncio.run(_test())

    def test_push_notification(self):
        async def _test():
            sm = McpAsyncSessionManager()
            sid = await sm.create_session()
            assert await sm.push_notification(sid, "test msg") is True
            session = await sm.get_session(sid)
            msg = await asyncio.wait_for(session.notification_queue.get(), timeout=1)
            assert msg == "test msg"
        asyncio.run(_test())

    def test_count(self):
        async def _test():
            sm = McpAsyncSessionManager()
            assert await sm.count() == 0
            await sm.create_session()
            await sm.create_session()
            assert await sm.count() == 2
        asyncio.run(_test())

    def test_push_to_deleted_session(self):
        async def _test():
            sm = McpAsyncSessionManager()
            sid = await sm.create_session()
            await sm.delete_session(sid)
            assert await sm.push_notification(sid, "msg") is False
        asyncio.run(_test())


# ═══════════════════════════════════════════════════════════════
# GET /metrics/*
# ═══════════════════════════════════════════════════════════════


class TestMetricsEndpoints:
    """Tests for HTTP /metrics/* endpoints."""

    def test_metrics_report_returns_200(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/report")
        assert status == 200
        data = json.loads(body)
        assert "metrics" in data
        assert "total_tasks" in data
        assert "health_score" in data
        # All 5 metrics present
        for name in ("vcr", "srg", "cpvo", "rrr", "ttd"):
            assert name in data["metrics"]
            assert "value" in data["metrics"][name]

    def test_metrics_report_default_format(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/report")
        data = json.loads(body)
        assert "total_tasks" in data

    def test_metrics_vcr(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/vcr")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "vcr"
        assert "value" in data
        assert "unit" in data

    def test_metrics_srg(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/srg")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "srg"
        assert "interpretation" in data

    def test_metrics_cpvo(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/cpvo")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "cpvo"
        assert data["unit"] == "ms/verification"

    def test_metrics_rrr(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/rrr")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "rrr"
        assert "value" in data

    def test_metrics_ttd(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/ttd")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "ttd"
        assert data["unit"] == "minutes"

    def test_metrics_status(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/status")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "ok"
        assert "databases" in data

    def test_metrics_trend_known(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/trend/vcr")
        assert status == 200
        data = json.loads(body)
        assert data["metric"] == "vcr"
        assert "history" in data

    def test_metrics_trend_unknown(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/trend/unknown_metric")
        assert status == 200
        data = json.loads(body)
        assert "error" in data
        assert "unknown_metric" in data["error"]

    def test_metrics_trend_with_limit(self, addr):
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/metrics/trend/vcr?limit=5")
        assert status == 200
        data = json.loads(body)
        assert data["metric"] == "vcr"
        assert isinstance(data["history"], list)

    def test_all_metrics_endpoints_return_json(self, addr):
        """Проверка Content-Type для всех metrics endpoints."""
        host, port = addr
        endpoints = [
            "/metrics/report",
            "/metrics/vcr",
            "/metrics/srg",
            "/metrics/cpvo",
            "/metrics/rrr",
            "/metrics/ttd",
            "/metrics/status",
            "/metrics/trend/vcr",
        ]
        for endpoint in endpoints:
            status, headers, body = _http(host, port, "GET", endpoint)
            assert status == 200, f"{endpoint} returned {status}"
            ct = headers.get("content-type", "")
            assert "json" in ct, f"{endpoint} Content-Type is {ct}"


# ═══════════════════════════════════════════════════════════════
# POST /policy/override — User-Choice Override без MCP (правило 11)
# ═══════════════════════════════════════════════════════════════


class TestPolicyOverrideEndpoint:
    """HTTP-доступ к override без MCP-протокола.

    PolicyEngine и apply_override мокаются, чтобы не писать в реальный
    runtime_05/policies.json и не зависеть от рантайм-реестра.
    """

    EN_MSG = "use deepseek instead of claude for coding"
    RU_MSG = "используй freebuff для research"
    FAKE_RESULT = {
        "applied": True,
        "capability": "coding",
        "runtime": "deepseek",
        "previous_runtime": None,
        "matched": "use (?P<rt>[a-z]+) for (?P<cap>[a-z]+)",
        "message": EN_MSG,
    }

    def _post(self, host, port, body):
        return _http(
            host, port, "POST", "/policy/override",
            body=json.dumps(body),
        )

    def test_override_applies_english(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override",
            return_value=dict(self.FAKE_RESULT),
        ) as m:
            status, headers, body = self._post(
                host, port, {"message": self.EN_MSG}
            )
        assert status == 200
        data = json.loads(body)
        assert data["success"] is True
        assert data["data"]["applied"] is True
        assert data["data"]["capability"] == "coding"
        assert data["data"]["runtime"] == "deepseek"
        m.assert_called_once()
        assert m.call_args[0][0] == self.EN_MSG

    def test_override_applies_russian(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        fake = dict(self.FAKE_RESULT)
        fake["capability"] = "research"
        fake["runtime"] = "freebuff"
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override", return_value=fake
        ):
            status, headers, body = self._post(
                host, port, {"message": self.RU_MSG}
            )
        assert status == 200
        data = json.loads(body)
        assert data["data"]["capability"] == "research"
        assert data["data"]["runtime"] == "freebuff"

    def test_override_bad_payloads_return_400(self, addr):
        host, port = addr
        for payload in ({}, {"message": ""}, {"message": 42}, "not-a-dict"):
            status, _, body = self._post(host, port, payload)
            assert status == 400, f"{payload!r} should be 400"
            assert json.loads(body)["success"] is False

    def test_override_invalid_json_returns_400(self, addr):
        host, port = addr
        status, _, body = _http(
            host, port, "POST", "/policy/override", body="{invalid"
        )
        assert status == 400
        assert json.loads(body)["success"] is False

    def test_override_unrecognized_phrase_returns_422(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override", return_value=None
        ) as m:
            status, _, body = self._post(
                host, port, {"message": "hello world, nothing to override"}
            )
        assert status == 422
        data = json.loads(body)
        assert data["success"] is False
        assert "parse" in data["error"].lower()
        m.assert_called_once()

    def test_override_engine_unavailable_returns_503(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: None)
        with mock.patch("freebuff_plugin_03.policy.apply_override") as m:
            status, _, body = self._post(
                host, port, {"message": self.EN_MSG}
            )
        assert status == 503
        assert json.loads(body)["success"] is False
        m.assert_not_called()

    def test_override_rejects_evil_origin(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        status, _, body = _http(
            host, port, "POST", "/policy/override",
            body=json.dumps({"message": self.EN_MSG}),
            headers={"Origin": "http://evil.com"},
        )
        assert status == 403
        assert json.loads(body)["success"] is False

    def test_override_requires_auth(self, addr, monkeypatch):
        """Без валидного Bearer — 401 (эндпоинт защищён, как /mcp)."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.setenv("FREEBUFF_MCP_TOKEN", "correct-token-abcdef123456")
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()
        host, port = addr
        status, headers, body = self._post(
            host, port, {"message": self.EN_MSG}
        )
        assert status == 401
        assert "www-authenticate" in headers

    def test_override_success_with_bearer(self, addr, monkeypatch):
        """С валидным Bearer + мок-инженером — 200."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.setenv("FREEBUFF_MCP_TOKEN", "correct-token-abcdef123456")
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override",
            return_value=dict(self.FAKE_RESULT),
        ):
            host, port = addr
            status, _, body = _http(
                host, port, "POST", "/policy/override",
                body=json.dumps({"message": self.EN_MSG}),
                headers={"Authorization": "Bearer correct-token-abcdef123456"},
            )
        assert status == 200
        assert json.loads(body)["success"] is True

    def test_override_passes_capability_param(self, addr, monkeypatch):
        """capability из тела передаётся в apply_override (переопределение)."""
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override",
            return_value=dict(self.FAKE_RESULT),
        ) as m:
            status, _, body = self._post(
                host, port,
                {"message": self.EN_MSG, "capability": "research"},
            )
        assert status == 200
        m.assert_called_once()
        assert m.call_args[0][0] == self.EN_MSG
        assert m.call_args[0][2] == "research"
        assert m.call_args[0][3] is False

    def test_override_passes_dry_run_flag(self, addr, monkeypatch):
        """dry_run=true передаётся в apply_override (без записи)."""
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: object())
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override",
            return_value=dict(self.FAKE_RESULT),
        ) as m:
            status, _, body = self._post(
                host, port,
                {"message": self.EN_MSG, "dry_run": True},
            )
        assert status == 200
        assert m.call_args[0][2] is None
        assert m.call_args[0][3] is True

    def test_override_dry_run_without_engine_ok(self, addr, monkeypatch):
        """dry_run=true НЕ требует PolicyEngine (503 не возвращается)."""
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: None)
        with mock.patch(
            "freebuff_plugin_03.policy.apply_override",
            return_value={
                "applied": False, "dry_run": True,
                "capability": "coding", "runtime": "deepseek",
            },
        ) as m:
            status, _, body = self._post(
                host, port,
                {"message": self.EN_MSG, "dry_run": True},
            )
        assert status == 200
        m.assert_called_once()
        # engine передан как None, но dry_run позволяет продолжить
        assert m.call_args[0][1] is None

    def test_override_invalid_capability_returns_400(self, addr):
        """capability не-string, пустой или из пробелов — 400 на уровне эндпоинта."""
        host, port = addr
        for cap in (42, "", "   "):
            status, _, body = self._post(
                host, port,
                {"message": self.EN_MSG, "capability": cap},
            )
            assert status == 400, f"capability={cap!r} should be 400"
            assert json.loads(body)["success"] is False

    def test_override_invalid_dry_run_returns_400(self, addr):
        """dry_run не-bool — 400 на уровне эндпоинта."""
        host, port = addr
        for dr in ("yes", 1, "true"):
            status, _, body = self._post(
                host, port,
                {"message": self.EN_MSG, "dry_run": dr},
            )
            assert status == 400, f"dry_run={dr!r} should be 400"
            assert json.loads(body)["success"] is False


class TestPolicyOverrideE2E:
    """End-to-end: POST /policy/override с РЕАЛЬНЫМ PolicyEngine.

    В отличие от мок-тестов TestPolicyOverrideEndpoint, здесь не мокается
    apply_override — используется настоящий PolicyEngine с policy_file
    во временной директории (tmp_path). Проверяется сквозной путь:
    HTTP-запрос → парсинг фразы → set_preference → персист в policies.json
    на диске.
    """

    EN_MSG = "use deepseek instead of claude for coding"

    @staticmethod
    def _make_engine(tmp_path: Path):
        """Реальный PolicyEngine на временном policy_file (как в test_policy_conversational)."""
        from freebuff_plugin_03.policy import PolicyEngine

        class MockRuntimeRegistry:
            def get(self, name):
                class FakeRuntime:
                    class Status:
                        value = "connected"
                    status = Status()
                    capabilities = ["coding"]
                return FakeRuntime()

            def is_connected(self, name):
                return True

        class MockCapabilityRegistry:
            def get_runtime_for_capability(self, capability, preferred_runtime=None):
                return {"runtime": "freebuff", "confidence": 0.8, "connected": True}

            def score_runtime(self, runtime_name, capability):
                return 0.8

        policy_file = tmp_path / "policies.json"
        # Пустой seed только если файла ещё нет — reload-тест персистит через POST
        if not policy_file.exists():
            policy_file.write_text(
                '{"version": "1.0", "policies": {]]', encoding="utf-8"
            )
        return PolicyEngine(
            MockRuntimeRegistry(),
            MockCapabilityRegistry(),
            policy_file=str(policy_file),
        )

    def _post(self, host, port, body):
        return _http(
            host, port, "POST", "/policy/override",
            body=json.dumps(body),
        )

    def test_e2e_override_persists_to_policies_json(self, addr, monkeypatch, tmp_path):
        """Реальный engine: override применяется и персистится в policies.json на диске."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, body = self._post(host, port, {"message": self.EN_MSG})

        assert status == 200
        data = json.loads(body)
        assert data["success"] is True
        assert data["data"]["applied"] is True
        assert data["data"]["capability"] == "coding"
        assert data["data"]["runtime"] == "deepseek"

        # Персист: политика записана в policies.json на диске
        on_disk = json.loads((tmp_path / "policies.json").read_text(encoding="utf-8"))
        assert on_disk["version"] == "1.0"
        assert on_disk["policies"]["coding"]["preferred_runtime"] == "deepseek"
        # Engine разделяет то же состояние
        assert engine.get_policy("coding").preferred_runtime == "deepseek"

    def test_e2e_override_rus_persists(self, addr, monkeypatch, tmp_path):
        """Русская фраза также персистится (research → freebuff)."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, body = self._post(
            host, port, {"message": "используй freebuff для research"}
        )

        assert status == 200
        data = json.loads(body)
        assert data["data"]["applied"] is True
        assert data["data"]["capability"] == "research"
        assert data["data"]["runtime"] == "freebuff"

        on_disk = json.loads((tmp_path / "policies.json").read_text(encoding="utf-8"))
        assert on_disk["policies"]["research"]["preferred_runtime"] == "freebuff"

    def test_e2e_override_capability_param_persists(self, addr, monkeypatch, tmp_path):
        """capability-параметр переопределяет capability из фразы и персистится."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, body = self._post(
            host, port,
            {"message": self.EN_MSG, "capability": "research"},
        )

        assert status == 200
        data = json.loads(body)
        assert data["data"]["applied"] is True
        assert data["data"]["capability"] == "research"
        assert data["data"]["runtime"] == "deepseek"

        on_disk = json.loads((tmp_path / "policies.json").read_text(encoding="utf-8"))
        assert "coding" not in on_disk["policies"]
        assert on_disk["policies"]["research"]["preferred_runtime"] == "deepseek"

    def test_e2e_dry_run_does_not_persist(self, addr, monkeypatch, tmp_path):
        """dry_run=true: интент распознан, но policies.json НЕ изменяется."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, body = self._post(
            host, port,
            {"message": self.EN_MSG, "dry_run": True},
        )

        assert status == 200
        data = json.loads(body)
        assert data["data"]["applied"] is False
        assert data["data"]["dry_run"] is True
        assert data["data"]["capability"] == "coding"
        assert data["data"]["runtime"] == "deepseek"

        # Файл остался пустым (персиста нет)
        on_disk = json.loads((tmp_path / "policies.json").read_text(encoding="utf-8"))
        assert on_disk["policies"] == {}

    def test_e2e_replaces_existing_preference_on_disk(self, addr, monkeypatch, tmp_path):
        """Повторный override заменяет предыдущее значение в policies.json."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        engine.set_preference("coding", "claude-code")
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, body = self._post(host, port, {"message": self.EN_MSG})

        assert status == 200
        data = json.loads(body)
        assert data["data"]["previous_runtime"] == "claude-code"

        on_disk = json.loads((tmp_path / "policies.json").read_text(encoding="utf-8"))
        assert on_disk["policies"]["coding"]["preferred_runtime"] == "deepseek"

    def test_e2e_engine_reload_sees_persisted_policy(self, addr, monkeypatch, tmp_path):
        """Новый PolicyEngine (перезагрузка сервиса) видит политику из policies.json."""
        host, port = addr
        engine = self._make_engine(tmp_path)
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)

        status, _, _ = self._post(host, port, {"message": self.EN_MSG})
        assert status == 200

        # Свежий engine на том же файле — политика загружается с диска
        reloaded = self._make_engine(tmp_path)
        assert reloaded.get_policy("coding").preferred_runtime == "deepseek"
        assert reloaded.select_runtime("coding") == "deepseek"


# ═══════════════════════════════════════════════════════════════
# GET /policy/status — текущие предпочтения (правило 11)
# ═══════════════════════════════════════════════════════════════


class TestPolicyStatusEndpoint:
    """HTTP-просмотр текущих предпочтений из policies.json (правило 11).

    PolicyEngine мокается, чтобы не зависеть от реального runtime_05/policies.json.
    """

    def _make_engine(self, policies: dict | None = None):
        engine = mock.MagicMock()
        engine.list_policies.return_value = policies or {}
        return engine

    def test_status_returns_preferences(self, addr, monkeypatch):
        host, port = addr
        from freebuff_plugin_03.policy.config import CapabilityPolicy
        engine = self._make_engine({
            "coding": CapabilityPolicy(preferred_runtime="deepseek"),
            "research": CapabilityPolicy(
                preferred_runtime="freebuff",
                fallback_chain=["openclaw"],
            ),
        ])
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)
        status, _, body = _http(host, port, "GET", "/policy/status")
        assert status == 200
        data = json.loads(body)
        assert data["success"] is True
        assert data["data"]["count"] == 2
        assert data["data"]["preferences"] == {
            "coding": "deepseek",
            "research": "freebuff",
        }
        # Полная сериализация политик (не только preferences)
        assert data["data"]["policies"]["coding"]["preferred_runtime"] == "deepseek"
        assert data["data"]["policies"]["research"]["fallback_chain"] == ["openclaw"]
        assert data["data"]["policies"]["research"]["constraints"] == []

    def test_status_empty(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(
            _mcp_fastapi, "_get_policy_engine", lambda: self._make_engine()
        )
        status, _, body = _http(host, port, "GET", "/policy/status")
        assert status == 200
        data = json.loads(body)
        assert data["data"]["count"] == 0
        assert data["data"]["preferences"] == {}
        assert data["data"]["policies"] == {}

    def test_status_constraints_serialized(self, addr, monkeypatch):
        """Constraints сериализуются (rule_type + params)."""
        host, port = addr
        from freebuff_plugin_03.policy.config import CapabilityPolicy, PolicyRule
        engine = self._make_engine({
            "coding": CapabilityPolicy(
                preferred_runtime="deepseek",
                constraints=[PolicyRule(rule_type="min_confidence", params={"value": 0.8})],
            ),
        ])
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)
        status, _, body = _http(host, port, "GET", "/policy/status")
        assert status == 200
        data = json.loads(body)
        cons = data["data"]["policies"]["coding"]["constraints"]
        assert cons == [{"rule_type": "min_confidence", "params": {"value": 0.8}}]

    def test_status_policy_without_preferred_still_counted(self, addr, monkeypatch):
        """Политика без preferred_runtime есть в policies/count, но не в preferences."""
        host, port = addr
        from freebuff_plugin_03.policy.config import CapabilityPolicy
        engine = self._make_engine({
            "coding": CapabilityPolicy(fallback_chain=["freebuff"]),
        ])
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: engine)
        status, _, body = _http(host, port, "GET", "/policy/status")
        assert status == 200
        data = json.loads(body)
        assert data["data"]["count"] == 1
        assert data["data"]["preferences"] == {}
        assert data["data"]["policies"]["coding"]["fallback_chain"] == ["freebuff"]
        assert data["data"]["policies"]["coding"]["preferred_runtime"] is None

    def test_status_engine_unavailable_returns_503(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(_mcp_fastapi, "_get_policy_engine", lambda: None)
        status, _, body = _http(host, port, "GET", "/policy/status")
        assert status == 503
        assert json.loads(body)["success"] is False

    def test_status_rejects_evil_origin(self, addr, monkeypatch):
        host, port = addr
        monkeypatch.setattr(
            _mcp_fastapi, "_get_policy_engine", lambda: self._make_engine()
        )
        status, _, body = _http(
            host, port, "GET", "/policy/status",
            headers={"Origin": "http://evil.com"},
        )
        assert status == 403
        assert json.loads(body)["success"] is False

    def test_status_requires_auth(self, addr, monkeypatch):
        """Без валидного Bearer — 401 (эндпоинт защищён, как /policy/override)."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.setenv("FREEBUFF_MCP_TOKEN", "correct-token-abcdef123456")
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/policy/status")
        assert status == 401
        assert "www-authenticate" in headers

    def test_status_success_with_bearer(self, addr, monkeypatch):
        """С валидным Bearer + мок-инженером — 200."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.setenv("FREEBUFF_MCP_TOKEN", "correct-token-abcdef123456")
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()
        monkeypatch.setattr(
            _mcp_fastapi, "_get_policy_engine", lambda: self._make_engine()
        )
        host, port = addr
        status, _, body = _http(
            host, port, "GET", "/policy/status",
            headers={"Authorization": "Bearer correct-token-abcdef123456"},
        )
        assert status == 200
        assert json.loads(body)["success"] is True


# ═══════════════════════════════════════════════════════════════
# Bearer Token Authorization (pompts_11/TASK_SECURE_MCP_ACCESS.md Step 2)
# ═══════════════════════════════════════════════════════════════


class TestAuthorization:
    """Проверки Bearer-token auth_middleware на /mcp endpoints.

    Модульный setdefault даёт bypass для существующих тестов;
    здесь — отключаем bypass (FREEBUFF_MCP_AUTH_DISABLED=0) и подкладываем
    FREEBUFF_MCP_TOKEN; чистим кеш токена перед каждым тестом.
    """

    TEST_TOKEN = "test-token-secret-aaaaaa"

    def _setup_auth(
        self,
        monkeypatch,
        token: str = TEST_TOKEN,
    ) -> None:
        """Disable bypass, set env token + env=test, clear cache."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.setenv("FREEBUFF_MCP_TOKEN", token)
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()

    def test_no_authorization_header_returns_401(self, addr, monkeypatch):
        self._setup_auth(monkeypatch)
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 401
        assert "www-authenticate" in headers
        assert 'Bearer realm="buffy-mcp"' in headers.get(
            "www-authenticate", ""
        )

    def test_wrong_bearer_returns_401(self, addr, monkeypatch):
        self._setup_auth(monkeypatch, token="correct-token-xxxxxx")
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host,
            port,
            "POST",
            body=body,
            headers={"Authorization": "Bearer wrong-token-yyyyyy"},
        )
        assert status == 401

    def test_non_bearer_scheme_returns_401(self, addr, monkeypatch):
        self._setup_auth(monkeypatch)
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        for bad_auth in ("a", "Basic xyz", "Bearer", "Token 123", ""):
            status, _, _ = _http(
                host,
                port,
                "POST",
                body=body,
                headers={"Authorization": bad_auth},
            )
            assert status == 401, f"{bad_auth!r} should be 401"

    def test_correct_bearer_returns_200(self, addr, monkeypatch):
        token = "right-token-abcdef123456"
        self._setup_auth(monkeypatch, token=token)
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, headers, resp = _http(
            host,
            port,
            "POST",
            body=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status == 200
        assert json.loads(resp)["result"] == {}

    def test_correct_bearer_for_delete_returns_204(self, addr, monkeypatch):
        token = "right-token-abcdef123456"
        self._setup_auth(monkeypatch, token=token)
        host, port = addr
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            }
        )
        _, init_h, _ = _http(
            host,
            port,
            "POST",
            body=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        sid = init_h["mcp-session-id"]
        status, headers, resp = _http(
            host,
            port,
            "DELETE",
            headers={
                "Authorization": f"Bearer {token}",
                "Mcp-Session-Id": sid,
            },
        )
        assert status == 204

    def test_no_token_configured_returns_401(self, addr, monkeypatch):
        """Никакого токена в env, Vault не задан — всё 401."""
        monkeypatch.setenv("FREEBUFF_MCP_AUTH_DISABLED", "0")
        monkeypatch.delenv("FREEBUFF_MCP_TOKEN", raising=False)
        monkeypatch.delenv("FREEBUFF_VAULT_ADDR", raising=False)
        monkeypatch.setenv("FREEBUFF_ENV", "test")
        _mcp_fastapi._reset_token_cache()
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        status, _, _ = _http(
            host,
            port,
            "POST",
            body=body,
            headers={"Authorization": "Bearer anything-not-real"},
        )
        assert status == 401

    def test_health_endpoint_unprotected(self, addr):
        """GET / НЕ требует Bearer (для liveness probe)."""
        host, port = addr
        status, headers, body = _http(host, port, "GET", "/")
        assert status == 200

    def test_metrics_observability_unaffected(self, addr):
        """GET /metrics/* НЕ требует Bearer (для observability при сбое auth)."""
        host, port = addr
        status, _, _ = _http(host, port, "GET", "/metrics/status")
        assert status == 200

    def test_dashboard_unprotected(self, addr):
        """GET /dashboard НЕ требует Bearer (статический HTML)."""
        host, port = addr
        status, _, _ = _http(host, port, "GET", "/dashboard")
        # 200 если HTML есть, 404 если нет — но НЕ 401
        assert status in (200, 404)

    def test_hmac_compare_digest_used_no_eq_compare(self):
        """Sanity: исходник использует hmac.compare_digest, а не == для токенов."""
        src = Path(_mcp_fastapi.__file__).read_text(encoding="utf-8")
        assert "hmac.compare_digest" in src
        # Анти-регрессия: ловим `==` сравнения с provided/expected в любом порядке
        bad = re.search(r"==\s*(provided|expected)\b", src)
        assert bad is None, (
            "Found '== provided/expected' — must use hmac.compare_digest"
        )


# ═══════════════════════════════════════════════════════════════
# /api/v1/* Meeting Tasks REST (042_06 Фаза E, фронтенд-контракт 043)
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_tasks_db(tmp_path, monkeypatch):
    """Временная БД для тестов Meeting Tasks REST.

    Monkey-patch task_manager.DB_PATH → указывает на tmp_path. Эндпоинты
    в скриптах читают DB_PATH динамически (через task_manager.DB_PATH),
    поэтому patch применяется на лету.
    """
    db_path = tmp_path / "data_13" / "context.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_mcp_fastapi.task_manager, "DB_PATH", db_path)
    return db_path


class TestMeetingTasksREST:
    """REST-эндпоинты для 043 frontend dashboard
    (api.ts: getProjects/getTasks/createTask). Реальный TaskManager +
    uvicorn server + DB isolation через tmp_tasks_db.

    Auth bypass: FREEBUFF_ENV=test + FREEBUFF_MCP_AUTH_DISABLED=1 (setdefault).
    """

    @staticmethod
    def _seed_projects(db, names=("CRM",)):
        """Сидирует projects table (FK для create_task)."""
        conn = _mcp_fastapi.task_manager.init_db(db)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                name TEXT PRIMARY KEY, path TEXT NOT NULL,
                description TEXT DEFAULT '', last_scanned TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
            """
        )
        for n in names:
            conn.execute(
                "INSERT OR REPLACE INTO projects "
                "(name, path, description, status, last_scanned) "
                "VALUES (?, ?, ?, 'active', '2026-08-01T00:00:00+00:00')",
                (n, f"/tmp/{n}", f"project {n}"),
            )
        conn.commit()
        conn.close()

    # ── /api/v1/projects ──

    def test_list_projects_empty_returns_count_zero(
        self, addr, tmp_tasks_db
    ):
        """Без таблицы projects — пустой список (soft fallback)."""
        host, port = addr
        status, _, body = _http(host, port, "GET", "/api/v1/projects")
        assert status == 200
        data = json.loads(body)
        assert data["success"] is True
        assert data["data"]["count"] == 0
        assert data["data"]["projects"] == []

    def test_list_projects_seeded_sorted_by_name(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        self._seed_projects(tmp_tasks_db, names=("CRM", "diet_platform"))
        status, _, body = _http(host, port, "GET", "/api/v1/projects")
        assert status == 200
        data = json.loads(body)
        assert data["data"]["count"] == 2
        assert [p["name"] for p in data["data"]["projects"]] == [
            "CRM", "diet_platform"
        ]
        assert data["data"]["projects"][0]["status"] == "active"
        assert data["data"]["projects"][0]["last_scanned"]

    # ── /api/v1/tasks GET ──

    def test_get_tasks_empty_project_returns_count_zero(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        status, _, body = _http(
            host, port, "GET", "/api/v1/tasks?project_id=ghost"
        )
        assert status == 200
        data = json.loads(body)
        assert data["data"]["count"] == 0
        assert data["data"]["tasks"] == []

    def test_get_tasks_with_type_filter(self, addr, tmp_tasks_db):
        host, port = addr
        self._seed_projects(tmp_tasks_db)
        _mcp_fastapi.task_manager.create_task(
            "CRM", "Code", task_type="digital", db_path=tmp_tasks_db
        )
        _mcp_fastapi.task_manager.create_task(
            "CRM", "Встреча",
            task_type="meeting",
            meeting_time="2026-08-02T14:00",
            location="Офис",
            participants=["Алексей"],
            db_path=tmp_tasks_db,
        )
        status, _, body = _http(
            host, port, "GET", "/api/v1/tasks?project_id=CRM&type=meeting"
        )
        assert status == 200
        data = json.loads(body)
        assert data["data"]["count"] == 1
        t = data["data"]["tasks"][0]
        assert t["task_type"] == "meeting"
        assert t["meeting_time"] == "2026-08-02T14:00"
        assert t["participants"] == ["Алексей"]

    def test_get_tasks_invalid_filter_returns_400(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        status, _, body = _http(
            host, port, "GET", "/api/v1/tasks?project_id=CRM&type=bogus"
        )
        assert status == 400
        assert json.loads(body)["success"] is False

    # ── /api/v1/tasks POST ──

    def test_post_task_digital_returns_201(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        self._seed_projects(tmp_tasks_db)
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks",
            body=json.dumps({
                "project_id": "CRM", "title": "API endpoint",
                "task_type": "digital",
            ]),
        )
        assert status == 201
        data = json.loads(body)
        assert data["success"] is True
        task = data["data"]["task"]
        assert task["title"] == "API endpoint"
        assert task["task_type"] == "digital"
        assert task["id"].startswith("tm-")
        assert task["status"] == "pending"
        assert task["created_at"]

    def test_post_task_meeting_with_full_attrs(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        self._seed_projects(tmp_tasks_db)
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks",
            body=json.dumps({
                "project_id": "CRM", "title": "Sync",
                "task_type": "meeting",
                "meeting_time": "2026-08-02T14:00",
                "location": "Офис",
                "participants": ["Алексей", "Иван"],
                "priority": "high",
                "description": "Согласование roadmap",
            ]),
        )
        assert status == 201
        data = json.loads(body)
        task = data["data"]["task"]
        assert task["task_type"] == "meeting"
        assert task["meeting_time"] == "2026-08-02T14:00"
        assert task["location"] == "Офис"
        assert task["participants"] == ["Алексей", "Иван"]
        assert task["priority"] == "high"
        assert task["description"] == "Согласование roadmap"

    def test_post_task_missing_title_returns_400(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        self._seed_projects(tmp_tasks_db)
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks",
            body=json.dumps({
                "project_id": "CRM", "title": "", "task_type": "digital",
            ]),
        )
        assert status == 400
        assert json.loads(body)["success"] is False

    def test_post_task_meeting_attr_for_digital_returns_400(
        self, addr, tmp_tasks_db
    ):
        """meeting_time + task_type=digital → 400 (правило 8)."""
        host, port = addr
        self._seed_projects(tmp_tasks_db)
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks",
            body=json.dumps({
                "project_id": "CRM", "title": "x", "task_type": "digital",
                "meeting_time": "2026-08-02T14:00",
            ]),
        )
        assert status == 400
        assert "meeting_time" in json.loads(body)["error"]
        assert "Context-Aware" in json.loads(body)["error"]

    def test_post_task_invalid_json_returns_400(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks", body="{invalid"
        )
        assert status == 400
        assert json.loads(body)["success"] is False

    def test_post_task_non_dict_body_returns_400(
        self, addr, tmp_tasks_db
    ):
        host, port = addr
        status, _, body = _http(
            host, port, "POST", "/api/v1/tasks",
            body=json.dumps(["not", "a", "dict"]),
        )
        assert status == 400
        assert json.loads(body)["success"] is False
