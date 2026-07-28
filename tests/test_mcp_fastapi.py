#!/usr/bin/env python3
"""
test_mcp_fastapi.py — Tests for FastAPI MCP wrapper (Streamable HTTP).

Uses uvicorn in a thread + http.client (same pattern as test_mcp_server.py HTTP tests).
Avoids FastAPI TestClient compatibility issues with httpx.
"""

import asyncio
import http.client
import json
import socket
import sys
import threading
import time
***REMOVED***

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

fastapi = pytest.importorskip("fastapi")

from scripts.mcp_fastapi import app, McpAsyncSessionManager  # noqa: E402
from scripts.mcp_server import PROTOCOL_VERSION, PARSE_ERROR, METHOD_NOT_FOUND  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _find_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1***REMOVED***


def _http(host: str, port: int, method: str, path: str = "/mcp",
          body: str | None = None, headers: dict | None = None) -> tuple[int, dict, str***REMOVED***:
    """Make HTTP request, return (status, headers_dict, body_str)."""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    hdrs = {"Content-Type": "application/json"***REMOVED***
    if headers:
        hdrs.update(headers)
    body_bytes = body.encode("utf-8") if body else None
    conn.request(method, path, body=body_bytes, headers=hdrs)
    resp = conn.getresponse()
    status = resp.status
    resp_headers = {k.lower(): v for k, v in resp.getheaders()***REMOVED***
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
    import scripts.mcp_fastapi as mod
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
        assert data["status"***REMOVED*** == "ok"
        assert data["server"***REMOVED*** == "buffy-mcp"
        assert data["endpoint"***REMOVED*** == "/mcp"
        assert data["protocol"***REMOVED*** == PROTOCOL_VERSION


# ═══════════════════════════════════════════════════════════════
# POST /mcp
# ═══════════════════════════════════════════════════════════════


class TestPostInitialize:
    def test_initialize_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200

    def test_initialize_returns_session_id(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert "mcp-session-id" in headers
        assert len(headers["mcp-session-id"***REMOVED***) > 0

    def test_initialize_returns_protocol_version(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert headers.get("mcp-protocol-version") == PROTOCOL_VERSION

    def test_initialize_returns_server_info(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        data = json.loads(resp)
        assert "result" in data
        assert data["result"***REMOVED***["protocolVersion"***REMOVED*** == PROTOCOL_VERSION


class TestPostPing:
    def test_ping_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["result"***REMOVED*** == {***REMOVED***


class TestPostNotification:
    def test_notification_returns_202(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {***REMOVED******REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 202


class TestPostToolsList:
    def test_tools_list_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        data = json.loads(resp)
        assert "tools" in data["result"***REMOVED***
        assert len(data["result"***REMOVED***["tools"***REMOVED***) > 0

    def test_tools_list_includes_knowledge_search(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        names = [t["name"***REMOVED*** for t in json.loads(resp)["result"***REMOVED***["tools"***REMOVED******REMOVED***
        assert "knowledge_search" in names


class TestPostResourcesList:
    def test_resources_list(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/list"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "resources" in json.loads(resp)["result"***REMOVED***


class TestPostPromptsList:
    def test_prompts_list(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "prompts" in json.loads(resp)["result"***REMOVED***


class TestPostToolsCall:
    def test_session_status_tool(self, addr):
        host, port = addr
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "session_status", "arguments": {***REMOVED******REMOVED***,
        ***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert "content" in json.loads(resp)["result"***REMOVED***


class TestPostBatch:
    def test_batch_request(self, addr):
        host, port = addr
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"***REMOVED***,
        ***REMOVED***
        status, headers, resp = _http(host, port, "POST", body=json.dumps(batch))
        assert status == 200
        data = json.loads(resp)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0***REMOVED***["id"***REMOVED*** == 1
        assert data[1***REMOVED***["id"***REMOVED*** == 2

    def test_batch_all_notifications(self, addr):
        host, port = addr
        batch = [{"jsonrpc": "2.0", "method": "notifications/initialized"***REMOVED******REMOVED***
        status, headers, resp = _http(host, port, "POST", body=json.dumps(batch))
        assert status == 202


class TestPostErrors:
    def test_invalid_json_returns_400(self, addr):
        host, port = addr
        status, headers, resp = _http(host, port, "POST", body="{invalid")
        assert status == 400
        assert json.loads(resp)["error"***REMOVED***["code"***REMOVED*** == PARSE_ERROR

    def test_unknown_method_returns_error(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["error"***REMOVED***["code"***REMOVED*** == METHOD_NOT_FOUND

    def test_unknown_session_id_returns_404(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Mcp-Session-Id": "nonexistent"***REMOVED***,
        )
        assert status == 404

    def test_shutdown_returns_200(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "shutdown"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200
        assert json.loads(resp)["result"***REMOVED*** == {***REMOVED***


# ═══════════════════════════════════════════════════════════════
# DELETE /mcp
# ═══════════════════════════════════════════════════════════════


class TestDelete:
    def test_delete_session(self, addr):
        host, port = addr
        # Create session via initialize
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        _, init_h, _ = _http(host, port, "POST", body=body)
        session_id = init_h["mcp-session-id"***REMOVED***

        status, headers, resp = _http(
            host, port, "DELETE", headers={"Mcp-Session-Id": session_id***REMOVED***
        )
        assert status == 204

    def test_delete_unknown_session(self, addr):
        host, port = addr
        status, headers, resp = _http(
            host, port, "DELETE", headers={"Mcp-Session-Id": "nonexistent"***REMOVED***
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
            host, port, "GET", headers={"Mcp-Session-Id": "nonexistent"***REMOVED***
        )
        assert status == 404

    def test_get_sse_content_type(self, addr):
        host, port = addr
        # Create session first
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
        _, init_h, _ = _http(host, port, "POST", body=body)
        session_id = init_h["mcp-session-id"***REMOVED***

        # GET SSE stream
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        request = (
            f"GET /mcp HTTP/1.1\r\n"
            f"Host: {host***REMOVED***:{port***REMOVED***\r\n"
            f"Mcp-Session-Id: {session_id***REMOVED***\r\n"
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
        assert "200" in header_str.split("\r\n")[0***REMOVED***
        assert "text/event-stream" in header_str
        assert PROTOCOL_VERSION in header_str


# ═══════════════════════════════════════════════════════════════
# Origin Validation
# ═══════════════════════════════════════════════════════════════


class TestOriginValidation:
    def test_evil_origin_rejected(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://evil.com"***REMOVED***,
        )
        assert status == 403

    def test_localhost_origin_allowed(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://localhost:3000"***REMOVED***,
        )
        assert status == 200

    def test_no_origin_allowed(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(host, port, "POST", body=body)
        assert status == 200

    def test_evil_origin_bypass_attempt(self, addr):
        host, port = addr
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
        status, headers, resp = _http(
            host, port, "POST", body=body,
            headers={"Origin": "http://localhost.evil.com"***REMOVED***,
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
