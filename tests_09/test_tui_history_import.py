"""Регрессионные тесты tui_history_import.

Покрывают: детерминированный session_id, формат timestamp (регрессия бага
с префиксом tui- в поле времени), импорт сессии в context.db,
идемпотентность повторного запуска.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts_01 import tui_history_import as thi

SCHEMA = """
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',
    project TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    message_count INTEGER NOT NULL DEFAULT 0,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    last_summary TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL
);
"""


def _make_session_dir(tmp_path: Path, name: str = "2026-08-20T01-35-09.940Z") -> Path:
    """Создаёт папку сессии manicode: chat-meta.json + chat-messages.json."""
    d = tmp_path / "projects" / "root" / "chats" / name
    d.mkdir(parents=True)
    (d / "chat-meta.json").write_text(
        json.dumps({"firstPrompt": "сгенерируй картинку танка"}), encoding="utf-8"
    )
    msgs = [
        {
            "id": "user-1",
            "variant": "user",
            "content": "сгенерируй мне картинку танка",
            "timestamp": "01:35 PM",
            "blocks": [],
        },
        {
            "id": "ai-1",
            "variant": "ai",
            "content": "",
            "timestamp": "01:36 PM",
            "blocks": [{"type": "text", "content": "Вот картинка"}],
        },
        {
            "id": "div-1",
            "variant": "divider",
            "content": "",
            "timestamp": "01:37 PM",
            "blocks": [{"type": "mode-divider", "mode": "LITE"}],
        },
    ]
    (d / "chat-messages.json").write_text(json.dumps(msgs), encoding="utf-8")
    return d


def _fresh_db(tmp_path: Path) -> str:
    """Новая БД с минимальной схемой (как в data_13/context.db)."""
    db = str(tmp_path / "ctx.db")
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    con.close()
    return db


def test_deterministic_session_id() -> None:
    assert thi.deterministic_session_id("phone", "2026-08-20T01-35-09.940Z") == (
        "tui-phone-2026-08-20T01-35-09.940Z"
    )


def test_to_platform_ts_has_no_tui_prefix() -> None:
    """Регрессия: timestamp не должен содержать 'tui-...' префикс."""
    sid = "tui-phone-2026-08-20T01-35-09.940Z"
    ts = thi.to_platform_ts("01:36 PM", sid, 2)
    assert "tui-" not in ts
    assert ts.startswith("2026-08-20T13:36:02")


def test_estimate_tokens() -> None:
    assert thi.estimate_tokens("") == 1
    assert thi.estimate_tokens("привет") >= 1


def test_import_creates_session_and_messages(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(thi, "CTX_DB", _fresh_db(tmp_path))
    sess_dir = _make_session_dir(tmp_path)
    sess_id = thi.deterministic_session_id("phone", sess_dir.name)
    assert thi.import_context_db("phone", [(sess_id, str(sess_dir))]) == 1

    con = sqlite3.connect(thi.CTX_DB)
    row = con.execute(
        "SELECT message_count, topic FROM sessions WHERE session_id = ?", (sess_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == 3  # message_count = все исходные сообщения (включая divider)
    assert "картинку" in row[1]

    msgs = con.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
        (sess_id,),
    ).fetchall()
    assert len(msgs) == 2
    assert msgs[0][0] == "user"
    assert msgs[1][0] == "assistant"
    assert "Вот картинка" in msgs[1][1]
    con.close()


def test_import_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(thi, "CTX_DB", _fresh_db(tmp_path))
    sess_dir = _make_session_dir(tmp_path)
    sess_id = thi.deterministic_session_id("phone", sess_dir.name)
    pair = [(sess_id, str(sess_dir))]
    assert thi.import_context_db("phone", pair) == 1
    assert thi.import_context_db("phone", pair) == 0

    con = sqlite3.connect(thi.CTX_DB)
    n = con.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?", (sess_id,)
    ).fetchone()[0]
    assert n == 2
    con.close()