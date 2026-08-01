"""
Agent Context Bridge: termux-ai-agent ↔ freebuff ContextManager.

Provides a thin adapter that lets the local termux-ai-agent:
  - restore/create a freebuff session on startup
  - log every user request and assistant response
  - create periodic checkpoints
  - auto-conspect on shutdown

Usage in termux-ai-agent/main.py:
    from freebuff.scripts_01.agent_context_bridge import get_context_bridge
    bridge = get_context_bridge()
    bridge.ensure_session()
    bridge.log_user(request.raw_text)
    ...
    bridge.log_assistant(response_dict)
    ...
    bridge.auto_conspect()
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, Optional

from scripts_01.context_manager import ContextManager, SessionStatus, CheckpointType


_FREEBUFF_ROOT = str(Path(__file__).resolve().parent.parent)


class AgentContextBridge:
    """Bridge that persists termux-ai-agent interactions into freebuff.

    The bridge is designed to be used as a module-level singleton so that
    multiple calls to ``run()`` share the same session.  If no session exists,
    it creates one; if an active session already exists for the agent, it
    reuses it.
    """

    def __init__(self, workspace_root: str = _FREEBUFF_ROOT) -> None:
        self._workspace_root = workspace_root
        self._cm = ContextManager(workspace_root)
        self._session_id: Optional[str***REMOVED*** = None
        self._project = "termux-ai-agent"
        self._topic = "v4.0 interaction"
        self._checkpoint_interval = 10

    @property
    def session_id(self) -> Optional[str***REMOVED***:
        return self._session_id

    def ensure_session(self, project: str = "", topic: str = "") -> str:
        """Restore the latest active session or create a new one.

        Args:
            project: optional project name override
            topic: optional topic override

        Returns:
            The active session id.
        """
        if self._session_id:
            return self._session_id

        active = self._cm.list_sessions(SessionStatus.ACTIVE)
        for s in active:
            if s["project"***REMOVED*** == self._project:
                self._session_id = s["session_id"***REMOVED***
                return self._session_id

        snap = self._cm.start_session(
            project=project or self._project,
            topic=topic or self._topic,
        )
        self._session_id = snap.session_id
        return self._session_id

    def log_user(self, text: str) -> None:
        """Log a user request in the current session."""
        sid = self.ensure_session()
        self._cm.add_message(sid, "user", text)
        self._maybe_checkpoint(sid)

    def log_assistant(self, response: Dict[str, Any***REMOVED***) -> None:
        """Log a compact assistant response summary in the current session."""
        sid = self.ensure_session()
        compact = self._compact_response(response)
        self._cm.add_message(sid, "assistant", compact)
        self._maybe_checkpoint(sid)

    def log_error(self, error: Exception) -> None:
        """Log an orchestrator error as a system message."""
        sid = self.ensure_session()
        self._cm.add_message(sid, "system", f"Orchestrator error: {error***REMOVED***")

    @staticmethod
    def _compact_response(response: Dict[str, Any***REMOVED***) -> str:
        """Return a compact JSON summary of the assistant response."""
        summary = {
            "status": response.get("status"),
            "tool": response.get("tool"),
            "error": response.get("error"),
            "error_details": response.get("error_details"),
            "metrics": response.get("metrics"),
        ***REMOVED***
        # Remove None values to keep the message short
        summary = {k: v for k, v in summary.items() if v is not None***REMOVED***
        text = json.dumps(summary, ensure_ascii=False, default=str)
        # Cap length to avoid bloating the context DB
        max_len = 1000
        if len(text) > max_len:
            text = text[:max_len***REMOVED*** + "... [truncated***REMOVED***"
        return text

    def _maybe_checkpoint(self, session_id: str) -> None:
        """Create a periodic checkpoint when the interval is reached."""
        session = self._cm.get_session(session_id)
        if session is None:
            return
        if session.message_count > 0 and session.message_count % self._checkpoint_interval == 0:
            self._cm.save_checkpoint(
                session_id,
                f"Auto-checkpoint after {session.message_count***REMOVED*** messages",
                ctype=CheckpointType.AUTO_INTERVAL,
            )

    def checkpoint(self, summary: str) -> None:
        """Create a manual checkpoint in the current session."""
        sid = self.ensure_session()
        self._cm.save_checkpoint(sid, summary, ctype=CheckpointType.MANUAL)

    def auto_conspect(self) -> Optional[str***REMOVED***:
        """Finalize the current session and generate a conspect.

        Returns:
            Path to the generated conspect file, or None if there is no session.
        """
        if not self._session_id:
            return None

        conspect = self._cm.export_checkpoint_summary(self._session_id)
        self._cm.save_checkpoint(
            self._session_id,
            "Session completed. Conspect generated.",
            ctype=CheckpointType.POST_STEP,
        )
        self._cm.complete_session(self._session_id)

        summaries_dir = os.path.join(self._workspace_root, "context_12", "summaries")
        os.makedirs(summaries_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        filepath = os.path.join(summaries_dir, f"conspect_termux-ai-agent_{ts***REMOVED***.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(conspect)

        return filepath

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Return a short status dict for the current session."""
        if not self._session_id:
            return {"active": False***REMOVED***
        status = self._cm.get_context_status(self._session_id)
        return {"active": True, **status***REMOVED***


_bridge: Optional[AgentContextBridge***REMOVED*** = None


def get_context_bridge() -> AgentContextBridge:
    """Return the module-level singleton bridge rooted in the freebuff workspace."""
    global _bridge
    if _bridge is None:
        _bridge = AgentContextBridge(_FREEBUFF_ROOT)
    return _bridge
