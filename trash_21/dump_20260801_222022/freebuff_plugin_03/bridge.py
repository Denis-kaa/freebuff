"""
Freebuff Plugin Bridge — связка freebuff с stream_session и context_manager.

Процесс-безопасные функции: session_start() и session_end() можно вызывать
из разных процессов, обмениваясь session_id через файл.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone
***REMOVED***
from typing import Optional

FREEBUFF_ROOT = Path(os.environ.get(
    "FREEBUFF_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
sys.path.insert(0, str(FREEBUFF_ROOT))

from scripts_01.context_manager import ContextManager
from scripts_01.stream_session import STREAMS_DIR

# ═══════════════════════════════════════════════════════════════
# StreamBridge accessor — designated channel for plugin→core streaming
# ═══════════════════════════════════════════════════════════════

_stream_bridge = None


def get_stream_bridge():
    """Lazy accessor for StreamBridge.

    This is the ONLY way plugin code should access core streaming.
    All plugin modules (mcp_server.py, api.py, tgbot.py) MUST use
    this function instead of importing scripts.stream_bridge directly.
    """
    global _stream_bridge
    if _stream_bridge is None:
        from scripts_01.stream_bridge import StreamBridge
        _stream_bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
    return _stream_bridge


_event_bus = None


def get_event_bus():
    """Lazy accessor for EventBus.

    This is the ONLY way plugin code should access the core EventBus.
    All plugin modules that need Event/EventBus MUST use this function
    instead of importing scripts.event_bus directly.

    Returns None if EventBus is unavailable (graceful degradation).
    """
    global _event_bus
    if _event_bus is None:
        try:
            from scripts_01.event_bus import get_default_event_bus
            _event_bus = get_default_event_bus()
        except Exception:
            _event_bus = None
    return _event_bus


def create_event(event_type: str, source: str, data: dict):
    """Create an Event object using the core EventBus Event class.

    This is the ONLY way plugin code should create Event instances.
    Returns None if Event class is unavailable.
    """
    try:
        from scripts_01.event_bus import Event
        return Event(type=event_type, source=source, data=data)
    except Exception:
        return None


def _make_sid() -> str:
    """Короткий читаемый ID сессии (8 символов, буквы и цифры)."""
    return uuid.uuid4().hex[:8***REMOVED***


def _find_stream_dir(sid: str) -> Path | None:
    """Ищет стрим-директорию по .session_id начинающемуся с sid."""
    if not STREAMS_DIR.exists():
        return None
    for d in sorted(STREAMS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            sf = d / ".session_id"
            if sf.exists() and sf.read_text().strip() == sid:
                return d
    return None


def _log_json(sid: str, role: str, data: dict) -> None:
    """Пишет запись в raw.jsonl сессии."""
    session_dir = _find_stream_dir(sid)
    if not session_dir:
        return
    jsonl_file = session_dir / "raw.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "source": "freebuff_plugin",
        **data,
    ***REMOVED***
    with open(jsonl_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def session_start(topic: str = "freebuff session") -> str:
    """
    Начать новую сессию (без вывода лишнего в stdout).

    Возвращает:
        session_id (8 символов).
    """
    from scripts_01.stream_session import start_session as _start_stream

    sid = _make_sid()

    # Подавляем stdout stream_session (его "▶ Сессия начата:" и т.д.)
    with contextlib.redirect_stdout(io.StringIO()):
        _start_stream(topic=topic, session_id=sid)

    _log_json(sid, "system", {"event": "session_start", "topic": topic***REMOVED***)

    return sid


def session_end(sid: str, summary: str = "Session completed") -> str | None:
    """
    Завершить сессию: системное событие → чекпоинт → конспект.

    Args:
        sid: session_id (8 символов).
        summary: описание.

    Returns:
        путь к конспекту или None.
    """
    if not sid or len(sid) < 4:
        return None

    cm = ContextManager(str(FREEBUFF_ROOT))

    # Системное событие
    _log_json(sid, "system", {"event": "session_end", "summary": summary***REMOVED***)

    # Ищем сессию в SQLite по точному совпадению session_id
    sessions = cm.list_sessions()
    target = None
    for s in sessions:
        if s["session_id"***REMOVED*** == sid:
            target = s
            break

    if target is None:
        # Пробуем по префиксу (если сохранился старый формат)
        for s in sessions:
            if s["session_id"***REMOVED***.startswith(sid):
                target = s
                break

    if target is None:
        return None

    full_id = target["session_id"***REMOVED***

    # Завершаем сессию и создаём конспект
    from scripts_01.auto_conspect import auto_conspect

    try:
        cm.complete_session(full_id)
        filepath = auto_conspect(full_id)
        return filepath if filepath else None
    except Exception as e:
        print(f"⚠️ session_end error: {e***REMOVED***", file=sys.stderr)
        return None


def session_list(status: str | None = None) -> list[dict***REMOVED***:
    """
    Список сессий из ContextManager.

    Args:
        status: фильтр по статусу ("active", "completed") или None (все).

    Returns:
        list[dict***REMOVED***: список сессий с ключами session_id, topic, status, message_count.
    """
    cm = ContextManager(str(FREEBUFF_ROOT))
    sessions = cm.list_sessions()
    if status:
        return [s for s in sessions if s.get("status") == status***REMOVED***
    return sessions


def is_pid_alive(pid: int) -> bool:
    """Проверяет, жив ли процесс по PID."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Freebuff Plugin Bridge CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="Начать сессию (выводит session_id)")

    p_end = sub.add_parser("end", help="Завершить сессию")
    p_end.add_argument("session_id", help="ID сессии (8 символов)")
    p_end.add_argument("--summary", default="Session completed", help="Описание")

    args = parser.parse_args()

    if args.command == "start":
        sid = session_start()
        print(sid, end="")

    elif args.command == "end":
        sid = args.session_id.strip()
        cp = session_end(sid, args.summary)
        if cp:
            print(f"✔ Конспект: {cp***REMOVED***")
        else:
            print("✔ Сессия завершена")


if __name__ == "__main__":
    main()
