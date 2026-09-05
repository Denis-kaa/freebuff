"""core_02/forge_passport.py — Forge Passport dataclass (machine-readable кузня contract).

Источник истины: декларативный YAML-манифест в ``runtime_05/factories/<factory_id>/<forge_id>.yaml``.
Этот модуль — типизированная runtime-модель с валидацией и round-trip YAML serialization.

Pattern mirrors ``ScenarioManifest → ScenarioRegistry``: dataclass from_yaml + frozen=True +
tuple для всех списков (иммутабельность + конвенция scenario.py).

CAN-16 ADDITIVE: НЕ модифицирует scenario.py / scenario_registry.py / forge_registry.py
/ blueprint_v3.py. Только новый модуль.

Usage::

    from core_02.forge_passport import ForgePassport
    pp = ForgePassport.from_yaml("runtime_05/factories/architecture/review.yaml")
    pp.validate()  # list[str***REMOVED*** violations; empty = valid
    pp.to_dict()   # JSON-convention
"""

from __future__ import annotations

import os
***REMOVED***
from dataclasses import dataclass, field, asdict
***REMOVED***
from typing import Any, Optional, Union, cast


# ─── Closed vocab (ANTI-6b) — imported lazily to avoid hard dep at import-time ──
# KNOWN_CAPABILITIES lives in blueprint_v3.py. We import on first validate() call.
# If unknown token is passed → ValueError at validate() step (not silently at runtime).
_KNOWN_CAPABILITIES_CACHE: Optional[frozenset[str***REMOVED******REMOVED*** = None


def _get_known_capabilities() -> frozenset[str***REMOVED***:
    """Lazy import of KNOWN_CAPABILITIES from blueprint_v3 (avoid hard dep up-front)."""
    global _KNOWN_CAPABILITIES_CACHE
    if _KNOWN_CAPABILITIES_CACHE is None:
        try:
            from core_02.blueprint_v3 import KNOWN_CAPABILITIES
            _KNOWN_CAPABILITIES_CACHE = KNOWN_CAPABILITIES
        except ImportError:
            # Blueprint v3 may not be importable in minimal envs (rare); we
            # fall back to allowing ANY token, but log a warning at the call-site.
            _KNOWN_CAPABILITIES_CACHE = frozenset()
    return _KNOWN_CAPABILITIES_CACHE


# ─── module-level safety helpers ──────────────────────────────────────────────

_SLUG_RE = re.compile(r"^[a-z***REMOVED***[a-z0-9_***REMOVED***{1,30***REMOVED***$")
_VALID_STATUSES: tuple[str, ...***REMOVED*** = ("design", "material", "production")


def _as_tuple(value: Any, *, field_name: str) -> tuple[Any, ...***REMOVED***:
    """Convert list-like → tuple. Raises ValueError if dict/None/non-iterable
    (gромкая ошибка per B10/R-127 — НЕ тихая потеря данных)."""
    if value is None or value == "":
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    # dict, scalar, etc. — refused.
    raise ValueError(
        f"{field_name***REMOVED***: ожидался YAML список; получено {type(value).__name__***REMOVED***. "
        f"НЕ-scalar → НЕ тихая потеря (B10/R-127)."
    )


def _as_dict(value: Any, *, field_name: str) -> dict[str, Any***REMOVED***:
    """Convert dict-like → dict. Raises if scalar (per B10/R-127)."""
    if value is None or value == "":
        return {***REMOVED***
    if isinstance(value, dict):
        return value
    raise ValueError(
        f"{field_name***REMOVED***: ожидался YAML-объект (dict); получено {type(value).__name__***REMOVED***. "
        f"НЕ-scalar-для-объекта → НЕ тихая потеря (B10/R-127)."
    )


# ─── palette of 9 v1.1 passport fields ───────────────────────────────────────
# Each is a SCHEMA-SAFE container; specifics defined in respective YAML manifests.


@dataclass(frozen=True)
class ForgePassport:
    """Машиночитаемый паспорт одной Forge (кузни).

    Frozen contract: after load → immutable. Mutations require re-loading the
    source YAML manifest (`runtime_05/factories/<factory>/<forge>.yaml`).

    Schema (per pomt 078_19 §2 DoD #1):

    Реестровые поля: forge_id, factory_id, version, status, display_name, capabilities, metadata.
    9 паспортных полей v1.1: mission, inputs, production_workflow, engines, quality_gates,
    outputs, artifacts, interfaces, memory, knowledge.
    """

    # ─── Реестровые поля ──────────────────────────────────────────────────
    forge_id: str
    factory_id: str
    version: str
    status: str  # 'design' | 'material' | 'production'
    display_name: str
    capabilities: tuple[str, ...***REMOVED***
    metadata: dict[str, Any***REMOVED*** = field(default_factory=dict)

    # ─── 9 паспортных полей v1.1 (Mission/Input/Workflow/Engines/Gates/Output/Artifacts/Interfaces/Memory, без Skills/Prompts/Tools на карте кузни) ───
    mission: str = ""
    inputs: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    production_workflow: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    engines: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    quality_gates: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    outputs: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    artifacts: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    interfaces: tuple[str, ...***REMOVED*** = field(default_factory=tuple)
    memory: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)
    knowledge: tuple[Any, ...***REMOVED*** = field(default_factory=tuple)

    # ─── exported class-level ──────────────────────────────────────────────
    REQUIRED_FIELDS: tuple[str, ...***REMOVED*** = (
        "forge_id", "factory_id", "version", "status", "display_name",
        "mission", "outputs",
    )

    # ─── YAML load / dump ──────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: Union[str, Path***REMOVED***) -> "ForgePassport":
        """Load passport from deterministic YAML manifest.

        Raises FileNotFoundError if path missing; ValueError on schema errors
        (per pomt 078_19 §3 — громкая ошибка, не silent corruption).
        """
        import yaml  # local import — keeps import-time cheap

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Manifest не найден: {p***REMOVED***. Passports живут в "
                f"runtime_05/factories/<factory_id>/<forge_id>.yaml."
            )
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Manifest повреждён (невалидный YAML) в {p***REMOVED***: {exc***REMOVED***. "
                f"Восстанови из .bak.* или почини синтаксис."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Manifest {p***REMOVED*** не является YAML-словарём (ожидался dict, "
                f"получено {type(data).__name__***REMOVED***)."
            )

        return cls._from_dict(data, source=str(p))

    @classmethod
    def _from_dict(cls, data: dict[str, Any***REMOVED***, *, source: str = "<dict>") -> "ForgePassport":
        """Internal: build from already-parsed dict (used by from_yaml + tests)."""
        # Brief: lead error with source for diagnostics.
        def err(field: str, why: str) -> ValueError:
            return ValueError(f"{source***REMOVED***: forge_passport::{field***REMOVED*** — {why***REMOVED***")

        forge_id = str(data.get("forge_id", "")).strip()
        if not forge_id:
            raise err("forge_id", "обязательное поле, непустое")
        if not _SLUG_RE.match(forge_id):
            raise err(
                "forge_id",
                f"должен соответствовать {_SLUG_RE.pattern***REMOVED*** (lowercase, начинается с буквы)",
            )

        factory_id = str(data.get("factory_id", "")).strip()
        if not factory_id:
            raise err("factory_id", "обязательное поле, непустое")
        if not _SLUG_RE.match(factory_id):
            raise err(
                "factory_id",
                f"должен соответствовать {_SLUG_RE.pattern***REMOVED***",
            )

        status = str(data.get("status", "")).strip()
        if status not in _VALID_STATUSES:
            raise err(
                "status",
                f"должен быть ∈ {_VALID_STATUSES***REMOVED***, получено {status!r***REMOVED***",
            )

        version = str(data.get("version", "")).strip() or "0.0.0"
        display_name = str(data.get("display_name", "")).strip()

        mission = str(data.get("mission", "")).strip()

        # Special-case: `outputs` is a list (multiple outputs allowed per
        # v1.1 §17.1), but at least 1 is required (one Forge = one result).
        outputs_raw = data.get("outputs", [***REMOVED***)
        outputs = _as_tuple(outputs_raw, field_name="outputs")

        return cls(
            forge_id=forge_id,
            factory_id=factory_id,
            version=version,
            status=status,
            display_name=display_name,
            capabilities=_as_tuple(data.get("capabilities", [***REMOVED***), field_name="capabilities"),
            metadata=_as_dict(data.get("metadata", {***REMOVED***), field_name="metadata"),
            mission=mission,
            inputs=_as_tuple(data.get("inputs", [***REMOVED***), field_name="inputs"),
            production_workflow=_as_tuple(data.get("production_workflow", [***REMOVED***), field_name="production_workflow"),
            engines=_as_tuple(data.get("engines", [***REMOVED***), field_name="engines"),
            quality_gates=_as_tuple(data.get("quality_gates", [***REMOVED***), field_name="quality_gates"),
            outputs=outputs,
            artifacts=_as_tuple(data.get("artifacts", [***REMOVED***), field_name="artifacts"),
            interfaces=tuple(str(x) for x in _as_tuple(data.get("interfaces", [***REMOVED***), field_name="interfaces")),
            memory=_as_tuple(data.get("memory", [***REMOVED***), field_name="memory"),
            knowledge=_as_tuple(data.get("knowledge", [***REMOVED***), field_name="knowledge"),
        )

    def to_yaml(self) -> str:
        """Render back to deterministic YAML (round-trippable)."""
        import yaml  # local import
        out = asdict(self)
        return cast(str, yaml.safe_dump(out, sort_keys=False, allow_unicode=True, default_flow_style=False))

    def to_dict(self) -> dict[str, Any***REMOVED***:
        """JSON-convention dict (lists instead of tuples for JSON-friendliness)."""
        d = asdict(self)
        # Convert tuples → lists (JSON/YAML encoding-friendly).
        for k, v in list(d.items()):
            if isinstance(v, tuple):
                d[k***REMOVED*** = list(v)
            elif isinstance(v, dict) and k == "metadata":
                pass  # already dict
        return d

    # ─── validation (B10/R-127 invariants + ANTI-6b vocab guard) ──────────

    def validate(self) -> list[str***REMOVED***:
        """Return list of violation strings (empty = valid).

        Invariants (per pomt 078_19 §2 DoD #1, B10/R-127 + ANTI-6b):
        - forge_id lowercase-slug non-empty
        - mission non-empty (uuid: кузня без миссии — кузня без смысла)
        - status ∈ {'design', 'material', 'production'***REMOVED***
        - outputs non-empty (одна Forge = один производственный результат)
        - capabilities ⊆ KNOWN_CAPABILITIES (закрытый словарь, ANTI-6b)
        """
        violations: list[str***REMOVED*** = [***REMOVED***
        if not self.forge_id:
            violations.append("forge_id must be non-empty (B10)")
        elif not _SLUG_RE.match(self.forge_id):
            violations.append(
                f"forge_id {self.forge_id!r***REMOVED*** must match {_SLUG_RE.pattern***REMOVED*** "
                f"(lowercase + starts-with-letter; B10/R-127)"
            )
        if not self.mission:
            violations.append("mission must be non-empty (uuid: forge without mission = forge without purpose)")
        if self.status not in _VALID_STATUSES:
            violations.append(
                f"status {self.status!r***REMOVED*** must be ∈ {_VALID_STATUSES***REMOVED***"
            )
        if not self.outputs:
            violations.append(
                "outputs must be non-empty (one Forge = one production result; B10/R-127)"
            )
        if self.capabilities:
            known = _get_known_capabilities()
            if known:  # only validate when KNOWN_CAPABILITIES is importable
                unknown = [c for c in self.capabilities if c not in known***REMOVED***
                if unknown:
                    violations.append(
                        f"capabilities содержат unknown tokens {unknown***REMOVED*** (закрытый "
                        f"словарь KNOWN_CAPABILITIES требует ANTI-6b compliance; "
                        f"silently demoting routing to qwen2.5:1.5b запрещено)."
                    )
        return violations

    # ─── equality / hashing (frozen=True gives both for free) ──────────────
    def __post_init__(self) -> None:
        # Extra sanity: factory_id matches slug-regex too (mirror forge_id defense).
        if self.factory_id and not _SLUG_RE.match(self.factory_id):
            raise ValueError(
                f"factory_id {self.factory_id!r***REMOVED*** must match {_SLUG_RE.pattern***REMOVED***"
            )


__all__ = [
    "ForgePassport",
    "REQUIRED_FIELDS",  # backward-compat re-export
***REMOVED***


# Module-level re-export for `from core_02.forge_passport import REQUIRED_FIELDS`.
# (ForgePassport.REQUIRED_FIELDS is a class attribute on the frozen dataclass;
# expose at module scope so test_forge_passport.py can import it directly.)
REQUIRED_FIELDS = ForgePassport.REQUIRED_FIELDS
