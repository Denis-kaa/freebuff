#!/usr/bin/env python3
"""
tool_runtime.py — Tool Runtime для Buffy Project.

Выделенная подсистема инструментов с единым интерфейсом, метаданными,
валидацией параметров и EventBus интеграцией.

Архитектура:
  ToolRegistry
  ├── register(tool)         — регистрация инструмента
  ├── execute(name, params)  — выполнение с валидацией + EventBus
  ├── get(name)              — получение инструмента
  └── list_tools()           — список всех инструментов с метаданными

Встроенные инструменты:
  - GitTool       — git status, diff, log, add, commit, branch, tag
  - SQLiteTool    — query, execute (generic SQLite)
  - HTTPTool      — GET, POST, PUT, DELETE, HEAD
  - FileTool      — read, write, list, delete, copy, move
  - ShellTool     — shell-команды с таймаутом

Использование:
    from scripts.tool_runtime import ToolRegistry, FileTool, ShellTool

    registry = ToolRegistry()
    registry.register(FileTool())
    registry.register(ShellTool())

    result = registry.execute("file.read", {"path": "README.md"***REMOVED***)
    print(result.data)
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

WORKSPACE = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class ToolResult:
    """Стандартный результат выполнения инструмента."""
    success: bool
    data: Any = None
    error: Optional[str***REMOVED*** = None
    duration_ms: float = 0.0
    tool_name: str = ""
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class ParamSchema:
    """Схема одного параметра инструмента."""
    name: str
    type: str  # "string" | "integer" | "boolean" | "array" | "object"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[str***REMOVED******REMOVED*** = None
    pattern: Optional[str***REMOVED*** = None  # regex
    min_length: Optional[int***REMOVED*** = None
    max_length: Optional[int***REMOVED*** = None


@dataclass
class ToolMeta:
    """Метаданные инструмента."""
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"  # "git", "database", "network", "filesystem", "shell"
    parameters: List[ParamSchema***REMOVED*** = field(default_factory=list)
    examples: List[Dict[str, Any***REMOVED******REMOVED*** = field(default_factory=list)
    timeout_default: int = 30


# ═══════════════════════════════════════════════════════════════
# BaseTool
# ═══════════════════════════════════════════════════════════════


class BaseTool(ABC):
    """Абстрактный базовый класс для всех инструментов."""

    @property
    @abstractmethod
    def meta(self) -> ToolMeta:
        """Метаданные инструмента."""
        ...

    @abstractmethod
    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        """Выполняет инструмент с переданными параметрами.

        Args:
            params: словарь параметров (ключи = имена из ParamSchema)
            context: опциональный контекст выполнения (workspace, env vars, etc.)

        Returns:
            ToolResult
        """
        ...

    def validate_params(self, params: Dict[str, Any***REMOVED***) -> List[str***REMOVED***:
        """Валидирует параметры по схеме.

        Returns:
            Список ошибок валидации (пустой = всё ок)
        """
        errors: List[str***REMOVED*** = [***REMOVED***
        for p in self.meta.parameters:
            value = params.get(p.name)
            if p.required and value is None:
                errors.append(f"Missing required parameter: {p.name***REMOVED***")
                continue
            if value is None:
                continue

            # Type check
            if p.type == "string" and not isinstance(value, str):
                errors.append(f"Parameter '{p.name***REMOVED***' must be string, got {type(value).__name__***REMOVED***")
            elif p.type == "integer" and not isinstance(value, int):
                errors.append(f"Parameter '{p.name***REMOVED***' must be integer, got {type(value).__name__***REMOVED***")
            elif p.type == "boolean" and not isinstance(value, bool):
                errors.append(f"Parameter '{p.name***REMOVED***' must be boolean, got {type(value).__name__***REMOVED***")

            # String validations
            if isinstance(value, str):
                if p.min_length is not None and len(value) < p.min_length:
                    errors.append(f"Parameter '{p.name***REMOVED***' too short: {len(value)***REMOVED*** < {p.min_length***REMOVED***")
                if p.max_length is not None and len(value) > p.max_length:
                    errors.append(f"Parameter '{p.name***REMOVED***' too long: {len(value)***REMOVED*** > {p.max_length***REMOVED***")

            # Enum
            if p.enum and value is not None and value not in p.enum:
                errors.append(f"Parameter '{p.name***REMOVED***' must be one of {p.enum***REMOVED***, got '{value***REMOVED***'")

        return errors

    def with_defaults(self, params: Dict[str, Any***REMOVED***) -> Dict[str, Any***REMOVED***:
        """Заполняет отсутствующие параметры значениями по умолчанию."""
        result = dict(params)
        for p in self.meta.parameters:
            if p.name not in result and p.default is not None:
                result[p.name***REMOVED*** = p.default
        return result


# ═══════════════════════════════════════════════════════════════
# GitTool
# ═══════════════════════════════════════════════════════════════


class GitTool(BaseTool):
    """Инструмент для Git операций."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="git",
            description="Execute git commands: status, diff, log, add, commit, branch, tag, checkout",
            version="1.0.0",
            category="git",
            parameters=[
                ParamSchema(name="command", type="string", description="Git command (status, diff, log, add, commit, branch, tag, checkout, pull, push)", required=True),
                ParamSchema(name="args", type="string", description="Additional arguments for the git command", default=""),
                ParamSchema(name="cwd", type="string", description="Working directory", default=str(WORKSPACE)),
                ParamSchema(name="timeout", type="integer", description="Timeout in seconds", default=60),
            ***REMOVED***,
            examples=[
                {"command": "status", "description": "Show working tree status"***REMOVED***,
                {"command": "diff", "args": "--cached", "description": "Show staged changes"***REMOVED***,
                {"command": "log", "args": "--oneline -5", "description": "Last 5 commits"***REMOVED***,
                {"command": "branch", "description": "List branches"***REMOVED***,
            ***REMOVED***,
        )

    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        params = self.with_defaults(params)
        command = params.get("command", "")
        args = params.get("args", "")
        cwd = params.get("cwd", str(WORKSPACE))
        timeout = params.get("timeout", 60)

        if not command:
            return ToolResult(success=False, error="No git command specified", tool_name="git")

        full_cmd = f"git {command***REMOVED*** {args***REMOVED***".strip()
        try:
            start = time.time()
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            duration_ms = (time.time() - start) * 1000
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return ToolResult(
                success=success,
                data=output,
                error=None if success else f"Exit code: {result.returncode***REMOVED***\n{result.stderr[:200***REMOVED******REMOVED***",
                duration_ms=duration_ms,
                tool_name="git",
                metadata={"returncode": result.returncode, "command": full_cmd***REMOVED***,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Git timeout ({timeout***REMOVED***s)", tool_name="git")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="git")


# ═══════════════════════════════════════════════════════════════
# SQLiteTool
# ═══════════════════════════════════════════════════════════════


class SQLiteTool(BaseTool):
    """Инструмент для SQLite запросов."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="sqlite",
            description="Execute SQLite queries: SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER",
            version="1.0.0",
            category="database",
            parameters=[
                ParamSchema(name="query", type="string", description="SQL query to execute", required=True),
                ParamSchema(name="db_path", type="string", description="Path to SQLite database file", required=True),
                ParamSchema(name="params", type="array", description="Query parameters (for prepared statements)", default=[***REMOVED***),
                ParamSchema(name="fetch", type="string", description="Fetch mode: 'all', 'one', 'none'", default="all", enum=["all", "one", "none"***REMOVED***),
            ***REMOVED***,
            examples=[
                {"query": "SELECT * FROM sessions LIMIT 5", "db_path": "data/context.db", "description": "Read sessions"***REMOVED***,
                {"query": "INSERT INTO sessions (id, project) VALUES (?, ?)", "db_path": "data/context.db", "params": ["s1", "test"***REMOVED***, "fetch": "none", "description": "Insert session"***REMOVED***,
            ***REMOVED***,
        )

    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        params = self.with_defaults(params)
        query = params.get("query", "")
        db_path = params.get("db_path", "")
        bind_params = params.get("params", [***REMOVED***)
        fetch = params.get("fetch", "all")

        if not query:
            return ToolResult(success=False, error="No SQL query specified", tool_name="sqlite")
        if not db_path:
            return ToolResult(success=False, error="No db_path specified", tool_name="sqlite")

        full_path = Path(db_path)
        if not full_path.is_absolute():
            full_path = WORKSPACE / full_path

        if not full_path.exists():
            return ToolResult(success=False, error=f"Database not found: {full_path***REMOVED***", tool_name="sqlite")

        try:
            start = time.time()
            conn = sqlite3.connect(str(full_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, bind_params)

            affected = cursor.rowcount

            if fetch == "all":
                rows = cursor.fetchall()
                data = [dict(row) for row in rows***REMOVED***
            elif fetch == "one":
                row = cursor.fetchone()
                data = dict(row) if row else None
            else:
                data = None

            conn.commit()
            conn.close()
            duration_ms = (time.time() - start) * 1000

            return ToolResult(
                success=True,
                data=data,
                duration_ms=duration_ms,
                tool_name="sqlite",
                metadata={"affected_rows": affected, "fetch_mode": fetch***REMOVED***,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="sqlite")


# ═══════════════════════════════════════════════════════════════
# HTTPTool
# ═══════════════════════════════════════════════════════════════


class HTTPTool(BaseTool):
    """Инструмент для HTTP запросов."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="http",
            description="Execute HTTP requests: GET, POST, PUT, DELETE, HEAD, PATCH",
            version="1.0.0",
            category="network",
            parameters=[
                ParamSchema(name="url", type="string", description="Request URL", required=True),
                ParamSchema(name="method", type="string", description="HTTP method", default="GET", enum=["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH"***REMOVED***),
                ParamSchema(name="headers", type="object", description="HTTP headers as dict", default={***REMOVED***),
                ParamSchema(name="body", type="object", description="Request body (JSON-serializable)", default=None),
                ParamSchema(name="timeout", type="integer", description="Timeout in seconds", default=10),
                ParamSchema(name="follow_redirects", type="boolean", description="Follow redirects", default=True),
            ***REMOVED***,
            examples=[
                {"url": "https://api.github.com/repos/user/repo", "description": "GET repo info"***REMOVED***,
                {"url": "https://httpbin.org/post", "method": "POST", "body": {"key": "value"***REMOVED***, "description": "POST JSON"***REMOVED***,
            ***REMOVED***,
        )

    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        params = self.with_defaults(params)
        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", {***REMOVED***)
        body = params.get("body")
        timeout = params.get("timeout", 10)
        follow_redirects = params.get("follow_redirects", True)

        if not url:
            return ToolResult(success=False, error="No URL specified", tool_name="http")

        try:
            start = time.time()
            with httpx.Client(follow_redirects=follow_redirects, timeout=timeout) as client:
                json_body = body if isinstance(body, dict) else None
                response = client.request(method=method, url=url, headers=headers, json=json_body)
                duration_ms = (time.time() - start) * 1000

                # Try to parse response as JSON
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text[:10000***REMOVED***

                success = 200 <= response.status_code < 300
                return ToolResult(
                    success=success,
                    data=response_data,
                    error=None if success else f"HTTP {response.status_code***REMOVED***: {response.reason_phrase***REMOVED***",
                    duration_ms=duration_ms,
                    tool_name="http",
                    metadata={
                        "status_code": response.status_code,
                        "method": method,
                        "url": url,
                    ***REMOVED***,
                )
        except httpx.TimeoutException:
            return ToolResult(success=False, error=f"HTTP timeout ({timeout***REMOVED***s)", tool_name="http")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="http")


# ═══════════════════════════════════════════════════════════════
# FileTool
# ═══════════════════════════════════════════════════════════════


class FileTool(BaseTool):
    """Инструмент для файловых операций."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="file",
            description="File system operations: read, write, list, delete, copy, move, exists, mkdir",
            version="1.0.0",
            category="filesystem",
            parameters=[
                ParamSchema(name="action", type="string", description="File operation", required=True,
                            enum=["read", "write", "list", "delete", "copy", "move", "exists", "mkdir"***REMOVED***),
                ParamSchema(name="path", type="string", description="File or directory path", required=True),
                ParamSchema(name="content", type="string", description="Content to write (for write action)", default=""),
                ParamSchema(name="destination", type="string", description="Destination path (for copy/move)", default=""),
                ParamSchema(name="recursive", type="boolean", description="Recursive (for delete/list)", default=False),
            ***REMOVED***,
            examples=[
                {"action": "read", "path": "README.md", "description": "Read a file"***REMOVED***,
                {"action": "write", "path": "test.txt", "content": "hello", "description": "Write a file"***REMOVED***,
                {"action": "list", "path": "src", "description": "List directory"***REMOVED***,
            ***REMOVED***,
        )

    def _resolve_path(self, path: str, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> Path:
        workspace = WORKSPACE
        if context and context.get("workspace"):
            workspace = Path(context["workspace"***REMOVED***)
        p = Path(path)
        if not p.is_absolute():
            p = workspace / p
        return p.resolve()

    def _validate_safe_path(self, path: Path, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> None:
        """Проверяет, что путь не выходит за пределы workspace."""
        workspace = WORKSPACE
        if context and context.get("workspace"):
            workspace = Path(context["workspace"***REMOVED***)
        resolved = path.resolve()
        workspace_resolved = workspace.resolve()
        if not str(resolved).startswith(str(workspace_resolved)):
            raise PermissionError(f"Path outside workspace: {path***REMOVED*** (workspace: {workspace_resolved***REMOVED***)")

    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        params = self.with_defaults(params)
        action = params.get("action", "")
        path = params.get("path", "")
        content = params.get("content", "")
        destination = params.get("destination", "")
        recursive = params.get("recursive", False)

        if not action:
            return ToolResult(success=False, error="No action specified", tool_name="file")
        if not path:
            return ToolResult(success=False, error="No path specified", tool_name="file")

        try:
            full_path = self._resolve_path(path, context)
            self._validate_safe_path(full_path, context)

            workspace = WORKSPACE
            if context and context.get("workspace"):
                workspace = Path(context["workspace"***REMOVED***)

            start = time.time()

            if action == "read":
                if not full_path.exists():
                    return ToolResult(success=False, error=f"File not found: {path***REMOVED***", tool_name="file")
                if not full_path.is_file():
                    return ToolResult(success=False, error=f"Not a file: {path***REMOVED***", tool_name="file")
                data = full_path.read_text(encoding="utf-8")
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=data, duration_ms=duration_ms, tool_name="file",
                                  metadata={"size": len(data), "path": str(full_path)***REMOVED***)

            elif action == "write":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=f"Written {len(content)***REMOVED*** chars", duration_ms=duration_ms,
                                  tool_name="file", metadata={"size": len(content), "path": str(full_path)***REMOVED***)

            elif action == "list":
                if not full_path.exists():
                    return ToolResult(success=False, error=f"Directory not found: {path***REMOVED***", tool_name="file")
                if not full_path.is_dir():
                    return ToolResult(success=False, error=f"Not a directory: {path***REMOVED***", tool_name="file")
                pattern = "**/*" if recursive else "*"
                files = [***REMOVED***
                for f in sorted(full_path.glob(pattern)):
                    rel = str(f.relative_to(workspace)) if str(f).startswith(str(workspace)) else str(f)
                    ftype = "dir" if f.is_dir() else "file"
                    files.append({"path": str(rel), "type": ftype, "size": f.stat().st_size if f.is_file() else 0***REMOVED***)
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=files, duration_ms=duration_ms, tool_name="file")

            elif action == "delete":
                if not full_path.exists():
                    return ToolResult(success=False, error=f"Not found: {path***REMOVED***", tool_name="file")
                if full_path.is_file():
                    full_path.unlink()
                elif full_path.is_dir():
                    import shutil
                    shutil.rmtree(full_path)
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=f"Deleted: {path***REMOVED***", duration_ms=duration_ms, tool_name="file")

            elif action == "copy":
                if not destination:
                    return ToolResult(success=False, error="No destination specified", tool_name="file")
                dest_path = self._resolve_path(destination, context)
                self._validate_safe_path(dest_path, context)
                import shutil
                if full_path.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(full_path), str(dest_path))
                elif full_path.is_dir():
                    shutil.copytree(str(full_path), str(dest_path))
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=f"Copied {path***REMOVED*** → {destination***REMOVED***", duration_ms=duration_ms, tool_name="file")

            elif action == "move":
                if not destination:
                    return ToolResult(success=False, error="No destination specified", tool_name="file")
                dest_path = self._resolve_path(destination, context)
                self._validate_safe_path(dest_path, context)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.rename(dest_path)
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=f"Moved {path***REMOVED*** → {destination***REMOVED***", duration_ms=duration_ms, tool_name="file")

            elif action == "exists":
                data = full_path.exists()
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=data, duration_ms=duration_ms, tool_name="file")

            elif action == "mkdir":
                full_path.mkdir(parents=True, exist_ok=True)
                duration_ms = (time.time() - start) * 1000
                return ToolResult(success=True, data=f"Created directory: {path***REMOVED***", duration_ms=duration_ms, tool_name="file")

            else:
                return ToolResult(success=False, error=f"Unknown action: {action***REMOVED***", tool_name="file")

        except PermissionError as e:
            return ToolResult(success=False, error=str(e), tool_name="file")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="file")


# ═══════════════════════════════════════════════════════════════
# ShellTool
# ═══════════════════════════════════════════════════════════════


class ShellTool(BaseTool):
    """Инструмент для выполнения shell-команд."""

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="shell",
            description="Execute shell commands with timeout and working directory control",
            version="1.0.0",
            category="shell",
            parameters=[
                ParamSchema(name="command", type="string", description="Shell command to execute", required=True,
                            min_length=1),
                ParamSchema(name="cwd", type="string", description="Working directory", default=str(WORKSPACE)),
                ParamSchema(name="timeout", type="integer", description="Timeout in seconds", default=30),
                ParamSchema(name="env", type="object", description="Additional environment variables", default={***REMOVED***),
            ***REMOVED***,
            examples=[
                {"command": "ls -la", "description": "List files"***REMOVED***,
                {"command": "python -c 'print(\"hello\")'", "description": "Run Python inline"***REMOVED***,
                {"command": "find . -name '*.py' | head -10", "description": "Find Python files"***REMOVED***,
            ***REMOVED***,
        )

    def execute(self, params: Dict[str, Any***REMOVED***, context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> ToolResult:
        params = self.with_defaults(params)
        command = params.get("command", "")
        cwd = params.get("cwd", str(WORKSPACE))
        timeout = params.get("timeout", 30)
        extra_env = params.get("env", {***REMOVED***)

        if not command:
            return ToolResult(success=False, error="No command specified", tool_name="shell")

        try:
            env = os.environ.copy()
            env.update(extra_env)

            start = time.time()
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd, env=env,
            )
            duration_ms = (time.time() - start) * 1000
            output = result.stdout + result.stderr
            success = result.returncode == 0

            return ToolResult(
                success=success,
                data=output,
                error=None if success else f"Exit code: {result.returncode***REMOVED***\n{result.stderr[:500***REMOVED******REMOVED***",
                duration_ms=duration_ms,
                tool_name="shell",
                metadata={"returncode": result.returncode, "command": command[:100***REMOVED******REMOVED***,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Shell timeout ({timeout***REMOVED***s)", tool_name="shell")
        except Exception as e:
            return ToolResult(success=False, error=str(e), tool_name="shell")


# ═══════════════════════════════════════════════════════════════
# ToolRegistry
# ═══════════════════════════════════════════════════════════════


class ToolRegistry:
    """Центральный реестр инструментов.

    Особенности:
      - Регистрация/получение/список инструментов
      - Валидация параметров перед выполнением
      - EventBus интеграция (tool.executed / tool.failed)
      - Контекст выполнения (workspace, env vars, etc.)
    """

    def __init__(
        self,
        event_bus: Optional[Any***REMOVED*** = None,
        default_context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ):
        self._tools: Dict[str, BaseTool***REMOVED*** = {***REMOVED***
        self._event_bus = event_bus
        self._default_context = default_context or {"workspace": str(WORKSPACE)***REMOVED***

    def register(self, tool: BaseTool) -> str:
        """Регистрирует инструмент в реестре.

        Args:
            tool: экземпляр BaseTool

        Returns:
            Имя инструмента (tool.meta.name)
        """
        name = tool.meta.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name***REMOVED***")
        self._tools[name***REMOVED*** = tool
        return name

    def register_defaults(self) -> List[str***REMOVED***:
        """Регистрирует все встроенные инструменты.

        Returns:
            Список имён зарегистрированных инструментов
        """
        names = [***REMOVED***
        for tool_cls in [GitTool, SQLiteTool, HTTPTool, FileTool, ShellTool***REMOVED***:
            names.append(self.register(tool_cls()))
        return names

    def get(self, name: str) -> Optional[BaseTool***REMOVED***:
        """Получает инструмент по имени."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str***REMOVED*** = None) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список всех или отфильтрованных инструментов с метаданными.

        Args:
            category: фильтр по категории (None = все)

        Returns:
            Список метаданных инструментов
        """
        result = [***REMOVED***
        for name, tool in sorted(self._tools.items()):
            meta = tool.meta
            if category and meta.category != category:
                continue
            result.append({
                "name": meta.name,
                "description": meta.description,
                "version": meta.version,
                "category": meta.category,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                        "enum": p.enum,
                    ***REMOVED***
                    for p in meta.parameters
                ***REMOVED***,
                "examples": meta.examples,
            ***REMOVED***)
        return result

    def execute(
        self,
        tool_name: str,
        params: Dict[str, Any***REMOVED***,
        context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ) -> ToolResult:
        """Выполняет инструмент с валидацией и EventBus интеграцией.

        Args:
            tool_name: имя зарегистрированного инструмента
            params: параметры для инструмента
            context: опциональный контекст (переопределяет default_context)

        Returns:
            ToolResult
        """
        tool = self._tools.get(tool_name)
        if not tool:
            err_msg = f"Tool not found: {tool_name***REMOVED***"
            self._publish_event("tool.failed", {
                "tool": tool_name,
                "error": err_msg,
                "params": params,
            ***REMOVED***)
            return ToolResult(success=False, error=err_msg, tool_name=tool_name)

        # Merge contexts
        exec_context = dict(self._default_context)
        if context:
            exec_context.update(context)

        # Validate params
        errors = tool.validate_params(params)
        if errors:
            err_msg = "; ".join(errors)
            self._publish_event("tool.failed", {
                "tool": tool_name,
                "error": err_msg,
                "params": params,
                "validation_errors": errors,
            ***REMOVED***)
            return ToolResult(success=False, error=err_msg, tool_name=tool_name)

        # Execute
        try:
            result = tool.execute(params, exec_context)
        except Exception as e:
            result = ToolResult(success=False, error=str(e), tool_name=tool_name)

        # Publish event
        event_type = "tool.executed" if result.success else "tool.failed"
        self._publish_event(event_type, {
            "tool": tool_name,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "error": result.error,
            "params": params,
        ***REMOVED***)

        return result

    def execute_multi(
        self,
        calls: List[Tuple[str, Dict[str, Any***REMOVED******REMOVED******REMOVED***,
        context: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
        stop_on_error: bool = False,
    ) -> List[ToolResult***REMOVED***:
        """Выполняет несколько инструментов последовательно.

        Args:
            calls: список (tool_name, params)
            context: опциональный контекст
            stop_on_error: остановиться при первой ошибке

        Returns:
            Список ToolResult
        """
        results: List[ToolResult***REMOVED*** = [***REMOVED***
        for tool_name, params in calls:
            result = self.execute(tool_name, params, context)
            results.append(result)
            if not result.success and stop_on_error:
                break
        return results

    # ── EventBus ───────────────────────────────────────────

    def _publish_event(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие через EventBus."""
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type=event_type,
                    data=data,
                    source="tool_runtime",
                ))
            except Exception:
                pass  # Не ломаем выполнение из-за EventBus

    def set_event_bus(self, event_bus: Any) -> None:
        """Устанавливает или меняет EventBus."""
        self._event_bus = event_bus


# ═══════════════════════════════════════════════════════════════
# Orchestrator integration helpers
# ═══════════════════════════════════════════════════════════════


def create_default_registry(event_bus: Optional[Any***REMOVED*** = None) -> ToolRegistry:
    """Создаёт реестр со всеми встроенными инструментами.

    Args:
        event_bus: опциональный EventBus

    Returns:
        ToolRegistry с зарегистрированными default-инструментами
    """
    registry = ToolRegistry(event_bus=event_bus)
    registry.register_defaults()
    return registry


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Tool Runtime — система инструментов Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Примеры:
  python scripts/tool_runtime.py list
  python scripts/tool_runtime.py list --category git
  python scripts/tool_runtime.py run shell '{"command": "ls -la"***REMOVED***'
  python scripts/tool_runtime.py run file '{"action": "read", "path": "README.md"***REMOVED***'
  python scripts/tool_runtime.py run git '{"command": "status"***REMOVED***'
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="Список инструментов")
    p_list.add_argument("--category", help="Фильтр по категории")

    # run
    p_run = sub.add_parser("run", help="Выполнить инструмент")
    p_run.add_argument("tool", help="Имя инструмента")
    p_run.add_argument("params", help="Параметры в JSON")
    p_run.add_argument("--context", help="Контекст в JSON")

    args = parser.parse_args()

    registry = create_default_registry()

    if args.command == "list":
        tools = registry.list_tools(category=args.category)
        print(f"🔧 Tools ({len(tools)***REMOVED***):")
        for t in tools:
            params_str = ", ".join(
                f"{p['name'***REMOVED******REMOVED***:{p['type'***REMOVED******REMOVED***{'*' if p.get('required') else ''***REMOVED***"
                for p in t["parameters"***REMOVED***
            )
            print(f"  {t['name'***REMOVED***:10***REMOVED***  [{t['category'***REMOVED***:12***REMOVED******REMOVED***  {t['description'***REMOVED***[:60***REMOVED******REMOVED***")
            if params_str:
                print(f"             params: {params_str***REMOVED***")
            if t.get("examples"):
                for ex in t["examples"***REMOVED***[:2***REMOVED***:
                    print(f"             eg: {ex['command'***REMOVED******REMOVED***")

    elif args.command == "run":
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON params: {e***REMOVED***")
            return

        context = None
        if args.context:
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid JSON context: {e***REMOVED***")

        result = registry.execute(args.tool, params, context)

        if result.success:
            print(f"✅ {args.tool***REMOVED*** — OK ({result.duration_ms:.0f***REMOVED***ms)")
            if isinstance(result.data, str):
                print(result.data[:2000***REMOVED***)
            else:
                print(json.dumps(result.data, ensure_ascii=False, indent=2)[:2000***REMOVED***)
        else:
            print(f"❌ {args.tool***REMOVED*** — FAILED ({result.duration_ms:.0f***REMOVED***ms)")
            print(f"   Error: {result.error***REMOVED***")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
