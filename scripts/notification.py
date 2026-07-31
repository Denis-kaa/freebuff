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
    from scripts.notification import notify, notify_task_complete

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
import time
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s***REMOVED*** %(message)s", stream=sys.stderr)
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

# Визуальный [SUMMARY***REMOVED*** блок.
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
        logger.info("[INFO***REMOVED*** Sending completion notification... (attempt %s)", attempt)
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
                ***REMOVED***,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                logger.info("[INFO***REMOVED*** Notification delivered.")
                return True
            logger.error("[ERROR***REMOVED*** Notification failed (attempt %s): %s", attempt, proc.stderr.strip())
        except subprocess.TimeoutExpired:
            logger.error("[ERROR***REMOVED*** Notification timeout (attempt %s): timeout (10s)", attempt)
        except FileNotFoundError:
            logger.error(
                "❌ termux-notification: command not found despite is_available() check"
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("[ERROR***REMOVED*** Notification exception (attempt %s): %s", attempt, exc)
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
    message = f"{title***REMOVED***: {content***REMOVED***" if title else content
    # Android обрезает длинные сообщения — усекаем заранее (≤ 240 символов).
    if len(message) > 240:
        message = message[:237***REMOVED*** + "..."
    try:
        proc = subprocess.run([cmd, message***REMOVED***, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            logger.info("[INFO***REMOVED*** Notification delivered via toast fallback.")
            return True
        logger.warning("[WARN***REMOVED*** termux-toast error: %s", proc.stderr.strip())
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
            f.write(f"[{ts***REMOVED******REMOVED*** {title***REMOVED***: {content***REMOVED***\n")
        logger.info("[INFO***REMOVED*** Notification logged to %s", log_path)
        return True
    except OSError as exc:
        logger.error("[ERROR***REMOVED*** Cannot write to %s: %s", log_path, exc)
        return False


def _get_visual_output_stream():
    """Выбирает поток для печати [SUMMARY***REMOVED*** блока (honor user stdout request).

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
    """Определяет, нужно ли печатать визуальный [SUMMARY***REMOVED*** блок.

    Логика:
    - FREEBUFF_FORCE_VISUAL=1   → принудительная печать
    - stdout is TTY             → печатать в stdout (запрос пользователя)
    - stdout redirect, но stderr is TTY → печатать в stderr

    Returns:
        True если блок нужно печатать.
    """
    return _get_visual_output_stream() is not None


def _print_visual_summary(title: str, body: str, channel_reason: str = "") -> bool:
    """Side-effect: печатает pipe-safe визуальный [SUMMARY***REMOVED*** блок в stderr.

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
        title = title[:43***REMOVED*** + "..."
    if body and len(body) > _VISUAL_LINE_WIDTH:
        body = body[:_VISUAL_LINE_WIDTH***REMOVED*** + "..."
    if len(channel_reason) > _VISUAL_LINE_WIDTH:
        channel_reason = channel_reason[:_VISUAL_LINE_WIDTH***REMOVED*** + "..."
    lines = [***REMOVED***
    box = "═" * _VISUAL_BOX_WIDTH
    sep = "─" * _VISUAL_BOX_WIDTH
    lines.append(box)
    lines.append(f"  [SUMMARY***REMOVED*** {title***REMOVED***")
    lines.append(sep)
    if body:
        lines.append(f"  {body***REMOVED***")
    lines.append(f"  Channel: {channel_reason***REMOVED***")
    lines.append(box)
    try:
        for line in lines:
            print(line, file=stream)
        logger.debug("[DEBUG***REMOVED*** Visual summary block printed to %s", stream)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WARN***REMOVED*** Visual summary print failed: %s", exc)
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
        logger.info("[INFO***REMOVED*** Notification suppressed by FREEBUFF_NO_NOTIFY")
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
            logger.error("[ERROR***REMOVED*** All notification channels exhausted. Уведомление не доставлено ни одним из способов.")
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
        logger.error("[ERROR***REMOVED*** All notification channels exhausted. Уведомление не доставлено ни одним из способов.")

    # Визуальный [SUMMARY***REMOVED*** блок fires на ЛЮБОМ исходе cascade.
    _print_visual_summary(title, content, reason)
    return status


def notify_task_complete(
    task_name: str,
    status: str = "Успешно",
    duration: str = "",
    details: str = "",
    task_type: str = "",
    is_error: bool = False,
) -> Dict[str, str***REMOVED*** | bool:
    """Формирует и отправляет уведомление о завершении задачи.

    Args:
        task_name: название задачи
        status: статус (Успешно / Ошибка / С предупреждениями / Частично / Отменена)
        duration: длительность выполнения
        details: дополнительные детали результата
        task_type: тип задачи (опционально)
        is_error: принудительно показать иконку ошибки

    Returns:
        Словарь {"title": ..., "content": ...***REMOVED*** сформированного уведомления.
    """
    error_statuses = ("Ошибка", "failed", "error", "FAILED")
    warning_statuses = ("С предупреждениями", "Предупреждение", "Частично", "warning", "partial", "WARNING")
    if is_error or status in error_statuses:
        icon = "❌"
    elif status in warning_statuses:
        icon = "⚠"
    else:
        icon = "✅"

    title_parts = [f"{icon***REMOVED*** AI Agent"***REMOVED***
    if task_type:
        title_parts.append(f"[{task_type***REMOVED******REMOVED***")
    title = " ".join(title_parts)

    content_parts = [f"📋 {task_name***REMOVED***"***REMOVED***
    if status:
        content_parts.append(f"📊 Статус: {status***REMOVED***")
    if duration:
        content_parts.append(f"⏱ Время: {duration***REMOVED***")
    if details:
        content_parts.append(details)
    content = "\n".join(content_parts)

    ok = notify(title=title, content=content)
    if not ok:
        return False
    return {"title": title, "content": content***REMOVED***


def notify_error(
    task_name: str,
    error: str,
    stage: str = "",
    duration: str = "",
) -> Dict[str, str***REMOVED*** | bool:
    """Отправляет уведомление об ошибке.

    Args:
        task_name: название задачи
        error: описание ошибки
        stage: на каком этапе произошла ошибка
        duration: длительность выполнения

    Returns:
        Словарь {"title": ..., "content": ...***REMOVED*** сформированного уведомления.
    """
    title = "❌ AI Agent"
    content_parts = [f"📋 {task_name***REMOVED***"***REMOVED***
    content_parts.append("📊 Статус: Ошибка")
    if stage:
        content_parts.append(f"⚠ Этап: {stage***REMOVED***")
    if error:
        content_parts.append(f"🔴 Причина: {error***REMOVED***")
    if duration:
        content_parts.append(f"⏱ Время: {duration***REMOVED***")
    content = "\n".join(content_parts)
    ok = notify(title=title, content=content)
    if not ok:
        return False
    return {"title": title, "content": content***REMOVED***


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
