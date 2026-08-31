"""Phase D pytest runner backed by the Phase E execution boundary.

Student code always runs in a child process and a temporary workspace; the
application process never imports it. The grader uses wall-clock, CPU and
output limits. Address-space limiting remains available in the backend but is
omitted for pytest bootstrap compatibility in Termux/proot.
"""

from __future__ import annotations

import ast
import hashlib
import os
import signal
import time
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.execution import ExecutionJob, ExecutionPolicy, ExecutionStatus, TermuxSubprocessBackend
from app.grading.contract import (
    Correctness,
    EvidenceCandidate,
    ExerciseSpec,
    FailureKind,
    GradingResult,
    GradingStatus,
    SubmissionIdentity,
)


class DuplicateSubmissionError(ValueError):
    """Raised when the same exercise receives the same source twice."""


class PytestGrader:
    """Run one submission at a time with deterministic normalization."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        max_output_bytes: int = 64 * 1024,
        python_executable: str | Path | None = None,
        execution_backend: TermuxSubprocessBackend | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.python_executable = str(python_executable or sys.executable)
        self.execution_backend = execution_backend or TermuxSubprocessBackend()
        self._seen: set[tuple[str, str]] = set()

    def grade(self, exercise: ExerciseSpec, student_code: str) -> GradingResult:
        """Grade source and return a frozen, normalized result."""
        if not isinstance(student_code, str):
            raise TypeError("student_code must be str")
        code_hash = hashlib.sha256(student_code.encode("utf-8")).hexdigest()
        duplicate_key = (exercise.exercise_id, code_hash)
        if duplicate_key in self._seen:
            raise DuplicateSubmissionError(
                f"duplicate submission for {exercise.exercise_id}: {code_hash[:12]}"
            )
        self._seen.add(duplicate_key)

        identity = SubmissionIdentity(
            submission_id=self._submission_id(exercise.exercise_id, code_hash),
            exercise_id=exercise.exercise_id,
            student_code_hash=code_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            result = self._run(exercise, student_code, identity)
        except OSError as exc:
            result = self._result(
                identity,
                GradingStatus.INFRASTRUCTURE_ERROR,
                FailureKind.GRADER_FAILURE,
                Correctness("infrastructure_error", 0, 0, 0, 0),
                (f"grader process could not start: {type(exc).__name__}",),
            )
        return result

    @staticmethod
    def _submission_id(exercise_id: str, code_hash: str) -> str:
        digest = hashlib.sha256(f"{exercise_id}\0{code_hash}".encode()).hexdigest()
        return f"sub_{digest[:24]}"

    def _run(
        self,
        exercise: ExerciseSpec,
        student_code: str,
        identity: SubmissionIdentity,
    ) -> GradingResult:
        if not exercise.tests_path.is_file():
            return self._result(
                identity,
                GradingStatus.INFRASTRUCTURE_ERROR,
                FailureKind.GRADER_FAILURE,
                Correctness("infrastructure_error", 0, 0, 0, 0),
                ("exercise test file is missing",),
            )

        preflight = self._preflight(exercise, student_code, identity)
        if preflight is not None:
            return preflight

        with tempfile.TemporaryDirectory(prefix="python-mentor-grade-") as raw_dir:
            workspace = Path(raw_dir)
            student_path = workspace / exercise.student_filename
            tests_path = workspace / exercise.tests_path.name
            junit_path = workspace / "junit.xml"
            output_path = workspace / "pytest-output.log"
            student_path.write_text(student_code, encoding="utf-8")
            tests_path.write_bytes(exercise.tests_path.read_bytes())

            env = self._sanitized_environment(workspace)
            command = [
                self.python_executable,
                "-m",
                "pytest",
                "-q",
                "-s",
                "--junitxml",
                str(junit_path),
                tests_path.name,
            ]
            execution = self.execution_backend.execute(
                ExecutionJob(command=tuple(command), workspace=workspace, environment=env),
                ExecutionPolicy(
                    timeout_seconds=self.timeout_seconds,
                    max_output_bytes=self.max_output_bytes,
                    # RLIMIT_AS is disabled for pytest bootstrap in Termux/proot;
                    # the backend still supports it for direct execution jobs.
                    cpu_seconds=5,
                    address_space_bytes=None,
                ),
            )
            output = execution.stdout

            if execution.status is ExecutionStatus.TIMEOUT:
                return self._result(
                    identity,
                    GradingStatus.TIMEOUT,
                    FailureKind.STUDENT_FAILURE,
                    Correctness("timeout", 0, 0, 0, 0),
                    ("submission exceeded the grading timeout",),
                )
            if execution.status is ExecutionStatus.RESOURCE_ERROR:
                return self._result(
                    identity,
                    GradingStatus.INFRASTRUCTURE_ERROR,
                    FailureKind.GRADER_FAILURE,
                    Correctness("infrastructure_error", 0, 0, 0, 0),
                    ("execution resource limit was reached",),
                )
            if execution.status is ExecutionStatus.OUTPUT_LIMIT:
                return self._result(
                    identity,
                    GradingStatus.INFRASTRUCTURE_ERROR,
                    FailureKind.GRADER_FAILURE,
                    Correctness("infrastructure_error", 0, 0, 0, 0),
                    ("grader output limit exceeded",),
                )

            return self._normalize(
                identity,
                exercise,
                execution.returncode,
                output,
                junit_path,
            )

    def _preflight(
        self,
        exercise: ExerciseSpec,
        student_code: str,
        identity: SubmissionIdentity,
    ) -> GradingResult | None:
        """Classify deterministic parse/import failures before pytest collection."""
        try:
            student_tree = ast.parse(student_code, filename=exercise.student_filename)
        except SyntaxError:
            return self._result(
                identity,
                GradingStatus.ERROR,
                FailureKind.STUDENT_FAILURE,
                Correctness("error", 0, 0, 0, 0),
                ("student code has a syntax error",),
                evidence_candidates=(
                    EvidenceCandidate(
                        type="exercise_result",
                        competency_id=exercise.competency_id,
                        strength="weak",
                        metadata=(("grading_status", GradingStatus.ERROR.value),),
                    ),
                ),
            )

        try:
            test_tree = ast.parse(
                exercise.tests_path.read_text(encoding="utf-8"),
                filename=exercise.tests_path.name,
            )
        except (OSError, UnicodeDecodeError):
            return self._result(
                identity,
                GradingStatus.INFRASTRUCTURE_ERROR,
                FailureKind.GRADER_FAILURE,
                Correctness("infrastructure_error", 0, 0, 0, 0),
                ("exercise test file could not be read",),
            )
        except SyntaxError:
            return self._result(
                identity,
                GradingStatus.INFRASTRUCTURE_ERROR,
                FailureKind.GRADER_FAILURE,
                Correctness("infrastructure_error", 0, 0, 0, 0),
                ("exercise test file has a syntax error",),
            )

        student_module = Path(exercise.student_filename).stem
        imported_names = {
            alias.name
            for node in ast.walk(test_tree)
            if isinstance(node, ast.ImportFrom) and node.module == student_module
            for alias in node.names
            if alias.name != "*"
        }
        defined_names = {
            node.name
            for node in student_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        missing = sorted(imported_names - defined_names)
        if missing:
            return self._result(
                identity,
                GradingStatus.ERROR,
                FailureKind.STUDENT_FAILURE,
                Correctness("error", 0, 0, 0, 0),
                ("student module is missing required names",),
                evidence_candidates=(
                    EvidenceCandidate(
                        type="exercise_result",
                        competency_id=exercise.competency_id,
                        strength="weak",
                        metadata=(("grading_status", GradingStatus.ERROR.value),),
                    ),
                ),
            )
        return None

    @staticmethod
    def _sanitized_environment(workspace: Path) -> dict[str, str]:
        allowed = {"PATH", "LANG", "LC_ALL", "TZ"}
        env = {key: value for key, value in os.environ.items() if key in allowed}
        env.update(
            {
                "HOME": str(workspace),
                "TMPDIR": str(workspace),
                "TEMP": str(workspace),
                "TMP": str(workspace),
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            }
        )
        return env

    def _normalize(
        self,
        identity: SubmissionIdentity,
        exercise: ExerciseSpec,
        returncode: int | None,
        output: str,
        junit_path: Path,
    ) -> GradingResult:
        total, passed, failed, errors = _parse_junit(junit_path)
        if returncode == 0:
            status = GradingStatus.PASS
            kind = FailureKind.NONE
            diagnostics: tuple[str, ...] = ()
        elif returncode == 1 and failed > 0:
            status = GradingStatus.FAIL
            kind = FailureKind.STUDENT_FAILURE
            diagnostics = ("one or more exercise assertions failed",)
        elif returncode == 1 and _is_student_error(
            output, exercise.student_filename, exercise.tests_path.name
        ):
            status = GradingStatus.ERROR
            kind = FailureKind.STUDENT_FAILURE
            diagnostics = ("student code raised an error during grading",)
        elif returncode == 5 or (returncode == 1 and total == 0):
            status = GradingStatus.INFRASTRUCTURE_ERROR
            kind = FailureKind.GRADER_FAILURE
            diagnostics = ("exercise produced no runnable tests",)
        else:
            status = GradingStatus.INFRASTRUCTURE_ERROR
            kind = FailureKind.GRADER_FAILURE
            diagnostics = ("grader or exercise test infrastructure failed",)

        correctness_status = {
            GradingStatus.PASS: "passed",
            GradingStatus.FAIL: "failed",
            GradingStatus.ERROR: "error",
            GradingStatus.TIMEOUT: "timeout",
            GradingStatus.INFRASTRUCTURE_ERROR: "infrastructure_error",
        }[status]
        candidates: tuple[EvidenceCandidate, ...] = ()
        if status in (GradingStatus.PASS, GradingStatus.FAIL, GradingStatus.ERROR):
            strength = "strong" if status is GradingStatus.PASS else "weak"
            candidates = (
                EvidenceCandidate(
                    type="exercise_result",
                    competency_id=exercise.competency_id,
                    strength=strength,
                    metadata=(("grading_status", status.value),),
                ),
            )
        return self._result(
            identity,
            status,
            kind,
            Correctness(correctness_status, total, passed, failed, errors),
            diagnostics,
            evidence_candidates=candidates,
        )

    @staticmethod
    def _result(
        identity: SubmissionIdentity,
        status: GradingStatus,
        failure_kind: FailureKind,
        correctness: Correctness,
        diagnostics: Iterable[str],
        *,
        evidence_candidates: tuple[EvidenceCandidate, ...] = (),
    ) -> GradingResult:
        return GradingResult(
            identity=identity,
            status=status,
            failure_kind=failure_kind,
            correctness=correctness,
            diagnostics=tuple(diagnostics),
            evidence_candidates=evidence_candidates,
        )


def _parse_junit(path: Path) -> tuple[int, int, int, int]:
    if not path.is_file():
        return 0, 0, 0, 0
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0, 0, 0, 0
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    total = passed = failed = errors = 0
    for suite in suites:
        for case in suite.findall("testcase"):
            total += 1
            if case.find("failure") is not None:
                failed += 1
            elif case.find("error") is not None:
                errors += 1
            else:
                passed += 1
    return total, passed, failed, errors


def _is_student_error(output: str, student_filename: str, tests_filename: str) -> bool:
    """Recognize collection/runtime errors caused by student code only."""
    if student_filename not in output:
        return False
    if tests_filename in output and output.rfind(tests_filename) > output.rfind(student_filename):
        # A traceback ending in the test file is a grader/test fixture error.
        return False
    return any(
        marker in output
        for marker in (
            "ImportError",
            "ModuleNotFoundError",
            "SyntaxError",
            "NameError",
            "RuntimeError",
            "Traceback",
        )
    )
