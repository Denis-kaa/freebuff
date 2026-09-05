"""ACP Protocol — Agent Communication Protocol.

Восстановлен v5.189.91 по контракту тестов tests_09/test_bridge_layer.py.

ACP — это протокол межагентного взаимодействия через EventBus.
AgentInfo/AgentRegistry хранят реестр агентов и pending-задач.
ACPHandler обрабатывает discover/task/result/status/broadcast/heartbeat.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Protocol constants
# ═══════════════════════════════════════════════════════════════

ACP_DISCOVER = "acp.discover"
ACP_TASK = "acp.task"
ACP_RESULT = "acp.result"
ACP_STATUS = "acp.status"
ACP_BROADCAST = "acp.broadcast"
ACP_HEARTBEAT = "acp.heartbeat"


# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    name: str
    version: str = ""
    status: AgentStatus = AgentStatus.ONLINE
    capabilities: Dict[str, str] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)


@dataclass
class ACPTask:
    """An ACP task request."""
    target: str
    source: str
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    correlation_id: str = field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")


@dataclass
class ACPResult:
    """Result of an ACP task execution."""
    task_id: str
    source: str
    target: str
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# AgentRegistry
# ═══════════════════════════════════════════════════════════════

class AgentRegistry:
    """Registry of known agents with pending task management."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentInfo] = {}
        self._pending_tasks: Dict[str, ACPTask] = {}
        self._results: Dict[str, ACPResult] = {}
        self._lock = threading.Lock()

    def register(self, info: AgentInfo) -> None:
        """Register or update an agent."""
        info.last_seen = time.time()
        with self._lock:
            self._agents[info.name] = info

    def get(self, name: str) -> Optional[AgentInfo]:
        return self._agents.get(name)

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._agents:
                del self._agents[name]
                return True
            return False

    def list_agents(self, status: Optional[AgentStatus] = None) -> List[AgentInfo]:
        agents = list(self._agents.values())
        if status is not None:
            agents = [a for a in agents if a.status == status]
        return agents

    def is_online(self, name: str) -> bool:
        agent = self._agents.get(name)
        return agent is not None and agent.status == AgentStatus.ONLINE

    def update_status(self, name: str, status: AgentStatus) -> bool:
        with self._lock:
            agent = self._agents.get(name)
            if agent is None:
                return False
            agent.status = status
            return True

    def prune_offline(self, max_age_seconds: float = 300) -> int:
        """Remove agents that haven't been seen recently."""
        now = time.time()
        pruned = 0
        with self._lock:
            to_remove = [
                name for name, info in self._agents.items()
                if info.status == AgentStatus.OFFLINE
                and (now - info.last_seen) > max_age_seconds
            ]
            for name in to_remove:
                del self._agents[name]
                pruned += 1
        return pruned

    def register_pending_task(self, task: ACPTask) -> None:
        with self._lock:
            self._pending_tasks[task.task_id] = task

    def complete_task(self, result: ACPResult) -> None:
        with self._lock:
            self._results[result.task_id] = result
            self._pending_tasks.pop(result.task_id, None)

    def wait_for_result(self, task_id: str, timeout: float = 30) -> Optional[ACPResult]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if task_id in self._results:
                    return self._results[task_id]
            time.sleep(0.05)
        return None

    def get_pending_task(self, task_id: str) -> Optional[ACPTask]:
        return self._pending_tasks.get(task_id)

    def get_pending_tasks_for_agent(self, agent_name: str) -> List[ACPTask]:
        return [
            t for t in self._pending_tasks.values()
            if t.target == agent_name
        ]


# ═══════════════════════════════════════════════════════════════
# ACPHandler
# ═══════════════════════════════════════════════════════════════

class ACPHandler:
    """Handles ACP protocol events via EventBus."""

    def __init__(
        self,
        event_bus: Any,
        registry: AgentRegistry,
        agent_name: str = "buffy",
        agent_version: str = "1.0.0",
    ) -> None:
        self._event_bus = event_bus
        self._registry = registry
        self._agent_name = agent_name
        self._agent_version = agent_version
        self._capabilities: Dict[str, str] = {}
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._running = False
        self._sub_id: Optional[str] = None
        self.on_broadcast: Optional[Callable[[dict, str], None]] = None

    def register_capability(self, name: str, description: str) -> None:
        self._capabilities[name] = description

    def remove_capability(self, name: str) -> None:
        self._capabilities.pop(name, None)

    def on_tool(self, name: str) -> Callable:
        """Decorator to register a tool handler."""
        def decorator(fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Callable:
            self._tool_handlers[name] = fn
            if name not in self._capabilities:
                self._capabilities[name] = fn.__doc__ or name
            return fn
        return decorator

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._sub_id = self._event_bus.subscribe(self._on_acp_event)
        self.send_status_update()

    def stop(self) -> None:
        self._running = False
        if self._sub_id is not None:
            self._event_bus.unsubscribe(self._sub_id)
            self._sub_id = None

    def _on_acp_event(self, event: Any) -> None:
        """Route incoming ACP events."""
        event_type = getattr(event, "type", None)
        source = getattr(event, "source", "")
        data = getattr(event, "data", {})

        if event_type == ACP_DISCOVER:
            self._handle_discover(source, data)
        elif event_type == ACP_TASK:
            self._handle_task(data)
        elif event_type == ACP_RESULT:
            pass  # handled by registry.wait_for_result
        elif event_type == ACP_STATUS:
            self._handle_status(data, source)
        elif event_type == ACP_BROADCAST:
            self._handle_broadcast(data, source)

    def _handle_discover(self, source: str, data: dict) -> None:
        """Respond to discover with our info."""
        self._event_bus.publish({
            "type": ACP_STATUS,
            "source": self._agent_name,
            "data": {
                "agent": self._agent_name,
                "version": self._agent_version,
                "status": "online",
                "capabilities": self._capabilities,
                "reply_to": source,
            },
        })

    def _handle_status(self, data: dict, source: str) -> None:
        """Register agent from status update."""
        status_str = data.get("status", "online")
        try:
            status = AgentStatus(status_str)
        except ValueError:
            status = AgentStatus.ONLINE
        info = AgentInfo(
            name=data.get("agent", source),
            version=data.get("version", ""),
            status=status,
            capabilities=data.get("capabilities", {}),
        )
        self._registry.register(info)

    def _handle_task(self, data: dict) -> None:
        """Execute a task targeted at us."""
        if data.get("target") != self._agent_name:
            return
        tool = data.get("tool", "")
        task_id = data.get("task_id", "")
        arguments = data.get("arguments", {})
        correlation_id = data.get("correlation_id", "")

        if tool in self._tool_handlers:
            try:
                result_data = self._tool_handlers[tool](arguments)
                success = True
                error = None
            except Exception as exc:
                result_data = {}
                success = False
                error = str(exc)
        else:
            result_data = {}
            success = False
            error = f"Unknown tool: {tool}"

        self._event_bus.publish({
            "type": ACP_RESULT,
            "source": self._agent_name,
            "data": {
                "task_id": task_id,
                "target": data.get("source", ""),
                "source": self._agent_name,
                "success": success,
                "data": result_data,
                "error": error,
                "correlation_id": correlation_id,
            },
        })

    def _handle_broadcast(self, data: dict, source: str) -> None:
        if self.on_broadcast is not None:
            self.on_broadcast(data, source)

    def send_task(
        self,
        target: str,
        tool: str,
        arguments: Dict[str, Any],
        timeout: float = 5,
    ) -> Optional[ACPResult]:
        """Send a task to another agent and wait for result."""
        task = ACPTask(target=target, source=self._agent_name, tool=tool, arguments=arguments)
        self._registry.register_pending_task(task)

        self._event_bus.publish({
            "type": ACP_TASK,
            "source": self._agent_name,
            "data": {
                "target": target,
                "tool": tool,
                "task_id": task.task_id,
                "arguments": arguments,
                "correlation_id": task.correlation_id,
            },
        })

        return self._registry.wait_for_result(task.task_id, timeout=timeout)

    def send_broadcast(self, message: str) -> None:
        self._event_bus.publish({
            "type": ACP_BROADCAST,
            "source": self._agent_name,
            "data": {"message": message, "agent": self._agent_name},
        })

    def send_status_update(self) -> None:
        self._event_bus.publish({
            "type": ACP_STATUS,
            "source": self._agent_name,
            "data": {
                "agent": self._agent_name,
                "version": self._agent_version,
                "status": "online",
                "capabilities": self._capabilities,
            },
        })
