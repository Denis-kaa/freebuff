"""Extract-слой Reports Hub: markdown, metrics, gitstats, pytestinfo, registry.

Реэкспорт для коротких импортов (реализация — H2, спека §5).
"""

from __future__ import annotations

from services_08.reports_hub.extract.gitstats import GitCommit, collect_git_history
from services_08.reports_hub.extract.markdown import (
    ParsedDocument,
    Section,
    Table,
    find_sections,
    first_paragraph,
    parse_markdown,
)
from services_08.reports_hub.extract.metrics import MetricHit, extract_metrics, summarize_metrics
from services_08.reports_hub.extract.pytestinfo import PytestCount, count_tests
from services_08.reports_hub.extract.registry import RegistrySummary, read_registry_summary

__all__ = [
    "GitCommit",
    "MetricHit",
    "ParsedDocument",
    "PytestCount",
    "RegistrySummary",
    "Section",
    "Table",
    "collect_git_history",
    "count_tests",
    "extract_metrics",
    "find_sections",
    "first_paragraph",
    "parse_markdown",
    "read_registry_summary",
    "summarize_metrics",
]

