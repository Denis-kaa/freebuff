"""Automation — авто-действия при task-событиях.

Действия:
- escalate: при task.failed — уведомление об ошибке
- notify_complete: при task.completed — уведомление об успехе
- rerun: опциональный rerun при task.failed (пока заглушка)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


class AutomationRule:
    """Правило автоматизации: event_type → действие."""

    def __init__(
        self,
        event_type: str,
        action: str,
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None,
        enabled: bool = True,
    ):
        self.event_type = event_type
        self.action = action
        self.handler = handler
        self.enabled = enabled

    def matches(self, event_type: str) -> bool:
        """Проверяет подходит ли событие под правило (поддержка wildcard)."""
        if self.event_type.endswith(".*"):
            prefix = self.event_type[:-2]
            return event_type.startswith(prefix)
        return self.event_type == event_type


class TaskAutomation:
    """Движок автоматизации task-событий.

    Содержит набор правил (AutomationRule) и выполняет действия
    при срабатывании событий.
    """

    def __init__(self) -> None:
        self._rules: List[AutomationRule] = []
        self._actions_log: List[Dict[str, Any]] = []
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Инициализация правил по умолчанию."""
        # Escalate при ошибке
        self._rules.append(
            AutomationRule(
                event_type="task.failed",
                action="escalate",
            )
        )

        # Уведомление при завершении
        self._rules.append(
            AutomationRule(
                event_type="task.completed",
                action="notify_complete",
            )
        )

    def add_rule(self, rule: AutomationRule) -> None:
        """Добавить правило автоматизации."""
        self._rules.append(rule)

    def process_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        notify_fn: Optional[Callable[[str], Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Обработать событие: найти подходящие правила и выполнить действия.

        Args:
            event_type: тип события
            data: данные события
            notify_fn: функция уведомления (str → Any)

        Returns:
            список выполненных действий
        """
        executed: List[Dict[str, Any]] = []

        for rule in self._rules:
            if not rule.enabled or not rule.matches(event_type):
                continue

            action_result = self._execute_action(
                rule=rule,
                event_type=event_type,
                data=data,
                notify_fn=notify_fn,
            )
            executed.append(action_result)
            self._actions_log.append(action_result)

        return executed

    def get_rules(self) -> List[Dict[str, Any]]:
        """Вернуть список правил."""
        return [
            {
                "event_type": r.event_type,
                "action": r.action,
                "enabled": r.enabled,
            }
            for r in self._rules
        ]

    def get_actions_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Вернуть лог выполненных действий."""
        return list(reversed(self._actions_log[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """Статистика автоматизации."""
        action_counts: Dict[str, int] = {}
        for entry in self._actions_log:
            action = entry.get("action", "")
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "total_rules": len(self._rules),
            "active_rules": sum(1 for r in self._rules if r.enabled),
            "total_actions_executed": len(self._actions_log),
            "actions_by_type": action_counts,
        }

    # ── Приватные ────────────────────────────────────────────

    def _execute_action(
        self,
        rule: AutomationRule,
        event_type: str,
        data: Dict[str, Any],
        notify_fn: Optional[Callable[[str], Any]] = None,
    ) -> Dict[str, Any]:
        """Выполнить действие правила."""
        now = datetime.now(timezone.utc).isoformat()
        task_id = data.get("task_id") or data.get("id", "")
        task_name = data.get("task_name") or data.get("name", "")

        result: Dict[str, Any] = {
            "timestamp": now,
            "event_type": event_type,
            "action": rule.action,
            "task_id": task_id,
            "success": False,
        }

        try:
            if rule.action == "escalate":
                message = self._build_escalate_message(data)
                if notify_fn:
                    notify_fn(message)
                result["success"] = True
                result["message"] = message

            elif rule.action == "notify_complete":
                message = self._build_complete_message(data)
                if notify_fn:
                    notify_fn(message)
                result["success"] = True
                result["message"] = message

            elif rule.action == "rerun":
                # Заглушка: rerun пока не реализован
                result["success"] = False
                result["message"] = "rerun not implemented yet"

            elif rule.handler:
                rule.handler(data)
                result["success"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    def _build_escalate_message(self, data: Dict[str, Any]) -> str:
        """Построить сообщение для escalation."""
        task_id = data.get("task_id") or data.get("id", "")
        task_name = data.get("task_name") or data.get("name", "Unknown")
        error = data.get("error", "No error details")

        return (
            f"🚨 ESCALATE: Task failed!\n"
            f"Task: {task_name} ({task_id})\n"
            f"Error: {error}"
        )

    def _build_complete_message(self, data: Dict[str, Any]) -> str:
        """Построить сообщение о завершении."""
        task_id = data.get("task_id") or data.get("id", "")
        task_name = data.get("task_name") or data.get("name", "Unknown")
        duration = data.get("duration_seconds") or data.get("duration", "")

        msg = f"✅ Task completed: {task_name} ({task_id})"
        if duration:
            msg += f" in {duration}s"
        return msg
