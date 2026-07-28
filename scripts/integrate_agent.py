"""
Integration bridge: связка freebuff ContextManager ↔ termux-ai-agent.
Добавляет в main.py автосохранение контекста при каждом запросе.

Использование (в main.py termux-ai-agent):
    from freebuff.scripts.integrate_agent import FreebuffBridge
    bridge = FreebuffBridge()
    bridge.on_request(query, result)
    bridge.on_session_end()
"""

import os
import sys
from datetime import datetime, timezone

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

from scripts.context_manager import ContextManager, CheckpointType


class FreebuffBridge:
    """Мост между termux-ai-agent и freebuff ContextManager."""

    def __init__(self, auto_checkpoint_interval: int = 10):
        self._cm = ContextManager(WORKSPACE)
        self._active_session: str | None = None
        self._auto_interval = auto_checkpoint_interval

    def on_session_start(self, project: str = "termux-ai-agent", topic: str = "") -> str:
        """Вызывается при старте агента."""
        snap = self._cm.start_session(project=project, topic=topic)
        self._active_session = snap.session_id

        # Проверяем предыдущий конспект
        summaries_dir = os.path.join(WORKSPACE, "context", "summaries")
        if os.path.isdir(summaries_dir):
            files = sorted(
                [f for f in os.listdir(summaries_dir) if f.endswith(".md")***REMOVED***,
                reverse=True,
            )
            if files:
                with open(os.path.join(summaries_dir, files[0***REMOVED***), "r") as f:
                    conspect = f.read()[:2000***REMOVED***
                sys.stderr.write(f"[FreebuffBridge***REMOVED*** Loaded conspect: {files[0***REMOVED******REMOVED*** ({len(conspect)***REMOVED*** chars)\n")

        return self._active_session

    def on_request(self, query: str, result: dict | None = None) -> None:
        """Вызывается при каждом запросе пользователя."""
        if not self._active_session:
            self.on_session_start()
        assert self._active_session is not None, "on_session_start должен установить _active_session"

        self._cm.add_message(
            session_id=self._active_session,
            role="user",
            content=query[:2000***REMOVED***,
            token_count=len(query.split()),
            auto_checkpoint_interval=self._auto_interval,
        )

        if result:
            self._cm.add_message(
                session_id=self._active_session,
                role="assistant",
                content=str(result)[:2000***REMOVED***,
                token_count=50,
            )

    def on_checkpoint(self, summary: str) -> None:
        """Ручной чекпоинт."""
        if self._active_session:
            self._cm.save_checkpoint(
                self._active_session, summary, ctype=CheckpointType.POST_STEP
            )

    def on_session_end(self) -> str:
        """Вызывается при завершении агента."""
        if not self._active_session:
            return ""

        self._cm.save_checkpoint(
            self._active_session,
            "Session ended",
            ctype=CheckpointType.POST_STEP,
        )
        self._cm.complete_session(self._active_session)

        # Генерируем конспект
        from scripts.auto_conspect import auto_conspect
        path = auto_conspect(self._active_session)

        sid = self._active_session
        self._active_session = None
        return path
