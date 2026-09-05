"""prompt_queue.py — файловая очередь промтов (promt 48).

Статусы = перемещение файлов между папками `pompts_11/{user,running,done,failed***REMOVED***`
(детерминированный файловый подход, без БД — как требует promt 48).

Формат файла промта:
    Имя:    task_<YYYYmmdd_HHMMSS>_<chat_id или anon>.md
    Шапка:  # TASK: <название> + **Ключ:** значение метаданных
    Тело:   после строки `---` — полный текст задачи
    Отчёт:  секция `## Отчёт` (заполняет диспетчер)

Модуль — чистые функции без TG-зависимостей (тестируемость без сети).
"""

from __future__ import annotations

import os
***REMOVED***
import time as _time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional

# ── Папки очереди ─────────────────────────────────────────────

PROMPTS_DIR_NAME = "pompts_11"
QUEUE_DIRS = ("user", "running", "done", "failed")
STATUS_DIR_MAP = {
    "pending": "user",
    "running": "running",
    "done": "done",
    "failed": "failed",
***REMOVED***


def _workspace_root() -> Path:
    """Корень проекта: env override → каталог, где лежит этот файл."""
    return Path(
        os.environ.get(
            "FREEBUFF_ROOT",
            str(Path(__file__).resolve().parent.parent),
        )
    )


def prompts_dir() -> Path:
    return _workspace_root() / PROMPTS_DIR_NAME


def queue_dir(status: str) -> Path:
    """Папка очереди для статуса (pending→user, running→running, done, failed)."""
    sub = STATUS_DIR_MAP.get(status, "user")
    return prompts_dir() / sub


def ensure_queue_dirs() -> None:
    """Создаёт все папки очереди (идемпотентно)."""
    for sub in QUEUE_DIRS:
        (prompts_dir() / sub).mkdir(parents=True, exist_ok=True)


# ── Метаданные файла ──────────────────────────────────────────

_META_PATTERN = re.compile(r"^\*\*(?P<key>[A-Za-z ***REMOVED***+):\*\*\s*(?P<value>.*)$")


@dataclass
class PromptMeta:
    """Метаданные + тело промта, извлечённые из файла."""

    path: Path
    task_id: str
    chat_id: int = 0
    created: str = ""
    priority: int = 0
    source: str = "cli"
    status: str = "pending"
    title: str = ""
    body: str = ""
    report: str = ""
    # Multi-turn metadata (added v5.79.0, promt 48 multi-turn extension).
    iteration: int = 1
    max_iterations: int = 3
    # Модель Баффи (v5.88.0): позиция/алиас в стартовом списке freebuff.
    # "auto"/"0"/"flash" = рекомендованная DeepSeek V4 Flash (free, безлимит);
    # "1".."5" = позиция в списке выбора модели.
    model: str = "auto"
    # CON-35 (v5.90.0): счётчик подряд идущих backoff-тиков (инстанс занят) + флаг
    # «уведомили в TG один раз». Хранятся в мете файла, переживают cron-тики.
    backoff_streak: int = 0
    backoff_notified: bool = False
    # Multi-turn sub-budgets (Task 2, promt 61): clarification vs work iteration.
    # `clarification_count` инкрементируется ТОЛЬКО при kind=='clarification',
    # `iteration` — ТОЛЬКО при kind=='work'. Бюджеты независимы: work iter ≤3
    # не съедается длинной clarifications-сессией ≤10.
    clarification_count: int = 0
    max_clarifications: int = 10

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "task_id": self.task_id,
            "chat_id": self.chat_id,
            "created": self.created,
            "priority": self.priority,
            "source": self.source,
            "status": self.status,
            "title": self.title,
            "body": self.body,
            "report": self.report,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "model": self.model,
            "backoff_streak": self.backoff_streak,
            "backoff_notified": self.backoff_notified,
            "clarification_count": self.clarification_count,
            "max_clarifications": self.max_clarifications,
            "path": str(self.path),
        ***REMOVED***


def new_task_id() -> str:
    """Уникальный id задачи: <timestamp>_<short-uuid>."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{ts***REMOVED***_{uuid.uuid4().hex[:6***REMOVED******REMOVED***"


def prompt_filename(task_id: str, chat_id: int = 0) -> str:
    """Имя файла промта: task_<task_id>_<chat или anon>.md."""
    suffix = str(chat_id) if chat_id else "anon"
    return f"task_{task_id***REMOVED***_{suffix***REMOVED***.md"


def write_user_prompt(
    text: str,
    *,
    chat_id: int = 0,
    priority: int = 0,
    source: str = "cli",
    title: str = "",
    model: str = "auto",
) -> Path:
    """Создаёт промт в папке user/ (pending). Возвращает путь файла.

    Это точка входа команды `/task` в TG-боте и ручного CLI-добавления.
    model: позиция/алиас модели Баффи в стартовом списке выбора freebuff
           ("auto"/"0" = рекомендованная DeepSeek V4 Flash).
    """
    ensure_queue_dirs()
    tid = new_task_id()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fname = prompt_filename(tid, chat_id)
    path = queue_dir("pending") / fname

    if not title:
        # Первая строка текста как название (до ~60 символов)
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        title = first[:60***REMOVED*** or tid

    content = (
        f"# TASK: {title***REMOVED***\n\n"
        f"**ID:** {tid***REMOVED***\n"
        f"**Chat ID:** {chat_id***REMOVED***\n"
        f"**Created:** {stamp***REMOVED***\n"
        f"**Priority:** {int(priority)***REMOVED***\n"
        f"**Status:** pending\n"
        f"**Source:** {source***REMOVED***\n"
        f"**Model:** {model***REMOVED***\n"
        f"**Iteration:** 1\n"
        f"**Max Iterations:** 3\n"
        f"**Max Clarifications:** 10\n"
        f"\n---\n\n"
        f"{text.strip()***REMOVED***\n"
        f"\n---\n\n"
        f"## Отчёт\n\n**Результат:** (ожидает диспетчер)\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def parse_prompt(path: Path) -> Optional[PromptMeta***REMOVED***:
    """Разбирает файл промта в PromptMeta. None при невалидном файле."""
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    meta: Dict[str, str***REMOVED*** = {***REMOVED***
    title = ""
    body_start = 0
    in_header = False
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith("# TASK:"):
            title = stripped[len("# TASK:"):***REMOVED***.strip()
            in_header = True
            continue
        if in_header:
            m = _META_PATTERN.match(stripped)
            if m:
                meta[m.group("key").strip().lower()***REMOVED*** = m.group("value").strip()
                continue
            if stripped == "---":
                body_start = i + 1
                break
        if stripped == "---" and not in_header:
            body_start = i + 1
            break

    body_lines = [ln for ln in lines[body_start:***REMOVED*** if ln.strip()***REMOVED***
    body = "\n".join(body_lines)

    # Секция отчёта
    report = ""
    if "## Отчёт" in body:
        body, _, report_part = body.partition("## Отчёт")
        report = report_part.strip()

    def _int(key: str, default: int = 0) -> int:
        try:
            return int(meta.get(key, default))
        except (TypeError, ValueError):
            return default

    return PromptMeta(
        path=path,
        task_id=meta.get("id", path.stem),
        chat_id=_int("chat id"),
        created=meta.get("created", ""),
        priority=_int("priority"),
        source=meta.get("source", "cli"),
        status=meta.get("status", "pending"),
        title=title or meta.get("id", path.stem),
        body=body.strip(),
        report=report,
        iteration=_int("iteration", 1),
        max_iterations=_int("max iterations", 3),
        model=meta.get("model", "auto").strip() or "auto",
        # CON-35: backoff-метаданные из шапки (0/false если отсутствуют)
        backoff_streak=_int("backoff streak"),
        backoff_notified=meta.get("backoff notified", "").strip().lower() == "true",
        clarification_count=_int("clarification count", 0),
        max_clarifications=_int("max clarifications", 10),
    )


def scan_pending() -> List[PromptMeta***REMOVED***:
    """Все ожидающие промты из user/, отсортированные по приоритету (убыв) затем по имени."""
    ensure_queue_dirs()
    results: List[PromptMeta***REMOVED*** = [***REMOVED***
    for p in sorted(queue_dir("pending").glob("*.md")):
        meta = parse_prompt(p)
        if meta is not None:
            results.append(meta)
    results.sort(key=lambda m: (-m.priority, str(m.path.name)))
    return results


def scan_resumable() -> List[PromptMeta***REMOVED***:
    """Multi-turn: сканирует running/ на файлы со status 'running-pending' или 'running-resumable'.

    Chronologically ordered by iteration (ascending: earlier tasks first). Excludes
    файлы уже в `running/.in_progress/` (atomic lock для защиты от cron-overlap).
    """
    ensure_queue_dirs()
    sub = prompts_dir() / "running"
    active = sub / ".in_progress"
    results: List[PromptMeta***REMOVED*** = [***REMOVED***
    for p in sorted(sub.glob("*.md")):
        # Skip files currently held under .in_progress/ lock (active processing).
        if active in p.parents:
            continue
        meta = parse_prompt(p)
        if meta is None:
            continue
        if meta.status in ("running-pending", "running-resumable"):
            results.append(meta)
    # Earlier iter first; within same iter, alphabetical
    results.sort(key=lambda m: (m.iteration, str(m.path.name)))
    return results


def scan_in_progress_locked() -> List[Path***REMOVED***:
    """Возвращает файлы, заблокированные текущим cron-тиком (running/.in_progress/).

    Диагностика только — диспетчер не обрабатывает эти файлы. Используется для
    логов/чтобы сказать 'lock owner is active'.
    """
    ensure_queue_dirs()
    return sorted((prompts_dir() / "running" / ".in_progress").glob("*.md"))


def move_to_status(path: Path, status: str) -> Path:
    """Перемещает файл промта в папку нового статуса. Возвращает новый путь.

    WARNING: caller MUST reassign if it needs the post-rename path:
        p = move_to_status(p, "running")  # re-assign required (`p` is the OLD path)
    Detail: atomic `Path.rename()` — старый путь больше не существует после вызова.
    Test lock: test_queue_command_multiturn_badge в test_telegram_bot.py покрывает это.
    """
    ensure_queue_dirs()
    target_dir = queue_dir(status)
    new_path = target_dir / path.name
    if path != new_path and path.exists():
        path.rename(new_path)
    return new_path


def set_report(path: Path, status: str, report_text: str) -> Path:
    """Записывает отчёт и перемещает файл в папку статуса (done/failed)."""
    text = path.read_text(encoding="utf-8")
    text = text.replace("**Status:** pending", f"**Status:** {status***REMOVED***")
    text = text.replace("**Status:** running", f"**Status:** {status***REMOVED***")
    if "## Отчёт" in text:
        head, _, _tail = text.partition("## Отчёт")
        text = f"{head***REMOVED***## Отчёт\n\n{report_text.strip()***REMOVED***\n"
    else:
        text = f"{text***REMOVED***\n\n## Отчёт\n\n{report_text.strip()***REMOVED***\n"
    path.write_text(text, encoding="utf-8")
    return move_to_status(path, status)


def append_iteration(
    path: Path,
    iteration: int,
    pending_question: str,
    new_status: str = "running-pending",
    timestamp: str = "",
) -> Path:
    """Multi-turn: добавляет в файл секцию `--- Iteration N ---`, обновляет Status + Iteration.

    Pending_question извлечён из `.freebuff_result.pending_task` (string field).
    После append файл остаётся в running/ (НЕ делаем move) — следующий cron-тик
    обработает как resumable.

    Note: separator pattern включает `--- ` (with trailing space), чтобы отличать
    от уже существующих разделителей `---`.
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    text = path.read_text(encoding="utf-8")
    # Update Status + Iteration headers (in-place replacement)
    text = re.sub(r"\*\*Status:\*\*[^\n***REMOVED****", f"**Status:** {new_status***REMOVED***", text)
    text = re.sub(r"\*\*Iteration:\*\*[^\n***REMOVED****", f"**Iteration:** {iteration***REMOVED***", text)

    iter_block = (
        f"\n--- Iteration {iteration***REMOVED*** ({timestamp***REMOVED***) ---\n"
        f"**Баффи:** {pending_question.strip()***REMOVED***\n"
    )
    if "## Отчёт" in text:
        head, _, tail = text.partition("## Отчёт")
        # Replace existing '## Отчёт' section with new framing.
        report_prelude = f"## Отчёт\n\n**Статус:** iteration {iteration***REMOVED*** оставил pending_task; ожидает следующий cron-тик.\n\n"
        text = f"{head***REMOVED***{iter_block***REMOVED***\n{report_prelude***REMOVED***{tail.lstrip()***REMOVED***"
    else:
        text = f"{text***REMOVED***{iter_block***REMOVED***\n"
    path.write_text(text, encoding="utf-8")
    return path


def update_meta_value(path: Path, key: str, value: Any) -> Path:
    """Multi-turn helper: replace `**Key:** <value>` строки в шапке файла.

    Если ключа нет — добавляет перед первым `---` разделителем (новая метастрока).
    Используется для `**Status:**` updates без полного set_report() (когда
    move_to_status не нужен — файл остаётся в running/).
    """
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"\*\*{re.escape(key)***REMOVED***:\*\*[^\n***REMOVED****")
    if pattern.search(text):
        text = pattern.sub(f"**{key***REMOVED***:** {value***REMOVED***", text)
    else:
        # Insert before the body's first `---` separator
        if "\n---" in text:
            head, sep, tail = text.partition("\n---")
            text = f"{head***REMOVED***\n**{key***REMOVED***:** {value***REMOVED***\n{sep***REMOVED***{tail***REMOVED***"
        else:
            text = f"{text***REMOVED***\n**{key***REMOVED***:** {value***REMOVED***\n"
    path.write_text(text, encoding="utf-8")
    return path


def recover_stale_running(max_age_s: int = 3600) -> List[str***REMOVED***:
    """Возвращает зависшие промты из running/ обратно в user/ (по mtime).

    Если диспетчер упал между move_to_status(running) и set_report(done/failed),
    файл навсегда застревает в running/. Этот sweep (например, при старте cron)
    возвращает такие файлы в user/ для повторной обработки — «не терять задачу».

    Args:
        max_age_s: минимальный возраст файла (сек), чтобы считаться зависшим.
    Returns:
        Список имён возвращённых файлов.
    """
    ensure_queue_dirs()
    recovered: List[str***REMOVED*** = [***REMOVED***

    now = _time.time()
    for p in sorted(queue_dir("running").glob("*.md")):
        try:
            age = now - p.stat().st_mtime
        except OSError:
            continue
        if age > max_age_s:
            move_to_status(p, "pending")
            recovered.append(p.name)
    return recovered


def queue_counts() -> Dict[str, int***REMOVED***:
    """Счётчики по папкам (для /status и диагностики)."""
    ensure_queue_dirs()
    return {
        status: len(list(queue_dir(status).glob("*.md")))
        for status in ("pending", "running", "done", "failed")
    ***REMOVED***


if __name__ == "__main__":
    # Ручной CLI: python scripts_01/prompt_queue.py "<текст>"
    import sys

    text = " ".join(sys.argv[1:***REMOVED***)
    if not text:
        print("Usage: python scripts_01/prompt_queue.py '<task text>'")
        sys.exit(1)
    path = write_user_prompt(text, source="cli")
    print(f"✅ Промт создан: {path***REMOVED***")
