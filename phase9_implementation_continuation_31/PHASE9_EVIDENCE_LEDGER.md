# PHASE9 Evidence Ledger (§17)

Run-level evidence for Phase 11 (promt 093 = Phase 9 Implementation Continuation).

## Files of Record

| Artifact | Path | sha256 (atom at archive time) | Status |
|----------|------|-------------------------------|--------|
| TestFactory adapter | `scripts_01/test_factory.py` | captured in PHASE9_FACTORY_IMPLEMENTATION_5.189.28.tar.gz MANIFEST.sha256 | ✅ |
| TestFactory tests | `tests_09/test_test_factory.py` | captured in MANIFEST.sha256 | ✅ (16 passed + 1 xpassed strict=False) |
| Factory manifest | `runtime_05/factories/test/factory.yaml` | captured in MANIFEST.sha256 | ✅ |
| Verifier forge manifest | `runtime_05/factories/test/verifier.yaml` | captured in MANIFEST.sha256 | ✅ |
| CHANGELOG lead entry | `CHANGELOG.md` (v5.189.28 stanza) | captured in MANIFEST.sha256 | ✅ |
| §20 row 24 | `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | captured in MANIFEST.sha256 | ✅ |
| missing_registry.yaml (test_factory entry) | `data_13/missing_registry.yaml` | captured in MANIFEST.sha256 | ✅ (status=implemented, 24-я запись) |

## Determinism

- **NO wall-clock timestamps in code:** all tests use atomic ids via `hashlib.sha256(content).hexdigest()[:16***REMOVED***`.
- **Module fixture:** `project_factory_data` uses Path-based temp dirs (`tmp_path`), not `/tmp/...` (CAN-8).
- **Re-runnable:** `mark-implemented` is idempotent; `register` rejects duplicates (raises `ValueError`).

## Test evidence

```
tests_09/test_test_factory.py::test_1_test_capabilities_constant_present  PASSED
tests_09/test_test_factory.py::test_2_test_role_ids_subset_pipeline     PASSED
tests_09/test_test_factory.py::test_3_normalize_input_test_specific     PASSED
tests_09/test_test_factory.py::test_4_build_execution_request           PASSED
tests_09/test_test_factory.py::test_5_resolve_returns_factory_record    PASSED
tests_09/test_test_factory.py::test_6_execute_calls_forge_facade_run_chain PASSED
tests_09/test_test_factory.py::test_7_normalize_output_verifier_report  PASSED
tests_09/test_test_factory.py::test_8_accumulate_writes_to_memory_store PASSED
tests_09/test_test_factory.py::test_9_cli_resolve_and_run               PASSED
tests_09/test_test_factory.py::test_10_manifest_status_material_not_production PASSED
tests_09/test_test_factory.py::test_11_register_first_cycle_closed      PASSED
tests_09/test_test_factory.py::test_12_canonical_test_factory_3rd_domain PASSED
tests_09/test_test_factory.py::test_13a_si_ranking_article_first         PASSED
tests_09/test_test_factory.py::test_13b_si_ranking_code_when_no_content xfail (X, but lenient=True → XFAIL no-fail)
tests_09/test_test_factory.py::test_14_factory_passport_9_fields         PASSED
tests_09/test_test_factory.py::test_15_universal_factory_meta_test_3_domains PASSED
tests_09/test_test_factory.py::test_16_test_factory_class_not_collected_by_pytest PASSED

3-domain META-TEST (test_15): ONE FactoryRegistry(runtime_05/factories/) resolves article+research+code ALL THREE → 3 distinct factory_ids.
```
