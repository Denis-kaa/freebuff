"""Regression tests for scripts_01/prompt_dispatcher.py (promt 48).

Uses injected fake launcher + FREEBUFF_ROOT isolation — no real Buffy run,
no real TG round-trip (send_tg=False).
"""
from __future__ import annotations

import pytest

from scripts_01.prompt_dispatcher import (
    _default_launcher,
    _format_report,
    dispatch_all,
    dispatch_one,
)
from scripts_01.prompt_queue import (
    move_to_status,
    parse_prompt,
    queue_counts,
    queue_dir,
    scan_pending,
    update_meta_value,
    write_user_prompt,
)


@pytest.fixture
def queue_root(tmp_path, monkeypatch):
    """Isolates the queue inside a tmp dir via FREEBUFF_ROOT (read at call-time).

    CON-33 (v5.89.0): `_live_instance_busy` мокается на False по умолчанию —
    иначе тесты зависят от реального окружения (если живой freebuff-инстанс
    запущен, pgrep вернёт busy и диспетчер заbackoff'нется вместо запуска
    задачи). Тесты, проверяющие backoff, переопределяют monkeypatch'ем.
    """
    import scripts_01.prompt_dispatcher as pd

    monkeypatch.setenv("FREEBUFF_ROOT", str(tmp_path))
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: False)
    return tmp_path


def _ok_launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
    return {"success": True, "output": "Готово", "duration": 1.2}


def _fail_launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
    return {"success": False, "output": "", "error": "boom", "duration": 0.5}


def _raise_launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
    raise RuntimeError("launcher crashed")


def _blocked_launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
    """Имитирует wrapper.launch_and_wait при занятом single-instance (v5.88.0)."""
    return {
        "success": False,
        "blocked_single_instance": True,
        "output": "Freebuff is already running...",
        "error": "single_instance_busy: freebuff уже запущен",
        "duration": 90.0,
    }


def test_dispatch_one_noop_when_empty(queue_root):
    result = dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert result["handled"] is False
    assert result["status"] == "noop"


def test_dispatch_one_success_moves_to_done(queue_root):
    write_user_prompt("Задача A", chat_id=111, priority=5)
    result = dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert result["handled"] is True
    assert result["status"] == "done"
    counts = queue_counts()
    assert counts["pending"] == 0
    assert counts["done"] == 1
    done_meta = parse_prompt(queue_dir("done") / result["path"].rsplit("/", 1)[-1])
    assert done_meta is not None
    assert done_meta.report != ""
    assert "Готово" in done_meta.report


def test_dispatch_one_failure_moves_to_failed(queue_root):
    write_user_prompt("Задача B", chat_id=222)
    result = dispatch_one(launcher=_fail_launcher, send_tg=False)
    assert result["handled"] is True
    assert result["status"] == "failed"
    assert "boom" in result["report"]
    counts = queue_counts()
    assert counts["failed"] == 1
    assert counts["pending"] == 0


def test_dispatch_multi_turn_defers_on_single_instance_blocker(queue_root):
    """Multi-turn ветка: single-instance blocker → файл остаётся в running/ как
    running-pending (НЕ failed), итерация не теряется, retry завершает задачу.
    """
    path = write_user_prompt("Задача multi", chat_id=555)
    # Подготавливаем running-pending файл (как после append_iteration)
    running_path = move_to_status(path, "running")
    update_meta_value(running_path, "Status", "running-pending")

    result = dispatch_one(launcher=_blocked_launcher, send_tg=False)
    assert result["handled"] is True
    assert result["status"] == "deferred_single_instance"
    counts = queue_counts()
    assert counts["running"] == 1  # вернулся в running/, не failed
    assert counts["failed"] == 0

    # Retry после освобождения инстанса → задача завершается (multi-turn путь)
    result2 = dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert result2["status"] == "done"
    assert queue_counts()["done"] == 1


def test_dispatch_one_defers_on_single_instance_blocker(queue_root):
    """Single-instance blocker (v5.88.0): задача возвращается в user/, не failed.

    freebuff допускает один инстанс; живая сессия занимает его → spawned
    экземпляр не стартует. Диспетчер должен отложить задачу (defer), а не
    фейлить — следующий cron-тик попробует снова после освобождения.
    """
    write_user_prompt("Задача D", chat_id=444)
    result = dispatch_one(launcher=_blocked_launcher, send_tg=False)
    assert result["handled"] is True
    assert result["status"] == "deferred_single_instance"
    counts = queue_counts()
    assert counts["pending"] == 1  # вернулась в user/
    assert counts["failed"] == 0   # не ложный failed

    # После освобождения инстанса задача обрабатывается нормально
    result2 = dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert result2["status"] == "done"
    assert queue_counts()["done"] == 1


def test_dispatch_one_launcher_exception_treated_as_failed(queue_root):
    write_user_prompt("Задача C", chat_id=333)
    result = dispatch_one(launcher=_raise_launcher, send_tg=False)
    assert result["status"] == "failed"
    assert "launcher crashed" in result["report"]
    assert queue_counts()["failed"] == 1


def test_dispatch_all_processes_everything(queue_root):
    write_user_prompt("Задача 1", chat_id=1)
    write_user_prompt("Задача 2", chat_id=2)
    results = dispatch_all(launcher=_ok_launcher, send_tg=False)
    assert len(results) == 2
    assert all(r["status"] == "done" for r in results)
    counts = queue_counts()
    assert counts["pending"] == 0
    assert counts["done"] == 2


def test_dispatch_all_respects_max_tasks(queue_root):
    write_user_prompt("Задача 1", chat_id=1)
    write_user_prompt("Задача 2", chat_id=2)
    write_user_prompt("Задача 3", chat_id=3)
    results = dispatch_all(launcher=_ok_launcher, send_tg=False, max_tasks=2)
    assert len(results) == 2
    assert queue_counts()["pending"] == 1


def test_format_report_ok_and_fail(queue_root):
    ok_meta = parse_prompt(write_user_prompt("X"))
    assert ok_meta is not None
    ok = _format_report(
        ok_meta,
        {"success": True, "output": "вывод", "duration": 3.0},
    )
    assert "✅ Выполнено" in ok
    assert "вывод" in ok
    bad_meta = parse_prompt(write_user_prompt("Y"))
    assert bad_meta is not None
    bad = _format_report(
        bad_meta,
        {"success": False, "output": "", "error": "ошибка"},
    )
    assert "❌ Не выполнено" in bad
    assert "ошибка" in bad


def test_pending_cleared_after_scan_moves(queue_root):
    """Файл перемещается в running, затем в done — никогда не остаётся в user/."""
    write_user_prompt("Задача", chat_id=9)
    assert len(scan_pending()) == 1
    dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert len(scan_pending()) == 0


def test_default_launcher_uses_phase_based_launch_and_wait(monkeypatch):
    """Диспетчер запускает Баффи через launch_and_wait (анти-OOM), не synchronous_oneshot."""
    import freebuff_plugin_03.wrapper as wrapper_mod

    calls: dict = {}

    def _fake(prompt, cwd, timeout, model="auto"):
        calls.update(prompt=prompt, cwd=cwd, timeout=timeout, model=model)
        return {"success": True, "result": "OK", "duration": 1.0}

    monkeypatch.setattr(wrapper_mod, "launch_and_wait", _fake)

    result = _default_launcher("prompt text", "/some/cwd", 42)
    assert result["success"] is True
    assert result["result"] == "OK"
    assert calls == {
        "prompt": "prompt text", "cwd": "/some/cwd", "timeout": 42, "model": "auto",
    }


def test_dispatch_one_forwards_model_to_launcher(queue_root):
    """Модель из шапки задачи (**Model:**) пробрасывается в launcher (v5.88.0)."""
    write_user_prompt("Задача с моделью", chat_id=1, model="2")
    seen: dict = {}

    def _capture(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
        seen.update(model=model, prompt=prompt)
        return {"success": True, "output": "OK", "duration": 0.5}

    result = dispatch_one(launcher=_capture, send_tg=False)
    assert result["handled"] is True
    assert result["status"] == "done"
    assert seen.get("model") == "2"
    assert "Задача с моделью" in seen.get("prompt", "")


def test_dispatch_one_default_model_is_auto(queue_root):
    """Без **Model:** в задаче диспетчер использует 'auto' (DeepSeek V4 Flash)."""
    write_user_prompt("Задача без модели", chat_id=1)
    seen: dict = {}

    def _capture(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
        seen.update(model=model)
        return {"success": True, "output": "OK", "duration": 0.5}

    dispatch_one(launcher=_capture, send_tg=False)
    assert seen.get("model") == "auto"


# ── CON-33 (v5.89.0): single-instance backoff ────────────────────


def _assert_launcher_never_called(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
    raise AssertionError("launcher не должен вызываться при backoff (CON-33)")


def test_dispatch_one_backoff_skips_spawn_when_instance_busy(queue_root, monkeypatch):
    """CON-33: инстанс занят живой сессией → backoff БЕЗ вызова launcher (БЕЗ spawn)."""
    import scripts_01.prompt_dispatcher as pd

    write_user_prompt("Задача backoff", chat_id=777)
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)

    result = dispatch_one(launcher=_assert_launcher_never_called, send_tg=False)
    assert result["handled"] is False
    assert result["status"] == "deferred_single_instance_backoff"
    counts = queue_counts()
    assert counts["pending"] == 1  # задача осталась в user/, не потеряна
    assert counts["failed"] == 0   # не ложный failed


def test_dispatch_one_runs_normally_when_instance_free(queue_root, monkeypatch):
    """CON-33: инстанс свободен → обычный запуск (launcher вызывается)."""
    import scripts_01.prompt_dispatcher as pd

    write_user_prompt("Задача normal", chat_id=778)
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: False)

    result = dispatch_one(launcher=_ok_launcher, send_tg=False)
    assert result["status"] == "done"
    assert queue_counts()["done"] == 1


def test_dispatch_all_breaks_on_backoff(queue_root, monkeypatch):
    """CON-33: --all при занятом инстансе останавливается после первого backoff,
    не спавнит tmux для остальных задач и не теряет очередь."""
    import scripts_01.prompt_dispatcher as pd

    write_user_prompt("Задача 1", chat_id=1)
    write_user_prompt("Задача 2", chat_id=2)
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)

    results = dispatch_all(launcher=_assert_launcher_never_called, send_tg=False)
    assert len(results) == 1
    assert results[0]["status"] == "deferred_single_instance_backoff"
    counts = queue_counts()
    assert counts["pending"] == 2  # обе задачи целы
    assert counts["failed"] == 0


def test_dispatch_all_skip_busy_precheck_after_first_launch(queue_root, monkeypatch):
    """CON-33: после успешного первого launch последующие задачи в --all НЕ
    отсекаются pre-check'ом (skip_busy_precheck=True) — не ложный backoff."""
    import scripts_01.prompt_dispatcher as pd

    # Первый вызов (pre-check False) → инстанс свободен → done.
    # Второй вызов (pre-check skip) → busy pre-check игнорируется → done.
    calls: list = []

    def _flaky_busy() -> bool:
        # Симулируем: после первого launch инстанс «занят нашим» процессом
        return len(calls) > 0

    def _launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
        calls.append(prompt)
        return {"success": True, "output": "OK", "duration": 0.5}

    monkeypatch.setattr(pd, "_live_instance_busy", _flaky_busy)
    write_user_prompt("Задача 1", chat_id=1)
    write_user_prompt("Задача 2", chat_id=2)

    results = dispatch_all(launcher=_launcher, send_tg=False)
    assert len(results) == 2
    assert all(r["status"] == "done" for r in results)
    assert len(calls) == 2  # обе задачи реально запущены


def test_deferred_at_stamp_on_blocker(queue_root):
    """CON-33: при blocked_single_instance задача получает **Deferred At:** метку
    в шапке (для аудита backoff-окна), файл возвращается в user/."""
    write_user_prompt("Задача stamp", chat_id=779)
    result = dispatch_one(launcher=_blocked_launcher, send_tg=False)
    assert result["status"] == "deferred_single_instance"
    counts = queue_counts()
    assert counts["pending"] == 1

    pending = scan_pending()[0]
    text = pending.path.read_text(encoding="utf-8")
    assert "**Deferred At:**" in text


def test_live_instance_busy_false_on_pgrep_error(monkeypatch):
    """CON-33: ошибка pgrep → False (fail-open: разрешаем spawn, wrapper поймает
    реальный блокер маркером — НЕ застреваем навсегда)."""
    import subprocess

    import scripts_01.prompt_dispatcher as pd

    def _raise(*args, **kwargs):
        raise FileNotFoundError("pgrep not found")

    monkeypatch.setattr(subprocess, "run", _raise)
    assert pd._live_instance_busy() is False


def test_live_instance_busy_true_when_pgrep_finds_binary(monkeypatch):
    """CON-33: pgrep находит бинарь → инстанс занят → backoff."""
    import subprocess

    import scripts_01.prompt_dispatcher as pd

    class _FakeResult:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeResult())
    assert pd._live_instance_busy() is True

    class _FakeMiss:
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _FakeMiss())
    assert pd._live_instance_busy() is False


def test_dispatch_all_breaks_on_wrapper_blocker(queue_root):
    """CON-33 (round-2 fix): --all останавливается и на wrapper-блокере
    (`deferred_single_instance`), не только на pre-check backoff. Иначе файл,
    возвращённый в user/, пере-подхватывался бы следующим проходом цикла →
    бесконечный цикл / N×90s впустую на известную занятость."""
    write_user_prompt("Задача 1", chat_id=1)
    write_user_prompt("Задача 2", chat_id=2)

    calls: list = []

    def _launcher(prompt: str, cwd: str, timeout: int, model: str = "auto") -> dict:
        calls.append(prompt)
        # Первая задача блокируется инстансом (wrapper-детект) → deferral
        return {
            "success": False,
            "blocked_single_instance": True,
            "output": "Freebuff is already running...",
            "duration": 90.0,
        }

    results = dispatch_all(launcher=_launcher, send_tg=False)
    assert len(results) == 1
    assert results[0]["status"] == "deferred_single_instance"
    assert len(calls) == 1  # вторая задача НЕ запускается — инстанс занят
    counts = queue_counts()
    assert counts["pending"] == 2  # обе задачи целы (1 вернулась, 2 не тронута)
    assert counts["failed"] == 0


# ── CON-35 (v5.90.0): backoff-cooldown + TG-уведомление один раз ──


def test_backoff_streak_increments_and_notifies_once(queue_root, monkeypatch):
    """CON-35: streak растёт каждый занятый тик; TG-уведомление — ОДИН раз при
    достижении порога (не каждый тик)."""
    import scripts_01.prompt_dispatcher as pd

    tg_calls: list = []
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    monkeypatch.setattr(
        pd, "_send_tg_report", lambda meta, text: tg_calls.append(text)
    )

    write_user_prompt("Задача cooldown", chat_id=1)

    # Тики 1-2 (порог 3): streak растёт, TG ещё нет
    for _ in range(2):
        r = dispatch_one(
            launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=3
        )
        assert r["status"] == "deferred_single_instance_backoff"
    assert len(tg_calls) == 0
    meta = scan_pending()[0]
    assert meta.backoff_streak == 2
    assert meta.backoff_notified is False

    # Тик 3: порог достигнут → TG ровно один раз + флаг notified
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=3
    )
    assert len(tg_calls) == 1
    meta = scan_pending()[0]
    assert meta.backoff_streak == 3
    assert meta.backoff_notified is True

    # Тики 4-5: порог уже достигнут, но повторных уведомлений НЕТ
    for _ in range(2):
        dispatch_one(
            launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=3
        )
    assert len(tg_calls) == 1  # всё ещё один
    assert scan_pending()[0].backoff_streak == 5


def test_backoff_notify_disabled_when_zero(queue_root, monkeypatch):
    """CON-35: backoff_notify=0 → streak копится, но TG никогда не шлётся."""
    import scripts_01.prompt_dispatcher as pd

    tg_calls: list = []
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    monkeypatch.setattr(
        pd, "_send_tg_report", lambda meta, text: tg_calls.append(text)
    )
    write_user_prompt("Задача без уведомлений", chat_id=2)

    for _ in range(10):
        dispatch_one(
            launcher=_assert_launcher_never_called,
            send_tg=True,
            backoff_notify=0,
        )
    assert len(tg_calls) == 0
    assert scan_pending()[0].backoff_streak == 10
    assert scan_pending()[0].backoff_notified is False


def test_backoff_streak_resets_when_instance_free(queue_root, monkeypatch):
    """CON-35: после освобождения инстанса задача запускается, streak сброшен
    в 0 — следующий busy-период начнёт считать заново."""
    import scripts_01.prompt_dispatcher as pd

    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    write_user_prompt("Задача reset", chat_id=3)
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=False, backoff_notify=5
    )
    assert scan_pending()[0].backoff_streak == 1

    # Инстанс освободился → задача выполняется, streak сброшен
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: False)
    r = dispatch_one(launcher=_ok_launcher, send_tg=False, backoff_notify=5)
    assert r["status"] == "done"
    assert queue_counts()["done"] == 1
    assert queue_counts()["pending"] == 0

    # Новая задача в новом busy-периоде: streak начинает с 0
    write_user_prompt("Задача новый период", chat_id=4)
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=False, backoff_notify=5
    )
    assert scan_pending()[0].backoff_streak == 1


def test_backoff_meta_preserved_in_file(queue_root, monkeypatch):
    """CON-35: streak и notified живут в мете файла (переживают cron-тики,
    т.к. каждый тик — отдельный процесс). Флаг notified ставится ТОЛЬКО при
    реальной отправке TG (send_tg=True), не на --no-tg тиках."""
    import scripts_01.prompt_dispatcher as pd

    tg_calls: list = []
    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    monkeypatch.setattr(
        pd, "_send_tg_report", lambda meta, text: tg_calls.append(text)
    )
    path = write_user_prompt("Задача мета", chat_id=5)
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=2
    )
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=2
    )

    text = path.read_text(encoding="utf-8")
    assert "**Backoff Streak:** 2" in text
    assert "**Backoff Notified:** true" in text
    assert len(tg_calls) == 1


def test_backoff_notified_flag_not_set_when_tg_off(queue_root, monkeypatch):
    """CON-35: --no-tg тик, пересекший порог, НЕ ставит флаг notified —
    иначе будущие TG-тики навсегда потеряли бы возможность уведомить."""
    import scripts_01.prompt_dispatcher as pd

    monkeypatch.setattr(pd, "_live_instance_busy", lambda: True)
    path = write_user_prompt("Задача no-tg", chat_id=6)
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=False, backoff_notify=2
    )
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=False, backoff_notify=2
    )

    text = path.read_text(encoding="utf-8")
    assert "**Backoff Streak:** 2" in text
    assert "**Backoff Notified:** true" not in text

    # Следующий TG-тик всё ещё может уведомить (флаг не установлен)
    tg_calls: list = []
    monkeypatch.setattr(
        pd, "_send_tg_report", lambda meta, text: tg_calls.append(text)
    )
    dispatch_one(
        launcher=_assert_launcher_never_called, send_tg=True, backoff_notify=2
    )
    assert len(tg_calls) == 1


# ── Task 2 (promt 61): discriminated pending_task + counter split ─────────────


def _clarifying_launcher_factory(text: str = "\u0443\u0442\u043e\u0447\u043d\u0438 \u0432\u0432\u043e\u0434\u043d\u044b\u0435"):
    """Returns launcher that emits clarification pending_task (new dict format)."""
    import json as _json

    def _launcher(prompt, cwd, timeout, model="auto"):
        return {
            "success": True,
            "result": _json.dumps({"pending_task": {"type": "clarification", "text": text}}),
            "output": "clarification iter",
            "duration": 0.5,
        }

    return _launcher


def _legacy_string_pending_launcher_factory(text: str = "legacy bare string"):
    """Returns launcher that emits legacy bare-string pending_task (backward-compat)."""
    import json as _json

    def _launcher(prompt, cwd, timeout, model="auto"):
        return {
            "success": True,
            "result": _json.dumps({"pending_task": text}),
            "output": "legacy string iter",
            "duration": 0.5,
        }

    return _launcher


def test_clarification_budget_doesnt_consume_work_budget(queue_root):
    """Task 2 (promt 61): длинная clarification-сессия НЕ сжигает work-iteration budget.

    Сценарий: 6 итераций kind='clarification' → clarification_count растёт
    (1→6), но `iteration` остаётся в файле шапки 1/3 (НЕ bumped). Это проверяет
    что бюджеты разведены и могут сосуществовать.
    """
    write_user_prompt("\u0417\u0430\u0434\u0430\u0447\u0430 \u0441 clarifications", chat_id=777)

    # 1\u2011й dispatch (init): user/ \u2192 running/, clarification_count 0\u21921
    r1 = dispatch_one(launcher=_clarifying_launcher_factory("Q0"), send_tg=False)
    assert r1["handled"] is True
    assert r1["status"] == "multi-turn-pending-clarification"
    assert r1["clarification_count"] == 1
    assert r1["iteration"] == 1  # work iter UNCHANGED
    assert r1["max_clarifications"] == 10
    assert r1["max_iterations"] == 3

    # \u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0435 5 \u0442\u0438\u043a\u043e\u0432: 1\u21922\u21923\u21924\u21925\u21926
    for expected_cc in range(2, 7):
        r = dispatch_one(
            launcher=_clarifying_launcher_factory(f"Q{expected_cc}"), send_tg=False
        )
        assert r["status"] == "multi-turn-pending-clarification", (
            f"cc={expected_cc}: expected multi-turn-pending-clarification, got {r['status']}"
        )
        assert r["clarification_count"] == expected_cc, f"cc={expected_cc}: bump failed"
        assert r["iteration"] == 1, f"cc={expected_cc}: work iter changed (budget leak!)"

    # \u0424\u0430\u0439\u043b \u0432 running/: iteration \u0432 \u0448\u0430\u043f\u043a\u0435 \u043e\u0441\u0442\u0430\u0451\u0442\u0441\u044f 1/3
    running_files = list(queue_dir("running").glob("*.md"))
    assert len(running_files) == 1, f"running should hold 1 file, got {len(running_files)}"
    running_meta = parse_prompt(running_files[0])
    assert running_meta is not None
    assert running_meta.iteration == 1, "work iteration header was bumped (bug!)"
    assert running_meta.max_iterations == 3
    assert running_meta.clarification_count == 6
    assert running_meta.max_clarifications == 10


def test_clarification_budget_exhausted_force_fails_without_touching_work_iter(queue_root):
    """Task 2: clarification budget exhausted \u2192 max_clarifications_reached, work iter (1/3) preserved."""
    write_user_prompt(
        "\u0417\u0430\u0434\u0430\u0447\u0430 \u0441 exhausting clarifications", chat_id=888
    )
    launcher = _clarifying_launcher_factory("Q")

    # 1\u2011\u0439 dispatch: cc 0\u21921 (multi-turn init)
    r1 = dispatch_one(launcher=launcher, send_tg=False)
    assert r1["status"] == "multi-turn-pending-clarification"

    # \u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0435 9 \u0442\u0438\u043a\u043e\u0432: cc 1\u21922\u2026\u21929\u219210 (\u0432\u0441\u0435 \u0432 budget max=10)
    for _ in range(9):
        r = dispatch_one(launcher=launcher, send_tg=False)
        assert r["status"] == "multi-turn-pending-clarification"

    # 11\u2011\u0439 dispatch: cc=10, next_cc=11 > max=10 \u2192 FORCE-FAIL
    final = dispatch_one(launcher=launcher, send_tg=False)
    assert final["handled"] is True
    assert final["status"] == "failed-multi-turn-max-clarification"
    assert final["reason"] == "max_clarifications_reached"
    assert final["clarification_count"] == 10
    assert final["iteration"] == 1, "work iter was modified despite clarification-only failure"
    assert final["max_iterations"] == 3

    counts = queue_counts()
    assert counts["failed"] == 1, "file should be in failed/"
    assert counts["running"] == 0, "file should NOT be in running/ (force-failed)"


def test_legacy_bare_string_pending_task_routes_as_work(queue_root):
    """Task 2 backward-compat: legacy bare string `.pending_task: '?'` \u2192 kind='work'.

    Никакая миграция \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0445 \u0430\u0433\u0435\u043d\u0442\u043e\u0432 \u043d\u0435 \u043d\u0443\u0436\u043d\u0430: bare string \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438
    \u0440\u0430\u0443\u0442\u0438\u0442\u0441\u044f \u043a\u0430\u043a work-pending next (\u043a\u0430\u043a \u0438 \u0434\u043e Task 2).
    """
    write_user_prompt("Legacy task", chat_id=999)
    launcher = _legacy_string_pending_launcher_factory("Bare string text")

    r1 = dispatch_one(launcher=launcher, send_tg=False)
    assert r1["handled"] is True
    assert r1["status"] == "multi-turn-pending"  # legacy \u2192 work routing
    assert r1.get("clarification_count", 0) == 0, "legacy bare string \u043d\u0435 bump\u0438\u0442 clarification_count"


# \u2500\u2500 Task 1 (promt 61): running-resumable status + process_answer handler \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


def test_clarification_sets_running_resumable_status(queue_root):
    """Task 1 (promt 61): clarification dispatch \u2192 Status = running-resumable (\u0430 \u043d\u0435 running-pending).

    File \u0432 running/ \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c \u0432 \u0441\u0442\u0430\u0442\u0443\u0441\u0435 resumable (\u043fause, awaits TG /answer).
    """
    # _clarifying_launcher_factory defined locally in this test file (Task 2)

    write_user_prompt("\u0417\u0430\u0434\u0430\u0447\u0430 \u0441 clarification", chat_id=2024)
    launcher = _clarifying_launcher_factory("Q-resumable")

    r1 = dispatch_one(launcher=launcher, send_tg=False)
    assert r1["status"] == "multi-turn-pending-clarification"

    running_files = list(queue_dir("running").glob("*.md"))
    assert len(running_files) == 1
    m = parse_prompt(running_files[0])
    assert m.status == "running-resumable", f"\u043e\u0436\u0438\u0434\u0430\u043b\u043e\u0441\u044c running-resumable, \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u0438 {m.status}"

    # scan_resumable \u0432\u043a\u043b\u044e\u0447\u0430\u0435\u0442 resumable (\u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c grep)
    from scripts_01.prompt_queue import scan_resumable
    resumable_list = scan_resumable()
    assert len(resumable_list) == 1, f"scan_resumable \u0434\u043e\u043b\u0436\u0435\u043d \u0432\u0435\u0440\u043d\u0443\u0442\u044c \u043e\u0434\u0438\u043d \u0444\u0430\u0439\u043b, got {len(resumable_list)}"


def test_process_answer_resumes_running_resumable_task(queue_root):
    """Task 1 (promt 61): process_answer(task_id, text) \u2014 \u0440\u0435\u0437\u044e\u043c running-resumable \u0437\u0430\u0434\u0430\u0447\u0438.

    \u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439: dispatch clarification \u2192 resumable pause \u2192 user answers \u2192 Status reset to pending,
    iteration bumps, cc reset, file in running/ ready for next cron tick.
    """
    from scripts_01.prompt_dispatcher import process_answer

    write_user_prompt("\u0417\u0430\u0434\u0430\u0447\u0430", chat_id=3030)
    launcher = _clarifying_launcher_factory("Q")

    r1 = dispatch_one(launcher=launcher, send_tg=False)
    assert r1["status"] == "multi-turn-pending-clarification"
    task_id = r1.get("path", "").split("/")[-1] if False else None  # extract from meta
    running_files = list(queue_dir("running").glob("*.md"))
    assert len(running_files) == 1
    meta_before = parse_prompt(running_files[0])
    assert meta_before.status == "running-resumable"
    assert meta_before.clarification_count == 1
    task_id = meta_before.task_id

    # \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043e\u0442\u0432\u0435\u0447\u0430\u0435\u0442 \u0447\u0435\u0440\u0435\u0437 process_answer
    result = process_answer(task_id, "X is the missing context")
    assert result["ok"] is True
    assert result["task_id"] == task_id
    assert result["old_status"] == "running-resumable"
    assert result["new_status"] == "running-pending"
    assert result["old_iteration"] == 1
    assert result["new_iteration"] == 2

    # \u0424\u0430\u0439\u043b \u0432 running/: status \u0441\u0431\u0440\u043e\u0448\u0435\u043d, iter +1, cc reset
    running_files_after = list(queue_dir("running").glob("*.md"))
    meta_after = parse_prompt(running_files_after[0])
    assert meta_after.status == "running-pending", f"\u043e\u0436\u0438\u0434\u0430\u043b\u043e\u0441\u044c running-pending, got {meta_after.status}"
    assert meta_after.iteration == 2
    assert meta_after.clarification_count == 0

    # \u0412 \u0444\u0430\u0439\u043b\u0435 \u0432\u0438\u0434\u0435\u043d answer block (Body \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 \u0442\u0435\u043a\u0441\u0442 \u043e\u0442\u0432\u0435\u0442\u0430)
    full_text = running_files_after[0].read_text(encoding="utf-8")
    assert "X is the missing context" in full_text, "answer text not persisted to file body"
    assert "Answer received" in full_text


def test_process_answer_rejects_non_resumable_status(queue_root):
    """Task 1: process_answer должен отказываться если Status не running-resumable.

    Сценарий: файл в running/ со статусом running-pending (work-pending next iter,
    не ждёт answer). /answer должен быть отклонён потому что answer только для
    running-resumable (clarification-awaiting).
    """
    from scripts_01.prompt_dispatcher import process_answer

    # Setup: задача в user/, dispatch → running/pending (work-pending cycle, не resumable)
    path = write_user_prompt("Test reject", chat_id=4040)
    work_launcher = _legacy_string_pending_launcher_factory("work pending text")
    r1 = dispatch_one(launcher=work_launcher, send_tg=False)
    assert r1["status"] == "multi-turn-pending", f"unexpected init status: {r1}"
    work_meta = parse_prompt(list(queue_dir("running").glob("*.md"))[0])
    assert work_meta.status == "running-pending"

    # /answer rejected: task is running-pending (work), NOT running-resumable (clarification)
    result = process_answer(work_meta.task_id, "should be rejected")
    assert result["ok"] is False
    assert "not awaiting answer" in result["error"], (
        f"ожидалось 'not awaiting answer', got {result}"
    )
    assert result["current_status"] == "running-pending"


def test_process_answer_returns_not_found_for_user_dir_task(queue_root):
    """Task 1: process_answer на pending задачу в user/ возвращает 'not found in running/'.

    (validates 404 error path — pending файлы не должны попадать под answer flow
    потому что ещё не запущены даже первой итерацией).
    """
    from scripts_01.prompt_dispatcher import process_answer

    path = write_user_prompt("Pending task", chat_id=5050)
    pending_meta = parse_prompt(path)
    assert pending_meta.status == "pending"

    result = process_answer(pending_meta.task_id, "ignored")
    assert result["ok"] is False
    assert "not found in running/" in result["error"]


def test_process_answer_returns_error_for_unknown_task(queue_root):
    """Task 1: process_answer(\u041d\u0415\u0421\u0423\u0429\u0415\u0421\u0422\u0412\u0423\u042e\u0429\u0418\u0419 task_id) \u2192 \u043e\u0448\u0438\u0431\u043a\u0430 not found."""
    from scripts_01.prompt_dispatcher import process_answer

    result = process_answer("NEVER_EXISTED", "X")
    assert result["ok"] is False
    assert "not found in running/" in result["error"]
