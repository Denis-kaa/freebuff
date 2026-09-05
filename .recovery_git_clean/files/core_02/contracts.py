"""core_02/contracts.py — Cascade JSON contracts: system → workspace → project → agent → task.

Implements Задача 1 from MISSION (SESSION_UNDERSTANDING_2026-08-02.md):
- JSON describes who, where, which rights, what to do — not free-form prose.
- Inheritance with most-specific-wins semantics (deep merge).
- ``task.json::assigned_model: "auto"`` is resolved through SmartRouter.

Pure module — no I/O, no disk mutation. Imported by ``core_02/wizard_lib.py``
and tested in ``tests_09/test_wizard.py``.
"""

from __future__ import annotations

from typing import Any


# Canonical ordering for inheritance. Earlier levels act as defaults; later
# levels override only the keys they explicitly state. Unknown levels are
# silently skipped when merging.
CASCADE_LEVELS: tuple[str, ...***REMOVED*** = (
    "system", "workspace", "project", "agent", "task",
)

# Structural minimum for a task contract: goal + assigned_role + routing_hint.
# Wizard workflow always produces one, but a hand-written task.json might forget.
_TASK_REQUIRED_FIELDS: tuple[str, ...***REMOVED*** = (
    "goal", "assigned_role", "routing_hint",
)


def deep_merge(base: dict, override: dict) -> dict:
    """Most-specific-wins deep merge for nested dicts.

    Recurses for both sides being dicts; otherwise overrides. Returns a fresh
    dict — never mutates callers. Scalar keys (str/list/int) on the override
    side replace the base values wholesale.

    Edge case: a base scalar overridden by a dict gets replaced
    (override wins). See tests/test_contracts.py::test_deep_merge_replaces_non_dict_with_dict.
    """
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k***REMOVED***, dict) and isinstance(v, dict):
            out[k***REMOVED*** = deep_merge(out[k***REMOVED***, v)
        else:
            out[k***REMOVED*** = v
    return out


class CascadeContract:
    """system → workspace → project → agent → task — most specific wins."""

    LEVELS: tuple[str, ...***REMOVED*** = CASCADE_LEVELS

    @classmethod
    def merge(cls, levels: dict[str, dict***REMOVED***) -> dict:
        """Apply deep merge in fixed level order. Unknown levels skipped."""
        result: dict[str, Any***REMOVED*** = {***REMOVED***
        for level in cls.LEVELS:
            payload = levels.get(level)
            if not isinstance(payload, dict):
                continue
            result = deep_merge(result, payload)
        return result

    @classmethod
    def validate_levels(cls, levels: dict[str, dict***REMOVED***) -> list[str***REMOVED***:
        """Return list of structural errors. Empty list = OK.

        Blockers are reported (not raised): wizard writes a sidecar
        ``validation_errors.txt`` so users see issues without losing work.

        Sidecar semantics: ``run_wizard`` only writes/overwrites
        ``validation_errors.txt`` on runs that produce errors. A clean run
        (``errors == [***REMOVED***``) leaves any prior sidecar intact on disk —
        callers should treat the file as "present ⇒ warnings exist", not
        "fresh this run". Don't rely on the sidecar as an idempotent
        refresh marker.
        """
        errors: list[str***REMOVED*** = [***REMOVED***
        for level in cls.LEVELS:
            if level not in levels:
                errors.append(f"missing level '{level***REMOVED***'")
                continue
            if not isinstance(levels[level***REMOVED***, dict):
                errors.append(
                    f"level '{level***REMOVED***' must be a dict, got "
                    f"{type(levels[level***REMOVED***).__name__***REMOVED***"
                )
        task = levels.get("task")
        if isinstance(task, dict):
            for required in _TASK_REQUIRED_FIELDS:
                if required not in task:
                    errors.append(f"task.{required***REMOVED*** required")
        return errors


def resolve_assigned_model(
    task: dict,
    capabilities: list[str***REMOVED*** | None = None,
    router=None,
) -> str:
    """Resolve ``task.assigned_model`` through SmartRouter if it equals ``"auto"``.

    Returns the resolved model name (always a string, never ``"auto"``).
    Caller doesn't need to know whether routing ran.

    Local import for ``SmartRouter``/``ModelCatalog`` keeps import contracts
    isolated: import-time failures in ``core_02.router`` (transitive dep,
    syntax error, broken catalog) don't cascade into ``core_02.contracts`` —
    only the function call triggers the dependency.
    """
    from core_02.router import SmartRouter, ModelCatalog  # local import — isolated
    assigned = task.get("assigned_model", "auto")
    if assigned != "auto":
        return assigned
    hint: list[str***REMOVED*** = (
        list(capabilities) if capabilities is not None
        else list(task.get("routing_hint", [***REMOVED***))
    )
    if router is None:
        router = SmartRouter(catalog=ModelCatalog.default())
    decision = router.route(required_capabilities=hint)
    return decision.model


__all__ = [
    "CASCADE_LEVELS",
    "CascadeContract",
    "deep_merge",
    "resolve_assigned_model",
***REMOVED***
