"""core_02/forge_facade.py — ForgeFacade: явный, управляемый мост Blueprint v3 → Forge.

P3 (промт 70, Миссия 2): закрывает gap §7.6 п.2 «No direct Forge invocation»
БЕЗ нарушения §7.3 boundary («Direct Forge call из Scenario — НЕТ»).

Принципы:
1. ForgePipeline инстанцируется ТОЛЬКО здесь. Scenario/роли/wizard_lib
   не получают прямой доступ (grep-инвариант §7.3 сохраняется).
2. ``initiate_forge()`` — единственный метод запуска, вызывается ПО ЯВНОМУ
   запросу завершившей артефакт роли (не автоматически, не молча).
3. UNFORGED-семантика не меняется: статус вычисляет ``forge_registry.record_run()``
   (та же логика, что в ``scripts_01/forge.py``).
4. Узкий scope: только 14 pipeline-ролей (12 ядро + frontend + devops);
   справочные роли (orchestrator, context_keeper) и presale-трек
   (response_writer) — вне. (Задача 0 считала 15/17 производственных стадий
   С УЧЁТОМ response_writer; из Facade-scope он исключён.)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
***REMOVED***
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core_02.forge_pipeline import ForgePipeline, _now as _iso_now
from core_02.forge_registry import ForgeRegistry, UNFORGED
from core_02.role_executor import BaseRoleExecutor, RoleExecutorRegistry
from core_02.workspace import Project

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


# === Классификация 14 ролей для chain-runner (шаг 3 ROADMAP §18, v5.157.0) ===
#   - LIGHT_ROLES: аналитические/документационные, артефакты создаёт сама роль,
#     а не Forge. Для них CHECK-режим (RoleArtifactValidator) достаточен —
#     полный цикл ForgePipeline бессмысленн (Forge не генерирует их outputs).
#   - HEAVY_ROLES: реальные side-effects кода/тестов — нужен полный
#     цикл ForgePipeline (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT).
#   - CONDITIONAL (inline): frontend (project.type == "web") + devops
#     (always = полный цикл), обрабатываются через явную condicionallогику
#     в run_chain (не вынесены в константу, т.к. правила зависят от project.type).
LIGHT_ROLES: frozenset[str***REMOVED*** = frozenset({
    "explainer", "lisa", "risk", "decomposer",
    "architect", "auditor", "documenter", "retrospective",
***REMOVED***)

HEAVY_ROLES: frozenset[str***REMOVED*** = frozenset({
    "developer", "tester", "fixer", "acceptance",
***REMOVED***)


# ForgeRegistry уже импортирован выше. project_id вычисляется через
# ForgeRegistry._slug() (@staticmethod на классе) — DRY: один источник
# истины для project_id-алгоритма (R-127/B10 machine-readable invariant).

# 14 производственных стадий цепочки Blueprint v3 (см. P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md §1.3):
# 12 ядро + frontend + devops. Задача 0 считала 15/17 — включая presale-трек
# response_writer, который исключён из Facade-scope (дизайн §0.4).
# Справочные роли (orchestrator, context_keeper) также НЕ включены.
PIPELINE_ROLES: frozenset[str***REMOVED*** = frozenset({
    "explainer",
    "lisa",
    "risk",
    "decomposer",
    "architect",
    "auditor",
    "developer",
    "frontend",
    "devops",
    "tester",
    "fixer",
    "acceptance",
    "documenter",
    "retrospective",
***REMOVED***)

# Правильная полная цепочка (для документации/валидации порядка в будущем).
# Включена и как источник истины для порядка; "frontend"/"devops"/"fixer" — условные ветки.
PIPELINE_CHAIN: tuple[str, ...***REMOVED*** = (
    "explainer", "lisa", "risk", "decomposer", "architect", "auditor",
    "developer", "frontend", "devops", "tester", "fixer",
    "acceptance", "documenter", "retrospective",
)

# Reference-роли, для которых Facade-путь ЗАКРЫТ (gate → ValueError).
REFERENCE_ROLES: frozenset[str***REMOVED*** = frozenset({"orchestrator", "context_keeper"***REMOVED***)


# Дефолтные output-паттерны ролей для fallback (когда registry.yaml НЕ загружен).
# Это mirror того, что есть в blueprints_v3/registry.yaml для 14 pipeline-ролей
# (12 ядро + frontend + devops) — но без semantic-метаданных (description,
# triggers, dependencies). Используется только для machine-checkable
# existence-проверки артефактов, когда registry.yaml недоступен.
#
# При появлении 5 этапа Forge-классификации (categorical types, B-вне-модели)
# этот fallback остаётся как safety net и должен синхронизироваться с registry.
DEFAULT_ROLE_OUTPUTS: Dict[str, Tuple[str, ...***REMOVED******REMOVED*** = {
    "explainer":     ("brief.md", "parsed_requirements.md"),
    "lisa":          ("lisa_report.md",),
    "risk":          ("risk_matrix.md",),
    "decomposer":    ("decomposition.md", "module_list.md", "integration_topology.md"),
    "architect":     ("architecture.md", "adr/*.md", "contracts.yaml"),
    "auditor":       ("audit_report.md",),
    "developer":     ("src/**/*.py", "tests/**/*.py", "migrations/*.py"),
    "frontend":      ("frontend/**/*.tsx", "frontend/**/*.css", "frontend/**/*.html"),
    "devops":        ("Dockerfile", "docker-compose.yml",
                      ".github/workflows/*.yml", "terraform/*.tf"),
    "tester":        ("tests/**/*.py", "mutation_test_results.md"),
    "fixer":         ("bug_fixes.md", "regression_tests.py"),
    "acceptance":    ("acceptance_report.md", "validation.md"),
    "documenter":    ("README.md", "PORTFOLIO_CASE.md", "TG_POST.md",
                      "API_DOCS.md", "ARCHITECTURE.md"),
    "retrospective": ("retrospective_report.md", "LESSONS.md",
                      "lisa_calibration.yaml"),
***REMOVED***


# Кандидаты путей для авто-поиска registry.yaml (относительно project_root и cwd).
# Совпадает с конвенцией v5.152.0 (промт 70, ADR-013): blueprints_v3/registry.yaml
# на платформенном уровне, рядом с blueprints/blueprint.
DEFAULT_REGISTRY_CANDIDATES: Tuple[str, ...***REMOVED*** = (
    "blueprints_v3/registry.yaml",
    "registry.yaml",  # для самых плоских layouts (тесты, урезанные setups)
)


@dataclass(frozen=True)
class RoleArtifactReport:
    """Отчёт по одной роли: scope = existence (наличие) файлов-артефактов.

    SCOPE EXPLICITLY EXISTENCE-ONLY (промт 70, IDEA_EXPLORER_RUN_FORGE_FACADE
    §2 UNKNOWN + §16 H1-REFUTED fix): валидация контента (формат, schema)
    остаётся UNKNOWN и при реализации шага 3 должна быть зафиксирована явно.
    """

    role_id: str
    required: Tuple[str, ...***REMOVED***   # выходные паттерны (registry или fallback)
    present: Tuple[str, ...***REMOVED***    # фактически существующие файлы (≤10, осторожно)
    missing: Tuple[str, ...***REMOVED***    # паттерны без матчей
    status: str                 # "ok" | "partial" | "missing"

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "role_id": self.role_id,
            "required": list(self.required),
            "present": list(self.present),
            "missing": list(self.missing),
            "status": self.status,
        ***REMOVED***


@dataclass(frozen=True)
class ValidationSummary:
    """Агрегированный отчёт RoleArtifactValidator для проекта.

    Поля:
      - registry_status: "loaded" | "missing" | "unreadable" — состояние registry.yaml.
      - overall: "ok" (все ok) | "partial" (хотя бы один partial/missing
        при loaded registry) | "degraded" (registry missing/unreadable
        + хотя бы что-то найдено через fallback).
      - base_check_*: результат compose с существующим ForgePipeline.stage_check()
        (опционально, при compose_check=True). Если compose отключён —
        status="skipped", missing=().
    """

    project_id: str
    project_root: str
    registry_path: Optional[str***REMOVED***  # None если registry_status="missing" и явный путь не задан
    registry_status: str
    roles_checked: Tuple[str, ...***REMOVED***
    role_reports: Tuple[RoleArtifactReport, ...***REMOVED***
    overall: str
    base_check_status: str
    base_check_missing: Tuple[str, ...***REMOVED***

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "project_id": self.project_id,
            "project_root": self.project_root,
            "registry_path": self.registry_path,
            "registry_status": self.registry_status,
            "roles_checked": list(self.roles_checked),
            "role_reports": [r.to_dict() for r in self.role_reports***REMOVED***,
            "overall": self.overall,
            "base_check_status": self.base_check_status,
            "base_check_missing": list(self.base_check_missing),
        ***REMOVED***


@dataclass(frozen=True)
class ForgeFacadeResult:
    """Результат явного Forge-прогона через Facade."""

    project_id: str
    requested_by_role: str
    status_before: str
    status_after: str
    overall: str
    stages: tuple[dict[str, str***REMOVED***, ...***REMOVED***
    initiated_explicitly: bool = True  # фиксация «не молча»: всегда явный вызов
    project_read_only: bool = False    # B2 R-124: фиксация «не мутировал ли Project»

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "project_id": self.project_id,
            "requested_by_role": self.requested_by_role,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "overall": self.overall,
            "stages": list(self.stages),
            "initiated_explicitly": self.initiated_explicitly,
            "project_read_only": self.project_read_only,
        ***REMOVED***


# === Chain-runner dataclasses (шаг 3 ROADMAP §18, v5.157.0) ===
# ChainStage — один этап в run_chain (mode + status + details).
@dataclass(frozen=True)
class ChainStage:
    """Этап chain-runner: режим + статус + детали.

    Modes:
      - "check_only" — LIGHT-роль проверена RoleArtifactValidator (только existence).
      - "generate" — LIGHT-роль, артефакт которой материализован RoleExecutorRegistry
        (ADR-016; только при light_mode="generate" + executor зарегистрирован).
      - "full_cycle" — HEAVY/CONDITIONAL-true роль прогнана через initiate_forge.
      - "conditional_skip" — роль пропущена по условию (например, frontend для script).

    Status (отдельный set для каждого mode):
      - check_only: "ok" | "partial" | "missing" — copy из RoleArtifactReport.status.
      - generate: "generated" | "partial" | "gen_failed".
      - full_cycle: "run_ok" | "run_failed" | "init_error".
      - conditional_skip: "skipped".
    """

    role_id: str
    mode: str
    status: str
    details: str
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "role_id": self.role_id,
            "mode": self.mode,
            "status": self.status,
            "details": self.details,
            "duration_s": self.duration_s,
        ***REMOVED***


# ChainRun — агрегированный результат run_chain по всем ролям.
@dataclass(frozen=True)
class ChainRun:
    """Результат ForgeFacade.run_chain по списку ролей.

    Поля:
      - chain: tuple[ChainStage, ...***REMOVED*** — по одной стадии на каждую роль.
        Порядок = порядок входного role_ids (default = PIPELINE_CHAIN).
      - overall: "ok" | "partial" | "failed" | "degraded" (детали в §16 IDEA_EXPLORER).
      - validation_summary: Optional[ValidationSummary***REMOVED*** — trace к full-валидации
        артефактов (если compose_artifact_check=True).
      - validation_registry_status: "loaded" | "missing" | "unreadable" | "not_run".
    """

    project_id: str
    project_root: str
    stage_count: int
    chain: Tuple[ChainStage, ...***REMOVED***
    overall: str
    started_at: str
    finished_at: str
    validation_registry_status: str
    validation_summary: Optional[ValidationSummary***REMOVED*** = None

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "project_id": self.project_id,
            "project_root": self.project_root,
            "stage_count": self.stage_count,
            "chain": [s.to_dict() for s in self.chain***REMOVED***,
            "overall": self.overall,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "validation_registry_status": self.validation_registry_status,
            "validation_summary": (
                self.validation_summary.to_dict()
                if self.validation_summary is not None else None
            ),
        ***REMOVED***


class ForgeFacade:
    """Единственная санкционированная точка входа: роль → Forge-прогон.

    Соблюдает §7.3: Scenario/роли НЕ вызывают ForgePipeline напрямую.
    """

    def __init__(
        self,
        registry: Optional[ForgeRegistry***REMOVED*** = None,
        dry_run: bool = False,
        workspace_steps_policy: str = "optional",
    ) -> None:
        self.registry = registry or ForgeRegistry()
        self.dry_run = dry_run
        self.workspace_steps_policy = workspace_steps_policy

    # ── gate ────────────────────────────────────────────────────────────

    def can_initiate(self, role_id: str) -> bool:
        """Gate: только pipeline-роли могут инициировать Forge-прогон."""
        return role_id in PIPELINE_ROLES

    # ── основной метод ──────────────────────────────────────────────────

    def initiate_forge(
        self,
        project: Project,
        requested_by_role: str,
        hooks: Optional[dict[str, Callable[[Project, Any***REMOVED***, None***REMOVED******REMOVED******REMOVED*** = None,
        skip: Optional[set[str***REMOVED******REMOVED*** = None,
        project_read_only: bool = False,
    ) -> ForgeFacadeResult:
        """ЯВНЫЙ запрос на Forge-прогон от завершившей артефакт роли.

        Args:
            project: проект (L-2 контейнер).
            requested_by_role: роль, завершившая свой артефакт и явно
                запрашивающая Forge-прогон. Должна быть в PIPELINE_ROLES.
            hooks: on_report и пр. хуки (пробрасываются в ForgePipeline).
            skip: стадии для пропуска (как в ForgePipeline.run(skip=...)).
            project_read_only: B2 R-124 — если True, Forge НЕ мутирует
                артефакты Project (RUNNABLE.md/CHECKLIST.md), только проверяет.
                Default False (обратная совместимость: legacy-Facade-поведение).

        Returns:
            ForgeFacadeResult с полной сводкой и статусами до/после.

        Raises:
            ValueError: если роль вне pipeline-множества (gate).
        """
        if not self.can_initiate(requested_by_role):
            raise ValueError(
                f"role_id {requested_by_role!r***REMOVED*** не входит в PIPELINE_ROLES "
                f"Facade (разрешены: {sorted(PIPELINE_ROLES)***REMOVED***). "
                f"Справочные роли {sorted(REFERENCE_ROLES)***REMOVED*** не инициируют Forge-прогон "
                f"(§7.3: только через явный вызов pipeline-роли)."
            )

        project_id = self.registry.register_project(project.name, str(project.root))
        status_before = UNFORGED
        prev = self.registry.get_project_status(project_id)
        if prev is not None:
            status_before = prev.status

        pipe = ForgePipeline(
            project,
            dry_run=self.dry_run,
            hooks=hooks or {***REMOVED***,
            workspace_steps_policy=self.workspace_steps_policy,
            project_read_only=project_read_only,
        )
        run = pipe.run(skip=skip)

        status_after = self.registry.record_run(project_id, run).status
        stages = tuple(
            {"name": s.name, "status": s.status***REMOVED*** for s in run.stages
        )

        return ForgeFacadeResult(
            project_id=project_id,
            requested_by_role=requested_by_role,
            status_before=status_before,
            status_after=status_after,
            overall=run.overall,
            stages=stages,
            project_read_only=project_read_only,
        )    # ── query (read-only, не меняет состояние) ───────────────────────────

    def get_status(self, project_id: str):
        """Текущий статус проекта в forge_registry (read-only)."""
        return self.registry.get_project_status(project_id)

    # ── additive: record_chain_run pass-through (v5.173.0, prereq для --resume sentinel-persistence) ─
    # Thin delegate на self.registry.record_run для ChainRun-объектов.
    # Используется scripts_01/forge.py cmd_chain для sentinel-persistence (статус
    # init_error в ChainStage). До v5.173.0 ForgeFacade.record_run был ожидаем,
    # но НЕ экспонирован — cmd_chain использовал hasattr-degradation.
    # Теперь экспонирован — sentinel-перситенс станет реальным (не graceful no-op).
    def record_run(
        self,
        project_name: str,
        chain_run: "ChainRun",
    ) -> ForgeStatus:
        """Записать результат ChainRun в registry для --resume partial-recovery.

        Thin pass-through на ``self.registry.record_run(project_id, chain_run)``.
        project_id резолвится через ``self.registry._slug(project_name)`` (DRY:
        единый источник истины для slug-алгоритма — forge_registry._slug).

        Args:
            project_name: имя проекта (НЕ полный root и НЕ pre-slugged id).
            chain_run: ChainRun dataclass (instance of ``ChainRun``).

        Returns:
            Обновлённый ``ForgeStatus`` (вызывающий код может проверить
            ``status.last_pipeline['chain'***REMOVED***`` для последующего --resume).

        Raises:
            KeyError: если проект не зарегистрирован (см. record_run в registry).
            AttributeError: propagates если chain_run не имеет ``.to_dict()``.

        Констрейнты (CAN-16 ADDITIVE):
          1. Не модифицирует существующие методы Facade (только НОВЫЙ метод в классе).
          2. Делегирует существующему registry.record_run (не дублирует логику сериализации).
          3. project_id = slug (НЕ полный root) — соответствует записи в
             registry по register_project.
        """
        project_id = self.registry._slug(project_name)
        return self.registry.record_run(project_id, chain_run)

    # ── additive: делегат на RoleArtifactValidator (шаг 2 ROADMAP §16, v5.156.0) ─

    def validate_role_artifacts(
        self,
        project: Project,
        role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
        *,
        compose_check: bool = True,
        registry_path: Optional[Path***REMOVED*** = None,
    ) -> ValidationSummary:
        """Делегирует RoleArtifactValidator.validate() — additive прокси.

        Сценарий: pipeline-роль завершила артефакт и просит Facade
        «проверь, что все мои outputs на месте» (или весь chain в целом).
        Не трогает существующий ForgePipeline.stage_check() — compose
        (когда compose_check=True) делается внутри валидатора через
        явный ForgePipeline.stage_check() вызов (CON-16/CON-21: additive).
        """
        validator = RoleArtifactValidator(registry_path=registry_path)
        return validator.validate(
            project,
            role_ids=role_ids,
            compose_check=compose_check,
        )

    # ── additive: chain-runner (шаг 3 ROADMAP §18, v5.157.0) ────────────────
    #
    # run_chain — выполнение цепочки из 14 pipeline-ролей в порядке PIPELINE_CHAIN.
    # Каждая роль обрабатывается в одном из 3 режимов:
    #   - LIGHT (аналитические/документационные): только CHECK-existence артефактов
    #     (RoleArtifactValidator), НЕ запускаем ForgePipeline (бессмысленно —
    #     артефакты создаёт сама роль, не Forge).
    #   - HEAVY (developer/tester/fixer/acceptance): полный цикл ForgePipeline
    #     через initiate_forge(...).
    #   - CONDITIONAL:
    #       - frontend: project.type == "web" ? full_cycle : conditional_skip.
    #       - devops: всегда condition: always = full_cycle.
    #
    # Pre-flight: compose_artifact_check=True (default) → один проход
    # RoleArtifactValidator для всех 14 ролей (chain быстро читает status
    # из готовых RoleArtifactReport). ValidationSummary включена в ChainRun
    # для full-traceability (debugging пропущенных артефактов).
    #
    # Констрейнты (фиксированы в IDEA_EXPLORER_RUN_FORGE_FACADE §16/§18,
    # CHANGELOG v5.155.0 + v5.156.0):
    #   1. ADDITIVE — только core_02/forge_facade.py расширяется.
    #   2. §7.3 соблюдается — Run chain → initiate_forge → единственный мост → Forge.
    #   3. UNFORGED через record_run (та же логика, что initiate_forge).
    #   4.Graceful degradation — registry missing → degraded (НЕ failed).
    #   5. project_read_only=True при full_cycle (для chain-runner, чтобы
    #      не мутировать project между ролями).

    def run_chain(
        self,
        project: Project,
        role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
        *,
        registry_path: Optional[Path***REMOVED*** = None,
        compose_artifact_check: bool = True,
        project_read_only: bool = True,
        skip_full_cycle_stages: Optional[Set[str***REMOVED******REMOVED*** = None,
        light_mode: str = "check_only",
        executor_registry: Optional[RoleExecutorRegistry***REMOVED*** = None,
    ) -> ChainRun:
        """Chain-runner поверх PIPELINE_CHAIN + RoleArtifactValidator + initiate_forge.

        Args:
            project: целевой Project (Project.load(root)).
            role_ids: какие роли исполнить и в каком порядке.
                Default = ``PIPELINE_CHAIN`` (все 14, линейный порядок).
                Все роли должны быть в ``PIPELINE_ROLES`` (gate).
            registry_path: явный путь к registry.yaml для RoleArtifactValidator;
                если None — резолвер ищет через DEFAULT_REGISTRY_CANDIDATES.
            compose_artifact_check: True (default) → один проход
                RoleArtifactValidator для всех ролей chain; False → пропуск.
            project_read_only: True (default) → для HEAVY full_cycle Forge
                НЕ мутирует Project (RUNNABLE.md/CHECKLIST.md) — B2 R-124.
                False → legacy-поведение Forge пишет артефакты.
            skip_full_cycle_stages: substages FORGE/CHECK/BUILD/TEST/DEPLOY/REPORT,
                которые надо пропустить внутри full_cycle ролей
                (default: None = все 6 стадий выполняются).
            light_mode: "check_only" (default) | "generate" (ADR-016).
                "generate" → для LIGHT-роли с отсутствующим/partial артефактом
                вызывается executor_registry (если есть) для материализации
                файлов, затем re-validation только этой роли. Дефолт check_only
                = обратная совместимость (существующие тесты не затрагиваются).
            executor_registry: RoleExecutorRegistry (ADR-016), опционально.
                При None (или отсутствующем executor для роли) LIGHT-роли
                остаются check_only даже в light_mode="generate".

        Returns:
            ChainRun со stage-by-stage отчётом и ValidationSummary для traceability.

        Note (ADR-016): pre-flight ValidationSummary — снапшот ДО генерации;
        актуальный post-генерационный статус LIGHT-роли несёт её ChainStage
        (mode="generate").

        Raises:
            ValueError: если role_ids содержит вне-scope-роль (gate).
                Для ошибок forge-runtime (subprocess fail) — exception подавляется
                через ``status="init_error"`` в ChainStage (chain продолжается).
        """
        # 0) Normalise input и gate
        if isinstance(role_ids, list):
            role_ids = tuple(role_ids)
        roles = role_ids if role_ids is not None else PIPELINE_CHAIN
        invalid = [r for r in roles if r not in PIPELINE_ROLES***REMOVED***
        if invalid:
            raise ValueError(
                f"role_ids содержит вне-scope-роли {invalid***REMOVED***; "
                f"PIPELINE_ROLES = {sorted(PIPELINE_ROLES)***REMOVED***"
            )
        if light_mode not in ("check_only", "generate"):
            raise ValueError(
                f"light_mode={light_mode!r***REMOVED*** вне {{'check_only', 'generate'***REMOVED******REMOVED***"
            )

        started_at = _iso_now()

        # 1) Pre-flight: ValidationSummary (через уже существующий delegate v5.156.0)
        validation: Optional[ValidationSummary***REMOVED*** = None
        if compose_artifact_check:
            validation = self.validate_role_artifacts(
                project,
                role_ids=roles,
                compose_check=True,
                registry_path=registry_path,
            )

        # 2) Per-role stage.
        stages: List[ChainStage***REMOVED*** = [***REMOVED***
        preskip = skip_full_cycle_stages or set()
        for rid in roles:
            stage_start = time.monotonic()

            # ── LIGHT (CHECK-only / generate) ────────────────────────────────────
            if rid in LIGHT_ROLES:
                rprt = _role_report_for(validation, rid)
                # ADR-016: light_mode="generate" — материализовать недостающий
                # артефакт через RoleExecutorRegistry (если executor есть).
                if light_mode == "generate" and executor_registry is not None:
                    executor = executor_registry.get(rid)
                    if executor is not None and (rprt is None or rprt.status != "ok"):
                        stages.append(self._execute_light_generate(
                            project, rid, executor, stage_start, registry_path,
                        ))
                        continue
                if rprt is None:
                    stages.append(ChainStage(
                        role_id=rid, mode="check_only",
                        status="skipped",
                        details="compose_artifact_check=False (no validation)",
                        duration_s=time.monotonic() - stage_start,
                    ))
                else:
                    details = _format_check_details(rprt)
                    stages.append(ChainStage(
                        role_id=rid, mode="check_only",
                        status=rprt.status,   # ok/partial/missing — copy as-is
                        details=details,
                        duration_s=time.monotonic() - stage_start,
                    ))
                continue

            # ── CONDITIONAL: frontend (project.type=="web"?) ───────────────────────────
            if rid == "frontend":
                proj_type = getattr(project, "type", "") or ""
                if proj_type != "web":
                    stages.append(ChainStage(
                        role_id=rid, mode="conditional_skip",
                        status="skipped",
                        details=(
                            f"project.type={proj_type!r***REMOVED*** != 'web'; "
                            f"frontend пропущен (per registry.yaml condition)"
                        ),
                        duration_s=time.monotonic() - stage_start,
                    ))
                    continue
                # else: frontend для web-проекта → falls through HEAVY full_cycle

            # ── HEAVY / active CONDITIONAL (developer/tester/fixer/acceptance/
            #    devops/frontend-on-web) → полный цикл ForgePipeline через
            #    initiate_forge(..., project_read_only=...).
            try:
                # Map skip substage names ("FORGE","CHECK",…) → ForgePipeline internal ("stage_forge","stage_check",…)
                internal_skip = _map_skip_to_internal(preskip)
                result = self.initiate_forge(
                    project,
                    requested_by_role=rid,
                    skip=internal_skip,
                    project_read_only=project_read_only,
                )
                stages.append(ChainStage(
                    role_id=rid, mode="full_cycle",
                    status="run_ok" if result.overall == "ok" else "run_failed",
                    details=_format_full_cycle_details(result),
                    duration_s=time.monotonic() - stage_start,
                ))
            except ValueError as ve:
                # роль вне PIPELINE_ROLES (защита от caller-ошибки)
                stages.append(ChainStage(
                    role_id=rid, mode="full_cycle",
                    status="init_error",
                    details=f"ValueError: {ve***REMOVED***",
                    duration_s=time.monotonic() - stage_start,
                ))
            except Exception as exc:
                # runtime-сбои (subprocess fail, file IO, etc.) — chain-soft-failure
                stages.append(ChainStage(
                    role_id=rid, mode="full_cycle",
                    status="init_error",
                    details=f"{type(exc).__name__***REMOVED***: {exc***REMOVED***",
                    duration_s=time.monotonic() - stage_start,
                ))

        # 3) Aggregate overall
        finished_at = _iso_now()
        overall, reg_status = _aggregate_chain_overall(stages, validation)

        return ChainRun(
            project_id=ForgeRegistry._slug(project.name),
            project_root=str(project.root),
            stage_count=len(stages),
            chain=tuple(stages),
            overall=overall,
            started_at=started_at,
            finished_at=finished_at,
            validation_registry_status=reg_status,
            validation_summary=validation,
        )

    # ── additive: LIGHT-role generation (ADR-016, v5.189.38) ────────────────

    def _execute_light_generate(
        self,
        project: Project,
        role_id: str,
        executor: BaseRoleExecutor,
        stage_start: float,
        registry_path: Optional[Path***REMOVED***,
    ) -> ChainStage:
        """Запустить executor LIGHT-роли и пере-проверить артефакты (ADR-016).

        Вызывается из ``run_chain`` только при ``light_mode="generate"`` + есть
        executor для роли + артефакт роли отсутствует/partial (или нет
        pre-flight validation). После генерации — re-validation только этой
        роли (compose off), чтобы chain-stage нёс актуальный статус.

        Fail-safe: любой exception executor'а → status="gen_failed" (chain
        продолжается, НЕ abort — симметрично full_cycle init_error).
        """
        try:
            created = executor.execute(project, role_id) or [***REMOVED***
        except Exception as exc:  # noqa: BLE001 — fail-safe, chain продолжается
            return ChainStage(
                role_id=role_id, mode="generate",
                status="gen_failed",
                details=f"{type(exc).__name__***REMOVED***: {exc***REMOVED***",
                duration_s=time.monotonic() - stage_start,
            )
        if not created:
            return ChainStage(
                role_id=role_id, mode="generate",
                status="gen_failed",
                details="executor вернул пустой список созданных файлов",
                duration_s=time.monotonic() - stage_start,
            )
        reval = self.validate_role_artifacts(
            project, role_ids=(role_id,), compose_check=False,
            registry_path=registry_path,
        )
        new_rprt = _role_report_for(reval, role_id)
        if new_rprt is not None and new_rprt.status == "ok":
            return ChainStage(
                role_id=role_id, mode="generate", status="generated",
                details=f"created={created***REMOVED***",
                duration_s=time.monotonic() - stage_start,
            )
        post = new_rprt.status if new_rprt is not None else "unknown"
        return ChainStage(
            role_id=role_id, mode="generate", status="partial",
            details=f"created={created***REMOVED*** but re-check={post***REMOVED***",
            duration_s=time.monotonic() - stage_start,
        )


# === RoleArtifactValidator (ADDITIVE, шаг 2 ROADMAP §16, promts 68/70, v5.156.0) ===
# Констрейнты (фиксированы в P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md §16 и CHANGELOG v5.155.0):
#   1. ADDITIVE — только НОВЫЙ класс внутри core_02/forge_facade.py.
#      Существующие модули (workspace.py, forge_pipeline.py, forge_registry.py)
#      НЕ модифицируются → ревью-инвариант: grep "RoleArtifactValidator"
#      встречается ТОЛЬКО в forge_facade.py.
#   2. SCOPE = EXISTENCE — проверяет только НАЛИЧИЕ файлов (Path.is_file()
#      и pathlib.Path.glob для паттернов). НЕ проверяет content-схему
#      (формат контента остаётся UNKNOWN из §2 — при реализации шага 3
#      зафиксировать явно).
#   3. COMPOSE — использует существующий ForgePipeline.stage_check() для
#      базового CHECK (README/RUNNABLE/CHECKLIST/STEPS) БЕЗ изменений.
#   4. GRACEFUL DEGRADATION — если registry.yaml отсутствует/битый →
#      используется DEFAULT_ROLE_OUTPUTS fallback; overall="degraded";
#      валидатор НЕ падает.
class RoleArtifactValidator:
    """Аддитивный валидатор существования файлов-артефактов ролей Blueprint v3.

    Pipeline-роль завершила свой этап — Facade.validate_role_artifacts()
    проверяет, что её outputs-паттерны из registry.yaml (или fallback)
    действительно материализованы в ``project.root``.

    Дизайн:
      - registry_resolution: явный путь → project_root/<cand> → cwd/<cand>
        → "missing" (если ничего не нашли).
      - parser: yaml.safe_load → json.loads fallback (как forge_registry._load).
      - outputs_source: registry.pipeline[***REMOVED***.outputs (если loaded)
        ИЛИ DEFAULT_ROLE_OUTPUTS (если missing/unreadable,
        для указанных role_ids).
      - existence_check: прямой Path.is_file() для простых паттернов,
        pathlib.Path.glob() (с ``**`` recursive support) для glob.
      - glob_match_metric: ≥1 матч = present (для всех ролей).
      - compose: опциональный ForgePipeline.stage_check() для базового набора
        (CON-16 additive — НЕ модифицирует forge_pipeline.py).
    """

    PRESENT_CAP: int = 10  # максимум матчей в present[***REMOVED*** для отчёта

    def __init__(
        self,
        registry_path: Optional[Path***REMOVED*** = None,
        registry_candidates: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
    ) -> None:
        self.registry_path = registry_path
        self.registry_candidates = (
            registry_candidates if registry_candidates is not None
            else DEFAULT_REGISTRY_CANDIDATES
        )

    # ── registry resolution ────────────────────────────────────────────

    def _resolve_registry(
        self, project_root: Path
    ) -> Tuple[str, Optional[Path***REMOVED******REMOVED***:
        """Resolve registry.yaml: явный путь → candidates → missing.

        Returns (registry_status, path_or_None):
          - ("loaded", path): путь существует, можно пытаться парсить.
          - ("missing", path_or_None): путь не найден среди кандидатов.
        """
        # 1) явный путь — приоритет
        if self.registry_path is not None:
            p = Path(self.registry_path)
            return ("loaded" if p.is_file() else "missing"), p
        # 2) candidates: per-project → cwd
        for cand in self.registry_candidates:
            for base in (project_root, Path.cwd()):
                p = base / cand
                if p.is_file():
                    return "loaded", p
        return "missing", None

    @staticmethod
    def _try_load_registry(path: Path) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """yaml.safe_load → json.loads fallback. None = unreadable."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        if yaml is not None:
            try:
                loaded = yaml.safe_load(text)
                if isinstance(loaded, dict):
                    return loaded
            except Exception:
                pass  # упало в yaml — пробуем json
        try:
            import json
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return None
        return None

    # ── outputs extraction ────────────────────────────────────────────

    @staticmethod
    def _extract_role_outputs(
        registry_data: Dict[str, Any***REMOVED***, role_ids: Tuple[str, ...***REMOVED***
    ) -> Dict[str, Tuple[str, ...***REMOVED******REMOVED***:
        """Достать outputs для указанных ролей из loaded registry."""
        out: Dict[str, Tuple[str, ...***REMOVED******REMOVED*** = {***REMOVED***
        pipeline = registry_data.get("pipeline") or [***REMOVED***
        if not isinstance(pipeline, list):
            return out
        wanted = set(role_ids)
        for entry in pipeline:
            if not isinstance(entry, dict):
                continue
            rid = entry.get("id")
            if rid not in wanted:
                continue
            outs = entry.get("outputs") or [***REMOVED***
            if isinstance(outs, list):
                out[rid***REMOVED*** = tuple(str(p) for p in outs if isinstance(p, str))
        return out

    # ── glob / file existence ─────────────────────────────────────────

    def _glob_materialized(
        self, project_root: Path, pattern: str
    ) -> Tuple[List[str***REMOVED***, bool***REMOVED***:
        """Проверяет наличие файла или ≥1 матча glob.

        Returns (present_files[:PRESENT_CAP***REMOVED***, present_bool).

        Без glob-символов (``*?[***REMOVED***``) — это прямой файл: проверяем is_file().
        С ``**`` — pathlib.Path.glob() обрабатывает рекурсивно (Python 3.5+).
        Возвращаем relative paths (лимит PRESENT_CAP).
        """
        if not pattern or not any(ch in pattern for ch in "*?["):
            target = project_root / pattern
            if target.is_file():
                return [pattern***REMOVED***, True
            return [***REMOVED***, False
        try:
            matches = sorted(
                str(p.relative_to(project_root))
                for p in project_root.glob(pattern)
                if p.is_file()
            )
        except (ValueError, OSError):
            return [***REMOVED***, False
        if not matches:
            return [***REMOVED***, False
        return matches[: self.PRESENT_CAP***REMOVED***, True

    # ── status classification ─────────────────────────────────────────

    @staticmethod
    def _classify_role_status(
        required: Tuple[str, ...***REMOVED***, present: Tuple[str, ...***REMOVED***, missing: Tuple[str, ...***REMOVED***
    ) -> str:
        """ok = все паттерны матчатся, missing = ни один не матчится, partial = смесь."""
        if not required:
            return "ok"  # роли без declared outputs — считаем ok
        total = len(required)
        ok_count = total - len(missing)
        if ok_count == total:
            return "ok"
        if ok_count == 0:
            return "missing"
        return "partial"

    @staticmethod
    def _overall_status(
        registry_status: str,
        role_reports: Tuple["RoleArtifactReport", ...***REMOVED***,
        base_check_status: str,
    ) -> str:
        """Агрегированный статус для ValidationSummary."""
        if registry_status != "loaded":
            return "degraded"
        statuses = {r.status for r in role_reports***REMOVED***
        if statuses and statuses.issubset({"ok"***REMOVED***):
            return "ok"
        if "missing" in statuses or "partial" in statuses:
            return "partial"
        return "degraded"  # нет role_reports с loaded registry — degraded

    # ── compose с base CHECK ───────────────────────────────────────────

    @staticmethod
    def _base_check(project: Project) -> Tuple[str, Tuple[str, ...***REMOVED******REMOVED***:
        """compose с существующим ForgePipeline.stage_check() (READ-ONLY mode).

        ВАЖНО: dry_run=False — stage_check() имеет early-return ``if self.dry_run:
        return ...status="skipped"...`` ДО реальной ok/failed-логики. Если
        передать dry_run=True, compose бесполезен (всегда "skipped"). ``stage_check``
        не делает side-effects (только читает), ``project_read_only=True`` страхует
        от потенциальных будущих записей (B2 R-124).
        """
        pipe = ForgePipeline(
            project,
            workspace_steps_policy="optional",
            project_read_only=True,  # B2 (R-124): не трогаем Project
        )
        res = pipe.stage_check()
        # res.details содержит «missing artifacts: A, B» — извлекаем явно,
        # потому что статус stage_check просто «ok»/«failed», без itemized missing.
        missing: Tuple[str, ...***REMOVED*** = ()
        try:
            req = project.get_requirements(steps_policy="optional")
            missing = tuple(req.missing or ())
        except (AttributeError, OSError):
            # get_requirements может упасть на повреждённых проектах — это не
            # критично для compose, просто missing будет пустой (failed без details).
            missing = ()
        return (res.status, missing)

    # ── main API ──────────────────────────────────────────────────────

    def validate(
        self,
        project: Project,
        role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
        *,
        compose_check: bool = True,
    ) -> ValidationSummary:
        """Валидирует existence файлов-артефактов ролей для проекта.

        Args:
            project: целевой Project (Project.load(root)).
            role_ids: какие роли проверить. По умолчанию — все PIPELINE_ROLES
                (14 production-стадий; reference и presale-track — вне).
            compose_check: True (по умолчанию) → дополнительно compose со
                существующим ForgePipeline.stage_check() (README/RUNNABLE/
                CHECKLIST/STEPS). Полезно для полной картины; отключить
                можно для performance.

        Returns:
            ValidationSummary с полным отчётом (to_dict()-сериализуемый).
        """
        # Default scope = все 14 pipeline-ролей, отсортированных для стабильных
        # отчётов (sorted на frozenset — детерминированный порядок).
        roles = role_ids or tuple(sorted(PIPELINE_ROLES))
        if isinstance(roles, list):
            roles = tuple(roles)
        project_root = Path(project.root)

        # 1) Resolve + load registry (или degraded fallback)
        reg_status, reg_path = self._resolve_registry(project_root)
        registry_data: Optional[Dict[str, Any***REMOVED******REMOVED*** = None
        if reg_status == "loaded" and reg_path is not None:
            registry_data = self._try_load_registry(reg_path)
            if registry_data is None:
                reg_status = "unreadable"

        # 2) Outputs source: registry ИЛИ DEFAULT_ROLE_OUTPUTS fallback
        outputs_source: Dict[str, Tuple[str, ...***REMOVED******REMOVED***
        if registry_data is not None:
            outputs_source = self._extract_role_outputs(registry_data, roles)
        else:
            outputs_source = {***REMOVED***

        # 3) Per-role existence check (вкл. fallback для ролей без registry-выхода)
        role_reports: List[RoleArtifactReport***REMOVED*** = [***REMOVED***
        for rid in roles:
            patterns = outputs_source.get(rid) or DEFAULT_ROLE_OUTPUTS.get(rid, ())
            present: List[str***REMOVED*** = [***REMOVED***
            missing: List[str***REMOVED*** = [***REMOVED***
            for pat in patterns:
                found, ok = self._glob_materialized(project_root, pat)
                if ok:
                    # Единый формат: только реальные relative-пути
                    # (≤ PRESENT_CAP на суммарный список). Без mixed-annotations.
                    present.extend(found)
                else:
                    missing.append(pat)
            present_capped = tuple(present[: self.PRESENT_CAP***REMOVED***)
            rprt = RoleArtifactReport(
                role_id=rid,
                required=patterns,
                present=present_capped,
                missing=tuple(missing),
                status=self._classify_role_status(
                    patterns, present_capped, tuple(missing)
                ),
            )
            role_reports.append(rprt)

        # 4) Compose с base CHECK (опционально)
        base_status, base_missing = ("skipped", ())
        if compose_check:
            try:
                base_status, base_missing = self._base_check(project)
            except (AttributeError, OSError):  # pragma: no cover — defensive
                base_status, base_missing = ("failed", ())

        # 5) Project_id — через ForgeRegistry._slug (@staticmethod, DRY).
        # НЕ дублируем алгоритм здесь: forge_registry._slug — единый источник.
        project_id = ForgeRegistry._slug(project.name)

        overall = self._overall_status(
            reg_status, tuple(role_reports), base_status
        )

        return ValidationSummary(
            project_id=project_id,
            project_root=str(project_root),
            registry_path=str(reg_path) if reg_path is not None else None,
            registry_status=reg_status,
            roles_checked=roles,
            role_reports=tuple(role_reports),
            overall=overall,
            base_check_status=base_status,
            base_check_missing=base_missing,
        )


__all__ = [
    "PIPELINE_ROLES",
    "PIPELINE_CHAIN",
    "LIGHT_ROLES",
    "HEAVY_ROLES",
    "REFERENCE_ROLES",
    "DEFAULT_ROLE_OUTPUTS",
    "DEFAULT_REGISTRY_CANDIDATES",
    "ForgeFacadeResult",
    "ChainStage",
    "ChainRun",
    "RoleArtifactReport",
    "ValidationSummary",
    "ForgeFacade",
    "RoleArtifactValidator",
***REMOVED***


# === Module-level helpers (шаг 3 ROADMAP §18, v5.157.0) ===
# Приватные helper'ы для run_chain; вынесены на module-level для улучшения
# testability без обращения к private методам Facade.
def _role_report_for(
    validation: Optional[ValidationSummary***REMOVED***, role_id: str
) -> Optional["RoleArtifactReport"***REMOVED***:
    """Извлекает RoleArtifactReport для роли из ValidationSummary (или None)."""
    if validation is None:
        return None
    for rprt in validation.role_reports:
        if rprt.role_id == role_id:
            return rprt
    return None


def _format_check_details(rprt: "RoleArtifactReport") -> str:
    """details для LIGHT chain_stage — статус + missing patterns (если есть)."""
    if rprt.status == "ok":
        return "all artifacts present"
    if rprt.status == "missing":
        return f"missing={[m for m in rprt.missing***REMOVED******REMOVED***"
    return f"partial: missing={[m for m in rprt.missing***REMOVED******REMOVED***"


def _format_full_cycle_details(result: ForgeFacadeResult) -> str:
    """details для HEAVY chain_stage — summary ForgePipeline stages."""
    stage_summary = ",".join(f"{s['name'***REMOVED******REMOVED***:{s['status'***REMOVED******REMOVED***" for s in result.stages)
    return f"stages=[{stage_summary***REMOVED******REMOVED*** ({result.overall***REMOVED***)"


# Маппинг human-readable skip-имён ("FORGE", "CHECK", "BUILD", "TEST",
# "DEPLOY", "REPORT") в internal ForgePipeline метода ("stage_forge", …).
# run_chain принимает человеко-читаемые имена (без префикса "stage_") —
# более прозрачно для caller-side.
_INTERNAL_SKIP_MAP: Dict[str, str***REMOVED*** = {
    "FORGE":   "stage_forge",
    "CHECK":   "stage_check",
    "BUILD":   "stage_build",
    "TEST":    "stage_test",
    "DEPLOY":  "stage_deploy",
    "REPORT":  "stage_report",
***REMOVED***


def _map_skip_to_internal(skip_names: Set[str***REMOVED***) -> Set[str***REMOVED***:
    """Преобразует внешние имена стадий ("FORGE") в internal ("stage_forge")."""
    if not skip_names:
        return set()
    return {_INTERNAL_SKIP_MAP.get(n, n) for n in skip_names***REMOVED***


def _aggregate_chain_overall(
    stages: List[ChainStage***REMOVED***,
    validation: Optional[ValidationSummary***REMOVED***,
) -> Tuple[str, str***REMOVED***:
    """Compute ChainRun.overall + registry_status из стадий + validation.

    Decision tree (per §18 IDEA_EXPLORER §3.5):
      - failed: нет стадий вовсе (fatal) ИЛИ все HEAVY init_error.
      - degraded: registry missing/unreadable + хоть что-то выполнилось.
      - ok: все ok/run_ok/skipped/generated (registry loaded).
      - partial: всё остальное (есть partial/missing/run_failed/init_error/
        gen_failed, но не все init_error).
    """
    n_stages = len(stages)
    if n_stages == 0:
        return ("failed", validation.registry_status if validation else "not_run")

    statuses = {s.status for s in stages***REMOVED***
    reg_status = (
        validation.registry_status if validation is not None else "not_run"
    )

    # Все HEAVY/CONDITIONAL-true (full_cycle) упали на init_error → failed.
    full_cycle_stages = [s for s in stages if s.mode == "full_cycle"***REMOVED***
    if full_cycle_stages and all(
        s.status == "init_error" for s in full_cycle_stages
    ):
        return ("failed", reg_status)

    # Registry missing/unreadable → degraded (не failed — chain отработал).
    if reg_status in ("missing", "unreadable"):
        return ("degraded", reg_status)

    # Есть неполадки (partial/missing/run_failed/init_error) → partial.
    imperfect = statuses & {
        "partial", "missing", "run_failed", "init_error", "gen_failed",
    ***REMOVED***
    if imperfect:
        return ("partial", reg_status)

    # Всё ok/run_ok/skipped, registry loaded → ok.
    return ("ok", reg_status)
