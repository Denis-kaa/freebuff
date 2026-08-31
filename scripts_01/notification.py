"""
notification.py — Runtime Notification System (MANDATORY RUNTIME CONTRACT).

Система отправки Android-уведомлений через Termux:API (termux-notification).

Стандарт:
  Каждая завершённая задача ОБЯЗАНА отправить уведомление пользователю.
  Это не дополнительная функция, а часть архитектуры Runtime Lifecycle.
  Нарушение = нарушение архитектурного контракта.

Жизненный цикл уведомления:
  1. Проверка доступности termux-notification
  2. Формирование заголовка и тела уведомления
  3. Отправка с exponential backoff retry (макс 3 попытки)
  4. Логирование каждой попытки
  5. Финальный статус: delivered / failed

Использование:
    from scripts_01.notification import notify, notify_task_complete

    # Простое уведомление
    notify("✅ AI Agent", "Задача завершена за 2 мин 41 сек.")

    # Уведомление о задаче
    notify_task_complete(
        task_name="Создание отчёта",
        status="Успешно",
        duration="2 мин 41 сек",
        details="Создано файлов: 8",
    )
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from scripts_01.event_bus import Subscription as _EventSubscription

logging.basicConfig(level=logging.INFO, format="[%(levelname)s) %(message)s", stream=sys.stderr)
logger = logging.getLogger("notification")

# Пути к бинарникам Termux:API (fallback для is_available()).
# Константы вычисляются один раз при импорте; тесты мокают их напрямую.
_TERMUX_NOTIFICATION_FALLBACK = "/data/data/com.termux/files/usr/bin/termux-notification"
TERMUX_NOTIFICATION = shutil.which("termux-notification") or _TERMUX_NOTIFICATION_FALLBACK
_TERMUX_TOAST_FALLBACK = "/data/data/com.termux/files/usr/bin/termux-toast"
TERMUX_TOAST = shutil.which("termux-toast") or _TERMUX_TOAST_FALLBACK

NOTIFICATION_LOG_PATH = Path.home() / "notifications.log"

# Retry-параметры (exponential backoff).
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RETRY_BACKOFF = 2.0

# Дефолты termux-notification.
DEFAULT_PRIORITY = "high"
DEFAULT_ID = "runtime"
DEFAULT_GROUP = "ai-agent"

# Визуальный [SUMMARY] блок.
_VISUAL_BOX_WIDTH = 56
_VISUAL_LINE_WIDTH = 52


def is_available() -> bool:
    """Проверяет доступность termux-notification.

    Returns:
        True если команда доступна и исполняема.
    """
    if not TERMUX_NOTIFICATION:
        return False
    return os.access(TERMUX_NOTIFICATION, os.X_OK)


def _try_primary_channel(
    title: str,
    content: str,
    notification_id: str = DEFAULT_ID,
    group: str = DEFAULT_GROUP,
    priority: str = DEFAULT_PRIORITY,
) -> bool:
    """Попытка отправки через termux-notification с 3-retry exponential backoff.

    Returns:
        True если доставлено, False если все попытки провалились
        или binary недоступен.
    """
    cmd = TERMUX_NOTIFICATION
    if not is_available():
        logger.error("❌ termux-notification не найден. Установи Termux:API из F-Droid и выполни: pkg install termux-api")
        return False
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("[INFO) Sending completion notification... (attempt %s)", attempt)
        try:
            proc = subprocess.run(
                [
                    cmd,
                    "--title", title,
                    "--content", content,
                    "--id", notification_id,
                    "--group", group,
                    "--priority", priority,
                    "--alert-once",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                logger.info("[INFO) Notification delivered.")
                return True
            logger.error("[ERROR) Notification failed (attempt %s): %s", attempt, proc.stderr.strip())
        except subprocess.TimeoutExpired:
            logger.error("[ERROR) Notification timeout (attempt %s): timeout (10s)", attempt)
        except FileNotFoundError:
            logger.error(
                "❌ termux-notification: command not found despite is_available() check"
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("[ERROR) Notification exception (attempt %s): %s", attempt, exc)
        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (RETRY_BACKOFF ** (attempt - 1))
            logger.info("Retrying in %.1f seconds", delay)
            time.sleep(delay)
    return False


def _try_toast_channel(title: str, content: str) -> bool:
    """Fallback: отправить Android Toast через termux-toast.

    Toasts НЕ подпадают под Android 13+ POST_NOTIFICATIONS ограничение
    и работают даже когда system notifications заблокированы. Возвращает
    True если команда завершилась успешно.

    Args:
        title: заголовок (включается в сообщение toast'а)
        content: тело сообщения
    """
    cmd = TERMUX_TOAST
    if not TERMUX_TOAST or not os.access(cmd, os.X_OK):
        logger.warning("⚠️  termux-toast не найден в %s", cmd)
        return False
    message = f"{title}: {content}" if title else content
    # Android обрезает длинные сообщения — усекаем заранее (≤ 240 символов).
    if len(message) > 240:
        message = message[:237] + "..."
    try:
        proc = subprocess.run([cmd, message], capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            logger.info("[INFO) Notification delivered via toast fallback.")
            return True
        logger.warning("[WARN) termux-toast error: %s", proc.stderr.strip())
        return False
    except Exception:  # noqa: BLE001
        return False


def _try_log_channel(title: str, content: str) -> bool:
    """Final fallback: записать уведомление в ~/notifications.log.

    Этот канал работает ВСЕГДА при наличии write-доступа к файловой системе —
    в том числе в CI, в фоновых процессах, в Termux без Termux:API.

    Args:
        title: заголовок уведомления
        content: тело уведомления

    Returns:
        True если запись в лог успешна.
    """
    log_path = Path(os.environ.get("FREEBUFF_NOTIFY_LOG", str(NOTIFICATION_LOG_PATH)))
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {title}: {content}\n")
        logger.info("[INFO) Notification logged to %s", log_path)
        return True
    except OSError as exc:
        logger.error("[ERROR) Cannot write to %s: %s", log_path, exc)
        return False


def _get_visual_output_stream():
    """Выбирает поток для печати [SUMMARY] блока (honor user stdout request).

    Приоритет:
      1. Если FREEBUFF_FORCE_VISUAL установлен → принудительно sys.stderr
         (bypass isatty() check — позволяет печатать в non-TTY субпроцессах)
      2. stdout is TTY → sys.stdout
      3. stderr is TTY → sys.stderr
      4. Оба redirected → None (молча пропускаем)

    Returns:
        Поток для печати или None.
    """
    if os.environ.get("FREEBUFF_FORCE_VISUAL", "").strip().lower() in ("1", "true", "yes", "y"):
        return sys.stderr
    if sys.stdout.isatty():
        return sys.stdout
    if sys.stderr.isatty():
        return sys.stderr
    return None


def _is_visual_summary_enabled() -> bool:
    """Определяет, нужно ли печатать визуальный [SUMMARY] блок.

    Логика:
    - FREEBUFF_FORCE_VISUAL=1   → принудительная печать
    - stdout is TTY             → печатать в stdout (запрос пользователя)
    - stdout redirect, но stderr is TTY → печатать в stderr

    Returns:
        True если блок нужно печатать.
    """
    return _get_visual_output_stream() is not None


def _print_visual_summary(title: str, body: str, channel_reason: str = "") -> bool:
    """Side-effect: печатает pipe-safe визуальный [SUMMARY] блок в stderr.

    Гарантии:
    - Безопасен для pipe (`python script.py > out.log`): молча пропускается
    - Безопасен для grep (`... | grep pattern`): молча пропускается

    Args:
        title: заголовок блока (обрезается до 43 символов)
        body: тело блока (содержимое уведомления)
        channel_reason: строка с описанием канала доставки

    Returns:
        True если блок напечатан.
    """
    stream = _get_visual_output_stream()
    if stream is None:
        return False
    # Defensive truncation: не ломать геометрию бокса.
    if len(title) > 43:
        title = title[:43] + "..."
    if body and len(body) > _VISUAL_LINE_WIDTH:
        body = body[:_VISUAL_LINE_WIDTH] + "..."
    if len(channel_reason) > _VISUAL_LINE_WIDTH:
        channel_reason = channel_reason[:_VISUAL_LINE_WIDTH] + "..."
    lines = []
    box = "═" * _VISUAL_BOX_WIDTH
    sep = "─" * _VISUAL_BOX_WIDTH
    lines.append(box)
    lines.append(f"  [SUMMARY] {title}")
    lines.append(sep)
    if body:
        lines.append(f"  {body}")
    lines.append(f"  Channel: {channel_reason}")
    lines.append(box)
    try:
        for line in lines:
            print(line, file=stream)
        logger.debug("[DEBUG) Visual summary block printed to %s", stream)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WARN) Visual summary print failed: %s", exc)
        return False


def notify(
    title: str,
    content: str,
    notification_id: str = DEFAULT_ID,
    group: str = DEFAULT_GROUP,
    priority: str = DEFAULT_PRIORITY,
) -> bool:
    """Отправляет системное уведомление через цепочку fallback-каналов.

    Цепочка доставки (по приоритету):
      1. termux-notification       — основной канал (требует POST_NOTIFICATIONS на Android 13+)
      2. termux-toast             — fallback 1 (Toasts НЕ подпадают под POST_NOTIFICATIONS)
      3. ~/notifications.log      — fallback 2 (работает всегда при FS-доступе)

    Returns:
        True если уведомление доставлено хотя бы одним каналом.
    """
    if os.environ.get("FREEBUFF_NO_NOTIFY"):
        logger.info("[INFO) Notification suppressed by FREEBUFF_NO_NOTIFY")
        return True

    status = False
    reason = "ALL CHANNELS FAILED (проверьте ~/notifications.log)"

    if not is_available():
        # Основной канал недоступен — пробуем только fallback-каналы.
        if _try_toast_channel(title, content):
            status = True
            reason = "delivered via termux-toast"
        elif _try_log_channel(title, content):
            status = True
            reason = "log fallback (Android notification BLOCKED on Termux 13+)"
        else:
            logger.error("[ERROR) All notification channels exhausted. Уведомление не доставлено ни одним из способов.")
    elif _try_primary_channel(title, content, notification_id, group, priority):
        status = True
        reason = "delivered via termux-notification"
    elif _try_toast_channel(title, content):
        status = True
        reason = "delivered via termux-toast"
    elif _try_log_channel(title, content):
        status = True
        reason = "log fallback (Android notification BLOCKED on Termux 13+)"
    else:
        logger.error("[ERROR) All notification channels exhausted. Уведомление не доставлено ни одним из способов.")

    # Визуальный [SUMMARY] блок fires на ЛЮБОМ исходе cascade.
    _print_visual_summary(title, content, reason)
    return status


def notify_task_complete(
    task_name: str,
    status: str = "Успешно",
    duration: str = "",
    details: str = "",
    task_type: str = "",
    is_error: bool = False,
) -> Dict[str, str] | bool:
    """Формирует и отправляет уведомление о завершении задачи.

    Args:
        task_name: название задачи
        status: статус (Успешно / Ошибка / С предупреждениями / Частично / Отменена)
        duration: длительность выполнения
        details: дополнительные детали результата
        task_type: тип задачи (опционально)
        is_error: принудительно показать иконку ошибки

    Returns:
        Словарь {"title": ..., "content": ...} сформированного уведомления.
    """
    error_statuses = ("Ошибка", "failed", "error", "FAILED")
    warning_statuses = ("С предупреждениями", "Предупреждение", "Частично", "warning", "partial", "WARNING")
    if is_error or status in error_statuses:
        icon = "❌"
    elif status in warning_statuses:
        icon = "⚠"
    else:
        icon = "✅"

    title_parts = [f"{icon} AI Agent"]
    if task_type:
        title_parts.append(f"[{task_type}]")
    title = " ".join(title_parts)

    content_parts = [f"📋 {task_name}"]
    if status:
        content_parts.append(f"📊 Статус: {status}")
    if duration:
        content_parts.append(f"⏱ Время: {duration}")
    if details:
        content_parts.append(details)
    content = "\n".join(content_parts)

    ok = notify(title=title, content=content)
    if not ok:
        return False
    return {"title": title, "content": content}


def notify_error(
    task_name: str,
    error: str,
    stage: str = "",
    duration: str = "",
) -> Dict[str, str] | bool:
    """Отправляет уведомление об ошибке.

    Args:
        task_name: название задачи
        error: описание ошибки
        stage: на каком этапе произошла ошибка
        duration: длительность выполнения

    Returns:
        Словарь {"title": ..., "content": ...} сформированного уведомления.
    """
    title = "❌ AI Agent"
    content_parts = [f"📋 {task_name}"]
    content_parts.append("📊 Статус: Ошибка")
    if stage:
        content_parts.append(f"⚠ Этап: {stage}")
    if error:
        content_parts.append(f"🔴 Причина: {error}")
    if duration:
        content_parts.append(f"⏱ Время: {duration}")
    content = "\n".join(content_parts)
    ok = notify(title=title, content=content)
    if not ok:
        return False
    return {"title": title, "content": content}


# ═══════════════════════════════════════════════════════════════
# EventBus-driven notification layer (Phase A, Promt 28/31)
# ═══════════════════════════════════════════════════════════════


@dataclass
class NotificationConfig:
    """Настройки EventBus-уведомлений."""

    enabled: bool = True
    # Уведомлять ли о начале задачи/workflow
    notify_on_start: bool = True
    # Уведомлять ли о смене этапа
    notify_on_stage_change: bool = True
    # Минимальный интервал (сек) между progress-уведомлениями одного таска
    progress_interval_seconds: float = 30.0
    # Тихий режим: только завершение/ошибка (без стартов и прогресса)
    quiet: bool = False
    # Только завершение/ошибка (альтернатива quiet)
    completion_only: bool = False

    @classmethod
    def from_env(cls) -> "NotificationConfig":
        """Создаёт конфиг из переменных окружения."""
        quiet = os.environ.get("FREEBUFF_NOTIFY_QUIET", "").strip().lower() in ("1", "true", "yes")
        completion_only = os.environ.get("FREEBUFF_NOTIFY_COMPLETION_ONLY", "").strip().lower() in ("1", "true", "yes")
        no_notify = os.environ.get("FREEBUFF_NO_NOTIFY", "").strip().lower() in ("1", "true", "yes")
        notify_on_stage = os.environ.get("FREEBUFF_NOTIFY_STAGE", "1").strip().lower() not in ("0", "false", "no", "n")
        try:
            progress_interval = float(os.environ.get("FREEBUFF_NOTIFY_PROGRESS_INTERVAL", "30"))
        except ValueError:
            progress_interval = 30.0
        return cls(
            enabled=not no_notify,
            quiet=quiet,
            completion_only=completion_only,
            notify_on_stage_change=notify_on_stage,
            progress_interval_seconds=max(5.0, progress_interval),
        )

    @property
    def should_notify_on_start(self) -> bool:
        return self.enabled and not self.quiet and not self.completion_only and self.notify_on_start

    @property
    def should_notify_on_stage(self) -> bool:
        return self.enabled and not self.quiet and not self.completion_only and self.notify_on_stage_change

    @property
    def should_notify_on_progress(self) -> bool:
        return self.enabled and not self.quiet and not self.completion_only


class NotificationManager:
    """Подписчик EventBus, который отправляет уведомления о ходе задач.

    Поддерживает события:
      - task.started, task.stage_changed, task.progress, task.completed, task.failed, task.warning
      - workflow.started, workflow.progress, workflow.completed, workflow.failed
      - step.started, step.completed, step.failed, step.retrying, step.skipped

    Использует rate-limiting, чтобы не завалить пользователя уведомлениями:
      - progress-уведомления одного task_id/workflow_id не чаще чем progress_interval_seconds
      - stage-уведомления без throttle, но можно отключить через конфиг
      - start/complete/error — немедленно (enabled/quiet permitting)
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        # event_type -> callable
        self._handlers: Dict[str, Callable[[Any], None]] = {
            "task.started": self._on_task_started,
            "task.stage_changed": self._on_task_stage_changed,
            "task.progress": self._on_task_progress,
            "task.completed": self._on_task_completed,
            "task.failed": self._on_task_failed,
            "task.warning": self._on_task_warning,
            "workflow.started": self._on_workflow_started,
            "workflow.progress": self._on_workflow_progress,
            "workflow.completed": self._on_workflow_completed,
            "workflow.failed": self._on_workflow_failed,
            "step.started": self._on_step_started,
            "step.completed": self._on_step_completed,
            "step.failed": self._on_step_failed,
            "step.retrying": self._on_step_retrying,
            "step.skipped": self._on_step_skipped,
        }
        # key (task_id or workflow_id) -> timestamp of last progress notification
        self._last_progress: Dict[str, float] = {}
        self._subscriptions: List["_EventSubscription"] = []
        self._lock = threading.Lock()

    # ── Registration ───────────────────────────────────────

    def register(self, event_bus: Any) -> None:
        """Подписывает менеджер на все поддерживаемые события."""
        for event_type in self._handlers:
            sub = event_bus.subscribe(event_type, self._on_event)
            self._subscriptions.append(sub)

    def unregister(self, event_bus: Any) -> None:
        """Отписывает менеджер от всех событий."""
        for sub in self._subscriptions:
            event_bus.unsubscribe(sub)
        self._subscriptions.clear()

    # ── Dispatch ─────────────────────────────────────────────

    def _on_event(self, event: Any) -> None:
        """Диспетчеризует событие в соответствующий handler."""
        if not self.config.enabled:
            return
        handler = self._handlers.get(event.type)
        if handler:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[WARN) Notification handler error for %s: %s", event.type, exc)

    # ── Rate limiting helpers ────────────────────────────────

    def _allow_throttled(self, key: str) -> bool:
        """Возвращает True, если с последнего уведомления key прошло
        достаточно времени, и обновляет timestamp."""
        with self._lock:
            now = time.monotonic()
            last = self._last_progress.get(key)
            if last is None or now - last >= self.config.progress_interval_seconds:
                self._last_progress[key] = now
                return True
            return False

    # ── Task handlers ────────────────────────────────────────

    def _on_task_started(self, event: Any) -> None:
        if not self.config.should_notify_on_start:
            return
        data = event.data
        task_name = data.get("task_name") or data.get("task_id") or "task"
        stage = data.get("stage", "")
        body = f" Начата задача: {task_name}"
        if stage:
            body += f"\nЭтап: {stage}"
        notify(title="🚀 AI Agent", content=body)

    def _on_task_stage_changed(self, event: Any) -> None:
        if not self.config.should_notify_on_stage:
            return
        data = event.data
        task_name = data.get("task_name") or data.get("task_id") or "task"
        stage = data.get("stage", "неизвестен")
        notify(title="🔄 AI Agent", content=f"{task_name}\nЭтап: {stage}")

    def _on_task_progress(self, event: Any) -> None:
        if not self.config.should_notify_on_progress:
            return
        data = event.data
        task_id = data.get("task_id") or data.get("task_name") or "task"
        if not self._allow_throttled(str(task_id)):
            return
        task_name = data.get("task_name") or task_id
        percent = data.get("percent")
        message = data.get("message", "")
        parts = [f"{task_name}"]
        if percent is not None:
            parts.append(f"{percent}%")
        if message:
            parts.append(message)
        notify(title="⏳ AI Agent", content="\n".join(parts))

    def _on_task_completed(self, event: Any) -> None:
        data = event.data
        notify_task_complete(
            task_name=data.get("task_name") or data.get("task_id") or "Задача",
            status=data.get("status", "Успешно"),
            duration=data.get("duration", ""),
            details=data.get("details", ""),
        )

    def _on_task_failed(self, event: Any) -> None:
        data = event.data
        notify_error(
            task_name=data.get("task_name") or data.get("task_id") or "Задача",
            error=data.get("error", "Неизвестная ошибка"),
            stage=data.get("stage", ""),
            duration=data.get("duration", ""),
        )

    def _on_task_warning(self, event: Any) -> None:
        data = event.data
        task_name = data.get("task_name") or data.get("task_id") or "Задача"
        warning = data.get("warning") or data.get("message", "")
        notify(title="⚠ AI Agent", content=f"{task_name}\n⚠ {warning}")

    # ── Workflow handlers ────────────────────────────────────

    def _on_workflow_started(self, event: Any) -> None:
        if not self.config.should_notify_on_start:
            return
        data = event.data
        goal = data.get("goal") or data.get("workflow_id") or "workflow"
        notify(title="🚀 AI Agent", content=f"Начат workflow:\n{goal}")

    def _on_workflow_progress(self, event: Any) -> None:
        if not self.config.should_notify_on_progress:
            return
        data = event.data
        workflow_id = data.get("workflow_id") or "workflow"
        if not self._allow_throttled(str(workflow_id)):
            return
        completed = data.get("completed_steps", 0)
        total = data.get("total_steps", 0)
        percent = int((completed / total) * 100) if total else 0
        notify(
            title="⏳ AI Agent",
            content=f"Workflow {workflow_id}\nПрогресс: {completed}/{total} ({percent}%)",
        )

    def _on_workflow_completed(self, event: Any) -> None:
        data = event.data
        notify_task_complete(
            task_name=data.get("goal") or data.get("workflow_id") or "Workflow",
            status=data.get("status", "Успешно"),
            duration=data.get("duration", ""),
            details=data.get("details", ""),
            task_type="workflow",
        )

    def _on_workflow_failed(self, event: Any) -> None:
        data = event.data
        notify_error(
            task_name=data.get("goal") or data.get("workflow_id") or "Workflow",
            error=data.get("error", "Неизвестная ошибка"),
            stage=data.get("stage", ""),
            duration=data.get("duration", ""),
        )

    # ── Step handlers ────────────────────────────────────────

    def _on_step_started(self, event: Any) -> None:
        # Не уведомляем о каждом шаге, чтобы не спамить.
        # Логируем только в debug.
        logger.debug("[DEBUG) step.started — no notification (anti-spam)")

    def _on_step_completed(self, event: Any) -> None:
        logger.debug("[DEBUG) step.completed — no notification (anti-spam)")

    def _on_step_failed(self, event: Any) -> None:
        data = event.data
        step_name = data.get("step_name") or data.get("step_id") or "шаг"
        error = data.get("error", "неизвестная ошибка")
        notify_error(task_name=f"Шаг {step_name}", error=error)

    def _on_step_retrying(self, event: Any) -> None:
        data = event.data
        step_id = str(data.get("step_id") or data.get("step_name") or "step")
        # Rate-limit retry notifications to avoid spam on many quick retries.
        if not self._allow_throttled(f"retry:{step_id}"):
            return
        step_name = data.get("step_name") or data.get("step_id") or "шаг"
        retry_count = data.get("retry_count", 0)
        max_retries = data.get("max_retries", 1)
        notify(
            title="🔄 AI Agent",
            content=f"Шаг {step_name}\nПовторная попытка {retry_count}/{max_retries}",
        )

    def _on_step_skipped(self, event: Any) -> None:
        data = event.data
        step_name = data.get("step_name") or data.get("step_id") or "шаг"
        notify(title="⏭ AI Agent", content=f"Шаг пропущен:\n{step_name}")


class ProgressTracker:
    """Удобный контекстный менеджер/хелпер для эмиссии событий прогресса.

    Пример:
        with ProgressTracker("Долгая задача", event_bus=bus) as pt:
            pt.set_stage("Загрузка")
            for i in range(10):
                pt.update_progress((i + 1) * 10, "загружаем...")
            pt.complete(details="Всё готово")

    Если event_bus не передан, события просто игнорируются (graceful degradation).
    """

    def __init__(
        self,
        task_name: str,
        event_bus: Optional[Any] = None,
        task_id: Optional[str] = None,
        source: str = "runtime",
    ):
        self.task_name = task_name
        self.task_id = task_id or task_name
        self.event_bus = event_bus
        self.source = source
        self._stage: str = ""
        self._start_time: Optional[float] = None
        self._finalized: bool = False

    # ── Event emission helpers ───────────────────────────────

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.event_bus is None:
            return
        # Lazy import to avoid circular dependency at module load
        from scripts_01.event_bus import Event
        self.event_bus.publish(Event(type=event_type, data=data, source=self.source))

    def start(self, stage: str = "") -> None:
        self._start_time = time.monotonic()
        data: Dict[str, Any] = {"task_id": self.task_id, "task_name": self.task_name}
        if stage:
            self._stage = stage
            data["stage"] = stage
        self._emit("task.started", data)

    def set_stage(self, stage: str) -> None:
        self._stage = stage
        self._emit("task.stage_changed", {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "stage": stage,
        })

    def update_progress(self, percent: int, message: str = "") -> None:
        data: Dict[str, Any] = {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "percent": max(0, min(100, percent)),
        }
        if message:
            data["message"] = message
        self._emit("task.progress", data)

    def complete(self, status: str = "Успешно", details: str = "") -> None:
        if self._finalized:
            return
        self._finalized = True
        duration = ""
        if self._start_time is not None:
            seconds = time.monotonic() - self._start_time
            duration = self._format_duration(seconds)
        self._emit("task.completed", {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": status,
            "duration": duration,
            "details": details,
        })

    def fail(self, error: str, stage: str = "") -> None:
        if self._finalized:
            return
        self._finalized = True
        duration = ""
        if self._start_time is not None:
            seconds = time.monotonic() - self._start_time
            duration = self._format_duration(seconds)
        self._emit("task.failed", {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "error": error,
            "stage": stage or self._stage,
            "duration": duration,
        })

    def warning(self, message: str) -> None:
        self._emit("task.warning", {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "warning": message,
        })

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)} сек"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)} мин"
        return f"{minutes / 60:.1f} ч"

    # ── Context manager support ──────────────────────────────

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.fail(str(exc_val))
        else:
            self.complete()
        return False


def register_notification_subscribers(
    event_bus: Any,
    config: Optional[NotificationConfig] = None,
) -> NotificationManager:
    """Регистрирует NotificationManager как подписчика EventBus.

    Args:
        event_bus: экземпляр EventBus
        config: конфигурация (если None — берётся из переменных окружения).

    Returns:
        Экземпляр NotificationManager (для отладки и тестирования).
    """
    if config is None:
        config = NotificationConfig.from_env()
    manager = NotificationManager(config=config)
    manager.register(event_bus)
    return manager


def main() -> int:
    """CLI для отправки уведомлений (тестирование и интеграция)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Runtime Notification System (MANDATORY RUNTIME CONTRACT)"
    )
    parser.add_argument("--title", "-t", default="✅ AI Agent", help="Заголовок уведомления")
    parser.add_argument("--content", "-c", default="📋 Тестовое уведомление", help="Текст уведомления")
    parser.add_argument("--id", "-i", default=DEFAULT_ID, help="ID уведомления")
    parser.add_argument("--group", "-g", default=DEFAULT_GROUP, help="Группа уведомления")
    parser.add_argument("--priority", "-p", default=DEFAULT_PRIORITY, help="Приоритет")
    parser.add_argument("--alert-once", "-b", action="store_true", help="Только один раз")
    args = parser.parse_args()

    print("📨 Отправка тестового уведомления...")
    ok = notify(args.title, args.content, args.id, args.group, args.priority)
    if ok:
        print("✅ Уведомление доставлено!")
        return 0
    print("❌ Ошибка доставки уведомления")
    return 1


if __name__ == "__main__":
    sys.exit(main())
