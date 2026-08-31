"""
MCP Client — клиент для подключения к внешним MCP-серверам.

Поддерживает два транспорта:
  - StdioMCPClient: подпроцесс + stdin/stdout (JSON-RPC 2.0)
  - HTTPMCPClient: Streamable HTTP (POST/GET/DELETE)

Оба реализуют единый интерфейс:
  - connect() — установить соединение
  - list_tools() — список инструментов сервера
  - call_tool(name, arguments) — вызвать инструмент
  - list_resources() — список ресурсов
  - read_resource(uri) — прочитать ресурс
  - disconnect() — закрыть соединение

Использование:
    # Stdio транспорт (путь к серверу передаётся как параметр)
    client = StdioMCPClient("python", ["./mcp_server.py"])
    client.connect()
    tools = client.list_tools()
    result = client.call_tool("knowledge_search", {"query": "python"})
    client.disconnect()

    # HTTP транспорт
    client = HTTPMCPClient("http://127.0.0.1:8765/mcp")
    client.connect()
    tools = client.list_tools()
    client.disconnect()
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


# ── Constants ──────────────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_REQUEST_TIMEOUT = 30.0


# ── Types ──────────────────────────────────────────────────────


@dataclass
class MCPToolInfo:
    """Информация об инструменте MCP сервера."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResourceInfo:
    """Информация о ресурсе MCP сервера."""
    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPCallResult:
    """Результат вызова инструмента MCP."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    is_error: bool = False
    content: List[Dict[str, Any]] = field(default_factory=list)


# ── Base MCP Client ────────────────────────────────────────────


class MCPClientBase:
    """Базовый класс для MCP клиентов."""

    def __init__(self, name: str = "mcp-client"):
        self.name = name
        self._connected = False
        self._request_id = 0
        self._server_info: Dict[str, Any] = {}
        self._session_id: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def server_info(self) -> Dict[str, Any]:
        return self._server_info

    def connect(self) -> bool:
        """Устанавливает соединение и выполняет initialize handshake."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Закрывает соединение."""
        raise NotImplementedError

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос и возвращает ответ."""
        raise NotImplementedError

    # ── MCP Methods ──────────────────────────────────────────

    def initialize(self) -> Dict[str, Any]:
        """Выполняет initialize handshake."""
        result = self._send_request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "clientInfo": {
                "name": self.name,
                "version": "1.0.0",
            },
            "capabilities": {},
        })
        self._server_info = result
        return result

    def ping(self) -> bool:
        """Проверяет соединение."""
        try:
            self._send_request("ping", {})
            return True
        except Exception:
            return False

    def list_tools(self) -> List[MCPToolInfo]:
        """Получает список инструментов сервера."""
        result = self._send_request("tools/list", {})
        tools = result.get("tools", [])
        return [
            MCPToolInfo(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPCallResult:
        """Вызывает инструмент на сервере."""
        try:
            result = self._send_request("tools/call", {
                "name": name,
                "arguments": arguments,
            })
            content = result.get("content", [])
            is_error = result.get("isError", False)
            return MCPCallResult(
                success=not is_error,
                data=content,
                is_error=is_error,
                content=content,
            )
        except Exception as e:
            return MCPCallResult(
                success=False,
                error=str(e),
            )

    def list_resources(self) -> List[MCPResourceInfo]:
        """Получает список ресурсов сервера."""
        result = self._send_request("resources/list", {})
        resources = result.get("resources", [])
        return [
            MCPResourceInfo(
                uri=r.get("uri", ""),
                name=r.get("name", ""),
                description=r.get("description", ""),
                mime_type=r.get("mimeType", "text/plain"),
            )
            for r in resources
        ]

    def read_resource(self, uri: str) -> Optional[str]:
        """Читает ресурс сервера."""
        try:
            result = self._send_request("resources/read", {"uri": uri})
            contents = result.get("contents", [])
            if contents:
                return contents[0].get("text", "")
            return None
        except Exception:
            return None

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Получает список промптов сервера."""
        result = self._send_request("prompts/list", {})
        return result.get("prompts", [])

    def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Optional[str]:
        """Получает промпт сервера."""
        try:
            params: Dict[str, Any] = {"name": name}
            if arguments:
                params["arguments"] = arguments
            result = self._send_request("prompts/get", params)
            messages = result.get("messages", [])
            if messages:
                return messages[0].get("content", {}).get("text", "")
            return None
        except Exception:
            return None


# ── Stdio MCP Client ────────────────────────────────────────────


class StdioMCPClient(MCPClientBase):
    """MCP Client через stdio транспорт (подпроцесс)."""

    def __init__(
        self,
        command: str,
        args: List[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        name: str = "stdio-mcp-client",
    ):
        super().__init__(name=name)
        self._command = command
        self._args = args or []
        self._cwd = cwd or os.getcwd()
        self._env = env or os.environ.copy()
        self._process: Optional[subprocess.Popen] = None
        self._response_queue: Queue = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._active_request_ids: set = set()  # отслеживаем активные request_id

    def connect(self) -> bool:
        """Запускает подпроцесс и выполняет handshake."""
        if self._connected:
            return True

        try:
            full_cmd = [self._command] + self._args
            self._process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                env=self._env,
                text=True,
                bufsize=1,  # line buffered
            )

            # Запускаем reader thread
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
                name=f"mcp-reader-{self.name}",
            )
            self._reader_thread.start()

            # Initialize handshake
            result = self.initialize()
            if result:
                self._connected = True
                return True

            self.disconnect()
            return False

        except Exception as e:
            print(f"⚠️ StdioMCPClient connect error: {e}", file=sys.stderr)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Завершает подпроцесс."""
        self._connected = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    def _reader_loop(self) -> None:
        """Читает stdout подпроцесса и складывает ответы в очередь."""
        if not self._process or not self._process.stdout:
            return
        try:
            for line in self._process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    response = json.loads(line)
                    self._response_queue.put(response)
                except json.JSONDecodeError:
                    pass  # игнорируем не-JSON вывод
        except (BrokenPipeError, ValueError, OSError):
            pass  # процесс завершился

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос и ждёт ответ."""
        if not self._process or not self._process.stdin:
            raise ConnectionError("Not connected")

        req_id = self._next_id()
        self._active_request_ids.add(req_id)
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

        with self._lock:
            request_str = json.dumps(request, ensure_ascii=False) + "\n"
            self._process.stdin.write(request_str)
            self._process.stdin.flush()

        # Ждём ответ с нужным ID
        deadline = time.time() + MCP_REQUEST_TIMEOUT
        while time.time() < deadline:
            try:
                response = self._response_queue.get(timeout=1)
            except Empty:
                continue

            resp_id = response.get("id")
            if resp_id == req_id:
                self._active_request_ids.discard(req_id)
                if "error" in response:
                    err = response["error"]
                    raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
                return response.get("result", {})
            elif resp_id not in self._active_request_ids:
                # Ответ с неизвестным ID (старый таймаутнутый запрос) — отбрасываем
                continue
            else:
                # Ответ для другого активного запроса — возвращаем в очередь
                self._response_queue.put(response)

        self._active_request_ids.discard(req_id)
        raise TimeoutError(f"MCP request timeout: {method}")


# ── HTTP MCP Client ────────────────────────────────────────────


class HTTPMCPClient(MCPClientBase):
    """MCP Client через Streamable HTTP транспорт."""

    def __init__(
        self,
        endpoint: str,
        name: str = "http-mcp-client",
    ):
        super().__init__(name=name)
        self._endpoint = endpoint.rstrip("/")
        self._session_id: Optional[str] = None

    def connect(self) -> bool:
        """Устанавливает HTTP соединение и выполняет handshake."""
        if self._connected:
            return True

        if not HTTP_AVAILABLE:
            print("⚠️ HTTPMCPClient: urllib not available", file=sys.stderr)
            return False

        try:
            # Initialize — получаем session_id из заголовков
            result = self._send_http_request("POST", {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {
                        "name": self.name,
                        "version": "1.0.0",
                    },
                    "capabilities": {},
                },
            })
            self._server_info = result
            self._connected = True
            return True
        except Exception as e:
            print(f"⚠️ HTTPMCPClient connect error: {e}", file=sys.stderr)
            return False

    def disconnect(self) -> None:
        """Закрывает HTTP сессию (DELETE)."""
        if self._session_id:
            try:
                self._send_http_raw("DELETE", b"")
            except Exception:
                pass
            self._session_id = None
        self._connected = False

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос через HTTP POST."""
        req_id = self._next_id()
        body = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        return self._send_http_request("POST", body)

    def _send_http_request(self, http_method: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет HTTP запрос и парсит JSON ответ."""
        if not HTTP_AVAILABLE:
            raise RuntimeError("urllib not available")

        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = Request(
            f"{self._endpoint}/mcp" if not self._endpoint.endswith("/mcp") else self._endpoint,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
            method=http_method,
        )

        if self._session_id:
            req.add_header("Mcp-Session-Id", self._session_id)

        try:
            with urlopen(req, timeout=MCP_REQUEST_TIMEOUT) as resp:
                # Сохраняем session_id из заголовков
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid

                body_data = resp.read().decode("utf-8")
                if not body_data:
                    return {}

                response = json.loads(body_data)

                # Проверяем JSON-RPC ошибку
                if isinstance(response, dict) and "error" in response:
                    err = response["error"]
                    raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")

                return response if isinstance(response, dict) else {}

        except URLError as e:
            raise RuntimeError(f"HTTP error: {e}")

    def _send_http_raw(self, http_method: str, body_bytes: bytes) -> None:
        """Отправляет сырой HTTP запрос (для DELETE без тела)."""
        if not HTTP_AVAILABLE:
            return

        req = Request(
            f"{self._endpoint}/mcp" if not self._endpoint.endswith("/mcp") else self._endpoint,
            data=body_bytes if body_bytes else None,
            headers={
                "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
            method=http_method,
        )

        if self._session_id:
            req.add_header("Mcp-Session-Id", self._session_id)

        try:
            with urlopen(req, timeout=MCP_REQUEST_TIMEOUT):
                pass
        except Exception:
            pass
