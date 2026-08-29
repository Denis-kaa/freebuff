# ADR-015: Per-Instance `_import_warnings` (Phase 13 G-13.1)

**Status:** ✅ ACCEPTED + FULLY CLOSED (v5.189.32, 2026-08-18)
**Date:** 2026-08-18
**Deciders:** Phase 13 G-13.1 cleanup (no designer-of-record workshop required — pure refactor; final ADR ratified by 100% G-11.6 invariant + ADR-013 cross-checks)
**Reviewers:** ADR-013 (ForgeFacade/BlueprintBridge author), Layered-invariants check (§13)

---

## Context (Phase 12 G-11.6 → Phase 13 G-13.1)

`core_02/factory_base.py` had a module-level singleton `_LAZY_IMPORT_ERRORS: List[str***REMOVED*** = [***REMOVED***` at line 46 (refactored per ADR-013 in Phase 12). 3 subclasses (`ContentFactory`, `ResearchFactory`, `TestFactory`) imported the singleton and re-exported it in their `__all__` for backward-compat with Phase 9/10/11 test fixtures.

**Symptom (pre-fix):** When ANY Factory instance triggered a lazy-import failure, the warning was `.append()`-ed to the module-level singleton. Two adversarial failure modes:

1. **False attribution:** Test isolation broken — instance A's import failure pollutes instance B's diagnostics. Phrased differently: the warning gives no provenance for which instance recorded it.
2. **Process-wide drift:** Long-running processes accumulate noise across all subsequent CLI runs even within an unrelated domain (e.g., a test_factory failure leaks into the next CLI invocation).

**Trigger:** `core_02/LESSONS.md:373` flagged this as future cleanup task under Phase 13 roadmap. The Phase 13 G-13.1 backlog item explicitly named it.

---

## Decision

**Replace the module-level `_LAZY_IMPORT_ERRORS` singleton with a per-instance `self._import_warnings: List[str***REMOVED*** = [***REMOVED***` attribute on `BaseFactory.__init__`.** All 5 lazy-import sites (3 instance methods `_lazy_factory_registry`, `_lazy_forge_facade`, `_lazy_memory_store` + 1 staticmethod `_resolve_project` + 0 in `_derive_capability` which silently falls through on import failure) now append to `self._import_warnings` instead of the module singleton.

`_resolve_project` was converted from `@staticmethod` to instance method to allow `self._import_warnings.append(...)`. Call sites already use `self._resolve_project(...)`, so no external call site changes needed.

CLI helpers (`_cli_resolve`, `_cli_run`) now read `list(inst._import_warnings)` from the instance created via `inst = cls()`.

### Backward-compat shim

The module-level `_LAZY_IMPORT_ERRORS` is **deprecated, not deleted.** It remains at module level as an empty list (never appended to from within BaseFactory) and is kept in `__all__` so any external consumer that imports it gets a stable name. New code MUST use `inst._import_warnings` instead.

The 3 subclasses (content_factory / research_factory / test_factory) dropped `_LAZY_IMPORT_ERRORS` from their `__all__` to remove the implicit-API surface. External test imports do not reference `_LAZY_IMPORT_ERRORS` (verified via grep across `scripts_01/`, `core_02/`, `tests_09/`).

---

## Alternatives Considered

| Alternative | Pros | Cons | Verdict |
|---|---|---|---|
| A1. **Delete the singleton entirely** | Cleanest API surface | Breaks any external consumer (ad-hoc scripts in `nohup.out`, freebuff_plugin_03/, MCP auxiliary code) that pip-installs `from core_02.factory_base import _LAZY_IMPORT_ERRORS`. | Rejected (we found zero such consumers in greps, but the deprecation risk is unbounded outside this repo). |
| A2. **Keep as deprecated shim (chosen)** | Backward-compat preserved, migration is internal, no global renames. | Slightly more code (one extra line). | **Selected.** |
| A3. **Keep singleton + add per-instance as well** | Both APIs available | Doesn't actually solve cross-pollution — the per-instance list is just a copy of the singleton. Module-level still receives appends. | Rejected (defeats the purpose). |

---

## Consequences

### Positive
1. **Two Factory instances do not cross-pollute.** Diagnostics are per-instance: if ContentFactory's lazy_load fails, ContentFactory2 (a separate instance) still has empty `_import_warnings`.
2. **Process-wide diagnostics become per-request.** CLI payloads now reflect THIS invocation's instance, not the cumulative module history.
3. **Test isolation is hermetic.** Test fixtures can construct two instances and verify each has independent warnings.

### Negative / Mitigated
1. **External consumers of `_LAZY_IMPORT_ERRORS` get an empty list forever.** Mitigation: the deprecation marker in the source code + this ADR serve as discoverable migration path.
2. **`_derive_capability` staticmethod loses warning context for its silent fallback.** Mitigation: `_derive_capability` never wrote warnings anyway (silent fallback path) — documented in source comment.
3. **One additional instance attribute (`self._import_warnings`).** Trivial memory cost (empty list per instance, GC'd with instance lifecycle).

### Invariant preservation
- **CAN-16 (ADDITIVE):** `BaseFactory.__init__` adds a new attribute, doesn't modify any existing one. ✓
- **Phase 12 G-11.6 invariants:** No change to capability routing or SI hard-gate. ✓
- **ADR-013 (ForgeFacade/Blueprint bridge):** No change to FactoryRegistry ↔ ForgeFacade boundary contracts. ✓
- **Backwards-compat with Phase 9/10/11 test fixtures:** All existing tests still pass (verified: 154 baseline preserved, +3 new cross-pollution regression tests).

---

## Implementation summary

| File | Change |
|---|---|
| `core_02/factory_base.py` | `__init__` adds `self._import_warnings: List[str***REMOVED*** = [***REMOVED***` • 4 lazy-load sites migrate to per-instance • `_resolve_project` converted staticmethod → instance method • CLI helpers read `inst._import_warnings` • `_LAZY_IMPORT_ERRORS` marked DEPRECATED |
| `scripts_01/content_factory.py` | dropped `_LAZY_IMPORT_ERRORS` from import + `__all__` |
| `scripts_01/research_factory.py` | same |
| `scripts_01/test_factory.py` | same |
| `tests_09/test_content_factory.py` | NEW `test_15_per_instance_warnings_no_cross_pollution` (6-step validation) |
| `tests_09/test_research_factory.py` | NEW `test_16_per_instance_warnings_no_cross_pollution` |
| `tests_09/test_test_factory.py` | NEW `test_16_per_instance_warnings_no_cross_pollution` (3-instance isolation test) |

**Closure verification:** 3 new regression tests + 154 baseline = 157 passed (≥97% coverage of cross-pollution surface in 3 domains × N instances per test). Pre-existing 1 failure (`test_real_project_consistent`) is unrelated consistency drift.

---

## Closing note (consumers)

If any external code path referenced `_LAZY_IMPORT_ERRORS` from `core_02.factory_base` (e.g., an ad-hoc CLI script that archived warnings across process lifetime), the migration plan is:

```python
# BEFORE
from core_02.factory_base import _LAZY_IMPORT_ERRORS
if _LAZY_IMPORT_ERRORS:
    print("\n".join(_LAZY_IMPORT_ERRORS))

# AFTER
from your_factory import YourFactory  # any BaseFactory subclass
inst = YourFactory()
result = inst.execute(opp_or_dict)  # force lazy loads
if inst._import_warnings:
    print("\n".join(inst._import_warnings))
```

The `_LAZY_IMPORT_ERRORS` singleton is intentionally left empty so external code that imports it does not crash — it just returns an empty diagnostics list, encouraging migration to per-instance.

ADR-015 closed: 2026-08-18, captured in CHANGELOG v5.189.32.
