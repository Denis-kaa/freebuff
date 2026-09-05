"""AuditEngine — аудит решений, действий и изменений конфигурации (спека §8)."""

from __future__ import annotations

from typing import List, Optional

from plugins_04.event.store import EventStore
from plugins_04.event.types import (
    AuditAction,
    AuditConfigChange,
    AuditDecision,
    AuditEntry,
    EventQuery,
)

AUDIT_TYPES = ("audit.decision", "audit.action", "audit.config_change")


class AuditEngine:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    def log_decision(self, decision: AuditDecision) -> str:
        return self.store.store(
            event_type="audit.decision",
            source="policy_engine",
            data={
                "summary": (
                    f"DECISION policy={decision.policy_name!r} capability={decision.capability!r}"
                    f" runtime={decision.runtime_selected!r} model={decision.model_selected!r}"
                ),
                "policy_name": decision.policy_name,
                "capability": decision.capability,
                "runtime_selected": decision.runtime_selected,
                "model_selected": decision.model_selected,
                "cost_estimate": decision.cost_estimate,
                **decision.context,
            },
        )

    def log_action(self, action: AuditAction) -> str:
        return self.store.store(
            event_type="audit.action",
            source=action.actor or "system",
            data={
                "summary": f"ACTION {action.action} on {action.target}: {action.before} → {action.after}",
                "actor": action.actor,
                "action": action.action,
                "target": action.target,
                "before": action.before,
                "after": action.after,
                **action.context,
            },
        )

    def log_config_change(self, change: AuditConfigChange) -> str:
        return self.store.store(
            event_type="audit.config_change",
            source="config",
            data={
                "summary": (
                    f"CONFIG {change.component}.{change.setting}: "
                    f"{change.old_value!r} → {change.new_value!r} (v{change.version})"
                ),
                "component": change.component,
                "setting": change.setting,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by": change.changed_by,
                "version": change.version,
            },
        )

    def get_audit_trail(
        self,
        target_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEntry]:
        if target_type:
            # MCP-контракт: "decision" → "audit.decision"
            etype = f"audit.{target_type}" if not target_type.startswith("audit.") else target_type
        else:
            etype = "audit.*"
        q = EventQuery(event_type=etype, limit=limit)
        events = self.store.query(q)
        trail = []
        for e in events:
            data = e.data or {}
            # MCP-контракт: type без "audit." префикса (decision/action/config_change)
            short_type = e.event_type.rsplit(".", 1)[-1] if e.event_type else ""
            trail.append(
                AuditEntry(
                    id=e.event_id,
                    type=short_type,
                    timestamp=e.timestamp,
                    data=data,
                    summary=str(data.get("summary", "")),
                )
            )
        return trail

    def search_audit(self, text: str, limit: int = 50) -> List[AuditEntry]:
        events = self.store.query(EventQuery(event_type="audit.*", data_search=text, limit=limit))
        return [
            AuditEntry(
                id=e.event_id,
                type=e.event_type.rsplit(".", 1)[-1] if e.event_type else "",
                timestamp=e.timestamp,
                data=e.data or {},
                summary=str((e.data or {}).get("summary", "")),
            )
            for e in events
        ]

    @staticmethod
    def format_audit_log(trail: List[AuditEntry]) -> str:
        """Форматирование всего audit trail в текст."""
        if not trail:
            return "Нет записей аудита"
        lines = ["AUDIT LOG:"]
        lines.extend(AuditEngine.format_audit_entry(e) for e in trail)
        return "\n".join(lines)

    @staticmethod
    def format_audit_entry(entry: AuditEntry) -> str:
        kind = entry.type.rsplit(".", 1)[-1].upper() if entry.type else "EVENT"
        lines = [f"[{kind}]"]
        if entry.summary:
            lines.append(f"  {entry.summary}")
        elif entry.data:
            for key, value in entry.data.items():
                if key != "summary":
                    lines.append(f"  {key}: {value}")
        if entry.timestamp:
            lines.append(f"  at {entry.timestamp}")
        return "\n".join(lines)
