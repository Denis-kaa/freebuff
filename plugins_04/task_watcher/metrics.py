"""Metrics — 수집 и агрегация метрик задач.

Считает:
- Duration от task.created/task.started до task.completed/task.failed
- Success rate (completed / (completed + failed))
- Count по event_type
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TaskMetrics:
    """Метрики задач: duration, success_rate, counts."""

    def __init__(self) -> None:
        # task_id → timestamp когда created/started
        self._start_times: Dict[str, float] = {}
        # task_id → timestamp когда completed/failed
        self._end_times: Dict[str, float] = {}
        # task_id → {"type": event_type, "start": ts, "end": ts, "duration": sec}
        self._tasks: Dict[str, Dict[str, Any]] = {}
        # счётчики по event_type
        self._counts: Dict[str, int] = {}

    def record_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> None:
        """Записать событие и обновить метрики.

        Args:
            event_type: тип события (task.created, task.started, task.completed, task.failed)
            data: данные события (должен содержать task_id или id)
            timestamp: ISO timestamp (если None — используется текущее время)
        """
        task_id = data.get("task_id") or data.get("id", "")
        if not task_id:
            return

        now = datetime.now(timezone.utc).timestamp()
        ts = now  # fallback

        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts = dt.timestamp()
            except (ValueError, TypeError):
                ts = now

        # Обновляем счётчик
        self._counts[event_type] = self._counts.get(event_type, 0) + 1

        # Инициализируем запись задачи
        if task_id not in self._tasks:
            self._tasks[task_id] = {
                "task_id": task_id,
                "task_name": data.get("task_name") or data.get("name", ""),
                "type": event_type,
                "start": None,
                "end": None,
                "duration": None,
                "status": "unknown",
            }

        task = self._tasks[task_id]

        # Start events
        if event_type in ("task.created", "task.started"):
            if task["start"] is None:
                task["start"] = ts
                task["type"] = event_type
            self._start_times[task_id] = ts

        # End events
        elif event_type in ("task.completed", "task.failed"):
            task["end"] = ts
            task["status"] = event_type.replace("task.", "")
            self._end_times[task_id] = ts

            # Вычисляем duration
            if task["start"] is not None:
                task["duration"] = round(ts - task["start"], 2)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить метрики по конкретной задаче."""
        return self._tasks.get(task_id)

    def get_summary(self) -> Dict[str, Any]:
        """Сводка по всем метрикам."""
        completed = sum(
            1 for t in self._tasks.values() if t["status"] == "completed"
        )
        failed = sum(
            1 for t in self._tasks.values() if t["status"] == "failed"
        )
        total = completed + failed
        success_rate = round(completed / total, 4) if total > 0 else 0.0

        durations = [
            t["duration"]
            for t in self._tasks.values()
            if t["duration"] is not None
        ]
        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        return {
            "total_tasks": len(self._tasks),
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "counts_by_type": dict(self._counts),
        }

    def get_top_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Топ задач по длительности (самые долгие)."""
        sorted_tasks = sorted(
            [t for t in self._tasks.values() if t["duration"] is not None],
            key=lambda t: t["duration"],
            reverse=True,
        )
        return sorted_tasks[:limit]

    def reset(self) -> None:
        """Сбросить все метрики."""
        self._start_times.clear()
        self._end_times.clear()
        self._tasks.clear()
        self._counts.clear()
