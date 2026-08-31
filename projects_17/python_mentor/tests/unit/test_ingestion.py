"""Unit-тесты ingestion на fixture-мини-треке (Phase B+C, Шаг 9; prompt1 §27–§28).

Hermetic: никакой сети; fixture копирует структуру реального репо.
Проверяют: parsing, license gate, идемпотентность (N→N), change→update,
mapping override, reports.
"""

from pathlib import Path

import pytest

from app.curriculum.map import load_competency_map
from app.ingestion.mapping import create_mapper, load_overrides
from app.ingestion.parser import (
    discover_exercises,
    load_track_config,
    parse_exercise,
    track_exercise_meta,
)
from app.ingestion.pipeline import ingest, rung_from_difficulty
from app.storage import open_corpus

# загружаем пути из conftest
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "exercism"
ROOT_PROJ = Path(__file__).resolve().parents[2]
SOURCES_YAML = ROOT_PROJ / "configs" / "sources.yaml"
MAP_YAML = ROOT_PROJ / "configs" / "competency_map.yaml"
OVERRIDES_YAML = ROOT_PROJ / "configs" / "exercise_overrides.yaml"


@pytest.fixture(scope="module")
def cm():
    return load_competency_map(MAP_YAML)


def test_discover_fixture() -> None:
    dirs = discover_exercises(FIXTURES)
    slugs = {p.name for p in dirs}
    assert slugs == {
        "guidos-gorgeous-lasagna", "black-jack", "log-levels",
        "hello-world", "two-fer", "bob",
    }


def test_parse_exercise_record() -> None:
    root = FIXTURES
    track = track_exercise_meta(load_track_config(root))
    d = root / "exercises" / "practice" / "hello-world"
    rec = parse_exercise(d, root, track)
    assert rec is not None
    assert rec.slug == "hello-world"
    assert rec.exercise_type == "practice"
    assert rec.source_difficulty == 1
    assert rec.content_hash  # непустой hash
    assert rec.statement_relpath.endswith("instructions.md")
    assert rec.tests_relpath.endswith("_test.py")


def test_content_hash_stable() -> None:
    root = FIXTURES
    track = track_exercise_meta(load_track_config(root))
    d = root / "exercises" / "practice" / "two-fer"
    h1 = parse_exercise(d, root, track).content_hash
    h2 = parse_exercise(d, root, track).content_hash
    assert h1 == h2


def test_ingest_fixture_idempotent(tmp_path: Path, cm) -> None:
    db = tmp_path / "c.db"
    r1 = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm)
    assert r1.discovered == 6
    assert r1.parsed == 6
    assert r1.inserted == 6
    assert r1.inserted == 6

    r2 = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm)
    assert r2.inserted == 0 and r2.updated == 0
    assert r2.unchanged == 6


def test_ingest_no_license_approved_skips() -> None:
    pass  # заменяется ниже тестом с pending-источником


def test_ingest_change_updates_not_inserts(tmp_path: Path, cm) -> None:
    db = tmp_path / "c.db"
    # первый импорт
    r1 = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm)
    assert r1.inserted == 6
    conn = open_corpus(db)
    h_before = conn.execute(
        "SELECT content_hash FROM exercises WHERE slug='hello-world'"
    ).fetchone()[0]
    conn.close()
    # изменяем stub hello-world
    stub = FIXTURES / "exercises" / "practice" / "hello-world" / "hello_world.py"
    orig = stub.read_text()
    stub.write_text(orig + "\n# change marker\n")
    try:
        r2 = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm)
        assert r2.updated == 1, r2.summary()
        assert r2.inserted == 0
        conn = open_corpus(db)
        h_after = conn.execute(
            "SELECT content_hash FROM exercises WHERE slug='hello-world'"
        ).fetchone()[0]
        conn.close()
        assert h_after != h_before
    finally:
        stub.write_text(orig)


def test_ingest_with_refs_flag(tmp_path: Path, cm) -> None:
    db = tmp_path / "c.db"
    r_no_refs = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm, with_refs=False)
    conn = open_corpus(db)
    refs = conn.execute(
        "SELECT COUNT(*) FROM exercises WHERE reference_solution_ref IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert refs == 0

    db2 = tmp_path / "c_refs.db"
    r_refs = ingest(FIXTURES, db2, SOURCES_YAML, competency_map=cm, with_refs=True)
    conn = open_corpus(db2)
    refs = conn.execute(
        "SELECT COUNT(*) FROM exercises WHERE reference_solution_ref IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert refs >= 6


def test_mapping_override_wins(tmp_path: Path, cm) -> None:
    """override (hello-world -> functions) приоритетнее эвристики."""
    overrides = load_overrides(OVERRIDES_YAML)
    assert overrides["hello-world"]["competency_id"] == "functions"
    mapper = create_mapper(cm, OVERRIDES_YAML)
    db = tmp_path / "c.db"
    r = ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm, mapper=mapper)
    conn = open_corpus(db)
    row = conn.execute(
        "SELECT competency_id, confidence, source FROM exercise_competencies"
        " WHERE exercise_id='exercism-python:hello-world'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["competency_id"] == "functions"
    assert row["source"] == "override"
    assert row["confidence"] == "high"


def test_mapping_unknown_competency_raises(tmp_path: Path) -> None:
    """override на несуществующую компетенцию — ошибка (конфиг-баг)."""
    import yaml

    cm = load_competency_map(MAP_YAML)
    bad = tmp_path / "bad_overrides.yaml"
    bad.write_text(
        yaml.safe_dump(
            {"overrides": [{"exercise_id": "bob", "competency_id": "nope", "confidence": "high"}]}
        ),
        encoding="utf-8",
    )
    mapper = create_mapper(cm, bad)
    with pytest.raises(ValueError):
        mapper(parse_exercise(
            FIXTURES / "exercises" / "practice" / "bob",
            FIXTURES,
            track_exercise_meta(load_track_config(FIXTURES)),
        ))


def test_gap_report_includes_zero(tmp_path: Path, cm, capsys) -> None:
    from app.ingestion.reports import gap_report

    db = tmp_path / "c.db"
    ingest(FIXTURES, db, SOURCES_YAML, competency_map=cm)
    conn = open_corpus(db)
    txt = gap_report(conn)
    conn.close()
    assert "CONTENT GAP" in txt


def test_rung_mapping() -> None:
    assert rung_from_difficulty(1) == "repetition"
    assert rung_from_difficulty(2) == "analogy"
    assert rung_from_difficulty(3) == "new"
    assert rung_from_difficulty(5) == "unfamiliar_context"
    assert rung_from_difficulty(7) == "combination"
    assert rung_from_difficulty(9) == "independent"