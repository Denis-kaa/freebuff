"""core_02/wizard_lib.py — Wizard logic (pure).

Stages project JSON contracts based on Blueprint v3 corpus and caller-provided
queries (project goal, task goal). Implements Задача 2 of MISSION in a
testable form (CLI entry lives in ``scripts_01/wizard.py``).

Design rationale lives in ``core_02/LESSONS.md`` (CON-6 et al.).
"""

from __future__ import annotations

import json
}
from typing import Any, Optional

from core_02.blueprint_v3 import BlueprintCorpus
from core_02.contracts import CascadeContract, resolve_assigned_model
from core_02.scenario import Scenario, Role
from core_02.scenario_registry import ScenarioRegistry


def _strip_query(query: str) -> set[str]:
    return {w.lower().strip(".,:;!\"'()[){}") for w in query.split()
            if w.strip(".,:;!\"'()[){]")]


def score_role_match(query: str, role_id: str, role_title: str, role_text: str) -> float:
    """Trivial keyword overlap score.

    Returns matches / len(query_words). ``0`` for empty query. Caps at 1.0.
    No LLM, no fuzzy embeddings — keeps deterministic & testable. See CAN-5.
    """
    words = _strip_query(query)
    if not words:
        return 0.0
    haystack = (role_title + " " + role_text).lower()
    matches = sum(1 for w in words if w in haystack)
    return matches / len(words)


def propose_roles(
    corpus: BlueprintCorpus,
    query: str,
    top_n: int = 3,
) -> list[tuple[str, str, float]]:
    """Return top-N role candidates (``(role_id, title, score)``) sorted desc.

    Fails safe: if nothing matches, falls back to the first registered role with
    score 0.0 so the wizard never deadlocks on an empty list. See CAN-5.
    """
    scored: list[tuple[str, str, float]] = []
    for role_id, _file, role_title, _type in corpus.list_roles():
        try:
            bp = corpus.load_blueprint(role_id)
        except FileNotFoundError:
            continue
        score = score_role_match(query, role_id, role_title, bp.sections.get("role", ""))
        scored.append((role_id, role_title, score))
    scored.sort(key=lambda r: (-r[2], r[0]))
    if not scored:
        # No roles at all (registry empty).
        return []
    if scored[0][2] <= 0.0:
        # Insert deterministic fallback head.
        first_fallback = corpus.list_roles()[0]
        scored.insert(0, (first_fallback[0], first_fallback[2], 0.0))
    return scored[:top_n]


def build_agent_json(corpus: BlueprintCorpus, role_id: str) -> dict[str, Any]:
    """Build the agent contract from a chosen role."""
    bp = corpus.load_blueprint(role_id)
    return {
        "role_id": role_id,
        "role_title": bp.header_meta.get("ROLE", ""),
        "version": bp.header_meta.get("VERSION", ""),
        "routing_hint": corpus.routing_hint(role_id),
        "sections_known": sorted(bp.sections.keys()),
        "missing_required_sections": corpus.validate_blueprint(bp),
    }


def build_task_json(
    corpus: BlueprintCorpus,
    role_id: str,
    goal: str,
    priority: str = "normal",
) -> dict[str, Any]:
    """Build the task contract with ``assigned_model: "auto"`` placeholder."""
    if priority not in ("low", "normal", "high", "critical"):
        raise ValueError(f"priority must be one of low|normal|high|critical, got {priority!r}")
    return {
        "goal": goal,
        "priority": priority,
        "assigned_role": role_id,
        "assigned_model": "auto",  # resolved by run_wizard
        "routing_hint": corpus.routing_hint(role_id),
        "created_by": "freebuff.wizard",
    }


def _seed_levels(
    workspace_path: Path,
    project_name: str,
    project_goal: str,
    workspace_mode: str,
) -> dict[str, dict[str, Any]]:
    return {
        "system": {
            "platform": "freebuff",
            "contracts_manifest": "1.0",
            "scenarios": {"blueprint_v3_integration": "active"},
        },
        "workspace": {
            "root": str(workspace_path),
            "mode": workspace_mode,
        },
        "project": {
            "name": project_name,
            "goal": project_goal,
        },
        "agent": {},  # filled below
        "task": {},    # filled below
    }


def run_wizard(
    corpus: BlueprintCorpus,
    workspace_path: Path,
    project_name: str,
    project_goal: str,
    task_goal: str,
    priority: str = "normal",
    workspace_mode: str = "single",
    force_role_id: str | None = None,
) -> dict[str, Any]:
    """Stage the JSON-contract set + merged.json on disk.

    Returns keys: ``paths`` (level→Path), ``merged_path``, ``contracts``,
    ``merged``, ``selected_role_id``, ``resolved_model``.
    """
    workspace_path = Path(workspace_path)
    project_dir = workspace_path / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    levels = _seed_levels(
        workspace_path=workspace_path,
        project_name=project_name,
        project_goal=project_goal,
        workspace_mode=workspace_mode,
    )

    if force_role_id:
        if force_role_id not in corpus._index:
            raise KeyError(f"force_role_id {force_role_id!r} not in registry")
        role_id = force_role_id
        role_title = corpus._index[role_id].get("role", "")
    else:
        scored = propose_roles(corpus, project_goal, top_n=3)
        if not scored:
            raise RuntimeError("no roles registered in corpus")
        role_id, role_title, _score = scored[0]

    levels["agent"] = build_agent_json(corpus, role_id)
    levels["task"] = build_task_json(corpus, role_id, task_goal, priority=priority)

    resolved_model = resolve_assigned_model(
        levels["task"],
        capabilities=corpus.routing_hint(role_id),
    )
    levels["task"]["assigned_model"] = resolved_model

    merged = CascadeContract.merge(levels)

    paths: dict[str, Path] = {}
    for level in CascadeContract.LEVELS:
        path = project_dir / f"{level}.json"
        path.write_text(
            json.dumps(levels[level], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths[level] = path
    merged_path = project_dir / "merged.json"
    merged_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Sidecar write policy: only on runs that yield errors. Clean runs
    # leave any prior file intact (NOT rebuilt) — see
    # ``CascadeContract.validate_levels`` docstring for the contract.
    errors = CascadeContract.validate_levels(levels)
    if errors:
        (project_dir / "validation_errors.txt").write_text(
            "\n".join(errors), encoding="utf-8",
        )

    return {
        "paths": paths,
        "merged_path": merged_path,
        "contracts": levels,
        "merged": merged,
        "selected_role_id": role_id,
        "resolved_model": resolved_model,
    }


def build_agent_json_for_registry(
    registry: ScenarioRegistry,
    scenario: Scenario,
    role: Role,
) -> dict[str, Any]:
    """Build the agent contract using a registry-resolved scenario/role pair.

    Same shape as :func:`build_agent_json` but the scenario (not just the
    role_id) is explicit so the registry-resolved branch doesn't need to
    re-discover it.
    """
    return {
        "role_id": role.role_id,
        "scenario_id": scenario.scenario_id,
        "role_title": role.title,
        "routing_hint": scenario.routing_hint(role.role_id),
        "missing_required_sections": scenario.validate(),
    }


def build_task_json_for_registry(
    registry: ScenarioRegistry,
    scenario: Scenario,
    role: Role,
    goal: str,
    priority: str = "normal",
) -> dict[str, Any]:
    """Build the task contract for registry-resolved role.

    routing_hint comes from the scenario directly (no re-projection).
    """
    if priority not in ("low", "normal", "high", "critical"):
        raise ValueError(f"priority must be one of low|normal|high|critical, got {priority!r}")
    return {
        "goal": goal,
        "priority": priority,
        "assigned_role": role.role_id,
        "assigned_scenario": scenario.scenario_id,
        "assigned_model": "auto",  # resolved by run_wizard_with_registry
        "routing_hint": scenario.routing_hint(role.role_id),
        "created_by": "freebuff.wizard",
    }


def _seed_levels_for_registry(
    workspace_path: Path,
    project_name: str,
    project_goal: str,
    workspace_mode: str,
) -> dict[str, dict[str, Any]]:
    """Variant of :func:`_seed_levels` that uses generic 'scenarios' metadata.

    The legacy single-scenario version hardcodes
    ``scenarios: {blueprint_v3_integration: active}``; this one writes
    ``scenarios_registered: [scenario_ids]`` instead so callers can see
    cross-scenario context at a glance.
    """
    return {
        "system": {
            "platform": "freebuff",
            "contracts_manifest": "1.0",
            "scenarios_registered": [],  # filled below
        },
        "workspace": {
            "root": str(workspace_path),
            "mode": workspace_mode,
        },
        "project": {
            "name": project_name,
            "goal": project_goal,
        },
        "agent": {},  # filled below
        "task": {},    # filled below
    }


def run_wizard_with_registry(
    registry: ScenarioRegistry,
    workspace_path: Path,
    project_name: str,
    project_goal: str,
    task_goal: str,
    priority: str = "normal",
    workspace_mode: str = "single",
    force_role_id: str | None = None,
) -> dict[str, Any]:
    """Stage the JSON contracts using a multi-scenario registry.

    This is the **preferred** entry point for new code: it works across
    any number of scenarios loaded via ``runtime_05/scenarios/*.yaml``
    manifests. The legacy :func:`run_wizard` (single-corpus BC) stays for
    callers that already reference the old signature.

    Returns keys: ``paths``, ``merged_path``, ``contracts``, ``merged``,
    ``selected_scenario_id``, ``selected_role_id``, ``resolved_model``.
    """
    workspace_path = Path(workspace_path)
    project_dir = workspace_path / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    levels = _seed_levels_for_registry(
        workspace_path=workspace_path,
        project_name=project_name,
        project_goal=project_goal,
        workspace_mode=workspace_mode,
    )
    levels["system"]["scenarios_registered"] = [
        sc.scenario_id for sc in registry.list_scenarios()
    ]

    if force_role_id:
        match = registry.find_role(force_role_id)
        if match is None:
            raise KeyError(
                f"force_role_id {force_role_id!r} not found across any scenario"
            )
        scenario, role = match
    else:
        scored = registry.propose_roles(project_goal, top_n=3)
        if not scored:
            raise RuntimeError(
                "no roles registered across any loaded scenario — "
                "check FREEBUFF_SCENARIOS_DIR / runtime_05/scenarios/"
            )
        scenario, role, _score = scored[0]

    levels["agent"] = build_agent_json_for_registry(registry, scenario, role)
    levels["task"] = build_task_json_for_registry(registry, scenario, role, task_goal, priority=priority)
    resolved_model = resolve_assigned_model(
        levels["task"],
        capabilities=scenario.routing_hint(role.role_id),
    )
    levels["task"]["assigned_model"] = resolved_model

    merged = CascadeContract.merge(levels)
    paths: dict[str, Path] = {}
    for level in CascadeContract.LEVELS:
        path = project_dir / f"{level}.json"
        path.write_text(
            json.dumps(levels[level], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths[level] = path
    merged_path = project_dir / "merged.json"
    merged_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    errors = CascadeContract.validate_levels(levels)
    if errors:
        (project_dir / "validation_errors.txt").write_text(
            "\n".join(errors), encoding="utf-8",
        )
    return {
        "paths": paths,
        "merged_path": merged_path,
        "contracts": levels,
        "merged": merged,
        "selected_scenario_id": scenario.scenario_id,
        "selected_role_id": role.role_id,
        "resolved_model": resolved_model,
    }


__all__ = [
    "score_role_match",
    "propose_roles",
    "build_agent_json",
    "build_task_json",
    "run_wizard",
    "build_agent_json_for_registry",
    "build_task_json_for_registry",
    "run_wizard_with_registry",
]
