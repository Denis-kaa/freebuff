"""Git-статистика Reports Hub (спека §5.1.3, H2).

`git log --follow --oneline` по каталогу проекта. Вне git —
graceful degradation: пустой список, раздел Timeline из git скрывается.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitCommit:
    """Один коммит: хеш + дата + тема."""

    short_hash: str
    date: str
    subject: str


def collect_git_history(project_dir: Path, limit: int = 50) -> list[GitCommit]:
    """Собрать историю коммитов проекта (новые первые).

    Args:
        project_dir: каталог проекта (путь внутри git-репозитория).
        limit: максимум коммитов.

    Returns:
        Список GitCommit; [] при отсутствии git/истории (не исключение).
    """
    try:
        proc = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--format=%h|%ad|%s", "--date=short", "--", "."],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    commits: list[GitCommit] = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        short_hash, date, subject = (p.strip() for p in parts)
        if not short_hash:
            continue
        commits.append(GitCommit(short_hash=short_hash, date=date, subject=subject))
    return commits
