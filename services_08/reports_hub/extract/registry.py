"""Чтение MissingRegistry для отчёта платформы (спека §4.2 registry, H2).

Парсит `data_13/missing_registry.yaml` без зависимости от core_02:
считает статусы implemented/registered/design_ready/prompt_written.
Битый/отсутствующий файл → пустая сводка + диагностика (не исключение наружу).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_STATUS_RE = re.compile(r"^\s+status:\s*(\S+)", re.MULTILINE)


@dataclass(frozen=True)
class RegistrySummary:
    """Сводка реестра возможностей."""

    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    available: bool = False
    source: str = ""


def read_registry_summary(registry_path: Path) -> RegistrySummary:
    """Прочитать сводку MissingRegistry из YAML.

    Args:
        registry_path: путь к `missing_registry.yaml`.

    Returns:
        RegistrySummary (available=False при отсутствии/битом файле).
    """
    if not registry_path.exists():
        return RegistrySummary(source=str(registry_path))
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError:
        return RegistrySummary(source=str(registry_path))
    statuses = _STATUS_RE.findall(text)
    if "schema_version" not in text and not statuses:
        return RegistrySummary(source=str(registry_path))
    by_status: dict[str, int] = {}
    for status in statuses:
        by_status[status] = by_status.get(status, 0) + 1
    return RegistrySummary(
        total=len(statuses),
        by_status=by_status,
        available=True,
        source=str(registry_path),
    )
