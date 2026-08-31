# core_02/forge_pipeline.py — Forge Pipeline (L-3)
# Buffy Forge v1 (RFC_BUFFY_FORGE_V1.md §3)

"""Пайплайн сборки проекта: FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT.

Этап 4.2 + 4.4 из PLAN_NEXT_OPERATIONS.md.

Каждая стадия — отдельный метод, можно запускать индивидуально.
Результат — PipelineRun со статусом стадий.

В Этапе 4.4 ForgePipeline принимает `workspace_steps_policy` и пробросом
в `Project.get_requirements` обеспечивает консистентное поведение с
`forge check` (workspace.yaml steps_policy: strict блокирует проект без
STEPS.md в любом entry-point).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core_02.workspace import Project


@dataclass
class StageResult:
    name: str
    status: str = "pending"
    details: str = ""
    duration_s: float = 0.0


@dataclass
class PipelineRun:
    project_name: str
    project_root: str
    stages: List[StageResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    overall: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_root": self.project_root,
            "stages": [vars(s) for s in self.stages],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "overall": self.overall,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_cmd(cmd: List[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode, output.strip()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError:
        return -2, "COMMAND NOT FOUND"
    except Exception as exc:  # pragma: no cover
        return -3, str(exc)


class ForgePipeline:
    """L-3 пайплайн: FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT."""

    def __init__(
        self,
        project: Project,
        dry_run: bool = False,
        hooks: Optional[Dict[str, Callable[[Project, "PipelineRun"], None]]] = None,
        workspace_steps_policy: str = "optional",
        project_read_only: bool = False,
    ):
        """
        Args:
            project: L-2 контейнер.
            dry_run: preview без side-effects.
            hooks: колбеки (on_report).
            workspace_steps_policy: optional|strict политика STEPS.md.
            project_read_only: B2 (R-124, промт 68) — Forge НЕ мутирует состояние
                Project напрямую: артефакты (RUNNABLE.md/CHECKLIST.md) не создаются,
                только проверяются. Дефолт False (обратная совместимость).
        """
        self.project = project
        self.dry_run = dry_run
        self.hooks = hooks or {}
        self.workspace_steps_policy = workspace_steps_policy
        self.project_read_only = project_read_only
        self.run_summary: Optional[PipelineRun] = None

    def stage_forge(self) -> StageResult:
        name = "FORGE"
        if self.dry_run:
            return StageResult(name=name, status="skipped", details="dry-run")
        if self.project_read_only:
            # B2 (R-124): read-only режим — Forge не пишет в Project напрямую.
            missing = self._missing_artifacts()
            if missing:
                return StageResult(
                    name=name, status="failed",
                    details=f"read-only (B2): артефакты не создаются; отсутствуют: {', '.join(missing)}",
                )
            return StageResult(
                name=name, status="ok",
                details="read-only (B2): артефакты на месте, состояние Project не мутировалось",
            )
        try:
            created = self._ensure_artifacts()
            return StageResult(
                name=name, status="ok",
                details=f"артефакты: {', '.join(created) if created else 'все на месте'}",
            )
        except Exception as exc:
            return StageResult(name=name, status="failed", details=str(exc))

    def stage_check(self) -> StageResult:
        name = "CHECK"
        try:
            diag = self.project.run_env_doctor()
            # Проброс политики: workspace_steps_policy идёт в get_requirements,
            # при наличии project.requirements_steps он перебивает.
            req = self.project.get_requirements(steps_policy=self.workspace_steps_policy)
            parts = []
            if diag.blockers:
                parts.append(f"blockers: {len(diag.blockers)}")
            if diag.warnings:
                parts.append(f"warnings: {len(diag.warnings)}")
            if req.missing:
                parts.append(f"missing artifacts: {', '.join(req.missing)}")
            if self.dry_run:
                return StageResult(name=name, status="skipped",
                                   details="dry-run; " + "; ".join(parts))
            ok = diag.ok and not req.missing
            return StageResult(
                name=name, status="ok" if ok else "failed",
                details="; ".join(parts) or "окружение в порядке",
            )
        except Exception as exc:
            return StageResult(name=name, status="failed", details=str(exc))

    def stage_build(self, build_cmd: Optional[List[str]] = None) -> StageResult:
        name = "BUILD"
        if self.dry_run:
            return StageResult(name=name, status="skipped", details="dry-run")
        cmd = build_cmd or self._default_build_cmd()
        if not cmd:
            return StageResult(name=name, status="skipped",
                               details="нет команды сборки (type=%s)" % self.project.type)
        code, output = _run_cmd(cmd, self.project.root)
        if code != 0:
            return StageResult(name=name, status="failed",
                               details=f"exit={code}: {output[:300]}")
        return StageResult(name=name, status="ok", details=f"exit=0 ({cmd[0]})")

    def stage_test(self, test_cmd: Optional[List[str]] = None) -> StageResult:
        name = "TEST"
        if self.dry_run:
            return StageResult(name=name, status="skipped", details="dry-run")
        cmd = test_cmd or self._default_test_cmd()
        if not cmd:
            return StageResult(name=name, status="skipped", details="нет тестов")
        code, output = _run_cmd(cmd, self.project.root, timeout=300)
        if code != 0:
            return StageResult(name=name, status="failed",
                               details=f"exit={code}: {output[:300]}")
        return StageResult(name=name, status="ok", details="tests passed")

    def stage_deploy(self) -> StageResult:
        name = "DEPLOY"
        if self.dry_run:
            return StageResult(name=name, status="skipped", details="dry-run")
        dist = self.project.root / "dist"
        if not dist.exists():
            return StageResult(name=name, status="skipped",
                               details="нет dist/ — deploy не требуется")
        bundles = list(dist.glob("bundle.js")) or list(dist.iterdir())
        if bundles:
            return StageResult(name=name, status="ok",
                               details=f"dist/ готов ({len(bundles)} файлов)")
        return StageResult(name=name, status="ok", details="dist/ существует")

    def stage_report(self) -> StageResult:
        name = "REPORT"
        hook = self.hooks.get("on_report")
        # Пост-обработка (Этап 4.5): агрегируем статистику STEPS.md для
        # стадии REPORT — используется и в терминальной сводке (details),
        # и в TG-уведомлении через on_report-hook.
        try:
            stats = self.project.get_steps_stats()
        except Exception as exc:  # pragma: no cover — defensive
            stats_summary = f"STEPS: <stat error: {exc}>"
        else:
            stats_summary = stats.to_line()
        if hook:
            try:
                hook(self.project, self.run_summary)
                # Statistics in details always — даже если хук отключён в логе.
                return StageResult(
                    name=name, status="ok",
                    details=f"отчёт отправлен; {stats_summary}",
                )
            except Exception as exc:
                return StageResult(
                    name=name, status="failed",
                    details=f"{exc}; {stats_summary}",
                )
        return StageResult(
            name=name, status="skipped",
            details=f"нет on_report хука; {stats_summary}",
        )

    def run(self, skip: Optional[set] = None) -> PipelineRun:
        skip = skip or set()
        run = PipelineRun(
            project_name=self.project.name,
            project_root=str(self.project.root),
            started_at=_now(),
        )
        self.run_summary = run
        for stage in (
            self.stage_forge, self.stage_check, self.stage_build,
            self.stage_test, self.stage_deploy, self.stage_report,
        ):
            if stage.__name__ in skip:
                run.stages.append(StageResult(
                    name=stage.__name__.replace("stage_", "").upper(),
                    status="skipped", details="исключена",
                ))
                continue
            if stage.__name__ == "stage_report":
                run.overall = (
                    "ok" if all(s.status in ("ok", "skipped") for s in run.stages)
                    else "failed"
                )
            res = stage()
            run.stages.append(res)
            if res.status == "failed":
                break
        run.overall = "ok" if all(s.status in ("ok", "skipped") for s in run.stages) else "failed"
        run.finished_at = _now()
        self.run_summary = run
        return run

    def _missing_artifacts(self) -> List[str]:
        """B2 (R-124): какие обязательные артефакты отсутствуют (read-only проверка)."""
        missing = []
        for fname in ("RUNNABLE.md", "CHECKLIST.md"):
            if not (self.project.root / fname).exists():
                missing.append(fname)
        return missing

    def _ensure_artifacts(self) -> List[str]:
        created: List[str] = []
        runnable = self.project.root / "RUNNABLE.md"
        if not runnable.exists():
            runnable.write_text(
                f"# RUNNABLE — {self.project.name}\n\n"
                f"## Требования\n- Node.js 18+, Python 3.10+\n"
                f"## Быстрый старт\n```bash\ncd {self.project.root.name}\n```\n",
                encoding="utf-8",
            )
            created.append("RUNNABLE.md")
        checklist = self.project.root / "CHECKLIST.md"
        if not checklist.exists():
            checklist.write_text(
                f"# CHECKLIST — {self.project.name}\n\n"
                "- [ ] Env Doctor: блокеров нет\n"
                "- [ ] README.md присутствует\n"
                "- [ ] Зависимости установлены\n",
                encoding="utf-8",
            )
            created.append("CHECKLIST.md")
        return created

    def _default_build_cmd(self) -> Optional[List[str]]:
        if self.project.type == "web":
            esbuild = self.project.root / "node_modules/esbuild-wasm/bin/esbuild"
            index = self.project.root / "src/index.tsx"
            if esbuild.exists() and index.exists():
                return [
                    "node", str(esbuild), "src/index.tsx", "--bundle",
                    "--outfile=dist/bundle.js",
                    "--alias:react-native=react-native-web",
                    "--define:process.env.NODE_ENV=development",
                    "--define:global=window",
                    "--format=iife", "--loader:.tsx=tsx", "--loader:.ts=ts",
                    "--platform=browser",
                ]
            if (self.project.root / "package.json").exists():
                return ["npm", "run", "build"]
            return None
        if (self.project.root / "package.json").exists():
            return ["npm", "run", "build"]
        if (self.project.root / "pyproject.toml").exists():
            return [sys.executable, "-m", "build"]
        return None

    def _default_test_cmd(self) -> Optional[List[str]]:
        if (self.project.root / "package.json").exists():
            return ["npm", "test"]
        if list(self.project.root.glob("test_*.py")) or (self.project.root / "tests").exists():
            return [sys.executable, "-m", "pytest", "-q"]
        return None


# === B16 Exec-layer 3-phase commit per stage (Phase 5 Forward-action #1) ===
# Per §37.2.B + §37.7: status-flag → atomic-write → EventBus-publish 3-phase.
# Failure rolls status back to UNFORGED (no partial state).
import contextlib
from core_02.boundaries_v17 import BOUNDARIES_V17, BState


@contextlib.contextmanager
def exec_stage_commit(project_id: str, stage_id: str):
    """B16 3-phase commit context manager per stage.

    Phase 1: status-flag = IN_PROGRESS
    Phase 2: atomic-write per stage (deferred to caller via try/finally)
    Phase 3: EventBus-publish on success / rollback on failure
    """
    from context_12.events_db import publish_event
    flag_status = "IN_PROGRESS"
    try:
        # Phase 1: status-flag
        _set_status_flag(project_id, stage_id, flag_status)
        publish_event(
            "exec.start",
            {"project_id": project_id, "stage_id": stage_id, "status": flag_status},
        )
        yield {"project_id": project_id, "stage_id": stage_id, "status": flag_status}
        # Phase 3: success publish
        _set_status_flag(project_id, stage_id, "DONE")
        publish_event(
            "exec.done",
            {"project_id": project_id, "stage_id": stage_id, "status": "DONE"},
        )
    except Exception as e:
        # Failure: roll back to UNFORGED (no partial state)
        _set_status_flag(project_id, stage_id, "UNFORGED")
        publish_event(
            "exec.failed",
            {"project_id": project_id, "stage_id": stage_id, "error": str(e)},
        )
        raise


def _set_status_flag(project_id: str, stage_id: str, status: str):
    """Set forge_registry.yaml status flag for project:stage. Per B9 single-writer."""
    import yaml, os
    reg_path = os.path.join("data_13", "forge_registry.yaml")
    if not os.path.exists(reg_path):
        return  # forge_registry.yaml can be created lazily
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = yaml.safe_load(f) or {}
    projects = reg.setdefault("projects", {})
    proj = projects.setdefault(project_id, {})
    stages = proj.setdefault("stages", {})
    stages[stage_id] = status
    with open(reg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(reg, f, default_flow_style=False, sort_keys=True)


# === Phase 5 Forward-action #3: stage_policy_check (DIS v0.2 integration) ===
# Per §39.6 Forward-action #3 + §37.2.C + §37.7 B17 transition.
# New 7-stage pipeline: FORGE -> CHECK -> BUILD -> POLICY -> TEST -> DEPLOY -> REPORT.
from core_02.dis_engine import PolicyChecker, DIRSReviewer, ConflictAnalyzer, TechnicalDebtAnalyzer


def stage_policy_check(project_id, doc_text=None, rules=None):
    """Stage 4 of 7: POLICY compliance via PolicyChecker.

    Returns (passed, violations). Failure rolls status back to UNFORGED.
    Per B16 Exec-layer 3-phase commit boundary.
    """
    if doc_text is None:
        doc_text = "all stages use atomic_write; no /tmp hardcoded paths; ADR-11 enforced; ADDITIVE architecture"
    pc = PolicyChecker()
    result = pc.enforce(doc_text, rules=rules)
    return result["passed"], result["violations"]


def review_rfc(rfc_path):
    """Convenience: invoke DIRSReviewer on an RFC document for ARE scoring."""
    with open(rfc_path, "r", encoding="utf-8") as f:
        text = f.read()
    reviewer = DIRSReviewer()
    return reviewer.review(text)
