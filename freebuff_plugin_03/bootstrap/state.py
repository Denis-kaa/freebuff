"""
State Management — bootstrap_state.json чтение/запись/merge.

Основание: docs_10/core/BOOTSTRAP_SPECIFICATION.md §5.3
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional

from freebuff_plugin_03.bootstrap import EnvironmentState, InstallStep


class BootstrapState:
    """Управление состоянием Bootstrap Engine.

    Сохраняет bootstrap_state.json после каждого успешного bootstrap
    для идемпотентности и авто-обновления.
    """

    def __init__(self, workspace_root: Path):
        self._path = Path(workspace_root) / "bootstrap_state.json"

    def load(self) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Загружает состояние из bootstrap_state.json.

        Returns:
            Dict с состоянием или None если файл не существует.
        """
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, data: Dict[str, Any***REMOVED***) -> None:
        """Сохраняет состояние.

        Args:
            data: словарь с состоянием для сохранения
        """
        data["timestamp"***REMOVED*** = datetime.now(timezone.utc).isoformat()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def get_component_version(self, component: str) -> Optional[str***REMOVED***:
        """Возвращает сохранённую версию компонента.

        Args:
            component: имя компонента ("freebuff", "python", ...)

        Returns:
            Версия или None если компонент не найден.
        """
        data = self.load()
        if not data:
            return None

        # Проверяем в разделах environments и runtimes
        env = data.get("environment", {***REMOVED***)
        if component in env:
            return env[component***REMOVED***

        runtimes = data.get("runtimes", {***REMOVED***)
        if component in runtimes:
            rt = runtimes[component***REMOVED***
            if rt.get("installed"):
                return rt.get("version")

        return None

    def mark_incomplete(self) -> None:
        """Помечает текущий bootstrap как incomplete."""
        data = self.load() or {***REMOVED***
        data["status"***REMOVED*** = "incomplete"
        self.save(data)

    def mark_complete(self) -> None:
        """Помечает текущий bootstrap как complete."""
        data = self.load() or {***REMOVED***
        data["status"***REMOVED*** = "complete"
        self.save(data)

    def is_complete(self) -> bool:
        """Проверяет, завершён ли последний bootstrap успешно."""
        data = self.load()
        if not data:
            return False
        return data.get("status") == "complete"

    def is_incomplete(self) -> bool:
        """Проверяет, был ли последний bootstrap прерван."""
        data = self.load()
        if not data:
            return False
        return data.get("status") == "incomplete"

    def clear(self) -> None:
        """Удаляет файл состояния."""
        if self._path.exists():
            self._path.unlink()

    def to_report_dict(
        self,
        env: EnvironmentState,
        steps: List[InstallStep***REMOVED***,
        warnings: List[str***REMOVED***,
        errors: List[str***REMOVED***,
        profile: str,
    ) -> Dict[str, Any***REMOVED***:
        """Формирует словарь для сохранения в state.json.

        Args:
            env: состояние окружения
            steps: выполненные шаги
            warnings: предупреждения
            errors: ошибки
            profile: имя профиля

        Returns:
            словарь для сохранения
        """
        return {
            "bootstrap_version": "1.0.0",
            "status": "complete",
            "profile": profile,
            "environment": {
                "python": env.python_version,
                "node": env.node_version or "not found",
                "git": "yes" if env.git_available else "no",
                "os": env.os_type,
                "termux": env.is_termux,
            ***REMOVED***,
            "runtimes": env.runtimes,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "skip_reason": s.skip_reason,
                ***REMOVED***
                for s in steps
            ***REMOVED***,
            "warnings": len(warnings),
            "errors": len(errors),
        ***REMOVED***
