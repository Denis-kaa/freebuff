"""Shared pytest fixtures for Freebuff tests."""
from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from scripts.context_manager import ContextManager


@pytest.fixture
def context_manager(tmp_path) -> "ContextManager":
    """Return a ContextManager backed by a temporary database and directories."""
    from scripts.context_manager import ContextManager, DEFAULT_CONTEXT_THRESHOLD

    db_path = str(tmp_path / "data" / "context.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    manager = ContextManager.__new__(ContextManager)
    manager._root = str(tmp_path)
    manager._db_path = db_path
    manager._sessions_dir = str(tmp_path / "sessions")
    manager._checkpoints_dir = str(tmp_path / "context" / "checkpoints")
    manager._summaries_dir = str(tmp_path / "context" / "summaries")
    manager._context_threshold = DEFAULT_CONTEXT_THRESHOLD
    manager._lock = threading.Lock()
    manager._event_bus = None

    for d in [manager._sessions_dir, manager._checkpoints_dir, manager._summaries_dir***REMOVED***:
        os.makedirs(d, exist_ok=True)

    manager._init_db()
    return manager
