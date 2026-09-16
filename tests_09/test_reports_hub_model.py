#!/usr/bin/env python3
"""Tests for Reports Hub model contract (спека §12, тест 3: test_model_contract).

ReportModel: сериализация/десериализация, schema_version.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub import SCHEMA_VERSION
from services_08.reports_hub.report.model import (
    DocCard,
    MetricTile,
    ReportModel,
    ReportSection,
    TimelineEntry,
)


def _sample_model() -> ReportModel:
    """Минимальная модель отчёта для round-trip проверок."""
    return ReportModel(
        slug="pechatnik",
        title="Печатник",
        generated_at="2026-09-16",
        exec_summary="Операционная система типографии.",
        exec_source="PROJECT_STATUS_REPORT.md",
        metrics=[MetricTile(label="тесты", value="249 passed", source="PROJECT_STATUS_REPORT.md:132")],
        timeline=[TimelineEntry(title="Этап 1", result="клиенты", commit="2a85211", date="2026-09-08")],
        sections=[ReportSection(name="roadmap", items=["H1 — каркас"])],
        docs=[DocCard(filename="PROJECT_STATUS_REPORT.md", doc_type="status", status_quote="COMPLETE")],
        diagnostics=["источник не найден: X.md"],
    )


class TestModelRoundTrip:
    def test_to_json_has_schema_version(self) -> None:
        payload = _sample_model().to_json()
        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["slug"] == "pechatnik"

    def test_from_json_round_trip(self) -> None:
        model = _sample_model()
        restored = ReportModel.from_json(model.to_json())
        assert restored == model

    def test_from_json_defaults(self) -> None:
        restored = ReportModel.from_json({"schema_version": SCHEMA_VERSION, "slug": "x"})
        assert restored.title == ""
        assert restored.metrics == []
        assert restored.timeline == []
        assert restored.sections == []
        assert restored.docs == []
        assert restored.diagnostics == []


class TestModelVersionGuard:
    def test_missing_version_raises(self) -> None:
        with pytest.raises(ValueError, match="schema_version"):
            ReportModel.from_json({"slug": "x"})

    def test_future_version_raises(self) -> None:
        with pytest.raises(ValueError, match="неподдерживаемая"):
            ReportModel.from_json({"schema_version": SCHEMA_VERSION + 1, "slug": "x"})
