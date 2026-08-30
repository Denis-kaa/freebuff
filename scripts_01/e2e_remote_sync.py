"""Phase 5.3-C: real TG round-trip e2e runner for Remote Sync runtime.

**Status:** End-to-end test runner for Phase 5.3-B `RemoteSyncCoordinatorImpl`.

Tests that `core_02.remote_sync.RemoteSyncCoordinatorImpl.push_state()` actually
delivers a delta envelope to Telegram Saved Messages (mandatory) and to Литвинов
(optional, when `--sync-group` is active), and that round-trip read-back via
`TGClient.get_messages(chat_id, ids=[msg_id])` returns non-empty, non-synthetic
messages (CAN-9 v5.59.0 discipline).

**Mirrors `e2e_promt47.py` discipline:**
  - 4-stage pipeline (pre-flight → planning → push → round-trip)
  - per-run log file `docs_10/e2e_logs/remote_sync_<TS>.md` (mirrors user directive `<timestamp>`)
  - structured markdown headers (Run banner + Stage 0/1/2/3 + Bugs + Summary)
  - exit 0/1 depending on round-trip completeness

**Architecture:** Single-process asyncio runner. NO long-lived TG connection;
each TG op bootstraps `connect → op → disconnect` (matches
`core_02/telegram_contract._send_text` pattern).

**CAN-9 / CAN-16 discipline:**
  - Round-trip is verified through `TGClient.get_messages(chat_id, ids=[msg_id])`
    (real Telethon read, NOT synthetic)
  - `text non-empty` check is the only verification metric (loose check —
    mirrors `tg_send_v5570.py::round_trip_verify`)

**CLI flags:**
  --silent           print-suppress banners (logic always runs)
  --skip-tg          zero TG side-effects (pre-flight only, freshness path)
  --sync-group       dual-channel: also push to Литвинов (default: Saved only)
  --dry-run          build content + log only; no actual TG send
  --e2e-log PATH     override log path (default: per-run timestamped file)
  --run-tag TEXT     custom run identifier (default: UTC timestamp)
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import logging
import sys
import time
import uuid
}
from typing import Any, Dict, List, Optional

# ── Freebuff root resolution (mirrors tg_send_v5570.py pattern) ───────────

FB_ROOT = Path(__file__).resolve().parent.parent
if str(FB_ROOT) not in sys.path:
    sys.path.insert(0, str(FB_ROOT))

import core_02.telegram_contract as tc  # noqa: E402
from core_02.remote_sync import (  # noqa: E402
    RemoteSyncCoordinatorImpl,
    SyncDelta,
    SyncMode,
)


# ── Logging (canonical pattern per CON-16) ────────────────────────────────

logger = logging.getLogger("e2e_remote_sync")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter("[e2e_remote_sync) %(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


# ── Public symbol exports ─────────────────────────────────────────────────

__all__ = [
    "main",
    "run_e2e_pipeline",
    "write_e2e_log",
    "stage0_preflight",
    "stage1_plan",
    "stage2_push_channels",
    "stage3_round_trip",
    "DEFAULT_E2E_LOG_DIR",
]


# ── Default paths ─────────────────────────────────────────────────────────

DEFAULT_E2E_LOG_DIR = FB_ROOT / "docs_10" / "e2e_logs"


# ── Helpers ───────────────────────────────────────────────────────────────


def _now_ms() -> int:
    return int(time.time() * 1000)


def _timestamp_for_filename() -> str:
    """YYYYMMDDTHHMMSS style for filename embedding (UTC)."""
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")


def _round_id() -> str:
    """Unique round-trip ID for embedding in delta.updated_keys."""
    return f"phase_5_3_c_{uuid.uuid4().hex[:8]}"


def _truncate(s: Optional[str], n: int = 80) -> str:
    if s is None:
        return "—"
    return s if len(s) <= n else s[: n - 1] + "…"


def _table_escape(s: Optional[str], n: int = 60) -> str:
    """Sanitize `|` chars that would break markdown table cell boundaries.

    Code-reviewer N-B2: TG error strings can contain `|` (e.g., telethon
    tracebacks), which breaks table structure silently. Escape `|` → `\|`
    AND escape backslash `\\` → `\\\\` (markdown escape order matters).
    Truncate to `n` chars after escaping.
    """
    if s is None:
        return "—"
    escaped = s.replace("\\", "\\\\").replace("|", "\\|")
    return escaped if len(escaped) <= n else escaped[: n - 1] + "…"


# ── Stage 0 — Pre-flight CHECK-only ──────────────────────────────────────


async def stage0_preflight(
    *, skip_tg: bool = False, log_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Validate TG session alive, runtime importable, log dir writable.
    Zero TG side-effects from this stage.
    """
    if log_dir is None:
        log_dir = DEFAULT_E2E_LOG_DIR

    preflight: Dict[str, Any] = {
        "tg_session": None,
        "core_02_import": False,
        "log_dir_writable": False,
        "skip_tg_flag": skip_tg,
    }

    # core_02 import check (already loaded at module init; verify class)
    try:
        from core_02.remote_sync import RemoteSyncCoordinatorImpl as _cls  # type: ignore
        preflight["core_02_import"] = bool(_cls is RemoteSyncCoordinatorImpl)
    except Exception as e:
        preflight["core_02_import_error"] = str(e)

    # log-dir writable check
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _tmp = log_dir / f".touch_{uuid.uuid4().hex[:6]}"
        _tmp.touch()
        _tmp.unlink()
        preflight["log_dir_writable"] = True
    except Exception as e:
        preflight["log_dir_writable_error"] = str(e)

    if skip_tg:
        return preflight

    # TG session alive (read-only — get_me accesses cached session state; no side-effect)
    try:
        from projects_17.tg_terminal_messenger.src.telegram.client import (  # type: ignore
            TGClient,
        )

        client = TGClient()
        connected = await client.connect()
        if not connected:
            preflight["tg_session"] = False
        else:
            try:
                _me = await client.get_me()
                tg_user_id = (
                    getattr(_me, "user_id", None)
                    or getattr(_me, "id", None)
                )
                preflight["tg_session"] = tg_user_id or True
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
    except Exception as e:
        preflight["tg_session_error"] = str(e)

    return preflight


# ── Stage 1 — Planning (SyncDelta construction) ───────────────────────────


def stage1_plan(round_id: str, sync_group_active: bool) -> SyncDelta:
    """Construct a SyncDelta with embedded `round_id` marker for verification.

    The marker travels through the wire format (envelope JSON) so a future
    `pull_state` round-trip can verify identity without trusted time-of-record.
    """
    return SyncDelta(
        timestamp_ms=_now_ms(),
        source_device_id="e2e_remote_sync_runner",
        revision=1,
        sync_mode=SyncMode.SAVED_MESSAGES if not sync_group_active else SyncMode.SYNC_GROUP,
        updated_keys={
            "round_id": round_id,
            "verified_via": "e2e_remote_sync.py",
            "phase": "5.3-C",
            "intent": "real TG round-trip via TGClient.get_messages",
        },
        deleted_keys=[],
    )


# ── Stage 2 — Push (TG delivery via RuntimeCoordinatorImpl) ───────────────


async def stage2_push_channels(
    delta: SyncDelta,
    *,
    sync_group_active: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    """Send delta to Saved Messages (mandatory) + Литвинов (optional)."""
    push: Dict[str, Any] = {
        "saved_msgs": {
            "chat_id": tc.SAVED_MESSAGES_CHAT_ID,
            "msg_id": None,
            "ok": False,
            "error": None,
        },
        "litvinov": None,
    }

    if dry_run:
        push["saved_msgs"]["ok"] = True
        push["saved_msgs"]["msg_id"] = "DRY_RUN"
        if sync_group_active:
            push["litvinov"] = {
                "chat_id": tc.ALEX_LITVINOV_CHAT_ID,
                "msg_id": "DRY_RUN",
                "ok": True,
                "error": None,
            }
        return push

    # Saved Messages (mandatory)
    try:
        coord_saved = RemoteSyncCoordinatorImpl("e2e_runner", SyncMode.SAVED_MESSAGES)
        await coord_saved.register_device("e2e_runner")
        saved_res = await coord_saved.push_state(delta)
        push["saved_msgs"]["msg_id"] = (saved_res.get("msg_ids") or [None])[0]
        push["saved_msgs"]["ok"] = bool(saved_res.get("ok"))
        push["saved_msgs"]["correlation_id"] = saved_res.get("correlation_id")
        push["saved_msgs"]["chunk_count"] = saved_res.get("chunk_count")
        if not saved_res.get("ok"):
            push["saved_msgs"]["error"] = saved_res.get("error")
        await coord_saved.shutdown()
    except Exception as e:  # defensive
        push["saved_msgs"]["error"] = f"Saved push coordinator exception: {e}"

    # Литвинов (optional)
    if sync_group_active:
        try:
            coord_lit = RemoteSyncCoordinatorImpl("e2e_runner", SyncMode.SYNC_GROUP)
            await coord_lit.register_device("e2e_runner")
            lit_res = await coord_lit.push_state(delta)
            push["litvinov"] = {
                "chat_id": tc.ALEX_LITVINOV_CHAT_ID,
                "msg_id": (lit_res.get("msg_ids") or [None])[0],
                "ok": bool(lit_res.get("ok")),
                "error": lit_res.get("error"),
                "correlation_id": lit_res.get("correlation_id"),
                "chunk_count": lit_res.get("chunk_count"),
            }
            await coord_lit.shutdown()
        except Exception as e:  # defensive
            push["litvinov"] = {
                "chat_id": tc.ALEX_LITVINOV_CHAT_ID,
                "msg_id": None,
                "ok": False,
                "error": f"Литвинов push coordinator exception: {e}",
            }

    return push


# ── Stage 3 — Round-trip (TGClient.get_messages read-back) ────────────────


async def stage3_round_trip(
    push_results: Dict[str, Any], *, dry_run: bool = False
) -> Dict[str, Any]:
    """Verify each push via TGClient.get_messages(chat_id, ids=[msg_id]).

    Mirrors `scripts_01/tg_send_v5570.py::round_trip_verify` discipline.

    Returns round-trip dict; keys: `connected`, `saved_msg_text_non_empty`,
    `lit_msg_text_non_empty`, `saved_msg_text_head`, `lit_msg_text_head`,
    `saved_msg_id`, `lit_msg_id`, `error`.
    """
    if dry_run:
        return {
            "connected": True,
            "saved_msg_text_non_empty": True,
            "lit_msg_text_non_empty": True,
            "saved_msg_id": "DRY_RUN",
            "lit_msg_id": "DRY_RUN",
            "saved_msg_text_head": "(DRY_RUN synthetic)",
            "lit_msg_text_head": "(DRY_RUN synthetic)",
        }

    try:
        from projects_17.tg_terminal_messenger.src.telegram.client import (  # type: ignore
            TGClient,
        )

        client = TGClient()
        connected = await client.connect()
        if not connected:
            return {
                "connected": False,
                "saved_msg_text_non_empty": False,
                "lit_msg_text_non_empty": False,
            }
    except Exception as e:
        return {
            "connected": False,
            "error": f"TGClient bootstrap failed: {e}",
            "saved_msg_text_non_empty": False,
            "lit_msg_text_non_empty": False,
        }

    out: Dict[str, Any] = {"connected": True}
    try:
        # Saved Messages round-trip via limit-scan + client-side filter
        # (TGClient.get_messages signature is `(entity, limit=5)` — does NOT
        #  expose `ids=` kwarg; mirror Phase 5.3-B `_history_via_tgclient`.)
        saved_msg_id = push_results["saved_msgs"]["msg_id"]
        if saved_msg_id is not None and saved_msg_id != "DRY_RUN":
            try:
                recent = await client.get_messages(
                    tc.SAVED_MESSAGES_CHAT_ID, limit=100
                )
                match = next(
                    (
                        m
                        for m in recent
                        if getattr(m, "id", None) == saved_msg_id
                    ),
                    None,
                )
                ok = bool(
                    match and getattr(match, "text", None)
                )
                out["saved_msg_id"] = saved_msg_id
                out["saved_msg_text_non_empty"] = ok
                if ok:
                    out["saved_msg_text_head"] = match.text[:100]
                # `limit-scan perf note`: 1 TG roundtrip; ~100 msgs scan cost
                # is acceptable for cold-path verify-gate (NOT hot-path).
            except Exception as e:
                logger.warning(
                    "stage3 Saved round-trip exception: %s", e,
                )
                out["saved_msg_id"] = saved_msg_id
                out["saved_msg_text_non_empty"] = None

        # Литвинов round-trip (same limit-scan pattern)
        if (
            push_results.get("litvinov") is not None
            and push_results["litvinov"].get("msg_id") is not None
            and push_results["litvinov"]["msg_id"] != "DRY_RUN"
        ):
            lit_msg_id = push_results["litvinov"]["msg_id"]
            try:
                recent = await client.get_messages(
                    tc.ALEX_LITVINOV_CHAT_ID, limit=100
                )
                match = next(
                    (
                        m
                        for m in recent
                        if getattr(m, "id", None) == lit_msg_id
                    ),
                    None,
                )
                ok = bool(
                    match and getattr(match, "text", None)
                )
                out["lit_msg_id"] = lit_msg_id
                out["lit_msg_text_non_empty"] = ok
                if ok:
                    out["lit_msg_text_head"] = match.text[:100]
            except Exception as e:
                logger.warning(
                    "stage3 Литвинов round-trip exception: %s", e,
                )
                out["lit_msg_id"] = lit_msg_id
                out["lit_msg_text_non_empty"] = None
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    return out


# ── Pipeline driver ──────────────────────────────────────────────────────


async def run_e2e_pipeline(
    *,
    sync_group_active: bool = False,
    skip_tg: bool = False,
    dry_run: bool = False,
    run_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full 4-stage pipeline. Returns aggregated dict."""
    round_id = _round_id()
    started_ms = _now_ms()
    started_iso = _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")

    preflight = await stage0_preflight(skip_tg=skip_tg)

    # Skip-tg path: pre-flight only
    if skip_tg:
        return {
            "started_iso": started_iso,
            "started_ms": started_ms,
            "round_id": round_id,
            "run_tag": run_tag,
            "sync_group_active": sync_group_active,
            "stage0_preflight": preflight,
            "stage1_delta_summary": None,
            "stage2_push": None,
            "stage3_round_trip": None,
            "stage4_log": None,
            "summary": "skipped via --skip-tg (pre-flight only)",
            "exit_code": 0,
            "ok": True,
            "skipped": True,
            "dry_run": False,
        }

    # Pre-flight hard-fail (no TG client available, etc.)
    if not (preflight.get("core_02_import") and preflight.get("log_dir_writable")):
        return {
            "started_iso": started_iso,
            "stage0_preflight": preflight,
            "summary": "preflight failed; aborting",
            "exit_code": 1,
            "ok": False,
            "skipped": False,
            "error": "preflight failed",
        }

    # Stage 1 → 2 → 3
    delta = stage1_plan(round_id, sync_group_active=sync_group_active)
    push = await stage2_push_channels(delta, sync_group_active=sync_group_active, dry_run=dry_run)
    rt = await stage3_round_trip(push, dry_run=dry_run)

    # Verdict
    if dry_run:
        ok = True
        summary = "dry-run OK (no TG side-effects)"
        exit_code = 0
    else:
        saved_ok = bool(rt.get("saved_msg_text_non_empty"))
        lit_excluded = push.get("litvinov") is None or not sync_group_active
        lit_ok = bool(rt.get("lit_msg_text_non_empty")) if not lit_excluded else True
        ok = saved_ok and lit_ok
        summary = (
            f"Saved={push['saved_msgs'].get('msg_id')} verified={saved_ok}; "
            + (
                f"Литвинов={push['litvinov'].get('msg_id')} verified={lit_ok}"
                if not lit_excluded
                else "no --sync-group (single-channel only)"
            )
        )
        exit_code = 0 if ok else 1

    return {
        "started_iso": started_iso,
        "started_ms": started_ms,
        "round_id": round_id,
        "run_tag": run_tag,
        "sync_group_active": sync_group_active,
        "stage0_preflight": preflight,
        "stage1_delta_summary": {
            "timestamp_ms": delta.timestamp_ms,
            "source_device_id": delta.source_device_id,
            "revision": delta.revision,
            "updated_keys": delta.updated_keys,
        },
        "stage2_push": push,
        "stage3_round_trip": rt,
        "stage4_log": None,  # populated by write_e2e_log after this
        "summary": summary,
        "exit_code": exit_code,
        "ok": ok,
        "skipped": False,
        "dry_run": dry_run,
    }


# ── Markdown log writer (CAN-16 anti-rewriting: per-run file isolation) ──


def write_e2e_log(results: Dict[str, Any], log_path: Path) -> Dict[str, Any]:
    """Write a single-run markdown file to `log_path`.

    Each run = single file. No splice-append across runs (CAN-16 applied via
    per-file isolation; cross-run comparison is via filename chronology).
    Mirrors `e2e_promt47.py::write_e2e_log` schema style with additions for
    round-trip-specific fields (msg_id, chat_id, text non-empty).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append(f"# Phase 5.3-C Remote Sync — End-to-End Run @ {results['started_iso']}")
    lines.append("")
    lines.append(f"- **Run tag**: {results.get('run_tag') or '(default — UTC timestamp)'}")
    lines.append(f"- **Round ID**: `{results.get('round_id')}`")
    lines.append(f"- **Sync Group active**: {results.get('sync_group_active', False)}")
    lines.append(f"- **Dry run**: {results.get('dry_run', False)}")
    lines.append(f"- **Skipped**: {results.get('skipped', False)}")
    status = (
        "✅ PASS"
        if (results.get("ok") or results.get("skipped"))
        else "❌ FAIL"
    )
    lines.append(f"- **Status**: {status}")
    lines.append("")

    # Stage 0 — pre-flight
    pf = results.get("stage0_preflight") or {}
    tg_session = pf.get("tg_session")
    tg_session_ok = tg_session is None and pf.get("skip_tg_flag")
    tg_session_ok = tg_session_ok or bool(tg_session)
    lines.append("## Stage 0 — Pre-flight (CHECK-only, no TG side-effects)")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|-------|--------|--------|")
    lines.append(
        f"| TG session alive | "
        f"{'✅' if tg_session_ok else ('⚠️ skipped' if pf.get('skip_tg_flag') else '❌')} "
        f"| `{tg_session or 'skipped'}`"
        + (f" — error: `{pf.get('tg_session_error')}`" if pf.get("tg_session_error") else "")
        + " |"
    )
    lines.append(
        f"| core_02.remote_sync importable | "
        f"{'✅' if pf.get('core_02_import') else '❌'} "
        f"| `RemoteSyncCoordinatorImpl`"
        + (f" — error: `{pf.get('core_02_import_error')}`" if pf.get("core_02_import_error") else "")
        + " |"
    )
    lines.append(
        f"| log-dir writable | "
        f"{'✅' if pf.get('log_dir_writable') else '❌'} "
        f"| `{DEFAULT_E2E_LOG_DIR}`"
        + (f" — error: `{pf.get('log_dir_writable_error')}`" if pf.get("log_dir_writable_error") else "")
        + " |"
    )
    lines.append("")

    # If skipped, end here
    if results.get("skipped"):
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Run {results.get('summary')}.")
        lines.append(f"- Exit code: `{results.get('exit_code')}`")
        lines.append("")
        log_path.write_text("\n".join(lines))
        return {"log_path": str(log_path), "line_count": len(lines)}

    # Stage 1 — planning
    sd = results.get("stage1_delta_summary") or {}
    if sd:
        lines.append("## Stage 1 — Planning (SyncDelta construction)")
        lines.append("")
        lines.append(f"- timestamp_ms: `{sd.get('timestamp_ms')}`")
        lines.append(f"- source_device_id: `{sd.get('source_device_id')}`")
        lines.append(f"- revision: `{sd.get('revision')}`")
        lines.append(
            f"- updated_keys: `{json.dumps(sd.get('updated_keys') or {}, sort_keys=True)}`"
        )
        lines.append("")

    # Stage 2 — push
    sp = results.get("stage2_push") or {}
    saved_data = sp.get("saved_msgs") or {}
    lit_data = sp.get("litvinov")
    lines.append("## Stage 2 — Push (TG delivery via RemoteSyncCoordinatorImpl)")
    lines.append("")
    lines.append("| Channel | chat_id | msg_id | ok | chunk_count | correlation_id | error |")
    lines.append("|---------|---------|--------|----|-------------|----------------|-------|")
    saved_error = _table_escape(saved_data.get("error"))
    lines.append(
        f"| Saved Messages | `{saved_data.get('chat_id')}` | "
        f"`{saved_data.get('msg_id') or '—'}` | "
        f"`{saved_data.get('ok')}` | "
        f"`{saved_data.get('chunk_count') or '—'}` | "
        f"`{(saved_data.get('correlation_id') or '—')[:30]}` | "
        f"`{saved_error}` |"
    )
    if lit_data:
        lit_error = _table_escape(lit_data.get("error"))
        lines.append(
            f"| Литвинов | `{lit_data.get('chat_id')}` | "
            f"`{lit_data.get('msg_id') or '—'}` | "
            f"`{lit_data.get('ok')}` | "
            f"`{lit_data.get('chunk_count') or '—'}` | "
            f"`{(lit_data.get('correlation_id') or '—')[:30]}` | "
            f"`{lit_error}` |"
        )
    lines.append("")

    # Stage 3 — round-trip
    rt = results.get("stage3_round_trip") or {}
    lines.append("## Stage 3 — Round-trip (TGClient.get_messages read-back)")
    lines.append("")
    lines.append(f"- Connected: **{rt.get('connected')}**")
    if rt.get("saved_msg_text_non_empty") is not None:
        is_yes = bool(rt.get("saved_msg_text_non_empty"))
        lines.append(
            f"- Saved msg_id `{rt.get('saved_msg_id')}` text non-empty: "
            f"**{'✅ TRUE' if is_yes else '❌ FALSE'}**"
        )
    if rt.get("saved_msg_text_head"):
        lines.append(f"  - text head: `{rt['saved_msg_text_head']}`")
    if rt.get("lit_msg_text_non_empty") is not None:
        is_yes = bool(rt.get("lit_msg_text_non_empty"))
        lines.append(
            f"- Литвинов msg_id `{rt.get('lit_msg_id')}` text non-empty: "
            f"**{'✅ TRUE' if is_yes else '❌ FALSE'}**"
        )
    if rt.get("lit_msg_text_head"):
        lines.append(f"  - text head: `{rt['lit_msg_text_head']}`")
    if rt.get("error"):
        lines.append(f"- Round-trip error: `{rt['error']}`")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {results.get('summary', '(no summary)')}")
    lines.append(f"- Exit code: `{results.get('exit_code')}`")
    lines.append("")

    # Bugs encountered
    bugs: List[str] = []
    if not rt.get("connected"):
        bugs.append("TGClient not connected during round-trip")
    if rt.get("saved_msg_text_non_empty") is False:
        bugs.append(
            f"Saved msg_id {rt.get('saved_msg_id')} not round-tripped "
            f"(text empty or msg missing in TG history)"
        )
    if (
        rt.get("lit_msg_text_non_empty") is False
        and lit_data is not None
    ):
        bugs.append(
            f"Литвинов msg_id {rt.get('lit_msg_id')} not round-tripped"
        )
    if bugs:
        lines.append("## Bugs encountered")
        lines.append("")
        for bug in bugs:
            lines.append(f"- {bug}")
        lines.append("")

    log_path.write_text("\n".join(lines))
    return {
        "log_path": str(log_path),
        "line_count": len(lines),
        "status": "written",
    }


# ── CLI entry point ──────────────────────────────────────────────────────


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="e2e_remote_sync",
        description=(
            "Phase 5.3-C real TG round-trip runner for the Freebuff Remote "
            "Sync runtime. Mirrors e2e_promt47.py discipline."
        ),
    )
    p.add_argument(
        "--silent",
        action="store_true",
        help="Suppress stdout banners (logic always runs).",
    )
    p.add_argument(
        "--skip-tg",
        action="store_true",
        help="Zero TG side-effects (pre-flight only).",
    )
    p.add_argument(
        "--sync-group",
        action="store_true",
        help="Dual-channel: also push to Литвинов (default: Saved only).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build content + log only; no actual TG send.",
    )
    p.add_argument(
        "--e2e-log",
        type=Path,
        default=None,
        help="Custom log path (default: "
        "docs_10/e2e_logs/remote_sync_<UTC-timestamp>.md).",
    )
    p.add_argument(
        "--run-tag",
        type=str,
        default=None,
        help="Custom run identifier (default: UTC timestamp).",
    )
    return p


def main() -> int:
    args = _build_arg_parser().parse_args()

    # Default log path: per-run timestamped file
    if args.e2e_log is None:
        tag = args.run_tag or _timestamp_for_filename()
        log_path = DEFAULT_E2E_LOG_DIR / f"remote_sync_{tag}.md"
    else:
        log_path = args.e2e_log
        log_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.silent:
        print("=== e2e_remote_sync.py \u2014 Phase 5.3-C round-trip ===")
        print(
            f"   flags: sync_group={args.sync_group}, "
            f"skip_tg={args.skip_tg}, dry_run={args.dry_run}"
        )
        print(f"   log_path: {log_path}")
        print()

    results = asyncio.run(
        run_e2e_pipeline(
            sync_group_active=args.sync_group,
            skip_tg=args.skip_tg,
            dry_run=args.dry_run,
            run_tag=args.run_tag,
        )
    )

    log_result = write_e2e_log(results, log_path)
    results["stage4_log"] = log_result

    if not args.silent:
        print("=== Run Summary ===")
        print(f"   {results.get('summary')}")
        print(
            f"   log written: {log_result['log_path']} "
            f"({log_result['line_count']} lines)"
        )
        print()

    return int(results.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
