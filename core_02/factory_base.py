#!/usr/bin/env python3
"""core_02/factory_base.py — BaseFactory template (Phase 12, ADR-013).

Base class for content/research/test domain-specific Factory adapters.
Extracted from the 3 near-identical ~400-line clones (scripts_01/content_factory,
scripts_01/research_factory, scripts_01/test_factory) created during Phase 9/10/11.

Each subclass declares ONLY:
- Class-level constants (CAPABILITIES, ROLE_IDS, ARTIFACT_KIND, ID_PREFIX,
  TAG_PREFIX, TITLE_PREFIX, PROG, FACTORY_ID).
- The domain-specific ``normalize_input(opp)`` method.

BaseFactory owns:
- Lazy import helpers (factory_registry / forge_facade / memory_store / project).
- ``resolve(capability)`` — capability → (FactoryPassport, ForgePassport) via FactoryRegistry.
- ``build_execution_request(opp, capability)``.
- ``execute(opp, *, dry_run, project_root, event_bus)`` — vertical slice.
- ``normalize_output(run, opp, request)`` — ChainRun → artifact dict.
- ``_accumulate(opp, artifact, run, *, event_bus)`` — MemoryStore + LearningLoop.
- ``_derive_capability(opp)`` staticmethod.
- ``_resolve_project(opp, *, project_root)`` staticmethod.
- ``_new_id()`` (uses ``cls.ID_PREFIX``).
- Module-level ``_LAZY_IMPORT_ERRORS`` DEPRECATED shim (v5.189.32, ADR-015):
  backed by ``__LAZY_IMPORT_ERRORS``, never appended to — use
  ``inst._import_warnings`` (per-instance) instead; external access fires
  DeprecationWarning via PEP 562 module __getattr__ (v5.189.33).
- ExecutionRequest dataclass (single source of truth).
- CLI helpers: ``_cli_resolve(cls, args)``, ``_cli_run(cls, args)``, ``make_argparser()``, ``main()``.

Charles of contract (Phase 9/10/11 invariants preserved):
- НЕ является content-движком: производство — через существующий ForgeFacade.
- CAN-16 ADDITIVE: НЕ модифицирует ForgePipeline / ForgeFacade / Blueprint / ScenarioIntelligence.
- Fail-safe: try/except, dict {ok, …} payload, exit 0/1/2.
- ID-prefix, tag prefix, title prefix через class-level constants.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import uuid
import warnings
from dataclasses import dataclass, asdict
}
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports — PHASE 13 G-13.1 (v5.189.32, ADR-015):
# Per-instance warnings are canonical (BaseFactory.__init__ sets
# self._import_warnings = []). The module-level singleton is kept as a
# DEPRECATED shim for any external consumer that imports
# `_LAZY_IMPORT_ERRORS` from this module; it is no longer appended to from
# within BaseFactory methods. See ADR-015 for migration rationale.
#
# PHASE 14 hardening (v5.189.33 sub-step): rename backing list to
# ``__LAZY_IMPORT_ERRORS`` (double-underscore prefix) so the
# PEP 562 module-level __getattr__ fires on every imported/access of
# ``_LAZY_IMPORT_ERRORS`` and emits a one-shot ``DeprecationWarning``
# pointing at ``inst._import_warnings``. The exported symbol name is
# preserved (still in __all__) so the migration path is transparent.
__LAZY_IMPORT_ERRORS: List[str] = []  # backing for deprecated shim


def __getattr__(name: str) -> Any:
    """PEP 562 module-level __getattr__: intercept any access of
    ``_LAZY_IMPORT_ERRORS`` from outside this module and emit a
    ``DeprecationWarning`` pointing at ``inst._import_warnings``.

    Behavior:
    *   First import (`from core_02.factory_base import _LAZY_IMPORT_ERRORS`)
        fires the warning (via stacklevel=2 → points at the call site).
    *   Per-Python warning caching, the default `default` filter shows it
        once per source location, so it does not flood.
    *   Internal subclasses NO LONGER import this symbol (v5.189.32),
        so they are unaffected.
    *   pytest-friendly: filterable via ``-W error::DeprecationWarning``
        or ``filterwarnings(["ignore", ..., DeprecationWarning, ...)``
        in pytest config; tests can also use
        ``warnings.catch_warnings(record=True)`` to assert emission.
    """
    if name == "_LAZY_IMPORT_ERRORS":
        warnings.warn(
            (
                "core_02.factory_base._LAZY_IMPORT_ERRORS is deprecated since v5.189.32; "
                "use ``inst._import_warnings`` on a BaseFactory (or subclass) instance instead. "
                "See ADR-015 for migration rationale."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return __LAZY_IMPORT_ERRORS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

DEFAULT_DATA_PATH = Path("data_13/opportunities.yaml")
DEFAULT_MEMORY_DB = Path("data_13/context.db")
DEFAULT_FACTORIES_DIR = Path("runtime_05/factories")

# Default class-level constants (subclasses override).
DEFAULT_CAPABILITIES: Tuple[str, ...] = ()
DEFAULT_ROLE_IDS: Tuple[str, ...] = (
    "explainer",
    "documenter",
    "retrospective",
)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _lazy_import(module_name: str, attr: str) -> Any:
    """Lazy import с top-level fallback (CLI-контекст)."""
    try:
        return getattr(__import__(module_name, fromlist=[attr]), attr)
    except ImportError:
        bare = module_name.rsplit(".", 1)[-1]
        try:
            return getattr(__import__(bare, fromlist=[attr]), attr)
        except ImportError:
            return None


# ─── Execution request (Factory → Forge) ────────────────────────────────────

@dataclass
class ExecutionRequest:
    """Нормализованный запрос исполнения от Factory к ForgeFacade.

    ЕДИНЫЙ dataclass для всех доменов (Phase 12 ADR-013: единый контракт).
    """

    opportunity_id: str
    project_id: str
    capability: str
    factory_id: str
    forge_id: str
    role_ids: Tuple[str, ...]
    inputs: Dict[str, Any]
    output_spec: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── BaseFactory ─────────────────────────────────────────────────────────────

class BaseFactory:
    """Базовый класс для доменных Factory-adapter (Phase 12 / ADR-013).

    Subclasses ДОЛЖНЫ переопределить:
      - ``CAPABILITIES`` (Tuple[str, ...]): capability-токены домена.
      - ``ARTIFACT_KIND`` (str): имя artifact_kind для out_spec.
      - ``ID_PREFIX`` (str): префикс id-генератора (art | res | tst).
      - ``TAG_PREFIX`` (str): tag для MemoryStore (content_factory | research_factory | test_factory).
      - ``TITLE_PREFIX`` (str): префикс title при _accumulate.
      - ``PROG`` (str): argparse prog имя (content_factory | research_factory | test_factory).
      - ``FACTORY_ID`` (str): factory_id в FactoryPassport (= directory name в runtime_05/factories/).

    Subclass ДОЛЖЕН реализовать:
      - ``normalize_input(opp)``: домен-специфичная нормализация.

    Наследуется всё остальное: lazy imports, resolve, execute, normalize_output,
    _accumulate, _derive_capability, _resolve_project, ExecutionRequest, CLI helpers.
    """

    # Pytest-collection-disabler (любой класс с Test* префиксом pytest collectирует
    # как test class; BaseFactory НЕ pytest-target. Конкретные *Factory (TestFactory,
    # ContentFactory, ResearchFactory) унаследуют этот флаг).
    __test__ = False

    # Class-level constants overridable per subclass.
    CAPABILITIES: Tuple[str, ...] = DEFAULT_CAPABILITIES
    ROLE_IDS: Tuple[str, ...] = DEFAULT_ROLE_IDS
    ARTIFACT_KIND: str = "generic_artifact"
    ID_PREFIX: str = "art"
    TAG_PREFIX: str = "factory"
    TITLE_PREFIX: str = "factory"
    PROG: str = "factory"
    FACTORY_ID: str = "factory"

    # PHASE 13 G-13.1 (ADR-015): per-instance non-shared warnings list. Class-level
    # declaration is required for mypy --strict (PEP 526 forward-reference). Instances
    # get a fresh `[]` via __init__; lazy-import failures append HERE, not the
    # legacy module-level singleton (deprecated since v5.189.32).
    _import_warnings: List[str]  # per-instance attribute (ADR-015, set via __init__)

    def __init__(
        self,
        factory_registry: Any = None,
        forge_facade: Any = None,
        memory_store: Any = None,
        learning_loop: Any = None,
    ):
        self._factory_registry = factory_registry
        self._forge_facade = forge_facade
        self._memory_store = memory_store
        self._learning_loop = learning_loop
        # PHASE 13 G-13.1 (ADR-015): per-instance warnings list. Lazy import
        # failures are appended HERE instead of the module-level singleton —
        # prevents two Factory instances from cross-polluting each other's
        # diagnostics when one of them has a missing dependency.
        self._import_warnings: List[str] = []  # fresh per instance

    # ─── registry access (lazy, fail-safe) ────────────────────────────────

    def _lazy_factory_registry(self) -> Any:
        reg = _lazy_import("core_02.factory_registry", "FactoryRegistry")
        if reg is None:
            self._import_warnings.append("factory_registry: unavailable")
            return None
        try:
            return reg(DEFAULT_FACTORIES_DIR)
        except Exception as exc:  # noqa: BLE001
            self._import_warnings.append(f"factory_registry: {exc}")
            return None

    def _lazy_forge_facade(self) -> Any:
        ff = _lazy_import("core_02.forge_facade", "ForgeFacade")
        if ff is None:
            self._import_warnings.append("forge_facade: unavailable")
            return None
        try:
            return ff()
        except Exception as exc:  # noqa: BLE001
            self._import_warnings.append(f"forge_facade: {exc}")
            return None

    def _lazy_memory_store(self) -> Any:
        if not DEFAULT_MEMORY_DB.exists():
            return None
        ms = _lazy_import("core_02.memory_store", "MemoryStore")
        if ms is None:
            # PHASE 13 G-13.1 (ADR-015) review-nit consistency: previously silent
            # fallback, now mirrors ``_lazy_factory_registry`` / ``_lazy_forge_facade``
            # by appending to per-instance warnings so all 3 lazy resources are
            # observable via ``inst._import_warnings``.
            self._import_warnings.append("memory_store: unavailable")
            return None
        try:
            return ms(DEFAULT_MEMORY_DB)
        except Exception as exc:  # noqa: BLE001
            # PHASE 13 G-13.1 (ADR-015) §Nit 1 completeness: also warn on
            # constructor-exception so all 3 lazy resources have fully symmetric
            # observable behavior (matches ``f"factory_registry: {exc}"`` /
            # ``f"forge_facade: {exc}"`` patterns). Conserves the exception in
            # the warning string so consumers can diagnose the failure mode.
            self._import_warnings.append(f"memory_store: {exc}")
            return None

    # ─── abstract ─────────────────────────────────────────────────────────

    def normalize_input(self, opp: Any) -> Dict[str, Any]:
        """Opportunity → домен-специфичный input dict.

        Subclass ДОЛЖЕН переопределить. Базовый fallback — common fields.
        """
        return {
            "title": getattr(opp, "title", "") or "",
            "description": getattr(opp, "description", "") or "",
            "source": getattr(opp, "source", "") or "",
            "source_path": getattr(opp, "source_path", "") or "",
            "evidence_path": getattr(opp, "evidence_path", "") or "",
            "provenance": dict(getattr(opp, "provenance", {}) or {}),
            "related_whims": list(getattr(opp, "related_whims", None) or []),
        }

    # ─── 1. Capability → (factory, forge) через универсальный Registry ────

    def resolve(
        self,
        capability: str,
    ) -> Optional[Tuple[Any, Any]]:
        """Capability → FactoryRegistry.select_forge → (FactoryPassport, ForgePassport).

        Domain-neutral: токен непрозрачен; Registry решает, какая фабрика/кузня
        его обслуживает. None если capability не зарегистрирована.
        """
        registry = self._factory_registry or self._lazy_factory_registry()
        if registry is None:
            return None
        try:
            pair = registry.select_forge(capability)
            if pair is None:
                return None
            return (pair[0], pair[1])
        except Exception:  # noqa: BLE001 — fail-safe
            return None

    # ─── 2-3. Execution request (Factory формирует, НЕ исполняет) ─────────

    def build_execution_request(
        self,
        opp: Any,
        capability: str,
    ) -> Optional[ExecutionRequest]:
        """normalize_input + resolve → ExecutionRequest (без исполнения).

        None если capability не разрешается (нет фабрики/кузни).
        """
        pair = self.resolve(capability)
        if pair is None:
            return None
        fp, fg = pair
        inputs = self.normalize_input(opp)
        return ExecutionRequest(
            opportunity_id=getattr(opp, "id", "") or "",
            project_id=getattr(opp, "project_id", "") or "",
            capability=capability,
            factory_id=getattr(fp, "factory_id", "") or "",
            forge_id=getattr(fg, "forge_id", "") or "",
            role_ids=self.ROLE_IDS,
            inputs=inputs,
            output_spec={
                "artifact_kind": self.ARTIFACT_KIND,
                "target": f"projects_17/{getattr(opp, 'project_id', '') or '<slug>'}/forge/",
            },
        )

    # ─── 4. Execute (через ForgeFacade — единственный boundary) ───────────

    def execute(
        self,
        opp: Any,
        *,
        dry_run: bool = False,
        project_root: Optional[Path] = None,
        event_bus: Any = None,
    ) -> Dict[str, Any]:
        """Полный vertical slice: resolve → request → ForgeFacade.run_chain → artifact.

        Возвращает dict {ok, artifact?, request?, error?}. dry_run=True НЕ
        вызывает ForgeFacade (только формирует request — evidence контракта).

        NOTE (ADR-018 §2 — семантика полей):
          - capability: закрытый токен (KNOWN_CAPABILITIES); None → fail-safe fallback.
          - factory_id / forge_id: АДВИЗОРНЫЕ (traceability в request/artifact),
            НЕ управляют исполнением. Единственный управляющий вход в
            ForgeFacade.run_chain — request.role_ids (self.ROLE_IDS).
          - В системе единый ForgeFacade/ForgePipeline; физического выбора кузни нет.
        """
        capability = self._derive_capability(opp)
        if not capability:
            return {"ok": False, "error": "no capability token on opportunity"}
        request = self.build_execution_request(opp, capability)
        if request is None:
            return {
                "ok": False,
                "error": f"capability {capability!r} not offered by any factory/forge",
                "capability": capability,
            }
        if dry_run:
            return {"ok": True, "dry_run": True, "request": request.to_dict()}

        facade = self._forge_facade or self._lazy_forge_facade()
        if facade is None:
            return {"ok": False, "error": "forge_facade unavailable", "request": request.to_dict()}

        project = self._resolve_project(opp, project_root=project_root)
        if project is None:
            return {
                "ok": False,
                "error": f"project {request.project_id!r} unresolved (projects_17/<project_id>)",
                "request": request.to_dict(),
            }

        try:
            run = facade.run_chain(
                project,
                role_ids=request.role_ids,
                project_read_only=True,
            )
        except Exception as exc:  # noqa: BLE001 — fail-safe
            return {"ok": False, "error": f"run_chain: {exc}", "request": request.to_dict()}

        artifact = self.normalize_output(run, opp, request)
        feedback = self._accumulate(opp, artifact, run, event_bus=event_bus)
        return {
            "ok": True,
            "artifact": artifact,
            "feedback": feedback,
            "request": request.to_dict(),
        }

    # ─── 5. Output normalization (ChainRun → artifact) ─────────────────────

    def normalize_output(
        self,
        run: Any,
        opp: Any,
        request: ExecutionRequest,
    ) -> Dict[str, Any]:
        """ChainRun → артефакт (path/kind/validation/overall).

        Единый Artifact-контракт (ADR-021 / ARTIFACT_CONTRACT_DESIGN_V1):
        строит ``core_02.artifact.Artifact.from_chain_run(...)`` и возвращает
        ``to_dict()`` — НАДМНОЖЕСТВО прежнего dict (все старые ключи + chain /
        stage_count / files / project_root). Сигнатура НЕ меняется (BC).
        """
        from core_02.artifact import Artifact  # lazy — нет жёсткой зависимости

        artifact = Artifact.from_chain_run(
            run,
            request,
            artifact_id=self._new_id(),
        )
        return artifact.to_dict()

    # ─── 6. ACCUMULATE + feedback (existing memory, CAN-16) ────────────────

    def _accumulate(
        self,
        opp: Any,
        artifact: Dict[str, Any],
        run: Any,
        *,
        event_bus: Any = None,
    ) -> Dict[str, Any]:
        """Artifact → MemoryStore kind=candidate + LearningLoop.

        Закрытые словари: kind='candidate' (существующий KNOWLEDGE_KINDS),
        lifecycle_stage='validated'|'raw'. Ошибки фиксируются, статус НЕ ломают.
        """
        memory = self._memory_store or self._lazy_memory_store()
        result: Dict[str, Any] = {"recorded": False, "knowledge_id": None}
        if memory is None:
            result["error"] = "memory_store unavailable"
            return result
        overall = getattr(run, "overall", "unknown") or "unknown"
        if overall == "ok":
            outcome, lifecycle, confidence = "success", "validated", 0.9
        elif overall == "degraded":
            outcome, lifecycle, confidence = "neutral", "validated", 0.7
        else:
            outcome, lifecycle, confidence = "failure", "raw", 0.5
        try:
            kid = memory.store_knowledge(
                kind="candidate",
                content=json.dumps(artifact, ensure_ascii=False, default=str),
                title=f"{self.TITLE_PREFIX}:{artifact['id']}",
                summary=(
                    f"opportunity={artifact['opportunity_id']} "
                    f"capability={artifact['capability']} "
                    f"forge={artifact['forge_id']} overall={overall}"
                ),
                tags=[self.TAG_PREFIX, artifact["capability"], artifact["opportunity_id"]],
                lifecycle_stage=lifecycle,
                status="draft",
                confidence_score=confidence,
            )
            result["knowledge_id"] = kid
            result["recorded"] = True
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"store_knowledge: {exc}"
            return result
        try:
            eid = memory.record_learning_event(
                trigger_id=f"{self.TITLE_PREFIX}:{artifact['id']}",
                context_snapshot={
                    "opportunity_id": artifact["opportunity_id"],
                    "capability": artifact["capability"],
                    "factory_id": artifact["factory_id"],
                    "forge_id": artifact["forge_id"],
                    "overall": overall,
                },
                outcome=outcome,
                lesson_id=kid,
            )
            result["learning_event_id"] = eid
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"record_learning_event: {exc}"
        if self._learning_loop is not None:
            try:
                self._learning_loop.record_feedback(kid, outcome)
            except Exception:  # noqa: BLE001
                pass
        if event_bus is not None:
            try:
                from scripts_01.event_bus import Event
                event_bus.publish(Event(
                    type="artifact.created",
                    source=self.TAG_PREFIX,
                    data=dict(artifact),
                ))
            except Exception:  # noqa: BLE001
                pass
        return result

    # ─── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _derive_capability(opp: Any) -> Optional[str]:
        """Capability-токен: provenance.capability → scenario.capability → None.

        Переиспользует opportunity_engine._derive_capability (single source of
        truth); локальный fallback только если движок недоступен (lazy import).
        """
        helper = _lazy_import("scripts_01.opportunity_engine", "_derive_capability")
        if helper is not None:
            try:
                cap = helper(opp)
                if isinstance(cap, str) and cap:
                    return cap
            except Exception:  # noqa: BLE001 — fail-safe
                pass
        prov = getattr(opp, "provenance", None) or {}
        cap = prov.get("capability") if isinstance(prov, dict) else None
        if isinstance(cap, str) and cap:
            return cap
        scenario = getattr(opp, "scenario", None)
        if isinstance(scenario, dict):
            cap = scenario.get("capability")
            if isinstance(cap, str) and cap:
                return cap
        return None

    # NOTE (Phase 13 G-13.1, ADR-015): converted from @staticmethod to instance
    # method so that lazy-import failures land in ``self._import_warnings``
    # (per-instance) instead of the deprecated module singleton. Call sites
    # already use ``self._resolve_project(...)`` so no caller changes needed.
    def _resolve_project(self, opp: Any, *, project_root: Optional[Path] = None) -> Any:
        """Project-объект для ForgeFacade.run_chain (best-effort, fail-safe)."""
        try:
            from core_02.workspace import Project
        except ImportError as exc:
            self._import_warnings.append(f"workspace.Project: {exc}")
            return None
        candidates: List[Path] = []
        if project_root is not None:
            candidates.append(Path(project_root))
        project_id = getattr(opp, "project_id", "") or ""
        if project_id:
            candidates.append(Path("projects_17") / project_id)
        for root in candidates:
            try:
                if (root / "MANIFEST.md").exists() or (root / "STEPS.md").exists():
                    return Project.load(root)
            except Exception:  # noqa: BLE001
                continue
        return None

    def _new_id(self) -> str:
        return f"{self.ID_PREFIX}-{uuid.uuid4().hex[:10]}"


# ─── CLI helpers (shared across all subclasses) ─────────────────────────────

def _load_opp(data_path: Path, opportunity_id: str) -> Any:
    from scripts_01.opportunity_engine import OpportunityStore
    store = OpportunityStore(data_path)
    return store.get(opportunity_id)


def _emit_json(payload: Dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _emit_text(line: str, *, json_mode: bool) -> None:
    out = sys.stderr if json_mode else sys.stdout
    out.write(line + "\n")
    out.flush()


@classmethod  # type: ignore[arg-type]
def _cli_resolve(cls, args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r} not found", json_mode=bool(args.json))
        return 1
    inst = cls()
    capability = cls._derive_capability(opp)
    pair = inst.resolve(capability) if capability else None
    # PHASE 13 G-13.1 (ADR-015): read PER-INSTANCE warnings (no module singleton).
    payload = {
        cls.PROG: "resolve",
        "opportunity_id": args.opportunity_id,
        "capability": capability,
        "factory_id": pair[0].factory_id if pair else None,
        "forge_id": pair[1].forge_id if pair else None,
        "import_warnings": list(inst._import_warnings),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"resolve: capability={capability} factory={payload['factory_id']} forge={payload['forge_id']}",
            json_mode=False,
        )
    return 0


@classmethod  # type: ignore[arg-type]
def _cli_run(cls, args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r} not found", json_mode=bool(args.json))
        return 1
    inst = cls()
    result = inst.execute(
        opp,
        dry_run=bool(getattr(args, "dry_run", False)),
        project_root=Path(args.project_root) if getattr(args, "project_root", None) else None,
    )
    # PHASE 13 G-13.1 (ADR-015): read PER-INSTANCE warnings (no module singleton).
    payload = {
        cls.PROG: "run",
        "opportunity_id": args.opportunity_id,
        "result": result,
        "import_warnings": list(inst._import_warnings),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        if result.get("ok"):
            _emit_text(
                f"run: ok artifact={result.get('artifact', {}).get('id')} "
                f"forge={result.get('artifact', {}).get('forge_id')} "
                f"overall={result.get('artifact', {}).get('overall')}",
                json_mode=False,
            )
        else:
            _emit_text(f"run: FAILED {result.get('error')}", json_mode=False)
    return 0 if result.get("ok") else 1


@classmethod  # type: ignore[arg-type]
def make_argparser(cls) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=cls.PROG,
        description=f"{cls.PROG} — Phase 12 BaseFactory subclass.",
    )
    parser.add_argument(
        "--data-path", default=str(DEFAULT_DATA_PATH),
        help=f"Opportunity YAML path (default {DEFAULT_DATA_PATH})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, help_text in (
        ("resolve", cls._cli_resolve, "capability → (factory, forge) resolution"),
        ("run", cls._cli_run, "full vertical slice: request → ForgeFacade → artifact"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("opportunity_id")
        p.add_argument("--json", action="store_true")
        if name == "run":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--project-root", default=None)
        p.set_defaults(func=fn)

    return parser


@classmethod  # type: ignore[arg-type]
def main(cls, argv: Optional[List[str]] = None) -> int:
    parser = cls.make_argparser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — fail-safe per spec
        _emit_text(f"error: {cls.PROG} unexpected failure: {exc}", json_mode=False)
        return 2


# Attach classmethods to BaseFactory after class body.
BaseFactory._cli_resolve = _cli_resolve  # type: ignore[attr-defined]
BaseFactory._cli_run = _cli_run  # type: ignore[attr-defined]
BaseFactory.make_argparser = make_argparser  # type: ignore[attr-defined]
BaseFactory.main = main  # type: ignore[attr-defined]


__all__ = [
    "BaseFactory",
    "ExecutionRequest",
    # DEPRECATED v5.189.32 (ADR-015): kept for backward-compat re-exports in
    # 3 subclasses (content/research/test factories). No longer appended to
    # from BaseFactory methods — use ``inst._import_warnings`` instead.
    "_LAZY_IMPORT_ERRORS",
    "DEFAULT_DATA_PATH",
    "DEFAULT_MEMORY_DB",
    "DEFAULT_FACTORIES_DIR",
]


if __name__ == "__main__":
    # Demo / smoke test (NOT production CLI — production uses subclasses).
    sys.exit(BaseFactory.main())
