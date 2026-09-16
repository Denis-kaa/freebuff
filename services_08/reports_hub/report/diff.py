"""Diff между генерациями Reports Hub (спека §8, H4).

Сравнение предыдущей модели (`site/data/history/<slug>.json`) с текущей
посекционно: новые секции/доки, изменение числа пунктов, метрики.
Результат — бейджи в отчёте + сводка на главной.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from services_08.reports_hub.report.model import ReportModel


@dataclass(frozen=True)
class MetricChange:
    """Изменение значения метрики (label: before → after)."""

    label: str
    before: str
    after: str

    def to_json(self) -> dict[str, str]:
        """JSON-представление."""
        return {"label": self.label, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class ModelDiff:
    """Diff двух генераций отчёта одного проекта."""

    slug: str = ""
    first_generation: bool = True
    timeline_added: int = 0
    docs_added: list[str] = field(default_factory=list)
    docs_removed: list[str] = field(default_factory=list)
    metric_changes: list[MetricChange] = field(default_factory=list)
    new_sections: list[str] = field(default_factory=list)
    removed_sections: list[str] = field(default_factory=list)
    item_deltas: list[tuple[str, int, int]] = field(default_factory=list)

    def has_changes(self) -> bool:
        """Есть ли содержательные изменения."""
        return bool(
            self.timeline_added
            or self.docs_added
            or self.docs_removed
            or self.metric_changes
            or self.new_sections
            or self.removed_sections
            or any(before != after for _, before, after in self.item_deltas)
        )

    def summary(self) -> str:
        """Человеческая сводка (спека §8: «+2 этапа, тесты 249→261, 1 новый док»)."""
        if self.first_generation:
            return "первая генерация"
        parts: list[str] = []
        if self.timeline_added:
            parts.append(f"+{self.timeline_added} этапов")
        for change in self.metric_changes:
            parts.append(f"{change.label} {change.before}→{change.after}")
        if self.docs_added:
            parts.append(f"+{len(self.docs_added)} новых доков")
        if self.docs_removed:
            parts.append(f"−{len(self.docs_removed)} доков")
        for name, before, after in self.item_deltas:
            if before != after:
                delta = after - before
                sign = "+" if delta > 0 else ""
                parts.append(f"{name} {before}→{after} ({sign}{delta})")
        if self.new_sections:
            parts.append("новые секции: " + ", ".join(self.new_sections))
        if self.removed_sections:
            parts.append("убраны секции: " + ", ".join(self.removed_sections))
        return " · ".join(parts) if parts else "без изменений"

    def to_json(self) -> dict[str, object]:
        """JSON-представление (для manifest)."""
        return {
            "slug": self.slug,
            "first_generation": self.first_generation,
            "timeline_added": self.timeline_added,
            "docs_added": self.docs_added,
            "docs_removed": self.docs_removed,
            "metric_changes": [change.to_json() for change in self.metric_changes],
            "new_sections": self.new_sections,
            "removed_sections": self.removed_sections,
            "item_deltas": [list(item) for item in self.item_deltas],
            "summary": self.summary(),
        }


def diff_models(current: ReportModel, previous: ReportModel | None) -> ModelDiff:
    """Сравнить текущую модель с предыдущей (посекционно, спека §8).

    Args:
        current: только что собранная модель.
        previous: модель предыдущей генерации (None → первая генерация).

    Returns:
        ModelDiff с бейджами и сводкой.
    """
    if previous is None:
        return ModelDiff(slug=current.slug, first_generation=True)
    metric_changes: list[MetricChange] = []
    previous_metrics = {tile.label: tile.value for tile in previous.metrics}
    for tile in current.metrics:
        before = previous_metrics.get(tile.label)
        if before is not None and before != tile.value:
            metric_changes.append(MetricChange(label=tile.label, before=before, after=tile.value))
    previous_docs = {card.filename for card in previous.docs}
    current_docs = {card.filename for card in current.docs}
    previous_sections = {section.name for section in previous.sections}
    current_sections = {section.name for section in current.sections}
    previous_items = {section.name: len(section.items) for section in previous.sections}
    item_deltas: list[tuple[str, int, int]] = []
    for section in current.sections:
        before_count = previous_items.get(section.name)
        if before_count is not None and before_count != len(section.items):
            item_deltas.append((section.name, before_count, len(section.items)))
    return ModelDiff(
        slug=current.slug,
        first_generation=False,
        timeline_added=max(len(current.timeline) - len(previous.timeline), 0),
        docs_added=sorted(current_docs - previous_docs),
        docs_removed=sorted(previous_docs - current_docs),
        metric_changes=metric_changes,
        new_sections=sorted(current_sections - previous_sections),
        removed_sections=sorted(previous_sections - current_sections),
        item_deltas=item_deltas,
    )


def history_path(site_root: Path, slug: str) -> Path:
    """Путь к history-JSON проекта (спека §4.2: `site/data/history/`)."""
    from services_08.reports_hub.report.summaries import slugify

    return site_root / "data" / "history" / f"{slugify(slug)}.json"


def load_history(site_root: Path, slug: str) -> ReportModel | None:
    """Прочитать предыдущую модель (None при отсутствии/битом файле)."""
    path = history_path(site_root, slug)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        return ReportModel.from_json(payload)
    except (ValueError, TypeError):
        return None


def save_history(site_root: Path, model: ReportModel) -> Path:
    """Атомарно записать модель в history (tmp → os.replace, спека §8).

    Returns:
        Путь записанного history-файла.
    """
    path = history_path(site_root, model.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(model.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)
    return path
