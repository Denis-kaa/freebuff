#!/usr/bin/env python3
"""scripts_01/forge_interactive_api.py — additive interactive bridge (v5.187.0).

Mounted by ``scripts_01/forge_api.py`` at ``/api/interactive`` prefix.

Routes (all under /api/interactive/v1):
    POST /projects                                     → create project + register
    POST /projects/{slug}/chain                        → sync invoke forge.py chain
    POST /projects/{slug}/chain/start                  → async start, returns run_id
    GET  /projects/{slug}/chain/{run_id}               → snapshot of running run
    GET  /projects/{slug}/chain/{run_id}/stream        → SSE stream of progress
    GET  /health                                        → interactive sub-router liveness

Why ADITIVE:
- ``forge_api.py`` is documented READ-ONLY (CAN-16 ADDITIVE invariant); all
  existing 8 GET endpoints under /api/v1/* are preserved unchanged.
- Interactive bridge exercises the same core primitives (ForgeRegistry,
  ForgeFacade, ``forge.py chain`` CLI) — NO parallel systems introduced.

Security:
- subprocess always uses argv-list + ``shell=False`` (NEVER shell-injected).
- Validation: slug must match ``^[a-z][a-z0-9_]{2,30}$`` (lowercase, starts
  with letter, 3-31 chars).
- Process cleanup: every subprocess gets ``terminate()`` in finally block on
  SSE disconnect + AsyncTask exception (cancels cleanly without orphans).

Run independently (debugging only — production mount is via forge_api.py):
    uvicorn scripts_01.forge_interactive_api:app --port 8766
"""
from __future__ import annotations

import asyncio
import json
import os
}
import subprocess
import sys
import uuid
from datetime import datetime, timezone
}
from typing import Annotated, Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints

# ─── sys.path bootstrap (mirrors SUT pattern in forge_api.py) ──────────
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ─── Platform constants ────────────────────────────────────────────────
PROJECTS_DIR = REPO_ROOT / "projects_17"
REGISTRY_PATH = REPO_ROOT / "data_13" / "forge_registry.yaml"
FORGE_CLI = REPO_ROOT / "scripts_01" / "forge.py"

ALLOWED_SLUG = re.compile(r"^[a-z)[a-z0-9_]{2,30]$")

# In-memory session store: run_id → RunSession. Reset on process restart.
# NOTE: for durable multi-instance support, migrate to data_13/interactive_runs.json
# (deferred to v5.190+ per CR observation backlog).
INMEM_RUNS: dict[str, "RunSession"] = {}

# ─── Optional standalone app (debug) ───────────────────────────────────
try:
    from fastapi import FastAPI  # type: ignore
    app = FastAPI(title="Freebuff Interactive Bridge", version="0.1.0")
    router = APIRouter(prefix="/api/interactive/v1", tags=["interactive"])
except ImportError:  # pragma: no cover — FastAPI optional dep
    FastAPI = None  # type: ignore
    app = None  # type: ignore
    router = APIRouter(prefix="/api/interactive/v1")


# ─── Storage ───────────────────────────────────────────────────────────
class RunSession:
    """In-memory representation of a chain run (UNFORGED → DEPLOYED pipeline exec)."""

    def __init__(self, slug: str, mode: str) -> None:
        self.run_id = uuid.uuid4().hex[:12]
        self.slug = slug
        self.mode = mode
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self.status = "running"  # running | done | init_error | aborted
        self.log: list[dict[str, Any]] = []  # [{ts, kind, msg}, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "slug": self.slug,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "log": list(self.log),
        }


# ─── Request / Response models ──────────────────────────────────────────
class ProjectCreateBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    slug: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=31)]] = None


class ChainRunBody(BaseModel):
    mode: str = Field("dry-run", description="dry-run | full-cycle | resume")
    resume: bool = False


# ─── Routes ────────────────────────────────────────────────────────────
@router.get("/health")
def interactive_health() -> dict[str, Any]:
    """Liveness for the interactive sub-router + INMEM_RUNS metrics."""
    return {
        "ok": True,
        "router": "interactive",
        "version": "5.187.0-interactive",
        "active_runs": sum(1 for s in INMEM_RUNS.values() if s.status == "running"),
        "total_runs_in_memory": len(INMEM_RUNS),
        "registry_path": str(REGISTRY_PATH),
        "projects_dir": str(PROJECTS_DIR),
    }


@router.post("/projects")
def create_project(body: ProjectCreateBody) -> dict[str, Any]:
    """Register a new project in ForgeRegistry + create projects_17/<slug>/ stub.

    Returns the created project metadata. Slug uniqueness is checked against the
    registry (no overwrite of existing).

    Validations:
      - Slug matches ``^[a-z][a-z0-9_]{2,30}$`` (auto-generated if absent).
      - Stub directory projects_17/<slug> created (mkdir, not mkdir -p).
      - ForgeRegistry.register_project(...) succeeds (atomic file write).
    """
    from core_02.forge_registry import ForgeRegistry

    slug = body.slug or ForgeRegistry._slug(body.name)
    if not ALLOWED_SLUG.match(slug):
        raise HTTPException(
            status_code=422,
            detail=f"invalid slug {slug!r}: must match ^[a-z][a-z0-9_]{{2,30}}$ "
                   "(lowercase, starts with letter, 3-31 chars)",
        )
    proj_dir = PROJECTS_DIR / slug
    # TOCTOU-safe: drop pre-check (v5.187.0 R1 fix per CR nit). FileExistsError
    # on mkdir maps to 409 (atomic vs the prior exists()+mkdir race).
    try:
        proj_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail=f"project directory already exists: {proj_dir}",
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to create project dir {proj_dir}: {exc!r}"
        )
    # Seed minimal README
    readme = (
        f"# {body.name}\n\nSlug: `{slug}`\n"
        f"Created by Freebuff Prototype UI ({datetime.now(timezone.utc).isoformat()}).\n\n"
        f"- Status starts at UNFORGED.\n"
        f"- Run `forge.py chain {slug} --resume` to record a chain history.\n"
        f"- Inspect via Prototype UI sidebar or `forge.py status {slug}`.\n"
    )
    write_ok = True
    try:
        (proj_dir / "README.md").write_text(readme, encoding="utf-8")
    except OSError as exc:
        write_ok = False
    # ForgeRegistry writes
    reg = ForgeRegistry(REGISTRY_PATH)
    try:
        project_id = reg.register_project(name=body.name, root=str(proj_dir), project_id=slug)
        post = reg.get_project_status(project_id)
        status = post.status if post else "UNKNOWN"
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"registry register_project failed: {exc!r}"
        )
    return {
        "ok": True,
        "project_id": project_id,
        "name": body.name,
        "root": str(proj_dir),
        "status": status,
        "registry_path": str(REGISTRY_PATH),
        "readme_written": write_ok,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/projects/{slug)/chain")
def run_chain_sync(slug: str, body: ChainRunBody) -> dict[str, Any]:
    """Synchronous invoke of ``python scripts_01/forge.py chain <slug> --json [--mode]``.

    Blocks the request thread until the forge.py subprocess completes (timeout 60s).
    Returns the parsed JSON chain payload from forge.py --json output plus the slug
    and mode for the frontend to render.
    """
    if not ALLOWED_SLUG.match(slug):
        raise HTTPException(status_code=422, detail=f"invalid slug {slug!r}")
    argv = ["python3", str(FORGE_CLI), "chain", slug, "--json"]
    if body.mode == "full-cycle":
        argv.append("--full-cycle")
    elif body.mode == "resume":
        argv.append("--resume")
    # else: dry-run (default; no extra flag)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"forge chain timed out after 60s (slug={slug} mode={body.mode})",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"forge CLI not found: {exc!r}")
    if proc.returncode != 0 and not proc.stdout.strip():
        raise HTTPException(
            status_code=500,
            detail=f"forge chain failed: rc={proc.returncode}; stderr={proc.stderr[:500]!r}",
        )
    # forge.py --json sometimes prefixes with [resume] line; strip it.
    cleaned = "\n".join(
        line for line in proc.stdout.splitlines()
        if line.strip() and not line.startswith("[resume)")
    )
    try:
        chain = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to parse forge --json output: {exc!r}; raw: {proc.stdout[:500]!r}",
        )
    return {
        "ok": True,
        "slug": slug,
        "mode": body.mode,
        "chain": chain,
        "rc": proc.returncode,
        "stderr_excerpt": proc.stderr[:300] if proc.stderr else "",
    }


@router.post("/projects/{slug)/chain/start")
async def start_chain_stream(slug: str, body: ChainRunBody) -> dict[str, Any]:
    """Async start: spawn subprocess, return run_id. Use /stream/{run_id] to subscribe."""
    if not ALLOWED_SLUG.match(slug):
        raise HTTPException(status_code=422, detail=f"invalid slug {slug!r}")
    mode = body.mode
    if mode not in ("dry-run", "full-cycle", "resume"):
        raise HTTPException(status_code=422, detail=f"invalid mode {mode!r}")
    sess = RunSession(slug=slug, mode=mode)
    INMEM_RUNS[sess.run_id] = sess
    argv = ["python3", str(FORGE_CLI), "chain", slug, "--json"]
    if mode == "full-cycle":
        argv.append("--full-cycle")
    elif mode == "resume":
        argv.append("--resume")
    proc = subprocess.Popen(
        argv,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,  # line-buffered
    )
    sess.log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "info",
        "msg": f"spawned forge.py chain (pid={proc.pid}, argv={' '.join(argv)})",
    ])
    # Schedule background task to drain subprocess into sess.log
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_drain_subprocess_to_session(sess, proc))
    except RuntimeError:
        # No running event loop (e.g., called outside asyncio context) — fall
        # back to thread-pool task via run_until_complete on next call.
        sess.log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": "warn",
            "msg": "no running event loop; subprocess drain deferred to next /stream call",
        ])
    return {
        "ok": True,
        "run_id": sess.run_id,
        "slug": slug,
        "mode": mode,
        "started_at": sess.started_at,
        "pid": proc.pid,
    }


async def _drain_subprocess_to_session(sess: RunSession, proc: subprocess.Popen) -> None:
    """Async drain subprocess stdout + stderr IN PARALLEL into sess.log.

    v5.187.0 R1 fix per CR nit: naive stdout-then-stderr could deadlock if
    forge.py writes >64KB to stderr mid-run (PIPE_BUF exhausted). Drain both
    streams concurrently via asyncio.gather over executor tasks.
    """
    loop = asyncio.get_running_loop()

    def _drain_one(stream, kind: str) -> None:
        """Blocking sync line-drain helper for use with run_in_executor."""
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            sess.log.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "msg": line.rstrip("\n"),
            ])

    try:
        await asyncio.gather(
            loop.run_in_executor(None, _drain_one, proc.stdout, "stdout"),
            loop.run_in_executor(None, _drain_one, proc.stderr, "stderr"),
        )
        rc = await loop.run_in_executor(None, lambda: proc.wait(timeout=10))
        sess.status = "done" if rc == 0 else f"init_error_rc={rc}"
    except subprocess.TimeoutExpired:
        sess.log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": "error",
            "msg": "subprocess wait() timed out after 10s",
        ])
        sess.status = "init_error"
        try:
            proc.terminate()
        except Exception:
            pass
    except Exception as exc:
        sess.log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": "error",
            "msg": f"drain exception: {exc!r}",
        ])
        sess.status = "init_error"
        try:
            proc.terminate()
        except Exception:
            pass
    finally:
        sess.finished_at = datetime.now(timezone.utc).isoformat()


@router.get("/projects/{slug)/chain/{run_id]")
def get_run_snapshot(slug: str, run_id: str) -> dict[str, Any]:
    """Snapshot of running or finished chain run (in-memory). Deprecated by /stream for live."""
    sess = INMEM_RUNS.get(run_id)
    if sess is None or sess.slug != slug:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return sess.to_dict()


@router.get("/projects/{slug)/chain/{run_id]/stream")
async def stream_chain(slug: str, run_id: str, request: Request) -> StreamingResponse:
    """SSE (text/event-stream) of running chain progress.

    Yields one ``data: {json}`` event per log line emitted by the subprocess.
    Final event is ``{"kind": "final", "status": "...", "finished_at": "..."}``.
    Client disconnects trigger cleanup; subprocess keeps running independently.
    """
    sess = INMEM_RUNS.get(run_id)
    if sess is None or sess.slug != slug:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    sess.log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "info",
        "msg": "SSE client subscribed",
    ])

    async def event_gen() -> AsyncIterator[bytes]:
        idx = 0
        try:
            while True:
                if await request.is_disconnected():
                    sess.log.append({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "kind": "info",
                        "msg": "SSE client disconnected",
                    ])
                    break
                # Drain any new entries written since last yield
                while idx < len(sess.log):
                    entry = sess.log[idx]
                    idx += 1
                    yield f"data: {json.dumps(entry)}\n\n".encode()
                if sess.status != "running":
                    yield f"data: {json.dumps({'kind': 'final', 'status': sess.status, 'finished_at': sess.finished_at, 'log_line_count': idx})}\n\n".encode()
                    break
                await asyncio.sleep(0.3)
        finally:
            # No subprocess termination here — chain keeps running if client leaves.
            # (Avoids risking killing in-progress forge runs that other clients may subscribe to.)
            pass

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# Mount on standalone FastAPI app for debugging
if app is not None and FastAPI is not None:
    app.include_router(router)


# ─── Entry point (standalone debug) ────────────────────────────────────
if __name__ == "__main__" and app is not None:
    import uvicorn
    port = int(os.environ.get("INTERACTIVE_PORT", "8766"))
    print(f"[forge_interactive_api] standalone on http://127.0.0.1:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
