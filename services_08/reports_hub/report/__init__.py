"""Пакет сборки отчёта Reports Hub (спека §4.2, report/).

Контракт модели + сборка проектного отчёта + библиотека доков +
резюме (override/детерминированные) + HTML-рендер + генерация сайта.
"""

from __future__ import annotations

from services_08.reports_hub.report.doclibrary import DocEntry, collect_docs, doc_type_of
from services_08.reports_hub.report.generate import GenerateResult, generate_site
from services_08.reports_hub.report.model import (
    DocCard,
    MetricTile,
    ReportModel,
    ReportSection,
    TimelineEntry,
)
from services_08.reports_hub.report.project_report import (
    build_project_report,
    extract_blockers,
    extract_roadmap,
    extract_timeline,
    slug_for,
)
from services_08.reports_hub.report.render import (
    SiteModel,
    render_doc_page,
    render_index,
    render_project_page,
    write_site,
)
from services_08.reports_hub.report.summaries import (
    DeterministicProvider,
    OverrideProvider,
    SummaryProvider,
    slugify,
)

__all__ = [
    "DeterministicProvider",
    "DocCard",
    "DocEntry",
    "GenerateResult",
    "MetricTile",
    "OverrideProvider",
    "ReportModel",
    "ReportSection",
    "SiteModel",
    "SummaryProvider",
    "TimelineEntry",
    "build_project_report",
    "collect_docs",
    "doc_type_of",
    "extract_blockers",
    "extract_roadmap",
    "extract_timeline",
    "generate_site",
    "render_doc_page",
    "render_index",
    "render_project_page",
    "slug_for",
    "slugify",
    "write_site",
]

