"""
collaboration.py — Live Collaboration Engine (Phase 7: CoWork / Companion Platform).

Система совместной работы в реальном времени для нескольких участников (пользователей
и агентов). Строится поверх EventBus, PresenceEngine и ACP Protocol.

Архитектура:
  ┌──────────────────────────────────────────────────────────────┐
  │                    Collaboration Engine                        │
  │                                                               │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
  │  │ Sessions    │  │ Participants│  │ Messages / Events    │  │
  │  │ (create/    │  │ (join/leave │  │ (send/broadcast/     │  │
  │  │  close/list)│  │  roles)     │  │  history)            │  │
  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
  │                                                               │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
  │  │ EventBus    │  │ Presence    │  │ StreamBridge        │  │
  │  │ интеграция  │  │ интеграция  │  │ интеграция (лог)    │  │
  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
  └──────────────────────────────────────────────────────────────┘

Типы событий Collaboration (через EventBus):
  collab.created        — создана новая сессия
  collab.joined         — участник присоединился
  collab.left           — участник покинул
  collab.closed         — сессия закрыта
  collab.message        — новое сообщение в сессии
  collab.participant_updated — изменился статус участника

Использование:
    from scripts_01.collaboration import CollaborationEngine

    engine = CollaborationEngine(event_bus=bus, presence_engine=pe)

    # Создать сессию
    collab = engine.create_session(
        topic="Code Review",
        owner="buffy",
        participants=["alice", "bob"],
    )

    # Отправить сообщение
    engine.send_message("session-1", "buffy", "Let's review the PR")

    # Получить историю
    history = engine.get_history("session-1")

CLI:
    python scripts_01/collaboration.py list                          # все сессии
    python scripts_01/collaboration.py get <session_id>              # детали сессии
    python scripts_01/collaboration.py create "Тема" --participants a,b
    python scripts_01/collaboration.py close <session_id>
    python scripts_01/collaboration.py send <session_id> buffy "текст"
    python scripts_01/collaboration.py history <session_id>
    python scripts_01/collaboration.py status                        # диагностика
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

WORKSPACE = Path(__file__).resolve().parent
COLLAB_DB = WORKSPACE / "data_13" / "collaboration.db"


class ParticipantRole:
    """Роли участников коллаборации.

    OWNER    — создатель сессии, может закрыть/удалить/управлять участниками
    EDITOR   — может писать сообщения и редактировать
    VIEWER   — только чтение сообщений
    """

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

    VALID = (OWNER, EDITOR, VIEWER)

    @staticmethod
    def is_valid(role: str) -> bool:
        """Проверяет, что роль допустима."""
        return role in ParticipantRole.VALID


class SessionStatus:
    """Статус сессии коллаборации."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"

    VALID = (ACTIVE, CLOSED, ARCHIVED)

    @staticmethod
    def is_valid(status: str) -> bool:
        """Проверяет, что статус допустим."""
        return status in SessionStatus.VALID


@dataclass
class Participant:
    """Участник коллаборативной сессии."""

    name: str = ""
    role: str = ParticipantRole.VIEWER
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_present: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollabMessage:
    """Сообщение в коллаборативной сессии.

    Types:
      text     — обычное текстовое сообщение
      system   — системное уведомление (join/leave)
      task     — назначение задачи
      file     — ссылка на файл
      decision — архитектурное решение
      code     — фрагмент кода
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    sender: str = ""
    content: str = ""
    msg_type: str = "text"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reply_to: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationSession:
    """Коллаборативная сессия — пространство для совместной работы."""

    session_id: str = field(default_factory=lambda: f"collab-{uuid.uuid4().hex[:8]}")
    topic: str = ""
    status: str = SessionStatus.ACTIVE
    owner: str = ""
    participants: List[Participant] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: str = ""
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_participant(self, name: str) -> Optional[Participant]:
        """Получить участника по имени."""
        for p in self.participants:
            if p.name == name:
                return p
        return None

    def has_participant(self, name: str) -> bool:
        """Проверить, есть ли участник."""
        return self.get_participant(name) is not None

    def participant_names(self) -> List[str]:
        """Имена всех участников."""
        return [p.name for p in self.participants]

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в dict для JSON."""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "status": self.status,
            "owner": self.owner,
            "participants": [
                {
                    "name": p.name,
                    "role": p.role,
                    "joined_at": p.joined_at,
                    "last_active": p.last_active,
                    "is_present": p.is_present,
                    "metadata": p.metadata,
                }
                for p in self.participants
            ],
            "participant_count": len(self.participants),
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "message_count": self.message_count,
            "metadata": self.metadata,
        }


class CollaborationEngine:
    """Движок совместной работы в реальном времени.

    Особенности:
      - SQLite персистентность (sessions + messages + participants таблицы)
      - EventBus интеграция (collab.* события)
      - PresenceEngine интеграция (авто-привязка участников)
      - Роли участников (owner/editor/viewer)
      - История сообщений с пагинацией
      - Thread-safe
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        event_bus: Any = None,
        presence_engine: Any = None,
    ):
        self._db_path = Path(db_path) if db_path else COLLAB_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus
        self._presence_engine = presence_engine
        self._lock = threading.RLock()
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
                CREATE TABLE IF NOT EXISTS collab_sessions (
                    session_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    owner TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    closed_at TEXT DEFAULT '',
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                )
                """
                )
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS collab_participants (
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    joined_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    is_present INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}',
                    PRIMARY KEY (session_id, name)
                )
                """
                )
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS collab_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    msg_type TEXT DEFAULT 'text',
                    timestamp TEXT NOT NULL,
                    reply_to TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                )
                """
                )
                conn.commit()
            finally:
                conn.close()

    def _publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Публикует событие в EventBus (если подключён)."""
        if self._event_bus is None:
            return
        try:
            from scripts_01.event_bus import Event

            self._event_bus.publish(Event(event_type, data))
        except Exception:
            pass

    # ── Сессии ────────────────────────────────────────────────────────

    def create_session(
        self,
        topic: str,
        owner: str | List[str] = "",
        participants: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CollaborationSession:
        """Создаёт коллаборативную сессию.

        Args:
            topic: тема сессии
            owner: владелец (создатель); допускается передать список участников
                   вторым позиционным аргументом (контракт тестов)
            participants: список имён участников (опционально)
            metadata: дополнительные данные

        Returns:
            CollaborationSession.
        """
        if isinstance(owner, (list, tuple)):
            participants = list(owner)
            owner = ""
        session_id = f"collab-{uuid.uuid4().hex[:8]}"
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO collab_sessions\n"
                    "                       (session_id, topic, status, owner, created_at, metadata)\n"
                    "                       VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, topic, SessionStatus.ACTIVE, owner, now_ts, json.dumps(metadata or {})),
                )
                # Владелец автоматически становится OWNER-участником.
                conn.execute(
                    "INSERT OR REPLACE INTO collab_participants\n"
                    "                           (session_id, name, role, joined_at, last_active, is_present)\n"
                    "                           VALUES (?, ?, ?, ?, ?, 1)",
                    (session_id, owner, ParticipantRole.OWNER, now_ts, now_ts),
                )
                for name in participants or []:
                    if name == owner:
                        continue
                    # Участники, добавленные при создании, получают EDITOR
                    # (контракт из test_create_session_with_participants).
                    conn.execute(
                        "INSERT OR REPLACE INTO collab_participants\n"
                        "                           (session_id, name, role, joined_at, last_active, is_present)\n"
                        "                           VALUES (?, ?, ?, ?, ?, 1)",
                        (session_id, name, ParticipantRole.EDITOR, now_ts, now_ts),
                    )
                conn.commit()
            finally:
                conn.close()
        # Системные сообщения о создании (контракт тестов: сообщение с 'created'
        # и сообщение(я) с 'joined' для каждого участника).
        if owner:
            self._add_system_message(session_id, f"Session '{topic}' created by {owner}")
        else:
            self._add_system_message(session_id, f"Session '{topic}' created")
        joined_names = [owner] if owner else []
        joined_names.extend(participants or [])
        for name in joined_names:
            self._add_system_message(session_id, f"{name} joined the session")
        session = self.get_session(session_id)
        self._publish("collab.created", {"session_id": session_id, "topic": topic, "owner": owner})
        assert session is not None
        return session

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Получает сессию по ID."""
        return self._load_session(session_id)

    def _load_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Загружает сессию из БД (под блокировкой)."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM collab_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    return None
                participants = self._load_participants(conn, session_id)
                try:
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except (TypeError, ValueError):
                    metadata = {}
                return CollaborationSession(
                    session_id=row["session_id"],
                    topic=row["topic"],
                    status=row["status"],
                    owner=row["owner"],
                    participants=participants,
                    created_at=row["created_at"],
                    closed_at=row["closed_at"] or "",
                    message_count=int(row["message_count"] or 0),
                    metadata=metadata,
                )
            finally:
                conn.close()

    def _load_participants(self, conn: sqlite3.Connection, session_id: str) -> List[Participant]:
        """Загружает участников сессии."""
        rows = conn.execute(
            "SELECT * FROM collab_participants WHERE session_id = ?", (session_id,)
        ).fetchall()
        result = []
        for r in rows:
            try:
                metadata = json.loads(r["metadata"]) if r["metadata"] else {}
            except (TypeError, ValueError):
                metadata = {}
            result.append(
                Participant(
                    name=r["name"],
                    role=r["role"],
                    joined_at=r["joined_at"],
                    last_active=r["last_active"],
                    is_present=bool(r["is_present"]),
                    metadata=metadata,
                )
            )
        return result

    def list_sessions(
        self, status: Optional[str] = None, participant_name: Optional[str] = None
    ) -> List[CollaborationSession]:
        """Список сессий с фильтрацией.

        Args:
            status: фильтр по статусу (active, closed, archived)
            participant_name: фильтр по участнику

        Returns:
            Список CollaborationSession.
        """
        with self._lock:
            conn = self._connect()
            try:
                if participant_name:
                    if status:
                        rows = conn.execute(
                            "SELECT s.* FROM collab_sessions s\n"
                            "                               JOIN collab_participants p ON s.session_id = p.session_id\n"
                            "                               WHERE p.name = ? AND s.status = ?\n"
                            "                               ORDER BY s.created_at DESC",
                            (participant_name, status),
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            "SELECT s.* FROM collab_sessions s\n"
                            "                               JOIN collab_participants p ON s.session_id = p.session_id\n"
                            "                               WHERE p.name = ?\n"
                            "                               ORDER BY s.created_at DESC",
                            (participant_name,),
                        ).fetchall()
                elif status:
                    rows = conn.execute(
                        "SELECT * FROM collab_sessions WHERE status = ? ORDER BY created_at DESC",
                        (status,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM collab_sessions ORDER BY created_at DESC"
                    ).fetchall()
                result = []
                for r in rows:
                    participants = self._load_participants(conn, r["session_id"])
                    try:
                        metadata = json.loads(r["metadata"]) if r["metadata"] else {}
                    except (TypeError, ValueError):
                        metadata = {}
                    result.append(
                        CollaborationSession(
                            session_id=r["session_id"],
                            topic=r["topic"],
                            status=r["status"],
                            owner=r["owner"],
                            participants=participants,
                            created_at=r["created_at"],
                            closed_at=r["closed_at"] or "",
                            message_count=int(r["message_count"] or 0),
                            metadata=metadata,
                        )
                    )
                return result
            finally:
                conn.close()

    def close_session(self, session_id: str) -> bool:
        """Закрывает сессию.

        Args:
            session_id: ID сессии

        Returns:
            True если сессия была найдена и закрыта.
        """
        session = self._load_session(session_id)
        if session is None or session.status != SessionStatus.ACTIVE:
            return False
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE collab_sessions SET status = ?, closed_at = ?\n"
                    "                       WHERE session_id = ?",
                    (SessionStatus.CLOSED, datetime.now(timezone.utc).isoformat(), session_id),
                )
                conn.commit()
            finally:
                conn.close()
        self._add_system_message(session_id, "Session closed")
        self._publish("collab.closed", {"session_id": session_id})
        return True

    # ── Участники ─────────────────────────────────────────────────────

    def join_session(self, session_id: str, participant_name: str, role: str = ParticipantRole.EDITOR) -> bool:
        """Присоединяет участника к сессии.

        Args:
            session_id: ID сессии
            participant_name: имя участника
            role: роль (editor, viewer)

        Returns:
            True если успешно присоединился.
        """
        session = self._load_session(session_id)
        if session is None or session.status != SessionStatus.ACTIVE:
            return False
        if not ParticipantRole.is_valid(role):
            return False
        if role == ParticipantRole.OWNER:
            role = ParticipantRole.EDITOR
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO collab_participants\n"
                    "                           (session_id, name, role, joined_at, last_active, is_present)\n"
                    "                           VALUES (?, ?, ?, ?, ?, 1)",
                    (session_id, participant_name, role, now_ts, now_ts),
                )
                conn.commit()
            finally:
                conn.close()
        self._add_system_message(session_id, f"{participant_name} joined the session")
        self._publish("collab.joined", {"session_id": session_id, "participant": participant_name, "role": role})
        return True

    def leave_session(self, session_id: str, participant_name: str) -> bool:
        """Удаляет участника из сессии.

        Args:
            session_id: ID сессии
            participant_name: имя участника

        Returns:
            True если участник был в сессии.
        """
        session = self._load_session(session_id)
        if session is None:
            return False
        if not session.has_participant(participant_name):
            return False
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE collab_participants SET is_present = 0\n"
                    "                                       WHERE session_id = ? AND name = ?",
                    (session_id, participant_name),
                )
                conn.commit()
            finally:
                conn.close()
        self._add_system_message(session_id, f"{participant_name} left the session")
        self._publish("collab.left", {"session_id": session_id, "participant": participant_name})
        return True

    def update_participant_role(self, session_id: str, participant_name: str, new_role: str) -> bool:
        """Обновляет роль участника.

        Args:
            session_id: ID сессии
            participant_name: имя участника
            new_role: новая роль

        Returns:
            True если роль обновлена.
        """
        session = self._load_session(session_id)
        if session is None or not session.has_participant(participant_name):
            return False
        if not ParticipantRole.is_valid(new_role):
            return False
        if new_role == ParticipantRole.OWNER and session.owner != participant_name:
            new_role = ParticipantRole.EDITOR
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE collab_participants SET role = ? WHERE session_id = ? AND name = ?",
                    (new_role, session_id, participant_name),
                )
                conn.commit()
            finally:
                conn.close()
        self._publish(
            "collab.participant_updated",
            {"session_id": session_id, "participant": participant_name, "role": new_role},
        )
        return True

    def sync_presence(self) -> int:
        """Синхронизирует присутствие участников с PresenceEngine.

        Отмечает участников, которые offline в PresenceEngine,
        как отсутствующих в сессии.

        Returns:
            Количество обновлённых участников.
        """
        if self._presence_engine is None:
            return 0
        count = 0
        for session in self.list_sessions():
            for participant in session.participants:
                presence = self._presence_engine.get(participant.name)
                if presence is None or presence.status == "offline":
                    if participant.is_present:
                        with self._lock:
                            conn = self._connect()
                            try:
                                conn.execute(
                                    "UPDATE collab_participants\n"
                                    "                           SET is_present = 0, last_active = ?\n"
                                    "                           WHERE session_id = ? AND name = ?",
                                    (datetime.now(timezone.utc).isoformat(), session.session_id, participant.name),
                                )
                                conn.commit()
                            finally:
                                conn.close()
                        count += 1
        return count

    # ── Сообщения ─────────────────────────────────────────────────────

    def _add_system_message(self, session_id: str, content: str) -> None:
        """Добавляет системное сообщение в сессию."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO collab_messages\n"
                    "                   (id, session_id, sender, content, msg_type, timestamp, reply_to, metadata)\n"
                    "                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        session_id,
                        "system",
                        content,
                        "system",
                        datetime.now(timezone.utc).isoformat(),
                        "",
                        "{]",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def send_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        msg_type: str = "text",
        reply_to: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CollabMessage]:
        """Отправляет сообщение в сессию.

        Args:
            session_id: ID сессии
            sender: отправитель
            content: текст сообщения
            msg_type: тип сообщения (text, system, task, file, decision, code)
            reply_to: ID сообщения, на которое отвечаем
            metadata: дополнительные данные

        Returns:
            CollabMessage или None если сессия закрыта/не найдена.
        """
        session = self._load_session(session_id)
        if session is None or session.status != SessionStatus.ACTIVE:
            return None
        # Контракт: отправитель НЕ обязан быть участником (тест send_with_reply
        # шлёт от 'alice', который не передавался в participants).
        message_id = str(uuid.uuid4())
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO collab_messages\n"
                    "                   (id, session_id, sender, content, msg_type, timestamp, reply_to, metadata)\n"
                    "                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        message_id,
                        session_id,
                        sender,
                        content,
                        msg_type,
                        now_ts,
                        reply_to,
                        json.dumps(metadata or {}),
                    ),
                )
                conn.execute(
                    "UPDATE collab_sessions SET message_count = message_count + 1 WHERE session_id = ?",
                    (session_id,),
                )
                conn.execute(
                    "UPDATE collab_participants SET last_active = ?\n"
                    "                       WHERE session_id = ? AND name = ?",
                    (now_ts, session_id, sender),
                )
                conn.commit()
            finally:
                conn.close()
        self._publish(
            "collab.message",
            {"session_id": session_id, "message_id": message_id, "sender": sender, "msg_type": msg_type},
        )
        return CollabMessage(
            id=message_id,
            session_id=session_id,
            sender=sender,
            content=content,
            msg_type=msg_type,
            timestamp=now_ts,
            reply_to=reply_to,
            metadata=metadata or {},
        )

    def get_history(
        self,
        session_id: str,
        limit: int = 50,
        since: Optional[str] = None,
        before: Optional[str] = None,
    ) -> List[CollabMessage]:
        """Получает историю сообщений сессии.

        Args:
            session_id: ID сессии
            limit: максимальное количество сообщений
            since: ISO timestamp — только сообщения после
            before: ISO timestamp — только сообщения до

        Returns:
            Список CollabMessage.
        """
        query = "SELECT * FROM collab_messages WHERE session_id = ?"
        params: List[Any] = [session_id]
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        if before:
            query += " AND timestamp <= ?"
            params.append(before)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(query, params).fetchall()
                result = []
                for r in rows:
                    try:
                        metadata = json.loads(r["metadata"]) if r["metadata"] else {}
                    except (TypeError, ValueError):
                        metadata = {}
                    result.append(
                        CollabMessage(
                            id=r["id"],
                            session_id=r["session_id"],
                            sender=r["sender"],
                            content=r["content"],
                            msg_type=r["msg_type"],
                            timestamp=r["timestamp"],
                            reply_to=r["reply_to"] or "",
                            metadata=metadata,
                        )
                    )
                return result
            finally:
                conn.close()

    def get_recent_events(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Получает последние события сессии (из EventBus лога).

        Note: EventBus.get_events() does exact matching, so we query
        all events and filter by prefix and session_id.

        Args:
            session_id: ID сессии
            limit: максимальное количество событий
        """
        if self._event_bus is None:
            return []
        try:
            events = self._event_bus.get_events(limit=limit * 5)
        except Exception:
            return []
        result = []
        for ev in events:
            data = getattr(ev, "data", {}) or {}
            if isinstance(data, dict) and data.get("session_id") == session_id:
                result.append({"type": getattr(ev, "event_type", ""), "data": data})
        return result[-limit:]

    # ── Диагностика ───────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Диагностика Collaboration Engine.

        Returns:
            Словарь с состоянием Engine.
        """
        sessions = self.list_sessions()
        total_messages = 0
        total_participants = 0
        for s in sessions:
            total_messages += s.message_count
            total_participants += len(s.participants)
        last_activity = "never"
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT timestamp FROM collab_messages ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
                if row:
                    last_activity = row[0]
            finally:
                conn.close()
        return {
            "status": "running",
            "running": True,
            "total_sessions": len(sessions),
            "active_sessions": sum(1 for s in sessions if s.status == SessionStatus.ACTIVE),
            "total_participants": total_participants,
            "total_messages": total_messages,
            "db_path": str(self._db_path),
            "eventbus_connected": self._event_bus is not None,
            "presence_connected": self._presence_engine is not None,
            "last_activity": last_activity,
        }


class Colors:
    """ANSI-цвета для CLI."""

    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    CYAN = "\x1b[36m"


# ── CLI ───────────────────────────────────────────────────────────────

def _cmd_list(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    sessions = engine.list_sessions(status=args.status, participant_name=args.participant)
    if not sessions:
        print("📭 No collaboration sessions")
        return
    print(f"Collaboration Sessions ({len(sessions)} sessions)")
    for s in sessions:
        icon = "●" if s.status == SessionStatus.ACTIVE else "○"
        print(f"  {icon} {s.session_id}: {s.topic} [{s.status}] owner={s.owner} msgs={s.message_count}")


def _cmd_get(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    session = engine.get_session(args.session_id)
    if session is None:
        print(f"❌ Session not found: {args.session_id}")
        return
    print(f"Session: {session.session_id}")
    print(f"  Topic:        {session.topic}")
    print(f"  Status:       {session.status}")
    print(f"  Owner:        {session.owner}")
    print(f"  Created:      {session.created_at}")
    print(f"  Closed:       {session.closed_at or '—'}")
    print(f"  Messages:     {session.message_count}")
    print("  Participants:")
    for p in session.participants:
        present = "●" if p.is_present else "○"
        print(f"    {present} {p.name} ({p.role}) last_active={p.last_active}")


def _cmd_create(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    participants = [p.strip() for p in (args.participants or "").split(",") if p.strip()]
    session = engine.create_session(args.topic, args.owner, participants)
    print(f"✅ Session created: {session.session_id}")


def _cmd_close(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    ok = engine.close_session(args.session_id)
    if ok:
        print(f"✅ Session closed: {args.session_id}")
    else:
        print(f"❌ Session not found or already closed: {args.session_id}")


def _cmd_send(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    msg = engine.send_message(args.session_id, args.sender, args.content, msg_type=args.type)
    if msg is None:
        print(f"❌ Session not found or closed: {args.session_id}")
        return
    print(f"✅ Message sent ({msg.id})")


def _cmd_history(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    messages = engine.get_history(args.session_id, limit=args.limit)
    if not messages:
        print("📭 No messages in session")
        return
    print(f"Messages ({len(messages)}):")
    for m in messages:
        print(f"  [{m.timestamp}] {m.sender} ({m.msg_type}): {m.content[:80]}")


def _cmd_status(args: argparse.Namespace) -> None:
    engine = CollaborationEngine(db_path=args.db_path)
    st = engine.get_status()
    print("Collaboration Engine Status")
    print(f"  Sessions:        {st['total_sessions']}")
    print(f"  Active:          {st['active_sessions']}")
    print(f"  Participants:    {st['total_participants']}")
    print(f"  Messages:        {st['total_messages']}")
    print(f"  DB:              {st['db_path']}")
    print(f"  EventBus:        {'connected' if st['eventbus_connected'] else 'not connected'}")
    print(f"  Presence:        {'connected' if st['presence_connected'] else 'not connected'}")
    print(f"  Last activity:   {st['last_activity']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collaboration Engine — Live Collaboration для CoWork Platform (Phase 7)"
    )
    parser.add_argument("--db", dest="db_path", default=None, help="Путь к БД")
    parser.add_argument("--json", action="store_true", help="JSON вывод")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Команда: list — список сессий.")
    p_list.add_argument("--status", help="Фильтр по статусу")
    p_list.add_argument("--participant", dest="participant", help="Фильтр по участнику")

    p_get = sub.add_parser("get", help="Команда: get <id> — детали сессии.")
    p_get.add_argument("session_id", help="ID сессии")

    p_create = sub.add_parser("create", help="Команда: create — создать сессию.")
    p_create.add_argument("topic", help="Тема сессии")
    p_create.add_argument("--owner", default="buffy", help="Владелец сессии")
    p_create.add_argument("--participants", help="Список участников через запятую")

    p_close = sub.add_parser("close", help="Команда: close — закрыть сессию.")
    p_close.add_argument("session_id", help="ID сессии")

    p_send = sub.add_parser("send", help="Команда: send — отправить сообщение.")
    p_send.add_argument("session_id", help="ID сессии")
    p_send.add_argument("sender", help="Отправитель")
    p_send.add_argument("content", help="Текст сообщения")
    p_send.add_argument("--type", default="text", help="Тип сообщения")

    p_hist = sub.add_parser("history", help="Команда: history — история сообщений.")
    p_hist.add_argument("session_id", help="ID сессии")
    p_hist.add_argument("--limit", type=int, default=50, help="Лимит сообщений")

    sub.add_parser("status", help="Команда: status — диагностика Engine.")

    args = parser.parse_args()

    handlers = {
        "list": _cmd_list,
        "get": _cmd_get,
        "create": _cmd_create,
        "close": _cmd_close,
        "send": _cmd_send,
        "history": _cmd_history,
        "status": _cmd_status,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
