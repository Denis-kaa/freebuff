"""Управление состоянием для Buffy."""

from __future__ import annotations

import datetime
import json
***REMOVED***
from typing import Any

from realtor_os.constants import STATE_PATH


class StateError(Exception):
    """Ошибка состояния."""


def _default_state() -> dict[str, Any***REMOVED***:
    return {
        "version": "0.1.0",
        "status": "healthy",
        "last_check": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "components": {
            "rag": "ok",
            "ocr": "ok",
            "llm": "ok",
        ***REMOVED***,
    ***REMOVED***


class StateManager:
    """Менеджер состояния companion."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or STATE_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any***REMOVED***:
        if not self._path.exists():
            return self.save(_default_state())
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StateError(f"Failed to load state: {exc***REMOVED***") from exc
        return data

    def save(self, data: dict[str, Any***REMOVED***) -> dict[str, Any***REMOVED***:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def update(self, **kwargs: Any) -> dict[str, Any***REMOVED***:
        data = self.load()
        data.update(kwargs)
        data["last_check"***REMOVED*** = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return self.save(data)


def load_state(path: Path | None = None) -> dict[str, Any***REMOVED***:
    return StateManager(path).load()


def save_state(data: dict[str, Any***REMOVED***, path: Path | None = None) -> dict[str, Any***REMOVED***:
    return StateManager(path).save(data)
