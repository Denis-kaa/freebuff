"""
project_pulse.py — Project Pulse Engine (Phase 7: CoWork / Companion Platform).

Лента изменений проекта: git-коммиты, изменения файлов, события EventBus.
Предоставляет единый таймлайн всей активности в проекте.

Архитектура:
  ┌─────────────────────────────────────────────────────┐
  │                  Project Pulse Engine                 │
  │                                                       │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
  │  │ Git      │  │ File     │  │ EventBus │           │
  │  │ Scanner  │  │ Watcher  │  │ Listener │           │
  │  └──────────┘  └──────────┘  └──────────┘           │
  │       │              │              │                │
  │       ▼              ▼              ▼                │
  │  ┌──────────────────────────────────────────────┐    │
  │  │            Pulse Timeline (SQLite)            │    │
  │  └──────────────────────────────────────────────┘    │
  └─────────────────────────────────────────────────────┘

Типы событий пульса:
  git.commit      — новый коммит
  git.branch      — создание/переключение ветки
  file.created    — новый файл
  file.modified   — изменение файла
  file.deleted    — удаление файла
  event.system    — системное событие
  event.task      — событие задачи
  event.collab    — событие коллаборации

Использование:
    from scripts_01.project_pulse import ProjectPulse

    pulse = ProjectPulse()
    pulse.scan_git()        # проверить git
    pulse.scan_files()      # проверить файлы
    entries = pulse.list()  # получить ленту

CLI:
    python scripts_01/project_pulse.py list          # лента
    python scripts_01/project_pulse.py list --limit 20
    python scripts_01/project_pulse.py stats         # статистика
    python scripts_01/project_pulse.py scan          # полное сканирование
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent
PULSE_DB = WORKSPACE / "data_13" / "project_pulse.db"

PULSE_TYPES: Dict[str, str] = {
    "git.commit": "💾",
    "git.branch": "🌿",
    "file.created": "📄",
    "file.modified": "✏️",
    "file.deleted": "🗑️",
    "file.renamed": "📝",
    "event.system": "⚙️",
    "event.task": "📋",
    "event.step": "🔧",
    "event.collab": "💬",
    "event.memory": "🧠",
    "event.plugin": "🔌",
    "event.presence": "🟢",
    "event.metrics": "📊",
    "event.unknown": "❓",
}

SNAPSHOT_FILE = WORKSPACE / ".pulse_snapshot.json"


def get_pulse_icon(event_type: str) -> str:
    """Get icon for pulse entry type."""
    return PULSE_TYPES.get(event_type, PULSE_TYPES["event.unknown"])


@dataclass
class PulseEntry:
    """Одна запись в ленте изменений проекта."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    title: str = ""
    description: str = ""
    source: str = ""
    ref: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в dict для JSON."""
        d = asdict(self)
        d["icon"] = get_pulse_icon(self.event_type)
        return d

    @property
    def icon(self) -> str:
        """Иконка записи по её типу."""
        return get_pulse_icon(self.event_type)


class ProjectPulse:
    """Project Pulse — лента изменений проекта.

    Собирает изменения из трёх источников:
      - Git: коммиты, ветки
      - Файлы: создание, модификация, удаление
      - EventBus: события системы

    Хранит всё в SQLite и предоставляет единый API для просмотра.
    """

    def __init__(self, db_path: Path | str | None = None, workspace: Path | str | None = None, event_bus: Any = None):
        self._db_path = Path(db_path) if db_path else PULSE_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._workspace = Path(workspace) if workspace else WORKSPACE
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._subscription = None
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
                CREATE TABLE IF NOT EXISTS pulse_entries (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    ref TEXT DEFAULT '',
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
                """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pulse_timestamp ON pulse_entries(timestamp)"
                )
                conn.commit()
            finally:
                conn.close()

    # ── CRUD ──────────────────────────────────────────────────────────

    def add_entry(self, entry: PulseEntry) -> str:
        """Добавляет внешнюю запись в пульс.

        Args:
            entry: PulseEntry для добавления

        Returns:
            ID записи.
        """
        self._insert(entry)
        return entry.id

    def _add_entry(
        self,
        description: str = "",
        source: str = "",
        event_type: str = "",
        title: str = "",
        ref: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Низкоуровневое добавление записи в пульс.

        Все параметры доступны как keywords (event_type/title/source/ref —
        контракт фикстуры pulse_with_entries). Возвращает ID созданной записи
        (контракт test_get_entry: entry.id == _add_entry(...)).
        """
        entry = PulseEntry(
            id=str(uuid.uuid4()),
            event_type=event_type,
            title=title,
            description=description,
            source=source,
            ref=ref,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._insert(entry)
        return entry.id

    def _insert(self, entry: PulseEntry) -> None:
        """Добавляет запись в БД (thread-safe, дедупликация по ref)."""
        if entry.ref and self._exists_by_ref(entry.ref):
            return
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO pulse_entries\n"
                    "                       (id, event_type, title, description, source, ref, timestamp, metadata)\n"
                    "                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.id,
                        entry.event_type,
                        entry.title,
                        entry.description,
                        entry.source,
                        entry.ref,
                        entry.timestamp,
                        json.dumps(entry.metadata),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def get(self, entry_id: str | PulseEntry) -> Optional[PulseEntry]:
        """Получает запись по ID (или извлекает ID из PulseEntry)."""
        if isinstance(entry_id, PulseEntry):
            entry_id = entry_id.id
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM pulse_entries WHERE id = ?", (entry_id,)
                ).fetchone()
                return self._row_to_entry(row) if row else None
            finally:
                conn.close()

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[PulseEntry]:
        """Получает ленту изменений.

        Args:
            limit: максимальное количество записей
            offset: смещение
            event_type: фильтр по типу события
            source: фильтр по источнику (git, file, event)
            since: ISO timestamp — только записи после

        Returns:
            Список PulseEntry.
        """
        query = "SELECT * FROM pulse_entries"
        conditions: List[str] = []
        params: List[Any] = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_entry(r) for r in rows]
            finally:
                conn.close()

    def list_json(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """JSON-совместимый список записей (для MCP).

        Returns:
            JSON-ready dict.
        """
        entries = self.list(limit=limit, event_type=event_type, source=source)
        entry_dicts = [e.to_dict() for e in entries]
        return {
            "success": True,
            "total": len(entries),
            "entries": entry_dicts,
            "data": {"total": len(entries), "entries": entry_dicts},
        }

    def clear(self) -> int:
        """Очищает все записи.

        Returns:
            Количество удалённых записей.
        """
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM pulse_entries")
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()

    def _row_to_entry(self, row: sqlite3.Row) -> PulseEntry:
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (TypeError, ValueError):
            metadata = {}
        return PulseEntry(
            id=row["id"],
            event_type=row["event_type"],
            title=row["title"],
            description=row["description"],
            source=row["source"],
            ref=row["ref"],
            timestamp=row["timestamp"],
            metadata=metadata,
        )

    def _exists_by_ref(self, ref: str) -> bool:
        """Проверяет, есть ли уже запись с таким ref."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT 1 FROM pulse_entries WHERE ref = ? LIMIT 1", (ref,)
                ).fetchone()
                return row is not None
            finally:
                conn.close()

    def _entry_exists(self, ref: str) -> bool:
        """Алиас для _exists_by_ref (контракт тестов)."""
        return self._exists_by_ref(ref)

    # ── Git-сканер ────────────────────────────────────────────────────

    def scan_git(self) -> int:
        """Сканирует git-репозиторий на новые коммиты и ветки.

        Использует `git log` и `git branch` для обнаружения изменений.

        Returns:
            Количество новых записей в пульсе.
        """
        added = 0
        git_dir = self._workspace
        try:
            # Коммиты.
            result = subprocess.run(
                ["git", "-C", str(git_dir), "log", "--oneline", "--all", "-n", "50"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split(" ", 1)
                hash_id = parts[0]
                subject = parts[1] if len(parts) > 1 else ""
                ref = f"git:commit:{hash_id}"
                if self._exists_by_ref(ref):
                    continue
                self._insert(
                    PulseEntry(
                        id=str(uuid.uuid4()),
                        event_type="git.commit",
                        title=f"Commit: {hash_id[:8]}",
                        description=subject,
                        source="git",
                        ref=ref,
                    )
                )
                added += 1
            # Ветки.
            result = subprocess.run(
                ["git", "-C", str(git_dir), "branch", "-a"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                branch = line.strip().lstrip("* ").strip()
                if not branch:
                    continue
                if branch.startswith("remotes/origin/"):
                    branch = branch[len("remotes/origin/"):]
                ref = f"git:branch:{branch}"
                if self._exists_by_ref(ref):
                    continue
                self._insert(
                    PulseEntry(
                        id=str(uuid.uuid4()),
                        event_type="git.branch",
                        title=f"Branch: {branch}",
                        description="",
                        source="git",
                        ref=ref,
                    )
                )
                added += 1
        except (subprocess.SubprocessError, OSError):
            return added
        return added

    # ── Файловый сканер ───────────────────────────────────────────────

    def scan_files(self, paths: Optional[List[str]] = None) -> int:
        """Сканирует изменения файлов в workspace.

        Сравнивает текущее состояние файлов с предыдущим снимком.

        Args:
            paths: конкретные пути для сканирования (опционально)

        Returns:
            Количество новых записей в пульсе.
        """
        snapshot = self._load_snapshot()
        current: Dict[str, float] = {}
        base = self._workspace
        if paths:
            for p in paths:
                fp = Path(p)
                if fp.exists() and fp.is_file():
                    current[str(fp)] = fp.stat().st_mtime
        else:
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    fp = Path(root) / fname
                    if ".git" in fp.parts:
                        continue
                    try:
                        current[str(fp)] = fp.stat().st_mtime
                    except OSError:
                        continue
        added = 0
        now = datetime.now(timezone.utc).isoformat()
        for path, mtime in current.items():
            prev = snapshot.get(path)
            rel = os.path.relpath(path, base)
            if prev is None:
                self._insert(
                    PulseEntry(
                        id=str(uuid.uuid4()),
                        event_type="file.created",
                        title=f"New file: {rel}",
                        description="",
                        source="file",
                        ref=f"file:created:{path}",
                        timestamp=now,
                    )
                )
                added += 1
            elif prev != mtime:
                self._insert(
                    PulseEntry(
                        id=str(uuid.uuid4()),
                        event_type="file.modified",
                        title=f"File changed: {rel}",
                        description="",
                        source="file",
                        ref=f"file:modified:{path}:{mtime}",
                        timestamp=now,
                    )
                )
                added += 1
        # Удалённые файлы.
        for path in snapshot:
            if path not in current:
                rel = os.path.relpath(path, base)
                self._insert(
                    PulseEntry(
                        id=str(uuid.uuid4()),
                        event_type="file.deleted",
                        title=f"File removed: {rel}",
                        description="",
                        source="file",
                        ref=f"file:deleted:{path}",
                        timestamp=now,
                    )
                )
                added += 1
        self._save_snapshot(current)
        return added

    def _load_snapshot(self) -> Dict[str, float]:
        """Загружает предыдущий снимок файлов."""
        snap_file = self._workspace / ".pulse_snapshot.json"
        try:
            if snap_file.exists():
                with open(snap_file, "r", encoding="utf-8") as f:
                    return {k: float(v) for k, v in json.load(f).items()}
        except (OSError, ValueError, TypeError):
            pass
        return {}

    def _save_snapshot(self, snapshot: Dict[str, float]) -> None:
        """Сохраняет снимок файлов."""
        snap_file = self._workspace / ".pulse_snapshot.json"
        try:
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except OSError:
            pass

    # ── EventBus ──────────────────────────────────────────────────────

    def subscribe_eventbus(self) -> bool:
        """Подписывается на EventBus для автоматического сбора событий.

        Returns:
            True если подписка успешна.
        """
        if self._event_bus is None:
            return False
        if self._subscription is not None:
            return True
        try:
            self._subscription = self._event_bus.subscribe("*", self._on_event)
            return True
        except Exception:
            return False

    def unsubscribe_eventbus(self) -> None:
        """Отписывается от EventBus."""
        if self._event_bus is None or self._subscription is None:
            return
        try:
            self._event_bus.unsubscribe(self._subscription)
        except Exception:
            pass
        self._subscription = None

    def _on_event(self, event: Any) -> None:
        """Обработчик событий EventBus — сохраняет в пульс."""
        event_type = getattr(event, "type", "") or getattr(event, "event_type", "") or ""
        data = getattr(event, "data", {}) or {}
        pulse_type = self._map_event_type(event_type)
        title = event_type
        if isinstance(data, dict):
            title = data.get("title") or data.get("task") or data.get("step") or data.get("message") or event_type
        ref = f"event:{event_type}:{getattr(event, 'id', '')}"
        if self._exists_by_ref(ref):
            return
        self._insert(
            PulseEntry(
                id=str(uuid.uuid4()),
                event_type=pulse_type,
                title=str(title)[:200],
                description="",
                source="event",
                ref=ref,
                metadata={"original_type": event_type} if isinstance(data, dict) else {},
            )
        )

    _EVENT_CATEGORY_MAP: Dict[str, str] = {
        "system": "system",
        "task": "task",
        "step": "step",
        "collab": "collab",
        "memory": "memory",
        "plugin": "plugin",
        "presence": "presence",
        "metrics": "metrics",
        "git": "git",
        "file": "file",
        "event": "event",
    }

    def _map_event_type(self, event_type: str) -> str:
        """Maps EventBus event type to pulse event type.

        Правило: первая часть типа события (до '.') маппится на
        "event.<category>"; неизвестные категории → "event.unknown".
        Уже сопоставленные типы (event.*) возвращаются как есть.
        """
        if not event_type:
            return "event.unknown"
        if event_type.startswith("event."):
            return event_type
        category = event_type.split(".", 1)[0]
        mapped = self._EVENT_CATEGORY_MAP.get(category)
        if mapped is None:
            return "event.unknown"
        return f"event.{mapped}"

    # ── Полное сканирование и статистика ──────────────────────────────

    def full_scan(self) -> Dict[str, int]:
        """Полное сканирование: git + файлы.

        Returns:
            Словарь {source: new_entries_count}. Ключ 'files' — число
            новых файловых записей (контракт тестов).
        """
        git_count = self.scan_git()
        files_count = self.scan_files()
        return {
            "git": git_count,
            "file": files_count,
            "files": files_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Статистика пульса.

        Returns:
            Словарь со статистикой.
        """
        with self._lock:
            conn = self._connect()
            try:
                total = conn.execute("SELECT COUNT(*) FROM pulse_entries").fetchone()[0]
                type_rows = conn.execute(
                    "SELECT event_type, COUNT(*) as cnt FROM pulse_entries GROUP BY event_type"
                ).fetchall()
                source_rows = conn.execute(
                    "SELECT source, COUNT(*) as cnt FROM pulse_entries GROUP BY source"
                ).fetchall()
                last_row = conn.execute(
                    "SELECT timestamp FROM pulse_entries ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
                last_24h_row = conn.execute(
                    "SELECT COUNT(*) FROM pulse_entries WHERE timestamp >= ?",
                    (datetime.now(timezone.utc).isoformat(),),
                ).fetchone()
                return {
                    "total_entries": int(total),
                    "type_counts": {r["event_type"]: int(r["cnt"]) for r in type_rows},
                    "source_counts": {r["source"]: int(r["cnt"]) for r in source_rows},
                    "last_entry": last_row[0] if last_row else "never",
                    "last_24h": int(last_24h_row[0]),
                    "db_path": str(self._db_path),
                }
            finally:
                conn.close()


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
    pulse = ProjectPulse(db_path=args.db_path)
    entries = pulse.list(limit=args.limit, event_type=args.type, source=args.source)
    if not entries:
        print("📭 No pulse entries")
        return
    print(f"Project Pulse ({len(entries)} entries)")
    for e in entries:
        icon = get_pulse_icon(e.event_type)
        print(f"  {icon} [{e.timestamp}] {e.title}")
        if e.description:
            print(f"     {e.description[:100]}")


def _cmd_stats(args: argparse.Namespace) -> None:
    pulse = ProjectPulse(db_path=args.db_path)
    stats = pulse.get_stats()
    print("Project Pulse Statistics")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Last 24h:      {stats['last_24h']}")
    print(f"  Last entry:    {stats['last_entry']}")
    if stats["type_counts"]:
        print("  By type:")
        for t, cnt in sorted(stats["type_counts"].items()):
            print(f"    {get_pulse_icon(t)} {t}: {cnt}")
    if stats["source_counts"]:
        print("  By source:")
        for s, cnt in sorted(stats["source_counts"].items()):
            print(f"    {s}: {cnt}")


def _cmd_scan(args: argparse.Namespace) -> None:
    pulse = ProjectPulse(db_path=args.db_path)
    print("🔍 Scanning project...")
    result = pulse.full_scan()
    print(f"✅ Done: {result['git']} git entries, {result['files']} file entries")


def _cmd_watch(args: argparse.Namespace) -> None:
    pulse = ProjectPulse(db_path=args.db_path)
    ok = pulse.subscribe_eventbus()
    if ok:
        print("✅ Subscribed to EventBus")
    else:
        print("⚠️ EventBus not available (pulse will still track git+files)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project Pulse — лента изменений проекта (Phase 7: CoWork)"
    )
    parser.add_argument("--db", dest="db_path", default=None, help="Путь к БД")
    parser.add_argument("--json", action="store_true", help="JSON вывод")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Команда: list — лента изменений.")
    p_list.add_argument("--limit", type=int, default=50, help="Лимит записей")
    p_list.add_argument("--type", help="Фильтр по типу события")
    p_list.add_argument("--source", help="Фильтр по источнику (git, file, event)")

    sub.add_parser("stats", help="Команда: stats — статистика.")
    sub.add_parser("scan", help="Команда: scan — полное сканирование.")
    sub.add_parser("watch", help="Команда: watch — подписка на EventBus.")

    args = parser.parse_args()

    handlers = {
        "list": _cmd_list,
        "stats": _cmd_stats,
        "scan": _cmd_scan,
        "watch": _cmd_watch,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
