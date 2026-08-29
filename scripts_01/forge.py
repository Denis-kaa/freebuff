#!/usr/bin/env python3
# scripts_01/forge.py — Forge CLI (L-5)
# Buffy Forge v1 (RFC_BUFFY_FORGE_V1.md §3-§5, PLAN_NEXT_OPERATIONS.md Задача 4.4)

"""CLI для Buffy Forge.

Команды:
    forge forge <project_path>    — полный цикл FORGE→REPORT
    forge check <project_path>    — только Env Doctor + требования (вкл. STEPS.md policy)
    forge status [status***REMOVED***         — список проектов со статусами
    forge register <project_path> — зарегистрировать новый проект
    forge report <project_path>   — отчёт в TG
    forge step <project_path> <phase> <text> — добавить запись в STEPS.md

STEPS.md policy (Этап 4.4):
    - workspace.yaml поле `steps_policy: optional|strict`.
    - project.yaml секция `requirements.steps: optional|required|strict`.
    - В strict (или required) режиме отсутствие STEPS.md → OVERALL=FAIL.

Флаги:
    --dry-run   — preview без side-effects
    --no-tg     — не отправлять отчёт в Telegram
"""

from __future__ import annotations

import argparse
import sys
***REMOVED***
from typing import Any, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core_02.forge_pipeline import ForgePipeline  # noqa: E402
from core_02.forge_registry import ForgeRegistry  # noqa: E402
from core_02.workspace import Project  # noqa: E402
import datetime as _dt  # noqa: E402  (v5.167.0: см. cmd_chain soft-failure)


def _load_registry() -> ForgeRegistry:
    return ForgeRegistry(ROOT / "data_13" / "forge_registry.yaml")


def _auto_register_workspace(project: Project, registry=None) -> Optional[str***REMOVED***:
    """B1 (R-123, промт 68): `forge register` → auto-регистрация Project в WorkspaceRegistry.

    Гарантия B1-границы (Workspace⊨Engine): регистрация проекта в Forge-реестре
    теперь автоматически создаёт Project-entry в workspace-слое (workspace↔project
    mapping с privacy-инвариантом, workspace_registry.py).

    Поведение:
      - если путь уже привязан к workspace — idempotent no-op, возвращает slug;
      - иначе проект привязывается к дефолтному workspace 'rabota' (Работа);
      - graceful degradation (CON-21): любая ошибка workspace-слоя НЕ блокирует
        `forge register` (ForgeRegistry остаётся источником истины для статусов).

    Returns workspace slug или None (деградация).
    """
    try:
        from core_02.workspace_registry import WorkspaceRegistry
        reg = registry if registry is not None else WorkspaceRegistry()
        reg.seed_defaults()
        ws = reg.find_workspace_for_project(str(project.root))
        if ws is not None:
            return ws.slug  # уже зарегистрирован (idempotent)
        bound = reg.add_project("rabota", str(project.root))
        if not bound:
            # strict=False: путь отсутствует на FS → привязка не произошла.
            # Не врём «привязан»: возвращаем None (деградация).
            print(
                f"  [workspace***REMOVED*** B1 (R-123): привязка не выполнена — путь "
                f"{project.root***REMOVED*** отсутствует на FS (warn-and-skip)"
            )
            return None
        return "rabota"
    except Exception as exc:  # pragma: no cover — деградация, не блокер
        print(f"  [workspace***REMOVED*** B1 auto-register пропущен: {exc***REMOVED***")
        return None


def _tg_notify(text: str) -> None:
    """Отправить TG-сообщение; gracefully degrade если нет транспорта."""
    try:
        from core_02.telegram_contract import is_tg_available
        if not is_tg_available():
            print("  [tg***REMOVED*** недоступен — отчёт пропущен")
            return
        try:
            from scripts_01.tg_session import send_text_message  # type: ignore
            send_text_message(text)
        except Exception:
            from core_02._tg_client_v2 import TgClientV2  # type: ignore
            client = TgClientV2()
            client.send(text)
        print("  [tg***REMOVED*** отчёт отправлен")
    except Exception as exc:
        print(f"  [tg***REMOVED*** ошибка: {exc***REMOVED***")


def _find_workspace_root(project_path) -> Optional[Path***REMOVED***:
    """Найти директорию с workspace.yaml, поднимаясь до 6 уровней."""
    cur = Path(project_path).resolve()
    if cur.is_file():
        cur = cur.parent
    for _ in range(6):
        if (cur / "workspace.yaml").exists():
            return cur
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent
    return None


def _load_workspace_steps_policy(ws_root: Path) -> str:
    """Прочитать steps_policy из workspace.yaml ('optional' / 'strict')."""
    try:
        import yaml as _yaml
        cfg = _yaml.safe_load(
            (ws_root / "workspace.yaml").read_text(encoding="utf-8")
        ) or {***REMOVED***
    except Exception:
        # Любая ошибка чтения/парсинга yaml → дефолтный lax-режим.
        return "optional"
    value = str(cfg.get("steps_policy") or "optional").strip().lower()
    return value if value in ("optional", "strict") else "optional"


def _workspace_policy_for(project_path) -> str:
    """Удобный wrapper: workspace_root + read policy в одно действие."""
    ws_root = _find_workspace_root(project_path)
    if ws_root is None:
        return "optional"
    return _load_workspace_steps_policy(ws_root)


def _format_steps_line(proj: Project) -> str:
    """Сформировать строку ‘📊 STEPS.md: …’ для TG-уведомления.

    Возвращает пустую строку для проектов, у которых STEPS.md отсутствует
    в optional-режиме (тогда статистика не имеет смысла для релиза).
    В strict/required режиме строка показывает отсутствие файла явно.
    """
    stats = proj.get_steps_stats()
    if not stats.exists:
        return "📊 STEPS.md: нет файла"
    last_part = (
        f", последний #{stats.last_step_n***REMOVED***" if stats.last_step_n is not None
        else ""
    )
    if not stats.format_ok:
        problems = f" ({len(stats.format_problems)***REMOVED*** проблем)" if stats.format_problems else ""
        return f"📊 STEPS.md: {stats.count***REMOVED*** шагов{last_part***REMOVED***, формат malformed{problems***REMOVED***"
    return f"📊 STEPS.md: {stats.count***REMOVED*** шагов{last_part***REMOVED***, формат OK"


def _record_learning_event(run) -> Optional[str***REMOVED***:
    """Phase 4.2 (промт 68): конвертировать PipelineRun output → learning event.

    Закрывает B7 (Factory vs Forge boundary): память получает факт прогона
    (outcome + статус стадий) для Learning Loop. R-3: статус passed|failed
    попадает в context_snapshot, queryable как фильтр.
    """
    try:
        from core_02.memory_store import MemoryStore
        outcome = "success" if run.overall == "ok" else "failure"
        snapshot = {
            "project_name": run.project_name,
            "project_root": run.project_root,
            "overall": run.overall,
            "status": "passed" if run.overall == "ok" else "failed",
            "stages": [
                {"name": s.name, "status": s.status***REMOVED*** for s in run.stages
            ***REMOVED***,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        ***REMOVED***
        with MemoryStore() as ms:
            eid = ms.record_learning_event(
                trigger_id=f"forge:{run.project_name***REMOVED***",
                context_snapshot=snapshot,
                outcome=outcome,
            )
        print(f"  [memory***REMOVED*** learning event {eid***REMOVED*** ({outcome***REMOVED***)")
        return eid
    except Exception as exc:  # graceful degradation: CLI не падает из-за памяти
        print(f"  [memory***REMOVED*** learning event не записан: {exc***REMOVED***")
        return None


def cmd_forge(args: argparse.Namespace) -> int:
    project = Project.load(args.project_path)
    ws_policy = _workspace_policy_for(args.project_path)
    registry = _load_registry()
    registry.register_project(project.name, str(project.root))

    hooks = {***REMOVED***
    if not args.no_tg:
        def _on_report(proj, run):
            steps_line = _format_steps_line(proj)
            msg = (
                f"⛏ Forge: {proj.name***REMOVED*** → {run.overall.upper()***REMOVED***\n"
                f"{steps_line***REMOVED***"
            )
            _tg_notify(msg)

        hooks["on_report"***REMOVED*** = _on_report

    pipe = ForgePipeline(
        project,
        dry_run=args.dry_run,
        hooks=hooks,
        workspace_steps_policy=ws_policy,
    )
    run = pipe.run()
    print(f"\nForge {project.name***REMOVED*** [{project.root***REMOVED******REMOVED***")
    for s in run.stages:
        print(f"  {s.status.upper():8s***REMOVED*** {s.name:6s***REMOVED*** {s.details[:80***REMOVED******REMOVED***")
    print(f"  OVERALL: {run.overall.upper()***REMOVED***")
    if not args.dry_run:
        registry.record_run(project.name, run)
        _record_learning_event(run)  # Phase 4.2 (B7): PipelineRun → learning event
    return 0 if run.overall == "ok" else 1


def cmd_check(args: argparse.Namespace) -> int:
    project = Project.load(args.project_path)
    ws_policy = _workspace_policy_for(args.project_path)
    diag = project.run_env_doctor()
    req = project.get_requirements(steps_policy=ws_policy)
    print(f"Check {project.name***REMOVED*** [{project.root***REMOVED******REMOVED***")
    print(f"  Env Doctor: {'OK' if diag.ok else 'FAIL'***REMOVED***")
    for b in diag.blockers:
        print(f"    blocker: {b***REMOVED***")
    for w in diag.warnings:
        print(f"    warning: {w***REMOVED***")
    print(f"  Артефакты: missing={req.missing or 'нет'***REMOVED***")
    # Краткий комментарий по политике
    eff = str(
        project.requirements_steps or ws_policy or "optional"
    ).strip().lower()
    policy_label = (
        "strict (STEPS.md обязателен)" if eff in ("required", "strict")
        else "optional"
    )
    print(f"  Steps policy: {policy_label***REMOVED***")
    if req.has_steps:
        if req.steps_format_ok:
            print("  STEPS.md: OK")
        else:
            print("  STEPS.md: malformed (warning)")
            for p in req.steps_format_problems:
                print(f"    step-format: {p***REMOVED***")
    else:
        marker = " (warning, optional)" if eff not in ("required", "strict") else ""
        print(f"  STEPS.md: missing{marker***REMOVED***")
    ok = diag.ok and not req.missing
    print(f"  OVERALL: {'OK' if ok else 'FAIL'***REMOVED***")
    return 0 if ok else 1


def cmd_step(args: argparse.Namespace) -> int:
    try:
        project = Project.load(args.project_path)
        n = project.append_step(args.phase, args.text)
    except ValueError as exc:
        print(f"Ошибка: {exc***REMOVED***", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"Проект/путь не найден: {exc***REMOVED***", file=sys.stderr)
        return 2
    print(f"Step #{n***REMOVED*** добавлен в STEPS.md проекта {project.name***REMOVED***.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    registry = _load_registry()
    statuses = registry.list_projects_by_status(args.status)
    if not statuses:
        print("Нет зарегистрированных проектов (forge register <path>)")
        return 1
    print(f"{'PROJECT':24s***REMOVED*** {'STATUS':10s***REMOVED*** ROOT")
    for st in statuses:
        print(f"{st.name:24s***REMOVED*** {st.status:10s***REMOVED*** {st.root***REMOVED***")
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    project = Project.load(args.project_path)
    registry = _load_registry()
    pid = registry.register_project(project.name, str(project.root))
    print(f"Зарегистрирован: {pid***REMOVED*** → {project.root***REMOVED***")
    slug = _auto_register_workspace(project)
    if slug:
        print(f"  [workspace***REMOVED*** B1 (R-123): проект привязан к workspace '{slug***REMOVED***'")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    if args.no_tg:
        print("--no-tg задан, отчёт не отправляю")
        return 0
    project = Project.load(args.project_path)
    _tg_notify(f"⛏ Forge отчёт: {project.name***REMOVED*** ({project.type***REMOVED***)")
    return 0


def _merge_chain_runs(prior_chain: list, partial: Any) -> Any:
    """Merge a partial --resume ChainRun into the prior full chain (v5.189.6).

    Returns a ChainRun covering every role in canonical PIPELINE_CHAIN order:
    roles NOT re-run by --resume keep their prior status; roles re-run get the
    fresh status from ``partial.chain``. Preserves cumulative progress so a
    subsequent --resume continues from the true last ok role (without this the
    partial chain overwrote the full one and the next resume fell back to full).

    Args:
        prior_chain: serialized prior ``last_pipeline['chain'***REMOVED***`` (list[dict***REMOVED***).
        partial: the ChainRun just produced by ``facade.run_chain`` (subset),
            or the soft-failure sentinel on the crash path (v5.189.8) — only
            ``.chain`` and ``.validation_summary`` are consumed.

    Returns:
        Merged ChainRun (stage_count == canonical chain length when prior full;
            crash-sentinel merge appends the ``<cmd_chain_wrapper>`` marker).
    """
    from core_02.forge_facade import (
        PIPELINE_CHAIN,
        ChainRun,
        ChainStage,
        _aggregate_chain_overall,
    )

    merged_map: dict = {***REMOVED***
    for st in prior_chain:
        if isinstance(st, dict) and st.get("role_id"):
            merged_map[st["role_id"***REMOVED******REMOVED*** = ChainStage(
                role_id=st["role_id"***REMOVED***,
                mode=st.get("mode", "check_only"),
                status=st.get("status", "missing"),
                details=st.get("details", ""),
                duration_s=st.get("duration_s", 0.0),
            )
    for st in partial.chain:
        merged_map[st.role_id***REMOVED*** = st

    ordered = [merged_map[rid***REMOVED*** for rid in PIPELINE_CHAIN if rid in merged_map***REMOVED***
    # Defensive: any role outside the canonical chain is appended (custom subsets).
    ordered += [st for rid, st in merged_map.items() if rid not in PIPELINE_CHAIN***REMOVED***

    merged_overall, _ = _aggregate_chain_overall(ordered, partial.validation_summary)
    return ChainRun(
        project_id=partial.project_id,
        project_root=partial.project_root,
        stage_count=len(ordered),
        chain=tuple(ordered),
        overall=merged_overall,
        started_at=partial.started_at,
        finished_at=partial.finished_at,
        validation_registry_status=partial.validation_registry_status,
        validation_summary=partial.validation_summary,
    )


def cmd_chain(args: argparse.Namespace) -> int:
    """Запустить ForgeFacade.run_chain для 14 pipeline-ролей (v5.160.0).

    ADDITIVE: новый subcommand к существующим forge/check/status/register/
    report/step. Существующие команды НЕ тронуты (grep-additive). Tолько
    scripts_01/forge.py расширен — никакой новой модификации core_02/*.

    Режимы (3 mutually-clear modes, по аналогии с cmd_forge):
      - default (safe read-only): run_chain(compose=True, project_read_only=True).
        HEAVY роли прогоняются через initiate_forge, но НЕ мутируют Project
        (B2 R-124 EVER ENFORCED). record_run срабатывает внутри initiate_forge
        (per-role в registry — это часть run_chain semantics, не дублирование).
      - --dry-run: как default, но ForgeFacade(dry_run=True) → ForgePipeline
        early-return на всех стадиях + НЕ _record_learning_event на CLI уровне
        (mirror cmd_forge --dry-run behavior).
      - --full-cycle: project_read_only=False → HEAVY роли мутируют
        RUNNABLE.md/CHECKLIST.md (реальный Forge-прогон). 

    Args:
        project_path: путь к project root (Project.load).
        --roles: comma-separated список ролей (default: все 14 в PIPELINE_CHAIN-порядке).
        --skip-stages: comma-separated substages (FORGE,CHECK,BUILD,TEST,DEPLOY,REPORT).
        --registry-path: явный путь к registry.yaml для RoleArtifactValidator.
        --no-compose: отключить compose artifact check (default=True).
        --generate: автогенерация недостающих LIGHT-артефактов через
            RoleExecutorRegistry (ADR-016; детерминированные роли: lisa).
            Дефолт — check_only (обратная совместимость).
        --json: stdout = ChainRun.to_dict() JSON.
        --no-tg: не отправлять в TG (флаг для symmetry с другими командами).

    Returns:
        exit code: 0 для ok|degraded, 1 для failed|partial.
    """
    import json as _json
    from core_02.forge_facade import ForgeFacade, ChainRun, ChainStage

    project = Project.load(args.project_path)
    ws_policy = _workspace_policy_for(args.project_path)
    registry = _load_registry()
    registry.register_project(project.name, str(project.root))

    role_ids = None
    if args.roles:
        role_ids = tuple(r.strip() for r in args.roles.split(",") if r.strip())

    skip_stages = None
    if args.skip_stages:
        skip_stages = {s.strip().upper() for s in args.skip_stages.split(",") if s.strip()***REMOVED***

    # ── ADR-016: --generate → автоисполнение LIGHT-ролей через RoleExecutorRegistry ──
    # llm_executor_registry = LisaExecutor (детерминированный) + 6 LLM-экзекьюторов
    # (explainer/risk/decomposer/architect/auditor/documenter).
    light_mode = "generate" if args.generate else "check_only"
    executor_registry = None
    if args.generate:
        from core_02.role_executor import llm_executor_registry
        executor_registry = llm_executor_registry()

    facade = ForgeFacade(
        registry=registry,
        dry_run=args.dry_run,
        workspace_steps_policy=ws_policy,
    )

    # v5.169.0 (FIXED-up): routes diagnostic [resume***REMOVED*** + SOFT FAILURE preamble to
    # STDERR если --quiet задан. Declared BEFORE resume block to avoid
    # UnboundLocalError (Python treats diag as local throughout cmd_chain
    # because of later assignment; reference must come AFTER declaration).
    diag = sys.stderr if args.quiet else sys.stdout

    # ── resume-from-cursor semantics (v5.162.0, forward-step FWD-1) ──────
    # Если --resume задан, читаем registry.get_project_status(...).last_pipeline['chain'***REMOVED***
    # ищем последний stage со status в {"ok", "run_ok"***REMOVED*** (completion statuses);
    # resume запускается с next-after этой позиции в PIPELINE_CHAIN.
    # Сериализация ChainRun → last_pipeline уже работает через initiate_forge → record_run
    # (закрывает use-case «знать на чём остановился роли для продолжения»). H4 REBUTTAL
    # (v5.158.0/v5.161.0) подтверждает: не нужны расширения STATUSES — достаточно existing поля.
    prior_chain: list = [***REMOVED***
    if args.resume:
        from core_02.forge_facade import PIPELINE_CHAIN as _PC_RESUME
        project_id = ForgeRegistry._slug(project.name)
        status = registry.get_project_status(project_id)
        resume_from: Optional[str***REMOVED*** = None
        if status is not None and status.last_pipeline is not None:
            prior_chain = status.last_pipeline.get("chain") or [***REMOVED***
            for stage in reversed(prior_chain):
                if (
                    isinstance(stage, dict)
                    and stage.get("status") in ("ok", "run_ok")
                ):
                    resume_from = stage.get("role_id")
                    break
        if resume_from and resume_from in _PC_RESUME:
            idx = _PC_RESUME.index(resume_from) + 1
            remaining = _PC_RESUME[idx:***REMOVED***
            if remaining:
                print(
                    f"  [resume***REMOVED*** last ok/run_ok={resume_from***REMOVED***; "
                    f"resuming {len(remaining)***REMOVED*** roles: {list(remaining)***REMOVED***",
                    file=diag,
                )
                role_ids = tuple(remaining)
            else:
                print(
                    f"  [resume***REMOVED*** все роли уже завершены "
                    f"({resume_from***REMOVED*** — last in PIPELINE_CHAIN)",
                    file=diag,
                )
                return 0
        elif resume_from:
            print(
                f"  [resume***REMOVED*** recorded role_id {resume_from!r***REMOVED*** не в PIPELINE_CHAIN "
                f"(возможно custom subset); running from scratch",
                file=diag,
            )
        else:
            print(
                "  [resume***REMOVED*** нет prior ok/run_ok в last_pipeline; "
                "running from scratch",
                file=diag,
            )

    try:
        run = facade.run_chain(
            project,
            role_ids=role_ids,
            registry_path=args.registry_path,
            compose_artifact_check=not args.no_compose,
            project_read_only=not args.full_cycle,
            skip_full_cycle_stages=skip_stages,
            light_mode=light_mode,
            executor_registry=executor_registry,
        )
    except Exception as exc:  # v5.167.0: soft-failure wrapping.
        # Soft-failure: facade.run_chain может raise на любой стадии (import
        # HEAVY ролей, registry corruption, project shape mismatch, ...). We:
        #   1) capture traceback excerpt (max ~1000 chars для storage sanity);
        #   2) generate synthetic ChainRun (sentinel stage со status='init_error');
        #   3) best-effort persist via facade.record_run if exposed (для последующего
        #      --resume partial-recovery на следующем прогоне);
        #   4) print fall-back diagnostic + return 1 (graceful, НЕ silent abrupt traceback).
        import traceback as _tb
        tb_full = _tb.format_exc(limit=20)
        tb_short = tb_full if len(tb_full) <= 1000 else tb_full[:1000***REMOVED*** + "\n... (truncated)"
        project_id = ForgeRegistry._slug(project.name)
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
        sentinel = ChainRun(
            project_id=project_id,
            project_root=str(project.root),
            stage_count=1,
            chain=(ChainStage(
                role_id="<cmd_chain_wrapper>",
                mode="check_only",
                status="init_error",
                details=f"{exc!r***REMOVED***\n--- Traceback ---\n{tb_short***REMOVED***",
                duration_s=0.0,
            ),),
            overall="failed",
            started_at=now_iso,
            finished_at=now_iso,
            validation_registry_status="missing",
            validation_summary=None,
        )
        # Best-effort registry persistence (для последующего --resume partial-recovery).
        # Если facade.record_run absence — warnings OK (forward-compatible).
        # v5.189.8 (crash-resume fidelity): на --resume НЕ затираем prior chain
        # голым 1-стадийным sentinel — сливаем sentinel в prior full chain через
        # _merge_chain_runs, чтобы last_pipeline['chain'***REMOVED*** сохранил true last
        # ok/run_ok → повторный --resume продолжит с него (а не from scratch).
        try:
            if hasattr(facade, "record_run"):
                to_persist = sentinel
                if args.resume and prior_chain:
                    to_persist = _merge_chain_runs(prior_chain, sentinel)
                facade.record_run(project.name, to_persist)
        except Exception as record_exc:  # pragma: no cover — деградация
            print(f"  [cmd_chain***REMOVED*** sentinel persistence skipped: {record_exc!r***REMOVED***", file=diag)
        print(
            f"\nChain for {project.name***REMOVED*** — SOFT FAILURE (init_error).\n"
            f"  exc: {exc!r***REMOVED***\n"
            f"  Traceback excerpt:\n{tb_short***REMOVED***\n",
            file=diag,
        )
        return 1

    # v5.189.6 (FWD-1 bugfix): persist ChainRun to registry on SUCCESS so that
    # `--resume` can do partial continuation. Previously cmd_chain only persisted
    # a sentinel on failure; on success last_pipeline held the per-role PipelineRun
    # (no 'chain' key), so --resume always fell back to full chain. Mirror cmd_forge:
    # record_run after a successful run, unless --dry-run.
    if not args.dry_run:
        try:
            to_persist = run
            # On --resume, merge the partial run into the prior full chain so the
            # persisted last_pipeline['chain'***REMOVED*** keeps all 14 roles (cumulative
            # progress preserved; next --resume continues from the true last ok).
            if args.resume and prior_chain and len(run.chain) < len(prior_chain):
                to_persist = _merge_chain_runs(prior_chain, run)
            facade.record_run(project.name, to_persist)
        except Exception as record_exc:  # pragma: no cover — деградация
            print(f"  [cmd_chain***REMOVED*** chain persistence skipped: {record_exc!r***REMOVED***", file=diag)

    if args.json:
        print(_json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"\nChain for {project.name***REMOVED*** [{project.root***REMOVED******REMOVED*** — overall: {run.overall.upper()***REMOVED***")
        for s in run.chain:
            print(f"  {s.status.upper():10s***REMOVED*** {s.role_id:12s***REMOVED*** {s.details***REMOVED***")
        if run.validation_summary is not None:
            print(
                f"  [compose***REMOVED*** registry={run.validation_registry_status***REMOVED***, "
                f"overall={run.validation_summary.overall***REMOVED***, "
                f"base_check={run.validation_summary.base_check_status***REMOVED***"
            )

    return 0 if run.overall in ("ok", "degraded") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge", description="Buffy Forge CLI (L-5)")
    global_flags = argparse.ArgumentParser(add_help=False)
    global_flags.add_argument("--dry-run", action="store_true", help="preview без side-effects")
    global_flags.add_argument("--no-tg", action="store_true", help="не отправлять отчёт в TG")
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-tg", action="store_true", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    p_forge = sub.add_parser("forge", parents=[global_flags***REMOVED***, help="полный цикл FORGE→REPORT")
    p_forge.add_argument("project_path")
    p_forge.set_defaults(func=cmd_forge)

    p_check = sub.add_parser("check", parents=[global_flags***REMOVED***, help="Env Doctor + требования")
    p_check.add_argument("project_path")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", parents=[global_flags***REMOVED***, help="список проектов со статусами")
    p_status.add_argument("status", nargs="?", default=None)
    p_status.set_defaults(func=cmd_status)

    p_reg = sub.add_parser("register", parents=[global_flags***REMOVED***, help="зарегистрировать проект")
    p_reg.add_argument("project_path")
    p_reg.set_defaults(func=cmd_register)

    p_report = sub.add_parser("report", parents=[global_flags***REMOVED***, help="отчёт в TG")
    p_report.add_argument("project_path")
    p_report.set_defaults(func=cmd_report)

    p_step = sub.add_parser(
        "step", parents=[global_flags***REMOVED***,
        help="добавить запись в STEPS.md проекта",
    )
    p_step.add_argument("project_path")
    p_step.add_argument("phase", help="короткое имя этапа (например: 'Forge integration')")
    p_step.add_argument("text", help="описание шага (почему, что дальше)")
    p_step.set_defaults(func=cmd_step)

    # ── chain (v5.160.0, ADDITIVE per CAN-16: existing subparsers нетронуты) ──
    p_chain = sub.add_parser(
        "chain", help="запуск run_chain для 14 pipeline-ролей"
    )
    p_chain.add_argument("project_path")
    # Mutually exclusive: --dry-run и --full-cycle семантически противоречат
    # (dry-run = preview без mutations; full-cycle = разрешает Project mutations).
    # Без этой группы argparse позволял бы оба одновременно → semantic conflict.
    chain_mode = p_chain.add_mutually_exclusive_group()
    chain_mode.add_argument(
        "--full-cycle", action="store_true",
        help="разрешить Project mutation (project_read_only=False)",
    )
    chain_mode.add_argument(
        "--dry-run", action="store_true",
        help="preview без side-effects (ForgeFacade.dry_run=True + no record_run)",
    )
    p_chain.add_argument(
        "--no-tg", action="store_true", help="не отправлять в TG",
    )
    p_chain.add_argument(
        "--registry-path",
        help="явный путь к registry.yaml (для RoleArtifactValidator)",
    )
    p_chain.add_argument(
        "--roles",
        help=(
            "comma-separated список ролей "
            "(default: все 14 в PIPELINE_CHAIN-порядке)"
        ),
    )
    p_chain.add_argument(
        "--skip-stages",
        help=(
            "comma-separated substages для пропуска в full_cycle ролях "
            "(FORGE,CHECK,BUILD,TEST,DEPLOY,REPORT)"
        ),
    )
    p_chain.add_argument(
        "--no-compose", action="store_true",
        help="отключить compose artifact check (default=True)",
    )
    p_chain.add_argument(
        "--generate", action="store_true",
        help=(
            "автогенерация недостающих LIGHT-артефактов через "
            "RoleExecutorRegistry (ADR-016): детерминированная lisa + "
            "LLM-роли explainer/risk/decomposer/architect/auditor/documenter. "
            "Дефолт — check_only (обратная совместимость)."
        ),
    )
    p_chain.add_argument(
        "--json", action="store_true",
        help="вывод в формате JSON (ChainRun.to_dict())",
    )
    p_chain.add_argument(
        "--resume", action="store_true",
        help=(
            "продолжить chain с последнего ok/run_ok в "
            "registry.last_pipeline['chain'***REMOVED*** (forward-step FWD-1, v5.162.0). "
            "Если prior ok/run_ok не найден — running from scratch."
        ),
    )
    p_chain.add_argument(
        "--quiet", action="store_true",
        help=(
            "подавить [resume***REMOVED*** + SOFT FAILURE diagnostic preamble в STDOUT "
            "(отправить в STDERR вместо), чтобы --json output был parsable без "
            "preamble-strip workaround (v5.169.0 \u2014 closes v5.164.0 architectural smell)."
        ),
    )
    p_chain.set_defaults(func=cmd_chain)

    return parser


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
