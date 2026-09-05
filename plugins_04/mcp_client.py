"""MCP client stack — stdio + HTTP + bridge types.

Восстановлен v5.189.88 (runtime) + v5.189.91 (bridge) по контракту тестов:
  - tests_09/test_runtime_abstraction.py (StdioMCPClient)
  - tests_09/test_bridge_layer.py (MCPClientBase, HTTPMCPClient, MCPToolInfo, MCPCallResult)
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Полный таймаут на initialize-handshake / вызов инструмента.
# Тесты монкипатчат этот атрибут — читать ТОЛЬКО через модульную ссылку.
MCP_REQUEST_TIMEOUT = 30.0

_NEXT_ID_LOCK = threading.Lock()
_NEXT_ID = 0


def _next_id() -> int:
    global _NEXT_ID
    with _NEXT_ID_LOCK:
        _NEXT_ID += 1
        return _NEXT_ID


@dataclass
class MCPToolInfo:
    """Информация об MCP-инструменте."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCallResult:
    """Результат call_tool (bridge-layer контракт)."""
    success: bool
    content: Optional[List[Dict[str, Any]]] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MCPClientBase(ABC):
    """Абстрактный базовый класс MCP-клиента."""

    def __init__(self, name: Optional[str] = None) -> None:
        self._name = name or self.__class__.__name__
        self._connected: bool = False
        self._server_info: Dict[str, Any] = {}
        self._session_id: Optional[str] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def server_info(self) -> Dict[str, Any]:
        return self._server_info

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    def initialize(self) -> Dict[str, Any]:
        """Perform MCP initialize handshake. Default: no-op (returns {})."""
        return {}

    def list_tools(self) -> List[MCPToolInfo]:
        return []

    def list_resources(self) -> List[Any]:
        return []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPCallResult:
        return MCPCallResult(success=False, error="Not implemented")


class ToolCallResult:
    """Результат call_tool (legacy duck-typed совместимость)."""

    def __init__(
        self,
        success: bool,
        content: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.content = content or []
        self.error = error


class StdioMCPClient(MCPClientBase):
    """MCP-клиент, говорящий JSON-RPC по stdin/stdout дочернего процесса."""

    def __init__(self, command: str, args: Optional[List[str]] = None, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self.command = command
        self.args = args or []
        self._proc: Optional[subprocess.Popen] = None
        self._request_id = 0

    # -- lifecycle -------------------------------------------------

    @property
    def is_connected(self) -> bool:  # type: ignore[override]
        """Property (не метод): адаптеры и тесты читают как атрибут."""
        return self._connected or (self._proc is not None and self._proc.poll() is None)

    def connect(self) -> bool:
        """Spawn процесс и выполнить initialize-handshake."""
        if self.is_connected:
            return True
        try:
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except OSError:
            self._proc = None
            return False

        # MCP initialize handshake inline (не через self.initialize(),
        # чтобы patch.object(MCPClientBase, "initialize") из тестов не ломал).
        init_result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "workspace-os-runtime", "version": "1.0"},
            },
        )
        if init_result is None:
            self.disconnect()
            return False

        info = init_result.get("serverInfo") if isinstance(init_result, dict) else None
        if isinstance(info, dict):
            self._server_info = {"serverInfo": info}
        self._notify("notifications/initialized")
        return True

    def list_tools(self) -> List[MCPToolInfo]:  # type: ignore[override]
        if not self.is_connected:
            return []
        result = self._request("tools/list", {})
        if not isinstance(result, dict):
            return []
        tools_raw = result.get("tools", [])
        if not isinstance(tools_raw, list):
            return []
        return [MCPToolInfo(
            name=t.get("name", ""),
            description=t.get("description", ""),
            input_schema=t.get("inputSchema", {}),
        ) for t in tools_raw if isinstance(t, dict)]

    def list_resources(self) -> List[Any]:
        if not self.is_connected:
            return []
        result = self._request("resources/list", {})
        if not isinstance(result, dict):
            return []
        resources: List[Any] = result.get("resources", [])
        return resources if isinstance(resources, list) else []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPCallResult:  # type: ignore[override]
        if not self.is_connected:
            return MCPCallResult(success=False, error="Not connected")
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result is None:
            return MCPCallResult(success=False, error="Request failed")
        content = result.get("content")
        return MCPCallResult(success=True, content=content if isinstance(content, list) else [])

    def disconnect(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        except Exception:
            pass

    def ping(self) -> bool:
        if not self.is_connected:
            return False
        return self._request("ping", {}) is not None

    # -- tools -----------------------------------------------------



    # -- JSON-RPC internals -----------------------------------------

    def _send(self, payload: Dict[str, Any]) -> bool:
        if self._proc is None or self._proc.stdin is None:
            return False
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def _read_line(self, timeout: float) -> Optional[str]:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            # select, чтобы readline не блокировал дольше deadline
            try:
                import select

                ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.2))
            except (OSError, ValueError, TypeError):
                ready = [proc.stdout]
            if not ready:
                if proc.poll() is not None:
                    return None
                continue
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    return None
                continue
            stripped = line.strip() if isinstance(line, str) else None
            return stripped if stripped else None
        return None

    def _request(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        req_id = _next_id()
        timeout = MCP_REQUEST_TIMEOUT
        if not self._send({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}):
            return None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self._read_line(max(0.05, deadline - time.monotonic()))
            if line is None:
                return None
            try:
                msg = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(msg, dict) and msg.get("id") == req_id:
                if "error" in msg:
                    return None
                return msg.get("result")
        return None

    def _notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})


class HTTPMCPClient(MCPClientBase):
    """HTTP-транспорт MCP (Streamable HTTP)."""

    def __init__(self, url: str, *, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._url = url

    def initialize(self) -> Dict[str, Any]:  # type: ignore[override]
        return {}

    def connect(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(
                self._url,
                data=json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "workspace-os-http", "version": "1.0"},
                    },
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid
                self._connected = True
                return True
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False
        self._session_id = None
