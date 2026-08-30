"""tests_09/test_scenario_intelligence_isolation.py — Phase 14 (v5.189.34).

ADR-015 mirror for ``scripts_01/scenario_intelligence.py``: per-instance
``_import_warnings`` must be fresh per ``ScenarioIntelligence`` instance and
must NOT cross-pollute between instances (or across factory classes). The
legacy module-level ``_LAZY_IMPORT_ERRORS`` is a DEPRECATED shim — never
appended to from within ScenarioIntelligence methods.

Ports the 3-test cross-pollution pattern from
``tests_09/test_content_factory.py::test_15`` (G-13.1) to SI's 3 lazy
resources: ``_scenario_registry``, ``_lazy_factory_registry``,
``_lazy_memory_store``.

NOTE: the factory_base pattern also had a cross-CLASS isolation check (e.g.
a ResearchFactory instance). That is intentionally NOT ported —
``ScenarioIntelligence`` has no subclasses, so cross-instance isolation is
THE meaningful invariant here (cross-class pollution is impossible by
construction).
"""

from __future__ import annotations

import sys
}

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts_01.scenario_intelligence as si_mod  # noqa: E402
from scripts_01.scenario_intelligence import ScenarioIntelligence  # noqa: E402


# ─── Fixtures / helpers ────────────────────────────────────────────────────

@pytest.fixture
def failing_lazy_import(monkeypatch):
    """Force si_mod._lazy_import to always return None (missing deps)."""

    def _failing(module_name: str, attr: str):
        return None

    monkeypatch.setattr(si_mod, "_lazy_import", _failing)


def _fresh_si() -> ScenarioIntelligence:
    """Fresh SI with NO injected deps (all lazy paths active)."""
    return ScenarioIntelligence(
        registry=None,
        factory_registry=None,
        memory_store=None,
    )


# ─── Test 1: fresh instance starts with empty warnings ─────────────────────

def test_1_fresh_instance_starts_with_empty_warnings():
    """Each ScenarioIntelligence instance must start with [] warnings."""
    inst = _fresh_si()
    assert inst._import_warnings == [], (
        "fresh ScenarioIntelligence instance must start with empty warnings"
    )
    # Class-level annotation must exist (mypy --strict PEP 526 forward-ref).
    # NOTE: a bare annotation does NOT create a class attribute — it lives in
    # ``__annotations__`` (and with `from __future__ import annotations` the
    # value is the string "List[str]"). Check the annotation dict, not the
    # attribute (accessing ScenarioIntelligence._import_warnings would raise
    # AttributeError).
    assert "_import_warnings" in ScenarioIntelligence.__annotations__, (
        "class-level annotation _import_warnings must be declared (PEP 526)"
    )


# ─── Test 2: per-instance warnings — no cross-pollution between instances ──

def test_2_lazy_failures_land_per_instance_no_cross_pollution(failing_lazy_import):
    """All 3 lazy methods append to self._import_warnings — never shared."""
    inst1 = _fresh_si()
    assert inst1._import_warnings == []

    # ─── 1. _scenario_registry — trigger on inst1 ───
    assert inst1._scenario_registry() is None
    assert inst1._import_warnings == ["scenario_registry: unavailable"], (
        f"inst1 warnings mismatch: {inst1._import_warnings!r}"
    )
    snap1 = list(inst1._import_warnings)

    # ─── 2. _lazy_factory_registry — trigger on inst1 ───
    assert inst1._lazy_factory_registry() is None
    assert inst1._import_warnings == snap1 + ["factory_registry: unavailable"], (
        f"inst1 must accumulate both warnings: {inst1._import_warnings!r}"
    )
    snap1 = list(inst1._import_warnings)

    # ─── 3. _lazy_memory_store — trigger on inst1 ───
    assert inst1._lazy_memory_store() is None
    assert inst1._import_warnings == snap1 + ["memory_store: unavailable"], (
        f"inst1 must accumulate all 3 warnings: {inst1._import_warnings!r}"
    )
    snap1 = list(inst1._import_warnings)  # full 3-warning snapshot for later

    # ─── 4. SECOND instance — must have FRESH empty warnings ───
    inst2 = _fresh_si()
    assert inst2._import_warnings == [], (
        "SECOND SI instance must have FRESH empty warnings (no cross-pollution)"
    )

    # ─── 5. Trigger lazy loads on inst2 — inst1 unchanged ───
    inst2._scenario_registry()
    inst2._lazy_factory_registry()
    inst2._lazy_memory_store()
    assert inst2._import_warnings == [
        "scenario_registry: unavailable",
        "factory_registry: unavailable",
        "memory_store: unavailable",
    ], f"inst2 warnings mismatch: {inst2._import_warnings!r}"
    assert inst1._import_warnings == snap1, (
        f"inst1 warnings DRIFTED after inst2 lazy loads — cross-pollution: "
        f"before={snap1!r} after={inst1._import_warnings!r}"
    )


# ─── Test 3: deprecated module-level singleton untouched (shim) ────────────

def test_3_deprecated_singleton_untouched_and_value_shape(failing_lazy_import):
    """Module-level _LAZY_IMPORT_ERRORS stays a List and NEVER receives appends.

    ADR-015 mirror: per-instance lazy methods append exclusively to
    ``inst._import_warnings``; the deprecated shim is read-only for external
    backward-compat consumers.

    NOTE (v5.189.36): the PEP 562 module-level ``__getattr__`` now emits
    DeprecationWarning on any access of ``_LAZY_IMPORT_ERRORS``; accesses here
    are wrapped in ``warnings.catch_warnings()`` (ignore) so the value-shape
    assertion is not polluted by the warning (mirrors test_content_factory
    test_15 handling).
    """
    import warnings

    # Snapshot before.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        depr_before = list(si_mod._LAZY_IMPORT_ERRORS)
    assert isinstance(depr_before, list), "shim must remain a real List"

    # Trigger ALL 3 lazy methods across 2 instances (would append in old code).
    inst1 = _fresh_si()
    inst1._scenario_registry()
    inst1._lazy_factory_registry()
    inst1._lazy_memory_store()
    inst2 = _fresh_si()
    inst2._scenario_registry()
    inst2._lazy_factory_registry()
    inst2._lazy_memory_store()

    # Deprecated singleton must NOT grow (per-instance migration complete).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        depr_after = list(si_mod._LAZY_IMPORT_ERRORS)
    assert depr_after == depr_before, (
        f"DEPRECATED module-level singleton must NOT receive appends from "
        f"per-instance lazy methods (ADR-015). before={depr_before!r} "
        f"after={depr_after!r}"
    )

    # Cross-check: warnings landed on the instances instead.
    assert len(inst1._import_warnings) == 3, inst1._import_warnings
    assert len(inst2._import_warnings) == 3, inst2._import_warnings


# ─── v5.189.36 hardening: PEP 562 __getattr__ emits DeprecationWarning on import ──

def test_4_lazy_import_errors_singleton_emits_deprecation_warning():
    """External consumer imports of ``_LAZY_IMPORT_ERRORS`` from
    ``scripts_01.scenario_intelligence`` MUST emit ``DeprecationWarning``
    pointing at ``inst._import_warnings`` (v5.189.36 hardening, mirrors
    core_02/factory_base.py v5.189.33 + test_content_factory test_16).

    Also verifies:
    - The access still returns a real ``List[str]`` (backward-compat surface).
    - The warning text contains the migration pointer.
    - The warning is filterable to ``error`` (pytest ``-W error::DeprecationWarning``
      does NOT break the value shape).
    - A second access still fires (no Python warning cache interference when
      the consumer changes stacklevel — caller-site dedup is up to the user).
    """
    import warnings

    # ─── 1. First access: DeprecationWarning fires ───
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        val = si_mod._LAZY_IMPORT_ERRORS

    assert isinstance(val, list), (
        f"DEPRECATED shim must remain a real list (backward-compat); got {type(val).__name__}"
    )
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), (
        f"Expected at least one DeprecationWarning, got: "
        f"{[(w.category.__name__, str(w.message)[:60]) for w in caught]}"
    )
    deprecation_msgs = [str(w.message) for w in caught
                       if issubclass(w.category, DeprecationWarning)]
    assert deprecation_msgs, "at least one DeprecationWarning must be present"
    assert any("inst._import_warnings" in m for m in deprecation_msgs), (
        f"DeprecationWarning must point at inst._import_warnings; got: {deprecation_msgs!r}"
    )
    assert any("scenario_intelligence._LAZY_IMPORT_ERRORS" in m for m in deprecation_msgs), (
        f"DeprecationWarning must mention _LAZY_IMPORT_ERRORS; got: {deprecation_msgs!r}"
    )

    # ─── 2. Re-access: deprecation still works (fresh catch_warnings resets state) ───
    with warnings.catch_warnings(record=True) as caught2:
        warnings.simplefilter("always", DeprecationWarning)
        val2 = si_mod._LAZY_IMPORT_ERRORS
    assert isinstance(val2, list)
    deprecation2 = [w for w in caught2 if issubclass(w.category, DeprecationWarning)]
    assert deprecation2, (
        "Each explicit consumer call should still get a DeprecationWarning; "
        "if this fails, Python's filter is suppressing it (check -W flags)"
    )

    # ─── 3. Under ``error::DeprecationWarning`` filter, access raises (documented design) ───
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        with pytest.raises(DeprecationWarning) as excinfo:
            si_mod._LAZY_IMPORT_ERRORS
    assert "inst._import_warnings" in str(excinfo.value), (
        f"Raised DeprecationWarning must point at inst._import_warnings; "
        f"got: {str(excinfo.value)[:120]}"
    )
