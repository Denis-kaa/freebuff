"""core_02/scenario.py — Generic Scenario abstraction.

A Scenario is anything that can answer ``list_roles()``, ``load_role_text(role_id)``,
and ``routing_hint(role_id)`` — typically a role corpus. The
:class:`ScenarioRegistry` (in ``core_02/scenario_registry.py``) holds several
of these and queries them all when the wizard asks "which role fits this
task?".

Concrete subclass today: ``BlueprintScenario`` (= ``BlueprintCorpus`` BC
alias — see ``core_02/blueprint_v3.py``). The class satisfies the Scenario
ABC surface so the registry treats it polymorphically alongside any future
scenario types (``RemoteScenario``, ``PluginScenario``, ...).

Design rationale lives in ``core_02/LESSONS.md`` (CON-9: ScenarioRegistry).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Role:
    """Generic role data — scenario-agnostic.

    Concrete scenarios project their internal representation into this
    dataclass so the registry API stays uniform across scenario types.
    Fields:

    * ``scenario_id`` — which scenario this role belongs to (registry-wide unique).
    * ``role_id`` — id within the scenario (must be unique within that scenario,
      may collide across scenarios — see ``ScenarioRegistry.find_role``).
    * ``title`` — human-readable label.
    * ``role_type`` — implementation / analysis / architecture / ... (Mirrors
      Kwork Arbitr v3 categories; new categories can be added per scenario).
    * ``file`` — source path inside the scenario (relative to scenario root).
    * ``routing_hint`` — capability strings for SmartRouter (subset of
      ``core_02.router.ModelCatalog`` capabilities).
    * ``extra`` — scenario-type-specific metadata (open dict).
    """

    scenario_id: str
    role_id: str
    title: str
    role_type: str
    file: str
    routing_hint: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)


class Scenario(ABC):
    """Base for any scenario type.

    A Scenario is a (possibly mutable) source of roles that the wizard can
    match against user queries. It exposes:

    * :attr:`scenario_id` — unique id used by registry cross-references.
    * :attr:`display_name` — human-readable label for UI.
    * :meth:`list_roles` — all roles registered in this scenario (returns
      :class:`Role` objects, not framework-specific types).
    * :meth:`load_role_text` — plain-text content of the role definition
      concatenated for fuzzy-match keyword overlap. Subclass may override to
      claim role sections, ignore xml wrap, etc.
    * :meth:`routing_hint` — SmartRouter capability strings per role.
    * :meth:`validate` — scenario-level validation errors. Empty list = OK;
      non-empty triggers ``ScenarioRegistry.validate_all`` to surface them.

    Constructor signature is intentionally freeform: subclasses declare the
    kwargs they need (typically ``scenario_id: str`` + ``root: Path``).
    ``ScenarioRegistry._instantiate`` passes the manifest fields as kwargs.
    """

    @property
    @abstractmethod
    def scenario_id(self) -> str:
        """Unique id used by registry cross-references."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable label for UI."""

    @abstractmethod
    def role_objects(self) -> list[Role]:
        """Return all roles exposed by this scenario as :class:`Role` objects.

        Distinct from any legacy ``roles()`` / ``list_roles()`` / ``role_dicts()``
        methods a concrete scenario may already expose — those keep
        scenario-specific return shapes (tuple, dict, raw entries) for BC
        callers. The registry uses this method exclusively to project
        scenario roles into the uniform ``Role`` shape.

        Naming choice: ``role_objects()`` (not ``roles()``) to avoid collision
        with legacy methods like ``BlueprintCorpus.roles() -> list[dict]``.
        See LESSONS ANTI-7b / PB-8 for the rationale.
        """

    @abstractmethod
    def load_role_text(self, role_id: str) -> str:
        """Return concatenated plain-text content of a role for fuzzy match.

        Subclasses choose how to compose this (header ROLE, system_role,
        main_objective...). For broken/missing role the contract is "empty
        string" (never raise) so fuzzy-match can skip the role gracefully.
        """

    @abstractmethod
    def routing_hint(self, role_id: str) -> list[str]:
        """Return SmartRouter capability strings for ``role_id``."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Return scenario-level validation errors (empty list = OK).

        Called by :class:`ScenarioRegistry.validate_all`. Subclasses should
        raise during init for hard failures and keep this method for soft
        warnings (e.g. cross-scenario duplicate role ids).
        """


@dataclass(frozen=True)
class ScenarioManifest:
    """Loaded YAML manifest — NOT instantiated yet.

    Built by :meth:`from_yaml`. The registry then dispatches on
    ``scenario_type`` to construct a concrete :class:`Scenario` subclass.
    """

    scenario_id: str
    scenario_type: str           # e.g. "blueprint_v3"
    display_name: str
    root: Path
    enabled: bool = True
    capabilities: tuple[str, ...] = ()  # scenario-level (distinct from per-role routing_hint)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "ScenarioManifest":
        """Parse a YAML file into a :class:`ScenarioManifest`.

        Required top-level keys: ``id`` (str), ``type`` (str), ``root`` (str path).
        Optional: ``display_name`` (defaults to id), ``enabled`` (defaults true),
        ``capabilities`` (list[str]), ``metadata`` (dict).
        """
        import yaml  # local — missing PyYAML only fails here, not at module-import time
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: manifest must be a YAML mapping at top level")
        missing = [k for k in ("id", "type", "root") if not raw.get(k)]
        if missing:
            raise ValueError(f"{path}: required keys missing: {missing}")
        sid = str(raw["id"])
        stype = str(raw["type"])
        sroot = Path(str(raw["root"])).expanduser().resolve()
        return cls(
            scenario_id=sid,
            scenario_type=stype,
            display_name=str(raw.get("display_name", sid)),
            root=sroot,
            enabled=bool(raw.get("enabled", True)),
            capabilities=tuple(raw.get("capabilities") or ()),
            metadata=dict(raw.get("metadata") or {}),
        )


__all__ = ["Role", "Scenario", "ScenarioManifest"]
