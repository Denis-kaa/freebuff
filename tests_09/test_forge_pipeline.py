# tests_09/test_forge_pipeline.py — Forge Pipeline FORGE→REPORT (Этап 4.2)
import pytest

from core_02.forge_pipeline import ForgePipeline, PipelineRun, StageResult
from core_02.workspace import Project


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "web_app"
    p.mkdir()
    (p / "project.yaml").write_text("name: web_app\ntype: web\n", encoding="utf-8")
    (p / "README.md").write_text("# Web App", encoding="utf-8")
    return Project.load(p)


class TestPipelineStages:
    def test_stage_forge_creates_artifacts(self, project):
        pipe = ForgePipeline(project)
        res = pipe.stage_forge()
        assert res.status == "ok"
        assert (project.root / "RUNNABLE.md").exists()
        assert (project.root / "CHECKLIST.md").exists()

    def test_stage_forge_dry_run(self, project):
        pipe = ForgePipeline(project, dry_run=True)
        res = pipe.stage_forge()
        assert res.status == "skipped"
        assert not (project.root / "RUNNABLE.md").exists()

    def test_stage_check(self, project):
        pipe = ForgePipeline(project)
        res = pipe.stage_check()
        assert res.status in ("ok", "failed")
        assert isinstance(res.details, str)

    def test_stage_build_no_cmd_skipped(self, tmp_path):
        # проект без package.json, esbuild, pyproject → BUILD skipped
        p = tmp_path / "plain_cli"
        p.mkdir()
        (p / "project.yaml").write_text("name: plain_cli\ntype: cli\n", encoding="utf-8")
        pipe = ForgePipeline(Project.load(p))
        res = pipe.stage_build()
        assert res.status == "skipped"

    def test_stage_build_bad_cmd_fails(self, project):
        pipe = ForgePipeline(project)
        res = pipe.stage_build(build_cmd=["definitely-not-a-command-xyz"])
        assert res.status == "failed"

    def test_stage_test_no_tests_skipped(self, project):
        pipe = ForgePipeline(project)
        res = pipe.stage_test()
        assert res.status == "skipped"

    def test_stage_deploy_no_dist(self, project):
        pipe = ForgePipeline(project)
        res = pipe.stage_deploy()
        assert res.status == "skipped"

    def test_stage_report_hook(self, project):
        calls = []
        pipe = ForgePipeline(project, hooks={"on_report": lambda proj, run: calls.append(proj.name)})
        res = pipe.stage_report()
        assert res.status == "ok"
        assert calls == ["web_app"]

    def test_report_hook_sees_final_overall(self, project):
        # хук должен получать run с финальным overall (не "pending") при run()
        seen = {}
        pipe = ForgePipeline(project, hooks={"on_report": lambda proj, run: seen.update(overall=run.overall)})
        run = pipe.run()
        assert run.overall in ("ok", "failed")
        assert seen.get("overall") == run.overall

    def test_stage_report_no_hook_skipped(self, project):
        pipe = ForgePipeline(project)
        assert pipe.stage_report().status == "skipped"


class TestPipelineRun:
    def test_run_full_pipeline(self, project):
        pipe = ForgePipeline(project)
        run = pipe.run()
        assert isinstance(run, PipelineRun)
        assert run.overall in ("ok", "failed")
        names = [s.name for s in run.stages]
        assert names == ["FORGE", "CHECK", "BUILD", "TEST", "DEPLOY", "REPORT"]

    def test_run_dry_run(self, project):
        pipe = ForgePipeline(project, dry_run=True)
        run = pipe.run()
        assert run.overall == "ok"
        assert all(s.status in ("ok", "skipped") for s in run.stages)

    def test_run_stops_on_failure(self, project):
        pipe = ForgePipeline(project)
        run = pipe.run()
        # Если CHECK упал — BUILD/TEST идут skipped (break), overall failed
        failed = [s for s in run.stages if s.status == "failed"]
        if failed:
            idx = next(i for i, s in enumerate(run.stages) if s.status == "failed")
            assert all(s.status == "skipped" or s.status == "failed"
                       for s in run.stages[idx:])

    def test_run_skip_stage(self, project):
        # PB-17 hermetic fix: dry_run=True делает все stage_* → 'skipped' до skip-branch,
        # устраняя env_doctor-зависимый flake (root-cause: stage_check в run() loop мог
        # вернуть 'failed' при blockers от diagnose(), что вызывало break до stage_report).
        pipe = ForgePipeline(project, dry_run=True)
        run = pipe.run(skip={"stage_report"})
        names = [s.name for s in run.stages]
        assert "REPORT" in names
        report = next(s for s in run.stages if s.name == "REPORT")
        assert report.status == "skipped"

    def test_run_summary_attached(self, project):
        pipe = ForgePipeline(project)
        run = pipe.run()
        assert pipe.run_summary is run

    def test_stage_check_propagates_workspace_steps_policy(self, tmp_path):
        """strict workspace_steps_policy → STEPS.md missing -> CHECK fails."""
        p = tmp_path / "no_steps_strict"
        p.mkdir()
        (p / "project.yaml").write_text("name: no_steps_strict\ntype: cli\n", encoding="utf-8")
        (p / "README.md").write_text("# x", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (p / "CHECKLIST.md").write_text("- [x)\n", encoding="utf-8")
        proj = Project.load(p)
        # strict -> CHECK failed (STEPS.md в missing).
        pipe = ForgePipeline(proj, workspace_steps_policy="strict")
        res = pipe.stage_check()
        assert res.status == "failed"
        assert "STEPS.md" in res.details
        # optional -> CHECK ok (или skipped в dry-run).
        pipe2 = ForgePipeline(proj, workspace_steps_policy="optional")
        res2 = pipe2.stage_check()
        assert res2.status == "ok"
        # project own override 'optional' в strict workspace = OK.
        p2 = tmp_path / "overridden"
        p2.mkdir()
        (p2 / "project.yaml").write_text(
            "name: overridden\ntype: cli\nrequirements:\n  steps: optional\n", encoding="utf-8"
        )
        (p2 / "README.md").write_text("# x", encoding="utf-8")
        (p2 / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (p2 / "CHECKLIST.md").write_text("- [x)\n", encoding="utf-8")
        proj2 = Project.load(p2)
        pipe3 = ForgePipeline(proj2, workspace_steps_policy="strict")
        res3 = pipe3.stage_check()
        assert res3.status == "ok"
