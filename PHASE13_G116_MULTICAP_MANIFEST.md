# PHASE13_G116_MULTICAP MANIFEST — v5.189.31

Phase 13 G-11.6b capability resolution policy formalization + multi-cap coverage.

## Files

| File | SHA256 (16) | Size |
|------|-------------|------|
| `docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md` | `aa0b4e9c4c714699` | 13086 bytes |
| `core_02/factory_registry.py` | `b22de3a9b0323e6c` | 19905 bytes |
| `scripts_01/scenario_intelligence.py` | `b28a648eb8d8df7c` | 41259 bytes |
| `tests_09/test_scenario_intelligence.py` | `6154e473949e33d3` | 38440 bytes |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | `7304a48ddad519b5` | 1661 bytes |
| `CHANGELOG.md` | `b59b77b0176a67f8` | 477483 bytes |
| `BUFFY.md` | `97b5fa7e4a2a2a25` | 24571 bytes |
| `BUFFY_PROJECT.md` | `62950dfea19c8e0e` | 16836 bytes |
| `TASK.md` | `a2d2138aea9f6102` | 10173 bytes |
| `data_13/missing_registry.yaml` | `bf01000d84fee5f2` | 13623 bytes |

## Archive

- Path: `PHASE13_G116_MULTICAP_5.189.31.tar.gz`
- sha256 `067783c97e35ba0481e96a7ec060bcc133670b18d3b7e8c445b2bf620f66d238`
- Built: 2026-08-18 (Phase 13 G-11.6b closeout, post set-membership refactor + 2 multi-cap regression tests)

## 3 design decisions (3-author workshop)

- **D-1**: `CapabilityResolutionPolicy` frozen dataclass + `CODE_RESOLUTION_POLICY` dict in `core_02/factory_registry.py`.
- **D-2**: SI hard-gate set-membership refactor — `opp_capability in set(scenario_caps_full)` (full tuple).
- **D-3**: 2 multi-cap regression tests (positive + cross-domain rejection).

## Defense-in-depth stack (D-1 ↔ D-2 ↔ D-3)

- Layer 1: CapabilityResolutionPolicy typed single source of truth (`core_02.factory_registry.CODE_RESOLUTION_POLICY`).
- Layer 2: select_forge() status-priority + tie-break (Phase 11 universality proof, test_15 META-TEST).
- Layer 3: SI hard-gate (set-membership, full-tuple comparison).

## Consensus continuity

v5.189.30 → v5.189.31 ADDITIVE: zero logic change in select_forge(); new code is purely additive (1 dataclass, 1 dict, 1 method, 1 helper, 1 dataclass field, 2 tests).

## Drift posture

- consistency_check TOTAL=25 (test_counter 3029 → 3030 sync; 25 PRE-EXISTING missing_registry_sync OUT OF SCOPE per CHANGELOG NOTE).
