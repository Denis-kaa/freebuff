"""Auto-Conspect: автоматическое конспектирование сессий.
Запускается при завершении разговора или по крону.
Создаёт сжатый конспект для вставки в следующий контекст.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from context_manager import ContextManager, SessionStatus, CheckpointType
from session_utils ***REMOVED***solve_session_id

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.environ.get("FREEBUFF_ROOT", PROJECT_ROOT)


def auto_conspect(session_id: str) -> str:
    """Создаёт конспект сессии и сохраняет в context_12/summaries/."""
    cm = ContextManager(WORKSPACE)

    session = cm.get_session(session_id)
    if session is None:
        return f"Session {session_id***REMOVED*** not found"

    # Экспортируем полную сессию
    full_export = cm.export_markdown(session_id)

    # Создаём конспект для следующего контекста
    conspect = cm.export_checkpoint_summary(session_id)

    # Сохраняем конспект
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    filename = f"conspect_{session.project***REMOVED***_{ts***REMOVED***.md"
    filepath = os.path.join(WORKSPACE, "context_12", "summaries", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(conspect)

    # Сохраняем финальный чекпоинт и завершаем сессию
    cm.save_checkpoint(
        session_id=session_id,
        summary=f"Session completed. Conspect saved to {filename***REMOVED***",
        ctype=CheckpointType.POST_STEP,
    )
    cm.complete_session(session_id)

    return filepath


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-conspect Freebuff sessions")
    parser.add_argument(
        "session_id",
        nargs="?",
        help="UUID сессии или первые 8 символов. Если не указан — обрабатываются все активные сессии.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустить демо-режим (создаёт тестовую сессию). Для ручного использования; не для cron.",
    )
    args = parser.parse_args()

    if args.demo:
        # Demo moved to a separate script; keep a thin wrapper here for backwards compatibility.
        from scripts_01.demo_auto_conspect import main as demo_main

        demo_main()
        sys.exit(0)

    cm = ContextManager(WORKSPACE)

    if args.session_id:
        full_id = resolve_session_id(cm, args.session_id)
        if full_id is None:
            print(f"❌ Сессия не найдена: {args.session_id***REMOVED***")
            sys.exit(1)
        targets = [full_id***REMOVED***
    else:
        targets = [s["session_id"***REMOVED*** for s in cm.list_sessions(status=SessionStatus.ACTIVE)***REMOVED***

    if not targets:
        print("No active sessions.")
        sys.exit(0)

    for sid in targets:
        session = cm.get_session(sid)
        print(f"Conspecting session: {sid[:8***REMOVED******REMOVED*** ({session.topic if session else '?'***REMOVED***)" if session else f"Conspecting session: {sid[:8***REMOVED******REMOVED***")
        result = auto_conspect(sid)
        print(f"  → {result***REMOVED***")
