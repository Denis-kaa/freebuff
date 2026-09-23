#!/usr/bin/env python3
"""Golden-тест Reports Hub на реальных доках печатника (спека §12, тест 9).

Защита от регрессий парсера: ожидаемые секции, хронология этапов,
ключевые метрики (249 passed, mypy clean 50 файлов).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.config import build_profile
from services_08.reports_hub.report.project_report import build_project_report
from services_08.reports_hub.report.render import render_project_page

PECHATNIK = PROJECT_ROOT / "projects_17" / "админка печатник"


def _model():
    """Модель печатника по реальным докам (без сети и git-зависимостей)."""
    profile = build_profile("админка печатник", PECHATNIK)
    return build_project_report(profile, generated_at="2026-09-16")


class TestGoldenPechatnik:
    def test_profile_has_docs(self) -> None:
        profile = build_profile("админка печатник", PECHATNIK)
        assert profile.has_report_docs is True
        assert profile.invalid_reason == ""

    def test_metrics_from_real_docs(self) -> None:
        model = _model()
        by_label = {tile.label: tile.value for tile in model.metrics}
        assert "249 passed" in by_label.get("тесты", "")
        assert "clean" in by_label.get("mypy", "")
        assert "50" in by_label.get("mypy", "")

    def test_timeline_stages_extracted(self) -> None:
        model = _model()
        assert len(model.timeline) >= 13
        titles = [entry.title for entry in model.timeline]
        assert any("Аудит" in title for title in titles)
        assert any(entry.commit for entry in model.timeline)

    def test_docs_library_populated(self) -> None:
        model = _model()
        names = {card.filename for card in model.docs}
        assert "PROJECT_STATUS_REPORT.md" in names
        assert any(name.startswith("PHASE_RULES_R") for name in names)
        assert all(card.summary or card.status_quote or card.date for card in model.docs)

    def test_sections_present(self) -> None:
        model = _model()
        sections = {section.name for section in model.sections}
        assert "roadmap" in sections
        assert "blockers" in sections

    def test_render_page_contains_key_facts(self) -> None:
        page = render_project_page(_model())
        assert "<title>" in page
        assert "--accent" in page
        assert "249 passed" in page
        assert "Хронология этапов" in page
        assert "Библиотека документов" in page

    def test_exec_summary_not_empty(self) -> None:
        model = _model()
        assert len(model.exec_summary) > 30
        assert model.exec_source.endswith("PROJECT_STATUS_REPORT.md")