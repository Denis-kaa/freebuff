"""Regression tests for scripts_01/prompt_queue.py (promt 48 file-queue)."""
from __future__ import annotations

import os

import pytest

from scripts_01.prompt_queue import (
    PromptMeta,
    ensure_queue_dirs,
    move_to_status,
    parse_prompt,
    queue_counts,
    queue_dir,
    recover_stale_running,
    scan_pending,
    set_report,
    write_user_prompt,
)


@pytest.fixture
def queue_root(tmp_path, monkeypatch):
    """Isolates the queue inside a tmp dir via FREEBUFF_ROOT (read at call-time)."""
    monkeypatch.setenv("FREEBUFF_ROOT", str(tmp_path))
    return tmp_path


def test_write_user_prompt_creates_pending_file(queue_root):
    path = write_user_prompt("Сделай отчёт по тестам", chat_id=12345, source="telegram")
    assert path.parent == queue_dir("pending")
    assert path.exists()
    assert path.parent.name == "user"
    text = path.read_text(encoding="utf-8")
    assert "# TASK:" in text
    assert "**Status:** pending" in text
    assert "**Chat ID:** 12345" in text


def test_write_user_prompt_title_from_first_line(queue_root):
    path = write_user_prompt("Название задачи\n\nПодробности", priority=3)
    meta = parse_prompt(path)
    assert meta is not None
    assert meta.title == "Название задачи"
    assert meta.priority == 3


def test_parse_prompt_roundtrip(queue_root):
    path = write_user_prompt(
        "Выполни рефакторинг модуля X.\nШаги: 1, 2, 3.",
        chat_id=777,
        source="cli",
        priority=2,
    )
    meta = parse_prompt(path)
    assert meta is not None
    assert meta.chat_id == 777
    assert meta.source == "cli"
    assert "рефакторинг" in meta.body
    assert meta.status == "pending"
    # Отчёт пока содержит плейсхолдер, а не результат
    assert "ожидает диспетчер" in meta.report


def test_parse_prompt_missing_file_returns_none(queue_root):
    assert parse_prompt(queue_root / "pompts_11" / "user" / "nope.md") is None


def test_write_parse_model_default_auto(queue_root):
    """Без model → 'auto' (DeepSeek V4 Flash) в шапке и в PromptMeta (v5.88.0)."""
    path = write_user_prompt("Задача", chat_id=1)
    text = path.read_text(encoding="utf-8")
    assert "**Model:** auto" in text
    meta = parse_prompt(path)
    assert meta is not None
    assert meta.model == "auto"


def test_write_parse_model_positional(queue_root):
    """model:2 записывается в шапку и читается parse_prompt (v5.88.0)."""
    path = write_user_prompt("Задача", chat_id=1, model="2")
    text = path.read_text(encoding="utf-8")
    assert "**Model:** 2" in text
    meta = parse_prompt(path)
    assert meta is not None
    assert meta.model == "2"
    assert meta.to_dict()["model"] == "2"


def test_parse_model_missing_legacy_file_defaults_auto(queue_root):
    """Старые файлы без **Model:** (созданные до v5.88.0) → model 'auto'."""
    ensure_queue_dirs()
    p = queue_dir("pending") / "task_legacy_missing_model.md"
    p.write_text(
        "# TASK: legacy\n\n"
        "**ID:** legacy_1\n"
        "**Status:** pending\n"
        "\n---\n\nзадача\n",
        encoding="utf-8",
    )
    meta = parse_prompt(p)
    assert meta is not None
    assert meta.model == "auto"


def test_scan_pending_sorts_by_priority_desc(queue_root):
    write_user_prompt("низкий приоритет", priority=0)
    write_user_prompt("высокий приоритет", priority=5)
    write_user_prompt("средний приоритет", priority=2)
    pending = scan_pending()
    assert [m.priority for m in pending] == [5, 2, 0]


def test_move_to_status_moves_file(queue_root):
    path = write_user_prompt("задача", chat_id=1)
    running = move_to_status(path, "running")
    assert running.parent == queue_dir("running")
    assert not path.exists()
    assert running.exists()


def test_set_report_writes_report_and_moves(queue_root):
    path = write_user_prompt("задача", chat_id=1)
    done = set_report(path, "done", "**Результат:** всё выполнено")
    assert done.parent == queue_dir("done")
    text = done.read_text(encoding="utf-8")
    assert "**Status:** done" in text
    assert "всё выполнено" in text
    meta = parse_prompt(done)
    assert meta is not None
    assert meta.report != ""


def test_queue_counts(queue_root):
    assert queue_counts() == {"pending": 0, "running": 0, "done": 0, "failed": 0}
    write_user_prompt("задача", chat_id=1)
    p2 = write_user_prompt("задача2", chat_id=2)
    move_to_status(p2, "done")
    counts = queue_counts()
    assert counts["pending"] == 1
    assert counts["done"] == 1


def test_recover_stale_running_returns_old_files_to_user(queue_root):
    import time

    path = write_user_prompt("задача", chat_id=1)
    running = move_to_status(path, "running")
    # «Застариваем» файл: mtime на 2 часа назад
    old = time.time() - 7200
    os.utime(running, (old, old))

    recovered = recover_stale_running(max_age_s=3600)
    assert recovered == [running.name]
    assert not running.exists()
    assert (queue_dir("pending") / running.name).exists()

    # Молодой файл (свежий mtime) не трогается
    p2 = write_user_prompt("свежая", chat_id=2)
    running2 = move_to_status(p2, "running")
    assert recover_stale_running(max_age_s=3600) == []
    assert running2.exists()


def test_prompt_meta_to_dict_roundtrip(queue_root):
    path = write_user_prompt("задача", chat_id=42)
    meta = parse_prompt(path)
    assert meta is not None
    d = meta.to_dict()
    assert d["chat_id"] == 42
    assert d["path"] == str(path)
    assert d["task_id"] == meta.task_id
