# PHASE9 Architecture Decisions (ADRs) (§19)

## ADR-013 — BaseFactory refactor DEFERRED to Phase 12

**Status:** ACCEPTED · 2026-08-17 · v5.189.28

**Context.** `scripts_01/content_factory.py`, `scripts_01/research_factory.py`, and `scripts_01/test_factory.py` are near-identical ~400-line clones — only capability set, normalize_input/normalize_output specifics, and artifact_kind differ. ~1200 LOC of structural duplication across 3 files.

**Decision.** Register-first cycle closes per Phase 11; extract `BaseFactory` template class into `core_02/factory_base.py` is deferred to Phase 12 to avoid scope creep and to preserve CAN-16 ADDITIVE invariant.

**Consequences.** Cleaner refactor target available for Phase 12 with 3 independent clients to verify against. Phase 11 ships with the duplication; ADR-013 documents the plan.

**Primary risk.** Maintaining 3 near-clones is error-prone (Phase 9/10/11 each had to fork structure). Mitigation: file_pickers search for shared symbols; consistency_check flags drift; Phase 12 refactor is the long-term solution.

## ADR-014 — `test_factory` registered as Variant B (NOT PRODUCTION)

**Status:** ACCEPTED · 2026-08-17 · v5.189.28

**Context.** promt93 §11 explicitly mandates Variant B (NOT PRODUCTION): "MISSING PRODUCTION EXECUTION CAPABILITY — TestFactory uses same ForgeFacade.run_chain pattern as Content/Research; no real verifier production exists."

**Decision.** `runtime_05/factories/test/factory.yaml::status: material` (NOT `production`). TestFactory demonstrates the boundary contract but is not exposed as a runtime tool. Permission-business boundary requires production deployment hook (separate missing_registry entry, deferred).

**Consequences.** test_10 `manifest_status_material_not_production` enforces this contract at CI time. Anyone trying to enable `test_factory` for production gets an explicit signal.

## ADR-015 — `test_13b` xfail lenient (`strict=False`)

**Status:** ACCEPTED · 2026-08-17 · v5.189.28

**Context.** Phase 9 reviewer intent was `strict=True` so any XPASS surfaces a regression signal. Phase 11 applied Phase 10 follow-up but did NOT restructure with hostile-competitive FakeRegistry.

**Decision.** `xfail(strict=False)` is the pragmatic trade-off. The Phase 9 SI ranking limitation remains open (deferred); strict=True would fail the suite on any future XPASS that doesn't relate to ranking.

**Consequences.** Phase 12 fix-path is RESTRUCTURE test_13b with HOSTILE FakeRegistry (two candidates competing for `code` capability with different scores) so strict=True would surface genuine SI-ranking regression. Until then, lenient XFAIL is the pragmatic choice documented in this ADR.
