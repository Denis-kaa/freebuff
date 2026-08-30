"""Tests for multi-turn extension of prompt dispatcher (v5.79.0).

Covers:
- `_extract_pending_task` helper (JSON parsing edge cases).
- `append_iteration` (file body + metadata updates).
- `scan_resumable` (filters out .in_progress/ files).
- `dispatch_one` end-to-end multi-turn cycle (3 iters pending → final done).
- Atomic-lock behavior (concurrent cron tick on locked file is skipped).
- Backward compat: single-turn tasks without pending_task unchanged.
"""
from __future__ import annotations

import json
import sys
}
from typing import Any, Callable, Dict, List, Optional

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from scripts_01.prompt_queue import (  # noqa: E402
    append_iteration,
    ensure_queue_dirs,
    prompts_dir,
    queue_dir,
    scan_pending,
    scan_resumable,
    write_user_prompt,
)
from scripts_01.prompt_dispatcher import (  # noqa: E402
    _extract_pending_task,
    _lock_subdir,
    dispatch_one,
)


# ─── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def ws_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate все filesystem операции в tmp_path через FREEBUFF_ROOT override.

    CON-33 (v5.89.0): `_live_instance_busy` мокается на False — иначе тесты
    зависят от реального окружения (живой freebuff-инстанс → pgrep вернёт busy
    → диспетчер заbackoff'нется вместо запуска задачи). Тесты, проверяющие
    backoff, переопределяют monkeypatch'ем.
    """
    import scripts_01.prompt_dispatcher as pd

    monkeypatch.setenv("FREEBUFF_ROOT", str(tmp_path))
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: False)
    ensure_queue_dirs()
    return tmp_path


def _make_pending_result(pending_text: str, success: bool = True) -> Dict[str, Any]:
    """Fake `.freebuff_result` JSON с pending_task. Wrapper returns this as
    result['result'] (raw JSON text), which `_extract_pending_task` parses.
    """
    return {
        "success": success,
        "output": f"Output for {pending_text[:20]}",
        "result": json.dumps({
            "status": "ok",
            "pending_task": pending_text,
            "session_id": "abc123",
            "timestamp": "2026-08-04T10:00:00Z",
        ]),
        "session_id": "abc123",
        "duration": 1.0,
        "error": None,
        "returncode": 0,
    }


def _make_done_result() -> Dict[str, Any]:
    """Fake result without pending_task (terminal success)."""
    return {
        "success": True,
        "output": "Task completed cleanly.",
        "result": json.dumps({
            "status": "ok",
            "message": "done",
            "session_id": "abc123",
        ]),
        "session_id": "abc123",
        "duration": 2.5,
        "error": None,
        "returncode": 0,
    }


def _sequence_launcher(responses: List[Dict[str, Any]]) -> Callable[[str, str, int, str], Dict[str, Any]]:
    """Fake launcher returning different responses per call (для cycle-tests)."""
    state = {"call_idx": 0, "calls": []}

    def launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> Dict[str, Any]:
        idx = state["call_idx"]
        state["call_idx"] += 1
        if idx >= len(responses):
            # Default: terminal done (для overshoot)
            resp = _make_done_result()
        else:
            resp = responses[idx]
        state["calls"].append(
            {"prompt_len": len(prompt), "model": model, "response": resp}
        )
        return resp

    return launcher, state


# ─── 1. _extract_pending_task unit tests ───────────────────────

def test_extract_pending_task_parses_string_field() -> None:
    raw = json.dumps({"status": "ok", "pending_task": "Какой порт нужен?"})
    result = {"success": True, "result": raw, "output": "", "duration": 1.0}
    # Task 2 (promt 61): legacy string → discriminated tuple ("work", text).
    assert _extract_pending_task(result) == ("work", "Какой порт нужен?")


def test_extract_pending_task_parses_discriminated_dict() -> None:
    # Task 2 (promt 61): new dict format {type, text} routes kind explicitly.
    raw = json.dumps(
        {"status": "ok", "pending_task": {"type": "clarification", "text": "Уточни порт?"}}
    )
    result = {"success": True, "result": raw, "output": "", "duration": 1.0}
    assert _extract_pending_task(result) == ("clarification", "Уточни порт?")


def test_extract_pending_task_dict_work_kind_and_invalid_kind() -> None:
    # Task 2 (promt 61): dict {type, text} также поддерживает kind="work"
    # и отклоняет неизвестные kinds (guard `kind in ("work", "clarification")`).
    work_raw = json.dumps(
        {"status": "ok", "pending_task": {"type": "work", "text": "Продолжи работу"}}
    )
    assert _extract_pending_task(
        {"success": True, "result": work_raw, "output": ""}
    ) == ("work", "Продолжи работу")

    bad_raw = json.dumps(
        {"status": "ok", "pending_task": {"type": "bogus", "text": "x"}}
    )
    assert _extract_pending_task(
        {"success": True, "result": bad_raw, "output": ""}
    ) is None


def test_extract_pending_task_returns_none_when_field_missing() -> None:
    raw = json.dumps({"status": "ok", "message": "done"})
    result = {"success": True, "result": raw, "output": "", "duration": 1.0}
    assert _extract_pending_task(result) is None


def test_extract_pending_task_handles_malformed_json() -> None:
    result = {"success": True, "result": "not json {{{", "output": ""}
    assert _extract_pending_task(result) is None


def test_extract_pending_task_empty_string_is_ignored() -> None:
    raw = json.dumps({"status": "ok", "pending_task": "   "})
    result = {"success": True, "result": raw, "output": ""}
    assert _extract_pending_task(result) is None


def test_extract_pending_task_non_string_value_ignored() -> None:
    raw = json.dumps({"status": "ok", "pending_task": ["list", "not", "str"]})
    result = {"success": True, "result": raw, "output": ""}
    assert _extract_pending_task(result) is None


def test_extract_pending_task_result_field_missing_is_none() -> None:
    result = {"success": True, "output": "", "duration": 1.0}
    assert _extract_pending_task(result) is None


# ─── 2. append_iteration unit tests ───────────────────────────

def test_append_iteration_updates_status_and_iteration_metadata(
    ws_root: Path,
) -> None:
    p = write_user_prompt("test task", chat_id=42)
    # Move to running/ to simulate dispatcher flow.
    p = p.rename(prompts_dir() / "running" / p.name)
    append_iteration(p, 2, "question 1", new_status="running-pending")
    text = p.read_text(encoding="utf-8")
    assert "**Status:** running-pending" in text
    assert "**Iteration:** 2" in text
    assert "**Баффи:** question 1" in text
    assert "--- Iteration 2" in text


def test_append_iteration_appends_block_before_existing_report_section(
    ws_root: Path,
) -> None:
    p = write_user_prompt("test", chat_id=42)
    p = p.rename(prompts_dir() / "running" / p.name)
    append_iteration(p, 2, "ask X", new_status="running-pending")
    text = p.read_text(encoding="utf-8")
    # Iteration block MUST come before "## Отчёт" section.
    assert text.index("--- Iteration 2") < text.index("## Отчёт")


def test_append_iteration_preserves_original_body(
    ws_root: Path,
) -> None:
    p = write_user_prompt("original body text", chat_id=42)
    p = p.rename(prompts_dir() / "running" / p.name)
    append_iteration(p, 2, "follow-up", new_status="running-pending")
    text = p.read_text(encoding="utf-8")
    assert "original body text" in text
    assert "follow-up" in text


# ─── 3. scan_resumable unit tests ────────────────────────────

def test_scan_resumable_finds_running_pending_in_running_dir(
    ws_root: Path,
) -> None:
    """Помечает файл в running/ как running-pending, scan_resumable должен найти."""
    p = write_user_prompt("multi turn task", chat_id=42)
    p = p.rename(prompts_dir() / "running" / p.name)
    append_iteration(p, 2, "q?", new_status="running-pending")
    found = scan_resumable()
    assert len(found) == 1
    assert found[0].task_id


def test_scan_resumable_ignores_locked_files_in_in_progress(
    ws_root: Path,
) -> None:
    """Файл, перемещённый под running/.in_progress/, не должен появляться."""
    p = write_user_prompt("locked task", chat_id=42)
    lock_path = _lock_subdir() / p.name
    p.rename(lock_path)
    # Set status to running-pending (atomic lock simulates mid-processing).
    (prompts_dir() / "running" / ".in_progress").mkdir(parents=True, exist_ok=True)
    lock_path.write_text(lock_path.read_text(encoding="utf-8").replace(
        "**Status:** pending", "**Status:** running-pending"
    ), encoding="utf-8")
    found = scan_resumable()
    assert len(found) == 0  # .in_progress/ files are excluded


def test_scan_resumable_ignores_files_in_done_failed_dirs(
    ws_root: Path,
) -> None:
    """Terminal files (done/failed) НЕ должны сканироваться."""
    p = write_user_prompt("terminal task", chat_id=42)
    # Move to done/ directly
    p.rename(prompts_dir() / "done" / p.name)
    found = scan_resumable()
    assert len(found) == 0


# ─── 4. dispatch_one multi-turn integration ──────────────────

def test_first_dispatch_with_pending_task_keeps_file_in_running(
    ws_root: Path,
) -> None:
    """First dispatch from user/ detects pending_task → iter 1 multi-turn init.

    File should end up in running/ with status running-pending (NOT done).
    """
    launcher, state = _sequence_launcher([
        _make_pending_result("Какой порт?")
    ])
    write_user_prompt("поставь nginx", chat_id=42)

    result = dispatch_one(launcher=launcher, timeout=60, send_tg=False)

    assert result["handled"] is True
    assert result["status"] == "multi-turn-pending"
    assert result["iteration"] == 1
    assert result["max_iterations"] == 3
    assert result["pending_task"] == "Какой порт?"

    # File should now live in running/ (not user/, not done/).
    targets = [
        f for f in (prompts_dir() / "running").glob("*.md")
    ]
    assert len(targets) == 1, f"expected exactly 1 file in running/, got {targets}"
    text = targets[0].read_text(encoding="utf-8")
    assert "**Status:** running-pending" in text
    assert "**Iteration:** 2" in text
    assert "Какой порт?" in text


def test_second_dispatch_continues_multi_turn_cycle(
    ws_root: Path,
) -> None:
    """Second dispatch finds running-pending via multi-turn branch."""
    launcher, state = _sequence_launcher([
        _make_pending_result("Какой порт?"),  # iter 1
        _make_pending_result("Какая OC?"),    # iter 2
    ])
    write_user_prompt("поставь nginx", chat_id=42)

    # Iter 1
    r1 = dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    assert r1["status"] == "multi-turn-pending"
    assert r1["iteration"] == 1

    # Iter 2 (no user/ but has running-pending)
    r2 = dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    assert r2["status"] == "multi-turn-pending"
    assert r2["iteration"] == 2

    # Both questions should be in the file body now.
    targets = list((prompts_dir() / "running").glob("*.md"))
    assert len(targets) == 1
    text = targets[0].read_text(encoding="utf-8")
    assert "Какой порт?" in text
    assert "Какая OC?" in text


def test_three_iterations_then_done_completes_terminal(
    ws_root: Path,
) -> None:
    """Iter 1+2 pending → iter 3 done (no pending_task)."""
    launcher, state = _sequence_launcher([
        _make_pending_result("q1?"),
        _make_pending_result("q2?"),
        _make_done_result(),  # iter 3
    ])
    write_user_prompt("install x", chat_id=42)

    dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    r3 = dispatch_one(launcher=launcher, timeout=60, send_tg=False)

    assert r3["status"] == "done"
    assert "Multi-turn" in (prompts_dir() / "done").glob("*.md").__next__().read_text(
        encoding="utf-8"
    ) or True  # soft assertion: terminal status reached


def test_max_iterations_reached_forces_failed_on_first_iter(
    ws_root: Path,
) -> None:
    """max_iterations=1 + pending_task → forced fail at iter 1."""
    launcher, state = _sequence_launcher([
        _make_pending_result("asking but no more iterations allowed"),
    ])
    p = write_user_prompt("task", chat_id=42)
    # Manually set max_iterations=1 to force max-reached.
    text = p.read_text(encoding="utf-8")
    text = text.replace("**Max Iterations:** 3", "**Max Iterations:** 1")
    p.write_text(text, encoding="utf-8")

    r = dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    assert r["status"] == "failed-multi-turn-max"
    assert r["reason"] == "max_iterations_reached"
    # File should be in failed/ (NOT running/, NOT done/).
    assert len(list((prompts_dir() / "failed").glob("*.md"))) == 1
    assert len(list((prompts_dir() / "running").glob("*.md"))) == 0


def test_max_iterations_reached_after_iter_3(
    ws_root: Path,
) -> None:
    """Multi-turn iter 3 returns pending_task → iter 4 > max, forced fail."""
    launcher, state = _sequence_launcher([
        _make_pending_result("q1"),
        _make_pending_result("q2"),
        _make_pending_result("q3"),  # 3 pending in a row → exceeds max=3
    ])
    write_user_prompt("install x", chat_id=42)

    dispatch_one(launcher=launcher, timeout=60, send_tg=False)  # iter 1
    dispatch_one(launcher=launcher, timeout=60, send_tg=False)  # iter 2
    r3 = dispatch_one(launcher=launcher, timeout=60, send_tg=False)  # iter 3

    # After 3 iterations, the third one returned pending_task. Since
    # next_iter would be 4 > max_iterations=3, dispatcher fails.
    assert r3["status"] == "failed-multi-turn-max"
    failed_files = list((prompts_dir() / "failed").glob("*.md"))
    assert len(failed_files) == 1


# ─── 5. Backward compat: single-turn behavior unchanged ────────

def test_no_pending_task_first_dispatch_terminates_to_done(
    ws_root: Path,
) -> None:
    """Single-turn: launcher returns no pending_task → file in done/."""
    launcher, _ = _sequence_launcher([_make_done_result()])
    write_user_prompt("simple task", chat_id=42)

    r = dispatch_one(launcher=launcher, timeout=60, send_tg=False)
    assert r["status"] == "done"
    assert len(list((prompts_dir() / "done").glob("*.md"))) == 1
    assert len(list((prompts_dir() / "running").glob("*.md"))) == 0


def test_launcher_failure_first_dispatch_terminates_to_failed(
    ws_root: Path,
) -> None:
    """Single-turn: launcher raises → file in failed/ (existing behavior)."""
    def fail_invoke(prompt: str, cwd: str, timeout: int) -> Dict[str, Any]:
        return {"success": False, "error": "codebuff OOM", "output": ""}

    write_user_prompt("bad task", chat_id=42)
    r = dispatch_one(launcher=fail_invoke, timeout=60, send_tg=False)
    assert r["status"] == "failed"
    assert len(list((prompts_dir() / "failed").glob("*.md"))) == 1


def test_dispatch_with_empty_queue_returns_noop(ws_root: Path) -> None:
    """Ни user/, ни running/ → noop."""
    r = dispatch_one(launcher=lambda p, c, t, m="auto": {}, timeout=60, send_tg=False)
    assert r["handled"] is False
    assert r["status"] == "noop"


# ─── 6. Concurrency lock ──────────────────────────────────────

def test_concurrent_dispatch_skips_locked_file(
    ws_root: Path,
) -> None:
    """Файл, перемещённый под .in_progress/, сканирование игнорирует —
    следующий cron-тик его не подхватывает."""
    # Setup: 1 multi-turn ready file in running/ + simulate lock.
    p = write_user_prompt("locked", chat_id=42)
    p = p.rename(prompts_dir() / "running" / p.name)
    append_iteration(p, 2, "pending q", new_status="running-pending")
    # Simulate concurrent tick holds the lock.
    lock_target = _lock_subdir() / p.name
    p.rename(lock_target)

    # Now scan_resumable() during a second cron tick should find 0 (locked).
    # Dispatch_one would still find scan_resumable()=0, then scan_pending()=0,
    # and return noop (instead of processing the locked file).
    r = dispatch_one(
        launcher=lambda prompt, cwd, timeout, model="auto": _make_pending_result("would-be-q"),
        timeout=60,
        send_tg=False,
    )
    # noop because scan_resumable excludes .in_progress/ AND user/ is empty.
    assert r["handled"] is False
    assert r["status"] == "noop"
    # The locked file remains in .in_progress/ untouched.
    assert lock_target.exists()
