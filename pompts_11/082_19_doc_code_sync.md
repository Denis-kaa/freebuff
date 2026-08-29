# 082_19 — DOC CODE SYNC
# Version: 1.0
# Date: 2026-08-12 (перенесён из prompts_11/080_19 в канон v5.189.3, H-1/H-2)
# Cycle: register-first (Missing Cap, currently absent from registry)
# Source: promt 4.md §19 artifact J + report §22.12 EXACT NEXT PROMPT

## ROLE

Ты — Senior Software Architect + Repository Forensics Engineer.

Реализуешь **PHASE J** Architecture-Code Synchronization Layer —
**не реализуешь Content Intelligence**.

## ЦЕЛЬ

Создать `core_02/doc_code_verify.py` — verifier, который проверяет, что
документация (`docs_10/engineering-memory/*.md`) согласована с кодом
(`core_02/`, `scripts_01/`, `runtime_05/`).

**Не делать:** переписывать существующие компоненты, мигрировать,
создавать параллельные системы.

## SCOPE BOUNDARY (per AGENTS.md §1)

**In scope:**
- `@entity`, `@contract`, `@symbol`, `@test`, `@event` анкоры в docs_10/engineering-memory/*.md
- Resolution через `PLATFORM_CODE_MAP_V1.md §A` (canonical registry)
- Verifier через AST scan `core_02/` + `scripts_01/` + `runtime_05/`
- Lifecycle classification: CONFIRMED / STALE / DOC_ONLY / UNKNOWN
- CLI: `python -m core_02.doc_code_verify <doc_or_dir> [--workspace .***REMOVED*** [--strict***REMOVED*** [--json***REMOVED***`

**Out of scope (FORBIDDEN):**
- Content Intelligence (Factory composition TR-11, Opportunity Engine)
- Whim Capture (missing cap, separate spec)
- Auto-discovery из scenario.py
- Replacing `consistency_check.py` (дополняет, не заменяет)

## DO D (Definition of Done)

- [ ***REMOVED*** `data_13/missing_registry.yaml`: `doc_code_verify` имеет `status=implemented`, `implementation=core_02/doc_code_verify.py`, `prompt_path=pompts_11/082_19_doc_code_sync.md`
- [ ***REMOVED*** `core_02/doc_code_verify.py`: ≤180 LOC, dataclass Claim + VerificationResult, 5 публичных функций
- [ ***REMOVED*** `tests_09/test_doc_code_verify.py`: ≤400 LOC, ≥10 tests, fail-safe harness
- [ ***REMOVED*** pytest нового файла: GREEN (100% pass)
- [ ***REMOVED*** mypy: clean
- [ ***REMOVED*** `python -m core_02.doc_code_verify docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md` exit 0, JSON output валиден
- [ ***REMOVED*** `python -m core_02.doc_code_verify docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` exit 0 (warn mode), finds ≥3 CONFIRMED anchors + flag любые STALE
- [ ***REMOVED*** §20 карта v1.1 (FACTORY_FORGE_ARCHITECTURE_V1.md): row «Code-Documentation Sync» flipped planned → implemented v5.189.0
- [ ***REMOVED*** CHANGELOG.md v5.189.0 prepend
- [ ***REMOVED*** CAN-16 ADDITIVE: 0 modifications to scenario.py / forge_registry.py / blueprint_v3.py / forge_passport.py / factory_registry.py

## DESIGN (per thinker verdict)

### Q1. Claim Extraction
**Решение: (b) Regex on closed patterns.**

```python
ANCHOR_RE = re.compile(
    r"@(entity|contract|symbol|test|event|module|component)\s+([\w\.\:***REMOVED***+)"
)
```

Strict regex на закрытый набор namespaces, capture (namespace, target).

### Q2. Anchor-to-Code Resolution
**Решение: (c) Both: PLATFORM_CODE_MAP as fast-path + AST as verifier.**

- Phase 1: load PLATFORM_CODE_MAP_V1.md §A as dict `[entity_id → {file, symbol, ...***REMOVED******REMOVED***`
- Phase 2: for each claim, check if entity_id in dict → if yes, AST-verify file::symbol exists

### Q3. Lifecycle Classification (4-state machine, ANTI-5 minimum)

```python
CONFIRMED  # anchor в Map + file::symbol exist (AST verify pass)
STALE      # anchor в Map, но file отсутствует или symbol missing
DOC_ONLY   # anchor в doc, но НЕТ в PLATFORM_CODE_MAP
UNKNOWN    # regex matched but malformed (e.g. target contains whitespace)
```

**Не включаем:** CODE_ONLY (нет проблемы — code без doc OK), CONTRADICTION
(требует semantic AI), PARTIAL (требует signature diff) — выходит за scope.

### Q4. Fail-Safe Semantics

- **Default `--mode=warn`**: exit 0 всегда, печатает findings info-only
- **Opt-in `--strict`**: exit 1 на любой STALE или DOC_ONLY finding (gate CI)
- Не падать на parse errors в docs (graceful: warning, skip doc, continue)
- Не падать на missing PLATFORM_CODE_MAP (warning, mark all claims DOC_ONLY with "no map" reason)

### Q5. CLI Surface (mirror consistency_check)

```python
python -m core_02.doc_code_verify <doc_or_dir>
    [--workspace <dir>***REMOVED***      # default: .
    [--strict***REMOVED***               # gate mode, exit 1 on STALE/DOC_ONLY
    [--json***REMOVED***                 # output JSON only, no human format
    [--namespace entity,contract,symbol,test,event***REMOVED***  # which to check (default all)
```

Aggregate output для директорий:
```json
{
  "docs_checked": 5,
  "total_claims": 47,
  "by_classification": {
    "CONFIRMED": 42, "STALE": 2, "DOC_ONLY": 2, "UNKNOWN": 1
  ***REMOVED***,
  "findings": [
    {"doc": "PLATFORM_CODE_MAP_V1.md", "line": 380, "namespace": "@entity", "target": "factory.registry", "classification": "CONFIRMED", "evidence": "core_02/factory_registry.py::FactoryRegistry"***REMOVED***,
    ...
  ***REMOVED***
***REMOVED***
```

## ARTIFACT SHAPES

```python
@dataclass(frozen=True)
class Claim:
    doc_path: str      # relative to workspace
    line_num: int      # 1-based
    namespace: str     # "@entity" / "@contract" / "@symbol" / "@test" / "@event"
    target: str        # "scenario.registry" / "ScenarioRegistry.find_role"

@dataclass(frozen=True)
class VerificationResult:
    claim: Claim
    classification: str  # CONFIRMED | STALE | DOC_ONLY | UNKNOWN
    mapped_file: str = ""     # e.g. "core_02/factory_registry.py"
    mapped_symbol: str = ""   # e.g. "FactoryRegistry"
    evidence: str = ""        # human-readable proof
```

## FUNCTIONS (5 public, ≤5 args each)

```python
def extract_claims(doc_path: Path) -> list[Claim***REMOVED***
def load_code_map(workspace: Path) -> dict[str, dict***REMOVED***
def check_symbol_exists(workspace: Path, file_rel: str, symbol: str) -> bool
def verify_claim(claim: Claim, code_map: dict, workspace: Path) -> VerificationResult
def run_verification(target_path: Path, workspace: Path, *, strict: bool = False) -> dict
```

## EDGE CASES (handles gracefully, NOT exceptions)

1. Doc with no anchors → `total_claims: 0`, no error
2. PLATFORM_CODE_MAP_V1.md missing → all claims DOC_ONLY with reason "no_map"
3. Malformed PLATFORM_CODE_MAP_V1.md (broken table) → catch yaml/parse errors, warn, mark DOC_ONLY
4. Anchor in code fence (```...```) → regex MUST exclude (use `^(?!.*```)` lookahead OR multi-line state)
5. Duplicate anchors in same doc → each line produced claim (inform_dup=True)
6. Symbol with `::` (Python path notation) → split, verify each part
7. File deleted since docs written → STALE with `"reason": "file_missing"`

## RISKS (top 3) + MITIGATION

1. **Regex false-positives in code fences** → limit regex to lines NOT inside ```...``` blocks (per-line state machine OR uppercase prefix heuristic like `'  @entity'`).
2. **PLATFORM_CODE_MAP table parser brittleness** → tolerant Markdown table regex, tolerate column reorder.
3. **AST check for class methods (`ScenarioRegistry.find_role`)** → handle `Class.method` by importing module + `hasattr(class_instance, 'method')`. Fallback to module-has-class check if import fails.

## ACCEPTANCE (testable)

1. `extract_claims` finds ≥3 anchors in PLATFORM_CODE_MAP_V1.md
2. `load_code_map` parses PLATFORM_CODE_MAP_V1.md table → ≥5 entries
3. `check_symbol_exists('core_02/scenario_registry.py', 'ScenarioRegistry')` returns True
4. `run_verification(PLATFORM_CODE_MAP_V1.md)` exits 0, finds ≥80% CONFIRMED
5. `run_verification(<bad doc>)` exits 0, mark all DOC_ONLY (warn mode)
6. `run_verification(<bad doc>, strict=True)` exits 1
7. `python -m core_02.doc_code_verify docs_10/engineering-memory/` aggregate JSON ≥20 claims across 3+ docs

## REFERENCES (canonical)

- `core_02/forge_passport.py` — frozen dataclass + _from_dict + validate() + to_yaml pattern (mirror style)
- `core_02/factory_registry.py` — _reload() graceful-degrade (yaml.YAMLError, empty-dict placeholder)
- `scripts_01/consistency_check.py` — CLI pattern (argparse + namespace + JSON output)
- `docs_10/engineering-memory/SEMANTIC_ANCHOR_SPEC_V1.md` — closed namespaces list
- `docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md` — canonical registry for resolution

## STOP CONDITIONS

Stop and report if:
- PLATFORM_CODE_MAP_V1.md format fundamentally changed (no table)
- AST check fails for >50% of files (pathlib bug?)
- Existing `consistency_check.py` already has 80% of this functionality → exit early with "DUPLICATE, scope rotate"

## ГАРАНТИИ

- CAN-16 ADDITIVE: file new, no edits to existing
- ANTI-6b: closed vocab for namespace list (no silent expansion)
- Backward-compat: warns, never errors by default
- Tests: pytest parametrize for edge case matrix
