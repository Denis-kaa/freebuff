"""
Event Platform — Event Store, Replay, Timeline, Audit, Pulse.

Спецификация: docs_10/core/EVENT_PLATFORM_SPECIFICATION.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Event Store Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class EventEntry:
    """Запись в Event Store."""
    event_id: str
    event_type: str
    source: str
    correlation_id: str = ""
    session_id: str = ""
    project: str = ""
    user_id: str = ""
    data: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class EventQuery:
    """Запрос к Event Store."""
    event_type: Optional[str***REMOVED*** = None        # точное совпадение или wildcard "task.*"
    source: Optional[str***REMOVED*** = None            # "orchestrator", "memory_engine"
    correlation_id: Optional[str***REMOVED*** = None
    session_id: Optional[str***REMOVED*** = None
    project: Optional[str***REMOVED*** = None
    user_id: Optional[str***REMOVED*** = None
    since: Optional[str***REMOVED*** = None             # ISO timestamp
    until: Optional[str***REMOVED*** = None
    data_search: Optional[str***REMOVED*** = None       # полнотекстовый поиск в data_json
    limit: int = 50
    offset: int = 0
    order: str = "desc"                     # asc / desc


# ═══════════════════════════════════════════════════════════════
# Event Replay Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class ReplayResult:
    """Результат воспроизведения событий."""
    total_events: int = 0
    delivered: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    errors_list: List[str***REMOVED*** = field(default_factory=list)


@dataclass
class RebuildResult:
    """Результат перестройки состояния."""
    target: str = ""
    events_processed: int = 0
    items_created: int = 0
    duration_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Timeline Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class TimelineEntry:
    """Одна запись временной шкалы."""
    timestamp: str
    event_type: str
    icon: str = ""
    title: str = ""
    description: str = ""
    data: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    correlation_id: str = ""
    session_id: str = ""


@dataclass
class Timeline:
    """Временная шкала."""
    entries: List[TimelineEntry***REMOVED***
    total: int = 0
    project: str = ""
    since: str = ""
    until: str = ""


# ═══════════════════════════════════════════════════════════════
# Audit Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class AuditDecision:
    """Решение Policy Engine."""
    policy_name: str = ""
    capability: str = ""
    runtime_selected: str = ""
    provider_selected: str = ""
    model_selected: str = ""
    fallback_used: bool = False
    cost_estimate: float = 0.0
    context: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class AuditAction:
    """Действие пользователя или агента."""
    actor: str = ""
    action: str = ""
    target: str = ""
    before: Optional[str***REMOVED*** = None
    after: Optional[str***REMOVED*** = None
    reason: str = ""


@dataclass
class AuditConfigChange:
    """Изменение конфигурации."""
    component: str = ""
    setting: str = ""
    old_value: str = ""
    new_value: str = ""
    changed_by: str = ""
    version: int = 1


@dataclass
class AuditEntry:
    """Запись аудита."""
    id: str = ""
    type: str = ""     # "decision", "action", "config_change"
    timestamp: str = ""
    data: Dict[str, Any***REMOVED*** = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Pulse Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class PulseEntry:
    """Запись Pulse — отформатирована для UI."""
    icon: str = ""
    title: str = ""
    description: str = ""
    timestamp: str = ""
    severity: str = "info"     # info, warning, error, success
    actionable: bool = False
    action_label: str = ""
    action_data: Dict[str, Any***REMOVED*** = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Icons Mapping
# ═══════════════════════════════════════════════════════════════

EVENT_ICONS: Dict[str, str***REMOVED*** = {
    "system.startup": "🚀",
    "system.shutdown": "🛑",
    "system.error": "❌",
    "session.created": "▶️",
    "session.completed": "✅",
    "session.checkpoint": "📌",
    "task.created": "📋",
    "task.completed": "✅",
    "task.failed": "❌",
    "step.started": "🔄",
    "step.completed": "✅",
    "step.failed": "❌",
    "memory.stored": "💾",
    "memory.deleted": "🗑",
    "knowledge.indexed": "📚",
    "knowledge.searched": "🔍",
    "mcp.server.initialized": "🔗",
    "mcp.tool.called": "🔧",
    "bridge.connected": "🌉",
    "policy.evaluated": "⚖️",
    "audit.decision": "📝",
    "audit.action": "👤",
    "audit.config_change": "⚙️",
    "checkpoint.created": "📌",
***REMOVED***


def get_event_icon(event_type: str) -> str:
    """Возвращает иконку для типа события.

    Сначала ищет точное совпадение, затем wildcard.
    """
    icon = EVENT_ICONS.get(event_type)
    if icon:
        return icon

    # Wildcard: task.completed → ищем task.*
    parts = event_type.split(".")
    if len(parts) > 1:
        wildcard = f"{parts[0***REMOVED******REMOVED***.*"
        return EVENT_ICONS.get(wildcard, "📌")

    return "📌"


__all__ = [
    "EventEntry",
    "EventQuery",
    "ReplayResult",
    "RebuildResult",
    "TimelineEntry",
    "Timeline",
    "AuditDecision",
    "AuditAction",
    "AuditConfigChange",
    "AuditEntry",
    "PulseEntry",
    "EVENT_ICONS",
    "get_event_icon",
***REMOVED***
