"""prompt_dispatcher.py — диспетчер промтов (promt 48).

Берёт промты из `pompts_11/user/`, запускает Баффи на выполнение,
перемещает в `done/` (✅) или `failed/` (❌) и отправляет отчёт в Telegram
(в Избранное через `report_to_saved_messages` + reply в исходный чат).

Цикл (один промт):
  1. scan_pending() → берём первый (приоритет, затем порядок создания)
  2. move_to_status(path, "running")
  3. launch Баффи через freebuff_plugin_03.wrapper.launch_and_wait (phase-based, анти-OOM)
  4. success → set_report(done, отчёт)  |  failure → set_report(failed, причина)
  5. TG-отчёт: report_to_saved_messages(отчёт) + best-effort reply в chat_id

Reuse First (promt 48): запуск через уже существующий wrapper (тот же, что
использует MCP-инструмент `run_freebuff`), TG-отправка через уже
существующий `core_02/telegram_contract`. Ничего не дублируем.

Usage:
    python scripts_01/prompt_dispatcher.py --once   # обработать 1 промт (для cron)
    python scripts_01/prompt_dispatcher.py --all    # обработать все ожидающие
    python scripts_01/prompt_dispatcher.py --dry-run# показать что бы обработалось

v5.79.0+: multi-turn (interactive) режим.
  - `running/resumable` файлы (status running-pending или running-resumable)
    подхватываются первыми через `scan_resumable()`.
  - Atomic lock через `running/.in_progress/` (concurrent cron-overlap защита).
  - `.freebuff_result.pending_task` (string field) сигнализирует продолжение цикла.
  - `max_iterations` cap per-task (default 3); at limit, force-failed.
  - Итерация body накапливается через `append_iteration` (не теряется между тиками).
  - TG badge `[Multi-turn N/M]` на каждой итерации.
  - `running-resumable` status (для future `/answer` TG command) — зарезервирован,
    пока нигде не устанавливается (см. followup).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# WORKSPACE в sys.path ДО импорта prompt_queue (прямой запуск `python scripts_01/...`).
WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from scripts_01.prompt_queue import (
    PromptMeta,
    append_iteration,
    move_to_status,
    parse_prompt,  # Task 1 (promt 61): used by process_answer для поиска running/-файла
    prompts_dir,
    recover_stale_running,
    scan_pending,
    scan_resumable,
    set_report,
    update_meta_value,
    queue_counts,
)

# ── Logging ────────────────────────────────────────────────────

logger = logging.getLogger("prompt_dispatcher")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(
        logging.Formatter("[prompt_dispatcher) %(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


# ── CON-33 (v5.89.0): single-instance backoff ────────────────────
#
# ── Task 1 (promt 61): TG `/answer` handler ──────────────────────────────────────
#
# /answer <task_id> <text>: резюмит running-resumable задачу после ответа
# пользователя в TG. Используется TG handler `cmd_answer`.


def process_answer(task_id: str, answer_text: str) -> Dict[str, Any]:
    """Task 1 (promt 61): резюм running-resumable задачи после user answer.

    Flow:
      1. Find file в running/ matching task_id (Status должен быть `running-resumable`).
      2. Status → `running-pending` (next cron tick resumes work).
      3. Iteration → +1 (answer разрешает clarification → следующий work-iteration).
      4. Clarification Count → 0 (clarification была разрешена answer'ом).
      5. Append `-- Answer received ... -- User answer:` block в файл (TG ответ
         виден Buffalo при следующей итерации).

    Returns:
      - {"ok": True, "task_id", "old_status", "new_status", "old_iteration",
        "new_iteration", "path"] при успехе
      - {"ok": False, "error": "task_id ... not found in running/", ...}
      - {"ok": False, "error": "task_id ... not awaiting answer (status=...)", ...}
    """
    # 1. Find file в running/
    matching = []
    running_root = prompts_dir() / "running"
    in_progress = running_root / ".in_progress"
    for p in sorted(running_root.glob("*.md")):
        if in_progress in p.parents:
            continue
        meta = parse_prompt(p)
        if meta is not None and meta.task_id == task_id:
            matching.append(meta)

    if not matching:
        return {
            "ok": False,
            "error": f"task_id {task_id} not found in running/",
            "task_id": task_id,
        }

    meta = matching[0]
    if meta.status != "running-resumable":
        return {
            "ok": False,
            "error": (
                f"task_id {task_id} not awaiting answer "
                f"(current status={meta.status})"
            ),
            "task_id": task_id,
            "current_status": meta.status,
        }

    # 2-4. Update headers (use existing update_meta_value helper)
    new_iter = meta.iteration + 1
    update_meta_value(meta.path, "Status", "running-pending")
    update_meta_value(meta.path, "Iteration", str(new_iter))
    update_meta_value(meta.path, "Clarification Count", "0")

    # 5. Append answer block (видим в следующей итерации Buffalo как часть body)
    timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    answer_block = (
        f"\n--- Answer received ({timestamp}) ---\n"
        f"**User answer:** {answer_text.strip()}\n"
    )
    text = meta.path.read_text(encoding="utf-8")
    if "## Отчёт" in text:
        head, _, tail = text.partition("## Отчёт")
        text = f"{head}{answer_block}\n## Отчёт\n{tail}"
    else:
        text = f"{text}{answer_block}\n"
    meta.path.write_text(text, encoding="utf-8")

    logger.info(
        "process_answer: task_id=%s → resumable→pending, iter %s→%s, cc reset",
        task_id, meta.iteration, new_iter,
    )

    return {
        "ok": True,
        "task_id": task_id,
        "old_status": "running-resumable",
        "new_status": "running-pending",
        "old_iteration": meta.iteration,
        "new_iteration": new_iter,
        "path": str(meta.path),
    }


# v5.88.0 ввёл deferral (blocked_single_instance → возврат в user/ вместо
# ложного failed), но каждый cron-тик (каждые 5 мин) продолжал спавнить tmux и
# ждать до ~90s, чтобы обнаружить занятый инстанс. CON-33 закрывает это дешёвым
# pre-check'ом: pgrep по подстроке пути бинаря freebuff (мс), без tmux/monitor,
# без OOM-риска — «skip, пока живой инстанс обнаружен» (deferred_at метка + skip).

# Подстрока пути бинаря freebuff, общая для host-Termux cmdline
# (/data/data/com.termux/.../config/manicode/freebuff) и inside-proot
# (/root/.config/manicode/freebuff). НЕ матчит обёртку (~/.local/bin/freebuff)
# и прочие процессы — только реальный бинарь (и его proot-wrapper).
_LIVE_INSTANCE_PGREP_PATTERN = "config/manicode/freebuff"


def _now_iso() -> str:
    """ISO-метка UTC для **Deferred At:** аудита (CON-33)."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _live_instance_busy() -> bool:
    """Дешёвый pre-check: занят ли единственный инстанс freebuff живой сессией.

    pgrep -f по подстроке пути бинаря (мс, без tmux/monitor). Fail-open:
    любая ошибка → False (разрешаем spawn; wrapper всё равно поймает блокер
    маркером `_SINGLE_INSTANCE_MARKERS` и вернёт deferral, как до CON-33).

    Note: backoff-пропуск целиком основан на этом pgrep-сигнале; **Deferred At:**
    метка — только аудит-след для чтения человеком, backoff её НЕ читает.
    """
    try:
        r = subprocess.run(
            ["pgrep", "-f", _LIVE_INSTANCE_PGREP_PATTERN],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


# ── CON-35 (v5.90.0): backoff-cooldown + TG-уведомление один раз ──
#
# CON-33 даёт мгновенный backoff, но молчит каждый тик. CON-35: если инстанс
# занят N+ тиков cron подряд, уведомляем в TG ОДИН раз (не каждый тик).
# Счётчик живёт в мете файла задачи (**Backoff Streak:**), переживает cron-тики.
# Cron тикает каждые 5 мин → 6 тиков ≈ 30 мин ожидания.

BACKOFF_NOTIFY_TICKS = 6


def _bump_backoff_streak(meta: PromptMeta, threshold: int, send_tg: bool) -> None:
    """CON-35: инкремент **Backoff Streak:** в мете файла задачи.

    При достижении порога threshold — TG-уведомление ОДИН раз (флаг
    **Backoff Notified:** true предотвращает повтор), не каждый тик.
    """
    new_streak = meta.backoff_streak + 1
    update_meta_value(meta.path, "Backoff Streak", str(new_streak))
    # threshold > 0: 0 = уведомления выключены (--backoff-notify 0).
    # Флаг **Backoff Notified:** ставим ТОЛЬКО при реальной отправке TG — иначе
    # --no-tg тик, пересекший порог, навсегда подавил бы будущие уведомления.
    if threshold > 0 and new_streak >= threshold and not meta.backoff_notified:
        if send_tg:
            update_meta_value(meta.path, "Backoff Notified", "true")
            _send_tg_report(
                meta,
                f"⏳ Очередь ждёт: инстанс freebuff занят {new_streak} тиков "
                f"подряд (~{new_streak * 5} мин). Задача `{meta.task_id}` "
                f"выполнится автоматически после закрытия живой сессии "
                f"(CON-35, уведомление один раз).",
            )
        if send_tg:
            logger.info(
                "CON-35: backoff streak %s для %s достиг порога %s; TG отправлено",
                new_streak,
                meta.task_id,
                threshold,
            )
        else:
            logger.info(
                "CON-35: backoff streak %s для %s достиг порога %s; TG off — флаг не ставился",
                new_streak,
                meta.task_id,
                threshold,
            )


def _reset_backoff_streak(meta: PromptMeta) -> None:
    """CON-35: сброс backoff-меты, когда задача реально обрабатывается."""
    if meta.backoff_streak or meta.backoff_notified:
        update_meta_value(meta.path, "Backoff Streak", "0")
        update_meta_value(meta.path, "Backoff Notified", "false")


# ── Запуск Баффи (инъектируемо для тестов) ─────────────────────

def _default_launcher(
    prompt: str, cwd: str, timeout: int, model: str = "auto"
) -> Dict[str, Any]:
    """Реальный запуск Баффи через wrapper — phase-based (анти-OOM для cron).

    wrapper.launch_and_wait = launch() + опрос .freebuff_result: Python
    завершается сразу после старта сессии (память freed), Codebuff работает
    один, результат забирается файлом. В отличие от synchronous_oneshot,
    не держит Python + Codebuff в памяти одновременно.

    model: модель Баффи из шапки задачи (**Model:**) — прокидвается в
    launch_and_wait → monitor.sh (выбор на стартовом экране freebuff).
    """
    from freebuff_plugin_03 import wrapper

    return wrapper.launch_and_wait(
        prompt=prompt,
        cwd=cwd,
        timeout=timeout,
        model=model,
    )


LauncherFn = Callable[[str, str, int, str], Dict[str, Any]]


# ── Atomic lock helpers (multi-turn): running/.in_progress/ ───────

def _lock_subdir() -> Path:
    """Папка-блокировка: running/.in_progress/ (atomic-rename based, no daemon)."""
    sub = prompts_dir() / "running" / ".in_progress"
    sub.mkdir(parents=True, exist_ok=True)
    return sub


def _move_to_lock(path: Path) -> Path:
    """Atomic move file under running/ → running/.in_progress/ (concurrency lock).

    Raises FileNotFoundError если файл уже перемещён (другой cron-тик владеет lock).
    """
    target = _lock_subdir() / path.name
    path.rename(target)
    return target


def _release_from_lock(lock_path: Path, target_status: str) -> Path:
    """Move out of running/.in_progress/ → queue_dir(target_status).

    Used после завершения итерации: running/ (multi-turn continue),
    или done/failed/ (terminal).
    """
    return move_to_status(lock_path, target_status)


# ── pending_task extraction (multi-turn signal) ────────────────────

def _extract_pending_task(result: Dict[str, Any]) -> Optional[tuple[str, str]]:
    """Парсит `.freebuff_result` → discriminated tuple `(kind, text)` или None.

    Task 2 (promt 61): поддержка двух форматов `pending_task`:
      - Legacy `string`: backwards-compat → (`"work"`, pt_text)
      - New dict `{type, text}`: kind = `"work"` | `"clarification"`

    Returns:
      - None если malformed JSON / пустой pending_task
      - `("work", text)` для legacy strings и для work-type dicts
      - `("clarification", text)` для clarification-type dicts

    Fallback на `"work"` для bare strings — не ломает существующих агентов
    (Баффи выводит `.freebuff_result.pending_task: "<вопрос>"` как plain string,
    который теперь автоматически интерпретируется как work pending next, как и до Task 2).
    Новый Task 1 (TG `/answer`) сможет объявить kind="clarification" через dict format.
    """
    raw = result.get("result") if isinstance(result, dict) else None
    if not raw or not isinstance(raw, str):
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    pt = data.get("pending_task")
    # Legacy bare string → treat as 'work' (existing behaviour, no migration needed)
    if isinstance(pt, str) and pt.strip():
        return ("work", pt.strip())
    # New discriminated dict → typed routing
    if isinstance(pt, dict):
        kind = pt.get("type", "work")
        text = pt.get("text", "")
        if (
            isinstance(kind, str)
            and kind in ("work", "clarification")
            and isinstance(text, str)
            and text.strip()
        ):
            return (kind, text.strip())
    return None


def _format_report(
    meta: PromptMeta,
    result: Dict[str, Any],
    multi_turn_badge: Optional[str] = None,
) -> str:
    """Форматирует отчёт для файла и TG.

    multi_turn_badge:
      - None   → обычный single-turn отчёт
      - str    → '[Multi-turn N/M]' префикс в Статусе; полезно при итерациях
    """
    duration = result.get("duration")
    if result.get("success"):
        head = "✅ Выполнено"
    else:
        head = "❌ Не выполнено"
    if multi_turn_badge:
        head = f"{head} ({multi_turn_badge})"
    lines = [
        f"**Статус:** {head}",
        f"**Задача:** {meta.title}",
        f"**Task ID:** {meta.task_id}",
    ]
    if multi_turn_badge:
        lines.append(f"**Итерация:** {meta.iteration}/{meta.max_iterations}")
    if duration is not None:
        lines.append(f"**Длительность:** {duration}s")
    output = result.get("output") or result.get("result") or ""
    if output:
        lines.append("\n**Вывод:**\n```\n" + output.strip()[:2000] + "\n```")
    err = result.get("error")
    if err:
        lines.append(f"\n**Ошибка:** {err}")
    return "\n".join(lines)


def _send_to_chat(chat_id: int, text: str) -> Optional[int]:
    """Отправка произвольному chat_id через telegram_contract (CON-19).

    Единственный chokepoint отправки — public `send_to_chat` в
    `core_02/telegram_contract.py` (тот же connect/send/disconnect, что у
    report_*). Диспетчер — sync CLI, поэтому async оборачивается в asyncio.run.
    None-safe (CAN-14): TG-недоступность не роняет диспетчер.
    """
    try:
        from core_02.telegram_contract import send_to_chat

        return asyncio.run(send_to_chat(chat_id, text))
    except Exception as e:
        logger.warning("TG reply to chat %s failed: %s", chat_id, e)
        return None


def _send_tg_report(meta: PromptMeta, report_text: str) -> Optional[int]:
    """Best-effort TG-отправка: в Избранное + reply в исходный чат.

    report_to_saved_messages — async, поэтому asyncio.run (диспетчер — sync CLI).
    None-safe (CAN-14): TG-недоступность не роняет диспетчер.
    """
    saved_id: Optional[int] = None
    try:
        from core_02.telegram_contract import port_to_saved_messages

        saved_id = asyncio.run(
            report_to_saved_messages(
                f"📨 [prompt dispatcher] Задача `{meta.task_id}`\n\n{report_text}"
            )
        )
    except Exception as e:
        logger.warning("TG report to Saved Messages failed: %s", e)

    if meta.chat_id:
        _send_to_chat(meta.chat_id, report_text)

    return saved_id


def _dispatch_multi_turn_iteration(
    meta: PromptMeta,
    launcher: LauncherFn,
    timeout: int,
    send_tg: bool,
) -> Dict[str, Any]:
    """Multi-turn BRANCH: process one iteration of a resumable task.

    Flow:
      1. Atomic lock: move file to running/.in_progress/ (concurrent cron skip).
      2. Launch with FULL body (includes all prior iteration transcripts).
      3. Parse .freebuff_result for `pending_task` (string field).
      4a. pending_task present + iter+1 <= max → append iteration, release to running/ as running-pending.
      4b. pending_task present + iter+1 > max → release to failed/ with max_iterations_reached.
      4c. NO pending_task → single-turn terminal behavior (done/failed).

    Returns dict с multi-turn metadata (iteration, max_iterations, pending_task).
    """
    logger.info(
        "Multi-turn iter %s/%s для %s: %s",
        meta.iteration,
        meta.max_iterations,
        meta.task_id,
        meta.title,
    )

    # 1. Atomic lock
    try:
        locked_path = _move_to_lock(meta.path)
    except FileNotFoundError:
        logger.warning(
            "Multi-turn SKIP %s: lock conflict (другой cron-тик уже владеет файлом)",
            meta.task_id,
        )
        return {
            "handled": False,
            "task_id": meta.task_id,
            "status": "skipped_locked",
        }

    # 2. Launch с полной body (включает transcript прошлых итераций)
    try:
        result = launcher(meta.body, str(WORKSPACE), timeout, meta.model)
    except Exception as e:
        logger.exception("Multi-turn launch failed for %s", meta.task_id)
        result = {"success": False, "error": str(e), "output": ""}

    # 2b. Single-instance blocker (v5.88.0): та же deferral-логика что в
    # dispatch_one. Живая сессия занимает единственный инстанс → spawned
    # экземпляр не стартует. НЕ фейлим: возвращаем файл из lock в running/
    # как running-pending, следующий cron-тик повторит итерацию.
    if result.get("blocked_single_instance"):
        update_meta_value(locked_path, "Status", "running-pending")
        update_meta_value(locked_path, "Deferred At", _now_iso())
        release = _release_from_lock(locked_path, "running")
        report_text = (
            f"**Статус:** ⏸ Отложено (инстанс freebuff занят живой сессией)\n"
            f"**Задача:** {meta.title}\n"
            f"**Task ID:** {meta.task_id}\n\n"
            f"freebuff допускает только один запущенный инстанс; сейчас его "
            f"занимает живая (интерактивная) сессия. Итерация {meta.iteration}/"
            f"{meta.max_iterations} возвращена в `running/` и будет повторена "
            f"следующим тиком cron после закрытия живой сессии."
        )
        logger.info(
            "Multi-turn %s deferred (single-instance busy); kept in running/ as pending",
            meta.task_id,
        )
        if send_tg:
            _send_tg_report(meta, report_text)
        return {
            "handled": True,
            "task_id": meta.task_id,
            "status": "deferred_single_instance",
            "iteration": meta.iteration,
            "max_iterations": meta.max_iterations,
            "path": str(release),
        }

    # 3. Парсим .freebuff_result на pending_task (Task 2 promt 61: discriminated).
    pending = _extract_pending_task(result)

    if pending:
        kind, pt_text = pending
        # ── Clarification routing (Task 2) ──────────────────────────
        # Consumption: clarification_count++; budget: max_clarifications (default 10).
        # Work iteration remains UNCHANGED — long clarification сессия не сжигает work budget.
        if kind == "clarification":
            next_cc = meta.clarification_count + 1
            if next_cc > meta.max_clarifications:
                # Clarification budget exhausted (work iteration preserved!)
                logger.warning(
                    "Multi-turn MAX_CLARIFICATIONS_REACHED %s on cc %s/%s; text: %s",
                    meta.task_id,
                    meta.clarification_count,
                    meta.max_clarifications,
                    pt_text[:100],
                )
                release = _release_from_lock(locked_path, "failed")
                badge = f"Multi-turn clarification {meta.clarification_count}/{meta.max_clarifications} MAX-reached"
                report_text = _format_report(meta, result, multi_turn_badge=badge)
                report_text += (
                    f"\n\n**Reason:** max_clarifications_reached "
                    f"(work iteration {meta.iteration}/{meta.max_iterations} preserved)\n"
                    f"**Последний pending_task:** {pt_text}\n"
                )
                final = set_report(release, "failed", report_text)
                if send_tg:
                    _send_tg_report(meta, report_text)
                return {
                    "handled": True,
                    "task_id": meta.task_id,
                    "status": "failed-multi-turn-max-clarification",
                    "iteration": meta.iteration,
                    "max_iterations": meta.max_iterations,
                    "clarification_count": meta.clarification_count,
                    "max_clarifications": meta.max_clarifications,
                    "reason": "max_clarifications_reached",
                    "pending_task": pt_text,
                    "path": str(final),
                }
            # Continue cycle — append clarification, set status to resumable (paused, awaits TG /answer).
            append_iteration(
                locked_path,
                meta.iteration,  # work iter unchanged
                pt_text,
                new_status="running-resumable",  # Task 1: paused, awaiting TG /answer
            )
            update_meta_value(locked_path, "Clarification Count", str(next_cc))
            release = _release_from_lock(locked_path, "running")
            badge = f"Multi-turn clarification {next_cc}/{meta.max_clarifications}"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += (
                f"\n\n**Следующий pending_task:** {pt_text}\n"
                f"**Work iter:** {meta.iteration}/{meta.max_iterations} (не изменился)\n"
            )
            if send_tg:
                _send_tg_report(meta, report_text)
            logger.info(
                "Multi-turn clarification %s/%s для %s (work iter stays %s/%s) → pending next",
                next_cc,
                meta.max_clarifications,
                meta.task_id,
                meta.iteration,
                meta.max_iterations,
            )
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "multi-turn-pending-clarification",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "clarification_count": next_cc,
                "max_clarifications": meta.max_clarifications,
                "pending_task": pt_text,
                "path": str(release),
            }

        # ── Work iteration routing (legacy default, unchanged behaviour) ──
        # Consumption: iteration++; budget: max_iterations (default 3).
        next_iter = meta.iteration + 1
        if next_iter > meta.max_iterations:
            # 4b. Max iterations reached → forced terminate
            logger.warning(
                "Multi-turn MAX_REACHED %s on iter %s/%s; pending_task: %s",
                meta.task_id,
                meta.iteration,
                meta.max_iterations,
                pt_text[:100],
            )
            release = _release_from_lock(locked_path, "failed")
            badge = f"Multi-turn {meta.iteration}/{meta.max_iterations} MAX-reached"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += (
                f"\n\n**Reason:** max_iterations_reached "
                f"(clarification count {meta.clarification_count}/{meta.max_clarifications} preserved)\n"
                f"**Последний pending_task:** {pt_text}\n"
            )
            final = set_report(release, "failed", report_text)
            if send_tg:
                _send_tg_report(meta, report_text)
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "failed-multi-turn-max",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "reason": "max_iterations_reached",
                "pending_task": pt_text,
                "path": str(final),
            }
        else:
            # 4a-continue. Append iteration + release back to running/ as running-pending.
            append_iteration(
                locked_path,
                next_iter,
                pt_text,
                new_status="running-pending",
            )
            release = _release_from_lock(locked_path, "running")
            badge = f"Multi-turn {meta.iteration}/{meta.max_iterations} pending next"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += f"\n\n**Следующий pending_task:** {pt_text}\n"
            if send_tg:
                _send_tg_report(meta, report_text)
            logger.info(
                "Multi-turn %s/%s для %s → pending next (released to running/)",
                meta.iteration,
                meta.max_iterations,
                meta.task_id,
            )
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "multi-turn-pending",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "pending_task": pt_text,
                "path": str(release),
            }

    # 4c. NO pending_task: terminal behavior (done / failed)
    badge = f"Multi-turn {meta.iteration}/{meta.max_iterations} done"
    report_text = _format_report(meta, result, multi_turn_badge=badge)
    if result.get("success"):
        final = set_report(locked_path, "done", report_text)
        status = "done"
    else:
        final = set_report(locked_path, "failed", report_text)
        status = "failed"
    logger.info(
        "Multi-turn Промт %s (iter %s/%s) → %s (terminal)",
        meta.task_id,
        meta.iteration,
        meta.max_iterations,
        status,
    )
    if send_tg:
        _send_tg_report(meta, report_text)
    return {
        "handled": True,
        "task_id": meta.task_id,
        "status": status,
        "iteration": meta.iteration,
        "max_iterations": meta.max_iterations,
        "path": str(final),
    }


def dispatch_one(
    launcher: LauncherFn = _default_launcher,
    timeout: int = 300,
    send_tg: bool = True,
    skip_busy_precheck: bool = False,
    backoff_notify: int = BACKOFF_NOTIFY_TICKS,
    resumable_only: bool = False,  # Task 3 (promt 61): skip user/ queue, only running/-resumable
) -> Dict[str, Any]:
    """Multi-turn-aware (v5.79.0): сначала resumable running/, потом pending user/.

    CON-33 (v5.89.0): если единственный инстанс freebuff занят живой сессией,
    НЕ спавним tmux впустую — дешёвый pgrep pre-check возвращает
    `deferred_single_instance_backoff` без файловых операций (задача остаётся
    в user/ или running/, не теряется, не фейлится).

    CON-35 (v5.90.0): при backoff счётчик **Backoff Streak:** в мете задачи
    инкрементируется; при достижении `backoff_notify` тиков подряд — TG-отчёт
    отправляется ОДИН раз (не каждый тик). При реальном запуске мета сбрасывается.

    skip_busy_precheck: True для задач 2..N в рамках одного --all (после первого
    успешного launch занятость — это наш собственный инстанс, не внешний).

    Returns:
      - {"handled": False, "status": "noop"}       — оба списка пусты
      - {"handled": False, "status": "deferred_single_instance_backoff"} — инстанс занят (CON-33)
      - {"handled": True, "task_id": ..., "status": "multi-turn-pending" | "failed-multi-turn-max" | "done" | "failed", ...}
    """
    resumable = scan_resumable()
    # Task 3: --resumable-only → skip user/ queue entirely (только running/-resumable)
    pending = [] if resumable_only else scan_pending()

    # ── CON-33 pre-check: инстанс занят → backoff без spawn ──
    # Порядок: дешёвая проверка очереди ПЕРЕД pgrep (не гоняем pgrep на пустой
    # очереди). Pre-check — только оптимизация; гонку с параллельным cron-тиком
    # по-прежнему ловит wrapper (`blocked_single_instance` → deferral).
    if not skip_busy_precheck and (resumable or pending) and _live_instance_busy():
        # CON-35: инкремент счётчика backoff-тиков; TG один раз при пороге.
        target = (resumable or pending)[0]
        _bump_backoff_streak(target, backoff_notify, send_tg)
        logger.info(
            "Single-instance busy (CON-33 pre-check) → backoff: не спавним tmux; "
            "следующий тик cron повторит после закрытия живой сессии"
        )
        return {
            "handled": False,
            "status": "deferred_single_instance_backoff",
            "task_id": target.task_id,
        }

    # ── MULTI-TURN: сначала resumable running/ ────────────────
    if resumable:
        _reset_backoff_streak(resumable[0])
        return _dispatch_multi_turn_iteration(
            resumable[0], launcher, timeout, send_tg
        )

    # ── SINGLE-TURN: existing pending behavior ────────────────
    if not pending:
        logger.info("Очередь пуста — нет промтов в user/")
        return {"handled": False, "status": "noop"}

    meta = pending[0]
    _reset_backoff_streak(meta)
    logger.info("Обработка промта %s: %s", meta.task_id, meta.title)

    # 1. moving → running (anti-race: atomic rename; if cron raced us → skip gracefully).
    # Dual-path safety: и bot, и cron могут вызвать `dispatch_one` параллельно.
    # Первый успешно сделает `move_to_status`, второй поймает FileNotFoundError → noop.
    try:
        running_path = move_to_status(meta.path, "running")
        meta.path = running_path
    except FileNotFoundError:
        logger.info(
            "dispatch_one: %s disappeared mid-move (raced by parallel cron spawn); skipping lock",
            meta.task_id,
        )
        return {
            "handled": False,
            "status": "skipped_locked",
            "task_id": meta.task_id,
        }
    report_text = ""

    # 2. Запуск Баффи
    try:
        result = launcher(meta.body, str(WORKSPACE), timeout, meta.model)
    except Exception as e:
        logger.exception("launch failed for %s", meta.task_id)
        result = {"success": False, "error": str(e), "output": ""}

    # 2b. Single-instance blocker (v5.88.0): живая сессия пользователя занимает
    # единственный инстанс freebuff → spawned-экземпляр видит 'already running'
    # и не стартует (wrapper помечает blocked_single_instance). Это НЕ ошибка
    # задачи — возвращаем её в user/ (deferral); следующий cron-тик попробует
    # снова после освобождения инстанса. Иначе каждый тик давал бы ложный failed.
    if result.get("blocked_single_instance"):
        # CON-33: фиксируем момент deferral для аудита. Следующий тик уже
        # отсекается дешёвым pgrep pre-check'ом выше (без spawn).
        update_meta_value(running_path, "Deferred At", _now_iso())
        deferred_path = move_to_status(running_path, "user")
        report_text = (
            f"**Статус:** ⏸ Отложено (инстанс freebuff занят живой сессией)\n"
            f"**Задача:** {meta.title}\n"
            f"**Task ID:** {meta.task_id}\n\n"
            f"freebuff допускает только один запущенный инстанс; сейчас его "
            f"занимает живая (интерактивная) сессия. Задача возвращена в "
            f"очередь `user/` и будет обработана следующим тиком cron после "
            f"закрытия живой сессии. Это не ошибка задачи."
        )
        logger.info(
            "Промт %s → deferred (single-instance busy); returned to user/",
            meta.task_id,
        )
        if send_tg:
            _send_tg_report(meta, report_text)
        return {
            "handled": True,
            "task_id": meta.task_id,
            "status": "deferred_single_instance",
            "path": str(deferred_path),
        }

    # 3. Detect multi-turn signal (v5.79.0 + Task 2 promt 61 discriminated).
    # Первый dispatch из user/ может получить pending_task — если kind=='clarification'
    # (Task 2 multi-turn сессия с уточнениями), он bump'ит только clarification_count
    # НЕ трогая iteration. work budget остаётся для будущих настоящих work-iter.
    # Note: НЕ guard'им по `max_iterations > 1` — max=1 + work-pending должна force-fail
    # (next_iter=2 > max=1 → max_iterations_reached), а не fall through в single-turn done.
    pending = _extract_pending_task(result)
    if pending:
        kind, pt_text = pending
        # ── Clarification routing (Task 2) ──────────────────────────
        if kind == "clarification":
            next_cc = meta.clarification_count + 1
            if next_cc > meta.max_clarifications:
                logger.warning(
                    "Single-turn init: MAX_CLARIFICATIONS_REACHED %s on cc %s/%s; text: %s",
                    meta.task_id,
                    meta.clarification_count,
                    meta.max_clarifications,
                    pt_text[:100],
                )
                badge = f"Multi-turn clarification {meta.clarification_count}/{meta.max_clarifications} MAX-reached"
                report_text = _format_report(meta, result, multi_turn_badge=badge)
                report_text += (
                    f"\n\n**Reason:** max_clarifications_reached "
                    f"(work iteration {meta.iteration}/{meta.max_iterations} preserved)\n"
                    f"**Последний pending_task:** {pt_text}\n"
                )
                final = set_report(running_path, "failed", report_text)
                if send_tg:
                    _send_tg_report(meta, report_text)
                return {
                    "handled": True,
                    "task_id": meta.task_id,
                    "status": "failed-multi-turn-max-clarification",
                    "iteration": meta.iteration,
                    "max_iterations": meta.max_iterations,
                    "clarification_count": meta.clarification_count,
                    "max_clarifications": meta.max_clarifications,
                    "reason": "max_clarifications_reached",
                    "pending_task": pt_text,
                    "path": str(final),
                }
            # Append clarification, set status to resumable (paused, awaits TG /answer).
            append_iteration(
                running_path,
                meta.iteration,
                pt_text,
                new_status="running-resumable",  # Task 1: paused, awaiting TG /answer
            )
            update_meta_value(running_path, "Clarification Count", str(next_cc))
            badge = f"Multi-turn clarification {next_cc}/{meta.max_clarifications}"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += (
                f"\n\n**Следующий pending_task:** {pt_text}\n"
                f"**Work iter:** {meta.iteration}/{meta.max_iterations} (не изменился)\n"
            )
            if send_tg:
                _send_tg_report(meta, report_text)
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "multi-turn-pending-clarification",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "clarification_count": next_cc,
                "max_clarifications": meta.max_clarifications,
                "pending_task": pt_text,
                "path": str(running_path),
            }

        # ── Work iteration routing (legacy default, unchanged) ────────
        next_iter = meta.iteration + 1  # =2 обычно
        if next_iter > meta.max_iterations:
            # max_iterations=1 forced-fail; либо iter > max после подсчёта
            logger.warning(
                "Single-turn but MAX_REACHED %s on iter %s/%s; pending_task: %s",
                meta.task_id,
                meta.iteration,
                meta.max_iterations,
                pt_text[:100],
            )
            badge = f"Multi-turn {meta.iteration}/{meta.max_iterations} MAX-reached"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += (
                f"\n\n**Reason:** max_iterations_reached "
                f"(clarification count {meta.clarification_count}/{meta.max_clarifications} preserved)\n"
                f"**Последний pending_task:** {pt_text}\n"
            )
            final = set_report(running_path, "failed", report_text)
            if send_tg:
                _send_tg_report(meta, report_text)
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "failed-multi-turn-max",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "reason": "max_iterations_reached",
                "pending_task": pt_text,
                "path": str(final),
            }
        else:
            # Multi-turn init: append + keep in running/ as running-pending
            append_iteration(
                running_path,
                next_iter,
                pt_text,
                new_status="running-pending",
            )
            badge = f"Multi-turn {meta.iteration}/{meta.max_iterations} pending next"
            report_text = _format_report(meta, result, multi_turn_badge=badge)
            report_text += f"\n\n**Следующий pending_task:** {pt_text}\n"
            logger.info(
                "Промт %s → multi-turn pending next (iter %s/%s, kept in running/)",
                meta.task_id,
                meta.iteration,
                meta.max_iterations,
            )
            if send_tg:
                _send_tg_report(meta, report_text)
            return {
                "handled": True,
                "task_id": meta.task_id,
                "status": "multi-turn-pending",
                "iteration": meta.iteration,
                "max_iterations": meta.max_iterations,
                "pending_task": pt_text,
                "path": str(running_path),
            }

    # 4. Terminal behavior (single-turn done / failed, NO multi-turn signal)
    report_text = _format_report(meta, result)
    try:
        if result.get("success"):
            final = set_report(running_path, "done", report_text)
            status = "done"
        else:
            final = set_report(running_path, "failed", report_text)
            status = "failed"
    except FileNotFoundError:
        # Race-safe: parallel cron may have moved file in between. Noop вместо крушения.
        logger.warning(
            "dispatch_one: running_path %s disappeared at terminal; race with cron? skipped",
            meta.task_id,
        )
        return {
            "handled": False,
            "status": "skipped_locked",
            "task_id": meta.task_id,
        }

    logger.info(
        "Промт %s → %s (файл: %s)",
        meta.task_id,
        status,
        final.name,
    )

    # 5. TG-отчёт
    if send_tg:
        _send_tg_report(meta, report_text)

    return {
        "handled": True,
        "task_id": meta.task_id,
        "status": status,
        "report": report_text,
        "path": str(final),
    }


def dispatch_all(
    launcher: LauncherFn = _default_launcher,
    timeout: int = 300,
    send_tg: bool = True,
    max_tasks: Optional[int] = None,
    backoff_notify: int = BACKOFF_NOTIFY_TICKS,
    resumable_only: bool = False,  # Task 3 (promt 61): see dispatch_one
) -> List[Dict[str, Any]]:
    """Обрабатывает все ожидающие промты (поочерёдно).

    CON-33: первый вызов dispatch_one идёт с pre-check'ом живого инстанса; если
    он вернул backoff (инстанс занят внешней сессией) — прерываем цикл сразу
    (не тратим время и память на остальные задачи). Последующие задачи (2..N)
    идут с skip_busy_precheck=True — после первого успешного launch занятость
    это наш собственный инстанс, повторный pgrep дал бы ложный backoff.
    """
    results: List[Dict[str, Any]] = []
    first = True
    while True:
        # Task 3: --resumable-only → skip user/ queue entirely (только running/-resumable)
        pending = [] if resumable_only else scan_pending()
        if not pending:
            break
        if max_tasks is not None and len(results) >= max_tasks:
            break
        result = dispatch_one(
            launcher=launcher,
            timeout=timeout,
            send_tg=send_tg,
            skip_busy_precheck=not first,
            backoff_notify=backoff_notify,
            resumable_only=resumable_only,
        )
        results.append(result)
        # CON-33: оба single-instance исхода (pre-check backoff и wrapper-блокер)
        # доказывают, что инстанс занят → остальные задачи в --all тоже упрутся
        # в блокер и будут впустую жечь spawn-циклы (~90s каждая). Останавливаемся.
        if result.get("status") in (
            "deferred_single_instance_backoff",
            "deferred_single_instance",
        ):
            break
        first = False
    return results


def _dry_run(resumable_only: bool = False) -> Dict[str, Any]:
    # Task 3: --resumable-only → report running/-resumable count (NOT user/ pending)
    if resumable_only:
        resumable = scan_resumable()
        return {
            "pending_count": 0,
            "tasks": [],
            "resumable_count": len(resumable),
            "resumable_tasks": [m.task_id for m in resumable],
            "counts": queue_counts(),
            "mode": "resumable-only",
        }
    pending = scan_pending()
    return {
        "pending_count": len(pending),
        "tasks": [m.task_id for m in pending],
        "counts": queue_counts(),
        "mode": "full",
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Freebuff prompt dispatcher (promt 48)")
    parser.add_argument("--once", action="store_true", help="Обработать один промт (для cron)")
    parser.add_argument("--all", action="store_true", help="Обработать все ожидающие")
    parser.add_argument("--dry-run", action="store_true", help="Показать очередь без обработки")
    parser.add_argument("--timeout", type=int, default=300, help="Таймаут запуска Баффи (с)")
    parser.add_argument("--no-tg", action="store_true", help="Не отправлять TG-отчёт")
    parser.add_argument(
        "--backoff-notify",
        type=int,
        default=BACKOFF_NOTIFY_TICKS,
        help=(
            "CON-35: TG-уведомление один раз, если инстанс занят N+ тиков подряд "
            f"(default {BACKOFF_NOTIFY_TICKS} = ~30 мин при cron 5 мин; 0 = выключено)"
        ),
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        help=(
            "Вернуть зависшие running/-промты (старше --recover-age) обратно в user/ "
            "и затем продолжить обычную обработку (или --dry-run, если указан)"
        ),
    )
    parser.add_argument("--recover-age", type=int, default=3600, help="Возраст для recover (с)")
    parser.add_argument(
        "--resumable-only",
        action="store_true",
        help=(
            "Task 3 (promt 61): process только running/-resumable tasks, "
            "пропуская user/ queue. crontab-poller для "
            "скорости цикла после TG /answer "
            "(вместо realtime rewrite — компромисс, see "
            "core_02/LESSONS.md)."
        ),
    )
    args = parser.parse_args()

    if args.recover:
        recovered = recover_stale_running(max_age_s=args.recover_age)
        if recovered:
            print(f"♻️ Восстановлено из running/ → user/: {len(recovered)}")
            for name in recovered:
                print(f"  • {name}")
        else:
            print("♻️ Зависших промтов в running/ нет.")

    if args.dry_run:
        info = _dry_run(resumable_only=args.resumable_only)
        if info["mode"] == "resumable-only":
            print(f"Resumable задач (--resumable-only): {info['resumable_count']}")
            for tid in info["resumable_tasks"]:
                print(f"  • {tid}")
        else:
            print(f"Ожидающих промтов (user/): {info['pending_count']}")
            for tid in info["tasks"]:
                print(f"  • {tid}")
        print(f"Папки: {info['counts']}")
        return 0

    if args.all:
        results = dispatch_all(
            timeout=args.timeout,
            send_tg=not args.no_tg,
            backoff_notify=args.backoff_notify,
            resumable_only=args.resumable_only,
        )
    else:
        results = [
            dispatch_one(
                timeout=args.timeout,
                send_tg=not args.no_tg,
                backoff_notify=args.backoff_notify,
                resumable_only=args.resumable_only,
            )
        ]

    done = sum(1 for r in results if r.get("status") == "done")
    failed = sum(1 for r in results if r.get("status") == "failed")
    noop = sum(1 for r in results if r.get("status") == "noop")
    deferred = sum(
        1
        for r in results
        if r.get("status") in ("deferred_single_instance_backoff", "deferred_single_instance")
    )
    print(
        f"✅ done: {done} | ❌ failed: {failed} | ⏸ noop: {noop} | "
        f"⏳ backoff (инстанс занят): {deferred}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
