"""Контракт модели отчёта Reports Hub (спека §4, §7).

ReportModel — dataclass-контракт: сайт = детерминированный рендер модели.
Модель версионируется (``schema_version``), JSON-сериализуема.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from services_08.reports_hub import SCHEMA_VERSION


@dataclass(frozen=True)
class MetricTile:
    """Одна плитка метрик (тесты, mypy, строки кода, коммиты)."""

    label: str
    value: str
    source: str = ""


@dataclass(frozen=True)
class TimelineEntry:
    """Одна строка хронологии этапов (№, название, коммит, дата, результат)."""

    title: str
    result: str = ""
    commit: str = ""
    date: str = ""


@dataclass(frozen=True)
class DocCard:
    """Карточка библиотеки документов."""

    filename: str
    doc_type: str = ""
    status_quote: str = ""
    date: str = ""
    size_bytes: int = 0
    summary: str = ""


@dataclass(frozen=True)
class ReportSection:
    """Именованная секция отчёта (метрики/timeline/roadmap/блокеры/доки)."""

    name: str
    items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportModel:
    """Отчёт по одному проекту (спека §7.1) или платформе (§7.3)."""

    schema_version: int = SCHEMA_VERSION
    slug: str = ""
    title: str = ""
    generated_at: str = ""
    exec_summary: str = ""
    exec_source: str = ""
    metrics: list[MetricTile] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    docs: list[DocCard] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Сериализовать модель в JSON-совместимый словарь."""
        return asdict(self)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> ReportModel:
        """Десериализовать модель из словаря (проверяет schema_version).

        Raises:
            ValueError: если schema_version отсутствует или новее поддерживаемой.
        """
        version = payload.get("schema_version")
        if version is None:
            raise ValueError("ReportModel: отсутствует schema_version")
        if not isinstance(version, int) or version > SCHEMA_VERSION:
            raise ValueError(
                f"ReportModel: неподдерживаемая schema_version={version!r} "
                f"(поддерживается <= {SCHEMA_VERSION})"
            )
        metrics = [MetricTile(**m) for m in payload.get("metrics", [])]
        timeline = [TimelineEntry(**t) for t in payload.get("timeline", [])]
        sections = [ReportSection(**s) for s in payload.get("sections", [])]
        docs = [DocCard(**d) for d in payload.get("docs", [])]
        return cls(
            schema_version=version,
            slug=str(payload.get("slug", "")),
            title=str(payload.get("title", "")),
            generated_at=str(payload.get("generated_at", "")),
            exec_summary=str(payload.get("exec_summary", "")),
            exec_source=str(payload.get("exec_source", "")),
            metrics=metrics,
            timeline=timeline,
            sections=sections,
            docs=docs,
            diagnostics=[str(x) for x in payload.get("diagnostics", [])],
        )
