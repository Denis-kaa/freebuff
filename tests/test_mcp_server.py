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
