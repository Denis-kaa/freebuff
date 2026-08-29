# PHASE9 Gap Map (§20)

| # | Gap | Severity | Owner | Phase |
|---|-----|----------|-------|-------|
| G-11.1 | Production execution capability for test_factory (Variant B → Variant A migration) | 🟡 Medium | Future | Phase 12+ |
| G-11.2 | SI ranking limitation: `code` capability loses to `article_generation` due to score-fallback (not capability-match gate) | 🟡 Medium | core_02/scenario_intelligence.py | Phase 12 |
| G-11.3 | BaseFactory refactor — 3 near-clone Factories (~1200 LOC structural dup) | 🟢 Low | core_02/factory_base.py | Phase 12 (per ADR-013) |
| G-11.4 | test_13b xfail lenient — restore strict=True with hostile FakeRegistry | 🟢 Low | tests_09/test_test_factory.py | Phase 12 (per ADR-015) |
| G-11.5 | test_15 historical-bound shape — currently passes with 3 or 4 historical factories; Phase 12 rewrite asserts EXACTLY 3 | 🟢 Low | tests_09/test_test_factory.py | Phase 12 |
| G-11.6 | capability → factory.select_forge() ambiguity — `code` capability now resolves to `test` factory (not developer/tester roles); BlueprintCorpus competitive resolution needs review | 🟡 Medium | core_02/factory_registry.py + core_02/blueprint_v3.py | Phase 12 |

## Open NOT-blocking inventory

- `forge_cli` resize command (Phase 7 NIT) — cosmetic-only CLI surface, no impact on universal boundary.
- `mypy` strict mode — explicitly not exercised (per project convention; mypy is light-typing).
- `playground_19` parity — TypeScript/Vite playground intentionally separate track.
