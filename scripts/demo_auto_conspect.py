#!/usr/bin/env python3
"""Demo script for auto_conspect functionality.

Starts a test session, adds a few messages, and runs auto_conspect.
This code was previously embedded in auto_conspect.py and could run
unintentionally when the script was invoked by cron. Use this script
only for manual demos/testing.

Usage:
    python scripts/demo_auto_conspect.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.environ.get("FREEBUFF_ROOT", PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from scripts.auto_conspect import auto_conspect
from scripts.context_manager import ContextManager, SessionStatus, CheckpointType


def main() -> None:
    cm = ContextManager(WORKSPACE)
    sessions = cm.list_sessions(status=SessionStatus.ACTIVE)

    if not sessions:
        print("No active sessions. Starting a test session...")
        snap = cm.start_session(project="freebuff", topic="Auto-conspect test")
        print(f"Created session: {snap.session_id***REMOVED***")
        cm.add_message(snap.session_id, "user", "Test message 1", token_count=20)
        cm.add_message(snap.session_id, "assistant", "Test response 1", token_count=50)
        cm.save_checkpoint(snap.session_id, "Test checkpoint", ctype=CheckpointType.AUTO_INTERVAL)
        result = auto_conspect(snap.session_id)
        print(f"Conspect saved to: {result***REMOVED***")
    else:
        for s in sessions:
            print(f"Conspecting session: {s['session_id'***REMOVED***[:8***REMOVED******REMOVED*** ({s['topic'***REMOVED******REMOVED***)")
            result = auto_conspect(s["session_id"***REMOVED***)
            print(f"  → {result***REMOVED***")


if __name__ == "__main__":
    main()
