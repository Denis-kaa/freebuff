"""core_02/scenario_registry.py — Multi-scenario registry with auto-discovery.

Loads scenario manifests (YAML) from a directory (default:
``freebuff_repo/runtime_05/scenarios/`` or ``$FREEBUFF_SCENARIOS_DIR``),
instantiates concrete :class:`Scenario` subclasses by ``type``, and exposes
cross-scenario search (``find_role``, ``propose_roles``, ``validate_all``).

Mirrors the runtime marketplace pattern in
``freebuff_plugin_03/runtime/registry.py`` for the runtime side. Same
philosophy: no core change when a new scenario type appears — the YAML
manifest + Python subclass (in the dispatch table) do all the work.

Backward compatibility:
* ``core_02/blueprint_v3.py::BlueprintCorpus`` keeps its old public API.
* :class:`BlueprintCorpus` ALSO satisfies the Scenario ABC, so the registry
  accepts it polymorphically.
* ``BlueprintScenario = BlueprintCorpus`` alias on the blueprint v3 module
  page keeps the new canonical name consistent.

Failure modes (logged + skipped unless ``silent=True`` is breached):
* Manifest YAML parse fails — record warning, skip.
* ``scenario_type`` unknown — record warning, skip.
* Duplicate ``scenario_id`` — first wins, others record a warning.
* Scenario root missing — instantiation may fail; recorded as warning.

Key invariants:
* :meth:`list_scenarios` returns only enabled, successfully-instantiated scenarios.
* :meth:`warnings` returns the load-time warnings for diagnostics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core_02.scenario import Role, Scenario, ScenarioManifest
from core_02.blueprint_v3 import BlueprintCorpus as BlueprintScenario  # BC alias


# Scenario-type → class dispatch table. New scenario types register here.
# The class MUST accept (scenario_id: str, root: Path) as kwargs.
_SCENARIO_TYPES: dict[str, type[Scenario]] = {
    "blueprint_v3": BlueprintScenario,
}


def _default_scenarios_dir() -> Optional[Path]:
    """Resolution order:

    1. ``$FREEBUFF_SCENARIOS_DIR`` env var (point at a custom scenarios dir).
    2. ``freebuff_repo/runtime_05/scenarios/`` (the canonical marketplace dir).

    Returns ``None`` if neither exists (registry will simply be empty — callers
    should treat as no-scenarios-configured).
    """
    import os
    env = os.environ.get("FREEBUFF_SCENARIOS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[1]
    default = repo_root / "runtime_05" / "scenarios"
    return default if default.exists() else None


class ScenarioRegistry:
    """Multi-scenario container with cross-scenario search.

    Parameters
    ----------
    scenarios_dir:
        Directory containing ``*.yaml`` manifests. ``None`` falls back to
        :func:`_default_scenarios_dir` resolution.
    silent:
        If True, swallow manifest-load warnings and let callers inspect via
        :meth:`warnings`. If False (default), warnings also go to stderr.
    """

    def __init__(
        self,
        scenarios_dir: Optional[Path] = None,
        silent: bool = False,
    ):
        self.scenarios_dir = scenarios_dir or _default_scenarios_dir()
        self._scenarios: dict[str, Scenario] = {}
        self._load_warnings: list[str] = []

        if self.scenarios_dir and self.scenarios_dir.exists():
            self._load_from_dir(self.scenarios_dir, silent=silent)
        elif not self.scenarios_dir:
            self._load_warnings.append(
                "no scenarios_dir resolved (neither $FREEBUFF_SCENARIOS_DIR "
                "nor runtime_05/scenarios/ available)"
            )

    # ─── loading ────────────────────────────────────────────────────────────

    def _load_from_dir(self, d: Path, silent: bool) -> None:
        """Walk ``*.yaml`` in alphabetical order; load each; emit warnings for skips."""
        import sys
        for yaml_path in sorted(d.glob("*.yaml")):
            try:
                manifest = ScenarioManifest.from_yaml(yaml_path)
            except (ValueError, Exception) as exc:
                warning = f"{yaml_path.name}: manifest parse failed — {exc}"
                self._load_warnings.append(warning)
                if not silent:
                    print(f"warning: {warning}", file=sys.stderr)
                continue
            if not manifest.enabled:
                continue
            try:
                scenario = self._instantiate(manifest)
            except (FileNotFoundError, ValueError, OSError) as exc:
                warning = f"{yaml_path.name}: instantiation failed — {exc}"
                self._load_warnings.append(warning)
                if not silent:
                    print(f"warning: {warning}", file=sys.stderr)
                continue
            if manifest.scenario_id in self._scenarios:
                warning = (
                    f"duplicate scenario_id {manifest.scenario_id!r} — "
                    f"second instance ignored (yaml={yaml_path.name})"
                )
                self._load_warnings.append(warning)
                if not silent:
                    print(f"warning: {warning}", file=sys.stderr)
                continue
            self._scenarios[manifest.scenario_id] = scenario

    def _instantiate(self, manifest: ScenarioManifest) -> Scenario:
        cls = _SCENARIO_TYPES.get(manifest.scenario_type)
        if cls is None:
            raise ValueError(
                f"unknown scenario_type {manifest.scenario_type!r}; "
                f"known types: {sorted(_SCENARIO_TYPES)}"
            )
        # Each Scenario subclass declares its own keyword signature.
        # Today only (scenario_id: str, root: Path) — extend in subclasses as needed.
        return cls(scenario_id=manifest.scenario_id, root=manifest.root)

    # ─── reading ─────────────────────────────────────────────────────────────

    def list_scenarios(self) -> list[Scenario]:
        """Return enabled, successfully-instantiated scenarios in load order."""
        return list(self._scenarios.values())

    def get(self, scenario_id: str) -> Optional[Scenario]:
        """Scenario by id; ``None`` if unknown."""
        return self._scenarios.get(scenario_id)

    def filter(self, scenario_id: str) -> "ScenarioRegistry":
        """Return a shallow-restricted view containing only ``scenario_id``.

        Replaces the previous ``__new__`` escape-hatch used in the CLI. The
        returned object is a fully-formed ``ScenarioRegistry`` (proper init,
        no private-attr mutation). Warnings are narrowed to those mentioning
        the kept scenario so diagnostics stay relevant.

        Raises ``KeyError`` if ``scenario_id`` isn't registered. The caller
        (``scripts_01/wizard.py``) checks with ``registry.get(...)`` first
        so the CLI emits a friendly error before this raises.
        """
        if scenario_id not in self._scenarios:
            raise KeyError(f"scenario_id {scenario_id!r} not registered")
        kept = self._scenarios[scenario_id]
        # Narrow warnings to entries that mention the kept scenario (or, as
        # a fallback, generic parse/instantiation warnings whose root is the
        # kept manifest).
        narrowed = [
            w for w in self._load_warnings
            if scenario_id in w or "manifest" in w
        ]
        view = ScenarioRegistry.__new__(ScenarioRegistry)  # skip __init__
        view.scenarios_dir = self.scenarios_dir
        view._scenarios = {scenario_id: kept}
        view._load_warnings = narrowed
        return view

    def find_role(self, role_id: str) -> Optional[tuple[Scenario, Role]]:
        """Cross-scenario role lookup. Returns first match or ``None``.

        If two scenarios expose the same role_id, first registered wins;
        cross-scenario collision is logged in :meth:`warnings` via per-scenario
        :meth:`Scenario.validate`.
        """
        for scenario in self._scenarios.values():
            for role in scenario.role_objects():
                if role.role_id == role_id:
                    return scenario, role
        return None

    def all_roles(self) -> list[tuple[Scenario, Role]]:
        """All (scenario, role) pairs across the registry."""
        pairs: list[tuple[Scenario, Role]] = []
        for scenario in self._scenarios.values():
            for role in scenario.role_objects():
                pairs.append((scenario, role))
        return pairs

    # ─── search ─────────────────────────────────────────────────────────────

    def propose_roles(
        self,
        query: str,
        top_n: int = 3,
    ) -> list[tuple[Scenario, Role, float]]:
        """Cross-scenario fuzzy-match by keyword overlap.

        Returns ``(scenario, role, score)`` tuples sorted by score desc.
        Fails safe: empty registry returns ``[]``; zero-score top returns
        head with first registered role + score 0.0 (deterministic).
        """
        # Local import — wizard_lib imports core_02; this keeps the dependency
        # edge one-way (registry → wizard_lib) and out of init.
        from core_02.wizard_lib import score_role_match
        scored: list[tuple[Scenario, Role, float]] = []
        for scenario, role in self.all_roles():
            text = scenario.load_role_text(role.role_id)
            score = score_role_match(query, role.role_id, role.title, text)
            scored.append((scenario, role, score))
        scored.sort(key=lambda r: (-r[2], r[0].scenario_id, r[1].role_id))
        if not scored:
            return []
        if scored[0][2] <= 0.0:
            first_scenario, first_role = self.all_roles()[0]
            scored.insert(0, (first_scenario, first_role, 0.0))
        return scored[:top_n]

    # ─── validation ─────────────────────────────────────────────────────────

    def validate_all(self) -> list[str]:
        """Aggregate errors across all loaded scenarios. Empty list = all OK."""
        errors: list[str] = []
        for sid, scenario in self._scenarios.items():
            for err in scenario.validate():
                errors.append(f"[{sid}] {err}")
        # Optional cross-scenario duplicate role_id warning (non-blocking).
        seen: dict[str, str] = {}
        for sid, scenario in self._scenarios.items():
            for role in scenario.role_objects():
                key = role.role_id
                if key in seen and seen[key] != sid:
                    errors.append(
                        f"role_id {key!r} appears in multiple scenarios "
                        f"({seen[key]}, {sid}) — find_role will return the first"
                    )
                seen[key] = sid
        return errors

    def warnings(self) -> list[str]:
        """All load-time warnings accumulated during instantiation."""
        return list(self._load_warnings)


__all__ = ["ScenarioRegistry", "_default_scenarios_dir", "_SCENARIO_TYPES"]
