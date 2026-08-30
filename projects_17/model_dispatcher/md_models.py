"""md_models.py — выбор модели freebuff «по убыванию мощности» (081_19_model_dispatcher).

Читает дамп стартового экрана freebuff (tmux capture-pane) и определяет,
какая из мощных моделей ДОСТУПНА (квота не израсходована). Выбирает
ПЕРВУЮ доступную по приоритету из config.yaml:
    glm-5.2 → mimo-2.5-pro → minimax-m3 → deepseek-v4-flash (free fallback).

Эвристика детекта (без гарантий точного layout TUI, версия 0.0.128):
  - строка модели — строка экрана, содержащая ВСЕ keywords модели
    (регистронезависимо);
  - позиция (position) — 0-based индекс строки среди обнаруженных строк
    моделей (0 = рекомендованная / курсор уже на ней, как в monitor.sh);
  - доступность — в строке НЕТ ни одного unavailable_marker
    (маркеры израсходованной квоты);
  - free_fallback — последняя модель приоритета, всегда доступна
    (позиция 0 = рекомендованная бесплатная).

Функции чистые и тестируемые без реального freebuff.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# ── Data model ────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelEntry:
    """Строка модели, обнаруженная на стартовом экране."""

    name: str
    keywords: tuple[str, ...]
    position: int            # 0-based индекс в списке моделей на экране
    available: bool
    free_fallback: bool = False


@dataclass(frozen=True)
class ModelSelection:
    """Результат выбора: модель + позиция для навигации ArrowDown ×N + Enter."""

    name: str
    position: int            # 0 = ничего не нажимать (рекомендованная)
    source: str              # "detected" | "fallback"
    reason: str = ""


# ── Parsing ───────────────────────────────────────────────────

def parse_screen(
    screen_text: str,
    models_priority: List[Dict[str, Any]],
    unavailable_markers: List[str],
) -> List[ModelEntry]:
    """Разбирает дамп стартового экрана в список ModelEntry.

    Args:
        screen_text: дамп tmux capture-pane (можно с ANSI-мусором — ищем
            только подстроки в нижнем регистре).
        models_priority: список моделей из config.yaml `models.priority`,
            каждая: {name, keywords: [...], free_fallback?}.
        unavailable_markers: маркеры недоступности из config.yaml
            `models.unavailable_markers`.

    Returns:
        Список ModelEntry в порядке появления на экране (позиции 0..N).
    """
    if not screen_text:
        return []
    lines = [ln.strip().lower() for ln in screen_text.splitlines()]

    # Строка модели: все keywords модели есть в строке.
    rows: List[Dict[str, Any]] = []   # {model, line, row_index}
    for model_cfg in models_priority:
        name = str(model_cfg.get("name", "?")).strip()
        keywords = tuple(str(k).lower() for k in model_cfg.get("keywords", []))
        if not keywords:
            continue
        for i, line in enumerate(lines):
            if all(k in line for k in keywords):
                rows.append({
                    "model": name,
                    "keywords": keywords,
                    "line": line,
                    "row": i,
                    "free_fallback": bool(model_cfg.get("free_fallback", False)),
                })

    # Дедикация: одна строка может матчить несколько моделей (glm + 5.2).
    # Берём самую конкретную (больше keywords) на строку; строки сортируем
    # по порядку появления.
    unique: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        row_idx = r["row"]
        if row_idx not in unique or len(r["keywords"]) > len(unique[row_idx]["keywords"]):
            unique[row_idx] = r

    entries: List[ModelEntry] = []
    for position, (row_idx, r) in enumerate(sorted(unique.items())):
        available = not any(m in r["line"] for m in unavailable_markers)
        entries.append(ModelEntry(
            name=r["model"],
            keywords=r["keywords"],
            position=position,
            available=available,
            free_fallback=r["free_fallback"],
        ))
    return entries


def pick_model(
    entries: List[ModelEntry],
    models_priority: List[Dict[str, Any]],
) -> ModelSelection:
    """Выбирает ПЕРВУЮ доступную модель по приоритету (по убыванию мощности).

    Порядок:
      1. Для каждой модели приоритета ищем entry с совпадающим name;
         если она доступна → выбираем её (free_fallback всегда доступна).
      2. Если ничего не обнаружено/не доступно — fallback на free-модель:
         последняя в приоритете (free_fallback=True), позиция 0
         (рекомендованная бесплатная, курсор уже на ней).

    Args:
        entries: результат parse_screen (может быть пустым — экран ещё не
            отрисован или layout не распознан).
        models_priority: конфиг `models.priority`.

    Returns:
        ModelSelection.
    """
    for model_cfg in models_priority:
        name = str(model_cfg.get("name", "")).strip()
        if not name:
            continue
        for e in entries:
            if e.name != name:
                continue
            if not _row_available(e):
                continue
            return ModelSelection(
                name=e.name,
                position=e.position,
                source="detected",
                reason=f"доступна на экране (позиция {e.position})",
            )

    # Fallback: free-модель из приоритета (позиция 0 = рекомендованная).
    for model_cfg in reversed(models_priority):
        if model_cfg.get("free_fallback"):
            return ModelSelection(
                name=str(model_cfg.get("name", "free")),
                position=0,
                source="fallback",
                reason="мощные модели недоступны/не распознаны — берём бесплатную",
            )

    # Без free_fallback в конфиге: позиция 0, первая модель приоритета.
    if models_priority:
        return ModelSelection(
            name=str(models_priority[0].get("name", "auto")),
            position=0,
            source="fallback",
            reason="конфиг без free_fallback — позиция 0 (рекомендованная)",
        )

    return ModelSelection(name="auto", position=0, source="fallback", reason="нет моделей в конфиге")


def _row_available(entry: ModelEntry) -> bool:
    """Доступность entry: free_fallback всегда доступна, иначе `available`."""
    if entry.free_fallback:
        return True
    return entry.available
