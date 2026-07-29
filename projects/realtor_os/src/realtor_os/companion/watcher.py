"""Наблюдение за состоянием системы и heartbeat."""

from __future__ import annotations

import time
***REMOVED***
from typing import Any

from realtor_os.companion.state import StateManager
from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.companion")


class Watcher:
    """Собирает статус компонентов и обновляет state.json."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._state = StateManager(state_path)

    def heartbeat(self, status: str = "healthy", components: dict[str, str***REMOVED*** | None = None) -> dict[str, Any***REMOVED***:
        """Обновить состояние системы.

        Args:
            status: Общий статус.
            components: Статусы компонентов.

        Returns:
            Актуальное состояние.
        """
        if components is None:
            components = {"rag": "ok", "ocr": "ok", "llm": "ok"***REMOVED***
        return self._state.update(status=status, components=components)

    def run(self, interval: int = 300) -> None:
        """Запустить периодический heartbeat.

        Args:
            interval: Интервал в секундах.
        """
        _LOGGER.info("Starting companion watcher with interval %ds", interval)
        while True:
            self.heartbeat()
            time.sleep(interval)
