"""Telegram integration contract — resolved chat_ids + report helpers.

Single source of truth for all TG integrations (closed in CAN-3 v5.40.0,
realized as contract in LESSONS §10). Consumers:

  - scripts_01/telegram_bot.py (`TelegramFreebuffBot` admin notifications)
  - freebuff_plugin_03/tgbot.py (`ScenarioTGBot` client escalation)
  - scripts_01/tg_smoke.py (E2E harness)

Public API:
  - SAVED_MESSAGES_CHAT_ID, LITVINOV_CHAT_ID, ALEX_LITVINOV_CHAT_ID, LIVE_SESSION_PHONE
  - async report_to_saved_messages(message: str) -> int | None
  - async report_to_litvinov(message: str) -> int | None
  - async report_to_alex_litvinov(message: str) -> int | None  (= report_to_litvinov)
  - async send_to_chat(chat_id: int, message: str) -> int | None  (произвольный chat)

Architecture:
  Lazy import of projects_17/tg_terminal_messenger/src/telegram/client.py::TGClient
  so this module is import-safe when tg_terminal_messenger is missing (CI without
  the sibling project, open-source redistributions).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("core_02.telegram_contract")

# ── Resolved chat_ids (CAN-3 closed 2026-08-02, v5.40.0) ─────
# Source of truth: docs_10/core/ARCHITECTURAL_DEBT.md §5.10
# (bootstrapped via projects_17/tg_terminal_messenger/tg_session.session,
#  API_ID=37035907 / API_HASH=383bbe0942526db1133edc23d8ba8023).
SAVED_MESSAGES_CHAT_ID: int = 7709651193
LITVINOV_CHAT_ID: int = 1063827731
ALEX_LITVINOV_CHAT_ID: int = LITVINOV_CHAT_ID  # explicit alias for clarity
LIVE_SESSION_PHONE: str = "+79223919054"  # informational; @vaalchik owner

_TG_CLIENT_DIR = (
    Path(__file__).resolve().parents[1]
    / "projects_17"
    / "tg_terminal_messenger"
)
_cached_client_factory: Optional[Any] = None  # cached TGClient *class*


# ─── Telegram client lazy bootstrap ────────────────────────────


def _get_tg_client_factory() -> Optional[Any]:
    """Lazy import TGClient class. Cached after first successful import.

    Returns None if tg_terminal_messenger module is unavailable
    or import raises — caller must defensively check.
    """
    global _cached_client_factory
    if _cached_client_factory is not None:
        return _cached_client_factory
    try:
        tg_dir = str(_TG_CLIENT_DIR)
        if tg_dir not in sys.path:
            sys.path.insert(0, tg_dir)
        from src.telegram.client import TGClient  # type: ignore

        _cached_client_factory = TGClient
        return TGClient
    except Exception as exc:
        logger.debug("TGClient import failed: %s", exc)
        return None


def is_tg_available() -> bool:
    """Public: True iff TGClient class can be imported from sibling project."""
    return _get_tg_client_factory() is not None


# ─── Internal: shared send path ──────────────────────────────


async def _send_text(chat_id: int, text: str) -> Optional[int]:
    """Bootstrap TGClient session + send_message → msg_id | None.

    Single chokepoint for TG-send mechanics. Failures are logged but don't
    raise — caller (report_to_alex_litvinov etc.) returns None on any error.

    Note: TGClient.connect() is async; we instantiate fresh per call to keep
    the module stateless (no leaked connection state across calls). Heavy
    plumbing optimization can be added later via a connection pool — out of
    scope for v5.42.0.
    """
    TGClient = _get_tg_client_factory()
    if TGClient is None:
        logger.error("_send_text: TGClient unavailable")
        return None
    client = TGClient()
    try:
        authorized = await client.connect()
        if not authorized:
            logger.warning("_send_text: session not authorized")
            return None
        msg = await client.send_message(chat_id, text)
        return getattr(msg, "id", None)
    except Exception:
        logger.exception("_send_text: failed for chat_id=%s", chat_id)
        return None
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ─── Public: report functions (3 aliases for clarity) ─────────


async def report_to_saved_messages(message: str) -> Optional[int]:
    """Send `message` to Saved Messages (Избранное) — own @vaalchik channel.

    Returns Telegram msg_id on success, None on any failure.
    Use for freebuff self-reports: build summaries, smoke harness output,
    operational breadcrumbs.
    """
    return await _send_text(SAVED_MESSAGES_CHAT_ID, message)


async def send_to_chat(chat_id: int, message: str) -> Optional[int]:
    """Send `message` to an arbitrary chat_id (public single chokepoint, CON-19).

    Reuses the same connect/send/disconnect mechanics as report_* helpers —
    this is the one place external callers should use for direct sends
    (e.g. prompt dispatcher replying to the originating chat).

    Returns Telegram msg_id on success, None on any failure (None-safe, CAN-14).
    """
    return await _send_text(chat_id, message)


async def report_to_litvinov(message: str) -> Optional[int]:
    """Send `message` to Александр Литвинов. Returns msg_id or None.

    Spec alias: `report_to_alex_litvinov` is the user-facing name from
    task spec; both refer to the same LITVINOV_CHAT_ID.
    """
    return await _send_text(LITVINOV_CHAT_ID, message)


# User-task literal function name (test-cycle entrypoint).
# Imports as `report_to_alex_litvinov` for callers wanting the explicit
# "alex" prefix; functionally identical to report_to_litvinov.
report_to_alex_litvinov = report_to_litvinov


__all__ = [
    "SAVED_MESSAGES_CHAT_ID",
    "LITVINOV_CHAT_ID",
    "ALEX_LITVINOV_CHAT_ID",
    "LIVE_SESSION_PHONE",
    "is_tg_available",
    "report_to_saved_messages",
    "report_to_litvinov",
    "report_to_alex_litvinov",
    "send_to_chat",
]
