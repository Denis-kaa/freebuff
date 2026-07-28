"""
Tests for Tool Runtime (scripts/tool_runtime.py).

Coverage:
  - Tool registration & listing
  - FileTool: read, write, list, delete, copy, move
  - ShellTool: command execution, timeout
  - GitTool: status, log
  - SQLiteTool: query, execute
  - HTTPTool: GET request
  - Validation: missing params, type checks
  - EventBus integration
  - Error handling
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
***REMOVED***
from unittest.mock import MagicMock, patch

import pytest

from scripts.tool_runtime import (
    WORKSPACE,
    BaseTool,
    FileTool,
    GitTool,
    HTTPTool,
    ParamSchema,
    ShellTool,
    SQLiteTool,
    ToolMeta,
    ToolRegistry,
    ToolResult,
    create_default_registry,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    path = tmp_path / "test.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello'), (2, 'world')")
    conn.commit()
    conn.close()
    return str(path)


# ═══════════════════════════════════════════════════════════════
# Registration & Listing
# ═══════════════════════════════════════════════════════════════


class TestRegistration:
    def test_register_and_get(self, registry: ToolRegistry):
        tool = FileTool()
        name = registry.register(tool)
        assert name == "file"
        assert registry.get("file") is tool

    def test_register_duplicate(self, registry: ToolRegistry):
        registry.register(FileTool())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(FileTool())

    def test_get_nonexistent(self, registry: ToolRegistry):
        assert registry.get("nonexistent") is None

    def test_register_defaults(self, registry: ToolRegistry):
        names = registry.register_defaults()
        assert "file" in names
        assert "shell" in names
        assert "git" in names
        assert "sqlite" in names
        assert "http" in names

    def test_list_tools(self, registry: ToolRegistry):
        registry.register(FileTool())
        registry.register(ShellTool())
        tools = registry.list_tools()
        assert len(tools) == 2
        names = [t["name"***REMOVED*** for t in tools***REMOVED***
        assert "file" in names
        assert "shell" in names

    def test_list_by_category(self, registry: ToolRegistry):
        registry.register_defaults()
        tools = registry.list_tools(category="git")
        assert len(tools) == 1
        assert tools[0***REMOVED***["name"***REMOVED*** == "git"

    def test_list_parameters(self, registry: ToolRegistry):
        registry.register(FileTool())
        tools = registry.list_tools()
        file_tool = next(t for t in tools if t["name"***REMOVED*** == "file")
        params = {p["name"***REMOVED***: p for p in file_tool["parameters"***REMOVED******REMOVED***
        assert "action" in params
        assert params["action"***REMOVED***["required"***REMOVED*** is True
        assert "enum" in params["action"***REMOVED***
        assert "path" in params

    def test_create_default_registry(self):
        registry = create_default_registry()
        tools = registry.list_tools()
        assert len(tools) == 5


# ═══════════════════════════════════════════════════════════════
# FileTool
# ═══════════════════════════════════════════════════════════════


class TestFileTool:
    def _ctx(self, tmp_path: Path) -> dict:
        return {"workspace": str(tmp_path)***REMOVED***

    def test_read_file(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        tool = FileTool()
        result = tool.execute({"action": "read", "path": str(f)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert result.data == "hello world"

    def test_read_nonexistent(self, tmp_path: Path):
        tool = FileTool()
        result = tool.execute({"action": "read", "path": str(tmp_path / "nope.txt")***REMOVED***, self._ctx(tmp_path))
        assert not result.success
        assert "not found" in (result.error or "").lower()

    def test_write_file(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        tool = FileTool()
        result = tool.execute({"action": "write", "path": str(target), "content": "test content"***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert target.read_text(encoding="utf-8") == "test content"

    def test_list_directory(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        tool = FileTool()
        result = tool.execute({"action": "list", "path": str(tmp_path)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert len(result.data) == 2

    def test_list_recursive(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "root.txt").write_text("root")
        (sub / "nested.txt").write_text("nested")
        tool = FileTool()
        result = tool.execute({"action": "list", "path": str(tmp_path), "recursive": True***REMOVED***, self._ctx(tmp_path))
        assert result.success
        paths = [f["path"***REMOVED*** for f in result.data***REMOVED***
        assert any("nested.txt" in p for p in paths)

    def test_delete_file(self, tmp_path: Path):
        f = tmp_path / "to_delete.txt"
        f.write_text("delete me")
        tool = FileTool()
        result = tool.execute({"action": "delete", "path": str(f)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert not f.exists()

    def test_copy_file(self, tmp_path: Path):
        src = tmp_path / "src.txt"
        src.write_text("copy me")
        dst = tmp_path / "dst.txt"
        tool = FileTool()
        result = tool.execute({"action": "copy", "path": str(src), "destination": str(dst)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert dst.read_text(encoding="utf-8") == "copy me"

    def test_move_file(self, tmp_path: Path):
        src = tmp_path / "move_src.txt"
        src.write_text("move me")
        dst = tmp_path / "move_dst.txt"
        tool = FileTool()
        result = tool.execute({"action": "move", "path": str(src), "destination": str(dst)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert dst.read_text(encoding="utf-8") == "move me"
        assert not src.exists()

    def test_exists(self, tmp_path: Path):
        f = tmp_path / "exists.txt"
        f.write_text("x")
        tool = FileTool()
        ctx = self._ctx(tmp_path)
        assert tool.execute({"action": "exists", "path": str(f)***REMOVED***, ctx).data is True
        assert tool.execute({"action": "exists", "path": str(tmp_path / "nope")***REMOVED***, ctx).data is False

    def test_mkdir(self, tmp_path: Path):
        d = tmp_path / "new_dir"
        tool = FileTool()
        result = tool.execute({"action": "mkdir", "path": str(d)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert d.exists() and d.is_dir()

    def test_mkdir_recursive(self, tmp_path: Path):
        d = tmp_path / "a" / "b" / "c"
        tool = FileTool()
        result = tool.execute({"action": "mkdir", "path": str(d)***REMOVED***, self._ctx(tmp_path))
        assert result.success
        assert d.exists()

    def test_path_safety(self, tmp_path: Path):
        """FileTool не должен выходить за пределы workspace."""
        outside = Path("/etc/passwd")
        tool = FileTool()
        ctx = self._ctx(tmp_path)
        result = tool.execute({"action": "read", "path": str(outside)***REMOVED***, ctx)
        assert not result.success

    def test_unknown_action(self, tmp_path: Path):
        tool = FileTool()
        result = tool.execute({"action": "unknown", "path": str(tmp_path)***REMOVED***, self._ctx(tmp_path))
        assert not result.success


# ═══════════════════════════════════════════════════════════════
# ShellTool
# ═══════════════════════════════════════════════════════════════


class TestShellTool:
    def test_echo(self):
        tool = ShellTool()
        result = tool.execute({"command": "echo hello"***REMOVED***)
        assert result.success
        assert "hello" in result.data

    def test_failure(self):
        tool = ShellTool()
        result = tool.execute({"command": "exit 42"***REMOVED***)
        assert not result.success
        assert "42" in (result.error or "")

    def test_no_command(self):
        tool = ShellTool()
        result = tool.execute({"command": ""***REMOVED***)
        assert not result.success

    def test_cwd(self, tmp_path: Path):
        (tmp_path / "marker.txt").write_text("yes")
        tool = ShellTool()
        result = tool.execute({"command": "ls marker.txt", "cwd": str(tmp_path)***REMOVED***)
        assert result.success
        assert "marker.txt" in result.data

    def test_env(self):
        tool = ShellTool()
        result = tool.execute({"command": "echo $MY_VAR", "env": {"MY_VAR": "custom"***REMOVED******REMOVED***)
        assert result.success
        assert "custom" in result.data.strip()


# ═══════════════════════════════════════════════════════════════
# GitTool
# ═══════════════════════════════════════════════════════════════


class TestGitTool:
    def test_git_status(self, tmp_path: Path):
        # Init a temp git repo
        subprocess.run(["git", "init"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"***REMOVED***, cwd=str(tmp_path), capture_output=True)

        tool = GitTool()
        result = tool.execute({"command": "status", "cwd": str(tmp_path)***REMOVED***)
        assert result.success

    def test_git_log(self, tmp_path: Path):
        subprocess.run(["git", "init"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"***REMOVED***, cwd=str(tmp_path), capture_output=True)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."***REMOVED***, cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "first"***REMOVED***, cwd=str(tmp_path), capture_output=True)

        tool = GitTool()
        result = tool.execute({"command": "log", "args": "--oneline", "cwd": str(tmp_path)***REMOVED***)
        assert result.success
        assert "first" in result.data

    def test_no_command(self):
        tool = GitTool()
        result = tool.execute({"command": ""***REMOVED***)
        assert not result.success


# ═══════════════════════════════════════════════════════════════
# SQLiteTool
# ═══════════════════════════════════════════════════════════════


class TestSQLiteTool:
    def test_select(self, db_path: str):
        tool = SQLiteTool()
        result = tool.execute({"query": "SELECT * FROM test", "db_path": db_path***REMOVED***)
        assert result.success
        assert len(result.data) == 2
        assert result.data[0***REMOVED***["name"***REMOVED*** == "hello"

    def test_select_one(self, db_path: str):
        tool = SQLiteTool()
        result = tool.execute({"query": "SELECT * FROM test WHERE id = 1", "db_path": db_path, "fetch": "one"***REMOVED***)
        assert result.success
        assert result.data["name"***REMOVED*** == "hello"

    def test_insert(self, db_path: str):
        tool = SQLiteTool()
        result = tool.execute({
            "query": "INSERT INTO test (id, name) VALUES (?, ?)",
            "db_path": db_path,
            "params": [3, "test"***REMOVED***,
            "fetch": "none",
        ***REMOVED***)
        assert result.success

        # Verify
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT name FROM test WHERE id = 3").fetchone()
        assert row[0***REMOVED*** == "test"
        conn.close()

    def test_missing_db(self, tmp_path: Path):
        tool = SQLiteTool()
        result = tool.execute({"query": "SELECT 1", "db_path": str(tmp_path / "nope.db")***REMOVED***)
        assert not result.success

    def test_no_query(self, db_path: str):
        tool = SQLiteTool()
        result = tool.execute({"query": "", "db_path": db_path***REMOVED***)
        assert not result.success

    def test_invalid_sql(self, db_path: str):
        tool = SQLiteTool()
        result = tool.execute({"query": "SELECT INVALID", "db_path": db_path***REMOVED***)
        assert not result.success


# ═══════════════════════════════════════════════════════════════
# HTTPTool
# ═══════════════════════════════════════════════════════════════


class TestHTTPTool:
    def test_get_success(self):
        tool = HTTPTool()
        # Use httpbin or a reliable test endpoint
        result = tool.execute({"url": "https://httpbin.org/get", "timeout": 5***REMOVED***)
        if result.success:
            assert isinstance(result.data, dict)
            assert "url" in result.data
        else:
            # Skip if no internet
            pytest.skip(f"No network: {result.error***REMOVED***")

    def test_invalid_url(self):
        tool = HTTPTool()
        result = tool.execute({"url": "https://nonexistent.example.com/test", "timeout": 3***REMOVED***)
        assert not result.success

    def test_no_url(self):
        tool = HTTPTool()
        result = tool.execute({"url": ""***REMOVED***)
        assert not result.success


# ═══════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════


class TestValidation:
    def test_missing_required(self, registry: ToolRegistry):
        registry.register(FileTool())
        # Missing required 'path'
        result = registry.execute("file", {"action": "read"***REMOVED***)
        assert not result.success
        assert "required" in (result.error or "").lower()

    def test_wrong_type(self, registry: ToolRegistry):
        registry.register(ShellTool())
        # 'timeout' should be integer
        result = registry.execute("shell", {"command": "echo hi", "timeout": "not_a_number"***REMOVED***)
        assert not result.success

    def test_enum_validation(self):
        """Проверка enum-валидации через ParamSchema."""
        schema = ParamSchema(name="action", type="string", enum=["read", "write"***REMOVED***, required=True)

        # Valid
        schema.enum = ["read", "write"***REMOVED***
        errors = [***REMOVED***
        if schema.enum and "read" not in schema.enum:
            errors.append("invalid")
        assert len(errors) == 0

        # Built-in validation via FileTool
        tool = FileTool()
        result = tool.execute({"action": "INVALID", "path": "/tmp"***REMOVED***)
        assert not result.success

    def test_default_values(self):
        tool = ShellTool()
        params = tool.with_defaults({"command": "echo hi"***REMOVED***)
        assert params["cwd"***REMOVED*** == str(WORKSPACE)
        assert params["timeout"***REMOVED*** == 30


# ═══════════════════════════════════════════════════════════════
# ToolRegistry.execute
# ═══════════════════════════════════════════════════════════════


class TestToolRegistryExecute:
    def test_execute_success(self, tmp_path: Path):
        registry = ToolRegistry(default_context={"workspace": str(tmp_path)***REMOVED***)
        registry.register(FileTool())
        f = tmp_path / "test.txt"
        f.write_text("content")
        result = registry.execute("file", {"action": "read", "path": str(f)***REMOVED***)
        assert result.success
        assert result.data == "content"

    def test_execute_tool_not_found(self, registry: ToolRegistry):
        result = registry.execute("nonexistent", {***REMOVED***)
        assert not result.success
        assert "not found" in (result.error or "").lower()

    def test_execute_multi(self, tmp_path: Path):
        registry = ToolRegistry(default_context={"workspace": str(tmp_path)***REMOVED***)
        registry.register(FileTool())
        registry.register(ShellTool())

        f = tmp_path / "multi.txt"
        f.write_text("multi test")

        calls = [
            ("file", {"action": "read", "path": str(f)***REMOVED***),
            ("shell", {"command": "echo done"***REMOVED***),
        ***REMOVED***
        results = registry.execute_multi(calls)
        assert len(results) == 2
        assert results[0***REMOVED***.success
        assert results[1***REMOVED***.success

    def test_execute_multi_stop_on_error(self, registry: ToolRegistry):
        registry.register(FileTool())
        calls = [
            ("file", {"action": "read", "path": "/nonexistent/nope.txt"***REMOVED***),
            ("file", {"action": "read", "path": "/tmp"***REMOVED***),
        ***REMOVED***
        results = registry.execute_multi(calls, stop_on_error=True)
        assert len(results) == 1
        assert not results[0***REMOVED***.success


# ═══════════════════════════════════════════════════════════════
# EventBus Integration
# ═══════════════════════════════════════════════════════════════


class TestEventBusIntegration:
    def test_tool_executed_event(self, tmp_path: Path):
        events = [***REMOVED***
        mock_bus = MagicMock()
        mock_bus.publish = lambda e: events.append(e.type)

        registry = ToolRegistry(event_bus=mock_bus, default_context={"workspace": str(tmp_path)***REMOVED***)
        registry.register(FileTool())

        f = tmp_path / "eb_test.txt"
        f.write_text("event bus test")
        registry.execute("file", {"action": "read", "path": str(f)***REMOVED***)

        assert "tool.executed" in events

    def test_tool_failed_event(self, registry: ToolRegistry):
        events = [***REMOVED***
        mock_bus = MagicMock()
        mock_bus.publish = lambda e: events.append(e.type)

        registry = ToolRegistry(event_bus=mock_bus)
        registry.register(FileTool())
        registry.execute("file", {"action": "read", "path": "/nonexistent"***REMOVED***)

        assert "tool.failed" in events

    def test_event_does_not_block_execution(self, tmp_path: Path):
        """EventBus ошибка не должна ломать выполнение."""
        broken_bus = MagicMock()
        broken_bus.publish = MagicMock(side_effect=Exception("Bus down"))

        registry = ToolRegistry(event_bus=broken_bus)
        registry.register(ShellTool())
        result = registry.execute("shell", {"command": "echo hi"***REMOVED***)
        assert result.success

    def test_set_event_bus(self):
        registry = ToolRegistry()
        assert registry._event_bus is None

        bus = MagicMock()
        registry.set_event_bus(bus)
        assert registry._event_bus is bus


# ═══════════════════════════════════════════════════════════════
# BaseTool abstract class
# ═══════════════════════════════════════════════════════════════


class TestBaseTool:
    def test_custom_tool(self):
        """Можно создать свой инструмент через наследование BaseTool."""

        class UppercaseTool(BaseTool):
            @property
            def meta(self) -> ToolMeta:
                return ToolMeta(
                    name="uppercase",
                    description="Convert text to uppercase",
                    parameters=[
                        ParamSchema(name="text", type="string", description="Input text", required=True),
                    ***REMOVED***,
                )

            def execute(self, params, context=None):
                text = params.get("text", "")
                return ToolResult(success=True, data=text.upper(), tool_name="uppercase")

        tool = UppercaseTool()
        result = tool.execute({"text": "hello"***REMOVED***)
        assert result.success
        assert result.data == "HELLO"

    def test_custom_tool_in_registry(self):
        class ReverseTool(BaseTool):
            @property
            def meta(self) -> ToolMeta:
                return ToolMeta(name="reverse", description="Reverse text")

            def execute(self, params, context=None):
                text = params.get("text", "")
                return ToolResult(success=True, data=text[::-1***REMOVED***, tool_name="reverse")

        registry = ToolRegistry()
        registry.register(ReverseTool())
        registry.register(FileTool())
        tools = registry.list_tools()
        assert len(tools) == 2
        names = [t["name"***REMOVED*** for t in tools***REMOVED***
        assert "reverse" in names
        assert "file" in names


# ═══════════════════════════════════════════════════════════════
# Orchestrator integration
# ═══════════════════════════════════════════════════════════════


class TestOrchestratorIntegration:
    def test_tool_types_match_orchestrator(self):
        """Проверяет, что FileTool и ShellTool покрывают ToolType из Orchestrator."""
        from scripts.orchestrator import ToolType

        registry = ToolRegistry()
        registry.register_defaults()

        # Map of ToolType → expected tool name in runtime
        type_map = {
            ToolType.SHELL: "shell",
            ToolType.FILE: "file",
            ToolType.GIT: "git",
        ***REMOVED***

        for tool_type, expected_name in type_map.items():
            tool = registry.get(expected_name)
            assert tool is not None, f"Missing tool for {tool_type.value***REMOVED***"
            assert tool.meta.name == expected_name
