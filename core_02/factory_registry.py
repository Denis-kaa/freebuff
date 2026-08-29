"""core_02/factory_registry.py — Factory Registry (auto-discovery + query API).

Источник истины: декларативные YAML-манифесты в ``runtime_05/factories/<factory_id>/``.
- ``factory.yaml`` — метаданные фабрики (НЕ дублирование паспортов);
- ``<forge_id>.yaml`` — паспорт Forge (см. ``core_02.forge_passport.ForgePassport``).

API симметрично ``ScenarioRegistry`` (см. ``core_02.scenario_registry``) и
разграничено по ``B-Rule 4/5``: FactoryRegistry ≠ ForgeRegistry (паспорта
кузен vs статусы проектов) ≠ ScenarioRegistry (мощности vs сценарии).
Никакой параллельной системы.

CAN-16 ADDITIVE: НЕ модифицирует scenario.py / scenario_registry.py /
forge_registry.py / blueprint_v3.py. Только новый модуль.

Usage::

    from core_02.factory_registry import FactoryRegistry
    r = FactoryRegistry()                                        # default runtime_05/factories/
    r = FactoryRegistry.from_env()                               # respects $FREEBUFF_FACTORIES_DIR
    factories = r.list_factories()                               # ['architecture', ...***REMOVED***
    forges   = r.list_forges("architecture")                     # [ForgePassport, ...***REMOVED***
    forge    = r.get_forge("architecture", "review")             # ForgePassport | None
    matches  = r.find_by_capability("review")                    # crosses factories

Fail-safe: битый манифест / неизвестная директория → warning, не крашится
(per pomt 078_19 §2 DoD #2). Cross-check: factory_id в манифесте == имя
директории (защита от typo); дубликаты forge_id → warning + first-wins.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
***REMOVED***
from typing import Optional, Tuple, Union

from core_02.factory_passport import FactoryPassport
from core_02.forge_passport import ForgePassport


DEFAULT_FACTORIES_DIR = Path("runtime_05/factories")
_FACTORY_METADATA_FILENAME = "factory.yaml"
_SUPPORTED_YAML_EXTENSIONS = (".yaml", ".yml")


class FactoryRegistry:
    """Машиночитаемый реестр фабрик и кузен (Forge Passport source-of-truth loader).

    Constructor triggers auto-discovery ONE TIME (eager) — surface warnings via
    ``warnings()`` API instead of failing. Use ``reload()`` to re-discover after
    adding new YAML manifests at runtime (e.g. on hot-reload).
    """

    def __init__(self, factories_dir: Optional[Union[str, Path***REMOVED******REMOVED*** = None):
        self.factories_dir = (
            Path(factories_dir) if factories_dir is not None else DEFAULT_FACTORIES_DIR
        )
        self._passports: dict[str, ForgePassport***REMOVED*** = {***REMOVED***  # key: factory_id/forge_id (slash-separated)
        self._factory_meta: dict[str, dict***REMOVED*** = {***REMOVED***        # factory_id -> factory.yaml parsed dict
        self._factory_passports: dict[str, FactoryPassport***REMOVED*** = {***REMOVED***  # C-2: типизированные паспорта фабрик
        self._warnings: list[str***REMOVED*** = [***REMOVED***
        self._reload()

    @classmethod
    def from_env(cls) -> "FactoryRegistry":
        """Construct from $FREEBUFF_FACTORIES_DIR (freebuff routing env var)."""
        env_dir = os.environ.get("FREEBUFF_FACTORIES_DIR")
        return cls(env_dir) if env_dir else cls()

    # ─── discovery ────────────────────────────────────────────────────────

    def _reload(self) -> None:
        """Walk factories_dir; load each factory.yaml + each <forge>.yaml."""
        self._passports.clear()
        self._factory_meta.clear()
        self._factory_passports.clear()
        self._warnings.clear()

        if not self.factories_dir.exists():
            self._warnings.append(
                f"factories_dir не существует: {self.factories_dir***REMOVED***. "
                f"Создайте runtime_05/factories/<factory_id>/ и разместите манифесты. "
                f"Registry пустой."
            )
            return

        if not self.factories_dir.is_dir():
            self._warnings.append(
                f"factories_dir не является директорией: {self.factories_dir***REMOVED***. "
                f"Registry пустой."
            )
            return

        for factory_dir in sorted(self.factories_dir.iterdir()):
            if not factory_dir.is_dir() or factory_dir.name.startswith("."):
                continue

            factory_id_dirname = factory_dir.name

            # 1) load factory.yaml (metadata, не паспорт)
            factory_yaml = factory_dir / _FACTORY_METADATA_FILENAME
            if not factory_yaml.exists():
                self._warnings.append(
                    f"{factory_dir***REMOVED***: factory.yaml отсутствует. "
                    f"Каждая фабрика обязана иметь factory.yaml (метаданные)."
                )
                self._factory_meta[factory_id_dirname***REMOVED*** = {***REMOVED***
            else:
                try:
                    import yaml
                    meta = yaml.safe_load(factory_yaml.read_text(encoding="utf-8"))
                    if not isinstance(meta, dict):
                        self._warnings.append(
                            f"{factory_yaml***REMOVED***: не словарь YAML (получено "
                            f"{type(meta).__name__***REMOVED***). Пропускаем метаданные."
                        )
                    else:
                        meta_factory_id = str(meta.get("factory_id", "")).strip()
                        if meta_factory_id and meta_factory_id != factory_id_dirname:
                            self._warnings.append(
                                f"{factory_yaml***REMOVED***: factory_id {meta_factory_id!r***REMOVED*** != "
                                f"имя директории {factory_id_dirname!r***REMOVED***. Cross-check защита."
                            )
                        # Use directory name as canonical factory_id for the registry index.
                        self._factory_meta[factory_id_dirname***REMOVED*** = meta
                        # C-2 (roadmap): типизированный паспорт фабрики (аддитивно).
                        # Ошибка паспорта → warning, raw meta сохраняется (fail-safe).
                        try:
                            self._factory_passports[factory_id_dirname***REMOVED*** = \
                                FactoryPassport._from_dict(meta, source=str(factory_yaml))
                        except ValueError as exc:
                            self._warnings.append(
                                f"{factory_yaml***REMOVED***: factory_passport невалиден ({exc***REMOVED***). "
                                f"Паспорт фабрики не зарегистрирован (raw meta сохранена)."
                            )
                except (ValueError, OSError, yaml.YAMLError) as exc:
                    self._warnings.append(
                        f"{factory_yaml***REMOVED***: повреждён или не читается ({exc***REMOVED***). Пропускаем."
                    )

            # 2) load all <forge_id>.yaml files (excluding factory.yaml itself)
            for forge_path in sorted(factory_dir.iterdir()):
                if not forge_path.is_file():
                    continue
                if forge_path.suffix not in _SUPPORTED_YAML_EXTENSIONS:
                    continue
                if forge_path.name == _FACTORY_METADATA_FILENAME:
                    continue
                # Conventionally, manifest files = single-forge documents named
                # <forge_id>.yaml. We also support scenario-style multi-forge
                # manifests via forge_id field — but in current schema each
                # file maps to exactly one forge (matches pomt 078_19 §1).
                self._load_one_forge(forge_path, factory_id_dirname)

    def _load_one_forge(self, path: Path, factory_id_dirname: str) -> None:
        try:
            passport = ForgePassport.from_yaml(path)
        except (FileNotFoundError, ValueError, OSError) as exc:
            self._warnings.append(
                f"{path***REMOVED***: невалидный manifest ({exc***REMOVED***). Пропускаем."
            )
            return

        # Cross-check: passport's factory_id field == directory name.
        if passport.factory_id != factory_id_dirname:
            self._warnings.append(
                f"{path***REMOVED***: forge_passport.factory_id {passport.factory_id!r***REMOVED*** != "
                f"имя директории {factory_id_dirname!r***REMOVED***. "
                f"Cross-check защита (защита от typo; registry использует "
                f"директорное имя как canonical)."
            )
            # Still register under directory name (single-source-of-truth).
            # Operationally we trust the filesystem layout, but warn loudly.

        key = f"{factory_id_dirname***REMOVED***/{passport.forge_id***REMOVED***"
        if key in self._passports:
            existing_path = self._passports[key***REMOVED***  # for diagnostics
            self._warnings.append(
                f"{path***REMOVED***: дубликат forge_id {passport.forge_id!r***REMOVED*** в фабрике "
                f"{factory_id_dirname!r***REMOVED*** (уже зарегистрирован: "
                f"{getattr(existing_path, '__source__', '?')***REMOVED***). "
                f"First-wins (existing сохраняется; новый пропускается)."
            )
            return

        self._passports[key***REMOVED*** = passport

    def reload(self) -> None:
        """Re-discover from disk (call after manually adding/editing manifests)."""
        self._reload()

    # ─── query API ────────────────────────────────────────────────────────

    def list_factories(self) -> list[str***REMOVED***:
        """Sorted list of factory_ids present in registry."""
        return sorted(self._factory_meta.keys())

    def list_forges(self, factory_id: str) -> list[ForgePassport***REMOVED***:
        """Sorted list of ForgePassports for a given factory_id.

        Returns empty list if factory_id not in registry (no error — matches
        ScenarioRegistry semantics).

        Note: factories whose factory.yaml is missing are still registered
        as empty-dict placeholders (graceful-degrade per F2 fix). Their forge
        list is empty here until metadata is added.
        """
        prefix = f"{factory_id***REMOVED***/"
        return sorted(
            (p for k, p in self._passports.items() if k.startswith(prefix)),
            key=lambda x: x.forge_id,
        )

    def get_forge(self, factory_id: str, forge_id: str) -> Optional[ForgePassport***REMOVED***:
        """Lookup by (factory_id, forge_id) — returns None if missing."""
        return self._passports.get(f"{factory_id***REMOVED***/{forge_id***REMOVED***")

    def find_by_capability(self, capability: str) -> list[ForgePassport***REMOVED***:
        """Bridge to Scenario Engine §6.2 (CapabilityRef resolution).

        Returns sorted list of ForgePassports whose `capabilities` tuple
        contains the requested token. Empty list if no match.
        """
        return sorted(
            (p for p in self._passports.values() if capability in p.capabilities),
            key=lambda x: (x.factory_id, x.forge_id),
        )

    def all_forges(self) -> list[ForgePassport***REMOVED***:
        """Sorted list of all ForgePassports in registry."""
        return sorted(
            self._passports.values(),
            key=lambda x: (x.factory_id, x.forge_id),
        )

    # ─── C-2: FactoryPassport + capability-каталог + селекция (roadmap C-2) ──
    # Полноценный FactoryRegistry: типизированный паспорт factory.yaml +
    # factory-level capability-каталог + API селекции (разблокирует Factory-путь
    # в цикле: opportunity-capability → factory → forge).

    def get_factory(self, factory_id: str) -> Optional[FactoryPassport***REMOVED***:
        """C-2: типизированный паспорт фабрики (factory.yaml). None если отсутствует/невалиден."""
        return self._factory_passports.get(factory_id)

    def factory_capabilities(self, factory_id: str) -> tuple[str, ...***REMOVED***:
        """C-2: capability-каталог фабрики = union factory.yaml capabilities + forge passports.

        Dedup + sorted (детерминированный порядок для traceability).
        """
        caps: set[str***REMOVED*** = set()
        fp = self._factory_passports.get(factory_id)
        if fp is not None:
            caps.update(fp.capabilities)
        for p in self.list_forges(factory_id):
            caps.update(p.capabilities)
        return tuple(sorted(caps))

    def find_factories_by_capability(self, capability: str) -> list[FactoryPassport***REMOVED***:
        """C-2: фабрики, чей capability-каталог (union factory.yaml + forge passports) содержит токен.

        Использует агрегированный ``factory_capabilities()`` — фабрика находится,
        если capability объявлена в factory.yaml ИЛИ в паспортах её кузен.
        """
        return sorted(
            (
                fp for fp in self._factory_passports.values()
                if capability in self.factory_capabilities(fp.factory_id)
            ),
            key=lambda x: x.factory_id,
        )

    def select_forge(
        self,
        capability: str,
        prefer_status: Optional[str***REMOVED*** = None,
    ) -> Optional[Tuple[FactoryPassport, ForgePassport***REMOVED******REMOVED***:
        """C-2: лучшая (factory, forge) пара по capability — разблокирует Factory-путь.

        Status-priority: production(3) > material(2) > design(1) на factory затем forge.
        ``prefer_status`` — минимальный status-фильтр (напр. 'material' → только
        material/production). Детерминированный tie-break: (factory_id, forge_id).
        Возвращает None если нет пары с capability.

        PHASE 12 G-11.6 (CANONICAL_ENGINE_ROUTING_V1.md): the ``code`` capability is
        canonically bound to ``(test, verifier)`` per Phase 11 TestFactory manifest.
        The status-priority policy here (production > material > design) already
        returns ``(test, verifier)`` deterministically because TestFactory is the
        only factory whose manifests declare the ``code`` capability token (Phase 11
        universality proof, test_15 META-TEST). No special case needed — defense-in-
        depth is achieved by the consistent status priority + tie-break. This
        docstring is the audit trail for Phase 12 G-11.6 closure; future contributors
        should consult ``docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md``
        before making ``code``-related routing changes.
        """
        _rank = {"design": 1, "material": 2, "production": 3***REMOVED***
        min_rank = _rank.get(prefer_status, 0) if prefer_status else 0
        best: Optional[Tuple[FactoryPassport, ForgePassport***REMOVED******REMOVED*** = None
        best_key: Optional[Tuple[int, int, str, str***REMOVED******REMOVED*** = None
        for fp in self._factory_passports.values():
            if _rank.get(fp.status, 0) < min_rank:
                continue
            for fg in self.list_forges(fp.factory_id):
                if capability not in fg.capabilities:
                    continue
                key = (_rank.get(fp.status, 0), _rank.get(fg.status, 0), fp.factory_id, fg.forge_id)
                if best_key is None or key > best_key:
                    best = (fp, fg)
                    best_key = key
        return best
    def resolve_by_policy(
        self,
        capability: str,
    ) -> Optional["CapabilityResolutionPolicy"***REMOVED***:
        """C-2 / Phase 13 G-11.6: programmatic lookup of capability routing policy.

        Returns the canonical factory/forge pair + workshop metadata for a
        declared capability, or ``None`` if no policy is registered. Backward-
        compatible: use ``select_forge()`` if you only need the (factory, forge)
        pair; use ``resolve_by_policy()`` if you need full provenance (rationale
        + decision_date + decided_by).

        Phase 13 G-11.6 ADDS this method as the canonical programmatic lookup;
        ``select_forge()`` is preserved for backward compatibility.
        """
        return CODE_RESOLUTION_POLICY.get(capability)


    def capability_catalog(self) -> dict[str, list[str***REMOVED******REMOVED***:
        """C-2: полный каталог capability → sorted factory_ids (union factory.yaml + forge passports)."""
        catalog: dict[str, set[str***REMOVED******REMOVED*** = {***REMOVED***
        for fp in self._factory_passports.values():
            for cap in self.factory_capabilities(fp.factory_id):
                catalog.setdefault(cap, set()).add(fp.factory_id)
        return {cap: sorted(fids) for cap, fids in sorted(catalog.items())***REMOVED***

    # ─── validation surfaces ──────────────────────────────────────────────

    def validate_all(self) -> list[str***REMOVED***:
        """Per-passport validate() over the whole registry.

        Returns flat list of violations (empty = perfectly valid). Each
        violation is prefixed with `<path>: ` for diagnostics.
        """
        violations: list[str***REMOVED*** = [***REMOVED***
        for k, p in self._passports.items():
            for v in p.validate():
                violations.append(f"{k***REMOVED***: {v***REMOVED***")
        return violations

    def warnings(self) -> list[str***REMOVED***:
        """Advisory warnings collected during _reload (manifest issues, dupes)."""
        return list(self._warnings)




@dataclass(frozen=True)
class CapabilityResolutionPolicy:
    """Frozen dataclass: capability → canonical (factory_id, forge_id) + workshop metadata.

    Used by Phase 13 G-11.6 to formalize the routing policy table. The Workshop
    transcript in ``docs_10/engineering-memory/CANONICAL_ENGINE_ROUTING_V1.md``
    documents the decision rationale and participants. Invariant I-4:
    ``code`` capability is canonically bound to ``(test, verifier)`` per Phase
    11 TestFactory universality proof. New policies MUST come from a fresh
    G-11.6 workshop reconvene (CAN-16 ADDITIVE).

    Additive (CAN-16): does NOT replace ``select_forge()`` — coexisting API.
    """

    capability: str
    factory_id: str
    forge_id: str
    status_min: str
    rationale: str
    decided_by: str
    decision_date: str  # ISO 8601 date


# Phase 13 G-11.6 (CANONICAL_ENGINE_ROUTING_V1.md §8): formal policy table.
# Additive: docstring audit-trail remains in select_forge for historical auditors,
# this typed struct is the programmatic single source of truth for policy lookup.
CODE_RESOLUTION_POLICY: dict[str, CapabilityResolutionPolicy***REMOVED*** = {
    "code": CapabilityResolutionPolicy(
        capability="code",
        factory_id="test",
        forge_id="verifier",
        status_min="design",
        rationale=(
            "Phase 11 TestFactory universality proof (test_15 META-TEST asserts "
            "factories == {'content', 'research', 'test'***REMOVED*** strict set equality). "
            "Status-priority tie-break (production > material > design) plus "
            "deterministic (factory_id, forge_id) tie-break yield canonical "
            "(test, verifier). Defense-in-depth via SI hard-gate."
        ),
        decided_by="Phase 13 G-11.6 capability resolution workshop (3-author)",
        decision_date="2026-08-18",
    ),
***REMOVED***


__all__ = ["FactoryRegistry", "DEFAULT_FACTORIES_DIR", "CapabilityResolutionPolicy", "CODE_RESOLUTION_POLICY"***REMOVED***
