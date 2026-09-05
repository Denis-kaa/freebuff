"""Phase D: deterministic grading contract and pytest runner."""

from app.grading.contract import (
    Correctness,
    EvidenceCandidate,
    ExerciseSpec,
    FailureKind,
    GradingResult,
    GradingStatus,
    SubmissionIdentity,
)
from app.grading.catalog import exercise_from_corpus
from app.grading.runner import DuplicateSubmissionError, PytestGrader

__all__ = [
    "Correctness",
    "DuplicateSubmissionError",
    "exercise_from_corpus",
    "EvidenceCandidate",
    "ExerciseSpec",
    "FailureKind",
    "GradingResult",
    "GradingStatus",
    "PytestGrader",
    "SubmissionIdentity",
***REMOVED***
