# tests_09/test_role_executor.py — RoleExecutorRegistry + LisaExecutor (ADR-016)
#
# Первый вертикальный срез ADR-016 (автоисполнение LIGHT-ролей Blueprint v3):
#   - RoleExecutorRegistry: role_id → executor (register/get/contains/len).
#   - LisaExecutor: детерминированный генератор lisa_report.md (обёртка lisa_estimator).
#   - ForgeFacade.run_chain(light_mode="generate", executor_registry=...):
#     недостающий LIGHT-артефакт материализуется executor'ом, затем re-validation.
#
# Обратная совместимость: дефолт light_mode="check_only" НЕ затрагивает
# существующие тесты test_run_chain.py (они не передают executor_registry).
import pytest

from core_02.forge_facade import ForgeFacade
from core_02.forge_registry import ForgeRegistry
from core_02.role_executor import (
    LLM_ROLE_IDS,
    BaseRoleExecutor,
    LisaExecutor,
    LlmRoleExecutor,
    RoleExecutorRegistry,
    default_executor_registry,
    llm_executor_registry,
)
from core_02.workspace import Project


# ─── helpers ────────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """Минимальный Project с README/RUNNABLE/CHECKLIST (базовый CHECK ok)."""
    p = tmp_path / "sheet_project"
    p.mkdir()
    (p / "project.yaml").write_text("name: sheet_project\ntype: script\n",
                                     encoding="utf-8")
    (p / "README.md").write_text("# sheet_project\n", encoding="utf-8")
    (p / "RUNNABLE.md").write_text("# RUNNABLE\n", encoding="utf-8")
    (p / "CHECKLIST.md").write_text("# CHECKLIST\n", encoding="utf-8")
    return Project.load(p)


@pytest.fixture
def registry(tmp_path):
    return ForgeRegistry(tmp_path / "forge_registry.yaml")


def _write_yaml_registry(path, pipeline: list) -> None:
    import yaml
    payload = {"pipeline": pipeline, "metadata": {"version": "test"}}
    with open(str(path), "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


# ─── RoleExecutorRegistry ────────────────────────────────────────────────────


class TestRoleExecutorRegistry:
    def test_register_and_get(self):
        reg = RoleExecutorRegistry([LisaExecutor()])
        assert "lisa" in reg
        assert isinstance(reg.get("lisa"), LisaExecutor)
        assert reg.role_ids() == ["lisa"]
        assert len(reg) == 1

    def test_get_missing_returns_none(self):
        reg = RoleExecutorRegistry()
        assert reg.get("explainer") is None
        assert "explainer" not in reg

    def test_register_rejects_empty_role_id(self):
        class EmptyExecutor(BaseRoleExecutor):
            role_id = ""

            def execute(self, project, role_id, **kwargs):
                return []

        reg = RoleExecutorRegistry()
        with pytest.raises(ValueError):
            reg.register(EmptyExecutor())

    def test_default_executor_registry_has_lisa(self):
        reg = default_executor_registry()
        assert "lisa" in reg
        assert len(reg) == 1


# ─── LisaExecutor (детерминированный) ────────────────────────────────────────


class TestLisaExecutor:
    def test_generates_lisa_report_from_brief(self, project):
        (project.root / "brief.md").write_text(
            "экспорт таблиц в excel для дашборда\n", encoding="utf-8"
        )
        executor = LisaExecutor()
        created = executor.execute(project, "lisa")
        assert created == ["lisa_report.md"]
        assert (project.root / "lisa_report.md").is_file()
        text = (project.root / "lisa_report.md").read_text(encoding="utf-8")
        assert "LISA Report" in text

    def test_uses_readme_when_no_brief(self, project):
        # fixture имеет только README.md (без brief/parsed/promt) → README.
        executor = LisaExecutor()
        created = executor.execute(project, "lisa")
        assert created == ["lisa_report.md"]
        assert (project.root / "lisa_report.md").is_file()

    def test_falls_back_to_project_name_when_no_input_files(self, tmp_path):
        # Нет ни одного input-файла → description = project.name.
        p = tmp_path / "bare_project"
        p.mkdir()
        (p / "project.yaml").write_text("name: bare_project\ntype: script\n",
                                         encoding="utf-8")
        proj = Project.load(p)
        executor = LisaExecutor()
        created = executor.execute(proj, "lisa")
        assert created == ["lisa_report.md"]
        assert (p / "lisa_report.md").is_file()

    def test_fail_safe_returns_empty_on_error(self, project, monkeypatch):
        executor = LisaExecutor()

        def boom(*args, **kwargs):
            raise RuntimeError("forced lisa failure")

        # LisaExecutor импортирует lisa_estimator внутри execute — ломаем его.
        import scripts_01.lisa_estimator as le
        monkeypatch.setattr(le, "lisa_estimator", boom)
        created = executor.execute(project, "lisa")
        assert created == []
        assert not (project.root / "lisa_report.md").exists()


# ─── ForgeFacade.run_chain(light_mode="generate") ────────────────────────────


class TestRunChainGenerate:
    def test_generate_mode_materializes_missing_lisa(self, tmp_path, project,
                                                     registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [{"id": "lisa", "outputs": ["lisa_report.md"]}])

        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(
            project, role_ids=("lisa",),
            registry_path=rp,
            light_mode="generate",
            executor_registry=default_executor_registry(),
        )
        stage = result.chain[0]
        assert stage.role_id == "lisa"
        assert stage.mode == "generate"
        assert stage.status == "generated"
        assert "lisa_report.md" in stage.details
        assert (project.root / "lisa_report.md").is_file()

    def test_generate_mode_skips_present_artifact(self, tmp_path, project,
                                                  registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [{"id": "lisa", "outputs": ["lisa_report.md"]}])
        (project.root / "lisa_report.md").write_text("# lisa\n", encoding="utf-8")

        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(
            project, role_ids=("lisa",),
            registry_path=rp,
            light_mode="generate",
            executor_registry=default_executor_registry(),
        )
        stage = result.chain[0]
        # Артефакт уже есть → executor НЕ вызывается, остаётся check_only ok.
        assert stage.mode == "check_only"
        assert stage.status == "ok"

    def test_generate_mode_without_executor_stays_check_only(self, tmp_path,
                                                             project, registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [{"id": "lisa", "outputs": ["lisa_report.md"]}])

        facade = ForgeFacade(registry=registry)
        # light_mode=generate, но executor_registry=None → check_only.
        result = facade.run_chain(
            project, role_ids=("lisa",),
            registry_path=rp,
            light_mode="generate",
        )
        stage = result.chain[0]
        assert stage.mode == "check_only"
        assert stage.status == "missing"
        assert not (project.root / "lisa_report.md").exists()

    def test_generate_mode_executor_failure_marks_gen_failed(self, tmp_path,
                                                             project, registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [{"id": "lisa", "outputs": ["lisa_report.md"]}])

        class BoomExecutor(BaseRoleExecutor):
            role_id = "lisa"

            def execute(self, project, role_id, **kwargs):
                raise RuntimeError("forced lisa failure")

        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(
            project, role_ids=("lisa",),
            registry_path=rp,
            light_mode="generate",
            executor_registry=RoleExecutorRegistry([BoomExecutor()]),
        )
        stage = result.chain[0]
        assert stage.mode == "generate"
        assert stage.status == "gen_failed"
        assert "RuntimeError" in stage.details
        # overall: 1 generate-стадия с gen_failed → partial (не failed — см. tree).
        assert result.overall == "partial"

    def test_default_light_mode_is_check_only(self, tmp_path, project, registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [{"id": "lisa", "outputs": ["lisa_report.md"]}])

        facade = ForgeFacade(registry=registry)
        # Без light_mode + executor_registry → дефолт check_only, ничего не пишет.
        result = facade.run_chain(project, role_ids=("lisa",), registry_path=rp)
        stage = result.chain[0]
        assert stage.mode == "check_only"
        assert stage.status == "missing"
        assert not (project.root / "lisa_report.md").exists()

    def test_invalid_light_mode_raises_value_error(self, project, registry):
        facade = ForgeFacade(registry=registry)
        with pytest.raises(ValueError):
            facade.run_chain(project, role_ids=("lisa",), light_mode="bogus")


# ─── LlmRoleExecutor (ADR-016, этап 2) ───────────────────────────────────────


class _FakeResponse:
    """Минимальный stand-in для ModelResponse (нужен только .content)."""

    def __init__(self, content: str):
        self.content = content


class _FakeGateway:
    """Fake ModelGateway: возвращает заготовленный content / бросает исключение."""

    def __init__(self, content: str = "", error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    def generate_by_capabilities(self, capabilities, messages, **kwargs):
        self.calls.append({"capabilities": capabilities, "messages": messages})
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.content)


class _FakeBlueprint:
    """Stand-in для Blueprint (нужен только .sections)."""

    def __init__(self, sections: dict | None = None):
        self.sections = sections or {}


class _FakeCorpus:
    """Fake BlueprintCorpus: load_blueprint + routing_hint без диска."""

    def __init__(self, sections: dict | None = None, hint: list | None = None):
        self.sections = sections or {
            "role": "Test Role",
            "system_role": "do the thing",
            "main_objective": "produce outputs",
            "output_format": "## RESULT",
        }
        self.hint = hint or ["summarize"]

    def load_blueprint(self, role_id: str):
        return _FakeBlueprint(self.sections)

    def routing_hint(self, role_id: str) -> list:
        return list(self.hint)


def _explainer_executor(gateway, corpus=None):
    return LlmRoleExecutor(
        role_id="explainer",
        expected_outputs=("brief.md", "parsed_requirements.md"),
        gateway=gateway,
        corpus=corpus or _FakeCorpus(),
    )


class TestLlmRoleExecutor:
    def test_generates_files_from_file_blocks(self, project):
        gw = _FakeGateway(content=(
            "@@FILE:brief.md\n# Brief\n@@ENDFILE\n"
            "@@FILE:parsed_requirements.md\n# Parsed\n@@ENDFILE\n"
        ))
        ex = _explainer_executor(gw)
        created = ex.execute(project, "explainer")
        assert sorted(created) == ["brief.md", "parsed_requirements.md"]
        assert (project.root / "brief.md").read_text(encoding="utf-8").startswith("# Brief")
        assert (project.root / "parsed_requirements.md").read_text(encoding="utf-8").startswith("# Parsed")

    def test_passes_blueprint_prompt_and_capabilities(self, project):
        gw = _FakeGateway(content="@@FILE:brief.md\nx\n@@ENDFILE\n")
        corpus = _FakeCorpus(hint=["summarize", "explain"])
        ex = _explainer_executor(gw, corpus=corpus)
        ex.execute(project, "explainer")
        assert len(gw.calls) == 1
        call = gw.calls[0]
        assert call["capabilities"] == ["summarize", "explain"]
        system, user = call["messages"]
        assert system["role"] == "system"
        assert "do the thing" in system["content"]
        assert user["role"] == "user"
        assert "@@FILE" in user["content"]
        assert "brief.md" in user["content"]

    def test_ignore_unauthorized_files(self, project):
        # Модель вернула файл вне expected_outputs → отброшен.
        gw = _FakeGateway(content=(
            "@@FILE:brief.md\n# Brief\n@@ENDFILE\n"
            "@@FILE:malicious.py\nprint(1)\n@@ENDFILE\n"
        ))
        ex = _explainer_executor(gw)
        created = ex.execute(project, "explainer")
        assert created == ["brief.md"]
        assert not (project.root / "malicious.py").exists()

    def test_path_traversal_rejected(self, project):
        gw = _FakeGateway(content=(
            "@@FILE:../../etc/passwd\nhacked\n@@ENDFILE\n"
            "@@FILE:brief.md\n# ok\n@@ENDFILE\n"
        ))
        ex = _explainer_executor(gw)
        created = ex.execute(project, "explainer")
        assert created == ["brief.md"]
        # Никакой файл не записан вне project.root (traversal-цель отклонена).
        assert not (project.root / "brief.md").parent.parent.joinpath("etc").exists()
        assert not (project.root / ".." / ".." / "etc" / "passwd").exists()

    def test_fail_safe_on_gateway_error_returns_empty(self, project):
        gw = _FakeGateway(error=RuntimeError("gateway down"))
        ex = _explainer_executor(gw)
        assert ex.execute(project, "explainer") == []

    def test_fail_safe_on_empty_content(self, project):
        gw = _FakeGateway(content="")
        ex = _explainer_executor(gw)
        assert ex.execute(project, "explainer") == []

    def test_single_output_fallback_writes_raw_content(self, project):
        # Роль с одним output + модель без file-block → raw-контент в файл.
        gw = _FakeGateway(content="# Risk Matrix\ncontent here\n")
        ex = LlmRoleExecutor(
            role_id="risk", expected_outputs=("risk_matrix.md",),
            gateway=gw, corpus=_FakeCorpus(),
        )
        created = ex.execute(project, "risk")
        assert created == ["risk_matrix.md"]
        assert (project.root / "risk_matrix.md").read_text(encoding="utf-8").startswith("# Risk Matrix")

    def test_glob_output_matches_concrete_filename(self, project):
        # architect: expected 'adr/*.md' — модель вернула adr/ADR-001.md.
        gw = _FakeGateway(content="@@FILE:adr/ADR-001.md\n# ADR\n@@ENDFILE\n")
        ex = LlmRoleExecutor(
            role_id="architect",
            expected_outputs=("architecture.md", "adr/*.md", "contracts.yaml"),
            gateway=gw, corpus=_FakeCorpus(),
        )
        created = ex.execute(project, "architect")
        assert created == ["adr/ADR-001.md"]
        assert (project.root / "adr" / "ADR-001.md").is_file()


class TestLlmExecutorRegistry:
    def test_registry_contains_lisa_plus_llm_roles(self):
        reg = llm_executor_registry()
        assert "lisa" in reg
        for role_id in LLM_ROLE_IDS:
            assert role_id in reg
            assert isinstance(reg.get(role_id), LlmRoleExecutor)
        assert len(reg) == 1 + len(LLM_ROLE_IDS)

    def test_default_registry_still_only_lisa(self):
        # default_executor_registry НЕ тронут (детерминированный по умолчанию).
        reg = default_executor_registry()
        assert reg.role_ids() == ["lisa"]

    def test_run_chain_generate_uses_llm_executor(self, tmp_path, project, registry):
        rp = tmp_path / "blueprints_v3" / "registry.yaml"
        rp.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(rp, [
            {"id": "explainer", "outputs": ["brief.md", "parsed_requirements.md"]},
        ])
        gw = _FakeGateway(content=(
            "@@FILE:brief.md\n# Brief\n@@ENDFILE\n"
            "@@FILE:parsed_requirements.md\n# Parsed\n@@ENDFILE\n"
        ))
        ex = _explainer_executor(gw)
        facade = ForgeFacade(registry=registry)
        result = facade.run_chain(
            project, role_ids=("explainer",),
            registry_path=rp,
            light_mode="generate",
            executor_registry=RoleExecutorRegistry([ex]),
        )
        stage = result.chain[0]
        assert stage.role_id == "explainer"
        assert stage.mode == "generate"
        assert stage.status == "generated"
        assert (project.root / "brief.md").is_file()
        assert (project.root / "parsed_requirements.md").is_file()
