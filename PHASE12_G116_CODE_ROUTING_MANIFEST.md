# PHASE12_G116_CODE_ROUTING MANIFEST — v5.189.30 (post set-membership fix)

Phase 12 / G-11.6 capability routing consensus closure.

## Files

| File | SHA256 (16) | Size |
|------|-------------|------|
| `docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md` | `f68a9bff5a5e9937` | 10445 bytes |
| `scripts_01/scenario_intelligence.py` | `40e39122263608ee` | 39951 bytes |
| `core_02/factory_registry.py` | `19d98eb036abfd9e` | 17352 bytes |
| `core_02/blueprint_v3.py` | `f6ba680d60cb1d86` | 30802 bytes |
| `tests_09/test_scenario_intelligence.py` | `ce0070dc297a5c0c` | 35291 bytes |
| `tests_09/test_research_factory.py` | `309ee1e55a008a96` | 17521 bytes |
| `tests_09/test_content_factory.py` | `c7f7287c340e3d39` | 15257 bytes |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | `d3a806a71787159b` | 933 bytes |
| `CHANGELOG.md` | `ac9c660b328dc56e` | 474821 bytes |
| `BUFFY.md` | `1bd5fc1b297f746d` | 24571 bytes |
| `BUFFY_PROJECT.md` | `fc5b34b0dcd0a823` | 16768 bytes |
| `TASK.md` | `3d9cd5bceaf3d2cd` | 10202 bytes |
| `PHASE12_G116_CODE_ROUTING_MANIFEST.md` | `e14a70fa7ddccefb` | 1991 bytes |

## Archive

- Path: `PHASE12_G116_CODE_ROUTING_5.189.30.tar.gz`
- sha256 `89fc92fd77cbd7ce0beab292e5e40d503d0457e59b972991412c12ce98238e78`
- Built: 2026-08-17 (post SI hard-gate set-membership fix; xfail-strip; CHANGELOG NOTE expansion)

## SI hard-gate post-set-membership

- Code: `domain_match = (scenario_caps is not None and bool(scenario_caps) and opp_capability is not None and opp_capability in set(scenario_caps))`
- Per CANONICAL_ENGINE_ROUTING_V1.md invariant I-4 (Strict Capability Match), comparing against FULL SET `scenario.capabilities` not just first element.
- Future-proof for `scenario_fullstack.capabilities = ["code", "refactor"***REMOVED***` with `opp(capability="refactor")`.

## Consensus summary

- D-1 (Role) + D-2 (Factory AUTHORITATIVE) + D-3 (Model); CON-7 invariant preserved.
- `code` => `(test, verifier)` at D-2.

## Drift posture

- consistency_check TOTAL=25 (test_counter 3029 synced; 25 PRE-EXISTING missing_registry_sync OUT OF SCOPE per CHANGELOG NOTE).
