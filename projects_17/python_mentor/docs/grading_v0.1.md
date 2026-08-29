# Phase D — Grading v0.1

## Boundary

Phase D grades one student submission against one approved exercise. The flow is:

```text
ExerciseSpec + student source
  -> temporary workspace
  -> child-process pytest
  -> JUnit XML
  -> normalized GradingResult
  -> evidence candidate only
```

Student code is never imported into the application process. `exercise_from_corpus()` accepts only an exercise whose source registry status is `approved` and rejects paths that escape the source checkout.

## Result contract

`GradingResult` is immutable and contains:

- `SubmissionIdentity`: `submission_id`, `exercise_id`, SHA-256 `student_code_hash`, UTC `created_at`;
- `status`: `PASS`, `FAIL`, `ERROR`, `TIMEOUT`, or `INFRASTRUCTURE_ERROR`;
- `failure_kind`: `none`, `student_failure`, or `grader_failure`;
- `correctness`: status and total/passed/failed/error test counts;
- normalized diagnostics and optional patterns;
- `evidence_candidates`, which are not persisted by Phase D.

There is intentionally no quality score, maintainability score, or competency score. Static metrics and correctness counts cannot directly mutate learning state.

## MVP execution limits

The runner uses a temporary directory, sanitized environment, process-group cleanup, a wall-clock timeout, and a bounded output file. This is a local grading boundary only. It is not the hardened sandbox planned for Phase E and does not promise OS-level network isolation or public multi-user security.

The same `(exercise_id, student_code_hash)` is rejected as a duplicate by one `PytestGrader` instance. Repeated source has a stable submission ID before the duplicate is rejected.

## Verification

`tests/unit/test_grading.py` covers passing, partial and multiple failures, syntax/import errors, timeout, output limit, malformed/missing exercise tests, duplicate submissions, stable identity, immutability, and student-vs-grader failure separation.
