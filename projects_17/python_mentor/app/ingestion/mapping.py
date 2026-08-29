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

***REMOVED***
***REMOVED***

import yaml

from app.curriculum.map import CompetencyMap
from app.ingestion.parser import ExerciseRecord

# --- blurb-эвристика (low confidence) --------------------------------
_BLURB_KEYWORDS: dict[str, tuple[str, ...***REMOVED******REMOVED*** = {
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
***REMOVED***


def load_overrides(path: str | Path) -> dict[str, dict***REMOVED***:
    """Загрузить configs/exercise_overrides.yaml -> {exercise_id: {competency_id, confidence***REMOVED******REMOVED***."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    out: dict[str, dict***REMOVED*** = {***REMOVED***
    for entry in raw.get("overrides", [***REMOVED***):
        ex_id = str(entry["exercise_id"***REMOVED***)
        if ex_id in out:
            raise ValueError(f"двойной override для упражнения {ex_id!r***REMOVED***")
        out[ex_id***REMOVED*** = {
            "competency_id": str(entry["competency_id"***REMOVED***),
            "confidence": str(entry.get("confidence", "low")),
        ***REMOVED***
    return out


def _concept_to_competency(cm: CompetencyMap) -> dict[str, list[str***REMOVED******REMOVED***:
    """concept slug -> [competency ids***REMOVED***."""
    out: dict[str, list[str***REMOVED******REMOVED*** = {***REMOVED***
    for c in cm.competencies:
        for concept in c.exercism_concepts:
            out.setdefault(concept, [***REMOVED***).append(c.id)
    return out


def _blurb_match(blurb: str) -> str | None:
    low = blurb.lower()
    for comp_id, words in _BLURB_KEYWORDS.items():
        for w in words:
            if re.search(rf"\b{w***REMOVED***\b", low):
                return comp_id
    return None


def apply_mapping(
    rec: ExerciseRecord,
    cm: CompetencyMap,
    overrides: dict[str, dict***REMOVED***,
) -> list[tuple[str, str, str***REMOVED******REMOVED***:
    """Вернуть [(competency_id, confidence, source)***REMOVED*** (0 или 1 связь)."""
    # 1) override
    if rec.slug in overrides:
        ov = overrides[rec.slug***REMOVED***
        return [(ov["competency_id"***REMOVED***, ov["confidence"***REMOVED***, "override")***REMOVED***

    # 2) rule-based по concepts
    concept_to = _concept_to_competency(cm)
    scores: dict[str, int***REMOVED*** = {***REMOVED***
    for concept in rec.source_concepts:
        for comp_id in concept_to.get(concept, [***REMOVED***):
            scores[comp_id***REMOVED*** = scores.get(comp_id, 0) + 1
    if scores:
        top = max(scores.values())
        best = sorted(c for c, s in scores.items() if s == top)[0***REMOVED***
        conf = "high" if top >= 2 else "medium"
        return [(best, conf, "rule")***REMOVED***

    # 3) blurb-эвристика (low)
    comp = _blurb_match(rec.blurb or rec.name)
    if comp is not None:
        return [(comp, "low", "rule")***REMOVED***

    # 4) unmapped
    return [***REMOVED***


def create_mapper(
    cm: CompetencyMap, overrides_path: str | Path
):
    """Фабрика Mapper для pipeline (замыкание на карту и overrides)."""
    overrides = load_overrides(overrides_path)
    by_id = cm.by_id()

    def mapper(rec: ExerciseRecord) -> list[tuple[str, str, str***REMOVED******REMOVED***:
        matches = apply_mapping(rec, cm, overrides)
        # валидируем: компетенция обязана существовать (иначе это баг конфига)
        validated: list[tuple[str, str, str***REMOVED******REMOVED*** = [***REMOVED***
        for comp_id, conf, src in matches:
            if comp_id not in by_id:
                raise ValueError(f"override мапит на несуществующую компетенцию {comp_id!r***REMOVED***")
            validated.append((comp_id, conf, src))
        return validated

    return mapper