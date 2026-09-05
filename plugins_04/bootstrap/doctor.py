"""RuntimeDoctor — диагностика окружения после установки (спека §2.1)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from plugins_04.bootstrap.types import DiagnosticReport, EnvironmentState

MIN_PYTHON = (3, 11)

# Ключи, наличие которых проверяется (любой из провайдеров достаточен для своей группы)
REQUIRED_KEY_GROUPS: "List[List[str]]" = [
    ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"],   # Claude
    ["OPENROUTER_API_KEY", "OPENAI_API_KEY"],           # OpenAI-compatible
]

REQUIRED_PIP_PACKAGES = ["requests", "pyyaml"]


def _parse_version(version: str) -> "tuple":
    try:
        return tuple(int(p) for p in re.findall(r"\d+", version)[:3])
    except Exception:
        return ()


class RuntimeDoctor:
    """Проверяет PATH, Runtime, ключи и зависимости; считает health score."""

    def __init__(self, env_state: EnvironmentState, workspace: Path) -> None:
        self.env = env_state
        self.workspace = Path(workspace)
        self._env_file_keys: set = set()
        self._load_env_file_keys()

    def _load_env_file_keys(self) -> None:
        env_file = self.workspace / ".env"
        try:
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        self._env_file_keys.add(line.split("=", 1)[0].strip())
        except OSError:
            pass

    # ── диагностика ────────────────────────────────────────

    def diagnose(self) -> DiagnosticReport:
        report = DiagnosticReport()
        report.path_issues = self._check_path()
        report.runtime_issues = self._check_runtimes()
        report.key_issues = self._check_keys()
        report.dependency_issues = self._check_dependencies()
        report.health_score = self._health_score(report)
        return report

    def _check_path(self) -> List[str]:
        issues: List[str] = []
        dirs = self.env.path_dirs
        if not dirs:
            issues.append("PATH is empty or not detected")
        elif not any("bin" in d for d in dirs):
            issues.append("no standard bin directory found in PATH")
        return issues

    def _check_runtimes(self) -> List[str]:
        issues: List[str] = []
        version = self.env.python_version
        parsed = _parse_version(version)
        if not parsed:
            issues.append("Python version not detected")
        elif parsed[:2] < MIN_PYTHON:
            major_minor = ".".join(str(p) for p in parsed[:2])
            issues.append(
                f"Python {major_minor} < required {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
            )
        # Node опционален — отсутствие не проблема
        return issues

    def _check_keys(self) -> List[str]:
        issues: List[str] = []
        for group in REQUIRED_KEY_GROUPS:
            found = any(
                key in os.environ or key in self._env_file_keys for key in group
            )
            if not found:
                issues.append(f"missing API keys: {' or '.join(group)}")
        return issues

    def _check_dependencies(self) -> List[str]:
        installed = {
            name.lower(): ver
            for name, ver in (self.env.pip_packages or {}).items()
        }
        issues: List[str] = []
        for pkg in REQUIRED_PIP_PACKAGES:
            if pkg.lower() not in installed:
                issues.append(f"python package '{pkg}' not installed")
        return issues

    def _health_score(self, report: DiagnosticReport) -> float:
        checks_total = 6
        failures = (
            len(report.path_issues)
            + len(report.runtime_issues)
            + len(report.key_issues)
            + len(report.dependency_issues)
        )
        if not self.env.git_available:
            failures += 1
        score = max(0.0, 1.0 - failures / checks_total)
        return round(score, 2)
