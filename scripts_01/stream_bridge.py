#!/usr/bin/env python3
"""
stream_bridge.py — Мост между Buffy (AI-ассистент) и stream_session.

Позволяет Buffy автоматически сохранять каждое сообщение в стрим-сессию
без необходимости вызывать stream_session.py вручную.

Использование (из кода Buffy):

    from scripts_01.stream_bridge import StreamBridge
    bridge = StreamBridge()

    # При старте сессии:
    bridge.start_session(topic="Анализ архитектуры")

    # После каждого user message:
    bridge.log_user("текст запроса")

    # После каждого assistant response:
    bridge.log_assistant("текст ответа")

    # При завершении:
    bridge.end_session()

    # Получить конспект для инжекта в контекст:
    conspect = bridge.get_context_resume()
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
}
from typing import Optional

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.context_manager import (
    ContextManager, CheckpointType, SessionStatus, DEFAULT_CONTEXT_THRESHOLD,
)
from scripts_01.stream_session import (
    start_session as _start_session,
    log_message as _log_message,
    attach_session as _attach_session,
    prune_all as _prune_all,
    _get_counter,
    CURRENT_FILE,
    STREAMS_DIR,
)

# ── Ленивый импорт auto_conspect (избегаем циклических импортов) ──

def _import_auto_conspect():
    """Импортирует auto_conspect (lazy)."""
    from scripts_01.auto_conspect import auto_conspect
    return auto_conspect


# ═══════════════════════════════════════════════════════════════
# StreamBridge
# ═══════════════════════════════════════════════════════════════

class StreamBridge:
    """
    Мост для автоматической записи диалога Buffy в стрим-сессию.

    Особенности:
    - Авто-привязка к последней SQLite-сессии (bootstrap)
    - Авто-создание новой стрим-сессии, если нет активной
    - log_user / log_assistant / log_system — удобные обёртки
    - end_session — финальный чекпоинт + конспект
    - get_context_resume — для вставки в новый контекст
    - auto_gc — очистка при старте (если вызвать)
    """

    def __init__(
        self,
        auto_bootstrap: bool = True,
        run_gc: bool = True,
    ):
        self._topic: str = ""
        self._session_dir: Path | None = None
        self._context_manager: ContextManager = ContextManager(
            str(WORKSPACE),
            context_threshold=DEFAULT_CONTEXT_THRESHOLD,
        )
        self._sid: str | None = None

        # GC при старте
        if run_gc:
            try:
                _prune_all(dry_run=False)
            except Exception:
                pass  # GC не критичен

        # Авто-бутстрап: пробуем восстановить последнюю сессию
        if auto_bootstrap:
            self._auto_bootstrap()

    # ── Авто-бутстрап ────────────────────────────────────────

    def _auto_bootstrap(self) -> None:
        """Пытается восстановить последнюю активную сессию или создать новую."""
        # Ищем активные сессии в SQLite
        active = self._context_manager.list_sessions(SessionStatus.ACTIVE)
        if active:
            s = active[0]
            sid = s["session_id"]
            # Пробуем привязать стрим
            try:
                self._session_dir = _attach_session(sid)
                self._sid = sid
                self._topic = s.get("topic", "")
                if self._session_dir:
                    print(f"[StreamBridge] Восстановлена сессия: {sid[:8]} ({s.get('topic', '')})")
                    return
            except Exception:
                pass

    def start_session(self, topic: str = "") -> str:
        """
        Начать новую стрим-сессию.

        Args:
            topic: Тема сессии.

        Returns:
            session_id (первые 8 символов).
        """
        self._topic = topic
        self._session_dir = _start_session(topic=topic)

        if self._session_dir:
            sid_file = self._session_dir / ".session_id"
            if sid_file.exists():
                self._sid = sid_file.read_text().strip()
                return self._sid[:8]
        return "unknown"

    # ── Логирование ──────────────────────────────────────────

    def log_user(self, text: str) -> Optional[int]:
        """Сохранить сообщение пользователя."""
        return _log_message("user", text)

    def log_assistant(self, text: str) -> Optional[int]:
        """Сохранить ответ ассистента."""
        return _log_message("assistant", text)

    def log_system(self, text: str) -> Optional[int]:
        """Сохранить системное сообщение."""
        return _log_message("system", text)

    def checkpoint(self, summary: str) -> None:
        """Ручной чекпоинт в стрим-сессию."""
        if not self._sid:
            return
        self._context_manager.save_checkpoint(
            session_id=self._sid,
            summary=summary,
            ctype=CheckpointType.MANUAL,
        )

    # ── Завершение ───────────────────────────────────────────

    def end_session(self, do_conspect: bool = True) -> str:
        """
        Завершить сессию: чекпоинт + конспект.

        Args:
            do_conspect: создать конспект при завершении.

        Returns:
            Путь к файлу конспекта (или пустая строка).
        """
        result = ""

        if self._sid and self._topic:
            # Финальный чекпоинт
            self._context_manager.save_checkpoint(
                session_id=self._sid,
                summary=f"Session '{self._topic}' completed",
                ctype=CheckpointType.POST_STEP,
            )

            # Конспект
            if do_conspect:
                try:
                    auto_conspect = _import_auto_conspect()
                    filepath = auto_conspect(self._sid)
                    result = filepath
                    print(f"[StreamBridge] Конспект: {filepath}")
                except Exception as e:
                    print(f"[StreamBridge] Ошибка конспекта: {e}", file=sys.stderr)

            # Помечаем COMPLETED
            self._context_manager.complete_session(self._sid)

        # Сбрасываем состояние
        self._session_dir = None
        self._sid = None
        self._topic = ""

        return result

    # ── Контекст ─────────────────────────────────────────────

    def get_context_resume(self) -> str:
        """
        Возвращает конспект последней завершённой сессии
        для вставки в контекст новой сессии.

        Ищет последний файл в context_12/summaries/.
        """
        summaries_dir = WORKSPACE / "context_12" / "summaries"
        if not summaries_dir.is_dir():
            return ""

        files = sorted(
            [f for f in summaries_dir.iterdir() if f.name.endswith(".md")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not files:
            return ""

        try:
            return files[0].read_text(encoding="utf-8")
        except Exception:
            return ""

    def get_status(self) -> dict:
        """Возвращает статус текущей сессии."""
        if not self._sid:
            return {"status": "no_session"}

        status = self._context_manager.get_context_status(self._sid)
        if self._session_dir:
            status["stream_dir"] = self._session_dir.name
            status["msg_count"] = _get_counter(self._session_dir)
        return status

    # ── Context Manager Interface ────────────────────────────

    @property
    def context_manager(self) -> ContextManager:
        return self._context_manager

    @property
    def session_id(self) -> str | None:
        return self._sid


# ═══════════════════════════════════════════════════════════════
# CLI для тестирования
# ═══════════════════════════════════════════════════════════════

def main():
    """Тестовый CLI для StreamBridge."""
    import argparse

    parser = argparse.ArgumentParser(description="StreamBridge — мост для Buffy")
    sub = parser.add_subparsers(dest="command")

    p_test = sub.add_parser("test", help="Тестовый прогон")
    p_test.add_argument("--topic", default="StreamBridge test", help="Тема сессии")

    p_status = sub.add_parser("status", help="Статус моста")

    args = parser.parse_args()

    if args.command == "test":
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge.start_session(topic=args.topic)
        bridge.log_user("Тестовый запрос пользователя")
        bridge.log_assistant("Тестовый ответ ассистента. " * 50)  # длинный текст
        print(f"Статус: {json.dumps(bridge.get_status(), ensure_ascii=False, indent=2)}")
        bridge.end_session()
        print("✅ Тест завершён")

    elif args.command == "status":
        bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
        status = bridge.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
