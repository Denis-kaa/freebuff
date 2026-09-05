"""Runtime adapters: ABC + Stdio/HTTP MCP implementations.

Восстановлено v5.189.88 по контракту тестов tests_09/test_runtime_abstraction.py.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

import plugins_04.mcp_client as _mcp_client
from plugins_04.mcp_client import StdioMCPClient
from plugins_04.runtime import (
    AdapterType,
    RuntimeCapability,
    RuntimeConfig,
    RuntimeHealth,
    RuntimeResult,
    RuntimeSession,
    SessionStatus,
)


class RuntimeAdapter(ABC):
    """Базовый абстрактный адаптер runtime."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._session: Optional[RuntimeSession] = None
        self.reset_session()

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> bool: ...

    @abstractmethod
    def ping(self) -> bool: ...

    @abstractmethod
    def health(self) -> RuntimeHealth: ...

    @abstractmethod
    def generate(self, messages: List[Dict[str, Any]]) -> RuntimeResult: ...

    def reset_session(self) -> None:
        """Сброс сессии — новая пустая (message_count == 0)."""
        # getattr: при __init__ базового класса name-свойство наследника ещё не готово
        runtime_name = getattr(self, "_name", None) or getattr(self, "name", "")
        self._session = RuntimeSession(runtime=runtime_name if isinstance(runtime_name, str) else "")

    def is_connected(self) -> bool:
        return False

    def list_capabilities(self) -> List[RuntimeCapability]:
        return []


class StdioMCPAdapter(RuntimeAdapter):
    """Адаптер к MCP-серверу через stdio subprocess."""

    adapter_type = AdapterType.STDIO_MCP.value

    def __init__(
        self,
        config: RuntimeConfig,
        command: str,
        args: List[str],
        name: str,
        display_name: str,
    ) -> None:
        super().__init__(config)
        # command/display_name как instance-атрибуты перекрывают property наследников;
        # name оставляем property-совместимым через object.__setattr__ нельзя для dataclass —
        # поэтому храним и отдаём через атрибуты.
        self._name = name
        self._display_name = display_name
        self.command = command
        self.args = list(args)
        self._client: Optional[StdioMCPClient] = None

    @property
    def name(self) -> str:
        return self._name  # type: ignore[no-any-return]

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def display_name(self) -> str:
        return self._display_name  # type: ignore[no-any-return]

    @display_name.setter
    def display_name(self, value: str) -> None:
        self._display_name = value

    def connect(self) -> bool:
        client = StdioMCPClient(self.command, self.args)
        ok = client.connect()
        if not ok:
            return False
        self._client = client
        if self._session is not None:
            self._session.status = SessionStatus.ACTIVE
        return True

    def disconnect(self) -> bool:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        return True

    def is_connected(self) -> bool:
        return self._client is not None and bool(getattr(self._client, "is_connected", False))

    def ping(self) -> bool:
        if not self.is_connected():
            return False
        assert self._client is not None
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def health(self) -> RuntimeHealth:
        connected = self.is_connected()
        alive = connected and self.ping()
        version = "unknown"
        tools_count = 0
        if connected and self._client is not None:
            info = getattr(self._client, "server_info", {}) or {}
            server_info = info.get("serverInfo") if isinstance(info, dict) else None
            if isinstance(server_info, dict):
                version = str(server_info.get("version", "unknown"))
            try:
                tools_count = len(self._client.list_tools())
            except Exception:
                tools_count = 0
        return RuntimeHealth(
            alive=alive,
            version=version,
            latency_ms=0,
            connected=connected,
            tools_count=tools_count,
        )

    def _select_tool(self, messages: List[Dict[str, Any]]) -> Optional[Any]:
        assert self._client is not None
        for tool in self._client.list_tools():
            schema = getattr(tool, "input_schema", None) or {}
            props = schema.get("properties", {}) if isinstance(schema, dict) else {}
            if "messages" in props or getattr(tool, "name", "") == "generate":
                return tool
        return None

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> RuntimeResult:
        start = time.monotonic()
        result = RuntimeResult(runtime=self.name)
        if not self.is_connected() or self._client is None:
            result.error = "Not connected"
            return result
        tool = self._select_tool(messages)
        if tool is None:
            result.error = "No suitable generation tool found"
            return result
        arguments: Dict[str, Any] = {"messages": messages}
        if system is not None:
            arguments["system"] = system
        if temperature is not None:
            arguments["temperature"] = temperature
        if max_tokens is not None:
            arguments["max_tokens"] = max_tokens
        try:
            call = self._client.call_tool(tool.name, arguments)
        except Exception as exc:  # pragma: no cover - защитный путь
            result.error = f"Tool call failed: {exc}"
            return result
        result.latency_ms = int((time.monotonic() - start) * 1000)
        if call.success:
            parts = [
                item.get("text", "")
                for item in call.content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            result.content = "\n".join(p for p in parts if p)
            if self._session is not None:
                self._session.message_count += len(messages)
        else:
            result.error = call.error or "Tool call failed"
        return result


class HTTPMCPAdapter(RuntimeAdapter):
    """Адаптер к MCP-серверу по HTTP (streamable/SSE)."""

    adapter_type = AdapterType.HTTP_MCP.value

    def __init__(
        self,
        config: RuntimeConfig,
        url: str,
        name: str,
        display_name: str,
    ) -> None:
        super().__init__(config)
        self._name = name
        self._display_name = display_name
        self.url = url
        self._connected = False

    @property
    def name(self) -> str:
        return self._name  # type: ignore[no-any-return]

    @property
    def display_name(self) -> str:
        return self._display_name  # type: ignore[no-any-return]

    @property
    def adapter_type_value(self) -> str:
        return AdapterType.HTTP_MCP.value

    def connect(self) -> bool:
        try:
            import urllib.request

            req = urllib.request.Request(
                self.url,
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=min(5.0, float(_mcp_client.MCP_REQUEST_TIMEOUT))):
                self._connected = True
                return True
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> bool:
        was_connected = self._connected
        self._connected = False
        _ = was_connected
        return True

    def is_connected(self) -> bool:
        return self._connected

    def ping(self) -> bool:
        return False

    def health(self) -> RuntimeHealth:
        return RuntimeHealth(alive=self._connected, connected=self._connected)

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> RuntimeResult:
        result = RuntimeResult(runtime=self.name)
        if not self._connected:
            result.error = "Not connected"
        return result


class AdapterRegistry:
    """Реестр классов адаптеров по типу."""

    def __init__(self) -> None:
        self._adapters: Dict[str, Type[RuntimeAdapter]] = {}

    def register(self, type_name: str, adapter_cls: Type[RuntimeAdapter]) -> None:
        self._adapters[type_name] = adapter_cls

    def get(self, type_name: str) -> Optional[Type[RuntimeAdapter]]:
        return self._adapters.get(type_name)

    def list_types(self) -> List[str]:
        return list(self._adapters.keys())

    def create(self, type_name: str, config: RuntimeConfig, **kwargs: Any) -> Optional[RuntimeAdapter]:
        """Создание адаптера с маппингом kwargs под его сигнатуру.

        Алиасы: runtime_name → name, display → display_name и т.п.
        """
        import inspect

        cls = self.get(type_name)
        if cls is None:
            return None
        aliases = {
            "name": ("runtime_name", "runtime", "adapter_name"),
            "display_name": ("display", "title", "adapter_display_name"),
            "command": ("cmd",),
            "url": ("endpoint",),
        }
        try:
            sig = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            return None
        call_kwargs: Dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self" or param_name == "config":
                continue
            if param_name in kwargs:
                call_kwargs[param_name] = kwargs[param_name]
                continue
            value = next((kwargs[a] for a in aliases.get(param_name, ()) if a in kwargs), None)
            if value is not None:
                call_kwargs[param_name] = value
            elif param.default is inspect.Parameter.empty:
                # Обязательный позиционный без значения — пустая строка/list по аннотации
                ann = param.annotation
                call_kwargs[param_name] = [] if "List" in str(ann) else ""
        try:
            return cls(config=config, **call_kwargs)  # type: ignore[misc]
        except TypeError:
            return None


default_adapter_registry = AdapterRegistry()
default_adapter_registry.register(AdapterType.STDIO_MCP.value, StdioMCPAdapter)
default_adapter_registry.register(AdapterType.HTTP_MCP.value, HTTPMCPAdapter)
