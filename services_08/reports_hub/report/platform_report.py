"""Отчёт платформы Workspace OS (спека §7.3, H5).

Полный срез по корню репозитория: TASK.md (открытые задачи), CHANGELOG.md
(лента релизов), живые метрики (pytest collect-only, MissingRegistry,
git-статистика) и счётчики docs_10 (ADR, аудиты, runbook).

Отсутствующий источник → секция «источник отсутствует», метрики остаются
(правило спеки §11); ничего не придумывается.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from services_08.reports_hub.extract.pytestinfo import count_tests
from services_08.reports_hub.extract.registry import RegistrySummary, read_registry_summary
from services_08.reports_hub.report.model import MetricTile, ReportModel, ReportSection

_TASK_OPEN_RE = re.compile(r"^\s*-\s*\[\s*\]\s*(.+)$", re.MULTILINE)
_RELEASE_RE = re.compile(r"^##\s*\[([^\]]+)\]\s*—\s*(\S+)", re.MULTILINE)


def _git_stat(root: Path, args: list[str]) -> int:
    """Одна git-цифра (0 при любой ошибке — вне git / пустая история)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if proc.returncode != 0:
        return 0
    try:
        return int(proc.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0


def _read_tasks(root: Path) -> tuple[list[str], list[str]]:
    """Открытые задачи из TASK.md (файл может быть большим — только чекбоксы)."""
    path = root / "TASK.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], [f"TASK.md: источник отсутствует"]
    items = [line.strip() for line in _TASK_OPEN_RE.findall(text)]
    return items, [] if items else ["TASK.md: открытых задач не найдено"]


def _read_releases(root: Path, limit: int = 8) -> tuple[list[str], list[str]]:
    """Лента релизов из CHANGELOG.md: «версия — дата» (последние первыми)."""
    path = root / "CHANGELOG.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], ["CHANGELOG.md: источник отсутствует"]
    releases = [f"{version} — {date}" for version, date in _RELEASE_RE.findall(text)]
    return releases[:limit], [] if releases else ["CHANGELOG.md: релизы не найдены"]


def _docs10_counters(root: Path) -> dict[str, int]:
    """Счётчики docs_10: ADR/решения, аудиты, runbook."""
    docs10 = root / "docs_10"
    counters = {
        "решения/ADR": 0,
        "аудиты": 0,
        "runbook": 0,
    }
    if not docs10.is_dir():
        return counters
    for key, markers in (
        ("решения/ADR", ("ADR", "DECISION")),
        ("аудиты", ("AUDIT",)),
        ("runbook", ("RUNBOOK",)),
    ):
        count = 0
        for marker in markers:
            try:
                count += sum(1 for _ in docs10.rglob(f"*{marker}*.md"))
            except OSError:
                continue
        counters[key] = count
    return counters


def build_platform_report(
    root: Path,
    generated_at: str,
    *,
    python_exe: str | None = None,
) -> tuple[ReportModel, RegistrySummary]:
    """Собрать отчёт платформы (спека §7.3).

    Args:
        root: корень репозитория платформы (TASK.md, CHANGELOG.md, data_13/, docs_10/).
        generated_at: штамп времени генерации.
        python_exe: интерпретатор для pytest collect-only (по умолчанию текущий).

    Returns:
        (ReportModel платформы, RegistrySummary) — реестр отдельно для
        прогресс-бара в рендере.
    """
    diagnostics: list[str] = []
    tests = count_tests(root / "tests_09", python_exe=python_exe)
    registry = read_registry_summary(root / "data_13" / "missing_registry.yaml")
    if not registry.available:
        diagnostics.append(f"MissingRegistry недоступен: {registry.source}")

    metrics = [
        MetricTile(label="тесты (collect-only)", value=str(tests.count) if tests.count >= 0 else "н/д", source=tests.source),
    ]
    if registry.available:
        implemented = registry.by_status.get("implemented", 0)
        metrics.append(
            MetricTile(
                label="реестр возможностей",
                value=f"{implemented}/{registry.total} implemented",
                source=registry.source,
            )
        )
    commits_week = _git_stat(root, ["rev-list", "--count", "--since=1 week ago", "HEAD"])
    metrics.append(MetricTile(label="коммиты за неделю", value=str(commits_week), source="git rev-list"))
    branches = _git_stat(root, ["branch", "--list", "--format=%(refname:short)"])
    metrics.append(
        MetricTile(
            label="активные ветки",
            value=str(_git_stat(root, ["branch", "--list"])),
            source="git branch" if branches else "git branch (0)",
        )
    )
    for label, count in _docs10_counters(root).items():
        metrics.append(MetricTile(label=f"docs_10 · {label}", value=str(count), source="docs_10/"))

    tasks, task_diag = _read_tasks(root)
    diagnostics.extend(task_diag)
    releases, release_diag = _read_releases(root)
    diagnostics.extend(release_diag)

    registry_items = (
        [f"{status}: {count}" for status, count in sorted(registry.by_status.items())]
        if registry.available
        else ["источник отсутствует"]
    )
    counters = _docs10_counters(root)
    sections = [
        ReportSection(name="tasks", items=tasks or ["источник отсутствует"]),
        ReportSection(name="releases", items=releases or ["источник отсутствует"]),
        ReportSection(name="registry", items=registry_items),
        ReportSection(
            name="docs10",
            items=[f"{label}: {count}" for label, count in counters.items()],
        ),
    ]
    model = ReportModel(
        slug="platform",
        title="Платформа Workspace OS",
        generated_at=generated_at,
        exec_summary="Полный срез платформы: открытые задачи, релизы, живые метрики и реестр возможностей.",
        exec_source="TASK.md + CHANGELOG.md + data_13/missing_registry.yaml",
        metrics=metrics,
        sections=sections,
        diagnostics=diagnostics,
    )
    return model, registry
