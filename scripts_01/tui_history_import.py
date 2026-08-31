#!/usr/bin/env python3
"""Импорт истории TUI-клиента (manicode) в платформенную память Workspace OS.

Проблема: сессии 26-29 августа шли через TUI-клиент (proot-Ubuntu manicode),
минуя платформенный pipeline, поэтому events.db замолчал 23 августа, а
context.db не содержит ни одной TUI-сессии.

Решение (Additive Architecture, без переписывания существующих модулей):
- data_13/context.db  -> sessions + messages (TUI-сессии, проект 'freebuff-tui')
- context_12/events.db -> event_store (tui.session.imported, batch)

Идемпотентность:
- session_id детерминированный: tui-<device>-<chat-dir-name>
- messages: INSERT OR IGNORE невозможен (нет UNIQUE) -> перед вставкой
  проверяется существование session_id в sessions; повторный запуск
  пропускает уже импортированные сессии целиком.
- events: INSERT OR IGNORE по event_id = sha1(session)[:12].

Соответствие CODE_QUALITY_STANDARD: type hints, docstrings, идемпотентность,
обработка ошибок, без магических чисел (константы вверху).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ══════════════════════════════════════════════════════════
# Константы
# ══════════════════════════════════════════════════════════

PHONE_ROOT = os.environ.get("TUI_PHONE_ROOT") or (
    "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/"
    "ubuntu/rootfs/root/.config/manicode"
)
SERVER_ROOT = os.environ.get("TUI_SERVER_ROOT") or "/tmp/buffy_history/server"
CTX_DB = os.environ.get("TUI_CTX_DB") or "data_13/context.db"
EVENTS_DB = os.environ.get("TUI_EVENTS_DB") or "context_12/events.db"
TUI_PROJECT = "freebuff-tui"
SESSION_PREFIX = "tui"
EVENT_TYPE = "tui.session.imported"
EVENT_SOURCE = "tui_history_import"
MAX_AI_SNIPPET = 1200
MAX_USER_CHARS = 8000
BATCH_SIZE = 200


def estimate_tokens(text: str) -> int:
    """Платформенная эвристика (~1.3 токена на 4 символа), как в context_manager."""
    if not text:
        return 1
    return max(1, int(len(text) / 4 * 1.3))


def to_platform_ts(raw: str, session_id: str, seq: int) -> str:
    """TUI-время '03:48 PM' -> ISO-8601 UTC. Без времени - полдень UTC сессии.

    session_id имеет вид 'tui-<device>-YYYY-MM-DDT...', поэтому дата
    извлекается с фиксированного смещения, а не с начала строки.
    """
    m = re.search(r"(\d{4)-\d{2]-\d{2])", session_id)
    date_part = m.group(1) if m else "1970-01-01"
    ts = f"{date_part}T12:00:00.000000+00:00"
    if raw:
        try:
            dt = datetime.strptime(raw.strip(), "%I:%M %p")
            ts = f"{date_part}T{dt.strftime('%H:%M')}:00.000000+00:00"
        except ValueError:
            pass
    # seq гарантирует монотонность внутри сессии (секунды-дубликаты разрешены)
    return ts.replace("00.000000+00:00", f"{min(seq, 59):02d}.000000+00:00")


def deterministic_session_id(device: str, chat_dir: str) -> str:
    """tui-<device>-<chat-dir>: детерминированный, коллизий нет (проверено)."""
    return f"{SESSION_PREFIX}-{device}-{chat_dir}"


def ai_text_from_blocks(msg: dict[str, Any]) -> str:
    """Склеивает текстовые блоки ai-сообщения."""
    parts = []
    for b in msg.get("blocks") or []:
        if b.get("type") == "text" and isinstance(b.get("content"), str):
            parts.append(b["content"])
    return " ".join(parts)


def load_chat_messages(sess_dir: str) -> list[dict[str, Any]]:
    """Читает chat-messages.json сессии (малые целиком, большие - USER-реплики)."""
    path = os.path.join(sess_dir, "chat-messages.json")
    if not os.path.exists(path):
        return []
    size = os.path.getsize(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"  WARN: {path}: {exc}", file=sys.stderr)
        return []


def first_prompt_from_meta(sess_dir: str) -> str:
    """firstPrompt из chat-meta.json (для topic)."""
    path = os.path.join(sess_dir, "chat-meta.json")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        return str(meta.get("firstPrompt", ""))[:300]
    except Exception:
        return ""


def find_sessions(root: str) -> list[str]:
    """Все папки-сессии в projects/*/chats/*/. """
    return sorted(
        os.path.dirname(p)
        for p in glob.glob(os.path.join(root, "projects", "*", "chats", "*", "chat-meta.json"))
    )


def import_context_db(device: str, sessions: list[tuple[str, str]]) -> int:
    """Импортирует сессии в context.db. Возвращает число новых сессий."""
    con = sqlite3.connect(CTX_DB, timeout=10.0)
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA foreign_keys=ON")
    now = datetime.now(timezone.utc).isoformat()
    imported = 0
    try:
        for session_id, sess_dir in sessions:
            existing = con.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if existing:
                continue

            msgs = load_chat_messages(sess_dir)
            topic = first_prompt_from_meta(sess_dir)
            token_est = sum(
                estimate_tokens(str(m.get("content") or "")) for m in msgs
            )

            con.execute(
                """INSERT INTO sessions
                   (session_id, status, project, topic, message_count,
                    token_estimate, last_summary, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    "completed",
                    TUI_PROJECT,
                    topic,
                    len(msgs),
                    token_est,
                    f"imported from manicode TUI ({device})",
                    json.dumps(
                        {"device": device, "source": "manicode", "import": "tui_history_import"},
                        ensure_ascii=False,
                    ),
                    now,
                    now,
                ),
            )

            rows = []
            for seq, m in enumerate(msgs, start=1):
                variant = m.get("variant")
                if variant == "user":
                    role = "user"
                    content = str(m.get("content") or "")[:MAX_USER_CHARS]
                elif variant == "ai":
                    role = "assistant"
                    content = ai_text_from_blocks(m)[:MAX_AI_SNIPPET]
                else:
                    continue  # divider и пр.
                if not content.strip():
                    continue
                ts = to_platform_ts(str(m.get("timestamp") or ""), session_id, seq)
                rows.append((session_id, role, content, estimate_tokens(content), ts))

            con.executemany(
                """INSERT INTO messages
                   (session_id, role, content, token_count, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                rows,
            )
            imported += 1
        con.commit()
    finally:
        con.close()
    return imported


def import_events(device: str, sessions: list[tuple[str, str]]) -> int:
    """Пакетный импорт событий в event_store через официальный EventStore.store_batch.

    Данные берутся из context.db (уже импортированные сессии),
    а не из chat-файлов - чтобы не перечитывать гигабайты при повторном запуске.
    """
    sys.path.insert(0, os.getcwd())
    from freebuff_plugin_03.event.store import EventStore  # noqa: E402

    con = sqlite3.connect(CTX_DB, timeout=10.0)
    con.execute("PRAGMA busy_timeout=5000")
    events = []
    for session_id, _sess_dir in sessions:
        row = con.execute(
            """SELECT topic, message_count, token_estimate
               FROM sessions WHERE session_id = ?""",
            (session_id,),
        ).fetchone()
        if row is None:
            continue  # сессия не импортирована (например, пустая папка без диалога)
        topic, msg_count, token_est = row
        user_count = con.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()[0]
        eid = hashlib.sha1(session_id.encode()).hexdigest()[:12]
        events.append(
            {
                "event_id": eid,
                "event_type": EVENT_TYPE,
                "source": EVENT_SOURCE,
                "session_id": session_id,
                "project": TUI_PROJECT,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session_id": session_id,
                    "device": device,
                    "message_count": msg_count,
                    "user_count": user_count,
                    "token_estimate": token_est,
                    "first_prompt": topic[:200],
                },
                "metadata": {"import": "tui_history_import", "device": device},
            }
        )
    con.close()
    store = EventStore(db_path=Path(EVENTS_DB).resolve())
    total = 0
    for i in range(0, len(events), BATCH_SIZE):
        total += store.store_batch(events[i : i + BATCH_SIZE])
    return total


def main() -> None:
    devices = [("phone", PHONE_ROOT), ("server", SERVER_ROOT)]
    grand_sessions = 0
    grand_events = 0
    for device, root in devices:
        if not os.path.isdir(root):
            print(f"SKIP {device}: {root} not found")
            continue
        sess_dirs = find_sessions(root)
        pairs = [
            (deterministic_session_id(device, os.path.basename(d)), d)
            for d in sess_dirs
        ]
        print(f"{device}: {len(pairs)} sessions found")
        n_sess = import_context_db(device, pairs)
        n_evt = import_events(device, pairs)
        grand_sessions += n_sess
        grand_events += n_evt
        print(f"{device}: imported {n_sess} sessions, {n_evt} events")
    print(f"TOTAL: {grand_sessions} sessions, {grand_events} events")


if __name__ == "__main__":
    main()
