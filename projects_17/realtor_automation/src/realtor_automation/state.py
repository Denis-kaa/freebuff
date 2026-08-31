"""Project state management for realtor_automation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ProjectState:
    """Holds the current project state."""

    version: str = "0.1.0"
    installed: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    phase: str = "init"
    backlog: list[str] = field(default_factory=list)
    knowledge_sources: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectState":
        return cls(**data)


class StateManager:
    """Persist and load project state."""

    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self) -> ProjectState:
        """Load state from disk or return a fresh state."""
        if not self._state_file.exists():
            return ProjectState()
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProjectState.from_dict(data)
        except (json.JSONDecodeError, TypeError) as exc:
            # If state file is corrupted, start fresh but keep a backup.
            backup = self._state_file.with_suffix(".json.bak")
            self._state_file.rename(backup)
            return ProjectState()

    def save(self) -> None:
        """Persist current state to disk."""
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(self._state.to_dict(), f, ensure_ascii=False, indent=2)

    @property
    def state(self) -> ProjectState:
        return self._state

    def set_phase(self, phase: str) -> None:
        self._state.phase = phase
        self.save()

    def add_installed(self, item: str) -> None:
        if item not in self._state.installed:
            self._state.installed.append(item)
            self.save()

    def add_risk(self, risk: str) -> None:
        if risk not in self._state.risks:
            self._state.risks.append(risk)
            self.save()

    def add_backlog_item(self, item: str) -> None:
        if item not in self._state.backlog:
            self._state.backlog.append(item)
            self.save()

    def increment_knowledge(self) -> None:
        self._state.knowledge_sources += 1
        self.save()

    def format_state(self) -> str:
        return (
            f"📊 PROJECT STATE [v{self._state.version}]\n"
            f"✅ Установлено: {', '.join(self._state.installed) or '—'}\n"
            f"⚠️ Ошибки/Риски: {', '.join(self._state.risks) or '—'}\n"
            f"🎯 Текущая фаза: {self._state.phase}\n"
            f"📋 Осталось: {', '.join(self._state.backlog) or '—'}\n"
            f"📚 База знаний: {self._state.knowledge_sources} источников\n"
            f"🕒 Обновлено: {self._state.updated_at}\n"
        )
