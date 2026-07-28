"""Auto-Conspect: автоматическое конспектирование сессий.
Запускается при завершении разговора или по крону.
Создаёт сжатый конспект для вставки в следующий контекст.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from context_manager import ContextManager, SessionStatus, CheckpointType

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def auto_conspect(session_id: str) -> str:
    """Создаёт конспект сессии и сохраняет в context/summaries/."""
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
    filepath = os.path.join(WORKSPACE, "context", "summaries", filename)
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
    # Пример использования
    cm = ContextManager(WORKSPACE)
    sessions = cm.list_sessions(status=SessionStatus.ACTIVE)

    if not sessions:
        print("No active sessions. Starting a test session...")
        snap = cm.start_session(project="freebuff", topic="Auto-conspect test")
        print(f"Created session: {snap.session_id***REMOVED***")
        cm.add_message(snap.session_id, "user", "Test message 1", token_count=20)
        cm.add_message(snap.session_id, "assistant", "Test response 1", token_count=50)
        cm.save_checkpoint(snap.session_id, "Test checkpoint", ctype=CheckpointType.AUTO_INTERVAL)
        result = auto_conspect(snap.session_id)
        print(f"Conspect saved to: {result***REMOVED***")
    else:
        for s in sessions:
            print(f"Conspecting session: {s['session_id'***REMOVED***[:8***REMOVED******REMOVED*** ({s['topic'***REMOVED******REMOVED***)")
            result = auto_conspect(s["session_id"***REMOVED***)
            print(f"  → {result***REMOVED***")
