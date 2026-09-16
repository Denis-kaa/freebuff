#!/usr/bin/env python3
"""Tests for Reports Hub metrics + gitstats + pytestinfo + registry (спека §12, тест 2).

test_metrics: «249 passed», «mypy clean (50 файлов)», статусы; плюс
graceful-тесты extract-подслоёв (git вне репо, registry без файла).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.extract.gitstats import collect_git_history
from services_08.reports_hub.extract.metrics import extract_metrics, summarize_metrics
from services_08.reports_hub.extract.pytestinfo import count_tests
from services_08.reports_hub.extract.registry import read_registry_summary


class TestMetricsRegex:
    def test_tests_passed_with_source(self) -> None:
        hits = extract_metrics("Состояние: **249 тестов зелёные**\n", path="R.md")
        passed = [h for h in hits if h.name == "tests_passed"]
        assert len(passed) == 1
        assert passed[0].value == "249"
        assert passed[0].source == "R.md:1"

    def test_mypy_clean_with_files(self) -> None:
        hits = extract_metrics("mypy clean (50 файлов)\n", path="R.md")
        mypy = [h for h in hits if h.name == "mypy_clean"]
        assert len(mypy) == 1
        assert "50" in mypy[0].value

    def test_status_emoji_collected(self) -> None:
        hits = extract_metrics("| S0 | ✅ завершён | 2026-09-12 |\n", path="R.md")
        emoji = [h for h in hits if h.name == "status_emoji"]
        assert [h.value for h in emoji] == ["✅"]

    def test_no_metrics_no_hits(self) -> None:
        assert extract_metrics("Обычный текст без цифр.\n", path="R.md") == []

    def test_summarize_keeps_last(self) -> None:
        hits = extract_metrics("100 passed\n200 passed\n", path="R.md")
        summary = summarize_metrics(hits)
        assert summary["tests_passed"].value == "200"
        assert summary["tests_passed"].source == "R.md:2"


class TestExtractGraceful:
    def test_git_outside_repo_returns_empty(self, tmp_path: Path) -> None:
        assert collect_git_history(tmp_path) == []

    def test_git_real_repo_collects(self) -> None:
        commits = collect_git_history(PROJECT_ROOT, limit=5)
        assert len(commits) >= 1
        assert commits[0].short_hash != ""
        assert commits[0].date != ""

    def test_registry_missing_file_not_available(self, tmp_path: Path) -> None:
        summary = read_registry_summary(tmp_path / "nope.yaml")
        assert summary.available is False
        assert summary.total == 0

    def test_registry_real_file(self) -> None:
        summary = read_registry_summary(PROJECT_ROOT / "data_13" / "missing_registry.yaml")
        assert summary.available is True
        assert summary.total >= 50
        assert summary.by_status.get("implemented", 0) >= 1

    def test_pytest_count_tmp_dir(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_mini.py"
        test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        result = count_tests(tmp_path)
        assert result.count == 1
        # Второй вызов — из кэша, тот же результат.
        assert count_tests(tmp_path).count == 1
