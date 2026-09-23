#!/usr/bin/env python3
"""tests_09/test_reports_hub_model_contract.py — тест №3 спеки reports-hub.

ReportModel (services_08/reports_hub/model.py): JSON round-trip, schema_version
(несовместимая версия → ValueError), закрытый словарь статусов секций (ANTI-6b),
источники фактов не теряются. Hermetic (tmp_path не нужен — чистые dataclass).
"""

from __future__ import annotations

import json

import pytest

from services_08.reports_hub.model import (
    SCHEMA_VERSION,
    ProjectReport,
    ReportModel,
    Section,
    SourceRef,
)


def _section() -> Section:
    return Section(
        kind="timeline",
        title="Хронология этапов",
        status="ok",
        items=[{"stage": 1, "commit": "86eb680", "date": "2026-09-12"}],
        source=SourceRef(path="projects_17/x/PROJECT_STATUS_REPORT.md", line=12),
    )


def test_roundtrip_full_model() -> None:
    """Модель с секциями и источниками — байт-в-байт round-trip (спека №3)."""
    model = ReportModel(
        generated_at="2026-09-13T12:00:00+00:00",
        projects=[
            ProjectReport(
                slug="p-abc",
                title="Печатник",
                generated_at="2026-09-13T12:00:00+00:00",
                sections=[_section()],
            ),
            ProjectReport(slug="empty", title="Пустой", generated_at="x", has_data=False),
        ],
    )
    restored = ReportModel.from_json_str(model.to_json_str())
    assert restored == model


def test_schema_version_mismatch_rejected() -> None:
    """schema_version не совпала → ValueError с объяснением (модель версионируется)."""
    raw = json.dumps(
        {"schema_version": 999, "generated_at": "x", "projects": []},
        ensure_ascii=False,
    )
    with pytest.raises(ValueError, match="schema_version"):
        ReportModel.from_json_str(raw)


def test_section_status_closed_vocabulary() -> None:
    """Статус секции вне закрытого кортежа → ValueError (ANTI-6b, не молча)."""
    bad = {"kind": "timeline", "title": "t", "status": "unknown"}
    with pytest.raises(ValueError, match="недопустимый статус"):
        Section.from_json(bad)


def test_missing_section_source_is_preserved() -> None:
    """Секция «источник не найден» (status='missing') не теряет note (§5.2)."""
    section = Section(
        kind="metrics", title="Метрики", status="missing", note="файл удалён"
    )
    restored = Section.from_json(section.to_json())
    assert restored.status == "missing"
    assert restored.note == "файл удалён"
    assert restored.source is None


def test_source_ref_roundtrip() -> None:
    ref = SourceRef(path="a/b.md", line=42)
    assert SourceRef.from_json(ref.to_json()) == ref
    assert SourceRef.from_json({"path": "c.md"}).line is None


def test_schema_version_is_one() -> None:
    assert SCHEMA_VERSION == 1
