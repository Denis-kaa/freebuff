"""
roles.py — Collaboration Roles Engine (Phase 7: CoWork / Companion Platform).

Система ролей для участников проекта (пользователей и агентов).
Определяет кто за что отвечает и какие действия может выполнять.

Роли (из IDEAS.md):
  Developer    — код, рефакторинг, тесты
  Reviewer     — code review, архитектурное ревью
  Documenter   — документация, ADR, CHANGELOG
  Researcher   — исследования, PoC, альтернативы
  Archiver     — память, Knowledge Graph, суммаризация
  Orchestrator — планирование, координация

Интеграции:
  - PresenceEngine: роль хранится в metadata агента
  - CollaborationEngine: роль определяет права в сессии
  - MCP Server: инструменты для управления ролями
  - CLI: управление ролями из командной строки

Использование:
    from scripts_01.roles import RoleEngine

    re = RoleEngine()
    re.assign_role("buffy", "developer")
    re.assign_role("alice", "reviewer")
    roles = re.get_roles("buffy")  # ["developer"***REMOVED***
    agents_by_role = re.list_by_role("developer")

CLI:
    python scripts_01/roles.py list                         # все назначения
    python scripts_01/roles.py get buffy                    # роли агента
    python scripts_01/roles.py assign buffy developer      # назначить роль
    python scripts_01/roles.py unassign buffy developer    # отозвать роль
    python scripts_01/roles.py by-role developer           # агенты по роли
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional, Set

WORKSPACE = Path(__file__).resolve().parent
ROLES_DB = WORKSPACE / "data_13" / "roles.db"

STANDARD_ROLES: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = {
    "developer": {
        "display_name": "Developer",
        "description": "Код, рефакторинг, тесты",
        "icon": "💻",
        "capabilities": ["coding", "testing", "refactoring"***REMOVED***,
        "priority": 1,
    ***REMOVED***,
    "reviewer": {
        "display_name": "Reviewer",
        "description": "Code review, архитектурное ревью",
        "icon": "👁️",
        "capabilities": ["review", "architecture"***REMOVED***,
        "priority": 2,
    ***REMOVED***,
    "documenter": {
        "display_name": "Documenter",
        "description": "Документация, ADR, CHANGELOG",
        "icon": "📝",
        "capabilities": ["documentation", "writing"***REMOVED***,
        "priority": 3,
    ***REMOVED***,
    "researcher": {
        "display_name": "Researcher",
        "description": "Исследования, PoC, альтернативы",
        "icon": "🔬",
        "capabilities": ["research", "analysis"***REMOVED***,
        "priority": 4,
    ***REMOVED***,
    "archiver": {
        "display_name": "Archiver",
        "description": "Память, Knowledge Graph, суммаризация",
        "icon": "🗄️",
        "capabilities": ["memory", "knowledge", "summarization"***REMOVED***,
        "priority": 5,
    ***REMOVED***,
    "orchestrator": {
        "display_name": "Orchestrator",
        "description": "Планирование, координация",
        "icon": "🎯",
        "capabilities": ["planning", "coordination", "delegation"***REMOVED***,
        "priority": 0,
    ***REMOVED***,
***REMOVED***


@dataclass
class RoleDefinition:
    """Определение роли."""

    name: str
    display_name: str
    description: str
    icon: str
    capabilities: List[str***REMOVED***
    priority: int

    @staticmethod
    def from_dict(name: str, data: dict) -> "RoleDefinition":
        """Создаёт RoleDefinition из словаря."""
        return RoleDefinition(
            name=name,
            display_name=data.get("display_name", name),
            description=data.get("description", ""),
            icon=data.get("icon", "❓"),
            capabilities=list(data.get("capabilities", [***REMOVED***)),
            priority=int(data.get("priority", 10)),
        )

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "capabilities": self.capabilities,
            "priority": self.priority,
        ***REMOVED***


@dataclass
class AgentRole:
    """Назначение роли агенту."""

    id: str
    agent_name: str = ""
    role_name: str = ""
    assigned_by: str = "system"
    assigned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализация в dict для JSON."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "role_name": self.role_name,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at,
            "metadata": self.metadata,
        ***REMOVED***


class RoleEngine:
    """Движок управления ролями участников.

    Особенности:
      - SQLite персистентность (role_assignments таблица)
      - Стандартные роли из IDEAS.md
      - Кастомные роли (можно добавлять)
      - Интеграция с PresenceEngine (sync)
      - Thread-safe
    """

    def __init__(self, db_path: Path | str | None = None, presence_engine: Any = None, collaboration_engine: Any = None):
        self._db_path = Path(db_path) if db_path else ROLES_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._presence_engine = presence_engine
        self._collaboration_engine = collaboration_engine
        self._custom_roles: Dict[str, RoleDefinition***REMOVED*** = {***REMOVED***
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
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
                CREATE TABLE IF NOT EXISTS role_assignments (
                    id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    role_name TEXT NOT NULL,
                    assigned_by TEXT DEFAULT 'system',
                    assigned_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{***REMOVED***'
                )
                """
                )
                conn.commit()
            finally:
                conn.close()

    # ── Роли ──────────────────────────────────────────────────────────

    def add_role(self, definition: RoleDefinition) -> bool:
        """Добавить кастомную роль (не перезаписывает стандартные)."""
        if definition.name in STANDARD_ROLES:
            return False
        with self._lock:
            if definition.name in self._custom_roles:
                return False
            self._custom_roles[definition.name***REMOVED*** = definition
        return True

    def list_roles(self) -> List[RoleDefinition***REMOVED***:
        """Список всех определений ролей (сортировка по приоритету, orchestrator первый)."""
        roles = [***REMOVED***
        for name, data in STANDARD_ROLES.items():
            roles.append(RoleDefinition.from_dict(name, data))
        with self._lock:
            roles.extend(self._custom_roles.values())
        roles.sort(key=lambda r: r.priority)
        return roles

    def get_role(self, name: str) -> Optional[RoleDefinition***REMOVED***:
        """Получить определение роли по имени."""
        data = STANDARD_ROLES.get(name)
        if data is not None:
            return RoleDefinition.from_dict(name, data)
        with self._lock:
            return self._custom_roles.get(name)

    def get_capabilities_for_role(self, role_name: str) -> List[str***REMOVED***:
        """Получить capabilities, соответствующие роли."""
        role = self.get_role(role_name)
        if role is None:
            return [***REMOVED***
        return list(role.capabilities)

    # ── Назначения ────────────────────────────────────────────────────

    def assign_role(self, agent_name: str, role_name: str, assigned_by: str = "system") -> bool:
        """Назначить роль агенту.

        Args:
            agent_name: имя агента
            role_name: имя роли
            assigned_by: кто назначил

        Returns:
            True если роль успешно назначена.
        """
        if self.get_role(role_name) is None:
            return False
        with self._lock:
            conn = self._connect()
            try:
                # Дедупликация: повторное назначение той же роли не создаёт дубль.
                existing = conn.execute(
                    "SELECT 1 FROM role_assignments WHERE agent_name = ? AND role_name = ?",
                    (agent_name, role_name),
                ).fetchone()
                if existing:
                    return True
                conn.execute(
                    "INSERT INTO role_assignments\n"
                    "                       (id, agent_name, role_name, assigned_by, assigned_at, metadata)\n"
                    "                       VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()),
                        agent_name,
                        role_name,
                        assigned_by,
                        datetime.now(timezone.utc).isoformat(),
                        "{***REMOVED***",
                    ),
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def unassign_role(self, agent_name: str, role_name: str) -> bool:
        """Отозвать роль у агента."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM role_assignments WHERE agent_name = ? AND role_name = ?",
                    (agent_name, role_name),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def unassign_all(self, agent_name: str) -> int:
        """Отозвать все роли агента.

        Returns:
            Количество отозванных ролей.
        """
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM role_assignments WHERE agent_name = ?",
                    (agent_name,),
                )
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()

    def get_roles(self, agent_name: str) -> List[str***REMOVED***:
        """Получить список ролей агента."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT role_name FROM role_assignments WHERE agent_name = ?",
                    (agent_name,),
                ).fetchall()
                return [r["role_name"***REMOVED*** for r in rows***REMOVED***
            finally:
                conn.close()

    def get_agent_roles_detailed(self, agent_name: str) -> List[AgentRole***REMOVED***:
        """Получить детальную информацию о ролях агента."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM role_assignments WHERE agent_name = ?",
                    (agent_name,),
                ).fetchall()
                return [self._row_to_agent_role(r) for r in rows***REMOVED***
            finally:
                conn.close()

    def list_assignments(self) -> List[AgentRole***REMOVED***:
        """Список всех назначений ролей."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM role_assignments ORDER BY agent_name, role_name"
                ).fetchall()
                return [self._row_to_agent_role(r) for r in rows***REMOVED***
            finally:
                conn.close()

    def list_by_role(self, role_name: str) -> List[str***REMOVED***:
        """Список агентов с указанной ролью."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT agent_name FROM role_assignments WHERE role_name = ?",
                    (role_name,),
                ).fetchall()
                return [r["agent_name"***REMOVED*** for r in rows***REMOVED***
            finally:
                conn.close()

    @staticmethod
    def _row_to_agent_role(row: sqlite3.Row) -> AgentRole:
        try:
            metadata = json.loads(row["metadata"***REMOVED***) if row["metadata"***REMOVED*** else {***REMOVED***
        except (TypeError, ValueError):
            metadata = {***REMOVED***
        return AgentRole(
            id=row["id"***REMOVED***,
            agent_name=row["agent_name"***REMOVED***,
            role_name=row["role_name"***REMOVED***,
            assigned_by=row["assigned_by"***REMOVED***,
            assigned_at=row["assigned_at"***REMOVED***,
            metadata=metadata,
        )

    # ── Capabilities ──────────────────────────────────────────────────

    def get_agent_capabilities(self, agent_name: str) -> List[str***REMOVED***:
        """Получить все capabilities агента на основе его ролей."""
        caps: Set[str***REMOVED*** = set()
        for role_name in self.get_roles(agent_name):
            caps.update(self.get_capabilities_for_role(role_name))
        return sorted(caps)

    # ── Интеграции ────────────────────────────────────────────────────

    def get_collab_role(self, agent_name: str) -> str:
        """Получить CollaborationEngine роль на основе project-ролей.

        Маппинг project-ролей → collaboration role:
          orchestrator → owner
          developer, reviewer → editor
          остальные → viewer
        """
        roles = self.get_roles(agent_name)
        if "orchestrator" in roles:
            return "owner"
        if "developer" in roles or "reviewer" in roles:
            return "editor"
        return "viewer"

    def sync_to_collab_session(self, session_id: str, agent_name: str) -> bool:
        """Синхронизирует роль агента в CollaborationSession.

        Args:
            session_id: ID сессии
            agent_name: имя агента

        Returns:
            True если роль обновлена.
        """
        if self._collaboration_engine is None:
            return False
        collab_role = self.get_collab_role(agent_name)
        try:
            return self._collaboration_engine.update_participant_role(
                session_id, agent_name, collab_role
            )
        except Exception:
            return False

    def sync_to_presence(self, agent_name: str) -> bool:
        """Синхронизирует роли агента с PresenceEngine.

        Сохраняет роли в metadata агента в PresenceEngine.
        """
        if self._presence_engine is None:
            return False
        roles = self.get_roles(agent_name)
        try:
            self._presence_engine.update_status(
                agent_name,
                "online",
                metadata={"roles": roles***REMOVED***,
            )
            return True
        except Exception:
            return False

    def sync_all_to_presence(self) -> int:
        """Синхронизирует все роли всех агентов с PresenceEngine.

        Returns:
            Количество синхронизированных агентов.
        """
        if self._presence_engine is None:
            return 0
        count = 0
        for assignment in self.list_assignments():
            if self.sync_to_presence(assignment.agent_name):
                count += 1
        return count

    # ── Статистика ────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any***REMOVED***:
        """Статистика системы ролей."""
        assignments = self.list_assignments()
        role_counts: Dict[str, int***REMOVED*** = {***REMOVED***
        agent_role_counts: Dict[str, int***REMOVED*** = {***REMOVED***
        for a in assignments:
            role_counts[a.role_name***REMOVED*** = role_counts.get(a.role_name, 0) + 1
            agent_role_counts[a.agent_name***REMOVED*** = agent_role_counts.get(a.agent_name, 0) + 1
        presence_synced = 0
        collab_synced = 0
        if self._presence_engine is not None:
            presence_synced = self.sync_all_to_presence()
        if self._collaboration_engine is not None:
            for a in assignments:
                if self.sync_to_collab_session(a.agent_name, a.agent_name):
                    collab_synced += 1
        return {
            "total_assignments": len(assignments),
            "defined_roles": len(self.list_roles()),
            "assigned_agents": len(agent_role_counts),
            "role_counts": role_counts,
            "agent_role_counts": agent_role_counts,
            "presence_synced": presence_synced,
            "collab_synced": collab_synced,
        ***REMOVED***


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
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    if args.roles:
        print("Defined Roles (")
        for role in engine.list_roles():
            print(f"  {role.icon***REMOVED*** {role.display_name***REMOVED*** ({role.name***REMOVED***) — {role.description***REMOVED***")
            print(f"     Capabilities: {', '.join(role.capabilities)***REMOVED***")
        return
    assignments = engine.list_assignments()
    if not assignments:
        print("📭 No role assignments")
        return
    print("Role Assignments (")
    for a in assignments:
        print(f"  {a.agent_name***REMOVED*** → {a.role_name***REMOVED*** (by {a.assigned_by***REMOVED*** at {a.assigned_at***REMOVED***)")


def _cmd_get(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    roles = engine.get_agent_roles_detailed(args.agent)
    if not roles:
        print(f"📭 No roles for '{args.agent***REMOVED***'")
        return
    print(f"Roles for '{args.agent***REMOVED***':")
    for r in roles:
        print(f"  {r.role_name***REMOVED*** — assigned by {r.assigned_by***REMOVED*** at {r.assigned_at***REMOVED***")


def _cmd_assign(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    ok = engine.assign_role(args.agent, args.role)
    if ok:
        print(f"✅ Role '{args.role***REMOVED***' assigned to '{args.agent***REMOVED***'")
    else:
        print(f"❌ Cannot assign '{args.role***REMOVED***' to '{args.agent***REMOVED***' — unknown role or error")


def _cmd_unassign(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    ok = engine.unassign_role(args.agent, args.role)
    if ok:
        print(f"✅ Role '{args.role***REMOVED***' removed from '{args.agent***REMOVED***'")
    else:
        print(f"⚠️ Role '{args.role***REMOVED***' not found for '{args.agent***REMOVED***'")


def _cmd_by_role(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    agents = engine.list_by_role(args.role)
    if not agents:
        print(f"📭 No agents with role '{args.role***REMOVED***'")
        return
    print(f"Agents with role '{args.role***REMOVED***':")
    for a in agents:
        print(f"  • {a***REMOVED***")


def _cmd_stats(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    stats = engine.get_stats()
    print("Role Engine Statistics")
    print(f"  Assignments:      {stats['total_assignments'***REMOVED******REMOVED***")
    print(f"  Defined roles:    {stats['defined_roles'***REMOVED******REMOVED***")
    print(f"  Presence sync:    {stats['presence_synced'***REMOVED******REMOVED***")
    print(f"  Collab sync:      {stats['collab_synced'***REMOVED******REMOVED***")
    if stats["role_counts"***REMOVED***:
        print("  By role:")
        for role, cnt in sorted(stats["role_counts"***REMOVED***.items()):
            print(f"    {role***REMOVED***: {cnt***REMOVED***")


def _cmd_sync(args: argparse.Namespace) -> None:
    engine = RoleEngine(db_path=args.db_path, presence_engine=None, collaboration_engine=None)
    count = engine.sync_all_to_presence()
    print(f"✅ Synced {count***REMOVED*** agents to PresenceEngine")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Role Engine — Collaboration Roles (Phase 7: CoWork)"
    )
    parser.add_argument("--db", dest="db_path", default=None, help="Путь к БД")
    parser.add_argument("--json", action="store_true", help="JSON вывод")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Команда: list — список всех назначений.")
    p_list.add_argument("--roles", action="store_true", help="Показать определения ролей")

    p_get = sub.add_parser("get", help="Команда: get — роли агента.")
    p_get.add_argument("agent", help="Имя агента")

    p_assign = sub.add_parser("assign", help="Команда: assign — назначить роль.")
    p_assign.add_argument("agent", help="Имя агента")
    p_assign.add_argument("role", help="Имя роли")

    p_unassign = sub.add_parser("unassign", help="Команда: unassign — отозвать роль.")
    p_unassign.add_argument("agent", help="Имя агента")
    p_unassign.add_argument("role", help="Имя роли")

    p_by = sub.add_parser("by-role", help="Команда: by-role — список агентов с ролью.")
    p_by.add_argument("role", help="Имя роли")

    sub.add_parser("stats", help="Команда: stats — статистика.")
    sub.add_parser("sync", help="Команда: sync — синхронизация с PresenceEngine.")

    args = parser.parse_args()

    handlers = {
        "list": _cmd_list,
        "get": _cmd_get,
        "assign": _cmd_assign,
        "unassign": _cmd_unassign,
        "by-role": _cmd_by_role,
        "stats": _cmd_stats,
        "sync": _cmd_sync,
    ***REMOVED***
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
