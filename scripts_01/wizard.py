"""scripts_01/wizard.py — Workspace OS wizard CLI entry.

Usage (modern, multi-scenario registry):
    python scripts_01/wizard.py --workspace /tmp --name interior_planner \\
        --project-goal "мобильное приложение-канвас" \\
        --task-goal "scaffold expo app"

    # or with --selftest (uses a tmp‑seed corpus, no canonical required):
    python scripts_01/wizard.py --selftest

    # pin a specific scenario via --scenario <id>:
    python scripts_01/wizard.py --scenario blueprint_v3 --workspace . --name foo \\
        --project-goal x --task-goal y

Design rules:
- Default mode: multi-scenario discovery via ``runtime_05/scenarios/`` (auto-load on
  every invocation). Env override ``FREEBUFF_SCENARIOS_DIR`` swaps the directory.
- BC mode (legacy): explicit ``--blueprints-dir`` still constructs a single
  ``BlueprintCorpus`` and runs the legacy ``run_wizard(corpus=...)`` path.
  This keeps old scripts / cronjobs / docs working unchanged.
- ``--scenario <id>`` filters the registry to one scenario before wizard logic.
- ``--selftest`` runs end‑to‑end against an in‑tmp seed so the CLI is
  testable without the canonical ``blueprints_v3/`` outside the workspace.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
}


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core_02 import blueprint_v3 as bpv3
from core_02.scenario_registry import ScenarioRegistry
from core_02.wizard_lib import run_wizard, run_wizard_with_registry


def _seed_minimal_corpus(target_dir: Path) -> Path:
    """Write a minimal registry.yaml + developer.md so wizard has *something* to read."""
    bp_dir = target_dir / "blueprints_v3_seed"
    bp_dir.mkdir(parents=True, exist_ok=True)
    (bp_dir / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: developer\n"
        "    file: 09_developer.md\n"
        "    type: implementation\n"
        "    role: AI Senior Backend Developer\n"
        "    description: backend\n"
        "    condition: always\n"
        "    triggers:\n"
        '      - "реализуй модуль"\n'
        "project_types:\n"
        "  web:\n"
        "    required_roles: [developer]\n"
        "    skip_roles: []\n"
        "complexity_routing:\n"
        "  small:\n"
        "    required_roles: [developer]\n"
        "    skip_roles: []\n"
        "categories:\n"
        "  implementation: [developer]\n"
        "metadata:\n"
        "  version: \"3.0.0\"\n",
        encoding="utf-8",
    )
    (bp_dir / "09_developer.md").write_text(
        "ROLE: AI Senior Backend Developer\n"
        "VERSION: 3.1.0\n\n"
        "<role>Senior backend engineer for production code.</role>\n\n"
        "<system_role>Implements modules and tests.</system_role>\n\n"
        "<input>Architecture spec.</input>\n\n"
        "<main_objective>Production-ready code.</main_objective>\n\n"
        "<priority_order>Correctness first.</priority_order>\n\n"
        "<implementation_scope_rules>Allowed: target module only.</implementation_scope_rules>\n\n"
        "<capabilities>\n"
        "- code\n"
        "- implement\n"
        "- debug\n"
        "</capabilities>\n",
        encoding="utf-8",
    )
    return bp_dir


def _summarise(result: dict) -> dict:
    out = {
        "selected_role_id": result["selected_role_id"],
        "resolved_model": result["resolved_model"],
        "paths": {k: str(v) for k, v in result["paths"].items()},
        "merged_path": str(result["merged_path"]),
    }
    if "selected_scenario_id" in result:
        out["selected_scenario_id"] = result["selected_scenario_id"]
    return out


def _seed_minimal_registry(target_dir: Path) -> tuple[Path, "ScenarioRegistry"]:
    """Build a tmp registry using an in-tmp blueprint corpus (for --selftest).

    Writes a one-scenario manifest + a 2-role corpus into the temp dir and
    returns (registry, workspace_dir) so the rest of the test runs end-to-end
    WITHOUT touching the canonical ``runtime_05/scenarios/`` outside workspace.
    """
    seed = _seed_minimal_corpus(target_dir)
    scenarios_dir = target_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "blueprint_v3.yaml").write_text(
        "id: blueprint_v3_selftest\n"
        "type: blueprint_v3\n"
        f"display_name: selftest\n"
        f"root: {seed}\n"
        "enabled: true\n",
        encoding="utf-8",
    )
    registry = ScenarioRegistry(scenarios_dir=scenarios_dir, silent=True)
    return registry


def main(args: argparse.Namespace) -> int:
    if args.selftest:
        # selftest exercises BOTH legacy (corpus) and new (registry) paths:
        # the legacy path tests BC; the registry path tests cross-scenario
        # discovery. We pick registry mode since it covers the more code.
        with tempfile.TemporaryDirectory(prefix="freebuff_wizard_selftest_") as td:
            registry = _seed_minimal_registry(Path(td))
            ws = Path(td) / "workspace"
            ws.mkdir()
            result = run_wizard_with_registry(
                registry=registry,
                workspace_path=ws,
                project_name="selftest_app",
                project_goal="тестовый прогон wizard",
                task_goal="выполнить self-test",
                force_role_id="developer",
            )
            print(json.dumps(_summarise(result), ensure_ascii=False, indent=2))
        return 0

    # ─── Multi-scenario (default) path ─────────────────────────────────────
    # Try ScenarioRegistry first. If empty AND --blueprints-dir was given,
    # fall back to legacy single-corpus mode (BC).
    blueprints_dir = args.blueprints_dir or os.environ.get("FREEBUFF_BLUEPRINTS_DIR")
    if blueprints_dir:
        # Explicit BC path: legacy single corpus.
        bd = Path(blueprints_dir)
        if not bd.exists():
            print(f"error: blueprints_dir {bd} does not exist", file=sys.stderr)
            return 2
        if not bd.is_dir():
            print(f"error: blueprints_dir {bd} is not a directory", file=sys.stderr)
            return 2
        if not (bd / "registry.yaml").exists():
            print(
                f"error: {bd}/registry.yaml missing — pip install/restore blueprint corpus",
                file=sys.stderr,
            )
            return 2
        corpus = bpv3.BlueprintCorpus(root=bd)
        result = run_wizard(
            corpus=corpus,
            workspace_path=Path(args.workspace),
            project_name=args.name,
            project_goal=args.project_goal,
            task_goal=args.task_goal,
            priority=args.priority,
            workspace_mode=args.mode,
            force_role_id=args.role,
        )
        print(json.dumps(_summarise(result), ensure_ascii=False, indent=2))
        return 0

    # Default: ScenarioRegistry with auto-discovery.
    registry = ScenarioRegistry(
        scenarios_dir=Path(args.scenarios_dir).expanduser().resolve()
        if args.scenarios_dir else None,
        silent=False,
    )
    if not registry.list_scenarios():
        print(
            "error: no scenarios registered. Either set $FREEBUFF_SCENARIOS_DIR, "
            "create runtime_05/scenarios/*.yaml, or pass --blueprints-dir for BC mode "
            "(or use --selftest)",
            file=sys.stderr,
        )
        return 2
    # Optional scenario filter — single-scenario mode inside registry.
    if args.scenario:
        only = registry.get(args.scenario)
        if only is None:
            print(
                f"error: --scenario {args.scenario!r} not registered; "
                f"available: {[sc.scenario_id for sc in registry.list_scenarios()]}",
                file=sys.stderr,
            )
            return 2
        # Single-scenario proxy via the registry's own filter() method
        # (replaces fragile `__new__` escape — proper init semantics +
        # narrowed warnings).
        registry = registry.filter(args.scenario)

    result = run_wizard_with_registry(
        registry=registry,
        workspace_path=Path(args.workspace),
        project_name=args.name,
        project_goal=args.project_goal,
        task_goal=args.task_goal,
        priority=args.priority,
        workspace_mode=args.mode,
        force_role_id=args.role,
    )
    print(json.dumps(_summarise(result), ensure_ascii=False, indent=2))
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Workspace OS wizard over Scenario registry + Blueprint v3 BC fallback."
    )
    p.add_argument("--selftest", action="store_true",
                   help="Run with a seed scenario in a tmp dir (no canonical required).")
    p.add_argument(
        "--blueprints-dir",
        default=None,
        help="BC mode: explicit path to a blueprints_v3 corpus. Disables registry mode.",
    )
    p.add_argument(
        "--scenarios-dir",
        default=None,
        help="Override scenarios directory (default: $FREEBUFF_SCENARIOS_DIR or runtime_05/scenarios).",
    )
    p.add_argument(
        "--scenario",
        default=None,
        help="Filter registry to a single scenario by id (e.g. 'blueprint_v3').",
    )
    p.add_argument("--workspace", default=".", help="Directory containing the new project.")
    p.add_argument("--name", help="Project name.")
    p.add_argument("--project-goal", help="Free-form goal for the project.")
    p.add_argument("--task-goal", help="Free-form goal for the first task.")
    p.add_argument("--priority", default="normal",
                   help="low|normal|high|critical (default normal).")
    p.add_argument("--mode", default="single",
                   help="workspace mode (single|cowork|teamwork). Default single.")
    p.add_argument("--role", default=None,
                   help="Force role_id (skip propose_roles fuzzy match).")
    return p


if __name__ == "__main__":
    ns = _arg_parser().parse_args()
    if not ns.selftest:
        for required in ("name", "project_goal", "task_goal"):
            if not getattr(ns, required):
                print(
                    f"error: --{required.replace('_', '-')} required (or use --selftest)",
                    file=sys.stderr,
                )
                sys.exit(2)
    sys.exit(main(ns))
