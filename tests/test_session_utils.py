"""Tests for scripts/session_utils.py."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.session_utils ***REMOVED***solve_session_id


class TestResolveSessionId:
    """Тесты resolve_session_id."""

    def test_resolve_full_uuid(self, context_manager):
        snap = context_manager.start_session(project="test", topic="full uuid")
        assert resolve_session_id(context_manager, snap.session_id) == snap.session_id

    def test_resolve_short_prefix(self, context_manager):
        snap = context_manager.start_session(project="test", topic="short prefix")
        short = snap.session_id[:8***REMOVED***
        assert resolve_session_id(context_manager, short) == snap.session_id

    def test_resolve_unknown(self, context_manager):
        assert resolve_session_id(context_manager, "deadbeef") is None

    def test_resolve_none(self, context_manager):
        assert resolve_session_id(context_manager, None) is None

    def test_resolve_full_uuid_nonexistent(self, context_manager):
        assert resolve_session_id(context_manager, "a" * 32) is None
