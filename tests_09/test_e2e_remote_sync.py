"""Tests for Phase 5.3-C `scripts_01/e2e_remote_sync.py` runner.

**Strategy:** mock-based. Real TG session fragile; mock TGClient async methods.
Scope (~12 tests): stage0 pre-flight + stage1 plan + stage2 push (dr/run + dual_channel) + stage3 round-trip (mocked TGClient.get_messages via limit-scan) + write_e2e_log (happy + skip + bugs) + CLI exit-code.
"""

from __future__ import annotations

import asyncio
import json
import sys
***REMOVED***
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_FB_ROOT = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
sys.path.insert(0, str(_FB_ROOT))
sys.path.insert(0, str(_FB_ROOT / "scripts_01"))

import scripts_01.e2e_remote_sync as ers  # noqa: E402


# ── Stage 0 — Pre-flight ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stage0_preflight_log_dir_writable(tmp_path):
    """Pre-flight must report log_dir_writable=True when target dir is writable."""
    pf = await ers.stage0_preflight(skip_tg=True, log_dir=tmp_path)
    assert pf["log_dir_writable"***REMOVED*** is True
    assert pf["skip_tg_flag"***REMOVED*** is True
    assert pf.get("log_dir_writable_error") is None


@pytest.mark.asyncio
async def test_stage0_preflight_skip_tg_no_tg_call(tmp_path):
    """With skip_tg=True, no TGClient.connect() attempted."""
    pf = await ers.stage0_preflight(skip_tg=True, log_dir=tmp_path)
    assert pf["tg_session"***REMOVED*** is None
    assert pf.get("tg_session_error") is None


@pytest.mark.asyncio
async def test_stage0_preflight_core_02_import_ok(tmp_path):
    """core_02.remote_sync.RemoteSyncCoordinatorImpl must be importable."""
    pf = await ers.stage0_preflight(skip_tg=True, log_dir=tmp_path)
    assert pf["core_02_import"***REMOVED*** is True
    assert pf.get("core_02_import_error") is None



# ── Stage 1 — Planning ────────────────────────────────────────────────────


def test_stage1_plan_unique_round_ids():
    """Round IDs should be unique per call (UUID-derived)."""
    delta_a = ers.stage1_plan(ers._round_id(), sync_group_active=False)
    delta_b = ers.stage1_plan(ers._round_id(), sync_group_active=False)
    assert delta_a.updated_keys["round_id"***REMOVED*** != delta_b.updated_keys["round_id"***REMOVED***
    assert delta_a.source_device_id == "e2e_remote_sync_runner"
    assert delta_a.revision == 1
    assert delta_a.sync_mode == ers.SyncMode.SAVED_MESSAGES
    assert delta_a.updated_keys["phase"***REMOVED*** == "5.3-C"
    assert delta_a.updated_keys["verified_via"***REMOVED*** == "e2e_remote_sync.py"


def test_stage1_plan_sync_group_mode():
    """sync_group_active=True selects SyncMode.SYNC_GROUP."""
    delta = ers.stage1_plan(ers._round_id(), sync_group_active=True)
    assert delta.sync_mode == ers.SyncMode.SYNC_GROUP


# ── Stage 2 — Push (TG delivery) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_stage2_push_dry_run_returns_synthetic_msg_ids():
    """--dry-run must return DRY_RUN msg_ids WITHOUT real TG call."""
    delta = ers.stage1_plan(ers._round_id(), sync_group_active=False)
    push = await ers.stage2_push_channels(delta, sync_group_active=False, dry_run=True)
    assert push["saved_msgs"***REMOVED***["msg_id"***REMOVED*** == "DRY_RUN"
    assert push["saved_msgs"***REMOVED***["ok"***REMOVED*** is True
    assert push["litvinov"***REMOVED*** is None


@pytest.mark.asyncio
async def test_stage2_push_dry_run_sync_group_dual_channel():
    """--dry-run + --sync-group should populate both synthetic msg_ids."""
    delta = ers.stage1_plan(ers._round_id(), sync_group_active=True)
    push = await ers.stage2_push_channels(delta, sync_group_active=True, dry_run=True)
    assert push["saved_msgs"***REMOVED***["msg_id"***REMOVED*** == "DRY_RUN"
    assert push["litvinov"***REMOVED*** is not None
    assert push["litvinov"***REMOVED***["msg_id"***REMOVED*** == "DRY_RUN"
    assert push["litvinov"***REMOVED***["chat_id"***REMOVED*** == 1063827731  # ALEX_LITVINOV_CHAT_ID


@pytest.mark.asyncio
async def test_stage2_push_no_sync_group_skips_litvinov():
    """Without --sync-group, litvinov channel must be None (NOT synthetic)."""
    delta = ers.stage1_plan(ers._round_id(), sync_group_active=False)
    push = await ers.stage2_push_channels(delta, sync_group_active=False, dry_run=True)
    assert push["saved_msgs"***REMOVED*** is not None
    assert push["litvinov"***REMOVED*** is None


# ── Stage 3 — Round-trip (TGClient.get_messages mocked via limit-scan) ──


class _FakeMessage:
    def __init__(self, msg_id: int, text: str):
        self.id = msg_id
        self.text = text


class _FakeTGClient:
    """Minimal TGClient mimic — implements the methods the runner uses.

    Only `get_messages` (with limit=N) is exercised, mirroring the
    limit-scan pattern adopted in e2e_remote_sync.stage3_round_trip.
    """

    def __init__(self, msgs: list = None, connect_ok: bool = True):
        self._msgs = msgs or [***REMOVED***
        self._connect_ok = connect_ok
        self.connect_call_count = 0

    async def connect(self):
        self.connect_call_count += 1
        return self._connect_ok

    async def disconnect(self):
        pass

    async def get_me(self):
        return MagicMock(user_id=7709651193)

    async def get_messages(self, entity, limit=5, **kwargs):
        return [m for m in self._msgs if limit >= 1***REMOVED***


async def _rt_with_injected_client(push, fake):
    tgclient_module = MagicMock()
    tgclient_module.TGClient = lambda: fake
    with patch.dict(sys.modules, {
        "projects_17": MagicMock(),
        "projects_17.tg_terminal_messenger": MagicMock(),
        "projects_17.tg_terminal_messenger.src": MagicMock(),
        "projects_17.tg_terminal_messenger.src.telegram": MagicMock(),
        "projects_17.tg_terminal_messenger.src.telegram.client": tgclient_module,
    ***REMOVED***):
        return await ers.stage3_round_trip(push, dry_run=False)


@pytest.mark.asyncio
async def test_stage3_round_trip_dry_run_true():
    """--dry-run returns synthetic TRUE for both channels."""
    push = {"saved_msgs": {"chat_id": 7709651193, "msg_id": "DRY_RUN"***REMOVED***, "litvinov": None***REMOVED***
    rt = await ers.stage3_round_trip(push, dry_run=True)
    assert rt["connected"***REMOVED*** is True
    assert rt["saved_msg_text_non_empty"***REMOVED*** is True
    assert rt["saved_msg_id"***REMOVED*** == "DRY_RUN"


@pytest.mark.asyncio
async def test_stage3_round_trip_get_text_present_via_limit_scan():
    """Recent msg with non-empty text → saved_msg_text_non_empty=True."""
    push = {"saved_msgs": {"chat_id": 7709651193, "msg_id": 100500***REMOVED***, "litvinov": None***REMOVED***
    fake = _FakeTGClient(msgs=[_FakeMessage(100500, "non-empty round-trip text")***REMOVED***)
    rt = await _rt_with_injected_client(push, fake)
    assert rt["saved_msg_text_non_empty"***REMOVED*** is True
    assert rt["saved_msg_id"***REMOVED*** == 100500
    assert "non-empty round-trip text" in rt.get("saved_msg_text_head", "")


@pytest.mark.asyncio
async def test_stage3_round_trip_get_messages_empty_returns_false():
    """Recent msgs don't include our msg_id → saved_msg_text_non_empty=False."""
    push = {"saved_msgs": {"chat_id": 7709651193, "msg_id": 100600***REMOVED***, "litvinov": None***REMOVED***
    fake = _FakeTGClient(msgs=[_FakeMessage(99999, "noise")***REMOVED***)
    rt = await _rt_with_injected_client(push, fake)
    assert rt["saved_msg_text_non_empty"***REMOVED*** is False
    assert rt["connected"***REMOVED*** is True


# ── write_e2e_log — markdown build ───────────────────────────────────────


def test_write_e2e_log_happy_path(tmp_path):
    """write_e2e_log writes structured markdown with all stage sections."""
    results = {
        "started_iso": "2026-08-03T12:00:00+00:00",
        "round_id": "phase_5_3_c_deadbeef",
        "run_tag": "happy_test",
        "sync_group_active": False,
        "dry_run": False,
        "skipped": False,
        "exit_code": 0,
        "ok": True,
        "summary": "Saved=138172 verified=True; no --sync-group (single-channel only)",
        "stage0_preflight": {
            "tg_session": 7709651193, "core_02_import": True,
            "log_dir_writable": True, "skip_tg_flag": False,
        ***REMOVED***,
        "stage1_delta_summary": {
            "timestamp_ms": 1700000000000,
            "source_device_id": "e2e_remote_sync_runner", "revision": 1,
            "updated_keys": {"round_id": "phase_5_3_c_deadbeef", "phase": "5.3-C"***REMOVED***,
        ***REMOVED***,
        "stage2_push": {
            "saved_msgs": {
                "chat_id": 7709651193, "msg_id": 138172, "ok": True, "error": None,
                "chunk_count": 1, "correlation_id": "tg:7709651193:e2e_runner-1-1700000000000",
            ***REMOVED***,
            "litvinov": None,
        ***REMOVED***,
        "stage3_round_trip": {
            "connected": True, "saved_msg_id": 138172,
            "saved_msg_text_non_empty": True,
            "saved_msg_text_head": "##FB_STATE## V1.0.0 ... CHUNK 0/1\n<json>",
        ***REMOVED***,
    ***REMOVED***
    log_path = tmp_path / "test_run.md"
    res = ers.write_e2e_log(results, log_path)
    assert res["status"***REMOVED*** == "written"
    assert res["line_count"***REMOVED*** > 20
    text = log_path.read_text()
    assert "Phase 5.3-C Remote Sync" in text
    assert "Stage 0 — Pre-flight" in text
    assert "Stage 1 — Planning" in text
    assert "Stage 2 — Push" in text
    assert "Stage 3 — Round-trip" in text
    assert "Summary" in text
    assert "✅ PASS" in text
    assert "138172" in text


def test_write_e2e_log_skip_tg_truncated(tmp_path):
    """When skipped=True, log should NOT include stage 1-3 sections."""
    results = {
        "started_iso": "2026-08-03T12:00:00+00:00",
        "round_id": "phase_5_3_c_skipmode", "run_tag": "skip_test",
        "sync_group_active": False, "dry_run": False, "skipped": True,
        "exit_code": 0, "ok": True,
        "summary": "skipped via --skip-tg (pre-flight only)",
        "stage0_preflight": {
            "tg_session": None, "core_02_import": True,
            "log_dir_writable": True, "skip_tg_flag": True,
        ***REMOVED***,
    ***REMOVED***
    log_path = tmp_path / "skip_test.md"
    ers.write_e2e_log(results, log_path)
    text = log_path.read_text()
    assert "skipped via --skip-tg" in text
    assert "Stage 1 — Planning" not in text
    assert "Stage 2 — Push" not in text
    assert "Stage 3 — Round-trip" not in text


def test_write_e2e_log_with_bugs_section(tmp_path):
    """When round-trip fails, Bugs encountered section must appear."""
    results = {
        "started_iso": "2026-08-03T12:00:00+00:00",
        "round_id": "phase_5_3_c_failpath", "run_tag": "fail_test",
        "sync_group_active": False, "dry_run": False, "skipped": False,
        "exit_code": 1, "ok": False, "summary": "Saved=138173 verified=False",
        "stage0_preflight": {
            "tg_session": 7709651193, "core_02_import": True,
            "log_dir_writable": True, "skip_tg_flag": False,
        ***REMOVED***,
        "stage1_delta_summary": {
            "timestamp_ms": 1700000001000,
            "source_device_id": "e2e_remote_sync_runner", "revision": 1,
            "updated_keys": {"round_id": "phase_5_3_c_failpath"***REMOVED***,
        ***REMOVED***,
        "stage2_push": {
            "saved_msgs": {
                "chat_id": 7709651193, "msg_id": 138173, "ok": True,
                "chunk_count": 1, "correlation_id": "tg:7709651193:e2e_runner-1-1700000001000",
            ***REMOVED***,
            "litvinov": None,
        ***REMOVED***,
        "stage3_round_trip": {
            "connected": True, "saved_msg_id": 138173,
            "saved_msg_text_non_empty": False,
        ***REMOVED***,
    ***REMOVED***
    log_path = tmp_path / "fail_test.md"
    ers.write_e2e_log(results, log_path)
    text = log_path.read_text()
    assert "Bugs encountered" in text
    assert "138173" in text
    assert "not round-tripped" in text
    assert "❌ FAIL" in text


# ── N-P3 polish round 5: integration test ── 4-stage end-to-end via --dry-run + tmp_path ──

@pytest.mark.slow  # v5.189.10: e2e-orchestration (9.5s в полном сьюите)
@pytest.mark.asyncio
async def test_run_e2e_pipeline_dry_run_happy(monkeypatch, tmp_path):
    """Integration test (N-P3 polish round 5): all 4 stages orchestrated end-to-end via
    run_e2e_pipeline with dry_run=True. Catches boundary regressions at orchestrator
    composition level (state handoff across stage dict keys, schema consistency).

    Why --dry_run here (round 4 root-cause fix): Round 3 leaked real TG round-trip (138370 != 999001)
    because sys.modules patch at projects_17.tg_terminal_messenger.src.telegram.client was bypassed
    by _get_tg_client_factory() in core_02/telegram_contract.py. dry_run=True short-circuits the
    real send+round-trip paths; the orchestrator returns synthetic 'DRY_RUN' msg_ids from stage2;
    stage3 still validates TGClient connect path via mocked execution.

    Round-5 polish (response to code-reviewer N-2..N-5):
      N-2: B-4 strengthened - assert presence + bool of `connected`/`saved_msg_text_non_empty`
      N-3: B-3 'DRY_RUN' tautology replaced with structural `ok=True` + symmetric blocks check
      N-5: cross-key consistency - saved_msgs and litvinov blocks have symmetric schema

    Schema verified from scripts_01/e2e_remote_sync.py source:
      result.stage0_preflight.{core_02_import, log_dir_writable***REMOVED***
      result.stage1_delta_summary.{source_device_id, revision, updated_keys***REMOVED***
      result.stage2_push.{saved_msgs.{chat_id, msg_id, ok***REMOVED***, litvinov.{same***REMOVED******REMOVED***
      result.stage3_round_trip.{connected, saved_msg_id, lit_msg_id, saved_msg_text_non_empty, lit_msg_text_non_empty***REMOVED***
    """
    hermetic_log_dir = tmp_path / "e2e_logs_integration"
    hermetic_log_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(ers, "DEFAULT_E2E_LOG_DIR", hermetic_log_dir)

    # v5.189.10 speedup: подменяем реальный TG-клиент (inline-импорт telethon
    # в stage0/stage3 стоит ~4s) фейком — dry_run-контракт orchestrator'а не
    # зависит от реального транспорта (как в _rt_with_injected_client).
    fake_client_module = MagicMock()
    fake_client_module.TGClient = lambda *a, **k: _FakeTGClient()
    for _name in (
        "projects_17",
        "projects_17.tg_terminal_messenger",
        "projects_17.tg_terminal_messenger.src",
        "projects_17.tg_terminal_messenger.src.telegram",
        "projects_17.tg_terminal_messenger.src.telegram.client",
    ):
        monkeypatch.setitem(
            sys.modules, _name,
            fake_client_module if _name.endswith(".client") else MagicMock(),
        )

    result = await ers.run_e2e_pipeline(
        sync_group_active=True,
        dry_run=True,
        skip_tg=False,
        run_tag="n_p3_integration_v5_64_0_dry_happy",
    )

    assert isinstance(result, dict), f"Orchestrator must return dict, got {type(result).__name__***REMOVED***"

    pre = result.get("stage0_preflight")
    plan_sum = result.get("stage1_delta_summary")
    push = result.get("stage2_push")
    rt = result.get("stage3_round_trip")

    # B-1: pre-flight OK (verified names from stage0_preflight source)
    assert pre is not None, f"pre-flight missing: keys={list(result.keys())***REMOVED***"
    assert pre.get("core_02_import") is True, f"core_02 import failed: {pre***REMOVED***"
    assert pre.get("log_dir_writable") is True, f"hermetic log_dir not writable: {pre***REMOVED***"

    # B-2: plan shape (SyncDelta contract)
    assert plan_sum is not None, f"stage1_delta_summary missing: keys={list(result.keys())***REMOVED***"
    assert plan_sum.get("source_device_id") == "e2e_remote_sync_runner", f"source_device_id mismatch: {plan_sum***REMOVED***"
    assert "updated_keys" in plan_sum, f"updated_keys missing from plan: {plan_sum***REMOVED***"
    assert plan_sum.get("revision") == 1, f"revision must be 1 (initial): {plan_sum***REMOVED***"

    # B-3: push structural symmetry (N-3 polish: dropped manual DRY_RUN msg_id tautology)
    assert push is not None, f"stage2_push missing: keys={list(result.keys())***REMOVED***"
    saved_msg = push.get("saved_msgs")
    lit_msg = push.get("litvinov")
    assert saved_msg is not None, f"saved_msgs missing: {push***REMOVED***"
    assert lit_msg is not None, f"litvinov block missing (sync_group_active=True): {push***REMOVED***"
    # Structural symmetry check (N-5): both channels have same schema keys
    saved_keys = set(saved_msg.keys())
    lit_keys = set(lit_msg.keys())
    assert saved_keys == lit_keys, f"channel dict schema asymmetric: saved={saved_keys***REMOVED*** lit={lit_keys***REMOVED***"
    # Per-channel ok status (orchestrator hardcodes ok=True in dry_run)
    assert saved_msg.get("ok") is True, f"saved ok=False in dry_run: {saved_msg***REMOVED***"
    assert lit_msg.get("ok") is True, f"litvinov ok=False in dry_run: {lit_msg***REMOVED***"
    # msg_ids present in both blocks (value arbitrary in dry_run, but key must exist)
    assert "msg_id" in saved_msg and "msg_id" in lit_msg, f"msg_id key missing: saved={saved_msg***REMOVED*** lit={lit_msg***REMOVED***"

    # B-4: round-trip stage shape (N-2 polish: stronger than typeof check)
    assert rt is not None, f"stage3_round_trip missing: keys={list(result.keys())***REMOVED***"
    assert isinstance(rt, dict), f"stage3_round_trip must be dict: {rt***REMOVED***"
    # Assert presence of canonical keys (even if dry_run=True, orchestrator produces these)
    for key in ["connected", "saved_msg_id", "lit_msg_id"***REMOVED***:
        assert key in rt, f"round-trip missing canonical key '{key***REMOVED***': {rt***REMOVED***"
    # `connected` is bool (preserved even in dry_run since TGClient.connect is still attempted)
    assert isinstance(rt.get("connected"), bool), f"connected must be bool: {rt***REMOVED***"
