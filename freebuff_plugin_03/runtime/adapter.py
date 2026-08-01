"""
Runtime Abstraction Layer — RuntimeAdapter базовый класс и реализации.

Спецификация: docs_10/core/RUNTIME_ABSTRACTION_SPECIFICATION.md §4
Основание: VISION_3.0.md §3.2
"""

from __future__ import annotations

import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type

from freebuff_plugin_03.runtime import (
    AdapterType,
    RuntimeCapability,
    RuntimeConfig,
    RuntimeDefinition,
    RuntimeHealth,
    RuntimeResult,
    RuntimeSession,
    RuntimeStatus,
    SessionStatus,
)
from freebuff_plugin_03.mcp_client import (
    StdioMCPClient,
    HTTPMCPClient,
    MCPToolInfo,
)


# ═══════════════════════════════════════════════════════════════
# RuntimeAdapter — Abstract Base Class
# ═══════════════════════════════════════════════════════════════


class RuntimeAdapter(ABC):
    """Базовый класс адаптера для AI Runtime.

    Каждый Runtime (freebuff, Claude Code, OpenClaw, ...) реализует
    этот интерфейс. Adapter скрывает детали транспорта (MCP stdio,
    MCP HTTP, subprocess) от Runtime Abstraction Layer.
    """

    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._session: Optional[RuntimeSession***REMOVED*** = None

    # ── Lifecycle ────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """Подключиться к Runtime (handshake, initialize)."""
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        """Отключиться от Runtime."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Проверить, активно ли подключение."""
        ...

    # ── Runtime API ──────────────────────────────────────────

    @abstractmethod
    def ping(self) -> bool:
        """Проверить доступность Runtime."""
        ...

    @abstractmethod
    def health(self) -> RuntimeHealth:
        """Полный health check Runtime."""
        ...

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str***REMOVED******REMOVED***,
        system: Optional[str***REMOVED*** = None,
        temperature: float = 0.7,
        max_tokens: Optional[int***REMOVED*** = None,
    ) -> RuntimeResult:
        """Генерация ответа от Runtime."""
        ...

    @abstractmethod
    def list_capabilities(self) -> List[RuntimeCapability***REMOVED***:
        """Список capability этого Runtime."""
        ...

    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список MCP-инструментов Runtime."""
        ...

    # ── Session ──────────────────────────────────────────────

    def get_session(self) -> Optional[RuntimeSession***REMOVED***:
        """Текущая сессия Runtime."""
        return self._session

    def reset_session(self) -> None:
        """Сбросить сессию (начать новую)."""
        self._session = RuntimeSession()

    @property
    @abstractmethod
    def name(self) -> str:
        """Каноническое имя Runtime (freebuff, claude-code)."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Человеческое имя (Freebuff CLI, Claude Code)."""
        ...

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Тип адаптера (stdio_mcp, http, subprocess)."""
        ...


# ═══════════════════════════════════════════════════════════════
# StdioMCPAdapter — через MCP STDIO (основной)
# ═══════════════════════════════════════════════════════════════


class StdioMCPAdapter(RuntimeAdapter):
    """Адаптер для Runtime, работающих через STDIO MCP протокол.

    Использует существующий StdioMCPClient из MCP Client библиотеки.
    Подходит для: freebuff (Codebuff), Claude Code, OpenClaw.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        command: str,
        args: Optional[List[str***REMOVED******REMOVED*** = None,
        runtime_name: str = "unknown",
        display_name: str = "Unknown Runtime",
    ):
        super().__init__(config)
        self._runtime_name = runtime_name
        self._display_name = display_name
        self._command = command
        self._args = args or [***REMOVED***
        self._client: Optional[StdioMCPClient***REMOVED*** = None
        self._tools: List[MCPToolInfo***REMOVED*** = [***REMOVED***
        self._capabilities: List[RuntimeCapability***REMOVED*** = [***REMOVED***

    def connect(self) -> bool:
        if self.is_connected():
            return True

        try:
            self._client = StdioMCPClient(
                command=self._command,
                args=self._args,
                cwd=self.config.work_dir,
                env=self.config.env_vars or None,
                name=self._runtime_name,
            )
            ok = self._client.connect()
            if ok:
                self._tools = self._client.list_tools()
                self._session = RuntimeSession(runtime=self._runtime_name)
            return ok
        except Exception as e:
            self._client = None
            return False

    def disconnect(self) -> bool:
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._tools = [***REMOVED***
        self._session = None
        return True

    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def ping(self) -> bool:
        if not self._client:
            return False
        try:
            return self._client.ping()
        except Exception:
            return False

    def health(self) -> RuntimeHealth:
        t0 = time.time()
        try:
            alive = self.ping()
            latency_ms = int((time.time() - t0) * 1000)
            if alive:
                return RuntimeHealth(
                    alive=True,
                    version=self._client.server_info.get("serverInfo", {***REMOVED***).get("version", "unknown")
                    if self._client else "unknown",
                    latency_ms=latency_ms,
                    connected=True,
                    tools_count=len(self._tools),
                )
            return RuntimeHealth(alive=False, latency_ms=latency_ms, error="ping failed")
        except Exception as e:
            return RuntimeHealth(alive=False, error=str(e))

    def generate(
        self,
        messages: List[Dict[str, str***REMOVED******REMOVED***,
        system: Optional[str***REMOVED*** = None,
        temperature: float = 0.7,
        max_tokens: Optional[int***REMOVED*** = None,
    ) -> RuntimeResult:
        if not self._client:
            return RuntimeResult(error="Not connected", runtime=self._runtime_name)

        t0 = time.time()
        try:
            # Пытаемся найти подходящий MCP инструмент для генерации
            tool_name = self._find_generate_tool()
            if not tool_name:
                return RuntimeResult(
                    error="No suitable generate tool found",
                    runtime=self._runtime_name,
                )

            # Формируем аргументы
            args: Dict[str, Any***REMOVED*** = {"messages": messages***REMOVED***
            if system:
                args["system"***REMOVED*** = system
            if temperature != 0.7:
                args["temperature"***REMOVED*** = temperature
            if max_tokens:
                args["max_tokens"***REMOVED*** = max_tokens

            result = self._client.call_tool(tool_name, args)

            if not result.success:
                return RuntimeResult(
                    error=result.error or "generate failed",
                    runtime=self._runtime_name,
                    latency_ms=int((time.time() - t0) * 1000),
                )

            # Извлекаем текст из content
            content_text = ""
            for c in result.content:
                if c.get("type") == "text":
                    content_text += c.get("text", "")

            # Обновляем сессию
            if self._session:
                self._session.message_count += 1
                self._session.token_estimate += len(messages) + len(content_text)
                self._session.status = SessionStatus.ACTIVE

            return RuntimeResult(
                content=content_text,
                runtime=self._runtime_name,
                latency_ms=int((time.time() - t0) * 1000),
            )

        except Exception as e:
            return RuntimeResult(
                error=str(e),
                runtime=self._runtime_name,
                latency_ms=int((time.time() - t0) * 1000),
            )

    def _find_generate_tool(self) -> Optional[str***REMOVED***:
        """Ищет подходящий MCP инструмент для генерации.

        Предпочитает: generate, generate_stream, codegen, run.
        Если не найдено — берёт первый попавшийся инструмент,
        который принимает messages.
        """
        preferred = {"generate", "generate_stream", "codegen", "run", "execute"***REMOVED***
        for tool in self._tools:
            if tool.name in preferred:
                return tool.name
        # Fallback: первый инструмент, который принимает messages
        for tool in self._tools:
            props = tool.input_schema.get("properties", {***REMOVED***)
            if "messages" in props or "prompt" in props:
                return tool.name
        # Fallback: первый инструмент
        if self._tools:
            return self._tools[0***REMOVED***.name
        return None

    def list_capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return self._capabilities

    def list_tools(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            ***REMOVED***
            for t in self._tools
        ***REMOVED***

    @property
    def name(self) -> str:
        return self._runtime_name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def adapter_type(self) -> str:
        return AdapterType.STDIO_MCP.value


# ═══════════════════════════════════════════════════════════════
# HTTPMCPAdapter — через MCP HTTP
# ═══════════════════════════════════════════════════════════════


class HTTPMCPAdapter(RuntimeAdapter):
    """Адаптер для Runtime с MCP HTTP транспортом.

    Использует HTTPMCPClient для подключения к Runtime через HTTP.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        endpoint: str,
        runtime_name: str = "http-runtime",
        display_name: str = "HTTP Runtime",
    ):
        super().__init__(config)
        self._runtime_name = runtime_name
        self._display_name = display_name
        self._endpoint = endpoint
        self._client: Optional[HTTPMCPClient***REMOVED*** = None
        self._tools: List[MCPToolInfo***REMOVED*** = [***REMOVED***
        self._capabilities: List[RuntimeCapability***REMOVED*** = [***REMOVED***

    def connect(self) -> bool:
        if self.is_connected():
            return True

        try:
            self._client = HTTPMCPClient(
                endpoint=self._endpoint,
                name=self._runtime_name,
            )
            ok = self._client.connect()
            if ok:
                self._tools = self._client.list_tools()
                self._session = RuntimeSession(runtime=self._runtime_name)
            return ok
        except Exception:
            self._client = None
            return False

    def disconnect(self) -> bool:
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._tools = [***REMOVED***
        self._session = None
        return True

    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def ping(self) -> bool:
        if not self._client:
            return False
        try:
            return self._client.ping()
        except Exception:
            return False

    def health(self) -> RuntimeHealth:
        t0 = time.time()
        try:
            alive = self.ping()
            return RuntimeHealth(
                alive=alive,
                latency_ms=int((time.time() - t0) * 1000),
                connected=alive,
                tools_count=len(self._tools),
            )
        except Exception as e:
            return RuntimeHealth(alive=False, error=str(e))

    def generate(
        self,
        messages: List[Dict[str, str***REMOVED******REMOVED***,
        system: Optional[str***REMOVED*** = None,
        temperature: float = 0.7,
        max_tokens: Optional[int***REMOVED*** = None,
    ) -> RuntimeResult:
        if not self._client:
            return RuntimeResult(error="Not connected", runtime=self._runtime_name)

        t0 = time.time()
        try:
            tool_name = self._find_generate_tool()
            if not tool_name:
                return RuntimeResult(error="No generate tool", runtime=self._runtime_name)

            args: Dict[str, Any***REMOVED*** = {"messages": messages***REMOVED***
            if system:
                args["system"***REMOVED*** = system
            if max_tokens:
                args["max_tokens"***REMOVED*** = max_tokens

            result = self._client.call_tool(tool_name, args)

            content_text = ""
            for c in result.content:
                if c.get("type") == "text":
                    content_text += c.get("text", "")

            return RuntimeResult(
                content=content_text,
                runtime=self._runtime_name,
                latency_ms=int((time.time() - t0) * 1000),
                error=result.error,
            )
        except Exception as e:
            return RuntimeResult(
                error=str(e),
                runtime=self._runtime_name,
                latency_ms=int((time.time() - t0) * 1000),
            )

    def _find_generate_tool(self) -> Optional[str***REMOVED***:
        preferred = {"generate", "generate_stream", "codegen", "run"***REMOVED***
        for tool in self._tools:
            if tool.name in preferred:
                return tool.name
        for tool in self._tools:
            props = tool.input_schema.get("properties", {***REMOVED***)
            if "messages" in props or "prompt" in props:
                return tool.name
        if self._tools:
            return self._tools[0***REMOVED***.name
        return None

    def list_capabilities(self) -> List[RuntimeCapability***REMOVED***:
        return self._capabilities

    def list_tools(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema***REMOVED***
            for t in self._tools
        ***REMOVED***

    @property
    def name(self) -> str:
        return self._runtime_name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def adapter_type(self) -> str:
        return AdapterType.HTTP_MCP.value


# ═══════════════════════════════════════════════════════════════
# Adapter Registry
# ═══════════════════════════════════════════════════════════════


class AdapterRegistry:
    """Реестр адаптеров Runtime — сопоставляет тип адаптера с классом.

    Позволяет плагинам регистрировать свои адаптеры.
    """

    def __init__(self):
        self._adapters: Dict[str, Type[RuntimeAdapter***REMOVED******REMOVED*** = {***REMOVED***

    def register(self, adapter_type: str, adapter_cls: Type[RuntimeAdapter***REMOVED***) -> None:
        """Зарегистрировать класс адаптера."""
        self._adapters[adapter_type***REMOVED*** = adapter_cls

    def get(self, adapter_type: str) -> Optional[Type[RuntimeAdapter***REMOVED******REMOVED***:
        """Получить класс адаптера по типу."""
        return self._adapters.get(adapter_type)

    def list_types(self) -> List[str***REMOVED***:
        """Список зарегистрированных типов адаптеров."""
        return list(self._adapters.keys())

    def create(
        self,
        adapter_type: str,
        config: RuntimeConfig,
        **kwargs,
    ) -> Optional[RuntimeAdapter***REMOVED***:
        """Создать экземпляр адаптера по типу."""
        cls = self.get(adapter_type)
        if cls is None:
            return None
        try:
            return cls(config=config, **kwargs)
        except Exception:
            return None


# Default adapter registry
default_adapter_registry = AdapterRegistry()
default_adapter_registry.register(AdapterType.STDIO_MCP.value, StdioMCPAdapter)
default_adapter_registry.register(AdapterType.HTTP_MCP.value, HTTPMCPAdapter)
