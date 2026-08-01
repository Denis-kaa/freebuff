"""
ACP — Agent Collaboration Protocol.

Протокол кооперации AI-агентов, построенный на Event Bus.
Позволяет агентам:
  - Обнаруживать друг друга (discover)
  - Отправлять задачи (task/result)
  - Широковещательно обмениваться сообщениями (broadcast)
  - Обновлять статус (online/offline/busy)

Транспорт: Event Bus (publish/subscribe).
Формат сообщений: JSON-RPC 2.0.

Типы событий ACP:
  acp.discover      — запрос/ответ списка агентов
  acp.task          — отправить задачу агенту
  acp.result        — результат выполнения задачи
  acp.broadcast     — широковещательное сообщение
  acp.status        — обновление статуса агента
  acp.error         — ошибка

Использование:
    from freebuff_plugin_03.acp_protocol import AgentRegistry, ACPHandler

    bus = get_default_event_bus()
    registry = AgentRegistry()
    handler = ACPHandler(bus, registry, agent_name="buffy")

    # Зарегистрировать возможности
    handler.register_capability("knowledge_search", "Поиск в Knowledge Engine")
    handler.register_capability("memory_store", "Сохранение в память")

    # Запустить обработчик
    handler.start()

    # Отправить задачу другому агенту
    handler.send_task("claude-agent", "knowledge_search", {"query": "python"***REMOVED***)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── ACP Constants ──────────────────────────────────────────────

ACP_VERSION = "0.1.0"
ACP_PROTOCOL = "acp-jsonrpc-2.0"

# Event types
ACP_DISCOVER = "acp.discover"
ACP_TASK = "acp.task"
ACP_RESULT = "acp.result"
ACP_BROADCAST = "acp.broadcast"
ACP_STATUS = "acp.status"
ACP_ERROR = "acp.error"
ACP_HEARTBEAT = "acp.heartbeat"

# ACP error codes
ACP_SUCCESS = 0
ACP_ERR_UNKNOWN_AGENT = -100
ACP_ERR_UNKNOWN_TOOL = -101
ACP_ERR_TASK_FAILED = -102
ACP_ERR_TIMEOUT = -103
ACP_ERR_INTERNAL = -104


class AgentStatus(Enum):
    """Статус агента в сети ACP."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class AgentInfo:
    """Информация об агенте в сети ACP."""
    name: str
    version: str = "1.0.0"
    status: AgentStatus = AgentStatus.ONLINE
    capabilities: Dict[str, str***REMOVED*** = field(default_factory=dict)  # tool_name → description
    protocol: str = ACP_PROTOCOL
    last_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class ACPTask:
    """Задача, отправляемая агенту."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12***REMOVED***)
    target: str = ""           # имя целевого агента
    source: str = ""           # имя источника
    tool: str = ""             # название инструмента
    arguments: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    timeout: float = 60.0      # таймаут в секундах
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str = ""   # для связывания task ↔ result


@dataclass
class ACPResult:
    """Результат выполнения задачи."""
    task_id: str = ""
    source: str = ""
    target: str = ""
    success: bool = True
    data: Any = None
    error: Optional[str***REMOVED*** = None
    duration_ms: float = 0.0
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str = ""


# ── Agent Registry ─────────────────────────────────────────────


class AgentRegistry:
    """Реестр агентов в сети ACP.

    Хранит информацию обо всех известных агентах и их возможностях.
    Thread-safe.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._agents: Dict[str, AgentInfo***REMOVED*** = {***REMOVED***
        self._pending_tasks: Dict[str, ACPTask***REMOVED*** = {***REMOVED***  # task_id → task
        self._task_results: Dict[str, ACPResult***REMOVED*** = {***REMOVED***  # task_id → result
        self._result_events: Dict[str, threading.Event***REMOVED*** = {***REMOVED***  # task_id → event

    # ── Agent management ────────────────────────────────────

    def register(self, info: AgentInfo) -> None:
        """Регистрирует или обновляет агента."""
        with self._lock:
            info.last_seen = datetime.now(timezone.utc).isoformat()
            self._agents[info.name***REMOVED*** = info

    def unregister(self, name: str) -> bool:
        """Удаляет агента из реестра."""
        with self._lock:
            return self._agents.pop(name, None) is not None

    def get(self, name: str) -> Optional[AgentInfo***REMOVED***:
        """Получает информацию об агенте."""
        with self._lock:
            return self._agents.get(name)

    def list_agents(self, status: Optional[AgentStatus***REMOVED*** = None) -> List[AgentInfo***REMOVED***:
        """Список всех агентов, опционально фильтрованных по статусу."""
        with self._lock:
            agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status***REMOVED***
        return sorted(agents, key=lambda a: a.name)

    def is_online(self, name: str) -> bool:
        """Проверяет, онлайн ли агент."""
        agent = self.get(name)
        return agent is not None and agent.status == AgentStatus.ONLINE

    def update_status(self, name: str, status: AgentStatus) -> bool:
        """Обновляет статус агента."""
        with self._lock:
            agent = self._agents.get(name)
            if agent is None:
                return False
            agent.status = status
            agent.last_seen = datetime.now(timezone.utc).isoformat()
            return True

    def prune_offline(self, max_age_seconds: float = 300.0) -> int:
        """Удаляет агентов, не подававших признаков жизни."""
        now = datetime.now(timezone.utc)
        to_remove: List[str***REMOVED*** = [***REMOVED***
        with self._lock:
            for name, info in self._agents.items():
                last = datetime.fromisoformat(info.last_seen)
                if (now - last).total_seconds() > max_age_seconds:
                    to_remove.append(name)
            for name in to_remove:
                del self._agents[name***REMOVED***
        return len(to_remove)

    # ── Task management ──────────────────────────────────────

    def register_pending_task(self, task: ACPTask) -> None:
        """Регистрирует ожидающую выполнения задачу."""
        with self._lock:
            self._pending_tasks[task.task_id***REMOVED*** = task
            self._result_events[task.task_id***REMOVED*** = threading.Event()

    def complete_task(self, result: ACPResult) -> None:
        """Сохраняет результат задачи и сигнализирует ожидающим."""
        with self._lock:
            self._task_results[result.task_id***REMOVED*** = result
            self._pending_tasks.pop(result.task_id, None)
            event = self._result_events.pop(result.task_id, None)
            if event:
                event.set()

    def wait_for_result(self, task_id: str, timeout: float = 60.0) -> Optional[ACPResult***REMOVED***:
        """Ожидает результат задачи (блокирующий вызов)."""
        event = self._result_events.get(task_id)
        if event is None:
            return self._task_results.get(task_id)
        if event.wait(timeout=timeout):
            with self._lock:
                return self._task_results.pop(task_id, None)
        return None  # timeout

    def get_pending_task(self, task_id: str) -> Optional[ACPTask***REMOVED***:
        """Получает ожидающую задачу."""
        with self._lock:
            return self._pending_tasks.get(task_id)

    def get_pending_tasks_for_agent(self, agent_name: str) -> List[ACPTask***REMOVED***:
        """Получает все ожидающие задачи для агента."""
        with self._lock:
            return [
                t for t in self._pending_tasks.values()
                if t.target == agent_name
            ***REMOVED***


# ── ACP Handler ────────────────────────────────────────────────


class ACPHandler:
    """Обработчик ACP протокола.

    Подписывается на события ACP через Event Bus, обрабатывает
    входящие сообщения и вызывает соответствующие хендлеры.

    Использование:
        bus = EventBus()
        registry = AgentRegistry()
        handler = ACPHandler(bus, registry, agent_name="buffy")

        # Зарегистрировать обработчик инструмента
        @handler.on_tool("knowledge_search")
        def handle_search(args: dict) -> dict:
            return {"results": [...***REMOVED******REMOVED***

        handler.start()
    """

    def __init__(
        self,
        event_bus: Any,
        registry: AgentRegistry,
        agent_name: str = "buffy",
        agent_version: str = "1.0.0",
        capabilities: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
    ):
        self._bus = event_bus
        self._registry = registry
        self._agent_name = agent_name
        self._agent_version = agent_version
        self._capabilities: Dict[str, str***REMOVED*** = capabilities or {***REMOVED***
        self._tool_handlers: Dict[str, Callable***REMOVED*** = {***REMOVED***
        self._subscriptions: List[Any***REMOVED*** = [***REMOVED***
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread***REMOVED*** = None
        self._agent_status = AgentStatus.ONLINE

    # ── Capability management ────────────────────────────────

    def register_capability(self, tool_name: str, description: str) -> None:
        """Регистрирует возможность агента."""
        self._capabilities[tool_name***REMOVED*** = description

    def remove_capability(self, tool_name: str) -> None:
        """Удаляет возможность агента."""
        self._capabilities.pop(tool_name, None)

    def on_tool(self, tool_name: str):
        """Декоратор для регистрации обработчика инструмента.

        Использование:
            @handler.on_tool("knowledge_search")
            def handle_search(args: dict) -> dict:
                ...
        """
        def decorator(func: Callable) -> Callable:
            self._tool_handlers[tool_name***REMOVED*** = func
            return func
        return decorator

    # ── Lifecycle ────────────────────────────────────────────

    def start(self) -> None:
        """Запускает обработчик: подписка на события + heartbeat + регистрация."""
        if self._running:
            return
        self._running = True

        from freebuff_plugin_03.bridge import create_event

        # Подписка на ACP события
        acp_events = [
            ACP_DISCOVER, ACP_TASK, ACP_RESULT,
            ACP_BROADCAST, ACP_STATUS, ACP_HEARTBEAT,
        ***REMOVED***
        for event_type in acp_events:
            sub = self._bus.subscribe(event_type, self._on_acp_event)
            self._subscriptions.append(sub)

        # Регистрация себя в локальном реестре и публикация статуса
        self._registry.register(AgentInfo(
            name=self._agent_name,
            version=self._agent_version,
            status=AgentStatus.ONLINE,
            capabilities=self._capabilities,
        ))
        self._publish_event(ACP_STATUS, {
            "agent": self._agent_name,
            "version": self._agent_version,
            "status": AgentStatus.ONLINE.value,
            "capabilities": self._capabilities,
        ***REMOVED***)

        # Heartbeat thread
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"acp-heartbeat-{self._agent_name***REMOVED***",
        )
        self._heartbeat_thread.start()

    def stop(self) -> None:
        """Останавливает обработчик: отписка + офлайн статус."""
        if not self._running:
            return
        self._running = False

        # Офлайн статус
        self._publish_event(ACP_STATUS, {
            "agent": self._agent_name,
            "status": AgentStatus.OFFLINE.value,
        ***REMOVED***)

        # Отписка от событий
        for sub in self._subscriptions:
            try:
                self._bus.unsubscribe(sub)
            except Exception:
                pass
        self._subscriptions.clear()

        self._agent_status = AgentStatus.OFFLINE

    # ── Event processing ─────────────────────────────────────

    def _on_acp_event(self, event: Any) -> None:
        """Обрабатывает входящее ACP событие."""
        try:
            event_type = event.type
            data = event.data if hasattr(event, 'data') else event
            source = event.source if hasattr(event, 'source') else "unknown"

            # Не обрабатываем свои же сообщения
            if source == self._agent_name:
                return

            if event_type == ACP_DISCOVER:
                self._handle_discover(data, source)

            elif event_type == ACP_TASK:
                self._handle_task(data, source)

            elif event_type == ACP_RESULT:
                self._handle_result(data, source)

            elif event_type == ACP_STATUS:
                self._handle_status(data)

            elif event_type == ACP_BROADCAST:
                self._handle_broadcast(data, source)

            elif event_type == ACP_HEARTBEAT:
                self._handle_heartbeat(data)

        except Exception as e:
            # Не ломаем шину из-за ошибки в одном обработчике
            import traceback
            traceback.print_exc()

    def _handle_discover(self, data: Dict[str, Any***REMOVED***, source: str) -> None:
        """Обрабатывает discover запрос — отвечает своей информацией."""
        # Отвечаем только на directed discover или всегда?
        # Отвечаем всегда — чтобы новые агенты узнавали о нас
        self._publish_event(ACP_DISCOVER, {
            "agent": self._agent_name,
            "version": self._agent_version,
            "status": self._agent_status.value,
            "capabilities": self._capabilities,
            "response_to": data.get("agent", source),
        ***REMOVED***)

    def _handle_task(self, data: Dict[str, Any***REMOVED***, source: str) -> None:
        """Обрабатывает входящую задачу."""
        target = data.get("target", "")
        if target != self._agent_name:
            return  # Задача не нам

        tool = data.get("tool", "")
        task_id = data.get("task_id", uuid.uuid4().hex[:12***REMOVED***)
        arguments = data.get("arguments", {***REMOVED***)
        correlation_id = data.get("correlation_id", "")

        # Проверяем, знаем ли мы такой инструмент
        handler = self._tool_handlers.get(tool)
        if handler is None:
            self._publish_event(ACP_RESULT, {
                "task_id": task_id,
                "source": self._agent_name,
                "target": source,
                "success": False,
                "error": f"Unknown tool: {tool***REMOVED***",
                "correlation_id": correlation_id,
            ***REMOVED***)
            return

        # Выполняем
        import time
        t0 = time.time()
        try:
            result_data = handler(arguments)
            duration_ms = (time.time() - t0) * 1000
            self._publish_event(ACP_RESULT, {
                "task_id": task_id,
                "source": self._agent_name,
                "target": source,
                "success": True,
                "data": result_data,
                "duration_ms": round(duration_ms, 1),
                "correlation_id": correlation_id,
            ***REMOVED***)
        except Exception as e:
            duration_ms = (time.time() - t0) * 1000
            self._publish_event(ACP_RESULT, {
                "task_id": task_id,
                "source": self._agent_name,
                "target": source,
                "success": False,
                "error": str(e),
                "duration_ms": round(duration_ms, 1),
                "correlation_id": correlation_id,
            ***REMOVED***)

    def _handle_result(self, data: Dict[str, Any***REMOVED***, source: str) -> None:
        """Обрабатывает полученный результат задачи."""
        result = ACPResult(
            task_id=data.get("task_id", ""),
            source=source,
            target=data.get("target", self._agent_name),
            success=data.get("success", True),
            data=data.get("data"),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0.0),
            correlation_id=data.get("correlation_id", ""),
        )
        self._registry.complete_task(result)

    def _handle_status(self, data: Dict[str, Any***REMOVED***) -> None:
        """Обрабатывает обновление статуса агента."""
        agent_name = data.get("agent", "unknown")
        status_str = data.get("status", AgentStatus.ONLINE.value)
        capabilities = data.get("capabilities", {***REMOVED***)

        try:
            status = AgentStatus(status_str)
        except ValueError:
            status = AgentStatus.ONLINE

        info = AgentInfo(
            name=agent_name,
            version=data.get("version", "1.0.0"),
            status=status,
            capabilities=capabilities,
            metadata=data.get("metadata", {***REMOVED***),
        )
        self._registry.register(info)

    def _handle_broadcast(self, data: Dict[str, Any***REMOVED***, source: str) -> None:
        """Обрабатывает широковещательное сообщение."""
        # Можно переопределить в подклассе
        message = data.get("message", "")
        if message:
            print(f"📢 ACP Broadcast from {source***REMOVED***: {message[:200***REMOVED******REMOVED***")
        self.on_broadcast(data, source)

    def on_broadcast(self, data: Dict[str, Any***REMOVED***, source: str) -> None:
        """Хук для обработки broadcast сообщений. Переопределите в подклассе."""
        pass

    def _handle_heartbeat(self, data: Dict[str, Any***REMOVED***) -> None:
        """Обрабатывает heartbeat — обновляет last_seen."""
        agent_name = data.get("agent", "unknown")
        agent = self._registry.get(agent_name)
        if agent:
            agent.last_seen = datetime.now(timezone.utc).isoformat()

    # ── Send methods ─────────────────────────────────────────

    def send_discover(self) -> None:
        """Отправляет discover запрос."""
        self._publish_event(ACP_DISCOVER, {
            "agent": self._agent_name,
            "version": self._agent_version,
        ***REMOVED***)

    def send_task(
        self,
        target: str,
        tool: str,
        arguments: Dict[str, Any***REMOVED***,
        timeout: float = 60.0,
    ) -> Optional[ACPResult***REMOVED***:
        """Отправляет задачу агенту и ожидает результат.

        Args:
            target: имя целевого агента
            tool: название инструмента
            arguments: аргументы
            timeout: таймаут в секундах

        Returns:
            ACPResult или None при таймауте
        """
        correlation_id = uuid.uuid4().hex[:8***REMOVED***
        task = ACPTask(
            target=target,
            source=self._agent_name,
            tool=tool,
            arguments=arguments,
            timeout=timeout,
            correlation_id=correlation_id,
        )

        self._registry.register_pending_task(task)
        self._publish_event(ACP_TASK, {
            "task_id": task.task_id,
            "target": target,
            "source": self._agent_name,
            "tool": tool,
            "arguments": arguments,
            "correlation_id": correlation_id,
        ***REMOVED***)

        return self._registry.wait_for_result(task.task_id, timeout=timeout)

    def send_broadcast(self, message: str, data: Optional[Dict[str, Any***REMOVED******REMOVED*** = None) -> None:
        """Отправляет широковещательное сообщение всем агентам."""
        payload: Dict[str, Any***REMOVED*** = {
            "agent": self._agent_name,
            "message": message,
        ***REMOVED***
        if data:
            payload["data"***REMOVED*** = data
        self._publish_event(ACP_BROADCAST, payload)

    def send_status_update(self) -> None:
        """Отправляет обновление статуса."""
        self._publish_event(ACP_STATUS, {
            "agent": self._agent_name,
            "version": self._agent_version,
            "status": self._agent_status.value,
            "capabilities": self._capabilities,
        ***REMOVED***)

    # ── Internal ─────────────────────────────────────────────

    def _publish_event(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие в Event Bus."""
        if self._bus is None:
            return
        try:
            from freebuff_plugin_03.bridge import create_event
            self._bus.publish(create_event(
                event_type=event_type,
                source=self._agent_name,
                data=data,
            ))
        except Exception:
            pass

    def _heartbeat_loop(self) -> None:
        """Периодически отправляет heartbeat."""
        while self._running:
            time.sleep(30)  # каждые 30 секунд
            if not self._running:
                break
            try:
                self._publish_event(ACP_HEARTBEAT, {
                    "agent": self._agent_name,
                ***REMOVED***)
                # При необходимости чистим мёртвых агентов
                self._registry.prune_offline(max_age_seconds=120.0)
            except Exception:
                pass

    # ── Properties ──────────────────────────────────────────

    @property
    def status(self) -> AgentStatus:
        return self._agent_status

    @status.setter
    def status(self, new_status: AgentStatus) -> None:
        self._agent_status = new_status
        self.send_status_update()
