#!/usr/bin/env python3
# measure_chain_cost.py — v5.179.0 real-cost timing campaign для `forge chain --dry-run`.
#
# Задача: per-CR-observation-gap в v5.178.0 — измерить real subprocess cost c exposed
# sentinel persistence (v5.173.0 facade.record_run). Запускает 3 проекта × 3 прогона
# через subprocess.run, вычисляет per-project статистики, сохраняет JSON.
#
# Использование:
#   python scripts_01/measure_chain_cost.py
#   python scripts_01/measure_chain_cost.py --runs 5
#   python scripts_01/measure_chain_cost.py --projects vkusvill_demo interior_planner --runs 3
#
# Output:
#   /tmp/forge_chain_chaos_cost.json — campaign_timestamp + per-project stats + summary
#
# CAN-16 ADDITIVE: не модифицирует forge.py или forge_facade.py; standalone invoker.
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
}

# Anchored paths (relative to repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent
FORGE_SCRIPT = REPO_ROOT / "scripts_01" / "forge.py"
DEFAULT_PROJECTS: tuple[str, ...] = (
    "projects_17/vkusvill_demo",
    "projects_17/interior_planner",
    "projects_17/vkusvill_research",
)
DEFAULT_RUNS_PER_PROJECT = 3
OUTPUT_JSON = Path("/tmp/forge_chain_chaos_cost.json")
INVOCATION_TIMEOUT_S = 120  # CI-friendly ceiling per invocation
PYTHON_BIN = sys.executable


def _git_rev() -> str:
    """Short git SHA (или 'unknown' если git недоступен / detached)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode("utf-8", errors="replace").strip()
    except Exception:  # noqa: BLE001 — best-effort metadata
        return "unknown"


def _try_parse_json(stdout: str) -> dict | None:
    """Best-effort JSON parsing of forge chain --json output."""
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _pct(values: list[float], percent: float) -> float:
    """Simple percentile (linear interpolation, statistics-friendly)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (percent / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _aggregate(samples: list[dict]) -> dict:
    """Compute per-project aggregation over collected samples."""
    durations = [s["duration_s"] for s in samples]
    exit_codes = [s["exit_code"] for s in samples]
    stage_counts = [
        (s["stdout_json"] or {}).get("stage_count", 0) for s in samples
    ]
    overalls = [
        (s["stdout_json"] or {}).get("overall", "unknown") for s in samples
    ]
    if not durations:
        return {
            "runs": 0,
            "mean_s": 0.0,
            "median_s": 0.0,
            "stdev_s": 0.0,
            "min_s": 0.0,
            "max_s": 0.0,
            "p95_s": 0.0,
            "samples_s": [],
            "exit_codes": [],
            "stage_counts": [],
            "overalls": [],
        }
    return {
        "runs": len(samples),
        "mean_s": round(statistics.mean(durations), 4),
        "median_s": round(statistics.median(durations), 4),
        "stdev_s": round(statistics.stdev(durations), 4) if len(durations) > 1 else 0.0,
        "min_s": round(min(durations), 4),
        "max_s": round(max(durations), 4),
        "p95_s": round(_pct(durations, 95.0), 4),
        "samples_s": [round(d, 4) for d in durations],
        "exit_codes": exit_codes,
        "stage_counts": stage_counts,
        "overalls": overalls,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real-cost timing campaign для forge chain --dry-run.",
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        default=list(DEFAULT_PROJECTS),
        help="Project directory paths (relative to repo root). Default: 3 demo projects.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS_PER_PROJECT,
        help=f"Runs per project (default {DEFAULT_RUNS_PER_PROJECT}).",
    )
    parser.add_argument(
        "--mode",
        choices=("dry_run", "default"),
        default="dry_run",
        help="Chain mode (default=dry_run — deterministic fast path).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_JSON,
        help=f"Output JSON path (default {OUTPUT_JSON}).",
    )
    args = parser.parse_args()

    # Resolve + validate project paths.
    resolved_projects: list[Path] = []
    for p in args.projects:
        pr = (REPO_ROOT / p).resolve() if not Path(p).is_absolute() else Path(p).resolve()
        if not pr.exists():
            print(f"[measure_chain_cost] SKIP missing: {pr}", file=sys.stderr)
            continue
        resolved_projects.append(pr)

    if not resolved_projects:
        print("[measure_chain_cost) no valid projects", file=sys.stderr)
        return 2

    # Resolve mode flag (--default vs --dry-run).
    mode_flag = [] if args.mode == "default" else ["--dry-run"]

    print(
        f"[measure_chain_cost] campaign: {len(resolved_projects)} projects × "
        f"{args.runs} runs each, mode={args.mode}",
        file=sys.stderr,
    )

    # Per-project samples collection.
    per_project_samples: dict[str, list[dict]] = {}
    for proj in resolved_projects:
        proj_name = proj.name
        samples = []
        for run_idx in range(args.runs):
            print(
                f"[measure_chain_cost] {proj_name} run {run_idx + 1}/{args.runs}...",
                file=sys.stderr,
            )
            cmd_args = [
                PYTHON_BIN,
                str(FORGE_SCRIPT),
                "chain",
                str(proj),
                *mode_flag,
                "--json",
                "--quiet",
            ]
            started = time.perf_counter()
            try:
                completed = subprocess.run(
                    cmd_args,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=INVOCATION_TIMEOUT_S,
                )
                duration_s = time.perf_counter() - started
                stderr_full = completed.stderr or ""
                stderr_excerpt = (
                    stderr_full[:200] + "..."
                    if len(stderr_full) > 200
                    else stderr_full
                )
                samples.append(
                    {
                        "exit_code": completed.returncode,
                        "duration_s": duration_s,
                        "stderr_excerpt": stderr_excerpt,
                        "stdout_json": _try_parse_json(completed.stdout),
                    }
                )
            except subprocess.TimeoutExpired:
                duration_s = time.perf_counter() - started
                samples.append(
                    {
                        "exit_code": 124,  # POSIX convention: timeout exit code
                        "duration_s": duration_s,
                        "stderr_excerpt": f"TIMEOUT after {INVOCATION_TIMEOUT_S}s",
                        "stdout_json": None,
                    }
                )
        per_project_samples[proj_name] = samples

    # Build output payload.
    output_payload: dict = {
        "campaign_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "schema_version": "v5.179.0",
        "config": {
            "mode": args.mode,
            "projects": [p.name for p in resolved_projects],
            "runs_per_project": args.runs,
            "timeout_s": INVOCATION_TIMEOUT_S,
        },
        "env": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "git_rev": _git_rev(),
        },
        "projects": {
            proj_name: _aggregate(samples)
            for proj_name, samples in per_project_samples.items()
        },
    }

    # Summary aggregates across all projects.
    all_durations = [
        s["duration_s"]
        for samples in per_project_samples.values()
        for s in samples
    ]
    if all_durations:
        output_payload["summary"] = {
            "total_invocations": len(all_durations),
            "aggregate_mean_s": round(
                statistics.mean(all_durations), 4
            ),
            "aggregate_median_s": round(
                statistics.median(all_durations), 4
            ),
            "aggregate_p95_s": round(_pct(all_durations, 95.0), 4),
        }
    else:
        output_payload["summary"] = {
            "total_invocations": 0,
            "aggregate_mean_s": 0.0,
            "aggregate_median_s": 0.0,
            "aggregate_p95_s": 0.0,
        }

    # Write JSON output.
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output_payload, indent=2, sort_keys=False), encoding="utf-8")

    # Print short summary to STDOUT (operator-friendly).
    print(f"[measure_chain_cost] wrote: {OUTPUT_JSON}", file=sys.stderr)
    print(f"[measure_chain_cost] summary: {output_payload['summary']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
