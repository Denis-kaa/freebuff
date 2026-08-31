"""Bridge from the Phase B+C corpus registry to the Phase D grader."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.grading.contract import ExerciseSpec


def exercise_from_corpus(
    conn: sqlite3.Connection,
    source_root: str | Path,
    exercise_id: str,
) -> ExerciseSpec:
    """Load one live exercise without copying corpus business rules into Grader."""
    row = conn.execute(
        """
        SELECT e.id, e.tests_relpath, e.stub_relpath, e.source_id,
               s.status
        FROM exercises AS e
        JOIN exercise_sources AS s ON s.id = e.source_id
        WHERE e.id = ?
        """,
        (exercise_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"exercise not found: {exercise_id}")
    if row["status"] != "approved":
        raise ValueError(f"exercise source is not approved: {exercise_id}")
    if not row["tests_relpath"] or not row["stub_relpath"]:
        raise ValueError(f"exercise has incomplete test/stub references: {exercise_id}")

    root = Path(source_root).resolve()
    tests_path = _contained_path(root, root / row["tests_relpath"])
    student_filename = Path(row["stub_relpath"]).name
    return ExerciseSpec(
        exercise_id=str(row["id"]),
        tests_path=tests_path,
        student_filename=student_filename,
    )


def _contained_path(root: Path, candidate: Path) -> Path:
    """Prevent a malformed registry path from escaping the source root."""
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("exercise path escapes source root") from exc
    return resolved
