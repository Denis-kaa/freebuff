"""Reports Hub — сервис красивых отчётов платформы Workspace OS.

Спека: reports-hub-spec.md (22 решения интервью). H1-каркас: модель отчёта
(`model`) + автообход projects_17 (`config`) + CLI-точка входа.

Границы (§3 не-цели): только читает исходники; без БД; без LLM внутри v1.
"""

from __future__ import annotations

REPORTS_HUB_SCHEMA_VERSION = 1

__all__ = ["REPORTS_HUB_SCHEMA_VERSION"]
