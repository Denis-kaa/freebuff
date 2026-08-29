"""Unit-тесты license gate (Phase B+C, Шаг 5, CP-5; prompt1 §11–§13)."""

import pytest

from app.ingestion.license import (
    ExerciseSource,
    can_be_live,
    load_sources,
    register_sources,
)
from app.storage import connect, init_db
***REMOVED***

ROOT = Path(__file__).resolve().parents[2***REMOVED***
SOURCES_YAML = ROOT / "configs" / "sources.yaml"


@pytest.fixture()
def conn():
    c = connect(":memory:", in_memory=True)
    init_db(c)
    return c


def _src(**over) -> ExerciseSource:
    base = dict(
        id="t", source_name="T", repository="r", source_url="",
        license="MIT", license_evidence="evidence", redistribution_allowed=True,
        modification_allowed=True, attribution_required=True, status="approved",
    )
    base.update(over)
    return ExerciseSource.from_dict(base)


def test_only_approved_is_live() -> None:
    assert can_be_live("approved") is True
    assert can_be_live("pending") is False
    assert can_be_live("rejected") is False


def test_approved_requires_evidence() -> None:
    with pytest.raises(ValueError):
        _src(status="approved", license_evidence="")


def test_pending_with_evidence_is_still_not_live() -> None:
    s = _src(status="pending", license_evidence="некий evidence")
    assert can_be_live(s.status) is False


def test_load_sources_yaml() -> None:
    sources = load_sources(SOURCES_YAML)
    assert len(sources) == 1
    s = sources[0***REMOVED***
    assert s.id == "exercism-python"
    assert s.status == "approved"
    assert s.license == "MIT"
    assert "1f6aab8667bf" in s.license_evidence


def test_register_and_live(conn) -> None:
    s = load_sources(SOURCES_YAML)
    register_sources(conn, s)
    row = conn.execute(
        "SELECT status, license FROM exercise_sources WHERE id='exercism-python'"
    ).fetchone()
    assert row is not None
    assert can_be_live(row["status"***REMOVED***) is True


def test_pending_source_not_in_live(conn) -> None:
    s = _src(id="other", status="pending", license_evidence="ev")
    register_sources(conn, [s***REMOVED***)
    assert can_be_live("pending") is False