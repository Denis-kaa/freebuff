"""Notifier — отправляет уведомления о task-событиях в 3 канала:
Telegram (TGClient), Pulse feed, лог-файл.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from plugins_04.event.types import PulseEntry

# ── Severity → emoji для TG ──────────────────────────────────

_TG_EMOJI: Dict[str, str] = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
}


class Notifier:
    """Отправляет уведомления о task-событиях.

    Поддерживает 3 канала:
    1. Telegram — через injectable send_fn
    2. Pulse feed — через PulseNotifier
    3. Лог-файл — в docs_10/logs/task_watcher.log
    """

    def __init__(
        self,
        send_fn: Optional[Callable[[str], Any]] = None,
        log_dir: Optional[Path] = None,
    ):
        """
        Args:
            send_fn: функция отправки сообщения в Telegram (str → Any).
                     Если None — TG-уведомления отключены.
            log_dir: директория для лог-файла.
                     Если None — defaults to docs_10/logs/.
        """
        self._send_fn = send_fn
        self._log_dir = log_dir or Path("docs_10") / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._pulse_feed: list[PulseEntry] = []
        self._notification_count = 0

    def notify(
        self,
        pulse_entry: PulseEntry,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Отправить уведомление во все доступные каналы.

        Args:
            pulse_entry: запись для pulse feed
            data: дополнительные данные события

        Returns:
            dict с результатами по каналам
        """
        results: Dict[str, Any] = {
            "tg": False,
            "pulse": False,
            "log_file": False,
        }

        # 1. Telegram
        results["tg"] = self._send_tg(pulse_entry)

        # 2. Pulse feed
        results["pulse"] = self._add_to_pulse(pulse_entry)

        # 3. Лог-файл
        results["log_file"] = self._write_log(pulse_entry, data)

        self._notification_count += 1
        return results

    def get_pulse_feed(self, limit: int = 50) -> list[PulseEntry]:
        """Вернуть последние записи pulse feed."""
        return list(reversed(self._pulse_feed[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """Статистика уведомлений."""
        return {
            "total_notifications": self._notification_count,
            "pulse_entries": len(self._pulse_feed),
            "tg_enabled": self._send_fn is not None,
        }

    # ── Приватные ────────────────────────────────────────────

    def _send_tg(self, entry: PulseEntry) -> bool:
        """Отправить уведомление в Telegram."""
        if self._send_fn is None:
            return False
        try:
            emoji = _TG_EMOJI.get(entry.severity, "📌")
            message = f"{emoji} {entry.title}"
            if entry.description:
                message += f"\n{entry.description}"
            self._send_fn(message)
            return True
        except Exception:
            return False

    def _add_to_pulse(self, entry: PulseEntry) -> bool:
        """Добавить запись в pulse feed."""
        try:
            self._pulse_feed.append(entry)
            return True
        except Exception:
            return False

    def _write_log(
        self,
        entry: PulseEntry,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Записать событие в лог-файл."""
        try:
            log_file = self._log_dir / "task_watcher.log"
            now = datetime.now(timezone.utc).isoformat()
            record = {
                "timestamp": now,
                "event_type": entry.event_type,
                "title": entry.title,
                "description": entry.description,
                "severity": entry.severity,
                "event_id": entry.event_id,
            }
            if data:
                record["data"] = data

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return True
        except Exception:
            return False
