#!/usr/bin/env python3
"""Tests for Reports Hub summaries override (спека §12, тест 8: test_summaries_override).

Приоритет override > детерминированного; осиротевшие ключи summaries.json
попадают в диагностику генерации (спека §11: не молча).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.report.generate import generate_site
from services_08.reports_hub.report.summaries import (
    DeterministicProvider,
    OverrideProvider,
    slugify,
)


class TestOverrideProvider:
    def test_priority_over_deterministic(self) -> None:
        override = OverrideProvider({"project:demo:exec": "Кастомное резюме владельца"})
        assert override.exec_summary("project:demo:exec", "детерминированный фолбэк") == "Кастомное резюме владельца"

    def test_fallback_when_key_missing(self) -> None:
        override = OverrideProvider({})
        assert override.exec_summary("project:demo:exec", "фолбэк") == "фолбэк"
        assert override.doc_summary("project:demo:doc:x.md", "док-фолбэк") == "док-фолбэк"

    def test_orphans_tracked(self) -> None:
        override = OverrideProvider(
            {
                "project:demo:exec": "используется",
                "project:ghost:exec": "осиротевший",
            }
        )
        override.exec_summary("project:demo:exec", "фолбэк")
        assert override.orphans() == ["project:ghost:exec"]
        assert override.used() == {"project:demo:exec"}

    def test_from_file_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "summaries.json"
        path.write_text(
            json.dumps({"schema_version": 1, "project:demo:exec": "из файла"}, ensure_ascii=False),
            encoding="utf-8",
        )
        override = OverrideProvider.from_file(path)
        assert override.exec_summary("project:demo:exec", "фолбэк") == "из файла"

    def test_from_file_missing_or_broken(self, tmp_path: Path) -> None:
        assert OverrideProvider.from_file(tmp_path / "nope.json").orphans() == []
        path = tmp_path / "broken.json"
        path.write_text("[1,2,3]", encoding="utf-8")  # не dict → пустой override
        override = OverrideProvider.from_file(path)
        assert override.exec_summary("k", "фолбэк") == "фолбэк"

    def test_blank_and_non_string_values_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "summaries.json"
        path.write_text(
            json.dumps({"a": "   ", "b": 42, "schema_version": 1, "c": "годен"}, ensure_ascii=False),
            encoding="utf-8",
        )
        override = OverrideProvider.from_file(path)
        assert override.exec_summary("a", "фолбэк-A") == "фолбэк-A"
        assert override.exec_summary("b", "фолбэк-B") == "фолбэк-B"
        assert override.exec_summary("c", "фолбэк-C") == "годен"

    def test_deterministic_provider_passthrough(self) -> None:
        provider = DeterministicProvider()
        assert provider.exec_summary("k", "фолбэк") == "фолбэк"
        assert provider.doc_summary("k", "фолбэк") == "фолбэк"


class TestOrphansInGeneration:
    def _make_project(self, root: Path) -> None:
        project_dir = root / "projects_17" / "demo"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "reports_hub.yaml").write_text(
            "title: Demo\n"
            'docs:\n  - "PROJECT_STATUS_REPORT.md"\n'
            'timeline_sources:\n  - "PROJECT_STATUS_REPORT.md"\n',
            encoding="utf-8",
        )
        (project_dir / "PROJECT_STATUS_REPORT.md").write_text(
            "# S\n\n> Дата: 2026-09-16 · Состояние: **249 тестов зелёные**\n",
            encoding="utf-8",
        )

    def test_orphans_landed_in_diagnostics(self, tmp_path: Path) -> None:
        self._make_project(tmp_path)
        summaries = tmp_path / "summaries.json"
        summaries.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project:demo:exec": "Оверрайд резюме проекта",
                    "project:ghost:exec": "ключ-сирота",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = generate_site(tmp_path / "projects_17", tmp_path / "site", summaries_path=summaries)
        assert result.projects == 1
        assert any("осиротевшие ключи summaries" in d and "project:ghost:exec" in d for d in result.diagnostics)
        assert result.orphans == ["project:ghost:exec"]
        # Override применился к exec-резюме проекта.
        page = (tmp_path / "site" / "projects" / slugify("demo") / "index.html").read_text(encoding="utf-8")
        assert "Оверрайд резюме проекта" in page

    def test_no_orphans_no_diag(self, tmp_path: Path) -> None:
        self._make_project(tmp_path)
        summaries = tmp_path / "summaries.json"
        summaries.write_text(
            json.dumps({"schema_version": 1, "project:demo:exec": "точное резюме"}, ensure_ascii=False),
            encoding="utf-8",
        )
        result = generate_site(tmp_path / "projects_17", tmp_path / "site", summaries_path=summaries)
        assert result.orphans == []
        assert not any("осиротевшие" in d for d in result.diagnostics)

    def test_missing_summaries_file_is_noop(self, tmp_path: Path) -> None:
        self._make_project(tmp_path)
        result = generate_site(
            tmp_path / "projects_17", tmp_path / "site", summaries_path=tmp_path / "nope.json"
        )
        assert result.projects == 1
        assert result.orphans == []
