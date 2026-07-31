"""
presence.py — Agent Presence Engine (Phase 7: CoWork / Companion Platform).

Система отслеживания присутствия агентов в распределённой сети.
Строится поверх ACP (Agent Collaboration Protocol) и EventBus,
добавляя персистентность, богатые метаданные и MCP/CLI инструменты.

Архитектура:
  ┌──────────────┐     EventBus      ┌────────────────┐
  │  ACP Agent   │  presence.*       │  Presence      │
  │  Registry    │ ─────────────────►│  Engine        │
  │  (in-memory) │                   │  (persistent)  │
  └──────────────┘                   │                │
                                     │  SQLite:       │
  ┌──────────────┐                   │  - presence    │
  │  MCP Tools   │ ◄──── MCP ──────►│  - history     │
  │  (presence_*)│                   └────────────────┘
  └──────────────┘
                          ┌────────────────┐
                          │  CLI           │
                          │  list/get/     │
                          │  status/history│
                          └────────────────┘

Типы событий Presence:
  presence.online      — агент появился в сети
  presence.offline     — агент ушёл из сети
  presence.busy        — агент занят задачей
  presence.away        — агент отошёл
  presence.heartbeat   — пульс агента (каждые N секунд)
  presence.error       — ошибка агента
  presence.task_start  — агент начал задачу
  presence.task_end    — агент завершил задачу

Использование:
    from scripts.presence import PresenceEngine

    engine = PresenceEngine()
    engine.start()

    # Регистрация агента
    engine.register("buffy", capabilities={"code": "Code generation"***REMOVED***)

    # Обновление статуса
    engine.update_status("buffy", PresenceStatus.BUSY, current_task="Refactoring")

    # Получение статуса
    agent = engine.get("buffy")
    print(f"{agent.agent_name***REMOVED***: {agent.status.value***REMOVED***")

    engine.stop()

CLI:
    python scripts/presence.py list            # все агенты
    python scripts/presence.py get buffy       # детали агента
    python scripts/presence.py status          # диагностика
    python scripts/presence.py history         # история изменений
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional, Set

WORKSPACE = Path(__file__).resolve().parent
PRESENCE_DB = WORKSPACE / "data" / "presence.db"

DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_PRUNE_TIMEOUT = 120


class PresenceStatus:
    """Статус присутствия агента.

    ONLINE  — агент активен и доступен
    OFFLINE — агент отключён
    BUSY    — агент занят задачей
    AWAY    — агент отошёл
    ERROR   — у агента ошибка
    """

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    AWAY = "away"
    ERROR = "error"

    VALID = (ONLINE, OFFLINE, BUSY, AWAY, ERROR)

    @staticmethod
    def is_valid(status: str) -> bool:
        """Проверяет, что статус допустим."""
        return status in PresenceStatus.VALID


@dataclass
class AgentPresence:
    """Полная информация о присутствии агента.

    Attributes:
        agent_name: уникальное имя агента
        status: текущий статус присутствия
        version: версия агента
        capabilities: словарь capability_name → description
        current_task: текущая задача (если BUSY)
        uptime_seconds: время с момента последнего запуска агента
        host_info: информация о хосте (os, arch, python)
        last_seen: ISO timestamp последнего появления
        last_heartbeat: ISO timestamp последнего пульса
        registered_at: ISO timestamp регистрации
        metadata: произвольные метаданные
        error: сообщение об ошибке (если статус ERROR)
    """

    agent_name: str = ""
    status: str = PresenceStatus.ONLINE
    version: str = "1.0.0"
    capabilities: Dict[str, str***REMOVED*** = field(default_factory=dict)
    current_task: str = ""
    uptime_seconds: float = 0.0
    host_info: Dict[str, str***REMOVED*** = field(default_factory=dict)
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return asdict(self)


@dataclass
class PresenceHistoryEntry:
    """Запись в истории изменений присутствия."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    old_status: str = ""
    new_status: str = ""
    old_task: str = ""
    new_task: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)


class PresenceEngine:
    """Движок отслеживания присутствия агентов.

    Особенности:
      - SQLite персистентность (presence + history таблицы)
      - EventBus интеграция (presence.* события)
      - Heartbeat loop с авто-prune офлайн-агентов
      - История изменений статуса
      - Thread-safe
      - MCP-совместимый интерфейс
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        event_bus: Any = None,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        prune_timeout: int = DEFAULT_PRUNE_TIMEOUT,
    ):
        self._db_path = Path(db_path) if db_path else PRESENCE_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus
        self._heartbeat_interval = heartbeat_interval
        self._prune_timeout = prune_timeout
        self._lock = threading.RLock()
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread***REMOVED*** = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Открывает соединение с БД."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=3000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        """Инициализирует SQLite таблицы."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS presence (
                    agent_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'online',
                    version TEXT DEFAULT '1.0.0',
                    capabilities TEXT DEFAULT '{***REMOVED***',
                    current_task TEXT DEFAULT '',
                    uptime_seconds REAL DEFAULT 0,
                    host_info TEXT DEFAULT '{***REMOVED***',
                    last_seen TEXT,
                    last_heartbeat TEXT,
                    registered_at TEXT,
                    metadata TEXT DEFAULT '{***REMOVED***',
                    error TEXT DEFAULT ''
                )
                """
                )
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS presence_history (
                    id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    old_status TEXT DEFAULT '',
                    new_status TEXT NOT NULL,
                    old_task TEXT DEFAULT '',
                    new_task TEXT DEFAULT '',
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{***REMOVED***'
                )
                """
                )
                conn.commit()
            finally:
                conn.close()

    # ── Внутренние помощники ─────────────────────────────────────────

    def _publish(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие в EventBus (если подключён)."""
        if self._event_bus is None:
            return
        try:
            from scripts.event_bus import Event

            self._event_bus.publish(Event(event_type, data))
        except Exception:
            pass

    def _row_to_agent(self, row: sqlite3.Row) -> AgentPresence:
        """Конвертирует SQLite row в AgentPresence."""
        try:
            capabilities = json.loads(row["capabilities"***REMOVED***) if row["capabilities"***REMOVED*** else {***REMOVED***
        except (TypeError, ValueError):
            capabilities = {***REMOVED***
        try:
            host_info = json.loads(row["host_info"***REMOVED***) if row["host_info"***REMOVED*** else {***REMOVED***
        except (TypeError, ValueError):
            host_info = {***REMOVED***
        try:
            metadata = json.loads(row["metadata"***REMOVED***) if row["metadata"***REMOVED*** else {***REMOVED***
        except (TypeError, ValueError):
            metadata = {***REMOVED***
        return AgentPresence(
            agent_name=row["agent_name"***REMOVED***,
            status=row["status"***REMOVED***,
            version=row["version"***REMOVED*** or "1.0.0",
            capabilities=capabilities,
            current_task=row["current_task"***REMOVED*** or "",
            uptime_seconds=float(row["uptime_seconds"***REMOVED*** or 0),
            host_info=host_info,
            last_seen=row["last_seen"***REMOVED*** or "",
            last_heartbeat=row["last_heartbeat"***REMOVED*** or "",
            registered_at=row["registered_at"***REMOVED*** or "",
            metadata=metadata,
            error=row["error"***REMOVED*** or "",
        )

    def _load_agent(self, agent_name: str) -> Optional[AgentPresence***REMOVED***:
        """Загружает агента из БД (под блокировкой)."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM presence WHERE agent_name = ?", (agent_name,)
                ).fetchone()
                return self._row_to_agent(row) if row else None
            finally:
                conn.close()

    def _load_all_agents(self) -> List[AgentPresence***REMOVED***:
        """Загружает всех агентов из БД (под блокировкой)."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM presence").fetchall()
                return [self._row_to_agent(r) for r in rows***REMOVED***
            finally:
                conn.close()

    def _save_agent(self, agent: AgentPresence) -> None:
        """Сохраняет агента в БД (под блокировкой)."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO presence\n"
                    "                   (agent_name, status, version, capabilities, current_task,\n"
                    "                    uptime_seconds, host_info, last_seen, last_heartbeat,\n"
                    "                    registered_at, metadata, error)\n"
                    "                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        agent.agent_name,
                        agent.status,
                        agent.version,
                        json.dumps(agent.capabilities),
                        agent.current_task,
                        agent.uptime_seconds,
                        json.dumps(agent.host_info),
                        agent.last_seen,
                        agent.last_heartbeat,
                        agent.registered_at,
                        json.dumps(agent.metadata),
                        agent.error,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def _record_history(self, entry: PresenceHistoryEntry) -> None:
        """Записывает изменение в историю."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO presence_history\n"
                    "                   (id, agent_name, old_status, new_status, old_task, new_task, timestamp, metadata)\n"
                    "                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.id,
                        entry.agent_name,
                        entry.old_status,
                        entry.new_status,
                        entry.old_task,
                        entry.new_task,
                        entry.timestamp,
                        json.dumps(entry.metadata),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Запускает Presence Engine: восстанавливает uptime, стартует heartbeat thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
        # Восстанавливаем uptime: агенты с last_seen сохраняют время аптайма.
        for agent in self._load_all_agents():
            if agent.status == PresenceStatus.ONLINE:
                agent.uptime_seconds = 0.0
                self._save_agent(agent)
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="presence-heartbeat", daemon=True
        )
        self._heartbeat_thread.start()

    def stop(self) -> None:
        """Останавливает Presence Engine.

        Отмечает всех ONLINE агентов как OFFLINE и публикует
        события presence.offline для каждого.
        """
        with self._lock:
            self._running = False
        for agent in self._load_all_agents():
            if agent.status == PresenceStatus.ONLINE:
                self.update_status(agent.agent_name, PresenceStatus.OFFLINE)

    def _heartbeat_loop(self) -> None:
        """Периодически проверяет heartbeat и чистит офлайн-агентов."""
        while self._running:
            time.sleep(self._heartbeat_interval)
            if not self._running:
                break
            try:
                self._prune_offline()
            except Exception:
                pass

    def _prune_offline(self) -> int:
        """Удаляет агентов, не подававших heartbeat дольше prune_timeout.

        Returns:
            Количество удалённых агентов.
        """
        now = time.time()
        pruned = 0
        for agent in self._load_all_agents():
            if agent.status == PresenceStatus.OFFLINE:
                continue
            try:
                last_hb = datetime.fromisoformat(agent.last_heartbeat).timestamp()
            except (ValueError, TypeError):
                continue
            if now - last_hb > self._prune_timeout:
                # Помечаем агента OFFLINE (не удаляем — он остаётся в реестре).
                if self.update_status(agent.agent_name, PresenceStatus.OFFLINE):
                    pruned += 1
        return pruned

    # ── CRUD ──────────────────────────────────────────────────────────

    def register(
        self,
        agent_name: str,
        status: str = PresenceStatus.ONLINE,
        version: str = "1.0.0",
        capabilities: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
        host_info: Optional[Dict[str, str***REMOVED******REMOVED*** = None,
        metadata: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ) -> AgentPresence:
        """Регистрирует агента в системе присутствия.

        Если агент уже зарегистрирован — обновляет его данные.
        Публикует событие presence.online.

        Returns:
            AgentPresence зарегистрированного агента.
        """
        existing = self._load_agent(agent_name)
        now_ts = datetime.now(timezone.utc).isoformat()
        agent = AgentPresence(
            agent_name=agent_name,
            status=status if PresenceStatus.is_valid(status) else PresenceStatus.ONLINE,
            version=version,
            capabilities=capabilities or (existing.capabilities if existing else {***REMOVED***),
            host_info=host_info or (existing.host_info if existing else {***REMOVED***),
            metadata=metadata or (existing.metadata if existing else {***REMOVED***),
            last_seen=now_ts,
            last_heartbeat=now_ts,
            registered_at=existing.registered_at if existing else now_ts,
        )
        self._save_agent(agent)
        self._record_history(
            PresenceHistoryEntry(
                id=str(uuid.uuid4()),
                agent_name=agent_name,
                old_status=existing.status if existing else "",
                new_status=agent.status,
                old_task=existing.current_task if existing else "",
                new_task=agent.current_task,
            )
        )
        self._publish("presence.online", {"agent_name": agent_name, "status": agent.status***REMOVED***)
        return agent

    def unregister(self, agent_name: str) -> bool:
        """Удаляет агента из системы присутствия.

        Публикует событие presence.offline.

        Returns:
            True если агент был найден и удалён.
        """
        agent = self._load_agent(agent_name)
        if agent is None:
            return False
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM presence WHERE agent_name = ?", (agent_name,))
                conn.commit()
            finally:
                conn.close()
        self._record_history(
            PresenceHistoryEntry(
                id=str(uuid.uuid4()),
                agent_name=agent_name,
                old_status=agent.status,
                new_status=PresenceStatus.OFFLINE,
                old_task=agent.current_task,
                new_task="",
            )
        )
        self._publish("presence.offline", {"agent_name": agent_name***REMOVED***)
        return True

    def get(self, agent_name: str) -> Optional[AgentPresence***REMOVED***:
        """Получает информацию об агенте.

        Args:
            agent_name: имя агента

        Returns:
            AgentPresence или None если агент не найден.
        """
        return self._load_agent(agent_name)

    def update_status(
        self,
        agent_name: str,
        new_status: str,
        current_task: str = "",
        error: str = "",
        metadata: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ) -> Optional[AgentPresence***REMOVED***:
        """Обновляет статус агента.

        Args:
            agent_name: имя агента
            new_status: новый статус (online, offline, busy, away, error)
            current_task: текущая задача (если статус BUSY)
            error: сообщение об ошибке (если статус ERROR)
            metadata: дополнительные метаданные

        Returns:
            AgentPresence или None если агент не найден.
        """
        agent = self._load_agent(agent_name)
        if agent is None:
            return None
        if not PresenceStatus.is_valid(new_status):
            return None
        old_status = agent.status
        old_task = agent.current_task
        agent.status = new_status
        agent.current_task = current_task
        agent.error = error
        if metadata:
            agent.metadata.update(metadata)
        agent.last_seen = datetime.now(timezone.utc).isoformat()
        agent.uptime_seconds = (
            0.0 if new_status == PresenceStatus.ONLINE else agent.uptime_seconds
        )
        self._save_agent(agent)
        self._record_history(
            PresenceHistoryEntry(
                id=str(uuid.uuid4()),
                agent_name=agent_name,
                old_status=old_status,
                new_status=new_status,
                old_task=old_task,
                new_task=current_task,
            )
        )
        self._publish(f"presence.{new_status***REMOVED***", {"agent_name": agent_name, "status": new_status***REMOVED***)
        return agent

    def heartbeat(self, agent_name: str) -> Optional[AgentPresence***REMOVED***:
        """Обновляет heartbeat агента.

        Args:
            agent_name: имя агента

        Returns:
            AgentPresence или None если агент не найден.
        """
        agent = self._load_agent(agent_name)
        if agent is None:
            return None
        agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
        agent.last_seen = agent.last_heartbeat
        self._save_agent(agent)
        self._publish("presence.heartbeat", {"agent_name": agent_name***REMOVED***)
        return agent

    # ── Списки ────────────────────────────────────────────────────────

    def list_agents(
        self, status: Optional[str***REMOVED*** = None, capability: Optional[str***REMOVED*** = None
    ) -> List[AgentPresence***REMOVED***:
        """Список всех агентов с опциональной фильтрацией.

        Args:
            status: фильтр по статусу (online, offline, busy, away, error)
            capability: фильтр по capability (наличие определённой возможности)

        Returns:
            Список AgentPresence.
        """
        agents = self._load_all_agents()
        if status:
            agents = [a for a in agents if a.status == status***REMOVED***
        if capability:
            agents = [a for a in agents if capability in a.capabilities***REMOVED***
        return agents

    def list_online(self) -> List[AgentPresence***REMOVED***:
        """Список только ONLINE агентов."""
        return self.list_agents(status=PresenceStatus.ONLINE)

    def count(self) -> int:
        """Количество зарегистрированных агентов."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT COUNT(*) FROM presence").fetchone()
                return int(row[0***REMOVED***)
            finally:
                conn.close()

    # ── История ───────────────────────────────────────────────────────

    def get_history(
        self,
        agent_name: Optional[str***REMOVED*** = None,
        limit: int = 50,
        since: Optional[str***REMOVED*** = None,
    ) -> List[PresenceHistoryEntry***REMOVED***:
        """Получает историю изменений присутствия.

        Args:
            agent_name: фильтр по агенту
            limit: максимальное количество записей
            since: ISO timestamp — только записи после этой даты

        Returns:
            Список PresenceHistoryEntry.
        """
        query = "SELECT * FROM presence_history"
        conditions: List[str***REMOVED*** = [***REMOVED***
        params: List[Any***REMOVED*** = [***REMOVED***
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(query, params).fetchall()
                result = [***REMOVED***
                for r in rows:
                    try:
                        metadata = json.loads(r["metadata"***REMOVED***) if r["metadata"***REMOVED*** else {***REMOVED***
                    except (TypeError, ValueError):
                        metadata = {***REMOVED***
                    result.append(
                        PresenceHistoryEntry(
                            id=r["id"***REMOVED***,
                            agent_name=r["agent_name"***REMOVED***,
                            old_status=r["old_status"***REMOVED***,
                            new_status=r["new_status"***REMOVED***,
                            old_task=r["old_task"***REMOVED***,
                            new_task=r["new_task"***REMOVED***,
                            timestamp=r["timestamp"***REMOVED***,
                            metadata=metadata,
                        )
                    )
                return result
            finally:
                conn.close()

    # ── JSON-хелперы (для MCP) ────────────────────────────────────────

    def list_agents_json(
        self, status: Optional[str***REMOVED*** = None, capability: Optional[str***REMOVED*** = None
    ) -> Dict[str, Any***REMOVED***:
        """Возвращает JSON-совместимый список агентов (для MCP).

        Args:
            status: фильтр по статусу
            capability: фильтр по capability

        Returns:
            JSON-ready dict с агентами.
        """
        agents = self.list_agents(status=status, capability=capability)
        agent_dicts = [a.to_dict() for a in agents***REMOVED***
        return {
            "success": True,
            "total": len(agents),
            "agents": agent_dicts,
            "data": {"total": len(agents), "agents": agent_dicts***REMOVED***,
        ***REMOVED***

    def get_agent_json(self, agent_name: str) -> Dict[str, Any***REMOVED***:
        """Возвращает JSON-совместимые данные агента (для MCP)."""
        agent = self.get(agent_name)
        if agent is None:
            return {"success": False, "data": None, "found": False, "error": "Agent not found"***REMOVED***
        return {"success": True, "data": agent.to_dict(), "found": True***REMOVED***

    def get_history_json(
        self, agent_name: Optional[str***REMOVED*** = None, limit: int = 50
    ) -> Dict[str, Any***REMOVED***:
        """Возвращает JSON-совместимую историю (для MCP)."""
        entries = self.get_history(agent_name=agent_name, limit=limit)
        entry_dicts = [asdict(e) for e in entries***REMOVED***
        return {
            "success": True,
            "total": len(entries),
            "entries": entry_dicts,
            "data": {"total": len(entries), "entries": entry_dicts***REMOVED***,
        ***REMOVED***

    # ── Диагностика ───────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Диагностика Presence Engine.

        Returns:
            Словарь с состоянием Engine.
        """
        agents = self._load_all_agents()
        status_counts: Dict[str, int***REMOVED*** = {***REMOVED***
        for a in agents:
            status_counts[a.status***REMOVED*** = status_counts.get(a.status, 0) + 1
        last_change = "never"
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT timestamp FROM presence_history ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
                if row:
                    last_change = row[0***REMOVED***
            finally:
                conn.close()
        return {
            "status": "running" if self._running else "stopped",
            "running": self._running,
            "total_agents": len(agents),
            "online_count": status_counts.get(PresenceStatus.ONLINE, 0),
            "busy_count": status_counts.get(PresenceStatus.BUSY, 0),
            "error_count": status_counts.get(PresenceStatus.ERROR, 0),
            "status_counts": status_counts,
            "db_path": str(self._db_path),
            "heartbeat_interval": self._heartbeat_interval,
            "prune_timeout": self._prune_timeout,
            "eventbus_connected": self._event_bus is not None,
            "last_change": last_change,
        ***REMOVED***


def _status_icon(status: str) -> str:
    """Иконка для статуса присутствия."""
    return {
        PresenceStatus.ONLINE: "🟢",
        PresenceStatus.BUSY: "🟡",
        PresenceStatus.AWAY: "🟠",
        PresenceStatus.ERROR: "🔴",
        PresenceStatus.OFFLINE: "⚪",
    ***REMOVED***.get(status, "❓")


class Colors:
    """ANSI-цвета для CLI."""

    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"


# ── CLI ───────────────────────────────────────────────────────────────

def _cmd_list(args: argparse.Namespace) -> None:
    engine = PresenceEngine(db_path=args.db_path)
    agents = engine.list_agents(status=args.status, capability=args.capability)
    if not agents:
        print("📭 No agents registered")
        return
    print(f"Agent Presence ({len(agents)***REMOVED*** agents)")
    for a in agents:
        icon = _status_icon(a.status)
        task = f" — {a.current_task***REMOVED***" if a.current_task else ""
        print(f"  {icon***REMOVED*** {a.agent_name***REMOVED***: {a.status***REMOVED***{task***REMOVED*** (v{a.version***REMOVED***)")


def _cmd_get(args: argparse.Namespace) -> None:
    engine = PresenceEngine(db_path=args.db_path)
    agent = engine.get(args.agent)
    if agent is None:
        print(f"❌ Agent not found: {args.agent***REMOVED***")
        return
    print(f"Agent: {agent.agent_name***REMOVED***")
    print(f"  Status:      {_status_icon(agent.status)***REMOVED*** {agent.status***REMOVED***")
    print(f"  Version:     {agent.version***REMOVED***")
    print(f"  Task:        {agent.current_task or '—'***REMOVED***")
    print(f"  Uptime:      {agent.uptime_seconds:.0f***REMOVED***s")
    print(f"  Registered:  {agent.registered_at***REMOVED***")
    print(f"  Last seen:   {agent.last_seen***REMOVED***")
    if agent.capabilities:
        print("  Capabilities:")
        for name, desc in agent.capabilities.items():
            print(f"    • {name***REMOVED***: {desc***REMOVED***")


def _cmd_status(args: argparse.Namespace) -> None:
    engine = PresenceEngine(db_path=args.db_path)
    st = engine.get_status()
    print("Presence Engine Status")
    print(f"  Status:        {'🟢 Running' if st['running'***REMOVED*** else '🔴 Stopped'***REMOVED***")
    print(f"  Total agents:  {st['total_agents'***REMOVED******REMOVED***")
    print(f"  Online:        {st['online_count'***REMOVED******REMOVED***")
    print(f"  Busy:          {st['busy_count'***REMOVED******REMOVED***")
    print(f"  Error:         {st['error_count'***REMOVED******REMOVED***")
    print(f"  Heartbeat:     every {st['heartbeat_interval'***REMOVED******REMOVED***s")
    print(f"  Prune timeout: {st['prune_timeout'***REMOVED******REMOVED***s")
    print(f"  EventBus:      {'connected' if st['eventbus_connected'***REMOVED*** else 'not connected'***REMOVED***")
    print(f"  DB path:       {st['db_path'***REMOVED******REMOVED***")
    print(f"  Last change:   {st['last_change'***REMOVED******REMOVED***")


def _cmd_history(args: argparse.Namespace) -> None:
    engine = PresenceEngine(db_path=args.db_path)
    entries = engine.get_history(agent_name=args.agent, limit=args.limit, since=args.since)
    if not entries:
        print("📭 No history available")
        return
    print(f"Presence History ({len(entries)***REMOVED*** entries)")
    for e in entries:
        change = f"{e.old_status***REMOVED*** → {e.new_status***REMOVED***" if e.old_status else e.new_status
        print(f"  {e.timestamp***REMOVED***  {e.agent_name***REMOVED***: {change***REMOVED***")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Presence Engine — Agent Presence для CoWork Platform (Phase 7)"
    )
    parser.add_argument("--db", dest="db_path", default=None, help="Путь к БД")
    parser.add_argument("--json", action="store_true", help="JSON вывод")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Команда: list — список всех агентов.")
    p_list.add_argument("--status", help="Фильтр по статусу")
    p_list.add_argument("--capability", help="Фильтр по capability")

    p_get = sub.add_parser("get", help="Команда: get <agent> — детали агента.")
    p_get.add_argument("agent", help="Имя агента")

    sub.add_parser("status", help="Команда: status — диагностика Presence Engine.")

    p_hist = sub.add_parser("history", help="Команда: history — история изменений присутствия.")
    p_hist.add_argument("--agent", help="Фильтр по агенту")
    p_hist.add_argument("--limit", type=int, default=50, help="Лимит записей")
    p_hist.add_argument("--since", help="ISO timestamp, только после")

    args = parser.parse_args()

    handlers = {
        "list": _cmd_list,
        "get": _cmd_get,
        "status": _cmd_status,
        "history": _cmd_history,
    ***REMOVED***
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
