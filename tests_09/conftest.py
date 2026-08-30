"""Shared pytest fixtures for Freebuff tests."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from scripts_01.context_manager import ContextManager


@pytest.fixture
def context_manager(tmp_path) -> "ContextManager":
    """Return a ContextManager backed by a temporary database and directories."""
    from scripts_01.context_manager import ContextManager, DEFAULT_CONTEXT_THRESHOLD

    db_path = str(tmp_path / "data_13" / "context.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    manager = ContextManager.__new__(ContextManager)
    manager._root = str(tmp_path)
    manager._db_path = db_path
    manager._sessions_dir = str(tmp_path / "sessions_15")
    manager._checkpoints_dir = str(tmp_path / "context_12" / "checkpoints")
    manager._summaries_dir = str(tmp_path / "context_12" / "summaries")
    manager._context_threshold = DEFAULT_CONTEXT_THRESHOLD
    manager._lock = threading.Lock()
    manager._event_bus = None

    for d in [manager._sessions_dir, manager._checkpoints_dir, manager._summaries_dir]:
        os.makedirs(d, exist_ok=True)

    manager._init_db()
    return manager


# ═══════════════════════════════════════════════════
# Session Mesh v2.0 fixtures
# ═══════════════════════════════════════════════════


@pytest.fixture
def mesh_tmp_db(tmp_path: Path):
    """Temporary SQLite database path for Mesh event store tests."""
    db_path = tmp_path / "test_events.db"
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def offline_queue_path(tmp_path: Path):
    """Temporary storage path for OfflineQueue tests."""
    yield tmp_path


# ═══════════════════════════════════════════════════
# Corpus isolation fixture (canonical, replaces duplicated _isolate_corpus_root)
# ═══════════════════════════════════════════════════


@pytest.fixture
def isolated_corpus_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect ``scripts_01.corpus_persistence.DEFAULT_CORPUS_DIR`` to tmp_path.

    Canonical replacement for ``_isolate_corpus_root`` helpers that were duplicated
    across 3 test files (``test_corpus_persistence``, ``test_corpus_inspector``,
    ``test_pricing_enumerator``). v5.189.64: single fixture by DRY principle.

    Yields:
        Path: tmp_path-isolated corpus root (callers use this for direct IO).
    """
    corpus_root = tmp_path / "corpus"
    from scripts_01 import corpus_persistence

    monkeypatch.setattr(corpus_persistence, "DEFAULT_CORPUS_DIR", corpus_root)
    # Also propagate to subscription-coupling endpoints (pricing_enumerator).
    try:
        from scripts_01 import pricing_enumerator  # pragma: no cover

        if hasattr(pricing_enumerator, "DEFAULT_CORPUS_DIR"):
            monkeypatch.setattr(pricing_enumerator, "DEFAULT_CORPUS_DIR", corpus_root)
    except ImportError:
        pass
    yield corpus_root
