"""
Bootstrap: восстановление контекста при старте сессии с Buffy.
v2.0.0: читает BUFFY.md, загружает последний конспект, создаёт/восстанавливает
сессию, запускает StreamBridge для автоматического стриминга контекста.

Использование:
    python scripts_01/bootstrap.py                          # интерактивный режим
    python scripts_01/bootstrap.py --project termux-ai-agent  # с проектом
    python scripts_01/bootstrap.py --quiet                   # только вывод конспекта
"""

from __future__ import annotations

import os
}
import sys
from datetime import datetime, timezone

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

from scripts_01.context_manager import ContextManager, SessionStatus
from scripts_01.event_bus import get_default_event_bus
from scripts_01.memory_engine import MemoryEngine, MemoryLevel
from scripts_01.stream_bridge import StreamBridge


def _load_buffy_manifest(path: str) -> list[str]:
    """Validate the Buffy rules/identity manifest and return warnings."""
    warnings: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            warnings.append("BUFFY.md is empty")
        elif "BUFFY" not in content and "Buffy" not in content:
            warnings.append("BUFFY.md may be corrupted (no Buffy marker found)")
    except FileNotFoundError:
        warnings.append("BUFFY.md not found — conventions/identity unavailable")
    except Exception as exc:
        warnings.append(f"BUFFY.md read error: {exc}")
    return warnings


def _load_last_real_conspect(workspace: str) -> tuple[str, str] | None:
    """Return (filename, content) of the latest non-test conspect, or None."""
    summaries_dir = os.path.join(workspace, "context_12", "summaries")
    if not os.path.isdir(summaries_dir):
        return None

    files = sorted(
        [f for f in os.listdir(summaries_dir) if f.endswith(".md")],
        reverse=True,
    )
    content_markers = ["auto-conspect test", "auto conspect test", "demo", "test session"]
    filename_markers = ["test", "demo", "auto"]
    for name in files:
        filepath = os.path.join(summaries_dir, name)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        lower = content.lower()
        if any(marker in lower for marker in content_markers):
            continue
        lower_name = name.lower()
        if any(re.search(rf"\b{marker}\b", lower_name) for marker in filename_markers):
            continue
        if content.strip():
            return name, content
    return None


def _check_task_status(workspace: str, stale_days: int = 3) -> list[str]:
    """Warn if TASK.md is stale or missing/final."""
    warnings: list[str] = []
    task_path = os.path.join(workspace, "TASK.md")
    if not os.path.exists(task_path):
        warnings.append("TASK.md not found — no active task context")
        return warnings

    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(task_path), tz=timezone.utc)
        age_days = (datetime.now(timezone.utc) - mtime).days
        with open(task_path, "r", encoding="utf-8") as f:
            text = f.read().lower()
        final = any(status in text for status in ("🟢", "completed", "done", "готово"))
        if age_days > stale_days and not final:
            warnings.append(
                f"TASK.md is {age_days} days old and not marked final — consider updating or archiving"
            )
    except Exception as exc:
        warnings.append(f"TASK.md check error: {exc}")
    return warnings


def run_startup_self_check(workspace: str, stale_days: int = 3) -> list[str]:
    """Trigger 1: perform the session-start self-check.

    Returns a list of human-readable warnings. An empty list means all checks passed.
    """
    warnings: list[str] = []
    warnings.extend(_load_buffy_manifest(os.path.join(workspace, "BUFFY.md")))
    if _load_last_real_conspect(workspace) is None:
        warnings.append("No real conspect found — all saved conspects are auto/test generated")
    warnings.extend(_check_task_status(workspace, stale_days=stale_days))
    return warnings


def _seed_knowledge() -> int:
    """Keep Knowledge Memory in sync with project docs (idempotent).

    Lazily initializes the default EventBus so importing this module does
    not have side effects.
    """
    from scripts_01.seed_knowledge import seed

    bus = get_default_event_bus(WORKSPACE)
    return seed(workspace_root=WORKSPACE, event_bus=bus, rebuild=False)


def _knowledge_is_empty() -> bool:
    """Return True if the Knowledge Memory layer has no seeded entries."""
    try:
        me = MemoryEngine(workspace_root=WORKSPACE)
        return not me.list_entries(level=MemoryLevel.KNOWLEDGE)
    except Exception:
        return True


def bootstrap(
    project: str = "",
    topic: str = "",
    quiet: bool = False,
    start_stream: bool = True,
    seed: bool = False,
) -> dict:
    """
    Полный цикл восстановления контекста с авто-стримингом.

    Args:
        project: Название проекта для новой сессии.
        topic: Тема сессии.
        quiet: Подавить вывод.
        start_stream: Автоматически запустить StreamBridge.
        seed: Принудительно пересоздать Knowledge Memory из документов.

    Returns:
        dict с ключами: session_id, conspect, buffy_prompt, messages_restored,
                        stream_active, stream_topic, stream_id
    """
    # Keep Knowledge Memory in sync with project docs before starting the session.
    # This runs once when Knowledge Memory is empty, or when --seed is passed.
    if seed or _knowledge_is_empty():
        try:
            _seed_knowledge()
        except Exception as e:
            if not quiet:
                print(f"️ Knowledge seed: {e}", file=sys.stderr)

    cm = ContextManager(WORKSPACE)
    result: dict = {
        "session_id": "",
        "conspect": "",
        "buffy_prompt": "",
        "messages_restored": 0,
        "stream_active": False,
        "stream_topic": "",
        "stream_id": "",
    }

    # 1. Пробуем восстановить активную сессию
    active = cm.list_sessions(SessionStatus.ACTIVE)
    if active:
        s = active[0]
        result["session_id"] = s["session_id"]
        result["messages_restored"] = s["message_count"]
        if not quiet:
            print(f"🔄 Восстановлена сессия: {s['session_id'][:8]}")
            print(f"   Проект: {s['project']} | Тема: {s['topic']} | Сообщений: {s['message_count']}")
    else:
        # 2. Новая сессия
        snap = cm.start_session(project=project, topic=topic)
        result["session_id"] = snap.session_id
        if not quiet:
            print(f"🟢 Новая сессия: {snap.session_id[:8]}")
            print(f"   Проект: {snap.project} | Тема: {snap.topic}")

    # 3. Загружаем последний конспект (игнорируем тестовые/автоматические)
    conspect_info = _load_last_real_conspect(WORKSPACE)
    if conspect_info:
        conspect_name, conspect_content = conspect_info
        result["conspect"] = conspect_content
        if not quiet:
            print(f"\n📋 Последний конспект: {conspect_name}")
            print("-" * 50)
            print(result["conspect"][:500])
            if len(result["conspect"]) > 500:
                print("... (обрезано)")
    else:
        if not quiet:
            print("\n⚠️ Нет подходящего конспекта (все найденные — тестовые/автоматические).")

    # 4. Запуск StreamBridge (авто-стриминг)
    if start_stream:
        try:
            bridge = StreamBridge(auto_bootstrap=True, run_gc=True)
            result["stream_active"] = bridge.session_id is not None
            if bridge.session_id:
                status = bridge.get_status()
                result["stream_id"] = bridge.session_id[:8]
                if not quiet:
                    print(f"\n📡 StreamBridge активен: {result['stream_id']}")
                    if "usage_percent" in status:
                        print(f"   Контекст: {status['usage_percent']}%")
        except Exception as e:
            if not quiet:
                print(f"\n⚠️ StreamBridge: {e}", file=sys.stderr)

    # 5. Запускаем триггер самопроверки (не должен ломать старт)
    try:
        result["warnings"] = run_startup_self_check(WORKSPACE)
    except Exception as exc:
        result["warnings"] = [f"Self-check failed: {exc}"]

    # 6. Формируем стартовый промпт для Buffy
    result["buffy_prompt"] = _build_buffy_prompt(result)

    if not quiet:
        print("\n📋 СТАРТОВЫЙ ПРОМПТ ДЛЯ BUFFY:")
        print("-" * 50)
        print(result["buffy_prompt"])

    return result


def _build_buffy_prompt(result: dict) -> str:
    """Строит промпт для начала диалога с Buffy."""
    lines = [
        "Я начинаю новую сессию.",
        "",
        f"Session ID: {result['session_id']}",
        f"Messages restored: {result['messages_restored']}",
    ]

    if result.get("stream_active"):
        lines.append(f"Stream ID: {result.get('stream_id', '?')} (active)")

    warnings = result.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("## ⚠️ Self-check warnings")
        for warning in warnings:
            lines.append(f"- {warning}")

    if result["conspect"]:
        lines.append("")
        lines.append("## Контекст предыдущей сессии")
        lines.append(result["conspect"][:2000])  # ограничиваем токены

    lines.append("")
    lines.append(
        "Прочитай BUFFY.md, восстанови контекст из context.db "
        f"(session_id={result['session_id']}), и расскажи кратко "
        "что было в прошлой сессии и что мы продолжаем."
    )

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────

def main():
    project = ""
    topic = ""
    quiet = False
    seed = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--project" and i + 1 < len(args):
            project = args[i + 1]
            i += 2
        elif args[i] == "--topic" and i + 1 < len(args):
            topic = args[i + 1]
            i += 2
        elif args[i] == "--quiet":
            quiet = True
            i += 1
        elif args[i] == "--seed":
            seed = True
            i += 1
        else:
            i += 1

    result = bootstrap(project=project, topic=topic, quiet=quiet, seed=seed)

    if quiet:
        # В quiet-режиме выводим только промпт (для пайпа в другой процесс)
        print(result["buffy_prompt"])


if __name__ == "__main__":
    main()
