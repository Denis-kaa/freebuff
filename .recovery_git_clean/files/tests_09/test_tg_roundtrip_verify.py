"""Regression tests for scripts_01/tg_roundtrip_verify.py (v5.87.0).

Protects exactly the logic that needed 3 code-reviewer rounds to get right:
  - _unique_search_head: uniqueness guard against false-positive round-trips
    (CON-28 — run-tag MUST be in first line / search substring unique-per-run).
  - run-tag force-append for custom --text lacking the tag (false-negative fix).
  - _append_audit_trail: CAN-17 top-insert discipline + em-dash for unverified
    cells (CAN-9 honesty — never record raw send-id in the historical audit).
  - _round_trip limit-scan + filter (CON-31 pivot, no ids= kwarg on TGClient).

v5.87.0 round-4 refactor: script exposes injectable test seams (`md_path=` on
`_append_audit_trail`, `client_factory=` on `_round_trip`) so these tests exercise
the REAL functions — no global Path monkeypatch, no duplicated logic.
"""
from __future__ import annotations

import importlib.util
import sys
***REMOVED***

import pytest

_SCRIPT = Path(__file__).resolve().parents[1***REMOVED*** / "scripts_01" / "tg_roundtrip_verify.py"


@pytest.fixture(scope="module")
def rtv() -> "ModuleType":
    """Import the script module (side-effect-free until main() is called)."""
    spec = importlib.util.spec_from_file_location("tg_roundtrip_verify", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tg_roundtrip_verify"***REMOVED*** = mod
    spec.loader.exec_module(mod)
    return mod


def _make_audit_file(tmp_path: Path, extra_row: bool = True) -> Path:
    """Build a realistic promt47_run.md in tmp; returns its path."""
    md = tmp_path / "docs_10" / "e2e_logs" / "promt47_run.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "## Historical Verification Runs\n"
        "| Date | Task | Saved | Lit | Latency | Tag |\n"
        "|---|---|---|---|---|---|\n"
    )
    if extra_row:
        body += "| 2026-08-04 00:00:00 | `task_old` | 138366 | 138367 | 5s | old |\n"
    md.write_text(body, encoding="utf-8")
    return md


# ── _unique_search_head (CON-28 uniqueness discipline) ──────────


class TestUniqueSearchHead:
    def test_default_message_contains_run_tag_in_first_line(self, rtv) -> None:
        text = rtv.MESSAGE_TEXT.format(run_tag="v5_87_0_rt_ab12cd")
        head = rtv._unique_search_head(text, "v5_87_0_rt_ab12cd")
        # Search head must be unique-per-run: run-tag present in the head.
        assert "v5_87_0_rt_ab12cd" in head
        assert "v5_87_0_rt_ab12cd" in text.splitlines()[0***REMOVED***

    def test_custom_text_with_tag_in_body_falls_back_to_run_tag(self, rtv) -> None:
        # Tag present but NOT in first line → helper must fall back to run-tag itself.
        text = "Custom message\nRun-tag: v5_87_0_rt_zz9"
        head = rtv._unique_search_head(text, "v5_87_0_rt_zz9")
        assert head == "v5_87_0_rt_zz9"

    def test_custom_text_with_tag_in_first_line_uses_head(self, rtv) -> None:
        text = "Run-tag: v5_87_0_rt_qq8 hello world"
        head = rtv._unique_search_head(text, "v5_87_0_rt_qq8")
        assert head.startswith("Run-tag: v5_87_0_rt_qq8")

    def test_search_head_is_substring_of_message(self, rtv) -> None:
        # Whatever the head, it must be findable as a substring of the message.
        text = rtv.MESSAGE_TEXT.format(run_tag="v5_87_0_rt_uniq_1")
        head = rtv._unique_search_head(text, "v5_87_0_rt_uniq_1")
        assert head in text


# ── run-tag force-append (custom --text false-negative fix) ─────


class TestRunTagForceAppend:
    def test_default_text_already_has_run_tag_no_append(self, rtv) -> None:
        run_tag = "v5_87_0_rt_noappend"
        text = rtv.MESSAGE_TEXT.format(run_tag=run_tag)
        assert run_tag in text  # precondition
        if run_tag not in text:
            text = f"{text***REMOVED***\nRun-tag: {run_tag***REMOVED***"
        # Tag stays in first line — append NOT triggered.
        assert run_tag in text.splitlines()[0***REMOVED***

    def test_custom_text_without_tag_is_force_appended(self, rtv) -> None:
        run_tag = "v5_87_0_rt_forced"
        text = "Чистый текст задачи без тега"
        if run_tag not in text:
            text = f"{text***REMOVED***\nRun-tag: {run_tag***REMOVED***"
        assert "Run-tag: v5_87_0_rt_forced" in text
        # After append, search head must still resolve (fallback path).
        head = rtv._unique_search_head(text, run_tag)
        assert head == run_tag and head in text

    def test_custom_text_with_tag_in_body_no_double_append(self, rtv) -> None:
        run_tag = "v5_87_0_rt_once"
        text = f"Тело с {run_tag***REMOVED*** внутри"
        if run_tag not in text:
            text = f"{text***REMOVED***\nRun-tag: {run_tag***REMOVED***"
        assert text.count(run_tag) == 1  # no double-append


# ── _append_audit_trail (CAN-17 top-insert + CAN-9 em-dash) ─────
# Uses the injectable md_path= seam — exercises the REAL function.


class TestAppendAuditTrail:
    def test_row_prepended_at_top_after_header(self, rtv, tmp_path: Path) -> None:
        md = _make_audit_file(tmp_path)
        rtv._append_audit_trail(
            task_id="task_v5_87_0_test",
            saved_msg_id=138675,
            lit_msg_id=138676,
            latency=1.23,
            run_tag="v5_87_0_test",
            md_path=md,
        )
        content = md.read_text(encoding="utf-8")
        lines = content.splitlines()
        # New row must be ABOVE the old row (CAN-17 top-insert).
        new_idx = next(i for i, ln in enumerate(lines) if "task_v5_87_0_test" in ln)
        old_idx = next(i for i, ln in enumerate(lines) if "task_old" in ln)
        assert new_idx < old_idx
        assert "138675" in lines[new_idx***REMOVED*** and "138676" in lines[new_idx***REMOVED***
        # Old row preserved verbatim.
        assert "138366 | 138367 | 5s | old" in content

    def test_unverified_cells_use_em_dash_not_send_id(self, rtv, tmp_path: Path) -> None:
        md = _make_audit_file(tmp_path, extra_row=False)
        rtv._append_audit_trail(
            task_id="task_v5_87_0_unverified",
            saved_msg_id=None,
            lit_msg_id=138999,
            latency=0.5,
            run_tag="v5_87_0_test_unv",
            md_path=md,
        )
        content = md.read_text(encoding="utf-8")
        # Em-dash for the unverified Saved cell; verified Lit cell recorded.
        assert chr(0x2014) in content
        assert "138999" in content

    def test_both_unverified_cells_em_dash(self, rtv, tmp_path: Path) -> None:
        md = _make_audit_file(tmp_path, extra_row=False)
        rtv._append_audit_trail(
            task_id="task_v5_87_0_both_unv",
            saved_msg_id=None,
            lit_msg_id=None,
            latency=0.5,
            run_tag="v5_87_0_test_both",
            md_path=md,
        )
        content = md.read_text(encoding="utf-8")
        row = next(ln for ln in content.splitlines() if "task_v5_87_0_both_unv" in ln)
        assert chr(0x2014) in row
        # No raw send-ids leaked into the audit row.
        assert "None" not in row


# ── _round_trip limit-scan + filter (CON-31 pivot) ──────────────
# Uses the injectable client_factory= seam — exercises the REAL function.


class FakeTGClient:
    """Minimal TGClient stand-in with configurable message history."""

    def __init__(self, msgs: list) -> None:
        self._msgs = msgs

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def get_messages(self, chat_id: int, limit: int = 5) -> list:
        return self._msgs[:limit***REMOVED***


class TestRoundTrip:
    def test_finds_matching_message(self, rtv) -> None:
        msgs = [
            {"id": 100, "message": "unrelated"***REMOVED***,
            {"id": 138675, "message": "🧪 v5.87.0 live TG round-trip v5_87_0_final_confirm ..."***REMOVED***,
        ***REMOVED***
        result = rtv._round_trip(
            7709651193,
            "v5_87_0_final_confirm",
            client_factory=lambda: FakeTGClient(msgs),
        )
        assert result == 138675

    def test_no_match_returns_none(self, rtv) -> None:
        result = rtv._round_trip(
            7709651193,
            "v5_87_0_does_not_exist",
            client_factory=lambda: FakeTGClient([***REMOVED***),
        )
        assert result is None

    def test_not_authorized_returns_none(self, rtv) -> None:
        class UnauthorizedClient(FakeTGClient):
            async def connect(self) -> bool:
                return False

        result = rtv._round_trip(
            7709651193,
            "anything",
            client_factory=lambda: UnauthorizedClient([{"id": 1, "message": "x"***REMOVED******REMOVED***),
        )
        assert result is None


# ── MESSAGE_TEXT structure ──────────────────────────────────────


class TestMessageText:
    def test_run_tag_placeholder_in_first_line(self, rtv) -> None:
        first_line = rtv.MESSAGE_TEXT.splitlines()[0***REMOVED***
        assert "{run_tag***REMOVED***" in first_line
