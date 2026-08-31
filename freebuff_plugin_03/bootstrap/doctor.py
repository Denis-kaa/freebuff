"""
Runtime Doctor — диагностика окружения.

Основание: docs_10/core/BOOTSTRAP_SPECIFICATION.md §3.5
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from freebuff_plugin_03.bootstrap import DiagnosticReport, EnvironmentState


class RuntimeDoctor:
    """Диагностика окружения.

    Проверяет:
    - PATH (наличие всех нужных директорий)
    - Runtime (наличие и версии)
    - Зависимости (pip пакеты)
    - Ключи (наличие API ключей)
    """

    def __init__(self, env: EnvironmentState, workspace: Path):
        self._env = env
        self._workspace = workspace

    def diagnose(self) -> DiagnosticReport:
        """Запускает полную диагностику."""
        report = DiagnosticReport()

        self._check_path(report)
        self._check_runtimes(report)
        self._check_dependencies(report)
        self._check_keys(report)
        self._calculate_health(report)

        return report

    def _check_path(self, report: DiagnosticReport) -> None:
        """Проверяет PATH."""
        required_dirs = [
            "/usr/local/bin",
            os.path.expanduser("~/.local/bin"),
        ]
        if self._env.is_termux:
            required_dirs.append(os.environ.get("PREFIX", "/data/data/com.termux/files/usr") + "/bin")

        for d in required_dirs:
            if d not in self._env.path_dirs:
                report.path_issues.append(f"{d} not in PATH")

        # Проверяем базовые утилиты
        for util in ["python3", "git", "curl"]:
            if not shutil.which(util):
                report.path_issues.append(f"{util} not found in PATH")

    def _check_runtimes(self, report: DiagnosticReport) -> None:
        """Проверяет runtime."""
        # Python (из EnvironmentState, а не из sys.version_info)
        try:
            parts = self._env.python_version.split(".")
            if len(parts) >= 2:
                py_major = int(parts[0])
                py_minor = int(parts[1])
                if py_major < 3 or (py_major == 3 and py_minor < 11):
                    report.runtime_issues.append(
                        f"Python {py_major}.{py_minor} < 3.11 — may cause compatibility issues"
                    )
        except (ValueError, IndexError):
            pass

        # Git
        if self._env.git_available:
            try:
                result = subprocess.run(
                    ["git", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    ver = result.stdout.strip()
            except Exception:
                pass

        # freebuff
        if shutil.which("freebuff"):
            try:
                result = subprocess.run(
                    ["freebuff", "--version"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    pass  # freebuff работает
                else:
                    report.runtime_issues.append("freebuff CLI is installed but returns error")
            except Exception:
                report.runtime_issues.append("freebuff CLI is installed but fails to run")

    def _check_dependencies(self, report: DiagnosticReport) -> None:
        """Проверяет зависимости."""
        required_pips = ["requests", "pyyaml"]
        for pkg in required_pips:
            if pkg not in self._env.pip_packages:
                report.dependency_issues.append(f"pip package '{pkg}' not installed")

    def _check_keys(self, report: DiagnosticReport) -> None:
        """Проверяет наличие API ключей."""
        # .env файл
        env_path = self._workspace / ".env"
        if not env_path.exists():
            report.key_issues.append(".env file not found")

        # Ключи из .env
        if env_path.exists():
            try:
                for line in env_path.read_text().split("\n"):
                    if line.startswith("ANTHROPIC_API_KEY"):
                        report.key_issues.append("")
                    elif line.startswith("OPENAI_API_KEY"):
                        report.key_issues.append("")
                    elif line.startswith("OPENROUTER_API_KEY"):
                        report.key_issues.append("")
            except Exception:
                pass

        # keys/ директория
        keys_dir = self._workspace / ".keys"
        if not keys_dir.exists():
            report.key_issues.append("No API keys found")
        else:
            # Очищаем пустые строки (ключи найдены)
            report.key_issues = [k for k in report.key_issues if k]

    def _calculate_health(self, report: DiagnosticReport) -> None:
        """Вычисляет health score."""
        total_issues = (
            len(report.path_issues)
            + len(report.runtime_issues)
            + len(report.dependency_issues)
            + len(report.key_issues)
        )

        if total_issues == 0:
            report.health_score = 1.0
        elif total_issues <= 2:
            report.health_score = 0.8
        elif total_issues <= 5:
            report.health_score = 0.5
        else:
            report.health_score = 0.2
