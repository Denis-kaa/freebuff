"""Манифест для Buffy companion control."""

from __future__ import annotations

import json
}
from typing import Any

from realtor_os.constants import MANIFEST_PATH, PROJECT_ROOT


class ManifestError(Exception):
    """Ошибка манифеста."""


def generate_manifest(path: Path | None = None) -> dict[str, Any]:
    """Сгенерировать buffy_manifest.json."""
    if path is None:
        path = MANIFEST_PATH

    manifest: dict[str, Any] = {
        "project": "realtor_os",
        "version": "0.1.0",
        "owner": "realtor_etagi_poykovsky",
        "description": "Local privacy-first automation for a realtor",
        "environment": "Termux/Android/ARM64",
        "root_required": False,
        "commands": {
            "status": "PYTHONPATH=src python -m realtor_os.cli status",
            "start": "bash scripts/start_system.sh",
            "ingest": "PYTHONPATH=src python -m realtor_os.cli ingest",
            "ask": "PYTHONPATH=src python -m realtor_os.cli ask",
            "ocr": "PYTHONPATH=src python -m realtor_os.cli ocr",
            "learn": "PYTHONPATH=src python -m realtor_os.cli learn",
        },
        "state_file": "companion/state.json",
        "log_file": "logs/realtor_os.log",
        "config_file": "config.yaml",
        "docs": {
            "readme": "README.md",
            "architecture": "docs/ARCHITECTURE.md",
            "roadmap": "docs/ROADMAP.md",
            "changelog": "docs/CHANGELOG.md",
        },
    }

    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    """Загрузить buffy_manifest.json."""
    if path is None:
        path = MANIFEST_PATH

    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid manifest JSON: {exc}") from exc

    return data


def get_project_root() -> Path:
    return PROJECT_ROOT
