"""SQLite storage (Phase B+C, Шаги 4–6).

Схема v0.1 — 5 таблиц (prompt1 §22–§23):
  competencies, competency_prerequisites, exercise_sources,
  exercises, exercise_competencies

Инварианты: PRAGMA foreign_keys=ON; UNIQUE; CHECK на enum-поля;
user_version для миграций. НЕ создаём таблицы будущих фаз
(submissions, evidence, review_states, learning_events, student_competencies).
"""

from __future__ import annotations

import sqlite3
}

SCHEMA_VERSION = 1

_LEGACY_DROP = ""  # аддитивная миграция: без DROP

SCHEMA_SQL = f"""
PRAGMA user_version = {SCHEMA_VERSION};

CREATE TABLE IF NOT EXISTS competencies (
    id                      TEXT PRIMARY KEY,
    name                    TEXT NOT NULL,
    description             TEXT NOT NULL,
    category                TEXT NOT NULL CHECK (category IN
        ('python_fundamentals','control_flow','collections','functions',
         'strings','exceptions','modules','oop','files_io','testing',
         'code_structure')),
    understand_criteria     TEXT NOT NULL,
    can_do_criteria         TEXT NOT NULL,
    typical_errors_json     TEXT NOT NULL DEFAULT '[]',
    verification_exercise   TEXT NOT NULL DEFAULT '',
    project_marker          TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS competency_prerequisites (
    competency_id    TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    prerequisite_id  TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    PRIMARY KEY (competency_id, prerequisite_id),
    CHECK (competency_id != prerequisite_id)
);

CREATE TABLE IF NOT EXISTS exercise_sources (
    id                      TEXT PRIMARY KEY,          -- напр. 'exercism-python'
    source_name             TEXT NOT NULL,
    repository              TEXT NOT NULL,
    source_url              TEXT NOT NULL DEFAULT '',
    license                 TEXT NOT NULL,
    license_evidence        TEXT NOT NULL,
    redistribution_allowed  INTEGER NOT NULL DEFAULT 0 CHECK (redistribution_allowed IN (0, 1)),
    modification_allowed    INTEGER NOT NULL DEFAULT 0 CHECK (modification_allowed IN (0, 1)),
    attribution_required    INTEGER NOT NULL DEFAULT 1 CHECK (attribution_required IN (0, 1)),
    status                  TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
    imported_at             TEXT,
    content_hash            TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id                     TEXT PRIMARY KEY,           -- 'exercism-python:hello-world'
    source_id              TEXT NOT NULL REFERENCES exercise_sources(id),
    exercise_type          TEXT NOT NULL CHECK (exercise_type IN ('concept','practice')),
    slug                   TEXT NOT NULL,
    name                   TEXT NOT NULL DEFAULT '',
    blurb                  TEXT NOT NULL DEFAULT '',
    source_difficulty      INTEGER NOT NULL DEFAULT 1,
    pedagogical_rung       TEXT NOT NULL DEFAULT 'repetition' CHECK (pedagogical_rung IN
        ('repetition','analogy','new','unfamiliar_context','combination','independent')),
    statement_relpath      TEXT,
    tests_relpath          TEXT,
    stub_relpath           TEXT,
    reference_solution_ref TEXT,
    source_url             TEXT NOT NULL DEFAULT '',
    content_hash           TEXT NOT NULL,
    UNIQUE (source_id, slug)
);

CREATE TABLE IF NOT EXISTS exercise_competencies (
    exercise_id   TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    competency_id TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    confidence    TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
    source        TEXT NOT NULL DEFAULT 'rule',        -- 'rule' | 'override'
    PRIMARY KEY (exercise_id, competency_id)
);

CREATE INDEX IF NOT EXISTS idx_exercises_source ON exercises(source_id);
CREATE INDEX IF NOT EXISTS idx_exercises_type ON exercises(exercise_type);
CREATE INDEX IF NOT EXISTS idx_ex_comp_competency ON exercise_competencies(competency_id);
CREATE INDEX IF NOT EXISTS idx_prereq_prereq ON competency_prerequisites(prerequisite_id);
"""


def connect(db_path: str | Path, *, in_memory: bool = False) -> sqlite3.Connection:
    """Открыть соединение с включённым foreign_keys (обязательно для тестов)."""
    if in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Создать схему v0.1 (идемпотентно)."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def open_corpus(db_path: str | Path) -> sqlite3.Connection:
    """Открыть (при необходимости создать) corpus SQLite с полной схемой."""
    conn = connect(db_path)
    init_db(conn)
    return conn