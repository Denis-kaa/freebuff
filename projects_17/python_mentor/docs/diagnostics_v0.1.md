# Phase F — Static Diagnostics v0.1

## Contract

```text
Student source
  -> ASTAnalyzer + ASTRuleRegistry
  -> Pylint/Radon/Flake8/Bandit adapters
  -> SensorReport[Diagnostic***REMOVED***
  -> error-pattern metadata
```

`Diagnostic` is an immutable normalized finding with:

- `source` and stable `rule_id`;
- `pattern_id`;
- normalized severity (`info`, `low`, `medium`, `high`);
- file, line and column;
- human-readable message;
- `diagnostic_only = true`.

`SensorReport` also records `ok`, `unavailable`, `failed` and `invalid_output`. Native analyzer schemas and exit codes do not leak into the domain contract.

## AST registry

`app/diagnostics/ast_rules.py` uses the standard-library `ast` parser and a deterministic ordered registry:

- `AST001` mutable default argument;
- `AST002` bare `except`;
- `AST003` excessive control-flow nesting;
- `AST004` mutable module-level state;
- `AST005` obvious builtin shadowing;
- `AST006` unreachable code after a terminating statement;
- `AST007` oversized function.

Syntax errors are normalized as `AST000/syntax-error`. The registry does not import or execute student code.

## External sensors

`app/diagnostics/adapters.py` provides:

- `PylintAdapter` — JSON messages; Pylint bitmask exit codes are accepted when JSON is valid.
- `RadonAdapter` — cyclomatic complexity, raw LOC, Halstead and maintainability index. MI is represented as an `info` diagnostic and remains diagnostic-only.
- `Flake8Adapter` — normalized line-oriented findings.
- `BanditAdapter` — JSON findings only when `security_eligible=True`; otherwise the sensor is explicitly skipped.

Adapters invoke subprocesses without a shell, use a configurable 60-second default timeout for the current Termux bootstrap cost, and classify unavailable tools, tool failures and malformed output separately. The default timeout is adjustable per adapter.

## Boundary

Phase F does not create `EvidenceCandidate`, append evidence events, calculate competency state, calculate mastery, or select hints. `map_diagnostics()` returns reference-only `ErrorPattern` metadata for the future Hint Engine. In particular:

- `maintainability_index` never becomes competency evidence;
- diagnostic count/severity never becomes a learner score;
- Bandit findings are not automatically shown to the learner;
- analyzer availability is not treated as a student failure.

## Verification

- `tests/unit/test_diagnostics.py` — 14 hermetic tests covering AST positive/negative/edge/syntax cases, deterministic ordering, all Radon metric families, Pylint/Flake8/Bandit parser normalization, malformed output, unavailable tools, tool failure and Bandit security eligibility.
- Live Termux smoke: Pylint 4.0.7, Radon 6.0.1, Flake8 7.3.0 and Bandit 1.9.4 all invoked through the adapters successfully with the configured timeout.
- Project gate: `70 passed, 2 skipped`; `mypy app/ --ignore-missing-imports` has no errors.

Phase F is a sensor layer only. Evidence Engine and Hint Engine remain future phases H and G.
