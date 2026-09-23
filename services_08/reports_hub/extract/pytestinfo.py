"""Счётчик тестов Reports Hub (спека §4.2 pytestinfo, H2).

Живой счётчик через `pytest --collect-only -q` с кэшем по mtime.
Тяжёлый полный прогон не запускается: только сбор (collect-only).
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

_COLLECT_RE = re.compile(r"(\d+)\s+tests?\s+collected", re.IGNORECASE)


@dataclass
class PytestCount:
    """Результат подсчёта: число тестов + источник + свежесть."""

    count: int
    source: str
    collected_at: float = 0.0


#: Кэш счётчиков: ключ — строка каталога. Инвалидация — по newest mtime .py.
_CACHE: dict[str, tuple[float, PytestCount]] = {}


def _newest_mtime(root: Path) -> float:
    """Максимальный mtime .py файлов под root (0.0 при отсутствии)."""
    newest = 0.0
    try:
        for path in root.rglob("*.py"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > newest:
                newest = mtime
    except OSError:
        pass
    return newest


def count_tests(tests_dir: Path, python_exe: str | None = None, timeout: int = 60) -> PytestCount:
    """Посчитать тесты через pytest --collect-only (с кэшем по mtime).

    Args:
        tests_dir: каталог с тестами.
        python_exe: интерпретатор с pytest (по умолчанию — текущий sys.executable,
            а не bare ``python3``: системный python может не иметь pytest).
        timeout: лимит секунд на сбор.

    Returns:
        PytestCount; count=-1 при недоступности pytest (источник фиксирует причину).
    """
    import sys

    interpreter = python_exe or sys.executable
    key = f"{interpreter}|{tests_dir}"
    newest = _newest_mtime(tests_dir)
    cached = _CACHE.get(key)
    if cached and cached[0] >= newest and cached[1].count >= 0:
        return cached[1]
    try:
        proc = subprocess.run(
            [interpreter, "-m", "pytest", "--collect-only", "-q", str(tests_dir)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return PytestCount(count=-1, source=f"collect failed: {exc}")
    combined = proc.stdout + proc.stderr
    match = _COLLECT_RE.search(combined)
    if not match:
        # Pytest 9 в quiet-режиме иногда печатает «1 test collected»
        # (singular) — основной regex уже покрывает; иначе честный -1.
        fallback = re.findall(r"^(.+::\S+)\s*$", combined, re.MULTILINE)
        if not fallback:
            return PytestCount(count=-1, source="pytest collect: счётчик не найден")
        result = PytestCount(
            count=len(fallback),
            source=f"pytest --collect-only {tests_dir} (fallback: строки ::test)",
            collected_at=time.time(),
        )
        _CACHE[key] = (newest, result)
        return result
    result = PytestCount(
        count=int(match.group(1)),
        source=f"pytest --collect-only {tests_dir}",
        collected_at=time.time(),
    )
    _CACHE[key] = (newest, result)
    return result
