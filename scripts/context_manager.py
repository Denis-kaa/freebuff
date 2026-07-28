"""
ContextManager: unified session persistence and auto-summarization.
Объединяет паттерны из CLEAN_CORP, OpenClaw, Kwork Arbitr Context Keeper.

Возможности:
- Сохранение сессий в SQLite (как WorkerQueue)
- Автосуммаризация на чекпоинтах (как Kwork Arbitr Context Keeper)
- Чекпоинты состояния (как last_context.txt)
- Device identity tracking (как OpenClaw)
- Экспорт в Markdown (как SESSION_DUMP.md)
- Авто-очистка ABANDONED сессий
- CONTEXT_FULL триггер при превышении порога токенов
- Версионирование схемы БД
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

# ── Версионирование схемы ──────────────────────────────────────

SCHEMA_VERSION = 2
"""Текущая версия схемы БД.

История:
  1 — начальная схема (2026-07)
  2 — добавлены колонки: checkpoint_count, token_threshold (2026-07)
"""

# ── Порог контекста ────────────────────────────────────────────

DEFAULT_CONTEXT_THRESHOLD = 28000
"""Порог токенов, после которого создаётся CONTEXT_FULL чекпоинт.
DeepSeek v4 Flash: ~32K токенов, ставим запас ~28K.
"""


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CHECKPOINT = "checkpoint"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CheckpointType(str, Enum):
    MANUAL = "manual"        # пользователь явно сохранил
    AUTO_INTERVAL = "auto_interval"  # по таймеру (каждые N сообщений)
    PRE_CRITICAL = "pre_critical"    # перед важной операцией
    POST_STEP = "post_step"         # после завершения этапа
    CONTEXT_FULL = "context_full"   # контекст близок к лимиту


@dataclass
class SessionSnapshot:
    """Снимок состояния сессии."""
    session_id: str
    status: SessionStatus
    project: str
    topic: str
    message_count: int = 0
    token_estimate: int = 0
    last_summary: str = ""
    checkpoint_type: CheckpointType | None = None
    metadata: dict[str, Any***REMOVED*** = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContextManager:
    """
    Универсальный менеджер контекста для freebuff workspace.

    Использование:
        cm = ContextManager("/storage/emulated/0/PROJECTS/workstation/freebuff/")
        cm.start_session(project="termux-ai-agent", topic="v4.0 architecture")
        cm.save_checkpoint(summary="Implemented Worker Queue", ctype=CheckpointType.POST_STEP)
        cm.add_message({"role": "user", "content": "..."***REMOVED***)
        cm.export_markdown()

    EventBus: публикует session.created, session.completed, checkpoint.created
    """

    def __init__(
        self,
        workspace_root: str,
        context_threshold: int = DEFAULT_CONTEXT_THRESHOLD,
        event_bus: Any = None,
    ) -> None:
        self._root = workspace_root
        self._db_path = os.path.join(workspace_root, "data", "context.db")
        self._sessions_dir = os.path.join(workspace_root, "sessions")
        self._checkpoints_dir = os.path.join(workspace_root, "context", "checkpoints")
        self._summaries_dir = os.path.join(workspace_root, "context", "summaries")
        self._context_threshold = context_threshold
        self._lock = threading.Lock()
        self._event_bus = event_bus  # Optional EventBus instance

        for d in [self._sessions_dir, self._checkpoints_dir, self._summaries_dir***REMOVED***:
            os.makedirs(d, exist_ok=True)

        self._init_db()

    # ═══════════════════════════════════════════════════════════
    # Инициализация и миграции БД
    # ═══════════════════════════════════════════════════════════

    def _init_db(self) -> None:
        """Инициализирует БД и применяет миграции."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        with self._get_conn() as conn:
            # Текущая версия схемы
            current_version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***

            if current_version == 0:
                # Свежая БД — создаём всё с нуля
                self._create_schema_v1(conn)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION***REMOVED***")
                conn.commit()
                return

            # Применяем миграции последовательно
            if current_version < 2:
                self._migrate_v1_to_v2(conn)

            # Если версия выше текущей — несовместимость
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Schema version {current_version***REMOVED*** > {SCHEMA_VERSION***REMOVED***. "
                    "Downgrade not supported."
                )

    @staticmethod
    def _create_schema_v1(conn: sqlite3.Connection) -> None:
        """Схема v1 — начальная."""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'active',
                project TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                message_count INTEGER NOT NULL DEFAULT 0,
                token_estimate INTEGER NOT NULL DEFAULT 0,
                last_summary TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{***REMOVED***',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                checkpoint_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                token_estimate INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_session
                ON checkpoints(session_id, created_at);
        """)

    @staticmethod
    def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
        """Миграция v1→v2: без изменений схемы, только версия.

        В v2 добавили логику CONTEXT_FULL триггера — она работает
        на уровне Python, схема БД осталась той же.
        """
        conn.execute(f"PRAGMA user_version = 2")
        conn.commit()

    # ═══════════════════════════════════════════════════════════
    # Оценка токенов
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Оценивает количество токенов в тексте.

        Эвристика: ~1.3 токена на 4 символа (для русского/кода).
        На Termux/Android tiktoken недоступен (segfault в C-расширении),
        поэтому используем только текстовую эвристику.
        """
        if not text:
            return 1
        try:
            return max(1, int(len(text) / 4 * 1.3))
        except Exception:
            return len(text)  # грубо, но безопасно

    # ═══════════════════════════════════════════════════════════
    # Подключение
    # ═══════════════════════════════════════════════════════════

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Session Management
    # ═══════════════════════════════════════════════════════════

    def start_session(
        self,
        project: str = "",
        topic: str = "",
        session_id: str | None = None,
    ) -> SessionSnapshot:
        """Начинает новую сессию или загружает существующую."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc).isoformat()

        with self._lock, self._get_conn() as conn:
            existing = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            if existing:
                return SessionSnapshot(
                    session_id=existing["session_id"***REMOVED***,
                    status=SessionStatus(existing["status"***REMOVED***),
                    project=existing["project"***REMOVED***,
                    topic=existing["topic"***REMOVED***,
                    message_count=existing["message_count"***REMOVED***,
                    token_estimate=existing["token_estimate"***REMOVED***,
                    last_summary=existing["last_summary"***REMOVED***,
                    metadata=json.loads(existing["metadata"***REMOVED***),
                    created_at=existing["created_at"***REMOVED***,
                    updated_at=existing["updated_at"***REMOVED***,
                )

            conn.execute(
                """INSERT INTO sessions
                   (session_id, status, project, topic, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, SessionStatus.ACTIVE.value, project, topic, now, now),
            )
            conn.commit()

        # Публикуем событие
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="session.created",
                    source="context_manager",
                    data={
                        "session_id": session_id[:12***REMOVED***,
                        "project": project,
                        "topic": topic,
                    ***REMOVED***,
                ))
            except Exception:
                pass

        return SessionSnapshot(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            project=project,
            topic=topic,
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
        auto_checkpoint_interval: int = 0,
    ) -> dict[str, Any***REMOVED*** | None:
        """
        Добавляет сообщение в сессию.

        Если token_count не указан — вычисляется автоматически.
        Если auto_checkpoint_interval > 0 и количество сообщений
        кратно интервалу — создаёт авточекпоинт.
        Если общий token_estimate превышает context_threshold —
        создаёт CONTEXT_FULL чекпоинт.

        Возвращает словарь чекпоинта, если он был создан, иначе None.
        """
        if token_count is None:
            token_count = self._estimate_tokens(content)

        now = datetime.now(timezone.utc).isoformat()
        result_checkpoint: dict[str, Any***REMOVED*** | None = None

        with self._lock, self._get_conn() as conn:
            conn.execute(
                """INSERT INTO messages (session_id, role, content, token_count, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, role, content, token_count, now),
            )

            conn.execute(
                """UPDATE sessions
                   SET message_count = message_count + 1,
                       token_estimate = token_estimate + ?,
                       updated_at = ?
                   WHERE session_id = ?""",
                (token_count, now, session_id),
            )

            row = conn.execute(
                "SELECT message_count, token_estimate FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            conn.commit()

        if row is None:
            return None

        msg_count = row["message_count"***REMOVED***
        token_est = row["token_estimate"***REMOVED***

        # 1. AUTO_INTERVAL чекпоинт
        if auto_checkpoint_interval > 0 and msg_count % auto_checkpoint_interval == 0:
            result_checkpoint = self.save_checkpoint(
                session_id=session_id,
                summary=f"Auto-checkpoint at message {msg_count***REMOVED*** ({token_est***REMOVED*** tokens)",
                ctype=CheckpointType.AUTO_INTERVAL,
            )

        # 2. CONTEXT_FULL чекпоинт (если превысили порог и ещё не создали)
        if (result_checkpoint is None
                and self._context_threshold > 0
                and token_est >= self._context_threshold):
            result_checkpoint = self.save_checkpoint(
                session_id=session_id,
                summary=f"Context nearly full: {token_est***REMOVED*** tokens (threshold {self._context_threshold***REMOVED***). Consider summarizing.",
                ctype=CheckpointType.CONTEXT_FULL,
            )

        return result_checkpoint

    def save_checkpoint(
        self,
        session_id: str,
        summary: str,
        ctype: CheckpointType = CheckpointType.MANUAL,
    ) -> dict[str, Any***REMOVED***:
        """Сохраняет чекпоинт с суммаризацией.

        Если тип чекпоинта CONTEXT_FULL — дополнительно сохраняет
        автоматический rollup-конспект в context/context_full_rollup.md
        для быстрой вставки в новый контекст.

        Возвращаемый словарь включает "rollup_path" для CONTEXT_FULL.
        """
        now = datetime.now(timezone.utc).isoformat()
        rollup_path: str | None = None

        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT message_count, token_estimate FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Session not found: {session_id***REMOVED***")

            conn.execute(
                """INSERT INTO checkpoints
                   (session_id, checkpoint_type, summary, message_count, token_estimate, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, ctype.value, summary, row["message_count"***REMOVED***, row["token_estimate"***REMOVED***, now),
            )

            conn.execute(
                "UPDATE sessions SET last_summary = ?, updated_at = ? WHERE session_id = ?",
                (summary, now, session_id),
            )
            conn.commit()

            # Сохраняем в файл для быстрого доступа
            self._write_checkpoint_file(session_id, summary, ctype, row["message_count"***REMOVED***)

        # ═══════════════════════════════════════════════════════
        # CONTEXT_FULL -> автоматический rollup-конспект
        # ═══════════════════════════════════════════════════════
        if ctype == CheckpointType.CONTEXT_FULL:
            try:
                rollup_path = self._save_context_rollup(session_id)
            except Exception as e:
                print(f"⚠️ Rollup error: {e***REMOVED***", file=sys.stderr)

        # Публикуем событие чекпоинта
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="checkpoint.created",
                    source="context_manager",
                    data={
                        "session_id": session_id[:12***REMOVED***,
                        "checkpoint_type": ctype.value,
                        "message_count": row["message_count"***REMOVED***,
                        "token_estimate": row["token_estimate"***REMOVED***,
                        "summary": summary[:200***REMOVED***,
                    ***REMOVED***,
                ))
            except Exception:
                pass

        return {
            "session_id": session_id,
            "checkpoint_type": ctype.value,
            "summary": summary,
            "message_count": row["message_count"***REMOVED***,
            "token_estimate": row["token_estimate"***REMOVED***,
            "created_at": now,
            "rollup_path": rollup_path,
        ***REMOVED***

    def _save_context_rollup(
        self, session_id: str, max_tokens: int = 2000
    ) -> str:
        """Генерирует и сохраняет rollup-конспект для CONTEXT_FULL.

        Создаёт файл context/context_full_rollup.md, который содержит
        сжатый конспект сессии для инжекта в новый контекст.

        Returns:
            Путь к файлу конспекта.
        """
        conspect = self.export_checkpoint_summary(
            session_id, max_tokens=max_tokens
        )

        # Добавляем заголовок AUTO-ROLLUP
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        rollup = (
            f"> 🔄 **Auto-Rollup** generated at {ts***REMOVED***\n"
            f"> *Context threshold reached — inject this into the next session to maintain continuity*\n"
            f">\n"
            f"> File: `context/context_full_rollup.md`\n"
            f"\n"
            f"---\n"
            f"\n"
            f"{conspect***REMOVED***\n"
        )

        filepath = os.path.join(self._root, "context", "context_full_rollup.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(rollup)

        return filepath

    def _write_checkpoint_file(
        self,
        session_id: str,
        summary: str,
        ctype: CheckpointType,
        msg_count: int,
    ) -> None:
        """Записывает чекпоинт в Markdown-файл."""
        filename = f"checkpoint_{session_id[:8***REMOVED******REMOVED***_{ctype.value***REMOVED***_{msg_count***REMOVED***.md"
        filepath = os.path.join(self._checkpoints_dir, filename)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        content = f"""# Checkpoint: {ctype.value***REMOVED***
**Session:** {session_id***REMOVED***
**Messages:** {msg_count***REMOVED***
**Timestamp:** {ts***REMOVED***

## Summary
{summary***REMOVED***

---
_Generated by ContextManager_
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def get_session(self, session_id: str) -> SessionSnapshot | None:
        """Загружает сессию."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

            if row is None:
                return None

            return SessionSnapshot(
                session_id=row["session_id"***REMOVED***,
                status=SessionStatus(row["status"***REMOVED***),
                project=row["project"***REMOVED***,
                topic=row["topic"***REMOVED***,
                message_count=row["message_count"***REMOVED***,
                token_estimate=row["token_estimate"***REMOVED***,
                last_summary=row["last_summary"***REMOVED***,
                metadata=json.loads(row["metadata"***REMOVED***),
                created_at=row["created_at"***REMOVED***,
                updated_at=row["updated_at"***REMOVED***,
            )

    def get_checkpoints(self, session_id: str) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Возвращает все чекпоинты сессии."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM checkpoints
                   WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows***REMOVED***

    def get_messages(
        self, session_id: str, limit: int = 100
    ) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Возвращает последние сообщения сессии (от старых к новым)."""
        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                """SELECT role, content, token_count, timestamp
                   FROM messages
                   WHERE session_id = ?
                   ORDER BY id ASC
                   LIMIT ?""",
                (session_id, limit),
            ).fetchall()

        return [dict(row) for row in rows***REMOVED***

    def get_message_count(self, session_id: str) -> int:
        """Возвращает количество сообщений в сессии."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return row["cnt"***REMOVED*** if row else 0

    def get_last_summary(self, session_id: str) -> str:
        """Возвращает последнюю суммаризацию для контекста."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_summary FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return row["last_summary"***REMOVED*** if row else ""

    def get_total_token_estimate(self, session_id: str) -> int:
        """Возвращает общий token_estimate сессии."""
        with self._lock, self._get_conn() as conn:
            row = conn.execute(
                "SELECT token_estimate FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return row["token_estimate"***REMOVED*** if row else 0

    def complete_session(self, session_id: str) -> None:
        """Завершает сессию (помечает как COMPLETED)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                (SessionStatus.COMPLETED.value, now, session_id),
            )
            conn.commit()

        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="session.completed",
                    source="context_manager",
                    data={"session_id": session_id[:12***REMOVED******REMOVED***,
                ))
            except Exception:
                pass

    def update_session_status(
        self, session_id: str, status: SessionStatus
    ) -> None:
        """Обновляет статус сессии."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                (status.value, now, session_id),
            )
            conn.commit()

    def list_sessions(
        self, status: SessionStatus | None = None
    ) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Список всех сессий."""
        with self._lock, self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    """SELECT session_id, status, project, topic, message_count,
                               token_estimate, updated_at
                       FROM sessions WHERE status = ? ORDER BY updated_at DESC""",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT session_id, status, project, topic, message_count,
                               token_estimate, updated_at
                       FROM sessions ORDER BY updated_at DESC"""
                ).fetchall()

        return [dict(row) for row in rows***REMOVED***

    # ═══════════════════════════════════════════════════════════
    # Очистка ABANDONED сессий
    # ═══════════════════════════════════════════════════════════

    def prune_abandoned(self, days: int = 1) -> int:
        """Удаляет ABANDONED сессии старше N дней.

        Returns:
            Количество удалённых сессий.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        deleted = 0

        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                """SELECT session_id FROM sessions
                   WHERE status = ? AND updated_at < ?""",
                (SessionStatus.ABANDONED.value, cutoff),
            ).fetchall()

            for row in rows:
                sid = row["session_id"***REMOVED***
                conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
                conn.execute("DELETE FROM checkpoints WHERE session_id = ?", (sid,))
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
                deleted += 1

            if deleted:
                conn.commit()

        # Чистим файлы чекпоинтов
        for row in rows:
            for f in os.listdir(self._checkpoints_dir):
                if f.startswith(f"checkpoint_{row['session_id'***REMOVED***[:8***REMOVED******REMOVED***"):
                    try:
                        os.remove(os.path.join(self._checkpoints_dir, f))
                    except OSError:
                        pass

        return deleted

    def auto_abandon_stale(self, days: int = 1) -> int:
        """Переводит старые ACTIVE сессии в ABANDONED.

        Сессия считается «старой», если:
        - статус ACTIVE
        - updated_at старше N дней
        - message_count == 0 (пустая сессия)

        Returns:
            Количество помеченных сессий.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        abandoned = 0

        with self._lock, self._get_conn() as conn:
            rows = conn.execute(
                """SELECT session_id FROM sessions
                   WHERE status = ?
                     AND updated_at < ?
                     AND message_count = 0""",
                (SessionStatus.ACTIVE.value, cutoff),
            ).fetchall()

            for row in rows:
                conn.execute(
                    "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                    (SessionStatus.ABANDONED.value,
                     datetime.now(timezone.utc).isoformat(),
                     row["session_id"***REMOVED***),
                )
                abandoned += 1

            if abandoned:
                conn.commit()

        return abandoned

    # ═══════════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════════

    def export_markdown(self, session_id: str) -> str:
        """Экспортирует сессию в Markdown (как SESSION_DUMP.md)."""
        session = self.get_session(session_id)
        if session is None:
            return ""

        checkpoints = self.get_checkpoints(session_id)
        messages = self.get_messages(session_id)

        lines = [
            f"# Session: {session.topic or session.session_id[:8***REMOVED******REMOVED***",
            f"**Project:** {session.project***REMOVED***",
            f"**Messages:** {session.message_count***REMOVED***",
            f"**Tokens (est):** {session.token_estimate***REMOVED***",
            f"**Status:** {session.status.value***REMOVED***",
            f"**Created:** {session.created_at***REMOVED***",
            f"**Updated:** {session.updated_at***REMOVED***",
            "",
            "## Checkpoints",
            "",
        ***REMOVED***

        for cp in checkpoints:
            lines.append(f"- [{cp['checkpoint_type'***REMOVED******REMOVED******REMOVED*** ({cp['message_count'***REMOVED******REMOVED*** msgs): {cp['summary'***REMOVED***[:100***REMOVED******REMOVED***")

        lines.extend(["", "## Messages", ""***REMOVED***)

        for msg in messages:
            role_icon = {"user": "🧑", "assistant": "🤖", "system": "⚙️"***REMOVED***.get(msg["role"***REMOVED***, "❓")
            content_preview = msg["content"***REMOVED***[:200***REMOVED***.replace("\n", " ")
            lines.append(f"{role_icon***REMOVED*** **{msg['role'***REMOVED******REMOVED*****: {content_preview***REMOVED***")

        export = "\n".join(lines)

        filepath = os.path.join(self._summaries_dir, f"session_{session_id[:8***REMOVED******REMOVED***.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(export)

        return export

    def export_checkpoint_summary(
        self, session_id: str, max_tokens: int = 2000
    ) -> str:
        """Экспортирует сжатый конспект сессии (для вставки в новый контекст)."""
        session = self.get_session(session_id)
        checkpoints = self.get_checkpoints(session_id)

        if session is None:
            return ""

        lines = [
            f"# Context Resume: {session.topic***REMOVED***",
            f"_Session {session.session_id[:8***REMOVED******REMOVED*** | {session.message_count***REMOVED*** messages | {session.token_estimate***REMOVED*** tokens_",
            "",
            "## Key Points",
        ***REMOVED***

        for cp in checkpoints:
            lines.append(f"- {cp['summary'***REMOVED******REMOVED***")

        lines.append("")
        lines.append(f"**Latest:** {session.last_summary***REMOVED***")

        result = "\n".join(lines)

        # Обрезаем по токенам, а не по длине
        if self._estimate_tokens(result) > max_tokens:
            result = self._truncate_to_tokens(result, max_tokens)

        return result

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        """Обрезает текст до указанного количества токенов."""
        chars_per_token = 4.0 / 1.3  # ~3 символа на токен
        max_chars = int(max_tokens * chars_per_token)
        if len(text) <= max_chars:
            return text
        return text[:max_chars***REMOVED*** + "\n\n... (truncated)"

    def get_context_status(self, session_id: str) -> dict[str, Any***REMOVED***:
        """Возвращает статус контекста для сессии."""
        session = self.get_session(session_id)
        if session is None:
            return {"error": "Session not found"***REMOVED***

        return {
            "session_id": session_id[:8***REMOVED***,
            "message_count": session.message_count,
            "token_estimate": session.token_estimate,
            "threshold": self._context_threshold,
            "usage_percent": round(
                session.token_estimate / self._context_threshold * 100, 1
            ) if self._context_threshold > 0 else 0,
            "is_full": session.token_estimate >= self._context_threshold
            if self._context_threshold > 0 else False,
            "status": session.status.value,
        ***REMOVED***
