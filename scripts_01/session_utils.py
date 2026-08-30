"""Shared helpers for working with Freebuff sessions.

Used by CLI tools and cron scripts that need to resolve a short/partial
session_id to a full UUID.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts_01.context_manager import ContextManager


def resolve_session_id(cm: "ContextManager", partial_id: str | None) -> str | None:
    """Находит полный session_id по частичному (первые 8 символов).

    Если переданный идентификатор уже длинный (>=32 символов), проверяет
    его существование через ContextManager. Иначе ищет по префиксу среди
    всех известных сессий.
    """
    if partial_id is None:
        return None
    if len(partial_id) >= 32:  # уже полный UUID
        return partial_id if cm.get_session(partial_id) else None
    for s in cm.list_sessions():
        if s["session_id"].startswith(partial_id):
            return str(s["session_id"])
    return None
