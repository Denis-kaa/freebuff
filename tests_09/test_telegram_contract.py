"""Regression tests for core_02/telegram_contract — chat_ids + report wrappers.

Coverage:
  - constants equal to v5.40.0 resolved values (SAVED_MESSAGES_CHAT_ID,
    LITVINOV_CHAT_ID, ALEX_LITVINOV_CHAT_ID alias).
  - is_tg_available() reports True iff TGClient importable.
  - report_to_saved_messages / report_to_litvinov / report_to_alex_litvinov
    return msg_id when bootstrap + send succeeds; None when TGClient missing.
  - Alias identity: report_to_alex_litvinov is report_to_litvinov.
  - Lazy import path is exercised via monkeypatch on _cached_client_factory.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from core_02 import telegram_contract as tc


# ─── Fixtures: FakeTGClient + monkeypatch hooks ───────────────


class FakeTGClient:
    """In-memory TGClient with controllable authorize/connect/send outcomes.

    Defaults: connect() returns True (authorized), send_message returns a
    Message-like object with .id=999. Override via `cls.next_authorized` or
    `cls.next_send_raises` per-test via monkeypatch.
    """

    next_authorized: bool = True
    next_send_raises: Optional[Exception***REMOVED*** = None
    next_msg_id: int = 999
    last_send_args: Optional[tuple[Any, str***REMOVED******REMOVED*** = None
    call_count: int = 0

    def __init__(self) -> None:
        self.class_state = type(self)
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        return self.class_state.next_authorized

    async def send_message(self, entity: Any, text: str) -> Any:
        self.class_state.last_send_args = (entity, text)
        self.class_state.call_count += 1
        if self.class_state.next_send_raises is not None:
            exc = self.class_state.next_send_raises
            self.class_state.next_send_raises = None
            raise exc
        return SimpleNamespace(id=self.class_state.next_msg_id)

    async def disconnect(self) -> None:
        self.connected = False


@pytest.fixture
def fake_tg(monkeypatch: pytest.MonkeyPatch) -> type[FakeTGClient***REMOVED***:
    """Reset FakeTGClient state + inject as TGClient factory."""
    FakeTGClient.next_authorized = True
    FakeTGClient.next_send_raises = None
    FakeTGClient.next_msg_id = 999
    FakeTGClient.last_send_args = None
    FakeTGClient.call_count = 0
    monkeypatch.setattr(tc, "_cached_client_factory", FakeTGClient)
    return FakeTGClient


# ─── Constants ─────────────────────────────────────────────────


def test_saved_messages_chat_id_constant() -> None:
    """SAVED_MESSAGES_CHAT_ID == 7709651193 (v5.40.0 resolved value)."""
    assert tc.SAVED_MESSAGES_CHAT_ID == 7709651193


def test_litvinov_chat_id_constant() -> None:
    """LITVINOV_CHAT_ID == 1063827731 (v5.40.0 resolved value)."""
    assert tc.LITVINOV_CHAT_ID == 1063827731


def test_alex_litvinov_alias_constant() -> None:
    """ALEX_LITVINOV_CHAT_ID is an alias for LITVINOV_CHAT_ID."""
    assert tc.ALEX_LITVINOV_CHAT_ID == tc.LITVINOV_CHAT_ID == 1063827731


def test_live_session_phone_constant() -> None:
    """LIVE_SESSION_PHONE documents current session phone (informational)."""
    assert tc.LIVE_SESSION_PHONE == "+79223919054"


def test_public_api_exports() -> None:
    """__all__ documents stable public API (consumers must import from these names)."""
    expected = {
        "SAVED_MESSAGES_CHAT_ID",
        "LITVINOV_CHAT_ID",
        "ALEX_LITVINOV_CHAT_ID",
        "LIVE_SESSION_PHONE",
        "is_tg_available",
        "report_to_saved_messages",
        "report_to_litvinov",
        "report_to_alex_litvinov",
        "send_to_chat",
    ***REMOVED***
    assert set(tc.__all__) >= expected


# ─── Function identity ─────────────────────────────────────────


def test_report_to_alex_litvinov_is_report_to_litvinov() -> None:
    """report_to_alex_litvinov and report_to_litvinov refer to the same callable."""
    assert tc.report_to_alex_litvinov is tc.report_to_litvinov


def test_report_functions_are_coroutines() -> None:
    """Each report_* is an async coroutine function (awaitable)."""
    for fn in (
        tc.report_to_saved_messages,
        tc.report_to_litvinov,
        tc.report_to_alex_litvinov,
    ):
        assert asyncio.iscoroutinefunction(fn), f"{fn.__name__***REMOVED*** must be async"


# ─── TGClient availability ────────────────────────────────────


def test_is_tg_available_returns_true_when_factory_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tc, "_cached_client_factory", FakeTGClient)
    assert tc.is_tg_available() is True


def test_is_tg_available_returns_false_when_factory_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensively break the lazy import: monkeypatch the factory function itself.
    The sibling project is normally present in this env; we replace
    `_get_tg_client_factory` with a stub returning None so `is_tg_available`
    observes the missing-TGClient path.
    """
    monkeypatch.setattr(tc, "_get_tg_client_factory", lambda: None)
    assert tc.is_tg_available() is False


# ─── Report functions: happy path (FakeTGClient) ───────────────


def test_report_to_saved_messages_returns_msg_id(fake_tg: type[FakeTGClient***REMOVED***) -> None:
    async def run() -> int | None:
        return await tc.report_to_saved_messages("hello smoke")

    msg_id = asyncio.run(run())
    assert msg_id == 999
    assert fake_tg.last_send_args == (tc.SAVED_MESSAGES_CHAT_ID, "hello smoke")
    assert fake_tg.call_count == 1


def test_report_to_litvinov_uses_litvinov_chat_id(fake_tg: type[FakeTGClient***REMOVED***) -> None:
    async def run() -> int | None:
        return await tc.report_to_litvinov("Привет от Freebuff")

    msg_id = asyncio.run(run())
    assert msg_id == 999
    assert fake_tg.last_send_args == (tc.LITVINOV_CHAT_ID, "Привет от Freebuff")


def test_report_to_alex_litvinov_uses_litvinov_chat_id(
    fake_tg: type[FakeTGClient***REMOVED***,
) -> None:
    async def run() -> int | None:
        return await tc.report_to_alex_litvinov("wizard smoke test")

    msg_id = asyncio.run(run())
    assert msg_id == 999
    # Uses LITVINOV_CHAT_ID (alias) — same pipeline as report_to_litvinov.
    assert fake_tg.last_send_args == (tc.LITVINOV_CHAT_ID, "wizard smoke test")


# ─── send_to_chat (public arbitrary-chat chokepoint, CON-19) ──


def test_send_to_chat_is_public_async() -> None:
    """send_to_chat is an exported async coroutine function."""
    assert hasattr(tc, "send_to_chat")
    assert asyncio.iscoroutinefunction(tc.send_to_chat)


def test_send_to_chat_sends_to_arbitrary_chat(fake_tg: type[FakeTGClient***REMOVED***) -> None:
    async def run() -> int | None:
        return await tc.send_to_chat(123456, "direct reply")

    msg_id = asyncio.run(run())
    assert msg_id == 999
    assert fake_tg.last_send_args == (123456, "direct reply")
    assert fake_tg.call_count == 1


def test_send_to_chat_returns_none_when_tgclient_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """send_to_chat None-safe: missing TGClient → None (no raise)."""
    monkeypatch.setattr(tc, "_get_tg_client_factory", lambda: None)

    async def run() -> int | None:
        return await tc.send_to_chat(123456, "x")

    assert asyncio.run(run()) is None


def test_send_to_chat_returns_none_when_send_raises(
    fake_tg: type[FakeTGClient***REMOVED***,
) -> None:
    fake_tg.next_send_raises = RuntimeError("blip")

    async def run() -> int | None:
        return await tc.send_to_chat(123456, "x")

    assert asyncio.run(run()) is None


# ─── Report functions: failure modes ──────────────────────────


def test_report_returns_none_when_tgclient_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force the TGClient factory to return None via direct function mockup.
    Same setup as test_is_tg_available_returns_false_when_factory_missing but
    exercises the report path: `_send_text` exits via `TGClient is None`
    branch and returns None.
    """
    monkeypatch.setattr(tc, "_get_tg_client_factory", lambda: None)
    async def run() -> int | None:
        return await tc.report_to_litvinov("hello")

    assert asyncio.run(run()) is None


def test_report_returns_none_when_not_authorized(
    fake_tg: type[FakeTGClient***REMOVED***,
) -> None:
    fake_tg.next_authorized = False
    async def run() -> int | None:
        return await tc.report_to_saved_messages("hello")

    assert asyncio.run(run()) is None


def test_report_returns_none_when_send_raises(
    fake_tg: type[FakeTGClient***REMOVED***,
) -> None:
    fake_tg.next_send_raises = RuntimeError("simulated network blip")
    async def run() -> int | None:
        return await tc.report_to_litvinov("hello")

    assert asyncio.run(run()) is None


# ─── Lazy import contract ─────────────────────────────────────


def test_get_tg_client_factory_returns_none_when_module_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str***REMOVED***,
) -> None:
    """When sys.path doesn't expose tg_terminal_messenger + cached None,
    _get_tg_client_factory returns None without raising.
    """
    monkeypatch.setattr(tc, "_cached_client_factory", None)
    # Force import path that WILL raise. Patch sys.modules so any
    # `from src.telegram.client import TGClient` raises ImportError.
    monkeypatch.setitem(__import__("sys").modules, "src", None)
    monkeypatch.setitem(__import__("sys").modules, "src.telegram", None)
    monkeypatch.setitem(__import__("sys").modules, "src.telegram.client", None)
    assert tc._get_tg_client_factory() is None


def test_is_tg_available_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_tg_available() doesn't mutate _cached_client_factory as a side effect
    when no import attempt was made.

    Note: in normal flow, is_tg_available() calls _get_tg_client_factory which
    WILL mutate _cached_client_factory (set to the imported class). This test
    ensures that an import failure doesn't crash is_tg_available().
    """
    monkeypatch.setattr(tc, "_cached_client_factory", None)
    monkeypatch.setitem(__import__("sys").modules, "src", None)
    monkeypatch.setitem(__import__("sys").modules, "src.telegram", None)
    monkeypatch.setitem(__import__("sys").modules, "src.telegram.client", None)
    # Should return False without raising.
    assert tc.is_tg_available() is False
