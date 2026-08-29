# PHASE9 Deferred Backlog (§21)

## From §11 Variant B

- **TestFactory → production**: full production execution pipeline (separate missing_registry entry; security review; deployment workflow per `missing_registry` register-first).
- **Variant A migration**: requires proving that verifier_report artifact kind has production consumer (current: only candidate-collection to MemoryStore).

## From §11 Architecture Simplification

- **`BaseFactory` template in `core_02/factory_base.py`** — Phase 12 cleanup (per ADR-013).
- **Capability → factory competitive resolution** — Phase 12 review (per Gap G-11.6).

## From Reviewer Nits

- **test_13b hostile FakeRegistry** — Phase 12 restructure (per ADR-015).
- **test_15 EXACTLY-3 boundary** — Phase 12.

## From Cross-Reference

- **G-11.6: `code` capability ambiguity** between developer role (BlueprintCorpus) and test_factory (this Phase) — needs ONE designer-of-record verdict; deferred to Phase 12 workshop.
- **Phase 12 universal-boundary audit** — full factorial test of N=4 Factories; required before §11 Variant A migration for `test_factory`.
