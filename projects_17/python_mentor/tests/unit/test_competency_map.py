"""Unit-тесты Competency Map (Phase B+C, Шаг 3; prompt1 §27).

Проверяют: загрузку, уникальность id, обязательные поля, валидность
prerequisites, ацикличность (цикл → ошибка), coverage по Exercism concepts.
Hermetic: только локальные файлы.
"""

***REMOVED***

import pytest
import yaml

from app.curriculum.map import (
    CompetencyMap,
    coverage_report,
    load_competency_map,
    validate_competency_map,
)

ROOT = Path(__file__).resolve().parents[2***REMOVED***
MAP_PATH = ROOT / "configs" / "competency_map.yaml"


@pytest.fixture(scope="module")
def cm() -> CompetencyMap:
    return load_competency_map(MAP_PATH)


def test_load_valid_map(cm: CompetencyMap) -> None:
    assert len(cm.competencies) >= 15 and len(cm.competencies) <= 25, (
        f"§6: 15–25 компетенций, получено {len(cm.competencies)***REMOVED***"
    )
    assert cm.version == "0.1"


def test_validate_ok(cm: CompetencyMap) -> None:
    assert validate_competency_map(cm) == [***REMOVED***


def test_unique_ids(cm: CompetencyMap) -> None:
    ids = [c.id for c in cm.competencies***REMOVED***
    assert len(ids) == len(set(ids))


def test_all_categories_used(cm: CompetencyMap) -> None:
    cats = {c.category for c in cm.competencies***REMOVED***
    # 11 групп из §6 — должны быть все
    assert cats == {
        "python_fundamentals", "control_flow", "collections", "functions",
        "strings", "exceptions", "modules", "oop", "files_io", "testing",
        "code_structure",
    ***REMOVED***


def _mutate(tmp_path: Path, patch):
    raw = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))
    patch(raw)
    p = tmp_path / "map.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return CompetencyMap.from_dict(yaml.safe_load(p.read_text()))


def test_cycle_detected(tmp_path: Path) -> None:
    def patch(raw):
        for c in raw["competencies"***REMOVED***:
            if c["id"***REMOVED*** == "variables":
                c["prerequisites"***REMOVED*** = ["primitive-types"***REMOVED***  # идёт обратно

    cm = _mutate(tmp_path, patch)
    errors = validate_competency_map(cm)
    assert any("cycle" in e for e in errors)


def test_unknown_prerequisite_detected(tmp_path: Path) -> None:
    def patch(raw):
        raw["competencies"***REMOVED***[0***REMOVED***["prerequisites"***REMOVED*** = ["no-such-comp"***REMOVED***

    cm = _mutate(tmp_path, patch)
    errors = validate_competency_map(cm)
    assert any("unknown prerequisite" in e for e in errors)


def test_duplicate_id_detected(tmp_path: Path) -> None:
    def patch(raw):
        raw["competencies"***REMOVED***.append(dict(raw["competencies"***REMOVED***[0***REMOVED***))

    cm = _mutate(tmp_path, patch)
    errors = validate_competency_map(cm)
    assert any("duplicate id" in e for e in errors)


def test_bad_category_detected(tmp_path: Path) -> None:
    def patch(raw):
        raw["competencies"***REMOVED***[0***REMOVED***["category"***REMOVED*** = "unicorns"

    cm = _mutate(tmp_path, patch)
    errors = validate_competency_map(cm)
    assert any("category" in e for e in errors)


def test_coverage_no_holes(cm: CompetencyMap) -> None:
    """Каждый concept из 67: либо покрыт, либо в явном unmapped списке."""
    concepts_dir = ROOT / "data" / "exercism_src" / "concepts"
    if not concepts_dir.is_dir():
        pytest.skip("клон не загружен — coverage-тест пропущен")
    available = [p.name for p in concepts_dir.iterdir() if p.is_dir()***REMOVED***
    rep = coverage_report(cm, available)
    assert rep["uncovered_concepts"***REMOVED*** == [***REMOVED***, rep["uncovered_concepts"***REMOVED***
    assert rep["covered_concepts"***REMOVED*** + len(rep["explicitly_unmapped_concepts"***REMOVED***) == len(
        available
    )
    assert rep["covered_concepts"***REMOVED*** >= 40


def test_mapped_concepts_are_real_slugs(cm: CompetencyMap) -> None:
    concepts_dir = ROOT / "data" / "exercism_src" / "concepts"
    if not concepts_dir.is_dir():
        pytest.skip("клон не загружен")
    available = {p.name for p in concepts_dir.iterdir() if p.is_dir()***REMOVED***
    mapped = cm.mapped_concepts()
    unknown = mapped - available
    assert not unknown, f"маппинг ссылается на несуществующие концепты: {unknown***REMOVED***"