"""Stable, immutable result contract for deterministic grading.

The contract deliberately contains no quality score or mastery score. Static
metrics and learning-state updates belong to later phases and cannot leak into
this result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
***REMOVED***
from typing import Any


class GradingStatus(str, Enum):
    """Public normalized outcome categories."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


class FailureKind(str, Enum):
    """Whether an unsuccessful run belongs to the learner or the grader."""

    NONE = "none"
    STUDENT_FAILURE = "student_failure"
    GRADER_FAILURE = "grader_failure"


@dataclass(frozen=True)
class ExerciseSpec:
    """The minimum exercise boundary required by the Phase D runner."""

    exercise_id: str
    tests_path: Path
    student_filename: str
    competency_id: str | None = None

    def __post_init__(self) -> None:
        if not self.exercise_id.strip():
            raise ValueError("exercise_id must not be empty")
        if not self.student_filename or Path(self.student_filename).name != self.student_filename:
            raise ValueError("student_filename must be a plain filename")
        if self.tests_path.is_dir():
            raise ValueError("tests_path must point to a test file")


@dataclass(frozen=True)
class SubmissionIdentity:
    """Stable identity of a submitted source string."""

    submission_id: str
    exercise_id: str
    student_code_hash: str
    created_at: str

    def to_dict(self) -> dict[str, str***REMOVED***:
        return {
            "submission_id": self.submission_id,
            "exercise_id": self.exercise_id,
            "student_code_hash": self.student_code_hash,
            "created_at": self.created_at,
        ***REMOVED***


@dataclass(frozen=True)
class Correctness:
    """Test accounting independent of a learning or competency score."""

    status: str
    tests_total: int
    tests_passed: int
    tests_failed: int
    tests_error: int

    def __post_init__(self) -> None:
        if min(
            self.tests_total,
            self.tests_passed,
            self.tests_failed,
            self.tests_error,
        ) < 0:
            raise ValueError("test counts cannot be negative")
        if self.tests_passed + self.tests_failed + self.tests_error > self.tests_total:
            raise ValueError("test result counts exceed tests_total")

    def to_dict(self) -> dict[str, int | str***REMOVED***:
        return {
            "status": self.status,
            "tests_total": self.tests_total,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_error": self.tests_error,
        ***REMOVED***


@dataclass(frozen=True)
class EvidenceCandidate:
    """Candidate only; Phase D never persists it to a learning engine."""

    type: str
    competency_id: str | None
    strength: str
    metadata: tuple[tuple[str, str***REMOVED***, ...***REMOVED*** = ()

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "type": self.type,
            "competency_id": self.competency_id,
            "strength": self.strength,
            "metadata": dict(self.metadata),
        ***REMOVED***


@dataclass(frozen=True)
class GradingResult:
    """Complete normalized result returned by :class:`PytestGrader`."""

    identity: SubmissionIdentity
    status: GradingStatus
    failure_kind: FailureKind
    correctness: Correctness
    diagnostics: tuple[str, ...***REMOVED*** = ()
    patterns: tuple[str, ...***REMOVED*** = ()
    evidence_candidates: tuple[EvidenceCandidate, ...***REMOVED*** = ()

    @property
    def submission_id(self) -> str:
        return self.identity.submission_id

    @property
    def exercise_id(self) -> str:
        return self.identity.exercise_id

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            **self.identity.to_dict(),
            "status": self.status.value,
            "failure_kind": self.failure_kind.value,
            "correctness": self.correctness.to_dict(),
            "diagnostics": list(self.diagnostics),
            "patterns": list(self.patterns),
            "evidence_candidates": [
                candidate.to_dict() for candidate in self.evidence_candidates
            ***REMOVED***,
        ***REMOVED***
