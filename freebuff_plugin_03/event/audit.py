"""
Audit Engine — система аудита решений и действий.

Основание: docs_10/core/EVENT_PLATFORM_SPECIFICATION.md §6
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from freebuff_plugin_03.event import (
    AuditAction,
    AuditConfigChange,
    AuditDecision,
    AuditEntry,
    EventQuery,
)


class AuditEngine:
    """Система аудита.

    Фиксирует:
    - Какие политики были применены
    - Какие Runtime/Provider/Model были выбраны
    - Кто (пользователь/агент) что сделал
    - Когда были изменения конфигурации

    Использует EventStore с event_type = "audit.{type***REMOVED***".
    """

    def __init__(self, store: Any):
        self._store = store

    def log_decision(self, decision: AuditDecision) -> str:
        """Зафиксировать решение Policy Engine.

        Маппинг: AuditDecision → event_type="audit.decision", data_json=decision
        """
        return self._store.store(
            event_type="audit.decision",
            source="policy_engine",
            data=asdict(decision),
            correlation_id=decision.context.get("correlation_id", ""),
            session_id=decision.context.get("session_id", ""),
            metadata={
                "policy_name": decision.policy_name,
                "capability": decision.capability,
            ***REMOVED***,
        )

    def log_action(self, action: AuditAction) -> str:
        """Зафиксировать действие пользователя/агента.

        Маппинг: AuditAction → event_type="audit.action", data_json=action
        """
        return self._store.store(
            event_type="audit.action",
            source=action.actor,
            data=asdict(action),
            correlation_id="",
        )

    def log_config_change(self, change: AuditConfigChange) -> str:
        """Зафиксировать изменение конфигурации.

        Маппинг: AuditConfigChange → event_type="audit.config_change", data_json=change
        """
        return self._store.store(
            event_type="audit.config_change",
            source=change.changed_by,
            data=asdict(change),
            correlation_id="",
        )

    def get_audit_trail(
        self,
        target_type: str = "",
        target_id: str = "",
        limit: int = 50,
    ) -> List[AuditEntry***REMOVED***:
        """Получить аудит-трейл для объекта.

        Args:
            target_type: тип аудита ("decision", "action", "config_change")
            target_id: ID объекта (policy_name, actor, component)
            limit: максимальное количество записей

        Returns:
            Список AuditEntry
        """
        query = EventQuery(limit=limit, order="desc")

        if target_type:
            query.event_type = f"audit.{target_type***REMOVED***"

        entries = self._store.query(query)

        # Фильтр по target_id на уровне приложения
        if target_id:
            filtered = [***REMOVED***
            for e in entries:
                data = e.data
                if data.get("policy_name") == target_id:
                    filtered.append(e)
                elif data.get("actor") == target_id:
                    filtered.append(e)
                elif data.get("component") == target_id:
                    filtered.append(e)
            entries = filtered

        return [self._entry_to_audit_entry(e) for e in entries***REMOVED***

    def search_audit(self, query_str: str) -> List[AuditEntry***REMOVED***:
        """Поиск по аудит-логу."""
        query = EventQuery(
            data_search=query_str,
            event_type="audit.*",
            limit=50,
        )
        entries = self._store.query(query)
        return [self._entry_to_audit_entry(e) for e in entries***REMOVED***

    @staticmethod
    def _entry_to_audit_entry(event_entry) -> AuditEntry:
        """Конвертирует EventEntry в AuditEntry."""
        audit_type = event_entry.event_type.replace("audit.", "")
        return AuditEntry(
            id=event_entry.event_id,
            type=audit_type,
            timestamp=event_entry.timestamp,
            data=event_entry.data,
        )

    @staticmethod
    def format_audit_entry(entry: AuditEntry) -> str:
        """Форматирует AuditEntry в текст."""
        ts = entry.timestamp[:19***REMOVED***
        data = entry.data

        if entry.type == "decision":
            return (
                f"[{ts***REMOVED******REMOVED*** 📝 DECISION: {data.get('capability', '?')***REMOVED***\n"
                f"  Policy: {data.get('policy_name', '?')***REMOVED***\n"
                f"  Runtime: {data.get('runtime_selected', '?')***REMOVED*** → Model: {data.get('model_selected', '?')***REMOVED***\n"
                f"  Cost: ${data.get('cost_estimate', 0):.2f***REMOVED*** | Fallback: {'YES' if data.get('fallback_used') else 'NO'***REMOVED***"
            )

        elif entry.type == "action":
            return (
                f"[{ts***REMOVED******REMOVED*** 👤 ACTION: {data.get('action', '?')***REMOVED***\n"
                f"  Actor: {data.get('actor', '?')***REMOVED***\n"
                f"  Target: {data.get('target', '?')***REMOVED***\n"
                f"  Before: {data.get('before', '—')***REMOVED*** → After: {data.get('after', '—')***REMOVED***"
            )

        elif entry.type == "config_change":
            return (
                f"[{ts***REMOVED******REMOVED*** ⚙️ CONFIG: {data.get('setting', '?')***REMOVED***\n"
                f"  Component: {data.get('component', '?')***REMOVED***\n"
                f"  Old: {data.get('old_value', '—')***REMOVED*** → New: {data.get('new_value', '—')***REMOVED***\n"
                f"  By: {data.get('changed_by', '?')***REMOVED***"
            )

        return f"[{ts***REMOVED******REMOVED*** {entry.type***REMOVED***: {str(data)[:80***REMOVED******REMOVED***"

    def format_audit_log(self, entries: List[AuditEntry***REMOVED***) -> str:
        """Форматирует список AuditEntry в текст."""
        if not entries:
            return "📭 Нет записей аудита."

        lines = ["=== AUDIT LOG ===", ""***REMOVED***
        for entry in entries:
            lines.append(self.format_audit_entry(entry))
            lines.append("")
        return "\n".join(lines)
