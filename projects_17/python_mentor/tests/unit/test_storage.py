"""Unit-тесты SQLite schema (Phase B+C, Шаг 4, CP-4; prompt1 §22–§23).

Проверяют FK, UNIQUE, CHECK, PRAGMA foreign_keys. Hermetic: в памяти.
"""

import sqlite3

import pytest

from app.storage import connect, init_db


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", in_memory=True)
    init_db(c)
    return c


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO exercise_sources (id, source_name, repository, license,"
        " license_evidence, redistribution_allowed, modification_allowed,"
        " attribution_required, status) VALUES (?,?,?,?,?,1,1,1,?)",
        ("s1", "exercism", "exercism/python", "MIT", "evidence", "approved"),
    )
    conn.execute(
        "INSERT INTO exercises (id, source_id, exercise_type, slug, content_hash)"
        " VALUES ('s1:hello', 's1', 'practice', 'hello', 'abc')"
    )
    conn.commit()


def test_foreign_keys_pragma_on(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0***REMOVED*** == 1


def test_schema_version(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA user_version").fetchone()
    assert row[0***REMOVED*** == 1


def test_tables_exist(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {r[0***REMOVED*** for r in rows***REMOVED***
    assert names == {
        "competencies",
        "competency_prerequisites",
        "exercise_sources",
        "exercises",
        "exercise_competencies",
    ***REMOVED***, names


def test_fk_violation_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercises (id, source_id, exercise_type, slug, content_hash)"
            " VALUES ('x:y', 'no-such-source', 'practice', 'y', 'h')"
        )


def test_unique_source_slug_pair(conn: sqlite3.Connection) -> None:
    _seed(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercises (id, source_id, exercise_type, slug, content_hash)"
            " VALUES ('s1:hello2', 's1', 'practice', 'hello', 'def')"
        )


def test_check_bad_enum(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercise_sources (id, source_name, repository, license,"
            " license_evidence, status) VALUES ('x','x','x','MIT','e','weird')"
        )


def test_check_bad_rung(conn: sqlite3.Connection) -> None:
    _seed(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO exercises (id, source_id, exercise_type, slug,"
            " pedagogical_rung, content_hash)"
            " VALUES ('s1:z', 's1', 'practice', 'z', 'expert', 'h')"
        )


def test_self_prerequisite_blocked(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO competencies (id, name, description, category,"
        " understand_criteria, can_do_criteria)"
        " VALUES ('c1','C1','d','functions','u','u')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO competency_prerequisites (competency_id, prerequisite_id)"
            " VALUES ('c1', 'c1')"
        )


def test_no_future_tables(conn: sqlite3.Connection) -> None:
    """Запрещённые таблицы будущих фаз не существуют (prompt1 §35)."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND"
        " name IN ('submissions','evidence','review_states','learning_events',"
        " 'student_competencies')"
    ).fetchall()
    assert rows == [***REMOVED***