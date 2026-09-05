"""BootstrapState — персистентное состояние bootstrap (bootstrap_state.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins_04.bootstrap.types import EnvironmentState, InstallStep

STATE_FILENAME = "bootstrap_state.json"


class BootstrapState:
    """Менеджер состояния среды: load/save/clear + отчётная структура."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)
        self.path = self.workspace / STATE_FILENAME

    # ── базовые операции ────────────────────────────────────

    def load(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self.path, encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            return data
        except Exception:
            return None

    def save(self, data: Dict[str, Any]) -> None:
        payload = dict(data)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.workspace.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    # ── статусные предикаты ────────────────────────────────

    def is_complete(self) -> bool:
        data = self.load()
        return bool(data and data.get("status") == "complete")

    def is_incomplete(self) -> bool:
        data = self.load()
        return bool(data and data.get("status") == "incomplete")

    def mark_incomplete(self) -> None:
        data = self.load() or {}
        data["status"] = "incomplete"
        self.save(data)

    # ── запросы ────────────────────────────────────────────

    def get_component_version(self, component: str) -> Optional[str]:
        """Версия компонента из environment.* или runtimes.*.version."""
        data = self.load()
        if not data:
            return None
        env = data.get("environment", {})
        if isinstance(env, dict) and component in env:
            value = env[component]
            return value if isinstance(value, str) else None
        runtimes = data.get("runtimes", {})
        entry = runtimes.get(component)
        if isinstance(entry, dict):
            version = entry.get("version")
            return version if isinstance(version, str) else None
        return None

    # ── отчёт ──────────────────────────────────────────────

    def to_report_dict(
        self,
        env_state: EnvironmentState,
        steps: List[InstallStep],
        warnings: List[str],
        errors: List[str],
        profile: str,
    ) -> Dict[str, Any]:
        return {
            "profile": profile,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "complete" if not errors else "incomplete",
            "environment": {
                "os": env_state.os_type,
                "python": env_state.python_version,
                "node": env_state.node_version,
                "git": env_state.git_available,
                "disk_free_gb": env_state.disk_free_gb,
                "ram_total_mb": env_state.ram_total_mb,
                "ram_available_mb": env_state.ram_available_mb,
            },
            "runtimes": {},
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in steps
            ],
            "warnings": list(warnings),
            "errors": list(errors),
        }
