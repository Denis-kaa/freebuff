"""
Bridge Layer — универсальный мост между MCP (Model Context Protocol) и ACP (Agent Collaboration Protocol).

Позволяет:
  1. MCP → ACP: Вызов MCP инструмента транслируется в ACP задачу для агента
  2. ACP → MCP: ACP задача транслируется в вызов MCP инструмента на внешнем сервере
  3. Agent Discovery: MCP серверы автоматически регистрируются как ACP агенты
  4. Bidirectional: двусторонняя трансляция

Архитектура:
  ┌─────────────┐     MCP      ┌──────────────┐     ACP      ┌─────────────┐
  │ External    │◄───────────►│  Bridge      │◄───────────►│  Local      │
  │ MCP Server  │             │  Layer       │             │  Agents     │
  └─────────────┘             │              │             └─────────────┘
                              │  ┌────────┐  │
  ┌─────────────┐     MCP     │  │ MCP    │  │
  │ Codebuff    │◄───────────►│  │ Client │  │
  │ (freebuff)  │             │  └────────┘  │
  └─────────────┘             │  ┌────────┐  │
                              │  │ ACP    │  │
  ┌─────────────┐     ACP     │  │Handler │  │
  │ Claude      │◄───────────►│  └────────┘  │
  │ Code        │             └──────────────┘
  └─────────────┘

Использование:
    from freebuff_plugin_03.bridge_layer import BridgeLayer
    from freebuff_plugin_03.bridge import get_event_bus

    bus = get_event_bus()
    bridge = BridgeLayer(bus, agent_name="buffy-bridge")
    bridge.start()

    # Подключить внешний MCP сервер (путь передаётся как параметр)
    bridge.connect_mcp_stdio("python", ["./mcp_server.py"***REMOVED***, name="local-mcp")

    # Теперь можно отправлять ACP задачи, которые будут выполнены на MCP сервере
    # И наоборот — MCP инструменты доступны как ACP возможности
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from freebuff_plugin_03.acp_protocol import (
    ACPHandler, AgentRegistry, AgentInfo, AgentStatus,
    ACPTask, ACPResult,
)
from freebuff_plugin_03.mcp_client import (
    MCPClientBase, StdioMCPClient, HTTPMCPClient,
    MCPToolInfo, MCPCallResult,
)

# ═══════════════════════════════════════════════════════════════
# Bridge Layer
# ═══════════════════════════════════════════════════════════════


@dataclass
class BridgeMCPServer:
    """Запись о подключённом MCP сервере в Bridge Layer."""
    name: str
    client: MCPClientBase
    type: str = "stdio"  # stdio или http
    tools: List[MCPToolInfo***REMOVED*** = field(default_factory=list)
    resources: List[Any***REMOVED*** = field(default_factory=list)
    connected_at: float = 0.0
    last_ping: float = 0.0
    error: Optional[str***REMOVED*** = None
    connection_params: Dict[str, Any***REMOVED*** = field(default_factory=dict)


class BridgeLayer:
    """Универсальный мост между MCP и ACP.

    Bridge Layer регистрируется в ACP как агент со своими возможностями,
    подключается к внешним MCP серверам и транслирует запросы между протоколами.

    MCP → ACP:
      При вызове инструмента MCP сервера через ACP, Bridge Layer
      перенаправляет вызов на соответствующий MCP сервер и возвращает результат.

    ACP → MCP:
      MCP инструменты автоматически регистрируются как ACP возможности
      агента "buffy-bridge".
    """

    def __init__(
        self,
        event_bus: Any,
        agent_name: str = "buffy-bridge",
        agent_version: str = "1.0.0",
    ):
        self._agent_name = agent_name
        self._agent_version = agent_version
        self._bus = event_bus

        # ACP components
        self._registry = AgentRegistry()
        self._acp = ACPHandler(
            event_bus=event_bus,
            registry=self._registry,
            agent_name=agent_name,
            agent_version=agent_version,
        )

        # MCP connections
        self._mcp_servers: Dict[str, BridgeMCPServer***REMOVED*** = {***REMOVED***
        self._mcp_lock = threading.Lock()

        # Sync thread
        self._sync_thread: Optional[threading.Thread***REMOVED*** = None
        self._running = False

        # Register local capabilities
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Регистрирует возможности Bridge Layer в ACP."""
        self._acp.register_capability(
            "bridge.list_servers",
            "Список подключённых MCP серверов и их инструментов",
        )
        self._acp.register_capability(
            "bridge.connect_stdio",
            "Подключить MCP сервер через stdio",
        )
        self._acp.register_capability(
            "bridge.connect_http",
            "Подключить MCP сервер через HTTP",
        )
        self._acp.register_capability(
            "bridge.disconnect",
            "Отключить MCP сервер",
        )
        self._acp.register_capability(
            "bridge.rpc",
            "Выполнить произвольный JSON-RPC запрос к MCP серверу",
        )
        self._acp.register_capability(
            "bridge.forward",
            "Перенаправить ACP задачу на MCP сервер",
        )

        # Register tool handlers via decorator
        @self._acp.on_tool("bridge.list_servers")
        def _handle_list_servers(args: dict) -> dict:
            return self._list_servers_json()

        @self._acp.on_tool("bridge.connect_stdio")
        def _handle_connect_stdio(args: dict) -> dict:
            command = args.get("command", "")
            tool_args = args.get("args", [***REMOVED***)
            name = args.get("name", command)
            return self.connect_mcp_stdio(command, tool_args, name=name)

        @self._acp.on_tool("bridge.connect_http")
        def _handle_connect_http(args: dict) -> dict:
            endpoint = args.get("endpoint", "")
            name = args.get("name", "http-mcp")
            return self.connect_mcp_http(endpoint, name=name)

        @self._acp.on_tool("bridge.disconnect")
        def _handle_disconnect(args: dict) -> dict:
            name = args.get("name", "")
            success = self.disconnect_mcp(name)
            return {"success": success***REMOVED***

        @self._acp.on_tool("bridge.rpc")
        def _handle_rpc(args: dict) -> dict:
            server_name = args.get("server", "")
            method = args.get("method", "")
            params = args.get("params", {***REMOVED***)
            return self._rpc_to_server(server_name, method, params)

        @self._acp.on_tool("bridge.forward")
        def _handle_forward(args: dict) -> dict:
            target = args.get("target", "")
            tool = args.get("tool", "")
            arguments = args.get("arguments", {***REMOVED***)
            return self._forward_to_mcp(target, tool, arguments)

    # ── Lifecycle ────────────────────────────────────────────

    def start(self) -> None:
        """Запускает Bridge Layer: ACP handler + sync thread."""
        if self._running:
            return
        self._running = True

        # Запускаем ACP handler
        self._acp.start()

        # Sync thread — пингует MCP серверы и синхронизирует инструменты
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name=f"bridge-sync-{self._agent_name***REMOVED***",
        )
        self._sync_thread.start()

        print(f"🔗 Bridge Layer '{self._agent_name***REMOVED***' started")

    def stop(self) -> None:
        """Останавливает Bridge Layer."""
        if not self._running:
            return
        self._running = False

        # Отключаем все MCP серверы
        with self._mcp_lock:
            for name in list(self._mcp_servers.keys()):
                self.disconnect_mcp(name)

        # Останавливаем ACP
        self._acp.stop()

        print(f"🔗 Bridge Layer '{self._agent_name***REMOVED***' stopped")

    # ── MCP Connection Management ────────────────────────────

    def connect_mcp_stdio(
        self,
        command: str,
        args: List[str***REMOVED*** = None,
        cwd: Optional[str***REMOVED*** = None,
        name: Optional[str***REMOVED*** = None,
    ) -> Dict[str, Any***REMOVED***:
        """Подключает MCP сервер через stdio транспорт.

        Args:
            command: команда для запуска (например, "python")
            args: аргументы (например, ["scripts_01/mcp_server.py"***REMOVED***)
            cwd: рабочая директория
            name: имя для сервера (по умолчанию command + args)

        Returns:
            dict с результатом подключения
        """
        server_name = name or (f"{command***REMOVED*** {' '.join(args)***REMOVED***" if args else command)

        # Проверяем, не подключён ли уже
        if server_name in self._mcp_servers:
            return {"success": True, "message": f"Already connected: {server_name***REMOVED***"***REMOVED***

        client = StdioMCPClient(
            command=command,
            args=args or [***REMOVED***,
            cwd=cwd,
            name=server_name,
        )

        try:
            ok = client.connect()
            if not ok:
                return {"success": False, "error": f"Failed to connect: {server_name***REMOVED***"***REMOVED***

            # Получаем список инструментов
            tools = client.list_tools()
            resources = client.list_resources()

            entry = BridgeMCPServer(
                name=server_name,
                client=client,
                type="stdio",
                tools=tools,
                resources=resources,
                connected_at=time.time(),
                last_ping=time.time(),
                connection_params={
                    "command": command,
                    "args": args or [***REMOVED***,
                    "cwd": cwd,
                ***REMOVED***,
            )

            with self._mcp_lock:
                self._mcp_servers[server_name***REMOVED*** = entry

            # Регистрируем инструменты MCP сервера как ACP возможности
            for tool in tools:
                desc = f"[MCP:{server_name***REMOVED******REMOVED*** {tool.description***REMOVED***"
                self._acp.register_capability(f"mcp.{server_name***REMOVED***.{tool.name***REMOVED***", desc)

            return {
                "success": True,
                "server": server_name,
                "tools": len(tools),
                "resources": len(resources),
                "tool_names": [t.name for t in tools***REMOVED***,
            ***REMOVED***

        except Exception as e:
            client.disconnect()
            return {"success": False, "error": str(e)***REMOVED***

    def connect_mcp_http(
        self,
        endpoint: str,
        name: Optional[str***REMOVED*** = None,
    ) -> Dict[str, Any***REMOVED***:
        """Подключает MCP сервер через HTTP транспорт.

        Args:
            endpoint: URL эндпоинта (например, "http://127.0.0.1:8765/mcp")
            name: имя для сервера

        Returns:
            dict с результатом подключения
        """
        server_name = name or f"http-mcp-{endpoint***REMOVED***"

        if server_name in self._mcp_servers:
            return {"success": True, "message": f"Already connected: {server_name***REMOVED***"***REMOVED***

        client = HTTPMCPClient(endpoint=endpoint, name=server_name)

        try:
            ok = client.connect()
            if not ok:
                return {"success": False, "error": f"Failed to connect: {endpoint***REMOVED***"***REMOVED***

            tools = client.list_tools()
            resources = client.list_resources()

            entry = BridgeMCPServer(
                name=server_name,
                client=client,
                type="http",
                tools=tools,
                resources=resources,
                connected_at=time.time(),
                last_ping=time.time(),
                connection_params={
                    "endpoint": endpoint,
                ***REMOVED***,
            )

            with self._mcp_lock:
                self._mcp_servers[server_name***REMOVED*** = entry

            for tool in tools:
                desc = f"[MCP:{server_name***REMOVED******REMOVED*** {tool.description***REMOVED***"
                self._acp.register_capability(f"mcp.{server_name***REMOVED***.{tool.name***REMOVED***", desc)

            return {
                "success": True,
                "server": server_name,
                "tools": len(tools),
                "resources": len(resources),
                "tool_names": [t.name for t in tools***REMOVED***,
            ***REMOVED***

        except Exception as e:
            client.disconnect()
            return {"success": False, "error": str(e)***REMOVED***

    def disconnect_mcp(self, name: str) -> bool:
        """Отключает MCP сервер.

        Args:
            name: имя сервера

        Returns:
            True если успешно
        """
        with self._mcp_lock:
            entry = self._mcp_servers.pop(name, None)
            if entry is None:
                return False

            # Удаляем ACP возможности этого сервера
            prefix = f"mcp.{name***REMOVED***."
            for tool_name in list(self._acp._capabilities.keys()):
                if tool_name.startswith(prefix):
                    self._acp.remove_capability(tool_name)

            entry.client.disconnect()
            return True

    def list_mcp_servers(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список подключённых MCP серверов."""
        with self._mcp_lock:
            servers = [
                {
                    "name": s.name,
                    "type": s.type,
                    "tools": len(s.tools),
                    "tool_names": [t.name for t in s.tools***REMOVED***,
                    "connected": s.connected_at,
                    "error": s.error,
                ***REMOVED***
                for s in self._mcp_servers.values()
            ***REMOVED***
        return servers

    def _list_servers_json(self) -> dict:
        """Возвращает JSON-совместимый список серверов."""
        return {
            "servers": self.list_mcp_servers(),
            "total": len(self._mcp_servers),
        ***REMOVED***

    # ── MCP ↔ ACP Translation ───────────────────────────────

    def _forward_to_mcp(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any***REMOVED***,
    ) -> Dict[str, Any***REMOVED***:
        """Перенаправляет вызов на MCP сервер.

        Args:
            server_name: имя MCP сервера
            tool_name: название инструмента
            arguments: аргументы

        Returns:
            результат вызова
        """
        with self._mcp_lock:
            server = self._mcp_servers.get(server_name)

        if server is None:
            return {"success": False, "error": f"MCP server not found: {server_name***REMOVED***"***REMOVED***

        result = server.client.call_tool(tool_name, arguments)

        # Парсим content
        content_data = None
        for c in result.content:
            if c.get("type") == "text":
                try:
                    content_data = json.loads(c.get("text", "{***REMOVED***"))
                except (json.JSONDecodeError, TypeError):
                    content_data = c.get("text")

        return {
            "success": result.success,
            "data": content_data or result.data,
            "error": result.error,
            "content": result.content,
        ***REMOVED***

    def _rpc_to_server(
        self,
        server_name: str,
        method: str,
        params: Dict[str, Any***REMOVED***,
    ) -> Dict[str, Any***REMOVED***:
        """Выполняет произвольный JSON-RPC запрос к MCP серверу."""
        with self._mcp_lock:
            server = self._mcp_servers.get(server_name)

        if server is None:
            return {"success": False, "error": f"MCP server not found: {server_name***REMOVED***"***REMOVED***

        try:
            # Пробуем через стандартные методы
            if method == "tools/list":
                tools = server.client.list_tools()
                return {"success": True, "data": [{"name": t.name, "description": t.description***REMOVED*** for t in tools***REMOVED******REMOVED***
            elif method == "resources/list":
                resources = server.client.list_resources()
                return {"success": True, "data": [{"uri": r.uri, "name": r.name***REMOVED*** for r in resources***REMOVED******REMOVED***
            elif method == "tools/call":
                return self._forward_to_mcp(server_name, params.get("name", ""), params.get("arguments", {***REMOVED***))
            elif method == "ping":
                ok = server.client.ping()
                return {"success": ok, "data": {"alive": ok***REMOVED******REMOVED***
            else:
                return {"success": False, "error": f"Unknown method: {method***REMOVED***"***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def _handle_acp_task_on_mcp(self, task: ACPTask) -> Optional[ACPResult***REMOVED***:
        """Обрабатывает ACP задачу, перенаправляя её на MCP сервер.

        Вызывается из ACP handler, когда задача адресована MCP серверу.
        """
        # Парсим имя сервера из tool: mcp.{server***REMOVED***.{tool***REMOVED***
        tool_parts = task.tool.split(".")
        if len(tool_parts) < 3 or tool_parts[0***REMOVED*** != "mcp":
            return None  # Не MCP задача

        server_name = tool_parts[1***REMOVED***
        mcp_tool = ".".join(tool_parts[2:***REMOVED***)

        import time
        t0 = time.time()

        result = self._forward_to_mcp(server_name, mcp_tool, task.arguments)
        duration_ms = (time.time() - t0) * 1000

        return ACPResult(
            task_id=task.task_id,
            source=self._agent_name,
            target=task.source,
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            duration_ms=round(duration_ms, 1),
            correlation_id=task.correlation_id,
        )

    # ── Sync Loop ────────────────────────────────────────────

    def _sync_loop(self) -> None:
        """Периодически пингует MCP серверы и синхронизирует инструменты."""
        while self._running:
            time.sleep(60)  # каждую минуту

            if not self._running:
                break

            try:
                with self._mcp_lock:
                    server_names = list(self._mcp_servers.keys())

                for server_name in server_names:
                    try:
                        with self._mcp_lock:
                            server = self._mcp_servers.get(server_name)
                        if server is None:
                            continue

                        # Ping
                        alive = server.client.ping()
                        if alive:
                            server.last_ping = time.time()
                            server.error = None
                        else:
                            server.error = "ping failed"
                            # Пробуем переподключиться
                            self._reconnect_mcp(server_name)
                    except Exception as e:
                        with self._mcp_lock:
                            if server_name in self._mcp_servers:
                                self._mcp_servers[server_name***REMOVED***.error = str(e)

                # Prune offline ACP агентов
                pruned = self._registry.prune_offline(max_age_seconds=300.0)
                if pruned:
                    print(f"🔗 Bridge: pruned {pruned***REMOVED*** offline agents")

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️ Bridge sync error: {e***REMOVED***", file=sys.__stdout__)

    def _reconnect_mcp(self, server_name: str) -> bool:
        """Переподключает MCP сервер используя сохранённые connection_params."""
        with self._mcp_lock:
            server = self._mcp_servers.get(server_name)
            if server is None:
                return False

            old_client = server.client
            params = server.connection_params

            # Создаём новый клиент того же типа из сохранённых параметров
            try:
                if server.type == "stdio":
                    new_client = StdioMCPClient(
                        command=params.get("command", ""),
                        args=params.get("args", [***REMOVED***),
                        cwd=params.get("cwd"),
                        name=server_name,
                    )
                elif server.type == "http":
                    new_client = HTTPMCPClient(
                        endpoint=params.get("endpoint", ""),
                        name=server_name,
                    )
                else:
                    server.error = "unknown client type"
                    return False

                ok = new_client.connect()
                if not ok:
                    server.error = "reconnect failed"
                    return False

                # Обновляем
                server.client = new_client
                server.tools = new_client.list_tools()
                server.error = None
                server.last_ping = time.time()

                # Пытаемся отключить старый
                try:
                    old_client.disconnect()
                except Exception:
                    pass

                return True
            except Exception as e:
                server.error = f"reconnect error: {e***REMOVED***"
                return False

    # ── ACP Integration ──────────────────────────────────────

    def register_acp_tool_handler(self, tool_name: str, handler) -> None:
        """Регистрирует дополнительный ACP обработчик инструмента.

        Позволяет расширять Bridge Layer новыми возможностями.
        """
        self._acp.register_capability(tool_name, handler.__doc__ or tool_name)
        # Используем декоратор
        decorator = self._acp.on_tool(tool_name)
        decorator(handler)

    def send_acp_broadcast(self, message: str, data: Dict[str, Any***REMOVED*** = None) -> None:
        """Отправляет ACP broadcast."""
        self._acp.send_broadcast(message, data)

    def send_acp_task(
        self,
        target: str,
        tool: str,
        arguments: Dict[str, Any***REMOVED***,
        timeout: float = 60.0,
    ) -> Optional[ACPResult***REMOVED***:
        """Отправляет ACP задачу агенту.

        Если агент — MCP сервер, задача автоматически перенаправляется.
        """
        return self._acp.send_task(target, tool, arguments, timeout=timeout)

    @property
    def acp_handler(self) -> ACPHandler:
        """ACP handler для прямого доступа."""
        return self._acp

    @property
    def agent_registry(self) -> AgentRegistry:
        """Реестр ACP агентов."""
        return self._registry

    @property
    def is_running(self) -> bool:
        return self._running
