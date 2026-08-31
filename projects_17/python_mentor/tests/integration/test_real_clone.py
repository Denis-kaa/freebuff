"""Integration-тест на реальном клоне exercism/python (Phase B+C, Шаг 9).

Не выполняется по умолчанию: python -m pytest -m integration.
Требует локального клона data/exercism_src (см. RUNNABLE).
"""

from pathlib import Path

import pytest

from app.curriculum.map import load_competency_map
from app.ingestion.mapping import create_mapper
from app.ingestion.parser import discover_exercises
from app.ingestion.pipeline import ingest
from app.storage import open_corpus

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "exercism_src"
SOURCES = ROOT / "configs" / "sources.yaml"
MAP = ROOT / "configs" / "competency_map.yaml"
OVERRIDES = ROOT / "configs" / "exercise_overrides.yaml"


@pytest.fixture(scope="module")
def real_clone() -> Path:
    if not (SRC / "config.json").exists():
        pytest.skip("нет локального клона — запусти: git clone --depth 1 https://github.com/exercism/python data/exercism_src")
    return SRC


def test_real_clone_shape(real_clone: Path) -> None:
    assert (real_clone / "LICENSE").exists()
    practice = (real_clone / "exercises" / "practice").iterdir()
    assert len(list(practice)) >= 100


def test_real_canary_ingest(tmp_path: Path, real_clone: Path) -> None:
    """Canary: небольшой срез реального корпуса, идемпотентность N→N."""
    subsets = []
    for group in ("concept", "practice"):
        d = real_clone / "exercises" / group
        subsets.append((group, sorted(p.name for p in d.iterdir() if p.is_dir())[:10]))
    # через pipeline на полном корпусе (без сети это быстро — 161 записей)
    db = tmp_path / "canary.db"
    cm = load_competency_map(MAP)
    mapper = create_mapper(cm, OVERRIDES)
    r1 = ingest(real_clone, db, SOURCES, competency_map=cm, mapper=mapper)
    assert r1.discovered == r1.parsed >= 140
    assert r1.errors == []
    r2 = ingest(real_clone, db, SOURCES, competency_map=cm, mapper=mapper)
    assert r2.inserted == 0 and r2.updated == 0
    assert r2.unchanged == r1.inserted
    conn = open_corpus(db)
    n = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    conn.close()
    assert n == r1.inserted