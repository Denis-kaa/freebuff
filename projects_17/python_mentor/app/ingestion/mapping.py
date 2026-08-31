"""Competency mapping (Phase B+C, Шаг 7; prompt1 §18–§20, §31–§32).

Правила:
  1. override (configs/exercise_overrides.yaml) — абсолютный приоритет;
  2. rule-based: concepts упражнения (из track config practices/prerequisites)
     → компетенции, у которых эти concept'ы в exercism_concepts;
     confidence: high если ≥2 концепта совпали, medium если 1;
  3. эвристика по blurb (ключевые слова) — только при отсутствии правил → low;
  4. ничего не найдено → НЕ мапим (unmapped, честно, без псевдо-уверенности).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from app.curriculum.map import CompetencyMap
from app.ingestion.parser import ExerciseRecord

# --- blurb-эвристика (low confidence) --------------------------------
_BLURB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "primitive-types": ("number", "integer", "float", "numeric"),
    "lists": ("list", "array", "collection"),
    "dicts": ("dictionary", "dict", "map", "hash"),
    "strings": ("string", "text", "sentence", "word"),
    "sets": ("set", "duplicate", "unique"),
    "conditionals": ("if", "condition", "branch"),
    "loops": ("loop", "iterate", "repeat"),
    "functions": ("function", "call"),
    "classes": ("class", "object", "instance"),
    "files-io": ("file", "read", "write"),
    "exceptions": ("error", "except", "fail"),
    "testing": ("test", "suite"),
}


def load_overrides(path: str | Path) -> dict[str, dict]:
    """Загрузить configs/exercise_overrides.yaml -> {exercise_id: {competency_id, confidence]]."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    out: dict[str, dict] = {}
    for entry in raw.get("overrides", []):
        ex_id = str(entry["exercise_id"])
        if ex_id in out:
            raise ValueError(f"двойной override для упражнения {ex_id!r}")
        out[ex_id] = {
            "competency_id": str(entry["competency_id"]),
            "confidence": str(entry.get("confidence", "low")),
        }
    return out


def _concept_to_competency(cm: CompetencyMap) -> dict[str, list[str]]:
    """concept slug -> [competency ids]."""
    out: dict[str, list[str]] = {}
    for c in cm.competencies:
        for concept in c.exercism_concepts:
            out.setdefault(concept, []).append(c.id)
    return out


def _blurb_match(blurb: str) -> str | None:
    low = blurb.lower()
    for comp_id, words in _BLURB_KEYWORDS.items():
        for w in words:
            if re.search(rf"\b{w}\b", low):
                return comp_id
    return None


def apply_mapping(
    rec: ExerciseRecord,
    cm: CompetencyMap,
    overrides: dict[str, dict],
) -> list[tuple[str, str, str]]:
    """Вернуть [(competency_id, confidence, source)] (0 или 1 связь)."""
    # 1) override
    if rec.slug in overrides:
        ov = overrides[rec.slug]
        return [(ov["competency_id"], ov["confidence"], "override")]

    # 2) rule-based по concepts
    concept_to = _concept_to_competency(cm)
    scores: dict[str, int] = {}
    for concept in rec.source_concepts:
        for comp_id in concept_to.get(concept, []):
            scores[comp_id] = scores.get(comp_id, 0) + 1
    if scores:
        top = max(scores.values())
        best = sorted(c for c, s in scores.items() if s == top)[0]
        conf = "high" if top >= 2 else "medium"
        return [(best, conf, "rule")]

    # 3) blurb-эвристика (low)
    comp = _blurb_match(rec.blurb or rec.name)
    if comp is not None:
        return [(comp, "low", "rule")]

    # 4) unmapped
    return []


def create_mapper(
    cm: CompetencyMap, overrides_path: str | Path
):
    """Фабрика Mapper для pipeline (замыкание на карту и overrides)."""
    overrides = load_overrides(overrides_path)
    by_id = cm.by_id()

    def mapper(rec: ExerciseRecord) -> list[tuple[str, str, str]]:
        matches = apply_mapping(rec, cm, overrides)
        # валидируем: компетенция обязана существовать (иначе это баг конфига)
        validated: list[tuple[str, str, str]] = []
        for comp_id, conf, src in matches:
            if comp_id not in by_id:
                raise ValueError(f"override мапит на несуществующую компетенцию {comp_id!r}")
            validated.append((comp_id, conf, src))
        return validated

    return mapper