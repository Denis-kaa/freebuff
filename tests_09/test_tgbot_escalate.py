"""Regression tests for ScenarioTGBot.cmd_escalate (v5.42.0 wire-in).

Verifies that `/escalate [note]` handler in `freebuff_plugin_03/tgbot.py`:
  1. Calls `report_to_alex_litvinov` (from `core_02.telegram_contract`) exactly
     once per command invocation.
  2. Includes timestamp, source chat_id, loaded scenario count, and the user's
     note argument in the escalation text.
  3. On success: replies with `msg_id` confirmation message.
  4. On report returning `None` (TG unavailable): replies with diagnostic
     warning, not silent failure.
  5. On report raising exception: replies with error message, does not crash.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from freebuff_plugin_03 import tgbot


# ─── Fixtures ───────────────────────────────────────────────────


def _build_update_with_args(*args: str) -> Any:
    """Mimics telegram.Update with given /escalate args."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


def _build_context(*args: str) -> Any:
    """Mimics telegram.ext.ContextTypes.DEFAULT_TYPE with given /escalate args."""
    ctx = MagicMock()
    ctx.args = list(args) if args else []
    return ctx


# ─── Tests ───────────────────────────────────────────────────────


def test_cmd_escalate_calls_report_with_correct_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """cmd_escalate invokes report_to_alex_litvinov with formatted escalation text."""
    captured: list[tuple[str, Any]] = []

    async def fake_report(message: str) -> int:
        captured.append((message, "called"))
        return 999  # msg_id

    monkeypatch.setattr(tgbot, "report_to_alex_litvinov", fake_report)

    bot = tgbot.ScenarioTGBot()
    asyncio.run(
        bot.cmd_escalate(_build_update_with_args("test‑note"), _build_context("test‑note"))
    )

    assert len(captured) == 1, f"expected 1 call, got {len(captured)}"
    msg, _ = captured[0]
    # Spot‑check the escalation message contents.
    assert "🚨 [Freebuff escalation]" in msg
    assert "Source chat_id: 12345" in msg
    assert "Note: test‑note" in msg
    assert "Loaded scenarios:" in msg
    assert "UTC" in msg


def test_cmd_escalate_handles_no_note() -> None:
    """cmd_escalate works without args (note → '(none)')."""
    captured: list[str] = []

    async def fake_report(message: str) -> int:
        captured.append(message)
        return 999

    with patch.object(tgbot, "report_to_alex_litvinov", side_effect=fake_report):
        bot = tgbot.ScenarioTGBot()
        update = _build_update_with_args()
        ctx = _build_context()  # no args
        asyncio.run(bot.cmd_escalate(update, ctx))

    assert len(captured) == 1
    assert "Note: (none)" in captured[0]


def test_cmd_escalate_success_replies_with_msg_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """On success, reply text contains the msg_id."""
    async def fake_report(message: str) -> int:
        return 12345

    monkeypatch.setattr(tgbot, "report_to_alex_litvinov", fake_report)

    reply_text: list[str] = []

    async def capture_reply(text: str, **kwargs: Any) -> None:
        reply_text.append(text)

    update = MagicMock()
    update.effective_chat.id = 1
    update.effective_message = MagicMock()
    update.effective_message.reply_text = capture_reply

    bot = tgbot.ScenarioTGBot()
    asyncio.run(bot.cmd_escalate(update, _build_context("note")))

    assert any("12345" in t and "доставлена" in t for t in reply_text), (
        f"success message not found in {reply_text}"
    )


def test_cmd_escalate_returns_none_replies_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """When `report_to_alex_litvinov` returns None (TG unavailable) — reply with warning."""
    async def fake_report(message: str) -> None:
        return None  # TGClient unavailable

    monkeypatch.setattr(tgbot, "report_to_alex_litvinov", fake_report)

    reply_text: list[str] = []

    async def capture_reply(text: str, **kwargs: Any) -> None:
        reply_text.append(text)

    update = MagicMock()
    update.effective_chat.id = 1
    update.effective_message = MagicMock()
    update.effective_message.reply_text = capture_reply

    bot = tgbot.ScenarioTGBot()
    asyncio.run(bot.cmd_escalate(update, _build_context()))

    assert any("не доставлена" in t or "TGClient" in t for t in reply_text), (
        f"warning expected in {reply_text}"
    )


def test_cmd_escalate_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """If report raises, cmd_escalate must catch and reply with error, not propagate."""
    async def fake_report(message: str) -> int:
        raise RuntimeError("simulated network blip")

    monkeypatch.setattr(tgbot, "report_to_alex_litvinov", fake_report)

    reply_text: list[str] = []

    async def capture_reply(text: str, **kwargs: Any) -> None:
        reply_text.append(text)

    update = MagicMock()
    update.effective_chat.id = 1
    update.effective_message = MagicMock()
    update.effective_message.reply_text = capture_reply

    bot = tgbot.ScenarioTGBot()
    # Should NOT raise.
    asyncio.run(bot.cmd_escalate(update, _build_context()))

    assert any("Escalation error" in t for t in reply_text), (
        f"error reply expected in {reply_text}"
    )
