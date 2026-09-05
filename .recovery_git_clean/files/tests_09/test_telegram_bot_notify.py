"""Regression tests for `/notify` + `/notify_client` handlers (v5.42.0 wire-in).

Verifies that the module-level handlers in `scripts_01/telegram_bot.py`:
  1. `/notify` calls `report_to_saved_messages` (from `core_02.telegram_contract`)
     exactly once per invocation, with the admin-wrapped message text.
  2. `/notify_client` calls `report_to_alex_litvinov` exactly once, with the
     client-wrapped message text.
  3. Both handlers reply with usage when invoked without arguments.
  4. On success: reply contains the `msg_id` confirmation.
  5. On `None` return (TG unavailable): reply with diagnostic warning.
  6. On exception: reply with error, never crash.
  7. The module-level wrappers `_notify` / `_notify_client` delegate to the
     corresponding `cmd_*` handlers (ship-blocker fix: top-level functions
     no longer carry a stray `self` parameter).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts_01 import telegram_bot as tbot


# ─── Fixtures ───────────────────────────────────────────────────


def _build_update(chat_id: int = 12345) -> Any:
    """Mimics telegram.Update with a fixed effective_chat.id."""
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    return update


def _build_context(*args: str) -> Any:
    """Mimics telegram.ext.ContextTypes.DEFAULT_TYPE with given command args."""
    ctx = MagicMock()
    ctx.args = list(args) if args else [***REMOVED***
    return ctx


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ─── /notify → report_to_saved_messages ─────────────────────────


def test_cmd_notify_calls_report_to_saved_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/notify <text>` invokes report_to_saved_messages with admin-wrapped text."""
    captured: list[str***REMOVED*** = [***REMOVED***

    async def fake_report(message: str) -> int:
        captured.append(message)
        return 777  # msg_id

    monkeypatch.setattr(tbot, "report_to_saved_messages", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify(update, _build_context("hello", "world")))

    assert len(captured) == 1, f"expected 1 call, got {len(captured)***REMOVED***"
    msg = captured[0***REMOVED***
    assert "📨 [Freebuff admin notify***REMOVED***" in msg
    assert "chat_id=12345" in msg
    assert "hello world" in msg

    update.effective_message.reply_text.assert_awaited_once()
    reply = update.effective_message.reply_text.await_args.args[0***REMOVED***
    assert "777" in reply and "Доставлено в Избранное" in reply


def test_cmd_notify_no_args_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/notify` without args → usage reply, report NOT called."""
    called = False

    async def fake_report(message: str) -> int:
        nonlocal called
        called = True
        return 1

    monkeypatch.setattr(tbot, "report_to_saved_messages", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify(update, _build_context()))

    assert called is False, "report must not be called without args"
    update.effective_message.reply_text.assert_awaited_once()
    assert "Usage: /notify" in update.effective_message.reply_text.await_args.args[0***REMOVED***


def test_cmd_notify_returns_none_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report_to_saved_messages` → None (TG unavailable) → warning reply."""
    async def fake_report(message: str) -> None:
        return None

    monkeypatch.setattr(tbot, "report_to_saved_messages", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify(update, _build_context("ping")))

    update.effective_message.reply_text.assert_awaited_once()
    reply = update.effective_message.reply_text.await_args.args[0***REMOVED***
    assert "Не доставлено в Избранное" in reply


def test_cmd_notify_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report_to_saved_messages` raising → error reply, no crash."""
    async def fake_report(message: str) -> int:
        raise RuntimeError("simulated network blip")

    monkeypatch.setattr(tbot, "report_to_saved_messages", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify(update, _build_context("ping")))  # should NOT raise

    update.effective_message.reply_text.assert_awaited_once()
    assert "Ошибка notify" in update.effective_message.reply_text.await_args.args[0***REMOVED***


# ─── /notify_client → report_to_alex_litvinov ───────────────────


def test_cmd_notify_client_calls_report_to_alex_litvinov(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/notify_client <text>` invokes report_to_alex_litvinov with client-wrapped text."""
    captured: list[str***REMOVED*** = [***REMOVED***

    async def fake_report(message: str) -> int:
        captured.append(message)
        return 888  # msg_id

    monkeypatch.setattr(tbot, "report_to_alex_litvinov", fake_report)

    update = _build_update(chat_id=999)
    _run(tbot.cmd_notify_client(update, _build_context("client", "msg")))

    assert len(captured) == 1, f"expected 1 call, got {len(captured)***REMOVED***"
    msg = captured[0***REMOVED***
    assert "📨 [Freebuff notify → клиент***REMOVED***" in msg
    assert "chat_id=999" in msg
    assert "client msg" in msg

    update.effective_message.reply_text.assert_awaited_once()
    reply = update.effective_message.reply_text.await_args.args[0***REMOVED***
    assert "888" in reply and "Доставлено клиенту" in reply
    assert str(tbot.LITVINOV_CHAT_ID) in reply


def test_cmd_notify_client_no_args_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/notify_client` without args → usage reply, report NOT called."""
    called = False

    async def fake_report(message: str) -> int:
        nonlocal called
        called = True
        return 1

    monkeypatch.setattr(tbot, "report_to_alex_litvinov", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify_client(update, _build_context()))

    assert called is False, "report must not be called without args"
    update.effective_message.reply_text.assert_awaited_once()
    assert "Usage: /notify_client" in update.effective_message.reply_text.await_args.args[0***REMOVED***


def test_cmd_notify_client_returns_none_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report_to_alex_litvinov` → None (TG unavailable) → warning reply."""
    async def fake_report(message: str) -> None:
        return None

    monkeypatch.setattr(tbot, "report_to_alex_litvinov", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify_client(update, _build_context("ping")))

    update.effective_message.reply_text.assert_awaited_once()
    reply = update.effective_message.reply_text.await_args.args[0***REMOVED***
    assert "Не доставлено клиенту" in reply


def test_cmd_notify_client_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report_to_alex_litvinov` raising → error reply, no crash."""
    async def fake_report(message: str) -> int:
        raise RuntimeError("simulated network blip")

    monkeypatch.setattr(tbot, "report_to_alex_litvinov", fake_report)

    update = _build_update()
    _run(tbot.cmd_notify_client(update, _build_context("ping")))  # should NOT raise

    update.effective_message.reply_text.assert_awaited_once()
    assert "Ошибка notify_client" in update.effective_message.reply_text.await_args.args[0***REMOVED***


# ─── Module-level wrappers ──────────────────────────────────────


def test_module_wrappers_delegate_to_cmd_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_notify`/`_notify_client` wrappers delegate to the cmd_* handlers.

    Regression for the ship-blocker: `cmd_notify`/`cmd_notify_client` are
    top-level functions (no `self`); the CommandHandler registration uses the
    wrapper to keep a stable binding.
    """
    notify_called: list[tuple[Any, Any***REMOVED******REMOVED*** = [***REMOVED***
    notify_client_called: list[tuple[Any, Any***REMOVED******REMOVED*** = [***REMOVED***

    async def fake_cmd_notify(update: Any, context: Any) -> None:
        notify_called.append((update, context))

    async def fake_cmd_notify_client(update: Any, context: Any) -> None:
        notify_client_called.append((update, context))

    monkeypatch.setattr(tbot, "cmd_notify", fake_cmd_notify)
    monkeypatch.setattr(tbot, "cmd_notify_client", fake_cmd_notify_client)

    update = _build_update()
    ctx = _build_context("x")
    _run(tbot._notify(update, ctx))
    _run(tbot._notify_client(update, ctx))

    assert len(notify_called) == 1
    assert len(notify_client_called) == 1
    assert notify_called[0***REMOVED***[0***REMOVED*** is update
    assert notify_client_called[0***REMOVED***[0***REMOVED*** is update
