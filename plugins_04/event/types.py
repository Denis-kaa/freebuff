"""Event Platform types — восстановлено v5.189.90 по контракту тестов
tests_09/test_event_store.py и спецификации docs_10/EVENT_PLATFORM_SPECIFICATION.md §11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EventEntry:
    """Одно событие в Store."""

    event_id: str
    event_type: str
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    session_id: str = ""
    project: str = ""
    user: str = ""
    timestamp: str = ""


@dataclass
class EventQuery:
    """Запрос к EventStore. event_type поддерживает wildcard: task.*, *."""

    event_type: Optional[str] = None
    source: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    project: Optional[str] = None
    user: Optional[str] = None
    since: str = ""
    until: str = ""
    data_search: str = ""              # FTS5 / LIKE поиск по data_json
    limit: int = 50
    offset: int = 0
    order: str = "desc"                # asc | desc


# ── Replay ──────────────────────────────────────────────────


@dataclass
class ReplayResult:
    """Результат воспроизведения событий."""

    total_events: int = 0
    delivered: int = 0
    errors: int = 0
    duration_ms: float = 0.0


@dataclass
class RebuildResult:
    """Результат пересборки состояния компонента из событий."""

    target: str = ""
    events_processed: int = 0
    errors: int = 0


# ── Timeline ────────────────────────────────────────────────


@dataclass
class TimelineEntry:
    """Элемент временной шкалы."""

    timestamp: str = ""
    event_type: str = ""
    icon: str = "📌"
    title: str = ""
    description: str = ""
    session_id: str = ""
    project: str = ""
    event_id: str = ""


@dataclass
class Timeline:
    """Временная шкала: entries + total."""

    entries: List[TimelineEntry] = field(default_factory=list)
    total: int = 0


# ── Audit ───────────────────────────────────────────────────


@dataclass
class AuditDecision:
    """Аудит решения о выборе runtime/модели."""

    policy_name: str = ""
    capability: str = ""
    runtime_selected: str = ""
    model_selected: str = ""
    cost_estimate: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditAction:
    """Аудит действия пользователя/системы."""

    actor: str = ""
    action: str = ""
    target: str = ""
    before: str = ""
    after: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditConfigChange:
    """Аудит изменения конфигурации."""

    component: str = ""
    setting: str = ""
    old_value: Any = None
    new_value: Any = None
    changed_by: str = ""
    version: int = 0


@dataclass
class AuditEntry:
    """Элемент audit trail (обёртка над событием)."""

    id: str = ""
    type: str = ""
    timestamp: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


# ── Pulse ───────────────────────────────────────────────────


@dataclass
class PulseEntry:
    """Элемент ленты событий (pulse feed)."""

    icon: str = "📌"
    title: str = ""
    description: str = ""
    timestamp: str = ""
    severity: str = "info"             # info | success | warning | error
    event_type: str = ""
    event_id: str = ""
