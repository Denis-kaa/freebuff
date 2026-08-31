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
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

GIT_AVAILABLE = shutil.which("git") is not None

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.mcp_server import (
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
from freebuff_plugin_03.runtime import RuntimeResult

import http.client
import socket
import threading
import time
from contextlib import contextmanager
from typing import Optional, Tuple


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
    server.handle_initialize({"clientInfo": {"name": "test-client", "version": "1.0"}})
    return server


# ═══════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════


class TestRpcHelpers:
    """Test JSON-RPC response/error helpers."""

    def test_rpc_response(self):
        resp = json.loads(rpc_response(1, {"ok": True}))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["result"] == {"ok": True}

    def test_rpc_response_string_id(self):
        resp = json.loads(rpc_response("abc", {"data": 42}))
        assert resp["id"] == "abc"
        assert resp["result"] == {"data": 42}

    def test_rpc_error(self):
        resp = json.loads(rpc_error(1, METHOD_NOT_FOUND, "not found"))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["error"]["code"] == METHOD_NOT_FOUND
        assert resp["error"]["message"] == "not found"
        assert "data" not in resp["error"]

    def test_rpc_error_with_data(self):
        resp = json.loads(rpc_error(1, INTERNAL_ERROR, "boom", {"trace": "stack"}))
        assert resp["error"]["data"] == {"trace": "stack"}

    def test_rpc_notification(self):
        notif = json.loads(rpc_notification("test.event", {"key": "val"}))
        assert notif["jsonrpc"] == "2.0"
        assert notif["method"] == "test.event"
        assert "id" not in notif
        assert notif["params"] == {"key": "val"}


# ═══════════════════════════════════════════════════════════════
# Initialize / Handshake
# ═══════════════════════════════════════════════════════════════


class TestInitialize:
    """Test MCP initialize handshake."""

    def test_initialize_returns_protocol_version(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"}})
        assert result["protocolVersion"] == PROTOCOL_VERSION

    def test_initialize_returns_server_info(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"}})
        assert result["serverInfo"]["name"] == SERVER_NAME
        assert result["serverInfo"]["version"] == SERVER_VERSION

    def test_initialize_returns_capabilities(self, server):
        result = server.handle_initialize({"clientInfo": {"name": "test"}})
        caps = result["capabilities"]
        assert "tools" in caps
        assert "resources" in caps
        assert "prompts" in caps

    def test_initialize_sets_initialized_flag(self, server):
        assert server._initialized is False
        server.handle_initialize({"clientInfo": {"name": "test"}})
        assert server._initialized is True

    def test_dispatch_initialize(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = json.loads(server.dispatch(msg))
        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["protocolVersion"] == PROTOCOL_VERSION

    def test_notifications_initialized_no_response(self, server):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        resp = server.dispatch(msg)
        assert resp is None  # notifications don't get responses


# ═══════════════════════════════════════════════════════════════
# Ping
# ═══════════════════════════════════════════════════════════════


class TestPing:
    def test_ping(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        resp = json.loads(server.dispatch(msg))
        assert resp["id"] == 1
        assert resp["result"] == {}


# ═══════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════


class TestToolsList:
    """Test tools/list."""

    def test_list_returns_all_tools(self, server):
        result = server.handle_tools_list({})
        tools = result["tools"]
        assert len(tools) > 0
        # Should include knowledge_search and memory_store
        names = [t["name"] for t in tools]
        assert "knowledge_search" in names
        assert "memory_store" in names
        assert "memory_retrieve" in names
        assert "session_status" in names

    def test_list_tool_has_schema(self, server):
        result = server.handle_tools_list({})
        ks = next(t for t in result["tools"] if t["name"] == "knowledge_search")
        assert "inputSchema" in ks
        assert ks["inputSchema"]["type"] == "object"
        assert "query" in ks["inputSchema"]["properties"]
        assert "query" in ks["inputSchema"].get("required", [])

    def test_dispatch_tools_list(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        resp = json.loads(server.dispatch(msg))
        assert "tools" in resp["result"]


class TestToolsCall:
    """Test tools/call."""

    def test_call_unknown_tool(self, server):
        with pytest.raises(ValueError, match="Unknown tool"):
            server.handle_tools_call({"name": "nonexistent", "arguments": {}})

    def test_call_knowledge_search_empty_query(self, server):
        result = server.handle_tools_call({"name": "knowledge_search", "arguments": {}})
        assert result["isError"] is True

    def test_call_knowledge_search_with_query(self, server):
        result = server.handle_tools_call({
            "name": "knowledge_search",
            "arguments": {"query": "router capability"},
        })
        # May return empty results if KE not seeded, but shouldn't error
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"

    def test_call_memory_store_and_retrieve(self, server):
        # Store
        store_result = server.handle_tools_call({
            "name": "memory_store",
            "arguments": {
                "level": "working",
                "key": "test_key",
                "content": "test content",
                "summary": "test summary",
            },
        })
        assert store_result["isError"] is False

        # Retrieve
        ret_result = server.handle_tools_call({
            "name": "memory_retrieve",
            "arguments": {"level": "working", "key": "test_key"},
        })
        assert ret_result["isError"] is False
        data = json.loads(ret_result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["content"] == "test content"

    def test_call_memory_store_invalid_level(self, server):
        result = server.handle_tools_call({
            "name": "memory_store",
            "arguments": {"level": "invalid", "key": "k", "content": "c"},
        })
        assert result["isError"] is True

    def test_call_memory_list(self, server):
        # Store something first
        server.handle_tools_call({
            "name": "memory_store",
            "arguments": {"level": "working", "key": "k1", "content": "c1"},
        })
        result = server.handle_tools_call({
            "name": "memory_list",
            "arguments": {"level": "working"},
        })
        assert result["isError"] is False
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert len(data["data"]) >= 1

    def test_call_session_status(self, server):
        result = server.handle_tools_call({
            "name": "session_status",
            "arguments": {},
        })
        assert "content" in result
        assert result["isError"] is False

    def test_call_context_resume(self, server):
        result = server.handle_tools_call({
            "name": "context_resume",
            "arguments": {},
        })
        assert "content" in result

    def test_call_plugins_list(self, server):
        result = server.handle_tools_call({
            "name": "plugins_list",
            "arguments": {},
        })
        assert "content" in result

    def test_dispatch_tools_call(self, server):
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "session_status", "arguments": {}},
        }
        resp = json.loads(server.dispatch(msg))
        assert resp["id"] == 1
        assert "result" in resp
        assert "content" in resp["result"]


# ═══════════════════════════════════════════════════════════════
# Resources
# ═══════════════════════════════════════════════════════════════


class TestResourcesList:
    """Test resources/list."""

    def test_list_returns_resources(self, server):
        result = server.handle_resources_list({})
        resources = result["resources"]
        assert len(resources) > 0
        uris = [r["uri"] for r in resources]
        assert "buffy://manifest" in uris
        assert "buffy://roadmap" in uris
        assert "buffy://knowledge" in uris
        assert "buffy://memory" in uris

    def test_resource_has_fields(self, server):
        result = server.handle_resources_list({})
        res = next(r for r in result["resources"] if r["uri"] == "buffy://manifest")
        assert "name" in res
        assert "description" in res
        assert "mimeType" in res


class TestResourcesRead:
    """Test resources/read."""

    def test_read_manifest(self, server):
        # Create a fake BUFFY.md in temp workspace
        (Path(server.workspace) / "BUFFY.md").write_text("# Buffy\nTest manifest", encoding="utf-8")
        result = server.handle_resources_read({"uri": "buffy://manifest"})
        assert len(result["contents"]) == 1
        assert "Buffy" in result["contents"][0]["text"]
        assert result["contents"][0]["mimeType"] == "text/markdown"

    def test_read_unknown_resource(self, server):
        with pytest.raises(ValueError, match="Unknown resource"):
            server.handle_resources_read({"uri": "buffy://nonexistent"})

    def test_read_knowledge_overview(self, server):
        result = server.handle_resources_read({"uri": "buffy://knowledge"})
        assert len(result["contents"]) == 1
        # Should be JSON (list of knowledge entries)
        data = json.loads(result["contents"][0]["text"])
        assert isinstance(data, list)

    def test_read_memory_overview(self, server):
        result = server.handle_resources_read({"uri": "buffy://memory"})
        assert len(result["contents"]) == 1
        data = json.loads(result["contents"][0]["text"])
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
        result = server.handle_prompts_list({})
        prompts = result["prompts"]
        names = [p["name"] for p in prompts]
        assert "context_resume" in names
        assert "knowledge_search" in names
        assert "task_start" in names

    def test_get_context_resume_prompt(self, server):
        result = server.handle_prompts_get({"name": "context_resume", "arguments": {}})
        assert "messages" in result
        assert result["messages"][0]["role"] == "user"
        assert "session" in result["messages"][0]["content"]["text"].lower()

    def test_get_task_start_prompt(self, server):
        result = server.handle_prompts_get({
            "name": "task_start",
            "arguments": {"task": "implement feature X", "project": "freebuff"},
        })
        text = result["messages"][0]["content"]["text"]
        assert "implement feature X" in text

    def test_get_unknown_prompt(self, server):
        with pytest.raises(ValueError, match="Unknown prompt"):
            server.handle_prompts_get({"name": "nonexistent", "arguments": {}})


# ═══════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test JSON-RPC error handling."""

    def test_unknown_method(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "unknown/method"}
        resp = json.loads(server.dispatch(msg))
        assert "error" in resp
        assert resp["error"]["code"] == METHOD_NOT_FOUND

    def test_notification_unknown_method_no_response(self, server):
        msg = {"jsonrpc": "2.0", "method": "unknown/method", "params": {}}
        resp = server.dispatch(msg)
        assert resp is None

    def test_shutdown_method(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "shutdown"}
        resp = json.loads(server.dispatch(msg))
        assert resp["id"] == 1
        assert resp["result"] == {}

    def test_logging_set_level(self, server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "logging/setLevel", "params": {"level": "info"}}
        resp = json.loads(server.dispatch(msg))
        assert resp["id"] == 1
        assert resp["result"] == {}

    def test_invalid_params_raises_error(self, server):
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = json.loads(server.dispatch(msg))
        assert "error" in resp
        assert resp["error"]["code"] == INVALID_PARAMS


# ═══════════════════════════════════════════════════════════════
# Batch requests
# ═══════════════════════════════════════════════════════════════


class TestBatchRequests:
    """Test JSON-RPC batch request handling."""

    def test_batch_two_requests(self, server):
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        responses = []
        for msg in batch:
            resp = server.dispatch(msg)
            if resp:
                responses.append(json.loads(resp))
        assert len(responses) == 2
        assert responses[0]["id"] == 1
        assert responses[1]["id"] == 2

    def test_batch_with_notification(self, server):
        batch = [
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        ]
        responses = []
        for msg in batch:
            resp = server.dispatch(msg)
            if resp:
                responses.append(json.loads(resp))
        # Only the ping should get a response
        assert len(responses) == 1
        assert responses[0]["id"] == 1


# ═══════════════════════════════════════════════════════════════
# Server status / introspection
# ═══════════════════════════════════════════════════════════════


class TestServerStatus:
    """Test server status and introspection."""

    def test_status(self, server):
        status = server.get_status()
        assert status["server"] == SERVER_NAME
        assert status["version"] == SERVER_VERSION
        assert status["protocol"] == PROTOCOL_VERSION
        assert status["tools"] > 0
        assert status["resources"] > 0
        assert status["prompts"] > 0
        assert isinstance(status["tool_names"], list)
        assert isinstance(status["resource_uris"], list)

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
        assert tool.input_schema == {"type": "object", "properties": {}}
        assert tool.handler is None
        assert tool.category == "general"

    def test_mcp_resource_defaults(self):
        res = McpResource(uri="test://x", name="x", description="d")
        assert res.mime_type == "text/plain"
        assert res.handler is None

    def test_mcp_prompt_defaults(self):
        p = McpPrompt(name="test", description="d")
        assert p.arguments == []
        assert p.handler is None


# ═══════════════════════════════════════════════════════════════
# ToolRegistry integration
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# Bootstrap Engine tools (MCP integration)
# ═══════════════════════════════════════════════════════════════


class TestBootstrapTools:
    """Test bootstrap_check, bootstrap_run, bootstrap_status MCP tools."""

    @staticmethod
    def _mock_subprocess(returncode: int = 0, stdout: str = "", stderr: str = ""):
        """Helper: patch subprocess.run with proper return values."""
        return patch("subprocess.run", return_value=type("Proc", (), {
            "returncode": returncode, "stdout": stdout, "stderr": stderr,
        })())

    def _check_result(self, result, expect_success=True):
        """Helper: parse tool call result and return data dict."""
        assert result["isError"] is False
        data = json.loads(result["content"][0]["text"])
        if expect_success:
            assert data["success"] is True, f"Expected success, got: {data.get('error', '')}"
        return data

    def test_bootstrap_check_returns_env(self, server):
        """bootstrap_check returns environment state."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_check",
                "arguments": {},
            })
            data = self._check_result(result)
            assert "python_version" in data["data"]
            assert data["data"]["workspace"] == str(server.workspace)

    def test_bootstrap_check_quick(self, server):
        """bootstrap_check with quick=True."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_check",
                "arguments": {"quick": True},
            })
            data = self._check_result(result)
            assert "os" in data["data"]

    def test_bootstrap_check_engine_unavailable(self, server):
        """bootstrap_check raises error if engine unavailable."""
        with patch.object(server, "_get_bootstrap_engine", return_value=None):
            result = server.handle_tools_call({
                "name": "bootstrap_check",
                "arguments": {},
            })
            assert result["isError"] is True
            text = result["content"][0]["text"]
            assert "not available" in text

    def test_bootstrap_run_minimal_profile(self, server):
        """bootstrap_run with minimal profile."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_run",
                "arguments": {"profile": "minimal"},
            })
            data = self._check_result(result)
            assert data["data"]["profile"] == "minimal"
            assert "duration_ms" in data["data"]
            assert "steps" in data["data"]
            assert "diagnosis" in data["data"]

    def test_bootstrap_run_default_profile(self, server):
        """bootstrap_run with default (minimal) profile."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_run",
                "arguments": {},
            })
            data = self._check_result(result)
            assert data["data"]["profile"] == "minimal"

    def test_bootstrap_run_developer_profile(self, server):
        """bootstrap_run with developer profile."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_run",
                "arguments": {"profile": "developer"},
            })
            data = self._check_result(result)
            assert data["data"]["profile"] == "developer"

    def test_bootstrap_run_unknown_profile_handled_gracefully(self, server):
        """bootstrap_run with unknown profile handles gracefully (falls back to minimal)."""
        with self._mock_subprocess():
            result = server.handle_tools_call({
                "name": "bootstrap_run",
                "arguments": {"profile": "nonexistent_profile_xyz"},
            })
            # Engine stores the original profile name in report
            # but internally falls back to 'minimal' profile
            data = self._check_result(result, expect_success=True)
            assert "nonexistent_profile_xyz" in data["data"]["profile"]
            assert "duration_ms" in data["data"]
            assert isinstance(data["data"]["steps"], list)

    def test_bootstrap_status_never_run(self, server):
        """bootstrap_status when never run."""
        result = server.handle_tools_call({
            "name": "bootstrap_status",
            "arguments": {},
        })
        data = self._check_result(result)
        assert data["data"]["status"] == "never_run"

    def test_bootstrap_status_after_run(self, server):
        """bootstrap_status after bootstrap_run."""
        with self._mock_subprocess():
            # Run bootstrap first
            server.handle_tools_call({
                "name": "bootstrap_run",
                "arguments": {"profile": "minimal"},
            })
            # Check status
            result = server.handle_tools_call({
                "name": "bootstrap_status",
                "arguments": {},
            })
            data = self._check_result(result)
            assert data["data"]["profile"] == "minimal"

    def test_bootstrap_tools_in_list(self, server):
        """bootstrap tools are listed in tools/list."""
        result = server.handle_tools_list({})
        names = [t["name"] for t in result["tools"]]
        assert "bootstrap_check" in names
        assert "bootstrap_run" in names
        assert "bootstrap_status" in names

    def test_bootstrap_tools_have_schemas(self, server):
        """bootstrap tools have proper input schemas."""
        result = server.handle_tools_list({})
        tools = {t["name"]: t for t in result["tools"]}

        check = tools["bootstrap_check"]
        assert "quick" in check["inputSchema"]["properties"]

        run = tools["bootstrap_run"]
        assert "profile" in run["inputSchema"]["properties"]

        status = tools["bootstrap_status"]
        assert status["inputSchema"]["properties"] == {}

    def test_dispatch_bootstrap_check_via_rpc(self, server):
        """bootstrap_check works via JSON-RPC dispatch."""
        with self._mock_subprocess():
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "bootstrap_check", "arguments": {}},
            }
            resp = json.loads(server.dispatch(msg))
            assert resp["id"] == 1
            assert "content" in resp["result"]
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["success"] is True


class TestRuntimeTools:
    """Test runtime_list, runtime_connect, runtime_disconnect, runtime_select, runtime_generate MCP tools."""

    def _mock_registry(self, server):
        """Install mock runtime registry and capability registry on server."""
        mock_reg = MagicMock()
        mock_cap = MagicMock()
        server._runtime_registry = mock_reg
        server._runtime_capability_registry = mock_cap
        return mock_reg, mock_cap

    def test_runtime_list(self, server):
        """runtime_list returns registry status."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.get_status.return_value = {
            "active": "freebuff",
            "total": 1,
            "connected": 0,
            "runtimes": [],
            "known": [],
        }
        result = server.handle_tools_call({"name": "runtime_list", "arguments": {}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert "active" in data["data"]
        assert data["data"]["total"] == 1

    def test_runtime_connect(self, server):
        """runtime_connect delegates to registry.connect."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.connect.return_value = (True, "connected")
        result = server.handle_tools_call({"name": "runtime_connect", "arguments": {"name": "freebuff"}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["connected"] is True
        mock_reg.connect.assert_called_once_with("freebuff")

    def test_runtime_disconnect(self, server):
        """runtime_disconnect delegates to registry.disconnect."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.disconnect.return_value = True
        result = server.handle_tools_call({"name": "runtime_disconnect", "arguments": {"name": "freebuff"}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["disconnected"] is True
        mock_reg.disconnect.assert_called_once_with("freebuff")

    def test_runtime_select(self, server):
        """runtime_select sets active runtime."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.set_active.return_value = True
        result = server.handle_tools_call({"name": "runtime_select", "arguments": {"name": "freebuff"}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["active"] is True
        mock_reg.set_active.assert_called_once_with("freebuff")

    def test_runtime_select_unknown_runtime(self, server):
        """runtime_select returns error when runtime is not registered."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.set_active.return_value = False
        result = server.handle_tools_call({"name": "runtime_select", "arguments": {"name": "unknown"}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "not registered" in data["error"]

    def test_runtime_generate_by_name(self, server):
        """runtime_generate with explicit name."""
        mock_reg, _ = self._mock_registry(server)
        adapter = MagicMock()
        adapter.is_connected.return_value = True
        adapter.generate.return_value = RuntimeResult(
            content="generated text",
            runtime="freebuff",
            model_used="deepseek-v4",
            latency_ms=42,
        )
        mock_reg.get_adapter.return_value = adapter
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "prompt": "hello"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["content"] == "generated text"
        assert data["data"]["runtime"] == "freebuff"

    def test_runtime_generate_by_capability(self, server):
        """runtime_generate with capability selects runtime via capability registry."""
        mock_reg, mock_cap = self._mock_registry(server)
        mock_cap.get_runtime_for_capability.return_value = {"runtime": "claude-code", "confidence": 0.95}
        adapter = MagicMock()
        adapter.is_connected.return_value = True
        adapter.generate.return_value = RuntimeResult(
            content="code review result",
            runtime="claude-code",
        )
        mock_reg.get_adapter.return_value = adapter
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"capability": "review", "prompt": "review this"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["runtime"] == "claude-code"
        mock_cap.get_runtime_for_capability.assert_called_once_with("review")

    def test_runtime_generate_by_active_runtime(self, server):
        """runtime_generate falls back to active runtime."""
        mock_reg, _ = self._mock_registry(server)
        active_runtime = MagicMock()
        active_runtime.name = "freebuff"
        mock_reg.get_active.return_value = active_runtime
        adapter = MagicMock()
        adapter.is_connected.return_value = True
        adapter.generate.return_value = RuntimeResult(
            content="active runtime response",
            runtime="freebuff",
        )
        mock_reg.get_adapter.return_value = adapter
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"prompt": "hello"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["content"] == "active runtime response"

    def test_runtime_generate_requires_prompt_or_messages(self, server):
        """runtime_generate returns error when neither prompt nor messages provided."""
        mock_reg, _ = self._mock_registry(server)
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "prompt or messages is required" in data["error"]

    def test_runtime_generate_connects_if_not_connected(self, server):
        """runtime_generate auto-connects if adapter not connected."""
        mock_reg, _ = self._mock_registry(server)
        adapter = MagicMock()
        adapter.is_connected.return_value = False
        adapter.generate.return_value = RuntimeResult(
            content="after connect",
            runtime="freebuff",
        )
        mock_reg.get_adapter.return_value = adapter
        mock_reg.connect.return_value = (True, "connected")
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "prompt": "hello"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        mock_reg.connect.assert_called_once_with("freebuff")

    def test_runtime_tools_in_list(self, server):
        """runtime tools are listed in tools/list."""
        result = server.handle_tools_list({})
        names = [t["name"] for t in result["tools"]]
        assert "runtime_list" in names
        assert "runtime_connect" in names
        assert "runtime_disconnect" in names
        assert "runtime_select" in names
        assert "runtime_generate" in names

    def test_runtime_tools_have_schemas(self, server):
        """runtime tools have proper input schemas."""
        result = server.handle_tools_list({})
        tools = {t["name"]: t for t in result["tools"]}
        assert "name" in tools["runtime_connect"]["inputSchema"]["properties"]
        assert "name" in tools["runtime_select"]["inputSchema"]["properties"]
        assert "prompt" in tools["runtime_generate"]["inputSchema"]["properties"]

    def test_runtime_list_registry_unavailable(self, server):
        """runtime_list returns error when registry is unavailable."""
        server._runtime_registry = None
        with patch.object(server, "_get_runtime_registry", return_value=None):
            result = server.handle_tools_call({"name": "runtime_list", "arguments": {}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "not available" in data["error"]

    def test_runtime_generate_invalid_temperature(self, server):
        """runtime_generate rejects non-numeric temperature."""
        mock_reg, _ = self._mock_registry(server)
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "prompt": "hi", "temperature": "hot"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "temperature" in data["error"]

    def test_runtime_generate_invalid_max_tokens(self, server):
        """runtime_generate rejects non-positive max_tokens."""
        mock_reg, _ = self._mock_registry(server)
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "prompt": "hi", "max_tokens": -10},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "max_tokens" in data["error"]

    def test_runtime_generate_capability_unregistered(self, server):
        """runtime_generate returns error when capability selects an unregistered runtime."""
        mock_reg, mock_cap = self._mock_registry(server)
        mock_cap.get_runtime_for_capability.return_value = {"runtime": "openclaw", "confidence": 0.95}
        mock_reg.get.return_value = None
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"capability": "research", "prompt": "hello"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "not registered" in data["error"]

    def test_runtime_registry_lazy_accessor_does_not_auto_discover(self, server):
        """_get_runtime_registry should not auto-discover runtimes on access."""
        with patch("freebuff_plugin_03.runtime.registry.RuntimeRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.load.return_value = None
            registry = server._get_runtime_registry()
            assert registry is instance
            instance.discover.assert_not_called()

    def test_runtime_generate_connect_fails(self, server):
        """runtime_generate surfaces error when runtime cannot connect."""
        mock_reg, _ = self._mock_registry(server)
        mock_reg.get_adapter.return_value = None
        mock_reg.connect.return_value = (False, "binary not found")
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "prompt": "hello"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "binary not found" in data["error"]

    def test_runtime_generate_invalid_messages_shape(self, server):
        """runtime_generate rejects malformed messages."""
        mock_reg, _ = self._mock_registry(server)
        result = server.handle_tools_call({
            "name": "runtime_generate",
            "arguments": {"name": "freebuff", "messages": "not a list"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "messages must be a list" in data["error"]


class TestToolRegistryIntegration:
    """Test that ToolRegistry tools are auto-discovered as MCP tools."""

    def test_git_tool_registered(self, server):
        names = [t["name"] for t in server.handle_tools_list({})["tools"]]
        assert "git" in names

    def test_file_tool_registered(self, server):
        names = [t["name"] for t in server.handle_tools_list({})["tools"]]
        assert "file" in names

    def test_shell_tool_registered(self, server):
        names = [t["name"] for t in server.handle_tools_list({})["tools"]]
        assert "shell" in names

    def test_git_tool_has_input_schema(self, server):
        tools = server.handle_tools_list({})["tools"]
        git_tool = next(t for t in tools if t["name"] == "git")
        props = git_tool["inputSchema"]["properties"]
        assert "command" in props
        assert props["command"]["type"] == "string"
        assert "command" in git_tool["inputSchema"].get("required", [])

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="git not available")
    @pytest.mark.slow  # v5.189.10: реальный git subprocess (~5.6s)
    def test_call_git_status(self, server):
        # Initialize a git repo in temp workspace
        import subprocess
        subprocess.run(["git", "init"], cwd=server.workspace, capture_output=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=server.workspace, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=server.workspace, capture_output=True)

        result = server.handle_tools_call({
            "name": "git",
            "arguments": {"command": "status"},
        })
        assert "content" in result
        # git status should work
        text = result["content"][0]["text"]
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
        assert sm.push_notification(sid, 'data: {"test": true)') is True
        session = sm.get_session(sid)
        msg = session.notification_queue.get_nowait()
        assert '{"test": true]' in msg

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
        ids = {sm.create_session() for _ in range(100)}
        assert len(ids) == 100

    def test_session_manager_thread_safe(self):
        import threading
        sm = McpSessionManager()
        results = []

        def create_sessions():
            for _ in range(50):
                results.append(sm.create_session())

        threads = [threading.Thread(target=create_sessions) for _ in range(4)]
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
    from scripts_01.mcp_server import McpHttpServer, McpHTTPRequestHandler, McpSessionManager

    session_mgr = McpSessionManager()
    # Find an available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

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
                   body: Optional[str] = None,
                   headers: Optional[dict] = None) -> Tuple[int, dict, str]:
    """Make an HTTP request and return (status, headers, body)."""
    conn = http.client.HTTPConnection(host, port, timeout=5)
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


class TestHttpTransport:
    """Test Streamable HTTP transport (POST/GET/DELETE at /mcp)."""

    def test_post_initialize_creates_session(self, server):
        """POST initialize should return 200 with Mcp-Session-Id header."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            assert "mcp-session-id" in headers
            assert "mcp-protocol-version" in headers
            data = json.loads(resp_body)
            assert data["result"]["protocolVersion"] == PROTOCOL_VERSION
            # Session was created
            session_id = headers["mcp-session-id"]
            assert sm.get_session(session_id) is not None

    def test_post_ping(self, server):
        """POST ping should return 200 with JSON-RPC response."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["id"] == 1
            assert data["result"] == {}

    def test_post_notification_returns_202(self, server):
        """POST notification (no id) should return 202 Accepted."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 202
            assert resp_body == ""

    def test_post_tools_list(self, server):
        """POST tools/list should return 200 with tool list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "tools" in data["result"]
            assert len(data["result"]["tools"]) > 0

    def test_post_resources_list(self, server):
        """POST resources/list should return 200 with resource list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "resources" in data["result"]

    def test_post_prompts_list(self, server):
        """POST prompts/list should return 200 with prompt list."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "prompts" in data["result"]

    def test_post_batch_request(self, server):
        """POST batch request should return 200 with array of responses."""
        with _start_http_server(server) as (host, port, sm):
            batch = [
                {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            ]
            body = json.dumps(batch)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["id"] == 1
            assert data[1]["id"] == 2

    def test_post_batch_all_notifications(self, server):
        """POST batch with only notifications should return 202."""
        with _start_http_server(server) as (host, port, sm):
            batch = [
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
            ]
            body = json.dumps(batch)
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 202

    def test_post_unknown_method(self, server):
        """POST unknown method should return 200 with JSON-RPC error."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["error"]["code"] == METHOD_NOT_FOUND

    def test_post_invalid_json(self, server):
        """POST invalid JSON should return 400 with parse error."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(host, port, "POST", body="{invalid")
            assert status == 400
            data = json.loads(resp_body)
            assert data["error"]["code"] == PARSE_ERROR

    def test_post_wrong_path(self, server):
        """POST to wrong path should return 404."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(host, port, "POST", path="/wrong", body=body)
            assert status == 404

    def test_delete_terminates_session(self, server):
        """DELETE with Mcp-Session-Id should terminate session (204)."""
        with _start_http_server(server) as (host, port, sm):
            # Create session via initialize
            init_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            _, init_headers, _ = _http_request(host, port, "POST", body=init_body)
            session_id = init_headers["mcp-session-id"]

            # Delete it
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": session_id}
            )
            assert status == 204
            assert sm.get_session(session_id) is None

    def test_delete_unknown_session(self, server):
        """DELETE with unknown session should return 404."""
        with _start_http_server(server) as (host, port, sm):
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": "nonexistent"}
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
                host, port, "GET", headers={"Mcp-Session-Id": "nonexistent"}
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
                "params": {"name": "session_status", "arguments": {}},
            })
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert "content" in data["result"]

    def test_protocol_version_header(self, server):
        """All responses should include Mcp-Protocol-Version header."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert headers.get("mcp-protocol-version") == PROTOCOL_VERSION

    def test_post_shutdown(self, server):
        """POST shutdown should return 200 with empty result."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "shutdown"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200
            data = json.loads(resp_body)
            assert data["result"] == {}

    def test_post_invalid_origin_rejected(self, server):
        """POST with invalid Origin header should return 403."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Origin": "http://evil.com"},
            )
            assert status == 403

    def test_post_localhost_origin_allowed(self, server):
        """POST with localhost Origin should be allowed."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Origin": "http://localhost:3000"},
            )
            assert status == 200

    def test_post_no_origin_allowed(self, server):
        """POST without Origin (CLI client) should be allowed."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(host, port, "POST", body=body)
            assert status == 200

    def test_post_with_invalid_session_id_rejected(self, server):
        """POST with invalid Mcp-Session-Id should return 404."""
        with _start_http_server(server) as (host, port, sm):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            status, headers, resp_body = _http_request(
                host, port, "POST", body=body,
                headers={"Mcp-Session-Id": "nonexistent-session"},
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
                f"Host: {host}:{port}\r\n"
                f"Mcp-Session-Id: {sid}\r\n"
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
            assert "200" in header_str.split("\r\n")[0], f"Expected 200, got: {header_str.split(chr(13)+chr(10))[0]}"
            assert "text/event-stream" in header_str

            # Push a notification
            notification = json.dumps({"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 50}})
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
            assert "data:" in sse_text, f"No 'data:' in SSE response: {sse_text!r}"
            assert "notifications/progress" in sse_text

    def test_delete_no_content_length_header(self, server):
        """204 response must NOT have Content-Length header (RFC 7230)."""
        with _start_http_server(server) as (host, port, sm):
            sid = sm.create_session()
            status, headers, resp_body = _http_request(
                host, port, "DELETE", headers={"Mcp-Session-Id": sid}
            )
            assert status == 204
            assert "content-length" not in headers


class TestPolicyOverrideTool:
    """Test policy_override MCP tool (правило 11 User-Choice Override в диалоге)."""

    def _install_fake_engine(self, server):
        """Подменяет PolicyEngine на фейк с get_policy/set_preference."""
        engine = MagicMock()
        policy = MagicMock()
        policy.preferred_runtime = None
        engine.get_policy.return_value = policy
        engine.set_preference = MagicMock()
        server._policy_engine = engine
        return engine

    def test_policy_override_registered(self, server):
        """policy_override присутствует в tools/list."""
        result = server.handle_tools_list({})
        names = [t["name"] for t in result["tools"]]
        assert "policy_override" in names

    def test_policy_override_schema(self, server):
        """policy_override имеет schema с required message."""
        result = server.handle_tools_list({})
        tools = {t["name"]: t for t in result["tools"]}
        schema = tools["policy_override"]["inputSchema"]
        assert "message" in schema["properties"]
        assert "message" in schema["required"]

    def test_policy_override_applies(self, server):
        """policy_override применяет override и возвращает результат."""
        engine = self._install_fake_engine(server)
        result = server.handle_tools_call({
            "name": "policy_override",
            "arguments": {"message": "use deepseek instead of claude for coding"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["capability"] == "coding"
        assert data["data"]["runtime"] == "deepseek"
        engine.set_preference.assert_called_once_with("coding", "deepseek")

    def test_policy_override_ru(self, server):
        """policy_override распознаёт русскую фразу."""
        engine = self._install_fake_engine(server)
        result = server.handle_tools_call({
            "name": "policy_override",
            "arguments": {"message": "используй freebuff для research"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        assert data["data"]["capability"] == "research"
        assert data["data"]["runtime"] == "freebuff"
        engine.set_preference.assert_called_once_with("research", "freebuff")

    def test_policy_override_unrecognized(self, server):
        """Нераспознанная фраза → ошибка, set_preference не вызывается."""
        engine = self._install_fake_engine(server)
        result = server.handle_tools_call({
            "name": "policy_override",
            "arguments": {"message": "непонятная фраза без интента"},
        })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "Could not parse" in data["error"]
        engine.set_preference.assert_not_called()

    def test_policy_override_missing_message(self, server):
        """Без message → ошибка."""
        result = server.handle_tools_call({"name": "policy_override", "arguments": {}})
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "message is required" in data["error"]

    def test_policy_override_engine_unavailable(self, server):
        """PolicyEngine недоступен → graceful error, не exception."""
        with patch.object(server, "_get_policy_engine", return_value=None):
            result = server.handle_tools_call({
                "name": "policy_override",
                "arguments": {"message": "use deepseek instead of claude for coding"},
            })
        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "PolicyEngine not available" in data["error"]
