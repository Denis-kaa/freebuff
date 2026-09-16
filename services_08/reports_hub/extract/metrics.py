"""Regex-слой метрик Reports Hub (спека §5.1.3, H2).

Числа выводятся с указанием источника (файл + строка) — анти-галлюцинация
(спека §5.2). Парсер не додумывает: нет совпадения → метрики нет.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MetricHit:
    """Одно извлечённое значение метрики с источником."""

    name: str
    value: str
    source: str


_TESTS_RE = re.compile(r"(\d[\d\s]*)\s*(?:passed|тестов?\s+зелёные|passed,)")
_MYPY_CLEAN_RE = re.compile(r"mypy\s+clean\s*(?:\((\d+)\s*файлов?ов?\)|\(\s*(\d+)\s*файлов?\s*\))?", re.IGNORECASE)
_MYPY_FILES_RE = re.compile(r"mypy\s+clean\s*\(\s*(\d+)", re.IGNORECASE)
_VERSION_RE = re.compile(r"\[?(5\.\d+\.\d+)\]?")
_STATUS_RE = re.compile(r"[🔴🟡🟢✅🔲🟠]")


def _source(path: str, line_no: int) -> str:
    """Источник метрики: файл + строка."""
    return f"{path}:{line_no}"


def extract_metrics(text: str, path: str = "") -> list[MetricHit]:
    """Извлечь метрики из текста отчёта.

    Args:
        text: содержимое документа.
        path: имя файла для источника.

    Returns:
        Список MetricHit (name: tests_passed | mypy_clean | version | status_emoji).
    """
    hits: list[MetricHit] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        tests = _TESTS_RE.search(line)
        if tests:
            raw = tests.group(1).replace(" ", "").replace("\u00a0", "")
            hits.append(MetricHit(name="tests_passed", value=raw, source=_source(path, line_no)))
        mypy = _MYPY_CLEAN_RE.search(line)
        if mypy:
            files = mypy.group(1) or mypy.group(2) or ""
            value = f"clean ({files} файлов)" if files else "clean"
            hits.append(MetricHit(name="mypy_clean", value=value, source=_source(path, line_no)))
        version = _VERSION_RE.search(line)
        if version:
            hits.append(MetricHit(name="version", value=version.group(1), source=_source(path, line_no)))
        for emoji in _STATUS_RE.findall(line):
            hits.append(MetricHit(name="status_emoji", value=emoji, source=_source(path, line_no)))
    return hits


def summarize_metrics(hits: list[MetricHit]) -> dict[str, MetricHit]:
    """Свести хиты к последнему значению каждой метрики (кроме status_emoji)."""
    summary: dict[str, MetricHit] = {}
    for hit in hits:
        if hit.name == "status_emoji":
            continue
        summary[hit.name] = hit
    return summary
