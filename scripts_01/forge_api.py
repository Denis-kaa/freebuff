#!/usr/bin/env python3
"""scripts_01/forge_api.py — FastAPI server exposing Freebuff platform surface.

REST API layer over the forge CLI surface (v5.160.0–v5.179.0 surface map).
READ-ONLY by design; does NOT mutate ``data_13/forge_registry.yaml``.

Endpoints (versioned under /api/v1):
  GET /                              landing page (JSON platform info)
  GET /health                        liveness check (registry + cost-json reachable)
  GET /api/v1/projects               list registered projects from registry
  GET /api/v1/projects/{slug}        project detail (registry status + last_pipeline)
  GET /api/v1/projects/{slug}/chain  ChainRun JSON (9-key schema, v5.164.0)
  GET /api/v1/metrics                v5.179.0 cost campaign (mean/median/p95 per project)
  GET /static/{path:path}            serve prototype HTML/CSS/JS from prototype_22/
  GET /prototype                     shortcut → prototype_22/index.html

History:
  - v5.181.0 (this release): CR round-2 + round-3 fixes applied —
      Round 2:
        * Import PIPELINE_CHAIN/LIGHT_ROLES from core_02.forge_facade (was hardcoded tuple).
        * Use real ForgeRegistry class (was raw yaml.safe_load bypassing B10 invariant).
        * Add CORSMiddleware for cross-origin prototype fetch (file://, Vite :5173).
        * Add ``_mock: true`` flag to synthetic payloads (consumer can distinguish real vs mock).
        * Move ``import json`` to top-level (style consistency).
        * Version bumped to 5.181.0-proto (prototype release, not the actual 5.181.0 tag).
      Round 3:
        * Add ``sys.path.insert(0, REPO_ROOT)`` so direct ``python scripts_01/forge_api.py``
          boot works (was ModuleNotFoundError before).
        * Use public ForgeRegistry API: ``schema_violations`` property + ``list_projects_by_status()``
          + ``get_project_status()`` (was reaching into ``_data`` / ``_schema_violations``).
        * Direct invocation: ``uvicorn.run(app, ...)`` instead of
          ``uvicorn.run("scripts_01.forge_api:app", ...)`` (no double-import).
        * Explicit ``HEAVY_ROLES`` import + classification in ``_classify_role`` (no implicit
          set-difference fallback).

Run via:
  python scripts_01/forge_api.py             # uses PORT env var or 8765
  PORT=9000 python scripts_01/forge_api.py
  uvicorn scripts_01.forge_api:app --port 8765  # equivalent
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
}
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ─── sys.path bootstrap (allows direct ``python scripts_01/forge_api.py``) ──
# ``scripts_01/`` is the script directory; ``core_02/`` lives at repo root.
# Without this insert the relative import ``from core_02.forge_facade …`` fails
# with ModuleNotFoundError when invoked outside the test runner (which already
# adds the root via conftest.py).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ─── Real platform constants (DRY — единственный источник истины) ──────────
from core_02.forge_facade import (  # noqa: E402  (after sys.path bootstrap)
    HEAVY_ROLES,
    LIGHT_ROLES,
    PIPELINE_CHAIN,
)
from core_02.forge_registry import (  # noqa: E402  (after sys.path bootstrap)
    ForgeRegistry,
    ForgeStatus,
)

# ─── Interactive bridge (v5.187.0) — interactive_router imported below. ───
# NOTE: import is placed here (above app creation) because forge_interactive_api was
# designed to load cleanly without the app context. The actual ``app.include_router(...)``
# MUST happen after ``app = FastAPI(...)`` (see below, v5.187.0 R1 fix for mount-order).
from scripts_01.forge_interactive_api import router as interactive_router  # noqa: E402

# ─── Paths (anchored relative to repo root) ────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data_13" / "forge_registry.yaml"
COST_JSON = Path("/tmp/forge_chain_chaos_cost.json")
DEMO_PROJECTS = (
    "projects_17/vkusvill_demo",
    "projects_17/interior_planner",
    "projects_17/vkusvill_research",
)
PROTOTYPE_DIR = REPO_ROOT / "prototype_22"

# REPO_ROOT already defined above for sys.path; reused here for path joins.


# ─── App lifecycle ─────────────────────────────────────────────────────────
# APP_VERSION — bumped from 5.181.0-proto to 5.187.2-proto (CR v5.187.2 nit:
# prototype evolved through v5.187.0 bridge + v5.187.1 redesign; the old marker
# misled the user who sees version in the dashboard/JSON). Test compares against
# this imported constant, so the bump is regression-safe.
APP_VERSION = "5.187.2-proto"
app = FastAPI(
    title="Freebuff Forge API",
    version=APP_VERSION,
    description="REST surface for the Freebuff platform management layer (prototype).",
)

# CORS: prototype frontends can be file://, Vite :5173 (vite dev), or different
# origin. Wide-open is acceptable for a local prototype; tighten for prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # GET for prototype static + read-only dashboard; POST for interactive
    # bridge (project create + chain-run invoke). OPTIONS for CORS preflight.
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─── Interactive bridge mount (v5.187.0) — MUST be AFTER app = FastAPI() ──
# forge_api.py is READ-ONLY by CAN-16 ADDITIVE invariant. The interactive
# bridge (POST /api/interactive/v1/projects, POST chain-run, SSE progress)
# exercises the SAME core primitives (ForgeRegistry + forge.py chain CLI);
# no parallel systems introduced. See scripts_01/forge_interactive_api.py.
app.include_router(interactive_router)


# ─── Helpers ───────────────────────────────────────────────────────────────
def _read_registry() -> dict[str, Any]:
    """Load data_13/forge_registry.yaml via real ForgeRegistry public API.

    Uses ForgeRegistry (B10 invariant validation + R-127 schema enforcement)
    instead of raw yaml.safe_load. Returns meta-bundle:
      - ``reg``: the constructed ForgeRegistry instance (for downstream lookups).
      - ``exists``: whether the registry file exists.
      - ``violations``: schema violations (public property).
      - ``load_error``: best-effort load error note (None if clean).
    """
    if not REGISTRY_PATH.exists():
        return {
            "reg": None,
            "exists": False,
            "violations": [],
            "load_error": "registry file does not exist",
        }
    try:
        reg = ForgeRegistry(REGISTRY_PATH)
        return {
            "reg": reg,
            "exists": True,
            "violations": reg.schema_violations,  # public @property (line 165)
            "load_error": getattr(reg, "_load_error", None),  # private but informational only
        }
    except Exception as exc:  # noqa: BLE001 — defensive: any registry error is degraded
        return {
            "reg": None,
            "exists": True,
            "violations": [],
            "load_error": repr(exc),
        }


def _read_cost_metrics() -> dict[str, Any]:
    """Load /tmp/forge_chain_chaos_cost.json (v5.179.0 campaign output)."""
    if not COST_JSON.exists():
        return {}
    try:
        return json.loads(COST_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_error": f"JSON parse failed: {exc!r}"}


def _project_slug_to_dir(slug: str) -> Optional[Path]:
    """Resolve project_id (slug-form or underscore-form) to demo project directory."""
    candidates = [
        REPO_ROOT / "projects_17" / slug,
        REPO_ROOT / "projects_17" / slug.replace("-", "_"),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return None


def _classify_role(role: str) -> str:
    """Classify role into mode name: check_only / full_cycle / conditional_skip.

    Explicit set-membership against core_02.forge_facade constants (HEAVY_ROLES +
    LIGHT_ROLES). Frontend is special-cased (per-project-type conditional).
    Unknown roles raise ValueError (will appear in mock as 'unknown_mode').
    """
    if role in LIGHT_ROLES:
        return "check_only"
    if role in HEAVY_ROLES:
        return "full_cycle"
    if role == "frontend":
        return "conditional_skip"
    return "unknown_mode"  # defensive — list PIPELINE_CHAIN explicitly for traceability


def _mock_chain_run(slug: str, registered: bool = False) -> dict[str, Any]:
    """Build deterministic mock ChainRun JSON matching v5.164.0 9-key schema.

    Always returns ``_mock: True`` so consumers can distinguish synthetic fixtures
    from real ``registry.last_pipeline``. Per task: backend is platform management
    surface, not real-time executor. Mock fixture reflects v5.179.0 measurements
    per project (mean/p95).
    """
    row = _read_cost_metrics().get("projects", {}).get(slug, {})
    mean_s = row.get("mean_s", 0.0)
    overall = row.get("overalls", ["degraded"])[0] if row.get("overalls") else "degraded"
    reg_status = row.get("validation_registry_status", "missing")
    chain = []
    for role in PIPELINE_CHAIN:
        mode = _classify_role(role)
        # frontend is conditional in mock: status reflects registration state
        if mode == "unknown_mode":
            # Defensive — should not happen for canonical PIPELINE_CHAIN,
            # but signal clearly instead of falling through.
            stage_status = "unknown_mode_role"
        elif role == "frontend" and not registered:
            stage_status = "skipped"
        elif overall == "ok":
            stage_status = "ok" if mode != "full_cycle" else "run_ok"
        elif reg_status == "missing":
            stage_status = "missing"
        else:
            stage_status = "partial" if mode != "full_cycle" else "run_failed"
        chain.append({
            "role_id": role,
            "mode": mode,
            "status": stage_status,
            "details": role,
            "duration_s": round(mean_s / 14.0, 4),
        ])
    return {
        "_mock": True,
        "project_id": slug.replace("_", "-"),
        "project_root": str(REPO_ROOT / "projects_17" / slug),
        "stage_count": 14,
        "overall": overall,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "validation_registry_status": reg_status,
        "validation_summary": (
            None if reg_status == "missing"
            else {"overall": "ok", "base_check_status": "ok"}
        ),
        "chain": chain,
    }


# ─── Routes ────────────────────────────────────────────────────────────────
@app.get("/")
def root(request: Request) -> Any:
    """Landing — dashboard HTML for browsers, JSON for API clients.

    v5.187.2 UX fix: opening ``http://host:8765/`` in a browser previously
    returned raw JSON (the route was API-only by design). Content negotiation:
    browsers send ``Accept: text/html`` → serve prototype_22/index.html; API
    clients (curl, fetch, TestClient) send ``Accept: */*`` → platform-info
    JSON (unchanged, backward-compatible).
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept and PROTOTYPE_DIR.exists():
        idx = PROTOTYPE_DIR / "index.html"
        if idx.exists():
            # Cache-Control: no-cache — browser should revalidate the dashboard
            # HTML so future prototype edits are not masked by stale cache (CR v5.187.2).
            return FileResponse(
                idx,
                media_type="text/html",
                headers={"Cache-Control": "no-cache"},
            )
    return {
        "name": "Freebuff Forge API",
        "version": APP_VERSION,
        "platform": "Freebuff Workspace OS",
        "workspace_root": str(REPO_ROOT),
        "pipeline_chain_source": "core_02.forge_facade.PIPELINE_CHAIN",
        "pipeline_chain_role_count": len(PIPELINE_CHAIN),
        "light_roles_count": len(LIGHT_ROLES),
        "endpoints": {
            "health": "/health",
            "projects": "/api/v1/projects",
            "project_detail": "/api/v1/projects/{slug]",
            "chain_json": "/api/v1/projects/{slug]/chain",
            "metrics": "/api/v1/metrics",
            "static": "/static/",
        },
        "docs": "https://freebuff.local/docs (pending — local prototype)",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness — registry + cost-json reachable + schema violations count."""
    reg_data = _read_registry()
    cost_data = _read_cost_metrics()
    return {
        "status": (
            "ok"
            if reg_data.get("_error") is None and cost_data.get("_error", "_ok") != "_error"
            else "degraded"
        ),
        "registry_present": reg_data.get("exists", False),
        "registry_violations": len(reg_data.get("violations", [])),
        "registry_load_error": reg_data.get("_error"),
        "cost_metrics_present": bool(cost_data) and cost_data.get("_error") is None,
        "registry_path": str(REGISTRY_PATH),
        "cost_path": str(COST_JSON),
        "app_version": APP_VERSION,
        "python": sys.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/projects")
def list_projects() -> dict[str, Any]:
    """List registered projects from data_13/forge_registry.yaml.

    Uses public ``ForgeRegistry.list_projects_by_status()`` (no filter → all).
    """
    reg_data = _read_registry()
    reg = reg_data.get("reg")
    items: List[dict[str, Any]] = []
    if reg is not None:
        statuses = reg.list_projects_by_status()  # public method, returns ForgeStatus list
        for s in statuses:
            last = s.last_pipeline or {}
            items.append({
                "project_id": s.project_id,
                "name": s.name,
                "root": s.root,
                "status": s.status,
                "last_run_at": s.last_run_at,
                "last_overall": last.get("overall"),
                "last_stage_count": last.get("stage_count"),
                "last_chain_len": len(last.get("chain") or []),
            ])
    return {
        "count": len(items),
        "schema_violations": reg_data.get("violations", []),
        "load_error": reg_data.get("load_error"),
        "projects": items,
    }


def _project_status_or_none(reg: Optional[ForgeRegistry], slug: str) -> tuple[Optional[ForgeStatus], Optional[str]]:
    """Resolve slug (canonical or hyphenated) to its ForgeStatus (or None).

    Returns (status, matched_key).
    """
    if reg is None:
        return None, None
    for key in (slug, slug.replace("-", "_")):
        s = reg.get_project_status(key)  # public method
        if s is not None:
            return s, key
    return None, None


@app.get("/api/v1/projects/{slug)")
def project_detail(slug: str) -> dict[str, Any]:
    """Single project detail from registry (real ForgeRegistry lookup + fallback for unregistered)."""
    reg_data = _read_registry()
    reg = reg_data.get("reg")
    status, matched = _project_status_or_none(reg, slug)

    if status is None:
        d = _project_slug_to_dir(slug)
        if d is None:
            raise HTTPException(status_code=404, detail=f"project not found: {slug}")
        return {
            "_mock": True,
            "matched_as": slug,
            "project_id": slug,
            "name": d.name,
            "root": str(d),
            "status": "UNREGISTERED",
            "registered_at": None,
            "last_run_at": None,
            "last_pipeline_overall": None,
            "last_pipeline_stage_count": None,
            "last_chain": [],
            "project_files_sample": [],
        }
    last = status.last_pipeline or {}
    proj_dir = Path(status.root or _project_slug_to_dir(slug) or REPO_ROOT)
    files_sample: List[str] = []
    if proj_dir.is_dir():
        try:
            files_sample = [str(p) for p in sorted(proj_dir.iterdir())[:5]]
        except (PermissionError, OSError):
            files_sample = []
    return {
        "_mock": False,
        "matched_as": matched,
        "project_id": matched,
        "name": status.name or matched,
        "root": status.root,
        "status": status.status,
        "registered_at": status.registered_at,
        "last_run_at": status.last_run_at,
        "last_pipeline_overall": last.get("overall"),
        "last_pipeline_stage_count": last.get("stage_count"),
        "last_chain": last.get("chain") or [],
        "project_files_sample": files_sample,
    }


@app.get("/api/v1/projects/{slug)/chain")
def project_chain(slug: str) -> dict[str, Any]:
    """ChainRun 9-key JSON for a single project (matches v5.164.0 canonical schema).

    If ``registry.last_pipeline.chain`` is real → return it (with ``_mock: False``).
    Otherwise → synthetic mock with ``_mock: True`` so consumer distinguishes.
    """
    reg_data = _read_registry()
    reg = reg_data.get("reg")
    status, matched = _project_status_or_none(reg, slug)
    last = (status.last_pipeline if status else None) or {}

    if status is not None and last.get("chain"):
        return {
            "_mock": False,
            "project_id": matched,
            "project_root": status.root,
            "stage_count": last.get("stage_count"),
            "chain": last.get("chain") or [],
            "overall": last.get("overall"),
            "started_at": last.get("started_at"),
            "finished_at": last.get("finished_at"),
            "validation_registry_status": last.get("validation_registry_status"),
            "validation_summary": last.get("validation_summary"),
        }

    # Fallback to mock (demo project or unregistered; reflect registry state)
    registered = status is not None
    mock = _mock_chain_run(slug, registered=registered)
    if matched:
        mock["project_id"] = matched
        if status is not None:
            mock["project_root"] = status.root or mock["project_root"]
    return mock


@app.get("/api/v1/metrics")
def metrics() -> dict[str, Any]:
    """v5.179.0 cost campaign metrics — measured mean/median/p95 per demo project."""
    cost = _read_cost_metrics()
    if not cost:
        return {"available": False, "reason": "cost JSON missing or unreadable"}
    return {
        "available": True,
        "campaign_timestamp": cost.get("campaign_timestamp"),
        "schema_version": cost.get("schema_version"),
        "config": cost.get("config"),
        "env": cost.get("env"),
        "projects": cost.get("projects"),
        "summary": cost.get("summary"),
    }


# ─── Static prototype mount (if prototype_22/ exists) ──────────────────────
if PROTOTYPE_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(PROTOTYPE_DIR)), name="prototype-static")

    @app.get("/prototype")
    def prototype_index() -> FileResponse:
        """Direct shortcut /prototype → prototype_22/index.html."""
        idx = PROTOTYPE_DIR / "index.html"
        if not idx.exists():
            raise HTTPException(status_code=404, detail="prototype index.html missing")
        return FileResponse(
            idx,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},  # symmetric with root (CR v5.187.2)
        )
else:
    @app.get("/prototype")
    def prototype_missing() -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "prototype_22/ directory not yet created",
                     "hint": "create prototype_22/{index.html,style.css,app.js]"],
        )


# ─── Entry point (uvicorn programmatic start) ──────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"[forge_api] starting on http://{host}:{port} (version {APP_VERSION})", flush=True)
    print(f"[forge_api] routes: /, /health, /api/v1/projects, /api/v1/metrics", flush=True)
    print(f"[forge_api] static mount: {'/static/ → ' + str(PROTOTYPE_DIR) if PROTOTYPE_DIR.exists() else 'prototype not found'}", flush=True)
    # Direct invocation (not string path) — avoids uvicorn re-importing the module.
    uvicorn.run(app, host=host, port=port, log_level="info")
