#!/usr/bin/env python3
"""
test_mcp_server.py — Тесты MCP Server для Buffy Project.

Покрытие:
  - JSON-RPC protocol (initialize, ping, errors)
  - tools/list, tools/call
  - resources/list, resources/read
  - prompts/list, prompts/get
  - Knowledge search tool
  - Memory store/retrieve/list tools
  - Session status + context resume tools
  - Plugin list tool
  - Error handling (unknown method, invalid params)
  - Batch requests
  - CLI interface (--status, --tools, --resources)
"""

import json
import os
import shutil
import sys
import tempfile
***REMOVED***
from unittest.mock import patch, MagicMock

import pytest

GIT_AVAILABLE = shutil.which("git") is not None

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts.mcp_server import (
    BuffyMcpServer,
    McpTool,
    McpResource,
    McpPrompt,
    McpSession,
    McpSessionManager,
    rpc_response,
    rpc_error,
    rpc_notification,
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    PARSE_ERROR,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)

import http.client
import socket
import threading
import time
from contextlib import contextmanager


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def server(tmp_path):
    """Create a BuffyMcpServer with a temp workspace."""
    return BuffyMcpServer(workspace_root=str(tmp_path))


@pytest.fixture
def initialized_server(server):
    """Pre-initialized server."""
    server.handle_initialize({"clientInfo": {"name": "test-client", "version": "1.0"***REMOVED******REMOVED***)
    return server


# ═══════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════


class TestRpcHelpers:
    """Test JSON-RPC response/error helpers."""

    def test_rpc_response(self):
        resp = json.loads(rpc_response(1, {"ok": True***REMOVED***))
        assert resp["jsonrpc"***REMOVED*** == "2.0"
        assert resp["id"***REMOVED*** == 1
        assert resp["result"***REMOVED*** == {"ok": True***REMOVED***

    def test_rpc_response_string_id(self):
        resp = json.loads(rpc_response("abc", {"data": 42***REMOVED***))
        assert resp["id"***REMOVED*** == "abc"
        assert resp["result"***REMOVED*** == {"data": 42***REMOVED***

    def test_rpc_error(self):
        resp = json.loads(rpc_error(1, METHOD_NOT_FOUND, "not found"))
        assert resp["jsonrpc"***REMOVED*** == "2.0"
        assert resp["id"***REMOVED*** == 1
        assert resp["error"***REMOVED***["code"***REMOVED*** == METHOD_NOT_FOUND
        assert resp["error"***REMOVED***["message"***REMOVED*** == "not found"
        assert "data" not in resp["error"***REMOVED***

    def test_rpc_error_with_data(self):
        resp = json.loads(rpc_error(1, INTERNAL_ERROR, "boom", {"trace": "stack"***REMOVED***))
        assert resp["error"***REMOVED***["data"***REMOVED*** == {"trace": "stack"***REMOVED***

    def test_rpc_notification(self):
        notif = json.loads(rpc_notification("test.event", {"key": "val"***REMOVED***))
        assert notif["jsonrpc"***REMOVED*** == "2.0"
        assert notif["method"***REMOVED*** == "test.event"
        assert "id" not in notif
        assert notif["params"***REMOVED*** == {"key": "val"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Initialize / Handshake
# ═══════════════════════════════════════════════════════════════


class TestInitialize:
    """Test MCP initialize handshake."""

    def test_initialize_returns_protocol_version(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"***REMOVED******REMOVED***)
        assert result["protocolVersion"***REMOVED*** == PROTOCOL_VERSION

    def test_initialize_returns_server_info(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"***REMOVED******REMOVED***)
        assert result["serverInfo"***REMOVED***["name"***REMOVED*** == SERVER_NAME
        assert result["serverInfo"***REMOVED***["version"***REMOVED*** == SERVER_VERSION

    def test_initialize_returns_capabilities(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"***REMOVED******REMOVED***)
        caps = result["capabilities"***REMOVED***
        assert "tools" in caps
        assert "resources" in caps
        assert "prompts" in caps

    def test_initialize_sets_initialized_flag(self, server):
        assert server._initialized is False
        server.handle_initialize({"clientInfo": {"name": "test"***REMOVED******REMOVED***)
        assert server._initialized is True

    def test_dispatch_initialize(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert resp["id"***REMOVED*** == 1
        assert "result" in resp
        assert resp["result"***REMOVED***["protocolVersion"***REMOVED*** == PROTOCOL_VERSION

    def test_notifications_initialized_no_response(self, server):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {***REMOVED******REMOVED***
        resp = server.dispatch(msg)
        assert resp is None  # notifications don't get responses


# ═══════════════════════════════════════════════════════════════
# Ping
# ═══════════════════════════════════════════════════════════════


class TestPing:
    def test_ping(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert resp["id"***REMOVED*** == 1
        assert resp["result"***REMOVED*** == {***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════


class TestToolsList:
    """Test tools/list."""

    def test_list_returns_all_tools(self, server):
        result = server.handle_tools_list({***REMOVED***)
        tools = result["tools"***REMOVED***
        assert len(tools) > 0
        # Should include knowledge_search and memory_store
        names = [t["name"***REMOVED*** for t in tools***REMOVED***
        assert "knowledge_search" in names
        assert "memory_store" in names
        assert "memory_retrieve" in names
        assert "session_status" in names

    def test_list_tool_has_schema(self, server):
        result = server.handle_tools_list({***REMOVED***)
        ks = next(t for t in result["tools"***REMOVED*** if t["name"***REMOVED*** == "knowledge_search")
        assert "inputSchema" in ks
        assert ks["inputSchema"***REMOVED***["type"***REMOVED*** == "object"
        assert "query" in ks["inputSchema"***REMOVED***["properties"***REMOVED***
        assert "query" in ks["inputSchema"***REMOVED***.get("required", [***REMOVED***)

    def test_dispatch_tools_list(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert "tools" in resp["result"***REMOVED***


class TestToolsCall:
    """Test tools/call."""

    def test_call_unknown_tool(self, server):
        with pytest.raises(ValueError, match="Unknown tool"):
            server.handle_tools_call({"name": "nonexistent", "arguments": {***REMOVED******REMOVED***)

    def test_call_knowledge_search_empty_query(self, server):
        result = server.handle_tools_call({"name": "knowledge_search", "arguments": {***REMOVED******REMOVED***)
        assert result["isError"***REMOVED*** is True

    def test_call_knowledge_search_with_query(self, server):
        result = server.handle_tools_call({
            "name": "knowledge_search",
            "arguments": {"query": "router capability"***REMOVED***,
        ***REMOVED***)
        # May return empty results if KE not seeded, but shouldn't error
        assert "content" in result
        assert len(result["content"***REMOVED***) == 1
        assert result["content"***REMOVED***[0***REMOVED***["type"***REMOVED*** == "text"

    def test_call_memory_store_and_retrieve(self, server):
        # Store
        store_result = server.handle_tools_call({
            "name": "memory_store",
            "arguments": {
                "level": "working",
                "key": "test_key",
                "content": "test content",
                "summary": "test summary",
            ***REMOVED***,
        ***REMOVED***)
        assert store_result["isError"***REMOVED*** is False

        # Retrieve
        ret_result = server.handle_tools_call({
            "name": "memory_retrieve",
            "arguments": {"level": "working", "key": "test_key"***REMOVED***,
        ***REMOVED***)
        assert ret_result["isError"***REMOVED*** is False
        data = json.loads(ret_result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***)
        assert data["success"***REMOVED*** is True
        assert data["data"***REMOVED***["content"***REMOVED*** == "test content"

    def test_call_memory_store_invalid_level(self, server):
        result = server.handle_tools_call({
            "name": "memory_store",
            "arguments": {"level": "invalid", "key": "k", "content": "c"***REMOVED***,
        ***REMOVED***)
        assert result["isError"***REMOVED*** is True

    def test_call_memory_list(self, server):
        # Store something first
        server.handle_tools_call({
            "name": "memory_store",
            "arguments": {"level": "working", "key": "k1", "content": "c1"***REMOVED***,
        ***REMOVED***)
        result = server.handle_tools_call({
            "name": "memory_list",
            "arguments": {"level": "working"***REMOVED***,
        ***REMOVED***)
        assert result["isError"***REMOVED*** is False
        data = json.loads(result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***)
        assert data["success"***REMOVED*** is True
        assert len(data["data"***REMOVED***) >= 1

    def test_call_session_status(self, server):
        result = server.handle_tools_call({
            "name": "session_status",
            "arguments": {***REMOVED***,
        ***REMOVED***)
        assert "content" in result
        assert result["isError"***REMOVED*** is False

    def test_call_context_resume(self, server):
        result = server.handle_tools_call({
            "name": "context_resume",
            "arguments": {***REMOVED***,
        ***REMOVED***)
        assert "content" in result

    def test_call_plugins_list(self, server):
        result = server.handle_tools_call({
            "name": "plugins_list",
            "arguments": {***REMOVED***,
        ***REMOVED***)
        assert "content" in result

    def test_dispatch_tools_call(self, server):
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "session_status", "arguments": {***REMOVED******REMOVED***,
        ***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert resp["id"***REMOVED*** == 1
        assert "result" in resp
        assert "content" in resp["result"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════


class TestResourcesList:
    """Test resources/list."""

    def test_list_returns_resources(self, server):
        result = server.handle_resources_list({***REMOVED***)
        resources = result["resources"***REMOVED***
        assert len(resources) > 0
        uris = [r["uri"***REMOVED*** for r in resources***REMOVED***
        assert "buffy://manifest" in uris
        assert "buffy://roadmap" in uris
        assert "buffy://knowledge" in uris
        assert "buffy://memory" in uris

    def test_resource_has_fields(self, server):
        result = server.handle_resources_list({***REMOVED***)
        res = next(r for r in result["resources"***REMOVED*** if r["uri"***REMOVED*** == "buffy://manifest")
        assert "name" in res
        assert "description" in res
        assert "mimeType" in res


class TestResourcesRead:
    """Test resources/read."""

    def test_read_manifest(self, server):
        # Create a fake BUFFY.md in temp workspace
        (Path(server.workspace) / "BUFFY.md").write_text("# Buffy\nTest manifest", encoding="utf-8")
        result = server.handle_resources_read({"uri": "buffy://manifest"***REMOVED***)
        assert len(result["contents"***REMOVED***) == 1
        assert "Buffy" in result["contents"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert result["contents"***REMOVED***[0***REMOVED***["mimeType"***REMOVED*** == "text/markdown"

    def test_read_unknown_resource(self, server):
        with pytest.raises(ValueError, match="Unknown resource"):
            server.handle_resources_read({"uri": "buffy://nonexistent"***REMOVED***)

    def test_read_knowledge_overview(self, server):
        result = server.handle_resources_read({"uri": "buffy://knowledge"***REMOVED***)
        assert len(result["contents"***REMOVED***) == 1
        # Should be JSON (list of knowledge entries)
        data = json.loads(result["contents"***REMOVED***[0***REMOVED***["text"***REMOVED***)
        assert isinstance(data, list)

    def test_read_memory_overview(self, server):
        result = server.handle_resources_read({"uri": "buffy://memory"***REMOVED***)
        assert len(result["contents"***REMOVED***) == 1
        data = json.loads(result["contents"***REMOVED***[0***REMOVED***["text"***REMOVED***)
        assert isinstance(data, dict)
        # Should have all 5 levels
        assert "working" in data
        assert "knowledge" in data


# ═══════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════


class TestPrompts:
    """Test prompts/list and prompts/get."""

    def test_list_prompts(self, server):
        result = server.handle_prompts_list({***REMOVED***)
        prompts = result["prompts"***REMOVED***
        names = [p["name"***REMOVED*** for p in prompts***REMOVED***
        assert "context_resume" in names
        assert "knowledge_search" in names
        assert "task_start" in names

    def test_get_context_resume_prompt(self, server):
        result = server.handle_prompts_get({"name": "context_resume", "arguments": {***REMOVED******REMOVED***)
        assert "messages" in result
        assert result["messages"***REMOVED***[0***REMOVED***["role"***REMOVED*** == "user"
        assert "session" in result["messages"***REMOVED***[0***REMOVED***["content"***REMOVED***["text"***REMOVED***.lower()

    def test_get_task_start_prompt(self, server):
        result = server.handle_prompts_get({
            "name": "task_start",
            "arguments": {"task": "implement feature X", "project": "freebuff"***REMOVED***,
        ***REMOVED***)
        text = result["messages"***REMOVED***[0***REMOVED***["content"***REMOVED***["text"***REMOVED***
        assert "implement feature X" in text

    def test_get_unknown_prompt(self, server):
        with pytest.raises(ValueError, match="Unknown prompt"):
            server.handle_prompts_get({"name": "nonexistent", "arguments": {***REMOVED******REMOVED***)


# ═══════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test JSON-RPC error handling."""

    def test_unknown_method(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "unknown/method"***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert "error" in resp
        assert resp["error"***REMOVED***["code"***REMOVED*** == METHOD_NOT_FOUND

    def test_notification_unknown_method_no_response(self, server):
        msg = {"jsonrpc": "2.0", "method": "unknown/method", "params": {***REMOVED******REMOVED***
        resp = server.dispatch(msg)
        assert resp is None

    def test_shutdown_method(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "shutdown"***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert resp["id"***REMOVED*** == 1
        assert resp["result"***REMOVED*** == {***REMOVED***

    def test_logging_set_level(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "logging/setLevel", "params": {"level": "info"***REMOVED******REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert resp["id"***REMOVED*** == 1
        assert resp["result"***REMOVED*** == {***REMOVED***

    def test_invalid_params_raises_error(self, server):
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {***REMOVED******REMOVED***,
        ***REMOVED***
        resp = json.loads(server.dispatch(msg))
        assert "error" in resp
        assert resp["error"***REMOVED***["code"***REMOVED*** == INVALID_PARAMS


# ═══════════════════════════════════════════════════════════════
# Batch requests
# ═══════════════════════════════════════════════════════════════


class TestBatchRequests:
    """Test JSON-RPC batch request handling."""

    def test_batch_two_requests(self, server):
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"***REMOVED***,
        ***REMOVED***
        responses = [***REMOVED***
        for msg in batch:
            resp = server.dispatch(msg)
            if resp:
                responses.append(json.loads(resp))
        assert len(responses) == 2
        assert responses[0***REMOVED***["id"***REMOVED*** == 1
        assert responses[1***REMOVED***["id"***REMOVED*** == 2

    def test_batch_with_notification(self, server):
        batch = [
            {"jsonrpc": "2.0", "method": "notifications/initialized"***REMOVED***,
            {"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***,
        ***REMOVED***
        responses = [***REMOVED***
        for msg in batch:
            resp = server.dispatch(msg)
            if resp:
                responses.append(json.loads(resp))
        # Only the ping should get a response
        assert len(responses) == 1
        assert responses[0***REMOVED***["id"***REMOVED*** == 1


# ═══════════════════════════════════════════════════════════════
# Server status / introspection
# ═══════════════════════════════════════════════════════════════


class TestServerStatus:
    """Test server status and introspection."""

    def test_status(self, server):
        status = server.get_status()
        assert status["server"***REMOVED*** == SERVER_NAME
        assert status["version"***REMOVED*** == SERVER_VERSION
        assert status["protocol"***REMOVED*** == PROTOCOL_VERSION
        assert status["tools"***REMOVED*** > 0
        assert status["resources"***REMOVED*** > 0
        assert status["prompts"***REMOVED*** > 0
        assert isinstance(status["tool_names"***REMOVED***, list)
        assert isinstance(status["resource_uris"***REMOVED***, list)

    def test_list_tools_info(self, server):
        tools = server.list_tools_info()
        assert len(tools) > 0
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)
        assert all("category" in t for t in tools)

    def test_list_resources_info(self, server):
        resources = server.list_resources_info()
        assert len(resources) > 0
        assert all("uri" in r for r in resources)


# ═══════════════════════════════════════════════════════════════
# McpTool / McpResource / McpPrompt dataclasses
# ═══════════════════════════════════════════════════════════════


class TestDataclasses:
    """Test MCP data classes."""

    def test_mcp_tool_defaults(self):
        tool = McpTool(name="test", description="test tool")
        assert tool.input_schema == {"type": "object", "properties": {***REMOVED******REMOVED***
        assert tool.handler is None
        assert tool.category == "general"

    def test_mcp_resource_defaults(self):
        res = McpResource(uri="test://x", name="x", description="d")
        assert res.mime_type == "text/plain"
        assert res.handler is None

    def test_mcp_prompt_defaults(self):
        p = McpPrompt(name="test", description="d")
        assert p.arguments == [***REMOVED***
        assert p.handler is None


# ═══════════════════════════════════════════════════════════════
# ToolRegistry integration
# ═══════════════════════════════════════════════════════════════


class TestToolRegistryIntegration:
    """Test that ToolRegistry tools are auto-discovered as MCP tools."""

    def test_git_tool_registered(self, server):
        names = [t["name"***REMOVED*** for t in server.handle_tools_list({***REMOVED***)["tools"***REMOVED******REMOVED***
        assert "git" in names

    def test_file_tool_registered(self, server):
        names = [t["name"***REMOVED*** for t in server.handle_tools_list({***REMOVED***)["tools"***REMOVED******REMOVED***
        assert "file" in names

    def test_shell_tool_registered(self, server):
        names = [t["name"***REMOVED*** for t in server.handle_tools_list({***REMOVED***)["tools"***REMOVED******REMOVED***
        assert "shell" in names

    def test_git_tool_has_input_schema(self, server):
        tools = server.handle_tools_list({***REMOVED***)["tools"***REMOVED***
        git_tool = next(t for t in tools if t["name"***REMOVED*** == "git")
        props = git_tool["inputSchema"***REMOVED***["properties"***REMOVED***
        assert "command" in props
        assert props["command"***REMOVED***["type"***REMOVED*** == "string"
        assert "command" in git_tool["inputSchema"***REMOVED***.get("required", [***REMOVED***)

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
    def test_call_git_status(self, server):
        # Initialize a git repo in temp workspace
        import subprocess
        subprocess.run(["git", "init"***REMOVED***, cwd=server.workspace, capture_output=True)
        subprocess.run(["git", "config", "user.name", "test"***REMOVED***, cwd=server.workspace, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"***REMOVED***, cwd=server.workspace, capture_output=True)

        result = server.handle_tools_call({
            "name": "git",
            "arguments": {"command": "status"***REMOVED***,
        ***REMOVED***)
        assert "content" in result
        # git status should work
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        # Should be successful (returncode 0 for status)
        assert "data" in data


# ═══════════════════════════════════════════════════════════════
# Session Manager (Streamable HTTP)
# ═══════════════════════════════════════════════════════════════


class TestSessionManager:
    """Test McpSessionManager for Streamable HTTP transport."""

    def test_create_session_returns_id(self):
        sm = McpSessionManager()
        sid = sm.create_session()
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_get_session_returns_session(self):
        sm = McpSessionManager()
        sid = sm.create_session()
        session = sm.get_session(sid)
        assert session is not None
        assert session.session_id == sid
        assert session.active is True

    def test_get_session_returns_none_for_unknown(self):
        sm = McpSessionManager()
        assert sm.get_session("nonexistent") is None

    def test_delete_session(self):
        sm = McpSessionManager()
        sid = sm.create_session()
        assert sm.delete_session(sid) is True
        assert sm.get_session(sid) is None

    def test_delete_session_unknown(self):
        sm = McpSessionManager()
        assert sm.delete_session("nonexistent") is False

    def test_push_notification(self):
        sm = McpSessionManager()
        sid = sm.create_session()
        assert sm.push_notification(sid, 'data: {"test": true***REMOVED***') is True
        session = sm.get_session(sid)
        msg = session.notification_queue.get_nowait()
        assert '{"test": true***REMOVED***' in msg

    def test_push_notification_to_deleted_session(self):
        sm = McpSessionManager()
        sid = sm.create_session()
        sm.delete_session(sid)
        assert sm.push_notification(sid, "test") is False

    def test_session_count(self):
        sm = McpSessionManager()
        assert sm.count() == 0
        s1 = sm.create_session()
        s2 = sm.create_session()
        assert sm.count() == 2
        sm.delete_session(s1)
        assert sm.count() == 1

    def test_session_id_is_unique(self):
        sm = McpSessionManager()
        ids = {sm.create_session() for _ in range(100)***REMOVED***
        assert len(ids) == 100

    def test_session_manager_thread_safe(self):
        import threading
        sm = McpSessionManager()
        results = [***REMOVED***

        def create_sessions():
            for _ in range(50):
                results.append(sm.create_session())

        threads = [threading.Thread(target=create_sessions) for _ in range(4)***REMOVED***
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 200
        assert len(set(results)) == 200  # all unique


# ═══════════════════════════════════════════════════════════════
# HTTP Transport (Streamable HTTP — MCP 2025-03-26)
# ═══════════════════════════════════════════════════════════════


@contextmanager
def _start_http_server(mcp_server: BuffyMcpServer, port: int = 0):
    """Start McpHttpServer on a random available port, yield (host, port)."""
    from scripts.mcp_server import McpHttpServer, McpHTTPRequestHandler, McpSessionManager

    session_mgr = McpSessionManager()
    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1***REMOVED***

    httpd = McpHttpServer(
        ("127.0.0.1", port),
        McpHTTPRequestHandler,
        mcp_server,
        session_mgr,
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", port, session_mgr
    finally:
        httpd.shutdown()
        httpd.server_close()


def _http_request(host: str, port: int, method: str, path: str = "/mcp",
                   body: Optional[str***REMOVED*** = None,
                   headers: Optional[dict***REMOVED*** = None) -> Tuple[int, dict, str***REMOVED***:
    """Make an HTTP request and return (status, headers, body)."""
    conn = http.client.HTTPConnection(host, port, timeout=5)
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


class TestHttpTransport:
    """Test Streamable HTTP transport (POST/GET/DELETE at /mcp)."""

    def test_post_initialize_creates_session(self, server):
        """POST initialize should return 200 with Mcp-Session-Id header."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            assert "mcp-session-id" in headers
            assert "mcp-protocol-version" in headers
            data = json.loads(resp_body)
            assert data["result"***REMOVED***["protocolVersion"***REMOVED*** == PROTOCOL_VERSION
            # Session was created
            session_id = headers["mcp-session-id"***REMOVED***
            assert sm.get_session(session_id) is not None

    def test_post_ping(self, server):
        """POST ping should return 200 with JSON-RPC response."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["id"***REMOVED*** == 1
            assert data["result"***REMOVED*** == {***REMOVED***

    def test_post_notification_returns_202(self, server):
        """POST notification (no id) should return 202 Accepted."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {***REMOVED******REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 202
            assert resp_body == ""

    def test_post_tools_list(self, server):
        """POST tools/list should return 200 with tool list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "tools" in data["result"***REMOVED***
            assert len(data["result"***REMOVED***["tools"***REMOVED***) > 0

    def test_post_resources_list(self, server):
        """POST resources/list should return 200 with resource list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/list"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "resources" in data["result"***REMOVED***

    def test_post_prompts_list(self, server):
        """POST prompts/list should return 200 with prompt list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "prompts" in data["result"***REMOVED***

    def test_post_batch_request(self, server):
        """POST batch request should return 200 with array of responses."""
        with _start_http_server(server) as (host, port, sm):
            batch = [
                {"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***,
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"***REMOVED***,
            ***REMOVED***
            body = json.dumps(batch)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0***REMOVED***["id"***REMOVED*** == 1
            assert data[1***REMOVED***["id"***REMOVED*** == 2

    def test_post_batch_all_notifications(self, server):
        """POST batch with only notifications should return 202."""
        with _start_http_server(server) as (host, port, sm):
            batch = [
                {"jsonrpc": "2.0", "method": "notifications/initialized"***REMOVED***,
            ***REMOVED***
            body = json.dumps(batch)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 202

    def test_post_unknown_method(self, server):
        """POST unknown method should return 200 with JSON-RPC error."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["error"***REMOVED***["code"***REMOVED*** == METHOD_NOT_FOUND

    def test_post_invalid_json(self, server):
        """POST invalid JSON should return 400 with parse error."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(host, port, "POST", body="{invalid")
            assert status == 400
            data = json.loads(resp_body)
            assert data["error"***REMOVED***["code"***REMOVED*** == PARSE_ERROR

    def test_post_wrong_path(self, server):
        """POST to wrong path should return 404."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", path="/wrong", body=body)
            assert status == 404

    def test_delete_terminates_session(self, server):
        """DELETE with Mcp-Session-Id should terminate session (204)."""
        with _start_http_server(server) as (host, port, sm):
            # Create session via initialize
            init_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {***REMOVED******REMOVED***)
            _, init_headers, _ = _http_request(host, port, "POST", body=init_body)
            session_id = init_headers["mcp-session-id"***REMOVED***

            # Delete it
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": session_id***REMOVED***
            )
            assert status == 204
            assert sm.get_session(session_id) is None

    def test_delete_unknown_session(self, server):
        """DELETE with unknown session should return 404."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": "nonexistent"***REMOVED***
            )
            assert status == 404

    def test_delete_without_session_id(self, server):
        """DELETE without Mcp-Session-Id should return 400."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(host, port, "DELETE")
            assert status == 400

    def test_get_without_session_id(self, server):
        """GET without Mcp-Session-Id should return 400."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(host, port, "GET")
            assert status == 400

    def test_get_unknown_session(self, server):
        """GET with unknown session should return 404."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(
                host, port, "GET", headers={"Mcp-Session-Id": "nonexistent"***REMOVED***
            )
            assert status == 404

    def test_get_wrong_path(self, server):
        """GET to wrong path should return 404."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(host, port, "GET", path="/wrong")
            assert status == 404

    def test_post_tools_call(self, server):
        """POST tools/call should return 200 with tool result."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "session_status", "arguments": {***REMOVED******REMOVED***,
            ***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "content" in data["result"***REMOVED***

    def test_protocol_version_header(self, server):
        """All responses should include Mcp-Protocol-Version header."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert headers.get("mcp-protocol-version") == PROTOCOL_VERSION

    def test_post_shutdown(self, server):
        """POST shutdown should return 200 with empty result."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "shutdown"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["result"***REMOVED*** == {***REMOVED***

    def test_post_invalid_origin_rejected(self, server):
        """POST with invalid Origin header should return 403."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Origin": "http://evil.com"***REMOVED***,
            )
            assert status == 403

    def test_post_localhost_origin_allowed(self, server):
        """POST with localhost Origin should be allowed."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Origin": "http://localhost:3000"***REMOVED***,
            )
            assert status == 200

    def test_post_no_origin_allowed(self, server):
        """POST without Origin (CLI client) should be allowed."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200

    def test_post_with_invalid_session_id_rejected(self, server):
        """POST with invalid Mcp-Session-Id should return 404."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"***REMOVED***)
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Mcp-Session-Id": "nonexistent-session"***REMOVED***,
            )
            assert status == 404

    def test_get_sse_stream_receives_notification(self, server):
        """GET SSE stream should receive notifications pushed via session_manager."""
        with _start_http_server(server) as (host, port, sm):
            # Create a session
            sid = sm.create_session()

            # Use raw socket to read SSE with timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            request = (
                f"GET /mcp HTTP/1.1\r\n"
                f"Host: {host***REMOVED***:{port***REMOVED***\r\n"
                f"Mcp-Session-Id: {sid***REMOVED***\r\n"
                f"Accept: text/event-stream\r\n"
                f"Connection: keep-alive\r\n"
                f"\r\n"
            )
            sock.sendall(request.encode("utf-8"))

            # Read HTTP headers (until empty line)
            header_data = b""
            while b"\r\n\r\n" not in header_data:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                header_data += chunk

            # Verify we got 200 + text/event-stream
            header_str = header_data.decode("utf-8", errors="replace")
            assert "200" in header_str.split("\r\n")[0***REMOVED***, f"Expected 200, got: {header_str.split(chr(13)+chr(10))[0***REMOVED******REMOVED***"
            assert "text/event-stream" in header_str

            # Push a notification
            notification = json.dumps({"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 50***REMOVED******REMOVED***)
            sm.push_notification(sid, notification)

            # Read SSE data (should get 'data: ...\n\n')
            sse_data = b""
            try:
                while b"data:" not in sse_data:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    sse_data += chunk
            except socket.timeout:
                pass

            sock.close()

            sse_text = sse_data.decode("utf-8", errors="replace")
            assert "data:" in sse_text, f"No 'data:' in SSE response: {sse_text!r***REMOVED***"
            assert "notifications/progress" in sse_text

    def test_delete_no_content_length_header(self, server):
        """204 response must NOT have Content-Length header (RFC 7230)."""
        with _start_http_server(server) as (host, port, sm):
            sid = sm.create_session()
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": sid***REMOVED***
            )
            assert status == 204
            assert "content-length" not in headers
