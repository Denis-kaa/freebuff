"""Пакет сборки отчёта Reports Hub (спека §4.2, build/).

Реэкспорт контракта модели для коротких импортов.
"""

from __future__ import annotations

from services_08.reports_hub.report.model import (
    DocCard,
    MetricTile,
    ReportModel,
    ReportSection,
    TimelineEntry,
)

__all__ = [
    "DocCard",
    "MetricTile",
    "ReportModel",
    "ReportSection",
    "TimelineEntry",
]

