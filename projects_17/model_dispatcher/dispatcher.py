#!/usr/bin/env python3
"""dispatcher.py — CLI «Диспетчер моделей» (081_19_model_dispatcher).

Цикл (один промт):
  1. scan(user/) → берём первый
  2. move → running/
  3. FreebuffDriver: tmux + freebuff → стартовый экран → выбор модели
     по убыванию (GLM → MiMo → MiniMax → DeepSeek) → «Enter a coding task»
     → отправка промта → мониторинг (вылеты/таймер)
  4. done/ (✅) с отчётом | failed/ (❌) | timeout → сессия сохранена
     (продолжение через `--resume`)

Usage:
    python -m projects_17.model_dispatcher.dispatcher --check
    python -m projects_17.model_dispatcher.dispatcher --models
    python -m projects_17.model_dispatcher.dispatcher --dry-run
    python -m projects_17.model_dispatcher.dispatcher --once
    python -m projects_17.model_dispatcher.dispatcher --all
    python -m projects_17.model_dispatcher.dispatcher --resume
    python -m projects_17.model_dispatcher.dispatcher --screen <task_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from . import md_freebuff, md_queue

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.yaml"


# ── Config ─────────────────────────────────────────────────────

def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Загружает config.yaml. При отсутствии — разумные дефолты."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    if cfg_path.exists() and yaml is not None:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg
    return {
        "session": {"timeout_minutes": 60},
        "models": {"priority": [], "unavailable_markers": []},
        "queue": {},
        "logging": {"level": "INFO"},
        "freebuff": {"binary_cmd": "", "continue_resume": True},
    }


def session_timeout_seconds(cfg: Dict[str, Any]) -> int:
    minutes = int(cfg.get("session", {}).get("timeout_minutes", 60))
    return max(1, minutes * 60)


def build_driver(cfg: Dict[str, Any], work_dir: str | Path) -> md_freebuff.FreebuffDriver:
    """Собирает FreebuffDriver из config."""
    fb = cfg.get("freebuff", {})
    sess = cfg.get("session", {})
    models = cfg.get("models", {})
    return md_freebuff.FreebuffDriver(
        work_dir=work_dir,
        binary_cmd=str(fb.get("binary_cmd", "")),
        timeout_s=session_timeout_seconds(cfg),
        model_priority=models.get("priority", []),
        unavailable_markers=models.get("unavailable_markers", []),
        max_restarts=int(sess.get("max_restarts", 2)),
        restart_delay_s=int(sess.get("restart_delay_seconds", 10)),
        startup_wait_s=int(sess.get("startup_wait_seconds", 120)),
        poll_s=int(sess.get("poll_seconds", 3)),
        continue_resume=bool(fb.get("continue_resume", True)),
    )


def work_dir_for(cfg: Dict[str, Any]) -> Path:
    """Рабочая директория сессии freebuff = корень воркспейса."""
    return md_queue.resolve_root()


def result_marker_mtime(cfg: Dict[str, Any]) -> Optional[int]:
    """mtime_ns существующего .freebuff_result (baseline против стейла)."""
    marker = work_dir_for(cfg) / ".freebuff_result"
    try:
        return marker.stat().st_mtime_ns
    except OSError:
        return None


def read_result(cfg: Dict[str, Any]) -> str:
    """Читает .freebuff_result (контент для отчёта)."""
    marker = work_dir_for(cfg) / ".freebuff_result"
    try:
        return marker.read_text(encoding="utf-8", errors="replace").strip()[:2000]
    except OSError:
        return ""


# ── AGENTS.md session overlay (мягкий reuse wrapper) ───────────

def _setup_agents_overlay(cfg: Dict[str, Any], prompt: str, sid: str) -> None:
    """Пишет session-AGENTS.md, чтобы агент знал о задаче и писал .freebuff_result.

    Мягкий reuse `freebuff_plugin_03.wrapper` (если доступен — платформа):
    `_backup_agents_md` + `_make_agents_md`. Вне платформы — no-op (промпт
    отправляется через TUI, результат можно отслеживать выводом сессии).
    """
    try:
        from freebuff_plugin_03 import wrapper

        work = Path(work_dir_for(cfg))
        wrapper._backup_agents_md(work)
        wrapper._make_agents_md(work, prompt, sid)
    except Exception:
        pass


def _restore_agents(cfg: Dict[str, Any]) -> None:
    """Восстанавливает канонический AGENTS.md после сессии (как monitor.sh).

    Безопасен в любом состоянии: если есть бэкап — восстанавливает; иначе,
    если AGENTS.md — это session-файл (маркер "Freebuff Plugin Session"),
    удаляет его. Не трогает канон (если бэкапа нет и файл не session).
    """
    work = Path(work_dir_for(cfg))
    backup = work / ".freebuff_original_agents"
    agents = work / "AGENTS.md"
    try:
        if backup.exists():
            backup.rename(agents)
            return
        if not agents.exists():
            return
        head = agents.read_text(encoding="utf-8", errors="replace")[:200]
        if "Freebuff Plugin Session" in head:
            agents.unlink()
    except OSError:
        pass


# ── Обработка одного промта ────────────────────────────────────

def _finish_with_driver(
    driver: md_freebuff.FreebuffDriver,
    cfg: Dict[str, Any],
    meta: md_queue.PromptMeta,
    running_path: Path,
    result: md_freebuff.SessionResult,
) -> Dict[str, Any]:
    """Общий финал: done|failed|timeout-saved + очистка сессии.

    Сессия останавливается (stop) на done/failed/error — освобождаем
    единственный инстанс (CON-33). На timeout — сессия СОХРАНЯЕТСЯ для
    --resume (ADR-002), AGENTS.md НЕ восстанавливается (агент может
    продолжить работу при resume).
    """
    duration = getattr(result, "duration_s", 0.0)
    model_used = result.model_used or driver.selected_model
    output = getattr(result, "output", "")[:2000]

    if result.status == "done":
        driver.stop()
        _restore_agents(cfg)
        body = read_result(cfg)
        report = (
            f"**Статус:** ✅ Выполнено\n"
            f"**Задача:** {meta.title}\n"
            f"**Task ID:** {meta.task_id}\n"
            f"**Модель:** {model_used}\n"
            f"**Длительность:** {duration}s\n"
            f"\n**Вывод (freebuff):**\n```\n{output}\n```\n"
            f"\n**Результат (.freebuff_result):**\n```\n{body}\n```\n"
        )
        final = md_queue.set_report(running_path, "done", report, cfg)
        return {"handled": True, "status": "done", "task_id": meta.task_id,
                "title": meta.title, "model_used": model_used,
                "duration_s": duration, "path": str(final)}

    if result.status == "timeout":
        # Сессия сохранена для --resume — задача остаётся в running/
        driver.save_context(meta.task_id)
        report = (
            f"**Статус:** ⏸ Отложено (таймер сессии)\n"
            f"**Задача:** {meta.title}\n"
            f"**Task ID:** {meta.task_id}\n"
            f"**Модель:** {model_used}\n"
            f"**Таймер:** {driver.timeout_s}s\n"
            f"Сессия freebuff сохранена — продолжится через `--resume`.\n"
        )
        try:
            running_path.write_text(
                running_path.read_text(encoding="utf-8") + "\n## Отчёт\n" + report + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        return {"handled": True, "status": "timeout-saved", "task_id": meta.task_id,
                "title": meta.title, "model_used": model_used,
                "duration_s": duration, "path": str(running_path)}

    # failed / crashed / error
    driver.stop()
    _restore_agents(cfg)
    report = (
        f"**Статус:** ❌ Не выполнено\n"
        f"**Задача:** {meta.title}\n"
        f"**Task ID:** {meta.task_id}\n"
        f"**Модель:** {model_used}\n"
        f"**Ошибка:** {result.error}\n"
        f"\n**Вывод (freebuff):**\n```\n{output}\n```\n"
    )
    final = md_queue.set_report(running_path, "failed", report, cfg)
    return {"handled": True, "status": result.status, "task_id": meta.task_id,
            "title": meta.title, "model_used": model_used,
            "duration_s": duration, "path": str(final)}


def process_one(
    cfg: Dict[str, Any],
    timeout_s: Optional[int] = None,
    dry_run: bool = False,
    resume: bool = False,
) -> Dict[str, Any]:
    """Берёт один промт (user/ или running/ при resume) и прогоняет через freebuff.

    Returns:
        dict: {handled, task_id, title, status, ...}
    """
    if resume:
        return _resume_one(cfg, timeout_s=timeout_s)

    pending = md_queue.scan("user", cfg)
    if not pending:
        return {"handled": False, "status": "noop"}

    meta = pending[0]
    if dry_run:
        return {
            "handled": True, "status": "dry-run", "task_id": meta.task_id,
            "title": meta.title, "model": meta.model, "path": str(meta.path),
        }

    # 1. running/
    try:
        running_path = md_queue.move_to_status(meta.path, "running", cfg)
    except OSError as e:
        return {"handled": False, "status": "move_failed", "error": str(e)}

    # 2. Запуск freebuff (с AGENTS.md overlay — агент пишет .freebuff_result)
    baseline = result_marker_mtime(cfg)
    driver = build_driver(cfg, work_dir_for(cfg))
    if timeout_s is not None:
        driver.timeout_s = timeout_s
    _setup_agents_overlay(cfg, meta.body or meta.title, driver.session_name)

    if not driver.start():
        # W-13 guard: не оставляем AGENTS.md session-overlay после падения запуска.
        _restore_agents(cfg)
        report = (
            f"**Статус:** ❌ Не выполнено\n"
            f"**Ошибка:** {driver.last_error}"
        )
        final = md_queue.set_report(running_path, "failed", report, cfg)
        return {"handled": True, "status": "failed", "task_id": meta.task_id,
                "path": str(final), "error": driver.last_error}

    try:
        # 3. Стартовый экран → выбор модели → промпт → мониторинг
        screen = driver.wait_for_screen()
        driver.select_best_model(screen)
        driver.send_prompt(meta.body or meta.title)
        result = driver.monitor(baseline_mtime=baseline)
    except Exception as e:
        result = md_freebuff.SessionResult(
            ok=False, status="error", error=str(e),
            model_used=driver.selected_model,
        )

    return _finish_with_driver(driver, cfg, meta, running_path, result)


def _resume_one(cfg: Dict[str, Any], timeout_s: Optional[int] = None) -> Dict[str, Any]:
    """Продолжает первую отложенную задачу (running/ + .md_state/<task_id>.json).

    «Часовая сессия не исчезает» (081_19_model_dispatcher): задача, отложенная по таймеру,
    возобновляется через `freebuff --continue` (сессия жива в tmux).
    """
    running = md_queue.scan("running", cfg)
    if not running:
        return {"handled": False, "status": "noop"}

    meta = running[0]
    state_dir = work_dir_for(cfg) / ".md_state"
    state_file = state_dir / f"{meta.task_id}.json"
    prev = {}
    try:
        prev = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    baseline = result_marker_mtime(cfg)
    driver = build_driver(cfg, work_dir_for(cfg))
    if timeout_s is not None:
        driver.timeout_s = timeout_s
    if prev.get("tmux_session"):
        driver.session_name = prev["tmux_session"]
    # Возобновление: --continue (resume=True), а не свежий запуск.
    driver.resume = True

    # Сессия ещё жива → просто переподключаемся и продолжаем мониторинг.
    # wait_for_screen ждёт появления экрана (стартовый или поле ввода), затем
    # отправляем продолжение напрямую (двойного ожидания не нужно).
    if driver.is_alive():
        driver.wait_for_screen(timeout_s=driver.startup_wait_s)
    else:
        _setup_agents_overlay(cfg, meta.body or meta.title, driver.session_name)
        if not driver.start():
            # W-13 guard: восстановить AGENTS.md при падении запуска.
            _restore_agents(cfg)
            return {"handled": True, "status": "failed", "task_id": meta.task_id,
                    "error": driver.last_error, "resume": True}
        driver.wait_for_screen()

    # Модель уже выбрана в прежней сессии — не перевыбираем (resume).
    if not driver.selected_model and prev.get("model"):
        driver.selected_model = prev["model"]

    try:
        driver.send_prompt("продолжай выполнение задачи из файла и сохрани результат в .freebuff_result")
        result = driver.monitor(baseline_mtime=baseline)
    except Exception as e:
        result = md_freebuff.SessionResult(
            ok=False, status="error", error=str(e), model_used=driver.selected_model,
        )

    # Успех → очищаем state-файл
    if result.status == "done":
        try:
            state_file.unlink()
        except OSError:
            pass
    return _finish_with_driver(driver, cfg, meta, meta.path, result)


# ── CLI ────────────────────────────────────────────────────────

def cmd_check(cfg: Dict[str, Any]) -> int:
    print("🔍 Проверка окружения Диспетчера моделей")
    print(f"  config: {DEFAULT_CONFIG} ({'✅' if DEFAULT_CONFIG.exists() else '❌ нет'})")
    q = md_queue.queue_counts(cfg)
    print(f"  очередь: {q}")
    driver = build_driver(cfg, work_dir_for(cfg))
    print(f"  команда запуска: {' '.join(driver.build_launch_cmd(work_dir_for(cfg)))}")
    fb = cfg.get("freebuff", {})
    print(f"  continue_resume: {fb.get('continue_resume', True)}")
    print(f"  таймер сессии: {session_timeout_seconds(cfg)}s (по умолчанию 1 час)")
    return 0


def cmd_models(cfg: Dict[str, Any]) -> int:
    print("📋 Приоритет моделей (по убыванию мощности)")
    for i, m in enumerate(cfg.get("models", {}).get("priority", [])):
        fb = " · free-fallback" if m.get("free_fallback") else ""
        print(f"  {i + 1}. {m.get('name')} — keywords={m.get('keywords')}{fb}")
    markers = cfg.get("models", {}).get("unavailable_markers", [])
    print(f"  маркеры недоступности: {markers}")
    return 0


def cmd_screen(cfg: Dict[str, Any], task_id: str) -> int:
    """Показывает дамп экрана сохранённой сессии (отладка)."""
    state_dir = work_dir_for(cfg) / ".md_state"
    state_file = state_dir / f"{task_id}.json"
    if not state_file.exists():
        print(f"❌ Нет сохранённой сессии для {task_id} (ищите в {state_dir})")
        return 1
    data = json.loads(state_file.read_text(encoding="utf-8"))
    tmux_session = data.get("tmux_session", "")
    print(f"📺 Экран сессии {task_id} (tmux={tmux_session}, model={data.get('model')})")
    driver = build_driver(cfg, work_dir_for(cfg))
    driver.session_name = tmux_session
    print(driver.capture() or "(пусто — сессия мертва)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Диспетчер моделей (081_19_model_dispatcher) — автоматизация freebuff TUI"
    )
    parser.add_argument("--config", default=None, help="Путь к config.yaml")
    parser.add_argument("--check", action="store_true", help="Проверка окружения")
    parser.add_argument("--models", action="store_true", help="Список моделей")
    parser.add_argument("--dry-run", action="store_true", help="Показать очередь без обработки")
    parser.add_argument("--once", action="store_true", help="Обработать один промт")
    parser.add_argument("--all", action="store_true", help="Обработать все ожидающие")
    parser.add_argument("--resume", action="store_true",
                        help="Продолжить отложенную сессию (running/ + --continue)")
    parser.add_argument("--screen", metavar="TASK_ID", help="Дамп экрана сохранённой сессии")
    parser.add_argument("--timeout", type=int, default=None,
                        help="Переопределить таймер сессии (минуты)")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    if args.check:
        return cmd_check(cfg)
    if args.models:
        return cmd_models(cfg)
    if args.screen:
        return cmd_screen(cfg, args.screen)

    timeout_s = args.timeout * 60 if args.timeout else None

    if args.all:
        results: List[Dict[str, Any]] = []
        while True:
            r = process_one(cfg, timeout_s=timeout_s, dry_run=args.dry_run)
            if not r.get("handled"):
                break
            results.append(r)
            if r.get("status") == "timeout-saved":
                break
    elif args.resume:
        results = [_resume_one(cfg, timeout_s=timeout_s)]
    else:
        results = [process_one(cfg, timeout_s=timeout_s, dry_run=args.dry_run)]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for r in results:
        if not r.get("handled"):
            print("ℹ️ Очередь пуста")
            continue
        st = str(r.get("status") or "")
        icon = {"done": "✅", "failed": "❌", "timeout-saved": "⏸", "dry-run": "🔍",
                "crashed": "💥", "error": "⚠️"}.get(st, "•")
        print(f"{icon} {st} · {r.get('task_id')} · {r.get('title', '')}")
        if r.get("model_used"):
            print(f"   модель: {r['model_used']} · {r.get('duration_s', 0)}s")
        if r.get("path"):
            print(f"   файл: {r['path']}")

    failed = sum(1 for r in results if r.get("status") == "failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
