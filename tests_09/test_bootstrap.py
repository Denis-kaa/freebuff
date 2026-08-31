"""Tests for scripts_01/bootstrap.py startup self-check."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01 import bootstrap as bs


def test_load_buffy_manifest_ok(tmp_path) -> None:
    path = tmp_path / "BUFFY.md"
    path.write_text("# BUFFY\n\nYou are Buffy.", encoding="utf-8")
    warnings = bs._load_buffy_manifest(str(path))
    assert warnings == []


def test_load_buffy_manifest_missing(tmp_path) -> None:
    path = tmp_path / "BUFFY.md"
    warnings = bs._load_buffy_manifest(str(path))
    assert any("not found" in w for w in warnings)


def test_load_last_real_conspect_skips_test(tmp_path) -> None:
    summaries = tmp_path / "context_12" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / "conspect_freebuff_2026-07-28_1200.md").write_text(
        "Auto-conspect test", encoding="utf-8"
    )
    (summaries / "conspect_tg_2026-07-28_1100.md").write_text(
        "Real work summary", encoding="utf-8"
    )
    result = bs._load_last_real_conspect(str(tmp_path))
    assert result is not None
    assert result[0] == "conspect_tg_2026-07-28_1100.md"
    assert "Real work summary" in result[1]


def test_check_task_status_warns_on_stale(tmp_path) -> None:
    task_path = tmp_path / "TASK.md"
    task_path.write_text("# TASK\n\nStatus: active\n", encoding="utf-8")
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    os.utime(str(task_path), (old_time.timestamp(), old_time.timestamp()))
    warnings = bs._check_task_status(str(tmp_path), stale_days=3)
    assert any("days old" in w for w in warnings)


def test_run_startup_self_check_no_task(tmp_path) -> None:
    buffy = tmp_path / "BUFFY.md"
    buffy.write_text("# BUFFY\n\nYou are Buffy.", encoding="utf-8")
    warnings = bs.run_startup_self_check(str(tmp_path), stale_days=3)
    assert any("TASK.md not found" in w for w in warnings)
