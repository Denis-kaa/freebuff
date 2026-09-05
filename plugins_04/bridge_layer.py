"""Bridge Layer — ACP ↔ MCP translation layer.

Восстановлен v5.189.91 по контракту тестов tests_09/test_bridge_layer.py.

BridgeLayer связывает ACP (межагентное взаимодействие через EventBus)
с MCP (Model Context Protocol — инструменты AI-моделей).

Ключевые компоненты:
  - BridgeLayer: start/stop, connect/disconnect MCP servers, forward/rpc
  - BridgeMCPServer: обёртка над MCP-клиентом с метаданными
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from plugins_04.acp_protocol import ACPHandler, AgentRegistry
from plugins_04.mcp_client import (
    HTTPMCPClient,
    MCPClientBase,
    MCPCallResult,
    MCPToolInfo,
    StdioMCPClient,
)


class BridgeMCPServer:
    """Metadata wrapper for a connected MCP server."""

    def __init__(
        self,
        name: str,
        client: MCPClientBase,
        tools: List[MCPToolInfo],
        resources: List[Any],
    ) -> None:
        self.name = name
        self.client = client
        self.tools = tools
        self.resources = resources


class BridgeLayer:
    """ACP ↔ MCP bridge: connects MCP servers and forwards ACP tasks."""

    def __init__(
        self,
        event_bus: Any,
        agent_name: str = "bridge",
        agent_version: str = "1.0.0",
    ) -> None:
        self._event_bus = event_bus
        self._agent_name = agent_name
        self._agent_version = agent_version
        self._registry = AgentRegistry()
        self._acp = ACPHandler(
            event_bus=event_bus,
            registry=self._registry,
            agent_name=agent_name,
            agent_version=agent_version,
        )
        self._mcp_servers: Dict[str, BridgeMCPServer] = {}
        self._running = False

        # Register bridge capabilities
        self._acp.register_capability("bridge.list_servers", "List connected MCP servers")
        self._acp.register_capability("bridge.connect_stdio", "Connect to stdio MCP server")
        self._acp.register_capability("bridge.rpc", "Forward JSON-RPC to MCP server")
        self._acp.register_capability("bridge.forward", "Forward tool call to MCP server")

        # Register ACP tool handlers
        self._acp._tool_handlers["bridge.list_servers"] = self._handle_list_servers
        self._acp._tool_handlers["bridge.connect_stdio"] = self._handle_connect_stdio
        self._acp._tool_handlers["bridge.rpc"] = self._handle_rpc
        self._acp._tool_handlers["bridge.forward"] = self._handle_forward

    # ── Properties ──────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def agent_registry(self) -> AgentRegistry:
        return self._registry

    @property
    def acp_handler(self) -> ACPHandler:
        return self._acp

    # ── Lifecycle ───────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._acp.start()

    def stop(self) -> None:
        self._running = False
        self._acp.stop()

    # ── MCP server management ───────────────────────────────────

    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": srv.name,
                "tools": len(srv.tools),
                "resources": len(srv.resources),
            }
            for srv in self._mcp_servers.values()
        ]

    def connect_mcp_stdio(
        self,
        command: str,
        args: Optional[List[str]] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        server_name = name or command

        if server_name in self._mcp_servers:
            return {
                "success": True,
                "server": server_name,
                "message": f"Already connected: {server_name}",
                "tools": len(self._mcp_servers[server_name].tools),
            }

        client = StdioMCPClient(command, args, name=server_name)
        ok = client.connect()
        if not ok:
            return {"success": False, "error": f"Failed to connect to {server_name}"}

        tools = client.list_tools()
        resources = client.list_resources()
        self._mcp_servers[server_name] = BridgeMCPServer(
            name=server_name,
            client=client,
            tools=tools,
            resources=resources,
        )
        return {
            "success": True,
            "server": server_name,
            "tools": len(tools),
            "resources": len(resources),
        }

    def connect_mcp_http(
        self,
        url: str,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        server_name = name or url

        if server_name in self._mcp_servers:
            return {
                "success": True,
                "server": server_name,
                "message": f"Already connected: {server_name}",
                "tools": len(self._mcp_servers[server_name].tools),
            }

        client = HTTPMCPClient(url, name=server_name)
        ok = client.connect()
        if not ok:
            return {"success": False, "error": f"Failed to connect to {server_name}"}

        tools = client.list_tools()
        resources = client.list_resources()
        self._mcp_servers[server_name] = BridgeMCPServer(
            name=server_name,
            client=client,
            tools=tools,
            resources=resources,
        )
        return {
            "success": True,
            "server": server_name,
            "tools": len(tools),
            "resources": len(resources),
        }

    def disconnect_mcp(self, name: str) -> bool:
        srv = self._mcp_servers.pop(name, None)
        if srv is None:
            return False
        srv.client.disconnect()
        return True

    # ── Forwarding ──────────────────────────────────────────────

    def _forward_to_mcp(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        srv = self._mcp_servers.get(server_name)
        if srv is None:
            return {"success": False, "error": f"Server not found: {server_name}"}

        call_result: MCPCallResult = srv.client.call_tool(tool_name, arguments)

        if call_result.error:
            return {"success": False, "error": call_result.error}

        # Try to parse content as JSON
        data: Any = call_result.content
        if call_result.content and len(call_result.content) == 1:
            item = call_result.content[0]
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    import json
                    data = json.loads(item["text"])
                except (json.JSONDecodeError, KeyError):
                    data = call_result.content

        return {"success": True, "data": data}

    def _rpc_to_server(
        self,
        server_name: str,
        method: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        srv = self._mcp_servers.get(server_name)
        if srv is None:
            return {"success": False, "error": f"Server not found: {server_name}"}

        if method == "tools/list":
            tools = srv.client.list_tools()
            return {"success": True, "data": tools}
        elif method == "resources/list":
            resources = srv.client.list_resources()
            return {"success": True, "data": resources}
        elif method == "ping":
            return {"success": True, "data": "pong"}
        else:
            return {"success": False, "error": f"Unknown method: {method}"}

    def _handle_acp_task_on_mcp(self, task: Any) -> Optional[MCPCallResult]:
        """Try to handle an ACP task by forwarding to an MCP server.

        Tool naming convention: mcp.{server}.{tool}
        """
        tool = getattr(task, "tool", "")
        parts = tool.split(".", 2)
        if len(parts) < 3 or parts[0] != "mcp":
            return None

        server_name = parts[1]
        mcp_tool = parts[2]
        arguments = getattr(task, "arguments", {})

        srv = self._mcp_servers.get(server_name)
        if srv is None:
            return MCPCallResult(
                success=False,
                error=f"MCP server not found: {server_name}",
            )

        return srv.client.call_tool(mcp_tool, arguments)

    # ── ACP tool handlers ───────────────────────────────────────

    def _handle_list_servers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "servers": self.list_mcp_servers(),
            "total": len(self._mcp_servers),
        }

    def _handle_connect_stdio(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.connect_mcp_stdio(
            command=args.get("command", ""),
            args=args.get("args"),
            name=args.get("name"),
        )

    def _handle_rpc(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._rpc_to_server(
            server_name=args.get("server", ""),
            method=args.get("method", ""),
            params=args.get("params", {}),
        )

    def _handle_forward(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._forward_to_mcp(
            server_name=args.get("server", ""),
            tool_name=args.get("tool", ""),
            arguments=args.get("arguments", {}),
        )

    # ── Public ACP API ──────────────────────────────────────────

    def register_acp_tool_handler(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        self._acp.register_capability(name, handler.__doc__ or name)
        self._acp._tool_handlers[name] = handler

    def send_acp_broadcast(self, message: str) -> None:
        self._acp.send_broadcast(message)

    def send_acp_task(
        self,
        target: str,
        tool: str,
        arguments: Dict[str, Any],
        timeout: float = 5,
    ) -> Optional[Any]:
        return self._acp.send_task(target, tool, arguments, timeout=timeout)
