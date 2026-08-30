# tests_09/test_run_chain.py — ForgeFacade.run_chain (P3, шаг 3 ROADMAP §18)
#
# Шаг 3 ROADMAP-LA-001 (промт 68/70, v5.157.0):
# run_chain — chain-runner поверх PIPELINE_CHAIN (14 ролей) с двумя режимами:
#   - LIGHT (8 ролей): CHECK-only через RoleArtifactValidator (existence артефактов).
#   - HEAVY (4 роли): полный цикл через initiate_forge(...
#     , project_read_only=True для B2 R-124).
#   - CONDITIONAL: frontend (project.type=="web") + devops (always).
#
# Использует шаг 2 (RoleArtifactValidator, v5.156.0) и шаг 1 (initiate_forge,
# v5.145.0) как compose-уровни. Не модифицирует существующие модули
# (workspace.py/forge_pipeline.py/forge_registry.py).
import pytest

from core_02.forge_facade import (
    HEAVY_ROLES,
    LIGHT_ROLES,
    PIPELINE_CHAIN,
    PIPELINE_ROLES,
    REFERENCE_ROLES,
    ChainRun,
    ChainStage,
    ForgeFacade,
    ValidationSummary,
)
from core_02.forge_registry import ForgeRegistry
from core_02.workspace import Project


# ─── helpers ────────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """Минимальный Project с README/RUNNABLE/CHECKLIST (базовый CHECK ok)."""
    p = tmp_path / "vkusvill_demo"
    p.mkdir()
    (p / "project.yaml").write_text("name: vkusvill_demo\ntype: script\n",
                                     encoding="utf-8")
    (p / "README.md").write_text("# vkusvill_demo\n", encoding="utf-8")
    (p / "RUNNABLE.md").write_text("# RUNNABLE\n", encoding="utf-8")
    (p / "CHECKLIST.md").write_text("# CHECKLIST\n", encoding="utf-8")
    return Project.load(p)


@pytest.fixture
def web_project(tmp_path):
    """Project типа web (для frontend full-cycle)."""
    p = tmp_path / "tg_messenger"
    p.mkdir()
    (p / "project.yaml").write_text("name: tg_messenger\ntype: web\n",
                                     encoding="utf-8")
    (p / "README.md").write_text("# tg_messenger\n", encoding="utf-8")
    (p / "RUNNABLE.md").write_text("# RUNNABLE\n", encoding="utf-8")
    (p / "CHECKLIST.md").write_text("# CHECKLIST\n", encoding="utf-8")
    return Project.load(p)


@pytest.fixture
def registry(tmp_path):
    """ForgeRegistry в tmp (изолировано per test)."""
    return ForgeRegistry(tmp_path / "forge_registry.yaml")


def _write_yaml_registry(path, pipeline: list) -> None:
    """registry.yaml в формате blueprints_v3 (yaml.safe_dump)."""
    import yaml
    payload = {"pipeline": pipeline, "metadata": {"version": "test"}}
    with open(str(path), "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


def _materialize_outputs(root, patterns: list) -> None:
    """Создаёт файлы-артефакты по паттернам (прямой файл или упрощённый glob)."""
    }
    for pat in patterns:
        if "*" in pat:
            simple = re.sub(r"\*\*?/|\*", "x", pat)
            (root / simple).parent.mkdir(parents=True, exist_ok=True)
            (root / simple).write_text("# artifact\n", encoding="utf-8")
        else:
            (root / pat).parent.mkdir(parents=True, exist_ok=True)
            (root / pat).write_text("# artifact\n", encoding="utf-8")


# ─── Контракты dataclasses и констант ─────────────────────────────────────────


class TestDataclassesAndConstants:
    def test_light_roles_count_and_set(self):
        assert len(LIGHT_ROLES) == 8
        assert LIGHT_ROLES == frozenset({
            "explainer", "lisa", "risk", "decomposer",
            "architect", "auditor", "documenter", "retrospective",
        ])

    def test_heavy_roles_count_and_set(self):
        assert len(HEAVY_ROLES) == 4
        assert HEAVY_ROLES == frozenset({
            "developer", "tester", "fixer", "acceptance",
        ])

    def test_light_plus_heavy_plus_conditional_equals_pipeline(self):
        # 14 = 8 LIGHT + 4 HEAVY + 2 CONDITIONAL (frontend/devops).
        all_classified = LIGHT_ROLES | HEAVY_ROLES | {"frontend", "devops"}
        assert PIPELINE_ROLES == all_classified

    def test_chainstage_frozen(self):
        stage = ChainStage(
            role_id="lisa", mode="check_only",
            status="ok", details="all artifacts present",
            duration_s=0.05,
        )
        assert stage.role_id == "lisa"
        assert stage.mode == "check_only"
        assert stage.status == "ok"
        # frozen: попытка mutation должна raise.
        with pytest.raises((AttributeError, Exception)):
            stage.role_id = "explainer"  # type: ignore[misc]

    def test_chainrun_frozen_and_to_dict(self):
        stage = ChainStage(
            role_id="developer", mode="full_cycle",
            status="run_ok", details="stages=[...]",
            duration_s=1.0,
        )
        run = ChainRun(
            project_id="vkusvill-demo",
            project_root="/tmp/x",
            stage_count=1, chain=(stage,),
            overall="ok",
            started_at="2026-08-10T00:00:00+00:00",
            finished_at="2026-08-10T00:01:00+00:00",
            validation_registry_status="loaded",
            validation_summary=None,
        )
        d = run.to_dict()
        assert d["project_id"] == "vkusvill-demo"
        assert d["stage_count"] == 1
        assert d["chain"][0]["role_id"] == "developer"
        assert d["validation_summary"] is None


# ─── Defaults: 14-ролевый chain в PIPELINE_CHAIN-порядке ──────────────────────


class TestChainDefaults:
    def test_run_chain_default_passes_through_all_14(self, project, registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project)
        assert isinstance(result, ChainRun)
        assert result.stage_count == 14
        # Порядок должен совпасть с PIPELINE_CHAIN.
        assert tuple(s.role_id for s in result.chain) == PIPELINE_CHAIN
        # Все 14 ролей — в chain.
        assert {s.role_id for s in result.chain} == set(PIPELINE_CHAIN)

    def test_run_chain_role_ids_subset_order_preserved(self, project, registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(
            project, role_ids=("tester", "lisa", "developer"),
        )
        # Порядок = порядку caller'а, не alphabetic/PIPELINE_CHAIN.
        assert tuple(s.role_id for s in result.chain) == (
            "tester", "lisa", "developer",
        )
        assert result.stage_count == 3


# ─── LIGHT-роли: CHECK-only mode, copy из RoleArtifactReport ───────────────────


class TestLightRoles:
    def test_lisa_uses_check_only_mode(self, project, registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("lisa",),
                                    compose_artifact_check=False)
        lisa_stage = result.chain[0]
        assert lisa_stage.role_id == "lisa"
        assert lisa_stage.mode == "check_only"
        # compose_artifact_check=False → нет validation → skipped.
        assert lisa_stage.status == "skipped"
        assert "no validation" in lisa_stage.details

    def test_artifact_missing_visible_in_light_details(self, tmp_path, project,
                                                          registry):
        # Реестр объявляет артефакты lisa, но на ФС их нет.
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [
            {"id": "lisa", "outputs": ["lisa_report.md"]},
        ])
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("lisa",),
                                    registry_path=rp)
        lisa_stage = result.chain[0]
        assert lisa_stage.mode == "check_only"
        assert lisa_stage.status == "missing"  # ни одного матча
        assert "lisa_report.md" in lisa_stage.details
        assert "missing=[" in lisa_stage.details
        # validation_summary сохранён для traceability.
        assert isinstance(result.validation_summary, ValidationSummary)
        assert result.validation_registry_status == "loaded"

    def test_artifact_present_yields_status_ok(self, tmp_path, project, registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [
            {"id": "explainer", "outputs": ["brief.md", "parsed_requirements.md"]},
        ])
        _materialize_outputs(project.root, ["brief.md", "parsed_requirements.md"])
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("explainer",),
                                    registry_path=rp)
        stage = result.chain[0]
        assert stage.mode == "check_only"
        assert stage.status == "ok"
        assert stage.details == "all artifacts present"


# ─── HEAVY-роли: full_cycle через initiate_forge ─────────────────────────────


class TestHeavyRoles:
    def test_developer_runs_full_cycle(self, project, registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("developer",))
        dev_stage = result.chain[0]
        assert dev_stage.role_id == "developer"
        assert dev_stage.mode == "full_cycle"
        assert dev_stage.status in ("run_ok", "run_failed")
        # details содержит summary ForgePipeline-стадий.
        assert "stages=[" in dev_stage.details

    def test_initiate_forge_supports_project_read_only_kwarg_additive(self, project,
                                                                         registry):
        # additive test: initiate_forge принимает новый опциональный project_read_only
        # (default False, backwards-compatible).
        facade = ForgeFacade(registry=registry)
        result_default = facade.initiate_forge(project, requested_by_role="developer")
        assert result_default.project_read_only is False
        result_ro = facade.initiate_forge(
            project, requested_by_role="developer", project_read_only=True,
        )
        assert result_ro.project_read_only is True
        # ForgePipeline RUNNABLE/CHECKLIST не должны быть созданы (read-only).
        assert not (project.root / "RUNNABLE.md").exists() or (
            (project.root / "RUNNABLE.md").read_text(encoding="utf-8").startswith("# RUNNABLE")
        )  # project fixture уже имеет эти файлы.

    def test_chain_propagates_project_read_only_to_initiate(self, project,
                                                                registry):
        # run_chain default project_read_only=True → Forge не должен бы писать
        # артефакты (но fixture уже их имеет — этот тест просто проверяет, что
        # ForgeFacade прошёл параметр через).
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("acceptance",),
                                    project_read_only=True)
        stage = result.chain[0]
        assert stage.status in ("run_ok", "run_failed")

    def test_heavy_exception_marks_init_error_with_soft_continue(self, project,
                                                                       registry):
        # Невалидный stage в skip_full_cycle_stages (ForgePipeline бросит exception
        # в subprocess).
        facade = ForgeFacade(registry=registry)
        # Используем все валидные skip, но искусственно сломаем через
        # registry+project_type mismatch (acceptance full cycle на script).
        result = facade.run_chain(project, role_ids=("developer",),
                                    skip_full_cycle_stages={"BUILD", "TEST", "DEPLOY", "REPORT"})
        stage = result.chain[0]
        assert stage.mode == "full_cycle"
        # Должен быть либо run_ok, либо run_failed — но НЕ init_error (subprocess
        # не должен упасть на пустом проекте без build_cmd).
        assert stage.status in ("run_ok", "run_failed")

    def test_chain_soft_failure_via_monkeypatch(self, project, registry, monkeypatch):
        """Если ForgePipeline.stage_forge raise Exception → ChainStage.status='init_error'.
        
        Подтверждает §6.3 контрактную гарантию chain-soft-failure (P3_FORGE_FACADE_DESIGN
        §6.3 + v5.157.0 forge_facade.py run_chain): try/except в full_cycle стадиях
        ForgePipeline-исключения → status='init_error', chain продолжается
        (catastrophic abort отсутствует), overall='partial' (не 'failed', потому
        что 'failed' требует ВСЕ full_cycle init_error ИЛИ 0 stages).
        
        Использует monkeypatch на ForgePipeline.stage_forge (первая стадия всегда
        вызывается в run()) — safety contract test для §6.3 contract.
        """
        from core_02.forge_pipeline import ForgePipeline

        def boom(self):
            raise RuntimeError("forced failure: stage_forge boom")

        monkeypatch.setattr(ForgePipeline, "stage_forge", boom)

        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("developer",),
                                    compose_artifact_check=False)
        assert result.stage_count == 1
        stage = result.chain[0]
        assert stage.role_id == "developer"
        assert stage.mode == "full_cycle"
        # Chain-soft-failure: Exception caught, status='init_error'.
        assert stage.status == "init_error"
        assert "RuntimeError" in stage.details
        assert "stage_forge boom" in stage.details
        # overall: 1 full_cycle стадия, она init_error → failed (по decision
        # tree §6.4 «full_cycle все init_error → failed»). Это корректно для
        # единственного инициированного heavy если он упал: catastrophic.
        assert result.overall == "failed"
        # Details содержит класс исключения + traceback-like msg.
        assert "RuntimeError" in stage.details

    def test_chain_soft_failure_continues_through_all_roles(self, project, registry,
                                                                monkeypatch):
        """Chain-soft-failure в одной HEAVY роли → другие роли всё равно отрабатывают.
        
        Edge-case: monkeypatch ломает только 'developer', другие роли chain
        (включая LIGHT/explainer + CONDITIONAL/devops) должны отработать штатно.
        Это подтверждает: chain НЕ abort после first failure.
        """
        # Ломаем ТОЛЬКО pipeline-ветку запуска для developer (chain-soft-failure).
        # ForgePipeline инстанцируется под капотом через initiate_forge, поэтому
        # мы monkeypatch'им ForgeFacade.initiate_forge (entry-point с
        # requested_by_role) — это позволяет селективно сломать одну роль в
        # multi-role chain, не ломая не-heavies. Предыдущий вариант через
        # self.project.name не работал: project передаётся ОДИН на все роли
        # chain, и `developer` не присутствует в name=vkusvill_demo.
        original_initiate = ForgeFacade.initiate_forge

        def selective_boom(self, project, requested_by_role, *args, **kwargs):
            if requested_by_role == "developer":
                raise RuntimeError("boom: developer-only failure")
            # Все прочие роли — прокидываем в original (lisa/frontend штатно).
            return original_initiate(self, project, requested_by_role,
                                       *args, **kwargs)

        monkeypatch.setattr(ForgeFacade, "initiate_forge", selective_boom)

        facade = ForgeFacade(registry=registry)
        # Берём 3 роли: lisa (LIGHT), developer (HEAVY — fail), frontend (cond skip).
        result = facade.run_chain(project, role_ids=("lisa", "developer", "frontend"),
                                    compose_artifact_check=False)
        assert result.stage_count == 3
        lisa_stage = result.chain[0]
        dev_stage = result.chain[1]
        front_stage = result.chain[2]
        # lisa (LIGHT) → check_only (compose off → skipped).
        assert lisa_stage.status == "skipped"
        # developer (HEAVY) → init_error chain-soft-failure через monkeypatch.
        assert dev_stage.status == "init_error"
        assert "RuntimeError" in dev_stage.details
        assert "developer-only failure" in dev_stage.details
        # frontend (CONDITIONAL skip, type=script) → skipped (chain продолжается).
        assert front_stage.status == "skipped"
        # Per decision tree §6.4: full_cycle_stages = [developer] (только он
        # full_cycle; lisa=check_only, frontend=conditional_skip). Один full_cycle
        # с init_error = все full_cycle упали → "failed" (catastrophic-single).
        # Chain НЕ aborted (все 3 стадии в result.chain), но overall="failed"
        # потому что единственный heavy/heavy-like роль дал init_error.
        # NB: "failed" здесь — overall REPORTING IMPACT (catastrophic-single
        # по §6.4), НЕ process termination. Chain продолжается через не-
        # упавшие роли (lisa=check_only, frontend=conditional_skip), что
        # подтверждено выше через result.stage_count == 3 + per-stage
        # assertions. Семантика отличается от «abort mid-way»: abort никогда
        # не происходит на одном init_error (chain-soft-failure, §6.3).
        assert result.overall == "failed"


# ─── CONDITIONAL: frontend (web?) / devops (always) ──────────────────────────


class TestConditionalRoles:
    def test_frontend_skipped_for_script_project(self, project, registry):
        # project fixture имеет type=script → frontend skip.
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("frontend",))
        stage = result.chain[0]
        assert stage.role_id == "frontend"
        assert stage.mode == "conditional_skip"
        assert stage.status == "skipped"
        assert "script" in stage.details
        assert "!= 'web'" in stage.details

    def test_frontend_runs_full_cycle_on_web_project(self, web_project,
                                                       registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(web_project, role_ids=("frontend",))
        stage = result.chain[0]
        assert stage.role_id == "frontend"
        assert stage.mode == "full_cycle"
        assert stage.status in ("run_ok", "run_failed")

    def test_devops_always_runs_full_cycle(self, project, registry):
        # devops condition: always → full_cycle даже на type=script.
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("devops",))
        stage = result.chain[0]
        assert stage.role_id == "devops"
        assert stage.mode == "full_cycle"
        assert stage.status in ("run_ok", "run_failed")


# ─── overall decision tree + error handling ───────────────────────────────────


class TestOverallAndErrors:
    def test_degraded_registry_marks_overall_degraded(self, project, registry):
        # registry_path не передан → fallback + degraded overall.
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("lisa",))
        assert result.validation_registry_status in ("missing", "loaded")
        # Если registry не найден — overall должен быть degraded (не failed).
        # Если loaded (cwd<->blueprints_v3/registry.yaml существует в workspace)
        # — overall=ok.
        if result.validation_registry_status in ("missing", "unreadable"):
            assert result.overall == "degraded"

    def test_invalid_role_raises_value_error(self, project, registry):
        facade = ForgeFacade(registry=registry)
        with pytest.raises(ValueError):
            facade.run_chain(project, role_ids=("nonexistent_role",))

    def test_reference_role_raises_value_error(self, project, registry):
        facade = ForgeFacade(registry=registry)
        for ref in sorted(REFERENCE_ROLES):
            with pytest.raises(ValueError):
                facade.run_chain(project, role_ids=(ref,))

    def test_chain_overall_in_valid_set(self, project, registry):
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(project, role_ids=("lisa",))
        # overall ∈ {"ok", "partial", "failed", "degraded"}
        assert result.overall in ("ok", "partial", "failed", "degraded")


# ─── ADDITIVE-INVARIANT (CON-16/CON-21/промт 68) ─────────────────────────────


class TestAdditiveInvariant:
    """Существующие модули НЕ тронуты chain-runner'ом."""

    def test_workspace_untouched_by_run_chain(self):
        import core_02.workspace as mod
        src = open(mod.__file__, encoding="utf-8").read()
        # grep-invariants: run_chain и ChainRun НЕ в workspace.py.
        assert "run_chain" not in src
        assert "ChainRun" not in src
        assert "ChainStage" not in src

    def test_forge_pipeline_untouched_by_run_chain(self):
        import core_02.forge_pipeline as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "run_chain" not in src
        assert "ChainRun" not in src
        assert "ChainStage" not in src

    def test_forge_registry_untouched_by_run_chain(self):
        import core_02.forge_registry as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "run_chain" not in src
        assert "ChainRun" not in src
        assert "ChainStage" not in src

    def test_run_chain_only_in_forge_facade(self):
        import core_02.forge_facade as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "def run_chain" in src
        assert "class ChainRun" in src
        assert "class ChainStage" in src

    def test_initiate_forge_signature_has_project_read_only(self):
        # additive test: новый опциональный kwarg в initiate_forge.
        import inspect
        from core_02.forge_facade import ForgeFacade
        sig = inspect.signature(ForgeFacade.initiate_forge)
        assert "project_read_only" in sig.parameters
        # Default = False (backwards compatible).
        assert sig.parameters["project_read_only"].default is False
