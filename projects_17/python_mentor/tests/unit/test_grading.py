"""Phase D tests: contract, student failures, and grader failures."""

from dataclasses import FrozenInstanceError
import time

import pytest

from app.grading.catalog import exercise_from_corpus
from app.grading.contract import (
    ExerciseSpec,
    FailureKind,
    GradingStatus,
)
from app.grading.runner import DuplicateSubmissionError, PytestGrader
from app.ingestion.pipeline import ingest
from app.storage import open_corpus

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "exercism"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES_YAML = PROJECT_ROOT / "configs" / "sources.yaml"


def make_exercise(tmp_path: Path, test_source: str) -> ExerciseSpec:
    tests = tmp_path / "exercise_tests.py"
    tests.write_text(test_source, encoding="utf-8")
    return ExerciseSpec(
        exercise_id="fixture:basic",
        tests_path=tests,
        student_filename="student.py",
        competency_id="functions",
    )


def test_passing_submission_has_normalized_counts_and_candidate(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import add


def test_one():
    assert add(1, 2) == 3


def test_two():
    assert add(-1, 1) == 0
""",
    )
    result = PytestGrader().grade(exercise, "def add(a, b):\n    return a + b\n")

    assert result.status is GradingStatus.PASS
    assert result.failure_kind is FailureKind.NONE
    assert result.correctness.to_dict() == {
        "status": "passed",
        "tests_total": 2,
        "tests_passed": 2,
        "tests_failed": 0,
        "tests_error": 0,
    }
    assert result.evidence_candidates[0].type == "exercise_result"
    assert result.evidence_candidates[0].competency_id == "functions"
    assert "quality" not in result.to_dict()


def test_partial_result_preserves_multiple_failed_tests(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import value


def test_pass():
    assert value(1) == 1


def test_fail_one():
    assert value(2) == 99


def test_fail_two():
    assert value(3) == 99
""",
    )
    result = PytestGrader().grade(exercise, "def value(number):\n    return number\n")

    assert result.status is GradingStatus.FAIL
    assert result.failure_kind is FailureKind.STUDENT_FAILURE
    assert result.correctness.tests_total == 3
    assert result.correctness.tests_passed == 1
    assert result.correctness.tests_failed == 2
    assert result.correctness.tests_error == 0


def test_student_syntax_error_is_error_not_infrastructure(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import value


def test_value():
    assert value() == 1
""",
    )
    result = PytestGrader().grade(exercise, "def value(:\n    return 1\n")

    assert result.status is GradingStatus.ERROR
    assert result.failure_kind is FailureKind.STUDENT_FAILURE
    assert result.correctness.status == "error"
    assert result.evidence_candidates


def test_student_import_error_is_error_not_infrastructure(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student ]quired_function


def test_required_function():
    assert required_function() == 1
""",
    )
    result = PytestGrader().grade(exercise, "def other_function():\n    return 1\n")

    assert result.status is GradingStatus.ERROR
    assert result.failure_kind is FailureKind.STUDENT_FAILURE


def test_timeout_is_student_failure_and_process_is_stopped(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import wait


def test_wait():
    assert wait() == 1
""",
    )
    result = PytestGrader(timeout_seconds=0.25).grade(
        exercise,
        "import time\n\ndef wait():\n    while True:\n        time.sleep(0.01)\n",
    )

    assert result.status is GradingStatus.TIMEOUT
    assert result.failure_kind is FailureKind.STUDENT_FAILURE
    assert result.correctness.tests_total == 0


def test_malformed_exercise_is_grader_failure(tmp_path: Path) -> None:
    exercise = make_exercise(tmp_path, "def test_broken(:\n    pass\n")
    result = PytestGrader().grade(exercise, "def anything():\n    return None\n")

    assert result.status is GradingStatus.INFRASTRUCTURE_ERROR
    assert result.failure_kind is FailureKind.GRADER_FAILURE
    assert result.evidence_candidates == ()


def test_missing_test_file_is_grader_failure(tmp_path: Path) -> None:
    exercise = ExerciseSpec(
        exercise_id="fixture:missing",
        tests_path=tmp_path / "missing.py",
        student_filename="student.py",
    )
    result = PytestGrader().grade(exercise, "pass\n")

    assert result.status is GradingStatus.INFRASTRUCTURE_ERROR
    assert result.failure_kind is FailureKind.GRADER_FAILURE
    assert result.correctness.tests_total == 0


def test_output_limit_is_grader_failure(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import spam


def test_spam():
    spam()
""",
    )
    result = PytestGrader(max_output_bytes=256).grade(
        exercise,
        "def spam():\n    print('x' * 100000)\n",
    )

    assert result.status is GradingStatus.INFRASTRUCTURE_ERROR
    assert result.failure_kind is FailureKind.GRADER_FAILURE


def test_duplicate_submission_is_rejected_before_second_run(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import value


def test_value():
    assert value() == 1
""",
    )
    grader = PytestGrader()
    code = "def value():\n    return 1\n"
    first = grader.grade(exercise, code)

    with pytest.raises(DuplicateSubmissionError):
        grader.grade(exercise, code)
    assert first.status is GradingStatus.PASS


def test_identity_is_stable_for_same_code_and_exercise(tmp_path: Path) -> None:
    exercise = make_exercise(
        tmp_path,
        """
from student import value


def test_value():
    assert value() == 1
""",
    )
    code = "def value():\n    return 1\n"
    first = PytestGrader().grade(exercise, code)
    second = PytestGrader().grade(exercise, code)

    assert first.submission_id == second.submission_id
    assert first.identity.student_code_hash == second.identity.student_code_hash
    assert first.correctness == second.correctness


def test_catalog_resolves_approved_ingested_exercise(tmp_path: Path) -> None:
    from app.curriculum.map import load_competency_map

    db = tmp_path / "corpus.db"
    competency_map = load_competency_map(PROJECT_ROOT / "configs" / "competency_map.yaml")
    ingest(FIXTURES, db, SOURCES_YAML, competency_map=competency_map)
    conn = open_corpus(db)
    try:
        exercise = exercise_from_corpus(
            conn,
            FIXTURES,
            "exercism-python:hello-world",
        )
    finally:
        conn.close()

    assert exercise.tests_path.name == "hello_world_test.py"
    assert exercise.student_filename == "hello_world.py"
    result = PytestGrader().grade(
        exercise,
        "def hello():\n    return 'Hello, World!'\n",
    )
    assert result.status is GradingStatus.PASS


def test_catalog_rejects_unapproved_source(tmp_path: Path) -> None:
    from app.curriculum.map import load_competency_map

    db = tmp_path / "corpus.db"
    competency_map = load_competency_map(PROJECT_ROOT / "configs" / "competency_map.yaml")
    ingest(FIXTURES, db, SOURCES_YAML, competency_map=competency_map)
    conn = open_corpus(db)
    conn.execute("UPDATE exercise_sources SET status='pending' WHERE id='exercism-python'")
    conn.commit()
    try:
        with pytest.raises(ValueError, match="not approved"):
            exercise_from_corpus(conn, FIXTURES, "exercism-python:hello-world")
    finally:
        conn.close()


def test_contract_is_immutable(tmp_path: Path) -> None:
    exercise = make_exercise(tmp_path, "def test_ok():\n    assert True\n")
    result = PytestGrader().grade(exercise, "pass\n")

    with pytest.raises(FrozenInstanceError):
        result.status = GradingStatus.FAIL  # type: ignore[misc]
