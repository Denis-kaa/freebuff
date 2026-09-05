"""Competency Map v0.1 — загрузка, валидация, coverage.

Контракт: blueprint §1. Используется Шагами 3 (map+validator), 7 (mapping),
8 (coverage report) Phase B+C.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
***REMOVED***
from typing import Any, Iterable

import yaml

REQUIRED_FIELDS = (
    "id", "name", "description", "category", "prerequisites",
    "understand_criteria", "can_do_criteria", "typical_errors",
    "verification_exercise", "project_marker", "exercism_concepts",
)
CATEGORIES = {
    "python_fundamentals", "control_flow", "collections", "functions",
    "strings", "exceptions", "modules", "oop", "files_io", "testing",
    "code_structure",
***REMOVED***


@dataclass(frozen=True)
class Competency:
    id: str
    name: str
    description: str
    category: str
    prerequisites: tuple[str, ...***REMOVED***
    understand_criteria: str
    can_do_criteria: str
    typical_errors: tuple[str, ...***REMOVED***
    verification_exercise: str
    project_marker: str
    exercism_concepts: tuple[str, ...***REMOVED***

    @classmethod
    def from_dict(cls, raw: dict) -> "Competency":
        return cls(
            id=str(raw["id"***REMOVED***),
            name=str(raw["name"***REMOVED***),
            description=str(raw["description"***REMOVED***),
            category=str(raw["category"***REMOVED***),
            prerequisites=tuple(str(x) for x in raw["prerequisites"***REMOVED***),
            understand_criteria=str(raw["understand_criteria"***REMOVED***),
            can_do_criteria=str(raw["can_do_criteria"***REMOVED***),
            typical_errors=tuple(str(x) for x in raw["typical_errors"***REMOVED***),
            verification_exercise=str(raw["verification_exercise"***REMOVED***),
            project_marker=str(raw["project_marker"***REMOVED***),
            exercism_concepts=tuple(str(x) for x in raw["exercism_concepts"***REMOVED***),
        )


@dataclass(frozen=True)
class CompetencyMap:
    version: str
    competencies: tuple[Competency, ...***REMOVED***
    unmapped_exercism_concepts: tuple[str, ...***REMOVED*** = ()

    def by_id(self) -> dict[str, Competency***REMOVED***:
        return {c.id: c for c in self.competencies***REMOVED***

    @classmethod
    def from_dict(cls, raw: dict) -> "CompetencyMap":
        return cls(
            version=str(raw.get("version", "0.0")),
            competencies=tuple(
                Competency.from_dict(c) for c in raw["competencies"***REMOVED***
            ),
            unmapped_exercism_concepts=tuple(
                str(x) for x in raw.get("unmapped_exercism_concepts", [***REMOVED***)
            ),
        )

    def mapped_concepts(self) -> set[str***REMOVED***:
        out: set[str***REMOVED*** = set()
        for c in self.competencies:
            out.update(c.exercism_concepts)
        return out


def load_competency_map(path: str | Path) -> CompetencyMap:
    """Загрузить карту из YAML (без валидации — используй validate_competency_map)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict) or "competencies" not in raw:
        raise ValueError(f"{path***REMOVED***: нет ключа 'competencies'")
    return CompetencyMap.from_dict(raw)


def validate_competency_map(cm: CompetencyMap) -> list[str***REMOVED***:
    """Вернуть список ошибок (пустой = валидно). Строгая схема, ацикличность."""
    errors: list[str***REMOVED*** = [***REMOVED***
    ids: set[str***REMOVED*** = set()
    for c in cm.competencies:
        if not c.id or c.id != c.id.strip().lower():
            errors.append(f"competency id {c.id!r***REMOVED*** должен быть lowercase без пробелов")
        if c.category not in CATEGORIES:
            errors.append(f"{c.id***REMOVED***: неизвестная category {c.category!r***REMOVED***")
        if c.id in ids:
            errors.append(f"duplicate id {c.id!r***REMOVED***")
        ids.add(c.id)
        for p in c.prerequisites:
            if p not in ids and p not in {x.id for x in cm.competencies***REMOVED***:
                errors.append(f"{c.id***REMOVED***: unknown prerequisite {p!r***REMOVED***")
    # Циклы (DFS)
    graph = {c.id: list(c.prerequisites) for c in cm.competencies***REMOVED***
    VISITING, DONE = 1, 2
    state: dict[str, int***REMOVED*** = {***REMOVED***

    def visit(node: str, path: list[str***REMOVED***) -> None:
        if state.get(node) == DONE:
            return
        if state.get(node) == VISITING:
            cycle = path[path.index(node):***REMOVED*** + [node***REMOVED***
            errors.append(f"cycle detected: {' -> '.join(cycle)***REMOVED***")
            return
        state[node***REMOVED*** = VISITING
        for dep in graph.get(node, [***REMOVED***):
            visit(dep, path + [node***REMOVED***)
        state[node***REMOVED*** = DONE

    for node in graph:
        visit(node, [***REMOVED***)
    return errors


def coverage_report(
    cm: CompetencyMap,
    available_concepts: Iterable[str***REMOVED***,
) -> dict[str, Any***REMOVED***:
    """Сколько Exercism concepts покрыто, какие нет."""
    available = set(available_concepts)
    mapped = cm.mapped_concepts()
    unmapped_explicit = set(cm.unmapped_exercism_concepts)
    covered = sorted(mapped & available)
    uncovered = sorted(available - mapped - unmapped_explicit)
    explicitly_unmapped = sorted(available & unmapped_explicit)
    return {
        "available_concepts": len(available),
        "covered_concepts": len(covered),
        "uncovered_concepts": uncovered,
        "explicitly_unmapped_concepts": explicitly_unmapped,
        "coverage_ratio": (
            round(len(covered) / len(available), 3) if available else 1.0
        ),
    ***REMOVED***


def main(argv: list[str***REMOVED*** | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:***REMOVED***
    path = argv[0***REMOVED*** if argv else "configs/competency_map.yaml"
    try:
        cm = load_competency_map(path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR load {path***REMOVED***: {exc***REMOVED***")
        return 2
    errors = validate_competency_map(cm)
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 2
    print(f"OK: {len(cm.competencies)***REMOVED*** competencies, 0 errors")
    # coverage (опционально: --concepts DIR|FILE)
    if len(argv) > 1 and argv[1***REMOVED*** == "--concepts":
        src = Path(argv[2***REMOVED***)
        if src.is_dir():
            concepts = [p.name for p in src.iterdir() if p.is_dir()***REMOVED***
        else:
            concepts = [l.strip() for l in src.read_text().splitlines() if l.strip()***REMOVED***
        rep = coverage_report(cm, concepts)
        print(f"concepts available: {rep['available_concepts'***REMOVED******REMOVED***")
        print(f"coverage: {rep['covered_concepts'***REMOVED******REMOVED*** ({rep['coverage_ratio'***REMOVED******REMOVED***)")
        uncovered: list[str***REMOVED*** = [str(x) for x in rep["uncovered_concepts"***REMOVED******REMOVED***
        if uncovered:
            print("uncovered:", ", ".join(uncovered))
        explicit: list[str***REMOVED*** = [str(x) for x in rep["explicitly_unmapped_concepts"***REMOVED******REMOVED***
        if explicit:
            print("explicitly unmapped:", ", ".join(explicit))
    return 0


if __name__ == "__main__":
    sys.exit(main())