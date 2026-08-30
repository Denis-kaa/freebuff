# tests_09/test_v0_1_boundaries.py — R-123/R-124/R-127 closure (промт 68, v0.1)
#
# Закрытие оставшихся границ §34.5 для v0.1 (ранее отложенных на v0.2):
#   R-123 (B1) — forge register → auto-registration в WorkspaceRegistry
#   R-124 (B2) — ForgePipeline project_read_only (Forge не мутирует Project)
#   R-127 (B10) — ForgeRegistry.validate_schema (UNFORGED ≠ UNTESTED, machine-checkable)
import pytest

from core_02.forge_pipeline import ForgePipeline
from core_02.forge_registry import (
    DEPLOYED,
    FAILED,
    UNFORGED,
    ForgeRegistry,
)
from core_02.workspace import Project
from scripts_01 import forge as forge_mod


# ── fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "demo"
    p.mkdir()
    (p / "project.yaml").write_text("name: demo\ntype: python\n", encoding="utf-8")
    (p / "README.md").write_text("# Demo", encoding="utf-8")
    (p / "RUNNABLE.md").write_text("## Быстрый старт\n```bash\ncd demo\n```\n", encoding="utf-8")
    (p / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
    return Project.load(p)


@pytest.fixture
def registry(tmp_path):
    return ForgeRegistry(tmp_path / "registry.yaml")


# ── R-123 (B1): forge register → WorkspaceRegistry auto-registration ─────


class TestR123B1AutoRegister:
    def test_auto_register_workspace_creates_entry(self, project, tmp_path):
        """forge register → проект автоматически привязывается к workspace 'rabota'."""
        from core_02.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry(tmp_path / "ws.db")
        slug = forge_mod._auto_register_workspace(project, registry=reg)
        assert slug == "rabota"
        ws = reg.find_workspace_for_project(str(project.root))
        assert ws is not None
        assert ws.slug == "rabota"

    def test_auto_register_idempotent(self, project, tmp_path):
        """Повторная регистрация — no-op (idempotent), slug тот же."""
        from core_02.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry(tmp_path / "ws.db")
        s1 = forge_mod._auto_register_workspace(project, registry=reg)
        s2 = forge_mod._auto_register_workspace(project, registry=reg)
        assert s1 == s2 == "rabota"
        ws = reg.find_workspace_for_project(str(project.root))
        assert ws.slug == "rabota"

    def test_auto_register_degradation_does_not_crash(self, project):
        """Graceful degradation (CON-21): ошибка workspace-слоя не роняет регистрацию."""
        class BoomRegistry:
            def seed_defaults(self):
                raise RuntimeError("boom")

            def find_workspace_for_project(self, path):
                raise RuntimeError("boom")

            def add_project(self, *a, **k):
                raise RuntimeError("boom")

        slug = forge_mod._auto_register_workspace(project, registry=BoomRegistry())
        assert slug is None


# ── R-124 (B2): ForgePipeline project_read_only ─────────────────────────


class TestR124B2ReadOnly:
    def test_read_only_does_not_create_artifacts(self, tmp_path):
        """project_read_only=True → Forge НЕ создаёт RUNNABLE.md/CHECKLIST.md."""
        p = tmp_path / "no_artifacts"
        p.mkdir()
        (p / "project.yaml").write_text("name: no_artifacts\ntype: python\n", encoding="utf-8")
        (p / "README.md").write_text("# x", encoding="utf-8")
        proj = Project.load(p)
        pipe = ForgePipeline(proj, project_read_only=True)
        res = pipe.stage_forge()
        assert res.status == "failed"  # артефактов нет → read-only проверка падает
        assert "read-only" in res.details
        assert not (p / "RUNNABLE.md").exists()
        assert not (p / "CHECKLIST.md").exists()

    def test_read_only_with_artifacts_passes(self, project):
        """Артефакты на месте → read-only FORGE ok, состояние не мутируется."""
        before = {f.name for f in project.root.iterdir()}
        pipe = ForgePipeline(project, project_read_only=True)
        res = pipe.stage_forge()
        assert res.status == "ok"
        assert "не мутировалось" in res.details
        after = {f.name for f in project.root.iterdir()}
        assert before == after  # ничего не создано и не изменено

    def test_default_mode_still_creates_artifacts(self, tmp_path):
        """Обратная совместимость: дефолт (project_read_only=False) создаёт артефакты."""
        p = tmp_path / "default_mode"
        p.mkdir()
        (p / "project.yaml").write_text("name: default_mode\ntype: python\n", encoding="utf-8")
        (p / "README.md").write_text("# x", encoding="utf-8")
        proj = Project.load(p)
        res = ForgePipeline(proj).stage_forge()
        assert res.status == "ok"
        assert (p / "RUNNABLE.md").exists()

    def test_missing_artifacts_helper(self, tmp_path):
        p = tmp_path / "partial"
        p.mkdir()
        (p / "project.yaml").write_text("name: partial\ntype: python\n", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        proj = Project.load(p)
        pipe = ForgePipeline(proj, project_read_only=True)
        missing = pipe._missing_artifacts()
        assert missing == ["CHECKLIST.md"]


# ── R-127 (B10): validate_schema (UNFORGED ≠ UNTESTED) ──────────────────


class TestR127B10Schema:
    def test_valid_unforged_passes(self, registry):
        pid = registry.register_project("fresh", "/tmp/fresh")
        assert registry.validate_schema() == []
        assert registry.schema_violations == []

    def test_unforged_with_last_run_at_violation(self, tmp_path):
        reg = ForgeRegistry(tmp_path / "r.yaml")
        reg.register_project("bad", "/tmp/bad")
        # симулируем битый реестр: UNFORGED, но last_run_at установлен
        reg._data["bad"]["last_run_at"] = "2026-08-10T00:00:00+00:00"
        violations = reg.validate_schema()
        assert any("UNFORGED but last_run_at" in v for v in violations)

    def test_unforged_with_last_pipeline_violation(self, tmp_path):
        reg = ForgeRegistry(tmp_path / "r.yaml")
        reg.register_project("bad2", "/tmp/bad2")
        reg._data["bad2"]["last_pipeline"] = {"overall": "ok"}
        violations = reg.validate_schema()
        assert any("UNFORGED but last_pipeline" in v for v in violations)

    def test_deployed_requires_last_run_at(self, tmp_path):
        reg = ForgeRegistry(tmp_path / "r.yaml")
        reg.register_project("ran", "/tmp/ran")
        reg._data["ran"]["status"] = DEPLOYED  # без last_run_at → нарушение
        violations = reg.validate_schema()
        assert any("DEPLOYED/FAILED implies a run" in v for v in violations)

    def test_record_run_produces_valid_schema(self, registry):
        """record_run переводит UNFORGED→DEPLOYED с last_run_at → схема валидна."""
        pid = registry.register_project("ok", "/tmp/ok")
        registry.record_run(pid, {"overall": "ok", "stages": []})
        assert registry.validate_schema() == []

    def test_invalid_status_violation(self, tmp_path):
        reg = ForgeRegistry(tmp_path / "r.yaml")
        reg.register_project("weird", "/tmp/weird")
        reg._data["weird"]["status"] = "UNTESTED"  # UNTESTED не в STATUSES
        violations = reg.validate_schema()
        assert any("invalid status" in v and "UNTESTED" in v for v in violations)

    def test_missing_required_field_violation(self, tmp_path):
        reg = ForgeRegistry(tmp_path / "r.yaml")
        pid = reg.register_project("no_root", "/tmp/x")
        assert pid == "no-root"  # _slug: не-алфанум → '-'
        del reg._data["no-root"]["root"]
        violations = reg.validate_schema()
        assert any("missing required field 'root'" in v for v in violations)

    def test_unreadable_yaml_reported_as_violation(self, tmp_path):
        """R-127: битый YAML не молча выглядит валидным — фиксируется violation."""
        path = tmp_path / "corrupted.yaml"
        path.write_text("projects: [unclosed\n", encoding="utf-8")
        reg = ForgeRegistry(path)
        violations = reg.validate_schema()
        assert any("unreadable YAML" in v for v in violations)
        assert reg.schema_violations == violations
