# core_02/workspace.py — Workspace (L-1) и Project (L-2) контейнеры
# Buffy Forge v1 (RFC_BUFFY_FORGE_V1.md §2a: Workspace → Project)

"""Организационные контейнеры Buffy Forge.

Этап 4.1 + 4.4 из PLAN_NEXT_OPERATIONS.md.

    Workspace (L-1) — верхний уровень: корень, набор проектов,
                      default_environment, steps_policy.
    Project   (L-2) — изолированный проект: конфиг, роли, контракты, требования,
                      diagnostics окружения (Env Doctor), AGENTS.md, STEPS.md,
                      requirements_steps (per-project override).

Политика STEPS.md (Этап 4.4, расширение strict-режима):
  - workspace.yaml поле `steps_policy: optional|strict` (default: optional).
  - project.yaml секция `requirements.steps: optional|required` — per-project override.
  - В режиме optional (default): STEPS.md не блокирует forge check.
  - В режиме strict / required: отсутствие STEPS.md → missing += 'STEPS.md'
    → OVERALL=FAIL в forge check/forge/forge_pipeline.

Резолюция: project.requirements_steps > workspace.steps_policy > 'optional'.
"""

from __future__ import annotations

***REMOVED***
from dataclasses import dataclass, field
***REMOVED***
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


_STEP_REGEX = re.compile(r"^##? step (\d+):", re.MULTILINE)

# Синонимы strict/required: workspace.yaml пишет 'strict', project.yaml — 'required'.
_STRICT_ALIASES = frozenset({"required", "strict"***REMOVED***)


def _steps_template(project_name: str) -> str:
    """Шаблон STEPS.md для только что созданного проекта."""
    return (
        f"# STEPS.md — {project_name***REMOVED***\n\n"
        f"> **Проект:** `{project_name***REMOVED***`\n"
        f"> **Формат:** `step N: <что сделано>; <почему>; <что дальше>`\n\n"
        f"---\n\n"
    )


def _validate_steps_format(path: Path) -> Tuple[bool, List[str***REMOVED******REMOVED***:
    """Валидирует формат STEPS.md: '# STEPS.md' первая строка + минимум один `## step N:`."""
    problems: List[str***REMOVED*** = [***REMOVED***
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        problems.append(f"не удалось прочитать STEPS.md: {exc***REMOVED***")
        return False, problems
    lines = [l for l in text.splitlines() if l.strip()***REMOVED***
    if not lines:
        problems.append("STEPS.md пустой.")
        return False, problems
    head = lines[0***REMOVED***.lstrip("# ").strip().lower()
    if not head.startswith("steps.md"):
        problems.append(
            f"первая строка должна начинаться с «# STEPS.md» (нашла: {lines[0***REMOVED***[:80***REMOVED***!r***REMOVED***)"
        )
    if not _STEP_REGEX.search(text):
        problems.append("не найден ни один заголовок вида `## step N:`.")
    return not problems, problems


# ─── Проект (L-2) ─────────────────────────────────────────────────────────


@dataclass
class StepsStats:
    """Статистика по STEPS.md (для стадии REPORT и TG-уведомлений)."""
    exists: bool
    count: int
    last_step_n: Optional[int***REMOVED***
    format_ok: bool
    format_problems: List[str***REMOVED*** = field(default_factory=list)

    def to_line(self) -> str:
        """Краткая строка для логов и TG: 'count=N last=N format=OK/.../missing'."""
        if not self.exists:
            return "STEPS: missing"
        if not self.format_ok:
            return (
                f"STEPS: count={self.count***REMOVED***"
                + (f" last=#{self.last_step_n***REMOVED***" if self.last_step_n is not None else "")
                + " format=malformed"
            )
        return (
            f"STEPS: count={self.count***REMOVED***"
            + (f" last=#{self.last_step_n***REMOVED***" if self.last_step_n is not None else " last=none")
            + " format=OK"
        )


@dataclass
class ProjectRequirements:
    has_readme: bool = False
    has_runnable: bool = False
    has_checklist: bool = False
    has_steps: bool = False
    has_web_fallback: bool = False
    runnable_quickstart: str = ""
    steps_format_ok: bool = True
    steps_format_problems: List[str***REMOVED*** = field(default_factory=list)
    missing: List[str***REMOVED*** = field(default_factory=list)


@dataclass
class EnvDiagnosis:
    ok: bool
    blockers: List[str***REMOVED*** = field(default_factory=list)
    warnings: List[str***REMOVED*** = field(default_factory=list)
    raw: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class Project:
    """L-2 контейнер: изолированный проект."""
    name: str
    root: Path
    type: str = "unknown"
    stack: List[str***REMOVED*** = field(default_factory=list)
    roles: List[str***REMOVED*** = field(default_factory=list)
    contracts: List[str***REMOVED*** = field(default_factory=list)
    # requirements.steps из project.yaml: 'optional'/'required' — per-project override.
    requirements_steps: Optional[str***REMOVED*** = None
    config_path: Optional[Path***REMOVED*** = None

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        root = Path(path)
        cfg_path = root / "project.yaml"
        if cfg_path.exists() and yaml is not None:
            try:
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {***REMOVED***
            except Exception:
                cfg = {***REMOVED***
        else:
            cfg = {***REMOVED***
        name = cfg.get("name") or root.name
        # Strict-mode per-project override: только валидные значения, иначе None.
        # Принимаем strict/required как синонимы (workspace-side и project-side).
        _rs_raw = (cfg.get("requirements") or {***REMOVED***).get("steps")
        if _rs_raw in ("optional", "required", "strict"):
            # Нормализация: "strict" на стороне project.yaml трактуется как "required"
            # (для единообразия резолюции ниже).
            _requirements_steps = "required" if _rs_raw == "strict" else _rs_raw
        else:
            _requirements_steps = None
        return cls(
            name=name,
            root=root,
            type=cfg.get("type", "unknown"),
            stack=[str(s) for s in cfg.get("stack", [***REMOVED***)***REMOVED***,
            roles=[str(r) for r in cfg.get("roles", [***REMOVED***)***REMOVED***,
            contracts=[str(c) for c in cfg.get("contracts", [***REMOVED***)***REMOVED***,
            requirements_steps=_requirements_steps,
            config_path=cfg_path if cfg_path.exists() else None,
        )

    def get_requirements(self, steps_policy: Optional[str***REMOVED*** = None) -> ProjectRequirements:
        req = ProjectRequirements()
        req.has_readme = (self.root / "README.md").exists()
        req.has_runnable = (self.root / "RUNNABLE.md").exists()
        req.has_checklist = (self.root / "CHECKLIST.md").exists()
        req.has_steps = (self.root / "STEPS.md").exists()
        runnable = self.root / "RUNNABLE.md"
        if runnable.exists():
            text = runnable.read_text(encoding="utf-8")
            req.has_web_fallback = (
                "web" in text.lower()
                and ("fallback" in text.lower() or "фолбэк" in text.lower() or "веб" in text.lower())
            )
            if "quickstart" in text.lower() or "быстрый старт" in text.lower():
                for line in text.splitlines():
                    if line.strip().startswith(("## ", "# ", "```")) and (
                        "quick" in line.lower() or "старт" in line.lower()
                    ):
                        req.runnable_quickstart = line.strip()
                        break
        if req.has_steps:
            req.steps_format_ok, req.steps_format_problems = _validate_steps_format(
                self.root / "STEPS.md"
            )
        missing = [***REMOVED***
        if not req.has_readme:
            missing.append("README.md")
        if not req.has_runnable:
            missing.append("RUNNABLE.md")
        if not req.has_checklist:
            missing.append("CHECKLIST.md")
        # Эффективная политика STEPS.md: project > workspace > 'optional'.
        # Принимаем оба синонима (required/strict).
        eff = str(
            self.requirements_steps or steps_policy or "optional"
        ).strip().lower()
        if eff in _STRICT_ALIASES and not req.has_steps:
            missing.append("STEPS.md")
        req.missing = missing
        return req

    def append_step(self, phase: str, text: str) -> int:
        if not phase.strip():
            raise ValueError("phase не может быть пустым.")
        if not text.strip():
            raise ValueError("text не может быть пустым.")
        steps_path = self.root / "STEPS.md"
        if not steps_path.exists():
            steps_path.parent.mkdir(parents=True, exist_ok=True)
            steps_path.write_text(_steps_template(self.name), encoding="utf-8")
        existing = steps_path.read_text(encoding="utf-8")
        nums = [int(m.group(1)) for m in _STEP_REGEX.finditer(existing)***REMOVED***
        next_n = (max(nums) + 1) if nums else 1
        block = (
            f"## step {next_n***REMOVED***: {phase.strip()***REMOVED***\n\n"
            f"{text.strip()***REMOVED***\n\n"
            f"---\n\n"
        )
        new_text = existing.rstrip() + "\n\n" + block
        steps_path.write_text(new_text, encoding="utf-8")
        return next_n

    def get_steps_stats(self) -> "StepsStats":
        """Агрегированная статистика по STEPS.md проекта.

        Возвращает StepsStats с полями:
          - exists: bool — файл присутствует?
          - count: int — количество заголовков `## step N:`
          - last_step_n: Optional[int***REMOVED*** — максимальный N (None, если нет шагов)
          - format_ok: bool — формат валиден (если exists; иначе False)
          - format_problems: List[str***REMOVED*** — найденные проблемы формата

        Используется в stage_report для post-processing и в TG-уведомлении
        через on_report-hook (см. scripts_01/forge.py: cmd_forge).
        Идемпотентно: читает файл один раз, не модифицирует.
        """
        steps_path = self.root / "STEPS.md"
        if not steps_path.exists():
            return StepsStats(
                exists=False, count=0, last_step_n=None,
                format_ok=False, format_problems=[***REMOVED***,
            )
        try:
            text = steps_path.read_text(encoding="utf-8")
        except Exception as exc:
            return StepsStats(
                exists=True, count=0, last_step_n=None,
                format_ok=False, format_problems=[f"read error: {exc***REMOVED***"***REMOVED***,
            )
        matches = list(_STEP_REGEX.finditer(text))
        nums = [int(m.group(1)) for m in matches***REMOVED***
        format_ok, format_problems = _validate_steps_format(steps_path)
        return StepsStats(
            exists=True,
            count=len(matches),
            last_step_n=max(nums) if nums else None,
            format_ok=format_ok,
            format_problems=format_problems,
        )

    def run_env_doctor(self) -> EnvDiagnosis:
        try:
            from core_02.environment_doctor import diagnose
            raw = diagnose(self.root)
        except Exception as exc:  # pragma: no cover
            return EnvDiagnosis(ok=False, blockers=[f"Env Doctor недоступен: {exc***REMOVED***"***REMOVED***, raw={***REMOVED***)
        blockers = [str(b) for b in raw.get("blockers", [***REMOVED***)***REMOVED***
        warnings = [str(w) for w in raw.get("warnings", [***REMOVED***)***REMOVED***
        return EnvDiagnosis(
            ok=bool(raw.get("ok", not blockers)),
            blockers=blockers,
            warnings=warnings,
            raw=raw,
        )

    def get_agents_md(self) -> str:
        path = self.root / "AGENTS.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        req = self.get_requirements()
        return {
            "name": self.name,
            "root": str(self.root),
            "type": self.type,
            "stack": self.stack,
            "roles": self.roles,
            "contracts": self.contracts,
            "requirements_steps": self.requirements_steps,
            "requirements": {
                "readme": (self.root / "README.md").exists(),
                "runnable": (self.root / "RUNNABLE.md").exists(),
                "checklist": (self.root / "CHECKLIST.md").exists(),
                "steps": (self.root / "STEPS.md").exists(),
                "steps_format_ok": req.steps_format_ok if req.has_steps else None,
                "missing": req.missing,
            ***REMOVED***,
        ***REMOVED***


# ─── Workspace (L-1) ──────────────────────────────────────────────────────


@dataclass
class WorkspaceHealth:
    ok: bool
    projects: List[Dict[str, Any***REMOVED******REMOVED*** = field(default_factory=list)
    degraded: List[str***REMOVED*** = field(default_factory=list)


@dataclass
class Workspace:
    """L-1 контейнер верхнего уровня."""
    name: str
    root: Path
    projects: List[Project***REMOVED*** = field(default_factory=list)
    default_environment: str = "development"
    steps_policy: str = "optional"  # 'optional' (default) | 'strict'
    config_path: Optional[Path***REMOVED*** = None

    @classmethod
    def load(cls, root: str | Path) -> "Workspace":
        root = Path(root)
        cfg_path = root / "workspace.yaml"
        cfg: Dict[str, Any***REMOVED*** = {***REMOVED***
        if cfg_path.exists() and yaml is not None:
            try:
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {***REMOVED***
            except Exception:
                cfg = {***REMOVED***
        ws_policy = str(cfg.get("steps_policy") or "optional").strip().lower()
        if ws_policy not in ("optional", "strict"):
            ws_policy = "optional"
        ws = cls(
            name=cfg.get("name") or root.name,
            root=root,
            default_environment=cfg.get("default_environment", "development"),
            steps_policy=ws_policy,
            config_path=cfg_path if cfg_path.exists() else None,
        )
        configured = [str(p) for p in cfg.get("projects", [***REMOVED***)***REMOVED***
        scan_targets = configured or [
            d.name for d in root.iterdir()
            if (d.is_dir() and not d.name.startswith(".") and (d / "project.yaml").exists())
            or (d.is_dir() and not d.name.startswith(".") and (d / "README.md").exists())
        ***REMOVED***
        seen: set = set()
        for name in scan_targets:
            p = root / name
            if not p.is_dir() or str(p) in seen:
                continue
            seen.add(str(p))
            ws.projects.append(Project.load(p))
        return ws

    def list_projects(self) -> List[Project***REMOVED***:
        return self.projects

    def get_project(self, name: str) -> Optional[Project***REMOVED***:
        for p in self.projects:
            if p.name == name or p.root.name == name:
                return p
        return None

    def validate(self) -> WorkspaceHealth:
        health = WorkspaceHealth(ok=True)
        for p in self.projects:
            diag = p.run_env_doctor()
            req = p.get_requirements(steps_policy=self.steps_policy)
            entry = {
                "name": p.name,
                "root": str(p.root),
                "env_ok": diag.ok,
                "env_blockers": diag.blockers,
                "requirements_missing": req.missing,
            ***REMOVED***
            health.projects.append(entry)
            if not diag.ok:
                health.ok = False
                health.degraded.append(p.name)
            elif req.missing:
                health.degraded.append(p.name)
        return health

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "name": self.name,
            "root": str(self.root),
            "default_environment": self.default_environment,
            "steps_policy": self.steps_policy,
            "projects": [p.to_dict() for p in self.projects***REMOVED***,
        ***REMOVED***


# === B7 Sub-Project container (Phase 5 Forward-action #1) ===
# Per §37.3.2 + §37.7 B7 partial: extend Project with Sub-Project for
# cross-Project Forge scope. Sub-Projects inherit Project metadata but
# maintain isolated forge_run scope.
from core_02.boundaries_v17 import BOUNDARIES_V17, BState


@dataclass(frozen=True)
class SubProject:
    """B7 Sub-Project container per §37.3.2."""
    sub_project_id: str
    parent_project_id: str
    workspace_id: str
    description: str = ""
    isolated_forge_scope: bool = True  # default B7 enforcement

    def namespace(self) -> str:
        return f"subproj:{self.workspace_id***REMOVED***:{self.parent_project_id***REMOVED***:{self.sub_project_id***REMOVED***"


def load_subprojects(parent_project_id: str) -> list:
    """Load Sub-Projects for a parent Project (yaml-driven)."""
    import os, yaml
    subproj_path = os.path.join(
        "projects_17", f"{parent_project_id***REMOVED***", "subprojects.yaml"
    )
    if not os.path.exists(subproj_path):
        return [***REMOVED***
    try:
        with open(subproj_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {***REMOVED***
        subs = data.get("subprojects", [***REMOVED***)
        return [
            SubProject(
                sub_project_id=s["sub_project_id"***REMOVED***,
                parent_project_id=parent_project_id,
                workspace_id=s.get("workspace_id", ""),
                description=s.get("description", ""),
            )
            for s in subs
        ***REMOVED***
    except Exception:
        return [***REMOVED***
