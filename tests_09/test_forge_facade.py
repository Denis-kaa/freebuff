# tests_09/test_forge_facade.py — ForgeFacade (P3, промт 70 Миссия 2)
import pytest

from core_02.forge_facade import (
    PIPELINE_ROLES,
    REFERENCE_ROLES,
    ChainRun,
    ChainStage,
    ForgeFacade,
    ForgeFacadeResult,
)
from core_02.forge_registry import DEPLOYED, FAILED, UNFORGED, ForgeRegistry
from core_02.workspace import Project


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "web_app"
    p.mkdir()
    (p / "project.yaml").write_text("name: web_app\ntype: web\n", encoding="utf-8")
    (p / "README.md").write_text("# Web App", encoding="utf-8")
    return Project.load(p)


@pytest.fixture
def registry(tmp_path):
    return ForgeRegistry(tmp_path / "forge_registry.yaml")


class TestPipelineRoleGate:
    def test_pipeline_roles_exclude_reference(self):
        assert "developer" in PIPELINE_ROLES
        assert "tester" in PIPELINE_ROLES
        assert "orchestrator" not in PIPELINE_ROLES
        assert "context_keeper" not in PIPELINE_ROLES
        assert "response_writer" not in PIPELINE_ROLES

    def test_chain_length(self):
        # Facade-scope: 14 стадий (12 ядро + frontend + devops).
        # Задача 0 считала 15/17 — включая presale-трек response_writer,
        # который исключён из Facade-scope (дизайн §0.4).
        assert len(PIPELINE_ROLES) == 14
        assert PIPELINE_ROLES == frozenset({
            "explainer", "lisa", "risk", "decomposer", "architect", "auditor",
            "developer", "frontend", "devops", "tester", "fixer",
            "acceptance", "documenter", "retrospective",
        })

    def test_can_initiate_gate(self, registry):
        facade = ForgeFacade(registry=registry)
        assert facade.can_initiate("developer") is True
        assert facade.can_initiate("orchestrator") is False
        assert facade.can_initiate("context_keeper") is False


class TestForgeFacadeInitiate:
    def test_initiate_forge_explicit(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        result = facade.initiate_forge(project, requested_by_role="developer")
        assert isinstance(result, ForgeFacadeResult)
        assert result.requested_by_role == "developer"
        assert result.initiated_explicitly is True
        assert result.status_before == UNFORGED
        assert result.status_after in (DEPLOYED, FAILED)
        assert result.overall in ("ok", "failed")
        # Проект зарегистрирован в реестре
        assert registry.get_project_status(result.project_id) is not None

    def test_initiate_forge_records_run(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        result = facade.initiate_forge(project, requested_by_role="tester")
        history = registry.get_pipeline_history(result.project_id)
        assert len(history) == 1
        assert history[0]["overall"] == result.overall

    def test_initiate_forge_rejects_reference_role(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        for ref in sorted(REFERENCE_ROLES):
            with pytest.raises(ValueError):
                facade.initiate_forge(project, requested_by_role=ref)

    def test_initiate_forge_rejects_unknown_role(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        with pytest.raises(ValueError):
            facade.initiate_forge(project, requested_by_role="nonexistent_role")

    def test_initiate_forge_returns_stages_summary(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        result = facade.initiate_forge(project, requested_by_role="developer")
        names = [s["name"] for s in result.stages]
        assert names == ["FORGE", "CHECK", "BUILD", "TEST", "DEPLOY", "REPORT"]
        assert all(s["status"] in ("ok", "skipped", "failed") for s in result.stages)

    def test_get_status_readonly(self, project, registry):
        facade = ForgeFacade(registry=registry, dry_run=True)
        result = facade.initiate_forge(project, requested_by_role="developer")
        # project_id слагифицируется (web_app → web-app), поэтому берём из результата.
        st = facade.get_status(result.project_id)
        assert st is not None
        assert st.name == "web_app"


class TestForgeFacadeRecordRun:
    """v5.173.0: facade.record_run pass-through (для cmd_chain sentinel-persistence)."""

    def _make_sentinel(self, project_id: str, project_root: str) -> ChainRun:
        """Helper: synthetic ChainRun как cmd_chain делает при soft-failure."""
        return ChainRun(
            project_id=project_id,
            project_root=project_root,
            stage_count=1,
            chain=(
                ChainStage(
                    role_id="<cmd_chain_wrapper>",
                    mode="check_only",
                    status="init_error",
                    details="synthetic test sentinel",
                    duration_s=0.0,
                ),
            ),
            overall="failed",
            started_at="2026-08-10T08:00:00+00:00",
            finished_at="2026-08-10T08:00:01+00:00",
            validation_registry_status="not_run",
        )

    def test_record_run_persists_chain_run_to_registry(self, project, registry):
        # Pre-condition: initiate_forge зарегистрировал проект в registry.
        ForgeFacade(registry=registry, dry_run=True).initiate_forge(
            project, requested_by_role="developer"
        )
        project_id = ForgeRegistry._slug(project.name)
        sentinel = self._make_sentinel(project_id, str(project.root))
        facade = ForgeFacade(registry=registry)
        status = facade.record_run(project.name, sentinel)
        # Sentinel persisted в last_pipeline['chain'].
        assert status.last_pipeline.get("chain") == sentinel.to_dict()["chain"]

    def test_record_run_returns_updated_status_with_last_run_at(
        self, project, registry
    ):
        ForgeFacade(registry=registry, dry_run=True).initiate_forge(
            project, requested_by_role="developer"
        )
        project_id = ForgeRegistry._slug(project.name)
        sentinel = self._make_sentinel(project_id, str(project.root))
        facade = ForgeFacade(registry=registry)
        status = facade.record_run(project.name, sentinel)
        # Returns updated ForgeStatus с populated last_run_at.
        assert status is not None
        assert status.last_run_at is not None
        assert status.last_pipeline.get("overall") == "failed"

    def test_record_run_uses_slug_for_project_id(self, project, registry):
        """DRY: ForgeRegistry._slug используется (НЕ полный root как id)."""
        ForgeFacade(registry=registry, dry_run=True).initiate_forge(
            project, requested_by_role="developer"
        )
        # Project name "web_app" → slug "web-app".
        slug_expected = ForgeRegistry._slug(project.name)
        assert slug_expected == "web-app"
        sentinel = self._make_sentinel(slug_expected, str(project.root))
        facade = ForgeFacade(registry=registry)
        # record_run использует slug(project.name) внутри — call должен SUCCEED.
        status = facade.record_run(project.name, sentinel)
        assert status.name == project.name

    def test_record_run_degraded_keeps_deployed_status(self, project, registry):
        """v5.189.7: degraded ChainRun (exit 0) не даунгрейдит DEPLOYED.

        Регрессия: --resume на сертифицированном проекте с missing registry
        агрегирует overall=degraded → статус не должен упасть в FAILED.
        """
        ForgeFacade(registry=registry, dry_run=True).initiate_forge(
            project, requested_by_role="developer"
        )
        project_id = ForgeRegistry._slug(project.name)
        facade = ForgeFacade(registry=registry)
        ok_run = ChainRun(
            project_id=project_id,
            project_root=str(project.root),
            stage_count=1,
            chain=(ChainStage(
                role_id="developer", mode="full_cycle", status="ok",
                details="certified", duration_s=0.0,
            ),),
            overall="ok",
            started_at="2026-08-10T08:00:00+00:00",
            finished_at="2026-08-10T08:00:01+00:00",
            validation_registry_status="loaded",
            validation_summary=None,
        )
        facade.record_run(project.name, ok_run)
        assert registry.get_project_status(project_id).status == DEPLOYED
        degraded = ChainRun(
            project_id=project_id,
            project_root=str(project.root),
            stage_count=1,
            chain=(ChainStage(
                role_id="developer", mode="check_only", status="ok",
                details="degraded re-run", duration_s=0.0,
            ),),
            overall="degraded",
            started_at="2026-08-10T09:00:00+00:00",
            finished_at="2026-08-10T09:00:01+00:00",
            validation_registry_status="missing",
            validation_summary=None,
        )
        status = facade.record_run(project.name, degraded)
        assert status.status == DEPLOYED  # не даунгрейд
        assert status.last_pipeline.get("overall") == "degraded"
        assert registry.validate_schema() == []

    def test_record_run_unregistered_project_raises_keyerror(self, tmp_path):
        """record_run нерегистрированного проекта → KeyError (per registry.record_run)."""
        p = tmp_path / "ghost_project"
        p.mkdir()
        (p / "project.yaml").write_text("name: ghost_project\n", encoding="utf-8")
        proj = Project.load(p)
        # НЕ зерегистрирован в registry → KeyError expected.
        registry = ForgeRegistry(tmp_path / "forge_registry.yaml")
        facade = ForgeFacade(registry=registry)
        sentinel = self._make_sentinel("ghost-project", str(proj.root))
        with pytest.raises(KeyError):
            facade.record_run(proj.name, sentinel)

    def test_record_run_is_thin_passthrough_no_logic(self, project, registry, monkeypatch):
        """Контракт: facade.record_run — тонкий делегат. registry.record_run
        вызывается ровно один раз с правильными args (project_id = slug).

        Uses ``monkeypatch.setattr`` для guaranteed rollback после test
        (даже при assertion failure или exception в _spy). CR micro-nit fix v5.174.0.
        """
        ForgeFacade(registry=registry, dry_run=True).initiate_forge(
            project, requested_by_role="developer"
        )
        project_id = ForgeRegistry._slug(project.name)
        sentinel = self._make_sentinel(project_id, str(project.root))
        facade = ForgeFacade(registry=registry)
        # Spy: подсчитываем количество вызовов registry.record_run.
        call_count = {"n": 0}
        captured = {"args": None}
        original_record_run = registry.record_run
        def _spy(project_id_arg, run_arg):
            call_count["n"] += 1
            captured["args"] = (project_id_arg, run_arg)
            return original_record_run(project_id_arg, run_arg)
        # monkeypatch.setattr: pytest гарантирует cleanup attribute restoration
        # после test (включая failure paths). Замена raw attribute assignment
        # из v5.173.0 (CR micro-nit).
        monkeypatch.setattr(facade.registry, "record_run", _spy)
        facade.record_run(project.name, sentinel)
        assert call_count["n"] == 1
        assert captured["args"][0] == project_id  # project_id = slug(project.name)
        assert captured["args"][1] is sentinel    # ChainRun passed by reference


class TestS73Invariant:
    """§7.3: Scenario/wizard НЕ импортируют ForgePipeline напрямую (grep-инвариант)."""

    def test_scenario_registry_has_no_forge_import(self):
        import core_02.scenario_registry as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "forge" not in src.lower(), "scenario_registry не должен знать про forge"

    def test_wizard_lib_has_no_forge_import(self):
        import core_02.wizard_lib as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "forge" not in src.lower(), "wizard_lib не должен знать про forge"

    def test_facade_is_the_only_new_bridge(self):
        # Facade импортирует ForgePipeline — это единственное санкционированное место.
        import core_02.forge_facade as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "from core_02.forge_pipeline import ForgePipeline" in src
