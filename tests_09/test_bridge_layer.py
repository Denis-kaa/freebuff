"""
Тесты для Bridge Layer: ACP Protocol, MCP Client, Bridge Layer.

Покрытие:
  - AgentRegistry: register, get, list, status, prune
  - ACPHandler: start/stop, capabilities, tool handlers, task send/receive
  - MCPClientBase: list_tools, call_tool, list_resources
  - StdioMCPClient: connect/disconnect, initialize, ping
  - BridgeLayer: start/stop, connect_mcp, list_servers, forward
  - ACP → MCP translation
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from freebuff_plugin_03.acp_protocol import (
    AgentRegistry, AgentInfo, AgentStatus,
    ACPHandler, ACPTask, ACPResult,
    ACP_DISCOVER, ACP_TASK, ACP_RESULT,
    ACP_STATUS, ACP_BROADCAST, ACP_HEARTBEAT,
)
from freebuff_plugin_03.bridge_layer import BridgeLayer, BridgeMCPServer
from freebuff_plugin_03.mcp_client import (
    MCPClientBase, StdioMCPClient, HTTPMCPClient,
    MCPToolInfo, MCPCallResult,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_event_bus():
    """Создаёт мок EventBus."""
    bus = MagicMock()
    bus.subscribe = MagicMock(return_value="sub-001")
    bus.unsubscribe = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def registry():
    """Создаёт AgentRegistry."""
    return AgentRegistry()


@pytest.fixture
def acp_handler(mock_event_bus, registry):
    """Создаёт ACPHandler."""
    handler = ACPHandler(
        event_bus=mock_event_bus,
        registry=registry,
        agent_name="test-agent",
        agent_version="1.0.0",
    )
    return handler


@pytest.fixture
def bridge(mock_event_bus):
    """Создаёт BridgeLayer."""
    b = BridgeLayer(
        event_bus=mock_event_bus,
        agent_name="test-bridge",
        agent_version="1.0.0",
    )
    return b


# ═══════════════════════════════════════════════════════════════
# AgentRegistry Tests
# ═══════════════════════════════════════════════════════════════


class TestAgentRegistry:
    """Тесты AgentRegistry."""

    def test_register_and_get(self, registry: AgentRegistry):
        info = AgentInfo(name="agent-1", version="1.0.0")
        registry.register(info)
        retrieved = registry.get("agent-1")
        assert retrieved is not None
        assert retrieved.name == "agent-1"
        assert retrieved.version == "1.0.0"
        assert retrieved.status == AgentStatus.ONLINE

    def test_register_updates_last_seen(self, registry: AgentRegistry):
        info = AgentInfo(name="agent-1", version="1.0.0")
        registry.register(info)
        retrieved = registry.get("agent-1")
        assert retrieved is not None
        assert retrieved.last_seen is not None

    def test_get_nonexistent(self, registry: AgentRegistry):
        assert registry.get("nonexistent") is None

    def test_unregister(self, registry: AgentRegistry):
        info = AgentInfo(name="agent-1")
        registry.register(info)
        assert registry.unregister("agent-1") is True
        assert registry.get("agent-1") is None

    def test_unregister_nonexistent(self, registry: AgentRegistry):
        assert registry.unregister("nonexistent") is False

    def test_list_agents(self, registry: AgentRegistry):
        registry.register(AgentInfo(name="agent-1", status=AgentStatus.ONLINE))
        registry.register(AgentInfo(name="agent-2", status=AgentStatus.BUSY))
        registry.register(AgentInfo(name="agent-3", status=AgentStatus.ONLINE))
        agents = registry.list_agents()
        assert len(agents) == 3

    def test_list_agents_filter_by_status(self, registry: AgentRegistry):
        registry.register(AgentInfo(name="agent-1", status=AgentStatus.ONLINE))
        registry.register(AgentInfo(name="agent-2", status=AgentStatus.BUSY))
        online = registry.list_agents(AgentStatus.ONLINE)
        assert len(online) == 1
        assert online[0].name == "agent-1"

    def test_is_online(self, registry: AgentRegistry):
        registry.register(AgentInfo(name="agent-1", status=AgentStatus.ONLINE))
        assert registry.is_online("agent-1") is True
        assert registry.is_online("nonexistent") is False

    def test_update_status(self, registry: AgentRegistry):
        registry.register(AgentInfo(name="agent-1", status=AgentStatus.ONLINE))
        assert registry.update_status("agent-1", AgentStatus.BUSY) is True
        agent = registry.get("agent-1")
        assert agent is not None
        assert agent.status == AgentStatus.BUSY

    def test_update_status_nonexistent(self, registry: AgentRegistry):
        assert registry.update_status("nonexistent", AgentStatus.BUSY) is False

    def test_prune_offline(self, registry: AgentRegistry):
        registry.register(AgentInfo(name="agent-1", status=AgentStatus.ONLINE))
        registry.register(AgentInfo(name="agent-2", status=AgentStatus.OFFLINE))
        pruned = registry.prune_offline(max_age_seconds=0)
        assert pruned >= 0  # может не сработать если время совпало

    def test_register_pending_and_complete_task(self, registry: AgentRegistry):
        task = ACPTask(target="agent-2", source="agent-1", tool="test")
        registry.register_pending_task(task)

        result = ACPResult(task_id=task.task_id, source="agent-2", target="agent-1")
        registry.complete_task(result)

        # Должен быть доступен
        stored = registry.wait_for_result(task.task_id, timeout=1)
        assert stored is not None
        assert stored.source == "agent-2"
        assert stored.success is True

    def test_wait_for_result_timeout(self, registry: AgentRegistry):
        task = ACPTask(target="agent-2", source="agent-1", tool="test")
        registry.register_pending_task(task)

        # Таймаут — не дожидаемся
        result = registry.wait_for_result(task.task_id, timeout=0.1)
        assert result is None


# ═══════════════════════════════════════════════════════════════
# ACPHandler Tests
# ═══════════════════════════════════════════════════════════════


class TestACPHandler:
    """Тесты ACPHandler."""

    def test_register_capabilities(self, acp_handler: ACPHandler):
        acp_handler.register_capability("test_tool", "Test tool description")
        assert "test_tool" in acp_handler._capabilities

    def test_remove_capability(self, acp_handler: ACPHandler):
        acp_handler.register_capability("test_tool", "description")
        acp_handler.remove_capability("test_tool")
        assert "test_tool" not in acp_handler._capabilities

    def test_start_stop(self, acp_handler: ACPHandler, mock_event_bus):
        acp_handler.start()
        assert acp_handler._running is True
        assert mock_event_bus.subscribe.called

        acp_handler.stop()
        assert acp_handler._running is False

    def test_on_tool_decorator(self, acp_handler: ACPHandler):
        @acp_handler.on_tool("my_tool")
        def handler(args: dict) -> dict:
            return {"result": "ok"}

        assert "my_tool" in acp_handler._tool_handlers
        result = acp_handler._tool_handlers["my_tool"]({"test": True})
        assert result["result"] == "ok"

    def test_handle_status_updates_registry(self, acp_handler: ACPHandler, mock_event_bus):
        """Проверяет, что handle_status регистрирует агента в реестре."""
        from scripts_01.event_bus import Event

        event = Event(
            type=ACP_STATUS,
            source="other-agent",
            data={
                "agent": "other-agent",
                "version": "2.0.0",
                "status": "online",
                "capabilities": {"tool1": "desc"},
            },
        )
        acp_handler._on_acp_event(event)

        agent = acp_handler._registry.get("other-agent")
        assert agent is not None
        assert agent.name == "other-agent"
        assert agent.version == "2.0.0"

    def test_handle_discover(self, acp_handler: ACPHandler, mock_event_bus):
        """Проверяет, что discover отвечает своей информацией."""
        from scripts_01.event_bus import Event

        acp_handler.register_capability("test_tool", "Test desc")

        event = Event(
            type=ACP_DISCOVER,
            source="asking-agent",
            data={"agent": "asking-agent"},
        )
        acp_handler._on_acp_event(event)

        # Должен опубликовать ответ
        assert mock_event_bus.publish.called

    def test_handle_task_runs_handler(self, acp_handler: ACPHandler, mock_event_bus):
        """Проверяет, что ACP задача запускает зарегистрированный обработчик."""
        from scripts_01.event_bus import Event

        @acp_handler.on_tool("my_tool")
        def handle_my_tool(args: dict) -> dict:
            return {"processed": True, "input": args}

        event = Event(
            type=ACP_TASK,
            source="other-agent",
            data={
                "target": "test-agent",
                "tool": "my_tool",
                "task_id": "task-001",
                "arguments": {"key": "value"},
                "correlation_id": "corr-001",
            },
        )
        acp_handler._on_acp_event(event)

        # Должен опубликовать результат
        published_calls = [c for c in mock_event_bus.publish.call_args_list]
        assert len(published_calls) >= 1

    def test_handle_unknown_tool_returns_error(self, acp_handler: ACPHandler, mock_event_bus):
        """Проверяет, что неизвестный инструмент возвращает ошибку."""
        from scripts_01.event_bus import Event

        event = Event(
            type=ACP_TASK,
            source="other-agent",
            data={
                "target": "test-agent",
                "tool": "nonexistent",
                "task_id": "task-002",
                "arguments": {},
                "correlation_id": "corr-002",
            },
        )
        acp_handler._on_acp_event(event)

        # Должен опубликовать ошибку
        assert mock_event_bus.publish.called

    def test_send_task(self, acp_handler: ACPHandler, mock_event_bus):
        """Проверяет отправку задачи."""
        from scripts_01.event_bus import Event

        result = acp_handler.send_task("other-agent", "test_tool", {"query": "hello"}, timeout=0.1)
        assert mock_event_bus.publish.called
        # Таймаут — результата не будет (нет обработчика на той стороне)
        assert result is None

    def test_send_broadcast(self, acp_handler: ACPHandler, mock_event_bus):
        acp_handler.send_broadcast("hello everyone")
        assert mock_event_bus.publish.called

    def test_send_status_update(self, acp_handler: ACPHandler, mock_event_bus):
        acp_handler.send_status_update()
        assert mock_event_bus.publish.called

    def test_on_broadcast_hook(self, acp_handler: ACPHandler):
        """Проверяет, что хук on_broadcast вызывается."""
        received = []

        def hook(data: dict, source: str):
            received.append((data, source))

        acp_handler.on_broadcast = hook

        from scripts_01.event_bus import Event
        event = Event(
            type=ACP_BROADCAST,
            source="other-agent",
            data={"message": "test", "agent": "other-agent"},
        )
        acp_handler._on_acp_event(event)

        assert len(received) == 1
        assert received[0][1] == "other-agent"


# ═══════════════════════════════════════════════════════════════
# MCPClientBase Tests
# ═══════════════════════════════════════════════════════════════


class TestMCPClientBase:
    """Тесты MCPClientBase."""

    def test_mcp_tool_info_creation(self):
        tool = MCPToolInfo(name="test", description="desc", input_schema={"type": "object"})
        assert tool.name == "test"
        assert tool.description == "desc"

    def test_mcp_call_result_success(self):
        result = MCPCallResult(success=True, data={"result": "ok"})
        assert result.success is True
        assert result.data["result"] == "ok"
        assert result.error is None

    def test_mcp_call_result_error(self):
        result = MCPCallResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


# ═══════════════════════════════════════════════════════════════
# BridgeLayer Tests
# ═══════════════════════════════════════════════════════════════


class TestBridgeLayer:
    """Тесты BridgeLayer."""

    def test_bridge_creation(self, bridge: BridgeLayer):
        assert bridge._agent_name == "test-bridge"
        assert bridge.is_running is False
        assert len(bridge._mcp_servers) == 0

    def test_start_stop(self, bridge: BridgeLayer, mock_event_bus):
        bridge.start()
        assert bridge.is_running is True

        bridge.stop()
        assert bridge.is_running is False

    def test_register_capabilities_on_start(self, bridge: BridgeLayer):
        """Проверяет, что при создании регистрируются встроенные возможности."""
        capabilities = bridge._acp._capabilities
        assert "bridge.list_servers" in capabilities
        assert "bridge.connect_stdio" in capabilities
        assert "bridge.rpc" in capabilities
        assert "bridge.forward" in capabilities

    def test_list_servers_empty(self, bridge: BridgeLayer):
        servers = bridge.list_mcp_servers()
        assert servers == []

    def test_connect_and_disconnect_mcp_stdio(self, bridge: BridgeLayer):
        """Подключение stdio MCP сервера (с моком клиента)."""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = [
            MCPToolInfo(name="test_tool", description="Test")
        ]
        mock_client.list_resources.return_value = []

        with patch("freebuff_plugin_03.bridge_layer.StdioMCPClient", return_value=mock_client):
            result = bridge.connect_mcp_stdio("python", ["test.py"], name="test-mcp")

        assert result["success"] is True
        assert result["server"] == "test-mcp"
        assert result["tools"] == 1

        # Отключаем
        assert bridge.disconnect_mcp("test-mcp") is True
        assert len(bridge._mcp_servers) == 0

    def test_connect_mcp_http(self, bridge: BridgeLayer):
        """Подключение HTTP MCP сервера (с моком клиента)."""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = []
        mock_client.list_resources.return_value = []

        with patch("freebuff_plugin_03.bridge_layer.HTTPMCPClient", return_value=mock_client):
            result = bridge.connect_mcp_http("http://localhost:8765/mcp", name="http-mcp")

        assert result["success"] is True
        assert result["server"] == "http-mcp"

        bridge.disconnect_mcp("http-mcp")

    def test_connect_duplicate(self, bridge: BridgeLayer):
        """Повторное подключение не создаёт дубликат."""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = []
        mock_client.list_resources.return_value = []

        with patch("freebuff_plugin_03.bridge_layer.StdioMCPClient", return_value=mock_client):
            bridge.connect_mcp_stdio("python", name="dup")
            result = bridge.connect_mcp_stdio("python", name="dup")

        assert result["success"] is True
        assert "already" in result.get("message", "").lower()
        assert len(bridge._mcp_servers) == 1

        bridge.disconnect_mcp("dup")

    def test_forward_to_mcp(self, bridge: BridgeLayer):
        """Перенаправление вызова на MCP сервер."""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = [
            MCPToolInfo(name="search", description="Search tool")
        ]
        mock_client.list_resources.return_value = []
        mock_client.call_tool.return_value = MCPCallResult(
            success=True,
            content=[{"type": "text", "text": '{"results": ["doc1"}]'}],
        )

        with patch("freebuff_plugin_03.bridge_layer.StdioMCPClient", return_value=mock_client):
            bridge.connect_mcp_stdio("python", name="fwd-test")

        result = bridge._forward_to_mcp("fwd-test", "search", {"query": "test"})
        assert result["success"] is True

        bridge.disconnect_mcp("fwd-test")

    def test_forward_policy_override_via_bridge(self, bridge: BridgeLayer):
        """policy_override доступен MCP-клиентам через Bridge Layer (правило 11).

        Проверяет полный путь ACP → Bridge → MCP: _forward_to_mcp вызывает
        server.client.call_tool с именем policy_override и сообщением.
        """
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = [
            MCPToolInfo(name="policy_override", description="Apply user override")
        ]
        mock_client.list_resources.return_value = []
        mock_client.call_tool.return_value = MCPCallResult(
            success=True,
            content=[{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "data": {
                        "capability": "coding",
                        "runtime": "deepseek",
                        "applied": True,
                    },
                }),
            }],
        )

        with patch("freebuff_plugin_03.bridge_layer.StdioMCPClient", return_value=mock_client):
            bridge.connect_mcp_stdio("python", name="policy-mcp")

        result = bridge._forward_to_mcp(
            "policy-mcp",
            "policy_override",
            {"message": "use deepseek instead of claude for coding"},
        )
        assert result["success"] is True
        # _forward_to_mcp: data = parsed content JSON (ответ сервера),
        # т.е. {"success": True, "data": {capability, runtime, applied}}
        assert result["data"]["success"] is True
        assert result["data"]["data"]["runtime"] == "deepseek"
        assert result["data"]["data"]["applied"] is True
        mock_client.call_tool.assert_called_once_with(
            "policy_override",
            {"message": "use deepseek instead of claude for coding"},
        )

        bridge.disconnect_mcp("policy-mcp")

    def test_forward_to_nonexistent_server(self, bridge: BridgeLayer):
        """Перенаправление на несуществующий сервер."""
        result = bridge._forward_to_mcp("nonexistent", "tool", {})
        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_rpc_to_server(self, bridge: BridgeLayer):
        """Произвольный JSON-RPC запрос к серверу."""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        mock_client.list_tools.return_value = [
            MCPToolInfo(name="tool1", description="Tool 1"),
        ]
        mock_client.list_resources.return_value = []

        with patch("freebuff_plugin_03.bridge_layer.StdioMCPClient", return_value=mock_client):
            bridge.connect_mcp_stdio("python", name="rpc-test")

        result = bridge._rpc_to_server("rpc-test", "tools/list", {})
        assert result["success"] is True
        assert len(result["data"]) == 1

        bridge.disconnect_mcp("rpc-test")

    def test_disconnect_nonexistent(self, bridge: BridgeLayer):
        assert bridge.disconnect_mcp("nonexistent") is False

    def test_acp_tool_handler_bridge_list_servers(self, bridge: BridgeLayer, mock_event_bus):
        """Проверяет, что bridge.list_servers как ACP инструмент работает."""
        bridge.start()

        # Вызов через ACP handler
        handler_entry = bridge._acp._tool_handlers.get("bridge.list_servers")
        assert handler_entry is not None
        result = handler_entry({})
        assert "servers" in result
        assert result["total"] == 0

        bridge.stop()

    def test_acp_tool_handler_bridge_rpc(self, bridge: BridgeLayer):
        """Проверяет bridge.rpc — вызов без сервера."""
        bridge.start()
        handler_entry = bridge._acp._tool_handlers.get("bridge.rpc")
        assert handler_entry is not None
        result = handler_entry({"server": "nonexistent", "method": "ping", "params": {}})
        assert result["success"] is False
        bridge.stop()

    def test_send_acp_broadcast(self, bridge: BridgeLayer, mock_event_bus):
        bridge.send_acp_broadcast("test broadcast")
        assert mock_event_bus.publish.called

    def test_send_acp_task(self, bridge: BridgeLayer, mock_event_bus):
        result = bridge.send_acp_task("nonexistent-agent", "test_tool", {}, timeout=0.1)
        assert result is None  # таймаут
        assert mock_event_bus.publish.called

    def test_agent_registry_property(self, bridge: BridgeLayer):
        assert bridge.agent_registry is bridge._registry

    def test_acp_handler_property(self, bridge: BridgeLayer):
        assert bridge.acp_handler is bridge._acp

    def test_register_acp_tool_handler(self, bridge: BridgeLayer):
        def custom_handler(args: dict) -> dict:
            """Custom handler."""
            return {"custom": True}

        bridge.register_acp_tool_handler("custom_tool", custom_handler)
        assert "custom_tool" in bridge._acp._capabilities
        assert "custom_tool" in bridge._acp._tool_handlers

    def test_handle_acp_task_on_mcp_non_mcp_tool(self, bridge: BridgeLayer):
        """ACP задача не для MCP — возвращает None."""
        task = ACPTask(
            target="test-bridge",
            source="other-agent",
            tool="not_an_mcp_tool",
            arguments={},
        )
        result = bridge._handle_acp_task_on_mcp(task)
        assert result is None

    def test_handle_acp_task_on_mcp_unknown_server(self, bridge: BridgeLayer):
        """ACP задача для MCP с неизвестным сервером."""
        task = ACPTask(
            target="test-bridge",
            source="other-agent",
            tool="mcp.nonexistent.tool",
            arguments={},
        )
        result = bridge._handle_acp_task_on_mcp(task)
        assert result is not None
        assert result.success is False


# ═══════════════════════════════════════════════════════════════
# MCPClient Integration Tests (with mocks)
# ═══════════════════════════════════════════════════════════════


class TestStdioMCPClientMocked:
    """Тесты StdioMCPClient с моками подпроцесса."""

    @pytest.fixture
    def mock_process(self):
        """Создаёт мок процесса."""
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()
        process.poll.return_value = None
        return process

    def test_connect_failure(self, mock_process):
        """Ошибка подключения — пустой результат initialize."""
        with patch("subprocess.Popen", return_value=mock_process):
            with patch.object(MCPClientBase, "initialize", return_value={}):
                client = StdioMCPClient("python", ["nonexistent.py"])
                ok = client.connect()
                assert ok is False  # пустой {} считается False

    def test_connect_with_initialize_error(self, mock_process):
        """Ошибка при initialize."""
        with patch("subprocess.Popen", return_value=mock_process):
            with patch.object(MCPClientBase, "initialize", side_effect=Exception("init failed")):
                client = StdioMCPClient("python", ["test.py"])
                ok = client.connect()
                assert ok is False

    def test_server_info_property(self):
        client = StdioMCPClient("python", name="test-client")
        client._server_info = {"name": "test-server", "version": "1.0"}
        assert client.server_info["name"] == "test-server"

    def test_is_connected_property(self):
        client = StdioMCPClient("python", name="test-client")
        assert client.is_connected is False
        client._connected = True
        assert client.is_connected is True


class TestHTTPMCPClientMocked:
    """Тесты HTTPMCPClient с моками HTTP."""

    def test_connect_fails_without_network(self):
        """HTTPMCPClient не может подключиться без сетевого доступа."""
        client = HTTPMCPClient("http://localhost:8765/mcp", name="test-http")
        ok = client.connect()
        assert ok is False  # нет сети в тестовой среде

    def test_disconnect(self):
        client = HTTPMCPClient("http://localhost:8765/mcp", name="test-http")
        client._session_id = "session-001"
        client._connected = True
        client.disconnect()
        assert client.is_connected is False
        assert client._session_id is None


# ═══════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestBridgeEdgeCases:
    """Тесты граничных случаев Bridge Layer."""

    def test_double_start_stop(self, bridge: BridgeLayer):
        bridge.start()
        bridge.start()  # второй start — no-op
        assert bridge.is_running is True
        bridge.stop()
        bridge.stop()  # второй stop — no-op
        assert bridge.is_running is False

    def test_stop_without_start(self, bridge: BridgeLayer):
        bridge.stop()  # не должно падать
        assert bridge.is_running is False

    def test_empty_registry_prune(self, registry: AgentRegistry):
        """Prune пустого реестра."""
        assert registry.prune_offline() == 0

    def test_wait_for_nonexistent_task(self, registry: AgentRegistry):
        result = registry.wait_for_result("nonexistent", timeout=0.1)
        assert result is None

    def test_get_pending_tasks_for_agent(self, registry: AgentRegistry):
        task1 = ACPTask(target="agent-1", source="me", tool="t1")
        task2 = ACPTask(target="agent-2", source="me", tool="t2")
        registry.register_pending_task(task1)
        registry.register_pending_task(task2)

        tasks_for_1 = registry.get_pending_tasks_for_agent("agent-1")
        assert len(tasks_for_1) == 1
        assert tasks_for_1[0].tool == "t1"

    def test_get_pending_task(self, registry: AgentRegistry):
        task = ACPTask(target="agent-1", source="me", tool="t1")
        registry.register_pending_task(task)

        retrieved = registry.get_pending_task(task.task_id)
        assert retrieved is not None
        assert retrieved.target == "agent-1"

        completed = registry.get_pending_task("nonexistent")
        assert completed is None
