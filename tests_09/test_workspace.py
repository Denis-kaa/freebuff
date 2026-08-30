# tests_09/test_workspace.py — Workspace (L-1) / Project (L-2) (Этап 4.1 + Этап 4.4 STEPS.md)
import pytest

from core_02.workspace import (
    Project,
    ProjectRequirements,
    Workspace,
    _validate_steps_format,
)


@pytest.fixture
def project_dir(tmp_path):
    p = tmp_path / "demo_app"
    p.mkdir()
    (p / "project.yaml").write_text(
        "name: demo_app\ntype: web\nstack: [react, node]\nroles: [web_dev]\ncontracts: [build]\n",
        encoding="utf-8",
    )
    (p / "README.md").write_text("# Demo", encoding="utf-8")
    (p / "RUNNABLE.md").write_text(
        "## Быстрый старт\n```bash\nnpm run dev\n```\nWeb fallback: да\n",
        encoding="utf-8",
    )
    (p / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
    return p


@pytest.fixture
def steps_ok(tmp_path):
    p = tmp_path / "STEPS.md"
    p.write_text(
        "# STEPS.md — demo\n\n"
        "> **Проект:** `demo`\n"
        "> **Формат:** `step N: ...`\n\n"
        "---\n\n"
        "## step 1: первая запись\n\nтело\n\n---\n\n",
        encoding="utf-8",
    )
    return p


class TestProject:
    def test_load_from_config(self, project_dir):
        proj = Project.load(project_dir)
        assert proj.name == "demo_app"
        assert proj.type == "web"
        assert proj.stack == ["react", "node"]
        assert proj.roles == ["web_dev"]
        assert proj.contracts == ["build"]

    def test_load_without_config(self, tmp_path):
        p = tmp_path / "plain"
        p.mkdir()
        (p / "README.md").write_text("# plain", encoding="utf-8")
        proj = Project.load(p)
        assert proj.name == "plain"
        assert proj.type == "unknown"

    def test_requirements_all_present(self, project_dir):
        proj = Project.load(project_dir)
        req = proj.get_requirements()
        assert req.has_readme and req.has_runnable and req.has_checklist
        assert req.missing == []
        assert req.has_web_fallback is True

    def test_requirements_missing(self, tmp_path):
        p = tmp_path / "bare"
        p.mkdir()
        proj = Project.load(p)
        req = proj.get_requirements()
        assert req.missing == ["README.md", "RUNNABLE.md", "CHECKLIST.md"]
        assert req.has_steps is False
        assert req.steps_format_ok is True

    def test_env_doctor_runs(self, project_dir):
        proj = Project.load(project_dir)
        diag = proj.run_env_doctor()
        assert hasattr(diag, "ok")
        assert isinstance(diag.blockers, list)

    def test_agents_md(self, tmp_path):
        p = tmp_path / "agents_proj"
        p.mkdir()
        (p / "AGENTS.md").write_text("## Роли", encoding="utf-8")
        proj = Project.load(p)
        assert "Роли" in proj.get_agents_md()

    def test_to_dict(self, project_dir):
        proj = Project.load(project_dir)
        d = proj.to_dict()
        assert d["name"] == "demo_app"
        assert d["requirements"]["readme"] is True
        assert d["requirements"]["steps"] is False

    # STEPS.md (Этап 4.4) — backward-compat: optional по умолчанию
    def test_steps_md_optional(self, project_dir):
        proj = Project.load(project_dir)
        req = proj.get_requirements()
        assert req.has_steps is False
        assert req.missing == []

    def test_steps_md_present_ok(self, project_dir, steps_ok):
        import shutil
        shutil.copy(str(steps_ok), str(project_dir / "STEPS.md"))
        proj = Project.load(project_dir)
        req = proj.get_requirements()
        assert req.has_steps is True
        assert req.steps_format_ok is True

    def test_append_step_creates_file(self, tmp_path):
        p = tmp_path / "fake"
        p.mkdir()
        proj = Project.load(p)
        n = proj.append_step("Init", "первая запись в журнале.")
        assert n == 1
        assert "## step 1: Init" in (p / "STEPS.md").read_text(encoding="utf-8")

    def test_append_step_increments(self, tmp_path):
        p = tmp_path / "fake"
        p.mkdir()
        proj = Project.load(p)
        proj.append_step("Init", "первая.")
        n2 = proj.append_step("Continue", "вторая.")
        assert n2 == 2
        text = (p / "STEPS.md").read_text(encoding="utf-8")
        assert "## step 1: Init" in text
        assert "## step 2: Continue" in text


class TestStepsPolicy:
    """STEPS.md policy: project.requirements_steps > workspace.steps_policy > 'optional'."""

    def test_project_load_reads_requirements_steps_required(self, tmp_path):
        p = tmp_path / "strict_proj"
        p.mkdir()
        (p / "project.yaml").write_text(
            "name: strict_proj\nrequirements:\n  steps: required\n", encoding="utf-8"
        )
        (p / "README.md").write_text("# strict_proj", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## Быстрый старт\n", encoding="utf-8")
        (p / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
        proj = Project.load(p)
        assert proj.requirements_steps == "required"

    def test_project_load_normalizes_strict_to_required(self, tmp_path):
        """'strict' в project.yaml — алиас workspace-level термина ('required')."""
        p = tmp_path / "strict_proj"
        p.mkdir()
        (p / "project.yaml").write_text(
            "name: strict_proj\nrequirements:\n  steps: strict\n", encoding="utf-8"
        )
        proj = Project.load(p)
        # Нормализация: на стороне проекта хранится каноническое 'required'
        assert proj.requirements_steps == "required"

    def test_project_load_ignores_invalid_requirements_steps(self, tmp_path):
        p = tmp_path / "weird_proj"
        p.mkdir()
        (p / "project.yaml").write_text(
            "name: weird_proj\nrequirements:\n  steps: reinvent\n", encoding="utf-8"
        )
        proj = Project.load(p)
        assert proj.requirements_steps is None

    def test_strict_project_requires_steps_missing(self, tmp_path):
        p = tmp_path / "needs_steps"
        p.mkdir()
        (p / "project.yaml").write_text(
            "name: needs_steps\nrequirements:\n  steps: required\n", encoding="utf-8"
        )
        (p / "README.md").write_text("# X", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (p / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
        proj = Project.load(p)
        req = proj.get_requirements()
        assert "STEPS.md" in req.missing

    def test_workspace_steps_policy_required_via_arg(self, tmp_path):
        """get_requirements(steps_policy='required'/'strict') блокирует отсутствующий STEPS.md."""
        p = tmp_path / "no_steps"
        p.mkdir()
        (p / "project.yaml").write_text("name: no_steps\n", encoding="utf-8")
        (p / "README.md").write_text("# x", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (p / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
        proj = Project.load(p)
        for mode in ("required", "strict"):
            req = proj.get_requirements(steps_policy=mode)
            assert "STEPS.md" in req.missing, f"mode={mode}"
        for mode in (None, "optional"):
            req = proj.get_requirements(steps_policy=mode)
            assert "STEPS.md" not in req.missing, f"mode={mode}"

    def test_project_override_optional_overrides_strict_workspace(self, tmp_path):
        """project.yaml `requirements.steps: optional` > workspace.yaml strict."""
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        (ws_root / "workspace.yaml").write_text("steps_policy: strict\n", encoding="utf-8")
        proj_dir = ws_root / "soft_pro"
        proj_dir.mkdir()
        (proj_dir / "project.yaml").write_text(
            "name: soft_pro\nrequirements:\n  steps: optional\n", encoding="utf-8"
        )
        (proj_dir / "README.md").write_text("# soft_pro", encoding="utf-8")
        (proj_dir / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (proj_dir / "CHECKLIST.md").write_text("- [x) ok\n", encoding="utf-8")
        proj = Project.load(proj_dir)
        assert proj.requirements_steps == "optional"
        # Workspace-level strict игнорируется из-за project override.
        from core_02.workspace import Workspace
        ws = Workspace.load(ws_root)
        # Workspace.validate прогоняет через steps_policy=self.steps_policy,
        # но project.requirements_steps перебивает.
        req = proj.get_requirements(steps_policy=ws.steps_policy)
        assert "STEPS.md" not in req.missing


class TestStepsStats:
    """Project.get_steps_stats() + StepsStats.to_line() (Этап 4.5: REPORT enrichment)."""

    def test_missing_returns_empty_stats(self, tmp_path):
        p = tmp_path / "no_steps_proj"
        p.mkdir()
        proj = Project.load(p)
        stats = proj.get_steps_stats()
        assert stats.exists is False
        assert stats.count == 0
        assert stats.last_step_n is None
        assert stats.format_ok is False
        assert stats.format_problems == []
        # to_line для отсутствующего файла — короткая форма.
        assert stats.to_line() == "STEPS: missing"

    def test_quality_for_only_header_no_steps(self, tmp_path):
        """Файл с шапкой, но без ## step N: → count=0, last=None, format не OK."""
        p = tmp_path / "header_only"
        p.mkdir()
        (p / "STEPS.md").write_text(
            "# STEPS.md — header_only\n\n> **Проект:** `header_only`\n\n---\n\n",
            encoding="utf-8",
        )
        proj = Project.load(p)
        # Должно существовать как Project, не нужно никаких артефактов,
        # get_steps_stats() обращается только к STEPS.md.
        stats = proj.get_steps_stats()
        assert stats.exists is True
        assert stats.count == 0
        assert stats.last_step_n is None
        assert stats.format_ok is False
        # format_problems включает "не найден ни один заголовок".
        assert any("step" in prb.lower() for prb in stats.format_problems)
        # to_line: last=none отсутствует, format=malformed
        assert "format=malformed" in stats.to_line()

    def test_counts_steps_and_records_last(self, tmp_path):
        p = tmp_path / "many_steps"
        p.mkdir()
        (p / "STEPS.md").write_text(
            "# STEPS.md — many_steps\n\n"
            "## step 1: первая\n\nbody 1\n\n---\n\n"
            "## step 2: вторая\n\nbody 2\n\n---\n\n"
            "## step 3: третья\n\nbody 3\n\n---\n\n",
            encoding="utf-8",
        )
        proj = Project.load(p)
        stats = proj.get_steps_stats()
        assert stats.exists is True
        assert stats.count == 3
        assert stats.last_step_n == 3
        assert stats.format_ok is True
        assert stats.format_problems == []
        line = stats.to_line()
        assert "count=3" in line
        assert "last=#3" in line
        assert "format=OK" in line

    def test_non_contiguous_step_numbers(self, tmp_path):
        """Поддержка ручной нумерации: 1, 5, 7 → count=3, last=7."""
        p = tmp_path / "non_contig"
        p.mkdir()
        (p / "STEPS.md").write_text(
            "# STEPS.md — non_contig\n\n"
            "## step 1: init\n\nbody\n\n---\n\n"
            "## step 5: jump\n\nbody\n\n---\n\n"
            "## step 7: end\n\nbody\n\n---\n\n",
            encoding="utf-8",
        )
        proj = Project.load(p)
        stats = proj.get_steps_stats()
        assert stats.count == 3
        assert stats.last_step_n == 7
        assert stats.format_ok is True

    def test_malformed_file_format_problems_recorded(self, tmp_path):
        p = tmp_path / "bad_steps"
        p.mkdir()
        (p / "STEPS.md").write_text(
            "это не шапка и не `## step N:`\n\nкакой-то текст\n",
            encoding="utf-8",
        )
        proj = Project.load(p)
        stats = proj.get_steps_stats()
        assert stats.exists is True
        assert stats.count == 0
        assert stats.format_ok is False
        assert len(stats.format_problems) >= 1
        # to_line: count=0, без last, format=malformed.
        line = stats.to_line()
        assert "format=malformed" in line
        assert "count=0" in line


class TestWorkspace:
    def test_load_with_workspace_yaml(self, tmp_path):
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        (ws_root / "workspace.yaml").write_text(
            "name: my-workspace\nprojects: [alpha]\ndefault_environment: staging\n",
            encoding="utf-8",
        )
        alpha = ws_root / "alpha"
        alpha.mkdir()
        (alpha / "project.yaml").write_text("name: alpha\ntype: cli\n", encoding="utf-8")
        (alpha / "README.md").write_text("# alpha", encoding="utf-8")
        ws = Workspace.load(ws_root)
        assert ws.name == "my-workspace"
        assert ws.default_environment == "staging"
        assert len(ws.projects) == 1
        assert ws.projects[0].name == "alpha"

    def test_load_steps_policy_default_optional(self, tmp_path):
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        (ws_root / "workspace.yaml").write_text("name: x\n", encoding="utf-8")
        ws = Workspace.load(ws_root)
        assert ws.steps_policy == "optional"

    def test_load_steps_policy_strict(self, tmp_path):
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        (ws_root / "workspace.yaml").write_text("steps_policy: strict\n", encoding="utf-8")
        ws = Workspace.load(ws_root)
        assert ws.steps_policy == "strict"

    def test_scan_without_yaml(self, tmp_path):
        ws_root = tmp_path / "ws2"
        ws_root.mkdir()
        for name in ("proj_a", "proj_b"):
            d = ws_root / name
            d.mkdir()
            (d / "README.md").write_text("# %s" % name, encoding="utf-8")
        ws = Workspace.load(ws_root)
        names = {p.name for p in ws.projects}
        assert names == {"proj_a", "proj_b"}

    def test_get_project(self, tmp_path):
        ws_root = tmp_path / "ws3"
        ws_root.mkdir()
        d = ws_root / "target"
        d.mkdir()
        (d / "project.yaml").write_text("name: target\n", encoding="utf-8")
        ws = Workspace.load(ws_root)
        assert ws.get_project("target") is not None
        assert ws.get_project("missing") is None

    def test_validate_health(self, tmp_path):
        ws_root = tmp_path / "ws4"
        ws_root.mkdir()
        d = ws_root / "ok_proj"
        d.mkdir()
        (d / "project.yaml").write_text("name: ok_proj\ntype: cli\n", encoding="utf-8")
        (d / "README.md").write_text("# ok", encoding="utf-8")
        (d / "RUNNABLE.md").write_text("## Быстрый старт\n", encoding="utf-8")
        (d / "CHECKLIST.md").write_text("- [x)\n", encoding="utf-8")
        ws = Workspace.load(ws_root)
        health = ws.validate()
        assert len(health.projects) == 1
        assert health.projects[0]["requirements_missing"] == []

    def test_validate_strict_workspace_degrades_no_steps(self, tmp_path):
        """Workspace.steps_policy=strict и проект без STEPS.md → degraded."""
        ws_root = tmp_path / "ws5"
        ws_root.mkdir()
        (ws_root / "workspace.yaml").write_text("steps_policy: strict\n", encoding="utf-8")
        d = ws_root / "needs_steps_proj"
        d.mkdir()
        (d / "project.yaml").write_text("name: needs_steps_proj\ntype: cli\n", encoding="utf-8")
        (d / "README.md").write_text("# x", encoding="utf-8")
        (d / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (d / "CHECKLIST.md").write_text("- [x)\n", encoding="utf-8")
        ws = Workspace.load(ws_root)
        health = ws.validate()
        assert "needs_steps_proj" in health.degraded
        assert "STEPS.md" in health.projects[0]["requirements_missing"]
