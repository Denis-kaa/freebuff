"""
distributed_agents.py — Мульти-агентная оркестрация через Bridge Layer + ACP.

Позволяет:
  1. Создавать mesh из AI-агентов (MCP серверов), подключённых через Bridge Layer
  2. Распределять подзадачи между агентами по их capability
  3. Запускать multi-agent workflow с координацией через ACP
  4. Мониторить статус и результаты распределённых агентов

Архитектура:
  ┌─────────────────────────────────────────────────────┐
  │                 DistributedCoordinator               │
  │  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
  │  │ AgentMesh  │  │TaskDistrib │  │DistWorkflow   │  │
  │  │ (реестр)   │  │(роутинг)   │  │(оркестрация)  │  │
  │  └─────┬──────┘  └─────┬──────┘  └──────┬────────┘  │
  │        │               │                │           │
  │        └───────────────┼────────────────┘           │
  │                        │                            │
  │              ┌─────────▼──────────┐                 │
  │              │    Bridge Layer     │                 │
  │              │  (MCP ↔ ACP)       │                 │
  │              └─────────┬──────────┘                 │
  └────────────────────────┼────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │ Agent A  │      │ Agent B  │      │ Agent C  │
  │ (MCP)    │      │ (MCP)    │      │ (MCP)    │
  │ coding   │      │ research │      │ testing  │
  └──────────┘      └──────────┘      └──────────┘

Использование:
    from scripts_01.distributed_agents import DistributedCoordinator
    from scripts_01.event_bus import EventBus

    bus = EventBus()
    coord = DistributedCoordinator(event_bus=bus)

    # Запустить mesh
    coord.start()

    # Подключить агентов через Bridge Layer
    coord.spawn_agent("agent-code", command="python", args=["mcp_server.py"***REMOVED***)
    coord.spawn_agent("agent-research", command="python", args=["research_server.py"***REMOVED***)

    # Запустить workflow
    plan = coord.run_distributed_workflow(
        goal="Implement feature",
        steps=[
            {"agent": "agent-code", "tool": "code", "arguments": {...***REMOVED******REMOVED***,
            {"agent": "agent-research", "tool": "research", "arguments": {...***REMOVED******REMOVED***,
        ***REMOVED***,
    )
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
***REMOVED***
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

WORKSPACE = Path(__file__).resolve().parent


class AgentNodeStatus(str, Enum):
    """Статус агента в mesh."""

    PENDING = "pending"
    CONNECTING = "connecting"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class WorkCoordStatus(str, Enum):
    """Статус распределённого workflow."""

    PENDING = "pending"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class AgentCapability:
    """Capability агента."""

    name: str
    description: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class AgentNode:
    """Узел агента в распределённой сети.

    Представляет одного агента, подключённого через Bridge Layer.
    Агент может быть:
      - Внешним MCP сервером (stdio/HTTP)
      - Локальным обработиком (например, версия Claude Code в подпроцессе)
      - Remote агентом через ACP
    """

    name: str
    agent_type: str = "mcp"
    status: AgentNodeStatus = AgentNodeStatus.PENDING
    capabilities: Dict[str, AgentCapability***REMOVED*** = field(default_factory=dict)
    transport: str = "stdio"
    address: str = ""
    connected_at: float = 0.0
    last_seen: float = 0.0
    error: Optional[str***REMOVED*** = None
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    bridge_server_name: str = ""

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "capabilities": {
                name: {
                    "name": cap.name,
                    "description": cap.description,
                    "confidence": cap.confidence,
                ***REMOVED***
                for name, cap in self.capabilities.items()
            ***REMOVED***,
            "transport": self.transport,
            "address": self.address,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
            "error": self.error,
            "metadata": self.metadata,
            "bridge_server_name": self.bridge_server_name,
        ***REMOVED***


@dataclass
class AgentTask:
    """Задача для распределённого агента."""

    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8***REMOVED******REMOVED***")
    agent: str = ""
    tool: str = ""
    capability: str = ""
    arguments: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    strategy: str = "best_match"
    timeout: float = 60.0
    status: str = "pending"
    created_at: float = field(default_factory=time.time)

    @property
    def task_id(self) -> str:
        """Алиас id (контракт тестов)."""
        return self.id


@dataclass
class AgentTaskResult:
    """Результат выполнения задачи агентом."""

    task_id: str
    agent: str
    success: bool
    data: Any = None
    error: Optional[str***REMOVED*** = None
    duration_ms: float = 0.0
    completed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class DistributedWorkflowStep:
    """Шаг распределённого workflow."""

    id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8***REMOVED******REMOVED***")
    agent: str = ""
    step_type: str = "tool"
    tool: str = ""
    arguments: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    depends_on: List[str***REMOVED*** = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str***REMOVED*** = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return {
            "id": self.id,
            "agent": self.agent,
            "step_type": self.step_type,
            "tool": self.tool,
            "arguments": self.arguments,
            "depends_on": self.depends_on,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        ***REMOVED***


@dataclass
class DistributedWorkflowPlan:
    """План распределённого workflow."""

    id: str = field(default_factory=lambda: f"wf-{uuid.uuid4().hex[:8***REMOVED******REMOVED***")
    goal: str = ""
    steps: List[DistributedWorkflowStep***REMOVED*** = field(default_factory=list)
    status: WorkCoordStatus = WorkCoordStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    errors: List[str***REMOVED*** = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps***REMOVED***,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "errors": self.errors,
        ***REMOVED***




class AgentMesh:
    """Реестр агентов в распределённой сети.

    Thread-safe. Хранит AgentNode с их capabilities и статусом.
    Позволяет находить агентов по capability и типу.
    """

    def __init__(self, max_agents: int = 10):
        self._agents: Dict[str, AgentNode***REMOVED*** = {***REMOVED***
        self._task_history: List[AgentTaskResult***REMOVED*** = [***REMOVED***
        self._max_agents = max_agents
        self._lock = threading.RLock()

    @property
    def max_agents(self) -> int:
        """Максимальное количество агентов в mesh."""
        return self._max_agents

    def register(self, node: AgentNode) -> None:
        """Регистрирует агента в mesh."""
        with self._lock:
            self._agents[node.name***REMOVED*** = node

    def unregister(self, name: str) -> bool:
        """Удаляет агента из mesh."""
        with self._lock:
            return self._agents.pop(name, None) is not None

    def get(self, name: str) -> Optional[AgentNode***REMOVED***:
        """Получает агента по имени."""
        with self._lock:
            return self._agents.get(name)

    def update_status(self, name: str, status: AgentNodeStatus) -> bool:
        """Обновляет статус агента."""
        with self._lock:
            node = self._agents.get(name)
            if node is None:
                return False
            node.status = status
            node.last_seen = time.time()
            return True

    def set_error(self, name: str, error: str) -> bool:
        """Устанавливает ошибку агента."""
        with self._lock:
            node = self._agents.get(name)
            if node is None:
                return False
            node.status = AgentNodeStatus.ERROR
            node.error = error
            return True

    def list_agents(
        self, status: Optional[AgentNodeStatus***REMOVED*** = None, agent_type: Optional[str***REMOVED*** = None
    ) -> List[AgentNode***REMOVED***:
        """Список агентов с фильтрацией."""
        with self._lock:
            agents = list(self._agents.values())
        if status is not None:
            agents = [a for a in agents if a.status == status***REMOVED***
        if agent_type is not None:
            agents = [a for a in agents if a.agent_type == agent_type***REMOVED***
        return agents

    def find_by_capability(self, capability: str) -> List[AgentNode***REMOVED***:
        """Находит агентов, у которых есть определённая capability.

        Args:
            capability: имя capability (например, "code", "research", "test")

        Returns:
            список подходящих агентов, отсортированный по confidence
        """
        with self._lock:
            matching = [
                a
                for a in self._agents.values()
                if a.status in (AgentNodeStatus.ONLINE, AgentNodeStatus.BUSY)
                and capability in a.capabilities
            ***REMOVED***
        matching.sort(
            key=lambda a: a.capabilities[capability***REMOVED***.confidence, reverse=True
        )
        return matching

    def get_online_count(self) -> int:
        """Количество онлайн-агентов."""
        return sum(
            1 for a in self.list_agents() if a.status == AgentNodeStatus.ONLINE
        )

    def get_summary(self) -> Dict[str, Any***REMOVED***:
        """Сводка по mesh."""
        agents = self.list_agents()
        return {
            "total": len(agents),
            "agents": [a.to_dict() for a in agents***REMOVED***,
            "online": sum(1 for a in agents if a.status == AgentNodeStatus.ONLINE),
            "busy": sum(1 for a in agents if a.status == AgentNodeStatus.BUSY),
            "error": sum(1 for a in agents if a.status == AgentNodeStatus.ERROR),
            "offline": sum(1 for a in agents if a.status == AgentNodeStatus.OFFLINE),
            "pending": sum(1 for a in agents if a.status == AgentNodeStatus.PENDING),
        ***REMOVED***

    def record_task_result(self, result: AgentTaskResult) -> None:
        """Сохраняет результат задачи в историю."""
        with self._lock:
            self._task_history.append(result)
            if len(self._task_history) > 1000:
                self._task_history = self._task_history[-500:***REMOVED***

    def get_task_history(
        self, limit: int = 50, agent: Optional[str***REMOVED*** = None
    ) -> List[AgentTaskResult***REMOVED***:
        """История задач."""
        with self._lock:
            history = list(self._task_history)
        if agent:
            history = [r for r in history if r.agent == agent***REMOVED***
        return history[-limit:***REMOVED***[::-1***REMOVED***

    def get_agent_stats(self, agent_name: str) -> Dict[str, Any***REMOVED***:
        """Статистика по агенту."""
        with self._lock:
            node = self._agents.get(agent_name)
            history = [r for r in self._task_history if r.agent == agent_name***REMOVED***
        success = sum(1 for r in history if r.success)
        total = len(history)
        avg_duration = (
            sum(r.duration_ms for r in history) / total if total else 0.0
        )
        return {
            "agent_name": agent_name,
            "status": node.status.value if node else "unknown",
            "total_tasks": total,
            "success": success,
            "success_count": success,
            "failed": total - success,
            "success_rate": (success / total if total else 0.0),
            "avg_duration_ms": avg_duration,
            "tools": list(node.capabilities.keys()) if node else [***REMOVED***,
        ***REMOVED***


class TaskDistributor:
    """Распределяет задачи между агентами по их capabilities.

    Стратегии распределения:
      - round_robin: по очереди между подходящими агентами
      - best_match: агенту с наибольшим confidence (по умолчанию)
      - all: всем подходящим агентам (broadcast)
      - specific: указанному агенту
    """

    def __init__(self, mesh: AgentMesh):
        self._mesh = mesh
        self._rr_index: Dict[str, int***REMOVED*** = {***REMOVED***

    def distribute(
        self,
        capability: str,
        arguments: Dict[str, Any***REMOVED***,
        strategy: str = "best_match",
        timeout: float = 60.0,
        specific_agent: Optional[str***REMOVED*** = None,
    ) -> Optional[AgentTask***REMOVED***:
        """Выбирает агента и создаёт задачу.

        Args:
            capability: требуемая capability
            arguments: аргументы задачи
            strategy: стратегия распределения (round_robin, best_match, specific)
            timeout: таймаут выполнения
            specific_agent: агент для стратегии specific

        Returns:
            AgentTask или None если подходящий агент не найден.
        """
        candidates = self._mesh.find_by_capability(capability)
        if strategy == "specific":
            if specific_agent is None:
                return None
            node = self._mesh.get(specific_agent)
            if node is None or capability not in node.capabilities:
                return None
            agent_name = specific_agent
        elif strategy == "round_robin":
            if not candidates:
                return None
            idx = self._rr_index.get(capability, 0)
            agent_name = candidates[idx % len(candidates)***REMOVED***.name
            self._rr_index[capability***REMOVED*** = idx + 1
        else:  # best_match
            if not candidates:
                return None
            agent_name = candidates[0***REMOVED***.name

        return AgentTask(
            id=f"task-{uuid.uuid4().hex[:8***REMOVED******REMOVED***",
            capability=capability,
            arguments=arguments,
            agent=agent_name,
            strategy=strategy,
            timeout=timeout,
        )

    def distribute_to_all(
        self, capability: str, arguments: Dict[str, Any***REMOVED***, timeout: float = 60.0
    ) -> List[AgentTask***REMOVED***:
        """Создаёт задачи для всех подходящих агентов (broadcast).

        Args:
            capability: требуемая capability
            arguments: аргументы задачи
            timeout: таймаут выполнения

        Returns:
            список AgentTask для каждого подходящего агента
        """
        candidates = self._mesh.find_by_capability(capability)
        return [
            AgentTask(
                id=f"task-{uuid.uuid4().hex[:8***REMOVED******REMOVED***",
                capability=capability,
                arguments=arguments,
                agent=node.name,
                strategy="all",
                timeout=timeout,
            )
            for node in candidates
        ***REMOVED***


class DistributedCoordinator:
    """Главный координатор распределённой сети агентов.

    Объединяет AgentMesh + TaskDistributor + BridgeLayer + EventBus.

    Жизненный цикл:
      1. start() — запускает координатор, мониторинг
      2. register_agent() / spawn_agent() — добавляет агентов
      3. run_distributed_workflow() — запускает распределённую работу
      4. stop() — останавливает координатор
    """

    def __init__(
        self,
        event_bus: Any = None,
        bridge_layer: Any = None,
        max_agents: int = 10,
        default_timeout: float = 60.0,
    ):
        self.mesh = AgentMesh(max_agents=max_agents)
        self._mesh = self.mesh
        self._distributor = TaskDistributor(self.mesh)
        self._event_bus = event_bus
        self._bridge_layer = bridge_layer
        self._workflows: Dict[str, DistributedWorkflowPlan***REMOVED*** = {***REMOVED***
        self._lock = threading.RLock()
        self._running = False
        self.is_running = False
        self._monitor_thread: Optional[threading.Thread***REMOVED*** = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Запускает координатор."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self.is_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, name="distributed-monitor", daemon=True
        )
        self._monitor_thread.start()
        self._publish("distributed.started", {"coordinator": True***REMOVED***)

    def stop(self) -> None:
        """Останавливает координатор."""
        with self._lock:
            self._running = False
            self.is_running = False
        self._publish("distributed.stopped", {***REMOVED***)

    def _monitor_loop(self) -> None:
        """Мониторит состояние агентов."""
        while self._running:
            time.sleep(30.0)
            try:
                for node in self._mesh.list_agents():
                    if node.status == AgentNodeStatus.OFFLINE:
                        continue
                    if time.time() - node.last_seen > 120.0:
                        old = node.status
                        self._mesh.update_status(node.name, AgentNodeStatus.OFFLINE)
                        self._publish("distributed.agent_offline", {"agent_name": node.name, "old_status": old.value***REMOVED***)
            except Exception as exc:  # noqa: BLE001
                self._publish("distributed.agent_lost", {"error": str(exc)***REMOVED***)

    def _publish(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие в EventBus."""
        if self._event_bus is None:
            return
        try:
            from scripts_01.event_bus import Event

            self._event_bus.publish(Event(event_type, data))
        except Exception:
            pass

    # ── Управление агентами ───────────────────────────────────────────

    def register_agent(
        self,
        name: str = "",
        agent_type: str = "mcp",
        capabilities: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
        address: str = "",
        transport: str = "stdio",
        metadata: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ) -> str:
        """Регистрирует агента в mesh без подключения.

        Args:
            name: имя агента (авто-генерация если не указано)
            agent_type: тип агента (mcp, local, remote)
            capabilities: {capability_name: description***REMOVED***
            address: адрес (команда или endpoint)
            transport: транспорт (stdio, http)
            metadata: дополнительные данные

        Returns:
            имя зарегистрированного агента
        """
        with self._lock:
            if len(self._mesh.list_agents()) >= self._mesh.max_agents:
                return ""
        if not name:
            name = f"agent-{uuid.uuid4().hex[:6***REMOVED******REMOVED***"
        caps: Dict[str, AgentCapability***REMOVED*** = {***REMOVED***
        for cap_name, desc in (capabilities or {***REMOVED***).items():
            caps[cap_name***REMOVED*** = AgentCapability(name=cap_name, description=desc)
        node = AgentNode(
            name=name,
            agent_type=agent_type,
            status=AgentNodeStatus.PENDING,
            capabilities=caps,
            transport=transport,
            address=address,
            connected_at=time.time(),
            last_seen=time.time(),
            metadata=metadata or {***REMOVED***,
            bridge_server_name="",
        )
        self._mesh.register(node)
        self._publish("distributed.agent_registered", {"agent_name": name, "agent_type": agent_type***REMOVED***)
        self._publish("distributed.agent_online", {"agent_name": name***REMOVED***)
        self._mesh.update_status(name, AgentNodeStatus.ONLINE)
        return name

    def spawn_agent(
        self,
        name: Optional[str***REMOVED*** = None,
        command: str = "",
        args: Optional[List[str***REMOVED******REMOVED*** = None,
        cwd: Optional[str***REMOVED*** = None,
        capabilities: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
        transport: str = "stdio",
        endpoint: str = "",
    ) -> Dict[str, Any***REMOVED***:
        """Запускает и подключает нового агента.

        Агент запускается как MCP сервер (подпроцесс) и
        подключается через Bridge Layer.

        Args:
            name: имя агента (авто-генерация если не указано)
            command: команда для запуска (например "python")
            args: аргументы команды
            cwd: рабочая директория
            capabilities: {capability_name: description***REMOVED***
            transport: транспорт (stdio, http)
            endpoint: endpoint для http транспорта

        Returns:
            словарь с результатом
        """
        with self._lock:
            if len(self._mesh.list_agents()) >= self._mesh.max_agents:
                return {
                    "success": False,
                    "error": f"Max agents reached ({self._mesh.max_agents***REMOVED***)",
                ***REMOVED***
        agent_name = name or f"agent-{uuid.uuid4().hex[:6***REMOVED******REMOVED***"
        if self._bridge_layer is None:
            # Регистрируем без подключения (graceful degradation).
            self.register_agent(
                name=agent_name,
                capabilities=capabilities,
                transport=transport,
                metadata={"note": "Registered without Bridge Layer"***REMOVED***,
            )
            return {"success": True, "agent": agent_name, "agent_name": agent_name, "connected": False***REMOVED***

        try:
            if hasattr(self._bridge_layer, "connect_mcp_stdio"):
                server_name = self._bridge_layer.connect_mcp_stdio(
                    name=agent_name,
                    command=command,
                    args=args or [***REMOVED***,
                    cwd=cwd,
                    transport=transport,
                    endpoint=endpoint,
                )
            else:
                server_name = self._bridge_layer.connect_mcp(
                    name=agent_name,
                    command=command,
                    args=args or [***REMOVED***,
                    cwd=cwd,
                    transport=transport,
                    endpoint=endpoint,
                )
        except Exception as exc:  # noqa: BLE001
            self._mesh.set_error(agent_name, str(exc))
            return {"success": False, "agent": agent_name, "agent_name": agent_name, "error": str(exc)***REMOVED***

        caps: Dict[str, AgentCapability***REMOVED*** = {***REMOVED***
        for cap_name, desc in (capabilities or {***REMOVED***).items():
            caps[cap_name***REMOVED*** = AgentCapability(name=cap_name, description=desc)
        node = AgentNode(
            name=agent_name,
            agent_type="mcp",
            status=AgentNodeStatus.ONLINE,
            capabilities=caps,
            transport=transport,
            address=command,
            connected_at=time.time(),
            last_seen=time.time(),
            bridge_server_name=server_name or "",
        )
        self._mesh.register(node)
        self._publish("distributed.agent_registered", {"agent_name": agent_name***REMOVED***)
        self._publish("distributed.agent_online", {"agent_name": agent_name***REMOVED***)
        return {"success": True, "agent": agent_name, "agent_name": agent_name, "connected": True, "server_name": server_name***REMOVED***

    def remove_agent(self, agent_name: str) -> bool:
        """Удаляет агента из mesh и отключает."""
        node = self._mesh.get(agent_name)
        if node is None:
            return False
        if self._bridge_layer is not None and node.bridge_server_name:
            try:
                self._bridge_layer.disconnect(node.bridge_server_name)
            except Exception:
                pass
        ok = self._mesh.unregister(agent_name)
        if ok:
            self._publish("distributed.agent_removed", {"agent_name": agent_name***REMOVED***)
        return ok

    def list_agents(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список агентов."""
        return [a.to_dict() for a in self._mesh.list_agents()***REMOVED***

    def broadcast_to_all(self, message: str, data: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> int:
        """Отправляет broadcast всем агентам.

        Args:
            message: сообщение
            data: дополнительные данные

        Returns:
            количество агентов, получивших broadcast
        """
        agents = self._mesh.list_agents()
        count = 0
        for node in agents:
            if node.status not in (AgentNodeStatus.ONLINE, AgentNodeStatus.BUSY):
                continue
            if self._bridge_layer is not None:
                server = node.bridge_server_name or node.name
                try:
                    if hasattr(self._bridge_layer, "send_acp_broadcast"):
                        self._bridge_layer.send_acp_broadcast(
                            server,
                            {"type": "broadcast", "message": message, "data": data or {***REMOVED******REMOVED***,
                        )
                    else:
                        self._bridge_layer.send_message(
                            server,
                            {"type": "broadcast", "message": message, "data": data or {***REMOVED******REMOVED***,
                        )
                    count += 1
                except Exception:
                    continue
            else:
                count += 1
        self._publish("distributed.heartbeat", {"message": message, "recipients": count***REMOVED***)
        return count

    # ── Выполнение задач ──────────────────────────────────────────────

    def execute_agent_task(self, task: AgentTask, timeout: float | None = None) -> AgentTaskResult:
        """Выполняет задачу на агенте через Bridge Layer.

        Args:
            task: задача для выполнения
            timeout: таймаут (переопределяет task.timeout)

        Returns:
            AgentTaskResult
        """
        node = self._mesh.get(task.agent)
        if node is None:
            result = AgentTaskResult(
                task_id=task.id, agent=task.agent, success=False, error="Agent not found"
            )
            self._mesh.record_task_result(result)
            return result
        if self._bridge_layer is None or not node.bridge_server_name:
            result = AgentTaskResult(
                task_id=task.id, agent=task.agent, success=False, error="Bridge Layer not available"
            )
            self._mesh.record_task_result(result)
            return result
        start = time.time()
        try:
            response = self._bridge_layer.execute_tool(
                node.bridge_server_name, task.capability, task.arguments, timeout=timeout or task.timeout
            )
            ok = bool(response and response.get("success", False))
            result = AgentTaskResult(
                task_id=task.id,
                agent=task.agent,
                success=ok,
                data=response,
                error=None if ok else (response or {***REMOVED***).get("error"),
                duration_ms=(time.time() - start) * 1000.0,
            )
        except Exception as exc:  # noqa: BLE001
            result = AgentTaskResult(
                task_id=task.id,
                agent=task.agent,
                success=False,
                error=str(exc),
                duration_ms=(time.time() - start) * 1000.0,
            )
        self._mesh.record_task_result(result)
        self._publish("distributed.task_completed", {"task_id": task.id, "agent": task.agent, "success": result.success***REMOVED***)
        return result

    def execute_parallel(self, tasks: List[AgentTask***REMOVED***, timeout: float = 60.0) -> List[AgentTaskResult***REMOVED***:
        """Выполняет несколько задач параллельно на разных агентах.

        Args:
            tasks: список задач
            timeout: общий таймаут

        Returns:
            список результатов
        """
        results: List[AgentTaskResult***REMOVED*** = [***REMOVED***
        for task in tasks:
            results.append(self.execute_agent_task(task, timeout=timeout))
        return results

    # ── Workflow ──────────────────────────────────────────────────────

    def run_distributed_workflow(
        self,
        goal: str,
        steps: List[Dict[str, Any***REMOVED******REMOVED***,
        timeout: float = 300.0,
    ) -> DistributedWorkflowPlan:
        """Запускает распределённый workflow.

        workflow_steps format:
            [
                {"agent": "agent-name", "tool": "tool-name", "arguments": {...***REMOVED***,
                 "depends_on": ["step-id"***REMOVED***, "step_type": "tool"***REMOVED***,
                {"agent": "agent-name", "step_type": "broadcast", "message": "..."***REMOVED***
            ***REMOVED***
        """
        workflow_id = f"wf-{uuid.uuid4().hex[:8***REMOVED******REMOVED***"
        wf_steps: List[DistributedWorkflowStep***REMOVED*** = [***REMOVED***
        for i, s in enumerate(steps):
            wf_steps.append(
                DistributedWorkflowStep(
                    id=s.get("id") or f"step_{i+1***REMOVED***",
                    agent=s.get("agent", ""),
                    step_type=s.get("step_type", "tool"),
                    tool=s.get("tool", ""),
                    arguments=s.get("arguments", {***REMOVED***),
                    depends_on=list(s.get("depends_on", [***REMOVED***)),
                )
            )
        plan = DistributedWorkflowPlan(id=workflow_id, goal=goal, steps=wf_steps)
        plan.status = WorkCoordStatus.PLANNING
        self._workflows[workflow_id***REMOVED*** = plan
        self._publish("distributed.workflow_planning", {"workflow_id": workflow_id, "goal": goal***REMOVED***)

        plan.status = WorkCoordStatus.RUNNING
        plan.updated_at = datetime.now(timezone.utc).isoformat()

        step_map = {s.id: s for s in wf_steps***REMOVED***
        start = time.time()
        completed = 0
        for step in wf_steps:
            # Проверяем зависимости.
            deps_failed = [d for d in step.depends_on if step_map.get(d) and step_map[d***REMOVED***.status == "failed"***REMOVED***
            if deps_failed:
                step.status = "skipped"
                step.error = "Dependencies failed"
                plan.errors.append(f"{step.id***REMOVED***: dependencies failed")
                continue
            if step.step_type == "broadcast":
                self.broadcast_to_all(step.arguments.get("message", ""), step.arguments)
                step.status = "completed"
                step.result = {"broadcast": True***REMOVED***
                completed += 1
            else:
                if not step.agent or not step.tool:
                    step.status = "failed"
                    step.error = "No agent or tool specified"
                    plan.errors.append(f"{step.id***REMOVED***: no agent or tool")
                    continue
                task = AgentTask(
                    id=f"task-{uuid.uuid4().hex[:8***REMOVED******REMOVED***",
                    capability=step.tool,
                    arguments=step.arguments,
                    agent=step.agent,
                    timeout=timeout,
                )
                result = self.execute_agent_task(task, timeout=timeout)
                step.result = result.data
                if result.success:
                    step.status = "completed"
                    completed += 1
                else:
                    step.status = "failed"
                    step.error = result.error or "Unknown error"
                    plan.errors.append(f"{step.id***REMOVED***: {step.error***REMOVED***")
            step.duration_ms = (time.time() - start) * 1000.0
            plan.updated_at = datetime.now(timezone.utc).isoformat()
            self._publish("distributed.workflow_progress", {"workflow_id": workflow_id, "step": step.id, "status": step.status***REMOVED***)

        if completed == len(wf_steps):
            plan.status = WorkCoordStatus.COMPLETED
        elif completed > 0:
            plan.status = WorkCoordStatus.PARTIAL
        else:
            plan.status = WorkCoordStatus.FAILED
        plan.updated_at = datetime.now(timezone.utc).isoformat()
        self._publish("distributed.workflow_completed", {"workflow_id": workflow_id, "status": plan.status.value***REMOVED***)
        return plan

    def get_workflow(self, workflow_id: str) -> Optional[DistributedWorkflowPlan***REMOVED***:
        """Получает workflow по ID."""
        with self._lock:
            return self._workflows.get(workflow_id)

    def _get_ready_steps(
        self, plan: DistributedWorkflowPlan, done_set: Optional[Set[str***REMOVED******REMOVED*** = None
    ) -> List[DistributedWorkflowStep***REMOVED***:
        """Шаги, готовые к выполнению: все зависимости в done_set (или их нет).

        Контракт тестов: coord._get_ready_steps(plan, set()) — шаги без
        незавершённых зависимостей.
        """
        done_set = done_set or set()
        ready = [***REMOVED***
        for s in plan.steps:
            if s.status in ("completed", "skipped", "failed"):
                continue
            deps = set(s.depends_on)
            if deps and not deps.issubset(done_set):
                continue
            ready.append(s)
        return ready

    def _get_blocked_steps(
        self, plan: DistributedWorkflowPlan, done_set: Optional[Set[str***REMOVED******REMOVED*** = None
    ) -> List[DistributedWorkflowStep***REMOVED***:
        """Шаги, заблокированные зависимостями из done_set.

        Контракт тестов: coord._get_blocked_steps(plan, {'s1'***REMOVED***) — шаги,
        чьи зависимости пересекаются с переданным множеством.
        """
        done_set = done_set or set()
        blocked = [***REMOVED***
        for s in plan.steps:
            if s.status in ("completed", "skipped", "failed"):
                continue
            deps = set(s.depends_on)
            if deps and deps.intersection(done_set):
                blocked.append(s)
        return blocked

    def list_workflows(self, limit: int = 10, status: Optional[WorkCoordStatus***REMOVED*** = None) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Список workflow."""
        with self._lock:
            workflows = list(self._workflows.values())
        if status is not None:
            workflows = [w for w in workflows if w.status == status***REMOVED***
        return [w.to_dict() for w in workflows[-limit:***REMOVED***[::-1***REMOVED******REMOVED***

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Общий статус системы."""
        mesh_summary = self._mesh.get_summary()
        workflows = self.list_workflows(limit=100)
        total_tasks = sum(len(w["steps"***REMOVED***) for w in workflows)
        success = sum(
            1 for w in workflows if w["status"***REMOVED*** == WorkCoordStatus.COMPLETED.value
        )
        return {
            "running": self._running,
            "mesh": mesh_summary,
            "total_workflows": len(workflows),
            "total_tasks": total_tasks,
            "success_count": success,
            "success_rate": (success / len(workflows) if workflows else 0.0),
            "bridge_layer": self._bridge_layer is not None,
        ***REMOVED***


# ── CLI ───────────────────────────────────────────────────────────────

def _cmd_agents(args: argparse.Namespace) -> None:
    coord = DistributedCoordinator()
    agents = coord.list_agents()
    print("🌐 Agent Mesh Summary")
    print(f"  Agents: {len(agents)***REMOVED***")
    for a in agents:
        status = a["status"***REMOVED***
        icon = "🟢" if status == "online" else ("🟡" if status == "busy" else "⚪")
        print(f"  {icon***REMOVED*** {a['name'***REMOVED******REMOVED***: {status***REMOVED*** ({a['agent_type'***REMOVED******REMOVED***)")
        if a["capabilities"***REMOVED***:
            print(f"     Capabilities ({len(a['capabilities'***REMOVED***)***REMOVED***): {', '.join(a['capabilities'***REMOVED***)***REMOVED***")


def _cmd_status(args: argparse.Namespace) -> None:
    coord = DistributedCoordinator()
    st = coord.get_status()
    print("🌐 Distributed System Status")
    print(f"  Coordinator: {'🟢 Active' if st['running'***REMOVED*** else '🔴 Stopped'***REMOVED***")
    print(f"  Bridge Layer: {'available' if st['bridge_layer'***REMOVED*** else 'not available'***REMOVED***")
    print(f"  Total agents: {st['mesh'***REMOVED***['total'***REMOVED******REMOVED*** (online: {st['mesh'***REMOVED***['online'***REMOVED******REMOVED***)")
    print(f"  Workflows: {st['total_workflows'***REMOVED******REMOVED*** (success: {st['success_count'***REMOVED******REMOVED***)")
    print(f"  Tasks: {st['total_tasks'***REMOVED******REMOVED***")


def _cmd_spawn(args: argparse.Namespace) -> None:
    coord = DistributedCoordinator()
    caps = {***REMOVED***
    for c in (args.capabilities or "").split(","):
        c = c.strip()
        if c:
            caps[c***REMOVED*** = f"{c***REMOVED*** capability"
    result = coord.spawn_agent(
        name=args.name,
        command=args.command,
        args=[args.args***REMOVED*** if args.args else [***REMOVED***,
        capabilities=caps,
    )
    if result.get("success"):
        print(f"✅ Agent '{result['agent_name'***REMOVED******REMOVED***' spawned")
    else:
        print(f"❌ Failed: {result.get('error', 'unknown')***REMOVED***")


def _cmd_workflow(args: argparse.Namespace) -> None:
    coord = DistributedCoordinator()
    if args.command == "list":
        workflows = coord.list_workflows(limit=args.limit)
        print("📋 Workflows (")
        if not workflows:
            print("No workflows yet.")
            return
        for w in workflows:
            print(f"  {w['id'***REMOVED******REMOVED***: {w['goal'***REMOVED******REMOVED*** [{w['status'***REMOVED******REMOVED******REMOVED*** steps={len(w['steps'***REMOVED***)***REMOVED***")
    elif args.command == "run":
        plan_data = None
        if args.plan:
            with open(args.plan, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
        if plan_data is None:
            print("❌ Workflow plan required (--plan plan.json)")
            return
        plan = coord.run_distributed_workflow(
            goal=plan_data.get("goal", args.goal or "Distributed workflow"),
            steps=plan_data.get("steps", [***REMOVED***),
        )
        print(f"🚀 Starting distributed workflow: {plan.goal***REMOVED***")
        print(f"  ID: {plan.id***REMOVED***")
        for s in plan.steps:
            icon = "✅" if s.status == "completed" else ("❌" if s.status == "failed" else "⏳")
            print(f"  {icon***REMOVED*** {s.id***REMOVED***: {s.agent or 'broadcast'***REMOVED*** → {s.tool or s.step_type***REMOVED*** [{s.status***REMOVED******REMOVED***")
        print(f"📊 Status: {plan.status.value***REMOVED***")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Distributed Agents — мульти-агентная оркестрация"
    )
    sub = parser.add_subparsers(dest="command")

    p_agents = sub.add_parser("agents", help="Список агентов")
    p_status = sub.add_parser("status", help="Общий статус системы")

    p_spawn = sub.add_parser("spawn", help="Запустить агента")
    p_spawn.add_argument("--name", help="Имя агента")
    p_spawn.add_argument("--command", default="python", help="Команда")
    p_spawn.add_argument("--args", help="Аргументы")
    p_spawn.add_argument("--capabilities", help="Capabilities (code research test)")

    p_wf = sub.add_parser("workflow", help="Управление workflow")
    wf_sub = p_wf.add_subparsers(dest="wf_command")
    p_wf_list = wf_sub.add_parser("list", help="Список workflow")
    p_wf_list.add_argument("--limit", type=int, default=10, help="Лимит")
    p_wf_run = wf_sub.add_parser("run", help="Запустить workflow")
    p_wf_run.add_argument("goal", nargs="?", default="", help="Цель workflow")
    p_wf_run.add_argument("--plan", help="JSON файл с планом шагов")

    args = parser.parse_args()

    if args.command == "agents":
        _cmd_agents(args)
        return 0
    if args.command == "status":
        _cmd_status(args)
        return 0
    if args.command == "spawn":
        _cmd_spawn(args)
        return 0
    if args.command == "workflow":
        args.command = args.wf_command
        _cmd_workflow(args)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
