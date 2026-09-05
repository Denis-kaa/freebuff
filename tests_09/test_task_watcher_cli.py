"""Tests for task_watcher CLI.

Run: python -m pytest tests_09/test_task_watcher_cli.py -v
"""

from __future__ import annotations

import pytest

from scripts_01.task_watcher_cli import main


class TestTaskWatcherCLI:
    """Тесты CLI команд task_watcher."""

    def test_help(self) -> None:
        """--help не падает."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_no_command(self) -> None:
        """Без команды — показывает help (exit 0)."""
        assert main([]) == 0

    def test_status(self) -> None:
        """Команда status."""
        assert main(["status"]) == 0

    def test_metrics(self) -> None:
        """Команда metrics."""
        assert main(["metrics"]) == 0

    def test_top(self) -> None:
        """Команда top."""
        assert main(["top"]) == 0

    def test_top_with_limit(self) -> None:
        """Команда top с --limit."""
        assert main(["top", "--limit", "5"]) == 0

    def test_pulse(self) -> None:
        """Команда pulse."""
        assert main(["pulse"]) == 0

    def test_automation(self) -> None:
        """Команда automation."""
        assert main(["automation"]) == 0

    def test_rules(self) -> None:
        """Команда rules."""
        assert main(["rules"]) == 0

    def test_simulate_created(self) -> None:
        """Симуляция task.created."""
        assert main([
            "simulate",
            "--type", "created",
            "--task-id", "cli-test-1",
            "--task-name", "CLI Test",
        ]) == 0

    def test_simulate_completed(self) -> None:
        """Симуляция task.completed с duration."""
        assert main([
            "simulate",
            "--type", "completed",
            "--task-id", "cli-test-2",
            "--task-name", "CLI Test 2",
            "--duration", "5.5",
        ]) == 0

    def test_simulate_failed(self) -> None:
        """Симуляция task.failed с ошибкой."""
        assert main([
            "simulate",
            "--type", "failed",
            "--task-id", "cli-test-3",
            "--task-name", "CLI Test 3",
            "--error", "connection refused",
        ]) == 0

    def test_unknown_command(self) -> None:
        """Неизвестная команда — argparse exit(2)."""
        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent"])
        assert exc_info.value.code == 2
